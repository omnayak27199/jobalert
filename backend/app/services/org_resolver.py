from __future__ import annotations

"""Normalize organization names from job titles."""

import re

# Title keyword → canonical organization (checked before generic abbreviations)
TITLE_ORG_PATTERNS: list[tuple[str, list[str]]] = [
    ("CG Vyapam (CGSSB)", [r"\bcg\s*vyapam\b", r"\bcgssb\b", r"\bvyapam\b.*\bcg\b"]),
    ("UPSC", [r"\bupsc\b"]),
    ("SSC", [r"\bssc\b"]),
    ("RRB", [r"\brrb\b"]),
    ("IBPS", [r"\bibps\b"]),
    ("NTPC", [r"\bntpc\b"]),
    ("ISRO", [r"\bisro\b"]),
    ("SBI", [r"\bsbi\b"]),
    ("PNB", [r"\bpnb\b"]),
    ("AAI", [r"\baai\b"]),
    ("CGPSC", [r"\bcgpsc\b"]),
    ("UPPSC", [r"\buppsc\b"]),
    ("TNPSC", [r"\btnpsc\b"]),
    ("KPSC", [r"\bkpsc\b"]),
]


def normalize_organization(title: str, organization: str = "") -> str:
    """Return canonical organization; avoid bare 'CG' for CG Vyapam posts."""
    combined = f"{title} {organization}"
    for canonical, patterns in TITLE_ORG_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return canonical

    org = organization.strip()
    if org.upper() in {"CG", "CG."} and "vyapam" in title.lower():
        return "CG Vyapam (CGSSB)"

    return org or "Government"
