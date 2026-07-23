# New-Grad Role Tracker

Self-updating Notion database of new-grad **SWE and PM** roles, aggregated from
public GitHub job repos, deduplicated, and refreshed every 6h via GitHub Actions.
Closed roles are archived out of the main view but retained. Full design in
[`SPEC.md`](./SPEC.md).

## Status

- **Slice 1 (done):** Simplify source, classifier (with intern exclusion), dedup,
  Notion upsert with ownership protection, GitHub Actions workflow, tests.
- **Slice 2 (done):** speedyapply `NEW_GRAD_USA.md` HTML-table parser
  (`sources/speedyapply.py`), registered in `pipeline.SOURCES`. Both sources live.

Live snapshot: ~1,070 SWE/PM roles after dedup across both sources.

## Setup

1. Create a Notion internal integration, copy its token.
2. Share the parent page with the integration (Connections → add it).
3. Create the database:
   ```bash
   export NOTION_TOKEN=secret_xxx
   python setup_database.py <PARENT_PAGE_ID>   # prints NOTION_DATABASE_ID
   ```
4. Set `NOTION_TOKEN` and `NOTION_DATABASE_ID` as GitHub repo secrets (for the
   Action) and/or in a local `.env` (see `.env.example`).

## Run

```bash
pip install -r requirements.txt
python pipeline.py        # fetch -> classify -> dedup -> upsert
python -m pytest tests/   # includes the ownership-protection test
```

## How it works

`fetch -> normalize -> classify (SWE/PM) -> dedup -> diff -> upsert`. The pipeline
owns sourcing fields; **`Tier`, `Applied`, and `Notes` are yours** and are never
written by a sync (enforced by `tests/test_ownership.py`). `First Seen` is written
once on insert. Closure only applies to sources that fetched successfully in a
given run, so a network blip can't wipe the tracker.

Built against Notion API `2025-09-03` (data-source model); the client resolves the
database's data source automatically.
