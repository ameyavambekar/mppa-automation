import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partC_page import PartCPage
from test_data.partC_factory import PartCData, PartCFactory, TypedInput
from utils.state_store import TestStateStore


def _login_and_open_part_c(page, user, editable: bool = True) -> PartCPage:
    """Logs in and opens Part C, clicking "Edit this section" when a saved Part C
    opens read-only (unless ``editable`` is False)."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    part_c = PartCPage(page)
    part_c.open()
    page.wait_for_load_state("networkidle")
    if editable:
        part_c.make_editable()
    return part_c


def _part_b_users():
    users = TestStateStore().get_agency_users_with_steps(["part_a", "part_b"])
    if not users:
        pytest.skip("No agency user with Part B saved in state store — run the Part B tests first.")
    return users


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_c_page(page) -> PartCPage:
    return PartCPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_part_c_page(page):
    """Yields (page, user) on an editable Part C, cleared client-side to its
    first-visit state (nothing saved). Prefers a user whose Part C is already
    saved, then the newest Part B user, so users with a never-saved Part C are
    kept for ``logged_in_part_c_unsaved_page``."""
    users = _part_b_users()
    user = next((u for u in users if u.steps.get("part_c") == "completed"), users[-1])
    part_c = _login_and_open_part_c(page, user)
    part_c.clear_form()
    yield page, user


@pytest.fixture
def logged_in_part_c_saved_page(page):
    """Yields (page, user) on Part C as it opens for a user who has saved it — read-only,
    "Edit this section" not clicked. Skips when the state store has no such user."""
    user = next((u for u in _part_b_users() if u.steps.get("part_c") == "completed"), None)
    if user is None:
        pytest.skip("No agency user with Part C saved in state store — run the Part C save tests first.")
    _login_and_open_part_c(page, user, editable=False)
    yield page, user


@pytest.fixture
def logged_in_part_c_unsaved_page(page):
    """Yields (page, user) on Part C for a user who has never saved it. A user
    found to have a saved Part C that the state store missed is recorded and
    skipped over. Skips when none is left."""
    store = TestStateStore()
    for user in _part_b_users():
        if user.steps.get("part_c") == "completed":
            continue
        part_c = _login_and_open_part_c(page, user)
        if part_c.placement_type_select.input_value() == "":
            yield page, user
            return
        store.mark_form_step_status(username=user.username, step="part_c", status="completed")
    pytest.skip("No agency user with Part B saved and Part C never saved in state store "
                "— run the Part B tests on a new user first.")


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def part_c_minimal_data() -> PartCData:
    """TC-120 / TC-136: mandatory fields only."""
    return PartCFactory.minimal()


@pytest.fixture
def part_c_training_data() -> PartCData:
    """TC-127 / TC-128: training = Yes with its own address."""
    return PartCFactory.with_training()


@pytest.fixture
def part_c_full_data() -> PartCData:
    """TC-142: every section filled."""
    return PartCFactory.full()


@pytest.fixture
def part_c_other_services_data() -> PartCData:
    """TC-137: Other Services filled."""
    return PartCFactory.with_other_services()


@pytest.fixture
def part_c_service_charges_data() -> PartCData:
    """TC-460: two agency types, charges not displayed."""
    return PartCFactory.service_charges()


@pytest.fixture
def part_c_digital_platform_data() -> PartCData:
    """TC-449: digital platform = Yes."""
    return PartCFactory.with_digital_platform()


@pytest.fixture
def part_c_training_same_address_data() -> PartCData:
    """TC-450: training at the registered office."""
    return PartCFactory.training_same_address()


@pytest.fixture
def part_c_mobilization_same_address_data() -> PartCData:
    """TC-451: mobilization at the registered office."""
    return PartCFactory.mobilization_same_address()


@pytest.fixture
def part_c_training_capacity_zero_data() -> PartCData:
    """TC-130: 0 rejected, 999999 accepted."""
    return PartCFactory.training_capacity_zero()


@pytest.fixture
def part_c_training_capacity_typed_cases() -> list[TypedInput]:
    """TC-130: Annual Training Capacity as-you-type rules."""
    return PartCFactory.training_capacity_typed_cases()


@pytest.fixture
def part_c_sector_other_invalid_data() -> PartCData:
    """TC-448: invalid Other sector texts."""
    return PartCFactory.sector_other_invalid()


@pytest.fixture
def part_c_centre_address_invalid_data() -> PartCData:
    """TC-452: invalid centre addresses."""
    return PartCFactory.centre_address_invalid()


@pytest.fixture
def part_c_training_sectors_invalid_data() -> PartCData:
    """TC-453: invalid Training Sectors."""
    return PartCFactory.training_sectors_invalid()


@pytest.fixture
def part_c_website_cases() -> PartCData:
    """TC-454: invalid and valid websites."""
    return PartCFactory.website_cases()


@pytest.fixture
def part_c_other_services_no_letters_data() -> PartCData:
    """TC-455: Other Services without letters."""
    return PartCFactory.other_services_no_letters()
