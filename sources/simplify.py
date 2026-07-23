"""SimplifyJobs/New-Grad-Positions source.

Clean JSON array. We keep only active + visible rows (an inactive role simply
won't appear in the fetched set, which is how the pipeline later marks it
Closed). Covers both SWE and PM.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import requests

from config import SIMPLIFY_URL
from models import Role

SOURCE = "simplify"


def _epoch_to_date(value) -> date | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).date()
    except (TypeError, ValueError, OSError):
        return None


def fetch(timeout: int = 30) -> list[Role]:
    resp = requests.get(SIMPLIFY_URL, timeout=timeout)
    resp.raise_for_status()
    records = resp.json()

    roles: list[Role] = []
    for r in records:
        if not (r.get("active", False) and r.get("is_visible", True)):
            continue
        locations = r.get("locations") or []
        location = ", ".join(locations) if isinstance(locations, list) else str(locations)
        url = r.get("url") or ""
        if not url:
            continue
        roles.append(
            Role(
                company=(r.get("company_name") or "").strip(),
                role_title=(r.get("title") or "").strip(),
                apply_url=url.strip(),
                source=SOURCE,
                location=location,
                sponsorship=r.get("sponsorship"),
                date_posted=_epoch_to_date(r.get("date_posted")),
            )
        )
    return roles
