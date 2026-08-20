from __future__ import annotations

"""Parse official recruitment HTML pages (job link viewer) into structured fields."""

import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.bilingual_text import decode_http_text

from app.services.advertisement_text_parser import enrich_from_full_text
from app.services.detail_fetcher import extract_closing_date, extract_links_from_page, is_pdf_url
from app.services.notification_pdf_parser import extract_application_dates, infer_post_label
from app.services.official_title import extract_official_title_from_text

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaJobBot/1.0; +https://indiajob.in/bot)"


def fetch_portal_html(url: str) -> Optional[str]:
    if not url or is_pdf_url(url):
        return None
    try:
        with httpx.Client(timeout=25.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return None
            if "application/pdf" in resp.headers.get("content-type", "").lower():
                return None
            return decode_http_text(resp.content, resp.encoding)
    except Exception as exc:
        logger.debug("Portal fetch failed %s: %s", url, exc)
        return None


def parse_portal_advertisement_page(url: str, title: str = "", organization: str = "") -> dict[str, Any]:
    """Extract PDF link, apply link, dates and hints from an official notification HTML page."""
    result: dict[str, Any] = {
        "pdf_url": None,
        "apply_url": None,
        "dates": [],
        "opening_date": None,
        "last_date": None,
        "qualification": None,
        "application_fee": None,
        "advertisement_no": None,
    }

    html = fetch_portal_html(url)
    if not html:
        return result

    links = extract_links_from_page(html, base_url=url)
    if links.get("pdf"):
        result["pdf_url"] = links["pdf"]
    if links.get("apply"):
        result["apply_url"] = links["apply"]

    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    page_title = extract_official_title_from_html(html, title)
    if page_title:
        result["official_title"] = page_title

    dates = extract_application_dates(text)
    if not dates:
        closing = extract_closing_date(text) or extract_closing_date(title)
        if closing:
            dates = [{"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": closing}]

    result["dates"] = dates
    for d in dates:
        label = d.get("label", "").lower()
        if "start" in label or "opening" in label:
            result["opening_date"] = d.get("date")
        if "last" in label:
            result["last_date"] = d.get("date")

    adv_match = re.search(
        r"(?:advertisement|advt\.?|notice|विज्ञापन|अधिसूचना)\s*(?:no\.?|number|सं\.?)?\s*[/\s.-]*\d+/\d{4}",
        text[:3000],
        re.I,
    )
    if adv_match:
        result["advertisement_no"] = adv_match.group(0).strip()

    fee_match = re.search(r"(?:application fee|exam fee)[:\s]*([^\n]{5,80})", text, re.I)
    if fee_match:
        result["application_fee"] = fee_match.group(1).strip()

    qual_match = re.search(r"(?:qualification|essential qualification)[:\s]*([^\n]{15,200})", text, re.I)
    if qual_match:
        result["qualification"] = qual_match.group(1).strip()

    age_match = re.search(r"age\s+limit[^:\n]{0,20}:\s*([^\n]{5,80})", text, re.I)
    if age_match:
        result["age_limit"] = age_match.group(1).strip()

    document_links: list[tuple[str, str]] = []
    if result.get("pdf_url"):
        document_links.append(("Official Notification PDF", result["pdf_url"]))
    if result.get("apply_url"):
        document_links.append(("Apply Online", result["apply_url"]))

    soup_links = BeautifulSoup(html, "lxml")
    for a in soup_links.select("a[href]"):
        href = a.get("href", "")
        if not href or href.startswith("javascript:"):
            continue
        full = urljoin(url, href)
        label = a.get_text(strip=True) or "Document"
        lower = label.lower()
        if any(kw in lower for kw in ("syllabus", "exam pattern", "admit", "answer key", "detailed adv")):
            document_links.append((label[:80], full))

    text_enriched = enrich_from_full_text(
        text,
        vacancy_rows=result.get("vacancy_rows"),
        document_links=document_links,
        existing_dates=result.get("dates"),
    )
    for key, val in text_enriched.items():
        if val is None or val == [] or val == "":
            continue
        if key in ("vacancy_rows", "dates") and result.get(key):
            result[key] = val
        elif key not in result:
            result[key] = val
        elif isinstance(val, str) and len(val) > len(str(result.get(key, ""))):
            result[key] = val
        elif isinstance(val, list) and len(val) > len(result.get(key) or []):
            result[key] = val

    if not result["pdf_url"]:
        soup = BeautifulSoup(html, "lxml")
        best_pdf: str | None = None
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if not href or href.startswith("javascript:"):
                continue
            full = urljoin(url, href)
            if not (is_pdf_url(full) or ".pdf" in full.lower()):
                continue
            label = a.get_text(strip=True).lower()
            if any(kw in label for kw in ("advertisement", "notification", "vacancy", "detailed", "advt")):
                best_pdf = full
                break
            best_pdf = best_pdf or full
        result["pdf_url"] = best_pdf

    post = infer_post_label(title, organization)
    if post and not post.endswith("See Official Notification"):
        result.setdefault("vacancy_rows", [
            {
                "sr": "01",
                "post": post,
                "vacancies": 0,
                "pay_level": "—",
                "pay_scale": "",
                "qualification": result.get("qualification") or "",
            }
        ])

    return result


def extract_official_title_from_html(html: str, fallback: str = "") -> Optional[str]:
    """Extract heading from official notification HTML page."""
    soup = BeautifulSoup(html, "lxml")
    selectors = (
        "h1",
        "h2",
        ".page-title",
        ".notification-title",
        ".content-title",
        "#ContentPlaceHolder1_lblTitle",
        "#lblTitle",
        ".subject",
        "td.subject",
    )
    for selector in selectors:
        el = soup.select_one(selector)
        if not el:
            continue
        text = el.get_text(" ", strip=True)
        if len(text) >= 15:
            return text[:350]
    body = soup.get_text("\n", strip=True)
    return extract_official_title_from_text(body, fallback)


def merge_enrichment(*sources: dict[str, Any]) -> dict[str, Any]:
    """Merge PDF + portal parse results — prefer richer data."""
    merged: dict[str, Any] = {}
    for src in sources:
        if not src:
            continue
        for key, val in src.items():
            if val is None or val == [] or val == "":
                continue
            if key == "vacancy_rows" and merged.get("vacancy_rows"):
                if len(val) > len(merged["vacancy_rows"]):
                    merged[key] = val
            elif key == "dates" and merged.get("dates"):
                if len(val) > len(merged["dates"]):
                    merged[key] = val
            elif key in ("vacancy_rows", "dates", "eligibility_rows", "selection_steps", "reservation", "special_notes", "application_fee_rows"):
                if isinstance(val, list) and len(val) > len(merged.get(key) or []):
                    merged[key] = val
            elif key == "official_title":
                if val and (not merged.get(key) or len(str(val)) > len(str(merged.get(key, "")))):
                    merged[key] = val
            elif key in merged and isinstance(val, str) and len(val) > len(str(merged[key])):
                merged[key] = val
            elif key not in merged:
                merged[key] = val
    return merged
