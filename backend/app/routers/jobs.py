from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import desc, func, or_, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job, JobCategory, NewsItem
from app.services.application_dates import (
    closed_visibility_cutoff,
    compute_application_window,
    is_job_listable,
)
from app.services.ingestion import fetch_and_store_all
from app.services.job_quality import is_publishable_job, job_meets_quality
from app.services.job_repair import ensure_job_sections, needs_deep_enrich, repair_job, sections_are_usable
from app.services.bilingual_text import search_variants
from app.services.recruitment_content import sections_from_json
from app.services.job_sections import is_pdf_url, resolve_job_sections
from app.services.official_portals import resolve_vyapam_post_url
from app.services.official_urls import resolve_apply_url, resolve_official_url, sanitize_external_url

router = APIRouter()

logger = logging.getLogger(__name__)

_stats_cache: tuple[float, "StatsOut"] | None = None
STATS_CACHE_TTL_SECONDS = 60


class JobListOut(BaseModel):
    """Lightweight job payload for list/card views (no sections or full content)."""

    id: int
    title: str
    organization: str
    category: str
    scope: str
    state: Optional[str]
    vacancies: Optional[int]
    apply_url: Optional[str]
    source_name: str
    published_date: Optional[datetime]
    last_date: Optional[datetime]
    qualification: Optional[str]
    is_verified: bool
    days_left: Optional[int] = None
    application_status: str = "unknown"
    days_since_closed: Optional[int] = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    title: str
    organization: str
    category: str
    scope: str
    state: Optional[str]
    vacancies: Optional[int]
    apply_url: Optional[str]
    source_url: str
    source_name: str
    published_date: Optional[datetime]
    last_date: Optional[datetime]
    exam_date: Optional[datetime]
    qualification: Optional[str]
    description: Optional[str]
    full_content: Optional[str]
    notification_url: Optional[str]
    age_limit: Optional[str]
    application_fee: Optional[str]
    sections: Optional[dict[str, Any]] = None
    is_verified: bool
    days_left: Optional[int] = None
    application_status: str = "unknown"
    days_since_closed: Optional[int] = None

    class Config:
        from_attributes = True


class NewsOut(BaseModel):
    id: int
    title: str
    summary: Optional[str]
    url: str
    source: str
    category: str
    is_important: bool
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_jobs: int
    closing_soon: int
    today_updates: int
    states_covered: int
    verified_jobs: int


def _job_to_out(job: Job, *, deep_sections: bool = False) -> JobOut:
    window = compute_application_window(job.last_date)
    days_left = window["days_left"]
    application_status = window["status"]
    days_since_closed = window["days_since_closed"]

    apply_url = sanitize_external_url(job.apply_url, job.organization, job.title)
    if is_pdf_url(apply_url):
        apply_url = sanitize_external_url(
            resolve_apply_url(job.organization, job.title) or resolve_official_url(job.organization, job.title),
            job.organization,
            job.title,
        )
    notification_url = sanitize_external_url(
        job.notification_url or job.apply_url, job.organization, job.title
    )

    # Do not promote apply link once the application window is closed.
    if application_status == "closed":
        apply_url = None

    return JobOut(
        id=job.id,
        title=job.title,
        organization=job.organization,
        category=job.category.value,
        scope=job.scope.value,
        state=job.state,
        vacancies=job.vacancies,
        apply_url=apply_url,
        source_url=job.source_url,
        source_name=job.source_name,
        published_date=job.published_date,
        last_date=job.last_date,
        exam_date=job.exam_date,
        qualification=job.qualification,
        description=job.description,
        full_content=job.full_content,
        notification_url=notification_url,
        age_limit=job.age_limit,
        application_fee=job.application_fee,
        sections=sections_from_json(job.sections_json)
        if job.sections_json
        else resolve_job_sections(job, deep=deep_sections),
        is_verified=job.is_verified,
        days_left=days_left,
        application_status=application_status,
        days_since_closed=days_since_closed,
    )


def _job_to_list_out(job: Job) -> JobListOut:
    window = compute_application_window(job.last_date)
    apply_url = sanitize_external_url(job.apply_url, job.organization, job.title)
    if window["status"] == "closed":
        apply_url = None
    return JobListOut(
        id=job.id,
        title=job.title,
        organization=job.organization,
        category=job.category.value,
        scope=job.scope.value,
        state=job.state,
        vacancies=job.vacancies,
        apply_url=apply_url,
        source_name=job.source_name,
        published_date=job.published_date,
        last_date=job.last_date,
        qualification=job.qualification,
        is_verified=job.is_verified,
        days_left=window["days_left"],
        application_status=window["status"],
        days_since_closed=window["days_since_closed"],
    )


def _apply_listable_date_filter(query):
    """Open jobs + recently closed (within grace period). Jobs without dates stay visible."""
    cutoff = closed_visibility_cutoff()
    return query.filter((Job.last_date.is_(None)) | (Job.last_date >= cutoff))


@router.get("/jobs", response_model=List[JobListOut])
def list_jobs(
    response: Response,
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    state: Optional[str] = None,
    scope: Optional[str] = None,
    search: Optional[str] = None,
    organization: Optional[str] = None,
    closing_soon: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    response.headers["Cache-Control"] = "public, max-age=60"

    query = db.query(Job).filter(Job.is_active == True)  # noqa: E712
    query = _apply_listable_date_filter(query)

    if category:
        try:
            cat = JobCategory(category)
            query = query.filter(Job.category == cat)
        except ValueError:
            pass

    if state:
        query = query.filter(Job.state.ilike(f"%{state}%"))

    if scope:
        query = query.filter(Job.scope == scope)

    if organization:
        org = organization.strip()
        if org:
            query = query.filter(Job.organization.ilike(f"%{org}%"))

    if search:
        clauses = []
        for variant in search_variants(search):
            pattern = f"%{variant}%"
            clauses.append(Job.title.ilike(pattern))
            clauses.append(Job.organization.ilike(pattern))
            clauses.append(Job.full_content.ilike(pattern))
            clauses.append(Job.sections_json.ilike(pattern))
        query = query.filter(or_(*clauses))

    if closing_soon:
        week_later = datetime.utcnow() + timedelta(days=7)
        query = query.filter(
            Job.last_date.isnot(None),
            Job.last_date <= week_later,
            Job.last_date >= datetime.utcnow(),
        )

    fetch_limit = min(limit * 2, 200)
    jobs = query.order_by(desc(Job.published_date)).offset(offset).limit(fetch_limit).all()
    jobs = [j for j in jobs if is_publishable_job(j) and is_job_listable(j.last_date)]
    jobs = jobs[:limit]
    return [_job_to_list_out(j) for j in jobs]


def _ensure_full_content(job: Job) -> None:
    """Build minimal on-site content without network (sync fallback)."""
    if job.full_content:
        return
    from app.services.detail_fetcher import build_full_content
    from app.services.org_resolver import normalize_organization

    org = normalize_organization(job.title, job.organization)
    job.organization = org
    last_fmt = job.last_date.strftime("%d %b %Y") if job.last_date else None
    exam_fmt = job.exam_date.strftime("%d %b %Y") if job.exam_date else None
    job.full_content = build_full_content(
        title=job.title,
        organization=org,
        state=job.state,
        category=job.category.value,
        vacancies=job.vacancies,
        qualification=job.qualification,
        last_date=last_fmt,
        exam_date=exam_fmt,
        description=job.description,
    )
    if not job.notification_url:
        job.notification_url = resolve_official_url(org, job.title)


def _background_deep_enrich(job_id: int) -> None:
    """Fetch PDF/portal details without blocking the HTTP response."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or not needs_deep_enrich(job):
            return
        ensure_job_sections(job, deep=True)
        db.commit()
    except Exception as exc:
        logger.warning("Background enrich failed for job %s: %s", job_id, exc)
        db.rollback()
    finally:
        db.close()


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "public, max-age=120"
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()  # noqa: E712
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job_meets_quality(job):
        raise HTTPException(status_code=404, detail="Job not found")

    if not is_job_listable(job.last_date):
        raise HTTPException(
            status_code=404,
            detail="This notification closed more than 7 days ago and is no longer available.",
        )

    # Fast path: serve cached sections — no PDF/portal fetch on page view
    if sections_are_usable(job):
        if needs_deep_enrich(job):
            background_tasks.add_task(_background_deep_enrich, job.id)
        return _job_to_out(job, deep_sections=False)

    # Missing sections: build skeleton only (no network I/O)
    ensure_job_sections(job, deep=False)
    if needs_deep_enrich(job):
        background_tasks.add_task(_background_deep_enrich, job.id)
    try:
        db.commit()
    except Exception:
        db.rollback()

    return _job_to_out(job, deep_sections=False)


@router.get("/news", response_model=List[NewsOut])
def list_news(
    important_only: bool = False,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(NewsItem)
    if important_only:
        query = query.filter(NewsItem.is_important == True)  # noqa: E712
    items = query.order_by(desc(NewsItem.published_at)).limit(limit).all()
    return items


@router.get("/stats", response_model=StatsOut)
def get_stats(response: Response, db: Session = Depends(get_db)):
    global _stats_cache
    response.headers["Cache-Control"] = "public, max-age=60"

    now = time.time()
    if _stats_cache and now - _stats_cache[0] < STATS_CACHE_TTL_SECONDS:
        return _stats_cache[1]

    notif = JobCategory.NOTIFICATION
    cutoff = closed_visibility_cutoff()
    base_jobs = (
        db.query(Job)
        .filter(
            Job.is_active == True,  # noqa: E712
            Job.category == notif,
            (Job.last_date.is_(None)) | (Job.last_date >= cutoff),
        )
        .all()
    )
    jobs = [j for j in base_jobs if is_publishable_job(j)]
    total = len(jobs)
    week_later = datetime.utcnow() + timedelta(days=7)
    now_dt = datetime.utcnow()
    closing = sum(
        1
        for j in jobs
        if j.last_date is not None and now_dt <= j.last_date <= week_later
    )
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = sum(1 for j in jobs if j.created_at and j.created_at >= today)
    states = len({j.state for j in jobs if j.state})
    verified = sum(1 for j in jobs if j.is_verified)
    result = StatsOut(
        total_jobs=total,
        closing_soon=closing,
        today_updates=today_count,
        states_covered=states,
        verified_jobs=verified,
    )
    _stats_cache = (now, result)
    return result


@router.get("/states")
def list_states(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "public, max-age=120"
    cutoff = closed_visibility_cutoff()
    states = (
        db.query(Job.state, func.count(Job.id).label("count"))
        .filter(
            Job.state.isnot(None),
            Job.is_active == True,  # noqa: E712
            Job.category == JobCategory.NOTIFICATION,
            (Job.last_date.is_(None)) | (Job.last_date >= cutoff),
        )
        .group_by(Job.state)
        .order_by(desc("count"))
        .all()
    )
    return [{"state": s[0], "count": s[1]} for s in states]


@router.post("/fetch")
async def trigger_fetch(db: Session = Depends(get_db)):
    result = await fetch_and_store_all(db)
    return {"status": "ok", **result}


@router.get("/sources")
def list_sources():
    from app.scrapers.sources_registry import (
        CENTRAL_GOVERNMENT_SOURCES,
        PSU_SOURCES,
        STATE_SOURCE_GROUPS,
        registry_stats,
    )

    stats = registry_stats()
    return {
        "stats": stats,
        "central_government": [
            {
                "name": s.name,
                "url": s.url,
                "organization": s.organization or s.name,
            }
            for s in CENTRAL_GOVERNMENT_SOURCES
        ],
        "states": [
            {
                "state": group.state,
                "sites": [
                    {
                        "name": s.name,
                        "url": s.url,
                        "organization": s.organization or s.name,
                    }
                    for s in group.sites
                ],
            }
            for group in STATE_SOURCE_GROUPS
        ],
        "psu": [
            {
                "name": s.name,
                "url": s.url,
                "organization": s.organization or s.name,
            }
            for s in PSU_SOURCES
        ],
    }
