import os

import pytest

from pages.forgot_password_page import ForgotPasswordPage
from pages.login_page import LoginPage
from pages.reset_password_page import RESET_PASSWORD_URL, ResetPasswordPage
from test_data.forgot_password_factory import ForgotPasswordData, ForgotPasswordFactory
from utils.state_store import TestStateStore


def _agency(index: int, purpose: str):
    """The ``index``-th oldest agency recorded with its e-mail and PAN. The oldest (index 0) is left alone
    for testing by hand."""
    users = TestStateStore().get_agency_users_with_email_and_pan()
    if len(users) <= index:
        pytest.skip(f"Forgot password needs {index + 1} agencies recorded with their e-mail and PAN ({purpose}).")
    return users[index]


# ── Account fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def reset_agency():
    """The agency whose password the reset tests change — every change is recorded in the state store."""
    return _agency(1, "one whose password is reset")


@pytest.fixture
def wrong_details_agency():
    """The agency the wrong-details tests (TC-565, TC-570) try to reset — kept apart from ``reset_agency``
    so a limit on failed attempts cannot block the reset tests."""
    return _agency(2, "one tried with wrong details")


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def forgot_password_page(page) -> ForgotPasswordPage:
    """Forgot password, logged out."""
    page.context.clear_cookies()
    forgot = ForgotPasswordPage(page)
    forgot.open()
    return forgot


@pytest.fixture
def logged_out_login_page(page) -> LoginPage:
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    return login


@pytest.fixture
def verified_reset_page(forgot_password_page, reset_agency) -> ResetPasswordPage:
    """Set a new password, opened by confirming ``reset_agency`` on Forgot password (captcha read by OCR)."""
    forgot_password_page.submit_details(reset_agency.username, reset_agency.email, reset_agency.pan)
    if not forgot_password_page.page.url.startswith(RESET_PASSWORD_URL):
        refusal = " ".join(forgot_password_page.server_error.all_inner_texts()) or "no message"
        pytest.fail(f"Confirming {reset_agency.username} did not open Set a new password ({refusal}).")
    return ResetPasswordPage(forgot_password_page.page)


@pytest.fixture
def network_lockout_allowed():
    """Skips the test unless RUN_NETWORK_LOCKOUT_TESTS=true. Reaching the Forgot password attempt limit
    locks it for everyone on this network for an hour (TC-570), so the test is run only on purpose."""
    if os.getenv("RUN_NETWORK_LOCKOUT_TESTS", "false").lower() != "true":
        pytest.skip("Locks Forgot password for this network for an hour — set RUN_NETWORK_LOCKOUT_TESTS=true to run.")


@pytest.fixture
def clipboard_access(page):
    """Lets the page read and write the clipboard (for pasting) for one test."""
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    yield page
    page.context.clear_permissions()


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def invalid_username_data() -> list[ForgotPasswordData]:
    return ForgotPasswordFactory.invalid_usernames()


@pytest.fixture
def username_typed_with_space_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.username_typed_with_space()


@pytest.fixture
def username_as_email_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.username_as_email()


@pytest.fixture
def valid_username_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.valid_username()


@pytest.fixture
def invalid_email_data() -> list[ForgotPasswordData]:
    return ForgotPasswordFactory.invalid_emails()


@pytest.fixture
def email_typed_with_space_and_capitals_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.email_typed_with_space_and_capitals()


@pytest.fixture
def pan_typed_in_small_letters_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.pan_typed_in_small_letters()


@pytest.fixture
def invalid_pan_data() -> list[ForgotPasswordData]:
    return ForgotPasswordFactory.invalid_pans()


@pytest.fixture
def pan_pasted_too_long_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.pan_pasted_too_long()


@pytest.fixture
def captcha_typed_with_symbols_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.captcha_typed_with_symbols()


@pytest.fixture
def captcha_with_0_and_1_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.captcha_with_0_and_1()


@pytest.fixture
def captcha_too_short_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.captcha_too_short()


@pytest.fixture
def unknown_username_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.unknown_username()


@pytest.fixture
def wrong_captcha_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.wrong_captcha()


@pytest.fixture
def new_password_data() -> ForgotPasswordData:
    return ForgotPasswordFactory.new_password()


@pytest.fixture
def password_checklist_data() -> dict[str, ForgotPasswordData]:
    return ForgotPasswordFactory.password_checklist_steps()


@pytest.fixture
def password_length_data() -> dict[int, ForgotPasswordData]:
    return ForgotPasswordFactory.password_lengths()
