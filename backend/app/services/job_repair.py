from __future__ import annotations

"""Repair jobs that still reference aggregator sites."""

import hashlib
import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.advertisement_enricher import enrich_job_advertisement
from app.services.date_parse import parse_flexible_date
from app.services.detail_fetcher import enrich_job_details, is_pdf_url
from app.services.official_urls import is_aggregator_url, resolve_apply_url, resolve_official_url
from app.services.org_resolver import normalize_organization
from app.services.recruitment_content import sections_from_json, sections_to_json
from app.services.official_title import choose_best_title
from app.services.content_quality import (
    filter_eligibility_rows,
    is_generic_title,
    sections_have_garbled_content,
    title_from_pdf_filename,
)

logger = logging.getLogger(__name__)

PORTAL_JUNK_MARKERS = (
    "skip to main content",
    "select your language",
    "javascript is disabled",
)


def _needs_repair(job: Job) -> bool:
    if is_aggregator_url(job.source_url or ""):
        return True
    if is_aggregator_url(job.apply_url or ""):
        return True
    if is_aggregator_url(job.notification_url or ""):
        return True
    if job.organization.upper() in {"CG", "CG."} and "vyapam" in job.title.lower():
        return True
    if "vyapam" in job.title.lower() and "vyapam" not in job.organization.lower():
        return True
    if "vyapam" in job.title.lower() and (not job.full_content or "Pay Matrix" not in (job.full_content or "")):
        return True
    if not job.last_date and job.full_content and "31.07.2025" in job.full_content:
        return True
    if not job.age_limit and job.full_content and "Age Limit" in job.full_content:
        return True
    if "vyapam" in job.title.lower() and not job.sections_json:
        return True
    if job.full_content and "%PDF-" in job.full_content:
        return True
    if is_pdf_url(job.notification_url) and not job.sections_json:
        return True
    if job.sections_json and is_pdf_url(job.notification_url):
        from app.services.recruitment_content import sections_from_json
        parsed = sections_from_json(job.sections_json)
        if parsed and not parsed.get("vacancy_rows") and not parsed.get("dates"):
            return True
    if not job.sections_json and job.source_url and not job.source_url.startswith("official://"):
        notif = (job.notification_url or "").lower()
        if not notif.endswith(".pdf"):
            return True
    if job.full_content and any(marker in job.full_content.lower() for marker in PORTAL_JUNK_MARKERS):
        return True
    if not job.last_date and job.full_content and re.search(
        r"closing date[^\n]{0,50}\d{1,2}/\d{1,2}/\d{4}", job.full_content, re.I
    ):
        return True
    if not job.sections_json:
        return True
    return False


def sections_are_usable(job: Job) -> bool:
    """True when cached sections_json is enough to render the detail page quickly."""
    if not job.sections_json:
        return False
    parsed = sections_from_json(job.sections_json)
    if not parsed:
        return False

    if sections_have_garbled_content(parsed):
        return False

    dates = parsed.get("dates") or []
    has_last = any("last" in d.get("label", "").lower() for d in dates)
    vac_rows = parsed.get("vacancy_rows") or []
    has_real_vacancy = parsed.get("total_vacancies") or any(r.get("vacancies", 0) > 0 for r in vac_rows)
    has_qual = bool(parsed.get("qualification") or filter_eligibility_rows(parsed.get("eligibility_rows")))
    has_fee = bool(parsed.get("application_fee_rows"))

    score = sum([has_last, has_real_vacancy, has_qual, has_fee, len(vac_rows) > 1])
    if score >= 3:
        return True
    if parsed.get("overview") or parsed.get("documents"):
        return score >= 2
    return False


def needs_deep_enrich(job: Job) -> bool:
    """True when a background PDF/portal fetch would materially improve the page."""
    has_pdf = is_pdf_url(job.notification_url or "") or is_pdf_url(job.source_url or "")
    has_page = any(
        u and u.startswith("http") and not u.startswith("official://") and not is_pdf_url(u)
        for u in (job.notification_url, job.source_url, job.apply_url)
    )
    if not has_pdf and not has_page:
        return False
    if not job.sections_json:
        return True
    if not sections_are_usable(job):
        return True
    parsed = sections_from_json(job.sections_json)
    if parsed and sections_have_garbled_content(parsed):
        return True
    if not parsed:
        return True
    dates = parsed.get("dates") or []
    has_last = any("last" in d.get("label", "").lower() for d in dates)
    if has_pdf and not has_last:
        return True
    rows = parsed.get("vacancy_rows") or []
    if len(rows) <= 1 and has_pdf:
        qual = str(rows[0].get("qualification", "")) if rows else ""
        pay = str(rows[0].get("pay_scale", "")) if rows else ""
        if (not qual or "see official" in qual.lower()) and "see official" in pay.lower():
            return True
    return False


def ensure_job_sections(job: Job, *, deep: bool = False) -> None:
    """Persist structured sections so every job has a detail page."""
    sections = enrich_job_advertisement(job, deep=deep)
    job.sections_json = sections_to_json(sections)

    if sections.get("title"):
        pdf_url = job.notification_url or job.apply_url or ""
        official = choose_best_title(
            sections["title"],
            title_from_pdf_filename(pdf_url),
            listing_title=job.title,
            pdf_url=pdf_url,
        )
        if official and not is_generic_title(official) and official != job.title:
            job.title = official[:350]

    for d in sections.get("dates") or []:
        if "last" in d.get("label", "").lower():
            parsed = parse_flexible_date(d.get("date", ""))
            if parsed:
                job.last_date = parsed
                break

    if not job.exam_date:
        for d in sections.get("dates") or []:
            label = d.get("label", "").lower()
            if "exam" in label and "admit" not in label:
                parsed = parse_flexible_date(d.get("date", ""))
                if parsed:
                    job.exam_date = parsed
                    break

    if sections.get("age_limit"):
        job.age_limit = sections["age_limit"]
    if sections.get("qualification") or sections.get("eligibility_rows"):
        first = (sections.get("eligibility_rows") or [{}])[0]
        qual = sections.get("qualification") or first.get("education")
        if qual:
            job.qualification = str(qual)[:500]
    if sections.get("total_vacancies"):
        job.vacancies = sections["total_vacancies"]
    if sections.get("application_fee"):
        job.application_fee = sections["application_fee"]

    job.updated_at = datetime.utcnow()


def deep_enrich_all_jobs(
    db: Session,
    *,
    limit: int | None = None,
    force: bool = False,
    commit_every: int = 20,
) -> dict[str, int]:
    """Deep-parse PDFs/portals and rebuild sections for all active jobs."""
    query = db.query(Job).filter(Job.is_active == True).order_by(Job.id)  # noqa: E712
    if limit:
        query = query.limit(limit)
    jobs = query.all()

    enriched = 0
    skipped = 0
    errors = 0

    for idx, job in enumerate(jobs, start=1):
        try:
            if not force and sections_are_usable(job) and not needs_deep_enrich(job):
                skipped += 1
                continue
            ensure_job_sections(job, deep=True)
            enriched += 1
            if enriched % commit_every == 0:
                db.commit()
                logger.info("Deep enriched %d / %d jobs", enriched, len(jobs))
        except Exception as exc:
            errors += 1
            logger.warning("Deep enrich failed for job %s: %s", job.id, exc)
            db.rollback()

    db.commit()
    logger.info(
        "Deep enrich complete: %d enriched, %d skipped, %d errors / %d total",
        enriched,
        skipped,
        errors,
        len(jobs),
    )
    return {
        "total": len(jobs),
        "enriched": enriched,
        "skipped": skipped,
        "errors": errors,
    }


async def repair_job(db: Session, job: Job) -> bool:
    """Re-enrich a single job from official sources. Returns True if updated."""
    if not _needs_repair(job):
        return False

    org = normalize_organization(job.title, job.organization)
    last_fmt = job.last_date.strftime("%d %b %Y") if job.last_date else None
    exam_fmt = job.exam_date.strftime("%d %b %Y") if job.exam_date else None

    details = await enrich_job_details(
        title=job.title,
        organization=org,
        state=job.state,
        category=job.category.value,
        vacancies=job.vacancies,
        qualification=job.qualification,
        last_date=last_fmt,
        exam_date=exam_fmt,
        description=job.description,
        source_url=job.source_url if not (job.source_url or "").startswith("official://") else resolve_official_url(org, job.title),
    )

    job.organization = details.get("organization") or org
    job.apply_url = details["apply_url"]
    if is_pdf_url(job.apply_url):
        job.apply_url = resolve_apply_url(job.organization, job.title) or resolve_official_url(
            job.organization, job.title
        )
    job.notification_url = details["notification_url"]
    job.full_content = details["full_content"]
    if details.get("sections_json"):
        job.sections_json = details["sections_json"]
    job.age_limit = details.get("age_limit")
    job.application_fee = details.get("application_fee")
    if details.get("qualification"):
        job.qualification = details["qualification"]
    if details.get("official_title"):
        job.title = details["official_title"][:350]
    if details.get("vacancies"):
        job.vacancies = details["vacancies"]
    if details.get("last_date"):
        parsed = parse_flexible_date(details["last_date"])
        if parsed:
            job.last_date = parsed
    ensure_job_sections(job, deep=True)
    job.source_name = job.organization

    if is_aggregator_url(job.source_url):
        job.source_url = (
            f"official://{job.organization}/"
            f"{hashlib.md5(job.title.encode()).hexdigest()[:12]}"
        )

    job.updated_at = datetime.utcnow()
    return True


async def repair_all_jobs(db: Session, limit: int | None = None) -> dict:
    """Repair all active jobs with aggregator URLs or missing content."""
    jobs = db.query(Job).filter(Job.is_active == True).all()  # noqa: E712
    if limit:
        jobs = jobs[:limit]
    updated = 0
    for job in jobs:
        if await repair_job(db, job):
            updated += 1
    db.commit()
    logger.info("Repaired %d / %d jobs", updated, len(jobs))
    return {"total": len(jobs), "updated": updated}
