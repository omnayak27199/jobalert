from __future__ import annotations

"""Single fetch action over 3 source lists: Central | State | PSU."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field

from app.scrapers.gov_scrapers import ScrapedJob
from app.scrapers.portal_scraper import PortalScraper
from app.scrapers.sources_registry import (
    CENTRAL_GOVERNMENT_SOURCES,
    PSU_SOURCES,
    STATE_SOURCE_GROUPS,
    registry_stats,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 15


@dataclass
class TierFetchStats:
    tier: str
    sites_checked: int = 0
    notifications_found: int = 0
    states_checked: int = 0


@dataclass
class FetchPipelineResult:
    jobs: list[ScrapedJob] = field(default_factory=list)
    central: TierFetchStats = field(default_factory=lambda: TierFetchStats("central"))
    state: TierFetchStats = field(default_factory=lambda: TierFetchStats("state"))
    psu: TierFetchStats = field(default_factory=lambda: TierFetchStats("psu"))

    @property
    def total_found(self) -> int:
        return len(self.jobs)


async def _scrape_portal(scraper: PortalScraper) -> list[ScrapedJob]:
    try:
        return await scraper.scrape()
    except Exception as exc:
        logger.error("Scraper failed for %s: %s", scraper.config.name, exc)
        return []


async def _scrape_batch(scrapers: list[PortalScraper]) -> list[ScrapedJob]:
    if not scrapers:
        return []
    results = await asyncio.gather(*[_scrape_portal(s) for s in scrapers])
    jobs: list[ScrapedJob] = []
    for batch_jobs in results:
        jobs.extend(batch_jobs)
    return jobs


def _dedupe_jobs(jobs: list[ScrapedJob], seen: set[str]) -> list[ScrapedJob]:
    unique: list[ScrapedJob] = []
    for job in jobs:
        key = hashlib.md5(job.source_url.encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique


async def run_fetch_pipeline() -> FetchPipelineResult:
    """
    One fetch action, three lists:
      1. All-India central government websites
      2. All states → each state's government site list
      3. PSU websites
    """
    result = FetchPipelineResult()
    seen: set[str] = set()
    stats = registry_stats()
    logger.info(
        "Fetch pipeline starting — central=%d, states=%d (%d sites), psu=%d",
        stats["central_government_sites"],
        stats["state_groups"],
        stats["state_government_sites"],
        stats["psu_sites"],
    )

    # ── List 1: Central Government ─────────────────────────────────────────
    central_scrapers = [PortalScraper(cfg) for cfg in CENTRAL_GOVERNMENT_SOURCES]
    for i in range(0, len(central_scrapers), BATCH_SIZE):
        batch = central_scrapers[i : i + BATCH_SIZE]
        jobs = _dedupe_jobs(await _scrape_batch(batch), seen)
        result.jobs.extend(jobs)
        result.central.notifications_found += len(jobs)
    result.central.sites_checked = len(central_scrapers)
    logger.info(
        "Central govt fetch done — %d sites, %d notifications",
        result.central.sites_checked,
        result.central.notifications_found,
    )

    # ── List 2: State-wise (iterate each state, then its sites) ────────────
    for group in STATE_SOURCE_GROUPS:
        state_scrapers = [PortalScraper(cfg) for cfg in group.sites]
        state_jobs: list[ScrapedJob] = []
        for i in range(0, len(state_scrapers), BATCH_SIZE):
            batch = state_scrapers[i : i + BATCH_SIZE]
            state_jobs.extend(await _scrape_batch(batch))
        unique_state_jobs = _dedupe_jobs(state_jobs, seen)
        result.jobs.extend(unique_state_jobs)
        result.state.notifications_found += len(unique_state_jobs)
        result.state.sites_checked += len(state_scrapers)
        result.state.states_checked += 1
        if unique_state_jobs:
            logger.info(
                "State %s — %d sites, %d notifications",
                group.state,
                len(group.sites),
                len(unique_state_jobs),
            )

    logger.info(
        "State fetch done — %d states, %d sites, %d notifications",
        result.state.states_checked,
        result.state.sites_checked,
        result.state.notifications_found,
    )

    # ── List 3: PSUs ───────────────────────────────────────────────────────
    psu_scrapers = [PortalScraper(cfg) for cfg in PSU_SOURCES]
    for i in range(0, len(psu_scrapers), BATCH_SIZE):
        batch = psu_scrapers[i : i + BATCH_SIZE]
        jobs = _dedupe_jobs(await _scrape_batch(batch), seen)
        result.jobs.extend(jobs)
        result.psu.notifications_found += len(jobs)
    result.psu.sites_checked = len(psu_scrapers)
    logger.info(
        "PSU fetch done — %d sites, %d notifications",
        result.psu.sites_checked,
        result.psu.notifications_found,
    )

    logger.info(
        "Fetch pipeline complete — %d unique notifications from %d sources",
        result.total_found,
        stats["total_sources"],
    )
    return result
