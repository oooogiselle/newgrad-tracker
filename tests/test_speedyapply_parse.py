from datetime import date

from sources.speedyapply import parse_markdown

# A FAANG+ table (has Salary) and an Other table (no Salary), plus surrounding
# non-table noise that must be ignored.
SAMPLE = """
- [New Graduate](x) - **395** available

### FAANG+

| Company | Position | Location | Salary | Posting | Age |
|---|---|---|---|---|---|
| <a href="https://www.google.com"><strong>Google</strong></a> | Technical Program Manager I - Infrastructure | Thornton, CO +2 | $216k/yr | <a href="https://www.google.com/about/careers/jobs/results/12345"><img src="https://i.imgur.com/badge.png" alt="Apply"/></a> | 4d |
| <a href="https://www.twitch.tv"><strong>Twitch</strong></a> | Software Engineer I - Discovery | San Francisco, CA | $193k/yr | <a href="https://job-boards.greenhouse.io/twitch/jobs/8623578002"><img src="https://i.imgur.com/badge.png" alt="Apply"/></a> | 7d |

### Other

| Company | Position | Location | Posting | Age |
|---|---|---|---|---|
| <a href="https://nuro.ai"><strong>Nuro</strong></a> | Software Engineer - Performance - New Grad | Mountain View, CA | <a href="https://nuro.ai/careersitem?gh_jid=6972272"><img src="https://i.imgur.com/badge.png" alt="Apply"/></a> | 5d |
| <a href="https://www.notion.com/"><strong>Notion</strong></a> | Software Engineer - Early Career - AI | San Francisco, CA | <a href="https://jobs.ashbyhq.com/notion/859"><img src="https://i.imgur.com/badge.png" alt="Apply"/></a> | 15d |
"""

RUN = date(2026, 7, 22)


def _by_company(roles, name):
    return next(r for r in roles if r.company == name)


def test_parses_both_layouts():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    assert len(roles) == 4
    companies = {r.company for r in roles}
    assert companies == {"Google", "Twitch", "Nuro", "Notion"}


def test_apply_url_is_outer_link_not_badge_image():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    twitch = _by_company(roles, "Twitch")
    assert twitch.apply_url == "https://job-boards.greenhouse.io/twitch/jobs/8623578002"
    assert "camo.githubusercontent" not in twitch.apply_url


def test_age_converts_to_date():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    google = _by_company(roles, "Google")
    assert google.date_posted == date(2026, 7, 18)  # 22 - 4 days


def test_salary_present_and_absent():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    assert _by_company(roles, "Twitch").salary == "$193k/yr"
    assert _by_company(roles, "Nuro").salary is None  # Other table has no Salary


def test_location_plus_n_preserved():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    assert _by_company(roles, "Google").location == "Thornton, CO +2"


def test_non_table_lines_ignored():
    # The "- [New Graduate]" bullet and headers must not become rows.
    roles = parse_markdown(SAMPLE, run_date=RUN)
    assert all(r.role_title for r in roles)
    assert all(r.apply_url.startswith("http") for r in roles)


def test_source_tagged():
    roles = parse_markdown(SAMPLE, run_date=RUN)
    assert all(r.source == "speedyapply" for r in roles)
