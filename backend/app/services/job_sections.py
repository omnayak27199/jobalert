from __future__ import annotations

"""Build structured job detail sections using the generic template + enricher."""

from app.models.job import Job
from app.services.advertisement_enricher import enrich_job_advertisement
from app.services.detail_fetcher import is_pdf_url
from app.services.job_detail_template import extract_advertisement_no


def resolve_job_sections(job: Job, *, deep: bool = False) -> dict:
    """Return the generic job detail template, filled from PDF/portal when deep=True."""
    return enrich_job_advertisement(job, deep=deep)
