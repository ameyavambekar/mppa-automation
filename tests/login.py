import allure
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.partA_page import PartAPage
from test_data.login_factory import LoginData


@allure.story("Agency Login")
@allure.title("TC-L01: Successful login with valid credentials from state store")
def test_successful_login(login_page: LoginPage, part_a_page: PartAPage, valid_login_data: LoginData):
    """
    Given an agency user whose credentials are stored in test_state.db
    When  they submit the login form with the correct username, password and CAPTCHA
    Then  Step 1 — Part A loads and the 'Save & Log out' link is visible
    And   they can log out cleanly

    Notion: TC-L01 | data: valid_agency_user
    """
    with allure.step("Open the login page"):
        login_page.open()

    with allure.step(f"Log in as '{valid_login_data.username}'"):
        login_page.login(valid_login_data.username, valid_login_data.password)

    with allure.step("Verify Step 1 — Part A loaded"):
        expect(part_a_page.save_and_logout_link).to_be_visible()

    with allure.step("Log out"):
        part_a_page.save_and_logout()
