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


def _status(page) -> str:
    """The welcome block's status badge — "Under review" until the certificate is issued, then "Registered"."""
    return AgencyHomePage(page).status_badge.inner_text().strip()


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
    """Yields (page, user) on Home for an agency whose application is submitted and still under
    review (no certificate yet). Home is read-only apart from "Mark all read", so any such agency
    will do."""
    for user in _submitted_agencies():
        if _login_to_home(page, user) and _status(page) == AgencyHomePage.UNDER_REVIEW:
            yield page, user
            return
    pytest.skip(NO_SUBMITTED_AGENCY)


@pytest.fixture
def registered_agency_home_page(page):
    """Yields (page, user) on Home for an agency whose registration certificate has been issued
    (status "Registered")."""
    for user in _submitted_agencies():
        if _login_to_home(page, user) and _status(page) == AgencyHomePage.REGISTERED:
            yield page, user
            return
    pytest.skip("No submitted agency has been issued a certificate yet — clear Desktop Scrutiny and "
                "Physical Verification for one in the admin portal.")


@pytest.fixture
def refused_agency_home_page(page):
    """Yields (page, user) on Home for an agency whose application has been refused (status "Refused").
    Read-only: any refused agency will do, whatever its appeals stand at."""
    for user in _submitted_agencies():
        if _login_to_home(page, user) and _status(page) == AgencyHomePage.REFUSED:
            yield page, user
            return
    pytest.skip("No submitted agency has been refused — run python -m utils.seed_appeals (irreversible, ask first).")


# First Appeal badge on Home › Appeals for each state the Appeals card test runs in
_FIRST_APPEAL_STATES = {"pending": re.compile(r"^Pending — decision by "),
                        "dismissed": re.compile(rf"^{AgencyHomePage.DISMISSED_BADGE}$")}


@pytest.fixture
def refused_home_with_first_appeal(request, page):
    """Indirectly parametrised with "pending" or "dismissed": yields (page, user, state) on Home for a refused
    agency whose First Appeal is in that state."""
    state = request.param
    home = AgencyHomePage(page)
    for user in _submitted_agencies():
        if not (_login_to_home(page, user) and _status(page) == AgencyHomePage.REFUSED):
            continue
        badge = home.appeal_level_badge(AgencyHomePage.FIRST_APPEAL)
        if badge.count() and _FIRST_APPEAL_STATES[state].match(badge.inner_text().strip()):
            yield page, user, state
            return
    pytest.skip(f"No refused agency has a {state} First Appeal — run python -m utils.seed_appeals "
                "(irreversible, ask first).")


@pytest.fixture
def home_with_unread_notifications(page):
    """Yields (page, user) on Home for an agency still under review with at least one unread
    notification. Every agency gets one when it pays; TC-522 ("Mark all read") uses it up, so the pool
    shrinks by one per run until TC-513 pays for another agency.

    Refused and registered agencies are left out: Home's timeline shows only the six latest events, so
    an agency with a long compliance or appeal history no longer shows "Application submitted" (TC-521)."""
    home = AgencyHomePage(page)
    for user in _submitted_agencies():
        if (_login_to_home(page, user) and _status(page) == AgencyHomePage.UNDER_REVIEW
                and home.unread_notifications.count()):
            yield page, user
            return
    pytest.skip("No agency under review has an unread notification left — run TC-513 to pay for another.")


@pytest.fixture
def home_without_unread_notifications(page):
    """Yields (page, user) on Home for an agency still under review whose notifications are all read.
    When there is none, the first such agency's notifications are marked read first."""
    home = AgencyHomePage(page)
    under_review = []
    for user in _submitted_agencies():
        if not (_login_to_home(page, user) and _status(page) == AgencyHomePage.UNDER_REVIEW):
            continue
        if not home.unread_notifications.count():
            yield page, user
            return
        under_review.append(user)
    if not under_review or not _login_to_home(page, under_review[0]):
        pytest.skip(NO_SUBMITTED_AGENCY)
    home.mark_all_read()
    yield page, under_review[0]


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
