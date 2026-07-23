"""Configuration for the new-grad role tracker.

Everything here is meant to be tuned without touching pipeline logic — the
classifier keyword lists in particular will need adjustment as misclassifications
surface (see SPEC.md, "Role-type classifier").
"""
from __future__ import annotations

# --- Source URLs (raw) ------------------------------------------------------
SIMPLIFY_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "New-Grad-Positions/dev/.github/scripts/listings.json"
)
SPEEDYAPPLY_URL = (
    "https://raw.githubusercontent.com/speedyapply/"
    "2027-SWE-College-Jobs/main/NEW_GRAD_USA.md"
)

# --- Role-type classifier ---------------------------------------------------
# Titles matching this are dropped outright, before SWE/PM classification.
# The classifier implements it as a word-boundary regex so "internal" (e.g.
# "Internal Tooling") is NOT excluded — only intern/interns/internship(s).
EXCLUDE_KEYWORDS = ["intern"]

# PM is checked BEFORE SWE on purpose: TPM titles often contain words like
# "infrastructure"/"platform" that would otherwise trip the SWE list, and the
# user's decision is that TPM counts as PM.
PM_KEYWORDS = [
    "product manager",
    "associate product manager",
    "apm",
    "product management",
    "technical program manager",
    "tpm",
]
SWE_KEYWORDS = [
    "software engineer",
    "swe",
    "sde",
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "full stack",
    "full-stack",
    "infrastructure",
    "platform engineer",
    "systems engineer",
    "developer",
    "firmware",
    "embedded",
]

# --- Notion schema ownership ------------------------------------------------
# User-owned fields are NEVER written by the pipeline (create or update).
# Create-only fields are written once, on insert, and never touched again.
USER_OWNED_FIELDS = {"tier", "applied", "notes"}
CREATE_ONLY_FIELDS = {"first_seen"}

# Notion property names, keyed by our internal Role field name. Keeping this
# indirection means renaming a Notion column is a one-line change here.
NOTION_PROPERTY_NAMES = {
    "company": "Company",
    "role_title": "Role Title",
    "role_type": "Role Type",
    "location": "Location",
    "apply_url": "Apply URL",
    "salary": "Salary",
    "source": "Source",
    "sponsorship": "Sponsorship",
    "date_posted": "Date Posted",
    "first_seen": "First Seen",
    "status": "Status",
    "possible_dup": "Possible Duplicate",
    "tier": "Tier",
    "applied": "Applied",
    "notes": "Notes",
}
