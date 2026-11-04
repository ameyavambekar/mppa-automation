import pytest

from config import ADMIN_LOGOUT_URL
from fixtures.sessions_fixtures import _super_admin_or_skip
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.users_page import OFFICERS_URL, OfficersPage
from test_data.admin_users_factory import OfficerData, OfficersFactory


def _logout(page):
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_officers_page(page) -> OfficersPage:
    """Logs in as the Super Administrator and opens Officers & Access; logs out on teardown."""
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(admin.username, admin.password)
    if error:
        pytest.fail(f"Admin login as {admin.username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)
    officers = OfficersPage(page)
    officers.open()
    yield officers
    _logout(page)


@pytest.fixture
def new_officers(logged_in_officers_page: OfficersPage):
    """Creates NEW test officers and deletes them on teardown — never an existing officer.

    ``new_officers.create(data)`` saves ``data`` through the save API (as the Super Administrator) and returns it
    with ``id`` set. ``new_officers.track(data)`` registers an officer a test created another way (the form, or a
    save request expected to fail) by looking up its id. Teardown deletes each tracked id only while its username
    is still the one the test created.
    """
    op = logged_in_officers_page
    tracked: dict[int, str] = {}

    class _Officers:
        @staticmethod
        def create(data: OfficerData) -> OfficerData:
            res = op.api("admins.save", op.save_payload(data))
            if not res["ok"]:
                pytest.fail(f"Could not create test officer {data.username}: {res['msg']}")
            data.id = res["data"]["id"]
            tracked[data.id] = data.username
            return data

        @staticmethod
        def track(data: OfficerData) -> OfficerData:
            row = op.find_officer(data.username)
            if row:
                data.id = row["id"]
                tracked[data.id] = data.username
            return data

        @staticmethod
        def track_id(officer_id: int, username: str):
            tracked[officer_id] = username

    yield _Officers

    if not tracked:
        return
    if OFFICERS_URL not in op.page.url:
        op.page.goto(ADMIN_DASHBOARD_URL)
        if "login" in op.page.url:          # the test logged out — sign in again to clean up
            admin = _super_admin_or_skip()
            AdminLoginPage(op.page).open()
            AdminLoginPage(op.page).login_past_captcha(admin.username, admin.password)
        op.open()
    for officer_id, username in tracked.items():
        row = op.find_officer(username)
        if row and row["id"] == officer_id:
            op.api("admins.delete", {"id": officer_id})


@pytest.fixture
def officer_login(second_browser):
    """Factory: logs ``data`` in to the Officer Console in a separate browser; returns (page, error shown).
    Every page opened is logged out on teardown."""
    browser = {}
    pages = []

    def _login(data: OfficerData):
        if "b" not in browser:
            browser["b"] = second_browser()
        ctx = browser["b"].new_context(viewport={"width": 1280, "height": 800})
        p = ctx.new_page()
        pages.append(p)
        lp = AdminLoginPage(p)
        lp.open()
        error = lp.login_past_captcha(data.username, data.password)
        if not error:
            p.wait_for_load_state("networkidle")
        return p, error

    yield _login
    for p in pages:
        _logout(p)


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def officers_data():
    """OfficersFactory — makes run-unique NEW test officers (district_officer / divisional_officer / commissioner)."""
    return OfficersFactory


@pytest.fixture
def district_officer_data() -> OfficerData:
    return OfficersFactory.district_officer()
