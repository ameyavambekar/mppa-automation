import re

import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partB_page import PartBPage
from test_data.partB_factory import KeyPersonData, PartBFactory, TypedInput
from utils.state_store import TestStateStore


def _login_and_open_part_b(page, user) -> PartBPage:
    """Logs in and opens Part B, leaving a single person card.

    Cards beyond the first are removed client-side (nothing is saved), so every
    test starts from "only <label> 1 is shown"."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    part_b = PartBPage(page)
    part_b.open()
    page.wait_for_load_state("networkidle")
    part_b.remove_added_persons()
    return part_b


def _part_b_already_saved(part_b: PartBPage, store: TestStateStore, user) -> bool:
    """A saved Part B reopens read-only with "Edit this section". When the state store
    missed that save, record it so the user is skipped from now on."""
    if not part_b.edit_section_link.is_visible():
        return False
    store.mark_form_step_status(username=user.username, step="part_b", status="completed")
    return True


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_b_page(page) -> PartBPage:
    return PartBPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def part_b_login_as(page):
    """Returns ``login_as(agency_type)``: logs in as a stored user whose Part A was
    saved with that legal constitution and whose Part B has never been saved, opens
    Part B with one card, and returns the user. Users with Part B saved are never
    used. Skips when no such user exists."""

    def login_as(agency_type: str):
        store = TestStateStore()
        for user in store.get_agency_users_with_steps(["part_a"], legal_constitution=agency_type):
            if user.steps.get("part_b") == "completed":
                continue
            part_b = _login_and_open_part_b(page, user)
            if not _part_b_already_saved(part_b, store, user):
                return user
        # Part A saved before its agency type was recorded — read it off Part B once and record it.
        for user in store.get_agency_users_with_steps(["part_a"]):
            if "legal_constitution" in user.step_data.get("part_a", {}) or user.steps.get("part_b") == "completed":
                continue
            part_b = _login_and_open_part_b(page, user)
            # Greedy up to the last ')' — "Limited Liability Partnership (LLP)" has its own.
            shown = re.search(r"based on your agency type: (.+)\)", part_b.category_banner.inner_text())
            if shown is None:
                continue
            store.mark_form_step_status(username=user.username, step="part_a", status="completed",
                                        data={"legal_constitution": shown.group(1).strip()})
            if shown.group(1).strip() == agency_type and not _part_b_already_saved(part_b, store, user):
                return user
        pytest.skip(f"No agency user with Part A saved as '{agency_type}' and Part B not saved in state store "
                    "— run the Part A tests first.")

    return login_as


@pytest.fixture
def logged_in_part_b_page(page, part_b_login_as):
    """Yields (page, user) for a Private Limited Company user with Part A saved and
    Part B never saved, on Part B with only Director 1."""
    user = part_b_login_as(PartBFactory.AGENCY_TYPE)
    yield page, user


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def part_b_valid_data() -> KeyPersonData:
    """TC-113: one complete, valid Director."""
    return PartBFactory.valid_director()


@pytest.fixture
def part_b_second_valid_data() -> KeyPersonData:
    """TC-114: a second, different Director."""
    return PartBFactory.second_valid_director()


@pytest.fixture
def part_b_blank_data() -> KeyPersonData:
    """TC-84: every field empty."""
    return PartBFactory.blank()


@pytest.fixture
def part_b_long_name_data() -> KeyPersonData:
    """TC-85: a 151-character Full Name."""
    return PartBFactory.full_name_too_long()


@pytest.fixture
def part_b_invalid_name_data() -> KeyPersonData:
    """TC-87: names with digits and symbols."""
    return PartBFactory.full_name_invalid_characters()


@pytest.fixture
def part_b_aadhaar_blank_data() -> KeyPersonData:
    """TC-89: Aadhaar left empty."""
    return PartBFactory.aadhaar_blank()


@pytest.fixture
def part_b_aadhaar_short_data() -> KeyPersonData:
    """TC-90: an 8-digit Aadhaar."""
    return PartBFactory.aadhaar_too_short()


@pytest.fixture
def part_b_aadhaar_prefix_data() -> KeyPersonData:
    """TC-91: Aadhaar numbers starting with 0 and 1."""
    return PartBFactory.aadhaar_starts_with_0_or_1()


@pytest.fixture
def part_b_foreign_national_data() -> KeyPersonData:
    """TC-94: a foreign national."""
    return PartBFactory.foreign_national()


@pytest.fixture
def part_b_passport_cleared_data() -> KeyPersonData:
    """TC-95: a passport entered, then nationality set back to Indian."""
    return PartBFactory.passport_cleared_for_indian()


@pytest.fixture
def part_b_address_invalid_data() -> KeyPersonData:
    """TC-97: Address empty, then too short."""
    return PartBFactory.address_blank_then_short()


@pytest.fixture
def part_b_personal_email_data() -> KeyPersonData:
    """TC-102 / TC-442: a valid personal email."""
    return PartBFactory.with_personal_email()


@pytest.fixture
def part_b_malformed_email_data() -> KeyPersonData:
    """TC-103: malformed personal emails."""
    return PartBFactory.malformed_emails()


@pytest.fixture
def part_b_mobile_blank_data() -> KeyPersonData:
    """TC-105: Mobile left empty."""
    return PartBFactory.mobile_blank()


@pytest.fixture
def part_b_mobile_wrong_format_data() -> KeyPersonData:
    """TC-106: mobile numbers that don't match [6-9][0-9]{9}."""
    return PartBFactory.mobile_wrong_format()


@pytest.fixture
def part_b_din_pan_blank_data() -> KeyPersonData:
    """TC-439: DIN / DPIN and PAN empty, then a short DIN."""
    return PartBFactory.din_and_pan_blank()


@pytest.fixture
def part_b_duplicate_aadhaar_data() -> KeyPersonData:
    """TC-112: a second Director reusing the first one's Aadhaar."""
    return PartBFactory.duplicate_aadhaar_director()


@pytest.fixture
def part_b_unsaved_name_data() -> KeyPersonData:
    """TC-443: a name typed and never saved."""
    return PartBFactory.unsaved_name()


@pytest.fixture
def part_b_aadhaar_typed_cases() -> list[TypedInput]:
    """TC-92: Aadhaar as-you-type rules."""
    return PartBFactory.aadhaar_typed_cases()


@pytest.fixture
def part_b_aadhaar_max_length_case() -> TypedInput:
    """TC-88: a 13th Aadhaar digit."""
    return PartBFactory.aadhaar_max_length_case()


@pytest.fixture
def part_b_mobile_typed_cases() -> list[TypedInput]:
    """TC-107: Mobile as-you-type rules."""
    return PartBFactory.mobile_typed_cases()


@pytest.fixture
def part_b_mobile_max_length_case() -> TypedInput:
    """TC-104: an 11th mobile digit."""
    return PartBFactory.mobile_max_length_case()


@pytest.fixture
def part_b_din_typed_cases() -> list[TypedInput]:
    """TC-438: DIN / DPIN as-you-type rules."""
    return PartBFactory.din_typed_cases()


@pytest.fixture
def part_b_pan_typed_cases() -> list[TypedInput]:
    """TC-440: PAN as-you-type rules."""
    return PartBFactory.pan_typed_cases()
