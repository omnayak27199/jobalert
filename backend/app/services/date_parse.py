from __future__ import annotations

from datetime import datetime
from typing import Optional

DATE_FORMATS = (
    "%d %b %Y",
    "%d %B %Y",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
)


def parse_flexible_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None
