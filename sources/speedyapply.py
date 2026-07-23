"""speedyapply/2027-SWE-College-Jobs source (NEW_GRAD_USA.md).

Markdown-table source. Parsing is driven off each table's HEADER row so the two
layouts collapse into one code path:

    FAANG+ / Quant : Company | Position | Location | Salary | Posting | Age
    Other          : Company | Position | Location | Posting | Age   (no Salary)

Key extractions (cells contain HTML, not Markdown):
  - company  : text inside <a href><strong>Google</strong></a> -> Google
  - apply_url: the href of the Posting cell's anchor
               <a href="APPLY_URL"><img alt="Apply"/></a> -> APPLY_URL
  - date     : Age like "13d" -> run_date - 13 days (no absolute date in source)
  - salary   : kept as-is ("$178k/yr") when the column exists, else None
  - location : kept as-is, including the "+N" shorthand

SWE-only source; the shared classifier still runs downstream to drop the
"Other"-bucket noise (case manager, lecturer, ...) and any intern rows.
"""
from __future__ import annotations

import html
import re
from datetime import date, timedelta

import requests

from config import SPEEDYAPPLY_URL
from models import Role

SOURCE = "speedyapply"

# header cell text (lowercased) -> internal field
_COLUMN_ALIASES = {
    "company": "company",
    "position": "role_title",
    "location": "location",
    "salary": "salary",
    "posting": "posting",
    "age": "age",
}

# Cells contain HTML, e.g.
#   company : <a href="..."><strong>Google</strong></a>
#   posting : <a href="APPLY_URL"><img src="badge.png" alt="Apply"/></a>
_STRONG_RE = re.compile(r"<strong>(.+?)</strong>", re.IGNORECASE)
_ANCHOR_TEXT_RE = re.compile(r">([^<>]+)</a>", re.IGNORECASE)
_HREF_RE = re.compile(r'href="([^"]+)"', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_AGE_RE = re.compile(r"(\d+)\s*d", re.IGNORECASE)


def _clean(s: str) -> str:
    return html.unescape(_TAG_RE.sub("", s)).strip()


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= {"-", ":", " "} and c for c in cells)


def _header_map(cells: list[str]) -> dict[str, int] | None:
    mapping: dict[str, int] = {}
    for i, cell in enumerate(cells):
        key = _COLUMN_ALIASES.get(cell.lower())
        if key:
            mapping[key] = i
    if {"company", "role_title", "posting", "age"} <= set(mapping):
        return mapping
    return None


def _company(cell: str) -> str:
    m = _STRONG_RE.search(cell)
    if m:
        return _clean(m.group(1))
    m = _ANCHOR_TEXT_RE.search(cell)
    if m:
        return _clean(m.group(1))
    return _clean(cell)


def _apply_url(cell: str) -> str | None:
    m = _HREF_RE.search(cell)
    return m.group(1).strip() if m else None


def _age_days(cell: str) -> int | None:
    m = _AGE_RE.search(cell)
    return int(m.group(1)) if m else None


def parse_markdown(text: str, run_date: date | None = None) -> list[Role]:
    run_date = run_date or date.today()
    roles: list[Role] = []
    columns: dict[str, int] | None = None

    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            columns = None  # left the table
            continue
        cells = _split_row(line)
        if _is_separator(cells):
            continue
        header = _header_map(cells)
        if header is not None:
            columns = header
            continue
        if columns is None:
            continue  # data row before any header we recognized
        if max(columns.values()) >= len(cells):
            continue  # malformed row, skip defensively

        def get(field: str) -> str | None:
            i = columns.get(field)
            return cells[i] if i is not None else None

        apply_url = _apply_url(get("posting") or "")
        if not apply_url:
            continue
        age = _age_days(get("age") or "")
        posted = run_date - timedelta(days=age) if age is not None else None
        salary = _clean(get("salary") or "") or None
        roles.append(
            Role(
                company=_company(get("company") or ""),
                role_title=_clean(get("role_title") or ""),
                apply_url=apply_url,
                source=SOURCE,
                location=_clean(get("location") or ""),
                salary=salary,
                date_posted=posted,
            )
        )
    return roles


def fetch(timeout: int = 30) -> list[Role]:
    resp = requests.get(SPEEDYAPPLY_URL, timeout=timeout)
    resp.raise_for_status()
    return parse_markdown(resp.text)
