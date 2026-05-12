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



# =============================================================================
# TC-01 — Valid Username Entry
# =============================================================================

@allure.story("TC-01: Valid Username Entry")
@allure.title("Successful username entry with valid input — no error shown")
def test_tc01_valid_username_accepted(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page,
    When I enter a valid username (min 6 chars, no spaces) and click outside the field,
    Then no inline error is displayed and the field retains the entered value.

    Notion ref: TC-01 | Data: AgencyUser01 (6+ chars, no spaces)
    """
    data = valid_registration_data

    with allure.step("Enter a valid username in the Username field"):
        registration_page.fill_username(data.username)   # blur is called inside

    with allure.step("Assert the field retains the entered value"):
        expect(registration_page.username_input).to_have_value(data.username)

    with allure.step("Assert no error keywords appear in the username helper"):
        expect(registration_page.username_helper).not_to_contain_text("required")
        expect(registration_page.username_helper).not_to_contain_text("must")
        expect(registration_page.username_helper).not_to_contain_text("taken")


# =============================================================================
# TC-02 — Username: Blank Submission
# =============================================================================

@allure.story("TC-02: Username — Blank Submission")
@allure.title("Error shown when Username is left blank on submission")
def test_tc02_blank_username_shows_error(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I leave the Username field blank and click SUBMIT REGISTRATION,
    Then the inline error "Username is required." is displayed.

    Notion ref: TC-02
    """
    with allure.step("Leave the Username field blank (do not type anything)"):
        # fill_username("") still triggers blur; either blur or submit reveals the error
        registration_page.fill_username("")

    with allure.step("Click SUBMIT REGISTRATION to trigger form-level validation"):
        dialog_message = registration_page.submit_and_handle_alert()

    with allure.step("Assert alert error: 'Invalid Username'"):
        assert("Invalid username: 6–30 chars, letters/numbers/underscore only." in dialog_message)


# =============================================================================
# TC-03 — Username: Too Short
# =============================================================================

@allure.story("TC-03: Username — Too Short")
@allure.title("Error shown when Username has fewer than 6 characters")
def test_tc03_short_username_shows_error(registration_page, short_username_data):
    """
    Given I am on the Pre-Registration page,
    When I enter a username with fewer than 6 characters and click outside,
    Then the inline error "Username must be at least 6 characters." is displayed.

    Notion ref: TC-03 | Data: Ag01 (4 chars)
    """
    data = short_username_data

    with allure.step(f"Enter a short username: '{data.username}'"):
        registration_page.fill_username(data.username)

    with allure.step("Assert inline error about minimum character length"):
        expect(registration_page.username_helper).to_contain_text(
            "6–30 chars, letters/numbers/underscore only"
        )

# =============================================================================
# TC-04 — Username: Already Taken
# =============================================================================

@allure.story("TC-04: Username — Already Taken")
@allure.title("Error shown when Username already exists in the system")
def test_tc04_username_already_taken_shows_inline_error(
    registration_page, username_already_taken_data
):
    """
    Given a user with username 'ameyavambekar' is already registered,
    And I am on the Pre-Registration page,
    When I enter 'ExistUser01' in the Username field and click outside,
    Then the inline error "❌ Username taken"
    is displayed (triggered by the async uniqueness-check API call on blur).

    Notion ref: TC-04 | Pre-condition: 'ameyavambekar' exists in the test DB
    """
    data = username_already_taken_data

    with allure.step(f"Enter an already-registered username: '{data.username}'"):
        registration_page.fill_username(data.username)   # blur triggers async check

    with allure.step("Wait for async uniqueness check and assert duplicate error"):
        expect(registration_page.username_helper).to_contain_text(
            "❌ Username taken"
        )


# =============================================================================
# TC-05 — Valid Password Entry with Strength Indicator
# =============================================================================

@allure.story("TC-05: Password Strength Indicator")
@allure.title("Strength indicator updates in real-time as password complexity increases")
def test_tc05_password_strength_indicator_updates(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I type progressively stronger passwords into the Password field,
    Then the strength indicator (#pwdHint) updates from Weak → Medium → Strong
    in real-time, and the Confirm Password field shows 'Passwords match' when
    both fields contain identical valid values.

    Notion ref: TC-06 (AC-1)
    Steps from spec:
      Step 2: 'password'   → Weak
      Step 3: 'password1'  → Fair
      Step 4: 'Password1@' → Strong
      Step 5: matching confirm → 'Passwords match'
    """
    with allure.step("Enter a weak password; assert strength shows 'Weak'"):
        registration_page.fill_password("password")
        expect(registration_page.password_helper).to_contain_text("Weak")

    with allure.step("Extend to include a digit; assert strength updates to 'Medium'"):
        registration_page.fill_password("password1")
        expect(registration_page.password_helper).to_contain_text("Fair")

    with allure.step("Add uppercase and symbol; assert strength shows 'Strong'"):
        registration_page.fill_password("Password1@")
        expect(registration_page.password_helper).to_contain_text("Strong")

    with allure.step("Enter matching Confirm Password; assert 'Passwords match'"):
        registration_page.fill_confirm_password("Password1@")
        expect(registration_page.confirm_password_helper).to_contain_text("Passwords match")



# =============================================================================
# TC-06 — Password: Missing Complexity Rules
# =============================================================================

@allure.story("TC-06: Password — Missing Complexity Rules")
@allure.title("Inline error shown for each violated password complexity rule")
def test_tc06_password_missing_complexity_shows_error(registration_page,password_no_symbol_data,password_no_number_data,password_no_uppercase_data,short_password_data):
    """
    Given I am on the Pre-Registration page,
    When I enter a password that violates one of the four complexity rules
    (no uppercase | no number | no symbol | too short),
    Then the password helper (#pwdHint) displays the specific inline error
    for the violated rule.

    Notion ref: TC-06
    Parametrised over:
      TC-06b — no uppercase  → 'Password must contain at least one uppercase letter.'
      TC-06c — no number     → 'Password must contain at least one number.'
      TC-06d — no symbol     → 'Password must contain at least one special character.'
      TC-06a — too short     → 'Password must be at least 8 characters.'
    """


    no_uppercase = password_no_uppercase_data
    no_symbol = password_no_symbol_data
    no_number = password_no_number_data
    short_password = short_password_data

    with allure.step("Enter a password without uppercase; assert uppercase missing error is displayed"):
        registration_page.fill_password(no_uppercase)
        expect(registration_page.password_uppercase_error).to_be_visible()
        registration_page.clear_password()

    with allure.step("Enter a password without number; assert number error is displayed"):
        registration_page.fill_password(no_number)
        expect(registration_page.password_number_error).to_be_visible()
        registration_page.clear_password()

    with allure.step("Enter a password without symbol; assert special symbol error is displayed"):
        registration_page.fill_password(no_symbol)
        expect(registration_page.password_symbol_error).to_be_visible()
        registration_page.clear_password()

    with allure.step("Enter a short password; assert length error is displayed"):
        registration_page.fill_password(short_password)
        expect(registration_page.password_length_error).to_be_visible()


# =============================================================================
# TC-07 — Confirm Password: Mismatch
# =============================================================================

@allure.story("TC-07: Confirm Password — Mismatch")
@allure.title("Error shown when Confirm Password does not match Password")
def test_tc07_confirm_password_mismatch_shows_error(registration_page, password_mismatch_data):
    """
    Given I am on the Pre-Registration page,
    When I enter a valid password in the Password field,
    And I enter a DIFFERENT value in the Confirm Password field,
    Then the confirm-password helper (#confirmHint) displays
    "Passwords do not match."

    Notion ref: TC-08
    Data: password='Password1@', confirm_password='Password1@DIFF'
    """
    data = password_mismatch_data

    with allure.step(f"Enter a valid password: '{data.password}'"):
        registration_page.fill_password(data.password)
        expect(registration_page.password_helper).to_contain_text("Strong")

    with allure.step(f"Enter a different confirm password: '{data.confirm_password}'"):
        registration_page.fill_confirm_password_and_blur(data.confirm_password)

    with allure.step("Assert mismatch error in confirm-password helper"):
        expect(registration_page.confirm_password_helper).to_contain_text(
            "Passwords do not match"
        )


# =============================================================================
# TC-08 — Password Show / Hide Toggle
# =============================================================================

@allure.story("TC-08: Password Show / Hide Toggle")
@allure.title("Password visibility toggles correctly between masked and plain text")
def test_tc08_password_show_hide_toggle(registration_page, ec5_show_hide_data):
    """
    Given I am on the Pre-Registration page,
    When I enter a password and click the SHOW toggle,
    Then the password input type changes from 'password' to 'text' (plain text visible),
    And clicking the toggle again re-masks it (type returns to 'password').
    The same behaviour applies to the Confirm Password field.

    Notion ref: TC-09 (EC-5)
    Data: password = 'Visible@1234'
    """
    data = ec5_show_hide_data

    # ── Password field ────────────────────────────────────────────────────────

    with allure.step("Step 2 — Enter password; verify it is masked by default"):
        registration_page.fill_password(data.password)
        expect(registration_page.password_input).to_have_attribute("type", "password")

    with allure.step("Step 3 — Click SHOW; verify password renders as plain text"):
        registration_page.toggle_password_visibility()
        expect(registration_page.password_input).to_have_attribute("type", "text")

    with allure.step("Step 4 — Click HIDE; verify password is re-masked"):
        registration_page.toggle_password_visibility()
        expect(registration_page.password_input).to_have_attribute("type", "password")

    # ── Confirm Password field ────────────────────────────────────────────────

    with allure.step("Step 5a — Enter confirm password; verify it is masked by default"):
        registration_page.fill_confirm_password(data.confirm_password)
        expect(registration_page.confirm_password_input).to_have_attribute("type", "password")

    with allure.step("Step 5b — Click SHOW on confirm field; verify plain text"):
        registration_page.toggle_confirm_password_visibility()
        expect(registration_page.confirm_password_input).to_have_attribute("type", "text")

    with allure.step("Step 5c — Click HIDE on confirm field; verify re-masked"):
        registration_page.toggle_confirm_password_visibility()
        expect(registration_page.confirm_password_input).to_have_attribute("type", "password")






# ===========================================================================
# TC-09 — Login Credentials Entry & Password Strength Feedback
# ===========================================================================

@allure.story("TC-09: Login Credentials")
@allure.title("Valid credentials accepted and password strength indicator updates")
def test_tc09_valid_credentials_accepted_and_strength_shown(
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
# TC-10 — OTP Delivery on Email Submit
# ===========================================================================

@allure.story("TC-10: OTP Delivery")
@allure.title("OTP is sent and countdown timer appears after clicking Get OTP")
def test_tc10_otp_sent_on_email_submit(registration_page, valid_registration_data):
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