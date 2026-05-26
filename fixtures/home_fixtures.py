import os

import pytest

from pages.dashboard_page import DashboardPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from utils.state_store import TestStateStore


def _login_and_navigate_to_home(page, user):
    """Logs in, waits for the application dashboard, then clicks ← Home."""
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url("**/dashboard**", timeout=15000)
    DashboardPage(page).home_link.click()
    page.wait_for_url("**/home**", timeout=15000)


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
    login = LoginPage(page)
    login.open()
    login.login(username, password)
    page.wait_for_url("**/home**", timeout=15000)
