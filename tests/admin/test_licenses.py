"""
Licences & Certificates — Admin Portal (KAN-33)
===============================================
Covers KAN-TC-257…267 and KAN-TC-625…643 (Registry › Licences & certificates,
/module/admin/licenses/licenses.php), logged in as the Super Admin.

Tests that change a certificate (renew, suspend, lift, expire, cancel, reinstate)
work on ``scratch_agency`` — the last Active agency in name order — and the
``certificate_restorer`` fixture makes it Active again with its original dates
on teardown. The actions stay in the agency's certificate History.

Not automated: KAN-TC-638 (a suspension ending by itself — needs a check the
next day) and KAN-TC-643 (Revoke — under review, not tried on dev).
KAN-TC-637 (District officer powers) skips unless ADMIN_DISTRICT_USERNAME /
ADMIN_DISTRICT_PASSWORD / ADMIN_DISTRICT_NAME are set.

Known failures (03-Nov-2026): TC-263 (View Cert is 404 — "Super admin" #59),
TC-262 and TC-639 (a renewal adds no "Renewed" History entry), TC-625 (the
page clock is in UTC), TC-633 (a cancelled certificate is counted under
Active, not Revoked) and TC-642 (an Expiring certificate offers Reinstate).
"""

import re
from datetime import date, datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from pages.admin.licenses_page import AdminLicensesPage
from test_data.licenses_factory import CertificateActionData, LicenseData, LicensesFactory
from utils.aio import aio_case

IST = timezone(timedelta(hours=5, minutes=30))

# Days-left bar colours (inline style set by the page)
GREEN_BAR = re.compile(r"15803d")
AMBER_BAR = re.compile(r"f59e0b")
RED_BAR = re.compile(r"dc2626")

DATE = re.compile(r"\d{2} \w{3} \d{4}")
TOAST = {
    "suspend": re.compile(r"^Certificate suspended until \d{2} \w{3} \d{4}"),
    "lift": "Suspension lifted — the certificate is active again.",
    "expire": "Certificate expired by order of the Commissioner.",
    "cancel": "Registration certificate cancelled.",
    "reinstate": "Registration certificate reinstated.",
}


def _display(iso_date: str) -> str:
    """ISO yyyy-mm-dd → the table's 'dd Mon yyyy' display format."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d %b %Y")


def _days(text: str):
    """'1805 days' → 1805, '12d overdue' → -12, anything else → None."""
    m = re.search(r"(\d+)\s*days?\b", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)d overdue", text)
    return -int(m.group(1)) if m else None


def _check_dialog(lp: AdminLicensesPage, action: str, agency: str):
    """The certificate action dialog shows the action's title, explanation, reason hint and buttons."""
    _, title, explanation, confirm, minimum = AdminLicensesPage.CERTIFICATE_ACTIONS[action]
    expect(lp.action_dialog).to_be_visible()
    expect(lp.action_dialog_title).to_have_text(f"{title} — {agency}")
    expect(lp.action_dialog_explanation).to_have_text(explanation)
    expect(lp.action_reason_input).to_have_attribute(
        "placeholder", f"At least {minimum} characters (shown to the agency)")
    expect(lp.action_confirm_button).to_have_text(confirm)
    expect(lp.action_close_button).to_have_text("Close")


def _act(lp: AdminLicensesPage, agency: str, data: CertificateActionData):
    """Performs a certificate action as a Given step (no dialog checks)."""
    return lp.certificate_action(agency, data.action, data.reason, data.period)


# ---------------------------------------------------------------------------
# TC-257  Stat chips count the certificates and filter the table
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-257")
@allure.story("Licences & Certificates")
@allure.title("TC-257: Stat chips count the certificates and filter the table")
def test_tc257_stat_chips_count_and_filter(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am on Licences & certificates
    When  I click each of the five chips
    Then  the URL has ?status=<value>, that chip is highlighted, its count equals the rows listed
          and every row has that status
    And   Active + Expiring + Expired + Revoked = Approved

    AIO: KAN-TC-257 | data: live table state
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Read the five chip counts"):
        counts = {s: lp.get_stat_chip_count(s) for s in lp.STATUS_FILTERS}
        allure.attach(str(counts), name="chip counts")

    with allure.step("Verify Active + Expiring + Expired + Revoked = Approved"):
        assert counts["active"] + counts["expiring"] + counts["expired"] + counts["revoked"] == counts["all"], counts

    for status in lp.STATUS_FILTERS:
        with allure.step(f"Click the '{status}' chip"):
            lp.filter_by_status(status)
            expect(lp.page).to_have_url(re.compile(rf"[?&]status={status}(&|$)"))
            expect(lp.selected_stat_chip).to_have_count(1)
            expect(lp.selected_stat_chip).to_have_attribute("href", re.compile(rf"status={status}&"))
        with allure.step(f"Verify {counts[status]} row(s), all '{status}'"):
            expect(lp.license_rows).to_have_count(counts[status])
            if status != "all":
                expect(lp.rows_with_status(status)).to_have_count(counts[status])
            if counts[status] == 0:
                expect(lp.empty_table_row).to_have_text(lp.EMPTY_TABLE)


# ---------------------------------------------------------------------------
# TC-258  Every approved agency is listed with all columns
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-258")
@allure.story("Licences & Certificates")
@allure.title("TC-258: Every approved agency is listed with registration, validity, status, certificate and actions")
def test_tc258_table_lists_agencies_with_all_columns(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am on Licences & certificates, Approved chip
    Then  the rows equal the Approved count and the heading's count
    And   the columns are #, Agency, Registration No., Valid From, Valid Upto, Days Left, Status,
          Certificate, Actions
    And   every row shows the agency and location, a 13-digit Registration No., both dates,
          Days Left = Valid Upto − today, a status label, View Cert, History and View

    AIO: KAN-TC-258 | data: live table state
    """
    lp = logged_in_admin_licenses_page
    approved = lp.get_stat_chip_count("all")

    with allure.step(f"Verify {approved} rows and the heading count"):
        expect(lp.license_rows).to_have_count(approved)
        expect(lp.page_title).to_have_text(f"Agency Licenses & Certificates ({approved} approved agencies)")

    with allure.step("Verify the columns"):
        expect(lp.table_headers).to_have_count(len(lp.COLUMNS))
        for i, column in enumerate(lp.COLUMNS):
            expect(lp.table_headers.nth(i)).to_contain_text(column)

    today = date.today()
    for agency in lp.agency_names():
        with allure.step(f"Verify the row of '{agency}'"):
            expect(lp.agency_location(agency)).to_contain_text(re.compile(r",\s*\w+"))
            expect(lp.registration_no(agency)).to_have_text(re.compile(r"^\d{13}$"))
            expect(lp.valid_from_cell(agency)).to_contain_text(DATE)
            expect(lp.valid_upto_cell(agency)).to_contain_text(DATE)
            expect(lp.status_badge(agency)).to_have_text(
                re.compile(r"^(Active|Expiring \(\d+d\)|Expired|Suspended.*|Revoked|Cancelled)$"))
            expect(lp.view_certificate_link(agency)).to_have_text(re.compile(r"View Cert"))
            expect(lp.action_button(agency, "History")).to_be_visible()
            expect(lp.view_application_link(agency)).to_be_visible()
            days = _days(lp.days_left_cell(agency).text_content())
            if days is not None:
                upto = date.fromisoformat(lp.get_row_validity_dates(agency)[1])
                assert abs(days - (upto - today).days) <= 1, (
                    f"{agency}: Days Left {days} but Valid Upto {upto} is {(upto - today).days} days away.")


# ---------------------------------------------------------------------------
# TC-259  Issue / Renew License opens a blank Issue License form
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-259")
@allure.story("Licences & Certificates")
@allure.title("TC-259: Issue / Renew License in the toolbar opens a blank Issue License form")
def test_tc259_issue_modal_opens_blank(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am on Licences & certificates
    When  I click 'Issue / Renew License'
    Then  'Issue License' opens with the agency_approvals note, Agency on '— Select Agency —' and enabled
          (listing every approved agency as 'Name (Application ID)'), Valid From = today, Valid Upto
          empty, the four quick buttons, Remarks, no License Number field, Save and Cancel

    AIO: KAN-TC-259 | data: today's date computed at runtime
    """
    lp = logged_in_admin_licenses_page
    approved = lp.get_stat_chip_count("all")

    with allure.step("Click 'Issue / Renew License'"):
        lp.open_issue_modal()
        expect(lp.issue_modal).to_be_visible()
        expect(lp.issue_modal_title).to_have_text("Issue License")
        expect(lp.issue_modal_note).to_contain_text(
            "Saving will update agency_approvals (valid_from / valid_upto) — this is what the certificate reads.")

    with allure.step("Verify the Agency dropdown"):
        expect(lp.modal_agency_select).to_have_value("")
        expect(lp.modal_agency_select).to_be_enabled()
        expect(lp.modal_agency_options.first).to_have_text("— Select Agency —")
        options = [" ".join(t.split()) for t in lp.modal_agency_options.all_text_contents()[1:]]
        assert options and all(re.fullmatch(r".+ \(\d{13}\)", o) for o in options), options
        assert len(options) >= approved, f"{len(options)} agencies in the dropdown, {approved} approved."

    with allure.step("Verify the dates, quick buttons, remarks and buttons"):
        expect(lp.modal_valid_from_input).to_have_value(date.today().isoformat())
        expect(lp.modal_valid_upto_input).to_have_value("")
        expect(lp.modal_quick_duration_buttons).to_have_text(["+1 Year", "+2 Years", "+3 Years", "+5 Years"])
        expect(lp.modal_notes_textarea).to_have_attribute("placeholder", "Any remarks…")
        expect(lp.modal_license_number_input).to_have_attribute("type", "hidden")
        expect(lp.modal_save_button).to_have_text("Save — Updates agency_approvals")
        expect(lp.modal_cancel_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-260  Renew / Issue on a row locks the agency and prefills the dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-260")
@allure.story("Licences & Certificates")
@allure.title("TC-260: Renew or Issue on a row opens the form with the agency locked and its dates prefilled")
def test_tc260_renew_prefills_agency_and_dates(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given an agency with an Active certificate
    When  I click Renew (or Issue) on its row
    Then  'Renew — <agency>' opens with the agency selected and locked
    And   Valid From / Valid Upto equal the row's dates and can be changed

    AIO: KAN-TC-260 | data: first Active row
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Read an Active agency's dates from its row"):
        agency = lp.agencies_with_status("active")[0]
        registration = lp.registration_no(agency).text_content().strip()
        valid_from, valid_upto = lp.get_row_validity_dates(agency)

    with allure.step(f"Click Renew / Issue on '{agency}'"):
        lp.open_renew_modal(agency)
        expect(lp.issue_modal).to_be_visible()
        expect(lp.issue_modal_title).to_have_text(f"Renew — {agency}")

    with allure.step("Verify the agency is selected and locked"):
        expect(lp.modal_selected_agency_option).to_have_text(re.compile(
            rf"^\s*{re.escape(agency)}\s+\({registration}\)\s*$"))
        expect(lp.modal_agency_select).to_be_disabled()

    with allure.step("Verify the dates are prefilled and editable"):
        expect(lp.modal_valid_from_input).to_have_value(valid_from)
        expect(lp.modal_valid_upto_input).to_have_value(valid_upto)
        expect(lp.modal_valid_from_input).to_be_editable()
        expect(lp.modal_valid_upto_input).to_be_editable()


# ---------------------------------------------------------------------------
# TC-261  Quick duration buttons set Valid Upto from Valid From
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-261")
@allure.story("Licences & Certificates")
@allure.title("TC-261: Quick duration buttons set Valid Upto from Valid From")
def test_tc261_quick_duration_buttons_calculate_valid_upto(
    logged_in_admin_licenses_page: AdminLicensesPage,
    quick_duration_data: LicenseData,
):
    """
    Given the Issue License modal is open
    When  I set Valid From and click +5, +1, +2 and +3 years
    Then  Valid Upto is that many years after Valid From
    When  I clear Valid From and click +1 Year
    Then  Valid Upto is today + 1 year

    AIO: KAN-TC-261 | data: quick_duration_base
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Open the Issue License modal"):
        lp.open_issue_modal()
        expect(lp.issue_modal).to_be_visible()

    with allure.step(f"Set Valid From: {quick_duration_data.valid_from}"):
        lp.fill_modal_valid_from(quick_duration_data.valid_from)
        expect(lp.modal_valid_from_input).to_have_value(quick_duration_data.valid_from)

    for years in (5, 1, 2, 3):
        expected_upto = LicensesFactory.plus_years(quick_duration_data.valid_from, years)
        with allure.step(f"Click '+{years}' — Valid Upto must become {expected_upto}"):
            lp.click_quick_duration(years)
            expect(lp.modal_valid_upto_input).to_have_value(expected_upto)

    with allure.step("Clear Valid From and click +1 Year — Valid Upto must be today + 1 year"):
        lp.fill_modal_valid_from("")
        lp.click_quick_duration(1)
        expect(lp.modal_valid_upto_input).to_have_value(LicensesFactory.plus_years(LicensesFactory.today(), 1))


# ---------------------------------------------------------------------------
# TC-262  Saving Issue / Renew updates the validity everywhere
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-262")
@allure.story("Licences & Certificates")
@allure.title("TC-262: Saving Issue / Renew updates the certificate validity everywhere")
def test_tc262_save_updates_validity(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    valid_renewal_data: LicenseData,
):
    """
    Given an agency with an Active certificate
    When  I renew it from today for 5 years (+5 Years) with a remark
    Then  the row shows the new dates (with ✓ and '✓ approvals'), Days Left and Active
    And   the detail row's 'Valid From / Valid Upto (approvals)' show the new dates
    And   History shows 'Renewed' with my name and role (known failure 03-Nov-2026: no entry is added)

    AIO: KAN-TC-262 | data: valid_renewal
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, valid_renewal_data

    with allure.step(f"Renew '{agency}': {data.valid_from} + {data.duration_years} years"):
        lp.open_renew_modal(agency)
        expect(lp.issue_modal_title).to_have_text(f"Renew — {agency}")
        lp.fill_modal_valid_from(data.valid_from)
        lp.click_quick_duration(data.duration_years)
        expect(lp.modal_valid_upto_input).to_have_value(data.valid_upto)
        lp.fill_modal_notes(data.notes)
        lp.save_modal_and_wait()
        expect(lp.issue_modal).to_be_hidden()

    with allure.step("Verify the row shows the new validity"):
        expect(lp.valid_from_cell(agency)).to_have_text(_display(data.valid_from))
        expect(lp.valid_upto_cell(agency)).to_contain_text(_display(data.valid_upto))
        expect(lp.valid_upto_cell(agency)).to_contain_text("✓")
        expect(lp.registration_cell(agency)).to_contain_text("✓ approvals")
        expected_days = (date.fromisoformat(data.valid_upto) - date.today()).days
        expect(lp.days_left_cell(agency)).to_contain_text(f"{expected_days} days")
        expect(lp.status_badge(agency)).to_have_text("Active")

    with allure.step("Verify the detail row shows the new dates (agency_approvals)"):
        lp.toggle_detail_row(agency)
        expect(lp.detail_row(agency)).to_be_visible()
        expect(lp.detail_field(agency, "Valid From (approvals)")).to_have_text(_display(data.valid_from))
        expect(lp.detail_field(agency, "Valid Upto (approvals)")).to_have_text(_display(data.valid_upto))

    with allure.step("Verify History shows 'Renewed'"):
        lp.open_history(agency)
        expect(lp.history_entries.first.locator(".t-title")).to_have_text("Renewed")


# ---------------------------------------------------------------------------
# TC-263  View Cert opens the Form-II certificate with the row's dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-263")
@allure.story("Licences & Certificates")
@allure.title("TC-263: View Cert opens the agency's Form-II certificate with the row's dates")
def test_tc263_view_cert_reflects_row(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given an agency with an Active certificate
    When  I click View Cert
    Then  'MPPA Certificate — <agency>' opens in a new tab (admin view) with the row's Registration
          No., a Certificate No., the row's Valid Upto, Print and Download PDF
    And   'View Full Certificate (MPPA FORM-II)' in the details opens the same certificate

    Known failure (03-Nov-2026, "Super admin" #59): the link is 404 Not Found.

    AIO: KAN-TC-263 | data: first Active row
    """
    lp = logged_in_admin_licenses_page
    agency = lp.agencies_with_status("active")[0]
    registration = lp.registration_no(agency).text_content().strip()
    valid_upto = date.fromisoformat(lp.get_row_validity_dates(agency)[1]).strftime("%d/%m/%Y")

    with allure.step(f"Click View Cert for '{agency}'"):
        cert = lp.open_certificate(agency)
        cert.wait_for_load_state()
    try:
        with allure.step("Verify the certificate"):
            expect(cert).to_have_title(f"MPPA Certificate — {agency}")
            body = cert.locator("body")
            expect(body).to_contain_text("ADMIN VIEW")
            expect(body).to_contain_text(f"Reg. ID {registration}")
            expect(body).to_contain_text(re.compile(r"Cert\. No\. \d+"))
            expect(body).to_contain_text(f"Valid Until {valid_upto}")
            expect(cert.get_by_text("Print").first).to_be_visible()
            expect(cert.get_by_text("Download PDF").first).to_be_visible()
        with allure.step("Verify the dashboard tab stayed on Licences & certificates"):
            expect(lp.page).to_have_url(re.compile(r"licenses\.php"))
    finally:
        cert.close()

    with allure.step("Open the row's details and click 'View Full Certificate (MPPA FORM-II)'"):
        lp.toggle_detail_row(agency)
        cert = lp.open_detail_certificate(agency)
        cert.wait_for_load_state()
    try:
        expect(cert).to_have_title(f"MPPA Certificate — {agency}")
    finally:
        cert.close()


# ---------------------------------------------------------------------------
# TC-264  Days Left bar colours
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-264")
@allure.story("Licences & Certificates")
@allure.title("TC-264: Days Left bar is green for valid, amber within 30 days and red once expired")
def test_tc264_days_left_bar_colours(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    days_left_color_data: dict,
):
    """
    Given an agency whose validity window I can re-issue
    When  the window leaves more than 30 days, 30 days or fewer, and none
    Then  the Days Left bar is green (Active), amber (Expiring) and red (Expired)

    The three states are produced one after another on one agency with Renew (the dev data has no
    expired certificate to look at).

    AIO: KAN-TC-264 | data: green_bar_validity / amber_bar_validity / expired_validity
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency
    for band, colour, label in (("green", GREEN_BAR, "Active"), ("amber", AMBER_BAR, "Expiring"),
                                ("expired", RED_BAR, "Expired")):
        data = days_left_color_data[band]
        with allure.step(f"Re-issue {data.valid_from} → {data.valid_upto}: bar must be {band}, status {label}"):
            lp.renew_license(agency, valid_from=data.valid_from, valid_upto=data.valid_upto, notes=data.notes)
            expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", colour)
            expect(lp.status_badge(agency)).to_contain_text(label)


# ---------------------------------------------------------------------------
# TC-265  Valid Upto before Valid From is not saved (Under Review)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-265")
@allure.story("Licences & Certificates")
@allure.title("TC-265: Valid Upto before Valid From is not saved")
def test_tc265_upto_before_from_rejected(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    upto_before_from_data: LicenseData,
):
    """
    Given the Renew modal is open for an agency
    When  I set Valid Upto earlier than Valid From and click Save
    Then  the agency's dates are unchanged

    The case is under review: the page does not compare the dates and the server's message has not
    been seen, so only the outcome (nothing saved) is checked.

    AIO: KAN-TC-265 | data: upto_before_from
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, upto_before_from_data
    original = lp.get_row_validity_dates(agency)

    with allure.step(f"Renew '{agency}' with Valid From {data.valid_from} and Valid Upto {data.valid_upto}"):
        lp.open_renew_modal(agency)
        lp.fill_modal_valid_from(data.valid_from)
        lp.fill_modal_valid_upto(data.valid_upto)
        lp.save_modal()
        lp.wait_for_load()

    with allure.step("Verify the agency's dates are unchanged"):
        lp.open(status="all")
        assert lp.get_row_validity_dates(agency) == original, (
            f"The invalid window was saved: {lp.get_row_validity_dates(agency)} (was {original}).")


# ---------------------------------------------------------------------------
# TC-266  Issue License cannot be saved without an agency
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-266")
@allure.story("Licences & Certificates")
@allure.title("TC-266: Issue License cannot be saved without an agency")
def test_tc266_missing_agency_rejected(
    logged_in_admin_licenses_page: AdminLicensesPage,
    missing_agency_data: LicenseData,
):
    """
    Given the Issue License modal is open from the toolbar (no agency selected)
    When  I set the dates and click Save
    Then  the browser's required-field check stops the save on Agency
    And   the modal stays open with the dates intact

    AIO: KAN-TC-266 | data: missing_agency
    """
    lp = logged_in_admin_licenses_page
    data = missing_agency_data

    with allure.step("Open Issue License — Agency left on '— Select Agency —'"):
        lp.open_issue_modal()
        expect(lp.modal_agency_select).to_have_value("")

    with allure.step(f"Set Valid From {data.valid_from} and Valid Upto {data.valid_upto}, click Save"):
        lp.fill_modal_valid_from(data.valid_from)
        lp.fill_modal_valid_upto(data.valid_upto)
        lp.save_modal()

    with allure.step("Verify the browser asks to select an agency"):
        message = lp.get_modal_agency_validation_message()
        allure.attach(message, name="Agency validation message")
        assert data.expected_error in message.lower(), f"Unexpected validation message: '{message}'"

    with allure.step("Verify the modal stays open with the dates intact"):
        expect(lp.issue_modal).to_be_visible()
        expect(lp.modal_valid_from_input).to_have_value(data.valid_from)
        expect(lp.modal_valid_upto_input).to_have_value(data.valid_upto)


# ---------------------------------------------------------------------------
# TC-267  Expiring (30d) boundary
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-267")
@allure.story("Licences & Certificates")
@allure.title("TC-267: A certificate expiring in exactly 30 days counts as Expiring; one in 31 days does not")
def test_tc267_expiring_inclusive_30_day_boundary(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    expiring_boundary_data: dict,
):
    """
    Given an agency whose validity window I can re-issue
    When  it expires in 31 days
    Then  it is Active, listed under Active and not under Expiring (30d)
    When  it expires in exactly 30 days
    Then  it is 'Expiring (30d)' with 30 days and an amber bar, listed under Expiring (30d) (count + 1)

    AIO: KAN-TC-267 | data: expiring_in_31_days / expiring_in_30_days
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency

    with allure.step("Re-issue expiring in 31 days"):
        data = expiring_boundary_data[31]
        lp.renew_license(agency, valid_from=data.valid_from, valid_upto=data.valid_upto, notes=data.notes)
        expect(lp.status_badge(agency)).to_have_text("Active")
        expiring_at_31 = lp.get_stat_chip_count("expiring")
    with allure.step("Verify it is listed under Active and not under Expiring (30d)"):
        lp.filter_by_status("active")
        expect(lp.license_row(agency)).to_have_count(1)
        lp.filter_by_status("expiring")
        expect(lp.license_row(agency)).to_have_count(0)

    with allure.step("Re-issue expiring in exactly 30 days"):
        lp.open(status="all")
        data = expiring_boundary_data[30]
        lp.renew_license(agency, valid_from=data.valid_from, valid_upto=data.valid_upto, notes=data.notes)
        expect(lp.status_badge(agency)).to_have_text("Expiring (30d)")
        expect(lp.days_left_cell(agency)).to_contain_text("30 days")
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", AMBER_BAR)
    with allure.step("Verify the Expiring (30d) count rose by one and lists the agency"):
        assert lp.get_stat_chip_count("expiring") == expiring_at_31 + 1
        lp.filter_by_status("expiring")
        expect(lp.license_row(agency)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-625  Page loads with heading, role note, chips, toolbar and table
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-625")
@allure.story("Licences & Certificates")
@allure.title("TC-625: Licences & certificates loads with heading, role note, chips, toolbar and table")
def test_tc625_page_loads(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am logged in to the Officer Console
    When  I click 'Licences & certificates' in the sidebar
    Then  'Licenses — Admin' opens with the heading and the current date and time (IST)
    And   the 'Who can do what' note, the five chips, search, Issue / Renew License, Renewal
          applications and the table sorted by Agency ▲

    Known failure (03-Nov-2026): the clock shows UTC, 5 h 30 min behind.

    AIO: KAN-TC-625 | data: none
    """
    lp = logged_in_admin_licenses_page

    with allure.step("Open Licences & certificates from the sidebar"):
        lp.page.goto(lp.page.url.split("/licenses/")[0] + "/index.php")
        lp.sidebar.nav_link("Licences & certificates").click()
        expect(lp.page).to_have_url(re.compile(r"/licenses/licenses\.php"))
        expect(lp.page).to_have_title("Licenses — Admin")

    with allure.step("Verify the heading and the role note"):
        expect(lp.page_title).to_have_text(re.compile(r"^Agency Licenses & Certificates \(\d+ approved agencies\)$"))
        for text in ("Who can do what:", "District officer", "suspend", "Divisional officer", "lift a suspension",
                     "Commissioner", "expire", "cancel", "reinstate", "Super Administrator",
                     "Every action is recorded in the certificate History."):
            expect(lp.info_box).to_contain_text(text)

    with allure.step("Verify the chips, search and toolbar"):
        for status, label in (("all", "Approved"), ("active", "Active"), ("expiring", "Expiring (30d)"),
                              ("expired", "Expired"), ("revoked", "Revoked")):
            expect(lp.stat_chip_label(status)).to_have_text(label)
            expect(lp.stat_chip_count(status)).to_have_text(re.compile(r"^\d+$"))
        expect(lp.search_input).to_have_attribute("placeholder", "Search agency name or registration no…")
        expect(lp.issue_renew_button).to_have_text("Issue / Renew License")
        expect(lp.renewal_applications_link).to_have_text("Renewal applications")

    with allure.step("Verify the table is sorted by Agency ▲"):
        expect(lp.table_header("Agency")).to_have_text("Agency ▲")
        names = lp.agency_names()
        assert names == sorted(names, key=str.casefold), names

    with allure.step("Verify the clock shows the current date and time (IST)"):
        shown = datetime.strptime(lp.page_clock.text_content().strip(), "%d %b %Y · %H:%M").replace(tzinfo=IST)
        now = datetime.now(IST)
        assert abs((now - shown).total_seconds()) < 300, (
            f"Clock shows {shown:%d %b %Y %H:%M}, IST is {now:%d %b %Y %H:%M}.")


# ---------------------------------------------------------------------------
# TC-626  Search keeps the chosen chip
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-626")
@allure.story("Licences & Certificates")
@allure.title("TC-626: Search by agency name or registration no. keeps the chosen chip")
def test_tc626_search_keeps_chip(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am on Licences & certificates
    When  I search part of an agency name, then a Registration No., then a name on the Active chip
    Then  only matching agencies are listed, the text stays in the search box, and the chip is kept

    AIO: KAN-TC-626 | data: first agency's name and Registration No.
    """
    lp = logged_in_admin_licenses_page
    agency = lp.agencies_with_status("active")[0]
    text = agency.split()[0]
    registration = lp.registration_no(agency).text_content().strip()

    with allure.step(f"Search for '{text}'"):
        lp.search(text)
        expect(lp.page).to_have_url(re.compile(rf"q={re.escape(text)}"))
        expect(lp.search_input).to_have_value(text)
        expect(lp.license_row(agency)).to_have_count(1)
        for row in lp.table_data():
            assert text.lower() in (row["agency"] + row["registration_no"]).lower(), row

    with allure.step(f"Search for Registration No. {registration}"):
        lp.search(registration)
        expect(lp.license_rows).to_have_count(1)
        expect(lp.registration_no(agency)).to_have_text(registration)

    with allure.step(f"Click Active, then search for '{text}'"):
        lp.open(status="active")
        lp.search(text)
        expect(lp.page).to_have_url(re.compile(r"status=active"))
        expect(lp.selected_stat_chip).to_have_attribute("href", re.compile(r"status=active&"))
        expect(lp.rows_with_status("active")).to_have_count(lp.license_rows.count())
        expect(lp.license_row(agency)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-627  Sorting
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-627")
@allure.story("Licences & Certificates")
@allure.title("TC-627: Sorting by Agency, Valid From, Valid Upto and Days Left in both directions")
def test_tc627_sorting(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given I am on Licences & certificates
    When  I click the Agency, Valid From, Valid Upto and Days Left headers, each twice
    Then  the rows are ordered by that column ascending, then descending; the chip is kept

    AIO: KAN-TC-627 | data: live table state
    """
    lp = logged_in_admin_licenses_page

    def dates(index):
        return [datetime.strptime(DATE.search(v).group(), "%d %b %Y") for v in lp.column_values(index)]

    def days():
        return [d for d in (_days(v) for v in lp.column_values(5)) if d is not None]

    with allure.step("Verify the default order is Agency ascending"):
        names = lp.agency_names()
        assert names == sorted(names, key=str.casefold), names

    with allure.step("Click Agency — descending"):
        lp.sort_by("agency_name")
        expect(lp.page).to_have_url(re.compile(r"sort=agency_name&dir=desc"))
        names = lp.agency_names()
        assert names == sorted(names, key=str.casefold, reverse=True), names

    for field, read in (("eff_start", lambda: dates(3)), ("eff_valid_upto", lambda: dates(4)), ("days_left", days)):
        with allure.step(f"Click {field} — ascending"):
            lp.sort_by(field)
            expect(lp.page).to_have_url(re.compile(rf"sort={field}&dir=asc"))
            values = read()
            assert values == sorted(values), f"{field} ascending: {values}"
        with allure.step(f"Click {field} again — descending"):
            lp.sort_by(field)
            expect(lp.page).to_have_url(re.compile(rf"sort={field}&dir=desc"))
            values = read()
            assert values == sorted(values, reverse=True), f"{field} descending: {values}"
            expect(lp.page).to_have_url(re.compile(r"status=all"))


# ---------------------------------------------------------------------------
# TC-628  Row details
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-628")
@allure.story("Licences & Certificates")
@allure.title("TC-628: Clicking a row opens its detail panel; clicking again closes it")
def test_tc628_row_details(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given an agency with an Active certificate
    When  I click its row
    Then  the detail row opens with Registration No., Agency Status, Email, PAN, Approval Date,
          Valid From / Valid Upto (approvals), Days Remaining, Approved By, Remarks and the two buttons,
          matching the row
    When  I click the row again
    Then  the detail row closes

    AIO: KAN-TC-628 | data: first Active row
    """
    lp = logged_in_admin_licenses_page
    agency = lp.agencies_with_status("active")[0]
    registration = lp.registration_no(agency).text_content().strip()
    days = lp.days_left_cell(agency).text_content().split()[0]

    with allure.step(f"Click the row of '{agency}'"):
        expect(lp.detail_row(agency)).to_be_hidden()
        lp.toggle_detail_row(agency)
        expect(lp.detail_row(agency)).to_be_visible()

    with allure.step("Verify the details"):
        for key in ("Agency Status", "Email", "PAN", "Approval Date", "Valid From (approvals)",
                    "Valid Upto (approvals)", "Approved By", "Remarks"):
            expect(lp.detail_field(agency, key)).to_have_count(1)
        expect(lp.detail_field(agency, "Registration No.")).to_have_text(registration)
        expect(lp.detail_field(agency, "Email")).to_have_text(re.compile(r"\S+@\S+\.\S+"))
        expect(lp.detail_field(agency, "PAN")).to_have_text(re.compile(r"^\s*[A-Z]{5}\d{4}[A-Z]\s*$"))
        expect(lp.detail_field(agency, "Days Remaining")).to_contain_text(days)
        expect(lp.detail_view_certificate_link(agency)).to_have_text(
            re.compile(r"View Full Certificate \(MPPA FORM-II\)"))
        expect(lp.detail_view_application_link(agency)).to_have_text(re.compile(r"View Full Application"))

    with allure.step("Click the row again"):
        lp.toggle_detail_row(agency)
        expect(lp.detail_row(agency)).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-629  View and View Full Application
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-629")
@allure.story("Licences & Certificates")
@allure.title("TC-629: View and View Full Application open the agency's full application")
def test_tc629_view_application(logged_in_admin_licenses_page: AdminLicensesPage):
    """
    Given an agency with an Active certificate
    When  I click View on its row, and View Full Application in its details
    Then  the agency's full application opens ('View Agency — <agency> | Admin') each time

    AIO: KAN-TC-629 | data: first Active row
    """
    lp = logged_in_admin_licenses_page
    agency = lp.agencies_with_status("active")[0]
    agency_id = lp.agency_id(agency)

    with allure.step(f"Click View for '{agency}'"):
        lp.open_application_view(agency)
        expect(lp.page).to_have_url(re.compile(rf"/dashboard/agency_view\.php\?id={agency_id}$"))
        expect(lp.page).to_have_title(f"View Agency — {agency} | Admin")
        expect(lp.page.get_by_role("heading", name=agency, exact=True).first).to_be_visible()

    with allure.step("Go back, open the details and click View Full Application"):
        lp.open(status="all")
        lp.toggle_detail_row(agency)
        lp.detail_view_application_link(agency).click()
        expect(lp.page).to_have_url(re.compile(rf"/dashboard/agency_view\.php\?id={agency_id}$"))
        expect(lp.page).to_have_title(f"View Agency — {agency} | Admin")


# ---------------------------------------------------------------------------
# TC-630  Suspend for a period
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-630")
@allure.story("Licences & Certificates")
@allure.title("TC-630: Suspending a certificate for a period suspends it and records it in History")
def test_tc630_suspend_for_a_period(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    suspension_data: CertificateActionData,
):
    """
    Given an agency with an Active certificate
    When  I click Suspend
    Then  'Suspend certificate — <agency>' shows the explanation, 'Suspend for' 30 Day(s) with the
          restore note, the reason box, Close and Suspend
    When  I suspend it for 7 days with a reason and accept 'Suspend certificate?'
    Then  a success message shows, the row is Suspended (Lift suspension offered, Suspend not)
    And   History's newest entry is 'Suspended — until <today + 7 days>' with the officer, role and reason

    AIO: KAN-TC-630 | data: suspension_7_days (restored on teardown)
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, suspension_data

    with allure.step(f"Click Suspend on '{agency}'"):
        lp.open_certificate_action(agency, "suspend")
        _check_dialog(lp, "suspend", agency)
        expect(lp.suspension_period).to_be_visible()
        expect(lp.suspension_period_number).to_have_value("30")
        expect(lp.suspension_period_unit).to_have_value("days")
        expect(lp.suspension_period).to_contain_text(
            "The certificate is restored automatically when this period ends. "
            "Only the Divisional officer or the Commissioner can lift it earlier.")

    with allure.step(f"Suspend for {data.period[0]} {data.period[1]} and accept the confirmation"):
        lp.set_suspension_period(*data.period)
        lp.fill_action_reason(data.reason)
        confirmation, toast = lp.confirm_certificate_action()
        assert confirmation == "Suspend certificate?", confirmation
        assert TOAST["suspend"].search(toast), toast

    with allure.step("Verify the row is Suspended"):
        expect(lp.status_badge(agency)).to_contain_text("Suspended")
        expect(lp.action_button(agency, "Lift suspension")).to_be_visible()
        expect(lp.action_button(agency, "Suspend")).to_have_count(0)

    with allure.step("Verify History"):
        lp.open_history(agency)
        expect(lp.history_title).to_have_text(f"Certificate history — {agency}")
        newest = lp.history_data()[0]
        allure.attach(str(newest), name="newest History entry")
        # The 'until' time is shown in UTC, so allow the day before in the early IST morning
        until = [(date.today() + timedelta(days=d)).isoformat() for d in (7, 6)]
        assert re.match(rf"^Suspended — until ({until[0]}|{until[1]}) \d{{2}}:\d{{2}}$", newest["title"]), newest
        assert re.search(r"· .+ \(.+\)$", newest["meta"]), newest
        assert data.reason in newest["body"], newest


# ---------------------------------------------------------------------------
# TC-631  Lift a suspension
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-631")
@allure.story("Licences & Certificates")
@allure.title("TC-631: Lifting a suspension makes the certificate active again")
def test_tc631_lift_suspension(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    short_suspension_data: CertificateActionData,
    lift_data: CertificateActionData,
):
    """
    Given an agency whose certificate is Suspended
    When  I click Lift suspension, give a reason and accept 'Lift suspension?'
    Then  a success message shows, the row is Active again
    And   History shows 'Suspension lifted' above 'Suspended — until …'

    AIO: KAN-TC-631 | data: suspension_1_day, lift
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency

    with allure.step(f"Given '{agency}' is suspended"):
        _act(lp, agency, short_suspension_data)
        expect(lp.status_badge(agency)).to_contain_text("Suspended")
        expect(lp.action_button(agency, "Suspend")).to_have_count(0)

    with allure.step("Click Lift suspension"):
        lp.open_certificate_action(agency, "lift")
        _check_dialog(lp, "lift", agency)
        expect(lp.suspension_period).to_be_hidden()

    with allure.step("Give a reason and accept the confirmation"):
        lp.fill_action_reason(lift_data.reason)
        confirmation, toast = lp.confirm_certificate_action()
        assert confirmation == "Lift suspension?", confirmation
        assert toast == TOAST["lift"], toast

    with allure.step("Verify the row is Active"):
        expect(lp.status_badge(agency)).to_have_text("Active")
        expect(lp.action_button(agency, "Lift suspension")).to_have_count(0)

    with allure.step("Verify History"):
        lp.open_history(agency)
        entries = lp.history_data()
        assert entries[0]["title"] == "Suspension lifted" and lift_data.reason in entries[0]["body"], entries[:2]
        assert entries[1]["title"].startswith("Suspended — until"), entries[:2]


# ---------------------------------------------------------------------------
# TC-632  Expire
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-632")
@allure.story("Licences & Certificates")
@allure.title("TC-632: Expiring a certificate makes it expired today")
def test_tc632_expire(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    expiry_data: CertificateActionData,
):
    """
    Given an agency with an Active certificate
    When  I click Expire, give a reason, click 'Expire now' and accept 'Expire certificate?'
    Then  a success message shows; the row is Expired with a red bar
    And   it is listed under Expired and not under Active; History shows 'Expired' with the reason

    AIO: KAN-TC-632 | data: expiry (reinstated on teardown)
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, expiry_data

    with allure.step(f"Click Expire on '{agency}'"):
        lp.open_certificate_action(agency, "expire")
        _check_dialog(lp, "expire", agency)

    with allure.step("Give a reason and accept the confirmation"):
        lp.fill_action_reason(data.reason)
        confirmation, toast = lp.confirm_certificate_action()
        assert confirmation == "Expire certificate?", confirmation
        assert toast == TOAST["expire"], toast

    with allure.step("Verify the row is Expired"):
        expect(lp.status_badge(agency)).to_have_text("Expired")
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", RED_BAR)
        expect(lp.days_left_cell(agency)).to_contain_text("overdue")

    with allure.step("Verify the chips"):
        lp.filter_by_status("expired")
        expect(lp.license_row(agency)).to_have_count(1)
        lp.filter_by_status("active")
        expect(lp.license_row(agency)).to_have_count(0)

    with allure.step("Verify History"):
        lp.open(status="all")
        lp.open_history(agency)
        newest = lp.history_data()[0]
        assert newest["title"].startswith("Expired") and data.reason in newest["body"], newest


# ---------------------------------------------------------------------------
# TC-633  Cancel
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-633")
@allure.story("Licences & Certificates")
@allure.title("TC-633: Cancelling a registration certificate revokes it")
def test_tc633_cancel(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    cancellation_data: CertificateActionData,
):
    """
    Given an agency with an Active certificate
    When  I click Cancel, give a reason, click 'Cancel certificate' and accept the confirmation
    Then  a success message shows; the row is Cancelled; Suspend, Expire and Cancel are no longer offered
    And   it is listed under Revoked and not under Active (known failure 03-Nov-2026: still counted Active)
    And   History shows 'Cancelled' with the reason

    AIO: KAN-TC-633 | data: cancellation (reinstated on teardown)
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, cancellation_data

    with allure.step(f"Click Cancel on '{agency}'"):
        lp.open_certificate_action(agency, "cancel")
        _check_dialog(lp, "cancel", agency)

    with allure.step("Give a reason and accept the confirmation"):
        lp.fill_action_reason(data.reason)
        confirmation, toast = lp.confirm_certificate_action()
        assert confirmation == "Cancel registration certificate?", confirmation
        assert toast == TOAST["cancel"], toast

    with allure.step("Verify the row is Cancelled"):
        expect(lp.status_badge(agency)).to_have_text("Cancelled")
        for label in ("Suspend", "Expire", "Cancel"):
            expect(lp.action_button(agency, label)).to_have_count(0)

    with allure.step("Verify History"):
        lp.open_history(agency)
        newest = lp.history_data()[0]
        assert newest["title"] == "Cancelled" and data.reason in newest["body"], newest
        lp.close_history()

    with allure.step("Verify it is listed under Revoked and not under Active"):
        lp.filter_by_status("revoked")
        expect(lp.license_row(agency)).to_have_count(1)
        lp.filter_by_status("active")
        expect(lp.license_row(agency)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-634  Reinstate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-634")
@allure.story("Licences & Certificates")
@allure.title("TC-634: Reinstating a certificate makes it active again")
def test_tc634_reinstate(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    expiry_data: CertificateActionData,
    reinstatement_data: CertificateActionData,
):
    """
    Given an agency whose certificate is Expired
    When  I click Reinstate, give a reason and accept 'Reinstate certificate?'
    Then  a success message shows; the row is Active, listed under Active
    And   History shows 'Reinstated' with the reason

    AIO: KAN-TC-634 | data: expiry, reinstatement
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, reinstatement_data

    with allure.step(f"Given '{agency}' is expired"):
        _act(lp, agency, expiry_data)
        expect(lp.status_badge(agency)).to_have_text("Expired")

    with allure.step("Click Reinstate"):
        lp.open_certificate_action(agency, "reinstate")
        _check_dialog(lp, "reinstate", agency)

    with allure.step("Give a reason and accept the confirmation"):
        lp.fill_action_reason(data.reason)
        confirmation, toast = lp.confirm_certificate_action()
        assert confirmation == "Reinstate certificate?", confirmation
        assert toast == TOAST["reinstate"], toast

    with allure.step("Verify the row is Active and listed under Active"):
        expect(lp.status_badge(agency)).to_have_text("Active")
        lp.open_history(agency)
        newest = lp.history_data()[0]
        assert newest["title"] == "Reinstated" and data.reason in newest["body"], newest
        lp.close_history()
        lp.filter_by_status("active")
        expect(lp.license_row(agency)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-635  Reason rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-635")
@allure.story("Licences & Certificates")
@allure.title("TC-635: A reason shorter than the minimum, or a cancelled confirmation, changes nothing")
def test_tc635_reason_rules(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    reason_rules_data: dict,
):
    """
    Given an agency with an Active certificate and the Suspend dialog open
    When  I confirm with a 19-character reason, or none
    Then  'Write at least 20 characters.' shows, no confirmation appears and the dialog stays open
    When  I confirm with exactly 20 characters and dismiss the browser confirmation
    Then  the dialog stays open and, after a reload, the certificate is still Active with no new History

    AIO: KAN-TC-635 | data: reason_19_chars / reason_20_chars
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency
    short, minimum = reason_rules_data["short"], reason_rules_data["minimum"]

    with allure.step("Note the newest History entry"):
        lp.open_history(agency)
        before = lp.history_data()[:1]
        lp.close_history()

    with allure.step(f"Open Suspend and confirm with a 19-character reason"):
        lp.open_certificate_action(agency, "suspend")
        lp.fill_action_reason(short.reason)
        confirmation, _ = lp.confirm_certificate_action(answer="dismiss")
        assert confirmation == "", f"A confirmation appeared: {confirmation}"
        expect(lp.action_error).to_have_text(short.expected_error)
        expect(lp.action_dialog).to_be_visible()

    with allure.step("Clear the reason and confirm"):
        lp.fill_action_reason("")
        confirmation, _ = lp.confirm_certificate_action(answer="dismiss")
        assert confirmation == ""
        expect(lp.action_error).to_have_text(short.expected_error)

    with allure.step("Confirm with exactly 20 characters and dismiss the browser confirmation"):
        lp.fill_action_reason(minimum.reason)
        confirmation, _ = lp.confirm_certificate_action(answer="dismiss")
        assert confirmation == "Suspend certificate?", confirmation
        expect(lp.action_dialog).to_be_visible()

    with allure.step("Close the dialog, reload and verify nothing changed"):
        lp.close_action_dialog()
        lp.open(status="all")
        expect(lp.status_badge(agency)).to_have_text("Active")
        lp.open_history(agency)
        assert lp.history_data()[:1] == before, "A History entry was added."


# ---------------------------------------------------------------------------
# TC-636  History
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-636")
@allure.story("Licences & Certificates")
@allure.title("TC-636: History lists every certificate action, or says there are none")
def test_tc636_history(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    short_suspension_data: CertificateActionData,
    lift_data: CertificateActionData,
):
    """
    Given one agency with no certificate actions and one with some (suspended and lifted)
    When  I click History on each
    Then  the first shows 'No certificate actions yet.'
    And   the second shows a timeline, newest first, each entry with a known label, date and time,
          officer and role, and the details

    AIO: KAN-TC-636 | data: suspension_1_day, lift
    """
    lp = logged_in_admin_licenses_page
    labels = re.compile(r"^(Suspended — until .+|Suspension lifted|Restored automatically|Expired.*|Cancelled|"
                        r"Reinstated|Renewed|Renewal applied|Renewal rejected)$")

    with allure.step("Find an agency with no certificate actions"):
        empty = None
        for agency in lp.agency_names():
            if agency == scratch_agency:
                continue
            lp.open_history(agency)
            if lp.history_entries.count() == 0:
                empty = agency
                break
            lp.close_history()
        if empty:
            expect(lp.history_title).to_have_text(f"Certificate history — {empty}")
            expect(lp.history_body).to_have_text(lp.HISTORY_EMPTY)
            lp.close_history()
        else:
            allure.attach("Every agency has certificate actions.", name="no empty history to check")

    with allure.step(f"Given '{scratch_agency}' was suspended and lifted"):
        _act(lp, scratch_agency, short_suspension_data)
        _act(lp, scratch_agency, lift_data)

    with allure.step("Open its History"):
        lp.open_history(scratch_agency)
        entries = lp.history_data()
        allure.attach("\n".join(str(e) for e in entries), name="History")
        assert [e["title"] for e in entries[:2]][0] == "Suspension lifted", entries[:2]
        assert entries[1]["title"].startswith("Suspended — until"), entries[:2]
        times = []
        for e in entries:
            assert labels.match(e["title"]), e
            m = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · .+ \(.+\)$", e["meta"])
            assert m, e
            times.append(m.group(1))
            assert e["body"], e
        assert times == sorted(times, reverse=True), f"Not newest first: {times}"


# ---------------------------------------------------------------------------
# TC-637  District officer powers (Under Review)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-637")
@allure.story("Licences & Certificates")
@allure.title("TC-637: A District officer can suspend but is not offered Expire, Cancel, Reinstate, Lift or validity edits")
def test_tc637_district_officer_powers(page, district_officer_login):
    """
    Given I am logged in as a District officer
    When  I open Licences & certificates
    Then  an Active row offers Suspend, History and View, but not Expire, Cancel or Issue / Renew
    And   a suspended row offers neither Lift suspension nor Reinstate

    Skips unless ADMIN_DISTRICT_USERNAME / ADMIN_DISTRICT_PASSWORD / ADMIN_DISTRICT_NAME are set.
    The direct server requests in the case are not automated.

    AIO: KAN-TC-637 | data: District officer from .env
    """
    district_officer_login()
    lp = AdminLicensesPage(page)
    lp.open(status="all")

    with allure.step("Verify an Active row's actions"):
        agency = lp.agencies_with_status("active")[0]
        labels = lp.row_action_labels(agency)
        assert {"Suspend", "History", "View"} <= set(labels), labels
        assert not {"Expire", "Cancel", "Issue", "Renew", "Reinstate"} & set(labels), labels

    with allure.step("Verify suspended rows offer neither Lift suspension nor Reinstate"):
        for row in lp.table_data():
            if row["status"].startswith("Suspended"):
                labels = lp.row_action_labels(row["agency"])
                assert not {"Lift suspension", "Reinstate"} & set(labels), (row["agency"], labels)


# ---------------------------------------------------------------------------
# TC-639  Renewing an expired certificate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-639")
@allure.story("Licences & Certificates")
@allure.title("TC-639: Renewing an expired certificate makes it active again")
def test_tc639_renew_expired(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    expiry_data: CertificateActionData,
    valid_renewal_data: LicenseData,
):
    """
    Given an agency whose certificate is Expired
    When  I renew it from today for 5 years
    Then  the row is Active with the new Valid Upto and a green bar
    And   it is listed under Active and not under Expired
    And   History shows 'Renewed' (known failure 03-Nov-2026: no entry is added)

    AIO: KAN-TC-639 | data: expiry, valid_renewal
    """
    lp = logged_in_admin_licenses_page
    agency, data = scratch_agency, valid_renewal_data

    with allure.step(f"Given '{agency}' is expired"):
        _act(lp, agency, expiry_data)
        expect(lp.status_badge(agency)).to_have_text("Expired")

    with allure.step("Renew it from today for 5 years"):
        lp.open_renew_modal(agency)
        expect(lp.issue_modal_title).to_have_text(f"Renew — {agency}")
        expect(lp.modal_agency_select).to_be_disabled()
        lp.fill_modal_valid_from(data.valid_from)
        lp.click_quick_duration(data.duration_years)
        lp.save_modal_and_wait()

    with allure.step("Verify the row is Active"):
        expect(lp.status_badge(agency)).to_have_text("Active")
        expect(lp.valid_upto_cell(agency)).to_contain_text(_display(data.valid_upto))
        expect(lp.days_left_bar_fill(agency)).to_have_attribute("style", GREEN_BAR)

    with allure.step("Verify the chips"):
        lp.filter_by_status("active")
        expect(lp.license_row(agency)).to_have_count(1)
        lp.filter_by_status("expired")
        expect(lp.license_row(agency)).to_have_count(0)

    with allure.step("Verify History shows 'Renewed'"):
        lp.open(status="all")
        lp.open_history(agency)
        expect(lp.history_entries.first.locator(".t-title")).to_have_text("Renewed")


# ---------------------------------------------------------------------------
# TC-640  Search with no match
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-640")
@allure.story("Licences & Certificates")
@allure.title("TC-640: A search with no match shows an empty table and keeps the search and chip")
def test_tc640_search_no_match(logged_in_admin_licenses_page: AdminLicensesPage, no_match_search: str):
    """
    Given I am on the Active chip
    When  I search for text no agency has
    Then  the table shows 'No approved agencies found.', the search box keeps the text and Active stays
          highlighted

    AIO: KAN-TC-640 | data: no_match_search
    """
    lp = logged_in_admin_licenses_page

    with allure.step(f"Click Active and search for '{no_match_search}'"):
        lp.filter_by_status("active")
        lp.search(no_match_search)

    with allure.step("Verify the empty table, search text and chip"):
        expect(lp.license_rows).to_have_count(0)
        expect(lp.empty_table_row).to_have_text(lp.EMPTY_TABLE)
        expect(lp.search_input).to_have_value(no_match_search)
        expect(lp.selected_stat_chip).to_have_attribute("href", re.compile(r"status=active&"))


# ---------------------------------------------------------------------------
# TC-641  Dialog dismissal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-641")
@allure.story("Licences & Certificates")
@allure.title("TC-641: Close, ✕, Esc or a click outside closes a dialog without changing anything")
def test_tc641_dialog_dismissal(logged_in_admin_licenses_page: AdminLicensesPage, scratch_agency: str):
    """
    Given an agency with an Active certificate
    When  I close the Suspend dialog with Close, Esc, ✕ and a click outside; the Renew modal with ✕, Esc
          and Cancel; Issue License with a click outside; and History with Esc
    Then  each closes, and after a reload the status, dates and History are unchanged

    AIO: KAN-TC-641 | data: none
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency
    dates = lp.get_row_validity_dates(agency)
    lp.open_history(agency)
    history = lp.history_data()[:1]
    lp.close_history()
    expect(lp.history_dialog).to_be_hidden()

    for how, close in (("Close", lp.close_action_dialog), ("Esc", lp.press_escape),
                       ("✕", lambda: lp.action_dialog_x_button.click()), ("a click outside", lp.click_outside_action_dialog)):
        with allure.step(f"Open Suspend, type a reason and close it with {how}"):
            lp.open_certificate_action(agency, "suspend")
            lp.fill_action_reason("A valid reason that is never confirmed")
            expect(lp.action_dialog).to_be_visible()
            close()
            expect(lp.action_dialog).to_be_hidden()

    for how, close in (("✕", lp.close_modal), ("Esc", lp.press_escape), ("Cancel", lp.cancel_modal)):
        with allure.step(f"Open Renew and close it with {how}"):
            lp.open_renew_modal(agency)
            expect(lp.issue_modal).to_be_visible()
            close()
            expect(lp.issue_modal).to_be_hidden()

    with allure.step("Open Issue / Renew License and click outside it"):
        lp.open_issue_modal()
        expect(lp.issue_modal).to_be_visible()
        lp.click_outside_modal()
        expect(lp.issue_modal).to_be_hidden()

    with allure.step("Open History and press Esc"):
        lp.open_history(agency)
        expect(lp.history_dialog).to_be_visible()
        lp.press_escape()
        expect(lp.history_dialog).to_be_hidden()

    with allure.step("Reload and verify nothing changed"):
        lp.open(status="all")
        expect(lp.status_badge(agency)).to_have_text("Active")
        assert lp.get_row_validity_dates(agency) == dates
        lp.open_history(agency)
        assert lp.history_data()[:1] == history, "A History entry was added."


# ---------------------------------------------------------------------------
# TC-642  Actions offered by state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-642")
@allure.story("Licences & Certificates")
@allure.title("TC-642: Actions offered match the certificate's state")
def test_tc642_actions_by_state(
    logged_in_admin_licenses_page: AdminLicensesPage,
    scratch_agency: str,
    short_suspension_data: CertificateActionData,
    lift_data: CertificateActionData,
    expiry_data: CertificateActionData,
    cancellation_data: CertificateActionData,
    reinstatement_data: CertificateActionData,
):
    """
    Given certificates that are Active, Expiring, Suspended, Expired and Cancelled (the last three made
          on one agency in turn)
    Then  Active / Expiring rows offer Suspend, Expire, Cancel, History, Issue or Renew and View, but not
          Lift suspension or Reinstate (known failure 03-Nov-2026: an Expiring row offers Reinstate)
    And   a Suspended row offers Lift suspension, not Suspend or Reinstate
    And   an Expired row offers Reinstate, not Lift suspension
    And   a Cancelled row offers Reinstate, not Suspend, Expire or Cancel

    AIO: KAN-TC-642 | data: suspension_1_day, lift, expiry, cancellation, reinstatement
    """
    lp = logged_in_admin_licenses_page
    agency = scratch_agency
    problems = []

    def check(name, state, offered, not_offered):
        labels = set(lp.row_action_labels(name))
        allure.attach(", ".join(sorted(labels)), name=f"{state}: {name}")
        if not offered <= labels or labels & not_offered:
            problems.append(f"{state} '{name}': offers {sorted(labels)}; needs {sorted(offered)}, "
                            f"must not offer {sorted(not_offered)}")

    with allure.step("Check every Active and Expiring row"):
        for status in ("active", "expiring"):
            for name in lp.agencies_with_status(status):
                labels = set(lp.row_action_labels(name))
                check(name, status, {"Suspend", "Expire", "Cancel", "History", "View"}, {"Lift suspension", "Reinstate"})
                if not labels & {"Issue", "Renew"}:
                    problems.append(f"{status} '{name}': offers neither Issue nor Renew")

    with allure.step(f"Suspend '{agency}' and check its actions, then lift"):
        _act(lp, agency, short_suspension_data)
        check(agency, "Suspended", {"Lift suspension"}, {"Suspend", "Reinstate"})
        _act(lp, agency, lift_data)

    with allure.step(f"Expire '{agency}' and check its actions, then reinstate"):
        _act(lp, agency, expiry_data)
        check(agency, "Expired", {"Reinstate"}, {"Lift suspension"})
        _act(lp, agency, reinstatement_data)

    with allure.step(f"Cancel '{agency}' and check its actions (reinstated on teardown)"):
        _act(lp, agency, cancellation_data)
        check(agency, "Cancelled", {"Reinstate"}, {"Suspend", "Expire", "Cancel"})

    assert not problems, "\n".join(problems)
