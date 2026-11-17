"""
tests/pre_registration/test_pre_registration.py
================================================
Full test suite for the MPPA Pre-Registration form.

Form layout (register.php)
--------------------------
1 Agency & Login Credentials · 2 Contact & Identity Verification ·
3 Document Upload · 4 Captcha Verification · 5 Declaration & Undertaking

Coverage map
------------
TC-01 … TC-04   Username (valid / blank / short / taken — EC-9)
TC-05 … TC-09   Password strength + rule checklist, mismatch, show/hide (EC-5), AC-1
TC-10 … TC-14   Email OTP (AC-2, AC-3, EC-2, EC-3) — need EMAIL_OTP_ENABLED on the server
TC-15 … TC-17   PAN auto-uppercase (EC-4), duplicate PAN (AC-7), district dropdown
TC-18 … TC-20   CAPTCHA valid / incorrect / refresh (EC-1)
TC-21 … TC-24   Declaration mandatory, 'Login & Continue' link (EC-8), read-only clauses, static UI
TC-25           Full valid submission → 'Registration Started!' overlay (AC-5, AC-6)
TC-26 … TC-28   Agency Name, Mobile, Alternate Phone field rules           (AIO KAN-TC-416 … 418)
TC-29 … TC-32   Document upload: valid / oversized / wrong type / missing   (AIO KAN-TC-419 … 422)
TC-33 … TC-35   User Manual gate, District "Other" → City, Confirm Password paste block (AIO KAN-TC-423 … 425)
"""

import json
import os
import re

import allure
import pytest
from playwright.sync_api import expect

from test_data.agency_registration_factory import AgencyRegistrationFactory
from utils.aio import aio_case
from utils.file_manager import INVALID_FORMAT, OVERSIZED_FILE, VALID_JPG, VALID_PDF

try:
    from utils.file_manager import get_document_path
    OVERSIZED_IMAGE = get_document_path("oversized_image.jpg")   # > 5 MB JPG
except FileNotFoundError:
    OVERSIZED_IMAGE = None

# ---------------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------------
pytestmark = [
    allure.feature("MPPA Pre-Registration"),
]

RULE_OK = re.compile(r"\bok\b")   # class added to a #pwRules item once satisfied


def _fill_credentials_and_contact(registration_page, data):
    """
    Fills Section 1 and Section 2 up to (and including) PAN.

    Email / mobile OTP are feature-flagged on the page and currently off; the
    verified flags are forced so these submit-path tests stay independent of
    the OTP flow when it is switched back on (OTP is covered by TC-10 … TC-14).
    """
    registration_page.fill_agency_name(getattr(data, "agency_name", "Test Agency"))
    registration_page.fill_credentials(data.username, data.password, data.confirm_password)
    registration_page.fill_email(data.email)
    registration_page.page.evaluate("() => { emailVerified = true; mobileVerified = true; }")
    registration_page.fill_mobile(getattr(data, "mobile", "9876543210"))
    registration_page.fill_alt_phone(getattr(data, "alt_phone", "02224567890"))
    registration_page.fill_pan(data.pan_number)



# =============================================================================
# TC-01 — Valid Username Entry
# =============================================================================

@aio_case("KAN-TC-3")
@allure.story("TC-01: Valid Username Entry")
@allure.title("Successful username entry with valid input — no error shown")
def test_tc01_valid_username_accepted(registration_page, valid_registration_data):
    """
    Given I am on the Registration User Manual page,
    When I scroll the manual, accept the declaration, and proceed to registration,
    And I enter a valid username (min 6 chars, no spaces) and click outside the field,
    Then no inline error is displayed and the field retains the entered value.

    Notion ref: TC-01 | Data: AgencyUser01 (6+ chars, no spaces)
    """
    data = valid_registration_data

    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

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
    Then the inline error "6–30 characters; letters, numbers, and underscores only" is displayed.

    Notion ref: TC-02
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Leave the Username field blank (do not type anything)"):
        registration_page.fill_username("")
        registration_page.submit_button.click()

    with allure.step("Click SUBMIT REGISTRATION to trigger form-level validation"):
        expect(registration_page.username_helper).to_contain_text(
            "6–30 characters; letters, numbers, and underscores only"
        )

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
    Then the inline error "6–30 characters; letters, numbers, and underscores only" is displayed.

    Notion ref: TC-03 | Data: Ag01 (4 chars)
    """
    data = short_username_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step(f"Enter a short username: '{data.username}'"):
        registration_page.fill_username(data.username)

    with allure.step("Assert inline error about minimum character length"):
        expect(registration_page.username_helper).to_contain_text(
            "6–30 characters; letters, numbers, and underscores only"
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
    Given a user is already registered in the system,
    And I am on the Pre-Registration page,
    When I enter an already registered username in the Username field,
    Then the inline error "Username taken"
    is displayed (triggered by the async uniqueness-check API call).

    Notion ref: TC-04
    """
    data = username_already_taken_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    # Route check_username API response to return taken=True
    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": true}'
        ) if "check_username" in (request.post_data or "")
        else route.continue_()
    )

    try:
        with allure.step(f"Enter an already-registered username: '{data.username}'"):
            registration_page.fill_username(data.username)

        with allure.step("Wait for async uniqueness check and assert duplicate error"):
            expect(registration_page.username_helper).to_contain_text("Username taken")
    finally:
        registration_page.page.unroute("**/register_process.php*")


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
    Then the strength indicator (#pwdHint) updates from Weak → Fair → Strong
    in real-time, the rule checklist (#pwRules) ticks off each satisfied rule,
    and the Confirm Password field shows 'Passwords match' when both fields
    contain identical valid values.

    Notion ref: TC-06 (AC-1)
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Assert the password rule checklist lists all six rules"):
        expect(registration_page.password_rules_list.locator("li")).to_have_count(6)

    with allure.step("Enter a weak password; assert strength shows 'Weak'"):
        registration_page.fill_password("password")
        expect(registration_page.password_helper).to_contain_text("Weak")
        expect(registration_page.password_rule("up")).not_to_have_class(RULE_OK)

    with allure.step("Extend to include a digit; assert strength updates to 'Fair'"):
        registration_page.fill_password("password1")
        expect(registration_page.password_helper).to_contain_text("Fair")
        expect(registration_page.password_rule("num")).to_have_class(RULE_OK)

    with allure.step("Add uppercase and symbol; assert strength shows 'Strong' and every rule is met"):
        registration_page.fill_password("Password1@")
        expect(registration_page.password_helper).to_contain_text("Strong")
        for rule in ("len", "up", "low", "num", "sym", "sp"):
            expect(registration_page.password_rule(rule)).to_have_class(RULE_OK)

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
    When I enter a password that violates complexity rules
    (no uppercase | no number | no symbol | too short | spaces),
    Then the password helper (#pwdHint) fails to reach Strong
    and the matching rule in the checklist (#pwRules) stays unticked.
    """
    no_uppercase = password_no_uppercase_data
    no_symbol = password_no_symbol_data
    no_number = password_no_number_data
    short_password = short_password_data

    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Enter password with spaces; assert space error and 'no spaces' rule unmet"):
        registration_page.fill_password("Pass word1@")
        expect(registration_page.password_helper).to_contain_text("No spaces allowed")
        expect(registration_page.password_rule("sp")).not_to_have_class(RULE_OK)
        registration_page.clear_password()

    with allure.step("Enter a password without uppercase; assert not Strong and uppercase rule unmet"):
        registration_page.fill_password(no_uppercase)
        expect(registration_page.password_helper).not_to_contain_text("Strong")
        expect(registration_page.password_uppercase_error).not_to_have_class(RULE_OK)
        registration_page.clear_password()

    with allure.step("Enter a password without number; assert not Strong and number rule unmet"):
        registration_page.fill_password(no_number)
        expect(registration_page.password_helper).not_to_contain_text("Strong")
        expect(registration_page.password_number_error).not_to_have_class(RULE_OK)
        registration_page.clear_password()

    with allure.step("Enter a password without symbol; assert not Strong and symbol rule unmet"):
        registration_page.fill_password(no_symbol)
        expect(registration_page.password_helper).not_to_contain_text("Strong")
        expect(registration_page.password_symbol_error).not_to_have_class(RULE_OK)
        registration_page.clear_password()

    with allure.step("Enter a short password; assert not Strong and length rule unmet"):
        registration_page.fill_password(short_password)
        expect(registration_page.password_helper).not_to_contain_text("Strong")
        expect(registration_page.password_length_error).not_to_have_class(RULE_OK)


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
    "✗ Passwords do not match".

    Notion ref: TC-08
    """
    data = password_mismatch_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

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

    Notion ref: TC-09 (EC-5)
    """
    data = ec5_show_hide_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Step 2 — Enter password; verify it is masked by default"):
        registration_page.fill_password(data.password)
        expect(registration_page.password_input).to_have_attribute("type", "password")

    with allure.step("Step 3 — Click SHOW; verify password renders as plain text"):
        registration_page.toggle_password_visibility()
        expect(registration_page.password_input).to_have_attribute("type", "text")

    with allure.step("Step 4 — Click HIDE; verify password is re-masked"):
        registration_page.toggle_password_visibility()
        expect(registration_page.password_input).to_have_attribute("type", "password")

    with allure.step("Step 5 — Enter confirm password; verify it is masked by default"):
        registration_page.fill_confirm_password(data.confirm_password)
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
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

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
@pytest.mark.usefixtures("email_otp_required")
@allure.story("TC-10: OTP Delivery")
@allure.title("OTP is sent and countdown timer appears after clicking Get OTP")
def test_tc10_otp_sent_on_email_submit(registration_page, valid_registration_data):
    """
    Given I have entered a valid email,
    When I click Get OTP,
    Then the countdown timer is visible and the OTP button becomes disabled.
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "OTP sent", "dev_otp": "123456"}'
        ) if "action=send_otp" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": false}'
        ) if "action=check_email" in (request.post_data or "")
        else route.continue_()
    )

    try:
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
    finally:
        registration_page.page.unroute("**/register_process.php*")


# =============================================================================
# TC-11 — Successful OTP Verification (AC-3)
# =============================================================================
@aio_case("KAN-TC-11")
@pytest.mark.usefixtures("email_otp_required")
@allure.story("TC-11: Successful OTP Verification")
@allure.title("Email is verified after entering correct OTP within validity window")
def test_tc11_email_verified_after_correct_otp(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and have clicked Get OTP,
    When I retrieve the 6-digit OTP from my inbox and enter it,
    Then the email field is marked as verified (green tick / 'Verified' label).

    Notion ref: TC-11 (AC-3)
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "OTP sent", "dev_otp": "123456"}'
        ) if "action=send_otp" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": false}'
        ) if "action=check_email" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "Verified"}'
        ) if "action=verify_otp" in (request.post_data or "")
        else route.continue_()
    )

    try:
        with allure.step("Fill Section 1 credentials"):
            registration_page.fill_credentials(
                data.username, data.password, data.confirm_password
            )

        with allure.step("Enter email and click Get OTP"):
            registration_page.fill_email_and_request_otp(data.email)

        with allure.step("Assert OTP countdown / resend button is visible (OTP dispatched)"):
            expect(registration_page.otp_countdown_timer).to_be_visible()

        with allure.step("Enter OTP and verify email"):
            registration_page.enter_otp_and_verify_email("123456")

        with allure.step("Assert email verified tag is shown"):
            expect(registration_page.email_verified_tag).to_be_visible()
    finally:
        registration_page.page.unroute("**/register_process.php*")


# =============================================================================
# TC-12 — OTP: Incorrect OTP Entry
# =============================================================================
@aio_case("KAN-TC-12")
@pytest.mark.usefixtures("email_otp_required")
@allure.story("TC-12: OTP — Incorrect Entry")
@allure.title("Error shown when an incorrect OTP is submitted")
def test_tc12_incorrect_otp_shows_error(registration_page, valid_registration_data):
    """
    Given OTP has been sent to the registered email,
    When I enter a deliberately wrong OTP (000000),
    Then an error 'Invalid OTP. Please check and try again.' is displayed
    and the email remains unverified.

    Notion ref: TC-12 | Data: wrong OTP = 000000
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "OTP sent", "dev_otp": "123456"}'
        ) if "action=send_otp" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": false}'
        ) if "action=check_email" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": false, "message": "Invalid OTP. Please check and try again."}'
        ) if "action=verify_otp" in (request.post_data or "")
        else route.continue_()
    )

    try:
        with allure.step("Fill Section 1 credentials"):
            registration_page.fill_credentials(
                data.username, data.password, data.confirm_password
            )

        with allure.step("Enter valid email and request OTP"):
            registration_page.fill_email_and_request_otp(data.email)
            expect(registration_page.otp_countdown_timer).to_be_visible()

        with allure.step("Enter an incorrect OTP and click Verify"):
            error = registration_page.submit_otp_and_handle_alert("000000")

        with allure.step("Assert OTP error shown; email verified tag absent"):
            assert "Invalid OTP" in error
            expect(registration_page.email_verified_tag).not_to_be_visible()
    finally:
        registration_page.page.unroute("**/register_process.php*")


# =============================================================================
# TC-13 — OTP: Expired OTP + Resend (EC-2)
# =============================================================================
@aio_case("KAN-TC-13")
@pytest.mark.usefixtures("email_otp_required")
@allure.story("TC-13: OTP — Expired OTP")
@allure.title("Expired OTP is rejected and resend issues a fresh OTP")
def test_tc13_expired_otp_rejected_resend_works(registration_page, valid_registration_data):
    """
    Given the OTP countdown has reached zero (OTP expired),
    When I enter the original (now-expired) OTP,
    Then an error 'Invalid OTP. OTP has expired.' is shown,
    And clicking 'Get OTP' again delivers a fresh OTP that can be verified.

    Notion ref: TC-13 (EC-2)
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "OTP sent", "dev_otp": "111111"}'
        ) if "action=send_otp" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": false}'
        ) if "action=check_email" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": false, "message": "Invalid OTP. OTP has expired."}'
        ) if "action=verify_otp" in (request.post_data or "") and "111111" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": true, "message": "Verified"}'
        ) if "action=verify_otp" in (request.post_data or "")
        else route.continue_()
    )

    try:
        with allure.step("Fill Section 1 credentials"):
            registration_page.fill_credentials(
                data.username, data.password, data.confirm_password
            )

        with allure.step("Enter valid email and request OTP; record the timer start"):
            registration_page.fill_email_and_request_otp(data.email)
            expect(registration_page.otp_countdown_timer).to_be_visible()

        with allure.step("Enter the expired OTP and assert expired error alert"):
            error = registration_page.submit_otp_and_handle_alert("111111")
            assert "Invalid OTP" in error or "expired" in error.lower()

        with allure.step("Simulate countdown expiry to enable Resend button"):
            registration_page.page.evaluate("""() => {
                const btn = document.getElementById('otpBtn');
                btn.disabled = false;
                btn.textContent = '📧 Resend OTP';
                btn.style.cursor = 'pointer';
            }""")
            expect(registration_page.otp_button).to_be_enabled()

        with allure.step("Click Get OTP resend button; assert new countdown starts"):
            registration_page.otp_button.click()
            expect(registration_page.otp_countdown_timer).to_be_visible()

        with allure.step("Enter fresh OTP and verify email"):
            registration_page.enter_otp_and_verify_email("222222")
            expect(registration_page.email_verified_tag).to_be_visible()
    finally:
        registration_page.page.unroute("**/register_process.php*")


# =============================================================================
# TC-14 — OTP: Undeliverable Email (EC-3)
# =============================================================================
@aio_case("KAN-TC-14")
@pytest.mark.usefixtures("email_otp_required")
@allure.story("TC-14: OTP — Undeliverable Email")
@allure.title("Error shown when OTP cannot be delivered to a non-existent domain")
def test_tc14_undeliverable_email_shows_error(registration_page, invalid_email_domain_data):
    """
    Given I enter a syntactically valid email whose domain does not exist,
    When I click Get OTP,
    Then an error 'OTP could not be delivered' is displayed and no OTP is sent.

    Notion ref: TC-14 (EC-3) | Data: user@nonexistentdomain12345
    """
    data = invalid_email_domain_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    dialog_message = []

    def handle_dialog(dialog):
        dialog_message.append(dialog.message)
        dialog.dismiss()

    registration_page.page.on("dialog", handle_dialog)

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"success": false, "message": "OTP could not be delivered. Please check the email address and try again."}'
        ) if "action=send_otp" in (request.post_data or "")
        else route.fulfill(
            status=200,
            content_type="application/json",
            body='{"taken": false}'
        ) if "action=check_email" in (request.post_data or "")
        else route.continue_()
    )

    try:
        with allure.step("Fill Section 1 credentials"):
            registration_page.fill_credentials(
                data.username, data.password, data.confirm_password
            )

        with allure.step(f"Enter non-existent-domain email: '{data.email}' and click Get OTP"):
            registration_page.fill_email_and_request_otp(data.email)
            registration_page.page.wait_for_timeout(500)

        with allure.step("Assert OTP delivery failure error is displayed"):
            assert len(dialog_message) > 0, "Expected alert dialog on undeliverable email"
            msg = dialog_message[0].lower()
            assert "email" in msg or "otp" in msg or "delivered" in msg

        with allure.step("Assert email is NOT marked as verified"):
            expect(registration_page.email_verified_tag).not_to_be_visible()
    finally:
        registration_page.page.remove_listener("dialog", handle_dialog)
        registration_page.page.unroute("**/register_process.php*")


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
    lowercase_pan = data.pan_number

    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step(f"Type PAN in lowercase: '{lowercase_pan}'"):
        registration_page.fill_pan(lowercase_pan)

    with allure.step("Assert field value is auto-uppercased"):
        expect(registration_page.pan_input).to_have_value(lowercase_pan.upper())

    with allure.step("Assert valid PAN format message is shown"):
        expect(registration_page.pan_helper).to_contain_text("Valid PAN format")


# =============================================================================
# TC-16 — PAN: Duplicate PAN Blocked (AC-7)
# =============================================================================
@aio_case("KAN-TC-17")
@allure.story("TC-16: PAN — Duplicate PAN Blocked")
@allure.title("Submission blocked when PAN is already registered in the system")
def test_tc16_duplicate_pan_blocked(registration_page, duplicate_pan_data):
    """
    Given a registration already exists with PAN AAAPL1234C,
    And I am on the Pre-Registration page with all other fields validly filled,
    When I enter the duplicate PAN and click SUBMIT REGISTRATION,
    Then the error 'This PAN number is already registered (or a registration
    with it is in progress). If this is your PAN, please contact support.' is shown.

    Notion ref: TC-16 (AC-7)
    """
    data = duplicate_pan_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": False, "message": registration_page.duplicate_pan_error})
        ) if ("register" in (request.post_data or "")) and ("action" in (request.post_data or ""))
        else route.continue_()
    )

    try:
        with allure.step("Fill Sections 1 & 2 with the duplicate PAN"):
            _fill_credentials_and_contact(registration_page, data)
            registration_page.select_district(data.district)

        with allure.step("Fill Section 3 — upload PAN card and signatory letterhead"):
            registration_page.fill_document_upload()

        with allure.step("Fill Section 4 CAPTCHA and accept Section 5 declaration"):
            registration_page.fill_captcha()
            registration_page.accept_declaration()

        with allure.step("Click SUBMIT REGISTRATION"):
            registration_page.submit()

        with allure.step("Assert duplicate PAN error and submission blocked"):
            expect(registration_page.server_error).to_be_visible()
            expect(registration_page.server_error).to_contain_text(registration_page.duplicate_pan_error)
    finally:
        registration_page.page.unroute("**/register_process.php*")


# =============================================================================
# TC-17 — District Dropdown Selection
# =============================================================================
@aio_case("KAN-TC-18")
@allure.story("TC-17: District Dropdown Selection")
@allure.title("District dropdown accepts a valid selection and shows error when skipped")
def test_tc17_district_dropdown_selection(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page,
    When I open the District dropdown and select 'Mumbai City',
    Then 'Mumbai City' is displayed as the selected value.
    When I attempt to submit without selecting a district,
    Then the alert 'Please select your district.' appears.

    Notion ref: TC-17
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Fill credentials and required fields prior to district"):
        _fill_credentials_and_contact(registration_page, data)

    with allure.step("Verify dropdown is visible"):
        expect(registration_page.district_select).to_be_visible()

    with allure.step("Select 'Mumbai City' from the dropdown"):
        registration_page.select_district("Mumbai City")

    with allure.step("Assert 'Mumbai City' is the selected value and City / Town box stays hidden"):
        expect(registration_page.district_select).to_have_value("519")
        expect(registration_page.city_box).to_be_hidden()

    with allure.step("Reset to no selection and attempt submit"):
        registration_page.district_select.select_option(value="")
        registration_page.blur_district()
        error = registration_page.submit_and_handle_alert()

    with allure.step("Assert required-district error alert appears"):
        assert registration_page.district_not_selected_error in error


# =============================================================================
# TC-18 — CAPTCHA: Valid Entry
# =============================================================================
@aio_case("KAN-TC-19")
@allure.story("TC-18: CAPTCHA — Valid Entry")
@allure.title("Correct CAPTCHA characters pass validation and produce no captcha error")
def test_tc18_valid_captcha_passes_validation(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page and can see the CAPTCHA text in Section 4,
    When I read the current CAPTCHA value from the DOM and type it exactly,
    Then the captcha input field retains the valid value.

    Notion ref: TC-18
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Fill Section 1 credentials"):
        registration_page.fill_credentials(
            data.username, data.password, data.confirm_password
        )

    with allure.step("Observe the CAPTCHA image and read its text from the DOM"):
        captcha_text = registration_page.read_captcha_value()
        assert len(captcha_text) == 6, f"Expected 6 captcha characters, got '{captcha_text}'"

    with allure.step(f"Enter the exact CAPTCHA characters: '{captcha_text}'"):
        registration_page.fill_captcha(captcha_text)

    with allure.step("Assert captcha input field retains value"):
        expect(registration_page.captcha_input).to_have_value(captcha_text)


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
    Then the error 'Incorrect CAPTCHA. Please try again.' is displayed
    and the form submission is blocked.

    Notion ref: TC-20 | Data: wrong captcha = 'AAA111'
    """
    WRONG_CAPTCHA = "AAA111"
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    registration_page.page.route(
        "**/register_process.php*",
        lambda route, request: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"success": False, "message": registration_page.incorrect_captcha_error})
        ) if ("register" in (request.post_data or "")) and ("action" in (request.post_data or ""))
        else route.continue_()
    )

    try:
        with allure.step("Fill Sections 1 – 3 validly"):
            _fill_credentials_and_contact(registration_page, data)
            registration_page.select_district(data.district)
            registration_page.fill_document_upload()

        with allure.step(f"Enter an incorrect CAPTCHA '{WRONG_CAPTCHA}' and accept the declaration"):
            registration_page.fill_captcha(WRONG_CAPTCHA)
            registration_page.accept_declaration()

        with allure.step("Click SUBMIT to trigger validation"):
            registration_page.submit()

        with allure.step("Assert CAPTCHA error is shown"):
            expect(registration_page.server_error).to_be_visible()
            expect(registration_page.server_error).to_contain_text(registration_page.incorrect_captcha_error)
    finally:
        registration_page.page.unroute("**/register_process.php*")


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
    And the CAPTCHA input field is cleared.

    Notion ref: TC-21 (EC-1)
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Record the current CAPTCHA value from the DOM"):
        original_captcha = registration_page.read_captcha_value()
        assert len(original_captcha) == 6, f"Expected 6 captcha chars, got '{original_captcha}'"

    with allure.step(f"Type the original CAPTCHA into the input: '{original_captcha}'"):
        registration_page.fill_captcha(original_captcha)
        expect(registration_page.captcha_input).to_have_value(original_captcha)

    with allure.step("Click Refresh and capture the new CAPTCHA value"):
        new_captcha = registration_page.refresh_captcha()

    with allure.step("Assert the CAPTCHA value has changed after Refresh"):
        assert new_captcha != original_captcha, (
            f"CAPTCHA did not change after Refresh — still showing '{original_captcha}'"
        )

    with allure.step("Assert the CAPTCHA input field has been cleared by the Refresh"):
        expect(registration_page.captcha_input).to_have_value("")


# =============================================================================
# TC-21 — Declaration Checkbox: Mandatory Check
# =============================================================================
@aio_case("KAN-TC-22")
@allure.story("TC-21: Declaration Checkbox — Mandatory")
@allure.title("Submit blocked when Declaration checkbox is unchecked; unblocked after check")
def test_tc21_declaration_checkbox_mandatory(registration_page, valid_registration_data):
    """
    Given all of Sections 1 – 4 are validly filled,
    When I leave the Declaration checkbox unchecked and click SUBMIT REGISTRATION,
    Then the error is displayed and submission is blocked.
    When I check the checkbox,
    Then the error disappears.

    Notion ref: TC-22
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Fill Sections 1 – 4 prior to declaration"):
        _fill_credentials_and_contact(registration_page, data)
        registration_page.select_district(data.district)
        registration_page.fill_document_upload()
        registration_page.fill_captcha()

    with allure.step("Confirm declaration checkbox is unchecked"):
        if registration_page.declaration_checkbox.is_checked():
            registration_page.declaration_checkbox.uncheck()
        expect(registration_page.declaration_checkbox).not_to_be_checked()

    with allure.step("Click SUBMIT REGISTRATION without accepting declaration"):
        registration_page.submit()

    with allure.step("Assert declaration error is displayed; submission is blocked"):
        expect(registration_page.declaration_error).to_be_visible()
        expect(registration_page.declaration_error).to_contain_text(
            registration_page.declaration_error_message
        )
        expect(registration_page.success_overlay).to_be_hidden()

    with allure.step("Check the Declaration checkbox"):
        registration_page.accept_declaration()
        expect(registration_page.declaration_checkbox).to_be_checked()

    with allure.step("Assert declaration error is no longer shown"):
        expect(registration_page.declaration_error).not_to_be_visible()


# =============================================================================
# TC-22 — Already Registered User Link Visible (EC-8)
# =============================================================================
@aio_case("KAN-TC-25")
@allure.story("TC-22: Already Registered User — Login Link Visible")
@allure.title("'Login & Continue' link is visible in the resume banner and redirects to login page")
def test_tc22_already_registered_login_link_visible(registration_page, login_page):
    """
    Given I am on the Pre-Registration page,
    When I look at the 'Already started a registration?' banner above the form,
    Then the 'Login & Continue' link is visible.
    When I click it,
    Then I am redirected to the MPPA Portal login page.

    Notion ref: TC-25 (EC-8)
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Assert the resume banner and 'Login & Continue' link are visible"):
        expect(registration_page.resume_banner).to_be_visible()
        expect(registration_page.resume_banner).to_contain_text("Already started a registration?")
        expect(registration_page.login_link).to_be_visible()

    with allure.step("Click the login link and assert redirect to login page"):
        registration_page.click_login_link()
        expect(login_page.login_title).to_be_visible()


# =============================================================================
# TC-23 — Self-Declaration Text is Read-Only
# =============================================================================
@aio_case("KAN-TC-27")
@allure.story("TC-23: Self-Declaration Text — Read-Only")
@allure.title("The declaratory clauses in Section 5 are displayed in a non-editable block")
def test_tc23_declaration_text_is_readonly(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I navigate to Section 5: Declaration & Undertaking,
    Then the declaratory clauses are displayed inside a container that is non-editable.

    Notion ref: TC-27
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Locate the declaration text block in Section 5"):
        expect(registration_page.section_header(5)).to_contain_text("Declaration & Undertaking")
        expect(registration_page.declaration_text_block).to_be_visible()

    with allure.step("Assert the declaration container is read-only (non-editable)"):
        content_editable = registration_page.declaration_text_block.get_attribute("contenteditable")
        assert content_editable in (None, "false"), (
            f"Declaration block is editable (contenteditable='{content_editable}')"
        )
        editable_children = registration_page.declaration_text_block.locator(
            "input:not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled])"
        )
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
    Then static UI elements are rendered correctly.

    Notion ref: TC-28
    """
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Assert page header reads 'New Agency Registration Form'"):
        expect(registration_page.page_title).to_be_visible()
        expect(registration_page.page_title).to_contain_text("Registration")

    with allure.step("Assert subtitle is displayed correctly"):
        expect(registration_page.page_subtitle).to_be_visible()
        expect(registration_page.page_subtitle).to_contain_text("Please fill all mandatory fields carefully.")

    with allure.step("Assert mandatory field badge is visible"):
        expect(registration_page.mandatory_field_badge).to_be_visible()
        expect(registration_page.mandatory_field_badge).to_contain_text("Marked fields are mandatory")

    with allure.step("Assert the five numbered section headers render in order"):
        expected_sections = [
            "Agency & Login Credentials",
            "Contact & Identity Verification",
            "Document Upload",
            "Captcha Verification",
            "Declaration & Undertaking",
        ]
        for number, title in enumerate(expected_sections, start=1):
            expect(registration_page.section_header(number)).to_contain_text(title)

    with allure.step("Assert technical support footer text is present"):
        expect(registration_page.support_footer).to_be_visible()
        expect(registration_page.support_footer).to_contain_text("support@placementportal.gov.in")


# =============================================================================
# TC-25 — Full Valid Submission: Success Overlay & Part A Navigation
# =============================================================================
@aio_case("KAN-TC-23")
@allure.story("TC-25: Full Valid Submission — Success Overlay & Part A Navigation")
@allure.title("Successful E2E pre-registration displays success overlay and redirects to Part A")
@pytest.mark.parametrize(
    "data_fixture",
    ["valid_registration_data", "district_other_data"],
    ids=["listed_district", "district_other_with_city"],
)
def test_tc25_full_valid_submission_shows_success_overlay(registration_page, data_fixture, request):
    """
    Given I fill all sections correctly (valid credentials, email,
    valid unique PAN, selected district — plus City / Town when the district is
    'Other' — uploaded documents, correct CAPTCHA, accepted declaration),
    When I click SUBMIT REGISTRATION,
    Then the server accepts the registration (no mocked response),
    And the 'Registration Started!' overlay is shown with a redirect countdown
    and a 'Continue to Part A' button (the Application ID is only issued after payment),
    And the registered user is persisted to the local state store DB
    (including city_name for the 'Other' variant).

    This is the producer of agency users for the login / home / dashboard /
    step-1 fixtures (get_agency_user_with_no_form), so it must register for real.

    Notion ref: TC-23 (AC-5 & AC-6) | Data: random listed district (supplies the Step-1
    Maharashtra-head-office users); district Other + random City / Town
    """
    from utils.state_store import TestStateStore

    data = request.getfixturevalue(data_fixture)
    allure.dynamic.parameter("scenario", data.scenario_label)
    # A successful submission logs the new agency in. The browser context is
    # shared across the session (conftest.py), so drop that login afterwards —
    # otherwise the next test's register.php no longer shows the form.
    request.addfinalizer(registration_page.start_new_session)
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Fill Section 1 — agency name and login credentials"):
        registration_page.fill_agency_name(getattr(data, "agency_name", "Test Agency"))
        registration_page.fill_credentials(data.username, data.password, data.confirm_password)
        expect(registration_page.username_helper).to_contain_text("Username available")

    with allure.step(f"Fill Section 2 — contact & identity, district '{data.district}' (OTP only if enabled on the server)"):
        registration_page.fill_contact_identity(
            data.email,
            data.pan_number,
            data.district,
            getattr(data, "mobile", "9876543210"),
            getattr(data, "alt_phone", "02224567890"),
            data.city_name,
        )
        expect(registration_page.pan_helper).to_contain_text("Valid PAN format")
        if data.city_name:
            expect(registration_page.city_name_input).to_have_value(data.city_name)
        else:
            expect(registration_page.city_box).to_be_hidden()

    with allure.step("Fill Section 3 — upload PAN card and signatory letterhead"):
        registration_page.fill_document_upload()
        expect(registration_page.pan_file_helper).to_contain_text("✓")
        expect(registration_page.auth_sign_file_helper).to_contain_text("✓")

    with allure.step("Fill Section 4 CAPTCHA and accept Section 5 declaration"):
        registration_page.fill_captcha()
        registration_page.accept_declaration()

    with allure.step("Click SUBMIT REGISTRATION and capture the server response"):
        with registration_page.page.expect_response(
            lambda r: "register_process.php" in r.url
            and r.request.method == "POST"
            and b"check_" not in (r.request.post_data_buffer or b"")
        ) as response_info:
            registration_page.submit()
        body = response_info.value.json()
        allure.attach(
            str(body), name="register_process.php response",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Assert the server accepted the registration"):
        expect(registration_page.server_error).to_be_hidden()
        assert body.get("success") is True, f"Registration rejected by server: {body.get('message')}"

    with allure.step("Assert 'Registration Started!' overlay with Part A redirect is displayed"):
        expect(registration_page.success_overlay).to_be_visible()
        expect(registration_page.registration_success_message).to_contain_text("Registration Started!")
        expect(registration_page.redirect_countdown).to_be_visible()
        expect(registration_page.continue_to_part_a_button).to_be_visible()
        expect(registration_page.continue_to_part_a_button).to_have_attribute(
            "href", re.compile(r"partA\.php")
        )

    with allure.step("Record registered user in state store DB for downstream tests"):
        # No ID is shown on screen any more; keep whatever the server returns (may be None).
        registration_id = body.get("registration_id") or body.get("application_id")
        TestStateStore().record_user(
            role="agency",
            username=data.username,
            password=data.password,
            agency_name=data.agency_name,
            email=data.email,
            mobile=data.mobile,
            alt_phone=data.alt_phone,
            pan=data.pan_number,
            district=data.district,
            city_name=data.city_name or None,
            registration_id=registration_id,
        )
        allure.attach(
            f"username={data.username}\ndistrict={data.district}\ncity_name={data.city_name or None}"
            f"\nregistration_id={registration_id}",
            name="State store entry",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Assert the stored row carries the district and City / Town"):
        stored = TestStateStore().get_user_by_username(data.username)
        assert stored is not None, f"{data.username} was not written to the state store"
        assert stored.district == data.district
        assert stored.city_name == (data.city_name or None)


# =============================================================================
# TC-26 — Agency Name: Mandatory, Max 150 Characters
# =============================================================================
@aio_case("KAN-TC-416")
@allure.story("TC-26: Agency Name — Mandatory, Max 150 Characters")
@allure.title("Agency Name is mandatory and limited to 150 characters")
def test_tc26_agency_name_mandatory_and_max_length(registration_page, agency_name_too_long_data):
    """
    Given I am on the Pre-Registration page,
    When I leave Agency Name blank and click SUBMIT REGISTRATION,
    Then the browser's required-field check blocks submission on Agency Name.
    When I type more than 150 characters,
    Then the field stops at 150 characters.

    AIO ref: KAN-TC-416 | Data: 160-character agency name
    """
    data = agency_name_too_long_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.agency_name_input).to_be_visible()

    with allure.step("Assert Agency Name placeholder and helper text"):
        expect(registration_page.agency_name_input).to_have_attribute(
            "placeholder", "Enter the full legal name of your placement agency"
        )
        expect(registration_page.agency_name_helper).to_contain_text(
            "This should match the name on your PAN card / registration documents"
        )

    with allure.step("Leave Agency Name blank and click SUBMIT REGISTRATION"):
        registration_page.fill_agency_name("")
        registration_page.submit()

    with allure.step("Assert the browser's required-field check blocks submission on Agency Name"):
        assert registration_page.first_invalid_field_id() == "agencyName"
        assert registration_page.get_validation_message(registration_page.agency_name_input), (
            "Expected a browser validation message on Agency Name"
        )
        expect(registration_page.success_overlay).to_be_hidden()

    with allure.step(f"Type a {len(data.agency_name)}-character agency name"):
        registration_page.type_agency_name(data.agency_name)

    with allure.step("Assert input stops at 150 characters"):
        expect(registration_page.agency_name_input).to_have_value(data.expected_value)


# =============================================================================
# TC-27 — Mobile Number: Valid 10-Digit Indian Mobile Only
# =============================================================================
@aio_case("KAN-TC-417")
@allure.story("TC-27: Mobile Number — Valid 10-Digit Indian Mobile Only")
@allure.title("Mobile Number accepts only a valid 10-digit Indian mobile number")
def test_tc27_mobile_number_validation(
    registration_page, valid_registration_data, mobile_with_non_digits_data,
    mobile_invalid_start_data, mobile_too_short_data,
):
    """
    Given I am on the Pre-Registration page,
    When I type a mobile number containing letters and symbols,
    Then non-digits are stripped and input stops at 10 digits.
    When the field is blank on submit,
    Then the browser's required-field check blocks submission on Mobile Number.
    When I submit a number starting with 5, or with fewer than 10 digits,
    Then the alert 'Enter a valid 10-digit mobile number starting with 6, 7, 8 or 9.' is shown.

    AIO ref: KAN-TC-417 | Data: 98a7-6 5432109, 5123456789, 98765
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.mobile_input).to_be_visible()

    with allure.step(f"Type '{mobile_with_non_digits_data.mobile}' into Mobile Number"):
        registration_page.type_mobile(mobile_with_non_digits_data.mobile)

    with allure.step("Assert non-digits are stripped and input is cut at 10 digits"):
        expect(registration_page.mobile_input).to_have_value(mobile_with_non_digits_data.expected_value)

    # Browser required-field check must run before submit_and_handle_alert(),
    # which switches the form to noValidate for the rest of the test.
    with allure.step("Fill earlier fields, clear Mobile Number and click SUBMIT REGISTRATION"):
        _fill_credentials_and_contact(registration_page, data)
        registration_page.fill_mobile("")
        registration_page.submit()

    with allure.step("Assert the browser's required-field check blocks submission on Mobile Number"):
        assert registration_page.first_invalid_field_id() == "mobile"
        expect(registration_page.success_overlay).to_be_hidden()

    for bad in (mobile_invalid_start_data, mobile_too_short_data):
        with allure.step(f"Submit with mobile '{bad.mobile}' and assert the invalid-mobile alert"):
            registration_page.fill_mobile(bad.mobile)
            message = registration_page.submit_and_handle_alert()
            assert bad.expected_error in message, f"Unexpected alert for '{bad.mobile}': {message!r}"

    with allure.step("Enter a valid mobile number; assert it is accepted with the helper text shown"):
        registration_page.fill_mobile(data.mobile)
        expect(registration_page.mobile_input).to_have_value(data.mobile)
        expect(registration_page.mobile_helper).to_contain_text(
            "Valid Indian mobile number starting with 6, 7, 8 or 9"
        )


# =============================================================================
# TC-28 — Alternate Phone Number: Mandatory, Digits / + / - / Spaces Only
# =============================================================================
@aio_case("KAN-TC-418")
@allure.story("TC-28: Alternate Phone Number — Mandatory, Restricted Characters")
@allure.title("Alternate Phone Number is mandatory and accepts only digits, +, - and spaces")
def test_tc28_alternate_phone_validation(
    registration_page, valid_registration_data, alt_phone_invalid_chars_data
):
    """
    Given I am on the Pre-Registration page,
    When I type an alternate phone number containing brackets and letters,
    Then those characters are stripped and input stops at 15 characters.
    When the field is blank on submit,
    Then the browser's required-field check blocks submission on Alternate Phone Number.

    AIO ref: KAN-TC-418 | Data: +91 (22) 2456-7890x
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.alt_phone_input).to_be_visible()

    with allure.step(f"Type '{alt_phone_invalid_chars_data.alt_phone}' into Alternate Phone Number"):
        registration_page.type_alt_phone(alt_phone_invalid_chars_data.alt_phone)

    with allure.step("Assert brackets and letters are stripped and input stops at 15 characters"):
        expect(registration_page.alt_phone_input).to_have_value(alt_phone_invalid_chars_data.expected_value)

    with allure.step("Fill earlier fields, clear Alternate Phone Number and click SUBMIT REGISTRATION"):
        _fill_credentials_and_contact(registration_page, data)
        registration_page.fill_alt_phone("")
        registration_page.submit()

    with allure.step("Assert the browser's required-field check blocks submission on Alternate Phone Number"):
        assert registration_page.first_invalid_field_id() == "altPhone"
        expect(registration_page.success_overlay).to_be_hidden()

    with allure.step("Enter a valid landline number; assert it is accepted with the helper text shown"):
        registration_page.fill_alt_phone(data.alt_phone)
        expect(registration_page.alt_phone_input).to_have_value(data.alt_phone)
        expect(registration_page.alt_phone_helper).to_contain_text(
            "Landline or secondary official contact number"
        )


# =============================================================================
# TC-29 — Document Upload: Valid Files Accepted
# =============================================================================
@aio_case("KAN-TC-419")
@allure.story("TC-29: Document Upload — Valid Files Accepted")
@allure.title("Valid PAN card and letterhead files are accepted in Document Upload")
def test_tc29_valid_documents_accepted(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I upload a PDF under 2 MB as the Company PAN Card
    And a JPG under 5 MB as the Authorised Signatory letterhead,
    Then each helper changes to '✓ <file name> (<size> MB)'.

    AIO ref: KAN-TC-419 | Data: valid_doc.pdf, valid_image.jpg
    """
    registration_page.ensure_on_registration_page()

    with allure.step("Assert Section 3 shows both uploads with their limits"):
        expect(registration_page.section_header(3)).to_contain_text("Document Upload")
        expect(registration_page.pan_upload_mode_file).to_be_checked()
        expect(registration_page.auth_upload_mode_file).to_be_checked()
        expect(registration_page.pan_file_helper).to_contain_text("PDF, JPG or PNG — max 2 MB")
        expect(registration_page.auth_sign_file_helper).to_contain_text(
            "Signed letterhead — PDF, JPG or PNG — max 5 MB"
        )

    with allure.step("Upload a valid PDF as the Company PAN Card"):
        registration_page.upload_pan_document(VALID_PDF)
        expect(registration_page.pan_file_helper).to_contain_text(f"✓ {os.path.basename(VALID_PDF)}")
        assert registration_page.get_selected_file_count(registration_page.pan_file_input) == 1

    with allure.step("Upload a valid JPG as the Authorised Signatory letterhead"):
        registration_page.upload_auth_sign_document(VALID_JPG)
        expect(registration_page.auth_sign_file_helper).to_contain_text(f"✓ {os.path.basename(VALID_JPG)}")
        assert registration_page.get_selected_file_count(registration_page.auth_sign_file_input) == 1


# =============================================================================
# TC-30 — Document Upload: Oversized File Rejected
# =============================================================================
@aio_case("KAN-TC-420")
@allure.story("TC-30: Document Upload — Oversized File Rejected")
@allure.title("Document larger than the size limit is rejected immediately")
def test_tc30_oversized_document_rejected(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I select a PAN card file over 2 MB, or a letterhead file over 5 MB,
    Then the file is cleared and the helper shows 'File exceeds N MB limit.'.
    When I then select a file within the limit,
    Then it is accepted.

    AIO ref: KAN-TC-420 | Data: oversized.pdf (3 MB), oversized_image.jpg (> 5 MB)
    """
    if OVERSIZED_IMAGE is None:
        pytest.skip(
            "oversized_image.jpg not found in test_data/documents/ — "
            "add a JPG > 5 MB to run this test."
        )
    registration_page.ensure_on_registration_page()

    with allure.step("Select a PDF larger than 2 MB for Company PAN Card"):
        registration_page.upload_pan_document(OVERSIZED_FILE)

    with allure.step("Assert the PAN file is cleared with the 2 MB error"):
        expect(registration_page.pan_file_helper).to_have_text(registration_page.pan_file_too_large_error)
        assert registration_page.get_selected_file_count(registration_page.pan_file_input) == 0

    with allure.step("Select a JPG larger than 5 MB for the Authorised Signatory letterhead"):
        registration_page.upload_auth_sign_document(OVERSIZED_IMAGE)

    with allure.step("Assert the letterhead file is cleared with the 5 MB error"):
        expect(registration_page.auth_sign_file_helper).to_have_text(registration_page.auth_sign_file_too_large_error)
        assert registration_page.get_selected_file_count(registration_page.auth_sign_file_input) == 0

    with allure.step("Select files within the limit; assert both are accepted"):
        registration_page.upload_pan_document(VALID_PDF)
        registration_page.upload_auth_sign_document(VALID_PDF)
        expect(registration_page.pan_file_helper).to_contain_text("✓")
        expect(registration_page.auth_sign_file_helper).to_contain_text("✓")


# =============================================================================
# TC-31 — Document Upload: Unsupported File Type Rejected
# =============================================================================
@aio_case("KAN-TC-421")
@allure.story("TC-31: Document Upload — Unsupported File Type Rejected")
@allure.title("Unsupported document file type is rejected immediately")
def test_tc31_unsupported_document_type_rejected(registration_page):
    """
    Given I am on the Pre-Registration page,
    When I select a file other than PDF, JPG or PNG for either upload,
    Then the file is cleared and the helper shows 'Only PDF, JPG, PNG files are allowed.'.

    AIO ref: KAN-TC-421 | Data: invalid.docx
    """
    registration_page.ensure_on_registration_page()

    with allure.step("Select a .docx file for Company PAN Card"):
        registration_page.upload_pan_document(INVALID_FORMAT)

    with allure.step("Assert the PAN file is cleared with the file-type error"):
        expect(registration_page.pan_file_helper).to_have_text(registration_page.unsupported_file_type_error)
        assert registration_page.get_selected_file_count(registration_page.pan_file_input) == 0

    with allure.step("Select a .docx file for the Authorised Signatory letterhead"):
        registration_page.upload_auth_sign_document(INVALID_FORMAT)

    with allure.step("Assert the letterhead file is cleared with the file-type error"):
        expect(registration_page.auth_sign_file_helper).to_have_text(registration_page.unsupported_file_type_error)
        assert registration_page.get_selected_file_count(registration_page.auth_sign_file_input) == 0


# =============================================================================
# TC-32 — Document Upload: Missing Document Blocks Submission
# =============================================================================
@aio_case("KAN-TC-422")
@allure.story("TC-32: Document Upload — Missing Document Blocks Submission")
@allure.title("Submission blocked when a mandatory document is not uploaded")
def test_tc32_missing_document_blocks_submission(registration_page, valid_registration_data):
    """
    Given all other fields are validly filled,
    When I upload only the Company PAN Card and click SUBMIT REGISTRATION,
    Then the alert 'Please upload the Authorised Signatory letterhead file.' is shown.
    When neither document is uploaded,
    Then the alert 'Please upload your PAN card file.' is shown.

    AIO ref: KAN-TC-422
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.username_input).to_be_visible()

    with allure.step("Fill Sections 1, 2 and 4 validly"):
        _fill_credentials_and_contact(registration_page, data)
        registration_page.select_district(data.district)
        registration_page.fill_captcha()

    with allure.step("Upload only the Company PAN Card and click SUBMIT REGISTRATION"):
        registration_page.upload_pan_document(VALID_PDF)
        message = registration_page.submit_and_handle_alert()

    with allure.step("Assert the missing-letterhead alert; form not submitted"):
        assert registration_page.auth_sign_file_missing_error in message, f"Unexpected alert: {message!r}"
        expect(registration_page.success_overlay).to_be_hidden()

    with allure.step("Remove the PAN card as well and click SUBMIT REGISTRATION"):
        registration_page.clear_pan_document()
        message = registration_page.submit_and_handle_alert()

    with allure.step("Assert the missing-PAN-card alert; form not submitted"):
        assert registration_page.pan_file_missing_error in message, f"Unexpected alert: {message!r}"
        expect(registration_page.success_overlay).to_be_hidden()


# =============================================================================
# TC-33 — User Manual Gate
# =============================================================================
@aio_case("KAN-TC-423")
@allure.story("TC-33: Registration User Manual Gate")
@allure.title("Registration User Manual must be accepted before the form opens")
def test_tc33_user_manual_gate(registration_page):
    """
    Given I have not accepted the User Manual in the current session,
    When I open register.php,
    Then I am redirected to the Registration User Manual with 5 sections
    And 'Proceed to Registration →' is enabled only while the agreement is ticked.
    When I tick it and proceed,
    Then the registration form opens, and reopening register.php in the
    same session goes straight to the form.

    AIO ref: KAN-TC-423
    """
    with allure.step("Start a fresh session and open register.php"):
        registration_page.start_new_session()
        registration_page.goto_register_url()

    with allure.step("Assert redirect to the Registration User Manual with 5 sections"):
        expect(registration_page.page).to_have_url(re.compile(r"user_manual\.php"))
        expect(registration_page.manual_title).to_have_text("Registration User Manual")
        for heading in ("1. Before You Begin", "2. Filling the Form", "3. Documents & Certificates",
                        "4. Fees & Payment", "5. Declarations"):
            expect(registration_page.manual_section_heading(heading)).to_be_visible()

    with allure.step("Assert 'Proceed to Registration →' is disabled before agreeing"):
        expect(registration_page.manual_proceed_button).to_be_disabled()

    with allure.step("Tick the agreement; assert the button becomes enabled"):
        registration_page.check_agree_user_manual()
        expect(registration_page.manual_proceed_button).to_be_enabled()

    with allure.step("Untick the agreement; assert the button is disabled again"):
        registration_page.uncheck_agree_user_manual()
        expect(registration_page.manual_proceed_button).to_be_disabled()

    with allure.step("Tick the agreement and click 'Proceed to Registration →'"):
        registration_page.check_agree_user_manual()
        registration_page.click_proceed_to_registration()

    with allure.step("Assert the registration form is displayed"):
        expect(registration_page.page_title).to_contain_text("New Agency Registration Form")

    with allure.step("Reopen register.php in the same session; assert the form opens directly"):
        registration_page.goto_register_url()
        expect(registration_page.page).to_have_url(re.compile(r"register\.php"))
        expect(registration_page.page_title).to_be_visible()


# =============================================================================
# TC-34 — District "Other" Reveals Mandatory City / Town
# =============================================================================
@aio_case("KAN-TC-424")
@allure.story("TC-34: District 'Other' — City / Town")
@allure.title("Selecting 'Other' district reveals a mandatory City / Town field")
def test_tc34_district_other_requires_city(
    registration_page, district_other_data, city_invalid_chars_data
):
    """
    Given I am on the Pre-Registration page,
    When I select 'Other' in the District dropdown,
    Then the City / Town field appears, receives focus and becomes mandatory,
    And digits / symbols typed into it are stripped.
    When City / Town is blank on submit,
    Then the browser's required-field check blocks submission on City / Town.
    When I change the District to another value,
    Then City / Town is hidden, cleared and no longer mandatory.

    AIO ref: KAN-TC-424 | Data: Navi Mumbai-2. Sector#5, Navi Mumbai
    """
    data = district_other_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.district_select).to_be_visible()

    with allure.step("Fill Sections 1 and 2 up to District"):
        _fill_credentials_and_contact(registration_page, data)

    with allure.step("Select 'Other' in the District dropdown"):
        registration_page.select_district(data.district)

    with allure.step("Assert City / Town appears, is focused and is mandatory"):
        expect(registration_page.city_box).to_be_visible()
        expect(registration_page.city_label).to_contain_text('City / Town')
        expect(registration_page.city_label).to_contain_text('(since you selected "Other")')
        expect(registration_page.city_name_input).to_be_focused()

    with allure.step(f"Type '{city_invalid_chars_data.city_name}'; assert digits and symbols are stripped"):
        registration_page.type_city_name(city_invalid_chars_data.city_name)
        expect(registration_page.city_name_input).to_have_value(city_invalid_chars_data.expected_value)

    with allure.step("Clear City / Town and click SUBMIT REGISTRATION"):
        registration_page.fill_city_name("")
        registration_page.submit()

    with allure.step("Assert the browser's required-field check blocks submission on City / Town"):
        assert registration_page.first_invalid_field_id() == "cityName"
        expect(registration_page.success_overlay).to_be_hidden()

    with allure.step(f"Enter a valid city: '{data.city_name}'"):
        registration_page.fill_city_name(data.city_name)
        expect(registration_page.city_name_input).to_have_value(data.city_name)

    with allure.step("Change the District to Pune; assert City / Town is hidden and cleared"):
        registration_page.select_district("Pune")
        expect(registration_page.city_box).to_be_hidden()
        expect(registration_page.city_name_input).to_have_value("")
        expect(registration_page.city_name_input).not_to_have_attribute("required", "")


# =============================================================================
# TC-35 — Confirm Password: Disabled Until Password, Paste Blocked
# =============================================================================
@aio_case("KAN-TC-425")
@allure.story("TC-35: Confirm Password — Disabled Until Password, Paste Blocked")
@allure.title("Confirm Password is disabled until a password is entered and blocks pasting")
def test_tc35_confirm_password_disabled_and_paste_blocked(registration_page, valid_registration_data):
    """
    Given I am on the Pre-Registration page,
    Then Confirm Password is disabled until the Password field has a value.
    When I paste into Confirm Password,
    Then nothing is pasted and 'Paste not allowed — type your password manually.'
    appears briefly.
    When I clear the Password field,
    Then Confirm Password is cleared and disabled again.

    AIO ref: KAN-TC-425
    """
    data = valid_registration_data
    registration_page.ensure_on_registration_page()
    expect(registration_page.password_input).to_be_visible()

    with allure.step("Assert Confirm Password is disabled before a password is entered"):
        expect(registration_page.confirm_password_input).to_be_disabled()
        expect(registration_page.confirm_password_helper).to_contain_text("Enter password above first")

    with allure.step("Type a password; assert Confirm Password becomes enabled"):
        registration_page.fill_password(data.password)
        expect(registration_page.confirm_password_input).to_be_enabled()
        expect(registration_page.confirm_password_helper).to_contain_text("Re-enter the password")

    with allure.step("Paste the password into Confirm Password"):
        registration_page.paste_into_confirm_password(data.password)

    with allure.step("Assert nothing was pasted and the paste error appears, then disappears"):
        expect(registration_page.confirm_password_input).to_have_value("")
        expect(registration_page.confirm_password_paste_error).to_be_visible()
        expect(registration_page.confirm_password_paste_error).to_have_text(registration_page.confirm_paste_error)
        expect(registration_page.confirm_password_paste_error).to_be_hidden(timeout=6000)

    with allure.step("Type the password manually; assert 'Passwords match'"):
        registration_page.fill_confirm_password(data.password)
        expect(registration_page.confirm_password_helper).to_contain_text("Passwords match")

    with allure.step("Clear the Password field; assert Confirm Password is cleared and disabled again"):
        registration_page.clear_password()
        expect(registration_page.confirm_password_input).to_be_disabled()
        expect(registration_page.confirm_password_input).to_have_value("")
        expect(registration_page.confirm_password_helper).to_contain_text("Enter password above first")

