from __future__ import annotations

"""Detect garbled OCR/PDF text and validate parsed recruitment fields."""

import re
from typing import Any, Optional
from urllib.parse import unquote

from app.services.bilingual_text import devanagari_ratio, has_devanagari

# Characters that dominate in broken PDF font-map extractions
_GARBLED_CHAR_RE = re.compile(r"[^\w\s\-–—/(),.\u0900-\u097F₹°:;+%'\"]")
_SPECIAL_CHAR_RE = re.compile(r"[\^*<>|~`@#\\={}\[\]]")

_GENERIC_TITLES = frozenset(
    {
        "advertisement",
        "notification",
        "recruitment",
        "vacancy",
        "vacancies",
        "official notification pdf",
        "apply online",
        "download pdf",
        "advertisement notification",
        "recruitment notification",
        "recruitment notice",
        "job notification",
        "current vacancies",
        "archived vacancies",
    }
)

_GENERIC_TITLE_WORDS = frozenset(
    {
        "advertisement",
        "notification",
        "recruitment",
        "vacancy",
        "vacancies",
        "official",
        "pdf",
        "download",
        "dated",
        "no",
        "number",
        "advt",
        "notice",
        "online",
        "form",
        "apply",
    }
)

_QUALIFICATION_KEYWORDS = (
    "graduate",
    "graduation",
    "degree",
    "diploma",
    "bachelor",
    "master",
    "doctorate",
    "ph.d",
    "phd",
    "md",
    "ms",
    "dnb",
    "dm",
    "m.ch",
    "mch",
    "iti",
    "10+2",
    "12th",
    "10th",
    "matric",
    "intermediate",
    "engineering",
    "mbbs",
    "b.ed",
    "bed",
    "b.tech",
    "btech",
    "m.tech",
    "mtech",
    "experience",
    "recognised",
    "recognized",
    "university",
    "institute",
    "concerned",
    "speciality",
    "specialty",
    "post graduate",
    "postgraduate",
    "स्नातक",
    "स्नातकोत्तर",
    "योग्यता",
    "डिग्री",
    "पद",
)

_POST_KEYWORDS = (
    "professor",
    "lecturer",
    "assistant",
    "officer",
    "clerk",
    "teacher",
    "engineer",
    "manager",
    "driver",
    "constable",
    "inspector",
    "supervisor",
    "technician",
    "operator",
    "assistant",
    "director",
    "scientist",
    "nurse",
    "doctor",
    "professor",
    "fireman",
    "store",
    "keeper",
    "medical",
    "assistant professor",
    "prof",
)


def text_quality_score(text: str) -> float:
    """Return 0.0 (garbled) to 1.0 (clean readable text)."""
    if not text:
        return 0.0

    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) < 5:
        return 0.0

    chars = [c for c in cleaned if not c.isspace()]
    if not chars:
        return 0.0

    ok_chars = sum(
        1
        for c in chars
        if c.isalnum() or c in " -–—/(),.₹°:;+%'\""
    )
    ok_ratio = ok_chars / len(chars)

    special_count = len(_SPECIAL_CHAR_RE.findall(cleaned))
    special_ratio = special_count / max(len(cleaned), 1)
    if special_ratio > 0.02:
        ok_ratio *= max(0.0, 1.0 - special_ratio * 8)

    tokens = re.findall(r"\S+", cleaned)
    if not tokens:
        return 0.0

    readable = 0
    for token in tokens:
        token_clean = re.sub(r"[^\w\u0900-\u097F]", "", token)
        if len(token_clean) < 3:
            continue
        if has_devanagari(token_clean) and devanagari_ratio(token_clean) >= 0.5:
            readable += 1
        elif re.search(r"[aeiouAEIOU]", token_clean) and sum(c.isalpha() for c in token_clean) >= 3:
            readable += 1
        elif token_clean.upper() in {"MD", "MS", "DNB", "DM", "ITI", "MBBS", "B.TECH", "M.TECH", "PHD"}:
            readable += 1

    word_ratio = readable / max(len(tokens), 1)

    lower = cleaned.lower()
    if any(kw in lower for kw in _QUALIFICATION_KEYWORDS):
        word_ratio = min(1.0, word_ratio + 0.15)
    if any(kw in lower for kw in _POST_KEYWORDS):
        word_ratio = min(1.0, word_ratio + 0.1)

    score = min(1.0, ok_ratio * 0.55 + word_ratio * 0.45)
    if special_ratio > 0.04:
        score *= max(0.2, 1.0 - special_ratio * 3)

    caret_ratio = cleaned.count("^") / max(len(cleaned), 1)
    if caret_ratio > 0.005:
        score *= max(0.15, 1.0 - caret_ratio * 20)

    return score


def is_garbled_text(text: str, threshold: float = 0.52) -> bool:
    return text_quality_score(text) < threshold


def document_text_is_usable(text: str) -> bool:
    """Check whether an entire PDF text extraction is readable enough to parse."""
    if not text or len(text.strip()) < 40:
        return False
    if is_garbled_text(text, threshold=0.62):
        return False
    sample = text[:8000]
    lines = [ln.strip() for ln in sample.split("\n") if ln.strip()]
    if not lines:
        return False
    good_lines = sum(1 for ln in lines[:40] if not is_garbled_text(ln, threshold=0.58))
    return good_lines >= max(3, len(lines[:40]) // 4)


def is_plausible_qualification(text: str) -> bool:
    if not text or len(text.strip()) < 8:
        return False
    cleaned = re.sub(r"\s+", " ", text.strip())
    if is_garbled_text(cleaned, threshold=0.55):
        return False
    if len(_SPECIAL_CHAR_RE.findall(cleaned)) >= 2:
        return False
    lower = cleaned.lower()
    if any(kw in lower for kw in _QUALIFICATION_KEYWORDS):
        return text_quality_score(cleaned) >= 0.45
    if re.search(r"\b\d{1,2}\s*\+\s*\d\b", cleaned):
        return True
    if has_devanagari(cleaned) and devanagari_ratio(cleaned) >= 0.25:
        return text_quality_score(cleaned) >= 0.55
    return False


def is_plausible_post_name(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    cleaned = re.sub(r"\s+", " ", text.strip())
    if is_generic_title(cleaned):
        return False
    if is_garbled_text(cleaned, threshold=0.55):
        return False
    if len(_SPECIAL_CHAR_RE.findall(cleaned)) >= 1:
        return False
    if re.search(r"[):]{1,2}\s*-", cleaned):
        return False
    lower = cleaned.lower()
    if any(w in lower for w in ("graduate", "qualification", "degree", "diploma", "bachelor", "dnb", "md/", "ms/")):
        if not any(kw in lower for kw in _POST_KEYWORDS):
            return False
    if any(kw in lower for kw in _POST_KEYWORDS):
        return text_quality_score(cleaned) >= 0.45
    if has_devanagari(cleaned):
        return text_quality_score(cleaned) >= 0.55
    if not re.match(r"[A-Z\u0900-\u097F]", cleaned):
        return False
    alpha = sum(c.isalpha() for c in cleaned)
    return alpha >= 5 and text_quality_score(cleaned) >= 0.58


def is_plausible_eligibility_row(row: dict[str, Any]) -> bool:
    post = str(row.get("post") or "").strip()
    education = str(row.get("education") or "").strip()
    if not education or len(education) < 8:
        return False
    if not is_plausible_qualification(education):
        return False
    if not post:
        return True
    return is_plausible_post_name(post)


def filter_eligibility_rows(rows: Optional[list[dict[str, Any]]]) -> list[dict[str, str]]:
    if not rows:
        return []
    filtered: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned = {
            "post": str(row.get("post") or "").strip()[:120],
            "education": str(row.get("education") or "").strip()[:250],
            "experience": str(row.get("experience") or "As per notification").strip()[:120],
            "other": str(row.get("other") or "").strip()[:120],
        }
        if not is_plausible_post_name(cleaned["post"]) and is_plausible_qualification(cleaned["education"]):
            cleaned["post"] = "All posts"
        elif is_generic_title(cleaned["post"]):
            cleaned["post"] = "All posts"
        if is_plausible_eligibility_row(cleaned):
            filtered.append(cleaned)
    return _dedupe_eligibility_rows(filtered)


def _dedupe_eligibility_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = row["education"].lower()[:40]
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique[:20]


def filter_fee_rows(rows: Optional[list[tuple[str, str]]]) -> list[tuple[str, str]]:
    if not rows:
        return []
    filtered: list[tuple[str, str]] = []
    for item in rows:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        label, fee = str(item[0]).strip(), str(item[1]).strip()
        if not fee:
            continue
        if is_garbled_text(label, threshold=0.3):
            continue
        if re.search(r"[\[\]{}]", label):
            continue
        filtered.append((label[:100], fee[:80]))
    return filtered[:8]


def filter_vacancy_rows(rows: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        post = str(row.get("post") or "").strip()
        if post and not is_plausible_post_name(post):
            if is_generic_title(post):
                continue
            if is_garbled_text(post, threshold=0.35):
                continue
        qual = str(row.get("qualification") or "").strip()
        if qual and not is_plausible_qualification(qual):
            row = dict(row)
            row["qualification"] = ""
        filtered.append(row)
    return filtered


def is_generic_title(title: str) -> bool:
    cleaned = re.sub(r"\s+", " ", (title or "").strip().lower())
    if not cleaned:
        return True
    if cleaned in _GENERIC_TITLES:
        return True
    words = cleaned.split()
    if len(words) == 1 and words[0] in _GENERIC_TITLE_WORDS:
        return True
    if len(words) <= 4 and all(
        w in _GENERIC_TITLE_WORDS or re.fullmatch(r"\d{1,4}[/\-]?\d{0,4}", w)
        for w in words
    ):
        return True
    if cleaned.startswith("advertisement") and len(words) <= 3:
        return True
    return False


def title_from_pdf_filename(url_or_name: str) -> Optional[str]:
    """Derive a readable title from a notification PDF filename."""
    name = unquote((url_or_name or "").split("/")[-1].split("?")[0])
    name = re.sub(r"\.pdf$", "", name, flags=re.I).strip()
    if not name:
        return None

    name = re.sub(r"\(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\)", " ", name)
    name = re.sub(r"[_-]+(?:advertisement|notification|advt|notice|recruitment)\b.*$", "", name, flags=re.I)
    name = name.replace("_(", " (").replace(")_", ") ").replace("_)", ")")
    name = re.sub(r"_+\(", " (", name)
    name = re.sub(r"\)_+", ") ", name)
    name = re.sub(r"[_]+", " ", name)
    name = re.sub(r"-(20\d{2})\b", r" \1", name)
    name = re.sub(r"\(\s*\)", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -–—/)")

    year_match = re.search(r"\b(20\d{2})\b", name)
    year = year_match.group(1) if year_match else ""
    name = re.sub(r"\b20\d{2}\b", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    if not name or len(name) < 4:
        return None

    words: list[str] = []
    for raw in name.split():
        token = raw.strip("()")
        if not token:
            continue
        upper = token.upper()
        if upper in {"MD", "MS", "DNB", "DM", "ITI", "MBBS", "SC", "ST", "OBC", "UR", "EWS", "PHD", "B.ED", "M.ED"}:
            words.append(upper.replace(".", ""))
        elif len(token) <= 4 and token.isupper():
            words.append(token)
        elif token.isupper() and len(token) > 4:
            words.append(token.title())
        else:
            words.append(token.replace("_", " ").title())

    title = " ".join(words).strip()
    if year and year not in title:
        title = f"{title} {year}".strip()
    lower = title.lower()
    if "recruitment" not in lower and "bharti" not in lower and "vacancy" not in lower:
        title = f"{title} Recruitment"

    if len(title) >= 12 and not is_generic_title(title):
        return title[:350]
    return None


def sections_have_garbled_content(sections: dict[str, Any]) -> bool:
    """True when cached sections contain obvious OCR garbage."""
    if not sections:
        return True

    title = str(sections.get("title") or "")
    if is_generic_title(title):
        return True

    elig = sections.get("eligibility_rows") or []
    if elig:
        valid = filter_eligibility_rows(elig)
        if len(valid) < max(1, len(elig) // 2):
            return True

    for row in sections.get("vacancy_rows") or []:
        post = str(row.get("post") or "")
        if post and is_garbled_text(post, threshold=0.35):
            return True
        if post and is_generic_title(post) and len(sections.get("vacancy_rows") or []) <= 2:
            return True

    qual = str(sections.get("qualification") or sections.get("qualification_summary") or "")
    if qual and not is_plausible_qualification(qual):
        return True

    fee_rows = sections.get("application_fee_rows") or []
    if fee_rows and not filter_fee_rows(fee_rows):
        return True

    return False
