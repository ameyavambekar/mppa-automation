import os
from dataclasses import dataclass

import pytest

from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.sessions_page import AdminSessionsPage
from pages.login_page import LoginPage
from test_data.sessions_factory import SessionData, SessionsFactory
from utils import failure_pages
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL, AUTH_BASE

AGENCY_LOGOUT_URL = f"{AUTH_BASE}/logout.php"


# ── Credential helpers ─────────────────────────────────────────────────────────

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
    pytest.skip(
        "Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env "
        "(or seed a super_admin in the state store)."
    )


# ── Agency session handle (used by the kill tests) ─────────────────────────────

@dataclass
class AgencySessionHandle:
    """A live agency session opened in an independent second browser.

    ``page`` is sitting where login lands (the agency home page — only
    agencies with a submitted application are listed); ``username``
    is what the admin Sessions table shows in its Username column for this
    session (so the admin side can locate and kill exactly this session)."""
    page: object
    username: str
    password: str


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_sessions_page(page) -> AdminSessionsPage:
    return AdminSessionsPage(page)


@pytest.fixture
def logged_in_admin_sessions_page(page) -> AdminSessionsPage:
    """Logs in as super admin then navigates to Session Management.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin cookie would otherwise leak into the next test.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(admin.username, admin.password)
    if error:
        pytest.fail(f"Admin login as {admin.username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)
    sessions = AdminSessionsPage(page)
    sessions.open()
    yield sessions
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def agency_session(second_browser, request):
    """Factory that logs an agency user into a fresh (visible) second browser,
    creating a brand-new Live session, and returns an ``AgencySessionHandle``.

    Used by TC-249 (kill a single session) and TC-250 (killed user is bounced
    to login). Targeting a session we created ourselves keeps the kill tests
    self-contained — they never terminate an unrelated user's live session.

    On teardown every agency session opened is logged out (harmless if it was
    already killed), then ``second_browser`` closes the browser.
    """
    handles: list[AgencySessionHandle] = []

    def _open() -> AgencySessionHandle:
        # Only agencies with a submitted application (they land on home.php) get a row in Session
        # Management; a user still in the Form-I wizard is never listed, so it cannot be killed.
        agencies = TestStateStore().get_agency_users_with_application()
        if not agencies:
            pytest.skip("No agency with a submitted application in the state store — run the Payment tests first.")

        browser = second_browser()
        for agency in agencies[:3]:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            p = ctx.new_page()
            failure_pages.register(request.node, p, f"agency {agency.username}")
            login = LoginPage(p)
            login.open()
            login.login(agency.username, agency.password)
            p.wait_for_load_state("networkidle")
            if "login" not in p.url:
                handle = AgencySessionHandle(page=p, username=agency.username, password=agency.password)
                handles.append(handle)
                return handle
            ctx.close()
        pytest.fail("None of the first three agencies with an application could log in.")

    yield _open

    for h in handles:
        try:
            h.page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        except Exception:
            pass


@pytest.fixture
def kill_all_allowed():
    """Skips the test unless RUN_KILL_ALL_TESTS=true. Kill All Active (TC-251, TC-256) ends EVERY open
    agency session on dev — anyone testing as an agency is logged out — so it is run only on purpose."""
    if os.getenv("RUN_KILL_ALL_TESTS", "false").lower() != "true":
        pytest.skip("Kill All ends every open agency session on dev — set RUN_KILL_ALL_TESTS=true to run.")


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def dashboard_tiles_data() -> SessionData:
    """TC-246 — expected tiles + column set."""
    return SessionsFactory.dashboard_tiles()


@pytest.fixture
def all_tab_data() -> SessionData:
    """TC-247 — expected columns for the default All tab."""
    return SessionsFactory.all_tab_layout()


@pytest.fixture
def kill_single_session_data() -> SessionData:
    """TC-249 — expected dialog / reason / status for a single kill."""
    return SessionsFactory.kill_single_session()


@pytest.fixture
def kill_redirect_data() -> SessionData:
    """TC-250 — kill then verify the agency user is bounced to login."""
    return SessionsFactory.kill_then_redirect()


@pytest.fixture
def kill_all_confirmation_data() -> SessionData:
    """TC-251 / TC-252 — Kill-All confirm dialog fragment."""
    return SessionsFactory.kill_all_confirmation()


@pytest.fixture
def stale_session_data() -> SessionData:
    """TC-254 — expected status/reason for a stale session row."""
    return SessionsFactory.stale_session_row()


@pytest.fixture
def no_ping_data() -> SessionData:
    """TC-255 — expected 'No ping' Last Ping text."""
    return SessionsFactory.no_ping_session()


@pytest.fixture
def kill_all_disabled_data() -> SessionData:
    """TC-256 — Kill-All unavailable when no active sessions exist."""
    return SessionsFactory.kill_all_disabled()
