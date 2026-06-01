import time

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.dashboard_page import AdminDashboardPage
from pages.admin.login_page import AdminLoginPage
from pages.login_page import LoginPage
from test_data.admin_login_factory import AdminLoginData
from utils.aio import aio_case


# ---------------------------------------------------------------------------
# TC-169  Successful admin login redirects to dashboard
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-169")
@allure.story("Admin Login")
@allure.title("TC-169: Successful Admin Login Redirects to Dashboard")
def test_tc169_successful_admin_login(
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given a Super Admin account exists and I am on the Admin Login page
    When  I enter valid username, password, and CAPTCHA and click ADMIN LOGIN
    Then  I am authenticated and redirected to the Dashboard Overview
    And   the SUPERADMIN role badge is visible in the sidebar

    Notion: KAN-TC-169 | data: valid_super_admin
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Verify restricted banner and Admin Login heading are shown"):
        expect(admin_login_page.restricted_banner).to_be_visible()
        expect(admin_login_page.admin_login_heading).to_be_visible()

    with allure.step(f"Login as '{valid_admin_login_data.username}' with valid credentials"):
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)

    with allure.step("Verify dashboard loaded and SUPERADMIN role badge is visible"):
        expect(admin_dashboard_page.role_badge).to_be_visible()
        expect(admin_dashboard_page.role_badge).to_contain_text("Super Admin")


# ---------------------------------------------------------------------------
# TC-170  Error shown and password cleared when credentials are wrong
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-170")
@allure.story("Admin Login")
@allure.title("TC-170: Error shown and password cleared when credentials are wrong")
def test_tc170_wrong_credentials(
    admin_login_page: AdminLoginPage, wrong_credentials_data: AdminLoginData
):
    """
    Given I am on the Admin Login page
    When  I enter incorrect credentials with a valid CAPTCHA and click ADMIN LOGIN
    Then  an error "Invalid username or password." is shown
    And   the username is retained while the password field is cleared

    Notion: KAN-TC-170 | data: wrong_credentials
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Submit incorrect credentials with a valid CAPTCHA"):
        admin_login_page.login(wrong_credentials_data.username, wrong_credentials_data.password)

    with allure.step("Verify error message is shown"):
        expect(admin_login_page.error_message).to_be_visible()
        assert wrong_credentials_data.expected_error in admin_login_page.error_message.text_content()

    with allure.step("Verify username is retained"):
        expect(admin_login_page.username_input).to_have_value(wrong_credentials_data.username)

    with allure.step("Verify password field is cleared"):
        expect(admin_login_page.password_input).to_have_value("")


# ---------------------------------------------------------------------------
# TC-171  Wrong CAPTCHA blocks login and generates a new CAPTCHA image
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-171")
@allure.story("Admin Login")
@allure.title("TC-171: Wrong CAPTCHA blocks login and generates a new CAPTCHA image")
def test_tc171_wrong_captcha(
    admin_login_page: AdminLoginPage, wrong_captcha_admin_data: AdminLoginData
):
    """
    Given I am on the Admin Login page with valid credentials ready
    When  I enter an incorrect CAPTCHA and click ADMIN LOGIN
    Then  an error "Incorrect CAPTCHA. Please try again." is shown
    And   a new CAPTCHA is generated and the CAPTCHA input is cleared

    Notion: KAN-TC-171 | data: valid_creds_wrong_captcha
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Capture the original CAPTCHA value"):
        original_captcha = admin_login_page.read_captcha_value()

    with allure.step("Submit valid credentials with an incorrect CAPTCHA and capture the alert"):
        message = admin_login_page.login_with_captcha_and_handle_alert(
            wrong_captcha_admin_data.username,
            wrong_captcha_admin_data.password,
            wrong_captcha_admin_data.captcha,
        )

    with allure.step("Verify the incorrect-CAPTCHA alert message"):
        assert "Captcha Incorrect" in message, (
            f"Expected a 'Captcha Incorrect' alert, got: {message!r}"
        )

    with allure.step("Verify a new CAPTCHA was generated and input cleared"):
        expect(admin_login_page.captcha_input).to_have_value("")
        assert admin_login_page.read_captcha_value() != original_captcha, (
            "A new CAPTCHA image should be generated after a failed attempt"
        )


# ---------------------------------------------------------------------------
# TC-172  Every login attempt is recorded in the audit log
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-172")
@allure.story("Admin Login")
@allure.title("TC-172: Every login attempt is recorded in the audit log")
def test_tc172_login_recorded_in_audit_log(
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given I perform a successful admin login
    When  I navigate to the Audit Log and inspect the most recent entry
    Then  the entry shows action=Admin Login, the username, an IP address,
          role=SUPERADMIN, and a timestamp

    Notion: KAN-TC-172 | data: valid_super_admin
    """
    with allure.step("Open the Admin Login page and log in successfully"):
        admin_login_page.open()
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)
        expect(admin_dashboard_page.role_badge).to_be_visible()

    with allure.step("Navigate to the Audit Log and filter to ADMIN_LOGIN events"):
        admin_dashboard_page.open_audit_log()
        expect(admin_dashboard_page.audit_log_table).to_be_visible()
        admin_dashboard_page.filter_audit_by_action("ADMIN_LOGIN")
        expect(admin_dashboard_page.audit_log_table).to_be_visible()

    with allure.step("Inspect the most recent ADMIN_LOGIN entry"):
        row = admin_dashboard_page.audit_log_first_row
        expect(row).to_be_visible()

    with allure.step("Verify action pill reads 'Admin Login'"):
        expect(admin_dashboard_page.audit_row_action(row)).to_contain_text("Admin Login")

    with allure.step("Verify the entry records the username"):
        expect(admin_dashboard_page.audit_row_detail_value(row, "username")).to_have_text(
            valid_admin_login_data.username
        )

    with allure.step("Verify the entry records an IP address"):
        ip_value = admin_dashboard_page.audit_row_detail_value(row, "ip").text_content()
        assert ip_value and ip_value.strip(), "Audit entry should record an IP address"

    with allure.step("Verify the entry records role=superadmin"):
        expect(admin_dashboard_page.audit_row_detail_value(row, "role")).to_have_text("superadmin")


# ---------------------------------------------------------------------------
# TC-173  Agency user credentials rejected on Admin Login form
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-173")
@allure.story("Admin Login")
@allure.title("TC-173: Agency user credentials rejected on Admin Login form")
def test_tc173_agency_creds_rejected_on_admin(
    admin_login_page: AdminLoginPage, agency_creds_on_admin_data: AdminLoginData
):
    """
    Given a valid agency account exists and I am on the Admin Login page
    When  I enter the agency username/password with a valid CAPTCHA and submit
    Then  an error "Invalid username or password." is shown and no admin session is created

    Notion: KAN-TC-173 | data: agency_creds_on_admin
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Submit agency credentials on the Admin Login form"):
        admin_login_page.login(
            agency_creds_on_admin_data.username, agency_creds_on_admin_data.password
        )

    with allure.step("Verify invalid-credentials error is shown"):
        expect(admin_login_page.error_message).to_be_visible()
        assert (
            agency_creds_on_admin_data.expected_error
            in admin_login_page.error_message.text_content()
        )

    with allure.step("Verify no admin session was created (still on the login page)"):
        assert "login.php" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-174  Admin credentials are not accepted on agency login page
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-174")
@allure.story("Admin Login")
@allure.title("TC-174: Admin credentials are not accepted on agency login page")
def test_tc174_admin_creds_rejected_on_agency(
    login_page: LoginPage, admin_creds_for_agency_data: AdminLoginData
):
    """
    Given a valid admin account exists and I am on the agency login page
    When  I enter the admin credentials and click login
    Then  the admin credentials are not accepted by the agency portal

    Notion: KAN-TC-174 | data: admin_creds_on_agency
    """
    with allure.step("Open the agency Login page"):
        login_page.open()

    with allure.step("Submit admin credentials on the agency login form"):
        login_page.login(admin_creds_for_agency_data.username, admin_creds_for_agency_data.password)

    with allure.step("Verify the admin credentials are rejected (error shown, still on login)"):
        expect(login_page.error_message).to_be_visible()
        assert "login.php" in login_page.get_url()


# ---------------------------------------------------------------------------
# TC-175  Expired idle admin session redirects to login with expiry message
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-175")
@allure.story("Admin Login")
@allure.title("TC-175: Expired idle admin session redirects to login with expiry message")
def test_tc175_idle_session_expiry(
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given I am logged in to the admin portal and the session timeout is configured
    When  I remain idle past the configured timeout (e.g. 30 minutes)
    Then  the session expires and I am redirected to the Admin Login page
    And   a message reads "Your session has expired. Please log in again."

    Notion: KAN-TC-175 | data: valid_super_admin
    Note:   The idle wait happens INSIDE the test (after login), so the active
            admin session is what times out.
    """
    # Idle just past the configured session timeout (~30 min).
    IDLE_SECONDS = 1810

    with allure.step("Login and arrive at the admin dashboard"):
        admin_login_page.open()
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)
        expect(admin_dashboard_page.role_badge).to_be_visible()

    with allure.step(f"Remain idle for {IDLE_SECONDS}s to let the session expire"):
        time.sleep(IDLE_SECONDS)

    with allure.step("After the idle period, attempt an interaction to trigger redirect"):
        admin_dashboard_page.open_audit_log()

    with allure.step("Verify redirect to Admin Login with session-expired message"):
        expect(admin_login_page.session_expired_message).to_be_visible()
        assert (
            "session has expired"
            in admin_login_page.session_expired_message.text_content().lower()
        )


# ---------------------------------------------------------------------------
# TC-176  Refresh button invalidates old CAPTCHA and generates a new image
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-176")
@allure.story("Admin Login")
@allure.title("TC-176: Clicking Refresh invalidates old CAPTCHA and generates a new image")
def test_tc176_refresh_invalidates_old_captcha(
    admin_login_page: AdminLoginPage, stale_captcha_data: AdminLoginData
):
    """
    Given I am on the Admin Login page
    When  I note the current CAPTCHA, click Refresh, then submit the OLD CAPTCHA value
    Then  a new CAPTCHA image is displayed, the input is cleared, and the old value is rejected
    And   login fails with "Incorrect CAPTCHA."

    Notion: KAN-TC-176 | data: stale_captcha
    """
    with allure.step("Open the Admin Login page and note the current CAPTCHA"):
        admin_login_page.open()
        old_captcha = admin_login_page.read_captcha_value()

    with allure.step("Click Refresh and verify a new CAPTCHA is generated"):
        new_captcha = admin_login_page.refresh_captcha()
        expect(admin_login_page.captcha_input).to_have_value("")
        assert new_captcha != old_captcha, "Refresh should generate a different CAPTCHA"

    with allure.step("Submit valid credentials with the OLD (stale) CAPTCHA and capture the alert"):
        message = admin_login_page.login_with_captcha_and_handle_alert(
            stale_captcha_data.username, stale_captcha_data.password, old_captcha
        )

    with allure.step("Verify the stale CAPTCHA is rejected"):
        assert "Captcha Incorrect" in message, (
            f"Expected a 'Captcha Incorrect' alert for the stale CAPTCHA, got: {message!r}"
        )


# ---------------------------------------------------------------------------
# TC-177  Blank username triggers "Username is required" error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-177")
@allure.story("Admin Login")
@allure.title("TC-177: Blank username is blocked by native required-field validation")
def test_tc177_blank_username(
    admin_login_page: AdminLoginPage, blank_username_admin_data: AdminLoginData
):
    """
    Given I am on the Admin Login page
    When  I leave the username blank, fill password + CAPTCHA, and click ADMIN LOGIN
    Then  the browser blocks submission with a native required-field validation
          tooltip on the username field, and login does not proceed

    Note: The username field uses HTML5 ``required`` — the browser surfaces a
          native validation tooltip rather than a server-side
          "Username is required." message.

    Notion: KAN-TC-177 | data: blank_username
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Fill password and CAPTCHA, leave username blank, then submit"):
        admin_login_page.fill_password(blank_username_admin_data.password)
        admin_login_page.fill_captcha(admin_login_page.read_captcha_value())
        admin_login_page.admin_login_button.click()

    with allure.step("Verify the username field fails native validation"):
        is_valid = admin_login_page.username_input.evaluate("el => el.checkValidity()")
        assert is_valid is False, "Username should be invalid when left blank"

    with allure.step("Verify a native validation tooltip message is shown for username"):
        validation_message = admin_login_page.username_input.evaluate("el => el.validationMessage")
        assert validation_message, "Browser should surface a non-empty validation tooltip"

    with allure.step("Verify login is blocked — still on the login page"):
        assert "login.php" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-178  Blank password triggers "Password is required" error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-178")
@allure.story("Admin Login")
@allure.title("TC-178: Blank password is blocked by native required-field validation")
def test_tc178_blank_password(
    admin_login_page: AdminLoginPage, blank_password_admin_data: AdminLoginData
):
    """
    Given I am on the Admin Login page
    When  I enter the username, leave password blank, fill CAPTCHA, and submit
    Then  the browser blocks submission with a native required-field validation
          tooltip on the password field, and login does not proceed

    Note: The password field uses HTML5 ``required`` — the browser surfaces a
          native validation tooltip rather than a server-side
          "Password is required." message.

    Notion: KAN-TC-178 | data: blank_password
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Fill username and CAPTCHA, leave password blank, then submit"):
        admin_login_page.fill_username(blank_password_admin_data.username)
        admin_login_page.fill_captcha(admin_login_page.read_captcha_value())
        admin_login_page.admin_login_button.click()

    with allure.step("Verify the password field fails native validation"):
        is_valid = admin_login_page.password_input.evaluate("el => el.checkValidity()")
        assert is_valid is False, "Password should be invalid when left blank"

    with allure.step("Verify a native validation tooltip message is shown for password"):
        validation_message = admin_login_page.password_input.evaluate("el => el.validationMessage")
        assert validation_message, "Browser should surface a non-empty validation tooltip"

    with allure.step("Verify login is blocked — still on the login page"):
        assert "login.php" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-179  Sub-admin account locks after 5 consecutive failed attempts
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-179")
@allure.story("Admin Login")
@allure.title("TC-179: Sub-admin account locks after 5 consecutive failed login attempts")
def test_tc179_subadmin_lockout(
    admin_login_page: AdminLoginPage,
    subadmin_wrong_password_data: AdminLoginData,
    subadmin_correct_data: AdminLoginData,
):
    """
    Given a sub-admin account exists and I am on the Admin Login page
    When  I submit the wrong password 5 consecutive times
    Then  each attempt errors, and after the 5th the account is locked
    And   a subsequent correct-credentials attempt is still blocked

    NOTE: This locks the sub-admin account — use a DEDICATED test account.

    Notion: KAN-TC-179 | data: subadmin_wrong_password / subadmin_correct
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Submit the wrong password 5 times consecutively"):
        for attempt in range(1, 6):
            with allure.step(f"Failed attempt {attempt}/5"):
                admin_login_page.login(
                    subadmin_wrong_password_data.username,
                    subadmin_wrong_password_data.password,
                )

    with allure.step("Verify the account-locked message after the 5th attempt"):
        expect(admin_login_page.account_locked_message).to_be_visible()
        assert "locked" in admin_login_page.account_locked_message.text_content().lower()

    with allure.step("Attempt login with correct sub-admin credentials — still blocked"):
        admin_login_page.login(subadmin_correct_data.username, subadmin_correct_data.password)
        expect(admin_login_page.account_locked_message).to_be_visible()


# ---------------------------------------------------------------------------
# TC-180  Super Admin account never locks regardless of failed attempts
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-180")
@allure.story("Admin Login")
@allure.title("TC-180: Super Admin account does not lock regardless of failed attempts")
def test_tc180_super_admin_never_locks(
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    super_admin_wrong_password_data: AdminLoginData,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given a Super Admin account exists
    When  I attempt login 10 times with the wrong password
    Then  each attempt shows "Invalid username or password." and the account never locks
    And   logging in with the correct credentials then succeeds

    Notion: KAN-TC-180 | data: super_admin_wrong_password / valid_super_admin
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Attempt login 10 times with the wrong password"):
        for attempt in range(1, 11):
            with allure.step(f"Failed attempt {attempt}/10"):
                admin_login_page.login(
                    super_admin_wrong_password_data.username,
                    super_admin_wrong_password_data.password,
                )
                expect(admin_login_page.error_message).to_be_visible()
                assert (
                    super_admin_wrong_password_data.expected_error
                    in admin_login_page.error_message.text_content()
                )

    with allure.step("Verify the account is NOT locked"):
        expect(admin_login_page.account_locked_message).not_to_be_visible()

    with allure.step("Log in with correct Super Admin credentials — succeeds"):
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)
        expect(admin_dashboard_page.role_badge).to_be_visible()


# ---------------------------------------------------------------------------
# TC-181  Admin whose session was killed by Super Admin is redirected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-181")
@allure.story("Admin Login")
@allure.title("TC-181: Admin whose session was killed by Super Admin is redirected on next action")
def test_tc181_killed_session_redirects(
    second_browser,
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    sub_admin_user,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given a sub-admin is logged in and the Super Admin kills that session
    When  the sub-admin next interacts with any page element
    Then  the sub-admin is redirected to the Admin Login page with:
          "Your session was terminated by an administrator."
    And   the kill action is recorded in the audit log

    Notion: KAN-TC-181 | data: sub_admin_user / valid_super_admin
    """
    # ── Sub-admin logs in (primary browser/page) ──
    with allure.step("Sub-admin logs in to the admin portal"):
        admin_login_page.open()
        admin_login_page.login(sub_admin_user.username, sub_admin_user.password)
        expect(admin_dashboard_page.role_badge).to_be_visible()

    # ── Super Admin logs in via an independent second browser ──
    with allure.step("Super Admin logs in via a second browser and kills the sub-admin session"):
        browser_2 = second_browser()
        sa_context = browser_2.new_context()
        sa_page = sa_context.new_page()
        sa_login = AdminLoginPage(sa_page)
        sa_dash = AdminDashboardPage(sa_page)
        sa_login.open()
        sa_login.login(valid_admin_login_data.username, valid_admin_login_data.password)
        sa_dash.open_session_management()
        # Sessions list is paginated — search to surface the sub-admin's row first.
        sa_dash.search_sessions(sub_admin_user.username)
        expect(sa_dash.active_session_row(sub_admin_user.username)).to_be_visible()
        sa_dash.kill_session_for(sub_admin_user.username)

    with allure.step("Verify the kill action is recorded in the audit log (SESSION_KILL)"):
        sa_dash.open_audit_log()
        sa_dash.filter_audit_by_action("SESSION_KILL")
        expect(sa_dash.audit_log_first_row).to_be_visible()

    with allure.step("Sub-admin interacts with a page element and is redirected"):
        admin_dashboard_page.open_audit_log()
        expect(admin_login_page.session_terminated_message).to_be_visible()
        assert (
            "terminated by an administrator"
            in admin_login_page.session_terminated_message.text_content().lower()
        )


# ---------------------------------------------------------------------------
# TC-182  "← Back to Agency Login" redirects to agency portal login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-182")
@allure.story("Admin Login")
@allure.title("TC-182: Clicking '← Back to Agency Login' redirects to agency portal login")
def test_tc182_back_to_agency_login(admin_login_page: AdminLoginPage):
    """
    Given I am on the Admin Login page
    When  I click "← Back to Agency Login"
    Then  I am redirected to the agency-facing login page without error

    Notion: KAN-TC-182
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Verify the back link is displayed"):
        expect(admin_login_page.back_to_agency_login_link).to_be_visible()

    with allure.step("Click '← Back to Agency Login'"):
        admin_login_page.back_to_agency_login_link.click()

    with allure.step("Verify redirect to the agency login page"):
        admin_login_page.page.wait_for_url("**/agency/auth/login.php**", timeout=15000)
        assert "/agency/auth/login.php" in admin_login_page.get_url()
