from __future__ import annotations

"""LLM-powered job enrichment for date parsing and summarization."""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.services.date_extractor import extract_dates, extract_vacancies

logger = logging.getLogger(__name__)

ENRICHMENT_PROMPT = """You are an expert at parsing Indian government job notifications.
Extract structured data from this recruitment notification text.

Return ONLY valid JSON with these fields:
{
  "last_date": "YYYY-MM-DD or null",
  "exam_date": "YYYY-MM-DD or null",
  "published_date": "YYYY-MM-DD or null",
  "vacancies": number or null,
  "qualification": "string or null (e.g. Graduate, 12th Pass, ITI)",
  "summary": "2-3 sentence plain English summary of the notification",
  "organization": "recruiting body abbreviation",
  "state": "Indian state name or null for central jobs",
  "category": "one of: notification, admit_card, result, answer_key, syllabus, education"
}

Notification title: {title}
Additional text: {description}
"""


@dataclass
class EnrichedJobData:
    last_date: Optional[datetime]
    exam_date: Optional[datetime]
    published_date: Optional[datetime]
    vacancies: Optional[int]
    qualification: Optional[str]
    summary: Optional[str]
    organization: Optional[str]
    state: Optional[str]
    category: Optional[str]
    is_verified: bool
    enriched_by: str  # "llm" | "regex"


def _parse_date_str(s: Optional[str]) -> Optional[datetime]:
    if not s or s == "null":
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return None


async def enrich_with_llm(title: str, description: str = "") -> EnrichedJobData:
    """Use LLM API for rich parsing. Falls back to regex if unavailable."""
    regex_dates = extract_dates(f"{title} {description}")
    regex_vacancies = extract_vacancies(title) or extract_vacancies(description)

    if not settings.llm_enabled or not settings.openai_api_key:
        return EnrichedJobData(
            last_date=regex_dates.last_date,
            exam_date=regex_dates.exam_date,
            published_date=regex_dates.published_date,
            vacancies=regex_vacancies,
            qualification=None,
            summary=description[:300] if description else None,
            organization=None,
            state=None,
            category=None,
            is_verified=regex_dates.is_verified,
            enriched_by="regex",
        )

    try:
        prompt = ENRICHMENT_PROMPT.format(
            title=title,
            description=description or "No additional description",
        )
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "Return only valid JSON, no markdown."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)

            last_date = _parse_date_str(data.get("last_date")) or regex_dates.last_date
            exam_date = _parse_date_str(data.get("exam_date")) or regex_dates.exam_date
            published = _parse_date_str(data.get("published_date")) or regex_dates.published_date

            return EnrichedJobData(
                last_date=last_date,
                exam_date=exam_date,
                published_date=published,
                vacancies=data.get("vacancies") or regex_vacancies,
                qualification=data.get("qualification"),
                summary=data.get("summary"),
                organization=data.get("organization"),
                state=data.get("state"),
                category=data.get("category"),
                is_verified=bool(last_date or exam_date),
                enriched_by="llm",
            )
    except Exception as e:
        logger.warning("LLM enrichment failed, using regex fallback: %s", e)
        return EnrichedJobData(
            last_date=regex_dates.last_date,
            exam_date=regex_dates.exam_date,
            published_date=regex_dates.published_date,
            vacancies=regex_vacancies,
            qualification=None,
            summary=description[:300] if description else None,
            organization=None,
            state=None,
            category=None,
            is_verified=regex_dates.is_verified,
            enriched_by="regex",
        )
