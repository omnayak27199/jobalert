from __future__ import annotations

"""Extract post tables, pay scales and dates from official notification PDFs."""

import logging
import re
from io import BytesIO
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import pdfplumber

from app.services.advertisement_text_parser import enrich_from_full_text
from app.services.bilingual_text import (
    extract_hindi_overview,
    extract_hindi_title,
    split_bilingual_line,
)
from app.services.content_quality import (
    filter_eligibility_rows,
    filter_fee_rows,
    filter_vacancy_rows,
    is_garbled_text,
    is_generic_title,
    is_plausible_qualification,
    is_plausible_post_name,
    title_from_pdf_filename,
)
from app.services.date_extractor import extract_dates
from app.services.official_title import (
    choose_best_title,
    extract_official_title_from_text,
    extract_pdf_metadata_title,
)
from app.services.pdf_text_extractor import extract_pdf_text, is_text_usable
from app.services.pdf_table_extractor import (
    extract_category_rows_from_text,
    extract_pdf_tables,
    extract_post_table_from_text,
)
from app.services.psc_ad_parser import parse_psc_advertisement

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; IndiaJobBot/1.0; +https://indiajob.in/bot)"


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def _post_from_title(title: str) -> Optional[str]:
    match = re.search(
        r"(?:post of|recruitment to the post of|for the post of)\s+(.+?)(?:,\s*[A-Z]|\(Advt|\.|$)",
        title,
        re.I,
    )
    if match:
        return match.group(1).strip()[:120]
    match = re.search(r"(lecturer\s*\([^)]+\))", title, re.I)
    if match:
        return match.group(1).strip()
    return None


def infer_post_label(title: str, organization: str) -> str:
    """Best-effort post name for the vacancy table."""
    post = _post_from_title(title)
    if post:
        return post
    match = re.search(
        r"(\d+\s+posts?|\d+\s+vacanc(?:y|ies))",
        title,
        re.I,
    )
    if match and len(title) < 120:
        return title.strip()
    if any(kw in title.lower() for kw in ("recruitment", "vacancy", "bharti", "notification")):
        cleaned = re.sub(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", "", title).strip()
        return cleaned[:140] if cleaned else (organization or title[:140])
    if organization:
        return f"{organization} — {title[:80]}"
    cleaned = re.sub(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", "", title).strip()
    return cleaned[:140] if cleaned else title[:140]


def extract_application_dates(text: str) -> list[dict[str, str]]:
    """Return opening + closing date rows for sections."""
    dates: list[dict[str, str]] = []
    opening = re.search(
        r"(?:opening date|start date|application start|online application[^:\n]{0,30}|"
        r"आवेदन\s*प्रारंभ|ऑनलाइन\s*आवेदन\s*(?:प्रारंभ|शुरू)|आवेदन\s*शुरू)"
        r"\s*[:\-]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})",
        text,
        re.I,
    )
    closing = re.search(
        r"(?:closing date|last date|apply(?: till| by| before| upto| up to)?|upto|till|"
        r"अंतिम\s*तिथि|आवेदन\s*(?:की\s*)?अंतिम\s*(?:तिथि|दिनांक)|अंत\s*तिथि)"
        r"\s*[:\-]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})",
        text,
        re.I,
    )
    if opening:
        dates.append(
            {
                "label": "Application Start",
                "label_hi": "आवेदन प्रारंभ",
                "date": opening.group(1).replace("-", "/").replace(".", "/"),
            }
        )
    if closing:
        dates.append(
            {
                "label": "Last Date to Apply",
                "label_hi": "अंतिम तिथि",
                "date": closing.group(1).replace("-", "/").replace(".", "/"),
            }
        )

    if not dates:
        dates = _extract_dates_by_context(text)

    if not dates:
        extracted = extract_dates(text)
        if extracted.last_date:
            dates.append(
                {
                    "label": "Last Date to Apply",
                    "label_hi": "अंतिम तिथि",
                    "date": extracted.last_date.strftime("%d/%m/%Y"),
                }
            )
    return dates


def _normalize_date_str(raw: str) -> str:
    return raw.replace("-", "/").replace(".", "/")


def _extract_dates_by_context(text: str) -> list[dict[str, str]]:
    """Mine dd/mm/yyyy and dd.mm.yyyy dates near last/closing/upto keywords."""
    dates: list[dict[str, str]] = []
    patterns = [
        (
            "Last Date to Apply",
            r"(?:last date|closing date|apply(?: till| by| before| upto| up to)?|upto|till|"
            r"अंतिम\s*तिथि|आवेदन\s*(?:की\s*)?अंतिम\s*(?:तिथि|दिनांक)|अंत\s*तिथि)"
            r"[^0-9]{0,40}(\d{1,2}[./-]\d{1,2}[./-]\d{4})",
        ),
        (
            "Application Start",
            r"(?:opening date|start date|from|आवेदन\s*प्रारंभ|ऑनलाइन\s*आवेदन\s*(?:प्रारंभ|शुरू)|"
            r"आवेदन\s*शुरू)[^0-9]{0,40}(\d{1,2}[./-]\d{1,2}[./-]\d{4})",
        ),
    ]
    for label, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            dates.append(
                {
                    "label": label,
                    "label_hi": "अंतिम तिथि" if "Last" in label else "आवेदन प्रारंभ",
                    "date": _normalize_date_str(match.group(1)),
                }
            )

    if dates:
        return dates

    # Fallback: pick plausible future dates from noisy OCR text.
    found = re.findall(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b", text)
    normalized: list[str] = []
    for raw in found:
        parts = re.split(r"[./-]", raw)
        if len(parts) != 3:
            continue
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        if not (1 <= day <= 31 and 1 <= month <= 12 and 2025 <= year <= 2028):
            continue
        norm = _normalize_date_str(raw)
        if day == 1 and month == 1:
            continue
        normalized.append(norm)

    unique = sorted(set(normalized), key=lambda d: tuple(int(x) for x in d.split("/")))
    if len(unique) >= 2:
        # Most repeated date in source text is often the application deadline.
        counts: dict[str, int] = {}
        for raw in found:
            norm = _normalize_date_str(raw)
            parts = norm.split("/")
            if len(parts) == 3 and 2025 <= int(parts[2]) <= 2028:
                counts[norm] = counts.get(norm, 0) + 1
        last_candidate = max(counts, key=counts.get) if counts else unique[-2 if len(unique) > 2 else -1]
        opening_candidate = unique[0]
        if opening_candidate == last_candidate and len(unique) > 1:
            opening_candidate = unique[0]
        dates.append({"label": "Application Start", "label_hi": "आवेदन प्रारंभ", "date": opening_candidate})
        dates.append({"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": last_candidate})
    elif len(unique) == 1:
        dates.append({"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": unique[0]})
    return dates


def _find_header_index(rows: list[list[Any]]) -> tuple[int, dict[str, int]]:
    for idx, row in enumerate(rows[:6]):
        cells = [_clean_cell(c).lower() for c in row]
        joined = " ".join(cells)
        if ("post" in joined or "पद" in joined) and (
            "total" in joined
            or "vacanc" in joined
            or "रिक्त" in joined
            or "posts" in joined
            or "संख्या" in joined
            or "कुल" in joined
        ):
            col_map: dict[str, int] = {}
            for ci, cell in enumerate(cells):
                if "post code" in cell or cell == "code":
                    col_map["code"] = ci
                elif (
                    "name of the post" in cell
                    or cell == "post"
                    or "name of post" in cell
                    or "पद का नाम" in cell
                    or "पदनाम" in cell
                    or cell == "पद"
                ):
                    col_map["post"] = ci
                elif cell == "total" or cell == "कुल":
                    col_map["total"] = ci
                elif "pay scale" in cell or "pay level" in cell or "level" in cell or "वेतन" in cell:
                    col_map["pay"] = ci
                elif (
                    "qualification" in cell
                    or "education" in cell
                    or "essential" in cell
                    or "योग्यता" in cell
                    or "शैक्षणिक" in cell
                ):
                    col_map["qualification"] = ci
                elif "vacanc" in cell or cell == "posts" or cell == "no." or cell == "no" or "रिक्त" in cell:
                    col_map.setdefault("total", ci)
            if "post" in col_map or "code" in col_map:
                return idx, col_map
    return -1, {}


def _parse_vacancy_table(rows: list[list[Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []

    header_idx, col_map = _find_header_index(rows)
    if header_idx < 0:
        return []

    # Sometimes headers span two rows — merge TOTAL column from next row
    if "total" not in col_map and header_idx + 1 < len(rows):
        sub = [_clean_cell(c).lower() for c in rows[header_idx + 1]]
        for ci, cell in enumerate(sub):
            if cell == "total":
                col_map["total"] = ci

    vacancy_rows: list[dict[str, Any]] = []
    data_rows = rows[header_idx + 1 :]
    if data_rows and any(_clean_cell(c).lower() == "total" for c in data_rows[0]):
        data_rows = data_rows[1:]

    sr = 0
    for row in data_rows:
        cells = [_clean_cell(c) for c in row]
        if not any(cells):
            continue

        post_idx = col_map.get("post", 2)
        code_idx = col_map.get("code", 1)
        total_idx = col_map.get("total")

        post = cells[post_idx] if post_idx < len(cells) else ""
        code = cells[code_idx] if code_idx < len(cells) else ""
        if not post and not code:
            continue
        if post.lower() in {"post", "name of the post", "name of post"}:
            continue

        total_val: Optional[int] = None
        if total_idx is not None and total_idx < len(cells):
            num = re.sub(r"[^\d]", "", cells[total_idx])
            if num.isdigit():
                total_val = int(num)

        if not total_val:
            # Fallback: last numeric cell in row
            for cell in reversed(cells):
                num = re.sub(r"[^\d]", "", cell)
                if num.isdigit() and 0 < int(num) < 50000:
                    total_val = int(num)
                    break

        sr += 1
        english_post, hindi_post = split_bilingual_line(post)
        label = english_post or post or f"Post {code}"
        if not is_plausible_post_name(label) and code:
            label = f"Post {code}"
        if code and code not in label:
            label = f"{label} ({code})"

        pay_scale = ""
        pay_level = ""
        pay_idx = col_map.get("pay")
        qual_idx = col_map.get("qualification")
        if pay_idx is not None and pay_idx < len(cells):
            pay_cell = cells[pay_idx]
            if pay_cell:
                pay_scale = pay_cell
                level_match = re.search(r"level[^0-9]*(\d+)", pay_cell, re.I)
                pay_level = f"Level-{level_match.group(1)}" if level_match else ""

        post_qual = ""
        if qual_idx is not None and qual_idx < len(cells):
            candidate_qual = cells[qual_idx][:200]
            if is_plausible_qualification(candidate_qual):
                post_qual = candidate_qual

        row_data: dict[str, Any] = {
            "sr": f"{sr:02d}",
            "post": label[:160],
            "vacancies": total_val or 0,
            "pay_level": pay_level,
            "pay_scale": pay_scale,
            "qualification": post_qual,
        }
        if hindi_post and hindi_post != label:
            row_data["post_hi"] = hindi_post[:160]
        vacancy_rows.append(row_data)

    return filter_vacancy_rows([r for r in vacancy_rows if r["post"]])


def extract_pay_scale_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return (post_hint, pay_scale, pay_level) tuples from PDF text."""
    blocks: list[tuple[str, str, str]] = []
    pattern = re.compile(
        r"(?:Post(?:\s+Name)?[^:]{0,80}:?\s*([^\n]+))?\s*Pay Scale:-?\s*(₹?\s*[\d,]+[^\n]{0,80})",
        re.I,
    )
    for match in pattern.finditer(text):
        post_hint = (match.group(1) or "").strip()
        pay_line = match.group(2).strip()
        level_match = re.search(r"pay level[^0-9]*(\d+)", pay_line, re.I)
        pay_level = f"Level-{level_match.group(1)}" if level_match else ""
        blocks.append((post_hint, pay_line, pay_level))

    if not blocks:
        for pay_line in re.findall(r"Pay Scale:-?\s*(₹[^\n]+)", text, re.I):
            level_match = re.search(r"pay level[^0-9]*(\d+)", pay_line, re.I)
            pay_level = f"Level-{level_match.group(1)}" if level_match else ""
            blocks.append(("", pay_line.strip(), pay_level))

    return blocks


def _attach_pay_scales(vacancy_rows: list[dict[str, Any]], pay_blocks: list[tuple[str, str, str]]) -> None:
    if not pay_blocks:
        return
    if len(pay_blocks) == 1 and len(vacancy_rows) >= 1:
        _, scale, level = pay_blocks[0]
        for row in vacancy_rows:
            row["pay_scale"] = scale
            row["pay_level"] = level
        return

    for row in vacancy_rows:
        post_lower = row["post"].lower()
        for hint, scale, level in pay_blocks:
            if hint and hint.lower()[:12] in post_lower:
                row["pay_scale"] = scale
                row["pay_level"] = level
                break


def fetch_pdf_bytes_sync(url: str) -> Optional[bytes]:
    try:
        with httpx.Client(timeout=45.0, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200 or not resp.content[:5].startswith(b"%PDF-"):
                return None
            return resp.content
    except Exception as exc:
        logger.debug("Sync PDF fetch failed %s: %s", url, exc)
        return None


async def fetch_pdf_bytes(url: str) -> Optional[bytes]:
    try:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                return None
            if not resp.content[:5].startswith(b"%PDF-"):
                return None
            return resp.content
    except Exception as exc:
        logger.debug("PDF fetch failed %s: %s", url, exc)
        return None


def parse_notification_pdf_bytes(data: bytes, title: str = "", pdf_url: str = "") -> dict[str, Any]:
    """Parse PDF bytes into sections-friendly structures."""
    result: dict[str, Any] = {
        "dates": [],
        "vacancy_rows": [],
        "total_vacancies": None,
        "qualification": None,
        "last_date": None,
    }

    text_parts: list[str] = []
    vacancy_rows: list[dict[str, Any]] = []

    text = extract_pdf_text(data, max_pages=12)
    psc_parsed: dict[str, Any] = {}
    if is_text_usable(text):
        for table in extract_pdf_tables(data, max_pages=6):
            vacancy_rows.extend(_parse_vacancy_table(table))

    meta_title = extract_pdf_metadata_title(data)
    if not text and not vacancy_rows:
        inferred_post = _post_from_title(title) or title_from_pdf_filename(pdf_url)
        if inferred_post:
            result["vacancy_rows"] = [
                {
                    "sr": "01",
                    "post": inferred_post,
                    "vacancies": 0,
                    "pay_level": "",
                    "pay_scale": "",
                    "qualification": "",
                }
            ]
        official = choose_best_title(meta_title, listing_title=title, pdf_url=pdf_url)
        if official:
            result["official_title"] = official
        return _finalize_parsed_result(result, pdf_url=pdf_url)

    post_hint = _post_from_title(title) or title_from_pdf_filename(pdf_url) or title[:120]

    if is_text_usable(text):
        result["dates"] = extract_application_dates(text)
        if result["dates"]:
            for d in result["dates"]:
                if "last" in d["label"].lower():
                    result["last_date"] = d["date"]

    # State PSC advertisements (HPSC, UPPSC, etc.) — category table, fee, dates
    psc_parsed = parse_psc_advertisement(text, title=title) if is_text_usable(text) else {}
    if psc_parsed:
        for key, val in psc_parsed.items():
            if val is None or val == [] or val == "":
                continue
            if key == "dates" and psc_parsed.get("dates"):
                result["dates"] = psc_parsed["dates"]
                if psc_parsed.get("last_date"):
                    result["last_date"] = psc_parsed["last_date"]
            elif key == "vacancy_rows" and psc_parsed.get("vacancy_rows"):
                if len(psc_parsed["vacancy_rows"]) >= len(vacancy_rows):
                    vacancy_rows = psc_parsed["vacancy_rows"]
            elif key == "total_vacancies" and psc_parsed.get("total_vacancies"):
                result["total_vacancies"] = psc_parsed["total_vacancies"]
            elif key in result and isinstance(val, str) and isinstance(result.get(key), str):
                if len(val) > len(str(result.get(key, ""))):
                    result[key] = val
            else:
                result[key] = val

    # Deduplicate vacancy rows by post name
    seen: set[str] = set()
    unique_rows: list[dict[str, Any]] = []
    for row in vacancy_rows:
        key = row["post"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    pay_blocks = extract_pay_scale_blocks(text)
    _attach_pay_scales(unique_rows, pay_blocks)

    if len(unique_rows) <= 1 and is_text_usable(text):
        text_rows = extract_post_table_from_text(text)
        if len(text_rows) > len(unique_rows):
            unique_rows = text_rows
        cat_rows = extract_category_rows_from_text(text, post_hint or "")
        if len(cat_rows) > len(unique_rows):
            unique_rows = cat_rows
            total = sum(r["vacancies"] for r in cat_rows if r["vacancies"])
            if total:
                result["total_vacancies"] = max(result.get("total_vacancies") or 0, total)

    if not unique_rows:
        inferred_post = _post_from_title(title) or psc_parsed.get("post_name") or title_from_pdf_filename(pdf_url)
        if inferred_post:
            pay_level = psc_parsed.get("pay_level") or (pay_blocks[0][2] if pay_blocks else "")
            pay_scale = psc_parsed.get("pay_scale") or (pay_blocks[0][1] if pay_blocks else "")
            unique_rows = [
                {
                    "sr": "01",
                    "post": inferred_post,
                    "vacancies": result.get("total_vacancies") or 0,
                    "pay_level": pay_level,
                    "pay_scale": pay_scale,
                    "qualification": result.get("qualification") or "",
                }
            ]
    elif len(unique_rows) == 1 and pay_blocks:
        _attach_pay_scales(unique_rows, pay_blocks)

    result["vacancy_rows"] = filter_vacancy_rows(unique_rows[:40])
    if result.get("total_vacancies"):
        pass
    elif unique_rows:
        main = next((r for r in unique_rows if r.get("sr") == "00"), unique_rows[0])
        if main.get("vacancies"):
            result["total_vacancies"] = main["vacancies"]
        else:
            total = sum(r["vacancies"] for r in unique_rows if r["vacancies"])
            result["total_vacancies"] = total or None

    if is_text_usable(text):
        qual_match = re.search(
            r"(?:qualification|essential qualification|शैक्षणिक\s+योग्यता|योग्यता)[^:\n]{0,20}[:：]?\s*([^\n]{15,200})",
            text,
            re.I,
        )
        if qual_match and not result.get("qualification"):
            candidate = qual_match.group(1).strip()
            if is_plausible_qualification(candidate):
                result["qualification"] = candidate

        age_match = re.search(
            r"(?:age limit|आयु\s*सीमा)[^:\n]{0,20}[:：]?\s*([^\n]{5,80})",
            text,
            re.I,
        )
        if age_match and not result.get("age_limit"):
            result["age_limit"] = age_match.group(1).strip()

        fee_match = re.search(r"(?:application fee|exam fee|fee)[:\s]*([^\n]{5,80})", text, re.I)
        if fee_match and not result.get("application_fee_rows"):
            fee_val = fee_match.group(1).strip()
            if not re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", fee_val) and "upto" not in fee_val.lower():
                result["application_fee"] = fee_val

        _apply_text_enrichment(result, text, psc_parsed)

    text_title = extract_official_title_from_text(text, title)
    filename_title = title_from_pdf_filename(pdf_url) if pdf_url else None
    official = choose_best_title(meta_title, text_title, filename_title, listing_title=title, pdf_url=pdf_url)
    if official and not is_generic_title(official):
        result["official_title"] = official
    elif filename_title:
        result["official_title"] = filename_title

    title_hi = extract_hindi_title(text)
    if title_hi:
        result["title_hi"] = title_hi
    overview_hi = extract_hindi_overview(text)
    if overview_hi:
        result["overview_hi"] = overview_hi

    if not unique_rows:
        inferred_post = (
            _post_from_title(title)
            or psc_parsed.get("post_name")
            or title_from_pdf_filename(pdf_url)
            or infer_post_label(title, "")
        )
        if inferred_post:
            unique_rows = [
                {
                    "sr": "01",
                    "post": inferred_post,
                    "vacancies": result.get("total_vacancies") or 0,
                    "pay_level": pay_blocks[0][2] if pay_blocks else "",
                    "pay_scale": pay_blocks[0][1] if pay_blocks else "",
                    "qualification": result.get("qualification") or "",
                }
            ]
            result["vacancy_rows"] = unique_rows

    return _finalize_parsed_result(result, pdf_url=pdf_url)


def _finalize_parsed_result(result: dict[str, Any], pdf_url: str = "") -> dict[str, Any]:
    official_title = result.get("official_title") or title_from_pdf_filename(pdf_url)
    if official_title and not is_generic_title(official_title):
        result["official_title"] = official_title

    result["eligibility_rows"] = filter_eligibility_rows(result.get("eligibility_rows"))
    result["application_fee_rows"] = filter_fee_rows(result.get("application_fee_rows"))

    vac_rows = filter_vacancy_rows(result.get("vacancy_rows") or [])
    if not vac_rows and official_title and not is_generic_title(official_title):
        vac_rows = [
            {
                "sr": "01",
                "post": official_title[:160],
                "vacancies": result.get("total_vacancies") or 0,
                "pay_level": "",
                "pay_scale": "See official notification PDF",
                "qualification": "",
            }
        ]
    result["vacancy_rows"] = vac_rows

    if official_title and not is_generic_title(official_title):
        for row in result.get("vacancy_rows") or []:
            post = str(row.get("post") or "")
            if not post or is_generic_title(post):
                row["post"] = official_title[:160]
            qual = str(row.get("qualification") or "")
            if qual and not is_plausible_qualification(qual):
                row["qualification"] = ""

        qual = str(result.get("qualification") or "")
        if not is_plausible_qualification(qual):
            result.pop("qualification", None)

        if not result.get("eligibility_rows"):
            qual = str(result.get("qualification") or "")
            if is_plausible_qualification(qual):
                result["eligibility_rows"] = [
                    {
                        "post": official_title[:120],
                        "education": qual[:250],
                        "experience": "As per notification",
                        "other": "",
                    }
                ]

    if result.get("qualification") and not is_plausible_qualification(str(result["qualification"])):
        result.pop("qualification", None)

    return result


_PSC_PROTECTED_KEYS = frozenset({
    "dates", "vacancy_rows", "total_vacancies", "qualification", "age_limit",
    "application_fee_rows", "application_fee", "advertisement_no",
    "selection_steps", "eligibility_rows", "overview", "post_name", "age_relaxation",
})


def _apply_text_enrichment(result: dict[str, Any], text: str, psc_parsed: dict[str, Any]) -> None:
    """Merge generic text parser output without clobbering PSC fields."""
    if is_garbled_text(text, threshold=0.55) or not is_text_usable(text):
        return

    text_enriched = enrich_from_full_text(
        text,
        vacancy_rows=result.get("vacancy_rows"),
        existing_dates=result.get("dates"),
    )
    for key, val in text_enriched.items():
        if val is None or val == [] or val == "":
            continue
        if key == "eligibility_rows":
            incoming = filter_eligibility_rows(val or [])
            if not incoming:
                continue
            existing = filter_eligibility_rows(result.get("eligibility_rows"))
            if len(incoming) > len(existing):
                result["eligibility_rows"] = incoming
            continue
        if key == "application_fee_rows":
            incoming = filter_fee_rows(val or [])
            if incoming:
                result["application_fee_rows"] = incoming
            continue
        if key in _PSC_PROTECTED_KEYS and psc_parsed.get(key):
            continue
        if key == "vacancy_rows":
            existing = result.get("vacancy_rows") or []
            incoming = filter_vacancy_rows(val or [])
            if len(incoming) > len(existing):
                result["vacancy_rows"] = incoming
            continue
        if key in ("age_limit", "qualification") and psc_parsed.get(key):
            continue
        if key == "qualification" and not is_plausible_qualification(str(val)):
            continue
        if key in result and isinstance(val, str) and isinstance(result.get(key), str):
            existing = str(result[key])
            if key in ("age_limit", "qualification") and existing and "year" in existing.lower():
                continue
            if len(val) <= len(existing) and key in ("age_limit", "qualification"):
                continue
        result[key] = val


def enrich_from_notification_pdf_sync(url: str, title: str = "") -> dict[str, Any]:
    if not url:
        return {}
    path = urlparse(url).path.lower()
    if not (path.endswith(".pdf") or ".pdf" in path):
        return {}
    data = fetch_pdf_bytes_sync(url)
    if not data:
        return {}
    try:
        return parse_notification_pdf_bytes(data, title=title, pdf_url=url)
    except Exception as exc:
        logger.warning("Sync PDF parse failed for %s: %s", url, exc)
        return {}


async def enrich_from_notification_pdf(url: str, title: str = "") -> dict[str, Any]:
    if not url:
        return {}
    path = urlparse(url).path.lower()
    if not (path.endswith(".pdf") or ".pdf" in path):
        return {}
    data = await fetch_pdf_bytes(url)
    if not data:
        return {}
    try:
        return parse_notification_pdf_bytes(data, title=title, pdf_url=url)
    except Exception as exc:
        logger.warning("PDF parse failed for %s: %s", url, exc)
        return {}
