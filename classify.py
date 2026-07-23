"""Classify a posting title into SWE / PM / drop.

Keyword-based and deliberately fuzzy (see SPEC.md). PM is checked first so that
TPM titles containing eng-ish words ("infrastructure", "platform") resolve to PM,
per the user's decision that TPM counts as PM.
"""
from __future__ import annotations

import re
from typing import Optional

from config import PM_KEYWORDS, SWE_KEYWORDS

# Matches intern / interns / internship / internships, but NOT "internal".
_EXCLUDE_RE = re.compile(r"(?<!\w)intern(?:ship)?s?(?!\w)", re.IGNORECASE)


def _matches(title_lc: str, keywords: list[str]) -> bool:
    for kw in keywords:
        # Word-boundary match so short tokens (swe, sde, tpm, apm) don't match
        # inside unrelated words. Hyphens are treated as boundaries too.
        if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", title_lc):
            return True
    return False


def classify(title: str) -> Optional[str]:
    """Return "SWE", "PM", or None (drop)."""
    title_lc = (title or "").lower()
    if _EXCLUDE_RE.search(title_lc):
        return None  # intern roles are out of scope
    if _matches(title_lc, PM_KEYWORDS):
        return "PM"
    if _matches(title_lc, SWE_KEYWORDS):
        return "SWE"
    return None
