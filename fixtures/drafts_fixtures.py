import os

import pytest

from config import ADMIN_LOGOUT_URL
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.drafts_page import AdminDraftsPage
from pages.admin.login_page import AdminLoginPage
from test_data.drafts_factory import DraftsData, DraftsFactory
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore, UserRecord


# ── Helpers ────────────────────────────────────────────────────────────────────

def _super_admin_or_skip() -> UserRecord:
    """Returns a super_admin UserRecord (``.env`` first, then the state store)."""
    store = TestStateStore()
    username = os.getenv("ADMIN_SUPER_USERNAME")
    password = os.getenv("ADMIN_SUPER_PASSWORD")
    if username and password:
        store.record_user(role="super_admin", username=username, password=password)
        return store.get_user_by_username(username)
    user = store.get_any_super_admin()
    if user is not None:
        return user
    pytest.skip("Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env (or seed a super_admin in the state store).")


def _admin_login(page) -> None:
    """Logs in to the Officer Console as the Super Admin (retrying a misread Security Code).

    A successful login shows "Login Successful!" on login.php, which moves to the dashboard by script
    0.7 s later; waits for that, or it would abort the caller's next ``goto`` (net::ERR_ABORTED)."""
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(admin.username, admin.password)
    if error:
        pytest.fail(f"Admin login as {admin.username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)


def _admin_logout(page) -> None:
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_drafts_page(page) -> AdminDraftsPage:
    return AdminDraftsPage(page)


@pytest.fixture
def logged_in_admin_drafts_page(page) -> AdminDraftsPage:
    """Logs in as the Super Admin and opens Registrations in Progress (All drafts). Logs out on teardown
    (the browser context is shared across the session)."""
    _admin_login(page)
    drafts = AdminDraftsPage(page)
    drafts.open()
    yield drafts
    _admin_logout(page)


@pytest.fixture
def known_draft(logged_in_admin_drafts_page: AdminDraftsPage):
    """Yields (drafts page, agency) for an unpaid draft of an agency the state store knows, with its e-mail,
    mobile, PAN and district recorded. Picks the oldest such draft — the one closest to its deadline, which
    the Extend test then moves later."""
    drafts = logged_in_admin_drafts_page
    store = TestStateStore()
    for username in reversed(drafts.usernames()):
        user = store.get_user_by_username(username)
        if user and user.email and user.pan and user.mobile and user.district and not user.application_id:
            yield drafts, user
            return
    pytest.skip("No unpaid draft of an agency the state store knows — run the registration tests first.")


@pytest.fixture
def throwaway_draft(page):
    """Registers a brand-new agency (its draft is used up by the Delete test), then logs in as the Super Admin
    and opens Registrations in Progress searched to that agency. Yields (drafts page, agency)."""
    user = AgencyBuilder(page).build("registered")
    _admin_login(page)
    drafts = AdminDraftsPage(page)
    drafts.open(filter_="all", query=user.username)
    yield drafts, user
    _admin_logout(page)


@pytest.fixture
def paid_agency() -> UserRecord:
    """An agency the tests paid for (it has an Application ID)."""
    users = [u for u in TestStateStore().get_agency_users_with_application() if u.application_id]
    if not users:
        pytest.skip("No paid agency in the state store — run TC-513 first.")
    return users[-1]


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def extend_deadline_data() -> DraftsData:
    return DraftsFactory.extend("3")


@pytest.fixture
def unknown_drafts_filter_data() -> DraftsData:
    return DraftsFactory.unknown_filter()


@pytest.fixture
def no_match_search_data() -> DraftsData:
    return DraftsFactory.no_match_search()


@pytest.fixture
def deadline_rule_data() -> DraftsData:
    return DraftsFactory.deadline_rule()


@pytest.fixture
def delete_confirmation_data() -> DraftsData:
    return DraftsFactory.delete_confirmation()
