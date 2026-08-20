from __future__ import annotations

"""Structured recruitment sections for rich job detail pages."""

import json
from typing import Any, Optional

CG_VYAPAM_POST_CONTENT: dict[str, dict] = {
    "NSSK26ONLINE": {
        "title": "Nagar Sena, Fire & Emergency Services & SDRF — Recruitment",
        "title_hi": "नगर सेना, अग्निशमन एवं आपातकालीन सेवाएँ तथा एसडीआरएफ — भर्ती विज्ञापन",
        "organization": "CG Vyapam (CGSSB) — Chhattisgarh Fire & Emergency Services / SDRF",
        "advertisement_no": "712-713 / Sta-3/Bharti/2025, Raipur, dated 12/06/2025",
        "vacancies": 295,
        "last_date": "31 July 2025",
        "start_date": "01 July 2025",
        "qualification_summary": (
            "Post-wise qualification — see eligibility table below"
        ),
        "age_limit": "18–28 years (as on 01.01.2025)",
        "age_relaxation": (
            "General +5 years for all (CG GAD order); SC/ST/OBC/EWS/women/ex-servicemen "
            "as per state rules; maximum 45 years after all relaxations"
        ),
        "application_fee_rows": [
            ("General / Unreserved", "As per official notification"),
            ("OBC", "As per official notification"),
            ("SC / ST / PwD", "As per official notification"),
        ],
        "overview": (
            "Chhattisgarh Fire & Emergency Services and SDRF invites online applications "
            "from local residents of Chhattisgarh to fill 295 vacancies under Third Class "
            "Non-Gazetted Executive Service Recruitment Rules, 2017. "
            "Only online applications accepted — no manual/postal forms. "
            "One candidate may apply for only ONE post."
        ),
        "overview_hi": (
            "छत्तीसगढ़ अग्निशमन एवं आपातकालीन सेवा तथा राज्य आपदा मोचन बल में "
            "295 रिक्त पदों हेतु छत्तीसगढ़ के स्थानीय निवासियों से ऑनलाइन आवेदन आमंत्रित। "
            "केवल ऑनलाइन आवेदन — एक अभ्यर्थी केवल एक पद हेतु आवेदन कर सकता है।"
        ),
        "vacancy_rows": [
            {"sr": "01", "post": "Station Officer (Sub Inspector)", "post_hi": "स्टेशन ऑफिसर (उप निरीक्षक)", "vacancies": 21, "pay_level": "Level-7", "pay_scale": "₹44,900 – ₹1,42,400", "qualification": "Graduate + as per notification"},
            {"sr": "02", "post": "Vehicle Driver", "post_hi": "वाहन चालक", "vacancies": 14, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 + Valid HMV Driving Licence"},
            {"sr": "03", "post": "Driver-cum-Operator", "post_hi": "वाहन चालक कम ऑपरेटर", "vacancies": 86, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 + Valid HMV Driving Licence"},
            {"sr": "04", "post": "Fireman", "post_hi": "फायर मेन", "vacancies": 117, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 / Higher Secondary"},
            {"sr": "05", "post": "Store Keeper", "post_hi": "स्टोर कीपर", "vacancies": 32, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 / Higher Secondary"},
            {"sr": "06", "post": "Mechanic", "post_hi": "मैकेनिक", "vacancies": 2, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 + ITI (Diesel Mechanic)"},
            {"sr": "07", "post": "Watchroom Operator", "post_hi": "वाचरूम ऑपरेटर", "vacancies": 19, "pay_level": "Level-4", "pay_scale": "₹25,500 – ₹81,100", "qualification": "10+2 + Trained Nagar Sainik (3 yrs service)"},
            {"sr": "08", "post": "Wireless Operator (Contract)", "post_hi": "वायरलैस ऑपरेटर (संविदा)", "vacancies": 4, "pay_level": "Contract", "pay_scale": "Lump-sum monthly contract", "qualification": "Trained Nagar Sainik (3 yrs service)"},
        ],
        "eligibility_rows": [
            {"post": "Station Officer", "education": "Graduate degree from recognized university", "experience": "As per detailed notification", "other": "CG local resident"},
            {"post": "Vehicle Driver / Driver-cum-Operator", "education": "10+2 or Higher Secondary", "experience": "—", "other": "Valid HMV driving licence"},
            {"post": "Fireman", "education": "10+2 or Higher Secondary", "experience": "—", "other": "CG local resident; PET required"},
            {"post": "Store Keeper", "education": "10+2 or Higher Secondary", "experience": "—", "other": "CG local resident"},
            {"post": "Mechanic", "education": "10+2 + ITI Diesel Mechanic", "experience": "—", "other": "CG local resident"},
            {"post": "Watchroom Operator", "education": "10+2 or Higher Secondary", "experience": "3 years as trained Nagar Sainik", "other": "Internal quota post"},
            {"post": "Wireless Operator (Contract)", "education": "As per notification", "experience": "3 years as trained Nagar Sainik", "other": "Contractual post"},
        ],
        "dates": [
            {"label": "Online Application Start", "label_hi": "ऑनलाइन आवेदन प्रारंभ", "date": "01.07.2025"},
            {"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": "31.07.2025"},
            {"label": "Correction Window", "label_hi": "संशोधन अवधि", "date": "10.08.2025"},
        ],
        "selection_steps": [
            "Online application on CG Vyapam portal",
            "Application fee payment (if applicable)",
            "Physical Efficiency Test (PET)",
            "Written examination (NSSK26)",
            "Trade / Skill test (for driver & technical posts)",
            "Document verification",
            "Final selection — 3 year probation for regular posts",
        ],
        "reservation": [
            "Category-wise reservation: UR / SC / ST / OBC / EWS — as per notification table",
            "Separate reservation for women",
            "Ex-servicemen quota",
            "Nagar Sainik quota (where applicable)",
        ],
        "special_notes": [
            "Watchroom Operator & Wireless Operator — only for trained Nagar Sainik with 3 years service",
            "Apply for ONE post only — multiple applications rejected",
            "Recruitment process at Raipur, Chhattisgarh",
        ],
        "syllabus_note": "Download official syllabus PDF from documents section below",
    },
}


def get_post_structured_content(post_id: str) -> Optional[dict]:
    key = post_id.split("PostID=")[-1].split("&")[0].upper() if "PostID=" in post_id else post_id.upper()
    return CG_VYAPAM_POST_CONTENT.get(key)


def build_generic_advertisement_sections(
    *,
    title: str,
    organization: str,
    state: Optional[str] = None,
    overview: Optional[str] = None,
    last_date: Optional[str] = None,
    start_date: Optional[str] = None,
    pdf_url: Optional[str] = None,
    apply_url: Optional[str] = None,
    vacancies: Optional[int] = None,
    qualification: Optional[str] = None,
    age_limit: Optional[str] = None,
    application_fee: Optional[str] = None,
    advertisement_no: Optional[str] = None,
    vacancy_rows: Optional[list[dict[str, Any]]] = None,
    dates: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """Build structured sections for jobs enriched from official portal pages."""
    pdf_links: list[tuple[str, str]] = []
    if pdf_url:
        pdf_links.append(("Official Notification PDF", pdf_url))
    if apply_url and apply_url != pdf_url:
        pdf_links.append(("Apply Online", apply_url))

    date_rows: list[dict[str, str]] = list(dates or [])
    if not date_rows:
        if start_date:
            date_rows.append({"label": "Application Start", "label_hi": "आवेदन प्रारंभ", "date": start_date})
        if last_date:
            date_rows.append({"label": "Last Date to Apply", "label_hi": "अंतिम तिथि", "date": last_date})

    rows = vacancy_rows or []
    total_vac = vacancies
    if not total_vac and rows:
        total_vac = sum(int(r.get("vacancies") or 0) for r in rows) or None

    summary = overview or (
        f"{organization} has published a recruitment notification. "
        "See post-wise vacancies, pay scale and eligibility below."
    )

    data: dict[str, Any] = {
        "title": title,
        "organization": organization,
        "advertisement_no": advertisement_no,
        "vacancies": total_vac,
        "overview": summary,
        "qualification_summary": qualification,
        "age_limit": age_limit,
        "application_fee_rows": (
            [("General", application_fee), ("SC/ST/OBC", "See notification")]
            if application_fee
            else []
        ),
        "dates": date_rows,
        "vacancy_rows": rows,
        "eligibility_rows": [],
    }
    return build_advertisement_sections(data, pdf_links)


def build_advertisement_sections(data: dict, pdf_links: list[tuple[str, str]]) -> dict[str, Any]:
    """Build JSON sections for frontend rendering."""
    documents = [{"label": label.strip(), "url": url} for label, url in pdf_links]

    syllabus_url = data.get("syllabus_url")
    for doc in documents:
        if "syllabus" in doc["label"].lower():
            syllabus_url = doc["url"]
            break

    notification_pdf = None
    for doc in documents:
        lower = doc["label"].lower()
        if "vigyapan" in lower or "advertisement" in lower or "notification" in lower:
            notification_pdf = doc["url"]
        if doc["url"].lower().endswith(".pdf") and not notification_pdf:
            notification_pdf = doc["url"]

    return {
        "title": data.get("title"),
        "title_hi": data.get("title_hi"),
        "organization": data.get("organization"),
        "advertisement_no": data.get("advertisement_no"),
        "total_vacancies": data.get("vacancies"),
        "overview": data.get("overview"),
        "overview_hi": data.get("overview_hi"),
        "vacancy_rows": data.get("vacancy_rows", []),
        "eligibility_rows": data.get("eligibility_rows", []),
        "age_limit": data.get("age_limit"),
        "age_relaxation": data.get("age_relaxation"),
        "application_fee_rows": data.get("application_fee_rows", []),
        "dates": data.get("dates", []),
        "selection_steps": data.get("selection_steps", []),
        "reservation": data.get("reservation", []),
        "special_notes": data.get("special_notes", []),
        "syllabus_url": syllabus_url,
        "syllabus_note": data.get("syllabus_note"),
        "documents": documents,
        "notification_pdf": notification_pdf,
    }


def sections_to_json(sections: dict[str, Any]) -> str:
    return json.dumps(sections, ensure_ascii=False)


def sections_from_json(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def structured_job_fields(data: dict) -> dict[str, Optional[str | int]]:
    return {
        "qualification": data.get("qualification_summary"),
        "age_limit": f"{data.get('age_limit', '')}. {data.get('age_relaxation', '')}".strip(". "),
        "application_fee": "Category-wise — see fee table on detail page",
        "vacancies": data.get("vacancies"),
        "last_date": data.get("last_date"),
        "organization": data.get("organization"),
    }


def build_structured_full_content(data: dict, pdf_links: list[tuple[str, str]]) -> str:
    """Minimal text fallback for search/legacy."""
    sections = build_advertisement_sections(data, pdf_links)
    return f"{sections.get('title', 'Recruitment')} — {sections.get('total_vacancies', '')} vacancies. See structured detail on page."
