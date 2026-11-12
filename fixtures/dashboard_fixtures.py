import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from utils.agency_builder import fresh_agency
from utils.state_store import TestStateStore


def _login_and_wait(page, user):
    """Logs in and waits for the Form-I wizard, where login now lands for
    incomplete registrations (Part A for users who haven't started it)."""
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)


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
    user = TestStateStore().get_agency_user_with_steps(["part_a"])
    if user is None:
        pytest.skip("No agency user with Part A (step 1) completed in state store.")
    _login_and_wait(page, user)
    yield page, user


@pytest.fixture
def fresh_agency_user_page(page):
    """Yields (page, user) for an agency user who has NOT started the 8-step wizard. When the state
    store has none left, a new agency is registered."""
    user = fresh_agency(page)
    _login_and_wait(page, user)
    yield page, user
