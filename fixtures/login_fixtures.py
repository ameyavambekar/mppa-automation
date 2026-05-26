import os

import pytest

from test_data.login_factory import LoginData, LoginFactory
from utils.state_store import TestStateStore


def _agency_user_or_skip():
    user = TestStateStore().get_agency_user_with_no_form()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    return user


@pytest.fixture
def valid_login_data() -> LoginData:
    return LoginFactory.valid_from_store(_agency_user_or_skip())


@pytest.fixture
def nonexistent_user_data() -> LoginData:
    return LoginFactory.nonexistent_user()


@pytest.fixture
def invalid_password_data() -> LoginData:
    user = _agency_user_or_skip()
    return LoginFactory.invalid_password(user.username)


@pytest.fixture
def wrong_captcha_data() -> LoginData:
    user = _agency_user_or_skip()
    return LoginFactory.wrong_captcha_credentials(user)


@pytest.fixture
def lockout_test_data() -> LoginData:
    """Uses a dedicated lockout-test account set via LOCKOUT_TEST_USERNAME env var.
    Set LOCKOUT_TEST_USERNAME to a real registered username before running TC-10.
    The account WILL be temporarily locked by this test."""
    username = os.getenv("LOCKED_AGENCY_USERNAME")
    if not username:
        pytest.skip(
            "Set LOCKOUT_TEST_USERNAME env var to a dedicated test account before running TC-10."
        )
    return LoginFactory.lockout_attempt(username)
