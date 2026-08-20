from __future__ import annotations

"""Generic scraper driven by sources_registry — handles all portals uniformly."""

import logging
import re
from typing import Iterable
from urllib.parse import unquote, urljoin

from app.services.content_quality import title_from_pdf_filename

from bs4 import BeautifulSoup

from app.scrapers.gov_scrapers import BaseScraper, ScrapedJob
from app.scrapers.sources_registry import SourceConfig
from app.services.date_extractor import classify_category
from app.services.official_title import normalize_listing_title

logger = logging.getLogger(__name__)

JOB_KEYWORDS = [
    "recruitment", "notification", "vacancy", "vacancies", "apply online",
    "online form", "online application", "bharti", "walk-in", "walkin",
    "appointment", "advertisement", "advt", "posts", "post of", "exam",
]

STRONG_KEYWORDS = [
    "recruitment", "vacancy", "vacancies", "online form", "apply online",
    "online application", "notification for", "advertisement", "advt",
    "posts", "post of", "bharti", "recruit",
    "vigyapan", "niyukti",
]

HINDI_STRONG_KEYWORDS = [
    "भर्ती", "विज्ञापन", "अधिसूचना", "रिक्त", "आवेदन", "नियुक्ति",
]

CATEGORY_DEFAULT_PATHS: dict[str, list[str]] = {
    "state_psc": [
        "/",
        "/advertisements",
        "/Posts?tag=ONLINEAPPLICATION",
    ],
    "government": ["/", "/careers", "/recruitment", "/notification"],
    "psu": ["/", "/careers", "/recruitment"],
    "university": ["/", "/recruitment", "/career", "/careers"],
    "education": ["/", "/recruitment", "/careers"],
    "defence": ["/", "/careers", "/recruitment"],
}

SOURCE_EXTRA_PATHS: dict[str, list[str]] = {
    "CG Vyapam": ["/Posts?tag=ONLINEAPPLICATION", "/NOTICE/"],
    "RPSC": ["/advertisements", "/applyonline"],
    "DSSSB": ["/notice-of-exam", "/dsssb/recruitment"],
    "MPPSC": ["/advertisement"],
    "TNPSC": ["/latest-notification.html", "/notifications.html"],
    "UPPSC": ["/Notifications.aspx", "/ViewAllNotifications.aspx"],
    "BPSC": ["/Notifications/Notification.html"],
    "Kerala PSC": ["/notifications"],
    "JPSC": ["/Advertisement", "/advertisement"],
    "Tripura PSC": ["/notifications", "/"],
}


def _is_job_link(title: str, href: str = "") -> bool:
    from app.services.job_quality import is_junk_title, is_junk_url

    t = title.strip()
    if not t or is_junk_title(t) or is_junk_url(href):
        return False
    if href.startswith("javascript:") or href in {"#", "/#"}:
        return False
    lower = t.lower()
    if len(t) < 12:
        return False
    if not any(kw in lower for kw in STRONG_KEYWORDS) and not any(kw in t for kw in HINDI_STRONG_KEYWORDS):
        return False
    if classify_category(t) != "notification":
        return False
    return True


def _title_from_pdf_href(href: str) -> str:
    derived = title_from_pdf_filename(href)
    if derived:
        return derived
    name = unquote(href.split("/")[-1].split("?")[0])
    name = re.sub(r"[_-]+", " ", name)
    name = re.sub(r"\.pdf$", "", name, flags=re.I).strip()
    return name[:160] if name else "Official Notification PDF"


class PortalScraper(BaseScraper):
    """Scrapes any government portal defined in SourceConfig."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self.source_name = config.name
        self.base_url = config.url.rstrip("/")

    def _paths_to_fetch(self) -> list[str]:
        paths: list[str] = list(self.config.paths or ["/"])
        paths.extend(CATEGORY_DEFAULT_PATHS.get(self.config.category, []))
        paths.extend(SOURCE_EXTRA_PATHS.get(self.config.name, []))
        seen: set[str] = set()
        ordered: list[str] = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                ordered.append(path)
        return ordered

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        seen_urls: set[str] = set()

        for path in self._paths_to_fetch():
            url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
            html = await self.fetch_html(url)
            if not html:
                continue
            for job in self._parse(html, page_url=url):
                if job.source_url in seen_urls:
                    continue
                seen_urls.add(job.source_url)
                jobs.append(job)

        return jobs[:40]

    def _make_job(self, title: str, url: str) -> ScrapedJob:
        job = self.parse_job_entry(title, url)
        job.source_name = self.config.name
        job.organization = self.config.organization or self.config.name
        job.state = self.config.state
        job.scope = self.config.scope
        job.category = "notification"
        if self.config.category in ("university", "education"):
            job.category = classify_category(title)
        return job

    def _candidate_links(self, soup: BeautifulSoup) -> Iterable[tuple[str, str]]:
        for node in soup.select("a[href], area[href]"):
            raw_title = node.get("title") or node.get_text(" ", strip=True)
            title = normalize_listing_title(raw_title)
            href = node.get("href", "")
            if title and href:
                yield title, href

        for row in soup.select("tr"):
            link = row.select_one("a[href]")
            if not link:
                continue
            link_text = link.get_text(" ", strip=True)
            row_text = row.get_text(" ", strip=True)
            title = link_text if len(link_text) >= 12 else row_text
            title = normalize_listing_title(title)
            href = link.get("href", "")
            if title and href:
                yield title, href

    def _parse(self, html: str, page_url: str = "") -> list[ScrapedJob]:
        soup = BeautifulSoup(html, "lxml")
        results: list[ScrapedJob] = []
        seen: set[str] = set()

        for title, href in self._candidate_links(soup):
            if not href or href.startswith("#"):
                continue

            abs_url = href if href.startswith("http") else urljoin(page_url or self.base_url + "/", href)
            lower_href = abs_url.lower()

            if lower_href.endswith(".pdf") or ".pdf" in lower_href.split("?")[0]:
                pdf_title = title if _is_job_link(title, abs_url) else _title_from_pdf_href(abs_url)
                if not _is_job_link(pdf_title, abs_url) and not any(
                    kw in pdf_title.lower() for kw in ("advt", "recruit", "vacancy", "notification", "exam")
                ):
                    continue
                if abs_url in seen:
                    continue
                seen.add(abs_url)
                results.append(self._make_job(pdf_title, abs_url))
                continue

            if not _is_job_link(title, abs_url):
                continue
            if abs_url in seen:
                continue
            seen.add(abs_url)
            results.append(self._make_job(title, abs_url))

        return results


def build_central_scrapers() -> list[PortalScraper]:
    from app.scrapers.sources_registry import CENTRAL_GOVERNMENT_SOURCES

    return [PortalScraper(cfg) for cfg in CENTRAL_GOVERNMENT_SOURCES]


def build_state_scrapers() -> list[PortalScraper]:
    from app.scrapers.sources_registry import STATE_GOVERNMENT_SOURCES

    return [PortalScraper(cfg) for cfg in STATE_GOVERNMENT_SOURCES]


def build_psu_scrapers() -> list[PortalScraper]:
    from app.scrapers.sources_registry import PSU_SOURCES

    return [PortalScraper(cfg) for cfg in PSU_SOURCES]


def build_all_portal_scrapers() -> list[PortalScraper]:
    from app.scrapers.sources_registry import get_all_fetch_sources

    return [PortalScraper(cfg) for cfg in get_all_fetch_sources()]
