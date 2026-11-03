import os
import re

import pytest

from config import ADMIN_LOGOUT_URL, FORMS_BASE
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.notifications_page import AdminNotificationsPage
from pages.declaration_page import PREVIEW_URL
from pages.login_page import LoginPage
from pages.payment_success_page import PaymentSuccessPage
from pages.preview_page import PreviewPage
from test_data.notifications_factory import NotificationsData, NotificationsFactory
from utils.agency_builder import AgencyBuilder, available
from utils.state_store import TestStateStore, UserRecord

ON_PREVIEW = re.compile(rf"{re.escape(PREVIEW_URL)}")


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


def _admin_login(page, username: str, password: str) -> None:
    """Logs in to the Officer Console (retrying a misread Security Code) and waits for the dashboard:
    login.php moves there by script 0.7 s after "Login Successful!", which would otherwise abort the
    caller's next ``goto`` (net::ERR_ABORTED)."""
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(username, password)
    if error:
        pytest.fail(f"Admin login as {username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)


def _admin_logout(page) -> None:
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


def _pay(page, user: UserRecord) -> bool:
    """Logs in as the agency and pays from Preview. False when Preview is not offered (already paid)."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    preview = PreviewPage(page)
    preview.open()
    page.wait_for_load_state("networkidle")
    store = TestStateStore()
    if not ON_PREVIEW.match(page.url):
        store.mark_form_step_status(username=user.username, step="payment", status="completed")
        return False
    preview.confirm_and_pay()
    store.mark_form_step_status(username=user.username, step="payment", status="completed")
    application_id = PaymentSuccessPage(page).application_id.inner_text().strip()
    store.record_application_id(username=user.username, application_id=application_id)
    return True


def submit_application(page) -> UserRecord:
    """Pays for an agency whose Declaration step is complete, which submits its application and raises a
    "New application" notification for the officers. Uses an unpaid agency from the state store, or builds
    one (see ``utils.agency_builder``). Leaves the browser logged out; returns the agency, with its
    Application ID."""
    store = TestStateStore()
    for user in available("declaration", store=store):
        if _pay(page, user):
            break
    else:
        user = AgencyBuilder(page, store).build("declaration")
        assert _pay(page, user), f"Preview was not offered to the newly built agency {user.username}"
    page.context.clear_cookies()
    return store.get_user_by_username(user.username)


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_notifications_page(page) -> AdminNotificationsPage:
    return AdminNotificationsPage(page)


@pytest.fixture
def logged_in_admin_notifications_page(page) -> AdminNotificationsPage:
    """Logs in as the Super Admin and opens Notifications. Logs out on teardown (the browser context is
    shared across the session)."""
    admin = _super_admin_or_skip()
    _admin_login(page, admin.username, admin.password)
    notifications = AdminNotificationsPage(page)
    notifications.open()
    yield notifications
    _admin_logout(page)


@pytest.fixture
def notifications_page_with_unread(page) -> AdminNotificationsPage:
    """Notifications as the Super Admin with at least one unread notification. Reading notifications uses
    them up, so when none is unread an application is submitted first (``submit_application``), which
    raises a "New application" notification."""
    admin = _super_admin_or_skip()
    _admin_login(page, admin.username, admin.password)
    notifications = AdminNotificationsPage(page)
    notifications.open()
    if notifications.unread_count() == 0:
        _admin_logout(page)
        submit_application(page)
        _admin_login(page, admin.username, admin.password)
        notifications.open()
    yield notifications
    _admin_logout(page)


@pytest.fixture
def notifications_after_submission(page):
    """Submits an application (pays for an agency), then logs in as the Super Admin and opens Notifications.
    Yields (notifications page, agency)."""
    admin = _super_admin_or_skip()
    agency = submit_application(page)
    _admin_login(page, admin.username, admin.password)
    notifications = AdminNotificationsPage(page)
    notifications.open()
    yield notifications, agency
    _admin_logout(page)


@pytest.fixture
def district_officer_login(page):
    """Returns a function that logs in as the District Officer from ADMIN_DISTRICT_USERNAME /
    ADMIN_DISTRICT_PASSWORD (district: ADMIN_DISTRICT_NAME). Skips when they are not set — dev has no
    District Officer the tests can sign in as. Logs out on teardown."""
    username = os.getenv("ADMIN_DISTRICT_USERNAME")
    password = os.getenv("ADMIN_DISTRICT_PASSWORD")
    if not (username and password and os.getenv("ADMIN_DISTRICT_NAME")):
        pytest.skip("Set ADMIN_DISTRICT_USERNAME / ADMIN_DISTRICT_PASSWORD / ADMIN_DISTRICT_NAME to a District Officer.")
    yield lambda: _admin_login(page, username, password)
    _admin_logout(page)


@pytest.fixture
def super_admin_login(page):
    """Returns a function that logs in as the Super Admin. Logs out on teardown."""
    admin = _super_admin_or_skip()
    yield lambda: _admin_login(page, admin.username, admin.password)
    _admin_logout(page)


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def state_wide_notifications_data() -> NotificationsData:
    return NotificationsFactory.state_wide()


@pytest.fixture
def unknown_filter_data() -> NotificationsData:
    return NotificationsFactory.unknown_filter()


@pytest.fixture
def district_officer_notifications_data() -> NotificationsData:
    return NotificationsFactory.district_officer(os.getenv("ADMIN_DISTRICT_NAME", ""))
