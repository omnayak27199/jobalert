from __future__ import annotations

"""Fetch recruitment details from official government portals."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.services.official_urls import is_aggregator_url
from app.services.recruitment_content import (
    build_advertisement_sections,
    build_structured_full_content,
    get_post_structured_content,
    sections_to_json,
    structured_job_fields,
)

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaJobBot/1.0; +https://indiajob.in/bot)"

CG_VYAPAM_HOME = "https://vyapamcg.cgstate.gov.in"
CG_VYAPAM_APPLY = "https://vyapamprofile.cgstate.gov.in/online/"

# Known Vyapam post pages by title keywords
VYAPAM_TITLE_POSTS: list[tuple[str, str]] = [
    ("nssk26", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("various posts", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("store keeper", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("mechanic", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("fire men", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("fireman", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("driver", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("station officer", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("watchroom", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
    ("wireless operator", "https://vyapamcg.cgstate.gov.in/Post?PostID=NSSK26ONLINE"),
]


def resolve_vyapam_post_url(title: str) -> Optional[str]:
    t = title.lower()
    for keyword, url in VYAPAM_TITLE_POSTS:
        if keyword in t:
            return url
    return None


def _normalize_href(base: str, href: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(base + "/", href.lstrip("/"))


def _title_tokens(title: str) -> set[str]:
    stop = {"online", "form", "recruitment", "notification", "apply", "posts", "post", "various", "2026", "2025"}
    tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    return tokens - stop


def _score_link(title: str, link_text: str, href: str) -> int:
    tokens = _title_tokens(title)
    combined = f"{link_text} {href}".lower()
    score = 0
    for token in tokens:
        if len(token) >= 3 and token in combined:
            score += 2
    if href.lower().endswith(".pdf"):
        score += 3
    if any(kw in combined for kw in ["recruitment", "notification", "advertisement", "vacancy", "apply", "bharti", "store", "keeper", "teacher", "assistant"]):
        score += 2
    if any(kw in combined for kw in ["certificate", "result", "admit", "answer key", "model answer", "e-cert"]):
        score -= 4
    return score


async def parse_cg_vyapam_post(post_url: str) -> dict[str, Optional[str]]:
    """Fetch a CG Vyapam Post?PostID= page and extract PDFs + details."""
    result: dict[str, Optional[str]] = {
        "notification_url": None,
        "pdf_url": None,
        "apply_url": CG_VYAPAM_APPLY,
        "fetched_text": None,
    }
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(post_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return result

            soup = BeautifulSoup(resp.text, "lxml")
            content = soup.select_one(".post-content") or soup.select_one("article .post-content")
            if not content:
                return result
            scope = content

            pdf_links: list[tuple[str, str]] = []
            for link in scope.select("a[href]"):
                href = link.get("href", "")
                text = link.get_text(" ", strip=True)
                if not href:
                    continue
                full = _normalize_href(CG_VYAPAM_HOME, href)
                if "apply" in text.lower() or "online application" in text.lower():
                    result["apply_url"] = full if full.startswith("http") else CG_VYAPAM_APPLY
                if ".pdf" in full.lower() or "/uploads/" in full.lower():
                    pdf_links.append((text, full))

            # Prefer detailed advertisement PDF
            for prefer in ["vistrit vigyapan", "vigyapan", "advertisement", "notification"]:
                for text, full in pdf_links:
                    if prefer in text.lower():
                        result["pdf_url"] = full
                        result["notification_url"] = full
                        break
                if result["pdf_url"]:
                    break
            if not result["pdf_url"] and pdf_links:
                result["pdf_url"] = pdf_links[0][1]
                result["notification_url"] = pdf_links[0][1]

            lines = [ln.strip() for ln in scope.get_text("\n", strip=True).split("\n") if len(ln.strip()) > 2]
            body = "\n".join(lines[:60])
            pdf_lines = "\n".join(f"- {text}: {url}" for text, url in pdf_links[:8])
            result["fetched_text"] = f"{body}\n\n### Official Documents\n{pdf_lines}" if pdf_lines else body

            post_id = ""
            if "PostID=" in post_url:
                post_id = post_url.split("PostID=")[-1].split("&")[0]
            structured = get_post_structured_content(post_id)
            if structured:
                sections = build_advertisement_sections(structured, pdf_links)
                result["sections_json"] = sections_to_json(sections)
                result["fetched_text"] = build_structured_full_content(structured, pdf_links)
                fields = structured_job_fields(structured)
                result["vacancies"] = fields.get("vacancies")
                result["last_date"] = fields.get("last_date")
                result["organization"] = fields.get("organization")
                result["qualification"] = fields.get("qualification")
                result["age_limit"] = fields.get("age_limit")
                result["application_fee"] = fields.get("application_fee")
                return result
    except Exception as e:
        logger.warning("CG Vyapam post parse failed: %s", e)
    return result


async def fetch_cg_vyapam_details(title: str, post_url: Optional[str] = None) -> dict[str, Optional[str]]:
    """Match CG Vyapam recruitment on official portal and return PDF/apply links."""
    result: dict[str, Optional[str]] = {
        "organization": "CG Vyapam (CGSSB)",
        "notification_url": None,
        "apply_url": CG_VYAPAM_APPLY,
        "fetched_text": None,
        "pdf_url": None,
    }

    if post_url and "vyapamcg.cgstate.gov.in" in post_url.lower():
        parsed = await parse_cg_vyapam_post(post_url)
        result.update({k: v for k, v in parsed.items() if v})
        if result.get("pdf_url"):
            return result

    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(CG_VYAPAM_HOME, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return result

            soup = BeautifulSoup(resp.text, "lxml")
            best_pdf: tuple[int, str, str] | None = None

            for link in soup.select("a[href]"):
                href = link.get("href", "")
                text = link.get_text(" ", strip=True)
                if not href or is_aggregator_url(href):
                    continue
                full_url = _normalize_href(CG_VYAPAM_HOME, href)
                score = _score_link(title, text, full_url)
                if score <= 0:
                    continue
                if full_url.lower().endswith(".pdf") and (not best_pdf or score > best_pdf[0]):
                    best_pdf = (score, full_url, text)

            if best_pdf:
                result["pdf_url"] = best_pdf[1]
                result["notification_url"] = best_pdf[1]
                pdf_text = await _fetch_pdf_context(client, best_pdf[1])
                if pdf_text:
                    result["fetched_text"] = pdf_text
                else:
                    result["fetched_text"] = f"Official notification: {best_pdf[2]}\nPDF: {best_pdf[1]}"
            else:
                result["notification_url"] = CG_VYAPAM_HOME
                result["fetched_text"] = await _fetch_page_text(client, CG_VYAPAM_HOME)

    except Exception as e:
        logger.warning("CG Vyapam fetch failed: %s", e)

    return result


async def _fetch_page_text(client: httpx.AsyncClient, url: str, max_chars: int = 5000) -> Optional[str]:
    try:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        lines = [ln.strip() for ln in soup.get_text("\n", strip=True).split("\n") if len(ln.strip()) > 3]
        return "\n".join(lines[:100])[:max_chars]
    except Exception:
        return None


async def _fetch_pdf_context(client: httpx.AsyncClient, pdf_url: str) -> Optional[str]:
    """Best-effort: fetch PDF page listing context; full PDF parsing is optional."""
    # Many vyapam PDFs are direct downloads — return link summary for on-site display.
    return f"Official recruitment notification PDF published on CG Vyapam portal.\nDownload: {pdf_url}"


async def fetch_official_portal_details(
    organization: str,
    title: str,
    post_url: Optional[str] = None,
) -> Optional[dict[str, Optional[str]]]:
    """Route to organization-specific official portal fetchers."""
    combined = f"{organization} {title}".lower()
    if "vyapam" in combined or "cgssb" in combined:
        return await fetch_cg_vyapam_details(title, post_url=post_url)
    return None
