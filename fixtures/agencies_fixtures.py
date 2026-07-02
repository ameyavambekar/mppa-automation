import os

import pytest

from pages.admin.agencies_page import AdminAgenciesPage
from pages.admin.agency_view_page import AdminAgencyViewPage
from pages.admin.login_page import AdminLoginPage
from test_data.agencies_factory import AgenciesFactory, AgencyStatusData
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL



# ── Credential helpers ─────────────────────────────────────────────────────────

def _super_admin_or_skip() -> UserRecord:
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
def admin_agencies_page(page) -> AdminAgenciesPage:
    return AdminAgenciesPage(page)


@pytest.fixture
def admin_agency_view_page(page) -> AdminAgencyViewPage:
    return AdminAgencyViewPage(page)


@pytest.fixture
def logged_in_admin_agencies_page(page) -> AdminAgenciesPage:
    """Logs in as super admin then navigates to the All Agencies list.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin session cookie would otherwise persist and the
    next test's ``login.open()`` would redirect straight to the dashboard,
    breaking its login flow.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    agencies = AdminAgenciesPage(page)
    agencies.open()
    yield agencies
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def agency_status_restorer(logged_in_admin_agencies_page: AdminAgenciesPage):
    """Restores an agency's status after a status-mutating test.

    The test calls ``agency_status_restorer(username)`` BEFORE changing
    anything: the agency's current status badge is captured from its list
    row. On teardown each registered agency is set back to that status via
    the list's Change Status modal, so status-mutating tests (TC-202,
    TC-205, TC-206, TC-209, TC-211) leave the dev data as they found it.
    Assigned MPPA numbers cannot be unassigned — only the status reverts.
    """
    ap = logged_in_admin_agencies_page
    originals = []

    def _register(username: str) -> str:
        status = ap.get_row_status(username)
        originals.append((username, status))
        return status

    yield _register

    for username, status in originals:
        try:
            ap.open()
            if ap.get_row_status(username) != status:
                ap.change_status(username, status, AgenciesFactory.CLEANUP_REMARKS)
        except Exception:
            pass


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def approve_with_remarks_data() -> AgencyStatusData:
    """TC-202 — approval with optional remarks."""
    return AgenciesFactory.approve_with_remarks()


@pytest.fixture
def reject_blank_remarks_data() -> AgencyStatusData:
    """TC-203 — rejection with blank remarks, expects block."""
    return AgenciesFactory.reject_blank_remarks()


@pytest.fixture
def suspend_blank_remarks_data() -> AgencyStatusData:
    """TC-204 — suspension with blank remarks, expects block."""
    return AgenciesFactory.suspend_blank_remarks()


@pytest.fixture
def reject_with_remarks_data() -> AgencyStatusData:
    """TC-205 — rejection with valid remarks for the audit-trail check."""
    return AgenciesFactory.reject_with_remarks()


@pytest.fixture
def suspend_with_remarks_data() -> AgencyStatusData:
    """TC-206 / TC-211 — suspension with valid remarks."""
    return AgenciesFactory.suspend_with_remarks()
