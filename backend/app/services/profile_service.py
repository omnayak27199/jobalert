from __future__ import annotations

"""Profile update helpers."""

import json
from datetime import datetime
from typing import Any

from app.models.user import UserProfile


def compute_profile_complete(profile: UserProfile) -> bool:
    """Profile is complete enough for personalized matching."""
    has_qual = bool(profile.highest_qualification)
    has_state = bool(profile.current_state)
    has_exp = profile.experience_years is not None
    has_edu = bool(_parse_json(profile.education_json))
    return has_qual and has_state and (has_exp or has_edu)


def _parse_json(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def apply_profile_fields(profile: UserProfile, data: dict[str, Any]) -> None:
    if "date_of_birth" in data:
        profile.date_of_birth = data["date_of_birth"]
    if "gender" in data:
        profile.gender = data["gender"]
    if "category" in data:
        profile.category = data["category"]
    if "current_state" in data:
        profile.current_state = data["current_state"]
    if "highest_qualification" in data:
        profile.highest_qualification = data["highest_qualification"]
    if "education" in data:
        profile.education_json = json.dumps(data["education"])
    if "experience_years" in data:
        profile.experience_years = data["experience_years"]
    if "experience" in data:
        profile.experience_json = json.dumps(data["experience"])
    if "skills" in data:
        profile.skills = json.dumps(data["skills"])
    if "preferred_posts" in data:
        profile.preferred_posts = json.dumps(data["preferred_posts"])
    if "preferred_departments" in data:
        profile.preferred_departments = json.dumps(data["preferred_departments"])
    if "bio" in data:
        profile.bio = data["bio"]
    profile.profile_complete = compute_profile_complete(profile)
    profile.updated_at = datetime.utcnow()
