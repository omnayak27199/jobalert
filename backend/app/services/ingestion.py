from __future__ import annotations

"""Job ingestion service - saves scraped jobs to database."""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.job import Job, JobCategory, JobScope, NewsItem
from app.scrapers.gov_scrapers import ScrapedJob
from app.scrapers.news_fetcher import ScrapedNews, fetch_news
from app.services.alerts import dispatch_alerts_for_new_jobs
from app.services.date_extractor import classify_category, detect_state
from app.services.detail_fetcher import enrich_job_details
from app.services.llm_enricher import enrich_with_llm
from app.services.official_urls import is_aggregator_url, resolve_official_url
from app.services.job_quality import is_valid_scraped_job
from app.services.official_title import normalize_listing_title
from app.services.org_resolver import normalize_organization

logger = logging.getLogger(__name__)


def _to_enum_category(category: str) -> JobCategory:
    mapping = {
        "notification": JobCategory.NOTIFICATION,
        "admit_card": JobCategory.ADMIT_CARD,
        "result": JobCategory.RESULT,
        "answer_key": JobCategory.ANSWER_KEY,
        "syllabus": JobCategory.SYLLABUS,
        "education": JobCategory.EDUCATION,
    }
    return mapping.get(category, JobCategory.NOTIFICATION)


def _to_enum_scope(scope: str) -> JobScope:
    mapping = {
        "all_india": JobScope.ALL_INDIA,
        "central": JobScope.CENTRAL,
        "state": JobScope.STATE,
    }
    return mapping.get(scope, JobScope.ALL_INDIA)


async def upsert_job(db: Session, scraped: ScrapedJob) -> Tuple[Optional[Job], bool]:
    """Returns (job, is_new). Skipped junk returns (None, False)."""
    if not is_valid_scraped_job(scraped.title, scraped.source_url, scraped.category):
        logger.debug("Skipping junk/non-notification job: %s", scraped.title[:80])
        return None, False

    existing = db.query(Job).filter(Job.source_url == scraped.source_url).first()
    is_new = existing is None

    if existing:
        existing.title = normalize_listing_title(scraped.title) or scraped.title
        existing.updated_at = datetime.utcnow()
        return existing, False

    enriched = await enrich_with_llm(scraped.title, scraped.description or "")

    category = enriched.category or scraped.category
    org = normalize_organization(scraped.title, enriched.organization or scraped.organization)
    state = enriched.state or scraped.state or detect_state(scraped.title, org)

    last_date_str = (enriched.last_date or scraped.last_date)
    exam_date_str = (enriched.exam_date or scraped.exam_date)
    last_fmt = last_date_str.strftime("%d %b %Y") if last_date_str else None
    exam_fmt = exam_date_str.strftime("%d %b %Y") if exam_date_str else None

    details = await enrich_job_details(
        title=scraped.title,
        organization=org,
        state=state,
        category=category,
        vacancies=enriched.vacancies or scraped.vacancies,
        qualification=enriched.qualification,
        last_date=last_fmt,
        exam_date=exam_fmt,
        description=enriched.summary or scraped.description,
        source_url=scraped.source_url,
    )

    # Use official portal as source — never store aggregator URLs as primary link
    canonical_source = scraped.source_url
    if is_aggregator_url(scraped.source_url):
        canonical_source = f"official://{org}/{hashlib.md5(scraped.title.encode()).hexdigest()[:12]}"

    display_title = details.get("official_title") or normalize_listing_title(scraped.title) or scraped.title

    job = Job(
        title=display_title,
        organization=details.get("organization") or org,
        category=_to_enum_category(category),
        scope=_to_enum_scope(scraped.scope),
        state=state,
        vacancies=enriched.vacancies or scraped.vacancies,
        apply_url=details["apply_url"],
        source_url=canonical_source,
        source_name=details.get("organization") or org,
        published_date=enriched.published_date or scraped.published_date,
        last_date=enriched.last_date or scraped.last_date,
        exam_date=enriched.exam_date or scraped.exam_date,
        qualification=enriched.qualification,
        description=enriched.summary or scraped.description,
        full_content=details["full_content"],
        notification_url=details["notification_url"],
        age_limit=details.get("age_limit"),
        application_fee=details.get("application_fee"),
        is_verified=enriched.is_verified,
    )
    db.add(job)
    return job, True


def upsert_news(db: Session, scraped: ScrapedNews) -> NewsItem:
    existing = db.query(NewsItem).filter(NewsItem.url == scraped.url).first()
    if existing:
        existing.title = scraped.title
        existing.is_important = scraped.is_important
        return existing

    item = NewsItem(
        title=scraped.title,
        summary=scraped.summary,
        url=scraped.url,
        source=scraped.source,
        category=scraped.category,
        is_important=scraped.is_important,
        published_at=scraped.published_at,
    )
    db.add(item)
    return item


async def fetch_and_store_all(db: Session) -> dict:
    """Run 3-list fetch pipeline, enrich, store, cleanup, and dispatch alerts."""
    from app.scrapers.fetch_pipeline import run_fetch_pipeline
    from app.scrapers.sources_registry import registry_stats

    registry = registry_stats()
    pipeline = await run_fetch_pipeline()
    jobs_scraped = pipeline.jobs
    news = await fetch_news()

    new_jobs: List[Job] = []
    job_count = 0

    for scraped_job in jobs_scraped:
        job, is_new = await upsert_job(db, scraped_job)
        if job is None:
            continue
        job_count += 1
        if is_new:
            db.flush()
            new_jobs.append(job)

    news_count = 0
    for scraped_news in news:
        upsert_news(db, scraped_news)
        news_count += 1

    db.commit()

    # Prune junk/expired listings and rebuild sections after every fetch.
    try:
        from app.services.cleanup_service import run_cleanup

        cleanup_stats = run_cleanup(db)
        logger.info("Post-fetch cleanup: %s", cleanup_stats)
    except Exception as exc:
        logger.warning("Post-fetch cleanup failed: %s", exc)

    alert_stats = {"email_users": 0, "whatsapp_users": 0}
    if new_jobs:
        alert_stats = await dispatch_alerts_for_new_jobs(db, new_jobs)

    logger.info(
        "Stored %d jobs (%d new), %d news. Alerts: %s",
        job_count, len(new_jobs), news_count, alert_stats,
    )
    return {
        "jobs": job_count,
        "new_jobs": len(new_jobs),
        "news": news_count,
        "alerts": alert_stats,
        "fetch_pipeline": {
            "central_sites": pipeline.central.sites_checked,
            "central_found": pipeline.central.notifications_found,
            "state_groups": pipeline.state.states_checked,
            "state_sites": pipeline.state.sites_checked,
            "state_found": pipeline.state.notifications_found,
            "psu_sites": pipeline.psu.sites_checked,
            "psu_found": pipeline.psu.notifications_found,
            "total_scraped": pipeline.total_found,
            "registry": registry,
        },
    }
