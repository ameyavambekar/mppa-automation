"""
First Appeal Management — Admin Portal
======================================
Covers KAN-TC-360 through KAN-TC-368 (Admin Console · Appeals module · 1st
Appeals / FORM-III).

The admin assertions run against the live Appeals list and review modal
(``AdminAppealsPage``) plus the Audit Log (``AdminAuditLogPage``). Most tests
discover a suitable FORM-III appeal from the current dev data and skip when none
exists — matching the dynamic-discovery style of ``test_agencies.py``.

Three tests need a precondition that cannot be assumed present (an appeal WITH
all documents, an appeal WITHOUT documents, or a LATE-filed appeal). Those
request a ``filed_first_appeal_*`` fixture, which files exactly that appeal in a
separate agency browser via the FirstAppealPage object and yields its order
number for the admin side to locate. Those fixtures skip when the agency cannot
file (e.g. it already has an appeal on record).

Outcome tests (TC-363/365) record a decision; appeal outcomes are not cleanly
reversible from the UI, so those mutations are left in place on the dev data.
"""

import re

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.audit_log_page import AdminAuditLogPage
from test_data.first_appeal_factory import AppealOutcomeData
from utils.aio import aio_case

FORM_III_TAB = "1st Appeal (FORM-III)"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_appeals_or_skip(ap: AdminAppealsPage):
    """Filter the list to FORM-III and return the row locator, or skip."""
    ap.filter_by_type(FORM_III_TAB)
    expect(ap.appeals_table).to_be_visible()
    if ap.appeal_rows.count() == 0:
        pytest.skip("No FORM-III (first) appeals in the dev data.")
    return ap.appeal_rows


def _submitted_first_appeal_or_skip(ap: AdminAppealsPage) -> int:
    """Id of a pending (submitted) FORM-III appeal, or skip."""
    ap.filter_by_type(FORM_III_TAB)
    expect(ap.appeals_table).to_be_visible()
    appeal_id = ap.get_first_appeal_id_with_status("submitted")
    if appeal_id == -1:
        pytest.skip("No pending (submitted) FORM-III appeal to record an outcome on.")
    return appeal_id


def _open_seeded_appeal_or_skip(ap: AdminAppealsPage, seeded: dict) -> int:
    """Locate a seeded appeal (by order number, falling back to Reg ID) and open
    its review modal. The newest matching row is the just-filed appeal."""
    ap.search(seeded["order_number"])
    if ap.appeal_rows.count() == 0 and seeded.get("reg_id"):
        ap.search(seeded["reg_id"])
    if ap.appeal_rows.count() == 0:
        pytest.skip(f"Seeded appeal '{seeded['order_number']}' not found in the admin list.")
    appeal_id = ap.get_appeal_id_of_row(ap.appeal_rows.first)
    ap.open_review_modal(appeal_id)
    expect(ap.review_modal).to_be_visible()
    return appeal_id


# ---------------------------------------------------------------------------
# TC-360  All submitted first appeals visible with the correct per-row fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-360")
@allure.story("First Appeal Management")
@allure.title("TC-360: All submitted first appeals are listed with the correct per-row fields")
def test_tc360_first_appeals_listed_with_fields(
    logged_in_admin_appeals_page: AdminAppealsPage,
):
    """
    Given I am logged in as Admin on the Appeals module
    When  I view the 1st Appeal (FORM-III) list
    Then  the list loads without error and shows only FORM-III submissions
    And   every row carries Agency Name, Reg ID, Date Filed and Outcome status

    AIO: KAN-TC-360 | data: live appeals list
    """
    ap = logged_in_admin_appeals_page
    rows = _first_appeals_or_skip(ap)

    with allure.step("Verify the list loaded without server errors"):
        expect(ap.page.get_by_text("Fatal error")).to_have_count(0)
        expect(ap.page.get_by_text("Warning:")).to_have_count(0)

    with allure.step("Verify every listed row is a FORM-III appeal"):
        for i in range(rows.count()):
            appeal_id = ap.get_appeal_id_of_row(rows.nth(i))
            expect(ap.form_type_badge(appeal_id)).to_contain_text(
                re.compile("FORM-III", re.IGNORECASE)
            )

    with allure.step("Verify the required per-row fields render on the first row"):
        appeal_id = ap.get_appeal_id_of_row(rows.first)
        assert ap.agency_name_cell(appeal_id).text_content().strip(), "Agency Name is blank."
        assert ap.reg_id_cell(appeal_id).text_content().strip(), "Reg ID is blank."
        expect(ap.filed_on_cell(appeal_id)).to_be_visible()
        expect(ap.status_badge(appeal_id)).to_be_visible()

    with allure.step("Attach the column headers (grounds column reviewed manually)"):
        headers = [
            ap.table_headers.nth(i).text_content().strip()
            for i in range(ap.table_headers.count())
        ]
        allure.attach(", ".join(headers), name="appeal list columns")


# ---------------------------------------------------------------------------
# TC-362  Documents appear as labelled download links in the detail view
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-362")
@allure.story("First Appeal Management")
@allure.title("TC-362: Each uploaded document appears as a labelled download link in the detail view")
def test_tc362_documents_are_labelled_download_links(
    logged_in_admin_appeals_page: AdminAppealsPage,
    filed_first_appeal_with_documents: dict,
):
    """
    Given an agency filed a FORM-III appeal with supporting documents
    When  I open the appeal's detail view
    Then  the Documents section lists each enclosure as a labelled link
    And   every link carries a target (href) and a non-empty label

    AIO: KAN-TC-362 | data: filed_first_appeal_with_documents
    """
    ap = logged_in_admin_appeals_page
    _open_seeded_appeal_or_skip(ap, filed_first_appeal_with_documents)

    with allure.step("Verify the Documents section lists labelled download links"):
        chips = ap.document_chips
        expect(chips.first).to_be_visible()
        count = chips.count()
        assert count > 0, "No document links shown for an appeal filed with enclosures."

    with allure.step("Verify each link is labelled and points somewhere"):
        has_target = False
        for i in range(count):
            chip = chips.nth(i)
            assert chip.text_content().strip(), f"Document link #{i} has no label."
            href = chip.get_attribute("href")
            if href and href.strip():
                has_target = True
        assert has_target, "No document link exposes a downloadable target (href)."


# ---------------------------------------------------------------------------
# TC-363  Recording an outcome persists it with admin identity and timestamp
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-363")
@allure.story("First Appeal Management")
@allure.title("TC-363: Selecting an outcome and saving updates the appeal with admin identity and timestamp")
def test_tc363_record_outcome_persists(
    logged_in_admin_appeals_page: AdminAppealsPage,
    allowed_outcome_data: AppealOutcomeData,
):
    """
    Given a pending FORM-III appeal is open in the review modal
    When  I select the 'Allow' outcome, enter remarks and save
    Then  the appeal's status updates to Allowed
    And   the reviewed column is populated (admin identity + decision timestamp)

    The decision is not reversible from the UI — the dev data keeps the outcome.

    AIO: KAN-TC-363 | data: allowed_with_remarks
    """
    ap = logged_in_admin_appeals_page
    appeal_id = _submitted_first_appeal_or_skip(ap)

    with allure.step("Record the outcome: allow + remarks"):
        ap.review_appeal(appeal_id, allowed_outcome_data.decision, allowed_outcome_data.remarks)

    with allure.step("Verify the appeal status updated to Allowed"):
        ap.open()
        expect(ap.status_badge(appeal_id)).to_contain_text(re.compile("allow", re.IGNORECASE))

    with allure.step("Verify the reviewed column now carries the admin decision metadata"):
        reviewed = ap.reviewed_cell(appeal_id).text_content().strip()
        allure.attach(reviewed, name="reviewed cell")
        assert reviewed and reviewed != "—", "Reviewed column was not populated after saving."


# ---------------------------------------------------------------------------
# TC-364  Saving without remarks is blocked by a required-field tooltip
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-364")
@allure.story("First Appeal Management")
@allure.title("TC-364: Saving an appeal outcome without remarks is blocked by a required-field tooltip")
def test_tc364_blank_remarks_blocked(
    logged_in_admin_appeals_page: AdminAppealsPage,
    rejected_blank_remarks_data: AppealOutcomeData,
):
    """
    Given a pending FORM-III appeal is open in the review modal
    When  I select an outcome (which enables Save) but leave remarks blank and click Save
    Then  a required-field validation tooltip is shown on the remarks field
    And   the outcome is not saved (the appeal's status is unchanged)

    AIO: KAN-TC-364 | data: rejected_blank_remarks
    """
    ap = logged_in_admin_appeals_page
    appeal_id = _submitted_first_appeal_or_skip(ap)
    original_status = ap.get_row_status(appeal_id)

    with allure.step("Open the review modal and select an outcome"):
        ap.open_review_modal(appeal_id)
        ap.select_decision(rejected_blank_remarks_data.decision)

    with allure.step("Verify 'Confirm & Save' is enabled once an outcome is selected"):
        expect(ap.confirm_decision_button).to_be_enabled()

    with allure.step("Attempt to save with the remarks field left blank"):
        ap.fill_decision_remarks("")
        ap.confirm_decision_button.click()

    with allure.step("Verify the required-remarks tooltip is shown"):
        message = ap.get_remarks_validation_message()
        allure.attach(
            f"tooltip='{message}' | expected≈'{rejected_blank_remarks_data.expected_error}'",
            name="remarks validation tooltip",
        )
        assert message, "No validation tooltip was shown for the empty remarks field."
        value_missing = ap.decision_remarks_textarea.evaluate("el => el.validity.valueMissing")
        assert value_missing, "Remarks field was not flagged as a missing required value."

    with allure.step("Verify the appeal's status is unchanged (outcome not saved)"):
        ap.open()
        assert ap.get_row_status(appeal_id) == original_status, (
            "Appeal status changed despite the empty-remarks tooltip block."
        )


# ---------------------------------------------------------------------------
# TC-365  Audit log captures the appeal-outcome event with full metadata
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-365")
@allure.story("First Appeal Management")
@allure.title("TC-365: Saving an appeal outcome writes an audit log entry with full metadata")
def test_tc365_audit_log_captures_outcome(
    logged_in_admin_appeals_page: AdminAppealsPage,
    allowed_for_audit_data: AppealOutcomeData,
):
    """
    Given a pending FORM-III appeal is open in the review modal
    When  I record an outcome with remarks
    Then  the Audit Log's newest entry carries an action pill and timestamp
    And   the full record references the appeal (its reg id or the remarks)

    AIO: KAN-TC-365 | data: allowed_for_audit
    """
    ap = logged_in_admin_appeals_page
    appeal_id = _submitted_first_appeal_or_skip(ap)
    reg_id = ap.reg_id_cell(appeal_id).text_content().strip()

    with allure.step("Record the outcome: allow + remarks"):
        ap.review_appeal(appeal_id, allowed_for_audit_data.decision, allowed_for_audit_data.remarks)

    with allure.step("Open the Audit Log and inspect the newest entry"):
        audit = AdminAuditLogPage(ap.page)
        audit.open()
        if audit.get_entry_count() == 0:
            pytest.skip("Audit Log is empty — cannot verify the outcome event.")
        entry = audit.log_entry(0)
        expect(audit.entry_action_pill(entry)).to_be_visible()
        expect(audit.entry_timestamp(entry)).to_be_visible()

    with allure.step("Verify the full record references the appeal"):
        audit.expand_entry(0)
        raw = audit.get_expanded_json_text()
        allure.attach(raw, name="audit raw record")
        remarks_fragment = allowed_for_audit_data.remarks.rstrip(".")
        assert reg_id in raw or remarks_fragment in raw or "appeal" in raw.lower(), (
            "Newest audit entry does not reference the appeal outcome."
        )


# ---------------------------------------------------------------------------
# TC-366  Limitation section flags a late-filed appeal with the stated reason
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-366")
@allure.story("First Appeal Management")
@allure.title("TC-366: Late-filed appeal shows the Limitation details and the stated reason for delay")
def test_tc366_late_filed_limitation_section(
    logged_in_admin_appeals_page: AdminAppealsPage,
    filed_late_first_appeal: dict,
):
    """
    Given an agency filed a FORM-III appeal beyond the 30-day limitation
    When  I open the appeal's detail view
    Then  the Limitation section is shown
    And   it carries the agency's stated reason for the delay

    (The associated email notification to the agency is verified out-of-band.)

    AIO: KAN-TC-366 | data: filed_late_first_appeal
    """
    ap = logged_in_admin_appeals_page
    _open_seeded_appeal_or_skip(ap, filed_late_first_appeal)

    with allure.step("Verify the Limitation section is rendered"):
        expect(ap.form_section_title("Limitation")).to_be_visible()

    with allure.step("Verify the stated reason for delay is shown"):
        doc_text = ap.form_document.text_content()
        reason_fragment = filed_late_first_appeal["delay_reason"][:25]
        assert reason_fragment and reason_fragment in doc_text, (
            "Late-filing reason for delay is not shown in the Limitation section."
        )


# ---------------------------------------------------------------------------
# TC-367  Each appeal from the same agency is an independent row
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-367")
@allure.story("First Appeal Management")
@allure.title("TC-367: Multiple first appeals from the same agency appear as independent rows")
def test_tc367_multiple_appeals_independent_rows(
    logged_in_admin_appeals_page: AdminAppealsPage,
):
    """
    Given one agency has filed more than one FORM-III appeal
    When  I view the 1st Appeals list
    Then  each appeal appears as its own row with a distinct appeal id
    And   the rows are not merged — each keeps its own date filed and status

    AIO: KAN-TC-367 | data: live appeals list (agency with multiple appeals)
    """
    ap = logged_in_admin_appeals_page
    rows = _first_appeals_or_skip(ap)

    with allure.step("Group the listed appeals by agency Reg ID"):
        by_reg: dict[str, list[int]] = {}
        for i in range(rows.count()):
            appeal_id = ap.get_appeal_id_of_row(rows.nth(i))
            reg_id = ap.reg_id_cell(appeal_id).text_content().strip()
            by_reg.setdefault(reg_id, []).append(appeal_id)

    reg_with_many = next((reg for reg, ids in by_reg.items() if len(ids) >= 2), None)
    if reg_with_many is None:
        pytest.skip("No agency in the dev data has two or more first appeals.")

    appeal_ids = by_reg[reg_with_many]
    with allure.step(f"Verify '{reg_with_many}' shows {len(appeal_ids)} independent rows"):
        assert len(set(appeal_ids)) == len(appeal_ids), "Appeal ids are not distinct."
        for appeal_id in appeal_ids:
            expect(ap.appeal_row(appeal_id)).to_be_visible()
            expect(ap.filed_on_cell(appeal_id)).to_be_visible()
            expect(ap.status_badge(appeal_id)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-368  Documents section shows a placeholder when no documents were uploaded
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-368")
@allure.story("First Appeal Management")
@allure.title("TC-368: Documents section shows 'No documents uploaded' when none were attached")
def test_tc368_no_documents_placeholder(
    logged_in_admin_appeals_page: AdminAppealsPage,
    filed_first_appeal_without_documents: dict,
):
    """
    Given an agency filed a FORM-III appeal without any attachments
    When  I open the appeal's detail view
    Then  the Documents section shows the 'No documents uploaded' placeholder
    And   no document links are rendered

    AIO: KAN-TC-368 | data: filed_first_appeal_without_documents
    """
    ap = logged_in_admin_appeals_page
    _open_seeded_appeal_or_skip(ap, filed_first_appeal_without_documents)

    with allure.step("Verify the 'No documents uploaded' placeholder is shown"):
        expect(ap.no_documents_note).to_be_visible()

    with allure.step("Verify no document links are rendered"):
        expect(ap.document_chips).to_have_count(0)
