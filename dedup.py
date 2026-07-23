"""Deduplication.

Primary key is the (normalized) apply URL — two rows with the same URL are the
same posting and the later one is dropped. Composite (company, title, location)
is a *soft* signal only: when it matches a row already seen from a DIFFERENT
source, the newer row is flagged `possible_dup=True` rather than merged. This
never destroys a genuinely distinct posting; the user resolves flagged rows in
Notion. (See SPEC.md, "Deduplication".)
"""
from __future__ import annotations

from models import Role


def dedup(roles: list[Role]) -> list[Role]:
    kept: list[Role] = []
    seen_urls: set[str] = set()
    # composite_key -> source that first contributed it
    composite_source: dict[str, str] = {}

    for role in roles:
        url = role.url_key()
        if url in seen_urls:
            continue  # exact same posting, already have it
        seen_urls.add(url)

        ckey = role.composite_key()
        prior_source = composite_source.get(ckey)
        if prior_source is not None and prior_source != role.source:
            role.possible_dup = True
        else:
            # record the first source to claim this composite key
            composite_source.setdefault(ckey, role.source)

        kept.append(role)

    return kept
