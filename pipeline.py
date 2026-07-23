"""Orchestration: fetch -> normalize -> classify -> dedup -> diff -> upsert.

Run: `python pipeline.py`  (needs NOTION_TOKEN and NOTION_DATABASE_ID in env).

Closure is scoped to sources that fetched successfully this run: if a source's
fetch fails, its existing rows are left untouched rather than all being marked
Closed. This is the safety property that keeps a transient GitHub/network blip
from wiping half the tracker.
"""
from __future__ import annotations

import os
import sys
from typing import Callable

try:  # optional: load a local .env for convenience (no-op in CI)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from classify import classify
from dedup import dedup
from models import Role
from notion_client import NotionClient
from sources import simplify, speedyapply

# Registered sources: (name, fetch fn).
SOURCES: list[tuple[str, Callable[[], list[Role]]]] = [
    (simplify.SOURCE, simplify.fetch),
    (speedyapply.SOURCE, speedyapply.fetch),
]


def gather() -> tuple[list[Role], set[str]]:
    """Fetch + classify all sources. Returns (roles, sources_that_succeeded).
    A source that raises is logged and skipped; its rows won't be closed later.
    """
    roles: list[Role] = []
    ok_sources: set[str] = set()
    for name, fetch in SOURCES:
        try:
            fetched = fetch()
        except Exception as exc:  # noqa: BLE001 - one bad source shouldn't kill the run
            print(f"[warn] source '{name}' failed: {exc}", file=sys.stderr)
            continue
        kept = 0
        for role in fetched:
            role.role_type = classify(role.role_title)
            if role.role_type is None:
                continue  # not SWE/PM -> drop
            roles.append(role)
            kept += 1
        ok_sources.add(name)
        print(f"[info] {name}: {kept} SWE/PM roles after classify")
    return roles, ok_sources


def run() -> None:
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        sys.exit("NOTION_TOKEN and NOTION_DATABASE_ID must be set")

    roles, ok_sources = gather()
    if not ok_sources:
        sys.exit("all sources failed; aborting without touching Notion")

    roles = dedup(roles)
    incoming = {r.url_key(): r for r in roles}
    print(f"[info] {len(incoming)} unique roles after dedup")

    client = NotionClient(token, database_id)
    existing = client.existing_rows()

    created = updated = closed = 0

    # Create / update
    for url, role in incoming.items():
        row = existing.get(url)
        if row is None:
            client.create_page(role)
            created += 1
        else:
            # Revive if it had been archived/closed and is live again.
            client.update_page(row["page_id"], role, archived=False)
            updated += 1

    # Close: existing rows absent from this run, but only for sources we
    # actually fetched successfully.
    for url, row in existing.items():
        if url in incoming:
            continue
        if row["source"] not in ok_sources:
            continue
        if row["archived"]:
            continue  # already archived
        client.close_page(row["page_id"])
        closed += 1

    print(f"[done] created={created} updated={updated} closed={closed}")


if __name__ == "__main__":
    run()
