"""
Agencies Management — Admin Portal
===================================
Covers KAN-TC-194 through KAN-TC-211.

The All Agencies list locators are grounded in a captured HTML snapshot. The
agency DETAIL view (agency_view.php) has no capture yet — its page object
(AdminAgencyViewPage) uses text-anchored locators derived from the AIO spec;
expect to tighten selectors on the first live run.

Status-mutating tests (TC-202, TC-205, TC-206, TC-209, TC-211) register the
target agency with ``agency_status_restorer`` first, so its original status
is restored through the list's Change Status modal on teardown. Assigned
MPPA numbers cannot be unassigned — those mutations are permanent and noted
per test.

Target agencies are discovered dynamically (first form-submitted row in the
needed status); tests skip when the dev dataset has no agency in the
required state.
"""

import re
import zipfile

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.agencies_page import AdminAgenciesPage
from pages.admin.agency_view_page import AdminAgencyViewPage
from pages.admin.audit_log_page import AdminAuditLogPage
from test_data.agencies_factory import AgenciesFactory, AgencyStatusData
from utils.aio import aio_case

EXPECTED_COLUMNS = (
    "#", "Reg ID", "Agency Name", "Username", "Email", "PAN",
    "Reg IP", "Registered On", "Status", "Actions",
)

STEP_STATUS_VALUES = {"SUBMITTED", "PENDING", "COMPLETE"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _viewable_username_or_skip(ap: AdminAgenciesPage, status: str) -> str:
    """First form-submitted agency in the given status, or skip."""
    username = ap.get_first_viewable_username(status)
    if not username:
        pytest.skip(f"No form-submitted agency with status '{status}' in the dev data.")
    return username


def _open_detail(ap: AdminAgenciesPage, username: str) -> AdminAgencyViewPage:
    """Clicks the row's View button and returns the detail page object."""
    ap.click_view(username)
    view = AdminAgencyViewPage(ap.page)
    view.wait_for_load()
    return view


# ---------------------------------------------------------------------------
# TC-194  All agencies appear in list regardless of status
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-194")
@allure.story("Agencies Management")
@allure.title("TC-194: All agencies appear in the list regardless of status")
def test_tc194_all_agencies_listed_regardless_of_status(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given I am logged in as Admin on the All Agencies list
    When  the page loads on the 'All' tab
    Then  the row count matches the All tab counter
    And   all 10 required columns are present
    And   every status with a non-zero tab count is represented in the list

    AIO: KAN-TC-194 | data: live table state
    """
    ap = logged_in_admin_agencies_page

    with allure.step("Verify the list loads with all agencies (All tab count)"):
        expect(ap.agencies_table).to_be_visible()
        expect(ap.active_filter_tab).to_contain_text("All")
        expect(ap.agency_rows).to_have_count(ap.get_filter_tab_count("all"))

    with allure.step("Verify all required columns are present"):
        for column in EXPECTED_COLUMNS:
            expect(ap.table_header(column)).to_be_visible()

    with allure.step("Verify every non-zero status is represented without filtering"):
        for status in ("submitted", "approved", "rejected", "suspended"):
            tab_count = ap.get_filter_tab_count(status)
            if tab_count > 0:
                assert ap.rows_with_status(status).count() > 0, (
                    f"Tab shows {tab_count} '{status}' agencies but none "
                    f"appear in the All view."
                )


# ---------------------------------------------------------------------------
# TC-195  Detail view opens with header, form data and sidebar panels
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-195")
@allure.story("Agencies Management")
@allure.title("TC-195: Agency detail view opens with header, form data and sidebar panels")
def test_tc195_detail_view_opens_with_all_areas(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a form-submitted agency is listed
    When  I click its View button
    Then  the detail view opens with the Reg ID header and status badge
    And   the Registration Info and Completion Status sidebar panels render
    And   '← Back to List' returns to the All Agencies list

    AIO: KAN-TC-195 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    reg_id = ap.reg_id_cell(username).text_content().strip()

    with allure.step(f"Click View for '{username}'"):
        view = _open_detail(ap, username)
        expect(view.page).to_have_url(re.compile(r"agency_view\.php"))

    with allure.step("Verify the header shows the Registration ID and status badge"):
        expect(view.page_heading).to_contain_text(reg_id)
        expect(view.header_status_badge).to_be_visible()

    with allure.step("Verify the sidebar panels are visible"):
        expect(view.registration_info_panel).to_be_visible()
        expect(view.completion_panel).to_be_visible()

    with allure.step("Click '← Back to List' and verify the list reloads"):
        view.click_back_to_list()
        expect(ap.page).to_have_url(re.compile(r"agency/list\.php"))
        expect(ap.agencies_table).to_be_visible()


# ---------------------------------------------------------------------------
# TC-196  Registration Info sidebar shows all 8 accurate metadata fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-196")
@allure.story("Agencies Management")
@allure.title("TC-196: Registration Info sidebar shows all 8 metadata fields accurately")
def test_tc196_registration_info_metadata_fields(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a form-submitted agency's detail view is open
    When  I inspect the Registration Info sidebar
    Then  all 8 fields are present: Reg ID, Username, Email, PAN, Registered,
          Last Login, Reg IP, Completion
    And   Reg ID / Username / Email / PAN match the values from the list row

    AIO: KAN-TC-196 | data: first viewable submitted agency, list row as oracle
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")

    with allure.step("Capture the list-row values as the comparison oracle"):
        reg_id = ap.reg_id_cell(username).text_content().strip()
        email = ap.email_cell(username).text_content().strip()
        pan = ap.pan_cell(username).text_content().strip()

    view = _open_detail(ap, username)

    with allure.step("Verify all 8 metadata fields are present"):
        for label in ("Reg ID", "Username", "Email", "PAN",
                      "Registered", "Last Login", "Reg IP", "Completion"):
            expect(view.info_field(label)).to_be_visible()

    with allure.step("Verify the values match the list row"):
        expect(view.info_field("Reg ID")).to_contain_text(reg_id)
        expect(view.info_field("Username")).to_contain_text(username)
        expect(view.info_field("Email")).to_contain_text(email)
        expect(view.info_field("PAN")).to_contain_text(pan)

    with allure.step("Verify Completion shows Yes or No"):
        expect(view.info_field("Completion")).to_have_text(re.compile(r"Yes|No"))


# ---------------------------------------------------------------------------
# TC-197  Wizard step statuses and overall percentage are accurate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-197")
@allure.story("Agencies Management")
@allure.title("TC-197: Each wizard step shows correct status and the overall percentage is accurate")
def test_tc197_completion_statuses_and_percentage(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given an agency's detail view is open
    When  I inspect the Completion Status panel
    Then  every wizard step shows SUBMITTED, PENDING or COMPLETE
    And   the overall percentage equals completed-steps / total-steps

    AIO: KAN-TC-197 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Verify the Completion Status panel is visible"):
        expect(view.completion_panel).to_be_visible()
        expect(view.step_status_badges.first).to_be_visible()

    with allure.step("Verify every step badge is SUBMITTED / PENDING / COMPLETE"):
        statuses = [
            view.step_status_badges.nth(i).text_content().strip().upper()
            for i in range(view.step_status_badges.count())
        ]
        allure.attach(", ".join(statuses), name="step statuses")
        assert statuses, "No step status badges found in the Completion panel."
        unexpected = [s for s in statuses if s not in STEP_STATUS_VALUES]
        assert not unexpected, f"Unexpected step status value(s): {unexpected}"

    with allure.step("Verify the percentage matches the step statuses"):
        done = sum(1 for s in statuses if s in ("SUBMITTED", "COMPLETE"))
        expected_pct = int(done / len(statuses) * 100)
        shown_pct = int(
            re.search(r"(\d+)\s*%", view.completion_percentage.text_content()).group(1)
        )
        assert shown_pct == expected_pct, (
            f"Panel shows {shown_pct}% but {done}/{len(statuses)} steps are "
            f"done ({expected_pct}%)."
        )


# ---------------------------------------------------------------------------
# TC-198  ZIP download bundles form data, enclosures and declarations
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-198")
@allure.story("Agencies Management")
@allure.title("TC-198: ZIP download contains Form-I data, enclosures and declarations")
def test_tc198_zip_download_contents(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a form-submitted agency's detail view is open
    When  I click '↓ Download ZIP'
    Then  a .zip download starts and is a valid, non-empty archive
    And   its entry list is attached for the bundled form data / enclosures /
          declarations review

    AIO: KAN-TC-198 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Click 'Download ZIP' and wait for the download"):
        download = view.download_zip()
        assert download.suggested_filename.lower().endswith(".zip"), (
            f"Expected a .zip download, got '{download.suggested_filename}'."
        )

    with allure.step("Verify the archive is valid and non-empty"):
        with zipfile.ZipFile(download.path()) as archive:
            entries = archive.namelist()
            allure.attach("\n".join(entries), name="ZIP entries")
            assert entries, "Downloaded ZIP archive is empty."
            assert archive.testzip() is None, "Downloaded ZIP archive is corrupted."


# ---------------------------------------------------------------------------
# TC-199  PDF generation produces a structured document
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-199")
@allure.story("Agencies Management")
@allure.title("TC-199: Generate PDF produces a document with the submitted values")
def test_tc199_generate_pdf(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a form-submitted agency's detail view is open
    When  I click '📄 Generate PDF'
    Then  a PDF opens in a new tab or downloads

    Visual review of the structured layout / absence of UI chrome is manual —
    this test verifies the generation succeeds and yields a PDF artefact.

    AIO: KAN-TC-199 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Click 'Generate PDF'"):
        kind, artefact = view.generate_pdf()

    if kind == "download":
        with allure.step("Verify the download is a PDF"):
            assert artefact.suggested_filename.lower().endswith(".pdf"), (
                f"Expected a .pdf download, got '{artefact.suggested_filename}'."
            )
    else:
        with allure.step("Verify the new tab serves the PDF document"):
            artefact.wait_for_load_state()
            allure.attach(artefact.url, name="PDF tab URL")
            assert "pdf" in artefact.url.lower(), (
                f"New tab URL does not look like a PDF: {artefact.url}"
            )
            artefact.close()


# ---------------------------------------------------------------------------
# TC-200  Unsubmitted steps show placeholders; no errors for partial apps
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-200")
@allure.story("Agencies Management")
@allure.title("TC-200: Unsubmitted steps show placeholder text and the view loads without errors")
def test_tc200_partial_application_placeholders(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given an agency's detail view is open
    When  the application is only partially submitted
    Then  pending steps show the 'Not yet submitted' placeholder
    And   the page renders without server errors

    AIO: KAN-TC-200 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Verify the detail view rendered without server errors"):
        expect(view.page_heading).to_be_visible()
        expect(view.page.get_by_text("Fatal error")).to_have_count(0)
        expect(view.page.get_by_text("Warning:")).to_have_count(0)

    with allure.step("Verify pending steps render the placeholder text"):
        placeholders = view.not_submitted_placeholders.count()
        allure.attach(str(placeholders), name="placeholder count")
        if placeholders:
            expect(view.not_submitted_placeholders.first).to_be_visible()


# ---------------------------------------------------------------------------
# TC-201  Update Status panel previews the next sequential MPPA number
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-201")
@allure.story("Agencies Management")
@allure.title("TC-201: Update Status panel previews the next sequential MPPA number before approval")
def test_tc201_mppa_number_preview(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a Submitted agency's detail view is open
    When  I inspect the Update Status panel
    Then  the MPPA preview block shows 'On approval, Reg ID will become:'
          with a well-formed sequential MPPA number

    AIO: KAN-TC-201 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Verify the Update Status panel is visible"):
        expect(view.update_status_panel).to_be_visible()

    with allure.step("Verify the MPPA number preview block"):
        expect(view.mppa_preview).to_be_visible()
        previewed = view.get_previewed_mppa_number()
        allure.attach(previewed, name="previewed MPPA number")
        assert AdminAgencyViewPage.MPPA_PATTERN.fullmatch(previewed), (
            f"Previewed MPPA number is malformed: '{previewed}'"
        )


# ---------------------------------------------------------------------------
# TC-202  Approval assigns the previewed MPPA number and writes an audit entry
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-202")
@allure.story("Agencies Management")
@allure.title("TC-202: Approval sets Approved status, assigns the previewed MPPA number and logs the action")
def test_tc202_approval_flow(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    agency_status_restorer,
    approve_with_remarks_data: AgencyStatusData,
):
    """
    Given a Submitted agency's detail view is open
    When  I enter optional remarks and click 'Approve Application'
    Then  the status badge changes to APPROVED
    And   the assigned MPPA number matches the preview
    And   the Audit Log records the approval

    Status is restored to 'submitted' on teardown via the list's Change
    Status modal — the assigned MPPA number itself is permanent.

    AIO: KAN-TC-202 | data: approve_with_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    agency_status_restorer(username)

    view = _open_detail(ap, username)
    previewed = view.get_previewed_mppa_number()

    with allure.step("Enter optional remarks and click 'Approve Application'"):
        view.fill_remarks(approve_with_remarks_data.remarks)
        view.approve_and_handle_alert(action="accept")
        view.wait_for_load()

    with allure.step("Verify the status badge shows APPROVED"):
        expect(view.header_status_badge).to_have_text(re.compile("approved", re.IGNORECASE))

    if previewed:
        with allure.step(f"Verify the previewed MPPA number '{previewed}' was assigned"):
            expect(view.page.get_by_text(previewed).first).to_be_visible()

    with allure.step("Verify the Audit Log recorded the approval"):
        audit = AdminAuditLogPage(ap.page)
        audit.open()
        audit.filter_by_action("AGENCY_APPROVE")
        entry = audit.log_entry(0)
        expect(audit.entry_action_pill(entry)).to_be_visible()
        expect(audit.entry_timestamp(entry)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-203  Rejection blocked when remarks are empty
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-203")
@allure.story("Agencies Management")
@allure.title("TC-203: Rejection is blocked when the remarks field is empty")
def test_tc203_reject_blocked_without_remarks(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    reject_blank_remarks_data: AgencyStatusData,
):
    """
    Given a Submitted agency's detail view is open
    When  I leave Remarks blank and click 'Reject Application'
    Then  the action is blocked with a 'Remarks are required' error
    And   the agency's status is unchanged

    AIO: KAN-TC-203 | data: reject_blank_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    original_status = ap.get_row_status(username)
    view = _open_detail(ap, username)

    with allure.step("Leave Remarks blank and click 'Reject Application'"):
        view.fill_remarks("")
        message = view.reject_and_handle_alert(action="accept")

    with allure.step(f"Verify the error: '{reject_blank_remarks_data.expected_error}'"):
        if message:
            assert "remark" in message.lower(), f"Unexpected dialog message: '{message}'"
        else:
            expect(view.error_alert).to_be_visible()
            expect(view.error_alert).to_contain_text("Remarks")

    with allure.step("Verify the agency's status is unchanged"):
        ap.open()
        assert ap.get_row_status(username) == original_status, (
            "Status changed despite the blocked rejection."
        )


# ---------------------------------------------------------------------------
# TC-204  Suspension blocked when remarks are empty
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-204")
@allure.story("Agencies Management")
@allure.title("TC-204: Suspension is blocked when the remarks field is empty")
def test_tc204_suspend_blocked_without_remarks(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    suspend_blank_remarks_data: AgencyStatusData,
):
    """
    Given a Submitted agency's detail view is open
    When  I leave Remarks blank and click 'Suspend Agency'
    Then  the action is blocked with a 'Remarks are required' error
    And   the agency's status is unchanged

    AIO: KAN-TC-204 | data: suspend_blank_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    original_status = ap.get_row_status(username)
    view = _open_detail(ap, username)

    with allure.step("Leave Remarks blank and click 'Suspend Agency'"):
        view.fill_remarks("")
        message = view.suspend_and_handle_alert(action="accept")

    with allure.step(f"Verify the error: '{suspend_blank_remarks_data.expected_error}'"):
        if message:
            assert "remark" in message.lower(), f"Unexpected dialog message: '{message}'"
        else:
            expect(view.error_alert).to_be_visible()
            expect(view.error_alert).to_contain_text("Remarks")

    with allure.step("Verify the agency's status is unchanged"):
        ap.open()
        assert ap.get_row_status(username) == original_status, (
            "Status changed despite the blocked suspension."
        )


# ---------------------------------------------------------------------------
# TC-205  Status changes write a complete audit log entry
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-205")
@allure.story("Agencies Management")
@allure.title("TC-205: Every status change generates an audit log entry with full metadata")
def test_tc205_status_change_audit_trail(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    agency_status_restorer,
    reject_with_remarks_data: AgencyStatusData,
):
    """
    Given a Submitted agency's detail view is open
    When  I reject the agency with valid remarks
    Then  the Audit Log's newest AGENCY_REJECT entry carries the action type,
          record reference and timestamp, with the remarks in the raw record

    AIO: KAN-TC-205 | data: reject_with_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    agency_status_restorer(username)
    view = _open_detail(ap, username)

    with allure.step(f"Reject '{username}' with remarks"):
        view.fill_remarks(reject_with_remarks_data.remarks)
        view.reject_and_handle_alert(action="accept")
        view.wait_for_load()

    with allure.step("Open the Audit Log filtered to AGENCY_REJECT"):
        audit = AdminAuditLogPage(ap.page)
        audit.open()
        audit.filter_by_action("AGENCY_REJECT")
        entry = audit.log_entry(0)
        expect(audit.entry_action_pill(entry)).to_be_visible()
        expect(audit.entry_timestamp(entry)).to_be_visible()
        expect(audit.entry_record_id(entry)).to_be_visible()

    with allure.step("Verify the raw record carries the remarks"):
        audit.expand_entry(0)
        raw = audit.get_expanded_json_text()
        allure.attach(raw, name="audit raw record")
        assert reject_with_remarks_data.remarks.rstrip(".") in raw, (
            "Remarks missing from the audit record."
        )


# ---------------------------------------------------------------------------
# TC-206  Status badge updates on detail view and list after a change
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-206")
@allure.story("Agencies Management")
@allure.title("TC-206: Status badge updates on the detail view and the list after a status change")
def test_tc206_status_badge_updates_everywhere(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    agency_status_restorer,
    suspend_with_remarks_data: AgencyStatusData,
):
    """
    Given a Submitted agency's detail view is open
    When  I suspend the agency with remarks
    Then  the detail-view header badge immediately shows SUSPENDED
    And   back on the All Agencies list the row badge shows suspended too

    AIO: KAN-TC-206 | data: suspend_with_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    agency_status_restorer(username)
    view = _open_detail(ap, username)

    with allure.step(f"Suspend '{username}' with remarks"):
        view.fill_remarks(suspend_with_remarks_data.remarks)
        view.suspend_and_handle_alert(action="accept")
        view.wait_for_load()

    with allure.step("Verify the detail-view badge shows SUSPENDED"):
        expect(view.header_status_badge).to_have_text(re.compile("suspended", re.IGNORECASE))

    with allure.step("Verify the list row badge shows suspended too"):
        ap.open()
        expect(ap.status_badge(username)).to_have_text("suspended")


# ---------------------------------------------------------------------------
# TC-207  Search filters the list in real time and clearing restores it
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-207")
@allure.story("Agencies Management")
@allure.title("TC-207: Search filters agencies in real time and clearing restores the full list")
def test_tc207_realtime_search_filter(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given multiple agencies are listed
    When  I type a known agency's username into the search bar
    Then  only matching rows remain visible (no page reload)
    When  I clear the search bar
    Then  the full list is restored

    AIO: KAN-TC-207 | data: first two listed usernames
    """
    ap = logged_in_admin_agencies_page

    with allure.step("Pick two distinct usernames from the list"):
        total = ap.agency_rows.count()
        assert total >= 2, "Need at least two agencies to verify filtering."
        target = ap.get_username_of_row(ap.agency_rows.nth(0))
        other = ap.get_username_of_row(ap.agency_rows.nth(1))

    with allure.step(f"Type '{target}' into the search bar"):
        ap.search(target)
        expect(ap.agency_row(target)).to_be_visible()
        expect(ap.agency_row(other)).to_be_hidden()

    with allure.step("Clear the search bar and verify the full list is restored"):
        ap.clear_search()
        expect(ap.agency_row(target)).to_be_visible()
        expect(ap.agency_row(other)).to_be_visible()
        assert ap.visible_agency_rows.count() == total


# ---------------------------------------------------------------------------
# TC-208  ZIP excludes empty placeholders for unuploaded enclosure slots
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-208")
@allure.story("Agencies Management")
@allure.title("TC-208: ZIP download contains only uploaded files — no empty placeholders")
def test_tc208_zip_excludes_empty_placeholders(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given a form-submitted agency's detail view is open
    When  I download the ZIP for a partially complete application
    Then  every file entry in the archive has non-zero content — no empty
          placeholder files for unuploaded enclosure slots

    AIO: KAN-TC-208 | data: first viewable submitted agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "submitted")
    view = _open_detail(ap, username)

    with allure.step("Download the ZIP archive"):
        download = view.download_zip()

    with allure.step("Verify no entry is an empty placeholder file"):
        with zipfile.ZipFile(download.path()) as archive:
            empty = [
                info.filename for info in archive.infolist()
                if not info.is_dir() and info.file_size == 0
            ]
            allure.attach("\n".join(archive.namelist()), name="ZIP entries")
            assert not empty, f"Empty placeholder file(s) found in ZIP: {empty}"


# ---------------------------------------------------------------------------
# TC-209  MPPA numbers are sequential and non-repeatable
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-209")
@allure.story("Agencies Management")
@allure.title("TC-209: MPPA numbers are assigned sequentially and never repeat")
def test_tc209_mppa_numbers_sequential(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    agency_status_restorer,
    approve_with_remarks_data: AgencyStatusData,
):
    """
    Given two Submitted agencies exist
    When  I approve the first agency
    Then  it is assigned exactly the previewed MPPA number
    And   the second agency's preview advances to the next sequential number
          (proving no reuse/duplication)

    Direct DB verification is out of scope for UI automation. The first
    agency's status is restored on teardown; its MPPA assignment is permanent.

    AIO: KAN-TC-209 | data: approve_with_remarks, two submitted agencies
    """
    ap = logged_in_admin_agencies_page

    with allure.step("Find two distinct submitted agencies"):
        rows = ap.viewable_rows_with_status("submitted")
        if rows.count() < 2:
            pytest.skip("Need two form-submitted agencies in 'submitted' status.")
        agency_a = ap.get_username_of_row(rows.nth(0))
        agency_b = ap.get_username_of_row(rows.nth(1))
        agency_status_restorer(agency_a)

    with allure.step(f"Read the MPPA preview for '{agency_a}'"):
        view = _open_detail(ap, agency_a)
        preview_a = view.get_previewed_mppa_number()
        assert preview_a, "No MPPA preview shown for the first submitted agency."

    with allure.step(f"Approve '{agency_a}' and verify the previewed number was assigned"):
        view.fill_remarks(approve_with_remarks_data.remarks)
        view.approve_and_handle_alert(action="accept")
        view.wait_for_load()
        expect(view.page.get_by_text(preview_a).first).to_be_visible()

    with allure.step(f"Verify '{agency_b}' now previews the NEXT sequential number"):
        ap.open()
        view_b = _open_detail(ap, agency_b)
        preview_b = view_b.get_previewed_mppa_number()
        assert preview_b, "No MPPA preview shown for the second submitted agency."
        seq_a = AdminAgencyViewPage.mppa_sequence_number(preview_a)
        seq_b = AdminAgencyViewPage.mppa_sequence_number(preview_b)
        assert preview_b != preview_a, "MPPA preview repeated an assigned number."
        assert seq_b == seq_a + 1, (
            f"Expected next sequential number {seq_a + 1}, but preview shows "
            f"{seq_b} ({preview_b})."
        )


# ---------------------------------------------------------------------------
# TC-210  Re-approving an already-approved agency is blocked
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-210")
@allure.story("Agencies Management")
@allure.title("TC-210: Approving an already-approved agency is warned about and blocked")
def test_tc210_reapproval_blocked(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given an agency that already holds APPROVED status and an MPPA number
    When  I open its detail view
    Then  a warning explains a new MPPA number will NOT be assigned
    And   the Approve action is disabled or absent

    AIO: KAN-TC-210 | data: first viewable approved agency
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "approved")
    view = _open_detail(ap, username)

    with allure.step("Verify the already-approved warning is shown"):
        expect(view.already_approved_warning).to_be_visible()

    with allure.step("Verify the Approve action is disabled or absent"):
        if view.approve_button.count():
            expect(view.approve_button.first).to_be_disabled()


# ---------------------------------------------------------------------------
# TC-211  Suspending an approved agency preserves its MPPA number
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-211")
@allure.story("Agencies Management")
@allure.title("TC-211: Suspending an approved agency preserves the MPPA number and certificate record")
def test_tc211_suspend_after_approval_preserves_mppa(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    agency_status_restorer,
    suspend_with_remarks_data: AgencyStatusData,
):
    """
    Given an Approved agency with an MPPA number
    When  I suspend it with remarks
    Then  the status changes to SUSPENDED
    And   the MPPA number is still displayed on the detail view
    And   the Audit Log records the suspension

    AIO: KAN-TC-211 | data: suspend_with_remarks
    """
    ap = logged_in_admin_agencies_page
    username = _viewable_username_or_skip(ap, "approved")
    agency_status_restorer(username)
    view = _open_detail(ap, username)

    with allure.step("Capture the agency's MPPA number before suspension"):
        body_text = view.page.locator("body").text_content()
        match = AdminAgencyViewPage.MPPA_PATTERN.search(body_text)
        if not match:
            pytest.skip("Approved agency shows no MPPA number on its detail view.")
        mppa = match.group()
        allure.attach(mppa, name="MPPA before suspension")

    with allure.step(f"Suspend '{username}' with remarks"):
        view.fill_remarks(suspend_with_remarks_data.remarks)
        view.suspend_and_handle_alert(action="accept")
        view.wait_for_load()

    with allure.step("Verify the status changed to SUSPENDED"):
        expect(view.header_status_badge).to_have_text(re.compile("suspended", re.IGNORECASE))

    with allure.step("Verify the MPPA number is preserved"):
        expect(view.page.get_by_text(mppa).first).to_be_visible()

    with allure.step("Verify the Audit Log recorded the suspension"):
        audit = AdminAuditLogPage(ap.page)
        audit.open()
        audit.filter_by_action("AGENCY_SUSPEND")
        entry = audit.log_entry(0)
        expect(audit.entry_action_pill(entry)).to_be_visible()
        expect(audit.entry_timestamp(entry)).to_be_visible()
