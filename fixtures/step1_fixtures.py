import pytest

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.partA_page import PartAPage
from test_data.step1_factory import PartAData, PartAFactory
from utils.state_store import TestStateStore


def _login_and_navigate_to_step1(page, user):
    """Logs in, waits for the dashboard, then clicks the Part A step card."""
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url("**/dashboard**", timeout=15000)
    DashboardPage(page).step_card("partA").click()
    page.wait_for_load_state("networkidle")


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_a_page(page) -> PartAPage:
    return PartAPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_part_a_page(page):
    """Yields (page, user) for any stored agency user, logged in and on Step 1."""
    user = TestStateStore().get_any_agency_user()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    _login_and_navigate_to_step1(page, user)
    yield page, user


@pytest.fixture
def logged_in_part_a_fresh_page(page):
    """Yields (page, user) for an agency user who has NOT started the wizard, logged in and on Step 1.

    Use for tests that require all Step 1 fields to be empty, or that will
    save Step 1 and update the state store (TC-58, TC-71, TC-72)."""
    user = TestStateStore().get_agency_user_with_no_form()
    if user is None:
        pytest.skip(
            "No agency user without form applications found in state store — "
            "run pre-registration tests first."
        )
    _login_and_navigate_to_step1(page, user)
    yield page, user


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def part_a_valid_data() -> PartAData:
    """TC-58: All mandatory fields, no optional fields."""
    return PartAFactory.valid_mandatory_fields()


@pytest.fixture
def part_a_future_date_data() -> PartAData:
    """TC-62: Date of incorporation is in the future."""
    return PartAFactory.future_date()


@pytest.fixture
def part_a_invalid_date_data() -> PartAData:
    """TC-63: Date in an invalid format."""
    return PartAFactory.invalid_date_format()


@pytest.fixture
def part_a_invalid_tan_data() -> PartAData:
    """TC-64: TAN in an incorrect format."""
    return PartAFactory.invalid_tan_format()


@pytest.fixture
def part_a_invalid_gstin_data() -> PartAData:
    """TC-65: GSTIN in an incorrect format."""
    return PartAFactory.invalid_gstin_format()


@pytest.fixture
def part_a_invalid_email_data() -> PartAData:
    """TC-66: Email missing @ or domain."""
    return PartAFactory.invalid_email_format()


@pytest.fixture
def part_a_invalid_mobile_letters_data() -> PartAData:
    """TC-67 step 1: Mobile number with letters."""
    return PartAFactory.invalid_mobile_with_letters()


@pytest.fixture
def part_a_invalid_mobile_short_data() -> PartAData:
    """TC-67 step 3: Mobile number that is too short."""
    return PartAFactory.invalid_mobile_too_short()


@pytest.fixture
def part_a_invalid_mobile_zero_data() -> PartAData:
    """TC-75: Mobile number starting with 0."""
    return PartAFactory.invalid_mobile_starts_with_zero()


@pytest.fixture
def part_a_invalid_url_data() -> PartAData:
    """TC-68: Website URL without http/https prefix."""
    return PartAFactory.invalid_website_url()


@pytest.fixture
def part_a_special_chars_name_data() -> PartAData:
    """TC-74: Agency name with special characters."""
    return PartAFactory.agency_name_with_special_chars()


@pytest.fixture
def part_a_duplicate_name_data() -> PartAData:
    """TC-76: Duplicate agency name (non-blocking warning)."""
    return PartAFactory.duplicate_agency_name()


@pytest.fixture
def part_a_without_branch_offices_data() -> PartAData:
    """TC-71: All mandatory fields, Branch Offices left blank."""
    return PartAFactory.without_branch_offices()


@pytest.fixture
def part_a_with_branch_offices_data() -> PartAData:
    """TC-72: All mandatory fields plus two branch office addresses."""
    return PartAFactory.with_branch_offices()


@pytest.fixture
def part_a_partial_data() -> PartAData:
    """TC-73: Only Agency Name and Official Email filled."""
    return PartAFactory.partial_fields_only()
