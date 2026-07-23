"""The common Role schema. Every source normalizes into this shape before
classification, dedup, or anything Notion-related.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Role:
    # --- pipeline-owned, populated by sources ---
    company: str
    role_title: str
    apply_url: str
    source: str                       # "simplify" | "speedyapply"
    location: str = ""
    salary: Optional[str] = None      # speedyapply only
    sponsorship: Optional[str] = None  # simplify only
    date_posted: Optional[date] = None

    # --- pipeline-owned, populated downstream ---
    role_type: Optional[str] = None   # "SWE" | "PM" | None (None => dropped)
    status: str = "Open"              # "Open" | "Closed"
    possible_dup: bool = False

    # first_seen / tier / applied / notes live only in Notion; the pipeline
    # sets first_seen on insert and never reads user-owned fields back.

    def composite_key(self) -> str:
        """Soft cross-source dedup key: normalized (company, title, location).
        First location only — the "+N" shorthand is dropped.
        """
        return "|".join([
            _norm(self.company),
            _norm(self.role_title),
            _norm(self.location.split("+")[0]),
        ])

    def url_key(self) -> str:
        """Primary dedup key: lightly-normalized apply URL."""
        return normalize_url(self.apply_url)


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    for junk in [",", ".", "  "]:
        s = s.replace(junk, " ")
    return " ".join(s.split())


def normalize_url(url: str) -> str:
    """Strip fragment and trailing slash, lowercase host. Query is kept because
    ATS links (e.g. ?gh_jid=...) carry the job identity there.
    """
    url = (url or "").strip()
    url = url.split("#", 1)[0]
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            url = f"{scheme.lower()}://{host.lower()}/{path}"
        else:
            url = f"{scheme.lower()}://{rest.lower()}"
    return url.rstrip("/")
