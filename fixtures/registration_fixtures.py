"""
fixtures/registration_fixtures.py
===================================
Data fixtures for the MPPA Pre-Registration form tests (TC-01 to TC-09).

Registered globally via pytest_plugins in conftest.py — no imports needed
in individual test files.

Fixture → Factory method → Notion TC
--------------------------------------
valid_registration_data       → valid()                  TC-01 / AC-5
blank_username_data           → blank_username()         TC-02
short_username_data           → short_username()         TC-03
username_with_space_data      → username_with_space()    TC-04
username_already_taken_data   → username_already_taken() TC-05
password_mismatch_data        → password_mismatch()      TC-08
ec5_show_hide_data            → ec5_password_show_hide() TC-09 / EC-5
"""

import pytest
from test_data.agency_registration_factory import AgencyRegistrationFactory


@pytest.fixture
def valid_registration_data():
    """TC-01 / AC-5 — All fields valid; happy-path / baseline data."""
    return AgencyRegistrationFactory.valid()


@pytest.fixture
def blank_username_data():
    """TC-02 — Username left blank; expects 'Username is required.' error."""
    return AgencyRegistrationFactory.blank_username()


@pytest.fixture
def short_username_data():
    """TC-03 — Username < 6 characters; expects min-length error."""
    return AgencyRegistrationFactory.short_username()


@pytest.fixture
def username_with_space_data():
    """TC-04 — Username contains a space; expects no-spaces error."""
    return AgencyRegistrationFactory.username_with_space()


@pytest.fixture
def username_already_taken_data():
    """TC-05 — Username already registered; expects duplicate error on blur."""
    return AgencyRegistrationFactory.username_already_taken()


@pytest.fixture
def password_mismatch_data():
    """TC-08 — confirm_password differs from password; expects mismatch error."""
    return AgencyRegistrationFactory.password_mismatch()


@pytest.fixture
def ec5_show_hide_data():
    """TC-09 / EC-5 — Fixed recognisable password for show/hide toggle test."""
    return AgencyRegistrationFactory.ec5_password_show_hide()

@pytest.fixture
def password_no_uppercase_data():
    """TC-06 — Password without uppercase letter"""
    return AgencyRegistrationFactory.password_no_uppercase().password

@pytest.fixture
def password_no_number_data():
    """TC-06 — Password without number"""
    return AgencyRegistrationFactory.password_no_number().password


@pytest.fixture
def password_no_symbol_data():
    """TC-06 — Password without special symbol"""
    return AgencyRegistrationFactory.password_no_symbol().password


@pytest.fixture
def short_password_data():
    """TC-06 — Password without special symbol"""
    return AgencyRegistrationFactory.password_too_short().password


# ── Section 2: Contact & Identity fixtures (TC-10 to TC-18) ──────────────────
# TC-10 uses valid_registration_data (already declared above).
# TC-11 uses valid_registration_data — the OTP is fetched live from testmail.app.

@pytest.fixture
def invalid_email_domain_data():
    """
    TC-14 / EC-3 — Syntactically valid email whose domain does not exist.
    OTP delivery is expected to fail.
    """
    return AgencyRegistrationFactory.invalid_email_domain()


@pytest.fixture
def ec4_pan_lowercase_data():
    """
    TC-15 / EC-4 — PAN entered in lowercase; the field should auto-uppercase
    the value in real-time.
    """
    return AgencyRegistrationFactory.ec4_pan_lowercase()


@pytest.fixture
def duplicate_pan_data():
    """TC-17 — PAN already registered in the system; expects duplicate error."""
    return AgencyRegistrationFactory.duplicate_pan()

@pytest.fixture
def no_district_data():
    """TC-18 (negative path) — District left unselected; expects required error."""
    return AgencyRegistrationFactory.no_district_selected()