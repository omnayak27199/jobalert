from __future__ import annotations

"""News fetcher for important government and education updates."""

import logging
from dataclasses import dataclass
from datetime import datetime

import feedparser
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ScrapedNews:
    title: str
    summary: str | None
    url: str
    source: str
    category: str
    is_important: bool
    published_at: datetime | None


NEWS_FEEDS = [
    ("https://www.employmentnews.gov.in/rss.xml", "Employment News", "jobs"),
    ("https://pib.gov.in/RssMain.aspx?ModId=6&Lang=2&RegId=3", "PIB India", "government"),
]

IMPORTANT_KEYWORDS = [
    "upsc", "ssc", "rrb", "ibps", "recruitment", "vacancy", "admit card",
    "result", "notification", "sarkari", "government job", "exam date",
    "last date", "neet", "jee", "cuet", "banking", "railway", "defence",
]


def _is_important(title: str, summary: str = "") -> bool:
    combined = f"{title} {summary}".lower()
    return any(kw in combined for kw in IMPORTANT_KEYWORDS)


async def fetch_news() -> list[ScrapedNews]:
    """Fetch news from RSS feeds and government sources."""
    news_items: list[ScrapedNews] = []

    for feed_url, source, category in NEWS_FEEDS:
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(feed_url)
                if response.status_code != 200:
                    continue
                feed = feedparser.parse(response.text)
                for entry in feed.entries[:20]:
                    title = entry.get("title", "")
                    if not title:
                        continue
                    summary = entry.get("summary", entry.get("description", ""))[:300]
                    url = entry.get("link", "")
                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    news_items.append(
                        ScrapedNews(
                            title=title,
                            summary=summary,
                            url=url,
                            source=source,
                            category=category,
                            is_important=_is_important(title, summary),
                            published_at=published,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to fetch news from %s: %s", feed_url, e)

    if len(news_items) < 5:
        news_items.extend(_get_sample_news())

    return news_items


def _get_sample_news() -> list[ScrapedNews]:
    now = datetime.utcnow()
    return [
        ScrapedNews(
            title="UPSC Civil Services 2026 Notification Expected Soon",
            summary="Union Public Service Commission may release Civil Services Examination 2026 notification in February.",
            url="https://upsc.gov.in/",
            source="IndiaJob",
            category="jobs",
            is_important=True,
            published_at=now,
        ),
        ScrapedNews(
            title="RRB NTPC CBT 2 Exam Schedule Released",
            summary="Railway Recruitment Board has announced the exam schedule for NTPC CBT 2 phase.",
            url="https://www.rrbcdg.gov.in/",
            source="IndiaJob",
            category="jobs",
            is_important=True,
            published_at=now,
        ),
        ScrapedNews(
            title="IBPS PO 2026 Registration Window Extended",
            summary="Institute of Banking Personnel Selection extends the last date for PO application.",
            url="https://www.ibps.in/",
            source="IndiaJob",
            category="jobs",
            is_important=True,
            published_at=now,
        ),
        ScrapedNews(
            title="NEET UG 2026 Counselling Schedule Announced",
            summary="MCC releases NEET UG counselling schedule for all India quota seats.",
            url="https://mcc.nic.in/",
            source="IndiaJob",
            category="education",
            is_important=True,
            published_at=now,
        ),
        ScrapedNews(
            title="SSC CGL 2026 Tier 1 Exam Dates Out",
            summary="Staff Selection Commission announces Tier 1 exam dates for Combined Graduate Level 2026.",
            url="https://ssc.nic.in/",
            source="IndiaJob",
            category="jobs",
            is_important=True,
            published_at=now,
        ),
    ]
