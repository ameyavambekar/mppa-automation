import os

import pytest

from pages.login_page import LoginPage
from utils.state_store import TestStateStore


def _login_and_wait(page, user):
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url("**/dashboard**", timeout=15000)


@pytest.fixture
def logged_in_agency_page(page):
    """Yields (page, user) logged in as any stored agency user."""
    user = TestStateStore().get_any_agency_user()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    _login_and_wait(page, user)
    yield page, user


@pytest.fixture
def agency_user_with_part_a_page(page):
    """Yields (page, user) where the user has completed step 1 (Part A) of Form-I."""
    user = TestStateStore().get_agency_user_with_steps(["1"])
    if user is None:
        pytest.skip("No agency user with Part A (step 1) completed in state store.")
    _login_and_wait(page, user)
    yield page, user


@pytest.fixture
def fresh_agency_user_page(page):
    """Yields (page, user) for an agency user who has NOT started the 8-step wizard."""
    user = TestStateStore().get_agency_user_with_no_form()
    if user is None:
        pytest.skip("No agency user without form applications found in state store.")
    _login_and_wait(page, user)
    yield page, user

