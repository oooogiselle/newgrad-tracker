"""Thin Notion client for the tracker.

Built against Notion API version 2025-09-03 (the data-source model): queries and
page creation target a *data source*, not the database container. The client
resolves the database's first data source once and caches it, which is correct
for the normal single-data-source case. See SPEC.md and Notion's 2025-09-03
upgrade guide.

The property builders enforce the ownership rule that matters most: user-owned
fields (tier / applied / notes) are never emitted, and first_seen is written only
on create. These are pure functions so the ownership test can check them without
touching the network.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

import requests

from config import (
    CREATE_ONLY_FIELDS,
    NOTION_PROPERTY_NAMES,
    USER_OWNED_FIELDS,
)
from models import Role, normalize_url

API = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"


# --------------------------------------------------------------------------- #
# Pure property builders (unit-testable, no network)
# --------------------------------------------------------------------------- #
def _prop(field: str) -> str:
    return NOTION_PROPERTY_NAMES[field]


def _text(value: Optional[str]) -> dict:
    return {"rich_text": [{"text": {"content": value}}] if value else []}


def _title(value: str) -> dict:
    return {"title": [{"text": {"content": value or ""}}]}


def _select(value: Optional[str]) -> dict:
    return {"select": {"name": value} if value else None}


def _url(value: Optional[str]) -> dict:
    return {"url": value or None}


def _date(value: Optional[date]) -> dict:
    return {"date": {"start": value.isoformat()} if value else None}


def _checkbox(value: bool) -> dict:
    return {"checkbox": bool(value)}


def _pipeline_properties(role: Role) -> dict[str, Any]:
    """All pipeline-owned properties EXCEPT create-only ones. This is exactly
    what an update is allowed to write."""
    props: dict[str, Any] = {
        _prop("company"): _title(role.company),
        _prop("role_title"): _text(role.role_title),
        _prop("role_type"): _select(role.role_type),
        _prop("location"): _text(role.location),
        _prop("apply_url"): _url(role.apply_url),
        _prop("salary"): _text(role.salary),
        _prop("source"): _select(role.source),
        _prop("sponsorship"): _select(role.sponsorship),
        _prop("date_posted"): _date(role.date_posted),
        _prop("status"): _select(role.status),
        _prop("possible_dup"): _checkbox(role.possible_dup),
    }
    # Guard: nothing user-owned or create-only may leak into an update payload.
    banned = {_prop(f) for f in (USER_OWNED_FIELDS | CREATE_ONLY_FIELDS)}
    assert not (set(props) & banned), "update payload touched a protected field"
    return props


def build_update_properties(role: Role) -> dict[str, Any]:
    """Properties written when a role already exists. Excludes user-owned fields
    and first_seen (create-only) so the user's tracking data is preserved."""
    return _pipeline_properties(role)


def build_create_properties(role: Role) -> dict[str, Any]:
    """Properties written on first insert. Adds first_seen (today); still never
    writes user-owned fields."""
    props = _pipeline_properties(role)
    props[_prop("first_seen")] = _date(date.today())
    return props


# --------------------------------------------------------------------------- #
# HTTP client
# --------------------------------------------------------------------------- #
class NotionClient:
    def __init__(self, token: str, database_id: str):
        self.database_id = database_id
        self._data_source_id: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    # -- data source resolution --------------------------------------------- #
    @property
    def data_source_id(self) -> str:
        if self._data_source_id is None:
            resp = self._session.get(f"{API}/databases/{self.database_id}")
            resp.raise_for_status()
            sources = resp.json().get("data_sources", [])
            if not sources:
                raise RuntimeError(
                    "Database has no data sources; check the ID and integration access."
                )
            self._data_source_id = sources[0]["id"]
        return self._data_source_id

    # -- reads --------------------------------------------------------------- #
    def existing_rows(self) -> dict[str, dict]:
        """Map normalized apply_url -> {page_id, source, archived}. Paginated."""
        rows: dict[str, dict] = {}
        payload: dict[str, Any] = {"page_size": 100}
        url = f"{API}/data_sources/{self.data_source_id}/query"
        while True:
            resp = self._session.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            for page in data.get("results", []):
                props = page.get("properties", {})
                apply_url = _read_url(props.get(_prop("apply_url")))
                if not apply_url:
                    continue
                rows[normalize_url(apply_url)] = {
                    "page_id": page["id"],
                    "source": _read_select(props.get(_prop("source"))),
                    "archived": page.get("archived", False),
                }
            if not data.get("has_more"):
                break
            payload["start_cursor"] = data["next_cursor"]
        return rows

    # -- writes -------------------------------------------------------------- #
    def create_page(self, role: Role) -> None:
        payload = {
            "parent": {"type": "data_source_id", "data_source_id": self.data_source_id},
            "properties": build_create_properties(role),
        }
        resp = self._session.post(f"{API}/pages", json=payload)
        resp.raise_for_status()

    def update_page(self, page_id: str, role: Role, archived: bool = False) -> None:
        payload = {"properties": build_update_properties(role), "archived": archived}
        resp = self._session.patch(f"{API}/pages/{page_id}", json=payload)
        resp.raise_for_status()

    def close_page(self, page_id: str) -> None:
        """Mark Closed and archive out of the main view (never delete)."""
        payload = {
            "properties": {_prop("status"): _select("Closed")},
            "archived": True,
        }
        resp = self._session.patch(f"{API}/pages/{page_id}", json=payload)
        resp.raise_for_status()


# --------------------------------------------------------------------------- #
# Read helpers (parse Notion property values back out)
# --------------------------------------------------------------------------- #
def _read_url(prop: Optional[dict]) -> Optional[str]:
    return (prop or {}).get("url")


def _read_select(prop: Optional[dict]) -> Optional[str]:
    sel = (prop or {}).get("select")
    return sel.get("name") if sel else None
