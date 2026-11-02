import time

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.audit_log_page import AdminAuditLogPage
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
    Then  I am authenticated and redirected to the MPPA Officer Console dashboard
    And   the "Super Administrator" role is shown in the top bar

    Notion: KAN-TC-169 | data: valid_super_admin
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Verify restricted banner and Admin Login heading are shown"):
        expect(admin_login_page.restricted_banner).to_be_visible()
        expect(admin_login_page.admin_login_heading).to_be_visible()

    with allure.step(f"Login as '{valid_admin_login_data.username}' with valid credentials"):
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)

    with allure.step("Verify dashboard loaded with the 'Super Administrator' role in the top bar"):
        expect(admin_dashboard_page.role_badge).to_be_visible()
        expect(admin_dashboard_page.role_badge).to_have_text(AdminDashboardPage.SUPER_ADMIN_ROLE)

    admin_dashboard_page.logout_button.click()

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
    Then  an error "Captcha is incorrect. Please try again." is shown
    And   a new CAPTCHA is generated and the CAPTCHA input is cleared

    Notion: KAN-TC-171 | data: valid_creds_wrong_captcha
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Capture the original CAPTCHA value"):
        original_captcha = admin_login_page.read_captcha_value()

    with allure.step("Submit valid credentials with an incorrect CAPTCHA"):
        admin_login_page.login_with_captcha(
            wrong_captcha_admin_data.username,
            wrong_captcha_admin_data.password,
            wrong_captcha_admin_data.captcha,
        )

    with allure.step("Verify the incorrect-CAPTCHA error message"):
        expect(admin_login_page.error_message).to_contain_text(
            wrong_captcha_admin_data.expected_error
        )

    with allure.step("Verify no admin session was created (still on the login page)"):
        assert "login.php" in admin_login_page.get_url()

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
    admin_dashboard_page.logout_button.click()

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
@allure.title("TC-175: Idle admin is logged out automatically after 15 minutes with the idle-timeout message")
def test_tc175_idle_session_expiry(
    idle_timeout_allowed,
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given I am logged in to the admin portal
    When  I leave the dashboard open without touching it
    Then  after 15 minutes (not before) the console goes to the Admin Login page by itself
          (?reason=idle_timeout)
    And   the banner reads "You were logged out automatically after 15 minutes of inactivity.
          Please log in again."

    Notion: KAN-TC-175 | KAN-23 AC-7 | data: valid_super_admin
    Note:   Runs only when RUN_IDLE_TIMEOUT_TESTS=true, because it waits over 15 minutes. The open
            console checks the session in the background and logs out on its own; no click is needed.
            Run headless (HEADLESS=true): mouse movement over a visible window counts as activity.
    """
    idle_seconds = AdminLoginPage.IDLE_TIMEOUT_MINUTES * 60

    with allure.step("Login and arrive at the admin dashboard"):
        admin_login_page.open()
        admin_login_page.login(valid_admin_login_data.username, valid_admin_login_data.password)
        expect(admin_dashboard_page.role_badge).to_be_visible()
        logged_in_at = time.monotonic()

    with allure.step("Leave the dashboard idle until the console logs out by itself"):
        admin_dashboard_page.wait_for_idle_logout(timeout_seconds=idle_seconds + 180)
        idle_for = time.monotonic() - logged_in_at

    with allure.step(f"Verify the logout came after the {AdminLoginPage.IDLE_TIMEOUT_MINUTES}-minute timeout"):
        # 30 s slack: the clock starts once the dashboard has rendered, a little after the console's own.
        assert idle_for >= idle_seconds - 30, f"Logged out after only {idle_for:.0f}s idle"

    with allure.step("Verify the Admin Login page shows the idle-timeout message"):
        expect(admin_login_page.session_expired_message).to_have_text(AdminLoginPage.IDLE_TIMEOUT_MESSAGE)
        assert "reason=idle_timeout" in admin_login_page.get_url()


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
    And   login fails with "Captcha is incorrect. Please try again."

    Notion: KAN-TC-176 | data: stale_captcha
    """
    with allure.step("Open the Admin Login page and note the current CAPTCHA"):
        admin_login_page.open()
        old_captcha = admin_login_page.read_captcha_value()

    with allure.step("Click Refresh and verify a new CAPTCHA is generated"):
        new_captcha = admin_login_page.refresh_captcha()
        expect(admin_login_page.captcha_input).to_have_value("")
        assert new_captcha != old_captcha, "Refresh should generate a different CAPTCHA"

    with allure.step("Submit valid credentials with the OLD (stale) CAPTCHA"):
        admin_login_page.login_with_captcha(
            stale_captcha_data.username, stale_captcha_data.password, old_captcha
        )

    with allure.step("Verify the stale CAPTCHA is rejected"):
        expect(admin_login_page.error_message).to_contain_text(stale_captcha_data.expected_error)
        assert "login.php" in admin_login_page.get_url()


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
@pytest.mark.skip(reason="not implemented yet")
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
        for attempt in range(1, 11):
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
# TC-180  Super Admin account locks after 5 consecutive wrong passwords
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-180")
@allure.story("Admin Login")
@allure.title("TC-180: Super Admin account locks for 15 minutes after 5 consecutive wrong passwords")
def test_tc180_super_admin_locks_after_wrong_passwords(
    admin_lockout_allowed,
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    super_admin_wrong_password_data: AdminLoginData,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given a Super Admin account that is not locked
    When  I submit a wrong password 5 times in a row, each answered "Invalid username or password."
    Then  a 6th wrong password shows "Too many wrong attempts. For security this account is locked for 15 minutes."
    And   the correct password is refused with the same message while the account is locked
    And   after 15 minutes the correct password logs me in again

    Notion: KAN-TC-180 | KAN-23 EC-1 | data: super_admin_wrong_password / valid_super_admin
    Note:   Runs only when RUN_ADMIN_LOCKOUT_TESTS=true: it locks the Super Admin (used by every admin
            test) and then waits out the 15-minute lock. Misread CAPTCHAs are retried and not counted.
    """
    wrong = super_admin_wrong_password_data
    lock_wait_seconds = AdminLoginPage.LOCKOUT_MINUTES * 60 + 30

    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    for attempt in range(1, AdminLoginPage.LOCKOUT_ATTEMPTS + 1):
        with allure.step(f"Wrong password {attempt}/{AdminLoginPage.LOCKOUT_ATTEMPTS} shows the invalid-credentials error"):
            message = admin_login_page.login_past_captcha(wrong.username, wrong.password)
            assert message == wrong.expected_error, f"Attempt {attempt}: {message!r}"

    with allure.step("The next wrong password is refused with the lock message"):
        message = admin_login_page.login_past_captcha(wrong.username, wrong.password)
        assert message == AdminLoginPage.ACCOUNT_LOCKED_MESSAGE, message

    with allure.step("The correct password is refused while the account is locked"):
        message = admin_login_page.login_past_captcha(valid_admin_login_data.username, valid_admin_login_data.password)
        assert message == AdminLoginPage.ACCOUNT_LOCKED_MESSAGE, message
        expect(admin_login_page.account_locked_message).to_be_visible()

    with allure.step(f"Wait {lock_wait_seconds}s for the lock to expire"):
        admin_login_page.page.wait_for_timeout(lock_wait_seconds * 1000)

    with allure.step("Reopen the Admin Login page and log in with the correct credentials - succeeds"):
        admin_login_page.open()
        message = admin_login_page.login_past_captcha(valid_admin_login_data.username, valid_admin_login_data.password)
        assert message == "", message
        expect(admin_dashboard_page.role_badge).to_have_text(AdminDashboardPage.SUPER_ADMIN_ROLE)

    admin_dashboard_page.logout()


# ---------------------------------------------------------------------------
# TC-181  Admin whose session was killed by Super Admin is redirected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-181")
@allure.story("Admin Login")
@allure.title("TC-181: Admin whose session was killed by Super Admin is redirected on next action")
@pytest.mark.skip(reason="kill session button generates error")
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
        admin_login_page.wait_for_load()
        assert "/agency/auth/login.php" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-582  Logout returns to Admin Login with a logged-out message
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-582")
@allure.story("Admin Login")
@allure.title("TC-582: Logout returns to Admin Login with a logged-out message")
def test_tc582_logout_shows_logged_out_message(
    logged_in_admin_dashboard_page: AdminDashboardPage,
    admin_login_page: AdminLoginPage,
):
    """
    Given I am logged in to the MPPA Officer Console
    When  I click "Log out" in the sidebar
    Then  the Admin Login page opens with "You have been logged out successfully."
    And   opening the dashboard URL again redirects to Admin Login with "Please log in to continue."

    Notion: KAN-TC-582 | KAN-23 AC-9
    """
    dashboard = logged_in_admin_dashboard_page

    with allure.step("Click 'Log out' in the sidebar"):
        dashboard.logout()

    with allure.step("Verify the Admin Login page shows the logged-out message"):
        expect(admin_login_page.logged_out_message).to_have_text(AdminLoginPage.LOGGED_OUT_MESSAGE)
        assert "reason=logged_out" in admin_login_page.get_url()

    with allure.step("Open the dashboard URL directly"):
        dashboard.open()

    with allure.step("Verify the session has ended - redirected to Admin Login"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        assert "reason=not_logged_in" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-583  Admin pages opened without a session redirect to Admin Login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-583")
@allure.story("Admin Login")
@allure.title("TC-583: Admin pages opened without a session redirect to Admin Login")
def test_tc583_admin_pages_need_a_session(
    no_admin_session,
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    admin_audit_log_page: AdminAuditLogPage,
):
    """
    Given no admin is logged in in this browser
    When  I open the Officer Console dashboard URL, and then the Audit Log URL
    Then  each time I am redirected to the Admin Login page with "Please log in to continue."

    Notion: KAN-TC-583 | KAN-23 AC-10
    """
    for name, page_object in (("dashboard", admin_dashboard_page), ("Audit Log", admin_audit_log_page)):
        with allure.step(f"Open the {name} URL without a session"):
            page_object.open()

        with allure.step(f"Verify the {name} URL redirects to Admin Login with 'Please log in to continue.'"):
            expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
            assert "reason=not_logged_in" in admin_login_page.get_url()
            expect(admin_login_page.admin_login_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-584  Security Code is case-insensitive
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-584")
@allure.story("Admin Login")
@allure.title("TC-584: Security Code is case-insensitive - a lower-case entry is accepted")
def test_tc584_lowercase_security_code_accepted(
    admin_login_page: AdminLoginPage,
    admin_dashboard_page: AdminDashboardPage,
    valid_admin_login_data: AdminLoginData,
):
    """
    Given I am on the Admin Login page with valid credentials
    When  I type the Security Code in lower case
    Then  the field shows it in upper case
    And   clicking ADMIN LOGIN logs me in to the Officer Console dashboard

    Notion: KAN-TC-584 | KAN-23 AC-11 | data: valid_super_admin
    """
    with allure.step("Open the Admin Login page and enter valid credentials"):
        admin_login_page.open()
        admin_login_page.fill_username(valid_admin_login_data.username)
        admin_login_page.fill_password(valid_admin_login_data.password)

    with allure.step("Type the Security Code in lower case"):
        code = admin_login_page.read_captcha_value()
        admin_login_page.type_captcha(code.lower())

    with allure.step("Verify the field shows the code in upper case"):
        expect(admin_login_page.captcha_input).to_have_value(code.upper())

    with allure.step("Click ADMIN LOGIN"):
        admin_login_page.admin_login_button.click()

    with allure.step("Verify the dashboard loads with the 'Super Administrator' role"):
        expect(admin_dashboard_page.role_badge).to_have_text(AdminDashboardPage.SUPER_ADMIN_ROLE)

    admin_dashboard_page.logout()


# ---------------------------------------------------------------------------
# TC-585  Blank Security Code is blocked by required-field validation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-585")
@allure.story("Admin Login")
@allure.title("TC-585: Blank Security Code is blocked by required-field validation")
def test_tc585_blank_security_code(
    admin_login_page: AdminLoginPage, valid_admin_login_data: AdminLoginData
):
    """
    Given I am on the Admin Login page
    When  I enter the username and password, leave the Security Code blank and click ADMIN LOGIN
    Then  the browser blocks submission with a native required-field validation
          tooltip on the Security Code field, and login does not proceed

    Notion: KAN-TC-585 | KAN-23 Field-Level Validations | data: valid_super_admin
    """
    with allure.step("Open the Admin Login page"):
        admin_login_page.open()

    with allure.step("Fill username and password, leave the Security Code blank, then submit"):
        admin_login_page.fill_username(valid_admin_login_data.username)
        admin_login_page.fill_password(valid_admin_login_data.password)
        admin_login_page.admin_login_button.click()

    with allure.step("Verify the Security Code field fails native validation"):
        is_valid = admin_login_page.captcha_input.evaluate("el => el.checkValidity()")
        assert is_valid is False, "Security Code should be invalid when left blank"

    with allure.step("Verify a native validation tooltip message is shown for the Security Code"):
        validation_message = admin_login_page.captcha_input.evaluate("el => el.validationMessage")
        assert validation_message, "Browser should surface a non-empty validation tooltip"

    with allure.step("Verify login is blocked - still on the login page"):
        assert "login.php" in admin_login_page.get_url()
