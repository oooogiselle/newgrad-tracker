"""One-time: create the tracker database under a parent page.

Run once: `python setup_database.py <PARENT_PAGE_ID>`; it prints the new
database id to put in NOTION_DATABASE_ID.

Creation uses Notion-Version 2022-06-28 on purpose: a freshly created database
always has exactly one data source, so the legacy create call is safe and its
body shape is stable. The runtime pipeline then talks to it via the 2025-09-03
data-source endpoints (see notion_client.py).
"""
from __future__ import annotations

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

from config import NOTION_PROPERTY_NAMES as P

API = "https://api.notion.com/v1"


def schema() -> dict:
    return {
        P["company"]: {"title": {}},
        P["role_title"]: {"rich_text": {}},
        P["role_type"]: {"select": {"options": [
            {"name": "SWE"}, {"name": "PM"},
        ]}},
        P["location"]: {"rich_text": {}},
        P["apply_url"]: {"url": {}},
        P["salary"]: {"rich_text": {}},
        P["source"]: {"select": {"options": [
            {"name": "simplify"}, {"name": "speedyapply"},
        ]}},
        P["sponsorship"]: {"select": {}},
        P["date_posted"]: {"date": {}},
        P["first_seen"]: {"date": {}},
        P["status"]: {"select": {"options": [
            {"name": "Open"}, {"name": "Closed"},
        ]}},
        P["possible_dup"]: {"checkbox": {}},
        # user-owned
        P["tier"]: {"select": {"options": [
            {"name": "Reach"}, {"name": "Target"}, {"name": "Safety"},
        ]}},
        P["applied"]: {"checkbox": {}},
        P["notes"]: {"rich_text": {}},
    }


def main(parent_page_id: str) -> None:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN must be set")
    resp = requests.post(
        f"{API}/databases",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        json={
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": "New-Grad Role Tracker"}}],
            "properties": schema(),
        },
        timeout=30,
    )
    resp.raise_for_status()
    db_id = resp.json()["id"]
    print("Database created.")
    print(f"NOTION_DATABASE_ID={db_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python setup_database.py <PARENT_PAGE_ID>")
    main(sys.argv[1])
