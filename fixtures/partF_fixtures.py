import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partF_page import PartFPage
from test_data.partF_factory import PartFData, PartFFactory, TypedInput
from utils.state_store import TestStateStore


def _login_and_open_part_f(page, user) -> PartFPage:
    """Logs in and opens Part F (a saved Part F reopens editable)."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    part_f = PartFPage(page)
    part_f.open()
    page.wait_for_load_state("networkidle")
    return part_f


def _remove_saved_documents(page, part_f: PartFPage) -> None:
    """A saved certificate document is no longer "missing", which would hide the
    'Please upload the document.' errors. Saving every certificate as No removes them."""
    if not any(part_f.has_saved_document(cert) for cert in PartFPage.CERTIFICATES):
        return
    part_f.clear_form()
    part_f.select_place(PartFFactory.PLACE)
    part_f.click_submit()
    part_f.success_message.wait_for()
    part_f.open()
    page.wait_for_load_state("networkidle")


def _part_c_users():
    users = TestStateStore().get_agency_users_with_steps(["part_a", "part_b", "part_c"])
    if not users:
        pytest.skip("No agency user with Part C saved in state store — run the Part C tests first.")
    return users


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_f_page(page) -> PartFPage:
    return PartFPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_part_f_page(page):
    """Yields (page, user) on Part F, cleared client-side to its first-visit state.
    Saved certificate documents are removed first (see ``_remove_saved_documents``).
    Prefers a user whose Part F is already saved, so users with a never-saved
    Part F are kept for ``logged_in_part_f_unsaved_page``."""
    users = _part_c_users()
    user = next((u for u in users if u.steps.get("part_f") == "completed"), users[-1])
    part_f = _login_and_open_part_f(page, user)
    _remove_saved_documents(page, part_f)
    part_f.clear_form()
    yield page, user


@pytest.fixture
def logged_in_part_f_unsaved_page(page):
    """Yields (page, user) on Part F for a user who has never saved it. A user found
    to have a saved Part F that the state store missed is recorded and skipped over.
    Skips when none is left."""
    store = TestStateStore()
    for user in _part_c_users():
        if user.steps.get("part_f") == "completed":
            continue
        part_f = _login_and_open_part_f(page, user)
        if part_f.place_select.input_value() == "":
            yield page, user
            return
        store.mark_form_step_status(username=user.username, step="part_f", status="completed")
    pytest.skip("No agency user with Part C saved and Part F never saved in state store "
                "— run the Part C tests on a new user first.")


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def part_f_all_no_data() -> PartFData:
    """TC-143 / TC-148: every certificate No, Place chosen."""
    return PartFFactory.all_no()


@pytest.fixture
def part_f_all_six_data() -> PartFData:
    """TC-144: all six certificates filled, plus a signature."""
    return PartFFactory.all_six()


@pytest.fixture
def part_f_contractor_licence_data() -> PartFData:
    """TC-154 / TC-155 / TC-156 / TC-162: a complete Contractor Licence."""
    return PartFFactory.contractor_licence()


@pytest.fixture
def part_f_lin_only_data() -> PartFData:
    """TC-163: only the LIN answered Yes."""
    return PartFFactory.lin_only()


@pytest.fixture
def part_f_future_date_data() -> PartFData:
    """TC-160: a future Date of Issue."""
    return PartFFactory.future_date()


@pytest.fixture
def part_f_invalid_dates_data() -> PartFData:
    """TC-161: impossible, pre-1900 and incomplete dates."""
    return PartFFactory.invalid_dates()


@pytest.fixture
def part_f_psara_number_data() -> PartFData:
    """TC-466: PSARA Licence No. rules."""
    return PartFFactory.psara_number_rules()


@pytest.fixture
def part_f_date_typed_cases() -> list[TypedInput]:
    """TC-467: date typing help."""
    return PartFFactory.date_typed_cases()
