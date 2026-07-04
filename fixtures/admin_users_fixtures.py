import os

import pytest

from pages.admin.login_page import AdminLoginPage
from pages.admin.users_page import AdminUsersPage
from test_data.admin_users_factory import AdminUserData, AdminUsersFactory
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL



# ── Credential helpers ─────────────────────────────────────────────────────────

def _super_admin_or_skip() -> UserRecord:
    """A super_admin UserRecord from .env (preferred) or the state store."""
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


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_users_page(page) -> AdminUsersPage:
    return AdminUsersPage(page)


@pytest.fixture
def logged_in_admin_users_page(page) -> AdminUsersPage:
    """Logs in as super admin then opens Admin User Management.

    Logs the admin out on teardown: the browser context is shared across the
    session, so a lingering admin cookie would send the next test's login flow
    straight to the dashboard.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    users = AdminUsersPage(page)
    users.open()
    yield users
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


# ── Created-account cleanup ────────────────────────────────────────────────────

@pytest.fixture
def created_admins(logged_in_admin_users_page: AdminUsersPage):
    """Tracks admin accounts a test creates and deletes them on teardown.

    The test calls ``created_admins(username)`` right after creating an account.
    On teardown each registered account is deleted (tolerantly — a test that
    deletes its own account, e.g. TC-276, leaves nothing to clean up), so the
    create tests don't accumulate accounts in the dev environment.
    """
    sp = logged_in_admin_users_page
    registered: list = []

    def _register(username: str) -> str:
        registered.append(username)
        return username

    yield _register

    for username in registered:
        try:
            sp.open()
            if sp.row_exists(username):
                sp.delete_admin(username, action="accept")
                sp.wait_for_load()
        except Exception:
            pass


@pytest.fixture
def throwaway_admin(logged_in_admin_users_page: AdminUsersPage, created_admins) -> AdminUserData:
    """Creates a fresh, valid sub-admin and registers it for cleanup.

    Used by the toggle / delete / new-account tests that need a real,
    self-contained account to act on without touching shared dev accounts."""
    sp = logged_in_admin_users_page
    data = AdminUsersFactory.new_admin(scenario_label="throwaway")
    sp.create_admin(
        data.username, data.full_name, data.email, data.password,
        role=data.role, permissions=data.permissions,
    )
    sp.wait_for_load()
    created_admins(data.username)
    return data


@pytest.fixture
def inactive_throwaway_admin(
    logged_in_admin_users_page: AdminUsersPage, throwaway_admin: AdminUserData
) -> AdminUserData:
    """A throwaway sub-admin already toggled to Inactive (TC-274 precondition)."""
    sp = logged_in_admin_users_page
    sp.toggle_admin_active_and_wait(throwaway_admin.username)
    sp.open()  # reload so the row reflects the persisted Inactive state
    return throwaway_admin


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def new_admin_data() -> AdminUserData:
    """TC-270 — a brand-new, valid admin account."""
    return AdminUsersFactory.new_admin()


@pytest.fixture
def short_username_data() -> AdminUserData:
    """TC-277 — username shorter than 4 characters."""
    return AdminUsersFactory.short_username()


@pytest.fixture
def weak_password_data() -> AdminUserData:
    """TC-278 — password missing the required complexity."""
    return AdminUsersFactory.weak_password()
