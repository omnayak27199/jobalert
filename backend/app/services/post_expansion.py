from __future__ import annotations

"""Split multi-post recruitments into separate job alert listings."""

import re
from datetime import datetime

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models.job import Job, JobCategory, JobScope
from app.services.application_dates import is_job_listable
from app.services.recruitment_content import (
    build_advertisement_sections,
    get_post_structured_content,
    sections_from_json,
    sections_to_json,
    structured_job_fields,
)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48] or "post"


def _parse_last_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = date_parser.parse(raw, dayfirst=True, fuzzy=True)
        if parsed.year < 2020 or parsed.year > 2035:
            return None
        return parsed
    except (ValueError, OverflowError):
        return None


def _find_vyapam_parent(db: Session) -> Job | None:
    """Prefer a parent with structured sections over a bare portal scrape."""
    with_sections = (
        db.query(Job)
        .filter(Job.title.ilike("%vyapam%"))
        .filter(Job.sections_json.isnot(None))
        .order_by(Job.id.desc())
        .first()
    )
    if with_sections:
        return with_sections

    return (
        db.query(Job)
        .filter(Job.title.ilike("%vyapam%"))
        .filter(Job.title.ilike("%nssk%") | Job.title.ilike("%various%"))
        .order_by(Job.id.desc())
        .first()
    )


def _single_post_sections(base: dict, row: dict, pdf_links: list[tuple[str, str]]) -> dict:
    post = row["post"]
    elig = [
        e for e in base.get("eligibility_rows", [])
        if post.split()[0].lower() in e.get("post", "").lower()
        or e.get("post", "").lower() in post.lower()
    ]
    if not elig:
        elig = [
            e for e in base.get("eligibility_rows", [])
            if row["post"].split("(")[0].strip().lower() in e.get("post", "").lower()
        ]

    single_data = {
        **base,
        "title": f"{post} Recruitment",
        "title_hi": f"{row.get('post_hi', post)} — CG Vyapam भर्ती",
        "vacancies": row["vacancies"],
        "qualification_summary": row.get("qualification"),
        "overview": (
            f"CG Vyapam invites online applications for {post} — "
            f"{row['vacancies']} vacancies. Pay Level {row.get('pay_level', '')}, "
            f"scale {row.get('pay_scale', '')}. Apply on official CG Vyapam portal."
        ),
        "overview_hi": (
            f"छत्तीसगढ़ व्यापम — {row.get('post_hi', post)} पद हेतु "
            f"{row['vacancies']} रिक्तियाँ। ऑनलाइन आवेदन करें।"
        ),
        "vacancy_rows": [row],
        "eligibility_rows": elig[:1] if elig else [],
        "reservation": [],
        "special_notes": [
            n for n in base.get("special_notes", [])
            if post.split()[0].lower() in n.lower() or "one post" in n.lower()
        ] or base.get("special_notes", [])[:1],
    }
    return build_advertisement_sections(single_data, pdf_links)


def expand_vyapam_nssk26(db: Session, post_id: str = "NSSK26ONLINE") -> dict:
    """Create one job alert per post under NSSK26 instead of one combined listing."""
    data = get_post_structured_content(post_id)
    if not data:
        return {"created": 0, "updated": 0, "deactivated": 0}

    pdf_links: list[tuple[str, str]] = []
    parent = _find_vyapam_parent(db)
    if parent:
        sections = sections_from_json(parent.sections_json) if parent.sections_json else None
        if sections and sections.get("documents"):
            pdf_links = [(d["label"], d["url"]) for d in sections["documents"]]
        if parent.notification_url:
            pdf_links.insert(0, ("Official Notification PDF", parent.notification_url))
        if parent.apply_url:
            pdf_links.append(("Apply Online", parent.apply_url))

    fields = structured_job_fields(data)
    structured_last_date = _parse_last_date(data.get("last_date"))
    created = updated = 0

    for row in data.get("vacancy_rows", []):
        post = row["post"]
        slug = _slug(post)
        source_url = f"official://CG Vyapam/{post_id}-{slug}"
        title = f"CG Vyapam {post} Recruitment 2026 — {row['vacancies']} Posts"

        sections = _single_post_sections(data, row, pdf_links)
        existing = db.query(Job).filter(Job.source_url == source_url).first()
        last_date = structured_last_date or (parent.last_date if parent else None)
        listable = is_job_listable(last_date)

        if existing:
            existing.title = title
            existing.vacancies = row["vacancies"]
            existing.qualification = row.get("qualification")
            existing.sections_json = sections_to_json(sections)
            existing.full_content = f"{title}. Apply on official CG Vyapam portal."
            existing.organization = fields.get("organization") or existing.organization
            existing.age_limit = fields.get("age_limit")
            existing.application_fee = fields.get("application_fee")
            existing.last_date = last_date
            existing.is_active = listable
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            job = Job(
                title=title,
                organization=fields.get("organization") or "CG Vyapam (CGSSB)",
                category=JobCategory.NOTIFICATION,
                scope=parent.scope if parent else JobScope.STATE,
                state=parent.state if parent else "Chhattisgarh",
                vacancies=row["vacancies"],
                apply_url=parent.apply_url if parent else "https://vyapamprofile.cgstate.gov.in/online/",
                source_url=source_url,
                source_name="CG Vyapam (CGSSB)",
                published_date=parent.published_date if parent else datetime.utcnow(),
                last_date=last_date,
                qualification=row.get("qualification"),
                description=f"CG Vyapam recruitment for {post} — {row['vacancies']} vacancies.",
                full_content=f"{title}. See eligibility, pay level and apply link.",
                notification_url=parent.notification_url if parent else None,
                age_limit=fields.get("age_limit"),
                application_fee=fields.get("application_fee"),
                sections_json=sections_to_json(sections),
                is_verified=bool(last_date),
                is_active=listable,
            )
            db.add(job)
            created += 1

    deactivated = 0
    if parent:
        parent.is_active = False
        parent.updated_at = datetime.utcnow()
        deactivated = 1

    # Deactivate other junk vyapam portal menu items
    junk = (
        db.query(Job)
        .filter(Job.is_active == True)  # noqa: E712
        .filter(Job.organization.ilike("%vyapam%"))
        .filter(
            Job.title.in_([
                "RECRUITMENT", "Recruitment", "EXAMINATION", "ADMIT CARD",
                "ONLINE APPLICATION", "RESULT", "FORMS & FORMAT", "FORMS AND FORMAT",
            ])
        )
        .all()
    )
    for j in junk:
        j.is_active = False
        deactivated += 1

    exam_noise = (
        db.query(Job)
        .filter(Job.is_active == True)  # noqa: E712
        .filter(Job.organization.ilike("%vyapam%"))
        .filter(
            Job.title.ilike("%online application%")
            | Job.title.ilike("%admit card%")
            | Job.title.ilike("%pat-%")
            | Job.title.ilike("%result%")
            | Job.title.ilike("%lsat%")
            | Job.title.ilike("%cg-set%")
        )
        .all()
    )
    for j in exam_noise:
        j.is_active = False
        deactivated += 1

    db.commit()
    return {"created": created, "updated": updated, "deactivated": deactivated}


def expand_all_multi_post_jobs(db: Session) -> dict:
    return expand_vyapam_nssk26(db)
