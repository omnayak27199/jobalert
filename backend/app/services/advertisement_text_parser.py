from __future__ import annotations

"""Extract eligibility, exam, selection and fee details from full notification text."""

import re
from typing import Any, Optional

from app.services.bilingual_text import extract_hindi_overview, extract_hindi_title
from app.services.content_quality import (
    filter_eligibility_rows,
    filter_fee_rows,
    is_plausible_post_name,
    is_plausible_qualification,
)

# Section boundary markers used across Indian govt notifications
_SECTION_END = re.compile(
    r"\n\s*(?:"
    r"age(?:\s+limit|\s+relaxation)?|"
    r"application\s+fee|exam\s+fee|"
    r"selection\s+process|mode\s+of\s+selection|scheme\s+of\s+examination|"
    r"reservation|how\s+to\s+apply|"
    r"important\s+(?:date|instruction)|"
    r"general\s+instruction|"
    r"disclaimer|"
    r"annexure|appendix|"
    r"आयु\s*सीमा|आवेदन\s*शुल्क|चयन\s*प्रक्रिया|"
    r"आरक्षण|आवेदन\s*कैसे\s*करें|"
    r"महत्वपूर्ण\s*(?:तिथि|निर्देश)|"
    r"सामान्य\s*निर्देश|"
    r"अनुलग्नक"
    r")\b",
    re.I,
)

_QUALIFICATION_HEADERS = re.compile(
    r"(?:essential|minimum|educational)\s+qualification|"
    r"eligibility\s+criteria|qualification\s+required|"
    r"minimum\s+educational\s+qualification|"
    r"शैक्षणिक\s+योग्यता|न्यूनतम\s+योग्यता|"
    r"योग्यता\s*[:：]",
    re.I,
)

_SELECTION_HEADERS = re.compile(
    r"(?:selection\s+process|mode\s+of\s+selection|scheme\s+of\s+(?:examination|selection)|"
    r"method\s+of\s+selection|stages\s+of\s+selection|recruitment\s+process|"
    r"चयन\s+प्रक्रिया|चयन\s+की\s+विधि|"
    r"परीक्षा\s+की\s+योजना)",
    re.I,
)

_RESERVATION_HEADERS = re.compile(
    r"(?:reservation|category[\-\s]wise|horizontal\s+reservation|"
    r"vacancy\s+reserved\s+for|"
    r"आरक्षण|श्रेणीवार|"
    r"आरक्षित\s+पद)",
    re.I,
)

_AGE_RELAX_HEADERS = re.compile(
    r"age\s+relaxation|relaxation\s+in\s+upper\s+age|upper\s+age\s+relaxation|"
    r"आयु\s+में\s+छूट|ऊपरी\s+आयु\s+में\s+छूट",
    re.I,
)


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _extract_block(text: str, header: re.Pattern[str], max_chars: int = 2500) -> str:
    match = header.search(text)
    if not match:
        return ""
    start = match.end()
    tail = text[start : start + max_chars]
    end_match = _SECTION_END.search(tail)
    block = tail[: end_match.start()] if end_match else tail
    return block.strip()


def _split_bullets(block: str) -> list[str]:
    lines: list[str] = []
    for raw in re.split(r"\n(?=\d+[\.\)]\s|[•●▪\-–—]\s|\([a-z]\)\s)", block):
        line = _clean_line(raw)
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        line = re.sub(r"^[•●▪\-–—]\s*", "", line)
        line = re.sub(r"^\([a-z]\)\s*", "", line, flags=re.I)
        if len(line) >= 8:
            lines.append(line[:400])
    if not lines:
        for raw in block.split("\n"):
            line = _clean_line(raw)
            if len(line) >= 12:
                lines.append(line[:400])
    return lines[:12]


def extract_age_limit(text: str) -> Optional[str]:
    patterns = [
        r"age\s+limit[^:\n]{0,30}:\s*([^\n]{5,120})",
        r"आयु\s*सीमा[^:\n]{0,20}[:：]?\s*([^\n]{5,120})",
        r"(?:minimum|min\.?)\s+age[^0-9]{0,20}(\d{2})[^0-9]{0,30}(?:maximum|max\.?)[^0-9]{0,20}(\d{2})",
        r"(?:न्यूनतम|कम\s*से\s*कम)\s*(\d{2})[^.\n]{0,40}(?:अधिकतम|अधिक\s*से\s*अधिक|अधिक)\s*(\d{2})",
        r"(?:not\s+below|minimum)\s+(\d{2})[^.\n]{0,40}(?:not\s+above|maximum|upto|up\s+to)\s+(\d{2})",
        r"(?:maximum|max\.?|upto|up\s+to)\s+(\d{2})\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            if match.lastindex and match.lastindex >= 2:
                return f"{match.group(1)}–{match.group(2)} years"
            return _clean_line(match.group(0))[:120]
    return None


def extract_age_relaxation(text: str) -> Optional[str]:
    block = _extract_block(text, _AGE_RELAX_HEADERS, max_chars=1200)
    if block:
        lines = _split_bullets(block)
        if lines:
            return " ".join(lines[:4])[:500]
    patterns = [
        r"(SC/ST[^.\n]{5,120})",
        r"(OBC[^.\n]{5,120}relaxation[^.\n]{0,80})",
        r"(ex[\-\s]?servicemen[^.\n]{5,120})",
        r"(PwD|PwBD|persons?\s+with\s+disabilit)[^.\n]{5,120}",
    ]
    parts: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            parts.append(_clean_line(match.group(0))[:150])
    return "; ".join(parts)[:500] if parts else None


def extract_qualification_summary(text: str) -> Optional[str]:
    block = _extract_block(text, _QUALIFICATION_HEADERS, max_chars=1800)
    if block:
        lines = _split_bullets(block)
        plausible = [line for line in lines if is_plausible_qualification(line)]
        if plausible:
            return " ".join(plausible[:3])[:600]
    match = re.search(
        r"(?:qualification|essential qualification)[^:\n]{0,20}:\s*([^\n]{15,300})",
        text,
        re.I,
    )
    if match:
        candidate = _clean_line(match.group(1))[:600]
        if is_plausible_qualification(candidate):
            return candidate
    return None


def extract_eligibility_rows(text: str, vacancy_rows: Optional[list[dict[str, Any]]] = None) -> list[dict[str, str]]:
    """Build post-wise eligibility rows from notification text."""
    rows: list[dict[str, str]] = []
    block = _extract_block(text, _QUALIFICATION_HEADERS, max_chars=4000)
    global_qual = extract_qualification_summary(text) or ""

    # Pattern: Post Name ... Qualification ...
    post_qual_pattern = re.compile(
        r"(?:post(?:\s+name)?|name\s+of\s+(?:the\s+)?post)\s*[:\-]?\s*([^\n]{3,80}).{0,80}?"
        r"(?:qualification|education)[:\s]+([^\n]{10,200})",
        re.I | re.S,
    )
    for match in post_qual_pattern.finditer(block or text):
        rows.append(
            {
                "post": _clean_line(match.group(1))[:120],
                "education": _clean_line(match.group(2))[:250],
                "experience": "As per notification",
                "other": "",
            }
        )

    # Numbered/bulleted post blocks: "1. Clerk — Graduate..."
    numbered = re.findall(
        r"(?:^|\n)\s*(?:\d+[\.\)]\s*)?([A-Z][^\n–—\-:]{3,60})\s*[:\-–—]\s*([^\n]{15,220})",
        block or text,
    )
    for post, detail in numbered:
        if any(kw in post.lower() for kw in ("qualification", "age", "fee", "note", "important")):
            continue
        post_clean = _clean_line(post)[:120]
        detail_clean = _clean_line(detail)[:250]
        if not is_plausible_post_name(post_clean):
            continue
        if not is_plausible_qualification(detail_clean):
            continue
        exp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|yr)s?\s+(?:of\s+)?experience", detail, re.I)
        rows.append(
            {
                "post": post_clean,
                "education": detail_clean,
                "experience": exp_match.group(0) if exp_match else "As per notification",
                "other": "",
            }
        )

    # Merge vacancy row qualifications
    for vr in vacancy_rows or []:
        qual = str(vr.get("qualification") or "").strip()
        post = str(vr.get("post") or "").strip()
        if not post:
            continue
        existing = next((r for r in rows if r["post"].lower()[:20] == post.lower()[:20]), None)
        if existing:
            if qual and qual.lower() not in existing["education"].lower():
                existing["education"] = qual if not existing["education"] else f"{existing['education']}; {qual}"
        elif qual:
            rows.append(
                {
                    "post": post[:120],
                    "education": qual[:250],
                    "experience": "As per notification",
                    "other": "",
                }
            )

    if not rows and global_qual and is_plausible_qualification(global_qual):
        post = "All posts"
        if vacancy_rows:
            first_post = str(vacancy_rows[0].get("post") or "").strip()
            if first_post and is_plausible_post_name(first_post):
                post = first_post[:120]
        exp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:year|yr)s?\s+(?:of\s+)?experience", global_qual, re.I)
        rows.append(
            {
                "post": post,
                "education": global_qual[:250],
                "experience": exp_match.group(0) if exp_match else "As per notification",
                "other": "",
            }
        )

    return filter_eligibility_rows(rows)


def extract_application_fee_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    fee_block = _extract_block(text, re.compile(r"(?:application\s+fee|exam\s+fee|fee\s+structure)", re.I), 1200)
    source = fee_block or text

    patterns = [
        (r"(?:general|ur/unreserved|unreserved|all\s+categories)[^₹Rs\d]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "General / UR"),
        (r"\bOBC\b[^₹Rs\d\n]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "OBC"),
        (r"\bEWS\b[^₹Rs\d\n]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "EWS"),
        (r"\bSC\b[^₹Rs/ST]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "SC"),
        (r"\bST\b[^₹Rs\d\n]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "ST"),
        (r"(?:PwD|PwBD|PH|disabled)[^₹Rs\d\n]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "PwD"),
        (r"(?:female|women)[^₹Rs\d\n]{0,20}([₹Rs\.]+\s*[\d,]+|nil|exempted|free)", "Women"),
    ]
    for pattern, label in patterns:
        match = re.search(pattern, source, re.I)
        if match:
            rows.append((label, _clean_line(match.group(1))[:80]))

    if not rows:
        single = re.search(r"(?:application fee|exam fee)[:\s]*([^\n]{5,100})", text, re.I)
        if single:
            val = _clean_line(single.group(1))[:80]
            if not re.search(r"\d{1,2}[./]\d{1,2}[./]\d{4}", val) and "upto" not in val.lower():
                rows.append(("General / UR", val))
    return filter_fee_rows(rows)


def extract_selection_steps(text: str) -> list[str]:
    block = _extract_block(text, _SELECTION_HEADERS, max_chars=2000)
    if not block:
        return []

    steps = _split_bullets(block)
    if steps:
        return steps[:10]

    # Inline comma/semicolon separated
    inline = re.search(
        r"(?:selection process|mode of selection)[^:\n]*:\s*([^\n]{20,400})",
        text,
        re.I,
    )
    if inline:
        parts = re.split(r"[;,]\s*(?=[A-Z])", inline.group(1))
        return [_clean_line(p) for p in parts if len(_clean_line(p)) >= 8][:10]
    return []


def extract_reservation_notes(text: str) -> list[str]:
    block = _extract_block(text, _RESERVATION_HEADERS, max_chars=1500)
    if not block:
        # Fallback: common reservation phrases
        notes: list[str] = []
        for pattern in (
            r"(\d+\s*%?\s*(?:vacancies|posts)?\s*(?:reserved|allotted)\s*(?:for|to)\s*[^\n]{5,80})",
            r"(horizontal\s+reservation[^\n]{5,120})",
            r"(women\s+reservation[^\n]{5,120})",
            r"(ex[\-\s]?servicemen\s+quota[^\n]{5,120})",
        ):
            match = re.search(pattern, text, re.I)
            if match:
                notes.append(_clean_line(match.group(1))[:200])
        return notes[:8]

    return _split_bullets(block)[:8]


def extract_special_notes(text: str) -> list[str]:
    block = _extract_block(
        text,
        re.compile(r"(?:important\s+(?:instruction|note|information)|general\s+instruction|note\s*:|disclaimer)", re.I),
        1800,
    )
    if block:
        return _split_bullets(block)[:8]

    notes: list[str] = []
    for pattern in (
        r"(only\s+online\s+application[^\n]{0,80})",
        r"(one\s+candidate\s+(?:may|can)\s+apply[^\n]{0,100})",
        r"(document\s+verification[^\n]{0,100})",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            notes.append(_clean_line(match.group(1))[:200])
    return notes[:6]


def extract_exam_and_event_dates(text: str) -> list[dict[str, str]]:
    """Extract exam, PET, admit card, result and correction dates."""
    extra: list[dict[str, str]] = []
    patterns: list[tuple[str, str, str]] = [
        ("Written Examination", "लिखित परीक्षा", r"(?:written\s+(?:examination|exam|test)|C(?:BT|PET)|computer\s+based|लिखित\s+परीक्षा)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Physical Efficiency Test (PET)", "शारीरिक दक्षता परीक्षा", r"(?:physical\s+(?:efficiency|standard)\s+test|PET|PST|शारीरिक\s+दक्षता)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Skill / Trade Test", "कौशल परीक्षा", r"(?:skill\s+test|trade\s+test|कौशल\s+परीक्षा)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Interview", "साक्षात्कार", r"(?:interview|viva\s+voce|साक्षात्कार)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Admit Card Release", "प्रवेश पत्र", r"(?:admit\s+card|hall\s+ticket|प्रवेश\s+पत्र)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Result Declaration", "परिणाम", r"(?:result(?:\s+declaration)?|परिणाम\s*घोषणा|परिणाम)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Correction Window", "संशोधन अवधि", r"(?:correction\s+(?:window|period|date)|संशोधन\s+अवधि)[^0-9\n]{0,50}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
        ("Exam Date", "परीक्षा तिथि", r"(?:date\s+of\s+(?:examination|exam)|exam\s+date|परीक्षा\s+तिथि)[^0-9\n]{0,40}(\d{1,2}[./-]\d{1,2}[./-]\d{4})"),
    ]
    seen_labels: set[str] = set()
    for label, label_hi, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            date_str = match.group(1).replace("-", "/").replace(".", "/")
            if label not in seen_labels:
                extra.append({"label": label, "label_hi": label_hi, "date": date_str})
                seen_labels.add(label)
    return extra


def extract_syllabus_info(text: str, links: Optional[list[tuple[str, str]]] = None) -> dict[str, Optional[str]]:
    syllabus_url: Optional[str] = None
    note: Optional[str] = None

    for label, url in links or []:
        lower = label.lower()
        if any(kw in lower for kw in ("syllabus", "exam pattern", "scheme of exam", "pariksha")):
            syllabus_url = url
            break

    if not syllabus_url:
        match = re.search(r"(https?://[^\s\)]+\.pdf)", text, re.I)
        if match and "syllabus" in text[max(0, match.start() - 80) : match.start()].lower():
            syllabus_url = match.group(1)

    block = _extract_block(text, re.compile(r"(?:syllabus|exam\s+pattern|scheme\s+of\s+examination)", re.I), 800)
    if block:
        note = _clean_line(block)[:300]
    elif "syllabus" in text.lower():
        note = "Syllabus available in official notification — see documents below."

    return {"syllabus_url": syllabus_url, "syllabus_note": note}


def enrich_from_full_text(
    text: str,
    *,
    vacancy_rows: Optional[list[dict[str, Any]]] = None,
    document_links: Optional[list[tuple[str, str]]] = None,
    existing_dates: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """Parse full advertisement/notification text into structured recruitment fields."""
    if not text or len(text.strip()) < 40:
        return {}

    result: dict[str, Any] = {}

    qual = extract_qualification_summary(text)
    if qual:
        result["qualification"] = qual

    age_limit = extract_age_limit(text)
    if age_limit:
        result["age_limit"] = age_limit

    age_relax = extract_age_relaxation(text)
    if age_relax:
        result["age_relaxation"] = age_relax

    elig_rows = extract_eligibility_rows(text, vacancy_rows)
    if elig_rows:
        result["eligibility_rows"] = elig_rows

    fee_rows = extract_application_fee_rows(text)
    if fee_rows:
        result["application_fee_rows"] = fee_rows
        result["application_fee"] = fee_rows[0][1]

    selection = extract_selection_steps(text)
    if selection:
        result["selection_steps"] = selection

    reservation = extract_reservation_notes(text)
    if reservation:
        result["reservation"] = reservation

    notes = extract_special_notes(text)
    if notes:
        result["special_notes"] = notes

    extra_dates = extract_exam_and_event_dates(text)
    if extra_dates:
        merged = list(existing_dates or [])
        existing_labels = {d.get("label", "").lower() for d in merged}
        for d in extra_dates:
            if d["label"].lower() not in existing_labels:
                merged.append(d)
        result["dates"] = merged

        for d in extra_dates:
            if "exam" in d["label"].lower() and "admit" not in d["label"].lower():
                result["exam_date"] = d["date"]
                break

    syllabus = extract_syllabus_info(text, document_links)
    if syllabus.get("syllabus_url"):
        result["syllabus_url"] = syllabus["syllabus_url"]
    if syllabus.get("syllabus_note"):
        result["syllabus_note"] = syllabus["syllabus_note"]

    title_hi = extract_hindi_title(text)
    if title_hi:
        result["title_hi"] = title_hi
    overview_hi = extract_hindi_overview(text)
    if overview_hi:
        result["overview_hi"] = overview_hi

    # Attach per-post qualification to vacancy rows when missing
    if vacancy_rows and elig_rows:
        for vr in vacancy_rows:
            if vr.get("qualification"):
                continue
            post_lower = str(vr.get("post", "")).lower()
            for er in elig_rows:
                if er["post"].lower()[:15] in post_lower or post_lower[:15] in er["post"].lower():
                    vr["qualification"] = er["education"][:200]
                    break
        result["vacancy_rows"] = vacancy_rows

    return result
