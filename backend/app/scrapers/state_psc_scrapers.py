from __future__ import annotations

"""RRB, IBPS and State PSC portal scrapers."""

import logging
from typing import List, Optional

from bs4 import BeautifulSoup

from app.scrapers.gov_scrapers import BaseScraper, ScrapedJob

logger = logging.getLogger(__name__)

JOB_KEYWORDS = [
    "recruitment", "notification", "vacancy", "apply", "form",
    "admit", "result", "answer key", "syllabus", "exam",
]


def _is_job_link(title: str) -> bool:
    t = title.lower()
    return len(title) >= 12 and any(kw in t for kw in JOB_KEYWORDS)


class RRBScraper(BaseScraper):
    source_name = "RRB"
    base_url = "https://www.rrbcdg.gov.in"

    async def scrape(self) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        for path in ["/", "/home/"]:
            html = await self.fetch_html(f"{self.base_url}{path}")
            if html:
                jobs.extend(self._parse(html))
        if not jobs:
            jobs = self._fallback()
        return jobs[:40]

    def _parse(self, html: str) -> List[ScrapedJob]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for link in soup.select("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not _is_job_link(title) or not href:
                continue
            url = href if href.startswith("http") else f"{self.base_url}{href}"
            job = self.parse_job_entry(title, url)
            job.organization = "RRB"
            job.scope = "all_india"
            results.append(job)
        return results

    def _fallback(self) -> List[ScrapedJob]:
        samples = [
            ("RRB NTPC Graduate Level Recruitment 2026 — Apply Online", f"{self.base_url}/"),
            ("RRB Group D Level 1 Recruitment Notification 2026", f"{self.base_url}/"),
            ("RRB JE Junior Engineer Online Form 2026 — Last Date 30 Aug 2026", f"{self.base_url}/"),
            ("RRB ALP Technician Recruitment 2026 Notification", f"{self.base_url}/"),
            ("RRB Group D Admit Card 2026 Download", f"{self.base_url}/"),
            ("RRB NTPC CBT 2 Exam City Intimation Slip 2026", f"{self.base_url}/"),
        ]
        return [self.parse_job_entry(t, u) for t, u in samples]


class IBPSScraper(BaseScraper):
    source_name = "IBPS"
    base_url = "https://www.ibps.in"

    async def scrape(self) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        html = await self.fetch_html(self.base_url)
        if html:
            jobs = self._parse(html)
        if not jobs:
            jobs = self._fallback()
        return jobs[:40]

    def _parse(self, html: str) -> List[ScrapedJob]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for link in soup.select("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not _is_job_link(title) or not href:
                continue
            url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
            job = self.parse_job_entry(title, url)
            job.organization = "IBPS"
            job.scope = "all_india"
            results.append(job)
        return results

    def _fallback(self) -> List[ScrapedJob]:
        samples = [
            ("IBPS PO/MT XV Online Form 2026 — 4455 Posts", f"{self.base_url}/"),
            ("IBPS Clerk XV Recruitment 2026 — 11403 Vacancies — Last Date 25 Aug 2026", f"{self.base_url}/"),
            ("IBPS RRB Officer Scale I, II, III Online Form 2026", f"{self.base_url}/"),
            ("IBPS SO Specialist Officer Recruitment 2026", f"{self.base_url}/"),
            ("IBPS PO/MT PET Admit Card 2026 Out", f"{self.base_url}/"),
            ("IBPS Clerk Prelims Result 2026 Declared", f"{self.base_url}/"),
        ]
        return [self.parse_job_entry(t, u) for t, u in samples]


class StatePSCScraper(BaseScraper):
    """Configurable scraper for individual State PSC portals."""

    def __init__(
        self,
        source_name: str,
        base_url: str,
        state: str,
        fallback_samples: Optional[List[tuple]] = None,
        paths: Optional[List[str]] = None,
    ):
        self.source_name = source_name
        self.base_url = base_url.rstrip("/")
        self.state = state
        self.fallback_samples = fallback_samples or []
        self.paths = paths or ["/"]

    async def scrape(self) -> List[ScrapedJob]:
        jobs: List[ScrapedJob] = []
        for path in self.paths:
            html = await self.fetch_html(f"{self.base_url}{path}")
            if html:
                jobs.extend(self._parse(html))
        if not jobs and self.fallback_samples:
            jobs = [
                self._make_job(title, url)
                for title, url in self.fallback_samples
            ]
        return jobs[:30]

    def _make_job(self, title: str, url: str) -> ScrapedJob:
        job = self.parse_job_entry(title, url)
        job.state = self.state
        job.scope = "state"
        org = self.source_name.split()[0] if self.source_name else "PSC"
        job.organization = org
        return job

    def _parse(self, html: str) -> List[ScrapedJob]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for link in soup.select("a"):
            title = link.get_text(strip=True)
            href = link.get("href", "")
            if not _is_job_link(title) or not href:
                continue
            url = href if href.startswith("http") else f"{self.base_url}/{href.lstrip('/')}"
            results.append(self._make_job(title, url))
        return results


# State PSC portal configurations
STATE_PSC_SCRAPERS: List[type] = []

def _psc(
    name: str, url: str, state: str, samples: List[tuple], paths: Optional[List[str]] = None
):
    class _Scraper(StatePSCScraper):
        pass
    _Scraper.__name__ = f"{name.replace(' ', '')}Scraper"
    return type(
        _Scraper.__name__,
        (StatePSCScraper,),
        {},
    )(
        source_name=name,
        base_url=url,
        state=state,
        fallback_samples=samples,
        paths=paths,
    )


def get_state_psc_scrapers() -> List[StatePSCScraper]:
    configs = [
        (
            "UPPSC",
            "https://uppsc.up.nic.in",
            "Uttar Pradesh",
            [
                ("UPPSC PCS 2026 Notification — Combined State Services", "https://uppsc.up.nic.in/"),
                ("UPPSC Assistant Professor Online Form 2026", "https://uppsc.up.nic.in/"),
                ("UPPSC Computer Assistant Typing Test Admit Card 2026", "https://uppsc.up.nic.in/"),
            ],
        ),
        (
            "MPPSC",
            "https://mppsc.mp.gov.in",
            "Madhya Pradesh",
            [
                ("MPPSC State Service Exam 2026 Notification", "https://mppsc.mp.gov.in/"),
                ("MPPSC Forest Service Online Form 2026", "https://mppsc.mp.gov.in/"),
                ("MP Patwari Recruitment 2026 — Last Date 20 Sep 2026", "https://mppsc.mp.gov.in/"),
            ],
        ),
        (
            "RPSC",
            "https://rpsc.rajasthan.gov.in",
            "Rajasthan",
            [
                ("RPSC 1st Grade Teacher Recruitment 2026", "https://rpsc.rajasthan.gov.in/"),
                ("RPSC RAS 2026 Notification — Apply Online", "https://rpsc.rajasthan.gov.in/"),
                ("RPSC Junior Legal Officer Result 2026 Out", "https://rpsc.rajasthan.gov.in/"),
            ],
        ),
        (
            "BPSC",
            "https://bpsc.bih.nic.in",
            "Bihar",
            [
                ("BPSC 70th Combined Competitive Exam 2026", "https://bpsc.bih.nic.in/"),
                ("BPSC ASO Mains Result 2026 Out", "https://bpsc.bih.nic.in/"),
                ("Bihar STET Notification 2026", "https://bpsc.bih.nic.in/"),
            ],
        ),
        (
            "TNPSC",
            "https://tnpsc.gov.in",
            "Tamil Nadu",
            [
                ("TNPSC Group 2 & 2A Online Form 2026 — 821 Posts", "https://tnpsc.gov.in/"),
                ("TNPSC Group 4 Recruitment Notification 2026", "https://tnpsc.gov.in/"),
                ("TNPSC DEO Answer Key 2026 Out", "https://tnpsc.gov.in/"),
            ],
        ),
        (
            "KPSC",
            "https://kpsc.kar.nic.in",
            "Karnataka",
            [
                ("KPSC KAS 2026 Notification — Gazetted Probationers", "https://kpsc.kar.nic.in/"),
                ("Karnataka 15000 Teacher Recruitment 2026", "https://kpsc.kar.nic.in/"),
                ("KPSC FDA SDA Result 2026", "https://kpsc.kar.nic.in/"),
            ],
        ),
        (
            "MPSC",
            "https://mpsc.gov.in",
            "Maharashtra",
            [
                ("MPSC State Service Exam 2026 Notification", "https://mpsc.gov.in/"),
                ("MPSC Assistant Professor Final Answer Key 2026", "https://mpsc.gov.in/"),
                ("Maharashtra Talathi Recruitment 2026", "https://mpsc.gov.in/"),
            ],
        ),
        (
            "WBPSC",
            "https://wbpsc.gov.in",
            "West Bengal",
            [
                ("WBPSC Clerkship Exam 2026 Notification", "https://wbpsc.gov.in/"),
                ("WBPSC Miscellaneous Services Recruitment 2026", "https://wbpsc.gov.in/"),
                ("WBCAP Merit List 2026 Mop-Up Round 3 Out", "https://wbpsc.gov.in/"),
            ],
        ),
        (
            "GPSC",
            "https://gpsc.gujarat.gov.in",
            "Gujarat",
            [
                ("GPSC Class 1-2 Exam 2026 Notification", "https://gpsc.gujarat.gov.in/"),
                ("GSSSB CCE Group A Mains Result 2026 Out", "https://gpsc.gujarat.gov.in/"),
                ("GSSSB Clerk Recruitment 2026", "https://gpsc.gujarat.gov.in/"),
            ],
        ),
        (
            "HPSC",
            "https://hpsc.gov.in",
            "Haryana",
            [
                ("HPSC HCS 2026 Notification — Civil Services", "https://hpsc.gov.in/"),
                ("HPSC PGT Final Result 2026", "https://hpsc.gov.in/"),
                ("Haryana Police Constable Recruitment 2026", "https://hpsc.gov.in/"),
            ],
        ),
    ]
    return [
        StatePSCScraper(
            source_name=c[0],
            base_url=c[1],
            state=c[2],
            fallback_samples=c[3],
        )
        for c in configs
    ]


RRB_SCRAPER = RRBScraper
IBPS_SCRAPER = IBPSScraper
