import pytest

from config import FORMS_BASE
from pages.declaration_page import DeclarationPage
from pages.login_page import LoginPage
from test_data.declaration_factory import DeclarationData, DeclarationFactory
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore


def _login_and_open_declaration(page, user) -> DeclarationPage:
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    declaration = DeclarationPage(page)
    declaration.open()
    page.wait_for_load_state("networkidle")
    return declaration


def _already_uploaded(declaration: DeclarationPage, store: TestStateStore, user) -> bool:
    """True when the state store missed an upload (counter above 0 or a card no longer PENDING);
    records it so the user is skipped from now on."""
    uploaded = (declaration.counter.inner_text().strip() != DeclarationPage.counter_text(0)
                or any(declaration.badge(key).inner_text().strip() != DeclarationPage.BADGE_PENDING
                       for key in DeclarationPage.FORMS))
    if uploaded:
        store.mark_form_step_status(username=user.username, step="declaration", status="in_progress")
    return uploaded


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def declaration_page(page) -> DeclarationPage:
    return DeclarationPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_declaration_page(page):
    """Yields (page, user) on the Declaration step for an agency whose Premises Photos step is
    complete and who has never uploaded a signed form (counter 0 / 2, both forms PENDING).
    Users with an upload are never used; when none is left, a new agency is built (see
    ``utils.agency_builder``)."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b", "part_c", "part_f", "enclosures", "premises"]):
        if user.steps.get("declaration") in ("in_progress", "completed"):
            continue
        if not _already_uploaded(_login_and_open_declaration(page, user), store, user):
            yield page, user
            return
    user = AgencyBuilder(page, store).build("premises")
    _login_and_open_declaration(page, user)
    yield page, user


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def declaration_signed_forms_data() -> DeclarationData:
    """TC-495: a signed PDF for each form."""
    return DeclarationFactory.signed_forms()


@pytest.fixture
def declaration_not_pdf_data() -> DeclarationData:
    """TC-501: a JPG and a PNG."""
    return DeclarationFactory.not_pdf()


@pytest.fixture
def declaration_too_large_data() -> DeclarationData:
    """TC-502: a 3 MB PDF, then a valid one."""
    return DeclarationFactory.too_large()
