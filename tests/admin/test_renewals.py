"""KAN-51 — Renewal Applications (officer side of the licence renewal): Licences & certificates → Renewal
applications (admin/licenses/renewals.php). The agency side is KAN-37 (tests/test_renewal.py).

KAN-TC-833…845 only read, except that the role cases (841–843) create NEW test officers through Officers &
Access and delete them afterwards. KAN-TC-838 needs a pending renewal and skips without one.

The pending renewal is found by reading the agencies' renewal pages; with RUN_RENEWAL_TESTS=true one is
submitted (after expiring a certificate if need be) when none is pending. KAN-TC-829 rejects it and KAN-TC-414
approves one (a rejected agency can file again); both only run
with RUN_RENEWAL_TESTS=true (irreversible on dev).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.agency_view_page import AdminAgencyViewPage
from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.components.sidebar import AdminSidebar
from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.notifications_page import AdminNotificationsPage
from pages.admin.renewals_page import ADMIN_RENEWALS_URL, AdminRenewalsPage
from pages.agency_home_page import AgencyHomePage
from pages.license_renewal_page import LicenseRenewalPage
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Renewal Applications"
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

    Notion: KAN-TC-412 | KAN-51 AC-3
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

    Notion: KAN-TC-413 | KAN-51 AC-8 | Data: "Too short" (reject), "ok" (approve)
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


@aio_case("KAN-TC-833")
@allure.story(STORY)
@allure.title("TC-833: Renewal applications opens from the sidebar and from Licences & certificates")
def test_tc833_reach_page(officer_renewals_page, renewal_admin_licenses_page: AdminLicensesPage):
    """
    Given I am logged in as the Super Administrator
    When  I open Renewal applications from the sidebar (Registry) and from Licences & certificates
    Then  the page opens with its title, heading, note, the Licences & certificates button, the four tabs with
          counts (Pending decision selected) and the nine columns

    Notion: KAN-TC-833 | KAN-51 AC-1
    """
    renewals = officer_renewals_page
    page = renewals.page
    licenses = renewal_admin_licenses_page
    sidebar = AdminSidebar(page)

    with allure.step("From Licences & certificates, click Registry → Renewal applications in the sidebar"):
        licenses.open()
        expect(sidebar.section_header(AdminRenewalsPage.SIDEBAR_SECTION)).to_be_visible()
        sidebar.go_to_renewals()
        expect(page).to_have_url(ADMIN_RENEWALS_URL)
        expect(page).to_have_title(AdminRenewalsPage.TITLE)

    with allure.step("Verify the header, tabs and columns"):
        expect(renewals.heading).to_have_text(AdminRenewalsPage.HEADING)
        expect(renewals.note).to_have_text(AdminRenewalsPage.NOTE)
        expect(renewals.licenses_link).to_be_visible()
        expect(renewals.tabs).to_have_text([re.compile(rf"^{label}\s*\d+$") for label in AdminRenewalsPage.TABS.values()])
        expect(renewals.selected_tab).to_have_count(1)
        expect(renewals.selected_tab).to_contain_text(AdminRenewalsPage.TABS["submitted"])
        expect(renewals.table_headers).to_have_text(list(AdminRenewalsPage.COLUMNS))

    with allure.step("Click Licences & certificates — Licences & certificates opens"):
        renewals.open_licenses()
        expect(page).to_have_url(re.compile(r"/admin/licenses/licenses\.php$"))

    with allure.step("Click its Renewal applications button — Renewal applications opens again"):
        licenses.open_renewal_applications()
        expect(page).to_have_url(re.compile(r"/admin/licenses/renewals\.php$"))
        expect(renewals.heading).to_have_text(AdminRenewalsPage.HEADING)


@aio_case("KAN-TC-834")
@allure.story(STORY)
@allure.title("TC-834: Each tab lists only its status and its count matches the rows")
def test_tc834_tabs_and_counts(decided_renewals):
    """
    Given renewals have been approved and rejected
    When  I open each tab
    Then  it is selected, lists only applications in its status, its count equals the rows, and All = Pending
          decision + Renewed + Rejected

    Notion: KAN-TC-834 | KAN-51 AC-2
    """
    renewals, all_rows = decided_renewals
    counts = renewals.tab_counts()

    with allure.step(f"Verify All = Pending decision + Renewed + Rejected ({counts})"):
        assert counts["all"] == counts["submitted"] + counts["approved"] + counts["rejected"], counts

    for tab, label in AdminRenewalsPage.TABS.items():
        with allure.step(f"Open '{label}' — selected, {counts[tab]} rows, only its status"):
            renewals.open_tab(tab)
            expect(renewals.selected_tab).to_have_count(1)
            expect(renewals.selected_tab).to_contain_text(label)
            expect(renewals.rows).to_have_count(counts[tab])
            rows = renewals.row_data()
            if tab == "all":
                assert [r["number"] for r in rows] == [r["number"] for r in all_rows]
            else:
                assert {r["status"] for r in rows} <= {AdminRenewalsPage.STATUS_OF_TAB[tab]}, rows
                assert len(rows) == sum(r["status"] == AdminRenewalsPage.STATUS_OF_TAB[tab] for r in all_rows)
            if not counts[tab]:
                expect(renewals.empty_row).to_have_text(AdminRenewalsPage.EMPTY_LIST)


@aio_case("KAN-TC-835")
@allure.story(STORY)
@allure.title("TC-835: Renewed and rejected applications show the decision, who took it and only Application")
def test_tc835_decided_rows(decided_renewals):
    """
    Given renewals have been approved and rejected
    When  I look at a row on the Renewed and on the Rejected tab
    Then  a renewed row shows "Renewed to <date>" and a green Renewed badge, a rejected row a red Rejected badge;
          both show "<date> · <officer>", their details and only the Application action

    Notion: KAN-TC-835 | KAN-51 AC-4
    """
    renewals, _ = decided_renewals
    checks = {"approved": (AdminRenewalsPage.RENEWED, "ui-badge-green", rf"^Up to {DATE} Renewed to {DATE}$"),
              "rejected": (AdminRenewalsPage.REJECTED, "ui-badge-red", rf"^Up to {DATE}$")}
    for tab, (status, colour, validity) in checks.items():
        with allure.step(f"Open '{AdminRenewalsPage.TABS[tab]}' and check its newest row"):
            renewals.open_tab(tab)
            row = renewals.row_data()[0]
            allure.attach(str(row), "Row", allure.attachment_type.TEXT)
            assert row["status"] == status, row
            assert colour in row["badge_class"].split(), row["badge_class"]
            assert re.fullmatch(validity, row["validity"]), row["validity"]
            assert re.fullmatch(rf"{DATE} · \S.*", row["decided"]), row["decided"]
            assert row["actions"] == [AdminRenewalsPage.APPLICATION_LABEL], row["actions"]
            assert re.fullmatch(r"\d{13,14}", row["reg"]) and row["agency"], row
            assert re.fullmatch(DATE, row["applied"]), row["applied"]
            assert re.fullmatch(r"Changes since registration: (No|Yes) Cases / suspension: (No|Yes)",
                                row["declarations"]), row["declarations"]
            assert row["fee"] == "₹2,000" and re.fullmatch(r"\S+", row["reference"]), (row["fee"], row["reference"])


@aio_case("KAN-TC-836")
@allure.story(STORY)
@allure.title("TC-836: Renewal applications are numbered and listed newest first, one row per application")
def test_tc836_order_and_numbering(decided_renewals):
    """
    Given renewal applications exist, and one agency applied more than once
    When  I open the All tab
    Then  the # numbers are unique and descending, and that agency has one row per application, each with its
          own number and payment reference

    Notion: KAN-TC-836 | KAN-51 AC-5
    """
    _, rows = decided_renewals
    numbers = [int(r["number"]) for r in rows]

    with allure.step(f"Verify the # column is unique and descending: {numbers}"):
        assert numbers == sorted(set(numbers), reverse=True), numbers

    with allure.step("Verify an agency that applied more than once has one row per application"):
        by_agency: dict[str, list] = {}
        for r in rows:
            by_agency.setdefault(r["reg"], []).append(r)
        repeat = next((rs for rs in by_agency.values() if len(rs) > 1), None)
        if repeat is None:
            pytest.skip("No agency has applied for renewal more than once.")
        allure.attach("\n".join(f"#{r['number']} {r['status']} {r['reference']}" for r in repeat),
                      repeat[0]["agency"], allure.attachment_type.TEXT)
        assert len({r["number"] for r in repeat}) == len(repeat)
        assert len({r["reference"] for r in repeat}) == len(repeat)


@aio_case("KAN-TC-837")
@allure.story(STORY)
@allure.title("TC-837: Application opens the agency's View Agency page")
def test_tc837_application_action(decided_renewals):
    """
    Given a renewal application is listed
    When  I click Application on it
    Then  the agency's View Agency page opens in the same tab with the same agency name and registration no.

    Notion: KAN-TC-837 | KAN-51 AC-6
    """
    renewals, rows = decided_renewals
    row = rows[0]
    page = renewals.page

    with allure.step(f"Click Application on renewal #{row['number']} of {row['agency']}"):
        renewals.open_application(row["reg"], row["number"])

    with allure.step("Verify the View Agency page of that agency"):
        agency_id = AdminRenewalsPage.agency_id(row["application"])
        expect(page).to_have_url(re.compile(rf"/admin/dashboard/agency_view\.php\?id={agency_id}$"))
        expect(page).to_have_title(re.compile(rf"^View Agency — {re.escape(row['agency'])}\b"))
        view = AdminAgencyViewPage(page)
        expect(view.content).to_contain_text(row["agency"])
        expect(view.content).to_contain_text(row["reg"])


@aio_case("KAN-TC-838")
@allure.story(STORY)
@allure.title("TC-838: The decision dialog closes without sending anything")
def test_tc838_dialog_close(officer_pending_renewal, renewal_dialog_remarks_data):
    """
    Given a renewal is pending
    When  I open Approve and Reject, type remarks and close with Close / ×
    Then  each dialog opens with empty remarks (at most 2000 characters), closing sends nothing, and the renewal
          stays pending with Approve and Reject

    Notion: KAN-TC-838 | KAN-51 AC-7 | Data: remarks typed, then the dialog closed
    """
    renewals, user = officer_pending_renewal
    reg, remarks = user.application_id, renewal_dialog_remarks_data.remarks

    for decision, close in (("approve", renewals.close_dialog), ("reject", renewals.close_dialog_with_x)):
        with allure.step(f"Click {decision.title()} — the dialog opens with an empty Remarks box"):
            renewals.open_decision(reg, decision)
            expect(renewals.dialog_title).to_have_text(
                AdminRenewalsPage.DIALOG_TITLE[decision].format(name=user.agency_name))
            expect(renewals.remarks_input).to_have_value("")
            expect(renewals.remarks_input).to_have_attribute("maxlength", AdminRenewalsPage.REMARKS_MAX)

        with allure.step(f"Type remarks and close the {decision} dialog — it closes"):
            renewals.fill_remarks(remarks)
            close()
            expect(renewals.dialog.locator(".smod-box")).to_be_hidden()

    with allure.step("Click Approve again — the Remarks box is empty"):
        renewals.open_decision(reg, "approve")
        expect(renewals.remarks_input).to_have_value("")
        renewals.close_dialog()

    with allure.step("Reload — the renewal is still pending with Approve and Reject"):
        renewals.open(tab="submitted")
        expect(renewals.status_badge(reg)).to_have_text(AdminRenewalsPage.PENDING)
        assert renewals.action_labels(reg)[:2] == [AdminRenewalsPage.APPROVE_LABEL, AdminRenewalsPage.REJECT_LABEL]


@aio_case("KAN-TC-839")
@allure.story(STORY)
@allure.title("TC-839: Officers are notified when an agency files a renewal")
def test_tc839_officer_notification(decided_renewals):
    """
    Given renewal applications have been filed
    When  I open Notifications
    Then  each renewal number has a "Renewal application #N received" notification with the body, the type, the
          agency and registration no., a blue dot, linking to the agency's View Agency page

    Notion: KAN-TC-839 | KAN-51 AC-11
    """
    renewals, rows = decided_renewals
    notifications = AdminNotificationsPage(renewals.page)

    with allure.step("Open Notifications"):
        notifications.open()

    for row in rows:
        title = AdminRenewalsPage.NOTIFICATION_TITLE.format(number=row["number"])
        with allure.step(f"Verify '{title}' ({row['agency']})"):
            item = notifications.item_with_title(title)
            expect(item).to_have_count(1)
            expect(notifications.item_title(item)).to_have_text(title)
            expect(notifications.item_body(item)).to_have_text(AdminRenewalsPage.NOTIFICATION_BODY)
            parts = notifications.meta_parts(item)
            assert parts[:2] == [AdminRenewalsPage.NOTIFICATION_TYPE, f"{row['agency']} ({row['reg']})"], parts
            assert notifications.dot_colour(item) == AdminRenewalsPage.NOTIFICATION_DOT
            agency_id = AdminRenewalsPage.agency_id(row["application"])
            expect(item).to_have_attribute("href", re.compile(rf"dashboard/agency_view\.php\?id={agency_id}$"))


@aio_case("KAN-TC-840")
@allure.story(STORY)
@allure.title("TC-840: Renewal decisions are recorded in the Audit log")
def test_tc840_audit_log(decided_renewals):
    """
    Given renewals have been approved and rejected
    When  I filter the Audit log by CERTIFICATE_RENEWED and by CERTIFICATE_RENEWAL_REJECTED
    Then  there is one entry per decision on agency_approvals with the agency's record ID and details starting
          "Renewal #N approved — certificate valid" / "Renewal application #N rejected:"

    Notion: KAN-TC-840 | KAN-51 AC-12
    """
    renewals, rows = decided_renewals
    audit = AdminAuditLogPage(renewals.page)
    actions = {AdminRenewalsPage.AUDIT_RENEWED: AdminRenewalsPage.RENEWED,
               AdminRenewalsPage.AUDIT_REJECTED: AdminRenewalsPage.REJECTED}
    for action, status in actions.items():
        decided = [r for r in rows if r["status"] == status]
        with allure.step(f"Filter by {action} — {len(decided)} entries expected"):
            audit.open(action_f=action)
            expect(audit.showing_events_text).to_contain_text(f"of {len(decided)} events")
            entries = [audit.log_entry(i) for i in range(audit.log_entries.count())]
            details = []
            for entry in entries:
                expect(audit.entry_action_pill(entry)).to_have_text(action)
                expect(audit.entry_table_name(entry)).to_have_text(AdminRenewalsPage.AUDIT_TABLE)
                details.append((audit.entry_record_id(entry).text_content().strip(),
                                audit.entry_detail_value(entry, "details").text_content().strip()))
            allure.attach("\n".join(f"{rid} {d}" for rid, d in details), action, allure.attachment_type.TEXT)

        for r in decided:
            prefix = AdminRenewalsPage.AUDIT_DETAILS[action].format(number=r["number"])
            record = f"ID #{AdminRenewalsPage.agency_id(r['application'])}"
            with allure.step(f"Verify renewal #{r['number']}: {record}, details start '{prefix}'"):
                # the preview is cut with "…" — compare as far as both go
                assert any(rid == record and (d.rstrip("…").startswith(prefix) or prefix.startswith(d.rstrip("…")))
                           for rid, d in details), details


def _scope_check(renewals: AdminRenewalsPage, expected: list[dict]):
    """Every tab of ``renewals`` lists exactly ``expected`` (rows of the Super Admin) and counts them."""
    for tab, label in AdminRenewalsPage.TABS.items():
        want = [r["number"] for r in expected if tab == "all" or r["status"] == AdminRenewalsPage.STATUS_OF_TAB[tab]]
        with allure.step(f"'{label}' lists {want or 'nothing'} and counts {len(want)}"):
            renewals.open(tab=tab)
            assert renewals.get_tab_count(tab) == len(want)
            assert [r["number"] for r in renewals.row_data()] == want
            if not want:
                expect(renewals.empty_row).to_have_text(AdminRenewalsPage.EMPTY_LIST)


@aio_case("KAN-TC-841")
@allure.story(STORY)
@allure.title("TC-841: A District officer sees only the renewals of their district")
def test_tc841_district_officer_scope(renewal_scope_rows, renewal_scope_areas, renewal_role_officer):
    """
    Given renewal applications exist in one district and none in another
    When  a District officer of each district opens Renewal applications
    Then  the first sees exactly their district's applications on every tab, with matching counts; the second
          sees 0 everywhere and "No renewal applications in this list."

    Notion: KAN-TC-841 | KAN-51 AC-13 | Data: NEW test District officers (deleted afterwards)
    """
    areas = renewal_scope_areas
    own = [r for r in renewal_scope_rows if r["district"] == areas.district]

    with allure.step(f"Log in as a new District officer of {areas.district} ({areas.division})"):
        renewals = renewal_role_officer("district", areas.division, areas.district)
        expect(AdminSidebar(renewals.page).renewals_link).to_be_visible()
    _scope_check(renewals, own)

    with allure.step(f"Log in as a new District officer of {areas.empty_district} (no renewals)"):
        renewals = renewal_role_officer("district", areas.empty_division, areas.empty_district)
    _scope_check(renewals, [])


@aio_case("KAN-TC-842")
@allure.story(STORY)
@allure.title("TC-842: A Divisional officer sees the renewals of their division, with the view-only note")
def test_tc842_divisional_officer_scope(renewal_scope_rows, renewal_scope_areas, renewal_role_officer):
    """
    Given renewal applications exist in a division
    When  a Divisional officer of that division opens Renewal applications
    Then  the page adds the view-only note, and every tab lists exactly the division's applications

    Notion: KAN-TC-842 | KAN-51 AC-14 | Data: a NEW test Divisional officer (deleted afterwards)
    """
    areas = renewal_scope_areas
    own = [r for r in renewal_scope_rows if r["district"] in areas.division_districts]

    with allure.step(f"Log in as a new Divisional officer of {areas.division}"):
        renewals = renewal_role_officer("division", areas.division)

    with allure.step("Verify the view-only note"):
        expect(renewals.note).to_contain_text(AdminRenewalsPage.NOTE)
        expect(renewals.page.get_by_text(AdminRenewalsPage.DIVISIONAL_NOTE)).to_be_visible()
    _scope_check(renewals, own)


@aio_case("KAN-TC-843")
@allure.story(STORY)
@allure.title("TC-843: The Commissioner sees every renewal application")
def test_tc843_commissioner_sees_all(renewal_scope_rows, renewal_role_officer):
    """
    Given renewal applications exist in several districts
    When  the Commissioner opens Renewal applications
    Then  every tab lists and counts the same applications as for the Super Administrator, without the
          view-only note

    Notion: KAN-TC-843 | KAN-51 AC-15 | Data: a NEW test Commissioner (deleted afterwards)
    """
    with allure.step("Log in as a new Commissioner"):
        renewals = renewal_role_officer("commissioner")
        expect(renewals.note).to_have_text(AdminRenewalsPage.NOTE)
        expect(renewals.page.get_by_text(AdminRenewalsPage.DIVISIONAL_NOTE)).to_have_count(0)
    _scope_check(renewals, renewal_scope_rows)


@aio_case("KAN-TC-844")
@allure.story(STORY)
@allure.title("TC-844: Renewal applications needs an officer login")
def test_tc844_logged_out(logged_out_page, admin_renewals_page: AdminRenewalsPage):
    """
    Given I am not logged in to the Officer Console
    When  I open admin/licenses/renewals.php (also with ?tab=all)
    Then  the officer login page opens with ?reason=not_logged_in and no renewal data is shown

    Notion: KAN-TC-844 | KAN-51 AC-16
    """
    for tab in (None, "all"):
        with allure.step(f"Open Renewal applications{f' (?tab={tab})' if tab else ''} — the login page opens"):
            admin_renewals_page.open(tab=tab)
            expect(logged_out_page).to_have_url(re.compile(r"/admin/auth/login\.php\?reason=not_logged_in$"))
            expect(admin_renewals_page.table_headers).to_have_count(0)


@aio_case("KAN-TC-845")
@allure.story(STORY)
@allure.title("TC-845: Current validity shows the certificate's current expiry, also on older applications")
def test_tc845_current_validity(decided_renewals, renewal_admin_licenses_page: AdminLicensesPage):
    """
    Given renewal applications exist
    When  I read "Up to" on every row of each agency
    Then  all the rows of an agency show the same date — its current Valid Upto on Licences & certificates

    Notion: KAN-TC-845 | KAN-51 EC-4
    """
    _, rows = decided_renewals
    licenses = renewal_admin_licenses_page
    up_to: dict[str, set] = {}
    names = {}
    for r in rows:
        up_to.setdefault(r["reg"], set()).add(_parse(r["validity"]))
        names[r["reg"]] = r["agency"]

    with allure.step("Open Licences & certificates (all statuses)"):
        licenses.open(status="all")

    for reg, dates in up_to.items():
        with allure.step(f"{names[reg]}: every row shows the current Valid Upto"):
            current = _parse(licenses.valid_upto_cell(names[reg]).text_content())
            assert dates == {current}, f"rows show {sorted(dates)}, Licences shows {current}"


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

    Notion: KAN-TC-829 | KAN-51 AC-10 | Data: reasons of 30+ characters — irreversible (RUN_RENEWAL_TESTS)
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

    Notion: KAN-TC-414 | KAN-51 AC-9, KAN-37 EC-6 | Data: "Documents verified, no adverse report." — irreversible
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
