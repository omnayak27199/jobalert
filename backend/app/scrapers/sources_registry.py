from __future__ import annotations

"""Three-tier source registry: Central Govt | State-wise | PSU."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class SourceConfig:
    name: str
    url: str
    state: Optional[str] = None
    category: str = "government"
    paths: List[str] = field(default_factory=lambda: ["/"])
    organization: Optional[str] = None
    scope: str = "central"
    fallback: List[Tuple[str, str]] = field(default_factory=list)
    tier: str = "central"  # central | state | psu


@dataclass
class StateSourceGroup:
    """All government recruitment sites for one state/UT."""

    state: str
    sites: List[SourceConfig] = field(default_factory=list)


# ── List 1: All-India Central Government ─────────────────────────────────────

CENTRAL_GOVERNMENT_SOURCES: List[SourceConfig] = [
    SourceConfig(
        "UPSC", "https://upsc.gov.in", scope="all_india", category="government",
        organization="UPSC", tier="central",
        paths=["/", "/en/Examination/ActiveExams"],
    ),
    SourceConfig(
        "SSC", "https://ssc.nic.in", scope="all_india", category="government",
        organization="SSC", tier="central",
    ),
    SourceConfig(
        "RRB", "https://rrbcdg.gov.in", scope="all_india", category="government",
        organization="RRB", tier="central",
    ),
    SourceConfig(
        "IBPS", "https://www.ibps.in", scope="all_india", category="government",
        organization="IBPS", tier="central",
    ),
    SourceConfig(
        "Employment News", "https://employmentnews.gov.in", scope="all_india",
        category="government", organization="Employment News", tier="central",
    ),
    SourceConfig(
        "KVS", "https://kvsangathan.nic.in", scope="all_india", category="education",
        organization="KVS", tier="central",
    ),
    SourceConfig(
        "NVS", "https://navodaya.gov.in", scope="all_india", category="education",
        organization="NVS", tier="central",
    ),
    SourceConfig(
        "AIIMS", "https://www.aiims.edu", scope="all_india", category="government",
        organization="AIIMS", tier="central",
    ),
    SourceConfig(
        "EPFO", "https://www.epfindia.gov.in", scope="all_india", category="government",
        organization="EPFO", tier="central",
    ),
    SourceConfig(
        "Income Tax", "https://www.incometaxindia.gov.in", scope="all_india",
        category="government", organization="Income Tax", tier="central",
    ),
    SourceConfig(
        "DRDO", "https://www.drdo.gov.in", scope="all_india", category="defence",
        organization="DRDO", tier="central",
    ),
    SourceConfig(
        "NTA", "https://nta.ac.in", scope="all_india", category="government",
        organization="NTA", tier="central",
    ),
]

# ── List 3: PSUs (Public Sector Undertakings) ────────────────────────────────

PSU_SOURCES: List[SourceConfig] = [
    SourceConfig("ISRO", "https://www.isro.gov.in", scope="all_india", category="psu",
        organization="ISRO", tier="psu", paths=["/", "/Careers"]),
    SourceConfig("NTPC", "https://careers.ntpc.co.in", scope="all_india", category="psu",
        organization="NTPC", tier="psu"),
    SourceConfig("ONGC", "https://ongcindia.com", scope="all_india", category="psu",
        organization="ONGC", tier="psu"),
    SourceConfig("BHEL", "https://careers.bhel.in", scope="all_india", category="psu",
        organization="BHEL", tier="psu"),
    SourceConfig("HAL", "https://hal-india.co.in", scope="all_india", category="psu",
        organization="HAL", tier="psu"),
    SourceConfig("IOCL", "https://iocl.com", scope="all_india", category="psu",
        organization="IOCL", tier="psu"),
    SourceConfig("SBI", "https://www.sbi.co.in", scope="all_india", category="psu",
        organization="SBI", tier="psu", paths=["/web/careers"]),
    SourceConfig("PNB", "https://www.pnbindia.in", scope="all_india", category="psu",
        organization="PNB", tier="psu", paths=["/recruitment.html"]),
    SourceConfig("AAI", "https://www.aai.aero", scope="all_india", category="psu",
        organization="AAI", tier="psu", paths=["/en/careers"]),
    SourceConfig("ECIL", "https://www.ecil.co.in", scope="all_india", category="psu",
        organization="ECIL", tier="psu"),
    SourceConfig("BPCL", "https://www.bharatpetroleum.in", scope="all_india", category="psu",
        organization="BPCL", tier="psu"),
]

# ── List 2: State-wise government sites ──────────────────────────────────────

_STATE_SITES: List[SourceConfig] = [
    SourceConfig("APPSC", "https://psc.ap.gov.in", "Andhra Pradesh", "state_psc",
        organization="APPSC", scope="state", tier="state"),
    SourceConfig("APSSB", "https://apssb.nic.in", "Arunachal Pradesh", "state_psc",
        organization="APSSB", scope="state", tier="state"),
    SourceConfig("APSC", "https://apsc.nic.in", "Assam", "state_psc",
        organization="APSC", scope="state", tier="state"),
    SourceConfig("BPSC", "https://bpsc.bih.nic.in", "Bihar", "state_psc",
        organization="BPSC", scope="state", tier="state"),
    SourceConfig("CG Vyapam", "https://vyapamcg.cgstate.gov.in", "Chhattisgarh", "state_psc",
        organization="CG Vyapam (CGSSB)", scope="state", tier="state",
        paths=["/", "/Posts?tag=ONLINEAPPLICATION"]),
    SourceConfig("CGPSC", "https://psc.cg.gov.in", "Chhattisgarh", "state_psc",
        organization="CGPSC", scope="state", tier="state"),
    SourceConfig("Goa PSC", "https://goapsc.gov.in", "Goa", "state_psc",
        organization="Goa PSC", scope="state", tier="state"),
    SourceConfig("GPSC", "https://gpsc.gujarat.gov.in", "Gujarat", "state_psc",
        organization="GPSC", scope="state", tier="state"),
    SourceConfig("HPSC", "https://hpsc.gov.in", "Haryana", "state_psc",
        organization="HPSC", scope="state", tier="state"),
    SourceConfig("HPPSC", "https://hppsc.hp.gov.in", "Himachal Pradesh", "state_psc",
        organization="HPPSC", scope="state", tier="state"),
    SourceConfig("JPSC", "https://jpsc.gov.in", "Jharkhand", "state_psc",
        organization="JPSC", scope="state", tier="state"),
    SourceConfig("KPSC", "https://kpsc.kar.nic.in", "Karnataka", "state_psc",
        organization="KPSC", scope="state", tier="state"),
    SourceConfig("Kerala PSC", "https://keralapsc.gov.in", "Kerala", "state_psc",
        organization="Kerala PSC", scope="state", tier="state"),
    SourceConfig("MPPSC", "https://mppsc.mp.gov.in", "Madhya Pradesh", "state_psc",
        organization="MPPSC", scope="state", tier="state"),
    SourceConfig("MPSC", "https://mpsc.gov.in", "Maharashtra", "state_psc",
        organization="MPSC", scope="state", tier="state"),
    SourceConfig("Manipur PSC", "https://mpscmanipur.gov.in", "Manipur", "state_psc",
        organization="Manipur PSC", scope="state", tier="state"),
    SourceConfig("Meghalaya PSC", "https://megpsc.gov.in", "Meghalaya", "state_psc",
        organization="Meghalaya PSC", scope="state", tier="state"),
    SourceConfig("Mizoram PSC", "https://mizoram.gov.in/portal", "Mizoram", "state_psc",
        organization="Mizoram PSC", scope="state", tier="state"),
    SourceConfig("Nagaland PSC", "https://npsc.nagaland.gov.in", "Nagaland", "state_psc",
        organization="Nagaland PSC", scope="state", tier="state"),
    SourceConfig("OPSC", "https://opsc.gov.in", "Odisha", "state_psc",
        organization="OPSC", scope="state", tier="state"),
    SourceConfig("OSSSC", "https://osssc.gov.in", "Odisha", "state_psc",
        organization="OSSSC", scope="state", tier="state"),
    SourceConfig("PPSC", "https://ppsc.gov.in", "Punjab", "state_psc",
        organization="PPSC", scope="state", tier="state"),
    SourceConfig("RPSC", "https://rpsc.rajasthan.gov.in", "Rajasthan", "state_psc",
        organization="RPSC", scope="state", tier="state"),
    SourceConfig("Sikkim PSC", "https://spscskm.gov.in", "Sikkim", "state_psc",
        organization="Sikkim PSC", scope="state", tier="state"),
    SourceConfig("TNPSC", "https://tnpsc.gov.in", "Tamil Nadu", "state_psc",
        organization="TNPSC", scope="state", tier="state"),
    SourceConfig("TSPSC", "https://tspsc.gov.in", "Telangana", "state_psc",
        organization="TSPSC", scope="state", tier="state"),
    SourceConfig("Tripura PSC", "https://tpsc.tripura.gov.in", "Tripura", "state_psc",
        organization="Tripura PSC", scope="state", tier="state"),
    SourceConfig("UPPSC", "https://uppsc.up.nic.in", "Uttar Pradesh", "state_psc",
        organization="UPPSC", scope="state", tier="state"),
    SourceConfig("UPSSSC", "https://upsssc.gov.in", "Uttar Pradesh", "state_psc",
        organization="UPSSSC", scope="state", tier="state"),
    SourceConfig("UKPSC", "https://ukpsc.gov.in", "Uttarakhand", "state_psc",
        organization="UKPSC", scope="state", tier="state"),
    SourceConfig("WBPSC", "https://wbpsc.gov.in", "West Bengal", "state_psc",
        organization="WBPSC", scope="state", tier="state"),
    SourceConfig("DSSSB", "https://dsssb.delhi.gov.in", "Delhi", "state_psc",
        organization="DSSSB", scope="state", tier="state"),
    SourceConfig("JKSSB", "https://jkssb.nic.in", "Jammu and Kashmir", "state_psc",
        organization="JKSSB", scope="state", tier="state"),
    SourceConfig("Ladakh Admin", "https://ladakh.gov.in", "Ladakh", "state_psc",
        organization="Ladakh", scope="state", tier="state"),
    SourceConfig("Puducherry PSC", "https://puducherry.gov.in", "Puducherry", "state_psc",
        organization="Puducherry PSC", scope="state", tier="state"),
]


def _build_state_groups(sites: List[SourceConfig]) -> List[StateSourceGroup]:
    grouped: dict[str, List[SourceConfig]] = {}
    for site in sites:
        state = site.state or "Unknown"
        grouped.setdefault(state, []).append(site)
    return [
        StateSourceGroup(state=state, sites=sorted(sites, key=lambda s: s.name))
        for state, sites in sorted(grouped.items())
    ]


STATE_SOURCE_GROUPS: List[StateSourceGroup] = _build_state_groups(_STATE_SITES)

# Flat list of all state sites (for scraper iteration)
STATE_GOVERNMENT_SOURCES: List[SourceConfig] = list(_STATE_SITES)

# ── Combined / legacy exports ────────────────────────────────────────────────

ALL_GOVERNMENT_SOURCES: List[SourceConfig] = (
    CENTRAL_GOVERNMENT_SOURCES + STATE_GOVERNMENT_SOURCES + PSU_SOURCES
)

# Backward-compatible aliases
CENTRAL_SOURCES = CENTRAL_GOVERNMENT_SOURCES
STATE_PSC_SOURCES = STATE_GOVERNMENT_SOURCES


def get_all_fetch_sources() -> List[SourceConfig]:
    """Return sources in fetch order: central → state → PSU."""
    return CENTRAL_GOVERNMENT_SOURCES + STATE_GOVERNMENT_SOURCES + PSU_SOURCES


def get_sources_by_state(state: str) -> List[SourceConfig]:
    return [s for s in ALL_GOVERNMENT_SOURCES if s.state == state]


def get_state_group(state: str) -> Optional[StateSourceGroup]:
    for group in STATE_SOURCE_GROUPS:
        if group.state == state:
            return group
    return None


def registry_stats() -> dict:
    return {
        "central_government_sites": len(CENTRAL_GOVERNMENT_SOURCES),
        "state_groups": len(STATE_SOURCE_GROUPS),
        "state_government_sites": len(STATE_GOVERNMENT_SOURCES),
        "psu_sites": len(PSU_SOURCES),
        "total_sources": len(ALL_GOVERNMENT_SOURCES),
        "states_covered": len(STATE_SOURCE_GROUPS),
    }
