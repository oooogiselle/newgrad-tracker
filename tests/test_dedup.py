from dedup import dedup
from models import Role


def _role(company, title, url, source, location="San Francisco, CA"):
    return Role(company=company, role_title=title, apply_url=url,
                source=source, location=location, role_type="SWE")


def test_same_url_collapses():
    roles = [
        _role("Stripe", "SWE New Grad", "https://s.co/1", "simplify"),
        _role("Stripe", "SWE New Grad", "https://s.co/1/", "speedyapply"),  # trailing slash
    ]
    out = dedup(roles)
    assert len(out) == 1


def test_cross_source_composite_flags_dup_not_merge():
    roles = [
        _role("Notion", "Software Engineer, Early Career", "https://notion.so/a", "simplify"),
        _role("Notion", "Software Engineer, Early Career", "https://ashby.com/b", "speedyapply"),
    ]
    out = dedup(roles)
    assert len(out) == 2, "distinct URLs must not be merged"
    flagged = [r for r in out if r.possible_dup]
    assert len(flagged) == 1
    assert flagged[0].source == "speedyapply"  # the later one is flagged


def test_same_source_composite_not_flagged():
    # Two genuinely distinct postings from the same source (e.g. two locations)
    # must NOT be flagged as dups of each other.
    roles = [
        _role("Amazon", "SDE I", "https://a.com/1", "simplify", "Seattle, WA"),
        _role("Amazon", "SDE I", "https://a.com/2", "simplify", "Seattle, WA"),
    ]
    out = dedup(roles)
    assert len(out) == 2
    assert not any(r.possible_dup for r in out)
