import os

import pytest

from pages.admin.dashboard_page import AdminDashboardPage
from pages.admin.login_page import AdminLoginPage
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
def admin_dashboard_page(page) -> AdminDashboardPage:
    return AdminDashboardPage(page)


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
    """TC-180 — wrong-password attempt for the super admin (never locks)."""
    return AdminLoginFactory.super_admin_wrong_password(_super_admin_or_skip())
