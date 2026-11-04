"""
Notices Management — Admin Portal (KAN-31)
==========================================
Covers KAN-TC-233…245 and 700…707, 709…713 (Administration › Notices,
/module/admin/notices/Admin notices manage.php), logged in as the Super Admin.
Rewritten 04-Nov-2026 for the redesigned page (Officer Console layout, Status
and Pin toggle buttons in the list, badge preview, client-side 5 MB guard,
Edit Notice / Update Notice / Cancel Edit).

The public Notice Board (/module/notices.php) needs no login: tests that check
it use ``open_public_board``, which opens it in a second browser with no
session. Every notice a test creates is deleted by ``cleanup_notices``.
TC-244 makes every notice inactive for a moment and re-activates exactly those
it switched off.

Not automated: KAN-TC-708 (pinning a third notice) and KAN-TC-714 (actions on
a notice deleted in another tab) are under review.

Known failures on dev (04-Nov-2026), each at the last check of its test (MPPA defect sheet,
"Super admin" tab, #71–76):
  TC-238  after "Update Notice" the form stays "Edit Notice" instead of returning to "Add New Notice" (#72)
  TC-241  after "Notice title is required." the body and badge entered are cleared (#73)
  TC-705  after "Notice body is required." the title entered is cleared (#73)
  TC-709  the General filter (no notices) shows "All (0)" instead of the total (#74)
  TC-710  the clock next to the heading shows UTC, not IST (#75)
  TC-712  a 200-character title with HTML, quotes and Marathi is refused with a raw
          "DB Error: SQLSTATE[22001] … Data too long for column 'title'" (#71)
  TC-713  the page title is "Manage Notices — Placement Agency Regulation Portal" (#76)
"""

import re
from datetime import datetime, timedelta

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.notices_page import NOTICES_URL, AdminNoticesPage
from test_data.notices_factory import NoticeData, NoticesFactory
from utils.aio import aio_case

STORY = "Notices Management"
CLOCK = re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4} · \d{2}:\d{2}$")
ACTIVE = re.compile(r"^\s*Active\s*$")
HIDDEN = re.compile(r"^\s*Hidden\s*$")  # an inactive notice's status button
PIN = re.compile(r"^\s*Pin\s*$")
PINNED = re.compile(r"^\s*Pinned\s*$")


def _today_labels() -> set[str]:
    """Today's date as the list shows it ("DD Mon YYYY"), in IST and in UTC (the page clock is UTC)."""
    now = NoticesFactory.today_ist()
    return {now.strftime(AdminNoticesPage.DATE_FORMAT),
            (now - timedelta(hours=5, minutes=30)).strftime(AdminNoticesPage.DATE_FORMAT)}


def _pinned_first(flags: list[bool]) -> bool:
    """True when every pinned item comes before every unpinned one."""
    return flags == sorted(flags, reverse=True)


def _add(np: AdminNoticesPage, data: NoticeData, **override):
    values = dict(title=data.title, body=data.body, badge=data.badge, dept=data.dept, active=data.active,
                  pinned=data.pinned, attachment_path=data.attachment_path)
    values.update(override)
    np.add_notice(**values)


# ---------------------------------------------------------------------------
# TC-233  Mandatory fields → notice listed immediately
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-233")
@allure.story(STORY)
@allure.title("TC-233: Filling the mandatory fields and clicking Add Notice saves the notice and lists it")
def test_tc233_add_notice_mandatory_fields(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                                           valid_notice_data: NoticeData):
    """
    Given I am on Manage Notices
    When  I enter a title, body, badge Alert and a department and click Add Notice
    Then  the notice is listed with its title, department, ALERT, "● Active", "Pin" and today's date
    And   the form is empty again

    AIO: KAN-TC-233 | KAN-31 AC-1 | data: {valid_notice_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = valid_notice_data

    with allure.step("Enter the title, body, badge and department"):
        np.fill_title(data.title)
        np.fill_body(data.body)
        np.select_badge(data.badge)
        expect(np.badge_preview).to_have_text("ALERT")
        np.fill_department(data.dept)

    with allure.step("Click 'Add Notice'"):
        np.submit_form()
        expect(np.success_alert).to_be_visible()

    with allure.step("Verify the new row"):
        expect(np.notice_title_cell(data.title)).to_have_text(data.title)
        expect(np.notice_dept(data.title)).to_have_text(data.dept)
        expect(np.notice_badge(data.title)).to_have_text("ALERT")
        expect(np.notice_status_button(data.title)).to_have_text(ACTIVE)
        expect(np.notice_pin_button(data.title)).to_have_text(PIN)
        assert np.notice_date(data.title).inner_text().strip() in _today_labels()

    with allure.step("Verify the form is empty again"):
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)
        expect(np.title_input).to_have_value("")
        expect(np.body_textarea).to_have_value("")


# ---------------------------------------------------------------------------
# TC-234  Active notice on the public board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-234")
@allure.story(STORY)
@allure.title("TC-234: An active notice is shown on the public Notice Board")
def test_tc234_active_notice_visible_on_public_board(logged_in_admin_notices_page: AdminNoticesPage,
                                                     cleanup_notices, active_notice_data: NoticeData,
                                                     open_public_board):
    """
    Given I add an active notice with badge New and a department
    When  anyone opens the public Notice Board
    Then  the notice is shown with its title, NEW badge, body and department

    AIO: KAN-TC-234 | KAN-31 AC-2 | data: {active_notice_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = active_notice_data

    with allure.step("Add the active notice"):
        _add(np, data)
        expect(np.notice_status_button(data.title)).to_have_text(ACTIVE)

    with allure.step("Open the public Notice Board"):
        board = open_public_board()

    with allure.step("Verify the notice's title, badge, body and department"):
        card = board.notice_card(data.title)
        expect(card).to_be_visible()
        expect(card.locator(".nbadge")).to_have_text("NEW")
        expect(card.locator(".notice-body")).to_contain_text(data.body)
        expect(card).to_contain_text(data.dept)


# ---------------------------------------------------------------------------
# TC-235  Inactive notice hidden from the public board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-235")
@allure.story(STORY)
@allure.title("TC-235: A notice saved with Active unchecked is hidden from the public Notice Board")
def test_tc235_inactive_notice_hidden_from_public_board(logged_in_admin_notices_page: AdminNoticesPage,
                                                        cleanup_notices, inactive_notice_data: NoticeData,
                                                        open_public_board):
    """
    Given I add a notice with Active unchecked
    Then  it is listed with status "Hidden"
    And   the public Notice Board does not show it

    AIO: KAN-TC-235 | KAN-31 AC-3 | data: {inactive_notice_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = inactive_notice_data

    with allure.step("Add the notice with Active unchecked"):
        _add(np, data)

    with allure.step("Verify it is listed as Hidden"):
        expect(np.notice_status_button(data.title)).to_have_text(HIDDEN)

    with allure.step("Verify the public Notice Board does not show it"):
        board = open_public_board()
        expect(board.notice_cards.first).to_be_visible()
        expect(board.notice_card(data.title)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-236  Pinned notice first
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-236")
@allure.story(STORY)
@allure.title("TC-236: A pinned notice is listed above the unpinned notices in the admin list and on the board")
def test_tc236_pinned_notice_at_top(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                                    pinned_notice_data: NoticeData, open_public_board):
    """
    Given at least two active unpinned notices exist
    When  I add an active notice with "Pin this notice" checked
    Then  it shows "Pinned" and every pinned row comes before every unpinned row, the unpinned ones newest first
    And   on the public board the pinned notices (including the new one) come first

    AIO: KAN-TC-236 | KAN-31 AC-4 | data: {pinned_notice_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = pinned_notice_data

    with allure.step("Add the pinned notice"):
        _add(np, data)
        expect(np.notice_pin_button(data.title)).to_have_text(PINNED)

    with allure.step("Verify the admin list order"):
        rows = np.rows_data()
        allure.attach(str([(r["pin"], r["date"], r["title"]) for r in rows]), name="admin list")
        assert len([r for r in rows if r["pin"] == "Pin"]) >= 2, "Needs two unpinned notices"
        assert _pinned_first([r["pin"] == "Pinned" for r in rows])
        dates = [datetime.strptime(r["date"], np.DATE_FORMAT) for r in rows if r["pin"] == "Pin"]
        assert dates == sorted(dates, reverse=True), "Unpinned notices are not newest first"

    with allure.step("Verify the public board order"):
        board = open_public_board()
        cards = board.read_cards()
        allure.attach(str([(c["pinned"], c["title"]) for c in cards]), name="board")
        assert _pinned_first([c["pinned"] for c in cards])
        assert any(c["pinned"] and c["title"] == data.title for c in cards), "The new notice is not pinned"


# ---------------------------------------------------------------------------
# TC-237  Badge colours
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-237")
@allure.story(STORY)
@allure.title("TC-237: Each badge type shows its colour in the preview, the admin list and on the public board")
def test_tc237_badge_colours(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices, open_public_board):
    """
    Given one active notice of each badge type
    Then  the form preview, the admin list and the public board show NEW red, ALERT amber, INFO blue,
          URGENT purple and GENERAL slate

    AIO: KAN-TC-237 | KAN-31 AC-5
    """
    np = logged_in_admin_notices_page
    colours = NoticesFactory.BADGE_COLOURS
    preview = {}

    with allure.step("Choose each badge type in the form"):
        for badge in colours:
            np.select_badge(badge)
            expect(np.badge_preview).to_have_text(badge.upper())
            preview[badge] = np.badge_preview_colour()

    with allure.step("Add one active notice of each badge type"):
        for badge in colours:
            data = NoticesFactory.badge_notice(badge)
            _add(np, data)
            expect(np.notice_row(data.title)).to_be_visible()

    with allure.step("Read the admin list and the public board"):
        rows = {r["title"]: r["badge_colour"] for r in np.rows_data()}
        board = {c["title"]: c["badge_colour"] for c in open_public_board().read_cards()}

    shown = {b: (preview[b], rows.get(NoticesFactory.badge_notice(b).title),
                 board.get(NoticesFactory.badge_notice(b).title)) for b in colours}
    allure.attach(str(shown), name="preview, list, board colours")
    with allure.step("Verify the colours"):
        assert shown == {b: (c, c, c) for b, c in colours.items()}


# ---------------------------------------------------------------------------
# TC-238  Edit
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-238")
@allure.story(STORY)
@allure.title("TC-238: Edit loads the notice into the Edit Notice form; Update Notice saves it everywhere")
def test_tc238_edit_notice(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                           notice_to_edit_data: NoticeData, open_public_board):
    """
    Given an active notice
    When  I click Edit
    Then  the form is "Edit Notice" (?edit=<id>) with the notice's values, "Update Notice" and "✕ Cancel Edit"
    When  I change the title and click Update Notice
    Then  the list and the public board show the new title and the form is "Add New Notice" again

    AIO: KAN-TC-238 | KAN-31 AC-6 | data: {notice_to_edit_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = notice_to_edit_data

    with allure.step("Create the notice"):
        _add(np, data, dept="Portal Administration")

    with allure.step("Click Edit"):
        np.click_edit(data.title)
        expect(np.page).to_have_url(re.compile(r"\?edit=\d+$"))

    with allure.step("Verify the Edit Notice form"):
        expect(np.form_title).to_have_text(np.EDIT_FORM_TITLE)
        expect(np.title_input).to_have_value(data.title)
        expect(np.body_textarea).to_have_value(data.body)
        expect(np.badge_select).to_have_value(data.badge)
        expect(np.badge_preview).to_have_text(data.badge.upper())
        expect(np.dept_input).to_have_value("Portal Administration")
        expect(np.pin_checkbox).not_to_be_checked()
        expect(np.active_checkbox).to_be_checked()
        expect(np.save_button).to_have_text(np.UPDATE_BUTTON)
        expect(np.cancel_link).to_have_text("✕ Cancel Edit")

    with allure.step("Change the title and click Update Notice"):
        np.fill_title(NoticesFactory.EDITED_TITLE)
        np.submit_form()

    with allure.step("Verify the list"):
        expect(np.notice_row(NoticesFactory.EDITED_TITLE)).to_be_visible()
        expect(np.notice_row(data.title)).to_have_count(0)

    with allure.step("Verify the public board"):
        board = open_public_board()
        expect(board.notice_card(NoticesFactory.EDITED_TITLE)).to_be_visible()
        expect(board.notice_card(data.title)).to_have_count(0)

    with allure.step("Verify the form is 'Add New Notice' again"):
        allure.attach(np.page.url, name="URL after Update Notice")
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)


# ---------------------------------------------------------------------------
# TC-239  Delete
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-239")
@allure.story(STORY)
@allure.title("TC-239: Del asks for confirmation; accepting removes the notice everywhere, dismissing keeps it")
def test_tc239_delete_notice(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                             notice_to_delete_data: NoticeData, open_public_board):
    """
    Given an active notice
    When  I click Del and dismiss "Delete this notice? This cannot be undone."
    Then  the notice is still listed
    When  I click Del and accept
    Then  it is removed from the list and from the public board

    AIO: KAN-TC-239 | KAN-31 AC-7 | data: {notice_to_delete_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = notice_to_delete_data

    with allure.step("Create the notice"):
        _add(np, data)
        expect(np.notice_row(data.title)).to_be_visible()

    with allure.step("Click Del and dismiss the prompt"):
        message = np.delete_notice_dismiss(data.title)
        assert message == np.DELETE_CONFIRM
        expect(np.notice_row(data.title)).to_be_visible()

    with allure.step("Click Del and accept the prompt"):
        assert np.delete_notice(data.title) == np.DELETE_CONFIRM
        expect(np.notice_row(data.title)).to_have_count(0)

    with allure.step("Verify the public board does not show it"):
        board = open_public_board()
        expect(board.notice_cards.first).to_be_visible()
        expect(board.notice_card(data.title)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-240  Attachment
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-240")
@allure.story(STORY)
@allure.title("TC-240: A PDF attached to a notice can be opened from Edit and from the public board")
def test_tc240_attachment(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                          notice_with_attachment_data: NoticeData, open_public_board):
    """
    Given I add an active notice with a PDF under 5 MB
    Then  Edit shows a "View File" link that serves the PDF
    And   the public board shows an attachment link with the notice that serves the PDF

    AIO: KAN-TC-240 | KAN-31 AC-8 | data: {notice_with_attachment_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = notice_with_attachment_data

    with allure.step("Add the notice with the PDF"):
        _add(np, data)
        expect(np.notice_row(data.title)).to_be_visible()

    with allure.step("Click Edit and check 'View File'"):
        np.click_edit(data.title)
        expect(np.view_file_link).to_be_visible()
        response = np.page.request.get(np.page.url.split("/module/")[0] + np.view_file_link.get_attribute("href"))
        assert response.ok and "pdf" in response.headers.get("content-type", ""), response.headers

    with allure.step("Click '✕ Cancel Edit'"):
        np.cancel_edit()
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)

    with allure.step("Open the attachment from the public board"):
        board = open_public_board()
        link = board.notice_attachment_link(data.title)
        expect(link).to_be_visible()
        response = board.page.request.get(board.page.url.split("/module/")[0] + link.get_attribute("href"))
        assert response.ok and "pdf" in response.headers.get("content-type", ""), response.headers


# ---------------------------------------------------------------------------
# TC-241  Blank title
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-241")
@allure.story(STORY)
@allure.title("TC-241: A blank or spaces-only Notice Title is refused")
def test_tc241_blank_title(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                           blank_title_data: NoticeData):
    """
    Given the Add New Notice form
    When  I leave the title blank and click Add Notice
    Then  the browser asks for the title and nothing is saved
    When  I enter only spaces as the title and click Add Notice
    Then  "Notice title is required." is shown, nothing is saved and the body is kept

    AIO: KAN-TC-241 | KAN-31 field-level validation | data: {blank_title_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = blank_title_data
    count = np.all_count()

    with allure.step("Leave the title blank and click Add Notice"):
        np.fill_body(data.body)
        np.select_badge(data.badge)
        np.save_button.click()
        assert np.title_input.evaluate("e => e.validity.valueMissing") is True
        expect(np.success_alert).to_have_count(0)

    with allure.step("Enter only spaces and click Add Notice"):
        np.fill_title("   ")
        np.submit_form()
        expect(np.error_alert).to_contain_text(data.expected_error)
        assert np.all_count() == count

    with allure.step("Verify the body and badge are kept"):
        expect(np.body_textarea).to_have_value(data.body)
        expect(np.badge_select).to_have_value(data.badge)


# ---------------------------------------------------------------------------
# TC-242  Wrong file type
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-242")
@allure.story(STORY)
@allure.title("TC-242: An attachment that is not JPG, PNG or PDF is refused")
def test_tc242_invalid_attachment_format(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                                         invalid_attachment_data: NoticeData):
    """
    Given the Add New Notice form
    Then  the file picker offers JPG, PNG and PDF only
    When  I submit a .docx anyway
    Then  "Attachment must be JPG, PNG or PDF." is shown and the notice is not listed

    AIO: KAN-TC-242 | KAN-31 field-level validation | data: {invalid_attachment_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = invalid_attachment_data

    with allure.step("Check the file picker's accepted types"):
        expect(np.attachment_input).to_have_attribute("accept", np.ATTACHMENT_ACCEPT)

    with allure.step("Submit the notice with a .docx"):
        _add(np, data)

    with allure.step("Verify the error and that nothing was saved"):
        expect(np.error_alert).to_contain_text(data.expected_error)
        expect(np.notice_row(data.title)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-243  File over 5 MB
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-243")
@allure.story(STORY)
@allure.title("TC-243: An attachment over 5 MB is refused before submitting")
def test_tc243_oversized_attachment(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                                    oversized_attachment_data: NoticeData, valid_pdf: str):
    """
    Given the Add New Notice form
    When  I choose a 6 MB PDF
    Then  "File exceeds 5 MB limit. Please choose a smaller file." is shown, the file is cleared and
          Add Notice is disabled
    When  I choose a PDF under 5 MB
    Then  the message goes and Add Notice is enabled
    When  the 6 MB PDF is submitted with the guard bypassed
    Then  the server refuses it and the notice is not listed

    AIO: KAN-TC-243 | KAN-31 field-level validation | data: {oversized_attachment_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = oversized_attachment_data

    with allure.step("Fill the notice and choose the 6 MB PDF"):
        np.fill_title(data.title)
        np.fill_body(data.body)
        np.upload_attachment(data.attachment_path)

    with allure.step("Verify the message, the cleared file and the disabled button"):
        expect(np.file_size_error).to_be_visible()
        expect(np.file_size_error).to_have_text(data.expected_error)
        assert np.attachment_file_count() == 0
        expect(np.save_button).to_be_disabled()

    with allure.step("Choose a PDF under 5 MB"):
        np.upload_attachment(valid_pdf)
        expect(np.file_size_error).to_be_hidden()
        expect(np.save_button).to_be_enabled()

    with allure.step("Submit the 6 MB PDF with the guard bypassed"):
        np.attachment_input.evaluate("e => e.removeAttribute('onchange')")
        np.upload_attachment(data.attachment_path)
        np.submit_form()

    with allure.step("Verify the server refused it"):
        expect(np.error_alert).to_be_visible()
        allure.attach(np.error_alert.inner_text(), name="server error")
        expect(np.notice_row(data.title)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-244  No active notice → placeholder on the board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-244")
@allure.story(STORY)
@allure.title("TC-244: The public Notice Board shows a placeholder when no notice is active")
def test_tc244_no_active_notices_placeholder(logged_in_admin_notices_page: AdminNoticesPage, open_public_board):
    """
    Given every notice is set Inactive with its status button
    When  the public Notice Board is opened
    Then  it shows "No notices found." and its heading (no broken layout)
    And   the notices switched off are made active again afterwards

    AIO: KAN-TC-244 | KAN-31 EC-2
    """
    np = logged_in_admin_notices_page
    deactivated: list[str] = []
    try:
        with allure.step("Set every active notice Inactive"):
            deactivated = np.deactivate_all_active()

        with allure.step("Open the public Notice Board"):
            board = open_public_board()

        with allure.step("Verify the placeholder"):
            expect(board.empty_state).to_be_visible()
            expect(board.empty_state).to_contain_text(board.NO_NOTICES)
            expect(board.board_heading).to_be_visible()
            expect(board.notice_cards).to_have_count(0)
    finally:
        with allure.step("Cleanup: make the same notices active again"):
            np.open()
            np.activate_notices(deactivated)


# ---------------------------------------------------------------------------
# TC-245  Filter tabs
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-245")
@allure.story(STORY)
@allure.title("TC-245: Filter tabs list only the notices of the chosen badge type")
def test_tc245_filter_tabs(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices):
    """
    Given notices of at least two badge types
    When  I click "Alert"
    Then  the URL has ?badge=alert, the tab is highlighted and only ALERT notices are listed
    When  I click "All (N)"
    Then  every notice is listed and N equals the rows
    When  I add an Alert notice
    Then  "All (N+1)" is shown and the notice is listed under Alert

    AIO: KAN-TC-245 | KAN-31 AC-11
    """
    np = logged_in_admin_notices_page

    with allure.step("Make sure an Alert notice exists"):
        seed = NoticesFactory.badge_notice("alert")
        _add(np, seed)
        total = np.all_count()
        assert len({r["badge"] for r in np.rows_data()}) >= 2, "Needs notices of two badge types"

    with allure.step("Click 'Alert'"):
        np.click_filter("Alert")
        expect(np.page).to_have_url(re.compile(r"\?badge=alert$"))
        expect(np.active_filter_pill).to_have_text("Alert")
        badges = {r["badge"] for r in np.rows_data()}
        assert badges == {"ALERT"}, badges

    with allure.step("Click 'All'"):
        np.click_filter("All")
        expect(np.notice_rows).to_have_count(total)

    with allure.step("Add an Alert notice"):
        _add(np, NoticeData(title=NoticesFactory.EXTRA_ALERT_TITLE, body="Tab count check.", badge="alert"))
        np.click_filter("All")
        assert np.all_count() == total + 1
        np.click_filter("Alert")
        expect(np.notice_row(NoticesFactory.EXTRA_ALERT_TITLE)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-700  Status button
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-700")
@allure.story(STORY)
@allure.title("TC-700: Clicking a notice's status button activates or deactivates it")
def test_tc700_status_button(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                             toggle_status_data: NoticeData, open_public_board):
    """
    Given an active notice
    When  I click its "● Active" button
    Then  it shows "Hidden" and the public board hides it
    When  I click "Hidden"
    Then  it shows "Active" and the board shows it again

    AIO: KAN-TC-700 | KAN-31 AC-9 | data: {toggle_status_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = toggle_status_data

    with allure.step("Create the active notice"):
        _add(np, data)
        expect(np.notice_status_button(data.title)).to_have_text(ACTIVE)

    with allure.step("Click 'Active'"):
        np.toggle_active(data.title)
        expect(np.notice_status_button(data.title)).to_have_text(HIDDEN)

    with allure.step("Verify the public board hides it"):
        board = open_public_board()
        expect(board.notice_cards.first).to_be_visible()
        expect(board.notice_card(data.title)).to_have_count(0)

    with allure.step("Click 'Hidden'"):
        np.toggle_active(data.title)
        expect(np.notice_status_button(data.title)).to_have_text(ACTIVE)

    with allure.step("Verify the public board shows it again"):
        board.open()
        expect(board.notice_card(data.title)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-701  Pin button
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-701")
@allure.story(STORY)
@allure.title("TC-701: Clicking Pin / Pinned pins or unpins a notice from the list")
def test_tc701_pin_button(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                          toggle_pin_data: NoticeData, open_public_board):
    """
    Given an active, unpinned notice
    When  I click "Pin"
    Then  it shows "Pinned" and is listed with the pinned notices, on the board too
    When  I click "Pinned"
    Then  it shows "Pin" and is no longer among the pinned notices, on the board too

    AIO: KAN-TC-701 | KAN-31 AC-10 | data: {toggle_pin_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = toggle_pin_data

    def pinned_titles(rows):
        return [r["title"] for r in rows if r["pin"] == "Pinned"]

    with allure.step("Create the unpinned notice"):
        _add(np, data)
        expect(np.notice_pin_button(data.title)).to_have_text(PIN)

    with allure.step("Click 'Pin'"):
        np.toggle_pin(data.title)
        expect(np.notice_pin_button(data.title)).to_have_text(PINNED)
        rows = np.rows_data()
        assert _pinned_first([r["pin"] == "Pinned" for r in rows]) and data.title in pinned_titles(rows)

    with allure.step("Verify the board lists it with the pinned notices"):
        board = open_public_board()
        cards = board.read_cards()
        assert _pinned_first([c["pinned"] for c in cards])
        assert any(c["pinned"] and c["title"] == data.title for c in cards)

    with allure.step("Click 'Pinned'"):
        np.toggle_pin(data.title)
        expect(np.notice_pin_button(data.title)).to_have_text(PIN)
        assert data.title not in pinned_titles(np.rows_data())

    with allure.step("Verify the board no longer pins it"):
        board.open()
        assert not any(c["pinned"] and c["title"] == data.title for c in board.read_cards())


# ---------------------------------------------------------------------------
# TC-702  Cancel Edit
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-702")
@allure.story(STORY)
@allure.title("TC-702: Cancel Edit leaves the notice unchanged and resets the form")
def test_tc702_cancel_edit(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                           cancel_edit_data: NoticeData):
    """
    Given a notice
    When  I click Edit, change its title and click "✕ Cancel Edit"
    Then  the form is an empty "Add New Notice" (badge Info, Active checked) and the list keeps the old title

    AIO: KAN-TC-702 | KAN-31 AC-12 | data: {cancel_edit_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = cancel_edit_data

    with allure.step("Create the notice, click Edit and change the title"):
        _add(np, data)
        np.click_edit(data.title)
        expect(np.form_title).to_have_text(np.EDIT_FORM_TITLE)
        np.fill_title(NoticesFactory.CANCELLED_TITLE)

    with allure.step("Click '✕ Cancel Edit'"):
        np.cancel_edit()

    with allure.step("Verify the form is reset"):
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)
        expect(np.title_input).to_have_value("")
        expect(np.body_textarea).to_have_value("")
        expect(np.badge_select).to_have_value("info")
        expect(np.active_checkbox).to_be_checked()
        expect(np.pin_checkbox).not_to_be_checked()
        expect(np.save_button).to_have_text(np.ADD_BUTTON)

    with allure.step("Verify the list keeps the original notice"):
        expect(np.notice_row(data.title)).to_be_visible()
        expect(np.notice_row(NoticesFactory.CANCELLED_TITLE)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-703  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-703")
@allure.story(STORY)
@allure.title("TC-703: Manage Notices needs an admin session")
def test_tc703_needs_a_session(no_admin_session, admin_notices_page: AdminNoticesPage,
                               admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the Manage Notices URL
    Then  the Admin Login page opens with "Please log in to continue."

    AIO: KAN-TC-703 | KAN-31 AC-13
    """
    with allure.step("Open the page without a session"):
        admin_notices_page.navigate(NOTICES_URL)

    with allure.step("Verify the Admin Login page"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)


# ---------------------------------------------------------------------------
# TC-704  Page loads from the sidebar
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-704")
@allure.story(STORY)
@allure.title("TC-704: Manage Notices page loads from the sidebar")
def test_tc704_page_loads_from_sidebar(logged_in_admin_notices_page: AdminNoticesPage):
    """
    Given I am logged in to the Officer Console
    When  I click "Notices" under Administration
    Then  Manage Notices opens with "Notices" highlighted, the heading and clock, the Add New Notice form
          (defaults: badge Info, Pin unchecked, Active checked) and the filter tabs and list

    AIO: KAN-TC-704 | KAN-31 story context
    """
    np = logged_in_admin_notices_page

    with allure.step("Click 'Notices' in the sidebar of the dashboard"):
        np.page.goto(ADMIN_DASHBOARD_URL)
        np.sidebar.go_to_notices()
        expect(np.page).to_have_url(NOTICES_URL)
        expect(np.sidebar.active_item).to_contain_text("Notices")

    with allure.step("Verify the header"):
        expect(np.heading).to_have_text(np.HEADING)
        expect(np.page_clock).to_have_text(CLOCK)

    with allure.step("Verify the form"):
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)
        expect(np.form_labels).to_contain_text(["Notice Title", "Notice Body", "Badge Type",
                                                "Department / Issuing Authority",
                                                "Attachment (PDF / Image · max 5 MB)"])
        expect(np.badge_select).to_have_value("info")
        expect(np.badge_preview).to_have_text("INFO")
        expect(np.pin_checkbox).not_to_be_checked()
        expect(np.active_checkbox).to_be_checked()
        expect(np.save_button).to_have_text(np.ADD_BUTTON)

    with allure.step("Verify the filter tabs and the list"):
        expect(np.filter_pills).to_have_count(len(np.FILTERS))
        expect(np.filter_pill("All")).to_have_text(re.compile(r"^All \(\d+\)$"))
        assert [t.strip() for t in np.table_headers.all_inner_texts()] == list(np.COLUMNS)


# ---------------------------------------------------------------------------
# TC-705  Blank body
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-705")
@allure.story(STORY)
@allure.title("TC-705: A blank or spaces-only Notice Body is refused")
def test_tc705_blank_body(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                          blank_body_data: NoticeData):
    """
    Given the Add New Notice form with a title
    When  I leave the body blank and click Add Notice
    Then  the browser asks for the body and nothing is saved
    When  I enter only spaces as the body
    Then  "Notice body is required." is shown, nothing is saved and the title is kept

    AIO: KAN-TC-705 | KAN-31 field-level validation | data: {blank_body_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = blank_body_data

    with allure.step("Leave the body blank and click Add Notice"):
        np.fill_title(data.title)
        np.save_button.click()
        assert np.body_textarea.evaluate("e => e.validity.valueMissing") is True
        expect(np.notice_row(data.title)).to_have_count(0)

    with allure.step("Enter only spaces as the body and click Add Notice"):
        np.fill_body("   ")
        np.submit_form()
        expect(np.error_alert).to_contain_text(data.expected_error)
        expect(np.notice_row(data.title)).to_have_count(0)

    with allure.step("Verify the title is kept"):
        expect(np.title_input).to_have_value(data.title)


# ---------------------------------------------------------------------------
# TC-706  Maximum lengths
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-706")
@allure.story(STORY)
@allure.title("TC-706: Title, body and department stop at their maximum lengths")
def test_tc706_max_lengths(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                           over_max_lengths_data: NoticeData):
    """
    Given the Add New Notice form
    When  I type one character over each limit (title 201, body 2,001, department 121)
    Then  the fields keep 200, 2,000 and 120 characters
    And   Add Notice saves the notice with them

    AIO: KAN-TC-706 | KAN-31 field-level validation | data: {over_max_lengths_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = over_max_lengths_data
    limits = np.MAX_LENGTHS

    with allure.step("Type one character over each limit"):
        np.title_input.press_sequentially(data.title, delay=0)
        np.body_textarea.fill(data.body[:-3])
        np.body_textarea.press_sequentially(data.body[-3:], delay=0)
        np.dept_input.press_sequentially(data.dept, delay=0)

    with allure.step("Verify each field stopped at its limit"):
        lengths = {"title": len(np.title_input.input_value()), "body": len(np.body_textarea.input_value()),
                   "dept_name": len(np.dept_input.input_value())}
        assert lengths == limits, lengths

    with allure.step("Click Add Notice"):
        np.submit_form()
        expect(np.success_alert).to_be_visible()

    with allure.step("Verify the notice is saved with the full lengths"):
        title = data.title[:limits["title"]]
        expect(np.notice_title_cell(title)).to_have_text(title)
        expect(np.notice_dept(title)).to_have_text(data.dept[:limits["dept_name"]])


# ---------------------------------------------------------------------------
# TC-707  Badge outside the list
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-707")
@allure.story(STORY)
@allure.title("TC-707: A badge type outside the list is refused")
def test_tc707_badge_outside_list(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                                  badge_outside_list_data: NoticeData):
    """
    Given the Add New Notice form
    When  the badge_type sent is not one of New / Alert / Info / Urgent / General
    Then  the notice is refused with an error, or saved as INFO — never with an unknown badge

    AIO: KAN-TC-707 | KAN-31 field-level validation | data: {badge_outside_list_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = badge_outside_list_data

    with allure.step(f"Send badge_type '{data.badge}'"):
        np.fill_title(data.title)
        np.fill_body(data.body)
        np.badge_select.evaluate("(s, v) => { s.add(new Option(v, v)); s.value = v; }", data.badge)
        np.submit_form()

    with allure.step("Verify it was refused or saved with a known badge"):
        rows = [r for r in np.rows_data() if r["title"] == data.title]
        allure.attach(str(rows) if rows else " ".join(np.error_alert.all_inner_texts()), name="result")
        if rows:
            assert rows[0]["badge"] in {"NEW", "ALERT", "INFO", "URGENT", "GENERAL"}, rows[0]
        else:
            expect(np.error_alert).to_be_visible()


# ---------------------------------------------------------------------------
# TC-709  Empty filter
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-709")
@allure.story(STORY)
@allure.title("TC-709: A filter with no notices shows an empty message and All keeps the total")
def test_tc709_empty_filter(logged_in_admin_notices_page: AdminNoticesPage):
    """
    Given no notice has the badge General
    When  I click "General"
    Then  the empty-list message is shown and "All (N)" still shows the total number of notices

    AIO: KAN-TC-709 | KAN-31 EC-3
    """
    np = logged_in_admin_notices_page
    total = np.all_count()
    if any(r["badge"] == "GENERAL" for r in np.rows_data()):
        pytest.skip("A General notice exists — the General filter is not empty.")

    with allure.step("Click 'General'"):
        np.click_filter("General")
        expect(np.empty_list).to_be_visible()

    with allure.step(f"Verify 'All' still shows {total}"):
        expect(np.filter_pill("All")).to_have_text(f"All ({total})")


# ---------------------------------------------------------------------------
# TC-710  Clock in IST
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-710")
@allure.story(STORY)
@allure.title("TC-710: Page clock shows the current IST time")
def test_tc710_clock_in_ist(logged_in_admin_notices_page: AdminNoticesPage):
    """
    Given I am on Manage Notices
    Then  the date and time next to the heading is the current IST time (within 2 minutes)

    AIO: KAN-TC-710 | KAN-31 EC-4
    """
    np = logged_in_admin_notices_page
    shown = np.page_clock.inner_text().strip()
    now = NoticesFactory.today_ist()
    allure.attach(f"page: {shown}\nIST:  {now:%d %b %Y · %H:%M}", name="clock")

    with allure.step(f"Verify '{shown}' is within 2 minutes of IST"):
        clock = datetime.strptime(shown, np.CLOCK_FORMAT)
        assert abs(clock - now) <= timedelta(minutes=NoticesFactory.CLOCK_TOLERANCE_MINUTES)


# ---------------------------------------------------------------------------
# TC-711  Edit link for a missing notice
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-711")
@allure.story(STORY)
@allure.title("TC-711: An edit link for a missing notice opens the Add form")
def test_tc711_edit_missing_notice(logged_in_admin_notices_page: AdminNoticesPage):
    """
    Given I am on Manage Notices
    When  I open ?edit=<an id that does not exist>
    Then  the form is an empty "Add New Notice" (notice_id 0) with no error

    AIO: KAN-TC-711 | KAN-31 EC-5
    """
    np = logged_in_admin_notices_page

    with allure.step(f"Open ?edit={NoticesFactory.MISSING_NOTICE_ID}"):
        np.open_with(f"edit={NoticesFactory.MISSING_NOTICE_ID}")

    with allure.step("Verify the Add form"):
        expect(np.form_title).to_have_text(np.ADD_FORM_TITLE)
        expect(np.notice_id_input).to_have_value("0")
        expect(np.title_input).to_have_value("")
        expect(np.save_button).to_have_text(np.ADD_BUTTON)
        expect(np.error_alert).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-712  Long text, HTML, quotes, Marathi
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-712")
@allure.story(STORY)
@allure.title("TC-712: Long text, HTML, quotes and Marathi are saved and shown as plain text")
def test_tc712_special_text(logged_in_admin_notices_page: AdminNoticesPage, cleanup_notices,
                            special_text_data: NoticeData, open_public_board):
    """
    Given I add an active notice with a 200-character title and a body with HTML, a script, quotes and Marathi
    Then  the list shows the title as text, cut with an ellipsis
    And   the public board shows the title, body and department exactly as typed, and no script runs

    AIO: KAN-TC-712 | KAN-31 EC-6 | data: {special_text_data.scenario_label}
    """
    np = logged_in_admin_notices_page
    data = special_text_data

    with allure.step("Add the notice"):
        _add(np, data)
        expect(np.error_alert).to_have_count(0)
        expect(np.success_alert).to_be_visible()

    with allure.step("Verify the list shows the title as text, cut with an ellipsis"):
        cell = np.notice_title_cell(NoticesFactory.SPECIAL_PREFIX)
        expect(cell).to_have_text(data.title)
        assert cell.evaluate("e => getComputedStyle(e).textOverflow") == "ellipsis"
        assert cell.evaluate("e => e.scrollWidth > e.clientWidth") is True

    with allure.step("Verify the public board shows the text as typed and runs no script"):
        board = open_public_board()
        card = board.notice_card(NoticesFactory.SPECIAL_PREFIX)
        expect(card.locator(".notice-title")).to_have_text(data.title)
        expect(card.locator(".notice-body")).to_have_text(data.body)
        expect(card).to_contain_text(data.dept)
        assert board.page.evaluate("() => window.__xss === undefined")
        assert np.page.evaluate("() => window.__xss === undefined")


# ---------------------------------------------------------------------------
# TC-713  Page title
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-713")
@allure.story(STORY)
@allure.title("TC-713: Page title matches the other Officer Console pages")
def test_tc713_page_title(logged_in_admin_notices_page: AdminNoticesPage):
    """
    Given I am on Manage Notices
    Then  the browser tab title is "Notices — MPPA Officer Console"

    AIO: KAN-TC-713 | KAN-31 EC-7
    """
    with allure.step(f"Verify the title is '{NoticesFactory.EXPECTED_TITLE}'"):
        expect(logged_in_admin_notices_page.page).to_have_title(NoticesFactory.EXPECTED_TITLE)
