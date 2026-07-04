"""
License Management — Admin Portal
==================================
Covers KAN-TC-257 through KAN-TC-267.

The dashboard lists every approved agency with its certificate validity
window. Tests that change validity dates (TC-262, TC-264, TC-267) register
the target agency with the ``license_restorer`` fixture first, so the
original Valid From / Valid Upto are re-issued on teardown and the dev data
is left as found.

Target agencies are picked dynamically from the table's first row — the AIO
sheet's named agencies ("Sunrise Placement Services" etc.) describe the
spec dataset, not the dev environment. Tile-vs-table count assertions
(TC-257, TC-258) assume the table fits on one page (no pagination), which
holds for the current dev dataset.
"""

import re
from datetime import date, datetime

import allure
from playwright.sync_api import expect

from pages.admin.licenses_page import AdminLicensesPage
from test_data.licenses_factory import LicenseData, LicensesFactory
from utils.aio import aio_case

# Days-left bar colours (inline style hex set by the dashboard)
GREEN_BAR = re.compile(r"15803d")
AMBER_BAR = re.compile(r"(f59e0b|d97706|b45309|ea580c)")
RED_BAR = re.compile(r"dc2626")

EXPECTED_COLUMNS = (
    "#", "Agency", "MPPA Reg No.", "License No.", "Valid From",
    "Valid Upto", "Days Left", "Status", "Certificate", "Actions",
)


def _display(iso_date: str) -> str:
    """ISO yyyy-mm-dd → the table's 'dd Mon yyyy' display format."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d %b %Y")


# ---------------------------------------------------------------------------
# TC-257  All 5 tiles show accurate counts based on current license records
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-257")
@allure.story("License Management")
@allure.title("TC-257: All 5 summary tiles show counts matching current license records")
def test_tc257_tiles_show_accurate_counts(
    logged_in_admin_licenses_page: AdminLicensesPage,
):
    """
    Given I am logged in as Admin on the License Management dashboard
    When  the page loads
    Then  all 5 tiles (Approved, Active, Expiring (30d), Expired, Revoked) are visible
    And   each tile count exactly matches the table rows in that state
    And   the Approved tile equals the total number of listed agencies

    AIO: KAN-TC-257 | data: live table state (single-page table assumed)
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Verify all 5 tiles are visible with their labels"):
        for status, label in (
            ("all", "Approved"), ("active", "Active"), ("expiring", "Expiring"),
            ("expired", "Expired"), ("revoked", "Revoked"),
        ):
            expect(lp.stat_chip(status)).to_be_visible()
            expect(lp.stat_chip_label(status)).to_contain_text(label, ignore_case=True)

    with allure.step("Verify the Approved tile equals the number of table rows"):
        expect(lp.license_rows.first).to_be_visible()
        approved = lp.get_stat_chip_count("all")
        assert approved == lp.license_rows.count(), (
            f"Approved tile shows {approved} but the table lists "
            f"{lp.license_rows.count()} agencies."
        )

    with allure.step("Verify each status tile matches the rows in that state"):
        for status in ("active", "expiring", "expired", "revoked"):
            tile = lp.get_stat_chip_count(status)
            rows = lp.count_rows_with_status(status)
            assert tile == rows, (
                f"'{status}' tile shows {tile} but {rows} table row(s) carry "
                f"the lb-{status} badge."
            )


# ---------------------------------------------------------------------------
# TC-258  Every approved agency appears in the table with all columns
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-258")
@allure.story("License Management")
@allure.title("TC-258: License table lists every approved agency with all required columns")
def test_tc258_table_lists_agencies_with_all_columns(
    logged_in_admin_licenses_page: AdminLicensesPage,
):
    """
    Given I am logged in as Admin on the License Management dashboard
    When  the license table loads
    Then  the 10 required columns are all present
    And   every row is populated: agency name, MPPA reg no., license no. (or
          'Auto'), validity dates, days-left, status badge, certificate link
          and actions

    AIO: KAN-TC-258 | data: live table state
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Verify the license table is visible and not empty"):
        expect(lp.licenses_table).to_be_visible()
        expect(lp.license_rows.first).to_be_visible()

    with allure.step("Verify all required columns are present"):
        for column in EXPECTED_COLUMNS:
            expect(lp.table_header(column)).to_be_visible()

    date_pattern = re.compile(r"\d{1,2} \w{3} \d{4}")
    for i in range(lp.license_rows.count()):
        agency = lp.get_agency_name(i)
        with allure.step(f"Verify row {i + 1} ('{agency}') is fully populated"):
            assert agency, f"Row {i + 1} has an empty agency name."
            expect(lp.mppa_reg_no(agency)).to_have_text(re.compile(r"MPPA/|\d+"))
            expect(lp.license_no_cell(agency)).not_to_be_empty()
            expect(lp.valid_from_cell(agency)).to_contain_text(date_pattern)
            expect(lp.valid_upto_cell(agency)).to_contain_text(date_pattern)
            expect(lp.days_left_cell(agency)).not_to_be_empty()
            expect(lp.status_badge(agency)).to_be_visible()
            expect(lp.view_certificate_link(agency)).to_be_visible()
            expect(lp.view_application_link(agency)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-259  Issue/Renew button opens modal blank with Valid From = today
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-259")
@allure.story("License Management")
@allure.title("TC-259: Issue/Renew License button opens modal blank with today's date")
def test_tc259_issue_modal_opens_blank(
    logged_in_admin_licenses_page: AdminLicensesPage,
):
    """
    Given I am logged in as Admin on the License Management dashboard
    When  I click the global 'Issue / Renew License' button
    Then  the modal opens in Issue mode with no agency pre-selected
    And   Valid From defaults to today's date, Valid Upto is empty
    And   the +1Y/+2Y/+3Y/+5Y quick-duration buttons are visible and enabled

    AIO: KAN-TC-259 | data: today's date computed at runtime
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Click 'Issue / Renew License'"):
        lp.open_issue_modal()
        expect(lp.issue_modal).to_be_visible()
        expect(lp.issue_modal_title).to_contain_text("Issue License")

    with allure.step("Verify the Agency dropdown is empty/unselected and enabled"):
        expect(lp.modal_agency_select).to_have_value("")
        expect(lp.modal_agency_select).to_be_enabled()

    with allure.step("Verify Valid From defaults to today and Valid Upto is empty"):
        expect(lp.modal_valid_from_input).to_have_value(date.today().isoformat())
        expect(lp.modal_valid_upto_input).to_have_value("")

    with allure.step("Verify all four quick-duration buttons are visible and enabled"):
        expect(lp.modal_quick_duration_buttons).to_have_count(4)
        for years in (1, 2, 3, 5):
            expect(lp.modal_quick_duration_button(years)).to_be_visible()
            expect(lp.modal_quick_duration_button(years)).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-260  Row-level Renew pre-selects the agency and pre-fills dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-260")
@allure.story("License Management")
@allure.title("TC-260: Row Renew pre-selects the agency and pre-fills its validity dates")
def test_tc260_renew_prefills_agency_and_dates(
    logged_in_admin_licenses_page: AdminLicensesPage,
):
    """
    Given an approved agency with stored validity dates is listed in the table
    When  I click the row's 'Renew' action
    Then  the modal opens in Renew mode with the agency pre-selected (locked)
    And   Valid From / Valid Upto are pre-filled with the row's stored dates

    AIO: KAN-TC-260 | data: first table row, dates read from its cells
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Read the first agency's stored validity dates from its row"):
        agency = lp.get_agency_name(0)
        valid_from, valid_upto = lp.get_row_validity_dates(agency)

    with allure.step(f"Click 'Renew' on the row for '{agency}'"):
        lp.open_renew_modal(agency)
        expect(lp.issue_modal).to_be_visible()
        expect(lp.issue_modal_title).to_contain_text("Renew")
        expect(lp.issue_modal_title).to_contain_text(agency)

    with allure.step("Verify the agency is pre-selected and locked"):
        expect(lp.modal_selected_agency_option).to_contain_text(agency)
        expect(lp.modal_agency_select).to_be_disabled()

    with allure.step("Verify the stored dates are pre-filled for reference"):
        expect(lp.modal_valid_from_input).to_have_value(valid_from)
        expect(lp.modal_valid_upto_input).to_have_value(valid_upto)

    with allure.step("Verify the dates remain editable for the new validity period"):
        expect(lp.modal_valid_from_input).to_be_enabled()
        expect(lp.modal_valid_upto_input).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-261  Quick-duration buttons auto-set Valid Upto from Valid From
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-261")
@allure.story("License Management")
@allure.title("TC-261: Quick-duration buttons set Valid Upto exactly N years from Valid From")
def test_tc261_quick_duration_buttons_calculate_valid_upto(
    logged_in_admin_licenses_page: AdminLicensesPage,
    quick_duration_data: LicenseData,
):
    """
    Given the Issue/Renew modal is open with Valid From set
    When  I click each quick-duration button (+5, +1, +2, +3 years)
    Then  Valid Upto is auto-set to exactly that many years from Valid From

    AIO: KAN-TC-261 | data: quick_duration_base
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Open the Issue/Renew modal"):
        lp.open_issue_modal()
        expect(lp.issue_modal).to_be_visible()

    with allure.step(f"Set Valid From: {quick_duration_data.valid_from}"):
        lp.fill_modal_valid_from(quick_duration_data.valid_from)
        expect(lp.modal_valid_from_input).to_have_value(quick_duration_data.valid_from)

    for years in (5, 1, 2, 3):
        expected_upto = LicensesFactory.plus_years(quick_duration_data.valid_from, years)
        with allure.step(f"Click '+{years} Year(s)' — Valid Upto must become {expected_upto}"):
            lp.click_quick_duration(years)
            expect(lp.modal_valid_upto_input).to_have_value(expected_upto)


# ---------------------------------------------------------------------------
# TC-262  Saving the modal updates approvals and licenses together
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-262")
@allure.story("License Management")
@allure.title("TC-262: Saving the license modal updates approvals and licenses records together")
def test_tc262_save_updates_approvals_and_licenses(
    logged_in_admin_licenses_page: AdminLicensesPage,
    license_restorer,
    valid_renewal_data: LicenseData,
):
    """
    Given the Renew modal is open for an approved agency
    When  I set a license number and a new validity window and click Save
    Then  the modal closes and the table row reflects the new dates and
          license number (agency_licenses)
    And   the expanded detail row's 'Valid Upto (approvals)' shows the new
          date (agency_approvals)

    Direct DB verification of transactional atomicity is out of scope for UI
    automation — both tables are asserted through their UI projections.

    AIO: KAN-TC-262 | data: valid_renewal
    """
    lp = logged_in_admin_licenses_page
    data = valid_renewal_data

    with allure.step("Capture the target agency and register it for date restore"):
        agency = lp.get_agency_name(0)
        license_restorer(agency)

    with allure.step(f"Renew '{agency}': {data.valid_from} → {data.valid_upto}"):
        lp.open_renew_modal(agency)
        lp.fill_modal_license_number(data.license_number)
        lp.fill_modal_valid_from(data.valid_from)
        lp.fill_modal_valid_upto(data.valid_upto)
        lp.fill_modal_notes(data.notes)
        lp.save_modal()
        lp.wait_for_load()

    with allure.step("Verify the modal closed after saving"):
        expect(lp.issue_modal).to_be_hidden()

    with allure.step("Verify the row shows the new validity window (approvals projection)"):
        expect(lp.valid_from_cell(agency)).to_contain_text(_display(data.valid_from))
        expect(lp.valid_upto_cell(agency)).to_contain_text(_display(data.valid_upto))
        expect(lp.status_badge(agency)).to_have_text("Active")

    with allure.step("Verify the row shows the new license number (licenses projection)"):
        expect(lp.license_no_cell(agency)).to_contain_text(data.license_number)

    with allure.step("Verify the detail row's 'Valid Upto (approvals)' matches"):
        lp.toggle_detail_row(agency)
        expect(lp.detail_row(agency)).to_be_visible()
        expect(lp.detail_field(agency, "Valid Upto (approvals)")).to_contain_text(
            _display(data.valid_upto)
        )


# ---------------------------------------------------------------------------
# TC-263  View Cert opens Form-II reflecting the stored validity dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-263")
@allure.story("License Management")
@allure.title("TC-263: View Cert opens the Form-II certificate with the stored validity dates")
def test_tc263_view_cert_reflects_stored_dates(
    logged_in_admin_licenses_page: AdminLicensesPage,
):
    """
    Given an approved agency with stored validity dates is listed in the table
    When  I click the row's 'View Cert' link
    Then  the MPPA FORM-II certificate opens in a NEW browser tab
    And   the dashboard tab stays on the License Management page
    And   the certificate displays the same Valid From / Valid Upto as stored
          in approvals

    AIO: KAN-TC-263 | data: first table row, dates read from its cells
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Read the first agency's stored validity dates from its row"):
        agency = lp.get_agency_name(0)
        valid_from, valid_upto = lp.get_row_validity_dates(agency)

    with allure.step(f"Click 'View Cert' for '{agency}' and capture the new tab"):
        cert_page = lp.open_certificate(agency)
        cert_page.wait_for_load_state()

    try:
        with allure.step("Verify the certificate opened in a separate new tab"):
            assert cert_page != lp.page, "Certificate did not open in a new tab."
            expect(cert_page).to_have_url(re.compile(r"certificate\.php"))

        with allure.step("Verify the dashboard tab stayed on License Management"):
            expect(lp.page).to_have_url(re.compile(r"licenses\.php"))
            expect(lp.licenses_table).to_be_visible()

        with allure.step("Verify the certificate shows the stored Valid From"):
            expect(
                cert_page.get_by_text(_display(valid_from)).first
            ).to_be_visible()

        with allure.step("Verify the certificate shows the stored Valid Upto"):
            expect(
                cert_page.get_by_text(_display(valid_upto)).first
            ).to_be_visible()
    finally:
        cert_page.close()


# ---------------------------------------------------------------------------
# TC-264  Days Left bar is green / amber / red by remaining validity
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-264")
@allure.story("License Management")
@allure.title("TC-264: Days Left bar shows green/amber/red based on remaining validity")
def test_tc264_days_left_bar_colours(
    logged_in_admin_licenses_page: AdminLicensesPage,
    license_restorer,
    days_left_color_data: dict,
):
    """
    Given an approved agency whose validity window I can re-issue
    When  the window leaves >90 days, ≤30 days, and negative days remaining
    Then  the Days Left bar renders green, amber, and red respectively
    And   the status badge tracks Active / Expiring / Expired

    The three states are produced sequentially on one agency via the Renew
    modal (the dev dataset can't be assumed to hold all three at once).

    AIO: KAN-TC-264 | data: green_bar_validity / amber_bar_validity / expired_validity
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Capture the target agency and register it for date restore"):
        agency = lp.get_agency_name(0)
        license_restorer(agency)

    with allure.step("Re-issue with >90 days remaining — bar must be green"):
        data = days_left_color_data["green"]
        lp.renew_license(agency, valid_from=data.valid_from,
                         valid_upto=data.valid_upto, notes=data.notes)
        lp.wait_for_load()
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", GREEN_BAR)
        expect(lp.status_badge(agency)).to_have_text("Active")

    with allure.step("Re-issue with ≤30 days remaining — bar must be amber"):
        data = days_left_color_data["amber"]
        lp.renew_license(agency, valid_from=data.valid_from,
                         valid_upto=data.valid_upto, notes=data.notes)
        lp.wait_for_load()
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", AMBER_BAR)
        expect(lp.status_badge(agency)).to_have_text("Expiring")

    with allure.step("Re-issue an expired window — bar must be red / overdue"):
        data = days_left_color_data["expired"]
        lp.renew_license(agency, valid_from=data.valid_from,
                         valid_upto=data.valid_upto, notes=data.notes)
        lp.wait_for_load()
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", RED_BAR)
        expect(lp.days_left_cell(agency)).to_contain_text("overdue")
        expect(lp.status_badge(agency)).to_have_text("Expired")


# ---------------------------------------------------------------------------
# TC-265  Valid Upto before Valid From is rejected on save
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-265")
@allure.story("License Management")
@allure.title("TC-265: Valid Upto earlier than Valid From triggers a validation error on save")
def test_tc265_upto_before_from_rejected(
    logged_in_admin_licenses_page: AdminLicensesPage,
    upto_before_from_data: LicenseData,
):
    """
    Given the Issue modal is open with an agency selected
    When  I set Valid Upto earlier than Valid From and click Save
    Then  the save is rejected with a 'Valid Upto must be after Valid From' error
    And   the agency's stored dates are not overwritten with the invalid window

    AIO: KAN-TC-265 | data: upto_before_from
    """
    lp = logged_in_admin_licenses_page
    data = upto_before_from_data

    with allure.step("Capture the first agency's current dates for the no-change check"):
        agency = lp.get_agency_name(0)
        original_from, original_upto = lp.get_row_validity_dates(agency)

    with allure.step("Open the Issue modal and select the agency"):
        lp.open_issue_modal()
        agency_value = (
            lp.modal_agency_select.locator("option", has_text=agency)
            .first.get_attribute("value")
        )
        lp.select_modal_agency(agency_value)
        expect(lp.modal_selected_agency_option).to_contain_text(agency)

    with allure.step(f"Set Valid From {data.valid_from} and earlier Valid Upto {data.valid_upto}"):
        lp.fill_modal_valid_from(data.valid_from)
        lp.fill_modal_valid_upto(data.valid_upto)
        expect(lp.modal_valid_upto_input).to_have_value(data.valid_upto)

    with allure.step("Click Save"):
        lp.save_modal()
        lp.wait_for_load()

    with allure.step(f"Verify the error message: '{data.expected_error}'"):
        expect(lp.error_alert).to_be_visible()
        expect(lp.error_alert).to_contain_text("Valid Upto")

    with allure.step("Verify the agency's stored dates were not changed"):
        assert lp.get_row_validity_dates(agency) == (original_from, original_upto), (
            "The invalid window was persisted — stored dates changed."
        )


# ---------------------------------------------------------------------------
# TC-266  Saving without selecting an agency is blocked
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-266")
@allure.story("License Management")
@allure.title("TC-266: Saving without selecting an agency shows a 'select an agency' error")
def test_tc266_missing_agency_rejected(
    logged_in_admin_licenses_page: AdminLicensesPage,
    missing_agency_data: LicenseData,
):
    """
    Given the Issue modal is open via the global button (no agency selected)
    When  I fill only Valid From / Valid Upto and click Save
    Then  the save is blocked with an agency-selection error (the required
          dropdown raises a validation message)
    And   the modal stays open with the entered dates intact

    AIO: KAN-TC-266 | data: missing_agency
    """
    lp = logged_in_admin_licenses_page
    data = missing_agency_data

    with allure.step("Open the Issue modal — agency left unselected"):
        lp.open_issue_modal()
        expect(lp.modal_agency_select).to_have_value("")

    with allure.step(f"Fill Valid From {data.valid_from} and Valid Upto {data.valid_upto}"):
        lp.fill_modal_valid_from(data.valid_from)
        lp.fill_modal_valid_upto(data.valid_upto)

    with allure.step("Click Save"):
        lp.save_modal()

    with allure.step("Verify the save is blocked with an agency-selection error"):
        message = lp.get_modal_agency_validation_message()
        allure.attach(message, name="agency-select validation message")
        assert message, "Save was not blocked: the agency select raised no validation message."
        assert "select" in message.lower(), (
            f"Unexpected validation message: '{message}'"
        )

    with allure.step("Verify the modal stays open with the entered dates intact"):
        expect(lp.issue_modal).to_be_visible()
        expect(lp.modal_valid_from_input).to_have_value(data.valid_from)
        expect(lp.modal_valid_upto_input).to_have_value(data.valid_upto)


# ---------------------------------------------------------------------------
# TC-267  Expiring (30d) tile boundary is inclusive at exactly 30 days
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-267")
@allure.story("License Management")
@allure.title("TC-267: License expiring in exactly 30 days is counted in the Expiring tile")
def test_tc267_expiring_tile_inclusive_30_day_boundary(
    logged_in_admin_licenses_page: AdminLicensesPage,
    license_restorer,
    expiring_boundary_data: dict,
):
    """
    Given an approved agency whose validity window I can re-issue
    When  its license expires on exactly the 31st day from today
    Then  it is NOT counted in the Expiring (30d) tile
    When  its license expires on exactly the 30th day from today
    Then  it IS counted (inclusive boundary) and the tile count rises by one

    AIO: KAN-TC-267 | data: expiring_in_31_days / expiring_in_30_days
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Capture the target agency and register it for date restore"):
        agency = lp.get_agency_name(0)
        license_restorer(agency)

    with allure.step("Re-issue expiring on the 31st day — must NOT count as Expiring"):
        data = expiring_boundary_data[31]
        lp.renew_license(agency, valid_from=data.valid_from,
                         valid_upto=data.valid_upto, notes=data.notes)
        lp.wait_for_load()
        expect(lp.status_badge(agency)).to_have_text("Active")
        expiring_at_31 = lp.get_stat_chip_count("expiring")

    with allure.step("Re-issue expiring on the 30th day — MUST count as Expiring"):
        data = expiring_boundary_data[30]
        lp.renew_license(agency, valid_from=data.valid_from,
                         valid_upto=data.valid_upto, notes=data.notes)
        lp.wait_for_load()
        expect(lp.status_badge(agency)).to_have_text("Expiring")

    with allure.step("Verify the Expiring (30d) tile count rose by exactly one"):
        expiring_at_30 = lp.get_stat_chip_count("expiring")
        assert expiring_at_30 == expiring_at_31 + 1, (
            f"Expiring tile was {expiring_at_31} with a 31-day window and "
            f"{expiring_at_30} with a 30-day window — expected an inclusive "
            f"+1 at exactly 30 days."
        )
