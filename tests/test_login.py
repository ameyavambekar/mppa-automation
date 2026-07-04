import allure
import pytest
from playwright.async_api import async_playwright
from playwright.sync_api import expect, sync_playwright

from conftest import login_page
from pages.dashboard_page import DashboardPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.registration_page import RegistrationPage
from test_data.login_factory import LoginData
from utils.aio import aio_case


# ---------------------------------------------------------------------------
# TC-01  AC-1  Valid Login with Correct Credentials and CAPTCHA
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-29")
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

    with allure.step("Verify dashboard loaded — home link is visible"):
        expect(dashboard_page.home_link).to_be_visible()

    with allure.step("Logout to clean up session"):
        dashboard_page.logout_button.click()
        expect(login_page.login_title).to_be_visible()


# ---------------------------------------------------------------------------
# TC-02  AC-2  Login Blocked — Incorrect Username
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-30")
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
@aio_case("KAN-TC-31")
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
@aio_case("KAN-TC-32")
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
# TC-05  Username Blank on Login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-33")
@allure.story("Agency Login")
@allure.title("TC-05 (KAN-TC-33): Error shown when Username is left blank on login")
def test_tc05_blank_username(login_page: LoginPage, blank_username_login_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I leave the Username field blank but fill a valid password and the correct CAPTCHA
    And   I click LOGIN TO PORTAL
    Then  an error message "Username is required." is shown
    And   login is blocked (no redirect to the dashboard)

    Notion: TC-05 | KAN-TC-33 | data: blank_username_login_data
    """
    data = blank_username_login_data

    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step("Leave the Username field blank"):
        login_page.fill_username("")

    with allure.step(f"Fill a valid password: '{data.password}'"):
        login_page.fill_password(data.password)

    with allure.step("Fill the displayed CAPTCHA exactly as shown"):
        login_page.fill_captcha(login_page.read_captcha_value())

    with allure.step("Click LOGIN TO PORTAL and assert blank-username error appears"):
        login_page.login_button.click()
        expect(login_page.error_message).to_be_visible()

    with allure.step("Verify login is blocked (still on the login page)"):
        expect(login_page.login_title).to_be_visible()


# ---------------------------------------------------------------------------
# TC-06  Password Blank on Login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-34")
@allure.story("Agency Login")
@allure.title("TC-06 (KAN-TC-34): Error shown when Password is left blank on login")
def test_tc06_blank_password(login_page: LoginPage, blank_password_login_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I fill a valid-looking username, leave the password blank, and fill the correct CAPTCHA
    And   I click LOGIN TO PORTAL
    Then  an error message "Password is required." is shown
    And   login is blocked (no redirect to the dashboard)

    Notion: TC-06 | KAN-TC-34 | data: blank_password_login_data
    """
    data = blank_password_login_data

    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step(f"Fill a valid-looking username: '{data.username}'"):
        login_page.fill_username(data.username)

    with allure.step("Leave the Password field blank"):
        login_page.fill_password("")

    with allure.step("Fill the displayed CAPTCHA exactly as shown"):
        login_page.fill_captcha(login_page.read_captcha_value())

    with allure.step("Click LOGIN TO PORTAL and assert blank-password error appears"):
        login_page.login_button.click()
        expect(login_page.error_message).to_be_visible()

    with allure.step("Verify login is blocked (still on the login page)"):
        expect(login_page.login_title).to_be_visible()


# ---------------------------------------------------------------------------
# TC-07  CAPTCHA Blank on Login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-35")
@allure.story("Agency Login")
@allure.title("TC-07 (KAN-TC-35): Error shown when CAPTCHA is left blank on login")
def test_tc07_blank_captcha(login_page: LoginPage, blank_captcha_login_data: LoginData):
    """
    Given I am on the Agency Login page
    When  I fill a valid-looking username and password but leave the CAPTCHA blank
    And   I click LOGIN TO PORTAL
    Then  an error message "Please enter the CAPTCHA." is shown
    And   login is blocked (no redirect to the dashboard)

    Notion: TC-07 | KAN-TC-35 | data: blank_captcha_login_data
    """
    data = blank_captcha_login_data

    with allure.step("Open the Agency Login page"):
        login_page.open()

    with allure.step(f"Fill a valid-looking username: '{data.username}'"):
        login_page.fill_username(data.username)

    with allure.step(f"Fill a valid-looking password: '{data.password}'"):
        login_page.fill_password(data.password)

    with allure.step("Leave the CAPTCHA field blank"):
        login_page.fill_captcha("")

    with allure.step("Click LOGIN TO PORTAL and assert blank-CAPTCHA error appears"):
        error = login_page.click_login_and_handle_alert()
        assert "CAPTCHA" in error.upper(), (
            f"Expected a blank-CAPTCHA validation error, got dialog message: '{error}'"
        )

    with allure.step("Verify login is blocked (still on the login page)"):
        expect(login_page.login_title).to_be_visible()


# ---------------------------------------------------------------------------
# TC-08  EC-3  Password Show / Hide Toggle
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-36")
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
@aio_case("KAN-TC-37")
@allure.story("Agency Login")
@allure.title("TC-09 (EC-2): Refresh button generates a new CAPTCHA and clears the CAPTCHA input")
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
@aio_case("KAN-TC-38")
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

@pytest.mark.wait_before(610)
# ---------------------------------------------------------------------------
# TC-11  AC-4  Session Auto-Expiry After 20 Minutes of Inactivity
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-39")
#@pytest.mark.skip(reason="Requires 20-minute idle wait — run manually when validating session timeout.")
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

    with allure.step("Verify session-expired message is shown on login page"):
        assert login_page.alert_info_logged_out_successfully in login_page.alert_info.text_content()


# ---------------------------------------------------------------------------
# TC-12  AC-5  My Application Status Card Displays Correct Data
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-40")
@allure.story("Home Page")
@allure.title("TC-12 (AC-5): My Application Status card shows Reg ID, status badge, and progress tracker")
def test_tc12_application_status_card(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given I have a submitted application and I am on the Home page
    When  the page loads
    Then  the My Application Status card is visible
    And   it shows the Registration ID, a status badge, and the Form Completion Progress section
    And   the 'Continue Filling Form →' link is present

    Notion: TC-12 | AC-5 | data: agency_with_part_a
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify My Application Status card is visible"):
        expect(home_page.application_status_card).to_be_visible()

    with allure.step("Verify Registration ID is displayed and non-empty"):
        expect(home_page.registration_id_value).to_be_visible()
        assert home_page.registration_id_value.text_content().strip(), \
            "Registration ID value should not be empty"

    with allure.step("Verify application status badge is present"):
        expect(home_page.application_status_badge).to_be_visible()

    with allure.step("Verify 'Continue Filling Form →' link is present"):
        expect(home_page.continue_filling_form_link).to_be_visible()
    home_page.logout()


# ---------------------------------------------------------------------------
# TC-13  AC-6  Progress Tracker Shows Correct Completion State
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-41")
@allure.story("Home Page")
@allure.title("TC-13 (AC-6): Form Completion Progress shows percentage and 8 part steps")
def test_tc13_progress_tracker(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given I have completed Part A only of the 8-step wizard
    When  I view the Home page
    Then  the Form Completion Progress section is visible with a percentage
    And   all 8 part steps are present: Part A, Part B, Part C, Part E, Part F, Docs, Decl., Auth.

    Notion: TC-13 | AC-6 | data: agency_with_part_a
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify Form Completion Progress section is visible"):
        expect(home_page.form_completion_progress_label).to_be_visible()

    with allure.step("Verify completion percentage is displayed"):
        expect(home_page.form_completion_percentage).to_be_visible()
        pct_text = home_page.form_completion_percentage.text_content()
        assert "%" in pct_text, f"Expected a percentage symbol in '{pct_text}'"

    with allure.step("Verify all 8 part steps are present"):
        for part_label in ["Part A", "Part B", "Part C", "Part E", "Part F", "Docs", "Decl.", "Auth."]:
            with allure.step(f"Verify '{part_label}' step tile is visible"):
                expect(home_page.part_step(part_label)).to_be_visible()

    home_page.logout()


# ---------------------------------------------------------------------------
# TC-14  EC-9  "Continue Filling Form" Link Navigates to Registration Form
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-42")
@allure.story("Home Page")
@allure.title("TC-14 (EC-9): 'Continue Filling Form →' navigates to the 8-step registration form")
def test_tc14_continue_filling_form_link(fresh_agency_user_home_page, home_page: HomePage,dashboard_page: DashboardPage):
    """
    Given I have a submitted application and I am on the Home page
    When  I click 'Continue Filling Form →' on the My Application Status card
    Then  I am navigated to the 8-step registration form

    Notion: TC-14 | EC-9 | data: agency_with_part_a
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify 'Continue Filling Form →' link is visible"):
        expect(home_page.continue_filling_form_link).to_be_visible()

    with allure.step("Click 'Continue Filling Form →'"):
        home_page.click_continue_filling_form()
        dashboard_page.wait_for_load()

    with allure.step("Verify navigation to the registration form (URL contains 'dashboard')"):
        assert "dashboard" in dashboard_page.get_url().lower(), \
            f"Expected to land on the application dashboard, got: {dashboard_page.get_url()}"
    dashboard_page.logout_button.click()

# ---------------------------------------------------------------------------
# TC-15  EC-9  "View Full Application" Link Navigates to Read-Only View
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-43")
@allure.story("Portal Dashboard")
@allure.title("TC-15 (EC-9): 'View Full Application →' opens a read-only view of the submitted application")
def test_tc15_view_full_application(agency_user_with_submitted_form, dashboard_page: DashboardPage,home_page:HomePage):
    """
    Given I have a submitted application and am on the dashboard
    When  I click "View Full Application →" on the My Application Status card
    Then  I am navigated to a read-only view of all 8 wizard steps

    Notion: TC-14 | EC-9 | data: agency_user_with_part_a
    """
    page = agency_user_with_submitted_form

    with allure.step("Verify 'View Full Application →' link is visible"):
        expect(home_page.view_full_application).to_be_visible()

    with allure.step("Click 'View Full Application →'"):
        home_page.click_view_full_application()
        dashboard_page.wait_for_load()

    with allure.step("Verify navigation to a read-only view of all 8 wizard steps"):
        expect(dashboard_page.submitted_application_read_only_preview).to_be_visible()
    dashboard_page.logout_button.click()


# ---------------------------------------------------------------------------
# TC-16  EC-9  Login page displays all static UI elements correctly
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-44")
@allure.story("Portal Dashboard")
@allure.title("TC-16 Login page displays all static UI elements correctly")
def test_tc16_login_ui_elements(login_page:LoginPage):
    """
    Given I am a registered Agency User
    When  I land on Login Page
    Then  I am able to view static UI elements
    """
    login_page.open()

    with allure.step("Verify Important Instructions panel is visible"):
        expect(login_page.instructions_text).to_be_visible()

    with allure.step("Verify Security Notice panel is visible"):
        expect(login_page.security_notice_text).to_be_visible()

    with allure.step("Verify footer text is visible"):
        expect(login_page.footer_text).to_be_visible()

# ---------------------------------------------------------------------------
# TC-17  "TRACK NOW →" on the Track Application card opens the Track Application Status pop-up
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-45")
@allure.story("Track Application Status")
@allure.title("TC-17 TRACK NOW → on the Track Application card opens the Track Application Status modal")
def test_tc17_track_application_status(fresh_agency_user_home_page,home_page:HomePage):
    """
    Given I am a registered Agency User
    When  I land on Home Page
    Then  I am able to Track application Status
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Track Application card is visible"):
        expect(home_page.track_application_card).to_be_visible()

    with allure.step("Click on Track Now ->"):
        home_page.click_track_now()

    with allure.step("Modal pop-up appears"):
        expect(home_page.track_application_modal).to_be_visible()

    with allure.step("Modal pop-up appears"):
        expect(home_page.track_application_modal).to_be_visible()

    with allure.step("Enter Registration ID"):
        home_page.enter_registration_id(user.registration_id)

    with allure.step("Click Track button"):
        home_page.track_application_button.click()
        home_page.track_application_close_button.click()
        home_page.logout()

# ---------------------------------------------------------------------------
# TC-18  AC-7  Notice Board Displays Active Notices
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-46")
@allure.story("Home Page")
@allure.title("TC-18 (AC-7): Notice Board shows active notices with type badges and a 'View all' link")
def test_tc18_notice_board(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given active government notices exist in the system
    And   I am on the dashboard
    When  the page loads
    Then  the Notice Board shows notices with type badges (NEW/ALERT/INFO/URGENT)
    And   a 'View all notices →' link is present

    Notion: TC-17 | AC-7 | data: any logged-in agency user
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify Notice Board section is visible"):
        expect(home_page.notice_board_section).to_be_visible()

    with allure.step("Verify at least one notice item is displayed"):
        expect(home_page.notice_items.first).to_be_visible()

    with allure.step("Verify notice type badges are present (NEW / ALERT / INFO / URGENT)"):
        expect(home_page.notice_type_badges.first).to_be_visible()

    with allure.step("Verify 'View all notices →' link is present"):
        expect(home_page.view_all_notices_link).to_be_visible()
    home_page.logout()

# ---------------------------------------------------------------------------
# TC-19  EC-10  Notice Board Shows Placeholder When No Notices Exist
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-47")
@pytest.mark.skip(reason="Requires Super Admin to unpublish all notices first — run in a controlled environment.")
@allure.story("Portal Dashboard")
@allure.title("TC-19 (EC-10): Notice Board shows placeholder when no active notices are published")
def test_tc19_notice_board_empty(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given no active notices are published by the Super Admin
    And   I am on the dashboard
    When  the page loads
    Then  the Notice Board shows: "No notices available at this time."
    And   no broken or empty rows are rendered

    Notion: TC-18 | EC-10 | pre-condition: Super Admin must unpublish all notices
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify Notice Board section is visible"):
        expect(home_page.notice_board_section).to_be_visible()

    with allure.step("Verify placeholder message is shown"):
        expect(home_page.no_notices_placeholder).to_be_visible()
        assert "No notices available" in home_page.no_notices_placeholder.text_content()

    with allure.step("Verify no notice items are rendered"):
        assert home_page.notice_items.count() == 0, "No notice items should be rendered"


# ---------------------------------------------------------------------------
# TC-20  AC-8  Quick Links Are Functional
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-48")
@allure.story("Home Page")
@allure.title("TC-20 (AC-8): All Quick Links navigate to their respective pages without breaking session")
def test_tc20_quick_links(fresh_agency_user_home_page, home_page: HomePage, page):
    """
    Given I am on the Home page
    When  I click each Quick Link in the right sidebar
    Then  I am navigated to the respective destination page
    And   the authenticated session is maintained throughout

    Notion: TC-19 | AC-8 | data: any logged-in agency user
    """
    page, user = fresh_agency_user_home_page

    # Quick Links visible in the screenshot (right sidebar)
    quick_links_to_test = [
        "Document Checklist",
        "User Manual (PDF)",
        "Frequently Asked Questions",
        "Contact Helpdesk",
        "Continue My Application",
        "Admin Login"
    ]

    with allure.step("Verify Quick Links section is visible"):
        expect(home_page.quick_links_section).to_be_visible()

    for link_text in quick_links_to_test:
        with allure.step(f"Click Quick Link: '{link_text}'"):
            expect(home_page.quick_link(link_text)).to_be_visible()
            home_page.click_quick_link(link_text)
            page.wait_for_load_state("networkidle")

        with allure.step(f"Verify navigation occurred for '{link_text}'"):
            assert page.url.strip(), "Page URL should be non-empty after navigation"

        with allure.step("Navigate back to the Home page"):
            page.go_back()
            page.wait_for_load_state("networkidle")

    with allure.step("Verify session is still active — logout button is visible"):
        expect(home_page.logout_button).to_be_visible()

    home_page.logout()

# ---------------------------------------------------------------------------
# TC-21  AC-9  Rejected Applicant Can Log In and View Remarks
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-49")
@allure.story("Portal Home")
@allure.title("TC-21 (AC-9): Rejected applicant logs in and sees rejection status, remarks, and appeal option")
def test_tc21_rejected_applicant(rejected_agency_user_page, home_page: HomePage):
    """
    Given an agency account whose application was rejected
    When  they log in
    Then  the dashboard shows a REJECTED status badge
    And   a link/option to view rejection remarks is visible
    And   an appeal option (Form-III) is visible

    Notion: TC-20 | AC-9 | data: rejected_agency_user (REJECTED_AGENCY_USERNAME env var)
    """
    rejected_agency_user_page

    with allure.step("Verify login succeeded — logout button is visible"):
        expect(home_page.logout_button).to_be_visible()

    with allure.step("Verify application status badge shows REJECTED"):
        expect(home_page.application_status_badge).to_be_visible()
        badge_text = home_page.application_status_badge.text_content().upper()
        assert "REJECTED" in badge_text, f"Expected REJECTED badge, got: '{badge_text}'"

    #with allure.step("Verify rejection remarks option is accessible"):

    with allure.step("Verify appeal option (Form-III) is visible"):
        expect(home_page.submit_appeal_card).to_be_visible()
    home_page.logout()

# ---------------------------------------------------------------------------
# TC-22  EC-5  "New Agency? Register here →" Link
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-51")
@allure.story("Agency Login")
@allure.title("TC-22 (EC-5): 'New Agency? Register here →' redirects to the Pre-Registration form")
def test_tc22_register_link(login_page: LoginPage, registration_page: RegistrationPage):
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
# TC-23  EC-4  Admin Login Button Navigates to Admin Login Page
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-52")
@allure.story("Agency Login")
@allure.title("TC-23 (EC-4): 'Admin Login' button navigates to the Super Admin login page")
def test_tc23_admin_login_button(login_page: LoginPage, valid_login_data: LoginData):
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

# ---------------------------------------------------------------------------
# TC-24  EC-7  Browser Back Does Not Return to Login While Session Is Active
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-53")
@allure.story("Home Page")
@allure.title("TC-24 (EC-7): Browser back button does not return user to login page while session is active")
def test_tc24_browser_back(fresh_agency_user_home_page, home_page: HomePage, page):
    """
    Given I am logged in and on the Home page
    When  I press the browser back button
    Then  I am NOT navigated back to the login page
    And   the Home page / authenticated area remains active

    Notion: TC-25 | EC-7 | data: any logged-in agency user
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify Home page is loaded — logout button is visible"):
        expect(home_page.logout_button).to_be_visible()

    with allure.step("Press the browser back button"):
        page.go_back()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify user is NOT redirected to the login page"):
        assert "login" not in page.url.lower(), \
            f"Browser back should not navigate to the login page, but URL is: {page.url}"

    with allure.step("Verify authenticated session is still intact"):
        expect(home_page.logout_button).to_be_visible()
    home_page.logout()

# ---------------------------------------------------------------------------
# TC-26  EC-8  Double Login from Two Browsers / Tabs
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-54")
@allure.story("Portal Dashboard")
@allure.title("TC-25 (EC-8): System handles concurrent sessions from two separate browsers")
def test_tc25_double_login(logged_in_agency_page, dashboard_page, second_browser):
    page_1, user = logged_in_agency_page

    with allure.step("Verify Browser 1 is logged in"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Open a second independent browser and login with the same credentials"):
        browser_2 = second_browser()
        ctx_2 = browser_2.new_context(viewport={"width": 1280, "height": 800})
        page_2 = ctx_2.new_page()

        login_2 = LoginPage(page_2)
        login_2.open()
        login_2.login(user.username, user.password)
        page_2.wait_for_load_state("networkidle")

        with allure.step("Verify second session reached dashboard or shows a session-conflict message"):
            on_dashboard = "dashboard" in page_2.url.lower()
            conflict_msg = page_2.locator(
                "//div[contains(text(),'logged out') or contains(text(),'new session')]"
            )
            assert on_dashboard or conflict_msg.count() > 0, (
                "Second login should either land on dashboard (concurrent sessions) "
                "or show a session-conflict notification"
            )
        dashboard_page2 = DashboardPage(page_2)


    with allure.step("Check Browser 1 state — either still active or notified of displacement"):
        page_1.reload()
        page_1.wait_for_load_state("networkidle")
        still_on_dashboard = "dashboard" in page_1.url.lower()
        displaced_msg = page_1.locator(
            "//div[contains(text(),'logged out') or contains(text(),'new session')]"
        )
        assert still_on_dashboard or displaced_msg.count() > 0, (
            "Browser 1 should either remain on dashboard (concurrent sessions) "
            "or show a session-displacement notification"
        )
        dashboard_page.logout_button.click()
        dashboard_page2.logout_button.click()




# ---------------------------------------------------------------------------
# TC-26  EC-6  Dashboard — No Application Started Yet Shows Progress 0%
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-56")
@allure.story("Portal Dashboard")
@allure.title("TC-26 (EC-6): Dashboard — No Application Started Yet Shows Progress 0%")
def test_tc26_no_application_started(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given I completed pre-registration but have NOT started the 8-step wizard
    When  I log in and view the dashboard
    Then  the My Application Status card shows: "You have not yet submitted your application."
    And   no progress tracker or submission date is shown

    Notion: TC-24 | EC-6 | data: fresh_agency_user (no form_applications rows)
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify Form Completion Progress is at 0%"):
        expect(home_page.form_completion_percentage).to_be_visible()
        completion_percent_text = home_page.form_completion_percentage.text_content()
        assert "0%" in completion_percent_text.lower(), (
            f"Expected 0%, got: '{completion_percent_text}'"
        )
    home_page.logout()




