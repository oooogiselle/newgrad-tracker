"""The correctness-critical test (SPEC.md, "Field ownership").

If the pipeline ever writes tier / applied / notes, it silently destroys the
user's manual tracking data. first_seen must be write-once (create only). These
tests pin both properties against the pure payload builders.
"""
from datetime import date

from config import NOTION_PROPERTY_NAMES as P
from models import Role
from notion_client import build_create_properties, build_update_properties

USER_OWNED = [P["tier"], P["applied"], P["notes"]]


def _role() -> Role:
    return Role(
        company="Stripe",
        role_title="Software Engineer, New Grad",
        apply_url="https://stripe.com/jobs/123",
        source="simplify",
        location="San Francisco, CA",
        role_type="SWE",
        date_posted=date(2026, 7, 1),
    )


def test_update_never_touches_user_owned_fields():
    props = build_update_properties(_role())
    for name in USER_OWNED:
        assert name not in props, f"update payload leaked user-owned field: {name}"


def test_create_never_touches_user_owned_fields():
    props = build_create_properties(_role())
    for name in USER_OWNED:
        assert name not in props, f"create payload leaked user-owned field: {name}"


def test_first_seen_is_create_only():
    assert P["first_seen"] not in build_update_properties(_role()), (
        "update must not write first_seen — it would reset the 'first seen' date"
    )
    assert P["first_seen"] in build_create_properties(_role()), (
        "create must set first_seen"
    )


def test_create_sets_first_seen_to_today():
    props = build_create_properties(_role())
    assert props[P["first_seen"]]["date"]["start"] == date.today().isoformat()
