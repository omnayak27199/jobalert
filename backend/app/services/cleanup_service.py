from __future__ import annotations

"""Post-fetch cleanup — deactivate junk/expired jobs and rebuild sections."""

import logging

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.application_dates import closed_visibility_cutoff
from app.services.job_quality import cleanup_reason, reactivation_reason
from app.services.job_repair import ensure_job_sections, needs_deep_enrich
from app.services.post_expansion import expand_all_multi_post_jobs

logger = logging.getLogger(__name__)


def run_cleanup(db: Session) -> dict:
    """Deactivate junk/expired jobs, expand multi-post listings, rebuild sections."""
    reactivated = 0
    for job in db.query(Job).filter(Job.is_active == False).all():  # noqa: E712
        if reactivation_reason(job):
            job.is_active = True
            reactivated += 1
            logger.info("Reactivated job %s: %s", job.id, job.title[:60])

    deactivated = 0
    for job in db.query(Job).filter(Job.is_active == True).all():  # noqa: E712
        reason = cleanup_reason(job)
        if reason:
            job.is_active = False
            deactivated += 1
            logger.info("Deactivated job %s: %s", job.id, reason)

    expired = 0
    cutoff = closed_visibility_cutoff()
    for job in db.query(Job).filter(Job.is_active == True).all():  # noqa: E712
        if job.last_date and job.last_date < cutoff:
            job.is_active = False
            expired += 1

    expand_result = expand_all_multi_post_jobs(db)

    sections_built = 0
    deep_built = 0
    for job in db.query(Job).filter(Job.is_active == True).all():  # noqa: E712
        use_deep = needs_deep_enrich(job)
        ensure_job_sections(job, deep=use_deep)
        sections_built += 1
        if use_deep:
            deep_built += 1

    db.commit()
    return {
        "reactivated": reactivated,
        "deactivated": deactivated,
        "expired": expired,
        "expand": expand_result,
        "sections_built": sections_built,
        "deep_built": deep_built,
    }
