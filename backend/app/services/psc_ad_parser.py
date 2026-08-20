from __future__ import annotations

"""Parse state PSC-style advertisements (HPSC, UPPSC, MPPSC, etc.)."""

import re
from typing import Any, Optional

from app.services.content_quality import is_plausible_qualification

# Common OCR substitutions in Indian govt PDF text
_OCR_DATE_FIXES = (
    (re.compile(r"(\d{1,2}),(\d{1,2})g,(\d{4})"), r"\1/\2/\3"),
    (re.compile(r"(\d{1,2})\.(\d{1,2})g\.(\d{4})"), r"\1/\2/\3"),
    (re.compile(r"(\d{1,2}),(\d{1,2}),(\d{4})"), r"\1/\2/\3"),
    (re.compile(r"(\d{1,2})\.(\d{1,2})r0x"), r"\1/\2/2025"),
)

_CATEGORY_LABELS = (
    ("Un-reserved (UR)", ("un-reserved", "unreserved", "(ur)")),
    ("SC", ("sc", "scheduled caste")),
    ("BC-A (Non Creamy Layer)", ("bc-a", "bca")),
    ("BC-B (Non Creamy Layer)", ("bc-b", "bcb")),
    ("EWS", ("ews",)),
    ("ESM", ("esm", "ex-servicemen", "ex servicemen")),
    ("PwBD", ("pwbd", "pwd", "persons with benchmark")),
    ("OSC of Haryana", ("osc",)),
    ("DSC of Haryana", ("dsc",)),
    ("Total", ("total",)),
)

_FEE_CATEGORY_PATTERNS: list[tuple[str, str]] = [
    ("PwBD / Disabled", r"(?:PwBD|PWD|disabled|benchmark disability)[^.\n]{0,80}?(?:NIL|₹?\s*[\d,]+|free|exempted)"),
    ("SC / ST / BC / EWS / Women (Haryana)", r"(?:SC|ST|BC|OBC|EWS|women)[^.\n]{0,120}?(?:NIL|₹?\s*[\d,]+/-?)"),
    ("ESM / DESM / DFF", r"(?:ESM|DESM|DFF|ex-servicemen)[^.\n]{0,80}?(?:NIL|₹?\s*[\d,]+/-?)"),
    ("General / UR / All remaining", r"(?:all remaining|general|ur/unreserved|unreserved)[^.\n]{0,80}?(?:NIL|₹?\s*[\d,]+/-?)"),
]


def preprocess_psc_text(text: str) -> str:
    """Fix glued words and common OCR errors in PSC PDF text."""
    if not text:
        return ""

    cleaned = text
    for pattern, repl in _OCR_DATE_FIXES:
        cleaned = pattern.sub(repl, cleaned)

    cleaned = re.sub(
        r"(?i)(closingdate|openingdate|lastdate)(forthe|for)",
        lambda m: m.group(1) + " for the ",
        cleaned,
    )
    cleaned = re.sub(
        r"(?i)(openingdate|closingdate|lastdate)",
        lambda m: m.group(1).replace("date", " date "),
        cleaned,
    )
    cleaned = re.sub(r"(?i)submissionofonlineapplications", "submission of online applications", cleaned)
    return cleaned


def _parse_date_token(raw: str) -> Optional[str]:
    raw = raw.strip().replace("-", "/").replace(".", "/").replace(",", "/")
    raw = raw.replace("g", "8").replace("l", "1")
    parts = raw.split("/")
    if len(parts) != 3:
        return None
    try:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not (1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030):
        return None
    return f"{day:02d}/{month:02d}/{year}"


def _is_age_reference_date(text: str, pos: int) -> bool:
    window = text[max(0, pos - 120) : pos + 40].lower()
    return any(
        kw in window
        for kw in (
            "age will be checked",
            "as on",
            "eligibility of the candidate with regard to age",
            "not less than",
            "not more than",
        )
    )


def extract_psc_application_dates(text: str) -> list[dict[str, str]]:
    """Extract opening/closing dates from PSC-style noisy PDF text."""
    text = preprocess_psc_text(text)
    dates: list[dict[str, str]] = []

    opening_patterns = [
        r"(?i)opening\s+date[^0-9]{0,80}?(\d{1,2}[./,]\d{1,2}[./,g]?\d{2,4})",
        r"(?i)opening\s+date[^0-9]{0,20}\)\s*(\d{1,2}[./]\d{1,2}[./]\d{4})",
        r"(?i)submission\s+of\s+online\s+applications[^0-9]{0,40}(\d{1,2}[./,]\d{1,2}[./,g]?\d{2,4})",
    ]
    closing_patterns = [
        r"(?i)closing\s+date[^0-9]{0,80}?(\d{1,2}[./]\d{1,2}[./]\d{4})",
        r"(?i)closing\s+date\s+for[^0-9]{0,80}?(\d{1,2}[./]\d{1,2}[./]\d{4})",
        r"(?i)online\s+applications[^0-9]{0,40}(\d{1,2}[./]\d{1,2}[./]\d{4})",
        r"(?i)can\s+be\s+submitted\s+up\s+to[^0-9]{0,40}(\d{1,2}[./]\d{1,2}[./]\d{4})",
    ]

    opening_val: Optional[str] = None
    closing_val: Optional[str] = None

    for pattern in opening_patterns:
        match = re.search(pattern, text)
        if match:
            parsed = _parse_date_token(match.group(1))
            if parsed and not _is_age_reference_date(text, match.start()):
                opening_val = parsed
                break

    for pattern in closing_patterns:
        for match in re.finditer(pattern, text):
            parsed = _parse_date_token(match.group(1))
            if parsed and not _is_age_reference_date(text, match.start()):
                closing_val = parsed
                break
        if closing_val:
            break

    if opening_val:
        dates.append({"label": "Application Start", "label_hi": "आवेदन प्रारंभ", "date": opening_val})
    if closing_val:
        dates.append({"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": closing_val})

    return dates


def extract_advertisement_number(text: str) -> Optional[str]:
    match = re.search(
        r"(?i)(?:advertisement|advt\.?)\s*(?:no\.?|number)\s*\.?\s*(\d+)\s*of\s*(\d{4})",
        text,
    )
    if match:
        return f"Advertisement No. {match.group(1)} of {match.group(2)}"
    match = re.search(r"(?i)advt\.?\s*no\.?\s*-?\s*(\d+/\d{4})", text)
    if match:
        return f"Advt. No. {match.group(1)}"
    return None


def extract_post_name(text: str, fallback_title: str = "") -> Optional[str]:
    patterns = [
        r"(?i)name\s+of\s+the\s+post\s*:?\s*\n?\s*(Assistant[^\n]{10,180}?Board\.?)",
        r"(?i)for\s+the\s+posts?\s+of\s*\n?\s*(Assistant[^\n]{10,180}?Board\.?)",
        r"(?i)recruitment\s+for\s+the\s+posts?\s+of\s*\n?\s*([^\n]{15,180}?Board\.?)",
        r"(?i)posts?\s+of\s+(Assistant[^\n]{10,160})",
        r"(?i)posts?\s+of\s+([A-Z][^\n]{10,160})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            post = re.sub(r"\s+", " ", match.group(1)).strip(" .")
            if len(post) >= 15:
                return post[:180]

    from app.services.notification_pdf_parser import _post_from_title

    return _post_from_title(fallback_title)


def extract_psc_qualification(text: str) -> Optional[str]:
    patterns = [
        r"(?i)(?:^|\n)\s*i\)\s*(Full time regular.+?)(?=Pay Scale|Note|CLOSING DATE|AGE LIMIT|\n\s*ii\))",
        r"(?i)(?:essential|minimum)\s+(?:educational\s+)?qualification[^:\n]{0,30}[:：]?\s*([^\n]{20,350})",
        r"(?i)(Bachelor[^\n]{15,200}?(?:Engineering|Degree)[^\n]{0,120})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.S)
        if match:
            qual = re.sub(r"\s+", " ", match.group(1)).strip(" .")
            if len(qual) >= 20 and "closing date" not in qual.lower() and is_plausible_qualification(qual):
                return qual[:500]
    return None


def extract_psc_age_limit(text: str) -> Optional[str]:
    normalized = text.replace("l8", "18").replace("l9", "19")
    patterns = [
        r"(?i)(?:not less than|minimum)\s*(\d{2})\s*years?\s+and\s+(?:not more than|maximum)\s*(\d{2})\s*years?",
        r"(?i)age\s+limits?\s*:?\s*\n?\s*a\)\s*candidate\s+should\s+not\s+be\s+less\s+than\s*(\d{2})[^0-9]{0,40}not\s+more\s+than\s*(\d{2})",
        r"(?i)between\s+(\d{2})\s*(?:to|-)\s*(\d{2})\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return f"{match.group(1)}–{match.group(2)} years"
    return None


def extract_psc_pay_scale(text: str) -> tuple[str, str]:
    match = re.search(
        r"(?i)pay\s+scale\s*:?\s*-?\s*level\s*-?\s*(\d+)\s*rs\.?\s*([\d,\sIg\-]+?)(?:/-|\n|Note)",
        text,
    )
    if not match:
        match = re.search(
            r"(?i)pay\s+scale[^.\n]{0,40}level\s*-?\s*(\d+)[^\n]{0,30}([\d,\sIg₹\-]+)",
            text,
        )
    if match:
        level = f"Level-{match.group(1)}"
        scale_raw = match.group(2).replace("I", "1").replace("g", "9").replace("l", "1")
        nums = re.findall(r"\d[\d,]*", scale_raw.replace(" ", ""))
        if len(nums) >= 2:
            return level, f"₹{nums[0]} – ₹{nums[1]}"
        if nums:
            return level, f"₹{nums[0]}"
    match = re.search(r"(?i)level\s*-?\s*(\d+)[^\n]{0,40}(₹[^\n]{5,60})", text)
    if match:
        return f"Level-{match.group(1)}", match.group(2).strip()
    return "", ""


def extract_psc_fee_rows(text: str) -> list[tuple[str, str]]:
    block_match = re.search(
        r"(?i)application\s+fee\s*:?\s*(.*?)(?:note\s*\d|admit\s+card|age\s+limit|mode\s+of\s+exam)",
        text,
        re.S,
    )
    source = block_match.group(1) if block_match else text
    rows: list[tuple[str, str]] = []

    if re.search(r"(?i)(?:pwbd|pwbd|disabilit|40\s*%).{0,120}?\bNIL\b", source, re.S):
        rows.append(("PwBD / Disabled (40%+)", "NIL"))

    if re.search(r"(?i)(?:SC|OSC|DSC|BC-A|BC-B|EWS|women).{0,200}?(?:250l|2501|z50l|250/-|250)", source, re.S):
        rows.append(("SC / ST / BC / EWS / Women (Haryana)", "₹250/-"))

    if re.search(r"(?i)(?:DESM|Destitute).{0,80}?(?:250l|2501|250/-|250)", source, re.S):
        rows.append(("DESM / Destitute (Haryana)", "₹250/-"))

    ur = re.search(r"(?i)(?:UR Category|belonging to U R|U R Category)[^0-9]{0,60}(\d{3,4})", source)
    if ur:
        rows.append(("UR Category (Haryana)", f"₹{ur.group(1)}/-"))

    remaining = re.search(r"(?i)all remaining candidates[^0-9]{0,40}(\d{3,4})", source)
    if remaining:
        rows.append(("All remaining candidates", f"₹{remaining.group(1)}/-"))

    numbered = re.findall(
        r"(?i)(?:^|\n)\s*(\d+)\.\s*([^\n]{5,160}?)\s*((?:NIL|₹?\s*[\d,]+/-?|free|exempted|\d{3,4}/-))",
        source,
    )
    for _num, category, fee in numbered:
        cat = re.sub(r"\s+", " ", category).strip(" .")
        fee_clean = re.sub(r"\s+", " ", fee).strip()
        if cat and fee_clean and not re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", fee_clean):
            pair = (cat[:100], fee_clean[:40])
            if pair not in rows:
                rows.append(pair)

    if not rows:
        for label, pattern in _FEE_CATEGORY_PATTERNS:
            match = re.search(pattern, source, re.I)
            if match:
                fee = re.search(r"(NIL|₹?\s*[\d,]+/-?|free|exempted)", match.group(0), re.I)
                if fee:
                    rows.append((label, fee.group(0).strip()))

    cleaned: list[tuple[str, str]] = []
    seen_fees: set[str] = set()
    for cat, fee in rows:
        if re.search(r"[\[\]{}]", cat):
            continue
        key = fee.strip().lower()
        if key in seen_fees and len(cleaned) >= 2:
            continue
        seen_fees.add(key)
        cleaned.append((cat, fee))
    return cleaned[:8]


def extract_psc_selection_steps(text: str) -> list[str]:
    match = re.search(
        r"(?i)mode\s+(?:of\s+)?examination\s*:?\s*-?\s*(.*?)(?:note\s*-|penalt|important\s+instruction|part\s*-?\s*b)",
        text,
        re.S,
    )
    block = match.group(1) if match else ""

    steps: list[str] = []
    for line in re.split(r"\n+", block):
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 15:
            continue
        if any(kw in line.lower() for kw in ("screening test", "written test", "interview", "subject knowledge", "cbt", "pet")):
            steps.append(line[:250])
    if steps:
        return steps[:8]

    inline = re.search(r"(?i)(three stage recruitment process[^.\n]{10,200})", text)
    if inline:
        return [re.sub(r"\s+", " ", inline.group(1)).strip()]
    inline = re.search(r"(?i)(screening\s+test[^.\n]{0,80}interview[^.\n]{0,80})", text)
    if inline:
        return [re.sub(r"\s+", " ", inline.group(1)).strip()[:250]]
    return []


def _find_category_number_line(text: str) -> Optional[list[int]]:
    anchor = re.search(r"(?i)category\s+wise\s+break", text)
    if anchor:
        tail = text[anchor.start() : anchor.start() + 5000]
        for line in tail.split("\n"):
            nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", line)]
            if not (5 <= len(nums) <= 12):
                continue
            if max(nums) > 500 or max(nums) < 3:
                continue
            if sum(1 for n in nums if n > 0) < 4:
                continue
            return nums

    direct = re.search(r"(?<!\d)((?:0?\d\s+){5,11}(?:29|3\d|[1-4]\d))(?:\s+0?\d){0,4}(?!\d)", text)
    if direct:
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", direct.group(0))]
        if 5 <= len(nums) <= 12:
            return nums
    return None


def extract_category_vacancy_rows(text: str, post_name: str) -> tuple[list[dict[str, Any]], Optional[int]]:
    nums = _find_category_number_line(text)
    if not nums:
        return [], None

    total = max(nums)
    if total < 5 or total > 10000:
        return [], None

    section = re.search(r"(?i)category\s+wise\s+break[\s\-up]*.{0,2500}", text, re.S)
    header_text = (section.group(0) if section else text).lower()

    labels_found: list[str] = []
    for label, keys in _CATEGORY_LABELS:
        if label == "Total":
            continue
        if any(k in header_text for k in keys):
            labels_found.append(label)

    pay_level, pay_scale = extract_psc_pay_scale(text)
    qual = extract_psc_qualification(text) or ""

    rows: list[dict[str, Any]] = [
        {
            "sr": "00",
            "post": post_name[:160],
            "vacancies": total,
            "pay_level": pay_level,
            "pay_scale": pay_scale or "",
            "qualification": qual[:200],
        }
    ]

    cat_nums = [n for n in nums if n != total]
    if labels_found and len(cat_nums) >= len(labels_found):
        cat_nums = cat_nums[: len(labels_found)]
    elif len(cat_nums) > len(labels_found):
        cat_nums = cat_nums[: max(1, len(nums) - 1)]

    default_labels = ["Un-reserved (UR)", "SC", "BC-A", "BC-B", "EWS", "ESM", "PwBD", "OSC", "DSC"]
    use_labels = labels_found or default_labels[: len(cat_nums)]

    for i, count in enumerate(cat_nums):
        if count <= 0:
            continue
        label = use_labels[i] if i < len(use_labels) else f"Category {i + 1}"
        rows.append(
            {
                "sr": f"{i + 1:02d}",
                "post": f"{post_name[:80]} — {label}",
                "vacancies": count,
                "pay_level": pay_level,
                "pay_scale": pay_scale or "—",
                "qualification": qual[:120] if qual else "",
            }
        )

    return rows, total


def parse_psc_advertisement(text: str, title: str = "") -> dict[str, Any]:
    """Full structured parse for state PSC notification PDF text."""
    if not text or len(text.strip()) < 80:
        return {}

    normalized = preprocess_psc_text(text)
    result: dict[str, Any] = {}

    adv_no = extract_advertisement_number(normalized)
    if adv_no:
        result["advertisement_no"] = adv_no

    post_name = extract_post_name(normalized, title) or title[:160]
    if post_name:
        result["post_name"] = post_name

    dates = extract_psc_application_dates(normalized)
    if dates:
        result["dates"] = dates
        for d in dates:
            if "last" in d["label"].lower():
                result["last_date"] = d["date"]

    vacancy_rows, total = extract_category_vacancy_rows(normalized, post_name)
    if vacancy_rows:
        result["vacancy_rows"] = vacancy_rows
        result["total_vacancies"] = total

    qual = extract_psc_qualification(normalized)
    if qual:
        result["qualification"] = qual

    age = extract_psc_age_limit(normalized)
    if age:
        result["age_limit"] = age

    fee_rows = extract_psc_fee_rows(normalized)
    if fee_rows:
        result["application_fee_rows"] = fee_rows
        result["application_fee"] = fee_rows[-1][1]

    pay_level, pay_scale = extract_psc_pay_scale(normalized)
    if pay_level or pay_scale:
        for row in result.get("vacancy_rows") or []:
            if not row.get("pay_level"):
                row["pay_level"] = pay_level
            if not row.get("pay_scale"):
                row["pay_scale"] = pay_scale or ""

    selection = extract_psc_selection_steps(normalized)
    if selection:
        result["selection_steps"] = selection

    if post_name and qual:
        result["eligibility_rows"] = [
            {
                "post": post_name[:120],
                "education": qual[:300],
                "experience": "As per notification",
                "other": result.get("age_limit") or "",
            }
        ]

    overview = re.search(
        r"(?i)(?:commission\s+invites|invites\s+online\s+applications)[^\n]{20,220}",
        normalized,
    )
    if overview:
        result["overview"] = re.sub(r"\s+", " ", overview.group(0)).strip()[:400]

    return result
