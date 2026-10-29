import re

import allure
from playwright.sync_api import expect

from config import AUTH_BASE
from pages.agency_home_page import AGENCY_HOME_URL, AgencyHomePage
from pages.declaration_page import PREVIEW_URL
from pages.login_page import LoginPage
from pages.notice_board_page import NoticeBoardPage
from utils.aio import aio_case

STORY = "Agency Home"
ON_HOME = re.compile(rf"^{re.escape(AGENCY_HOME_URL)}")
ON_LOGIN = re.compile(rf"^{re.escape(AUTH_BASE)}/login\.php")
APPLICATION_ID = re.compile(r"^\d{13}$")
DATE = r"\d{1,2} [A-Z][a-z]{2} \d{4}"
DATE_TIME = r"\d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2} [AP]M"
NOT_REACHED = re.compile(r"\bis-(done|current)\b")


def _user_text(username: str) -> re.Pattern:
    """'<username> (<13-digit Application ID>)' — the page puts a non-breaking space before the bracket."""
    return re.compile(rf"^\s*{re.escape(username)}\s+\((\d{{13}})\)\s*$")


def _application_id(home: AgencyHomePage, username: str) -> str:
    return _user_text(username).match(home.user_text.inner_text()).group(1)


def _expect_opens(page, link, path: str = None) -> None:
    """Clicking ``link`` loads a page without an HTTP error (at ``path`` under the module root when given)."""
    with page.expect_navigation() as navigation:
        link.click()
    response = navigation.value
    assert response is not None and response.ok, \
        f"{page.url} returned {response.status if response else 'no response'}"
    if path:
        expect(page).to_have_url(re.compile(rf"^{re.escape(AgencyHomePage.url_of(path))}"))


# ---------------------------------------------------------------------------
# TC-517  Login after submission lands on Home
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-517")
@allure.story(STORY)
@allure.title("TC-517: Login after submission lands on the Home page with the username and Application ID in the top bar")
def test_tc517_login_lands_on_home(agency_home: AgencyHomePage, submitted_agency):
    """
    Given my application has been submitted (paid)
    When  I log in with my username and password
    Then  the Home page opens, and the top bar shows the menu, "<username> (<Application ID>)" and Logout

    Notion: KAN-TC-517 | KAN-40 AC-1
    """
    page, user = submitted_agency

    with allure.step("Log in"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_load_state("networkidle")

    with allure.step("Verify the Home page opens"):
        expect(page).to_have_url(ON_HOME)
        agency_home.dismiss_testing_notice()

    with allure.step("Verify the top bar"):
        for label in AgencyHomePage.NAV_LINKS:
            expect(agency_home.nav_link(label)).to_be_visible()
        expect(agency_home.user_text).to_have_text(_user_text(user.username))
        expect(agency_home.logout_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-518  Welcome block
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-518")
@allure.story(STORY)
@allure.title("TC-518: Welcome block shows the agency name, Application ID, status and registration date")
def test_tc518_welcome_block(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I look at the welcome block
    Then  it shows "Agency dashboard", my agency name, my Application ID (as in the top bar), "Under review"
          and the date I registered, and "View Submitted Application" opens my submitted application

    Notion: KAN-TC-518 | KAN-40 AC-2
    """
    page, user = logged_in_agency_home_page
    application_id = _application_id(agency_home, user.username)

    with allure.step("Verify the welcome block"):
        expect(agency_home.eyebrow).to_have_text(AgencyHomePage.EYEBROW)
        expect(agency_home.agency_name).to_have_text(user.agency_name)
        expect(agency_home.application_id).to_have_text(APPLICATION_ID)
        expect(agency_home.application_id).to_have_text(application_id)
        expect(agency_home.status_badge).to_have_text(AgencyHomePage.UNDER_REVIEW)
        expect(agency_home.registered).to_have_text(re.compile(rf"^Registered\s*{DATE}$"))

    with allure.step("Click 'View Submitted Application'"):
        _expect_opens(page, agency_home.view_submitted_button, AgencyHomePage.VIEW_APPLICATION_PATH)


# ---------------------------------------------------------------------------
# TC-519  Next-step banner
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-519")
@allure.story(STORY)
@allure.title("TC-519: Banner says the application is under review in Desktop Scrutiny and no action is needed")
def test_tc519_next_step_banner(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given my application is in Desktop Scrutiny
    When  I open the Home page
    Then  the banner says it is under review in Stage 1 — Desktop Scrutiny and no action is needed, and
          "View my application" opens my submitted application

    Notion: KAN-TC-519 | KAN-40 AC-3
    """
    page, user = logged_in_agency_home_page

    with allure.step("Verify the banner"):
        expect(agency_home.next_step_heading).to_have_text(AgencyHomePage.STAGE_1_HEADING)
        expect(agency_home.next_step_text).to_have_text(AgencyHomePage.STAGE_1_TEXT)

    with allure.step("Click 'View my application'"):
        _expect_opens(page, agency_home.next_step_button, AgencyHomePage.VIEW_APPLICATION_PATH)


# ---------------------------------------------------------------------------
# TC-520  Application progress
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-520")
@allure.story(STORY)
@allure.title("TC-520: Application progress shows Submitted done, Desktop scrutiny current and the submission in the timeline")
def test_tc520_application_progress(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given my application has just been submitted
    When  I look at Application progress
    Then  it shows Stage 1 — Desktop Scrutiny and the 45-day decision badge; Submitted is done, Desktop
          scrutiny current, Physical verification and Certificate not reached; the timeline lists the
          submission with its date and time

    Notion: KAN-TC-520 | KAN-40 AC-4
    """
    page, user = logged_in_agency_home_page
    done, current, *later = AgencyHomePage.STAGES

    with allure.step("Verify the card header"):
        expect(agency_home.progress_subtitle).to_have_text(AgencyHomePage.STAGE_1_PROGRESS)
        expect(agency_home.progress_badge).to_have_text(AgencyHomePage.DECISION_BADGE)

    with allure.step("Verify the stage tracker"):
        expect(agency_home.stages).to_have_text(list(AgencyHomePage.STAGES))
        expect(agency_home.stage(done)).to_have_class(re.compile(r"\bis-done\b"))
        expect(agency_home.stage(current)).to_have_class(re.compile(r"\bis-current\b"))
        for label in later:
            expect(agency_home.stage(label)).not_to_have_class(NOT_REACHED)

    with allure.step("Verify the timeline"):
        event = AgencyHomePage.SUBMITTED_EVENT
        expect(agency_home.timeline_item(event)).to_have_count(1)
        expect(agency_home.timeline_time(event)).to_have_text(re.compile(rf"^{DATE_TIME}$"))
        expect(agency_home.timeline_note(event)).to_have_text(AgencyHomePage.SUBMITTED_EVENT_NOTE)


# ---------------------------------------------------------------------------
# TC-521  Unread submission notification
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-521")
@allure.story(STORY)
@allure.title("TC-521: Notifications show the unread submission notification with the Application ID")
def test_tc521_submission_notification(agency_home: AgencyHomePage, home_with_unread_notifications):
    """
    Given I have an unread notification
    When  I open the Home page
    Then  the card shows "<n> new" and "Mark all read", and the submission notification is highlighted with
          its title, my Application ID, the 45-day deadline, the date and time and "Open"

    Notion: KAN-TC-521 | KAN-40 AC-5
    """
    page, user = home_with_unread_notifications
    application_id = _application_id(agency_home, user.username)
    title = AgencyHomePage.SUBMITTED_NOTIFICATION

    with allure.step("Verify the card header"):
        unread = agency_home.unread_notifications.count()
        expect(agency_home.notifications_subtitle).to_have_text(f"{unread} new")
        expect(agency_home.mark_all_read_button).to_have_text(AgencyHomePage.MARK_ALL_READ_LABEL)

    with allure.step("Verify the submission notification"):
        expect(agency_home.notification_title(title)).to_have_text(title)
        expect(agency_home.notification_message(title)).to_contain_text(f"Application ID: {application_id}")
        expect(agency_home.notification_message(title)).to_contain_text("a decision is due within 45 days")
        expect(agency_home.notification_time(title)).to_have_text(re.compile(rf"^{DATE_TIME}\s*·\s*Open$"))
        expect(agency_home.notification_open_link(title)).to_be_visible()

    with allure.step("Verify it is the same moment as the submission in the timeline"):
        submitted_at = agency_home.timeline_time(AgencyHomePage.SUBMITTED_EVENT).inner_text().strip()
        expect(agency_home.notification_time(title)).to_contain_text(submitted_at)


# ---------------------------------------------------------------------------
# TC-522  Mark all read
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-522")
@allure.story(STORY)
@allure.title("TC-522: \"Mark all read\" clears the unread count and highlighting")
def test_tc522_mark_all_read(agency_home: AgencyHomePage, home_with_unread_notifications):
    """
    Given I have unread notifications
    When  I click "Mark all read"
    Then  the page reloads with no "<n> new" count and nothing highlighted; the notifications are still
          listed and stay read after a reload

    Uses up the agency's unread notification (see ``home_with_unread_notifications``).

    Notion: KAN-TC-522 | KAN-40 AC-6
    """
    page, user = home_with_unread_notifications
    listed = agency_home.notifications.count()

    with allure.step("Click 'Mark all read'"):
        agency_home.mark_all_read()

    with allure.step("Verify nothing is unread and the notifications are still listed"):
        expect(agency_home.unread_notifications).to_have_count(0)
        expect(agency_home.notifications_subtitle).not_to_contain_text("new")
        expect(agency_home.notifications).to_have_count(listed)

    with allure.step("Reload — the notifications stay read"):
        page.reload()
        expect(agency_home.unread_notifications).to_have_count(0)
        expect(agency_home.notifications).to_have_count(listed)


# ---------------------------------------------------------------------------
# TC-523  Tiles
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-523")
@allure.story(STORY)
@allure.title("TC-523: Tiles open My application, Corrections and Helpdesk")
def test_tc523_tiles(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I click each tile
    Then  My application opens the submitted application, Corrections the officer's requests and Helpdesk
          the Contact Us page

    Notion: KAN-TC-523 | KAN-40 AC-7
    """
    page, user = logged_in_agency_home_page

    expect(agency_home.tiles).to_have_count(len(AgencyHomePage.TILES))
    for label, path in AgencyHomePage.TILES.items():
        with allure.step(f"Click the '{label}' tile"):
            agency_home.open()
            _expect_opens(page, agency_home.tile(label), path)


# ---------------------------------------------------------------------------
# TC-524  Quick links
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-524")
@allure.story(STORY)
@allure.title("TC-524: Quick links open the document checklist, user manual, FAQ and helpdesk")
def test_tc524_quick_links(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I click each quick link
    Then  each opens its page without an error

    Known defect (29-Oct-2026, KAN-40): "Document checklist", "User manual (PDF)" and "Frequently asked
    questions" open module/guidelines.php, which returns 404 — this test fails.

    Notion: KAN-TC-524 | KAN-40 AC-7
    """
    page, user = logged_in_agency_home_page

    for label in AgencyHomePage.QUICK_LINKS:
        with allure.step(f"Click '{label}'"):
            agency_home.open()
            _expect_opens(page, agency_home.quick_link(label))
    expect(page).to_have_url(AgencyHomePage.url_of(AgencyHomePage.TILES["Helpdesk"]))


# ---------------------------------------------------------------------------
# TC-525  Notice board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-525")
@allure.story(STORY)
@allure.title("TC-525: Notice board shows the latest five notices and links to all notices")
def test_tc525_notice_board(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given notices have been published
    When  I look at the Notice board
    Then  it shows up to five notices, each with a NEW / ALERT / INFO badge and its text cut at 100
          characters, and "View all notices →" opens the Notice Board, which holds at least as many

    Notion: KAN-TC-525 | KAN-40 AC-8
    """
    page, user = logged_in_agency_home_page
    shown = agency_home.notices.count()

    with allure.step("Verify the notices"):
        assert 0 < shown <= AgencyHomePage.NOTICE_LIMIT, f"{shown} notices shown"
        for index in range(shown):
            expect(agency_home.notice_badge(index)).to_have_text(
                re.compile(rf"^({'|'.join(AgencyHomePage.NOTICE_BADGES)})$"))
            text = agency_home.notice_text(index).inner_text().strip()
            assert len(text) <= AgencyHomePage.NOTICE_TEXT_LIMIT, f"notice {index + 1} text is {len(text)} long"
            if text.endswith("…"):
                assert len(text) == AgencyHomePage.NOTICE_TEXT_LIMIT, f"notice {index + 1} was cut at {len(text)}"

    with allure.step("Click 'View all notices →'"):
        _expect_opens(page, agency_home.view_all_notices_link, "notices.php")
        board = NoticeBoardPage(page)
        expect(board.board_heading).to_be_visible()

    with allure.step("Verify Home shows the latest five (or all, when there are fewer)"):
        assert shown == min(AgencyHomePage.NOTICE_LIMIT, board.notice_cards.count()), \
            f"Home shows {shown} of {board.notice_cards.count()} notices"


# ---------------------------------------------------------------------------
# TC-526  Top menu
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-526")
@allure.story(STORY)
@allure.title("TC-526: Top menu links open their pages")
def test_tc526_top_menu(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I click About Portal, Downloads, Notices, Contact Us and Home
    Then  each opens its page

    Notion: KAN-TC-526 | KAN-40 AC-9
    """
    page, user = logged_in_agency_home_page

    for label, path in AgencyHomePage.NAV_LINKS.items():
        with allure.step(f"Click '{label}'"):
            _expect_opens(page, agency_home.nav_link(label), path)


# ---------------------------------------------------------------------------
# TC-527  Logout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-527")
@allure.story(STORY)
@allure.title("TC-527: Logout from Home ends the session")
def test_tc527_logout(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I click Logout
    Then  the Agency Login page opens, and opening module/home.php again shows the public landing page
          (Login in the top bar) instead of my dashboard

    Notion: KAN-TC-527 | KAN-40 AC-9
    """
    page, user = logged_in_agency_home_page

    with allure.step("Click 'Logout'"):
        agency_home.logout()
        expect(page).to_have_url(ON_LOGIN)

    with allure.step("Open the Home page directly — the public landing page is shown, not the dashboard"):
        agency_home.open()
        expect(agency_home.login_link).to_be_visible()
        expect(agency_home.user_text).to_have_count(0)
        expect(agency_home.welcome_block).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-528  Footer
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-528")
@allure.story(STORY)
@allure.title("TC-528: Footer shows the portal details and working links")
def test_tc528_footer(agency_home: AgencyHomePage, logged_in_agency_home_page):
    """
    Given I am on the Home page
    When  I look at the footer
    Then  it shows the portal, department, helpline, e-mail and copyright, and Privacy Policy, Terms of Use
          and Accessibility Statement link to their pages

    Known defect (29-Oct-2026, KAN-40): the three links point to "#" — this test fails.

    Notion: KAN-TC-528 | KAN-40 Sections in Scope
    """
    page, user = logged_in_agency_home_page

    with allure.step("Verify the footer text"):
        for text in AgencyHomePage.FOOTER_TEXTS:
            expect(agency_home.footer).to_contain_text(text)
        expect(agency_home.footer).to_contain_text(re.compile(r"Version \d+\.\d+\.\d+"))

    with allure.step("Verify the links lead to a page"):
        for label in AgencyHomePage.FOOTER_LINKS:
            expect(agency_home.footer_link(label)).not_to_have_attribute("href", "#")


# ---------------------------------------------------------------------------
# TC-529  No unread notifications
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-529")
@allure.story(STORY)
@allure.title("TC-529: No unread notifications — no count and nothing highlighted")
def test_tc529_no_unread_notifications(agency_home: AgencyHomePage, home_without_unread_notifications):
    """
    Given all my notifications are read
    When  I open the Home page
    Then  no "<n> new" count is shown and no notification is highlighted

    Notion: KAN-TC-529 | KAN-40 EC-1
    """
    page, user = home_without_unread_notifications

    with allure.step("Verify the Notifications card"):
        expect(agency_home.notifications_card).to_be_visible()
        expect(agency_home.unread_notifications).to_have_count(0)
        expect(agency_home.notifications_subtitle).not_to_contain_text("new")


# ---------------------------------------------------------------------------
# TC-530  Unpaid agency does not land on Home
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-530")
@allure.story(STORY)
@allure.title("TC-530: Agency that has not paid lands on its next step, not on Home")
def test_tc530_unpaid_lands_on_next_step(unpaid_agency):
    """
    Given my application is not yet paid and my Declaration step is complete
    When  I log in
    Then  the Preview step opens, not the Home page

    Notion: KAN-TC-530 | KAN-40 EC-2
    """
    page, user = unpaid_agency

    with allure.step("Log in"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_load_state("networkidle")

    with allure.step("Verify the Preview step opens"):
        expect(page).to_have_url(re.compile(rf"^{re.escape(PREVIEW_URL)}"))
