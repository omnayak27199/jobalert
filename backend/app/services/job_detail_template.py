from __future__ import annotations

"""Canonical job detail template — every job uses the same section structure."""

import re
from typing import Any, Optional

from app.models.job import Job
from app.services.recruitment_content import build_advertisement_sections
from app.services.content_quality import is_plausible_qualification

OPENING_LABEL = "Application Start"
LAST_DATE_LABEL = "Last Date to Apply"


def extract_advertisement_no(title: str) -> str | None:
    match = re.search(
        r"(?i)(?:advt\.?\s*no\.?\s*-?\s*\d+/\d{4}|advertisement\s*no\.?\s*\d+\s*of\s*\d{4}|advertisement\s*no\.?\s*\d+/\d{4})",
        title,
    )
    return match.group(0).strip() if match else None


def normalize_dates(
    dates: Optional[list[dict[str, str]]],
    opening: Optional[str] = None,
    closing: Optional[str] = None,
) -> list[dict[str, str]]:
    """Ensure opening + last date slots exist in the dates list."""
    rows = list(dates or [])
    has_open = any("start" in d.get("label", "").lower() or "opening" in d.get("label", "").lower() for d in rows)
    has_last = any("last" in d.get("label", "").lower() for d in rows)

    if opening and not has_open:
        rows.insert(0, {"label": OPENING_LABEL, "label_hi": "आवेदन प्रारंभ", "date": opening})
    if closing and not has_last:
        rows.append({"label": LAST_DATE_LABEL, "label_hi": "अंतिम तिथि", "date": closing})

    return rows


def normalize_vacancy_rows(
    rows: Optional[list[dict[str, Any]]],
    fallback_post: str,
    fallback_vacancies: Optional[int] = None,
) -> list[dict[str, Any]]:
    if rows:
        return rows
    if fallback_vacancies and fallback_vacancies > 0 and fallback_post:
        return [
            {
                "sr": "01",
                "post": fallback_post,
                "vacancies": fallback_vacancies,
                "pay_level": "",
                "pay_scale": "",
                "qualification": "",
            }
        ]
    return []


def build_job_detail_template(
    *,
    title: str,
    organization: str,
    state: Optional[str] = None,
    overview: Optional[str] = None,
    advertisement_no: Optional[str] = None,
    opening_date: Optional[str] = None,
    last_date: Optional[str] = None,
    dates: Optional[list[dict[str, str]]] = None,
    vacancy_rows: Optional[list[dict[str, Any]]] = None,
    eligibility_rows: Optional[list[dict[str, Any]]] = None,
    qualification: Optional[str] = None,
    age_limit: Optional[str] = None,
    age_relaxation: Optional[str] = None,
    application_fee: Optional[str] = None,
    application_fee_rows: Optional[list[tuple[str, str]]] = None,
    total_vacancies: Optional[int] = None,
    pdf_url: Optional[str] = None,
    apply_url: Optional[str] = None,
    selection_steps: Optional[list[str]] = None,
    reservation: Optional[list[str]] = None,
    special_notes: Optional[list[str]] = None,
    syllabus_url: Optional[str] = None,
    syllabus_note: Optional[str] = None,
) -> dict[str, Any]:
    """Build the standard job advertisement JSON used by the frontend template."""
    pdf_links: list[tuple[str, str]] = []
    if pdf_url:
        pdf_links.append(("Official Notification PDF", pdf_url))
    if apply_url and apply_url != pdf_url:
        pdf_links.append(("Apply Online", apply_url))
    if syllabus_url:
        pdf_links.append(("Syllabus / Exam Pattern", syllabus_url))

    date_rows = normalize_dates(dates, opening=opening_date, closing=last_date)

    fee_rows = list(application_fee_rows or [])
    if not fee_rows and application_fee:
        fee_rows = [("General / UR", application_fee)]

    rows = normalize_vacancy_rows(vacancy_rows, title[:120], total_vacancies)
    if not total_vacancies:
        total_vacancies = sum(int(r.get("vacancies") or 0) for r in rows) or None

    # Mirror qualification into eligibility table when rows missing
    elig = list(eligibility_rows or [])
    if not elig and qualification and is_plausible_qualification(qualification):
        elig = [
            {
                "post": rows[0]["post"] if rows else title[:80],
                "education": qualification,
                "experience": "As per notification",
                "other": state or "",
            }
        ]

    data: dict[str, Any] = {
        "title": title,
        "organization": organization,
        "advertisement_no": advertisement_no,
        "vacancies": total_vacancies,
        "overview": overview
        or f"{organization} recruitment notification. See post table, pay scale, dates and official PDF below.",
        "qualification_summary": qualification,
        "age_limit": age_limit,
        "age_relaxation": age_relaxation,
        "application_fee_rows": fee_rows,
        "dates": date_rows,
        "vacancy_rows": rows,
        "eligibility_rows": elig,
        "selection_steps": selection_steps or [],
        "reservation": reservation or [],
        "special_notes": special_notes or [],
        "syllabus_url": syllabus_url,
        "syllabus_note": syllabus_note,
    }
    return build_advertisement_sections(data, pdf_links)


def template_from_job(job: Job, enriched: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Merge Job model + enrichment dict into the canonical template."""
    enriched = enriched or {}
    opening = enriched.get("opening_date")
    closing = enriched.get("last_date")
    if job.last_date and not closing:
        closing = job.last_date.strftime("%d/%m/%Y")

    for d in enriched.get("dates") or []:
        label = d.get("label", "").lower()
        if "start" in label or "opening" in label:
            opening = opening or d.get("date")
        if "last" in label:
            closing = closing or d.get("date")

    pdf_url = enriched.get("pdf_url")
    if not pdf_url:
        for field in (job.notification_url, job.apply_url):
            if field and str(field).lower().split("?")[0].endswith(".pdf"):
                pdf_url = field
                break

    apply_url = job.apply_url if job.apply_url != pdf_url else enriched.get("apply_url")

    return build_job_detail_template(
        title=enriched.get("official_title") or job.title,
        organization=job.organization,
        state=job.state,
        overview=job.description or enriched.get("overview"),
        advertisement_no=enriched.get("advertisement_no"),
        opening_date=opening,
        last_date=closing,
        dates=enriched.get("dates"),
        vacancy_rows=enriched.get("vacancy_rows"),
        eligibility_rows=enriched.get("eligibility_rows"),
        qualification=enriched.get("qualification") or job.qualification,
        age_limit=enriched.get("age_limit") or job.age_limit,
        age_relaxation=enriched.get("age_relaxation"),
        application_fee=enriched.get("application_fee") or job.application_fee,
        application_fee_rows=enriched.get("application_fee_rows"),
        total_vacancies=job.vacancies or enriched.get("total_vacancies"),
        pdf_url=pdf_url,
        apply_url=apply_url,
        selection_steps=enriched.get("selection_steps"),
        reservation=enriched.get("reservation"),
        special_notes=enriched.get("special_notes"),
        syllabus_url=enriched.get("syllabus_url"),
        syllabus_note=enriched.get("syllabus_note"),
    )
