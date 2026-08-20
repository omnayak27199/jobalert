from __future__ import annotations

"""Extract vacancy / category tables from PDF pages and OCR text."""

import re
from io import BytesIO
from typing import Any, Optional

import pdfplumber

_TABLE_SETTINGS = [
    {
        "vertical_strategy": "lines_strict",
        "horizontal_strategy": "lines_strict",
        "intersection_tolerance": 8,
        "snap_tolerance": 4,
    },
    {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "intersection_tolerance": 10,
    },
    {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "min_words_vertical": 3,
        "min_words_horizontal": 2,
    },
]


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def extract_pdf_tables(data: bytes, max_pages: int = 40) -> list[list[list[Any]]]:
    """Return raw tables from all pages using multiple pdfplumber strategies."""
    found: list[list[list[Any]]] = []
    seen: set[str] = set()

    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages[:max_pages]:
            for settings in _TABLE_SETTINGS:
                try:
                    tables = page.extract_tables(table_settings=settings) or []
                except Exception:
                    continue
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    key = "|".join(_clean_cell(c) for c in table[0][:4])
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(table)
    return found


def extract_category_rows_from_text(text: str, post_name: str = "") -> list[dict[str, Any]]:
    """Parse category-wise vacancy rows from plain notification text."""
    rows: list[dict[str, Any]] = []
    if not text:
        return rows

    header = re.search(
        r"(?i)(?:category\s+wise|category[\-\s]wise|post\s+wise|vacancy\s+details|"
        r"श्रेणीवार|श्रेणी[\-\s]वार|आरक्षण\s*वर्ग)",
        text,
    )
    block = text[header.start() : header.start() + 4000] if header else text[:6000]

    # Pattern: Category name ... number
    patterns = [
        r"(?i)(Un[\-\s]?reserved|UR|General|SC|ST|OBC|BC[\-\s]?A|BC[\-\s]?B|EWS|ESM|PwBD|PWD|OSC|DSC|Women|Ex[\-\s]?Servicemen)[^\n\d]{0,40}?(\d{1,4})\b",
        r"(?i)(अन\s*आरक्षित|सामान्य|अनु\s*सूचित\s*जाति|अनु\s*सूचित\s*जन\s*जाति)[^\n\d]{0,40}?(\d{1,4})\b",
    ]
    seen: set[str] = set()
    sr = 0
    for pattern in patterns:
        for match in re.finditer(pattern, block):
            label = re.sub(r"\s+", " ", match.group(1)).strip()
            count = int(match.group(2))
            if count <= 0 or count > 5000:
                continue
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            sr += 1
            post = f"{post_name[:80]} — {label}" if post_name else label
            rows.append(
                {
                    "sr": f"{sr:02d}",
                    "post": post[:160],
                    "vacancies": count,
                    "pay_level": "",
                    "pay_scale": "",
                    "qualification": "",
                }
            )

    # Number line after category header (HPSC style)
    nums_match = re.search(r"(?i)category\s+wise[\s\S]{0,800}?\n([^\n]{10,120})\n", block)
    if nums_match and len(rows) < 3:
        nums = [int(n) for n in re.findall(r"\b(\d{1,3})\b", nums_match.group(1))]
        if 4 <= len(nums) <= 15:
            labels = ["UR", "SC", "BC-A", "BC-B", "EWS", "ESM", "PwBD", "OSC", "DSC"]
            for i, count in enumerate(nums):
                if count <= 0 or i >= len(labels):
                    continue
                sr += 1
                rows.append(
                    {
                        "sr": f"{sr:02d}",
                        "post": f"{post_name[:80]} — {labels[i]}" if post_name else labels[i],
                        "vacancies": count,
                        "pay_level": "",
                        "pay_scale": "",
                        "qualification": "",
                    }
                )

    return rows[:25]


def extract_post_table_from_text(text: str) -> list[dict[str, Any]]:
    """Extract multi-post rows from text lines (Post | Code | Vacancies | Pay)."""
    rows: list[dict[str, Any]] = []
    if not text:
        return rows

    line_pattern = re.compile(
        r"(?i)^\s*(\d{1,2})[\.\)]?\s+(.{8,100}?)\s+(\d{1,4})\s+(?:Level[\-\s]*(\d+)[^\n]{0,40})?(₹[\d,\s\-–]+|Rs\.?\s*[\d,\s\-–]+)?",
        re.M,
    )
    sr = 0
    for match in line_pattern.finditer(text):
        post = re.sub(r"\s+", " ", match.group(2)).strip(" .")
        vac = int(match.group(3))
        if vac <= 0 or vac > 10000:
            continue
        sr += 1
        level = f"Level-{match.group(4)}" if match.group(4) else ""
        pay = (match.group(5) or "").strip()
        rows.append(
            {
                "sr": f"{sr:02d}",
                "post": post[:160],
                "vacancies": vac,
                "pay_level": level,
                "pay_scale": pay,
                "qualification": "",
            }
        )
    return rows[:40]
