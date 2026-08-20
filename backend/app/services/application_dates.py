from __future__ import annotations

"""Application deadline status — open, closed (grace period), or expired."""

from datetime import datetime, timedelta
from typing import Literal, Optional, TypedDict

# Show closed listings for this many days after last application date, then hide.
CLOSED_VISIBLE_DAYS = 7

ApplicationStatus = Literal["open", "closed", "unknown"]


class ApplicationWindow(TypedDict):
    status: ApplicationStatus
    days_left: Optional[int]
    days_since_closed: Optional[int]
    is_listable: bool


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def closed_visibility_cutoff(now: Optional[datetime] = None) -> datetime:
    """Jobs with last_date before this cutoff are hidden from listings."""
    now = now or datetime.utcnow()
    return _start_of_day(now) - timedelta(days=CLOSED_VISIBLE_DAYS)


def compute_application_window(
    last_date: Optional[datetime],
    now: Optional[datetime] = None,
) -> ApplicationWindow:
    now = now or datetime.utcnow()
    if not last_date:
        return {
            "status": "unknown",
            "days_left": None,
            "days_since_closed": None,
            "is_listable": True,
        }

    last_day = _start_of_day(last_date)
    today = _start_of_day(now)
    delta_days = (last_day - today).days

    if delta_days >= 0:
        return {
            "status": "open",
            "days_left": delta_days,
            "days_since_closed": None,
            "is_listable": True,
        }

    days_since_closed = -delta_days
    return {
        "status": "closed",
        "days_left": None,
        "days_since_closed": days_since_closed,
        "is_listable": days_since_closed <= CLOSED_VISIBLE_DAYS,
    }


def is_job_listable(last_date: Optional[datetime], now: Optional[datetime] = None) -> bool:
    return compute_application_window(last_date, now)["is_listable"]
