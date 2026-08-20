from __future__ import annotations

"""Save parsed PDF notifications to the database."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.detail_fetcher import build_full_content
from app.services.ingestion import _to_enum_category, _to_enum_scope
from app.services.pdf_parser import ParsedPDF


def save_parsed_pdf(
    db: Session,
    parsed: ParsedPDF,
    source_filename: str,
    apply_url: Optional[str] = None,
) -> Job:
    source_url = f"pdf://{source_filename}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    scope = "state" if parsed.state else "central"
    job = Job(
        title=parsed.title,
        organization=parsed.organization,
        category=_to_enum_category(parsed.category),
        scope=_to_enum_scope(scope),
        state=parsed.state,
        vacancies=parsed.vacancies,
        apply_url=apply_url or parsed.apply_url,
        source_url=source_url,
        source_name=f"PDF Upload: {source_filename}",
        published_date=datetime.utcnow(),
        last_date=parsed.last_date,
        exam_date=parsed.exam_date,
        qualification=parsed.qualification,
        description=parsed.summary,
        is_verified=parsed.is_verified,
    )
    job.full_content = build_full_content(
        title=parsed.title,
        organization=job.organization,
        state=job.state,
        category=job.category.value,
        vacancies=job.vacancies,
        qualification=job.qualification,
        last_date=job.last_date.strftime("%d %b %Y") if job.last_date else None,
        exam_date=job.exam_date.strftime("%d %b %Y") if job.exam_date else None,
        description=parsed.summary,
        fetched_text=parsed.raw_text,
    )
    job.notification_url = apply_url or parsed.apply_url or source_url
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
