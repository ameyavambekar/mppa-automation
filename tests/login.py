import allure
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from test_data.login_factory import LoginData


@allure.story("Agency Login")
@allure.title("TC-L01: Successful login with valid credentials from state store")
def test_successful_login(login_page: LoginPage, dashboard_page: DashboardPage, valid_login_data: LoginData):
    """
    Given an agency user whose credentials are stored in test_state.db
    When  they submit the login form with the correct username, password and CAPTCHA
    Then  the dashboard loads and the logout button is visible
    And   they can log out cleanly

    Notion: TC-L01 | data: valid_agency_user
    """
    with allure.step("Open the login page"):
        login_page.open()

    with allure.step(f"Log in as '{valid_login_data.username}'"):
        login_page.login(valid_login_data.username, valid_login_data.password)

    with allure.step("Verify dashboard loaded"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Log out"):
        dashboard_page.logout()


@allure.story("Agency Login")
@allure.title("TC-L02: Login with an incorrect password shows an error message")
def test_invalid_password(login_page: LoginPage, invalid_password_data: LoginData):
    """
    Given a valid username from test_state.db
    When  the user submits the login form with a wrong password
    Then  an error message is displayed on the login page

    Notion: TC-L02 | data: invalid_password
    """
    with allure.step("Open the login page"):
        login_page.open()

    with allure.step(f"Submit login for '{invalid_password_data.username}' with wrong password"):
        login_page.login(invalid_password_data.username, invalid_password_data.password)

    with allure.step("Verify error message is visible"):
        expect(login_page.error_message).to_be_visible()


@allure.story("Agency Login")
@allure.title("TC-L03: Login with a nonexistent username shows an error message")
def test_nonexistent_user(login_page: LoginPage, nonexistent_user_data: LoginData):
    """
    Given a username that has never been registered in the system
    When  the user submits the login form
    Then  an error message is displayed on the login page

    Notion: TC-L03 | data: nonexistent_user
    """
    with allure.step("Open the login page"):
        login_page.open()

    with allure.step(f"Submit login for nonexistent user '{nonexistent_user_data.username}'"):
        login_page.login(nonexistent_user_data.username, nonexistent_user_data.password)

    with allure.step("Verify error message is visible"):
        expect(login_page.error_message).to_be_visible()
