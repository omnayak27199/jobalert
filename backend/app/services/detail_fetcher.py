from __future__ import annotations

"""Build rich job detail content and fetch official notification pages."""

import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.official_portals import fetch_official_portal_details, resolve_vyapam_post_url
from app.services.official_urls import is_aggregator_url, resolve_apply_url, resolve_official_url
from app.services.org_resolver import normalize_organization
from app.services.bilingual_text import decode_http_text
from app.services.notification_pdf_parser import enrich_from_notification_pdf
from app.services.official_title import choose_best_title, extract_official_title_from_text
from app.services.recruitment_content import (
    build_generic_advertisement_sections,
    sections_to_json,
)

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaJobBot/1.0; +https://indiajob.in/bot)"

PORTAL_JUNK_MARKERS = (
    "skip to main content",
    "select your language",
    "javascript is disabled",
    "web information manager",
)


def is_pdf_url(url: str | None) -> bool:
    if not url:
        return False
    lower = url.lower().split("?")[0]
    return lower.endswith(".pdf") or ".pdf" in lower


def is_pdf_binary_text(text: str | None) -> bool:
    if not text:
        return False
    sample = text.lstrip()[:16]
    return sample.startswith("%PDF-") or "\x00" in sample[:200]


def extract_closing_date(text: str) -> Optional[str]:
    if not text:
        return None
    patterns = [
        r"closing date[^:\n]{0,60}?\s*:?\s*-?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
        r"last date[^:\n]{0,40}?\s*:?\s*-?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
        r"(?:upto|till)[^0-9]{0,20}(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})",
        r"(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s*(?:is\s*)?(?:last|closing)\s*date",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).replace("-", "/")
    return None


def is_portal_junk_text(text: str) -> bool:
    lower = text.lower()
    hits = sum(1 for marker in PORTAL_JUNK_MARKERS if marker in lower)
    return hits >= 2


async def fetch_page_html(url: str) -> Optional[str]:
    if is_aggregator_url(url) or url.startswith("pdf://") or is_pdf_url(url):
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": USER_AGENT})
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                return None
            return response.text
    except Exception as e:
        logger.debug("Could not fetch HTML %s: %s", url, e)
        return None


async def fetch_page_text(url: str, max_chars: int = 6000) -> Optional[str]:
    if is_aggregator_url(url) or url.startswith("pdf://") or is_pdf_url(url):
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": USER_AGENT})
            if response.status_code != 200:
                return None
            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                return None
            if response.content[:5].startswith(b"%PDF-"):
                return None
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [ln.strip() for ln in text.split("\n") if ln.strip() and len(ln.strip()) > 3]
            return "\n".join(lines[:80])[:max_chars]
    except Exception as e:
        logger.debug("Could not fetch %s: %s", url, e)
        return None


def build_full_content(
    title: str,
    organization: str,
    state: Optional[str],
    category: str,
    vacancies: Optional[int],
    qualification: Optional[str],
    last_date: Optional[str],
    exam_date: Optional[str],
    description: Optional[str],
    fetched_text: Optional[str] = None,
    age_limit: Optional[str] = None,
    application_fee: Optional[str] = None,
    pdf_url: Optional[str] = None,
) -> str:
    """Build full advertisement detail for on-site display."""
    parts = []

    parts.append(f"## {title}\n")
    parts.append("### Recruitment Overview\n")
    parts.append(f"- **Recruiting Body:** {organization}")
    parts.append(f"- **Job Category:** {category.replace('_', ' ').title()}")
    parts.append(f"- **Location / State:** {state or 'All India (Central Government)'}")
    if vacancies:
        parts.append(f"- **Total Vacancies:** {vacancies:,}")
    if qualification:
        parts.append(f"- **Qualification Required:** {qualification}")
    if age_limit:
        parts.append(f"- **Age Limit:** {age_limit}")
    if application_fee:
        parts.append(f"- **Application Fee:** {application_fee}")

    parts.append("\n### Important Dates\n")
    parts.append(f"- **Last Date to Apply:** {last_date or 'See official notification'}")
    if exam_date:
        parts.append(f"- **Exam Date:** {exam_date}")

    if description:
        parts.append(f"\n### Brief Summary\n{description}\n")

    if pdf_url:
        parts.append(f"\n### Official Notification PDF\n")
        parts.append(f"- **Download PDF:** {pdf_url}")

    if fetched_text:
        parts.append("\n### Official Notification Details\n")
        if not is_pdf_binary_text(fetched_text):
            parts.append(fetched_text[:12000])

    parts.append("\n### How to Apply\n")
    parts.append(
        "1. Read the complete official notification carefully before applying.\n"
        "2. Check eligibility criteria — qualification, age limit, and experience.\n"
        "3. Click **Apply Online** or **Download Official Notification (PDF)** below.\n"
        "4. Fill the application form on the official government portal only.\n"
        "5. Pay the application fee (if applicable) through official channels.\n"
        "6. Save confirmation page and take a printout for future reference.\n"
    )

    parts.append("\n---\n*Source: Official government recruitment portal. "
                 "Always verify details on the official website before applying.*")

    return "\n".join(parts)


def extract_links_from_page(html: str, base_url: str = "") -> dict[str, str]:
    """Extract apply/notification PDF links from a page."""
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, str] = {}
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        text = link.get_text(strip=True).lower()
        link_text_raw = link.get_text(strip=True)
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        if href.startswith("http"):
            full = href
        elif base_url:
            full = urljoin(base_url, href)
        else:
            continue
        if is_aggregator_url(full):
            continue
        href_lower = full.lower()
        if href_lower.endswith(".pdf") or ".pdf" in href_lower.split("?")[0]:
            result["pdf"] = full
            result.setdefault("notification", full)
        if any(kw in text for kw in ["apply online", "apply now", "registration", "application form", "click here to apply", "ऑनलाइन आवेदन", "आवेदन करें"]):
            result["apply"] = full
        if any(
            kw in text or kw in link_text_raw
            for kw in [
                "notification", "advertisement", "detailed adv", "download", "vacancy",
                "विज्ञापन", "अधिसूचना", "विस्तृत", "सूचना",
            ]
        ):
            result.setdefault("notification", full)
    return result


async def enrich_job_details(
    title: str,
    organization: str,
    state: Optional[str],
    category: str,
    vacancies: Optional[int],
    qualification: Optional[str],
    last_date: Optional[str],
    exam_date: Optional[str],
    description: Optional[str],
    source_url: str,
) -> dict:
    """
    Resolve official URLs and build full on-site content.
    Never exposes aggregator URLs to users.
    """
    organization = normalize_organization(title, organization)
    notification_url: Optional[str] = None
    apply_url: Optional[str] = None
    pdf_url: Optional[str] = None
    fetched_text: Optional[str] = None
    age_limit: Optional[str] = None
    application_fee: Optional[str] = None
    official_post_url: Optional[str] = None
    if "vyapam" in f"{organization} {title}".lower():
        official_post_url = resolve_vyapam_post_url(title)

    official_base = resolve_official_url(organization, title, source_url)

    if is_pdf_url(source_url):
        pdf_url = source_url
        notification_url = source_url

    # 1) Scrape aggregator page internally to find official post/PDF links
    if is_aggregator_url(source_url):
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(source_url, headers={"User-Agent": USER_AGENT})
                if resp.status_code == 200:
                    links = extract_links_from_page(resp.text, base_url=source_url)
                    pdf_url = links.get("pdf")
                    notification_url = pdf_url or links.get("notification")
                    apply_url = links.get("apply")
                    if notification_url and "vyapamcg.cgstate.gov.in/post" in notification_url.lower():
                        official_post_url = notification_url
                    if notification_url and not is_aggregator_url(notification_url):
                        if not is_pdf_url(notification_url):
                            fetched_text = await fetch_page_text(notification_url)
                        else:
                            pdf_url = pdf_url or notification_url
        except Exception as e:
            logger.debug("Aggregator link extraction failed: %s", e)

    # 2) Organization-specific official portal fetch (uses post URL when available)
    portal_details = await fetch_official_portal_details(organization, title, post_url=official_post_url)
    if portal_details:
        organization = portal_details.get("organization") or organization
        notification_url = portal_details.get("notification_url") or portal_details.get("pdf_url") or notification_url
        pdf_url = portal_details.get("pdf_url") or pdf_url
        apply_url = portal_details.get("apply_url") or apply_url
        fetched_text = portal_details.get("fetched_text") or fetched_text
        if portal_details.get("vacancies") and not vacancies:
            vacancies = portal_details.get("vacancies")
        if portal_details.get("qualification"):
            qualification = portal_details.get("qualification")
        if portal_details.get("age_limit"):
            age_limit = portal_details.get("age_limit")
        if portal_details.get("application_fee"):
            application_fee = portal_details.get("application_fee")
        if portal_details.get("last_date") and not last_date:
            last_date = portal_details.get("last_date")

    sections_json: Optional[str] = None

    # 3) Direct official source URL (non-aggregator) — extract PDF + dates from HTML
    page_html: Optional[str] = None
    if not is_aggregator_url(source_url):
        page_html = await fetch_page_html(source_url)
        if page_html:
            links = extract_links_from_page(page_html, base_url=source_url)
            pdf_url = pdf_url or links.get("pdf")
            apply_url = apply_url or links.get("apply")
            notification_url = pdf_url or links.get("notification") or notification_url or source_url
            page_text = BeautifulSoup(page_html, "lxml").get_text("\n", strip=True)
            if not last_date:
                last_date = extract_closing_date(page_text) or extract_closing_date(title)
            if not fetched_text and not is_portal_junk_text(page_text):
                fetched_text = await fetch_page_text(source_url)

    notification_url = notification_url or official_base
    apply_url = apply_url or resolve_apply_url(organization, title) or official_base
    if is_pdf_url(apply_url):
        apply_url = resolve_apply_url(organization, title) or official_base
    if is_aggregator_url(notification_url):
        notification_url = official_base
    if is_aggregator_url(apply_url):
        apply_url = official_base

    # Prefer PDF as notification link when available
    if pdf_url and not pdf_url.startswith("pdf://"):
        notification_url = pdf_url

    if fetched_text and (is_portal_junk_text(fetched_text) or is_pdf_binary_text(fetched_text)):
        fetched_text = None

    if not pdf_url and is_pdf_url(notification_url):
        pdf_url = notification_url

    pdf_parsed: dict[str, Any] = {}
    portal_page_title: Optional[str] = None
    if pdf_url:
        pdf_parsed = await enrich_from_notification_pdf(pdf_url, title=title)
        if pdf_parsed.get("last_date") and not last_date:
            last_date = pdf_parsed["last_date"]
        if pdf_parsed.get("qualification") and not qualification:
            qualification = pdf_parsed["qualification"]
        if pdf_parsed.get("total_vacancies") and not vacancies:
            vacancies = pdf_parsed["total_vacancies"]

    if fetched_text:
        portal_page_title = extract_official_title_from_text(fetched_text, title)

    official_title = choose_best_title(
        pdf_parsed.get("official_title"),
        portal_page_title,
        portal_details.get("official_title") if portal_details else None,
        listing_title=title,
        pdf_url=pdf_url or "",
    )

    display_title = official_title or title

    if fetched_text:
        fee_match = re.search(r"(?:application fee|exam fee)[:\s]*([^\n]{5,80})", fetched_text, re.I)
        if fee_match:
            application_fee = fee_match.group(1).strip()
        age_match = re.search(r"(?:age limit|age)[:\s]*(\d{2}[^\n]{0,40})", fetched_text, re.I)
        if age_match:
            age_limit = age_match.group(1).strip()

    sections_json: Optional[str] = None
    if portal_details and portal_details.get("sections_json"):
        sections_json = portal_details["sections_json"]
    elif pdf_url or last_date or is_pdf_url(notification_url):
        adv_no = None
        adv_match = re.search(
            r"(?:advertisement|advt\.?|notice)\s*(?:no\.?|number)?\s*[/\s-]*(\d+/\d{4})",
            display_title,
            re.I,
        )
        if adv_match:
            adv_no = adv_match.group(0).strip()
        sections = build_generic_advertisement_sections(
            title=display_title,
            organization=organization,
            state=state,
            overview=description,
            last_date=last_date,
            pdf_url=pdf_url,
            apply_url=apply_url,
            vacancies=vacancies,
            qualification=qualification,
            age_limit=age_limit,
            application_fee=application_fee,
            advertisement_no=adv_no,
            vacancy_rows=pdf_parsed.get("vacancy_rows"),
            dates=pdf_parsed.get("dates"),
        )
        sections_json = sections_to_json(sections)

    if sections_json:
        full_content = build_full_content(
            title=display_title,
            organization=organization,
            state=state,
            category=category,
            vacancies=vacancies,
            qualification=qualification,
            last_date=last_date,
            exam_date=exam_date,
            description=description,
            fetched_text=None,
            age_limit=age_limit,
            application_fee=application_fee,
            pdf_url=pdf_url,
        )
    else:
        full_content = build_full_content(
            title=display_title,
            organization=organization,
            state=state,
            category=category,
            vacancies=vacancies,
            qualification=qualification,
            last_date=last_date,
            exam_date=exam_date,
            description=description,
            fetched_text=fetched_text,
            age_limit=age_limit,
            application_fee=application_fee,
            pdf_url=pdf_url,
        )

    return {
        "organization": organization,
        "notification_url": notification_url,
        "apply_url": apply_url or notification_url,
        "full_content": full_content,
        "sections_json": sections_json,
        "age_limit": age_limit,
        "application_fee": application_fee,
        "pdf_url": pdf_url,
        "vacancies": vacancies,
        "last_date": last_date,
        "qualification": qualification,
        "official_title": official_title if official_title != title else None,
    }
