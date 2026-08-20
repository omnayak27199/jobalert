from __future__ import annotations

"""Helpers for reading and splitting Hindi (Devanagari) and English text."""

import re
from typing import Optional

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
DEVANAGARI_WORD_RE = re.compile(r"[\u0900-\u097F][\u0900-\u097F\s\-–—/(),.0-9₹]*")

HINDI_JOB_KEYWORDS = (
    "भर्ती",
    "विज्ञापन",
    "अधिसूचना",
    "रिक्त",
    "रिक्ति",
    "पद",
    "आवेदन",
    "अंतिम",
    "तिथि",
    "योग्यता",
    "परीक्षा",
    "नियुक्ति",
    "संविदा",
)

HINDI_ROMAN_ALIASES: dict[str, tuple[str, ...]] = {
    "bharti": ("भर्ती",),
    "vigyapan": ("विज्ञापन",),
    "naukri": ("नौकरी",),
    "recruitment": ("भर्ती", "नियुक्ति"),
    "vacancy": ("रिक्त", "रिक्ति"),
    "notification": ("अधिसूचना", "विज्ञापन"),
    "apply": ("आवेदन",),
    "exam": ("परीक्षा",),
    "qualification": ("योग्यता",),
}


def has_devanagari(text: str) -> bool:
    return bool(text and DEVANAGARI_RE.search(text))


def devanagari_ratio(text: str) -> float:
    if not text:
        return 0.0
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    hindi = sum(1 for c in chars if "\u0900" <= c <= "\u097F")
    return hindi / len(chars)


def split_bilingual_line(line: str) -> tuple[str, str]:
    """Return (english_part, hindi_part) from a mixed line."""
    cleaned = re.sub(r"\s+", " ", (line or "").strip())
    if not cleaned:
        return "", ""

    hindi_chunks = [m.group(0).strip() for m in DEVANAGARI_WORD_RE.finditer(cleaned)]
    hindi = " ".join(hindi_chunks).strip()

    english = cleaned
    for chunk in hindi_chunks:
        english = english.replace(chunk, " ")
    english = re.sub(r"\s+", " ", english).strip(" -–—/|")

    if not english and hindi:
        return hindi, hindi
    return english, hindi


def extract_hindi_title(text: str, max_lines: int = 12) -> Optional[str]:
    """Pick the best Hindi heading line from notification text."""
    if not text:
        return None

    candidates: list[tuple[int, str]] = []
    for i, raw in enumerate(text.split("\n")[:max_lines]):
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 10 or len(line) > 350:
            continue
        if devanagari_ratio(line) < 0.35:
            continue
        score = int(devanagari_ratio(line) * 40)
        if any(kw in line for kw in HINDI_JOB_KEYWORDS):
            score += 25
        if re.search(r"\d+/\d{4}", line):
            score += 8
        if score >= 18:
            candidates.append((score, line))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], -len(item[1])))
    return candidates[0][1][:350]


def extract_hindi_overview(text: str) -> Optional[str]:
    """First substantial Hindi paragraph from body text."""
    if not text:
        return None

    for raw in text.split("\n"):
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 40:
            continue
        if devanagari_ratio(line) >= 0.45:
            return line[:600]
    return None


def contains_hindi_job_keyword(text: str) -> bool:
    if not text:
        return False
    return any(kw in text for kw in HINDI_JOB_KEYWORDS)


def search_variants(query: str) -> list[str]:
    """Expand a search query with Hindi equivalents for common roman terms."""
    variants = [query.strip()]
    if not query.strip():
        return variants

    lower = query.lower()
    for roman, hindi_terms in HINDI_ROMAN_ALIASES.items():
        if roman in lower:
            for term in hindi_terms:
                variants.append(query.lower().replace(roman, term))
                variants.append(term)

    if has_devanagari(query):
        variants.append(query)

    seen: set[str] = set()
    ordered: list[str] = []
    for item in variants:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered.append(item.strip())
    return ordered


def decode_http_text(content: bytes, declared_encoding: Optional[str] = None) -> str:
    """Decode HTTP body bytes with UTF-8 fallback and charset sniffing."""
    if not content:
        return ""

    for encoding in (declared_encoding, "utf-8", "utf-8-sig", "cp1252", "latin-1"):
        if not encoding:
            continue
        try:
            text = content.decode(encoding, errors="strict")
            if encoding.lower() in {"latin-1", "cp1252"} and "charset=utf-8" in text[:500].lower():
                return content.decode("utf-8", errors="replace")
            return text
        except (UnicodeDecodeError, LookupError):
            continue

    sniff = content[:4096].decode("latin-1", errors="ignore")
    meta = re.search(r'charset=["\']?([\w\-]+)', sniff, re.I)
    if meta:
        try:
            return content.decode(meta.group(1), errors="replace")
        except LookupError:
            pass
    return content.decode("utf-8", errors="replace")
