from __future__ import annotations

"""Extract official notification headings from PDF/HTML text."""

import re
from typing import Optional

from app.services.bilingual_text import contains_hindi_job_keyword, devanagari_ratio

from app.services.content_quality import is_generic_title, title_from_pdf_filename
from app.services.job_quality import is_junk_title

HEADING_KEYWORDS = (
    "recruitment",
    "notification",
    "advertisement",
    "advt",
    "vacancy",
    "vacancies",
    "corrigendum",
    "invitation",
    "engagement",
    "appointment",
    "post of",
    "posts of",
    "bharti",
    "niyukti",
    "vigyapan",
    "अधिसूचना",
    "विज्ञापन",
    "भर्ती",
)

FILENAME_SLUG = re.compile(r"^(?:advt|notification|recruit|vacancy)[_\-\s\d]+", re.I)


def normalize_listing_title(title: str) -> str:
    """Clean listing-page anchor/row text before storing."""
    cleaned = re.sub(r"\s+", " ", title or "").strip()
    if not cleaned:
        return cleaned
    cleaned = re.sub(r"^(?:sr\.?\s*no\.?\s*)?\d+[\.\):\-]\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\s*", "", cleaned)
    cleaned = re.sub(
        r"\s*(?:download\s*(?:pdf)?|view\s*(?:pdf|details)?|click here|read more)\s*$",
        "",
        cleaned,
        flags=re.I,
    )
    return cleaned[:350]


def _line_heading_score(line: str, index: int) -> int:
    if len(line) < 12 or len(line) > 400:
        return -100
    lower = line.lower()
    if line.startswith("http") or "www." in lower:
        return -100
    if re.match(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$", line):
        return -100
    if any(kw in lower for kw in ("application fee", "signature", "email:", "phone:", "fax:")):
        return -30

    score = max(0, 12 - index)
    if line.isupper() and len(line) > 18:
        score += 18
    if re.search(r"(?:advt\.?|advertisement|notice)\s*(?:no\.?|number)?", lower):
        score += 22
    if any(kw in lower for kw in HEADING_KEYWORDS):
        score += 28
    if is_generic_title(line):
        score -= 40
    if contains_hindi_job_keyword(line):
        score += 20
    if devanagari_ratio(line) >= 0.4:
        score += 15
    if "post of" in lower or "posts of" in lower:
        score += 12
    if re.search(r"\b20\d{2}\b", line):
        score += 4
    if re.search(r"\d+/\d{4}", line):
        score += 8
    return score


def extract_official_title_from_text(text: str, fallback: str = "") -> Optional[str]:
    """Best-effort official heading from PDF/HTML body text."""
    if not text or len(text.strip()) < 20:
        return normalize_listing_title(fallback) or fallback or None

    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n") if ln.strip()]
    candidates: list[tuple[int, str]] = []

    for i, line in enumerate(lines[:30]):
        score = _line_heading_score(line, i)
        if score >= 18:
            candidates.append((score, line))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], -len(item[1])))
        best = candidates[0][1]
        try:
            idx = lines.index(best)
        except ValueError:
            idx = -1
        if idx >= 0 and idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if (
                10 < len(nxt) < 220
                and _line_heading_score(nxt, idx + 1) >= 10
                and not nxt.endswith(".")
            ):
                best = f"{best} {nxt}"[:350]
        return best[:350]

    merged: list[str] = []
    for line in lines[:8]:
        if 12 <= len(line) <= 220 and _line_heading_score(line, len(merged)) >= 8:
            merged.append(line)
        if len(" ".join(merged)) > 45:
            break
    if merged:
        return " ".join(merged)[:350]

    cleaned = normalize_listing_title(fallback)
    return cleaned or None


def extract_pdf_metadata_title(data: bytes) -> Optional[str]:
    from io import BytesIO

    try:
        import pdfplumber

        with pdfplumber.open(BytesIO(data)) as pdf:
            meta = pdf.metadata or {}
            raw = meta.get("Title") or meta.get("title")
            if raw:
                title = re.sub(r"\s+", " ", str(raw)).strip()
                if len(title) > 12 and "untitled" not in title.lower():
                    return title[:350]
    except Exception:
        pass
    return None


def title_quality_score(title: str, listing_title: str = "") -> int:
    if not title or is_junk_title(title):
        return -100
    if is_generic_title(title):
        return -80
    lower = title.lower()
    score = min(len(title) // 8, 25)
    if any(kw in lower for kw in HEADING_KEYWORDS):
        score += 35
    if re.search(r"\d+/\d{4}", title):
        score += 12
    if "post of" in lower:
        score += 10
    if listing_title and len(title) > len(listing_title) + 8:
        score += 15
    if FILENAME_SLUG.match(title.replace(" ", "_")):
        score -= 30
    if title.count("_") >= 3:
        score -= 20
    if listing_title and title.strip().lower() == listing_title.strip().lower():
        score += 5
    return score


def choose_best_title(*candidates: Optional[str], listing_title: str = "", pdf_url: str = "") -> str:
    """Pick the most official-looking title from PDF/HTML/listing sources."""
    listing = normalize_listing_title(listing_title) or listing_title
    best = listing
    best_score = title_quality_score(listing, listing)

    filename_title = title_from_pdf_filename(pdf_url) if pdf_url else None
    if filename_title:
        candidates = (filename_title, *candidates)

    for candidate in candidates:
        if not candidate:
            continue
        cleaned = re.sub(r"\s+", " ", candidate).strip()
        if len(cleaned) < 10:
            continue
        if is_generic_title(cleaned):
            continue
        score = title_quality_score(cleaned, listing)
        if score > best_score:
            best_score = score
            best = cleaned

    if is_generic_title(best) and filename_title:
        return filename_title[:350]

    return best[:350]
