import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partF_page import PartFPage
from test_data.partF_factory import PartFData, PartFFactory, TypedInput
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore


def _login_and_open_part_f(page, user) -> PartFPage:
    """Logs in and opens Part F."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    part_f = PartFPage(page)
    part_f.open()
    page.wait_for_load_state("networkidle")
    return part_f


def _part_f_already_saved(part_f: PartFPage, store: TestStateStore, user) -> bool:
    """A saved Part F reopens editable but with "Next: Documents →". When the state
    store missed that save, record it so the user is skipped from now on."""
    if not part_f.next_documents_link.is_visible():
        return False
    store.mark_form_step_status(username=user.username, step="part_f", status="completed")
    return True


def _offline(user) -> bool:
    """Part C was recorded with a Service Mode that includes offline work."""
    return bool(user.step_data.get("part_c", {}).get("offline"))


def _part_f_asks_for_premises(part_f: PartFPage, store: TestStateStore, user) -> bool:
    """Part F shows the office premises document only for an offline Service Mode. When
    the store did not know that, record it so the user goes to the offline fixture."""
    if not part_f.premises_file_input.count():
        return False
    store.mark_form_step_status(username=user.username, step="part_c", status="completed",
                                data={"offline": True})
    return True


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_f_page(page) -> PartFPage:
    return PartFPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_part_f_page(page):
    """Yields (page, user) on Part F for a user whose Part C is saved and whose Part F
    has never been saved, so the form is in its first-visit state. Users with Part F
    saved are never used; when none is left, a new agency is built (see
    ``utils.agency_builder``). Part C's Service Mode is Online Only, so there is no
    office premises document."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b", "part_c"]):
        if user.steps.get("part_f") == "completed" or _offline(user):
            continue
        part_f = _login_and_open_part_f(page, user)
        if not _part_f_already_saved(part_f, store, user) and not _part_f_asks_for_premises(part_f, store, user):
            yield page, user
            return
    user = AgencyBuilder(page, store).build("part_c")
    _login_and_open_part_f(page, user)
    yield page, user


@pytest.fixture
def logged_in_offline_part_f_page(page):
    """Yields (page, user) on a never-saved Part F for a user whose Part C Service Mode
    includes offline work, so Part F asks for the office premises document. Only users
    recorded as offline are tried; when none is left, one is built with Service Mode
    "Offline Only"."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b", "part_c"]):
        if user.steps.get("part_f") == "completed" or not _offline(user):
            continue
        part_f = _login_and_open_part_f(page, user)
        if not _part_f_already_saved(part_f, store, user):
            yield page, user
            return
    user = AgencyBuilder(page, store).build("part_c", offline=True)
    _login_and_open_part_f(page, user)
    yield page, user


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
def part_f_premises_data() -> PartFData:
    """TC-579: every certificate No, with an office premises document."""
    return PartFFactory.with_premises_document()


@pytest.fixture
def part_f_undersized_certificate_data() -> PartFData:
    """TC-574: Contractor Licence with a document under 10 KB."""
    return PartFFactory.undersized_certificate()


@pytest.fixture
def part_f_undersized_signature_data() -> PartFData:
    """TC-575: a signature under 10 KB."""
    return PartFFactory.undersized_signature()


@pytest.fixture
def part_f_date_typed_cases() -> list[TypedInput]:
    """TC-467: date typing help."""
    return PartFFactory.date_typed_cases()
