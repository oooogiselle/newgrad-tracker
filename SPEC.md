# New-Grad Role Tracker — Spec v1

A self-updating Notion database of new-grad **SWE and PM** roles, aggregated from
public GitHub job repos, deduplicated, normalized to one schema, and refreshed on a
schedule. Closed roles are archived out of the main view but retained for history.

The pipeline owns the sourcing/normalization fields; the user owns the tracking
fields (`tier`, `applied`, `notes`). The upsert must never overwrite user-owned
fields — this is a correctness requirement, not a nice-to-have.

---

## Sources (v1)

| Source | Format | Roles | Date signal | Closed signal | Raw location |
|---|---|---|---|---|---|
| SimplifyJobs/New-Grad-Positions | clean JSON array | SWE + PM | `date_posted` (unix epoch) | `active: false` **or** key disappears | `.github/scripts/listings.json` on `dev` |
| speedyapply/2027-SWE-College-Jobs | Markdown table | SWE only | `Age` (relative, e.g. `13d`) → computed | key disappears only | `NEW_GRAD_USA.md` on `main` |

Raw fetch URLs:
- `https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json`
- `https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/NEW_GRAD_USA.md`

**Only the `NEW_GRAD_USA.md` file is pulled from speedyapply** — never `INTERN_USA.md`
or the `_INTL` variants. That file is USA + new-grad only by construction.

Explicitly out of scope for v1: LinkedIn / Indeed / Glassdoor (no usable API,
scraping breaks and violates ToS). Greenhouse/Lever direct endpoints deferred to v2.

---

## Trigger

GitHub Actions cron, every 6h. Both sources update more frequently than that
(Simplify ~hourly, speedyapply daily), so 6h keeps the tracker fresh without
hammering either repo.

---

## Dataflow

```
[cron every 6h]
   │
   ▼
[Fetch]
   ├─ Simplify listings.json  (JSON array)
   └─ speedyapply NEW_GRAD_USA.md  (Markdown → parsed rows)
   │
   ▼
[Normalize] map each source's shape → common Role schema
   │
   ▼
[Classify] title → SWE / PM / drop   (drops Quant, Hardware, DS, and noise rows)
   │
   ▼
[Dedup] primary key = apply_url
   └─ soft "possible duplicate" flag when composite matches across sources
   │
   ▼
[Diff] query Notion DB, match on apply_url
   ├─ new                → create page
   ├─ changed            → update pipeline-owned fields only
   └─ gone / active:false → status = Closed, archive out of main view (never delete)
   │
   ▼
[Notion DB] upsert  (user-owned fields untouched)
```

---

## Common Role schema

Every source is mapped into this shape before anything touches Notion.

| Field | Type | Owner | Source / notes |
|---|---|---|---|
| `company` | title | pipeline | normalized casing |
| `role_title` | text | pipeline | original posting title |
| `role_type` | select (SWE / PM) | pipeline | derived from title (see classifier) |
| `location` | text | pipeline | first location; `+N` shorthand preserved |
| `apply_url` | url | pipeline | canonical apply link — **primary dedup key** |
| `salary` | text | pipeline | speedyapply only; blank for Simplify |
| `source` | select (simplify / speedyapply) | pipeline | provenance |
| `sponsorship` | select | pipeline | Simplify only; blank for speedyapply |
| `date_posted` | date | pipeline | Simplify: epoch → date. speedyapply: `run_date − age` |
| `first_seen` | date | pipeline | set once, on first insert; never updated |
| `status` | select (Open / Closed) | pipeline | see closed-role handling |
| `possible_dup` | checkbox | pipeline | set when composite matches across sources |
| `tier` | select (Reach / Target / Safety) | **user** | manual |
| `applied` | checkbox | **user** | manual |
| `notes` | text | **user** | manual |

Both `date_posted` and `first_seen` are kept: `date_posted` is the source's claim
about when the role went up; `first_seen` is the honest "when did *this tracker*
first see it" signal. They diverge often enough to be worth both columns.

---

## Role-type classifier

Title keyword match → `SWE` / `PM` / drop. Case-insensitive.

**SWE:** software engineer, swe, backend, back-end, frontend, front-end,
full stack, full-stack, infrastructure, platform engineer, systems engineer,
developer, sde, firmware, embedded

**PM:** product manager, associate product manager, apm, product management,
**technical program manager, tpm** (TPM is treated as PM)

Anything matching neither list is **dropped**. This is how Quant, Hardware, Data
Science, and the noise rows in speedyapply's "Other" bucket (case manager,
lecturer, equity research analyst, etc.) get filtered out.

This is the fuzzy step in the pipeline — the keyword lists will need tuning as
misclassifications surface. Treat them as config, not fixed code.

---

## Deduplication

- **Primary key: `apply_url`.** Clean, and never wrongly merges two genuinely
  distinct postings.
- **Composite `(company + role_title + location)`** is computed as a secondary
  signal. When it matches an existing role from a *different* source, set
  `possible_dup = true` on the new row rather than merging.

Rationale: the same role often appears in both sources under different apply URLs,
and speedyapply itself lists near-duplicates (same title, different locations or
different ATS links). `url`-primary keeps these separate; the soft flag surfaces
likely dupes for the user to resolve in Notion, so the pipeline never destroys a
distinct posting by guessing.

---

## Closed-role handling

A role is marked `status = Closed` when:
- **Simplify:** `active: false` in the feed, **or** its `apply_url` disappears
  from the latest pull.
- **speedyapply:** its `apply_url` disappears from the latest pull (no `active`
  flag exists in that source).

On close: set `status = Closed` and **archive the Notion page** so it drops out of
the main view but stays queryable. **Never deleted.**

This requires tracking, per source, which keys were seen in the most recent run.

---

## Field ownership (correctness requirement)

The upsert writes **only** pipeline-owned fields (everything except `tier`,
`applied`, `notes`). Once the user sets a value in a user-owned field, no pipeline
run may overwrite it. A regression here silently destroys the user's tracking data,
so it should be covered by an explicit test before first real run.

---

## Source-specific parsing notes

**Simplify (`listings.json`)** — flat JSON array. Relevant fields per record:
`company_name`, `title`, `locations` (array), `url`, `active`, `is_visible`,
`sponsorship`, `date_posted` / `date_updated` (epoch), `terms`, `source`. Filter to
`active && is_visible` before classifying.

**speedyapply (`NEW_GRAD_USA.md`)** — three Markdown sub-tables (FAANG+ / Quant /
Other). Two column layouts:
- FAANG+ and Quant: `Company | Position | Location | Salary | Posting | Age`
- Other: `Company | Position | Location | Posting | Age` (no Salary)

The parser must detect which layout each table uses. `apply_url` is the link inside
the Posting cell (the ATS URL, not the "Apply" badge image). `Age` like `13d` →
`run_date − 13 days`. `Location` may carry `+N` shorthand for extra locations;
preserve the string as-is.

---

## Deferred to v2

- Greenhouse public API (`boards-api.greenhouse.io/v1/boards/{token}/jobs`)
- Lever public API (`api.lever.co/v0/postings/{company}?mode=json`)
- Target-company list driven from a Notion "Target Companies" DB instead of hardcoded
- Optional LLM enrichment (stack tags, tier auto-match)
- Location filtering (e.g. Bay Area + remote) — currently unfiltered within US
