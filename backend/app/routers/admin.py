from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.job import Job, JobCategory, JobScope
from app.models.user import User
from app.services.alerts import dispatch_alerts_for_new_jobs
from app.services.cleanup_service import run_cleanup
from app.services.date_parse import parse_flexible_date
from app.services.ingestion import _to_enum_category, _to_enum_scope, fetch_and_store_all
from app.services.job_repair import ensure_job_sections, deep_enrich_all_jobs, repair_all_jobs
from app.services.pdf_ingestion import save_parsed_pdf
from app.services.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")):
    if settings.admin_secret and x_admin_key != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin key. Pass X-Admin-Key header.")


class FetchResult(BaseModel):
    status: str
    jobs: int
    new_jobs: int
    news: int
    alerts: Optional[int] = None


class PDFUploadResult(BaseModel):
    status: str
    job_id: int
    title: str
    organization: str
    state: Optional[str]
    category: str
    last_date: Optional[str]
    message: str
    alerts_sent: Optional[dict[str, int]] = None


class ManualJobIn(BaseModel):
    title: str = Field(min_length=5, max_length=500)
    organization: str = Field(min_length=2, max_length=200)
    category: str = "notification"
    scope: str = "state"
    state: Optional[str] = None
    vacancies: Optional[int] = None
    qualification: Optional[str] = None
    description: Optional[str] = None
    last_date: Optional[str] = None
    exam_date: Optional[str] = None
    apply_url: Optional[str] = None
    notification_url: Optional[str] = None
    age_limit: Optional[str] = None
    application_fee: Optional[str] = None
    send_alerts: bool = True


class JobUpdateIn(BaseModel):
    title: Optional[str] = None
    organization: Optional[str] = None
    state: Optional[str] = None
    category: Optional[str] = None
    vacancies: Optional[int] = None
    qualification: Optional[str] = None
    description: Optional[str] = None
    last_date: Optional[str] = None
    exam_date: Optional[str] = None
    apply_url: Optional[str] = None
    notification_url: Optional[str] = None
    age_limit: Optional[str] = None
    application_fee: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AdminJobOut(BaseModel):
    id: int
    title: str
    organization: str
    state: Optional[str]
    category: str
    is_active: bool
    is_verified: bool
    last_date: Optional[datetime]
    created_at: datetime
    source_name: str

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    total_jobs: int
    active_jobs: int
    inactive_jobs: int
    today_jobs: int
    total_users: int
    states_covered: int
    verified_jobs: int


class AdminUserOut(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


def _apply_dates(job: Job, last_date: Optional[str], exam_date: Optional[str]) -> None:
    if last_date is not None:
        parsed = parse_flexible_date(last_date)
        job.last_date = parsed
    if exam_date is not None:
        parsed = parse_flexible_date(exam_date)
        job.exam_date = parsed


def _job_to_admin(job: Job) -> AdminJobOut:
    return AdminJobOut(
        id=job.id,
        title=job.title,
        organization=job.organization,
        state=job.state,
        category=job.category.value,
        is_active=job.is_active,
        is_verified=job.is_verified,
        last_date=job.last_date,
        created_at=job.created_at,
        source_name=job.source_name,
    )


@router.get("/admin/dashboard", response_model=DashboardOut)
def admin_dashboard(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.query(func.count(Job.id)).scalar() or 0
    active = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar() or 0  # noqa: E712
    inactive = total - active
    today_jobs = (
        db.query(func.count(Job.id)).filter(Job.created_at >= today).scalar() or 0
    )
    users = db.query(func.count(User.id)).scalar() or 0
    states = (
        db.query(func.count(func.distinct(Job.state)))
        .filter(Job.state.isnot(None), Job.is_active == True)  # noqa: E712
        .scalar()
        or 0
    )
    verified = db.query(func.count(Job.id)).filter(Job.is_verified == True).scalar() or 0  # noqa: E712
    return DashboardOut(
        total_jobs=total,
        active_jobs=active,
        inactive_jobs=inactive,
        today_jobs=today_jobs,
        total_users=users,
        states_covered=states,
        verified_jobs=verified,
    )


@router.get("/admin/users")
def list_admin_users(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    query = db.query(User)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(User.email.ilike(like), User.name.ilike(like), User.phone.ilike(like))
        )
    total = query.count()
    users = query.order_by(desc(User.created_at)).offset(offset).limit(limit).all()
    return {
        "total": total,
        "users": [AdminUserOut.model_validate(u) for u in users],
    }


@router.get("/admin/jobs")
def list_admin_jobs(
    q: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    query = db.query(Job)
    if active is not None:
        query = query.filter(Job.is_active == active)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(Job.title.ilike(pattern), Job.organization.ilike(pattern), Job.state.ilike(pattern))
        )
    total = query.count()
    jobs = query.order_by(desc(Job.created_at)).offset(offset).limit(limit).all()
    return {
        "total": total,
        "jobs": [_job_to_admin(j) for j in jobs],
    }


@router.post("/admin/jobs")
async def create_manual_job(
    body: ManualJobIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    slug = hashlib.md5(f"{body.title}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
    source_url = f"manual://admin/{slug}"

    job = Job(
        title=body.title.strip(),
        organization=body.organization.strip(),
        category=_to_enum_category(body.category),
        scope=_to_enum_scope(body.scope),
        state=body.state,
        vacancies=body.vacancies,
        qualification=body.qualification,
        description=body.description,
        apply_url=body.apply_url,
        notification_url=body.notification_url or body.apply_url,
        age_limit=body.age_limit,
        application_fee=body.application_fee,
        source_url=source_url,
        source_name="Manual Admin Entry",
        published_date=datetime.utcnow(),
        is_verified=True,
        is_active=True,
    )
    _apply_dates(job, body.last_date, body.exam_date)
    db.add(job)
    db.commit()
    db.refresh(job)

    ensure_job_sections(job, deep=bool(body.notification_url or body.apply_url))
    db.commit()
    db.refresh(job)

    alerts: dict[str, int] = {}
    if body.send_alerts:
        alerts = await dispatch_alerts_for_new_jobs(db, [job])

    return {
        "status": "created",
        "job_id": job.id,
        "job": _job_to_admin(job),
        "alerts": alerts,
    }


@router.patch("/admin/jobs/{job_id}")
def update_job(
    job_id: int,
    body: JobUpdateIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    for field in (
        "title",
        "organization",
        "state",
        "vacancies",
        "qualification",
        "description",
        "apply_url",
        "notification_url",
        "age_limit",
        "application_fee",
        "is_active",
        "is_verified",
    ):
        val = getattr(body, field)
        if val is not None:
            setattr(job, field, val)

    if body.category is not None:
        job.category = _to_enum_category(body.category)
    if body.last_date is not None or body.exam_date is not None:
        _apply_dates(job, body.last_date, body.exam_date)

    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return {"status": "updated", "job": _job_to_admin(job)}


@router.delete("/admin/jobs/{job_id}")
def deactivate_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_active = False
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "deactivated", "job_id": job_id}


@router.post("/admin/jobs/{job_id}/activate")
def activate_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_active = True
    job.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "activated", "job_id": job_id}


@router.post("/admin/jobs/{job_id}/re-enrich")
def re_enrich_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    ensure_job_sections(job, deep=True)
    db.commit()
    db.refresh(job)
    return {"status": "enriched", "job": _job_to_admin(job)}


@router.post("/admin/jobs/{job_id}/dispatch-alerts")
async def dispatch_job_alerts(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.is_active:
        raise HTTPException(status_code=400, detail="Job is inactive")
    result = await dispatch_alerts_for_new_jobs(db, [job])
    return {"status": "ok", **result}


@router.post("/admin/fetch")
async def manual_fetch(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    result = await fetch_and_store_all(db)
    return {
        "status": "ok",
        "message": f"Fetched {result['jobs']} jobs ({result['new_jobs']} new)",
        **result,
    }


@router.post("/admin/cleanup")
def admin_cleanup(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    result = run_cleanup(db)
    return {"status": "ok", **result}


@router.post("/admin/repair")
async def admin_repair(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    result = await repair_all_jobs(db)
    return {"status": "ok", **result}


@router.post("/admin/enrich-all")
def admin_enrich_all(
    force: bool = Query(False, description="Re-parse every job even if sections look complete"),
    limit: int = Query(0, description="Max jobs to process (0 = all active)"),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    """Deep-parse PDFs/portals and rebuild detail sections for all active jobs."""
    result = deep_enrich_all_jobs(
        db,
        limit=limit if limit > 0 else None,
        force=force,
    )
    return {"status": "ok", **result}


@router.post("/admin/upload-pdf", response_model=PDFUploadResult)
async def upload_pdf(
    file: UploadFile = File(...),
    state: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    apply_url: Optional[str] = Form(None),
    notification_url: Optional[str] = Form(None),
    send_alerts: bool = Form(True),
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF too large (max 20MB)")

    try:
        parsed = await parse_pdf(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if state:
        parsed.state = state
    if organization:
        parsed.organization = organization
    if title:
        parsed.title = title.strip()

    job = save_parsed_pdf(db, parsed, file.filename, apply_url=apply_url)
    if notification_url:
        job.notification_url = notification_url
    ensure_job_sections(job, deep=True)
    db.commit()
    db.refresh(job)

    alerts: dict[str, int] = {}
    if send_alerts:
        alerts = await dispatch_alerts_for_new_jobs(db, [job])

    return PDFUploadResult(
        status="published",
        job_id=job.id,
        title=job.title,
        organization=job.organization,
        state=job.state,
        category=job.category.value,
        last_date=job.last_date.isoformat() if job.last_date else None,
        message="PDF parsed and published successfully",
        alerts_sent=alerts or None,
    )
