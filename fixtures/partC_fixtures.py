import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partC_page import PartCPage
from test_data.partC_factory import PartCData, PartCFactory, TypedInput
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore


def _login_and_open_part_c(page, user) -> PartCPage:
    """Logs in and opens Part C."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    part_c = PartCPage(page)
    part_c.open()
    page.wait_for_load_state("networkidle")
    return part_c


def _part_c_already_saved(part_c: PartCPage, store: TestStateStore, user) -> bool:
    """A saved Part C reopens read-only with "Edit this section". When the state store
    missed that save, record it so the user is skipped from now on."""
    if not part_c.edit_section_link.is_visible():
        return False
    store.mark_form_step_status(username=user.username, step="part_c", status="completed")
    return True


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def part_c_page(page) -> PartCPage:
    return PartCPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_part_c_page(page):
    """Yields (page, user) on Part C for a user whose Part B is saved and whose Part C
    has never been saved, so the form is in its first-visit state. Users with Part C
    saved are never used; when none is left, a new agency is built (see
    ``utils.agency_builder``)."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b"]):
        if user.steps.get("part_c") == "completed":
            continue
        part_c = _login_and_open_part_c(page, user)
        if not _part_c_already_saved(part_c, store, user):
            yield page, user
            return
    user = AgencyBuilder(page, store).build("part_b")
    _login_and_open_part_c(page, user)
    yield page, user


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
