from __future__ import annotations

"""Parse government recruitment PDFs and extract structured job data."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import Optional

import httpx
import pdfplumber

from app.config import settings
from app.services.date_extractor import (
    classify_category,
    detect_state,
    extract_dates,
    extract_organization,
    extract_vacancies,
)
from app.services.official_title import extract_official_title_from_text
from app.services.pdf_text_extractor import extract_pdf_text

logger = logging.getLogger(__name__)

PDF_PARSE_PROMPT = """Extract recruitment notification details from this government job PDF text.
Return ONLY valid JSON:
{
  "title": "full notification title",
  "organization": "department/organization name",
  "state": "Indian state or null for central",
  "category": "notification|admit_card|result|answer_key|syllabus|education",
  "vacancies": number or null,
  "last_date": "YYYY-MM-DD or null",
  "exam_date": "YYYY-MM-DD or null",
  "qualification": "required qualification or null",
  "apply_url": "url if mentioned or null",
  "summary": "3-4 sentence summary of the notification"
}

PDF text:
{text}
"""


@dataclass
class ParsedPDF:
    title: str
    organization: str
    state: Optional[str]
    category: str
    vacancies: Optional[int]
    last_date: Optional[datetime]
    exam_date: Optional[datetime]
    qualification: Optional[str]
    apply_url: Optional[str]
    summary: Optional[str]
    raw_text: str
    is_verified: bool


def extract_text_from_pdf(file_bytes: bytes) -> str:
    return extract_pdf_text(file_bytes, max_pages=20)


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s or s == "null":
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _regex_parse(text: str, filename: str = "") -> ParsedPDF:
    """Fallback parsing without LLM."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    title = extract_official_title_from_text(text, filename.replace(".pdf", "").replace("_", " "))
    if not title:
        title = filename.replace(".pdf", "").replace("_", " ")

    dates = extract_dates(text)
    org = extract_organization(title) or extract_organization(text[:500])
    state = detect_state(text, org)
    category = classify_category(title, text[:1000])
    vacancies = extract_vacancies(text)

    return ParsedPDF(
        title=title,
        organization=org,
        state=state,
        category=category,
        vacancies=vacancies,
        last_date=dates.last_date,
        exam_date=dates.exam_date,
        qualification=None,
        apply_url=None,
        summary=text[:500] if text else None,
        raw_text=text[:2000],
        is_verified=dates.is_verified,
    )


async def _llm_parse(text: str, filename: str) -> ParsedPDF:
    if not settings.openai_api_key or not settings.llm_enabled:
        return _regex_parse(text, filename)

    try:
        truncated = text[:8000]
        prompt = PDF_PARSE_PROMPT.format(text=truncated)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "Return only valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 800,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?|```$", "", content.strip()).strip()
            data = json.loads(content)

            last_date = _parse_date(data.get("last_date"))
            exam_date = _parse_date(data.get("exam_date"))
            regex_fallback = _regex_parse(text, filename)

            return ParsedPDF(
                title=data.get("title") or regex_fallback.title,
                organization=data.get("organization") or regex_fallback.organization,
                state=data.get("state") or regex_fallback.state,
                category=data.get("category") or regex_fallback.category,
                vacancies=data.get("vacancies") or regex_fallback.vacancies,
                last_date=last_date or regex_fallback.last_date,
                exam_date=exam_date or regex_fallback.exam_date,
                qualification=data.get("qualification"),
                apply_url=data.get("apply_url"),
                summary=data.get("summary") or regex_fallback.summary,
                raw_text=text[:2000],
                is_verified=bool(last_date or exam_date),
            )
    except Exception as e:
        logger.warning("LLM PDF parse failed: %s", e)
        return _regex_parse(text, filename)


async def parse_pdf(file_bytes: bytes, filename: str = "notification.pdf") -> ParsedPDF:
    text = extract_text_from_pdf(file_bytes)
    if not text or len(text) < 30:
        raise ValueError("Could not extract text from PDF. It may be scanned/image-only.")
    return await _llm_parse(text, filename)
