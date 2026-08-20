from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.user import FavoriteJob, User, UserPreferences, UserProfile
from app.services.profile_service import apply_profile_fields
from app.services.auth import (
    create_access_token,
    email_is_admin,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2)
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    phone: Optional[str]
    is_admin: bool = False

    class Config:
        from_attributes = True


class PreferencesIn(BaseModel):
    states: List[str] = []
    categories: List[str] = []
    qualifications: List[str] = []
    organizations: List[str] = []
    email_alerts: bool = True
    whatsapp_alerts: bool = False
    alert_frequency: str = "instant"


class PreferencesOut(PreferencesIn):
    pass


class FavoriteOut(BaseModel):
    job_id: int
    created_at: datetime
    job: Optional[dict] = None


class EducationEntry(BaseModel):
    degree: str
    stream: Optional[str] = None
    board_university: Optional[str] = None
    year: Optional[int] = None
    percentage: Optional[str] = None


class ExperienceEntry(BaseModel):
    role: str
    organization: Optional[str] = None
    years: Optional[float] = None
    domain: Optional[str] = None


class ProfileIn(BaseModel):
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    current_state: Optional[str] = None
    highest_qualification: Optional[str] = None
    education: List[EducationEntry] = []
    experience_years: Optional[float] = None
    experience: List[ExperienceEntry] = []
    skills: List[str] = []
    preferred_posts: List[str] = []
    preferred_departments: List[str] = []
    bio: Optional[str] = None


class ProfileOut(BaseModel):
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    current_state: Optional[str] = None
    highest_qualification: Optional[str] = None
    education: List[EducationEntry] = []
    experience_years: Optional[float] = None
    experience: List[ExperienceEntry] = []
    skills: List[str] = []
    preferred_posts: List[str] = []
    preferred_departments: List[str] = []
    bio: Optional[str] = None
    profile_complete: bool = False
    stats: dict = {}


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class MatchedJobOut(BaseModel):
    job: "JobOut"
    match_score: int
    match_reasons: List[str]


# ── Auth ─────────────────────────────────────────────────────────────────────

def _ensure_configured_admin(user: User, db: Session) -> User:
    """Promote user when their email is listed in ADMIN_EMAILS."""
    if not user.is_admin and email_is_admin(user.email):
        user.is_admin = True
        db.commit()
        db.refresh(user)
    return user


@router.post("/auth/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        if db.query(User).filter(User.email == body.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            name=body.name,
            phone=body.phone,
            is_admin=email_is_admin(body.email),
        )
        db.add(user)
        db.flush()
        db.add(UserPreferences(user_id=user.id))
        db.add(UserProfile(user_id=user.id))
        db.commit()
        db.refresh(user)
        token = create_access_token(user.id, user.email)
        return TokenResponse(access_token=token, user=UserOut.model_validate(user))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Registration failed for %s: %s", body.email, exc)
        raise HTTPException(
            status_code=500,
            detail="Registration failed. Please try again or contact support.",
        ) from exc


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    user = _ensure_configured_admin(user, db)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/auth/admin-login", response_model=TokenResponse)
def admin_login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")
    user = _ensure_configured_admin(user, db)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="This account does not have admin access")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = _ensure_configured_admin(user, db)
    return user


# ── Preferences ──────────────────────────────────────────────────────────────

def _prefs_to_out(prefs: UserPreferences) -> PreferencesOut:
    return PreferencesOut(
        states=json.loads(prefs.states or "[]"),
        categories=json.loads(prefs.categories or "[]"),
        qualifications=json.loads(prefs.qualifications or "[]"),
        organizations=json.loads(prefs.organizations or "[]"),
        email_alerts=prefs.email_alerts,
        whatsapp_alerts=prefs.whatsapp_alerts,
        alert_frequency=prefs.alert_frequency,
    )


@router.get("/users/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.preferences:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        user.preferences = prefs
    return _prefs_to_out(user.preferences)


@router.put("/users/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = user.preferences or UserPreferences(user_id=user.id)
    prefs.states = json.dumps(body.states)
    prefs.categories = json.dumps(body.categories)
    prefs.qualifications = json.dumps(body.qualifications)
    prefs.organizations = json.dumps(body.organizations)
    prefs.email_alerts = body.email_alerts
    prefs.whatsapp_alerts = body.whatsapp_alerts
    prefs.alert_frequency = body.alert_frequency
    if not user.preferences:
        db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return _prefs_to_out(prefs)


def _profile_to_out(profile: UserProfile) -> ProfileOut:
    from app.services.job_matcher import profile_stats

    return ProfileOut(
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        category=profile.category,
        current_state=profile.current_state,
        highest_qualification=profile.highest_qualification,
        education=[EducationEntry(**e) for e in json.loads(profile.education_json or "[]") if isinstance(e, dict)],
        experience_years=profile.experience_years,
        experience=[ExperienceEntry(**e) for e in json.loads(profile.experience_json or "[]") if isinstance(e, dict)],
        skills=json.loads(profile.skills or "[]"),
        preferred_posts=json.loads(profile.preferred_posts or "[]"),
        preferred_departments=json.loads(profile.preferred_departments or "[]"),
        bio=profile.bio,
        profile_complete=profile.profile_complete,
        stats=profile_stats(profile),
    )


def _ensure_profile(user: User, db: Session) -> UserProfile:
    if user.profile:
        return user.profile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    user.profile = profile
    return profile


@router.get("/users/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _ensure_profile(user, db)
    return _profile_to_out(profile)


@router.put("/users/profile", response_model=ProfileOut)
def update_profile(
    body: ProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _ensure_profile(user, db)
    apply_profile_fields(
        profile,
        {
            "date_of_birth": body.date_of_birth,
            "gender": body.gender,
            "category": body.category,
            "current_state": body.current_state,
            "highest_qualification": body.highest_qualification,
            "education": [e.model_dump() for e in body.education],
            "experience_years": body.experience_years,
            "experience": [e.model_dump() for e in body.experience],
            "skills": body.skills,
            "preferred_posts": body.preferred_posts,
            "preferred_departments": body.preferred_departments,
            "bio": body.bio,
        },
    )

    # Sync profile state/qualification into alert preferences when empty
    prefs = user.preferences or UserPreferences(user_id=user.id)
    states = json.loads(prefs.states or "[]")
    if body.current_state and body.current_state not in states:
        states.append(body.current_state)
        prefs.states = json.dumps(states)
    quals = json.loads(prefs.qualifications or "[]")
    if body.highest_qualification and body.highest_qualification not in quals:
        quals.append(body.highest_qualification)
        prefs.qualifications = json.dumps(quals)
    if not user.preferences:
        db.add(prefs)

    db.commit()
    db.refresh(profile)
    return _profile_to_out(profile)


@router.patch("/users/me", response_model=UserOut)
def update_me(
    body: UserUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/matched-jobs")
def matched_jobs(
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.job import Job, JobCategory
    from app.routers.jobs import JobOut, _job_to_out
    from app.services.application_dates import closed_visibility_cutoff, is_job_listable
    from app.services.job_matcher import score_job_for_user
    from app.services.job_quality import is_publishable_job

    _ensure_profile(user, db)
    cutoff = closed_visibility_cutoff()
    query = db.query(Job).filter(
        Job.is_active == True,  # noqa: E712
        Job.category == JobCategory.NOTIFICATION,
        (Job.last_date.is_(None)) | (Job.last_date >= cutoff),
    )
    jobs = query.order_by(Job.published_date.desc()).limit(300).all()

    scored: list[MatchedJobOut] = []
    for job in jobs:
        if not is_publishable_job(job) or not is_job_listable(job.last_date):
            continue
        result = score_job_for_user(job, user)
        if result.matched:
            scored.append(
                MatchedJobOut(
                    job=_job_to_out(job),
                    match_score=result.score,
                    match_reasons=result.reasons,
                )
            )

    scored.sort(key=lambda x: x.match_score, reverse=True)
    return {"jobs": scored[:limit], "profile_complete": bool(user.profile and user.profile.profile_complete)}


# ── Favorites ─────────────────────────────────────────────────────────────────

@router.get("/users/favorites")
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favs = (
        db.query(FavoriteJob, Job)
        .join(Job, FavoriteJob.job_id == Job.id)
        .filter(FavoriteJob.user_id == user.id)
        .order_by(FavoriteJob.created_at.desc())
        .all()
    )
    from app.routers.jobs import _job_to_out
    return [
        {"job_id": f.job_id, "created_at": f.created_at, "job": _job_to_out(j)}
        for f, j in favs
    ]


@router.post("/users/favorites/{job_id}")
def add_favorite(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    existing = (
        db.query(FavoriteJob)
        .filter(FavoriteJob.user_id == user.id, FavoriteJob.job_id == job_id)
        .first()
    )
    if existing:
        return {"status": "already_saved"}
    db.add(FavoriteJob(user_id=user.id, job_id=job_id))
    db.commit()
    return {"status": "saved"}


@router.delete("/users/favorites/{job_id}")
def remove_favorite(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fav = (
        db.query(FavoriteJob)
        .filter(FavoriteJob.user_id == user.id, FavoriteJob.job_id == job_id)
        .first()
    )
    if fav:
        db.delete(fav)
        db.commit()
    return {"status": "removed"}


@router.get("/users/favorites/check/{job_id}")
def check_favorite(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exists = (
        db.query(FavoriteJob)
        .filter(FavoriteJob.user_id == user.id, FavoriteJob.job_id == job_id)
        .first()
        is not None
    )
    return {"saved": exists}
