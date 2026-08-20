from __future__ import annotations

"""AI/ML-inspired date extraction and job classification from raw text."""

import re
from datetime import datetime
from typing import NamedTuple

from dateutil import parser as date_parser

DATE_PATTERNS = [
    r"(?:last\s*date|closing\s*date|apply\s*(?:till|by|before)|end\s*date)\s*[:\-]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
    r"(?:last\s*date|closing\s*date)\s*[:\-]?\s*(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})",
    r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\s*(?:is\s*)?(?:last|closing)\s*date",
    r"(?:exam\s*date|date\s*of\s*exam)\s*[:\-]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
    r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})",
    # Hindi date labels (Devanagari)
    r"(?:अंतिम\s*तिथि|आवेदन\s*(?:की\s*)?अंतिम\s*(?:तिथि|दिनांक)|अंत\s*तिथि)[^0-9]{0,30}(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
    r"(?:आवेदन\s*प्रारंभ|ऑनलाइन\s*आवेदन\s*(?:प्रारंभ|शुरू)|आवेदन\s*शुरू)[^0-9]{0,30}(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
    r"(?:परीक्षा\s*तिथि|लिखित\s*परीक्षा)[^0-9]{0,30}(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})",
]

VACANCY_PATTERN = re.compile(
    r"(\d{1,6})\s*(?:vacanc(?:y|ies)|posts?|positions?|openings?|पद|रिक्त(?:ि|िय(?:ाँ|ां))?)",
    re.IGNORECASE,
)

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "admit_card": ["admit card", "hall ticket", "call letter", "intimation slip", "प्रवेश पत्र"],
    "result": ["result", "merit list", "cut off", "cutoff", "selected list", "परिणाम"],
    "answer_key": ["answer key", "response sheet", "omr sheet", "उत्तर कुंजी"],
    "syllabus": ["syllabus", "exam pattern", "selection process", "पाठ्यक्रम", "परीक्षा पैटर्न"],
    "education": ["admission", "counselling", "seat allotment", "entrance exam", "neet", "jee", "cuet"],
    "notification": [
        "online form", "recruitment", "notification", "apply online", "vacancy",
        "भर्ती", "विज्ञापन", "अधिसूचना", "आवेदन", "रिक्त",
    ],
}

STATE_NAMES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry", "Chandigarh",
]

STATE_ABBREVS = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana",
    "HP": "Himachal Pradesh", "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala",
    "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya",
    "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TS": "Telangana",
    "TR": "Tripura", "UP": "Uttar Pradesh", "UK": "Uttarakhand", "WB": "West Bengal",
    "DL": "Delhi", "JK": "Jammu and Kashmir", "LA": "Ladakh",
}


class ExtractedDates(NamedTuple):
    last_date: datetime | None
    exam_date: datetime | None
    published_date: datetime | None
    is_verified: bool


def _parse_date(text: str) -> datetime | None:
    try:
        parsed = date_parser.parse(text, dayfirst=True, fuzzy=True)
        if parsed.year < 2020 or parsed.year > 2030:
            return None
        return parsed
    except (ValueError, OverflowError):
        return None


def extract_dates(text: str) -> ExtractedDates:
    """Extract and verify dates from job notification text."""
    text_lower = text.lower()
    last_date = None
    exam_date = None
    published_date = None

    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = _parse_date(match.group(1))
            if parsed:
                last_date = parsed
                break

    exam_match = re.search(DATE_PATTERNS[3], text, re.IGNORECASE)
    if not exam_match:
        exam_match = re.search(DATE_PATTERNS[7], text, re.IGNORECASE)
    if exam_match:
        exam_date = _parse_date(exam_match.group(1))

    is_verified = last_date is not None or exam_date is not None
    return ExtractedDates(last_date, exam_date, published_date, is_verified)


def classify_category(title: str, description: str = "") -> str:
    """ML-style keyword scoring for job category classification."""
    combined = f"{title} {description}".lower()
    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[category] = score

    if not scores:
        return "notification"
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def extract_vacancies(text: str) -> int | None:
    """Extract vacancy count from title or description."""
    match = VACANCY_PATTERN.search(text)
    if match:
        count = int(match.group(1))
        if 1 <= count <= 100000:
            return count
    title_match = re.search(r"^(\d{1,6})\s", text)
    if title_match:
        count = int(title_match.group(1))
        if 1 <= count <= 100000:
            return count
    return None


def detect_state(title: str, organization: str = "") -> str | None:
    """Detect Indian state from job title and organization."""
    combined = f"{title} {organization}"

    for state in STATE_NAMES:
        if state.lower() in combined.lower():
            return state

    for abbrev, state in STATE_ABBREVS.items():
        if re.search(rf"\b{abbrev}\b", combined):
            return state

    state_psc_pattern = re.search(
        r"(UPSC|SSC|RRB|IBPS|ISRO|DRDO|NTPC|AAI|ECIL|BHEL|HAL|IOCL|SBI|PNB|BOB)",
        combined,
        re.IGNORECASE,
    )
    if state_psc_pattern:
        return None

    return None


def extract_organization(title: str) -> str:
    """Extract organization name from job title."""
    org_patterns = [
        r"^(UPSC|SSC|RRB|IBPS|ISRO|DRDO|NTPC|AAI|ECIL|BHEL|HAL|IOCL|SBI|PNB|BOB|UPSC|UPSSSC|UPPSC|MPPSC|RPSC|TNPSC|KPSC|WBPSC|BPSC|HPSC|GPSC|OPSC|APSC|JPSC|UKPSC|CGPSC|CGSSB|HPPSC|MPESB|OSSSC|KVS|NVS|AIIMS|ESIC|ITBP|BSF|CRPF|CISF|SSB|Indian Army|Indian Navy|Indian Air Force)",
        r"^(CG\s*Vyapam|CGSSB)",
        r"^([A-Z]{2,6})\s+\d",
    ]
    for pattern in org_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    words = title.split()
    if words:
        return words[0]
    return "Government"
