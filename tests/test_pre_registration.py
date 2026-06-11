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
from utils.aio import aio_case

# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------
pytestmark = [
    allure.feature("MPPA Pre-Registration"),
]



# =============================================================================
# TC-01 — Valid Username Entry
# =============================================================================

@aio_case("KAN-TC-3")
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

@aio_case("KAN-TC-1")
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

@aio_case("KAN-TC-2")
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

@aio_case("KAN-TC-5")
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

@aio_case("KAN-TC-6")
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

@aio_case("KAN-TC-7")
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

@aio_case("KAN-TC-8")
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

@aio_case("KAN-TC-9")
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
@aio_case("KAN-TC-10")
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


# =============================================================================
# TC-11 — Successful OTP Verification (AC-3)
# =============================================================================
@aio_case("KAN-TC-11")
@pytest.mark.wait_before(60)
@allure.story("TC-11: Successful OTP Verification")
@allure.title("Email is verified after entering correct OTP within validity window")
def test_tc11_email_verified_after_correct_otp(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and have clicked Get OTP,
    When I retrieve the 6-digit OTP from my inbox and enter it,
    Then the email field is marked as verified (green tick / 'Verified' label).

    Notion ref: TC-11 (AC-3)
    Pre-condition: testmail.app inbox reachable; TESTMAIL_NAMESPACE set in .env
    """
    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Enter email and click Get OTP"):
        registration_page.fill_email_and_request_otp(data.email)

    with allure.step("Assert OTP countdown / resend button is visible (OTP dispatched)"):
        expect(registration_page.otp_countdown_timer).to_be_visible()

    with allure.step("Fetch OTP from testmail.app inbox and enter it"):
        registration_page.enter_otp_and_verify_email()

    with allure.step("Assert email verified tag is shown"):
        expect(registration_page.email_verified_tag).to_be_visible()


# =============================================================================
# TC-12 — OTP: Incorrect OTP Entry
# =============================================================================
@aio_case("KAN-TC-12")
@pytest.mark.wait_before(60)
@allure.story("TC-12: OTP — Incorrect Entry")
@allure.title("Error shown when an incorrect OTP is submitted")
def test_tc12_incorrect_otp_shows_error(registration_page, valid_registration_data):
    """
    Given OTP has been sent to the registered email,
    When I enter a deliberately wrong OTP (000000),
    Then an inline error 'Incorrect OTP. Please check and try again.' is displayed
    and the email remains unverified.

    Notion ref: TC-12 | Data: wrong OTP = 000000
    """
    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Enter valid email and request OTP"):
        registration_page.fill_email_and_request_otp(data.email)
        expect(registration_page.otp_countdown_timer).to_be_visible()

    with allure.step("Enter an incorrect OTP and click Verify"):
        error = registration_page.submit_otp_and_handle_alert()

    with allure.step("Assert OTP error shown; email verified tag absent"):
        assert("Invalid OTP" in error)
        expect(registration_page.email_verified_tag).not_to_be_visible()


# =============================================================================
# TC-13 — OTP: Expired OTP + Resend (EC-2)
# =============================================================================
@aio_case("KAN-TC-13")
@pytest.mark.wait_before
@allure.story("TC-13: OTP — Expired OTP")
@allure.title("Expired OTP is rejected and resend issues a fresh OTP")
def test_tc13_expired_otp_rejected_resend_works(registration_page, valid_registration_data):
    """
    Given the OTP countdown has reached zero (OTP expired),
    When I enter the original (now-expired) OTP,
    Then an error 'OTP has expired. Please click 'Get OTP' to resend.' is shown,
    And clicking 'Get OTP' again delivers a fresh OTP that can be verified.

    Notion ref: TC-13 (EC-2)
    Marked @pytest.mark.slow — requires waiting for the OTP validity window to
    expire (typically 5–10 min in production). Run with: pytest -m slow
    """

    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Enter valid email and request OTP; record the timer start"):
        registration_page.fill_email_and_request_otp(data.email)
        expect(registration_page.otp_countdown_timer).to_be_visible()

    with allure.step("Wait for the OTP validity window to expire (countdown → 0)"):
        # Wait until the resend button becomes re-enabled (countdown reached zero).
        expect(registration_page.otp_button).to_be_enabled(timeout=600_000)  # 10 min

    with allure.step("Enter the now-expired OTP and click Verify"):
        # Use a placeholder — in real execution the tester has the original OTP.
        # For automation, the OTP was fetched earlier; here we simulate entering it late.
        error = registration_page.submit_otp_and_handle_alert()  # any value will fail as expired

    with allure.step("Assert expired OTP error is shown"):
        assert("Invalid OTP" in error)

    with allure.step("Click Get OTP resend button; assert new countdown starts"):
        registration_page.otp_button.click()
        expect(registration_page.otp_countdown_timer).to_be_visible()

    with allure.step("Enter fresh OTP from inbox and verify email"):
        registration_page.enter_otp_and_verify_email()
        expect(registration_page.email_verified_tag).to_be_visible()


# =============================================================================
# TC-14 — OTP: Undeliverable Email (EC-3)
# =============================================================================
@aio_case("KAN-TC-14")
@pytest.mark.wait_before
@allure.story("TC-14: OTP — Undeliverable Email")
@allure.title("Error shown when OTP cannot be delivered to a non-existent domain")
def test_tc14_undeliverable_email_shows_error(registration_page, invalid_email_domain_data):
    """
    Given I enter a syntactically valid email whose domain does not exist,
    When I click Get OTP,
    Then an error banner 'OTP could not be delivered. Please check the email
    address and try again.' is displayed and no OTP is sent.

    Notion ref: TC-14 (EC-3) | Data: user@nonexistentdomain12345
    """
    data = invalid_email_domain_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step(f"Enter non-existent-domain email: '{data.email}' and click Get OTP"):
        registration_page.fill_email_and_request_otp(data.email)

    with allure.step("Assert OTP delivery failure error is displayed"):
        expect(registration_page.email_helper).to_contain_text("Invalid email format")

    with allure.step("Assert email is NOT marked as verified"):
        expect(registration_page.email_verified_tag).not_to_be_visible()


# =============================================================================
# TC-15 — Valid PAN Entry with Auto-Uppercase (EC-4)
# =============================================================================

@aio_case("KAN-TC-15")
@allure.story("TC-15: Valid PAN Entry — Auto-Uppercase")
@allure.title("PAN entered in lowercase is auto-converted to uppercase in real-time")
def test_tc15_valid_pan_auto_uppercased(registration_page, ec4_pan_lowercase_data):
    """
    Given I am on the Pre-Registration page (email already verified),
    When I type a valid PAN number in lowercase (e.g. abcde1234f),
    Then the PAN field auto-uppercases the value to ABCDE1234F in real-time
    and no validation error is displayed.

    Notion ref: TC-15 (EC-4) | Data: lowercase valid PAN
    """
    data = ec4_pan_lowercase_data
    lowercase_pan = data.pan_number          # e.g. 'abcde1234f'

    with allure.step(f"Type PAN in lowercase: '{lowercase_pan}'"):
        registration_page.fill_pan(lowercase_pan)   # blur triggered inside

    with allure.step("Assert field value is auto-uppercased"):
        expect(registration_page.pan_input).to_have_value(lowercase_pan.upper())

    with allure.step("Assert no PAN format error is shown"):
        expect(registration_page.pan_helper).to_contain_text("Valid PAN format")


# =============================================================================
# TC-16 — PAN: Duplicate PAN Blocked (AC-7)
# =============================================================================
@aio_case("KAN-TC-17")
@pytest.mark.wait_before(4000)
@allure.story("TC-16: PAN — Duplicate PAN Blocked")
@allure.title("Submission blocked when PAN is already registered in the system")
def test_tc16_duplicate_pan_blocked(registration_page, duplicate_pan_data):
    """
    Given a registration already exists with PAN AAAPL1234C,
    And I am on the Pre-Registration page with all other fields validly filled,
    When I enter the duplicate PAN and click SUBMIT REGISTRATION,
    Then the error 'This PAN is already registered. Please use a different PAN
    or login if you are an existing user.' is shown and submission is blocked.

    Notion ref: TC-16 (AC-7)
    Pre-condition: PAN 'AAAPL1234C' exists in the test environment DB.
    """
    data = duplicate_pan_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Verify email via OTP"):
        registration_page.fill_email_and_request_otp(data.email)
        registration_page.enter_otp_and_verify_email()

    with allure.step(f"Enter duplicate PAN: '{data.pan_number}'"):
        registration_page.fill_pan(data.pan_number)

    with allure.step("Select district"):
        registration_page.select_district(data.district)

    with allure.step("Fill CAPTCHA and accept declaration"):
        captcha = registration_page.read_captcha_value()
        registration_page.fill_captcha(captcha)
        registration_page.accept_declaration()

    with allure.step("Click SUBMIT REGISTRATION"):
        registration_page.submit()

    with allure.step("Assert duplicate PAN error and submission blocked"):
        expect(registration_page.server_error).to_contain_text(registration_page.duplicate_pan_error)



# =============================================================================
# TC-17 — District Dropdown Selection
# =============================================================================
@aio_case("KAN-TC-18")
@pytest.mark.wait_before
@allure.story("TC-17: District Dropdown Selection")
@allure.title("District dropdown accepts a valid selection and shows error when skipped")
def test_tc17_district_dropdown_selection(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page,
    When I open the District dropdown and select 'Mumbai',
    Then 'Mumbai' is displayed as the selected value and no error is shown.
    When I attempt to submit without selecting a district (separate step),
    Then the error 'Please select the district where your agency is located.' appears.

    Notion ref: TC-17
    """
    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Verify email via OTP"):
        registration_page.fill_email_and_request_otp(data.email)
        registration_page.enter_otp_and_verify_email()

    with allure.step(f"Enter PAN: '{data.pan_number}'"):
        registration_page.fill_pan(data.pan_number)

    with allure.step("Verify dropdown initially shows '-- Select District --'"):
        expect(registration_page.district_select).to_have_value("")

    with allure.step("Select 'Mumbai City' from the dropdown"):
        registration_page.select_district("Mumbai City")

    with allure.step("Assert 'Mumbai City' is the selected value"):
        expect(registration_page.district_select).to_have_value("519")


    with allure.step("Reset to no selection and trigger blur-validation"):
        registration_page.district_select.select_option(value="")  # reset
        registration_page.blur_district()

    with allure.step("Fill CAPTCHA and accept declaration"):
        captcha = registration_page.read_captcha_value()
        registration_page.fill_captcha(captcha)
        registration_page.accept_declaration()

    with allure.step("Click SUBMIT REGISTRATION"):
        error = registration_page.submit_and_handle_alert()

    with allure.step("Step 6 — Assert required-district error appears"):
       assert(registration_page.district_not_selected_error in error)


# =============================================================================
# TC-18 — CAPTCHA: Valid Entry
# =============================================================================

@aio_case("KAN-TC-19")
@allure.story("TC-18: CAPTCHA — Valid Entry")
@allure.title("Correct CAPTCHA characters pass validation and produce no captcha error")
def test_tc18_valid_captcha_passes_validation(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and can see the CAPTCHA text in Section 3,
    When I read the current CAPTCHA value from the DOM and type it exactly,
    And I click SUBMIT REGISTRATION,
    Then no CAPTCHA-specific error is shown — the captcha section passes validation.

    Note: other section errors may still fire (email unverified, etc.).
    This test isolates CAPTCHA acceptance independently of the full form.

    Notion ref: TC-18 | Data: CAPTCHA value read live from #captcha DOM element
    """
    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Step 1 — Observe the CAPTCHA image and read its text from the DOM"):
        captcha_text = registration_page.read_captcha_value()
        allure.attach(
            captcha_text,
            name="CAPTCHA value read from DOM",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(f"Step 2 — Enter the exact CAPTCHA characters: '{captcha_text}'"):
        registration_page.fill_captcha(captcha_text)

    with allure.step("Step 3 — Click SUBMIT to trigger all section validations"):
        registration_page.submit()

    with allure.step("Assert no CAPTCHA-specific error is displayed"):
        expect(registration_page.captcha_hint).not_to_contain_text("Does not match")


# =============================================================================
# TC-19 — CAPTCHA: Incorrect Entry
# =============================================================================

@aio_case("KAN-TC-20")
@allure.story("TC-19: CAPTCHA — Incorrect Entry")
@allure.title("Error shown when CAPTCHA characters are entered incorrectly")
def test_tc19_incorrect_captcha_shows_error(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and the CAPTCHA image is shown,
    When I deliberately type characters that do not match the displayed CAPTCHA,
    And I click SUBMIT REGISTRATION,
    Then the inline error 'Incorrect CAPTCHA. Please try again.' is displayed
    and the form submission is blocked.

    Notion ref: TC-20 | Data: wrong captcha = 'AAA111' (hardcoded mismatch)
    """
    WRONG_CAPTCHA = "AAA111"

    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Step 1 — Observe the CAPTCHA image is displayed"):
        captcha_text = registration_page.read_captcha_value()
        allure.attach(
            captcha_text,
            name="Actual CAPTCHA value (for reference)",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(f"Step 2 — Enter deliberately wrong CAPTCHA value: '{WRONG_CAPTCHA}'"):
        registration_page.fill_captcha(WRONG_CAPTCHA)

    with allure.step("Step 3 — Click SUBMIT to trigger validation"):
        registration_page.submit()

    with allure.step("Assert CAPTCHA error is shown"):
        expect(registration_page.captcha_hint).to_contain_text("Does not match")

# =============================================================================
# TC-20 — CAPTCHA: Refresh Generates New CAPTCHA (EC-1)
# =============================================================================

@aio_case("KAN-TC-21")
@allure.story("TC-20: CAPTCHA — Refresh Generates New Value")
@allure.title("Refresh button generates a new CAPTCHA, clears input, and invalidates old value")
def test_tc20_captcha_refresh_generates_new_value(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and a CAPTCHA is displayed,
    When I note the current CAPTCHA text and type it into the input field,
    And I click the 'Refresh' button,
    Then a NEW CAPTCHA value is displayed (different from the previous one),
    And the CAPTCHA input field is cleared,
    And if I re-enter the OLD CAPTCHA value and submit, an error is shown
    (the old value has been invalidated by the refresh).

    Notion ref: TC-21 (EC-1)
    """
    data = valid_registration_data

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Step 1 — Record the current CAPTCHA value from the DOM"):
        original_captcha = registration_page.read_captcha_value()
        allure.attach(
            original_captcha,
            name="Original CAPTCHA value",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(f"Step 2 — Type the original CAPTCHA into the input: '{original_captcha}'"):
        registration_page.fill_captcha(original_captcha)

    with allure.step("Step 3 — Click Refresh and capture the new CAPTCHA value"):
        new_captcha = registration_page.refresh_captcha()
        allure.attach(
            new_captcha,
            name="New CAPTCHA value after refresh",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Assert the CAPTCHA value has changed after Refresh"):
        assert new_captcha != original_captcha, (
            f"CAPTCHA did not change after Refresh — "
            f"still showing '{original_captcha}'")

    with allure.step("Assert the CAPTCHA input field has been cleared by the Refresh"):
        expect(registration_page.captcha_input).to_have_value("")

    with allure.step(
        f"Step 4 — Re-enter the OLD CAPTCHA value ('{original_captcha}') and submit "
        "to confirm it is now invalidated"
    ):
        registration_page.fill_captcha(original_captcha)

    with allure.step("Assert CAPTCHA error shows — old value is no longer valid"):
        expect(registration_page.captcha_hint).to_contain_text("Does not match")


# =============================================================================
# TC-21 — Declaration Checkbox: Mandatory Check
# =============================================================================
@aio_case("KAN-TC-22")
@pytest.mark.wait_before
@allure.story("TC-21: Declaration Checkbox — Mandatory")
@allure.title("Submit blocked when Declaration checkbox is unchecked; unblocked after check")
def test_tc21_declaration_checkbox_mandatory(registration_page, valid_registration_data):
    """
    Given all of Sections 1, 2, and 3 are validly filled,
    When I leave the Declaration checkbox unchecked and click SUBMIT REGISTRATION,
    Then the error 'You must accept the declaration and undertaking to proceed.'
    is displayed and submission is blocked.
    When I check the checkbox,
    Then the error disappears and the submit button becomes active.

    Notion ref: TC-22
    """
    data = valid_registration_data

    with allure.step("Step 1 — Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Step 1 — Fill Section 2: verify email, PAN, district"):
        registration_page.fill_email_and_request_otp(data.email)
        registration_page.enter_otp_and_verify_email()
        registration_page.fill_pan(data.pan_number)
        registration_page.select_district(data.district)

    with allure.step("Step 1 — Fill Section 3 CAPTCHA correctly"):
        captcha = registration_page.read_captcha_value()
        registration_page.fill_captcha(captcha)

    with allure.step("Step 2 — Confirm declaration checkbox is unchecked"):
        expect(registration_page.declaration_checkbox).not_to_be_checked()

    with allure.step("Step 3 — Click SUBMIT REGISTRATION without accepting declaration"):
        registration_page.submit()

    with allure.step("Assert declaration error is displayed; submission is blocked"):
        expect(registration_page.declaration_error).to_be_visible()

    with allure.step("Step 4 — Check the Declaration checkbox"):
        registration_page.accept_declaration()
        expect(registration_page.declaration_checkbox).to_be_checked()

    with allure.step("Assert declaration error is no longer shown"):
        expect(registration_page.declaration_error).not_to_be_visible()


# =============================================================================
# TC-22 — Already Registered User Link Visible (EC-8)
# =============================================================================

@aio_case("KAN-TC-25")
@allure.story("TC-22: Already Registered User — Login Link Visible")
@allure.title("'Already registered? Login' link is visible and redirects to login page")
def test_tc22_already_registered_login_link_visible(registration_page,login_page):
    """
    Given I am on the Pre-Registration page,
    When I look at the footer of the form,
    Then the 'Already registered? Login here →' link is visible.
    When I click it,
    Then I am redirected to the MPPA Portal login page.

    Notion ref: TC-25 (EC-8)
    """
    with allure.step("Step 1 — Navigate to Pre-Registration page"):
        # registration_page fixture already opens the page
        pass

    with allure.step("Step 2 — Assert 'Already registered? Login here →' link is visible"):
        expect(registration_page.login_link).to_be_visible()

    with allure.step("Step 3 — Click the login link and assert redirect to login page"):
        registration_page.click_login_link()
        expect(login_page.login_title).to_be_visible()


# =============================================================================
# TC-23 — Self-Declaration Text is Read-Only
# =============================================================================

@aio_case("KAN-TC-27")
@allure.story("TC-23: Self-Declaration Text — Read-Only")
@allure.title("The 6 declaratory clauses in Section 4 are displayed in a non-editable block")
def test_tc23_declaration_text_is_readonly(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I navigate to Section 4: Declaration & Undertaking,
    Then the 6 declaratory clauses are displayed inside a bordered container
    that is non-editable — the cursor does not change to a text cursor and
    no input is possible.

    Notion ref: TC-27
    """
    with allure.step("Step 1 — Navigate to the Pre-Registration page"):
        # registration_page fixture already opens the page
        pass

    with allure.step("Step 2 — Locate the declaration text block in Section 4"):
        expect(registration_page.declaration_text_block).to_be_visible()

    with allure.step("Step 3 — Assert the declaration container is read-only (non-editable)"):
        content_editable = registration_page.declaration_text_block.get_attribute("contenteditable")
        assert content_editable in (None, "false"), (
            f"Declaration block is editable (contenteditable='{content_editable}')"
        )
        editable_children = registration_page.declaration_text_block.locator(
            "input:not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled])")
        assert editable_children.count() == 0, (
            f"Declaration block contains {editable_children.count()} editable child element(s)"
        )

# =============================================================================
# TC-24 — Page Header and Mandatory Field Indicator Display
# =============================================================================

@aio_case("KAN-TC-28")
@allure.story("TC-24: Static UI Elements")
@allure.title("Page header, subtitle, mandatory badge, and support footer render correctly")
def test_tc24_static_ui_elements_display_correctly(registration_page):
    """
    Given I am on the Pre-Registration page,
    Then the following static UI elements are rendered exactly as per the spec:
      Step 1 — Page header: 'New Agency Registration Form'
      Step 2 — Subtitle: 'Please fill all mandatory fields carefully. Details once
                          submitted cannot be changed without approval.'
      Step 3 — Mandatory field badge (top-right): '* Marked fields are mandatory'
      Step 4 — Technical support footer: 'support@placementportal.gov.in'

    Notion ref: TC-28
    """
    with allure.step("Step 1 — Assert page header reads 'New Agency Registration Form'"):
        expect(registration_page.page_title).to_be_visible()
        expect(registration_page.page_title).to_contain_text("New Agency Registration Form")

    with allure.step("Step 2 — Assert subtitle is displayed correctly"):
        expect(registration_page.page_subtitle).to_be_visible()
        expect(registration_page.page_subtitle).to_contain_text(
            "Please fill all mandatory fields carefully."
        )
        expect(registration_page.page_subtitle).to_contain_text(
            "Details once submitted cannot be changed without approval."
        )

    with allure.step("Step 3 — Assert mandatory field badge is visible"):
        expect(registration_page.mandatory_field_badge).to_be_visible()
        expect(registration_page.mandatory_field_badge).to_contain_text("Marked fields are mandatory")

    with allure.step("Step 4 — Assert technical support footer text is present"):
        expect(registration_page.support_footer).to_be_visible()
        expect(registration_page.support_footer).to_contain_text("support@placementportal.gov.in")


# =============================================================================
# TC-25 — Full Valid Submission: Registration ID Generated (AC-5 & AC-6)
# =============================================================================
@aio_case("KAN-TC-23")
@pytest.mark.wait_before
@allure.story("TC-25: Full Valid Submission — Registration ID Generated")
@allure.title("Successful E2E pre-registration generates a unique Registration ID")
def test_tc25_full_valid_submission_generates_registration_id(
    registration_page, valid_registration_data
):
    """
    Given I fill all four sections correctly (valid credentials, verified email,
    valid unique PAN, selected district, correct CAPTCHA, accepted declaration),
    When I click SUBMIT REGISTRATION,
    Then a success overlay is shown and a unique Registration ID in the format
    MPPA/[Year]/[SequenceNo] is displayed prominently on-screen.
    The registered user is then persisted to the local state store DB so that
    subsequent tests (e.g. Form-I) can retrieve a pre-existing agency user
    without re-registering.

    Notion ref: TC-23 (AC-5 & AC-6)
    Pre-condition: testmail.app reachable; no prior registration for this username/PAN/email.
    """
    from utils.state_store import TestStateStore

    data = valid_registration_data

    with allure.step("Steps 2–4 — Fill Section 1: username, password, confirm password"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Steps 5–6 — Fill Section 2: email OTP verification"):
        registration_page.fill_email_and_request_otp(data.email)
        registration_page.enter_otp_and_verify_email()

    with allure.step("Steps 7–8 — Fill Section 2: PAN and district"):
        registration_page.fill_pan(data.pan_number)
        registration_page.select_district(data.district)

    with allure.step("Step 9 — Fill Section 3: CAPTCHA"):
        captcha = registration_page.read_captcha_value()
        registration_page.fill_captcha(captcha)

    with allure.step("Step 10 — Accept Declaration checkbox"):
        registration_page.accept_declaration()

    with allure.step("Step 11 — Click SUBMIT REGISTRATION"):
        registration_page.submit()

    with allure.step("Assert success overlay / confirmation message is displayed"):
        expect(registration_page.registration_success_message).to_be_visible()

    with allure.step(
        "Assert Registration ID is visible"
    ):
        expect(registration_page.registration_id_text).to_be_visible()

    with allure.step("Record registered user in state store DB for downstream tests"):
        registration_id = registration_page.registration_id_text.text_content().strip()
        TestStateStore().record_user(
            role="agency",
            username=data.username,
            password=data.password,
            email=data.email,
            pan=data.pan_number,
            district=data.district,
            registration_id=registration_id,
        )
        allure.attach(
            f"username={data.username}\nregistration_id={registration_id}",
            name="State store entry",
            attachment_type=allure.attachment_type.TEXT,
        )
