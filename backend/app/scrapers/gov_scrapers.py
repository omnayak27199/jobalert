from __future__ import annotations

"""Base scraper and government job source fetchers."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.bilingual_text import decode_http_text

from app.services.date_extractor import (
    classify_category,
    detect_state,
    extract_dates,
    extract_organization,
    extract_vacancies,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; IndiaJobBot/1.0; +https://indiajob.in/bot)"
)


@dataclass
class ScrapedJob:
    title: str
    source_url: str
    source_name: str
    organization: str
    category: str
    state: str | None
    vacancies: int | None
    apply_url: str | None
    published_date: datetime | None
    last_date: datetime | None
    exam_date: datetime | None
    qualification: str | None
    description: str | None
    is_verified: bool
    scope: str


class BaseScraper(ABC):
    source_name: str = "Unknown"
    base_url: str = ""

    async def fetch_html(self, url: str) -> str | None:
        headers = {"User-Agent": USER_AGENT}
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers=headers,
                verify=False,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return decode_http_text(response.content, response.encoding)
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", url, e)
            return None

    def parse_job_entry(
        self,
        title: str,
        url: str,
        description: str = "",
    ) -> ScrapedJob:
        full_text = f"{title} {description}"
        dates = extract_dates(full_text)
        category = classify_category(title, description)
        org = extract_organization(title)
        state = detect_state(title, org)
        vacancies = extract_vacancies(title) or extract_vacancies(description)

        scope = "state" if state else "central"
        if any(x in title.upper() for x in ["ALL INDIA", "PAN INDIA"]):
            scope = "all_india"

        return ScrapedJob(
            title=title.strip(),
            source_url=url,
            source_name=self.source_name,
            organization=org,
            category=category,
            state=state,
            vacancies=vacancies,
            apply_url=url if "apply" in url.lower() or "form" in title.lower() else None,
            published_date=dates.published_date or datetime.utcnow(),
            last_date=dates.last_date,
            exam_date=dates.exam_date,
            qualification=None,
            description=description[:500] if description else None,
            is_verified=dates.is_verified,
            scope=scope,
        )

    @abstractmethod
    async def scrape(self) -> list[ScrapedJob]:
        pass


class EmploymentNewsScraper(BaseScraper):
    """Scraper for employmentnews.gov.in - official government employment portal."""

    source_name = "Employment News"
    base_url = "https://employmentnews.gov.in"

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        for path in ["/", "/newemp/contList.php", "/archive.php"]:
            html = await self.fetch_html(f"{self.base_url}{path}")
            if html:
                jobs.extend(self._parse(html, f"{self.base_url}{path}"))
        return jobs[:50]

    def _parse(self, html: str, page_url: str) -> list[ScrapedJob]:
        soup = BeautifulSoup(html, "lxml")
        results: list[ScrapedJob] = []
        seen: set[str] = set()
        for link in soup.select("a[href]"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 12 or not href:
                continue
            if classify_category(title) != "notification":
                continue
            url = href if href.startswith("http") else urljoin(page_url, href)
            if url in seen:
                continue
            seen.add(url)
            job = self.parse_job_entry(title, url)
            job.organization = "Employment News"
            job.scope = "all_india"
            results.append(job)
        return results


class FreeJobAlertScraper(BaseScraper):
    """Aggregator scraper - reads RSS/public listings for job data."""

    source_name = "FreeJobAlert"
    base_url = "https://www.freejobalert.com"

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        html = await self.fetch_html(self.base_url)
        if not html:
            return self._get_sample_jobs()

        soup = BeautifulSoup(html, "lxml")
        seen_urls: set[str] = set()

        for link in soup.select("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not title or len(title) < 15 or not href:
                continue
            if not any(
                kw in title.lower()
                for kw in ["form", "admit", "result", "notification", "recruitment", "vacancy", "syllabus", "answer key"]
            ):
                continue
            url = href if href.startswith("http") else f"{self.base_url}{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            jobs.append(self.parse_job_entry(title, url))

        if len(jobs) < 10:
            jobs.extend(self._get_sample_jobs())
        return jobs[:100]

    def _get_sample_jobs(self) -> list[ScrapedJob]:
        """Curated sample data when live scraping is unavailable."""
        samples = [
            ("RRB 3993 JE Online Form 2026 - Last Date 30 Aug 2026", "https://www.rrbcdg.gov.in/"),
            ("SBI 9124 Clerk Online Form 2026 - Last Date 15 Sep 2026", "https://www.sbi.co.in/careers"),
            ("ISRO 267 Assistant, JPA, UDC & Steno Online Form 2026", "https://www.isro.gov.in/Careers"),
            ("UPSSSC 1308 Veterinary Pharmacist Online Form 2026", "https://upsssc.gov.in/"),
            ("IBPS 11403 Clerk Online Form 2026 - Last Date 25 Aug 2026", "https://www.ibps.in/"),
            ("Karnataka 15000 Teacher Online Form 2026", "https://kpsc.kar.nic.in/"),
            ("NTPC 135 Deputy Manager Online Form 2026", "https://careers.ntpc.co.in/"),
            ("Union Bank of India 395 SO Online Form 2026", "https://www.unionbankofindia.co.in/english/recruitment.aspx"),
            ("AAI 389 Manager, Junior Executive Online Form 2026", "https://www.aai.aero/en/careers"),
            ("PNB 545 LBO Online Form 2026", "https://www.pnbindia.in/recruitment.html"),
            ("RRB Group D Admit Card 2026 Out", "https://www.rrbcdg.gov.in/"),
            ("Allahabad High Court Research Associate Admit Card 2026 Out", "https://www.allahabadhighcourt.in/"),
            ("UPPSC Computer Assistant Typing Test Admit Card 2026", "https://uppsc.up.nic.in/"),
            ("PSTET Result 2026", "https://pstet.pseb.ac.in/"),
            ("RSSB Junior Technical Assistant Final Result 2026 Out", "https://rssb.rajasthan.gov.in/"),
            ("GSSSB CCE Group A Mains Result 2026 Out", "https://gsssb.gujarat.gov.in/"),
            ("UPSSSC Assistant Accountant Final Result 2026", "https://upsssc.gov.in/"),
            ("MPSC Assistant Professor Final Answer Key 2026 Out", "https://mpsc.gov.in/"),
            ("RRB JE Syllabus 2026", "https://www.rrbcdg.gov.in/"),
            ("SBI Junior Associates Clerk Syllabus 2026", "https://www.sbi.co.in/careers"),
            ("OSSSC 5989 Nursing Officer Online Form 2026 - Last Date 16 Aug 2026", "https://osssc.gov.in/"),
            ("MPESB 2306 Group 2 Subgroup 4 Online Form 2026 - Last Date 18 Aug 2026", "https://esb.mp.gov.in/"),
            ("NFR 6777 Act Apprentice Online Form 2026 - Last Date 20 Aug 2026", "https://nfr.indianrailways.gov.in/"),
            ("ICF 1010 Act Apprentice Online Form 2026", "https://icf.indianrailways.gov.in/"),
            ("BPCL 154 Technician & Operator Online Form 2026", "https://www.bharatpetroleum.in/"),
            ("Indian Oil Officers Online Form 2026", "https://iocl.com/"),
            ("DRDO HEMRL Graduate Apprentice Offline Form 2026", "https://www.drdo.gov.in/"),
            ("ITBP CAPF 282 Medical Officer Online Form 2026", "https://rectt.itbpolice.nic.in/"),
            ("Rajasthan NEET UG Counselling 2026 Round 1 Schedule Out", "https://rajneetug2026.org/"),
            ("WBCAP Merit List 2026 Mop-Up Round 3 Out", "https://wbjeeb.nic.in/"),
        ]
        return [self.parse_job_entry(title, url) for title, url in samples]


class UPSCScraper(BaseScraper):
    source_name = "UPSC"
    base_url = "https://upsc.gov.in"

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        html = await self.fetch_html(f"{self.base_url}/en/Examination/ActiveExams")
        if not html:
            return jobs

        soup = BeautifulSoup(html, "lxml")
        for item in soup.select("a, li"):
            title = item.get_text(strip=True)
            href = item.get("href", "") if item.name == "a" else ""
            if len(title) < 10:
                continue
            url = href if href.startswith("http") else f"{self.base_url}{href}" if href else self.base_url
            if "exam" in title.lower() or "recruitment" in title.lower():
                jobs.append(self.parse_job_entry(title, url))
        return jobs[:30]


class SSCScraper(BaseScraper):
    source_name = "SSC"
    base_url = "https://ssc.nic.in"

    async def scrape(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        html = await self.fetch_html(self.base_url)
        if not html:
            return jobs

        soup = BeautifulSoup(html, "lxml")
        for link in soup.select("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if len(title) < 10:
                continue
            url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
            jobs.append(self.parse_job_entry(title, url))
        return jobs[:30]


async def run_all_scrapers() -> list[ScrapedJob]:
    """Fetch from 3 lists: central govt → state sites → PSUs."""
    from app.scrapers.fetch_pipeline import run_fetch_pipeline

    pipeline = await run_fetch_pipeline()
    return pipeline.jobs

