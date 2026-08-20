from __future__ import annotations

"""Filter junk portal links and validate job alert listings."""

import re
from typing import Optional
from urllib.parse import urlparse

from app.models.job import Job, JobCategory

# Titles that are navigation labels, not real recruitments
JUNK_TITLE_EXACT = {
    "recruitment",
    "recruitment notices",
    "recruitment corner",
    "orders/notifications",
    "orders / notifications",
    "click here to apply for service",
    "click here to apply",
    "forms & format",
    "forms and format",
    "examination",
    "admit card",
    "online application",
    "result",
    "results",
    "forums & format",
    "information technology",
    "information & public relations",
    "national informatics centre",
    "national informatics centre (nic) ladakh",
    "web information manager",
    "ministry of electronics & information technology",
    "jk bank recruitment",
    "ladakh police recruitment",
    "question bank",
    "draft rules",
    "online application",
    "apply online",
    "pat-2026 for admission",
    "archived vacancies",
    "current vacancies",
    "recruitment calendar",
    "recruitment rules",
    "annexures",
    "eligible list",
    "programme for interview",
    "notification",
    "recruitment advertisements",
    "recruitment requisition",
    "recruitment policy",
    "archive recruitment",
    "gazette notification",
    "examination calendar",
    "advertisement",
    "official notification pdf",
}

JUNK_TITLE_PREFIXES = (
    "click here",
    "click to",
    "read more",
    "view all",
    "see all",
    "download ",
    "for more",
    "online application -",
    "online application-",
    "admit card",
    "question bank",
    "notification :-",
    "notice:-",
    "notice regarding advt",
)

JUNK_URL_FRAGMENTS = (
    "#1745479152477",
    "/web-information-manager",
    "/online-citizen-services/",
    "/nic/",
    "/recruitment-corner/",
    "postid=recresult",
    "postid=admit",
    "postid=result",
)

NON_JOB_CATEGORIES = {
    JobCategory.ADMIT_CARD,
    JobCategory.RESULT,
    JobCategory.ANSWER_KEY,
    JobCategory.SYLLABUS,
    JobCategory.EDUCATION,
}

JUNK_TITLE_CONTAINS = (
    "eligible list for interview",
    "programme for interview",
    "revised programme for interview",
    "departmental examination",
    "annexures (",
    "recruitment rules of",
    "question bank",
    "roll no. wise marks",
    "schedule of interview",
    "interview letter for the post",
    "service is currently closed",
    "final rejection for the post",
    "combined subject knowledge test",
    "question paper for",
    "descriptive examination",
    "selection list",
    "mark list",
    "obtained mark",
    "caveat vigyapti",
    "score summary",
    "tentative schedule of written",
    "tentative revised schedule",
    "scheme of examination",
    "programme of the written examination",
    "written examination for recruitment",
    "interview/personality test",
    "personality test for the post",
    "provisional answer key",
    "representations about eligibility",
    "extension of period for submission",
    "postponed of recruitment examination",
    "availability of provisional",
    "submission of documents for",
)

RECRUITMENT_SIGNALS = re.compile(
    r"\b(recruitment|vacancy|vacancies|online form|apply online|bharti|"
    r"notification|advertisement|posts?\s+\d|\d+\s+posts?|last date|"
    r"store keeper|fireman|clerk|assistant|officer|teacher|constable|"
    r"inspector|engineer|manager|driver|mechanic)\b",
    re.I,
)


def _normalized_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def is_portal_homepage_url(url: str) -> bool:
    """True when URL is just a department homepage — not a specific notification."""
    if not url or url.startswith("official://"):
        return False
    parsed = urlparse(url.strip())
    path = (parsed.path or "").strip("/").lower()
    if not path:
        return True
    return path in {"index.html", "index.php", "home", "default.aspx", "main", "welcome"}


def is_homepage_scrape_content(text: Optional[str]) -> bool:
    if not text:
        return False
    lower = text.lower()
    if "welcome to " in lower and ("javascript is disabled" in lower or "help desk" in lower):
        return True
    if "welcome to " in lower and "recruitment overview" in lower and len(text) < 1200:
        return True
    return False


def has_actionable_job_data(job: Job) -> bool:
    """Must have real notification data — not just a portal homepage title."""
    if job.sections_json:
        return True
    if job.vacancies and job.vacancies > 0:
        return True
    if job.last_date:
        return True
    if job.qualification and len(job.qualification.strip()) > 15:
        return True

    if is_junk_title(job.title):
        return False

    notif = (job.notification_url or "").lower()
    if ".pdf" in notif or "/uploads/" in notif:
        return True

    source = job.source_url or ""
    if (
        not is_portal_homepage_url(source)
        and RECRUITMENT_SIGNALS.search(job.title)
        and (len(job.title) >= 25 or re.search(r"\b20\d{2}\b", job.title))
    ):
        return True

    if (
        job.description
        and len(job.description.strip()) > 80
        and RECRUITMENT_SIGNALS.search(job.title)
    ):
        return True

    return False


def is_junk_title(title: str) -> bool:
    t = _normalized_title(title)
    if any(kw in t for kw in JUNK_TITLE_CONTAINS):
        return True
    if not t or len(t) < 12:
        # Allow short titles only if they clearly mention a post + year
        if not re.search(r"\b(20\d{2}|recruitment|vacancy|form)\b", t, re.I):
            return True
    if t in JUNK_TITLE_EXACT:
        return True
    if any(t.startswith(p) for p in JUNK_TITLE_PREFIXES):
        return True
    # Single generic word in ALL CAPS
    if title.isupper() and len(title.split()) <= 2 and not re.search(r"\d", title):
        return True
    # Must look like a recruitment notification
    if not RECRUITMENT_SIGNALS.search(title):
        if len(title) < 40 and not re.search(r"\b20\d{2}\b", title):
            return True
    return False


def is_junk_url(url: str) -> bool:
    lower = (url or "").lower()
    if any(frag in lower for frag in JUNK_URL_FRAGMENTS):
        return True
    if "#1745479152477" in lower or "#36683661" in lower:
        return True
    return False


def is_valid_scraped_job(title: str, url: str, category: str) -> bool:
    if category != "notification":
        return False
    if is_portal_homepage_url(url):
        return False
    if is_junk_title(title) or is_junk_url(url):
        return False
    return True


def job_meets_quality(job: Job) -> bool:
    """Content quality gate — independent of is_active flag."""
    if job.category in NON_JOB_CATEGORIES:
        return False
    if is_junk_title(job.title) or is_junk_url(job.source_url or ""):
        return False
    if is_portal_homepage_url(job.source_url or "") and not has_actionable_job_data(job):
        return False
    if is_homepage_scrape_content(job.full_content) and not has_actionable_job_data(job):
        return False
    if not has_actionable_job_data(job):
        return False
    return True


def is_publishable_job(job: Job) -> bool:
    if not job.is_active:
        return False
    return job_meets_quality(job)


def cleanup_reason(job: Job) -> Optional[str]:
    if job.category in NON_JOB_CATEGORIES:
        return f"non-job category: {job.category.value}"
    if is_junk_title(job.title):
        return f"junk title: {job.title[:60]}"
    if is_junk_url(job.source_url or ""):
        return f"junk url: {job.source_url[:80]}"
    if is_portal_homepage_url(job.source_url or "") and not has_actionable_job_data(job):
        return "portal homepage only — no notification"
    if is_homepage_scrape_content(job.full_content) and not has_actionable_job_data(job):
        return "homepage scrape — no real notification content"
    if not has_actionable_job_data(job):
        return "missing vacancies, last date, PDF or eligibility"
    return None


def reactivation_reason(job: Job) -> Optional[str]:
    """Why an inactive job should become active again."""
    from app.services.application_dates import is_job_listable

    if job.category in NON_JOB_CATEGORIES:
        return None
    if not job_meets_quality(job):
        return None
    if not is_job_listable(job.last_date):
        return None
    return "meets quality and listable"
