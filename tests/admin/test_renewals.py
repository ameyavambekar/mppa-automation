"""KAN-37 — Licence Renewal (Form-II), officer side: Licences & certificates → Renewal applications
(admin/licenses/renewals.php).

The pending renewal is found by reading the agencies' renewal pages; with RUN_RENEWAL_TESTS=true one is
submitted (after expiring a certificate if need be) when none is pending. KAN-TC-829 rejects it and KAN-TC-414
approves one (a rejected agency can file again); both only run
with RUN_RENEWAL_TESTS=true (irreversible on dev).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.renewals_page import AdminRenewalsPage
from pages.agency_home_page import AgencyHomePage
from pages.license_renewal_page import LicenseRenewalPage
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Licence Renewal"
IST = timezone(timedelta(hours=5, minutes=30))
DATE = r"\d{2} [A-Z][a-z]{2} \d{4}"


def _today():
    return datetime.now(IST).date()


def _fmt(day) -> str:
    return day.strftime("%d %b %Y")


def _parse(text: str):
    return datetime.strptime(re.search(DATE, text).group(), "%d %b %Y").date()


def _renewed_expiry(current_expiry):
    """5 more years from the current expiry, or from today when already expired (the day before the anniversary)."""
    start = _today() if current_expiry < _today() else current_expiry + timedelta(days=1)
    return start.replace(year=start.year + 5) - timedelta(days=1)


@aio_case("KAN-TC-412")
@allure.story(STORY)
@allure.title("TC-412: The officer sees a submitted renewal under Pending decision")
def test_tc412_pending_listed(page, officer_pending_renewal):
    """
    Given an agency has submitted a renewal (No / No)
    When  I open Licences & certificates → Renewal applications
    Then  the page shows its heading, note and tabs with counts, and the agency's row under Pending decision
          shows its details, the declarations, the fee with its reference, Pending and Approve / Reject /
          Application; the All tab lists it too and Application opens the agency's application

    Notion: KAN-TC-412 | KAN-37 AC-10
    """
    renewals, user = officer_pending_renewal
    reg = user.application_id

    with allure.step("Verify the heading, note and tabs"):
        expect(renewals.heading).to_have_text(AdminRenewalsPage.HEADING)
        expect(renewals.note).to_have_text(AdminRenewalsPage.NOTE)
        expect(renewals.tabs).to_have_text([re.compile(rf"^{label}\s*\d+$") for label in AdminRenewalsPage.TABS.values()])
        expect(renewals.selected_tab).to_contain_text(AdminRenewalsPage.TABS["submitted"])
        expect(renewals.table_headers).to_have_text(list(AdminRenewalsPage.COLUMNS))

    with allure.step(f"Verify the row of {user.agency_name} under Pending decision"):
        expect(renewals.rows_of(reg)).to_have_count(1)
        number = renewals.renewal_number(reg)
        assert re.fullmatch(r"\d+", number), f"# is '{number}'"
        expect(renewals.agency_name(reg)).to_have_text(user.agency_name)
        if user.district and user.district != "Other":
            assert renewals.cell_text(reg, "District") == user.district
        assert re.fullmatch(rf"Up to {DATE}", renewals.cell_text(reg, "Current validity")), \
            renewals.cell_text(reg, "Current validity")
        assert re.fullmatch(DATE, renewals.cell_text(reg, "Applied")), renewals.cell_text(reg, "Applied")
        assert renewals.cell_text(reg, "Declarations") == "Changes since registration: No Cases / suspension: No"
        assert re.fullmatch(r"₹2,000 \S+", renewals.cell_text(reg, "Fee")), renewals.cell_text(reg, "Fee")
        expect(renewals.status_badge(reg)).to_have_text(AdminRenewalsPage.PENDING)
        assert renewals.action_labels(reg) == [AdminRenewalsPage.APPROVE_LABEL, AdminRenewalsPage.REJECT_LABEL,
                                               AdminRenewalsPage.APPLICATION_LABEL], renewals.action_labels(reg)

    with allure.step("Open the All tab — the application is listed and counted"):
        renewals.open_tab("all")
        expect(renewals.selected_tab).to_contain_text(AdminRenewalsPage.TABS["all"])
        expect(renewals.row(reg, number)).to_have_count(1)
        expect(renewals.status_badge(reg, number)).to_have_text(AdminRenewalsPage.PENDING)
        assert renewals.get_tab_count("all") == renewals.rows.count()

    with allure.step("Click Application — the agency's application opens"):
        renewals.open_application(reg, number)
        expect(page).to_have_url(re.compile(r"/dashboard/agency_view\.php\?id=\d+$"))


@aio_case("KAN-TC-413")
@allure.story(STORY)
@allure.title("TC-413: The decision dialog needs at least 5 characters to approve and 30 to reject")
def test_tc413_remarks_minimum(officer_pending_renewal, renewal_short_remarks_data):
    """
    Given a renewal is pending
    When  I open Reject and Approve and confirm with remarks that are too short
    Then  each dialog shows its title, note and placeholder, and asks for at least 30 / 5 characters; nothing is
          sent and the renewal stays pending

    Notion: KAN-TC-413 | KAN-37 AC-13 | Data: "Too short" (reject), "ok" (approve)
    """
    renewals, user = officer_pending_renewal
    reg = user.application_id
    for data in renewal_short_remarks_data:
        with allure.step(f"Click {data.decision.title()} — the dialog opens"):
            renewals.open_decision(reg, data.decision)
            expect(renewals.dialog_title).to_have_text(
                AdminRenewalsPage.DIALOG_TITLE[data.decision].format(name=user.agency_name))
            expect(renewals.dialog_note).to_have_text(AdminRenewalsPage.DIALOG_NOTE[data.decision])
            expect(renewals.remarks_input).to_have_attribute(
                "placeholder", AdminRenewalsPage.REMARKS_PLACEHOLDER[data.decision])

        with allure.step(f"Confirm with '{data.remarks}' — {data.expected_error}"):
            renewals.fill_remarks(data.remarks)
            renewals.confirm()
            expect(renewals.dialog_error).to_have_text(data.expected_error)
            renewals.close_dialog()

    with allure.step("Reload — the renewal is still pending"):
        renewals.open(tab="submitted")
        expect(renewals.status_badge(reg)).to_have_text(AdminRenewalsPage.PENDING)


@aio_case("KAN-TC-829")
@allure.story(STORY)
@allure.title("TC-829: Rejecting a renewal leaves the certificate as it was and tells the agency why")
def test_tc829_reject_renewal(officer_pending_renewal_to_decide, renewal_rejection_data,
                              renewal_admin_licenses_page: AdminLicensesPage, renewal_page: LicenseRenewalPage,
                              renewal_agency_login):
    """
    Given an agency with an expired certificate has a renewal pending
    When  I reject it with reasons of 30 characters or more
    Then  the renewal moves to Rejected, the certificate's status and validity do not change, History records
          the rejection with the reasons, and the agency sees the rejection with the reasons on its renewal page
          and on Home — and can file a new renewal

    Notion: KAN-TC-829 | KAN-37 AC-12 | Data: reasons of 30+ characters — irreversible (RUN_RENEWAL_TESTS)
    """
    renewals, user = officer_pending_renewal_to_decide
    reg, name = user.application_id, user.agency_name
    licenses = renewal_admin_licenses_page
    reasons = renewal_rejection_data.remarks
    today = _fmt(_today())

    with allure.step("Read the certificate on Licences & certificates before the decision"):
        licenses.open(status="all")
        status_before = licenses.status_badge(name).text_content().strip()
        validity_before = licenses.get_row_validity_dates(name)
        expired_before = licenses.get_stat_chip_count("expired")

    with allure.step("Reject the renewal with reasons"):
        renewals.open(tab="submitted")
        number = renewals.renewal_number(reg)
        toast = renewals.decide(reg, "reject", reasons)
        allure.attach(toast, "Toast", allure.attachment_type.TEXT)
        assert toast, "No toast after rejecting"

    with allure.step(f"Verify the tabs: renewal #{number} is no longer pending and is listed under Rejected"):
        renewals.open(tab="submitted")
        expect(renewals.row(reg, number)).to_have_count(0)
        renewals.open(tab="rejected")
        expect(renewals.row(reg, number)).to_have_count(1)
        expect(renewals.status_badge(reg, number)).to_have_text(AdminRenewalsPage.REJECTED)
        expect(renewals.status_badge(reg, number)).to_have_class(re.compile(r"\bui-badge-red\b"))
        expect(renewals.decided_by(reg, number)).to_have_text(re.compile(rf"^{today} · \S.*$"))
        assert renewals.action_labels(reg, number) == [AdminRenewalsPage.APPLICATION_LABEL], \
            renewals.action_labels(reg, number)

    with allure.step("Verify the certificate on Licences & certificates has not changed"):
        licenses.open(status="all")
        expect(licenses.status_badge(name)).to_have_text(status_before)
        assert licenses.get_row_validity_dates(name) == validity_before
        assert licenses.get_stat_chip_count("expired") == expired_before

    with allure.step("Verify the certificate History records the rejection"):
        licenses.open_history(name)
        entry = licenses.history_data()[0]
        assert entry["title"] == "Renewal rejected", entry
        assert entry["body"] == f"Renewal application #{number} rejected: {reasons}", entry
        licenses.close_history()

    with allure.step("As the agency, verify the renewal page shows the rejection and the form again"):
        renewal_agency_login(user)
        renewal_page.open()
        expect(renewal_page.latest_application).to_contain_text(
            re.compile(rf"Latest renewal application #{number} — filed {DATE}\s*·\s*{LicenseRenewalPage.REJECTED}"))
        expect(renewal_page.latest_application).to_contain_text(LicenseRenewalPage.rejection_reason(reasons))
        expect(renewal_page.form).to_be_visible()
        expect(renewal_page.submit_button).to_be_visible()

    with allure.step("Verify the rejection notification on Home"):
        home = AgencyHomePage(renewal_page.page)
        home.open()
        home.dismiss_testing_notice()
        title = AgencyHomePage.RENEWAL_REJECTED_NOTIFICATION
        expect(home.notification_title(title).first).to_have_text(title)
        expect(home.notification_message(title).first).to_have_text(
            AgencyHomePage.RENEWAL_REJECTED_NOTIFICATION_TEXT.format(reasons=reasons))
        expect(home.start_renewal_button).to_be_visible()


@aio_case("KAN-TC-414")
@allure.story(STORY)
@allure.title("TC-414: Approving a renewal of an expired certificate renews it for 5 years from today")
def test_tc414_approve_expired(officer_pending_renewal_to_decide, renewal_approval_data,
                               renewal_admin_licenses_page: AdminLicensesPage):
    """
    Given an agency with an expired certificate has a renewal pending
    When  I approve it with remarks
    Then  the toast gives the new expiry (5 years from today), the renewal moves to Renewed, Licences &
          certificates shows the certificate Active from today to the new expiry, and History records the renewal
          above the application

    Notion: KAN-TC-414 | KAN-37 AC-11, EC-6 | Data: "Documents verified, no adverse report." — irreversible
    (RUN_RENEWAL_TESTS) | Known defect: Licence Renewal Application #16 (Valid From keeps the original date) —
    this test fails on the last step
    """
    renewals, user = officer_pending_renewal_to_decide
    reg, name = user.application_id, user.agency_name
    licenses = renewal_admin_licenses_page
    today = _fmt(_today())

    with allure.step("Read the certificate on Licences & certificates before the decision"):
        licenses.open(status="all")
        expired_before = licenses.get_stat_chip_count("expired")
        current_expiry = _parse(licenses.valid_upto_cell(name).text_content())
        new_expiry = _fmt(_renewed_expiry(current_expiry))

    with allure.step(f"Approve the renewal — the certificate is valid up to {new_expiry}"):
        renewals.open(tab="submitted")
        number = renewals.renewal_number(reg)
        toast = renewals.decide(reg, "approve", renewal_approval_data.remarks)
        assert toast == AdminRenewalsPage.approved_toast(new_expiry), toast
        TestStateStore().record_agency_status(username=user.username, status="approved")

    with allure.step(f"Verify the tabs: renewal #{number} is no longer pending and is listed under Renewed"):
        renewals.open(tab="submitted")
        expect(renewals.row(reg, number)).to_have_count(0)
        renewals.open(tab="approved")
        expect(renewals.row(reg, number)).to_have_count(1)
        expect(renewals.cell(reg, "Current validity", number)).to_contain_text(f"Renewed to {new_expiry}")
        expect(renewals.status_badge(reg, number)).to_have_text(AdminRenewalsPage.RENEWED)
        expect(renewals.decided_by(reg, number)).to_have_text(re.compile(rf"^{today} · \S.*$"))
        assert renewals.action_labels(reg, number) == [AdminRenewalsPage.APPLICATION_LABEL], \
            renewals.action_labels(reg, number)

    with allure.step("Verify Licences & certificates"):
        licenses.open(status="all")
        expect(licenses.status_badge(name)).to_have_text("Active")
        expect(licenses.valid_upto_cell(name)).to_contain_text(new_expiry)
        days_left = (_renewed_expiry(current_expiry) - _today()).days
        expect(licenses.days_left_cell(name)).to_contain_text(f"{days_left} days")
        assert licenses.get_stat_chip_count("expired") == expired_before - 1

    with allure.step("Verify the certificate History"):
        licenses.open_history(name)
        entries = licenses.history_data()
        assert entries[0]["title"] == "Renewed", entries[:2]
        assert re.search(rf"Renewal #\d+ approved — certificate valid from {today} to {new_expiry}\. "
                         rf"{re.escape(renewal_approval_data.remarks)}", entries[0]["body"]), entries[0]
        assert entries[1]["title"] == "Renewal applied" and "₹2,000" in entries[1]["body"], entries[:2]
        licenses.close_history()

    with allure.step(f"Verify Valid From is today ({today}) — defect #16"):
        expect(licenses.valid_from_cell(name)).to_contain_text(today)
