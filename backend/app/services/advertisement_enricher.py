from __future__ import annotations

"""Fill the job detail template from PDF parser + portal page viewer."""

from typing import Any

from app.models.job import Job
from app.services.detail_fetcher import is_pdf_url
from app.services.job_detail_template import extract_advertisement_no, template_from_job
from app.services.notification_pdf_parser import enrich_from_notification_pdf_sync
from app.services.official_portals import resolve_vyapam_post_url
from app.services.portal_page_parser import merge_enrichment, parse_portal_advertisement_page
from app.services.recruitment_content import (
    build_advertisement_sections,
    get_post_structured_content,
    sections_from_json,
)


def _resolve_pdf_url(job: Job, portal_data: dict[str, Any]) -> str | None:
    for candidate in (portal_data.get("pdf_url"), job.notification_url, job.apply_url, job.source_url):
        if is_pdf_url(candidate):
            return candidate
    return None


def _resolve_page_url(job: Job) -> str | None:
    for candidate in (job.source_url, job.notification_url, job.apply_url):
        if not candidate or candidate.startswith("official://") or is_pdf_url(candidate):
            continue
        if candidate.count("/") <= 3:
            continue
        return candidate
    return None


def _deep_enrich(job: Job) -> dict[str, Any]:
    page_url = _resolve_page_url(job)
    portal_data = parse_portal_advertisement_page(page_url, job.title, job.organization) if page_url else {}

    pdf_url = _resolve_pdf_url(job, portal_data)
    pdf_data = enrich_from_notification_pdf_sync(pdf_url, job.title) if pdf_url else {}

    if not pdf_data and portal_data.get("pdf_url"):
        pdf_data = enrich_from_notification_pdf_sync(portal_data["pdf_url"], job.title)

    enriched = merge_enrichment(portal_data, pdf_data)
    if pdf_url and not enriched.get("pdf_url"):
        enriched["pdf_url"] = pdf_url
    if enriched.get("official_title"):
        enriched["advertisement_no"] = enriched.get("advertisement_no") or extract_advertisement_no(
            enriched["official_title"]
        )
    return enriched


def enrich_job_advertisement(job: Job, *, deep: bool = False) -> dict[str, Any]:
    """
    Step 1: Canonical template skeleton for every job.
    Step 2: When deep=True, parse official PDF + HTML page and fill the template.
    """
    if not deep:
        stored = sections_from_json(job.sections_json) if job.sections_json else None
        if stored:
            return stored
        return template_from_job(job, {"advertisement_no": extract_advertisement_no(job.title)})

    if "vyapam" in f"{job.organization} {job.title}".lower():
        post_url = resolve_vyapam_post_url(job.title)
        if post_url and "PostID=" in post_url:
            post_id = post_url.split("PostID=")[-1].split("&")[0]
            data = get_post_structured_content(post_id)
            if data:
                pdf_links: list[tuple[str, str]] = []
                if job.notification_url:
                    pdf_links.append(("Official Notification PDF", job.notification_url))
                if job.apply_url and job.apply_url != job.notification_url:
                    pdf_links.append(("Apply Online", job.apply_url))
                return build_advertisement_sections(data, pdf_links)

    enriched = _deep_enrich(job)
    enriched["advertisement_no"] = enriched.get("advertisement_no") or extract_advertisement_no(
        enriched.get("official_title") or job.title
    )
    return template_from_job(job, enriched)
