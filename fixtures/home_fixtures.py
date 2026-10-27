import os

import pytest

from pages.home_page import HomePage
from pages.login_page import LoginPage
from utils.state_store import TestStateStore

HOME_PAGE_REMOVED = (
    "Agency Home page is gone since the portal redesign: auth/home.php returns 404 "
    "and login lands incomplete registrations on the Form-I wizard (no dashboard or "
    "'← Home' link). Rework this test against the new flow."
)


def _login_and_navigate_to_home(page, user):
    """Previously: logged in, waited for the dashboard, clicked ← Home.
    Neither page exists any more, so every test using it is skipped."""
    pytest.skip(HOME_PAGE_REMOVED)


@pytest.fixture
def logged_in_home_page(page):
    """Yields (page, user) for any stored agency user, navigated to the Home page."""
    user = TestStateStore().get_agency_user_with_no_form()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    _login_and_navigate_to_home(page, user)
    yield page, user


@pytest.fixture
def agency_with_part_a_home_page(page):
    """Yields (page, user) for an agency user who has completed Part A (step 1),
    navigated to the Home page."""
    user = TestStateStore().get_agency_user_with_steps(["1"])
    if user is None:
        pytest.skip("No agency user with Part A (step 1) completed in state store.")
    _login_and_navigate_to_home(page, user)
    yield page, user


@pytest.fixture
def fresh_agency_user_home_page(page):
    """Yields (page, user) for an agency user who has NOT started the 8-step wizard,
    navigated to the Home page."""
    user = TestStateStore().get_agency_user_with_no_form()
    if user is None:
        pytest.skip("No agency user without form applications found in state store.")
    _login_and_navigate_to_home(page, user)
    yield page, user


@pytest.fixture
def rejected_agency_user_page(page):
    """Yields (page, user) for a rejected applicant.
    Requires REJECTED_AGENCY_USERNAME and REJECTED_AGENCY_PASSWORD env vars
    pointing to an account whose application was rejected in the portal."""
    username = os.getenv("REJECTED_AGENCY_USERNAME")
    password = os.getenv("REJECTED_AGENCY_PASSWORD")
    if not username or not password:
        pytest.skip(
            "Set REJECTED_AGENCY_USERNAME and REJECTED_AGENCY_PASSWORD env vars "
            "to run TC-20 (rejected applicant flow)."
        )
    pytest.skip(HOME_PAGE_REMOVED)


@pytest.fixture
def agency_user_with_submitted_form(page):
    username = os.getenv("submitted_form_username")
    password = os.getenv("submitted_form_password")
    login = LoginPage(page)
    login.open()
    login.login(username,password)
    yield page