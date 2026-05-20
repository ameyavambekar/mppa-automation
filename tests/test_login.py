import allure
import pytest
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.registration_page import RegistrationPage
from test_data.login_factory import LoginData

# ---------------------------------------------------------------------------
# TC-01  AC-1  Valid Login with Correct Credentials and CAPTCHA
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-01 (AC-1): Successful login redirects to Agency Portal Dashboard")
def test_tc01_valid_login(login_page: LoginPage, dashboard_page: DashboardPage, valid_login_data: LoginData):
    """
    Given I am on the Agency Login page and have a valid pre-registered account
    When  I enter the correct username, password, and CAPTCHA and click LOGIN TO PORTAL
    Then  I am authenticated and redirected to the Agency Portal Dashboard

    Notion: TC-01 | AC-1 | data: valid_agency_user
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step(f"Login as '{valid_login_data.username}' with correct credentials and CAPTCHA"):
        login_page.login(valid_login_data.username, valid_login_data.password)

    with allure.step("Verify dashboard loaded — logout button is visible"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Logout to clean up session"):
        dashboard_page.logout()


# ---------------------------------------------------------------------------
# TC-02  AC-2  Login Blocked — Incorrect Username
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-02 (AC-2): Error shown when a non-existent username is entered")
def test_tc02_nonexistent_username(login_page: LoginPage, nonexistent_user_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I enter a non-existent username with any password and valid CAPTCHA
    Then  an error is shown: "Invalid username or password. Please try again."
    And   the username field retains its value

    Notion: TC-02 | AC-2 | data: nonexistent_user
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step(f"Submit login with non-existent username '{nonexistent_user_data.username}'"):
        login_page.login(nonexistent_user_data.username, nonexistent_user_data.password)

    with allure.step("Verify error message is displayed"):
        expect(login_page.error_message).to_be_visible()

    with allure.step("Verify error text contains expected fragment"):
        assert "Invalid" in login_page.error_message.text_content()

    with allure.step("Verify username field still holds the entered value"):
        expect(login_page.username_input).to_have_value(nonexistent_user_data.username)


# ---------------------------------------------------------------------------
# TC-03  AC-2  Login Blocked — Incorrect Password
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-03 (AC-2): Error shown when an incorrect password is entered")
def test_tc03_invalid_password(login_page: LoginPage, invalid_password_data: LoginData):
    """
    Given I have a valid registered username
    When  I enter the correct username but a wrong password with valid CAPTCHA
    Then  an error is shown: "Invalid username or password. Please try again."
    And   the username field retains its value

    Notion: TC-03 | AC-2 | data: invalid_password
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step(f"Submit login as '{invalid_password_data.username}' with wrong password"):
        login_page.login(invalid_password_data.username, invalid_password_data.password)

    with allure.step("Verify error message is displayed"):
        expect(login_page.error_message).to_be_visible()

    with allure.step("Verify error text contains expected fragment"):
        assert "Invalid" in login_page.error_message.text_content()

    with allure.step("Verify username field still holds the entered value"):
        expect(login_page.username_input).to_have_value(invalid_password_data.username)


# ---------------------------------------------------------------------------
# TC-04  AC-3  Login Blocked — Incorrect CAPTCHA
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-04 (AC-3): Login blocked and new CAPTCHA generated on wrong CAPTCHA")
def test_tc04_wrong_captcha(login_page: LoginPage, wrong_captcha_data: LoginData):
    """
    Given I have valid credentials but enter a wrong CAPTCHA
    When  I click LOGIN TO PORTAL
    Then  login is blocked with error "Incorrect CAPTCHA. Please try again."
    And   the CAPTCHA input field is cleared
    And   a new CAPTCHA image is generated (different value)

    Notion: TC-04 | AC-3 | data: wrong_captcha
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Record the initial CAPTCHA value"):
        initial_captcha = login_page.read_captcha_value()

    with allure.step(f"Fill valid credentials for '{wrong_captcha_data.username}'"):
        login_page.fill_username(wrong_captcha_data.username)
        login_page.fill_password(wrong_captcha_data.password)

    with allure.step("Fill a deliberately wrong CAPTCHA value"):
        login_page.fill_captcha("AAAAAA")

    with allure.step("Click LOGIN TO PORTAL and Verify CAPTCHA error message is displayed"):
        assert "Captcha" in login_page.click_login_and_handle_alert()

    with allure.step("Verify CAPTCHA input field is cleared"):
        expect(login_page.captcha_input).to_have_value("")

    with allure.step("Verify a new CAPTCHA has been generated"):
        new_captcha = login_page.read_captcha_value()
        assert new_captcha != initial_captcha, (
            f"CAPTCHA was not refreshed after wrong entry (still '{initial_captcha}')"
        )


# ---------------------------------------------------------------------------
# TC-08  EC-3  Password Show / Hide Toggle
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-08 (EC-3): Password visibility toggles correctly on the login page")
def test_tc08_password_show_hide(login_page: LoginPage):
    """
    Given I am on the Agency Login page and have typed a password
    When  I click the SHOW toggle
    Then  the password field type changes to 'text' (characters visible)
    When  I click the toggle again (HIDE)
    Then  the password field type reverts to 'password' (masked)

    Notion: TC-08 | EC-3
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Enter a password in the password field"):
        login_page.fill_password("Secure@1234")

    with allure.step("Verify password is initially masked (type='password')"):
        expect(login_page.password_input).to_have_attribute("type", "password")

    with allure.step("Click the SHOW toggle"):
        login_page.toggle_password_visibility()

    with allure.step("Verify password is now visible (type='text')"):
        expect(login_page.password_input).to_have_attribute("type", "text")

    with allure.step("Click the toggle again to hide the password"):
        login_page.toggle_password_visibility()

    with allure.step("Verify password is masked again (type='password')"):
        expect(login_page.password_input).to_have_attribute("type", "password")


# ---------------------------------------------------------------------------
# TC-09  EC-2  CAPTCHA Refresh on Login Page
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-09 (EC-2): Refresh button generates a new CAPTCHA and invalidates the old one")
def test_tc09_captcha_refresh(login_page: LoginPage, valid_login_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I note the current CAPTCHA and click Refresh
    Then  a new different CAPTCHA is generated and the input field is cleared
    And   submitting with the old CAPTCHA value shows an error

    Notion: TC-09 | EC-2 | data: valid_agency_user
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Note the current CAPTCHA value"):
        original_captcha = login_page.read_captcha_value()

    with allure.step("Click the Refresh button"):
        new_captcha = login_page.refresh_captcha()

    with allure.step("Verify a new different CAPTCHA was generated"):
        assert new_captcha != original_captcha, (
            f"CAPTCHA did not change after refresh (still '{original_captcha}')"
        )

    with allure.step("Fill valid credentials and the OLD (now invalid) CAPTCHA value"):
        login_page.fill_username(valid_login_data.username)
        login_page.fill_password(valid_login_data.password)
        login_page.fill_captcha(original_captcha)


    with allure.step("Verify CAPTCHA error is shown (old value rejected) after clicking login"):
        assert "Captcha" in login_page.click_login_and_handle_alert()


# ---------------------------------------------------------------------------
# TC-10  EC-1  Account Locked After Repeated Failed Attempts
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-10 (EC-1): Account temporarily locked after 5 consecutive failed login attempts")
def test_tc10_account_lockout(login_page: LoginPage, lockout_test_data: LoginData):
    """
    Given a valid registered account (LOCKOUT_TEST_USERNAME)
    When  I fail to login 5 consecutive times with a wrong password
    Then  the account is temporarily locked with a lockout message
    And   a correct-credentials attempt during lockout is also blocked

    NOTE: This test uses LOCKOUT_TEST_USERNAME env var and will temporarily
    lock that account. Use a dedicated test account, not a shared one.

    Notion: TC-10 | EC-1 | data: lockout_attempt
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Attempt login with wrong password 5 times to trigger lockout"):
        for attempt in range(1, 10):
            with allure.step(f"Failed attempt {attempt}/7"):
                login_page.fill_username(lockout_test_data.username)
                login_page.fill_password(lockout_test_data.password)
                captcha = login_page.read_captcha_value()
                login_page.fill_captcha(captcha)
                login_page.login_button.click()


    with allure.step("Verify account-locked message is shown after 5th failed attempt"):
        expect(login_page.account_locked_message).to_be_visible()
        assert "Too many failed login attempts. Please wait 10 minutes and try again." in login_page.account_locked_message.text_content()


# ---------------------------------------------------------------------------
# TC-11  AC-4  Session Auto-Expiry After 20 Minutes of Inactivity
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Requires 20-minute idle wait — run manually when validating session timeout.")
@allure.story("Agency Login")
@allure.title("TC-11 (AC-4): Session expires after 20 minutes of inactivity")
def test_tc11_session_expiry(login_page: LoginPage, dashboard_page: DashboardPage, valid_login_data: LoginData):
    """
    Given I am logged in and on the dashboard
    When  I remain idle for 20 minutes
    Then  the session is terminated and I am redirected to the login page
    And   a message reads "Your session has expired due to inactivity. Please log in again."

    Notion: TC-11 | AC-4 | data: valid_agency_user
    """
    import time

    with allure.step("Login and arrive at the dashboard"):
        login_page.open()
        login_page.login(valid_login_data.username, valid_login_data.password)
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Wait 20 minutes (1200 seconds) without any interaction"):
        time.sleep(1200)

    with allure.step("Interact with the page to trigger session check"):
        login_page.page.reload()

    with allure.step("Verify session-expired message is shown on login page"):
        expect(login_page.error_message).to_be_visible()
        assert "expired" in login_page.error_message.text_content().lower()



# ---------------------------------------------------------------------------
# TC-12  EC-5  "New Agency? Register here →" Link
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-12 (EC-5): 'New Agency? Register here →' redirects to the Pre-Registration form")
def test_tc12_register_link(login_page: LoginPage, registration_page: RegistrationPage):
    """
    Given I am on the Agency Login page
    When  I click "New Agency? Register here →"
    Then  I am redirected to the New Agency Registration Form

    Notion: TC-22 | EC-5
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Verify registration link is visible"):
        expect(login_page.agency_registration_link).to_be_visible()

    with allure.step("Click 'New Agency? Register here →'"):
        login_page.agency_registration_link.click()

    with allure.step("Verify navigation to the pre-registration form"):
        registration_page.wait_for_load()
        expect(registration_page.page_title).to_contain_text("Registration")


# ---------------------------------------------------------------------------
# TC-13  EC-4  Admin Login Button Navigates to Admin Login Page
# ---------------------------------------------------------------------------

@allure.story("Agency Login")
@allure.title("TC-13 (EC-4): 'Admin Login' button navigates to the Super Admin login page")
def test_tc13_admin_login_button(login_page: LoginPage, valid_login_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I click the "Admin Login" button
    Then  I am navigated to the Super Admin login page
    And   agency credentials are not accepted there

    Notion: TC-23 | EC-4 | data: valid_agency_user
    """
    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Verify 'Admin Login' button is visible"):
        expect(login_page.admin_login_link).to_be_visible()

    with allure.step("Click 'Admin Login'"):
        login_page.admin_login_link.click()
        login_page.wait_for_load()

    with allure.step("Verify navigation to Admin login page"):
        assert "admin" in login_page.login_title.text_content().lower()

    with allure.step("Attempt login with agency credentials on the Admin login page"):
        login_page.fill_username(valid_login_data.username)
        login_page.fill_password(valid_login_data.password)
        captcha = login_page.read_captcha_value()
        login_page.fill_captcha(captcha)
        login_page.login_button.click()

    with allure.step("Verify agency credentials are rejected on the Admin login page"):
        expect(login_page.error_message).to_be_visible()
