# pyrefly: ignore [missing-import]
import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partA_page import PartAPage
from test_data.step1_factory import PartAData, PartAFactory, TypedInput
from utils.state_store import TestStateStore


def _login_and_navigate_to_step1(page, user):
    """Logs in, waits for the Form-I wizard, then opens Step 1 — Part A.

    Login lands on the step the user stopped at, so Part A is opened
    explicitly for users who have already completed it."""
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    PartAPage(page).open()
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
    """TC-58: every mandatory field, Maharashtra head office, no branches."""
    return PartAFactory.valid_mandatory_fields()


@pytest.fixture
def part_a_future_date_data() -> PartAData:
    """TC-62: a future date forced into the read-only date box."""
    return PartAFactory.future_date()


@pytest.fixture
def part_a_invalid_date_data() -> PartAData:
    """TC-63: a date in a format other than DD/MM/YYYY."""
    return PartAFactory.invalid_date_format()


@pytest.fixture
def part_a_invalid_tan_data() -> PartAData:
    """TC-64: TAN in an incorrect format."""
    return PartAFactory.invalid_tan_format()


@pytest.fixture
def part_a_tan_typed_lowercase() -> TypedInput:
    """TC-64 step 1: lower-case TAN with separators."""
    return PartAFactory.tan_typed_lowercase()


@pytest.fixture
def part_a_invalid_gstin_data() -> PartAData:
    """TC-65: 15-character GSTIN that doesn't match the format."""
    return PartAFactory.invalid_gstin_format()


@pytest.fixture
def part_a_without_branch_offices_data() -> PartAData:
    """TC-71: all mandatory fields, no branch office."""
    return PartAFactory.without_branch_offices()


@pytest.fixture
def part_a_with_branch_offices_data() -> PartAData:
    """TC-72: all mandatory fields plus two branch offices."""
    return PartAFactory.with_branch_offices()


@pytest.fixture
def part_a_unsaved_signatory_data() -> PartAData:
    """TC-78: one unsaved value before pressing browser back."""
    return PartAFactory.unsaved_signatory()


@pytest.fixture
def part_a_session_timeout_data() -> PartAData:
    """TC-80: fields entered before the session times out."""
    return PartAFactory.session_timeout_partial()


@pytest.fixture
def part_a_outside_maharashtra_data() -> PartAData:
    """TC-427 / TC-428: head office in Gujarat plus the Primary Maharashtra Office."""
    return PartAFactory.head_office_outside_maharashtra()


@pytest.fixture
def part_a_partial_data() -> PartAData:
    """TC-429: a few fields entered without saving."""
    return PartAFactory.partial_fields_only()


@pytest.fixture
def part_a_proprietorship_data() -> PartAData:
    """TC-430: Proprietorship without incorporation details."""
    return PartAFactory.proprietorship_without_incorporation()


@pytest.fixture
def part_a_branch_premise_other_data() -> PartAData:
    """TC-431: a branch whose premise type is Other."""
    return PartAFactory.branch_premise_other()


@pytest.fixture
def part_a_pincode_out_of_range_data() -> PartAData:
    """TC-434: out-of-range then in-range Maharashtra pincode."""
    return PartAFactory.pincode_outside_maharashtra()


@pytest.fixture
def part_a_as_you_type_cases() -> list[TypedInput]:
    """TC-436: raw input per text field and what the field shows."""
    return PartAFactory.as_you_type_cases()
