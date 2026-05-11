"""
tests/pre_registration/test_pre_registration.py
================================================
Full test suite for the MPPA Pre-Registration form.

Coverage map
------------
AC-1   test_valid_credentials_accepted_and_strength_shown
AC-2   test_otp_sent_on_email_submit
AC-3   test_email_verified_after_correct_otp
AC-4   test_invalid_pan_shows_inline_error
AC-5   test_full_valid_registration_submits  (parametrised by district)
AC-6   test_registration_id_displayed_and_format_is_correct
AC-7   test_duplicate_pan_blocked

FV     test_field_level_validations  (parametrised with all negative scenarios)

EC-1   test_captcha_refresh_generates_new_value
EC-2   (manual / environment-dependent — OTP resend after expiry)
EC-4   test_pan_lowercase_is_auto_uppercased
EC-5   test_password_show_hide_toggle
EC-6   test_submit_disabled_until_all_sections_valid
EC-8   test_already_registered_login_link_visible
EC-9   test_username_already_taken_shows_inline_error
"""

import re

import allure
import pytest
from playwright.sync_api import expect

from test_data.agency_registration_factory import AgencyRegistrationFactory

# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------
pytestmark = [
    allure.feature("MPPA Pre-Registration"),
    pytest.mark.pre_registration,
]



# ===========================================================================
# AC-1 — Login Credentials Entry & Password Strength Feedback
# ===========================================================================

@allure.story("AC-1: Login Credentials")
@allure.title("Valid credentials accepted and password strength indicator updates")
def test_valid_credentials_accepted_and_strength_shown(
    registration_page, valid_registration_data
):
    """
    Given I am on the pre-registration page,
    When I enter valid username, password, and matching confirm password,
    Then all fields are accepted and a strength indicator is shown.
    """
    data = valid_registration_data

    with allure.step("Fill all three credential fields"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )


    with allure.step("Assert no error on username or password fields"):
        expect(registration_page.password_helper).to_contain_text("Strong")
        expect(registration_page.confirm_password_helper).to_contain_text("Passwords match")
        expect(registration_page.username_helper).to_contain_text("Username available")




# ===========================================================================
# AC-2 — OTP Delivery on Email Submit
# ===========================================================================

@allure.story("AC-2: OTP Delivery")
@allure.title("OTP is sent and countdown timer appears after clicking Get OTP")
def test_otp_sent_on_email_submit(registration_page, valid_registration_data):
    """
    Given I have entered a valid email,
    When I click Get OTP,
    Then the countdown timer is visible and the OTP button becomes disabled.
    """
    data = valid_registration_data

    with allure.step("Fill credentials first"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Enter email and click Get OTP"):
        registration_page.fill_email_and_request_otp(data.email)

    with allure.step("Assert countdown timer is visible"):
        expect(registration_page.otp_countdown_timer).to_be_visible()

    with allure.step("Assert Get OTP button is disabled during countdown"):
        expect(registration_page.otp_button).to_be_disabled()