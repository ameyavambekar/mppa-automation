import re

import pytest

from pages.agency_home_page import AGENCY_HOME_URL, AgencyHomePage
from pages.login_page import LoginPage
from utils.state_store import TestStateStore

NO_SUBMITTED_AGENCY = ("No agency with a submitted (paid) application lands on Home — run TC-513 "
                       "(tests/test_preview.py), which pays for one.")


def _login(page, user) -> None:
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_load_state("networkidle")


def _submitted_agencies():
    """Agencies recorded as paid (TC-513, or paid by hand and recorded), oldest first."""
    return TestStateStore().get_agency_users_with_steps(["payment"])


def _login_to_home(page, user) -> bool:
    """Logs in as ``user``; True when login lands on Home (with the dev testing notice dismissed).
    Records the agency's Application ID from the top bar if the state store has none yet."""
    _login(page, user)
    if not page.url.startswith(AGENCY_HOME_URL):
        return False
    home = AgencyHomePage(page)
    home.dismiss_testing_notice()
    if not user.application_id:
        _record_application_id(home, user)
    return True


def _record_application_id(home: AgencyHomePage, user) -> None:
    """Agencies paid before Application IDs were stored: take it from '<username> (<Application ID>)'."""
    match = re.search(r"\((\d{13})\)", home.user_text.inner_text())
    if match:
        TestStateStore().record_application_id(username=user.username, application_id=match.group(1))


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def agency_home(page) -> AgencyHomePage:
    return AgencyHomePage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def submitted_agency(page):
    """Yields (page, user) on the Agency Login page for an agency whose application is submitted."""
    users = _submitted_agencies()
    if not users:
        pytest.skip(NO_SUBMITTED_AGENCY)
    LoginPage(page).open()
    yield page, users[0]


@pytest.fixture
def logged_in_agency_home_page(page):
    """Yields (page, user) on Home for an agency whose application is submitted. Home is
    read-only apart from "Mark all read", so any paid agency will do."""
    for user in _submitted_agencies():
        if _login_to_home(page, user):
            yield page, user
            return
    pytest.skip(NO_SUBMITTED_AGENCY)


@pytest.fixture
def home_with_unread_notifications(page):
    """Yields (page, user) on Home for a submitted agency with at least one unread notification.
    Every agency gets one when it pays; TC-522 ("Mark all read") uses it up, so the pool shrinks by
    one per run until TC-513 pays for another agency."""
    home = AgencyHomePage(page)
    for user in _submitted_agencies():
        if _login_to_home(page, user) and home.unread_notifications.count():
            yield page, user
            return
    pytest.skip("No submitted agency has an unread notification left — run TC-513 to pay for another.")


@pytest.fixture
def home_without_unread_notifications(page):
    """Yields (page, user) on Home for a submitted agency whose notifications are all read. When there
    is none, the first submitted agency's notifications are marked read first."""
    home = AgencyHomePage(page)
    users = _submitted_agencies()
    for user in users:
        if _login_to_home(page, user) and not home.unread_notifications.count():
            yield page, user
            return
    if not users or not _login_to_home(page, users[0]):
        pytest.skip(NO_SUBMITTED_AGENCY)
    home.mark_all_read()
    yield page, users[0]


@pytest.fixture
def unpaid_agency(page):
    """Yields (page, user) on the Agency Login page for an agency whose Declaration step is complete
    but which has not paid. Only logs in, so the agency is not used up."""
    store = TestStateStore()
    steps = ["part_a", "part_b", "part_c", "part_f", "enclosures", "premises", "declaration"]
    users = [u for u in store.get_agency_users_with_steps(steps)
             if u.steps.get("payment") not in ("in_progress", "completed")]
    if not users:
        pytest.skip("No unpaid agency with the Declaration step complete — run the Preview tests, "
                    "whose fixture builds one.")
    page.context.clear_cookies()
    LoginPage(page).open()
    yield page, users[0]
