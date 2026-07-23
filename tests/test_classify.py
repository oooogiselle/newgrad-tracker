from classify import classify


def test_basic_swe():
    assert classify("Software Engineer, New Grad") == "SWE"
    assert classify("Backend Developer I") == "SWE"
    assert classify("New College Grad - SSD Firmware Engineer") == "SWE"


def test_basic_pm():
    assert classify("Associate Product Manager") == "PM"
    assert classify("Product Management, Early Career") == "PM"


def test_tpm_counts_as_pm():
    assert classify("Technical Program Manager I - Google Cloud") == "PM"


def test_tpm_with_eng_word_still_pm():
    # "infrastructure" is a SWE keyword, but PM is checked first so TPM wins.
    assert classify("Technical Program Manager I - Infrastructure") == "PM"


def test_noise_is_dropped():
    assert classify("Part-Time Instructor - Software - CIT") is None
    assert classify("Equity Research Analyst/Associate - Software") is None
    assert classify("Lecturer - Cloud Management & Operations") is None


def test_known_false_positive_job_developer():
    # KNOWN LIMITATION: "Job Developer" (a social-services role) matches the
    # SWE keyword 'developer'. Documented here so the behavior is visible; fix
    # by tightening the keyword list when this class of noise shows up.
    assert classify("Case Manager I - Job Developer") == "SWE"


def test_short_tokens_need_boundaries():
    # 'swe' should not match inside a larger word
    assert classify("Answered Questions Specialist") is None


def test_intern_roles_dropped():
    assert classify("Product Manager Intern") is None
    assert classify("Software Engineer Intern") is None
    assert classify("Software Engineering Internship") is None
    assert classify("Backend Interns - 2027") is None


def test_internal_is_not_excluded():
    # "internal" contains "intern" but must NOT be dropped.
    assert classify("Software Engineer I - Internal Tooling") == "SWE"
