"""
District Breakup — Admin Portal (KAN-47)
========================================
Covers KAN-TC-678…688 and 690…694 (Reports › District breakup,
/module/admin/reports/district_breakup.php), logged in as the Super Admin.

The report's counts come from the live applications, so the tests compare the
page with itself and with Applications / Licences & certificates rather than
with fixed numbers.

Changes data: TC-688 suspends ``compliance_agency`` with a Route B compliance
case and then drops it (the agency is Active again; the case stays on
Compliance cases). TC-690 pays for an unpaid agency (or builds one), which
submits its application for good.

Not automated: KAN-TC-689 (approving / refusing an application needs the whole
Desktop scrutiny and Physical verification review and cannot be undone) and
KAN-TC-695…699 (under review). KAN-TC-694 skips while no submitted application
has the district "Other".

Known failures (04-Nov-2026, defect sheet "Super admin"): TC-692 (the clock
next to the heading shows UTC, 5 h 30 min behind IST — #68), TC-693 (the title
is "District-wise Breakup — Admin" instead of "… — MPPA Officer Console" — #69)
and TC-686 (the Applications "All applications" and "Approved" lists show "The
list could not be loaded (Ref …)", so those two columns cannot be compared;
every other per-district count matches — #70).
"""

import re
from datetime import datetime

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.applications_page import AdminApplicationsPage
from pages.admin.compliance_page import AdminCompliancePage
from pages.admin.district_breakup_page import ADMIN_DISTRICT_BREAKUP_URL, AdminDistrictBreakupPage
from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.login_page import AdminLoginPage
from test_data.compliance_factory import CaseActionData, ComplianceCaseData
from test_data.district_breakup_factory import DistrictBreakupFactory, DistrictCountChange
from utils.aio import aio_case

STORY = "District Breakup"
CLOCK = re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4} · \d{2}:\d{2}$")
ZERO_ROW = {"total": 0, "approved": 0, "submitted": 0, "rejected": 0, "suspended": 0}


def _counts(row: dict | None) -> dict[str, int]:
    return {key: (row or ZERO_ROW)[key] for key in ZERO_ROW}


def _delta(before: dict | None, after: dict | None) -> dict[str, int]:
    b, a = _counts(before), _counts(after)
    return {key: a[key] - b[key] for key in ZERO_ROW}


def _list_rows_by_district(apps: AdminApplicationsPage, view: str) -> dict[str, int] | str:
    """Opens an Applications view and counts its rows per district; returns the page's error text instead
    when the list cannot be loaded."""
    apps.open(view)
    if apps.load_error.count():
        return apps.load_error.inner_text().strip()
    counts: dict[str, int] = {}
    for row in apps.table_data():
        counts[row["district"]] = counts.get(row["district"], 0) + 1
    return counts


# ---------------------------------------------------------------------------
# TC-678  Page loads from the sidebar
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-678")
@allure.story(STORY)
@allure.title("TC-678: District breakup page loads from the sidebar")
def test_tc678_page_loads_from_sidebar(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am logged in to the Officer Console as the Super Administrator
    When  I click "District breakup" under Reports in the sidebar
    Then  the page opens with "District breakup" highlighted, the heading with the date and time,
          the "Registrations by District / City" bar chart and the "Detailed Breakup" table

    AIO: KAN-TC-678 | KAN-47 AC-1
    """
    report = logged_in_admin_district_breakup_page

    with allure.step("Click 'District breakup' in the sidebar"):
        report.sidebar.district_breakup_link.click()
        expect(report.page).to_have_url(re.compile(re.escape(ADMIN_DISTRICT_BREAKUP_URL) + r"$"))
        expect(report.sidebar.active_item).to_contain_text("District breakup")

    with allure.step("Verify the heading and the date and time"):
        expect(report.heading).to_have_text(report.HEADING)
        expect(report.page_clock).to_have_text(CLOCK)

    with allure.step("Verify the bar chart and the table cards"):
        expect(report.card_title(report.CHART_CARD)).to_have_text(report.CHART_CARD)
        expect(report.card_title(report.TABLE_CARD)).to_have_text(report.TABLE_CARD)
        expect(report.bar_rows.first).to_be_visible()
        expect(report.table_rows.first).to_be_visible()


# ---------------------------------------------------------------------------
# TC-679  Summary line
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-679")
@allure.story(STORY)
@allure.title("TC-679: Summary line counts the districts and the registrations")
def test_tc679_summary_line(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the subtitle reads "… — N location(s), T total registrations"
    And   there are N bar rows and N table rows, and the Total column adds up to T

    AIO: KAN-TC-679 | KAN-47 AC-2
    """
    report = logged_in_admin_district_breakup_page

    with allure.step("Read the subtitle"):
        summary = report.summary.inner_text().strip()
        allure.attach(summary, name="subtitle")
        counts = report.summary_counts()
        assert counts, f"Subtitle does not read '… — N location(s), T total registrations': {summary!r}"
        locations, total = counts

    with allure.step(f"Verify {locations} bar rows and {locations} table rows"):
        expect(report.bar_rows).to_have_count(locations)
        expect(report.table_rows).to_have_count(locations)

    with allure.step(f"Verify the Total column adds up to {total}"):
        assert sum(row["total"] for row in report.table_data()) == total


# ---------------------------------------------------------------------------
# TC-680  Total equals All applications
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-680")
@allure.story(STORY)
@allure.title("TC-680: Total registrations equal All applications on Applications")
def test_tc680_total_matches_applications(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    When  I open Applications
    Then  the "All applications" count equals the report's total registrations

    AIO: KAN-TC-680 | KAN-47 AC-2
    """
    report = logged_in_admin_district_breakup_page
    _, total = report.summary_counts()

    with allure.step("Open Applications and read 'All applications'"):
        apps = AdminApplicationsPage(report.page)
        apps.open("all")
        all_applications = apps.view_count("all")

    with allure.step(f"Verify All applications ({all_applications}) equals the report total ({total})"):
        assert all_applications == total


# ---------------------------------------------------------------------------
# TC-681  Bar labels and order
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-681")
@allure.story(STORY)
@allure.title("TC-681: Bar chart shows each district with its division and count, highest first")
def test_tc681_bar_labels_and_order(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  each bar is labelled "<District>, <Division>" with its count, each district appears once
    And   the counts never increase from one bar to the next

    AIO: KAN-TC-681 | KAN-47 AC-3
    """
    bars = logged_in_admin_district_breakup_page.bars_data()
    allure.attach(str(bars), name="bars")

    with allure.step("Verify every label is '<District>, <Division>' with a count"):
        bad = [b["label"] for b in bars if not b["district"] or not b["division"] or b["count"] < 1]
        assert not bad, f"Bars without a district, a division or a count: {bad}"

    with allure.step("Verify each district appears once"):
        districts = [b["district"] for b in bars]
        assert len(districts) == len(set(districts)), f"Repeated districts: {districts}"

    with allure.step("Verify the bars are ordered by count, highest first"):
        counts = [b["count"] for b in bars]
        assert counts == sorted(counts, reverse=True), f"Counts in page order: {counts}"


# ---------------------------------------------------------------------------
# TC-682  Bar lengths
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-682")
@allure.story(STORY)
@allure.title("TC-682: Bar lengths are relative to the highest count")
def test_tc682_bar_lengths(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the highest count's bar is 100% wide
    And   every other bar is count ÷ highest × 100, rounded to a whole %

    AIO: KAN-TC-682 | KAN-47 AC-3
    """
    bars = logged_in_admin_district_breakup_page.bars_data()
    highest = max(b["count"] for b in bars)
    expected = [(b["label"], DistrictBreakupFactory.bar_width(b["count"], highest)) for b in bars]
    actual = [(b["label"], b["width"]) for b in bars]
    allure.attach(f"expected: {expected}\nactual:   {actual}", name="bar widths")

    with allure.step(f"Verify the widths (highest count {highest} = 100%)"):
        assert actual == expected


# ---------------------------------------------------------------------------
# TC-683  Table matches the chart
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-683")
@allure.story(STORY)
@allure.title("TC-683: Detailed Breakup lists the districts in the chart's order with matching totals")
def test_tc683_table_matches_chart(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the table's columns are District, Division, Total, Approved, Submitted, Rejected, Suspended
    And   its rows are the chart's districts in the same order, with the same division and Total = bar count

    AIO: KAN-TC-683 | KAN-47 AC-4
    """
    report = logged_in_admin_district_breakup_page

    with allure.step("Verify the table columns"):
        expect(report.table_headers).to_have_text(list(report.COLUMNS))

    with allure.step("Compare the rows with the bars"):
        bars = [(b["district"], b["division"], b["count"]) for b in report.bars_data()]
        rows = [(r["district"], r["division"], r["total"]) for r in report.table_data()]
        allure.attach(f"bars: {bars}\nrows: {rows}", name="chart vs table")
        assert rows == bars


# ---------------------------------------------------------------------------
# TC-684  Status counts add up to Total
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-684")
@allure.story(STORY)
@allure.title("TC-684: Status counts add up to Total in every row")
def test_tc684_status_counts_add_up(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  in every row Approved + Submitted + Rejected + Suspended = Total, and no count is negative

    AIO: KAN-TC-684 | KAN-47 AC-4
    """
    report = logged_in_admin_district_breakup_page
    rows = report.table_data()
    allure.attach(str(rows), name="rows")

    with allure.step("Verify each row's status counts against its Total"):
        wrong = [r for r in rows if sum(r[c] for c in report.STATUS_COLUMNS) != r["total"]
                 or any(r[c] < 0 for c in report.STATUS_COLUMNS)]
        assert not wrong, f"Rows whose counts do not add up: {wrong}"


# ---------------------------------------------------------------------------
# TC-685  Column totals match Applications and Licences
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-685")
@allure.story(STORY)
@allure.title("TC-685: Approved, Rejected and Suspended totals match Applications and Licences")
def test_tc685_totals_match_applications(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the sums of Approved, Rejected and Suspended equal the Approved, Rejected and
          "Suspended / cancelled" counts on Applications
    And   the sum of Approved equals the Approved chip on Licences & certificates

    AIO: KAN-TC-685 | KAN-47 AC-5
    """
    report = logged_in_admin_district_breakup_page
    rows = report.table_data()
    sums = {c: sum(r[c] for r in rows) for c in ("approved", "rejected", "suspended")}

    with allure.step("Read the counts on Applications"):
        apps = AdminApplicationsPage(report.page)
        apps.open("all")
        views = {c: apps.view_count(c) for c in sums}

    with allure.step("Read the Approved chip on Licences & certificates"):
        licences = AdminLicensesPage(report.page)
        licences.open(status="all")
        licensed = licences.get_stat_chip_count("all")

    allure.attach(f"report: {sums}\napplications: {views}\nlicences approved: {licensed}", name="counts")
    with allure.step("Verify the report's column sums against Applications"):
        assert sums == views
    with allure.step("Verify the Approved sum against Licences & certificates"):
        assert sums["approved"] == licensed


# ---------------------------------------------------------------------------
# TC-686  Each district matches its applications
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-686")
@allure.story(STORY)
@allure.title("TC-686: Each district's counts match its applications")
def test_tc686_districts_match_applications(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    When  I count each Applications list's rows per district
    Then  every district's Total matches All applications, Submitted matches Desktop scrutiny + Physical
          verification, and Approved / Rejected / Suspended match their lists
    And   no district outside the report has an application (checked with the District filter too)

    AIO: KAN-TC-686 | KAN-47 AC-5
    """
    report = logged_in_admin_district_breakup_page
    table = report.table_by_district()
    apps = AdminApplicationsPage(report.page)

    with allure.step("Count each Applications list per district"):
        lists = {view: _list_rows_by_district(apps, view)
                 for view in ("all", "desktop", "physical", "approved", "rejected", "suspended")}
        allure.attach(str(lists), name="applications per district")

    problems = [f"Applications '{view}': {value}" for view, value in lists.items() if isinstance(value, str)]
    counted = {k: v for k, v in lists.items() if not isinstance(v, str)}

    def listed(district, *views):
        return sum(counted[v].get(district, 0) for v in views) if all(v in counted for v in views) else None

    with allure.step("Compare each district with the lists"):
        for district in sorted(set(table) | {d for v in counted.values() for d in v}):
            row = _counts(table.get(district))
            for column, views in (("total", ("all",)), ("submitted", ("desktop", "physical")),
                                  ("approved", ("approved",)), ("rejected", ("rejected",)),
                                  ("suspended", ("suspended",))):
                expected = listed(district, *views)
                if expected is not None and expected != row[column]:
                    problems.append(f"{district} {column}: report {row[column]}, Applications {expected}")

    with allure.step("Filter Applications by a district that is not in the report"):
        apps.open("desktop")
        missing = next((name for name in apps.district_ids() if name not in table), None)
        if missing:
            apps.open("desktop", district=apps.district_ids()[missing])
            if apps.rows.count():
                problems.append(f"{missing} is not in the report but has {apps.rows.count()} application(s)")

    allure.attach("\n".join(problems) or "none", name="differences")
    assert not problems, "District breakup does not match Applications:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# TC-687  Divisions
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-687")
@allure.story(STORY)
@allure.title("TC-687: Every district is shown with its own revenue division")
def test_tc687_divisions(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  each district's Division is its Maharashtra revenue division
          (e.g. Latur and Beed → Chhatrapati Sambhajinagar, Washim → Amravati)

    AIO: KAN-TC-687 | KAN-47 field-level validation
    """
    rows = logged_in_admin_district_breakup_page.table_data()
    wrong = [(r["district"], r["division"], DistrictBreakupFactory.division_of(r["district"])) for r in rows
             if r["district"] != DistrictBreakupFactory.OTHER_DISTRICT
             and r["division"] != DistrictBreakupFactory.division_of(r["district"])]
    allure.attach(str([(r["district"], r["division"]) for r in rows]), name="district, division")

    with allure.step("Verify each district's division"):
        assert not wrong, f"(district, shown division, expected division): {wrong}"


# ---------------------------------------------------------------------------
# TC-688  Suspension moves the agency to Suspended
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-688")
@allure.story(STORY)
@allure.title("TC-688: Suspending an agency moves it to the Suspended column")
def test_tc688_suspension_moves_to_suspended(logged_in_admin_compliance_page: AdminCompliancePage,
                                             compliance_agency: str, route_b_data: ComplianceCaseData,
                                             hearing_data: CaseActionData, revoke_data: CaseActionData,
                                             suspension_change: DistrictCountChange):
    """
    Given an approved agency with an Active certificate and no open compliance case
    When  a Route B compliance case suspends it
    Then  its district's Approved is 1 lower and Suspended 1 higher, with Total unchanged
    When  the case gets a hearing and the proceedings are dropped (the agency is Active again)
    Then  the district's counts are back to what they were

    AIO: KAN-TC-688 | KAN-47 AC-6 | data: {suspension_change.scenario_label}
    """
    cp = logged_in_admin_compliance_page
    report = AdminDistrictBreakupPage(cp.page)

    with allure.step("Note the report's counts"):
        report.open()
        before = report.table_by_district()

    with allure.step(f"Open a Route B case for {compliance_agency}"):
        cp.open()
        case_no, toast = cp.open_case_for(compliance_agency, route_b_data.trigger, route_b_data.details,
                                          route_b_data.high_risk, route_b_data.reasons)
        assert case_no, f"The Route B case was not opened: {toast}"
        district = cp.cases_for(compliance_agency)[0]["district"]
        allure.attach(district, name="district")

    with allure.step(f"Verify {district} moved one from Approved to Suspended"):
        report.open()
        suspended = report.table_by_district()
        assert _delta(before.get(district), suspended.get(district)) == suspension_change.as_dict(), (
            f"{district}: before {_counts(before.get(district))}, after {_counts(suspended.get(district))}")

    with allure.step("Schedule the hearing and drop the proceedings"):
        cp.open()
        _, toast = cp.take_action(case_no, "hearing", hearing_data.remarks, hearing_data.hearing_at,
                                  hearing_data.hearing_mode)
        assert toast == hearing_data.expected_message, toast
        _, toast = cp.take_action(case_no, revoke_data.action, revoke_data.remarks)
        assert toast == revoke_data.expected_message, toast

    with allure.step(f"Verify {district}'s counts are back"):
        report.open()
        assert _counts(report.table_by_district().get(district)) == _counts(before.get(district))


# ---------------------------------------------------------------------------
# TC-690  Counted only after payment
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-690")
@allure.story(STORY)
@allure.title("TC-690: An agency is counted only after it pays")
def test_tc690_counted_after_payment(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage,
                                     pay_for_new_application, new_submission_change: DistrictCountChange):
    """
    Given an agency has completed the Declaration but not paid (its draft is not counted:
          the report's total equals All applications)
    When  the agency pays
    Then  the total registrations, the agency's district's Total and Submitted are each 1 higher
    And   no other district changes

    AIO: KAN-TC-690 | KAN-47 AC-7 | data: {new_submission_change.scenario_label}
    """
    report = logged_in_admin_district_breakup_page

    with allure.step("Note the report's counts and check drafts are not counted"):
        _, total_before = report.summary_counts()
        before = report.table_by_district()
        apps = AdminApplicationsPage(report.page)
        apps.open("all")
        assert apps.view_count("all") == total_before

    with allure.step("Pay for an unpaid agency's application"):
        user = pay_for_new_application()
        allure.attach(f"{user.username} — {user.district} — {user.application_id}", name="agency")

    with allure.step(f"Verify only {user.district} changed: Total and Submitted +1"):
        report.open()
        _, total_after = report.summary_counts()
        after = report.table_by_district()
        changed = {d: _delta(before.get(d), after.get(d)) for d in set(before) | set(after)
                   if _delta(before.get(d), after.get(d)) != _delta(None, None)}
        allure.attach(str(changed), name="changed districts")
        assert total_after == total_before + 1
        assert changed == {user.district: new_submission_change.as_dict()}


# ---------------------------------------------------------------------------
# TC-691  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-691")
@allure.story(STORY)
@allure.title("TC-691: District breakup needs an admin session")
def test_tc691_needs_a_session(no_admin_session, admin_district_breakup_page: AdminDistrictBreakupPage,
                               admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the District breakup URL
    Then  I am sent to the Admin Login page with "Please log in to continue."

    AIO: KAN-TC-691 | KAN-47 AC-8
    """
    with allure.step("Open the page without a session"):
        admin_district_breakup_page.open()

    with allure.step("Verify the Admin Login page opens with 'Please log in to continue.'"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        assert "reason=not_logged_in" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-692  Clock in IST
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-692")
@allure.story(STORY)
@allure.title("TC-692: Page clock shows the current IST time")
def test_tc692_clock_in_ist(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the date and time next to the heading is the current IST date and time (within 2 minutes)

    AIO: KAN-TC-692 | KAN-47 EC-1
    """
    report = logged_in_admin_district_breakup_page
    shown = report.page_clock.inner_text().strip()
    now = DistrictBreakupFactory.now_ist()
    allure.attach(f"page: {shown}\nIST:  {now:%d %b %Y · %H:%M}", name="clock")

    with allure.step(f"Verify '{shown}' is within 2 minutes of {now:%d %b %Y %H:%M} IST"):
        clock = datetime.strptime(shown, report.CLOCK_FORMAT)
        assert abs(clock - now) <= DistrictBreakupFactory.CLOCK_TOLERANCE


# ---------------------------------------------------------------------------
# TC-693  Page title
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-693")
@allure.story(STORY)
@allure.title("TC-693: Page title matches the other Officer Console pages")
def test_tc693_page_title(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given I am on District breakup
    Then  the browser tab title is "District Breakup — MPPA Officer Console"

    AIO: KAN-TC-693 | KAN-47 EC-8
    """
    with allure.step(f"Verify the title is '{DistrictBreakupFactory.EXPECTED_TITLE}'"):
        expect(logged_in_admin_district_breakup_page.page).to_have_title(DistrictBreakupFactory.EXPECTED_TITLE)


# ---------------------------------------------------------------------------
# TC-694  District "Other"
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-694")
@allure.story(STORY)
@allure.title("TC-694: An agency registered outside the district list is counted under Other")
def test_tc694_other_district(logged_in_admin_district_breakup_page: AdminDistrictBreakupPage):
    """
    Given a submitted application whose district is "Other" (outside Maharashtra)
    Then  the report has an "Other" row counting it, and the total includes it

    AIO: KAN-TC-694 | KAN-47 EC-4
    """
    report = logged_in_admin_district_breakup_page
    table = report.table_by_district()
    other = DistrictBreakupFactory.OTHER_DISTRICT

    with allure.step("Count the applications with district 'Other' on Applications"):
        apps = AdminApplicationsPage(report.page)
        apps.open("desktop")
        other_id = apps.district_ids()[other]
        listed = 0
        for view in ("desktop", "physical", "rejected", "suspended"):
            apps.open(view, district=other_id)
            listed += apps.rows.count()
        if not listed and other not in table:
            pytest.skip('No submitted application has the district "Other".')

    with allure.step(f"Verify the report's '{other}' row counts them"):
        assert other in table, f'{listed} application(s) with district "Other", but no "Other" row'
        assert table[other]["total"] >= listed
