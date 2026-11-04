"""
Compliance Cases — Admin Portal (KAN-46)
========================================
Covers KAN-TC-644…671, 674, 675 and 677 (Enforcement › Compliance cases,
/module/admin/compliance/index.php), logged in as the Super Admin.

Tests that open cases work on ``compliance_agency`` — the second-last Active
agency on Licences & certificates (the last one belongs to the Licences tests).
On teardown its open cases are dropped and its certificate is made Active again
with its original dates; the cases and their History stay on the page.

Not automated: KAN-TC-672 (a suspension reaching its 6-month limit) and
KAN-TC-673 (the 15-day show cause date passing) need dates set in the database,
and KAN-TC-676 (what the agency sees) is under review. KAN-TC-670 (district
officer) skips unless ADMIN_DISTRICT_USERNAME / ADMIN_DISTRICT_PASSWORD /
ADMIN_DISTRICT_NAME are set.

Known failures (03-Nov-2026, defect sheet "Super admin"): TC-651 and TC-668
(the show cause due date and "Suspension valid until" are 5 h 30 min behind —
UTC — #64), TC-665 (opening a Route A case, the hearing, the window and the
drop leave no Audit log entry — #65), TC-675 (lifting the suspension on
Licences & certificates leaves the case at "Interim suspension" — #66) and
TC-677 (the window and the cancellation order are offered as soon as a hearing
is scheduled, before it takes place — #67).
"""

import os
import re
from datetime import datetime, timedelta

import allure
from playwright.sync_api import expect

from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.compliance_page import ADMIN_COMPLIANCE_URL, AdminCompliancePage
from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.login_page import AdminLoginPage
from test_data.compliance_factory import CaseActionData, ComplianceCaseData, ComplianceFactory
from utils.aio import aio_case

STORY = "Compliance Cases"
STAMP = "%Y-%m-%d %H:%M:%S"


def _stamp(text: str) -> datetime:
    """'2026-11-03 17:48:01' (as the page shows it) → datetime."""
    return datetime.strptime(re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text).group(), STAMP)


def _plus_months(when: datetime, months: int) -> datetime:
    month = when.month - 1 + months
    year, month = when.year + month // 12, month % 12 + 1
    return when.replace(year=year, month=month, day=min(when.day, 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31))


def _licence_badge(cp: AdminCompliancePage, agency: str):
    """Opens Licences & certificates and returns the agency's status label."""
    lp = AdminLicensesPage(cp.page)
    lp.open(status="all")
    return lp.status_badge(agency)


def _badge_class(colour: str):
    return re.compile(rf"\bui-badge-{colour}\b")


# ---------------------------------------------------------------------------
# TC-644  Page loads from the sidebar
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-644")
@allure.story(STORY)
@allure.title("TC-644: Compliance cases page loads from the sidebar")
def test_tc644_page_loads_from_sidebar(logged_in_admin_compliance_page: AdminCompliancePage):
    """
    Given I am logged in to the Officer Console as the Super Administrator
    When  I click "Compliance cases" under Enforcement in the sidebar
    Then  the page shows its title, heading, subtitle, "Open new case" and the case table
    And   with no cases the table shows "No compliance cases."

    AIO: KAN-TC-644 | KAN-46 AC-1
    """
    cp = logged_in_admin_compliance_page

    with allure.step("Click 'Compliance cases' in the sidebar"):
        cp.sidebar.compliance_link.click()
        cp.wait_for_table()
        expect(cp.page).to_have_url(re.compile(re.escape(ADMIN_COMPLIANCE_URL) + r"$"))
        expect(cp.page).to_have_title(cp.TITLE)

    with allure.step("Verify the heading, subtitle and 'Open new case'"):
        expect(cp.heading).to_have_text(cp.HEADING)
        expect(cp.subtitle).to_have_text(cp.SUBTITLE)
        expect(cp.open_new_case_button).to_have_text("Open new case")

    with allure.step("Verify the table columns and rows"):
        expect(cp.table_headers).to_have_text(list(cp.COLUMNS))
        if cp.case_rows.count() == 0:
            expect(cp.empty_table_row).to_have_text(cp.EMPTY_TABLE)
        else:
            expect(cp.case_rows.locator("button", has_text="Open")).to_have_count(cp.case_rows.count())


# ---------------------------------------------------------------------------
# TC-645  Row content
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-645")
@allure.story(STORY)
@allure.title("TC-645: Each case row shows its number, agency, district, route, status and opened time")
def test_tc645_row_content(logged_in_admin_compliance_page: AdminCompliancePage):
    """
    Given at least one compliance case exists
    Then  each row shows CMP/<year>/<6 hex>, the agency with its 13-digit Application ID, the district,
          Route "High risk" (red) or "Regular" (gray), a status badge in its colour, the opened time and Open

    AIO: KAN-TC-645 | KAN-46 AC-1 | data: live case list
    """
    cp = logged_in_admin_compliance_page
    rows = cp.rows_data()
    allure.attach(str(rows), name="rows")
    assert rows, "No compliance case on the page."

    for row in rows:
        with allure.step(f"Check {row['case_no']}"):
            assert re.fullmatch(r"CMP/\d{4}/[0-9A-F]{6}", row["case_no"]), row
            assert row["agency"] and re.fullmatch(r"\d{13}", row["reg_id"]), row
            assert row["district"], row
            assert (row["route"], "ui-badge-red" in row["route_class"]) in (("High risk", True), ("Regular", False)), row
            assert row["status"] in cp.STATUS_BADGES, row
            assert f"ui-badge-{cp.STATUS_BADGES[row['status']]}" in row["status_class"], row
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", row["opened"]), row
            assert row["open"] == "Open", row


# ---------------------------------------------------------------------------
# TC-646  Open compliance case form
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-646")
@allure.story(STORY)
@allure.title("TC-646: Open new case shows the Open compliance case form")
def test_tc646_open_case_form(logged_in_admin_compliance_page: AdminCompliancePage):
    """
    Given I am on Compliance cases
    When  I click "Open new case"
    Then  the "Open compliance case" dialog shows Agency (required), Trigger with its four choices, Details
          (required) and Immediate public risk? with No (Route A) selected and Yes (Route B)
    And   "Reasons in writing" is not shown

    AIO: KAN-TC-646 | KAN-46 AC-2
    """
    cp = logged_in_admin_compliance_page

    with allure.step("Click 'Open new case'"):
        cp.open_new_case()
        expect(cp.new_case_dialog).to_have_class(re.compile(r"\bis-open\b"))
        expect(cp.new_case_title).to_have_text("Open compliance case")

    with allure.step("Verify the fields"):
        expect(cp.new_case_label("agency_id")).to_have_text("Agency")
        expect(cp.agency_select).to_have_attribute("required", "")
        expect(cp.agency_select.locator("option:checked")).to_have_text("Select an approved agency")
        expect(cp.new_case_label("trigger_type")).to_have_text("Trigger")
        expect(cp.trigger_select.locator("option")).to_have_text(list(cp.TRIGGERS.values()))
        expect(cp.new_case_label("trigger_details")).to_have_text("Details of the complaint / finding")
        expect(cp.details_input).to_have_attribute("required", "")
        expect(cp.new_case_label("high_risk")).to_have_text("Immediate public risk? (Sec 6(2))")
        expect(cp.risk_select.locator("option")).to_have_text(list(cp.RISK_OPTIONS.values()))
        expect(cp.risk_select).to_have_value("0")
        expect(cp.open_case_button).to_have_text("Open case")

    with allure.step("Verify Reasons in writing is hidden"):
        expect(cp.risk_box).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-647  Agency lists only approved agencies
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-647")
@allure.story(STORY)
@allure.title("TC-647: Agency lists only approved agencies")
def test_tc647_agency_lists_approved_agencies(logged_in_admin_compliance_page: AdminCompliancePage):
    """
    Given the approved agencies listed on Licences & certificates (Approved chip)
    When  I open the Agency list of "Open new case"
    Then  it lists exactly those agencies, each as "Name — ApplicationID"

    AIO: KAN-TC-647 | KAN-46 AC-2
    """
    cp = logged_in_admin_compliance_page

    with allure.step("Read the approved agencies on Licences & certificates"):
        lp = AdminLicensesPage(cp.page)
        lp.open(status="all")
        approved = sorted(lp.agency_names())

    with allure.step("Open the Agency list on Compliance cases"):
        cp.open()
        cp.open_new_case()
        offered = cp.agency_options.all_text_contents()
        allure.attach("\n".join(offered), name="agency options")

    with allure.step("Verify every option is 'Name — ApplicationID' and the agencies match"):
        assert all(re.fullmatch(r".+ — \d{13}", o.strip()) for o in offered), offered
        assert sorted(cp.agency_option_names()) == approved


# ---------------------------------------------------------------------------
# TC-648  Yes shows Reasons in writing
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-648")
@allure.story(STORY)
@allure.title("TC-648: Choosing Yes shows Reasons in writing with the suspension rules; No hides it")
def test_tc648_yes_shows_reasons(logged_in_admin_compliance_page: AdminCompliancePage):
    """
    Given the Open compliance case dialog is open
    When  I choose Yes for Immediate public risk?
    Then  "Reasons in writing (mandatory for suspension)" appears with the 6-month / 15-day help text
    When  I choose No
    Then  it is hidden again

    AIO: KAN-TC-648 | KAN-46 AC-5
    """
    cp = logged_in_admin_compliance_page
    cp.open_new_case()

    with allure.step("Choose Yes"):
        cp.set_high_risk(True)
        expect(cp.risk_box).to_be_visible()
        expect(cp.risk_reasons_label).to_have_text(cp.RISK_REASONS_LABEL)
        expect(cp.risk_help).to_have_text(cp.RISK_HELP)

    with allure.step("Choose No"):
        cp.set_high_risk(False)
        expect(cp.risk_box).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-649  Required fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-649")
@allure.story(STORY)
@allure.title("TC-649: Open case is refused without an agency, a trigger or details")
def test_tc649_required_fields(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                               route_a_data: ComplianceCaseData, short_details_data: ComplianceCaseData):
    """
    Given the Open compliance case dialog is open
    When  I click "Open case" without an agency, or without details
    Then  the browser flags the empty field and no case is opened
    And   Trigger always has a value (Complaint by default — there is no empty choice)
    When  the details are shorter than 10 characters
    Then  "Describe the complaint / finding (at least 10 characters)." is shown and no case is opened

    AIO: KAN-TC-649 | KAN-46 AC-3 | data: {route_a_data.scenario_label}, {short_details_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    before = len(cp.cases_for(compliance_agency))
    cp.open_new_case()

    with allure.step("Leave Agency empty and click 'Open case'"):
        cp.fill_new_case(details=route_a_data.details)
        _, toast = cp.submit_new_case()
        assert toast == ""
        assert cp.validation_message(cp.agency_select), "Agency is not flagged"

    with allure.step("Verify Trigger has no empty choice and defaults to Complaint"):
        expect(cp.trigger_select).to_have_value("complaint")
        expect(cp.trigger_select.locator("option[value='']")).to_have_count(0)

    with allure.step("Choose the agency, leave Details empty and click 'Open case'"):
        cp.fill_new_case(agency_name=compliance_agency, details="")
        _, toast = cp.submit_new_case()
        assert toast == ""
        assert cp.validation_message(cp.details_input), "Details is not flagged"

    with allure.step(f"Enter 9-character details and click 'Open case'"):
        cp.fill_details(short_details_data.details)
        _, toast = cp.submit_new_case()
        assert toast == short_details_data.expected_error

    with allure.step("Verify no case was opened"):
        cp.close_new_case()
        cp.open()
        assert len(cp.cases_for(compliance_agency)) == before


# ---------------------------------------------------------------------------
# TC-650  Route A
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-650")
@allure.story(STORY)
@allure.title("TC-650: Route A opens a regular inquiry and the agency stays active")
def test_tc650_route_a_opens_inquiry(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                                     route_a_data: ComplianceCaseData):
    """
    Given an agency with an Active certificate and no open case
    When  I open a case with Immediate public risk? = No
    Then  "Case CMP/<year>/<code>: pre-cancellation show cause notice issued; agency remains active during the
          inquiry." is shown and the case is listed with Route Regular, Status under inquiry (amber) and
          Opened = now (IST)
    And   the agency's certificate is still Active

    AIO: KAN-TC-650 | KAN-46 AC-4 | data: {route_a_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page

    with allure.step("Open a Route A case"):
        case_no, toast = cp.open_case_for(compliance_agency, route_a_data.trigger, route_a_data.details)
        assert toast == f"Case {case_no}: {route_a_data.expected_message}", toast

    with allure.step("Verify the new row"):
        row = next(r for r in cp.rows_data() if r["case_no"] == case_no)
        allure.attach(str(row), name="row")
        assert re.fullmatch(rf"CMP/{ComplianceFactory.now_ist().year}/[0-9A-F]{{6}}", case_no)
        assert row["agency"] == compliance_agency
        expect(cp.route_badge(case_no)).to_have_text("Regular")
        expect(cp.status_badge(case_no)).to_have_text("under inquiry")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("amber"))
        assert abs(_stamp(row["opened"]) - ComplianceFactory.now_ist()) < timedelta(minutes=3), row["opened"]

    with allure.step("Verify the certificate is still Active on Licences & certificates"):
        expect(_licence_badge(cp, compliance_agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-651  Show cause notice due in 15 days
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-651")
@allure.story(STORY)
@allure.title("TC-651: Opening a case issues a show cause notice due in 15 days")
def test_tc651_show_cause_notice(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                                 route_a_data: ComplianceCaseData):
    """
    Given a Route A case was just opened
    When  I open it
    Then  Status is "Under inquiry (agency active)" and Trigger is "complaint — <details>"
    And   History has one "opened" entry: time · officer, and the show cause notice text with the details
    And   the show cause reply is due exactly 15 days after the case was opened

    AIO: KAN-TC-651 | KAN-46 AC-4 | data: {route_a_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case

    with allure.step("Open the case"):
        case = cp.open_case(case_no)
        allure.attach(str(case), name="case record")

    with allure.step("Verify Status and Trigger"):
        expect(cp.case_field("Status")).to_have_text("Status: Under inquiry (agency active)")
        expect(cp.case_field("Trigger")).to_have_text(f"Trigger: complaint — {route_a_data.details}")

    with allure.step("Verify the History entry"):
        history = cp.history_data()
        assert len(history) == 1 and history[0]["title"] == "opened", history
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} · .+", history[0]["meta"]), history
        assert f"Case {case_no}: {route_a_data.expected_message}" in history[0]["body"], history
        assert route_a_data.details in history[0]["body"], history

    with allure.step("Verify the reply is due 15 days after opening"):
        opened, due = _stamp(case["created_at"]), _stamp(case["scn_due_at"])
        assert due - opened == timedelta(days=15), f"opened {opened}, show cause reply due {due}"


# ---------------------------------------------------------------------------
# TC-652  Cancelling the suspension confirmation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-652")
@allure.story(STORY)
@allure.title("TC-652: Cancelling the suspension confirmation opens no case")
def test_tc652_cancel_suspension_confirm(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                                         route_b_data: ComplianceCaseData):
    """
    Given the Open compliance case form is filled for Route B with reasons
    When  I click "Open case"
    Then  "This will SUSPEND the agency immediately. Continue?" is asked
    When  I cancel
    Then  the dialog stays open, no case is opened and the certificate is still Active

    AIO: KAN-TC-652 | KAN-46 AC-5 | data: {route_b_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    before = len(cp.cases_for(compliance_agency))

    with allure.step("Fill the form for Route B and click 'Open case', then Cancel"):
        cp.open_new_case()
        cp.fill_new_case(compliance_agency, route_b_data.trigger, route_b_data.details, True, route_b_data.reasons)
        confirm, toast = cp.submit_new_case("dismiss")
        assert confirm == cp.SUSPEND_CONFIRM
        assert toast == ""
        expect(cp.new_case_dialog).to_have_class(re.compile(r"\bis-open\b"))

    with allure.step("Verify no case was opened"):
        cp.close_new_case()
        cp.open()
        assert len(cp.cases_for(compliance_agency)) == before

    with allure.step("Verify the certificate is still Active"):
        expect(_licence_badge(cp, compliance_agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-653  Route B suspends the agency
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-653")
@allure.story(STORY)
@allure.title("TC-653: Route B suspends the agency at once")
def test_tc653_route_b_suspends(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                                route_b_data: ComplianceCaseData):
    """
    Given an agency with an Active certificate and no open case
    When  I open a case with Immediate public risk? = Yes and reasons, and confirm the suspension
    Then  "Case <no>: interim suspension ordered (max 6 months) and 15-day show cause notice issued." is shown
    And   the case is listed with Route High risk (red) and Status suspended (red)
    And   the agency's certificate shows as Suspended on Licences & certificates

    AIO: KAN-TC-653 | KAN-46 AC-5 | data: {route_b_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page

    with allure.step("Open a Route B case and confirm"):
        cp.open_new_case()
        cp.fill_new_case(compliance_agency, route_b_data.trigger, route_b_data.details, True, route_b_data.reasons)
        confirm, toast = cp.submit_new_case("accept")
        assert confirm == cp.SUSPEND_CONFIRM
        case_no = re.search(r"CMP/\d{4}/\w+", toast).group()
        assert toast == f"Case {case_no}: {route_b_data.expected_message}", toast

    with allure.step("Verify the new row"):
        expect(cp.route_badge(case_no)).to_have_text("High risk")
        expect(cp.route_badge(case_no)).to_have_class(_badge_class("red"))
        expect(cp.status_badge(case_no)).to_have_text("suspended")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("red"))

    with allure.step("Verify the certificate is Suspended on Licences & certificates"):
        expect(_licence_badge(cp, compliance_agency)).to_have_text(re.compile(r"^Suspended"))


# ---------------------------------------------------------------------------
# TC-654  Route B reasons and suspension end date
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-654")
@allure.story(STORY)
@allure.title("TC-654: Route B case shows the reasons and a suspension end date within 6 months")
def test_tc654_route_b_details(logged_in_admin_compliance_page: AdminCompliancePage, route_b_case,
                               route_b_data: ComplianceCaseData):
    """
    Given a Route B case was just opened
    When  I open it
    Then  Status is "Interim suspension", the reasons are shown and "Suspension valid until" is no later than
          6 months after opening
    And   the only action offered is Schedule mandatory hearing
    And   History records the interim suspension and the 15-day show cause notice

    AIO: KAN-TC-654 | KAN-46 AC-5 | data: {route_b_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_b_case

    with allure.step("Open the case"):
        case = cp.open_case(case_no)
        opened = _stamp(case["created_at"])

    with allure.step("Verify Status, reasons and suspension end"):
        expect(cp.case_field("Status")).to_have_text("Status: Interim suspension")
        expect(cp.case_field("Reasons for suspension")).to_have_text(f"Reasons for suspension: {route_b_data.reasons}")
        until = _stamp(cp.case_field("Suspension valid until").text_content())
        assert opened < until <= _plus_months(opened, 6), f"opened {opened}, valid until {until}"

    with allure.step("Verify only a hearing is offered"):
        assert cp.allowed_actions() == ["hearing"]

    with allure.step("Verify the History entry"):
        history = cp.history_data()
        assert history[0]["title"] == "opened" and route_b_data.expected_message in history[0]["body"], history


# ---------------------------------------------------------------------------
# TC-655  Route B needs reasons
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-655")
@allure.story(STORY)
@allure.title("TC-655: Route B is refused without reasons in writing")
def test_tc655_route_b_needs_reasons(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                                     missing_reasons_data: dict):
    """
    Given the Open compliance case form is filled for Route B
    When  I click "Open case" with Reasons in writing empty, or only spaces, and confirm
    Then  "Reasons in writing are mandatory for interim suspension (Sec 6(2))." is shown
    And   no case is opened and the certificate is still Active

    AIO: KAN-TC-655 | KAN-46 AC-6 / EC-1 | data: route_b_without_reasons ('' and '   ')
    """
    cp = logged_in_admin_compliance_page
    before = len(cp.cases_for(compliance_agency))
    cp.open_new_case()

    for label, data in missing_reasons_data.items():
        with allure.step(f"Reasons {label}: click 'Open case' and confirm"):
            cp.fill_new_case(compliance_agency, data.trigger, data.details, True, data.reasons)
            _, toast = cp.submit_new_case("accept")
            assert toast == data.expected_error, toast

    with allure.step("Verify no case was opened"):
        cp.close_new_case()
        cp.open()
        assert len(cp.cases_for(compliance_agency)) == before

    with allure.step("Verify the certificate is still Active"):
        expect(_licence_badge(cp, compliance_agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-656  Case dialog
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-656")
@allure.story(STORY)
@allure.title("TC-656: Open shows the case details, allowed actions and History")
def test_tc656_case_dialog(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case):
    """
    Given a case Under inquiry
    When  I click Open on its row
    Then  the dialog "<Case No.> — <Agency>" shows Status, Trigger, the actions Schedule mandatory hearing and
          Drop proceedings / revoke suspension, a required "Remarks / speaking order", Submit and History
    When  I click Close
    Then  the dialog closes

    AIO: KAN-TC-656 | KAN-46 AC-7
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case

    with allure.step("Click Open"):
        cp.open_case(case_no)
        expect(cp.case_title).to_have_text(f"{case_no} — {agency}")

    with allure.step("Verify the details and the form"):
        expect(cp.case_field("Status")).to_be_visible()
        expect(cp.case_field("Trigger")).to_be_visible()
        expect(cp.action_labels).to_have_text([cp.ACTIONS["hearing"], cp.ACTIONS["drop"]])
        expect(cp.hearing_fields).to_be_hidden()
        expect(cp.window_field).to_be_hidden()
        expect(cp.remarks_label).to_have_text("Remarks / speaking order")
        expect(cp.remarks_input).to_have_attribute("required", "")
        expect(cp.submit_button).to_have_text("Submit")
        expect(cp.history_heading).to_be_visible()
        expect(cp.history_entries).to_have_count(1)

    with allure.step("Click Close"):
        cp.close_case()
        expect(cp.case_dialog).not_to_have_class(re.compile(r"\bis-open\b"))


# ---------------------------------------------------------------------------
# TC-657  Schedule mandatory hearing
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-657")
@allure.story(STORY)
@allure.title("TC-657: Schedule mandatory hearing records the date, time and mode")
def test_tc657_schedule_hearing(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                                hearing_data: CaseActionData):
    """
    Given a case Under inquiry
    When  I choose "Schedule mandatory hearing", pick a date 7 days ahead at 11:00, Virtual, and submit
    Then  "Mandatory hearing (Sec 6(4)) scheduled on <date>, 11:00 AM (virtual)." is shown and the status is
          hearing scheduled (blue)
    And   the dialog shows the hearing and History has a hearing entry with my remarks

    AIO: KAN-TC-657 | KAN-46 AC-8 | data: {hearing_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case
    cp.open_case(case_no)

    with allure.step("Choose 'Schedule mandatory hearing'"):
        cp.choose_action("hearing")
        expect(cp.hearing_fields).to_be_visible()
        expect(cp.hearing_mode_select.locator("option")).to_have_text(["Virtual", "Personal"])

    with allure.step(f"Set {hearing_data.hearing_at} ({hearing_data.hearing_mode}), remarks and Submit"):
        cp.set_hearing(hearing_data.hearing_at, hearing_data.hearing_mode)
        cp.fill_remarks(hearing_data.remarks)
        _, toast = cp.submit_action()
        assert toast == hearing_data.expected_message

    with allure.step("Verify the status"):
        expect(cp.status_badge(case_no)).to_have_text("hearing scheduled")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("blue"))

    with allure.step("Verify the hearing and History in the case dialog"):
        cp.open_case(case_no)
        expect(cp.case_field("Status")).to_have_text("Status: Hearing scheduled")
        when = hearing_data.hearing_at.replace("T", " ") + ":00"
        expect(cp.case_field("Hearing")).to_have_text(f"Hearing: {when} ({hearing_data.hearing_mode})")
        history = cp.history_data()
        assert history[0]["title"] == "hearing", history
        assert hearing_data.expected_message in history[0]["body"] and hearing_data.remarks in history[0]["body"], history


# ---------------------------------------------------------------------------
# TC-658  Hearing needs a date
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-658")
@allure.story(STORY)
@allure.title("TC-658: Hearing needs a date and time")
def test_tc658_hearing_needs_date(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                                  hearing_without_date_data: CaseActionData):
    """
    Given a case Under inquiry
    When  I schedule a hearing with no date and time
    Then  "Choose a future date and time for the hearing." is shown and the case stays under inquiry

    AIO: KAN-TC-658 | KAN-46 field-level validations | data: {hearing_without_date_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case
    data = hearing_without_date_data

    with allure.step("Submit a hearing without a date"):
        _, toast = cp.take_action(case_no, data.action, data.remarks, data.hearing_at, data.hearing_mode)
        assert toast == data.expected_error

    with allure.step("Verify the case is still under inquiry"):
        cp.close_case()
        expect(cp.status_badge(case_no)).to_have_text("under inquiry")


# ---------------------------------------------------------------------------
# TC-659  Grant 3–7 day window
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-659")
@allure.story(STORY)
@allure.title("TC-659: Grant 3–7 day window offers 3, 5 or 7 days and moves the case to Post-hearing window")
def test_tc659_grant_window(logged_in_admin_compliance_page: AdminCompliancePage, heard_case,
                            window_data: CaseActionData):
    """
    Given a case with a hearing scheduled
    When  I choose "Grant 3–7 day window"
    Then  a days list with 3, 5 and 7 appears, 7 selected
    When  I choose 3, enter remarks and submit
    Then  "Post-hearing window of 3 days granted to submit proof of compliance." is shown, the status is
          post hearing window (blue) and History has the window entry

    AIO: KAN-TC-659 | KAN-46 AC-9 | data: {window_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = heard_case
    cp.open_case(case_no)

    with allure.step("Choose 'Grant 3–7 day window'"):
        cp.choose_action("window")
        expect(cp.window_field).to_be_visible()
        expect(cp.window_days_select.locator("option")).to_have_text(["3", "5", "7"])
        expect(cp.window_days_select).to_have_value("7")

    with allure.step("Choose 3 days, remarks and Submit"):
        cp.set_window_days(window_data.window_days)
        cp.fill_remarks(window_data.remarks)
        _, toast = cp.submit_action()
        assert toast == window_data.expected_message

    with allure.step("Verify the status and History"):
        expect(cp.status_badge(case_no)).to_have_text("post hearing window")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("blue"))
        cp.open_case(case_no)
        expect(cp.case_field("Status")).to_have_text("Status: Post-hearing window")
        history = cp.history_data()
        assert history[0]["title"] == "window" and window_data.expected_message in history[0]["body"], history


# ---------------------------------------------------------------------------
# TC-660  Drop proceedings (Route A)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-660")
@allure.story(STORY)
@allure.title("TC-660: Drop proceedings closes a Route A case and offers no more actions")
def test_tc660_drop_route_a(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                            drop_data: CaseActionData):
    """
    Given a case Under inquiry
    When  I choose "Drop proceedings / revoke suspension", enter remarks and submit
    Then  "Proceedings dropped — agency remains fully ACTIVE." is shown and the status is closed dropped (green)
    And   the dialog shows "Closed — proceedings dropped", the drop in History and no actions
    And   the certificate is Active

    AIO: KAN-TC-660 | KAN-46 AC-10 | data: {drop_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case

    with allure.step("Drop the proceedings"):
        _, toast = cp.take_action(case_no, drop_data.action, drop_data.remarks)
        assert toast == drop_data.expected_message

    with allure.step("Verify the status"):
        expect(cp.status_badge(case_no)).to_have_text("closed dropped")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("green"))

    with allure.step("Verify the case dialog"):
        cp.open_case(case_no)
        expect(cp.case_field("Status")).to_have_text("Status: Closed — proceedings dropped")
        expect(cp.action_form).to_have_count(0)
        history = cp.history_data()
        assert history[0]["title"] == "drop", history
        assert drop_data.expected_message in history[0]["body"] and drop_data.remarks in history[0]["body"], history

    with allure.step("Verify the certificate is Active"):
        expect(_licence_badge(cp, agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-661  Dropping a Route B case revokes the suspension
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-661")
@allure.story(STORY)
@allure.title("TC-661: Dropping a Route B case revokes the suspension")
def test_tc661_drop_route_b(logged_in_admin_compliance_page: AdminCompliancePage, heard_route_b_case,
                            revoke_data: CaseActionData):
    """
    Given a Route B case (agency suspended) with a hearing scheduled
    When  I drop the proceedings
    Then  "Suspension revoked — agency status restored to ACTIVE." is shown and the status is closed revoked
          (green)
    And   the certificate is Active again

    AIO: KAN-TC-661 | KAN-46 AC-10 | data: {revoke_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = heard_route_b_case

    with allure.step("Verify the certificate is Suspended"):
        expect(_licence_badge(cp, agency)).to_have_text(re.compile(r"^Suspended"))
        cp.open()

    with allure.step("Drop the proceedings"):
        _, toast = cp.take_action(case_no, revoke_data.action, revoke_data.remarks)
        assert toast == revoke_data.expected_message

    with allure.step("Verify the status"):
        expect(cp.status_badge(case_no)).to_have_text("closed revoked")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("green"))
        cp.open_case(case_no)
        expect(cp.case_field("Status")).to_have_text("Status: Closed — suspension revoked")

    with allure.step("Verify the certificate is Active again"):
        expect(_licence_badge(cp, agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-662  Cancelling the cancellation-order confirmation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-662")
@allure.story(STORY)
@allure.title("TC-662: Cancelling the cancellation-order confirmation changes nothing")
def test_tc662_cancel_order_dismissed(logged_in_admin_compliance_page: AdminCompliancePage, heard_case,
                                      cancellation_order_data: CaseActionData):
    """
    Given a case with a hearing scheduled
    When  I choose "Issue cancellation order", enter the speaking order and submit
    Then  "Cancel this agency's registration?" is asked
    When  I cancel
    Then  the case keeps its status and the certificate is Active

    AIO: KAN-TC-662 | KAN-46 AC-11 | data: {cancellation_order_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = heard_case
    data = cancellation_order_data

    with allure.step("Issue the cancellation order and Cancel the confirmation"):
        confirm, toast = cp.take_action(case_no, data.action, data.remarks, answer="dismiss")
        assert confirm == cp.CANCEL_CONFIRM
        assert toast == ""
        expect(cp.case_dialog).to_have_class(re.compile(r"\bis-open\b"))

    with allure.step("Verify nothing changed"):
        cp.close_case()
        cp.open()
        expect(cp.status_badge(case_no)).to_have_text("hearing scheduled")
        expect(_licence_badge(cp, agency)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-663  Issue cancellation order
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-663")
@allure.story(STORY)
@allure.title("TC-663: Issue cancellation order cancels the agency's registration")
def test_tc663_cancel_order(logged_in_admin_compliance_page: AdminCompliancePage, heard_case,
                            cancellation_order_data: CaseActionData):
    """
    Given a case with a hearing scheduled
    When  I issue the cancellation order and confirm
    Then  "Speaking cancellation order issued. Registration CANCELLED; the agency may file a First Appeal within
          60 days." is shown and the status is cancelled (red)
    And   the dialog shows "Registration cancelled", the order in History and no actions
    And   the certificate is revoked on Licences & certificates (reinstated on teardown)

    AIO: KAN-TC-663 | KAN-46 AC-11 | data: {cancellation_order_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = heard_case
    data = cancellation_order_data

    with allure.step("Issue the cancellation order and confirm"):
        confirm, toast = cp.take_action(case_no, data.action, data.remarks, answer="accept")
        assert confirm == cp.CANCEL_CONFIRM
        assert toast == data.expected_message

    with allure.step("Verify the status and the case dialog"):
        expect(cp.status_badge(case_no)).to_have_text("cancelled")
        expect(cp.status_badge(case_no)).to_have_class(_badge_class("red"))
        cp.open_case(case_no)
        expect(cp.case_field("Status")).to_have_text("Status: Registration cancelled")
        expect(cp.action_form).to_have_count(0)
        history = cp.history_data()
        assert history[0]["title"] == "cancel" and data.remarks in history[0]["body"], history

    with allure.step("Verify the certificate is revoked on Licences & certificates"):
        expect(_licence_badge(cp, agency)).to_have_class(re.compile(r"\blb-revoked\b"))


# ---------------------------------------------------------------------------
# TC-664  Remarks required
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-664")
@allure.story(STORY)
@allure.title("TC-664: An action is refused without remarks")
def test_tc664_remarks_required(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                                hearing_data: CaseActionData, blank_remarks_data: CaseActionData):
    """
    Given a case Under inquiry is open in the dialog
    When  I submit a hearing, or a drop, with Remarks / speaking order empty
    Then  the browser flags the remarks and nothing is sent
    When  the remarks are only spaces
    Then  "Remarks / reasons are required." is shown
    And   the case stays under inquiry

    AIO: KAN-TC-664 | KAN-46 AC-12 | data: {blank_remarks_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case
    cp.open_case(case_no)

    with allure.step("Hearing filled in, remarks empty: Submit"):
        cp.choose_action("hearing")
        cp.set_hearing(hearing_data.hearing_at, hearing_data.hearing_mode)
        _, toast = cp.submit_action()
        assert toast == ""
        assert cp.validation_message(cp.remarks_input), "Remarks is not flagged"

    with allure.step("Drop, remarks empty: Submit"):
        cp.choose_action("drop")
        _, toast = cp.submit_action()
        assert toast == ""

    with allure.step("Drop, remarks only spaces: Submit"):
        cp.fill_remarks(blank_remarks_data.remarks)
        _, toast = cp.submit_action()
        assert toast == blank_remarks_data.expected_error

    with allure.step("Verify the case is still under inquiry"):
        cp.close_case()
        expect(cp.status_badge(case_no)).to_have_text("under inquiry")


# ---------------------------------------------------------------------------
# TC-665  Audit log
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-665")
@allure.story(STORY)
@allure.title("TC-665: Opening a case and every action are recorded in the Audit log")
def test_tc665_audit_log(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                         route_a_data: ComplianceCaseData, hearing_data: CaseActionData, drop_data: CaseActionData):
    """
    Given an agency with no open case
    When  I open a Route A case, schedule its hearing and drop it
    Then  the Audit log (Today) has an entry for each of the three, besides the Admin Login entries

    AIO: KAN-TC-665 | KAN-46 AC-13 | data: {route_a_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    start = ComplianceFactory.now_ist().replace(microsecond=0) - timedelta(seconds=5)

    with allure.step("Open a case, schedule the hearing and drop it"):
        case_no, _ = cp.open_case_for(compliance_agency, route_a_data.trigger, route_a_data.details)
        cp.take_action(case_no, "hearing", hearing_data.remarks, hearing_data.hearing_at, hearing_data.hearing_mode)
        expect(cp.status_badge(case_no)).to_have_text("hearing scheduled")
        cp.take_action(case_no, "drop", drop_data.remarks)
        expect(cp.status_badge(case_no)).to_have_text("closed dropped")

    with allure.step("Read today's Audit log entries since the case was opened"):
        al = AdminAuditLogPage(cp.page)
        al.open(date_f="today")
        events = [e for e in al.entries_data()
                  if datetime.strptime(e["timestamp"], "%d %b %Y, %H:%M:%S") >= start and e["action"] != "Admin Login"]
        allure.attach(str(events), name="entries since the case was opened")

    with allure.step("Verify the opening, the hearing and the drop are recorded"):
        assert len(events) >= 3, f"{len(events)} audit entries for {case_no} (open, hearing, drop): {events}"


# ---------------------------------------------------------------------------
# TC-666  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-666")
@allure.story(STORY)
@allure.title("TC-666: Compliance cases needs an admin session")
def test_tc666_needs_a_session(no_admin_session, admin_compliance_page: AdminCompliancePage,
                               admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the Compliance cases URL
    Then  I am sent to the Admin Login page with "Please log in to continue."

    AIO: KAN-TC-666 | KAN-46 AC-14
    """
    with allure.step("Open the page without a session"):
        admin_compliance_page.open(wait_for_table=False)

    with allure.step("Verify the Admin Login page opens with 'Please log in to continue.'"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        assert "reason=not_logged_in" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-667  Stale page
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-667")
@allure.story(STORY)
@allure.title("TC-667: An action not allowed for the case's status is refused (stale page)")
def test_tc667_stale_page(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                          hearing_data: CaseActionData, drop_data: CaseActionData):
    """
    Given a case Under inquiry is open in two tabs
    When  tab 1 drops the proceedings and tab 2 then submits a hearing
    Then  tab 2 shows "Action not allowed at this step." and the case stays closed dropped with no hearing

    AIO: KAN-TC-667 | KAN-46 field-level validations
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case

    with allure.step("Tab 2: open the case and fill in a hearing"):
        tab2 = AdminCompliancePage(cp.page.context.new_page())
        tab2.open()
        tab2.open_case(case_no)
        tab2.choose_action("hearing")
        tab2.set_hearing(hearing_data.hearing_at, hearing_data.hearing_mode)
        tab2.fill_remarks(hearing_data.remarks)

    try:
        with allure.step("Tab 1: drop the proceedings"):
            _, toast = cp.take_action(case_no, drop_data.action, drop_data.remarks)
            assert toast == drop_data.expected_message

        with allure.step("Tab 2: Submit the hearing"):
            _, toast = tab2.submit_action()
            assert toast == ComplianceFactory.NOT_ALLOWED
    finally:
        tab2.page.close()

    with allure.step("Verify the case is closed dropped with no hearing"):
        expect(cp.status_badge(case_no)).to_have_text("closed dropped")
        cp.open_case(case_no)
        assert [h["title"] for h in cp.history_data()] == ["drop", "opened"]


# ---------------------------------------------------------------------------
# TC-668  Times in IST
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-668")
@allure.story(STORY)
@allure.title("TC-668: Opened, suspension, hearing and History times are in IST")
def test_tc668_times_in_ist(logged_in_admin_compliance_page: AdminCompliancePage, route_b_case):
    """
    Given a Route B case was just opened
    Then  its Opened time and History time are the current IST time
    And   "Suspension valid until" is 6 months after opening at the same time of day
    When  I schedule a hearing tomorrow at 11:00 (Personal)
    Then  the dialog shows the hearing at 11:00 and the History time is the current IST time

    AIO: KAN-TC-668 | KAN-46 EC-8
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_b_case
    hearing = ComplianceFactory.hearing("personal", days_ahead=1, hour=11)

    with allure.step("Verify Opened and the History time"):
        now = ComplianceFactory.now_ist()
        opened = _stamp(cp.opened_cell(case_no).text_content())
        assert abs(opened - now) < timedelta(minutes=3), f"Opened {opened}, now (IST) {now}"
        cp.open_case(case_no)
        assert _stamp(cp.history_data()[0]["meta"]) == opened

    with allure.step("Verify 'Suspension valid until' is 6 months after opening, same time of day"):
        until = _stamp(cp.case_field("Suspension valid until").text_content())
        assert until == _plus_months(opened, 6), f"opened {opened}, valid until {until}"

    with allure.step("Schedule a hearing tomorrow at 11:00 and check it"):
        cp.choose_action("hearing")
        cp.set_hearing(hearing.hearing_at, hearing.hearing_mode)
        cp.fill_remarks(hearing.remarks)
        _, toast = cp.submit_action()
        assert toast == hearing.expected_message
        cp.open_case(case_no)
        expect(cp.case_field("Hearing")).to_have_text(f"Hearing: {hearing.hearing_at.replace('T', ' ')}:00 (personal)")
        assert abs(_stamp(cp.history_data()[0]["meta"]) - ComplianceFactory.now_ist()) < timedelta(minutes=3)


# ---------------------------------------------------------------------------
# TC-669  Long text and special characters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-669")
@allure.story(STORY)
@allure.title("TC-669: Long text and special characters in details, reasons and remarks are shown safely")
def test_tc669_long_text(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str,
                         long_text_data: ComplianceCaseData):
    """
    Given an agency with no open case
    When  I open a case whose details are about 1,000 characters ending with HTML, a script tag, quotes and
          Marathi text, and drop it with the same text as remarks
    Then  the dialog and History show the text exactly as typed, with no tag rendered

    AIO: KAN-TC-669 | KAN-46 EC-10 | data: {long_text_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    text = long_text_data.details

    with allure.step("Open a case with the long details"):
        case_no, toast = cp.open_case_for(compliance_agency, long_text_data.trigger, text)
        assert case_no, toast

    with allure.step("Verify the dialog shows the text as typed"):
        cp.open_case(case_no)
        expect(cp.case_field("Trigger")).to_have_text(f"Trigger: complaint — {text}")
        assert text in cp.history_data()[0]["body"]
        expect(cp.page.locator("#cBody script, #cBody b")).to_have_count(0)

    with allure.step("Drop the case with the same text as remarks"):
        cp.choose_action("drop")
        cp.fill_remarks(text)
        _, toast = cp.submit_action()
        assert toast == ComplianceFactory.DROPPED
        cp.open_case(case_no)
        assert text in cp.history_data()[0]["body"]
        expect(cp.page.locator("#cBody script, #cBody b")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-670  District officer scope
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-670")
@allure.story(STORY)
@allure.title("TC-670: A district officer sees only cases in their district")
def test_tc670_district_officer_scope(page, district_officer_login):
    """
    Given I am logged in as a District Officer
    When  I open Compliance cases
    Then  every case listed is for an agency in my district

    AIO: KAN-TC-670 | KAN-46 EC-9 | needs ADMIN_DISTRICT_* in .env
    """
    district = os.getenv("ADMIN_DISTRICT_NAME")
    district_officer_login()
    cp = AdminCompliancePage(page)
    cp.open()

    with allure.step(f"Verify every case is in {district}"):
        rows = cp.rows_data()
        allure.attach(str(rows), name="rows")
        assert all(r["district"] == district for r in rows), rows


# ---------------------------------------------------------------------------
# TC-671  Second case for the same agency
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-671")
@allure.story(STORY)
@allure.title("TC-671: A second case for an agency with an open case is refused")
def test_tc671_second_case_refused(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                                   route_a_data: ComplianceCaseData):
    """
    Given the agency already has an open case
    When  I open another case for it
    Then  "Case <open case> is already open for this agency." is shown and no case is added

    AIO: KAN-TC-671 | KAN-46 EC-2 | data: {route_a_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case
    before = len(cp.cases_for(agency))

    with allure.step("Open another Route A case for the agency"):
        new_case, toast = cp.open_case_for(agency, route_a_data.trigger, route_a_data.details)
        assert new_case == ""
        assert toast == ComplianceFactory.second_case_error(case_no)

    with allure.step("Verify no case was added"):
        cp.close_new_case()
        cp.open()
        assert len(cp.cases_for(agency)) == before


# ---------------------------------------------------------------------------
# TC-674  Hearing in the past
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-674")
@allure.story(STORY)
@allure.title("TC-674: A hearing date in the past is refused")
def test_tc674_hearing_in_past(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case,
                               hearing_in_past_data: CaseActionData):
    """
    Given a case Under inquiry
    When  I schedule its hearing for yesterday
    Then  "Choose a future date and time for the hearing." is shown and the case stays under inquiry

    AIO: KAN-TC-674 | KAN-46 EC-5 | data: {hearing_in_past_data.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_a_case
    data = hearing_in_past_data

    with allure.step(f"Schedule the hearing for {data.hearing_at}"):
        _, toast = cp.take_action(case_no, data.action, data.remarks, data.hearing_at, data.hearing_mode)
        assert toast == data.expected_error

    with allure.step("Verify the case is still under inquiry"):
        cp.close_case()
        expect(cp.status_badge(case_no)).to_have_text("under inquiry")


# ---------------------------------------------------------------------------
# TC-675  Certificate changed on Licences while a case is open
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-675")
@allure.story(STORY)
@allure.title("TC-675: Lifting the suspension on Licences & certificates keeps the case in step")
def test_tc675_lift_on_licences_while_case_open(logged_in_admin_compliance_page: AdminCompliancePage,
                                                route_b_case):
    """
    Given a Route B case has suspended the agency
    When  I click Lift suspension on the agency's row on Licences & certificates
    Then  either the lift is refused (the certificate stays Suspended) or the case no longer shows
          "Interim suspension" — the case and the certificate agree

    AIO: KAN-TC-675 | KAN-46 EC-6
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = route_b_case

    with allure.step("Lift the suspension on Licences & certificates"):
        lp = AdminLicensesPage(cp.page)
        lp.open(status="all")
        _, toast = lp.certificate_action(agency, "lift", "Automation — lifting while a compliance case is open.")
        allure.attach(toast, name="Licences toast")
        lp.open(status="all")
        certificate = lp.status_badge(agency).text_content().strip()

    with allure.step("Open the case on Compliance cases"):
        cp.open()
        cp.open_case(case_no)
        status = cp.case_field("Status").text_content().strip()

    with allure.step("Verify the case and the certificate agree"):
        assert certificate.startswith("Suspended") or status != "Status: Interim suspension", \
            f"Certificate '{certificate}' but case '{status}'"


# ---------------------------------------------------------------------------
# TC-677  Window and cancellation only after the hearing
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-677")
@allure.story(STORY)
@allure.title("TC-677: Window and cancellation order are not offered before the hearing has taken place")
def test_tc677_no_order_before_hearing(logged_in_admin_compliance_page: AdminCompliancePage, heard_case):
    """
    Given a case whose mandatory hearing is scheduled 7 days ahead
    When  I open it
    Then  "Grant 3–7 day window" and "Issue cancellation order" are not offered (they follow the hearing)

    AIO: KAN-TC-677 | KAN-46 AC-9 / AC-11
    """
    cp = logged_in_admin_compliance_page
    agency, case_no = heard_case

    with allure.step("Open the case"):
        case = cp.open_case(case_no)
        allure.attach(str(case), name="case record")

    with allure.step("Verify no window or cancellation order before the hearing date"):
        assert _stamp(case["hearing_at"]) > ComplianceFactory.now_ist()
        actions = cp.allowed_actions()
        assert "window" not in actions and "cancel" not in actions, f"Offered before the hearing: {actions}"
