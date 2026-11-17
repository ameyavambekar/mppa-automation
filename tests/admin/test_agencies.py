"""
Agencies Management — Admin Portal (KAN-25)
============================================
Covers KAN-TC-194 through KAN-TC-210 on the redesigned Officer Console (dev, 17-Nov-2026):

* the Applications list (agency/list.php) — stage cards Desktop scrutiny / Physical verification / Branch office
  verification, tabs All applications / Revert for compliance — with agency / Approved / Rejected / Suspended /
  cancelled, columns Application, District, Current step, Compliance, 45-day period, Action, and a search form
  submitted with Search (not live filtering);
* an application's page (dashboard/agency_view.php) — header with the Registration ID and status pill, Form-I
  data in eight step sections, Registration Info and Completion Status panels, Download documents (ZIP) and
  Application PDF.

All tests here are read-only. The old list's Change Status modal and the agency page's Update Status panel
(Approve / Reject / Suspend with remarks and an MPPA number preview) no longer exist: decisions now go through the
review workflow (KAN-12, tests/admin/test_application_review.py), suspension and cancellation through Compliance
cases (KAN-46), and certificate numbers are covered by KAN-28. TC-200…204, 206 and 209 therefore skip with the
reason; their AIO cases are Deprecated (17-Nov-2026). KAN-TC-205 moved to KAN-12 and KAN-TC-211 to KAN-46, so they
have no test here.

Known failures (dev, 17-Nov-2026 — possible defects, not yet logged):
* TC-196 / TC-197 — every submitted application's Completion Status reads 0/8 (0 %), all steps PENDING, and
  Registration Info shows "Complete: ✕ No".
* TC-198 / TC-208 — Download documents (ZIP) returns an empty archive (22 bytes, no files).
* TC-199 — Application PDF returns HTTP 500 with an empty body.
"""

import re
import zipfile

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.agencies_page import AdminAgenciesPage
from pages.admin.agency_view_page import AdminAgencyViewPage
from test_data.agencies_factory import AgencySearchData, CompletionData, RegistrationInfoData
from utils.aio import aio_case

_GONE = ("The redesigned Officer Console (dev, 17-Nov-2026) has no {what}; {where}. "
         "AIO case needs rewording or deprecating.")


def _open_review(ap: AdminAgenciesPage, application: dict) -> AdminAgencyViewPage:
    """Clicks the application's Review / View link on the All applications list."""
    ap.click_review(application["application_id"])
    return AdminAgencyViewPage(ap.page)


# ---------------------------------------------------------------------------
# TC-194  Every submitted application appears in the list, whatever its status
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-194")
@allure.story("Agencies Management")
@allure.title("TC-194: All applications lists every submitted application, whatever its status")
def test_tc194_all_agencies_listed_regardless_of_status(
    logged_in_admin_agencies_page: AdminAgenciesPage,
):
    """
    Given I am logged in as the Super Admin on Applications → All applications
    When  the page loads
    Then  the heading, the three stage cards and the five tabs show, with All applications active
    And   the All applications count equals the number of rows, and the six columns are present
    And   every application under each stage card and tab is also listed under All applications

    AIO: KAN-TC-194 | data: live list on dev
    """
    ap = logged_in_admin_agencies_page

    with allure.step("Verify the heading, stage cards and tabs"):
        expect(ap.heading).to_have_text(ap.TITLE)
        expect(ap.page).to_have_title(ap.PAGE_TITLE)
        expect(ap.stage_cards).to_have_count(len(ap.STAGE_LABELS))
        for view, label in ap.STAGE_LABELS.items():
            expect(ap.view_link(view)).to_contain_text(label)
        expect(ap.tabs).to_have_count(len(ap.TAB_LABELS))
        for view, label in ap.TAB_LABELS.items():
            expect(ap.view_link(view)).to_contain_text(label)
        expect(ap.active_tab).to_contain_text(ap.TAB_LABELS["all"])

    with allure.step("Verify the columns"):
        expect(ap.table_headers).to_have_text(list(ap.COLUMNS), ignore_case=True)

    with allure.step("Verify the All applications count equals the listed rows"):
        all_ids = ap.application_ids()
        if not all_ids:
            pytest.skip("No submitted application on dev.")
        assert ap.view_count("all") == len(all_ids), \
            f"All applications tab shows {ap.view_count('all')}, the list has {len(all_ids)} rows"
        assert len(set(all_ids)) == len(all_ids), f"An application is listed twice: {all_ids}"

    with allure.step("Verify every stage card's and tab's applications are also under All applications"):
        missing = {}
        for view in (*ap.STAGE_LABELS, *[v for v in ap.TAB_LABELS if v != "all"]):
            ids = ap.ids_in_view(view)
            assert ap.view_count(view) == len(ids), \
                f"'{view}' shows count {ap.view_count(view)} but lists {len(ids)} rows"
            extra = set(ids) - set(all_ids)
            if extra:
                missing[view] = sorted(extra)
        assert not missing, f"Applications missing from All applications: {missing}"


# ---------------------------------------------------------------------------
# TC-195  The application page opens with header, form data and panels
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-195")
@allure.story("Agencies Management")
@allure.title("TC-195: Review opens the application page with header, Form-I sections and panels")
def test_tc195_detail_view_opens_with_all_areas(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
):
    """
    Given I am on Applications → All applications
    When  I click Review / View for an application
    Then  its page shows the Registration ID as the title, a status pill and the header actions
    And   the eight Form-I step sections, Registration Info and Completion Status
    When  I click Back to list
    Then  the Applications list shows again

    AIO: KAN-TC-195 | data: first application under All applications
    """
    ap = logged_in_admin_agencies_page
    app_id = listed_application["application_id"]

    with allure.step(f"Click Review / View for {app_id}"):
        view = _open_review(ap, listed_application)
        expect(view.page).to_have_url(re.compile(rf"agency_view\.php\?id={listed_application['view_id']}$"))
        expect(view.page).to_have_title(view.TAB_TITLE)

    with allure.step("Verify the header"):
        expect(view.eyebrow).to_have_text(view.EYEBROW)
        expect(view.title).to_have_text(app_id)
        expect(view.registration_chip).to_contain_text(app_id)
        expect(view.status_pill).to_be_visible()
        expect(view.status_pill).not_to_be_empty()
        for label in ("Stage", "District", "Type", "Submitted"):
            expect(view.header_item(label)).to_be_visible()
        expect(view.back_to_list_link).to_be_visible()
        expect(view.download_zip_link).to_be_visible()
        expect(view.application_pdf_link).to_be_visible()

    with allure.step("Verify the eight Form-I step sections (expanding Full application when under review)"):
        view.expand_full_application()
        expect(view.step_titles).to_have_text(list(view.STEP_SECTIONS))
        for i in range(len(view.STEP_SECTIONS)):
            expect(view.step_titles.nth(i)).to_be_visible()

    with allure.step("Verify the Registration Info and Completion Status panels"):
        expect(view.info_panel).to_be_visible()
        expect(view.completion_panel).to_be_visible()

    with allure.step("Click Back to list and verify the Applications list shows"):
        view.click_back_to_list()
        expect(ap.heading).to_have_text(ap.TITLE)
        expect(ap.row(app_id)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-196  Registration Info shows all 8 fields with correct values
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-196")
@allure.story("Agencies Management")
@allure.title("TC-196: Registration Info shows all 8 fields with values matching the application")
def test_tc196_registration_info_metadata_fields(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
    registration_info_data: RegistrationInfoData,
):
    """
    Given I open the page of a submitted application
    Then  Registration Info lists Reg ID, Username, Email, PAN, Registered, Last Login, Reg. IP and Complete
    And   Reg ID is the Application ID, Email matches the list row, and each value has its expected format
    And   Complete reads Yes (the application was submitted and paid)

    AIO: KAN-TC-196 | data: registration_info_formats
    Known failure (dev, 17-Nov-2026): Complete reads "✕ No" for every submitted application.
    """
    view = _open_review(logged_in_admin_agencies_page, listed_application)

    with allure.step("Verify all 8 fields are present"):
        for label in view.INFO_FIELDS:
            expect(view.info_row(label)).to_have_count(1)

    with allure.step("Verify Reg ID and Email match the list"):
        assert view.info_value("Reg ID") == listed_application["application_id"]
        assert view.info_value("Email").lower() == listed_application["email"].lower(), \
            f"Email {view.info_value('Email')!r} differs from the list's {listed_application['email']!r}"

    with allure.step("Verify each value's format"):
        bad = {label: view.info_value(label) for label, pattern in registration_info_data.patterns.items()
               if not pattern.match(view.info_value(label))}
        assert not bad, f"Registration Info values in an unexpected format: {bad}"

    with allure.step("Verify Complete reads Yes for a submitted application"):
        expect(view.info_row("Complete")).to_contain_text(registration_info_data.complete_value)


# ---------------------------------------------------------------------------
# TC-197  Step statuses and the percentage are accurate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-197")
@allure.story("Agencies Management")
@allure.title("TC-197: Completion Status shows each step's status and a consistent percentage")
def test_tc197_completion_statuses_and_percentage(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
    completion_data: CompletionData,
):
    """
    Given I open the page of a submitted application
    Then  Completion Status lists the 8 steps, each SUBMITTED, PENDING or COMPLETE
    And   the summary "N/8 steps complete" agrees with the step statuses and the percentage is N/8
    And   no step of a submitted (paid) application is PENDING

    AIO: KAN-TC-197 | data: completion_of_submitted
    Known failure (dev, 17-Nov-2026): every submitted application reads 0/8 (0 %) with all steps PENDING.
    """
    view = _open_review(logged_in_admin_agencies_page, listed_application)

    with allure.step("Verify the 8 steps and their statuses"):
        statuses = view.completion_statuses()
        assert list(statuses) == list(view.COMPLETION_STEPS), f"Completion steps differ: {list(statuses)}"
        odd = {s: v for s, v in statuses.items() if v not in completion_data.allowed_statuses}
        assert not odd, f"Unexpected step statuses: {odd}"

    with allure.step("Verify the summary and percentage agree with the steps"):
        done, total, pct = view.completion_counts()
        assert total == completion_data.total_steps, f"Summary total is {total}"
        not_pending = sum(1 for v in statuses.values() if v != completion_data.submitted_status_expected)
        assert done == not_pending, f"Summary says {done}/{total}, steps show {not_pending} not pending"
        assert pct == int(done * 100 / total), f"{done}/{total} shown as {pct}%"

    with allure.step("Verify no step of a submitted application is PENDING"):
        pending = [s for s, v in statuses.items() if v == completion_data.submitted_status_expected]
        assert not pending, (f"Application {listed_application['application_id']} was submitted and paid, "
                             f"but Completion Status shows {done}/{total} ({pct}%) with PENDING steps: {pending}")


# ---------------------------------------------------------------------------
# TC-198  The ZIP holds the application's documents
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-198")
@allure.story("Agencies Management")
@allure.title("TC-198: Download documents (ZIP) gives a ZIP of the application's documents")
def test_tc198_zip_download_contents(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
    tmp_path,
):
    """
    Given I open the page of a submitted application
    When  I click Download documents (ZIP)
    Then  a file "<Application ID>.zip" downloads
    And   it is a valid ZIP holding at least one document

    AIO: KAN-TC-198 | data: first application under All applications
    Known failure (dev, 17-Nov-2026): the ZIP is empty (22 bytes).
    """
    view = _open_review(logged_in_admin_agencies_page, listed_application)

    with allure.step("Click Download documents (ZIP)"):
        download = view.download_zip()
        target = tmp_path / download.suggested_filename
        download.save_as(target)
        assert download.suggested_filename == f"{listed_application['application_id']}.zip"

    with allure.step("Verify the ZIP is valid and holds documents"):
        assert zipfile.is_zipfile(target), f"{target.name} is not a ZIP ({target.stat().st_size} bytes)"
        with zipfile.ZipFile(target) as zf:
            names = [i.filename for i in zf.infolist() if not i.is_dir()]
        allure.attach("\n".join(names) or "(empty)", name="ZIP entries", attachment_type=allure.attachment_type.TEXT)
        assert names, f"{target.name} is an empty archive ({target.stat().st_size} bytes)"


# ---------------------------------------------------------------------------
# TC-199  Application PDF
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-199")
@allure.story("Agencies Management")
@allure.title("TC-199: Application PDF returns a PDF document")
def test_tc199_generate_pdf(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
):
    """
    Given I open the page of a submitted application
    When  I click Application PDF (it opens in a new tab)
    Then  the response is HTTP 200 with a PDF body

    AIO: KAN-TC-199 | data: first application under All applications
    Known failure (dev, 17-Nov-2026): HTTP 500 with an empty body.
    """
    view = _open_review(logged_in_admin_agencies_page, listed_application)

    with allure.step("Verify the Application PDF link opens in a new tab"):
        expect(view.application_pdf_link).to_have_attribute("target", "_blank")

    with allure.step("Click Application PDF and verify the new tab receives a PDF"):
        response, tab = view.open_application_pdf()
        try:
            body = response.body()
        except Exception:  # a PDF the browser hands to its viewer / download may not expose a body
            body = b""
        finally:
            tab.close()
        content_type = response.headers.get("content-type", "")
        page_title = re.search(rb"<title>(.*?)</title>", body, re.S)
        seen = (f"HTTP {response.status}, {content_type!r}, {len(body)} bytes"
                + (f", HTML page titled {page_title.group(1).decode('utf-8', 'replace').strip()!r}" if page_title else ""))
        allure.attach(seen, name="Application PDF response", attachment_type=allure.attachment_type.TEXT)
        assert response.status == 200, f"Application PDF returned {seen}"
        assert "application/pdf" in content_type, f"Application PDF is not a PDF: {seen}"
        assert not body or body.startswith(b"%PDF"), f"Body does not start with %PDF: {body[:20]!r}"


# ---------------------------------------------------------------------------
# TC-200 … TC-206  Flows the redesign removed
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-200")
@allure.story("Agencies Management")
@allure.title("TC-200: Unsubmitted steps show placeholder text (not on the redesigned list)")
def test_tc200_partial_application_placeholders():
    """AIO: KAN-TC-200 — partly filled applications are not on the Applications list."""
    pytest.skip(_GONE.format(what="partly filled application on the Applications list",
                             where="drafts are under Registrations in progress (KAN-45)"))


@aio_case("KAN-TC-201")
@allure.story("Agencies Management")
@allure.title("TC-201: MPPA number preview before approval (removed)")
def test_tc201_mppa_number_preview():
    """AIO: KAN-TC-201 — the Update Status panel and its MPPA number preview are gone."""
    pytest.skip(_GONE.format(what="Update Status panel or MPPA number preview",
                             where="approval runs through the review workflow (KAN-12) and certificates (KAN-28)"))


@aio_case("KAN-TC-202")
@allure.story("Agencies Management")
@allure.title("TC-202: Approval from the agency page (removed)")
def test_tc202_approval_flow():
    """AIO: KAN-TC-202 — approval is the two-stage review workflow now."""
    pytest.skip(_GONE.format(what="Approve Application button",
                             where="approval is the two-stage review workflow (KAN-12, test_application_review.py)"))


@aio_case("KAN-TC-203")
@allure.story("Agencies Management")
@allure.title("TC-203: Rejection blocked without remarks (removed)")
def test_tc203_reject_blocked_without_remarks():
    """AIO: KAN-TC-203 — refusal is part of the review workflow now."""
    pytest.skip(_GONE.format(what="Reject Application button with remarks",
                             where="refusal is part of the review workflow (KAN-12)"))


@aio_case("KAN-TC-204")
@allure.story("Agencies Management")
@allure.title("TC-204: Suspension blocked without remarks (removed)")
def test_tc204_suspend_blocked_without_remarks():
    """AIO: KAN-TC-204 — suspension goes through Compliance cases now."""
    pytest.skip(_GONE.format(what="Suspend Agency button",
                             where="suspension and cancellation go through Compliance cases (KAN-46)"))


@aio_case("KAN-TC-206")
@allure.story("Agencies Management")
@allure.title("TC-206: Status badge updates after a status change (removed)")
def test_tc206_status_badge_updates_everywhere():
    """AIO: KAN-TC-206 — there is no status change on the agency page."""
    pytest.skip(_GONE.format(what="status change on the agency page",
                             where="the review workflow (KAN-12) moves applications between tabs"))


# ---------------------------------------------------------------------------
# TC-207  Search by name, Application ID, e-mail and PAN
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-207")
@allure.story("Agencies Management")
@allure.title("TC-207: Search finds an application by name, Application ID, e-mail and PAN; clearing restores the list")
def test_tc207_realtime_search_filter(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
    agency_search_data: AgencySearchData,
):
    """
    Given I am on Applications → All applications
    When  I search by the agency name, Application ID, e-mail and PAN of one application in turn
    Then  each search lists that application, and the search box keeps the query
    When  I search for text that matches nothing
    Then  the list shows "No applications in this list."
    When  I clear the search
    Then  the full list is restored

    AIO: KAN-TC-207 | data: search_by_each_field
    The search runs on the server when Search is clicked; the list does not filter as you type.
    """
    ap = logged_in_admin_agencies_page
    app_id = listed_application["application_id"]
    full_count = ap.view_count("all")

    with allure.step("Read the application's PAN from its page"):
        view = AdminAgencyViewPage(ap.page)
        view.open(listed_application["view_id"])
        values = {**listed_application, "pan": view.info_value("PAN")}
        ap.open("all")

    with allure.step("Verify the search box placeholder"):
        expect(ap.search_input).to_have_attribute("placeholder", ap.SEARCH_PLACEHOLDER)

    for field in agency_search_data.fields:
        with allure.step(f"Search by {field} '{values[field]}' and verify {app_id} is listed"):
            ap.search(values[field])
            expect(ap.search_input).to_have_value(values[field])
            expect(ap.row(app_id)).to_have_count(1)
            if field == "application_id":
                expect(ap.rows).to_have_count(1)
            assert len(ap.application_ids()) < full_count or full_count == 1, \
                f"Search by {field} did not narrow the list ({full_count} rows)"

    with allure.step("Search for text that matches nothing"):
        ap.search(agency_search_data.no_match_query)
        expect(ap.rows).to_have_count(0)
        expect(ap.empty_row).to_have_text(ap.EMPTY)

    with allure.step("Clear the search and verify the full list is restored"):
        ap.clear_search()
        expect(ap.rows).to_have_count(full_count)


# ---------------------------------------------------------------------------
# TC-208  The ZIP has no empty files
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-208")
@allure.story("Agencies Management")
@allure.title("TC-208: Download documents (ZIP) holds only real files — no empty placeholders")
def test_tc208_zip_excludes_empty_placeholders(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    listed_application: dict,
    tmp_path,
):
    """
    Given I open the page of a submitted application
    When  I download the documents ZIP
    Then  it holds at least one file and no file is zero bytes

    AIO: KAN-TC-208 | data: first application under All applications
    Known failure (dev, 17-Nov-2026): the ZIP is empty (22 bytes).
    """
    view = _open_review(logged_in_admin_agencies_page, listed_application)

    with allure.step("Download the documents ZIP"):
        download = view.download_zip()
        target = tmp_path / download.suggested_filename
        download.save_as(target)

    with allure.step("Verify the ZIP holds files and none is empty"):
        assert zipfile.is_zipfile(target), f"{target.name} is not a ZIP"
        with zipfile.ZipFile(target) as zf:
            files = [i for i in zf.infolist() if not i.is_dir()]
        assert files, f"{target.name} is an empty archive ({target.stat().st_size} bytes)"
        empty = [i.filename for i in files if i.file_size == 0]
        assert not empty, f"Empty placeholder files in the ZIP: {empty}"


# ---------------------------------------------------------------------------
# TC-209  MPPA numbers (removed)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-209")
@allure.story("Agencies Management")
@allure.title("TC-209: MPPA numbers are sequential (moved)")
def test_tc209_mppa_numbers_sequential():
    """AIO: KAN-TC-209 — no MPPA number is assigned on the agency page any more."""
    pytest.skip(_GONE.format(what="MPPA number assignment on the agency page",
                             where="certificate numbers are covered by KAN-28 (test_certificates.py)"))


# ---------------------------------------------------------------------------
# TC-210  An approved application cannot be approved again
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-210")
@allure.story("Agencies Management")
@allure.title("TC-210: An approved application is read only — it cannot be approved again")
def test_tc210_reapproval_blocked(
    logged_in_admin_agencies_page: AdminAgenciesPage,
    approved_application: dict,
):
    """
    Given an application under the Approved tab
    When  I open its page
    Then  the status pill reads Approved and a read-only notice says the certificate has been issued
    And   no decision buttons (approve, clear, refuse, revert) are offered

    AIO: KAN-TC-210 | data: first application under Approved
    """
    view = AdminAgencyViewPage(logged_in_admin_agencies_page.page)
    view.open(approved_application["view_id"])

    with allure.step("Verify the Approved pill and the read-only notice"):
        expect(view.title).to_have_text(approved_application["application_id"])
        expect(view.status_pill).to_have_text(re.compile(r"Approved", re.I))
        expect(view.read_only_notice).to_be_visible()
        expect(view.read_only_notice).to_contain_text(view.READ_ONLY_NOTICE)

    with allure.step("Verify no decision buttons are offered"):
        expect(view.decision_buttons).to_have_count(0)
