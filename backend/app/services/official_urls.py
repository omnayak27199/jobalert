from __future__ import annotations

"""Map organizations to official government portal URLs — never link to aggregators."""

from typing import Optional

# Official recruitment portals by organization abbreviation
OFFICIAL_PORTALS: dict[str, str] = {
    "UPSC": "https://upsc.gov.in",
    "SSC": "https://ssc.nic.in",
    "RRB": "https://www.rrbcdg.gov.in",
    "IBPS": "https://www.ibps.in",
    "SBI": "https://www.sbi.co.in/careers",
    "PNB": "https://www.pnbindia.in/recruitment.html",
    "BOB": "https://www.bankofbaroda.in/careers",
    "ISRO": "https://www.isro.gov.in/Careers",
    "DRDO": "https://www.drdo.gov.in/drdo/en/recruitment",
    "NTPC": "https://careers.ntpc.co.in",
    "ONGC": "https://ongcindia.com/wps/portal/ongc/recruitment",
    "BHEL": "https://careers.bhel.in",
    "HAL": "https://hal-india.co.in/Careers",
    "IOCL": "https://iocl.com/job-recruitments",
    "UPPSC": "https://uppsc.up.nic.in",
    "UPSSSC": "https://upsssc.gov.in",
    "MPPSC": "https://mppsc.mp.gov.in",
    "RPSC": "https://rpsc.rajasthan.gov.in",
    "BPSC": "https://bpsc.bih.nic.in",
    "TNPSC": "https://tnpsc.gov.in",
    "TSPSC": "https://tspsc.gov.in",
    "KPSC": "https://kpsc.kar.nic.in",
    "MPSC": "https://mpsc.gov.in",
    "WBPSC": "https://wbpsc.gov.in",
    "GPSC": "https://gpsc.gujarat.gov.in",
    "HPSC": "https://hpsc.gov.in",
    "HPPSC": "https://hppsc.hp.gov.in",
    "OPSC": "https://opsc.gov.in",
    "OSSSC": "https://osssc.gov.in",
    "UKPSC": "https://ukpsc.gov.in",
    "APPSC": "https://psc.ap.gov.in",
    "Kerala PSC": "https://keralapsc.gov.in",
    "CGPSC": "https://psc.cg.gov.in",
    "CG Vyapam": "https://vyapamcg.cgstate.gov.in",
    "CGSSB": "https://vyapamcg.cgstate.gov.in",
    "JPSC": "https://jpsc.gov.in",
    "PPSC": "https://ppsc.gov.in",
    "DSSSB": "https://dsssb.delhi.gov.in",
    "JKSSB": "https://jkssb.nic.in",
    "KVS": "https://kvsangathan.nic.in/recruitment.html",
    "NVS": "https://navodaya.gov.in/nvs/en/Recruitment",
    "AIIMS": "https://www.aiims.edu/en/recruitment.html",
    "EPFO": "https://www.epfindia.gov.in/site_en/recruitment.php",
    "AAI": "https://www.aai.aero/en/careers",
    "ITBP": "https://rectt.itbpolice.nic.in",
    "NFR": "https://nfr.indianrailways.gov.in",
    "ICF": "https://icf.indianrailways.gov.in",
}

# Title keywords → official portal (checked first)
TITLE_PORTAL_KEYWORDS: list[tuple[str, str]] = [
    ("vyapam", "https://vyapamcg.cgstate.gov.in"),
    ("cgssb", "https://vyapamcg.cgstate.gov.in"),
]

AGGREGATOR_DOMAINS = (
    "freejobalert.com",
    "sarkariresult.com",
    "rojgarresult.com",
    "governmentjobsalert.in",
    "sarkariresultsin.info",
)


def is_aggregator_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    if any(d in lower for d in AGGREGATOR_DOMAINS):
        return True
    if "play.google.com" in lower and "freejobalert" in lower:
        return True
    return False


def resolve_official_url(organization: str, title: str = "", fallback: Optional[str] = None) -> str:
    """Return official portal URL for an organization."""
    combined = f"{organization} {title}".lower()
    for keyword, url in TITLE_PORTAL_KEYWORDS:
        if keyword in combined:
            return url

    org_upper = organization.upper().strip()
    # Longest key match first to avoid CG matching CGPSC before CG Vyapam
    for key in sorted(OFFICIAL_PORTALS, key=len, reverse=True):
        url = OFFICIAL_PORTALS[key]
        key_upper = key.upper()
        if key_upper in org_upper or org_upper in key_upper:
            return url

    title_upper = title.upper()
    for key in sorted(OFFICIAL_PORTALS, key=len, reverse=True):
        if key.upper() in title_upper:
            return OFFICIAL_PORTALS[key]

    if fallback and not is_aggregator_url(fallback):
        return fallback
    return "https://www.employmentnews.gov.in"


# Online application portals (may differ from notification site)
OFFICIAL_APPLY_PORTALS: dict[str, str] = {
    "DSSSB": "https://dsssbonline.nic.in/",
    "TRIPURA PSC": "https://tpsc.tripura.gov.in/",
    "TPSC": "https://tpsc.tripura.gov.in/",
}


def resolve_apply_url(organization: str, title: str = "") -> Optional[str]:
    combined = f"{organization} {title}".upper()
    for key, url in OFFICIAL_APPLY_PORTALS.items():
        if key.upper() in combined:
            return url
    return None


def sanitize_external_url(
    url: Optional[str],
    organization: str = "",
    title: str = "",
) -> Optional[str]:
    """Return url only if it is official; otherwise resolve official portal."""
    if not url or url.startswith("official://"):
        return resolve_official_url(organization, title) if organization else None
    if url.startswith("pdf://"):
        return url
    if is_aggregator_url(url):
        return resolve_official_url(organization, title)
    return url
