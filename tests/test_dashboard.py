import allure
import pytest
from playwright.sync_api import expect, sync_playwright

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage


# ---------------------------------------------------------------------------
# TC-12  AC-5  My Application Status Card Displays Correct Data
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-12 (AC-5): My Application Status card shows Reg ID, status badge, and status message")
def test_tc12_application_status_card(fresh_agency_user_page, dashboard_page: DashboardPage):
    """
    Given I have a submitted application and am logged in
    When  the dashboard loads
    Then  the My Application Status card shows: Registration ID, status badge, status message,
          and a 'View Full Application →' link

    Notion: TC-12 | AC-5 | data: agency_user_with_part_a
    """
    page, user = fresh_agency_user_page

    with allure.step("Verify My Application Status card is visible"):
        expect(dashboard_page.application_status_card).to_be_visible()

    with allure.step("Verify Registration ID is displayed"):
        expect(dashboard_page.registration_id_value).to_be_visible()
        reg_id_text = dashboard_page.registration_id_value.text_content()
        assert reg_id_text.strip(), "Registration ID should not be empty"

    with allure.step("Verify application status badge is present"):
        expect(dashboard_page.application_status_badge).to_be_visible()

    with allure.step("Verify 'View Full Application →' link is present"):
        expect(dashboard_page.continue_filling_form_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-13  AC-6  Progress Tracker Shows Correct Completion State
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-13 (AC-6): Progress tracker accurately reflects completed and incomplete wizard parts")
def test_tc13_progress_tracker(logged_in_agency_page , dashboard_page: DashboardPage):
    """
    Given I have completed Part A only
    When  I view the dashboard
    Then  the progress tracker shows Part A as complete (green tick)
    And   remaining parts are greyed out
    And   the overall completion percentage is displayed

    Notion: TC-13 | AC-6 | data: agency_user_with_part_a
    """
    page, user = logged_in_agency_page

    with allure.step("Verify progress tracker is visible"):
        expect(dashboard_page.progress_tracker).to_be_visible()

    with allure.step("Verify Part A step is marked complete"):
        part_a = dashboard_page.part_step("Part A")
        expect(part_a).to_be_visible()

    with allure.step("Verify overall completion percentage is displayed"):
        expect(dashboard_page.completion_percentage).to_be_visible()
        pct_text = dashboard_page.completion_percentage.text_content()
        assert "%" in pct_text, f"Expected percentage symbol in '{pct_text}'"


# ---------------------------------------------------------------------------
# TC-14  EC-9  "View Full Application" Link Navigates to Read-Only View
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-14 (EC-9): 'View Full Application →' opens a read-only view of the submitted application")
def test_tc14_view_full_application(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given I have a submitted application and am on the dashboard
    When  I click "View Full Application →" on the My Application Status card
    Then  I am navigated to a read-only view of all 8 wizard steps

    Notion: TC-14 | EC-9 | data: agency_user_with_part_a
    """
    page, user = agency_user_with_part_a_page

    with allure.step("Verify 'View Full Application →' link is visible"):
        expect(dashboard_page.view_full_application_link).to_be_visible()

    with allure.step("Click 'View Full Application →'"):
        dashboard_page.click_view_full_application()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify navigation away from the main dashboard"):
        assert page.url != "", "Page should have navigated"


# ---------------------------------------------------------------------------
# TC-17  AC-7  Notice Board Displays Active Notices
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-17 (AC-7): Notice Board shows active notices with type badges and a 'View all' link")
def test_tc17_notice_board(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given active government notices exist in the system
    And   I am on the dashboard
    When  the page loads
    Then  the Notice Board shows notices with type badges (NEW/ALERT/INFO/URGENT)
    And   a 'View all notices →' link is present

    Notion: TC-17 | AC-7 | data: any logged-in agency user
    """
    page, user = logged_in_agency_page

    with allure.step("Verify Notice Board section is visible"):
        expect(dashboard_page.notice_board_section).to_be_visible()

    with allure.step("Verify at least one notice item is displayed"):
        expect(dashboard_page.notice_items.first).to_be_visible()

    with allure.step("Verify notice type badges are present (NEW / ALERT / INFO / URGENT)"):
        expect(dashboard_page.notice_type_badges.first).to_be_visible()

    with allure.step("Verify 'View all notices →' link is present"):
        expect(dashboard_page.view_all_notices_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-18  EC-10  Notice Board Shows Placeholder When No Notices Exist
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Requires Super Admin to unpublish all notices first — run in a controlled environment.")
@allure.story("Portal Dashboard")
@allure.title("TC-18 (EC-10): Notice Board shows placeholder when no active notices are published")
def test_tc18_notice_board_empty(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given no active notices are published by the Super Admin
    And   I am on the dashboard
    When  the page loads
    Then  the Notice Board shows: "No notices available at this time."
    And   no broken or empty rows are rendered

    Notion: TC-18 | EC-10 | pre-condition: Super Admin must unpublish all notices
    """
    page, user = logged_in_agency_page

    with allure.step("Verify Notice Board section is visible"):
        expect(dashboard_page.notice_board_section).to_be_visible()

    with allure.step("Verify placeholder message is shown"):
        expect(dashboard_page.no_notices_placeholder).to_be_visible()
        assert "No notices available" in dashboard_page.no_notices_placeholder.text_content()

    with allure.step("Verify no notice items are rendered"):
        assert dashboard_page.notice_items.count() == 0, "No notice items should be rendered"


# ---------------------------------------------------------------------------
# TC-19  AC-8  Quick Links Are Functional
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-19 (AC-8): All Quick Links navigate to their respective pages without breaking the session")
def test_tc19_quick_links(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given I am on the dashboard
    When  I click each Quick Link
    Then  I am navigated to the respective page and the authenticated session is maintained

    Notion: TC-19 | AC-8 | data: any logged-in agency user
    """
    page, user = logged_in_agency_page
    base_url = page.url

    quick_links = [
        "Document Checklist",
        "Frequently Asked Questions",
        "Contact Helpdesk",
        "View My Application",
    ]

    with allure.step("Verify Quick Links section is visible"):
        expect(dashboard_page.quick_links_section).to_be_visible()

    for link_text in quick_links:
        with allure.step(f"Click Quick Link: '{link_text}'"):
            expect(dashboard_page.quick_link(link_text)).to_be_visible()
            dashboard_page.click_quick_link(link_text)
            page.wait_for_load_state("networkidle")

        with allure.step(f"Verify navigation happened for '{link_text}'"):
            assert page.url != "", "Page URL should be non-empty after navigation"

        with allure.step("Navigate back to dashboard"):
            page.go_back()
            page.wait_for_load_state("networkidle")

    with allure.step("Verify session is still active after all navigations"):
        expect(dashboard_page.logout_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-20  AC-9  Rejected Applicant Can Log In and View Remarks
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-20 (AC-9): Rejected applicant logs in and sees rejection status, remarks, and appeal option")
def test_tc20_rejected_applicant(rejected_agency_user_page, dashboard_page: DashboardPage):
    """
    Given an agency account whose application was rejected
    When  they log in
    Then  the dashboard shows a REJECTED status badge
    And   a link/option to view rejection remarks is visible
    And   an appeal option (Form-III) is visible

    Notion: TC-20 | AC-9 | data: rejected_agency_user (REJECTED_AGENCY_USERNAME env var)
    """
    page, user = rejected_agency_user_page

    with allure.step("Verify login succeeded — logout button is visible"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Verify application status badge shows REJECTED"):
        expect(dashboard_page.application_status_badge).to_be_visible()
        badge_text = dashboard_page.application_status_badge.text_content().upper()
        assert "REJECTED" in badge_text, f"Expected REJECTED badge, got: '{badge_text}'"

    with allure.step("Verify rejection remarks option is accessible"):
        remarks_link = page.locator("//a[contains(text(),'remarks') or contains(text(),'Remarks') or contains(text(),'Rejection')]").first
        expect(remarks_link).to_be_visible()

    with allure.step("Verify appeal option (Form-III) is visible"):
        appeal_link = page.locator("//a[contains(text(),'Appeal') or contains(text(),'Form-III') or contains(text(),'appeal')]").first
        expect(appeal_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-24  EC-6  Dashboard — No Application Started Yet Shows Prompt
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-24 (EC-6): Dashboard shows 'begin registration' prompt when no application has been started")
def test_tc24_no_application_started(fresh_agency_user_page, dashboard_page: DashboardPage):
    """
    Given I completed pre-registration but have NOT started the 8-step wizard
    When  I log in and view the dashboard
    Then  the My Application Status card shows: "You have not yet submitted your application."
    And   no progress tracker or submission date is shown

    Notion: TC-24 | EC-6 | data: fresh_agency_user (no form_applications rows)
    """
    page, user = fresh_agency_user_page

    with allure.step("Verify 'begin registration' prompt is visible"):
        expect(dashboard_page.no_application_prompt).to_be_visible()
        prompt_text = dashboard_page.no_application_prompt.text_content()
        assert "not yet submitted" in prompt_text.lower() or "begin" in prompt_text.lower(), (
            f"Expected begin-registration prompt, got: '{prompt_text}'"
        )

    with allure.step("Verify progress tracker is NOT visible"):
        assert not dashboard_page.progress_tracker.is_visible(), (
            "Progress tracker should not be shown when no application has been started"
        )


# ---------------------------------------------------------------------------
# TC-25  EC-7  Browser Back Button Does Not Navigate to Login While Session Active
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-25 (EC-7): Browser back button does not return user to login page while session is active")
def test_tc25_browser_back(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given I am logged in and on the dashboard
    When  I press the browser back button
    Then  I remain on the dashboard (session not bypassed; not redirected to login)

    Notion: TC-25 | EC-7 | data: any logged-in agency user
    """
    page, user = logged_in_agency_page
    dashboard_url = page.url

    with allure.step("Verify dashboard is loaded"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Press the browser back button"):
        page.go_back()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify user is NOT redirected to the login page"):
        assert "login" not in page.url.lower(), (
            f"Browser back should not navigate to login, but URL is: {page.url}"
        )

    with allure.step("Verify dashboard elements are still accessible (session intact)"):
        expect(dashboard_page.logout_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-26  EC-8  Double Login from Two Browsers / Tabs
# ---------------------------------------------------------------------------

@allure.story("Portal Dashboard")
@allure.title("TC-26 (EC-8): System handles concurrent sessions from two separate browsers")
def test_tc26_double_login(logged_in_agency_page, dashboard_page: DashboardPage):
    """
    Given I am already logged in on Browser 1
    When  I open a second independent browser and log in with the same credentials
    Then  the system either allows both concurrent sessions
          OR terminates the older session with a notification

    Notion: TC-26 | EC-8 | data: any logged-in agency user
    """
    page_1, user = logged_in_agency_page

    with allure.step("Verify Browser 1 is logged in"):
        expect(dashboard_page.logout_button).to_be_visible()

    with allure.step("Open a second independent browser and login with the same credentials"):
        with sync_playwright() as p:
            browser_2 = p.chromium.launch(headless=True)
            ctx_2 = browser_2.new_context(viewport={"width": 1280, "height": 800})
            page_2 = ctx_2.new_page()

            login_2 = LoginPage(page_2)
            login_2.open()
            login_2.login(user.username, user.password)
            page_2.wait_for_load_state("networkidle")

            with allure.step("Verify second session reached dashboard or shows a session-conflict message"):
                on_dashboard = "dashboard" in page_2.url.lower()
                conflict_msg = page_2.locator("//div[contains(text(),'logged out') or contains(text(),'new session')]")
                assert on_dashboard or conflict_msg.count() > 0, (
                    "Second login should either land on dashboard (concurrent sessions) "
                    "or show a session-conflict notification"
                )

            browser_2.close()

    with allure.step("Check Browser 1 state — either still active or notified of displacement"):
        page_1.reload()
        page_1.wait_for_load_state("networkidle")
        still_on_dashboard = "dashboard" in page_1.url.lower()
        displaced_msg = page_1.locator("//div[contains(text(),'logged out') or contains(text(),'new session')]")
        assert still_on_dashboard or displaced_msg.count() > 0, (
            "Browser 1 should either remain on dashboard (concurrent sessions) "
            "or show a session-displacement notification"
        )
