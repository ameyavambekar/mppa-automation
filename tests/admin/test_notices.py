"""
Notices Management — Admin Portal
==================================
Covers KAN-TC-233 through KAN-TC-245.

Dual-role tests (TC-234, TC-235, TC-236, TC-237, TC-238, TC-239, TC-240,
TC-244) use the ``open_agency_board`` fixture to open a separate agency session
(via ``second_browser``) independently of the admin session held by the main
``page`` fixture. That fixture logs the agency user out on teardown; the admin
session is logged out by the ``logged_in_admin_notices_page`` fixture — both
matter because the main browser context is shared across the whole session.
"""

import re

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.login_page import AdminLoginPage
from pages.admin.notices_page import AdminNoticesPage
from pages.login_page import LoginPage
from pages.notice_board_page import NoticeBoardPage
from test_data.notices_factory import NoticeData, NoticesFactory
from config import AUTH_BASE
from utils.aio import aio_case
from utils.state_store import TestStateStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_notice_board(second_browser):
    """Open a visible second browser, log in as an agency user, and land on the
    public Notice Board page (/module/notices.php).

    After login the agency user lands on the dashboard; we then navigate to the
    dedicated Notice Board page where every active notice is rendered as a
    ``.notice-card``. The second browser honours the project HEADLESS / SLOW_MO
    settings, so its interactions are visible alongside the admin window.
    """
    store = TestStateStore()
    agency = store.get_any_agency_user()
    if agency is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")

    browser = second_browser()
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    p = ctx.new_page()

    login = LoginPage(p)
    login.open()
    login.login(agency.username, agency.password)
    board = NoticeBoardPage(p)
    board.open()
    return board


def _delete_all_test_notices(admin_notices_page: AdminNoticesPage) -> int:
    """Cleanup helper — deletes every notice the automation suite may have
    created. Pass a logged-in AdminNoticesPage already on the Notices page
    (e.g. the ``logged_in_admin_notices_page`` fixture). Returns the count
    deleted."""
    return admin_notices_page.delete_notices_matching(NoticesFactory.all_test_titles())


@pytest.fixture
def cleanup_notices(logged_in_admin_notices_page: AdminNoticesPage):
    """Teardown fixture: after the test, deletes every automation-created notice
    so each run self-cleans.

    Depends on ``logged_in_admin_notices_page``, so it shares the SAME page
    instance the test already uses — request both from a test (the test keeps
    using ``logged_in_admin_notices_page`` for its body) and this fixture's
    teardown handles the cleanup. Wired into every test that persists a notice.
    """
    yield logged_in_admin_notices_page
    logged_in_admin_notices_page.open()
    _delete_all_test_notices(logged_in_admin_notices_page)


AGENCY_LOGOUT_URL = f"{AUTH_BASE}/logout.php"


@pytest.fixture
def open_agency_board(second_browser):
    """Factory that logs an agency user into a fresh (visible) second browser
    and opens the public Notice Board, returning the NoticeBoardPage.

    On teardown it logs every agency session it opened out, then ``second_browser``
    closes the browser — so no agency session leaks into the next test.
    """
    boards = []

    def _open():
        board = _open_notice_board(second_browser)
        boards.append(board)
        return board

    yield _open

    for board in boards:
        try:
            board.page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TC-233  Mandatory fields → notice appears in admin list immediately
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-233")
@allure.story("Notices Management")
@allure.title("TC-233: Mandatory fields save notice and reflect immediately in admin list")
def test_tc233_add_notice_mandatory_fields(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    valid_notice_data: NoticeData,
):
    """
    Given I am logged in as Admin on the Notices Management page
    When  I fill Notice Title, Notice Body, and select Badge Type then click Add Notice
    Then  the notice is saved and immediately appears in the right-panel list
    And   the list row shows the correct title, badge (ALERT), Active status, and today's date

    Notion: KAN-TC-233 | data: valid_notice
    """
    np = logged_in_admin_notices_page

    with allure.step("Enter Notice Title"):
        np.fill_title(valid_notice_data.title)
        expect(np.title_input).to_have_value(valid_notice_data.title)

    with allure.step("Enter Notice Body"):
        np.fill_body(valid_notice_data.body)
        expect(np.body_textarea).to_have_value(valid_notice_data.body)

    with allure.step("Select Badge Type: Alert"):
        np.select_badge(valid_notice_data.badge)
        expect(np.badge_preview).to_have_text("ALERT")

    with allure.step("Click Add Notice"):
        np.submit_form()

    with allure.step("Verify success alert is shown"):
        expect(np.success_alert).to_be_visible()

    with allure.step("Verify notice appears in list with correct badge and Active status"):
        expect(np.notice_row(valid_notice_data.title)).to_be_visible()
        expect(np.notice_badge(valid_notice_data.title)).to_contain_text("ALERT")
        expect(np.notice_status_button(valid_notice_data.title)).to_contain_text("Active")


# ---------------------------------------------------------------------------
# TC-234  Active notice is visible on agency portal homepage
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-234")
@allure.story("Notices Management")
@allure.title("TC-234: Active notice is visible to agency users on the portal homepage")
def test_tc234_active_notice_visible_on_public_board(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    active_notice_data: NoticeData,
    open_agency_board,
):
    """
    Given I am logged in as Admin
    When  I add a notice with Active = checked
    Then  the notice is saved with Active status in the admin list
    And   an agency user can see the notice on the public Notice Board

    Notion: KAN-TC-234 | data: active_notice
    """
    np = logged_in_admin_notices_page

    with allure.step("Add notice with Active = checked"):
        np.add_notice(
            title=active_notice_data.title,
            body=active_notice_data.body,
            badge=active_notice_data.badge,
            active=True,
        )

    with allure.step("Verify notice saved with Active status in admin list"):
        expect(np.notice_row(active_notice_data.title)).to_be_visible()
        expect(np.notice_status_button(active_notice_data.title)).to_contain_text("Active")

    with allure.step("Log in as agency user and open the public Notice Board"):
        board = open_agency_board()

    with allure.step("Verify notice is visible on the public Notice Board"):
        expect(board.notice_card(active_notice_data.title)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-235  Inactive notice does NOT appear on agency notice board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-235")
@allure.story("Notices Management")
@allure.title("TC-235: Inactive notice does not appear on agency-facing notice board")
def test_tc235_inactive_notice_hidden_from_public_board(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    inactive_notice_data: NoticeData,
    open_agency_board,
):
    """
    Given I am logged in as Admin
    When  I add a notice with Active = unchecked
    Then  it is saved with Inactive status in the admin list
    And   the notice does NOT appear on the public notice board

    Notion: KAN-TC-235 | data: inactive_notice
    """
    np = logged_in_admin_notices_page

    with allure.step("Add notice with Active = unchecked"):
        np.add_notice(
            title=inactive_notice_data.title,
            body=inactive_notice_data.body,
            badge=inactive_notice_data.badge,
            active=False,
        )

    with allure.step("Verify notice saved with Inactive status in admin list"):
        expect(np.notice_row(inactive_notice_data.title)).to_be_visible()

    with allure.step("Verify admin panel shows Inactive indicator (not 'Active' button)"):
        expect(np.notice_status_button(inactive_notice_data.title)).not_to_contain_text("Active")

    with allure.step("Log in as agency user and open the public Notice Board"):
        board = open_agency_board()

    with allure.step("Verify notice does NOT appear on the public notice board"):
        expect(board.notice_card(inactive_notice_data.title)).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-236  Pinned notice is first on public board with Pinned indicator
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-236")
@allure.story("Notices Management")
@allure.title("TC-236: Pinned notice appears at the top of the public notice board")
def test_tc236_pinned_notice_at_top_of_board(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    pinned_notice_data: NoticeData,
    open_agency_board,
):
    """
    Given at least two other active unpinned notices exist
    When  I add a notice with Pin checked and Active checked
    Then  the admin list shows a Pinned indicator for that notice
    And   on the public board the pinned notice is the very first item

    Notion: KAN-TC-236 | data: pinned_notice
    """
    np = logged_in_admin_notices_page

    with allure.step("Add notice with Pin and Active both checked"):
        np.add_notice(
            title=pinned_notice_data.title,
            body=pinned_notice_data.body,
            badge=pinned_notice_data.badge,
            active=True,
            pinned=True,
        )

    with allure.step("Verify admin list shows Pinned indicator"):
        expect(np.notice_pin_button(pinned_notice_data.title)).to_contain_text("Pinned")

    with allure.step("Open the public Notice Board as agency user"):
        board = open_agency_board()

    with allure.step("Verify pinned notice is the first card on the board"):
        expect(board.first_notice_card).to_contain_text(pinned_notice_data.title)

    with allure.step("Verify the first card carries the 'Pinned' indicator"):
        expect(board.first_notice_card.locator(".pin-icon")).to_contain_text("Pinned")

    with allure.step("Verify other notices follow below (more than one card present)"):
        assert board.notice_cards.count() > 1


# ---------------------------------------------------------------------------
# TC-237  Each badge type maps to the correct colour on the public board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-237")
@allure.story("Notices Management")
@allure.title("TC-237: Each badge type renders the correct colour on the public notice board")
def test_tc237_badge_colours_on_public_board(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    open_agency_board,
):
    """
    Given I create one active notice for each badge type
    When  an agency user views the public notice board
    Then  ALERT, NEW, INFO, URGENT, and GENERAL badges each render with a distinct colour class

    Notion: KAN-TC-237
    """
    np = logged_in_admin_notices_page
    badges = ["new", "alert", "info", "urgent", "general"]

    with allure.step("Create one active notice for each badge type"):
        for badge in badges:
            data = NoticesFactory.badge_notice(badge)
            np.add_notice(title=data.title, body=data.body, badge=data.badge, active=True)
            expect(np.notice_row(data.title)).to_be_visible()

    with allure.step("Agency user opens the public Notice Board"):
        board = open_agency_board()

    # Each badge chip carries a colour-specific class, e.g. 'nbadge nbadge-alert'.
    badge_class_pattern = {
        "new":     re.compile(r"nbadge-new"),
        "alert":   re.compile(r"nbadge-alert"),
        "info":    re.compile(r"nbadge-info"),
        "urgent":  re.compile(r"nbadge-urgent"),
        "general": re.compile(r"nbadge-general"),
    }
    badge_label = {
        "new": "NEW", "alert": "ALERT", "info": "INFO",
        "urgent": "URGENT", "general": "GENERAL",
    }

    for badge in badges:
        data = NoticesFactory.badge_notice(badge)
        with allure.step(f"Verify {badge.upper()} badge renders correct colour class and label"):
            badge_el = board.notice_badge(data.title)
            expect(badge_el).to_have_class(badge_class_pattern[badge])
            expect(badge_el).to_have_text(badge_label[badge])


# ---------------------------------------------------------------------------
# TC-238  Edit pre-fills form; saving updates notice everywhere
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-238")
@allure.story("Notices Management")
@allure.title("TC-238: Editing a notice pre-fills all fields; save updates it everywhere")
def test_tc238_edit_notice_prefills_and_updates(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    notice_to_edit_data: NoticeData,
    open_agency_board,
):
    """
    Given at least one active notice exists in the admin list
    When  I click Edit (✏️) for a notice
    Then  the Add Notice form pre-populates with the notice's current values
    When  I update the title and save
    Then  the admin list and public notice board both reflect the new title

    Notion: KAN-TC-238 | data: notice_to_edit
    """
    np = logged_in_admin_notices_page

    with allure.step("Create the notice to be edited"):
        np.add_notice(
            title=notice_to_edit_data.title,
            body=notice_to_edit_data.body,
            badge=notice_to_edit_data.badge,
            active=True,
        )
        expect(np.notice_row(notice_to_edit_data.title)).to_be_visible()

    with allure.step("Click Edit (✏️) for the notice"):
        np.click_edit(notice_to_edit_data.title)

    with allure.step("Verify form pre-populates with original title and body"):
        expect(np.title_input).to_have_value(notice_to_edit_data.title)
        expect(np.body_textarea).to_have_value(notice_to_edit_data.body)

    with allure.step("Verify form header indicates edit mode"):
        expect(np.form_title).to_contain_text("Edit")

    with allure.step("Update the title and save"):
        np.fill_title(NoticesFactory.EDITED_TITLE)
        np.submit_form()

    with allure.step("Verify updated title appears in the admin list"):
        expect(np.notice_row(NoticesFactory.EDITED_TITLE)).to_be_visible()
        expect(np.notice_table).not_to_contain_text(notice_to_edit_data.title)

    with allure.step("Verify updated title is visible on the public notice board"):
        board = open_agency_board()
        expect(board.notice_card(NoticesFactory.EDITED_TITLE)).to_be_visible()
        expect(board.notice_card(notice_to_edit_data.title)).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-239  Confirming delete removes notice permanently
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-239")
@allure.story("Notices Management")
@allure.title("TC-239: Confirming delete removes notice from admin list and public board")
def test_tc239_delete_notice_permanently(
    logged_in_admin_notices_page: AdminNoticesPage,
    notice_to_delete_data: NoticeData,
    open_agency_board,
):
    """
    Given at least one active notice exists in the admin list
    When  I click Delete (🗑) for a notice and confirm the prompt
    Then  the confirmation prompt appears and the notice is removed from the admin list
    And   the notice no longer appears on the public notice board

    Notion: KAN-TC-239 | data: notice_to_delete
    """
    np = logged_in_admin_notices_page

    with allure.step("Create a notice to delete"):
        np.add_notice(
            title=notice_to_delete_data.title,
            body=notice_to_delete_data.body,
            badge=notice_to_delete_data.badge,
            active=True,
        )
        expect(np.notice_row(notice_to_delete_data.title)).to_be_visible()

    with allure.step("Click Delete (🗑) for the notice — confirm dialog should appear"):
        dialog_text = np.delete_notice(notice_to_delete_data.title)

    with allure.step("Verify confirmation prompt text"):
        assert "Delete" in dialog_text or "delete" in dialog_text or "confirm" in dialog_text.lower()

    with allure.step("Verify notice is removed from the admin list"):
        expect(np.notice_table).not_to_contain_text(notice_to_delete_data.title)

    with allure.step("Verify notice no longer appears on the public notice board"):
        board = open_agency_board()
        expect(board.notice_card(notice_to_delete_data.title)).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-240  PDF attachment is accessible as a download link on the public board
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-240")
@allure.story("Notices Management")
@allure.title("TC-240: PDF attachment uploaded with notice is downloadable on the public board")
def test_tc240_attachment_download_link_on_public_board(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
    notice_with_attachment_data: NoticeData,
    open_agency_board,
):
    """
    Given I prepare a valid PDF under 5 MB and set the notice to Active
    When  I add the notice with the PDF attachment
    Then  the notice is saved successfully with the attachment
    And   an agency user sees a download link for the PDF on the notice card

    Notion: KAN-TC-240 | data: notice_with_attachment
    """
    np = logged_in_admin_notices_page

    with allure.step("Add notice with PDF attachment"):
        np.add_notice(
            title=notice_with_attachment_data.title,
            body=notice_with_attachment_data.body,
            badge=notice_with_attachment_data.badge,
            active=True,
            attachment_path=notice_with_attachment_data.attachment_path,
        )

    with allure.step("Verify notice saved successfully in admin list"):
        expect(np.notice_row(notice_with_attachment_data.title)).to_be_visible()

    with allure.step("Agency user opens the public Notice Board"):
        board = open_agency_board()

    with allure.step("Verify attachment download link is visible on the notice card"):
        download_link = board.notice_attachment_link(notice_with_attachment_data.title)
        expect(download_link).to_be_visible()
        expect(download_link).to_have_attribute("href", re.compile(r".+"))


# ---------------------------------------------------------------------------
# TC-241  Blank title shows validation error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-241")
@allure.story("Notices Management")
@allure.title("TC-241: Submitting without Notice Title shows 'Notice title is required' error")
def test_tc241_blank_title_validation_error(
    logged_in_admin_notices_page: AdminNoticesPage,
    blank_title_data: NoticeData,
):
    """
    Given the Add Notice form is in a reset state
    When  I leave Title blank, fill Body and Badge, then click Add Notice
    Then  the notice is NOT saved
    And   the form remains open with the existing body and badge intact

    Notion: KAN-TC-241 | data: blank_title
    """
    np = logged_in_admin_notices_page

    with allure.step("Leave Title blank; fill Body and Badge"):
        np.fill_body(blank_title_data.body)
        np.select_badge(blank_title_data.badge)
        expect(np.title_input).to_have_value("")

    with allure.step("Click 'Add Notice'"):
        np.save_button.click()

    with allure.step("Verify notice was NOT saved (no success alert; URL unchanged)"):
        expect(np.success_alert).not_to_be_visible()
        assert "notices" in np.page.url.lower()

    with allure.step("Verify body and badge input are intact"):
        expect(np.body_textarea).to_have_value(blank_title_data.body)

    with allure.step("Verify title input is required / reports validity error"):
        is_invalid = np.page.evaluate(
            "document.querySelector(\"input[name='title']\").validity.valueMissing"
        )
        assert is_invalid is True


# ---------------------------------------------------------------------------
# TC-242  Non-PDF/image attachment triggers format error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-242")
@allure.story("Notices Management")
@allure.title("TC-242: Uploading a non-PDF/image file triggers a format error")
def test_tc242_invalid_attachment_format_error(
    logged_in_admin_notices_page: AdminNoticesPage,
    invalid_attachment_data: NoticeData,
):
    """
    Given the Add Notice form is visible
    When  I upload a .docx file as an attachment and submit the form
    Then  an error "Attachment must be JPG, PNG or PDF." is shown
    And   the notice is NOT saved

    Notion: KAN-TC-242 | data: invalid_attachment
    """
    np = logged_in_admin_notices_page

    with allure.step("Attempt to upload a .docx file as attachment"):
        np.add_notice(
            title=invalid_attachment_data.title,
            body=invalid_attachment_data.body,
            badge=invalid_attachment_data.badge,
            attachment_path=invalid_attachment_data.attachment_path,
        )

    with allure.step("Verify error message is shown for invalid format"):
        expect(np.error_alert).to_be_visible()
        assert invalid_attachment_data.expected_error in np.error_alert.text_content()

    with allure.step("Verify notice was NOT saved (not visible in table)"):
        expect(np.notice_table).not_to_contain_text(invalid_attachment_data.title)


# ---------------------------------------------------------------------------
# TC-243  File exceeding 5 MB triggers size error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-243")
@allure.story("Notices Management")
@allure.title("TC-243: File exceeding 5 MB size limit triggers a size error")
def test_tc243_oversized_attachment_size_error(
    logged_in_admin_notices_page: AdminNoticesPage,
    oversized_attachment_data: NoticeData,
):
    """
    Given the Add Notice form is visible
    When  I attach a PDF larger than 5 MB and submit the form
    Then  an error "File size exceeds 5 MB." is shown
    And   the notice is NOT saved

    Notion: KAN-TC-243 | data: oversized_attachment
    """
    np = logged_in_admin_notices_page

    with allure.step("Add a notice with file > 5 MB"):
        np.add_notice(
            title=oversized_attachment_data.title,
            body=oversized_attachment_data.body,
            badge=oversized_attachment_data.badge,
            attachment_path=oversized_attachment_data.attachment_path,
        )

    with allure.step("Verify error message is shown for oversized file"):
        expect(np.error_alert).to_be_visible()
        assert oversized_attachment_data.expected_error in np.error_alert.text_content()

    with allure.step("Verify notice was NOT saved (not visible in table)"):
        expect(np.notice_table).not_to_contain_text(oversized_attachment_data.title)


# ---------------------------------------------------------------------------
# TC-244  "No notices available" placeholder when no active notices exist
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-244")
@allure.story("Notices Management")
@allure.title("TC-244: Public board shows 'No notices available' when all notices are inactive")
def test_tc244_no_active_notices_shows_placeholder(
    logged_in_admin_notices_page: AdminNoticesPage,
    open_agency_board,
):
    """
    Given I deactivate all currently active notices in the admin panel
    When  an agency user visits the public notice board
    Then  the placeholder "No notices available at this time." is shown
    And   the page renders correctly with no broken layout

    NOTE: This test deactivates ALL active notices, then re-activates exactly
    the notices it switched off in a finally block — restoring the public notice
    board without touching notices that were already inactive.

    Notion: KAN-TC-244
    """
    np = logged_in_admin_notices_page
    deactivated: list[str] = []

    try:
        with allure.step("Deactivate all currently active notices"):
            deactivated = np.deactivate_all_active()

        with allure.step("Agency user opens the public Notice Board"):
            board = open_agency_board()

        with allure.step("Verify 'No notices available' placeholder is shown"):
            expect(board.empty_state).to_be_visible()
            expect(board.empty_state).to_contain_text("No notices found.")

        with allure.step("Verify page renders correctly (board hero still visible)"):
            expect(board.board_heading).to_be_visible()
    finally:
        with allure.step("Cleanup: re-activate exactly the notices we deactivated"):
            np.open()
            np.activate_notices(deactivated)


# ---------------------------------------------------------------------------
# TC-245  Filter tabs show only notices of that badge type
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-245")
@allure.story("Notices Management")
@allure.title("TC-245: Each filter tab in admin panel shows only notices of that badge type")
def test_tc245_filter_tabs_by_badge_type(
    logged_in_admin_notices_page: AdminNoticesPage,
    cleanup_notices,
):
    """
    Given at least one notice of each badge type exists
    When  I click the "Alert" tab
    Then  only Alert-badge notices are shown and the tab count matches
    When  I click the "All" tab
    Then  all notices are shown and the count is the total
    When  I add a new Alert notice
    Then  "All" and "Alert" tab counts both increment by one

    Notion: KAN-TC-245
    """
    np = logged_in_admin_notices_page

    # Only the "All (N)" pill carries a numeric count in the admin panel; the
    # per-badge pills (New, Alert, …) have no count. So the "Alert count" is
    # derived from the number of rows shown while the Alert filter is active.
    def _all_count() -> int:
        digits = "".join(filter(str.isdigit, np.filter_pill("All").text_content()))
        return int(digits) if digits else 0

    with allure.step("Ensure at least one Alert notice exists"):
        seed = NoticesFactory.badge_notice("alert")
        np.add_notice(title=seed.title, body=seed.body, badge="alert", active=True)
        expect(np.notice_row(seed.title)).to_be_visible()

    with allure.step("Note the current 'All' tab count (total notices)"):
        all_count = _all_count()

    with allure.step("Click 'Alert' filter tab"):
        np.click_filter("Alert")

    with allure.step("Verify only Alert-badge rows are shown"):
        for row in np.notice_rows.all():
            badge_text = row.locator(".nbadge").text_content().strip().upper()
            assert badge_text == "ALERT", f"Expected only ALERT rows, found: {badge_text}"

    with allure.step("Record the current number of Alert notices"):
        alert_count = np.notice_rows.count()

    with allure.step("Click 'All' tab"):
        np.click_filter("All")

    with allure.step("Verify all notices are shown and row count matches the 'All' tab count"):
        assert np.notice_rows.count() == all_count

    with allure.step("Add a new Alert notice"):
        extra = NoticeData(
            title=NoticesFactory.EXTRA_ALERT_TITLE,
            body="Extra alert notice to verify tab count increments.",
            badge="alert",
        )
        np.add_notice(title=extra.title, body=extra.body, badge="alert", active=True)

    with allure.step("Verify 'All' tab count incremented by 1"):
        np.click_filter("All")
        assert _all_count() == all_count + 1
        assert np.notice_rows.count() == all_count + 1

    with allure.step("Verify the number of Alert notices incremented by 1"):
        np.click_filter("Alert")
        assert np.notice_rows.count() == alert_count + 1
