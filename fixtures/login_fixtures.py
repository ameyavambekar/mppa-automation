import os

import pytest

from test_data.login_factory import LoginData, LoginFactory
from utils.agency_builder import fresh_agency


# The three fixtures below need an agency that has not started Form-I (its login lands on Part A). They take
# ``page`` because ``fresh_agency`` registers a new agency on it when the state store has none left.

@pytest.fixture
def valid_login_data(page) -> LoginData:
    return LoginFactory.valid_from_store(fresh_agency(page))


@pytest.fixture
def nonexistent_user_data() -> LoginData:
    return LoginFactory.nonexistent_user()


@pytest.fixture
def invalid_password_data(page) -> LoginData:
    user = fresh_agency(page)
    return LoginFactory.invalid_password(user.username)


@pytest.fixture
def wrong_captcha_data(page) -> LoginData:
    user = fresh_agency(page)
    return LoginFactory.wrong_captcha_credentials(user)


@pytest.fixture
def blank_username_login_data() -> LoginData:
    """KAN-TC-33 — Username blank, password + CAPTCHA filled correctly."""
    return LoginFactory.blank_username()


@pytest.fixture
def blank_password_login_data() -> LoginData:
    """KAN-TC-34 — Username filled, password blank, CAPTCHA filled correctly."""
    return LoginFactory.blank_password()


@pytest.fixture
def blank_captcha_login_data() -> LoginData:
    """KAN-TC-35 — Username + password filled, CAPTCHA blank."""
    return LoginFactory.blank_captcha()


@pytest.fixture
def lockout_test_data() -> LoginData:
    """Uses a dedicated lockout-test account set via LOCKOUT_TEST_USERNAME env var.
    Set LOCKOUT_TEST_USERNAME to a real registered username before running TC-10.
    The account WILL be temporarily locked by this test."""
    username = os.getenv("locked_agency_username")
    if not username:
        pytest.skip(
            "Set LOCKOUT_TEST_USERNAME env var to a dedicated test account before running TC-10."
        )
    return LoginFactory.lockout_attempt(username)
