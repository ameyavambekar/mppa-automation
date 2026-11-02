"""
Officer Notifications — Admin Portal
====================================
Covers KAN-TC-586 through KAN-TC-600 (Jira KAN-44).

The Notifications page lists every notification for the officer's jurisdiction,
with an Unread filter and "Mark all read"; the top-bar bell shows the unread count
and the latest 10. The notifications are live dev data, so the tests read them
from the page rather than expecting particular ones.

Reading notifications uses them up. The tests that need an unread one
(``notifications_page_with_unread``) pay for an agency's application first when
none is left, which raises a "New application" notification — TC-597 checks that
notification itself. TC-595 and TC-596 mark every notification read.

TC-598 needs a District Officer account (ADMIN_DISTRICT_USERNAME /
ADMIN_DISTRICT_PASSWORD / ADMIN_DISTRICT_NAME) and is skipped without one.
"""

import re

import allure
from playwright.sync_api import expect

from pages.admin.components.notifications_bell import AdminNotificationsBell
from pages.admin.dashboard_page import AdminDashboardPage
from pages.admin.login_page import AdminLoginPage
from pages.admin.notifications_page import ADMIN_NOTIFICATIONS_URL, AdminNotificationsPage
from test_data.notifications_factory import NotificationsData, NotificationsFactory
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Officer Notifications"
SELECTED = re.compile(r"ui-btn-primary")
NOT_SELECTED = re.compile(r"ui-btn-secondary")
UNREAD = re.compile(r"\bunread\b")
AGENCY_VIEW = re.compile(r"/module/admin/dashboard/agency_view\.php\?id=\d+$")
META = re.compile(r"^[^·]+ · ([^·]+ · )?\d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2} [AP]M$")
BELL_TIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
APPLICATION_ID = re.compile(r"\((\d{13})\)")


def _expect_unread_counts(np: AdminNotificationsPage, jurisdiction: str, unread: int):
    """The subtitle, the sidebar badge and the bell all show ``unread``."""
    expect(np.subtitle_text).to_have_text(AdminNotificationsPage.subtitle(jurisdiction, unread))
    expect(np.bell.button).to_have_attribute("aria-label", AdminNotificationsBell.label(unread))
    if unread:
        expect(np.sidebar.notifications_link.locator(".bc")).to_have_text(str(unread))
        expect(np.bell.count).to_have_text(str(unread))
    else:
        expect(np.sidebar.notifications_link.locator(".bc")).to_have_count(0)
        expect(np.bell.count).to_be_hidden()


def _application_ids(np: AdminNotificationsPage) -> dict[str, str]:
    """data-id → the 13-digit Application ID the notification names (for those that name one)."""
    ids = {}
    for i in range(np.items.count()):
        item = np.items.nth(i)
        found = APPLICATION_ID.search(np.item_title(item).inner_text() + " " + np.item_meta(item).inner_text())
        if found:
            ids[item.get_attribute("data-id")] = found.group(1)
    return ids


# ---------------------------------------------------------------------------
# TC-586  Page header and the default All view
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-586")
@allure.story(STORY)
@allure.title("TC-586: Notifications page loads with heading, unread subtitle, filters and Mark all read")
def test_tc586_page_loads(logged_in_admin_notifications_page: AdminNotificationsPage,
                          state_wide_notifications_data: NotificationsData):
    """
    Given I am logged in to the Officer Console as the Super Administrator
    When  I open Notifications
    Then  the page shows the heading "Notifications", the subtitle "Maharashtra State · N unread", the
          "All" and "Unread" filters and "Mark all read"
    And   "All" is selected and "Notifications" is the highlighted sidebar item

    Notion: KAN-TC-586 | KAN-44 AC-1 | data: state_wide
    """
    np = logged_in_admin_notifications_page
    jurisdiction = state_wide_notifications_data.jurisdiction

    with allure.step("Verify the page title, heading and subtitle"):
        expect(np.page).to_have_title(AdminNotificationsPage.PAGE_TITLE)
        expect(np.heading).to_have_text(AdminNotificationsPage.HEADING)
        expect(np.subtitle_text).to_have_text(re.compile(rf"^{re.escape(jurisdiction)} · \d+ unread$"))

    with allure.step("Verify the All / Unread filters and 'Mark all read'"):
        expect(np.all_filter).to_have_text(AdminNotificationsPage.ALL_LABEL)
        expect(np.unread_filter).to_have_text(AdminNotificationsPage.UNREAD_LABEL)
        expect(np.mark_all_read_button).to_have_text(AdminNotificationsPage.MARK_ALL_READ)

    with allure.step("Verify 'All' is selected and the sidebar highlights Notifications"):
        expect(np.all_filter).to_have_class(SELECTED)
        expect(np.unread_filter).to_have_class(NOT_SELECTED)
        expect(np.sidebar.notifications_link).to_have_class(re.compile(r"\bactive\b"))
        expect(np.items.first).to_be_visible()


# ---------------------------------------------------------------------------
# TC-587  Newest first
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-587")
@allure.story(STORY)
@allure.title("TC-587: Notifications are listed newest first")
def test_tc587_newest_first(logged_in_admin_notifications_page: AdminNotificationsPage):
    """
    Given I am on the Notifications page
    When  I read the date and time on each notification's meta line
    Then  each notification is the same age as or older than the one above it

    Notion: KAN-TC-587 | KAN-44 AC-1
    """
    np = logged_in_admin_notifications_page

    with allure.step("Read every notification's date and time"):
        expect(np.items.first).to_be_visible()
        times = [np.item_time(np.items.nth(i)) for i in range(np.items.count())]

    with allure.step(f"Verify the {len(times)} notifications are newest first"):
        assert times == sorted(times, reverse=True), f"Not newest first: {[t.isoformat() for t in times]}"


# ---------------------------------------------------------------------------
# TC-588  Row content
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-588")
@allure.story(STORY)
@allure.title("TC-588: Each notification shows a type-coloured dot, title, body, meta line and a New badge while unread")
def test_tc588_row_content(logged_in_admin_notifications_page: AdminNotificationsPage):
    """
    Given I am on the Notifications page
    Then  every notification has a coloured dot, a title, a body and a meta line
          "<type> · [<agency> (<Registration ID>) · ]DD Mon YYYY, HH:MM AM/PM", and links to its agency
    And   the dot is blue for a new application, red for the 45-day SLA, amber for an appeal and green for a
          decision
    And   unread notifications are highlighted with a "New" badge, read ones have neither, and there are as
          many "New" badges as the subtitle's unread count

    Notion: KAN-TC-588 | KAN-44 AC-2
    """
    np = logged_in_admin_notifications_page
    expect(np.items.first).to_be_visible()

    for i in range(np.items.count()):
        item = np.items.nth(i)
        title = np.item_title(item).inner_text()
        with allure.step(f"Verify notification {i + 1}: {title}"):
            expect(np.item_dot(item)).to_be_visible()
            expect(np.item_title(item)).not_to_be_empty()
            expect(np.item_body(item)).not_to_be_empty()
            expect(np.item_meta(item)).to_have_text(META)
            expect(item).to_have_attribute("href", AdminNotificationsPage.AGENCY_VIEW_LINK)
            label = np.meta_parts(item)[0]
            if label in AdminNotificationsPage.META_TYPES:
                colour = AdminNotificationsPage.TYPE_COLOURS[AdminNotificationsPage.META_TYPES[label]]
                assert np.dot_colour(item) == colour, f"'{title}' ({label}) dot is {np.dot_colour(item)}, not {colour}"
            if UNREAD.search(item.get_attribute("class")):
                expect(np.item_badge(item)).to_have_text(AdminNotificationsPage.NEW_BADGE)
            else:
                expect(np.item_badge(item)).to_have_count(0)

    with allure.step("Verify the number of 'New' badges equals the unread count"):
        expect(np.new_badges).to_have_count(np.unread_count())
        expect(np.unread_items).to_have_count(np.unread_count())


# ---------------------------------------------------------------------------
# TC-589  Unread filter
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-589")
@allure.story(STORY)
@allure.title("TC-589: Unread filter lists only unread notifications; All lists them all again")
def test_tc589_unread_filter(logged_in_admin_notifications_page: AdminNotificationsPage):
    """
    Given I am on the Notifications page with N unread notifications
    When  I click "Unread"
    Then  the URL ends with ?f=unread, "Unread" is selected and only the N unread notifications are listed
    When  I click "All"
    Then  "All" is selected and every notification is listed again

    Notion: KAN-TC-589 | KAN-44 AC-3
    """
    np = logged_in_admin_notifications_page
    expect(np.items.first).to_be_visible()
    total = np.items.count()
    unread = np.unread_count()

    with allure.step("Click 'Unread'"):
        np.show_unread()

    with allure.step(f"Verify only the {unread} unread notifications are listed"):
        expect(np.page).to_have_url(f"{ADMIN_NOTIFICATIONS_URL}?f=unread")
        expect(np.unread_filter).to_have_class(SELECTED)
        expect(np.all_filter).to_have_class(NOT_SELECTED)
        expect(np.items).to_have_count(unread)
        expect(np.read_items).to_have_count(0)

    with allure.step("Click 'All'"):
        np.show_all()

    with allure.step(f"Verify all {total} notifications are listed again"):
        expect(np.page).to_have_url(ADMIN_NOTIFICATIONS_URL)
        expect(np.all_filter).to_have_class(SELECTED)
        expect(np.items).to_have_count(total)


# ---------------------------------------------------------------------------
# TC-590  Unread counts agree
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-590")
@allure.story(STORY)
@allure.title("TC-590: Unread count agrees on the page, the sidebar, the bell and the dashboard")
def test_tc590_unread_counts_agree(logged_in_admin_notifications_page: AdminNotificationsPage,
                                   admin_dashboard_page: AdminDashboardPage,
                                   state_wide_notifications_data: NotificationsData):
    """
    Given I have N unread notifications
    Then  the subtitle, the sidebar Notifications badge and the bell all show N, and the bell's label is
          "Notifications (N unread)"
    And   the dashboard's "Needs your attention" says "N unread notification(s) for your area" (with nothing
          unread the dashboard has no "Needs your attention" card)

    Notion: KAN-TC-590 | KAN-44 AC-4 | data: state_wide
    """
    np = logged_in_admin_notifications_page
    unread = np.unread_count()

    with allure.step(f"Verify the subtitle, sidebar badge and bell all show {unread}"):
        _expect_unread_counts(np, state_wide_notifications_data.jurisdiction, unread)
        expect(np.unread_items).to_have_count(unread)

    with allure.step("Open the Dashboard"):
        admin_dashboard_page.open()

    if unread:
        with allure.step(f"Verify 'Needs your attention' counts {unread} unread"):
            expect(admin_dashboard_page.card_subtitle(AdminDashboardPage.ATTENTION_TITLE)).to_contain_text(
                f"{unread} unread notification")
    else:
        with allure.step("Verify the dashboard has no 'Needs your attention' card"):
            expect(admin_dashboard_page.card(AdminDashboardPage.TREND_TITLE)).to_be_visible()
            expect(admin_dashboard_page.card(AdminDashboardPage.ATTENTION_TITLE)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-592  Bell dropdown
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-592")
@allure.story(STORY)
@allure.title("TC-592: Bell dropdown lists the latest 10 notifications")
def test_tc592_bell_dropdown(logged_in_admin_notifications_page: AdminNotificationsPage):
    """
    Given I am on the Notifications page
    When  I click the bell
    Then  a dropdown opens with "Notifications", "Mark all read" and "View all notifications"
    And   it lists the 10 newest notifications in the page's order with their times, unread ones highlighted
    When  I click "View all notifications"
    Then  the Notifications page opens

    Notion: KAN-TC-592 | KAN-44 AC-7
    """
    np = logged_in_admin_notifications_page
    bell = np.bell
    expect(np.items.first).to_be_visible()
    shown = min(AdminNotificationsBell.LATEST, np.items.count())

    with allure.step("Click the bell"):
        bell.open()

    with allure.step("Verify the dropdown's header and footer"):
        expect(bell.dropdown).to_be_visible()
        expect(bell.button).to_have_attribute("aria-expanded", "true")
        expect(bell.dropdown_title).to_have_text(AdminNotificationsPage.HEADING)
        expect(bell.mark_all_read_button).to_have_text(AdminNotificationsBell.MARK_ALL_READ)
        expect(bell.view_all_link).to_have_text(AdminNotificationsBell.VIEW_ALL)

    with allure.step(f"Verify it lists the {shown} newest notifications in the page's order"):
        expect(bell.items).to_have_count(shown)
        for i in range(shown):
            item = np.items.nth(i)
            expect(bell.item_title(i)).to_have_text(np.item_title(item).inner_text())
            expect(bell.item_time(i)).to_have_text(BELL_TIME)
            if UNREAD.search(item.get_attribute("class")):
                expect(bell.items.nth(i)).to_have_class(UNREAD)
            else:
                expect(bell.items.nth(i)).not_to_have_class(UNREAD)

    with allure.step("Click 'View all notifications'"):
        bell.view_all_link.click()

    with allure.step("Verify the Notifications page opens"):
        expect(np.page).to_have_url(ADMIN_NOTIFICATIONS_URL)
        expect(np.heading).to_have_text(AdminNotificationsPage.HEADING)


# ---------------------------------------------------------------------------
# TC-594  Bell closes on an outside click
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-594")
@allure.story(STORY)
@allure.title("TC-594: Bell dropdown closes when clicking outside it")
def test_tc594_bell_closes_on_outside_click(logged_in_admin_notifications_page: AdminNotificationsPage):
    """
    Given the bell dropdown is open
    When  I click the page heading (outside the dropdown)
    Then  the dropdown closes

    Notion: KAN-TC-594 | KAN-44 AC-7
    """
    np = logged_in_admin_notifications_page

    with allure.step("Click the bell"):
        np.bell.open()
        expect(np.bell.dropdown).to_be_visible()

    with allure.step("Click the page heading"):
        np.bell.close_by_clicking_outside(np.heading)

    with allure.step("Verify the dropdown closes"):
        expect(np.bell.dropdown).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-599  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-599")
@allure.story(STORY)
@allure.title("TC-599: Notifications page needs an officer session")
def test_tc599_needs_a_session(no_admin_session, admin_notifications_page: AdminNotificationsPage,
                               admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the Notifications page URL
    Then  I am sent to the Admin Login page with "Please log in to continue."

    Notion: KAN-TC-599 | KAN-44 AC-10
    """
    with allure.step("Open the Notifications URL without a session"):
        admin_notifications_page.open()

    with allure.step("Verify the Admin Login page opens with 'Please log in to continue.'"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        assert "reason=not_logged_in" in admin_login_page.get_url()
        expect(admin_login_page.admin_login_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-600  Unknown filter value
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-600")
@allure.story(STORY)
@allure.title("TC-600: Unknown filter value shows the All list")
def test_tc600_unknown_filter_shows_all(logged_in_admin_notifications_page: AdminNotificationsPage,
                                        unknown_filter_data: NotificationsData):
    """
    Given I am on the Notifications page
    When  I open it with ?f=bogus
    Then  "All" is selected and the same notifications as the All view are listed

    Notion: KAN-TC-600 | KAN-44 field-level validation | data: unknown_filter
    """
    np = logged_in_admin_notifications_page
    expect(np.items.first).to_be_visible()
    all_ids = [np.items.nth(i).get_attribute("data-id") for i in range(np.items.count())]

    with allure.step(f"Open Notifications with ?f={unknown_filter_data.filter_value}"):
        np.open_with_filter(unknown_filter_data.filter_value)

    with allure.step("Verify 'All' is selected and every notification is listed"):
        expect(np.all_filter).to_have_class(SELECTED)
        expect(np.unread_filter).to_have_class(NOT_SELECTED)
        expect(np.items).to_have_count(len(all_ids))
        assert [np.items.nth(i).get_attribute("data-id") for i in range(len(all_ids))] == all_ids


# ---------------------------------------------------------------------------
# TC-597  Paying raises a New application notification
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-597")
@allure.story(STORY)
@allure.title("TC-597: Paying for an application raises a New application notification")
def test_tc597_new_application_notification(notifications_after_submission):
    """
    Given an agency whose Declaration step is complete pays on Preview (its application is submitted)
    When  I log in to the Officer Console as the Super Administrator and open Notifications
    Then  the newest notification is "New application: <agency> (<Application ID>)" with the body
          "Paid and submitted — Desktop Scrutiny can start. The 45-day period has begun.", a blue dot, the meta
          line "New application · <agency> (<Application ID>) · <date, time>" and a "New" badge

    Notion: KAN-TC-597 | KAN-44 AC-8 | data: new_application (the agency paid by the fixture)
    """
    np, agency = notifications_after_submission
    data = NotificationsFactory.new_application(agency.agency_name, agency.application_id)
    item = np.item_with_title(data.expected_title)

    with allure.step(f"Verify '{data.expected_title}' is listed once, as the newest notification"):
        expect(item).to_have_count(1)
        expect(np.item_title(np.items.first)).to_have_text(data.expected_title)

    with allure.step("Verify its body, meta line, dot, link and 'New' badge"):
        expect(np.item_body(item)).to_have_text(data.expected_body)
        expect(np.item_meta(item)).to_have_text(re.compile(rf"^{re.escape(data.expected_meta_label)} · "))
        assert np.dot_colour(item) == data.expected_colour, f"dot is {np.dot_colour(item)}"
        expect(item).to_have_attribute("href", AdminNotificationsPage.AGENCY_VIEW_LINK)
        expect(item).to_have_class(UNREAD)
        expect(np.item_badge(item)).to_have_text(AdminNotificationsPage.NEW_BADGE)


# ---------------------------------------------------------------------------
# TC-591  Opening a notification marks it read
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-591")
@allure.story(STORY)
@allure.title("TC-591: Opening an unread notification marks it read and opens its agency")
def test_tc591_open_marks_read(notifications_page_with_unread: AdminNotificationsPage,
                               state_wide_notifications_data: NotificationsData):
    """
    Given I have N unread notifications
    When  I click an unread notification
    Then  the agency's application view opens
    And   back on Notifications that notification is read and every unread count shows N - 1

    Notion: KAN-TC-591 | KAN-44 AC-5 | data: state_wide
    """
    np = notifications_page_with_unread
    unread = np.unread_count()
    item = np.unread_items.first
    notification_id = item.get_attribute("data-id")
    agency_link = item.get_attribute("href").split("/")[-1]

    with allure.step(f"Click the unread notification '{np.item_title(item).inner_text()}'"):
        np.open_item(item)

    with allure.step("Verify the agency's application view opens"):
        expect(np.page).to_have_url(AGENCY_VIEW)
        assert np.page.url.endswith(agency_link), f"Opened {np.page.url}, expected …/{agency_link}"

    with allure.step("Open Notifications again"):
        np.open()

    with allure.step(f"Verify the notification is read and the unread count is {unread - 1}"):
        expect(np.item_by_id(notification_id)).not_to_have_class(UNREAD)
        expect(np.item_badge(np.item_by_id(notification_id))).to_have_count(0)
        _expect_unread_counts(np, state_wide_notifications_data.jurisdiction, unread - 1)


# ---------------------------------------------------------------------------
# TC-593  Clicking a notification in the bell marks it read
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-593")
@allure.story(STORY)
@allure.title("TC-593: Clicking a notification in the bell marks it read and opens its agency")
def test_tc593_bell_click_marks_read(notifications_page_with_unread: AdminNotificationsPage,
                                     state_wide_notifications_data: NotificationsData):
    """
    Given I have N unread notifications
    When  I open the bell and click an unread notification
    Then  the agency's application view opens
    And   on Notifications that notification is read and every unread count shows N - 1

    Notion: KAN-TC-593 | KAN-44 AC-7 | data: state_wide
    """
    np = notifications_page_with_unread
    bell = np.bell
    unread = np.unread_count()

    with allure.step("Click the bell"):
        bell.open()
        expect(bell.unread_items.first).to_be_visible()
        item = bell.unread_items.first
        notification_id = item.get_attribute("data-id")
        agency_link = item.get_attribute("href")

    with allure.step(f"Click the unread notification '{item.locator('b').inner_text()}'"):
        bell.click_item(item)

    with allure.step("Verify the agency's application view opens"):
        expect(np.page).to_have_url(AGENCY_VIEW)
        assert np.page.url.endswith(agency_link), f"Opened {np.page.url}, expected …{agency_link}"

    with allure.step("Open Notifications"):
        np.open()

    with allure.step(f"Verify the notification is read and the unread count is {unread - 1}"):
        expect(np.item_by_id(notification_id)).not_to_have_class(UNREAD)
        _expect_unread_counts(np, state_wide_notifications_data.jurisdiction, unread - 1)


# ---------------------------------------------------------------------------
# TC-595  Mark all read (page)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-595")
@allure.story(STORY)
@allure.title("TC-595: Mark all read on the page marks every notification read")
def test_tc595_mark_all_read_page(notifications_page_with_unread: AdminNotificationsPage,
                                  state_wide_notifications_data: NotificationsData):
    """
    Given I have unread notifications
    When  I click "Mark all read" on the Notifications page
    Then  no notification shows "New", the subtitle shows "0 unread" and the sidebar badge and bell count are gone
    When  I click "Unread"
    Then  no notifications are listed

    Notion: KAN-TC-595 | KAN-44 AC-6 | data: state_wide
    """
    np = notifications_page_with_unread
    expect(np.unread_items.first).to_be_visible()

    with allure.step("Click 'Mark all read'"):
        np.mark_all_read()

    with allure.step("Verify every notification is read and every unread count is gone"):
        expect(np.items.first).to_be_visible()
        expect(np.unread_items).to_have_count(0)
        expect(np.new_badges).to_have_count(0)
        _expect_unread_counts(np, state_wide_notifications_data.jurisdiction, 0)

    with allure.step("Click 'Unread'"):
        np.show_unread()

    with allure.step("Verify no notifications are listed"):
        expect(np.items).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-596  Mark all read (bell)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-596")
@allure.story(STORY)
@allure.title("TC-596: Mark all read in the bell marks every notification read")
def test_tc596_mark_all_read_bell(notifications_page_with_unread: AdminNotificationsPage,
                                  state_wide_notifications_data: NotificationsData):
    """
    Given I have unread notifications
    When  I open the bell and click its "Mark all read"
    Then  the dropdown reloads with no unread notification and the bell count is hidden
    And   on Notifications the subtitle shows "0 unread" and no notification shows "New"

    Notion: KAN-TC-596 | KAN-44 AC-7 | data: state_wide
    """
    np = notifications_page_with_unread
    bell = np.bell

    with allure.step("Click the bell"):
        bell.open()
        expect(bell.count).to_be_visible()
        expect(bell.unread_items.first).to_be_visible()

    with allure.step("Click 'Mark all read' in the dropdown"):
        bell.mark_all_read()

    with allure.step("Verify the dropdown has no unread notification and the bell count is hidden"):
        expect(bell.unread_items).to_have_count(0)
        expect(bell.items.first).to_be_visible()
        expect(bell.count).to_be_hidden()

    with allure.step("Open Notifications"):
        np.open()

    with allure.step("Verify every notification is read"):
        expect(np.unread_items).to_have_count(0)
        _expect_unread_counts(np, state_wide_notifications_data.jurisdiction, 0)


# ---------------------------------------------------------------------------
# TC-598  District Officer scope
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-598")
@allure.story(STORY)
@allure.title("TC-598: District Officer sees only notifications for agencies in their district")
def test_tc598_district_officer_scope(super_admin_login, district_officer_login,
                                      admin_notifications_page: AdminNotificationsPage,
                                      district_officer_notifications_data: NotificationsData):
    """
    Given a District Officer account and agencies with notifications in that district and in others
    When  the District Officer opens Notifications
    Then  the subtitle names the officer's district
    And   every notification about an agency the tests registered is about an agency in that district
    And   the notifications the Super Administrator sees for the tests' agencies in other districts are not listed

    Notion: KAN-TC-598 | KAN-44 AC-9 | data: district_officer (ADMIN_DISTRICT_* in .env)
    Note:   An agency's district is read from the state store, so only the agencies the tests registered
            are checked.
    """
    np = admin_notifications_page
    district = district_officer_notifications_data.jurisdiction
    store = TestStateStore()

    def district_of(application_id: str):
        user = store.get_agency_user_by_application_id(application_id)
        return user.district if user else None

    with allure.step("As the Super Administrator, note the notifications about agencies in other districts"):
        super_admin_login()
        np.open()
        elsewhere = {nid for nid, app in _application_ids(np).items() if district_of(app) not in (None, district)}
        np.logout()

    with allure.step("Log in as the District Officer and open Notifications"):
        district_officer_login()
        np.open()

    with allure.step(f"Verify the subtitle names {district}"):
        expect(np.subtitle_text).to_contain_text(district)

    with allure.step(f"Verify every notification about a known agency is about one in {district}"):
        officer_ids = _application_ids(np)
        wrong = {nid: app for nid, app in officer_ids.items() if district_of(app) not in (None, district)}
        assert not wrong, f"Notifications about agencies outside {district}: {wrong}"

    with allure.step("Verify the Super Administrator's notifications for other districts are not listed"):
        listed = {np.items.nth(i).get_attribute("data-id") for i in range(np.items.count())}
        assert not elsewhere & listed, f"Listed for the District Officer: {elsewhere & listed}"
