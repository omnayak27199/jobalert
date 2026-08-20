from __future__ import annotations

"""Match jobs to candidate profile + alert preferences."""

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from app.models.job import Job
from app.models.user import User, UserPreferences, UserProfile
from app.services.recruitment_content import sections_from_json

QUALIFICATION_LEVELS: dict[str, int] = {
    "10th": 1,
    "10th pass": 1,
    "matric": 1,
    "12th": 2,
    "12th pass": 2,
    "intermediate": 2,
    "iti": 3,
    "diploma": 4,
    "graduate": 5,
    "graduation": 5,
    "bachelor": 5,
    "b.a": 5,
    "b.sc": 5,
    "b.com": 5,
    "b.tech": 5,
    "b.e": 5,
    "engineering": 5,
    "post graduate": 6,
    "postgraduate": 6,
    "master": 6,
    "m.a": 6,
    "m.sc": 6,
    "m.com": 6,
    "m.tech": 6,
    "mba": 6,
    "medical": 6,
    "mbbs": 6,
    "phd": 7,
    "doctorate": 7,
}


@dataclass
class MatchResult:
    matched: bool
    score: int
    reasons: list[str]


def _parse_json_list(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _qualification_level(text: str) -> int:
    lower = text.lower()
    best = 0
    for key, level in QUALIFICATION_LEVELS.items():
        if key in lower:
            best = max(best, level)
    return best


def _user_age(profile: UserProfile, on_date: Optional[date] = None) -> Optional[int]:
    if not profile.date_of_birth:
        return None
    today = on_date or date.today()
    dob = profile.date_of_birth.date() if isinstance(profile.date_of_birth, datetime) else profile.date_of_birth
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years if 15 <= years <= 70 else None


def _parse_age_limit(age_limit: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Return (min_age, max_age) from strings like '18-32 years' or 'Max 40 years'."""
    if not age_limit:
        return None, None
    text = age_limit.lower()
    range_match = re.search(r"(\d{2})\s*[-to]+\s*(\d{2})", text)
    if range_match:
        return int(range_match.group(1)), int(range_match.group(2))
    max_match = re.search(r"(?:max|maximum|upto|up to)\s*(\d{2})", text)
    if max_match:
        return None, int(max_match.group(1))
    min_match = re.search(r"(?:min|minimum)\s*(\d{2})", text)
    if min_match:
        return int(min_match.group(1)), None
    single = re.search(r"\b(\d{2})\s*years?\b", text)
    if single:
        val = int(single.group(1))
        return None, val
    return None, None


def _job_sections(job: Job) -> dict[str, Any]:
    return sections_from_json(job.sections_json) if job.sections_json else {}


def _job_post_names(job: Job) -> list[str]:
    sections = _job_sections(job)
    names: list[str] = [job.title]
    if sections.get("title_hi"):
        names.append(str(sections["title_hi"]))
    for row in sections.get("vacancy_rows") or []:
        if row.get("post"):
            names.append(str(row["post"]))
        if row.get("post_hi"):
            names.append(str(row["post_hi"]))
    for row in sections.get("eligibility_rows") or []:
        if row.get("post"):
            names.append(str(row["post"]))
    return names


def _job_age_limit_text(job: Job) -> Optional[str]:
    if job.age_limit:
        return job.age_limit
    sections = _job_sections(job)
    parts = [sections.get("age_limit") or "", sections.get("age_relaxation") or ""]
    combined = ". ".join(p for p in parts if p).strip(". ")
    return combined or None


def _job_required_qualification(job: Job) -> int:
    texts: list[str] = []
    if job.qualification:
        texts.append(job.qualification)
    sections = _job_sections(job)
    for row in sections.get("eligibility_rows") or []:
        if row.get("education"):
            texts.append(str(row["education"]))
    for row in sections.get("vacancy_rows") or []:
        if row.get("qualification"):
            texts.append(str(row["qualification"]))
    if not texts:
        texts.append(job.title)
    return max(_qualification_level(t) for t in texts)


def _job_experience_hint(job: Job) -> Optional[float]:
    sections = _job_sections(job)
    for row in sections.get("eligibility_rows") or []:
        exp = str(row.get("experience") or "")
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|yr)", exp.lower())
        if match:
            return float(match.group(1))
    combined = " ".join(
        str(row.get("education") or "") for row in sections.get("eligibility_rows") or []
    )
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|yr)", combined.lower())
    if match:
        return float(match.group(1))
    if job.qualification:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|yr)", job.qualification.lower())
        if match:
            return float(match.group(1))
    return None


def _job_selection_modes(job: Job) -> list[str]:
    sections = _job_sections(job)
    modes: list[str] = []
    for step in sections.get("selection_steps") or []:
        lower = step.lower()
        if "written" in lower or "cbt" in lower:
            modes.append("written")
        if "pet" in lower or "physical" in lower:
            modes.append("physical")
        if "interview" in lower:
            modes.append("interview")
        if "skill" in lower or "trade" in lower:
            modes.append("skill")
    return modes


def _category_matches_reservation(profile: UserProfile, job: Job) -> bool:
    category = (profile.category or "").lower()
    if not category or category in ("general", "ur", "unreserved"):
        return True
    sections = _job_sections(job)
    reservation_text = " ".join(sections.get("reservation") or []).lower()
    if not reservation_text:
        return True
    aliases = {
        "sc": ("sc", "scheduled caste"),
        "st": ("st", "scheduled tribe"),
        "obc": ("obc", "other backward"),
        "ews": ("ews", "economically weaker"),
        "pwd": ("pwd", "pwbd", "disabilit"),
    }
    for key, terms in aliases.items():
        if key in category or any(t in category for t in terms):
            return any(t in reservation_text for t in terms)
    return True


def _states_from_prefs(prefs: Optional[UserPreferences]) -> list[str]:
    if not prefs:
        return []
    return _parse_json_list(prefs.states)


def job_matches_preferences(job: Job, prefs: UserPreferences) -> bool:
    states = _parse_json_list(prefs.states)
    categories = _parse_json_list(prefs.categories)
    qualifications = _parse_json_list(prefs.qualifications)
    organizations = _parse_json_list(prefs.organizations)

    if states and job.state and not any(
        s.lower() in (job.state or "").lower() for s in states
    ):
        if not any(s.lower() in job.title.lower() for s in states):
            return False

    if categories and job.category.value not in categories:
        return False

    if qualifications and job.qualification:
        if not any(q.lower() in job.qualification.lower() for q in qualifications):
            return False

    if organizations:
        if not any(o.upper() in job.organization.upper() for o in organizations):
            if not any(o.upper() in job.title.upper() for o in organizations):
                return False

    return True


def score_job_for_user(job: Job, user: User) -> MatchResult:
    """Score how well a job matches the candidate profile (0-100)."""
    profile = user.profile
    prefs = user.preferences
    reasons: list[str] = []
    score = 40  # base if job is a notification

    if not profile or not profile.profile_complete:
        if prefs and job_matches_preferences(job, prefs):
            return MatchResult(True, 55, ["Matches your alert preferences"])
        return MatchResult(False, 0, ["Complete your profile for personalized matches"])

    # State
    preferred_states = _states_from_prefs(prefs)
    if profile.current_state:
        preferred_states = list({profile.current_state, *preferred_states})
    if preferred_states:
        if job.state and any(s.lower() in job.state.lower() for s in preferred_states):
            score += 15
            reasons.append(f"State: {job.state}")
        elif any(s.lower() in job.title.lower() for s in preferred_states):
            score += 8
            reasons.append("Related to your preferred state")
        else:
            return MatchResult(False, score, ["Outside your preferred states"])

    # Qualification
    user_level = _qualification_level(profile.highest_qualification or "")
    for entry in _parse_json_list(profile.education_json):
        if isinstance(entry, dict) and entry.get("degree"):
            user_level = max(user_level, _qualification_level(str(entry["degree"])))
    job_level = _job_required_qualification(job)
    if user_level >= job_level:
        score += 20
        reasons.append("Qualification matches")
    elif user_level >= job_level - 1:
        score += 10
        reasons.append("Qualification close to requirement")
    else:
        return MatchResult(False, score, ["Qualification below job requirement"])

    # Experience
    required_exp = _job_experience_hint(job)
    user_exp = float(profile.experience_years or 0)
    if required_exp is None:
        score += 10
    elif user_exp >= required_exp:
        score += 15
        reasons.append(f"Experience: {user_exp} yrs")
    elif user_exp >= required_exp - 1:
        score += 8
        reasons.append("Experience close to requirement")
    else:
        score -= 5

    # Age
    user_age = _user_age(profile)
    min_age, max_age = _parse_age_limit(_job_age_limit_text(job))
    if user_age is not None and (min_age or max_age):
        if min_age and user_age < min_age:
            return MatchResult(False, score, ["Below minimum age limit"])
        if max_age and user_age > max_age:
            return MatchResult(False, score, ["Above maximum age limit"])
        score += 10
        reasons.append("Age within limit")

    # Category vs reservation
    if profile.category and not _category_matches_reservation(profile, job):
        score -= 8

    # Preferred posts / skills — match post names and eligibility text
    preferred_posts = _parse_json_list(profile.preferred_posts)
    skills = _parse_json_list(profile.skills)
    post_names = " ".join(_job_post_names(job)).lower()
    elig_text = " ".join(
        str(r.get("education", ""))
        for r in (_job_sections(job).get("eligibility_rows") or [])
    ).lower()

    if preferred_posts and any(p.lower() in post_names for p in preferred_posts):
        score += 12
        reasons.append("Matches preferred post")
    elif preferred_posts and any(p.lower() in job.title.lower() for p in preferred_posts):
        score += 8
        reasons.append("Related to preferred post")

    if skills:
        skill_hits = [s for s in skills if s.lower() in post_names or s.lower() in elig_text]
        if skill_hits:
            score += min(10, 3 * len(skill_hits))
            reasons.append(f"Skill match: {', '.join(skill_hits[:2])}")

    # Selection process awareness
    selection_modes = _job_selection_modes(job)
    if selection_modes:
        reasons.append(f"Selection: {', '.join(selection_modes[:3])}")
        score += 2

    # Organizations from prefs
    if prefs and job_matches_preferences(job, prefs):
        score += 5
        reasons.append("Matches alert filters")

    score = min(100, max(0, score))
    return MatchResult(matched=score >= 50, score=score, reasons=reasons)


def job_matches_user(job: Job, user: User) -> bool:
    """True when job matches profile and/or alert preferences."""
    profile = user.profile
    prefs = user.preferences

    if profile and profile.profile_complete:
        return score_job_for_user(job, user).matched

    if prefs:
        return job_matches_preferences(job, prefs)

    return False


def profile_stats(profile: UserProfile) -> dict[str, Any]:
    education = _parse_json_list(profile.education_json)
    experience = _parse_json_list(profile.experience_json)
    filled = 0
    total = 8
    if profile.date_of_birth:
        filled += 1
    if profile.highest_qualification:
        filled += 1
    if profile.current_state:
        filled += 1
    if profile.experience_years is not None:
        filled += 1
    if education:
        filled += 1
    if experience:
        filled += 1
    if _parse_json_list(profile.skills):
        filled += 1
    if _parse_json_list(profile.preferred_posts):
        filled += 1
    completeness = int(round(filled / total * 100))
    return {
        "completeness_percent": completeness,
        "education_entries": len(education),
        "experience_entries": len(experience),
        "experience_years": profile.experience_years,
        "highest_qualification": profile.highest_qualification,
        "current_state": profile.current_state,
        "profile_complete": profile.profile_complete,
    }
