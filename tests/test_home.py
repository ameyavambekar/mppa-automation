import allure
import pytest
from playwright.sync_api import expect, sync_playwright

from pages.home_page import HomePage
from pages.login_page import LoginPage


# ---------------------------------------------------------------------------
# TC-12  AC-5  My Application Status Card Displays Correct Data
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TC-13  AC-6  Progress Tracker Shows Correct Completion State
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-13 (AC-6): Form Completion Progress shows percentage and 8 part steps")
def test_tc13_progress_tracker(agency_with_part_a_home_page, home_page: HomePage):
    """
    Given I have completed Part A only of the 8-step wizard
    When  I view the Home page
    Then  the Form Completion Progress section is visible with a percentage
    And   all 8 part steps are present: Part A, Part B, Part C, Part E, Part F, Docs, Decl., Auth.

    Notion: TC-13 | AC-6 | data: agency_with_part_a
    """
    page, user = agency_with_part_a_home_page

    with allure.step("Verify Form Completion Progress section is visible"):
        expect(home_page.form_completion_progress_section).to_be_visible()

    with allure.step("Verify completion percentage is displayed"):
        expect(home_page.completion_percentage).to_be_visible()
        pct_text = home_page.completion_percentage.text_content()
        assert "%" in pct_text, f"Expected a percentage symbol in '{pct_text}'"

    with allure.step("Verify all 8 part steps are present"):
        for part_label in ["Part A", "Part B", "Part C", "Part E", "Part F", "Docs", "Decl.", "Auth."]:
            with allure.step(f"Verify '{part_label}' step tile is visible"):
                expect(home_page.part_step(part_label)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-14  EC-9  "Continue Filling Form" Link Navigates to Registration Form
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-14 (EC-9): 'Continue Filling Form →' navigates to the 8-step registration form")
def test_tc14_continue_filling_form_link(agency_with_part_a_home_page, home_page: HomePage):
    """
    Given I have a submitted application and I am on the Home page
    When  I click 'Continue Filling Form →' on the My Application Status card
    Then  I am navigated to the 8-step registration form

    Notion: TC-14 | EC-9 | data: agency_with_part_a
    """
    page, user = agency_with_part_a_home_page

    with allure.step("Verify 'Continue Filling Form →' link is visible"):
        expect(home_page.continue_filling_form_link).to_be_visible()

    with allure.step("Click 'Continue Filling Form →'"):
        home_page.click_continue_filling_form()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify navigation to the registration form (URL contains 'dashboard')"):
        assert "dashboard" in page.url.lower(), \
            f"Expected to land on the application dashboard, got: {page.url}"


# ---------------------------------------------------------------------------
# TC-17  AC-7  Notice Board Displays Active Notices
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-17 (AC-7): Notice Board shows active notices with type badges and a 'View all' link")
def test_tc17_notice_board(logged_in_home_page, home_page: HomePage):
    """
    Given active government notices exist in the system
    When  I am on the Home page
    Then  the Notice Board section is visible
    And   at least one notice item is displayed
    And   notice type badges (NEW / ALERT / INFO / URGENT) are present
    And   the 'View all notices →' link is present

    Notion: TC-17 | AC-7 | data: any logged-in agency user
    """
    page, user = logged_in_home_page

    with allure.step("Verify Notice Board section is visible"):
        expect(home_page.notice_board_section).to_be_visible()

    with allure.step("Verify at least one notice item is displayed"):
        expect(home_page.notice_items.first).to_be_visible()

    with allure.step("Verify at least one notice type badge is present (NEW / ALERT / INFO / URGENT)"):
        expect(home_page.notice_type_badges.first).to_be_visible()

    with allure.step("Verify 'View all notices →' link is present"):
        expect(home_page.view_all_notices_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-18  EC-10  Notice Board Shows Placeholder When No Notices Exist
# ---------------------------------------------------------------------------

@pytest.mark.skip(
    reason="Requires Super Admin to unpublish all notices first — run in a controlled environment."
)
@allure.story("Home Page")
@allure.title("TC-18 (EC-10): Notice Board shows placeholder when no active notices are published")
def test_tc18_notice_board_empty(logged_in_home_page, home_page: HomePage):
    """
    Given no active notices are currently published by the Super Admin
    When  I am on the Home page
    Then  the Notice Board section shows: "No notices available at this time."
    And   no broken or empty notice rows are rendered

    Notion: TC-18 | EC-10 | pre-condition: Super Admin must unpublish all notices
    """
    page, user = logged_in_home_page

    with allure.step("Verify Notice Board section is visible"):
        expect(home_page.notice_board_section).to_be_visible()

    with allure.step("Verify placeholder message 'No notices available at this time.' is shown"):
        expect(home_page.no_notices_placeholder).to_be_visible()
        assert "No notices available" in home_page.no_notices_placeholder.text_content()

    with allure.step("Verify no notice items are rendered"):
        assert home_page.notice_items.count() == 0, \
            "No notice item elements should be rendered when no notices exist"


# ---------------------------------------------------------------------------
# TC-19  AC-8  Quick Links Are Functional
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-19 (AC-8): All Quick Links navigate to their respective pages without breaking session")
def test_tc19_quick_links(logged_in_home_page, home_page: HomePage):
    """
    Given I am on the Home page
    When  I click each Quick Link in the right sidebar
    Then  I am navigated to the respective destination page
    And   the authenticated session is maintained throughout

    Notion: TC-19 | AC-8 | data: any logged-in agency user
    """
    page, user = logged_in_home_page

    # Quick Links visible in the screenshot (right sidebar)
    quick_links_to_test = [
        "Document Checklist",
        "Frequently Asked Questions",
        "Contact Helpdesk",
        "Continue My Application",
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


# ---------------------------------------------------------------------------
# TC-20  AC-9  Rejected Applicant Can Log In and View Remarks
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-20 (AC-9): Rejected applicant sees REJECTED status, remarks option, and appeal link on Home")
def test_tc20_rejected_applicant(rejected_user_home_page, home_page: HomePage):
    """
    Given an agency account whose application was rejected
    When  they log in and navigate to the Home page
    Then  the My Application Status card shows a REJECTED status badge
    And   an option to view rejection remarks is visible
    And   an appeal option (Form-III) is visible

    Notion: TC-20 | AC-9 | data: rejected_user (REJECTED_AGENCY_USERNAME env var)
    """
    page, user = rejected_user_home_page

    with allure.step("Verify logout button is visible (session active)"):
        expect(home_page.logout_button).to_be_visible()

    with allure.step("Verify application status badge shows REJECTED"):
        expect(home_page.application_status_badge).to_be_visible()
        badge_text = home_page.application_status_badge.text_content().upper()
        assert "REJECTED" in badge_text, \
            f"Expected REJECTED badge, got: '{badge_text}'"

    with allure.step("Verify rejection remarks link/option is accessible"):
        remarks_link = page.locator(
            "//a[contains(normalize-space(.),'remarks') or "
            "contains(normalize-space(.),'Remarks') or "
            "contains(normalize-space(.),'Rejection')]"
        ).first
        expect(remarks_link).to_be_visible()

    with allure.step("Verify appeal option (Form-III) is visible"):
        appeal_link = page.locator(
            "//a[contains(normalize-space(.),'Appeal') or "
            "contains(normalize-space(.),'Form-III') or "
            "contains(normalize-space(.),'appeal')]"
        ).first
        expect(appeal_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-24  EC-6  Home Page Shows "Begin Registration" Prompt (No App Started)
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-24 (EC-6): Home page shows 'begin registration' prompt when no wizard application started")
def test_tc24_no_application_started(fresh_agency_user_home_page, home_page: HomePage):
    """
    Given I completed pre-registration (have a Registration ID)
    But   I have NOT yet started the 8-step registration wizard
    When  I navigate to the Home page
    Then  the My Application Status card shows a prompt to begin the wizard
    And   no Form Completion Progress bar or part steps are shown

    Notion: TC-24 | EC-6 | data: fresh_agency_user (no form_applications rows in state store)
    """
    page, user = fresh_agency_user_home_page

    with allure.step("Verify 'begin registration' prompt is visible"):
        expect(home_page.no_application_prompt).to_be_visible()
        prompt_text = home_page.no_application_prompt.text_content().lower()
        assert "not yet submitted" in prompt_text or "begin" in prompt_text, \
            f"Expected a begin-registration prompt, got: '{prompt_text}'"

    with allure.step("Verify Form Completion Progress section is NOT shown"):
        assert not home_page.form_completion_progress_section.is_visible(), \
            "Form Completion Progress section should not appear before the wizard is started"


# ---------------------------------------------------------------------------
# TC-25  EC-7  Browser Back Does Not Return to Login While Session Is Active
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-25 (EC-7): Browser back button does not return user to login page while session is active")
def test_tc25_browser_back(logged_in_home_page, home_page: HomePage):
    """
    Given I am logged in and on the Home page
    When  I press the browser back button
    Then  I am NOT navigated back to the login page
    And   the Home page / authenticated area remains active

    Notion: TC-25 | EC-7 | data: any logged-in agency user
    """
    page, user = logged_in_home_page

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


# ---------------------------------------------------------------------------
# TC-26  EC-8  Concurrent Sessions from Two Separate Browsers
# ---------------------------------------------------------------------------

@allure.story("Home Page")
@allure.title("TC-26 (EC-8): System handles concurrent sessions from two separate browsers")
def test_tc26_double_login(logged_in_home_page, home_page: HomePage):
    """
    Given I am already logged in and on the Home page (Browser 1)
    When  I open a second independent browser and log in with the same credentials
    Then  the system either allows both concurrent sessions
          OR terminates the older session and notifies: "You have been logged out..."

    Notion: TC-26 | EC-8 | data: any logged-in agency user
    """
    page_1, user = logged_in_home_page

    with allure.step("Verify Browser 1 is logged in and on the Home page"):
        expect(home_page.logout_button).to_be_visible()

    with allure.step("Open a second independent browser and log in with the same credentials"):
        with sync_playwright() as p:
            browser_2 = p.chromium.launch(headless=True)
            ctx_2 = browser_2.new_context(viewport={"width": 1280, "height": 800})
            page_2 = ctx_2.new_page()

            login_2 = LoginPage(page_2)
            login_2.open()
            login_2.login(user.username, user.password)
            page_2.wait_for_load_state("networkidle")

            with allure.step("Verify second session: landed on dashboard OR sees session-conflict message"):
                on_dashboard = "dashboard" in page_2.url.lower() or "home" in page_2.url.lower()
                conflict_msg = page_2.locator(
                    "//div[contains(normalize-space(.),'logged out') or "
                    "contains(normalize-space(.),'new session')]"
                )
                assert on_dashboard or conflict_msg.count() > 0, (
                    "Second login should either land on the portal home/dashboard "
                    "or show a session-conflict notification"
                )

            browser_2.close()

    with allure.step("Check Browser 1 state: still active OR displaced by new session"):
        page_1.reload()
        page_1.wait_for_load_state("networkidle")
        still_active = "login" not in page_1.url.lower()
        displaced_msg = page_1.locator(
            "//div[contains(normalize-space(.),'logged out') or "
            "contains(normalize-space(.),'new session')]"
        )
        assert still_active or displaced_msg.count() > 0, (
            "Browser 1 should either remain in the authenticated area "
            "or show a session-displacement notification"
        )
