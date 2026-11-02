import os

import pytest

from config import ADMIN_LOGOUT_URL
from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.dashboard_page import AdminDashboardPage
from pages.admin.login_page import AdminLoginPage
from test_data.admin_dashboard_factory import AdminDashboardData, AdminDashboardFactory
from test_data.admin_login_factory import AdminLoginData, AdminLoginFactory
from utils.state_store import TestStateStore, UserRecord


# ── Default dev sub-admin (seeded in state/test_state.db) ──────────────────────
# Dedicated sub-admin account used by TC-179 (lockout) and TC-181 (killed
# session). Overridable via ADMIN_SUB_USERNAME / ADMIN_SUB_PASSWORD env vars.
DEFAULT_SUB_ADMIN_USERNAME = "Test"
DEFAULT_SUB_ADMIN_PASSWORD = "Qwerty@123"


# ── Credential helpers ─────────────────────────────────────────────────────────

def _super_admin_or_skip() -> UserRecord:
    """Returns a super_admin UserRecord.

    The ``.env`` file is the source of truth: ADMIN_SUPER_USERNAME /
    ADMIN_SUPER_PASSWORD are read first and synced into the state store. Only
    if those env vars are unset do we fall back to a previously recorded
    super_admin. Skips the test if neither source is available.
    """
    store = TestStateStore()
    username = os.getenv("ADMIN_SUPER_USERNAME")
    password = os.getenv("ADMIN_SUPER_PASSWORD")
    if username and password:
        store.record_user(role="super_admin", username=username, password=password)
        return store.get_user_by_username(username)

    user = store.get_any_super_admin()
    if user is not None:
        return user

    pytest.skip(
        "Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env "
        "(or seed a super_admin in the state store)."
    )


def _sub_admin_or_skip() -> UserRecord:
    """Returns the dedicated sub-admin (role='admin') UserRecord.

    Uses the seeded dev sub-admin (DEFAULT_SUB_ADMIN_USERNAME /
    DEFAULT_SUB_ADMIN_PASSWORD = 'Test' / 'Qwerty@123'), overridable via the
    ADMIN_SUB_USERNAME / ADMIN_SUB_PASSWORD env vars. The credentials are
    upserted into the state store and resolved by username, so the SAME
    account is always returned. Use a DEDICATED account — TC-179 will lock it.
    """
    store = TestStateStore()
    username = os.getenv("ADMIN_SUB_USERNAME", DEFAULT_SUB_ADMIN_USERNAME)
    password = os.getenv("ADMIN_SUB_PASSWORD", DEFAULT_SUB_ADMIN_PASSWORD)
    store.record_user(role="admin", username=username, password=password)
    return store.get_user_by_username(username)


def _agency_user_or_skip() -> UserRecord:
    user = TestStateStore().get_any_agency_user()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    return user


# ── Page object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_login_page(page) -> AdminLoginPage:
    return AdminLoginPage(page)


@pytest.fixture
def admin_audit_log_page(page) -> AdminAuditLogPage:
    return AdminAuditLogPage(page)


@pytest.fixture
def admin_dashboard_page(page) -> AdminDashboardPage:
    return AdminDashboardPage(page)


# ── Navigation fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def logged_in_admin_dashboard_page(page) -> AdminDashboardPage:
    """Logs in as super admin and yields the Admin Dashboard (where admin login lands).

    Logs the admin out on teardown: the browser context is shared across the whole
    session, so the admin session cookie would otherwise persist and the next test's
    ``login.open()`` would redirect straight to the dashboard.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    dashboard = AdminDashboardPage(page)
    dashboard.role_badge.wait_for()
    dashboard.open()
    yield dashboard
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def no_admin_session(page):
    """Ends any admin session left in the shared browser context, so the test starts logged out."""
    page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")


@pytest.fixture
def idle_timeout_allowed():
    """Skips the test unless RUN_IDLE_TIMEOUT_TESTS=true. The admin idle-timeout test (TC-175) has to
    sit idle for over 15 minutes, so it is run only on purpose. Run it with HEADLESS=true: in a visible
    window, mouse movement over the page counts as activity and the console never goes idle."""
    if os.getenv("RUN_IDLE_TIMEOUT_TESTS", "false").lower() != "true":
        pytest.skip("Waits over 15 minutes for the admin idle timeout — set RUN_IDLE_TIMEOUT_TESTS=true to run.")


@pytest.fixture
def admin_lockout_allowed():
    """Skips the test unless RUN_ADMIN_LOCKOUT_TESTS=true. TC-180 locks the Super Admin account for
    15 minutes — every admin test logs in as the Super Admin — so it is run only on purpose."""
    if os.getenv("RUN_ADMIN_LOCKOUT_TESTS", "false").lower() != "true":
        pytest.skip("Locks the Super Admin for 15 minutes — set RUN_ADMIN_LOCKOUT_TESTS=true to run.")


# ── User-record fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def super_admin_user() -> UserRecord:
    return _super_admin_or_skip()


@pytest.fixture
def sub_admin_user() -> UserRecord:
    return _sub_admin_or_skip()


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def valid_admin_login_data() -> AdminLoginData:
    """TC-169 / TC-172 — valid super admin credentials."""
    return AdminLoginFactory.valid_super_admin(_super_admin_or_skip())


@pytest.fixture
def wrong_credentials_data() -> AdminLoginData:
    """TC-170 — non-existent admin username / bad password."""
    return AdminLoginFactory.wrong_credentials()


@pytest.fixture
def wrong_captcha_admin_data() -> AdminLoginData:
    """TC-171 — valid credentials with an incorrect CAPTCHA."""
    return AdminLoginFactory.valid_creds_wrong_captcha(_super_admin_or_skip())


@pytest.fixture
def agency_creds_on_admin_data() -> AdminLoginData:
    """TC-173 — agency credentials entered on the Admin Login form."""
    return AdminLoginFactory.agency_creds_on_admin(_agency_user_or_skip())


@pytest.fixture
def admin_creds_for_agency_data() -> AdminLoginData:
    """TC-174 — admin credentials to try on the agency login page."""
    return AdminLoginFactory.admin_creds_for_agency_page(_super_admin_or_skip())


@pytest.fixture
def blank_username_admin_data() -> AdminLoginData:
    """TC-177 — username left blank."""
    return AdminLoginFactory.blank_username()


@pytest.fixture
def blank_password_admin_data() -> AdminLoginData:
    """TC-178 — password left blank."""
    return AdminLoginFactory.blank_password(_super_admin_or_skip())


@pytest.fixture
def stale_captcha_data() -> AdminLoginData:
    """TC-176 — valid credentials with a stale (pre-refresh) CAPTCHA."""
    return AdminLoginFactory.stale_captcha(_super_admin_or_skip())


@pytest.fixture
def subadmin_wrong_password_data() -> AdminLoginData:
    """TC-179 — wrong-password attempt for a sub-admin (locks the account)."""
    return AdminLoginFactory.subadmin_wrong_password(_sub_admin_or_skip())


@pytest.fixture
def subadmin_correct_data() -> AdminLoginData:
    """TC-179 — correct sub-admin credentials (expected blocked while locked)."""
    return AdminLoginFactory.subadmin_correct(_sub_admin_or_skip())


@pytest.fixture
def super_admin_wrong_password_data() -> AdminLoginData:
    """TC-180 — wrong-password attempt for the super admin (the 5th in a row locks it)."""
    return AdminLoginFactory.super_admin_wrong_password(_super_admin_or_skip())


@pytest.fixture
def admin_dashboard_state_data() -> AdminDashboardData:
    """Admin Dashboard — the default state-wide view."""
    return AdminDashboardFactory.state_wide()


@pytest.fixture
def admin_dashboard_pune_division_data() -> AdminDashboardData:
    """Admin Dashboard — filtered to Pune Division (with its District filter)."""
    return AdminDashboardFactory.pune_division()
