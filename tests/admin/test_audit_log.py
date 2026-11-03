"""
Audit Log — Admin Portal
========================
Covers KAN-TC-290 through KAN-TC-301 and KAN-TC-618 through KAN-TC-624 (Jira KAN-36).

The Audit Log is an append-only feed of officer and agency events with stat tiles,
a search box, an action type dropdown, date tabs and 30 events per page. The events
are live dev data, so the tests read them from the page; what each action type should
record comes from ``AuditLogFactory.ACTIONS`` (the KAN-36 Action Types table).

Changing data:
* TC-295 makes one wrong-password login as the Super Admin (five in a row would lock
  the account for 15 minutes) and then logs in correctly.
* TC-296 logs in as the most recently paid agency.

Known defects (02-Nov-2026; defect sheet "MPPA", tab "Super admin", logged 03-Nov-2026) —
these tests fail:
* TC-293 — every search returns 0 events (KAN-36 EC-2; sheet #51, regression of #39).
* TC-298 — choosing an action type or searching drops the date range (EC-9; #52).
* TC-301 — the header clock is in UTC, entries mix IST and UTC, relative times read
  "just now" for hours-old events (EC-3; #53).
* TC-621 — the full record's By chip always says "system" (EC-4; #54).
* TC-622 — a page beyond the last shows "Showing 29941–1712 of 1,712 events" (EC-5; #55).
* TC-623 — "Showing 1–0 of 0 events" and "1 Events" (EC-1 / EC-6; #56).
* TC-624 — the search box echoes the search HTML-escaped twice (EC-10; #57).
"""

import json
import math
import re
from datetime import datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from config import ADMIN_BASE
from pages.admin.audit_log_page import ADMIN_AUDIT_LOG_URL, AdminAuditLogPage
from pages.admin.login_page import AdminLoginPage
from pages.agency_home_page import AGENCY_HOME_URL
from pages.login_page import LoginPage
from test_data.admin_login_factory import AdminLoginData
from test_data.audit_log_factory import AuditLogData, AuditLogFactory
from utils.aio import aio_case

STORY = "Audit Log"
IST = timezone(timedelta(hours=5, minutes=30))
HAS_VALUE = re.compile(r"\bhas-value\b")
EXPANDED = re.compile(r"\bexpanded\b")
RECORD_ID = re.compile(r"^ID #\d+$")
# How many of the newest events to look through for the one a test has just caused
RECENT = 10


def _timestamp(text: str) -> datetime:
    return datetime.strptime(text, AdminAuditLogPage.TIMESTAMP_FORMAT)


def _today_dates() -> set:
    """Today's date in India and in UTC — the page counts "today" by one and stamps entries in both
    (KAN-36 EC-3)."""
    now = datetime.now(timezone.utc)
    return {now.date(), now.astimezone(IST).date()}


def _showing(audit: AdminAuditLogPage) -> tuple:
    """(from, to, N) from "Showing {from}–{to} of {N} events"."""
    m = AdminAuditLogPage.SHOWING.match(audit.showing_events_text.inner_text().strip())
    assert m, f"Unexpected count text: {audit.showing_events_text.inner_text()!r}"
    return tuple(int(g.replace(",", "")) for g in m.groups())


def _expected_showing(first: int, last: int, total: int) -> str:
    return f"Showing {first}–{last} of {total:,} events"


# ---------------------------------------------------------------------------
# TC-290  Page loads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-290")
@allure.story(STORY)
@allure.title("TC-290: Audit Log loads with header, four tiles and the 30 newest events")
def test_tc290_page_loads(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am logged in to the Officer Console as the Super Administrator
    When  I click "Audit log" in the sidebar
    Then  the header shows "Audit Log · N Events" and a clock, the tiles Total Events (= N), Today, This Week and
          Action Types (= the number of action types in the dropdown)
    And   the filter bar is unfiltered (All Time, "— All Action Types —", empty search, no Clear all)
    And   the 30 newest events are listed newest first with "Showing 1–30 of N events"

    Notion: KAN-TC-290 | KAN-36 AC-1
    """
    audit = logged_in_admin_audit_log_page

    with allure.step("Click 'Audit log' in the sidebar"):
        audit.page.goto(f"{ADMIN_BASE}/index.php")
        audit.sidebar.go_to_audit_log()
        expect(audit.page).to_have_url(ADMIN_AUDIT_LOG_URL)

    with allure.step("Verify the title, header and clock"):
        expect(audit.page).to_have_title(AdminAuditLogPage.PAGE_TITLE)
        expect(audit.page_title).to_have_text(re.compile(r"^Audit Log · [\d,]+ Events?$"))
        expect(audit.clock).to_have_text(re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4} · \d{2}:\d{2}$"))
        total = audit.total_events()

    with allure.step("Verify the four tiles"):
        expect(audit.stat_cards.locator(".l")).to_have_text(list(AdminAuditLogPage.STAT_CARDS))
        assert audit.stat_number("Total Events") == total
        assert audit.stat_number("Action Types") == audit.action_options.count()

    with allure.step("Verify the filter bar is unfiltered"):
        expect(audit.search_input).to_have_attribute("placeholder", AdminAuditLogPage.SEARCH_PLACEHOLDER)
        expect(audit.search_input).to_have_value("")
        expect(audit.selected_action_option).to_have_text(AdminAuditLogPage.ALL_ACTIONS)
        expect(audit.active_date_filter_tab).to_have_text("All Time")
        expect(audit.clear_all_link).to_have_count(0)

    with allure.step(f"Verify the first {AdminAuditLogPage.PAGE_SIZE} of {total} events, newest first"):
        shown = min(total, AdminAuditLogPage.PAGE_SIZE)
        expect(audit.showing_events_text).to_have_text(_expected_showing(1, shown, total))
        expect(audit.log_entries).to_have_count(shown)
        stamps = [_timestamp(e["timestamp"]) for e in audit.entries_data()]
        assert stamps == sorted(stamps, reverse=True), "Events are not listed newest first"


# ---------------------------------------------------------------------------
# TC-291  Date tabs
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-291")
@allure.story(STORY)
@allure.title("TC-291: Today, 7 Days and 30 Days tabs narrow the log; All Time restores it")
def test_tc291_date_tabs(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    When  I click Today, 7 Days, 30 Days and then All Time
    Then  each tab is highlighted and sets date_f; Total Events and the header show the filtered count (Today = the
          Today tile, 7 Days = the This Week tile) and only events in that window are listed
    And   the Today, This Week and Action Types tiles keep their unfiltered values; All Time restores the full log

    Notion: KAN-TC-291 | KAN-36 AC-2
    """
    audit = logged_in_admin_audit_log_page
    total = audit.total_events()
    tiles = {label: audit.stat_number(label) for label in ("Today", "This Week", "Action Types")}
    today = _today_dates()
    windows = {"Today": ("today", tiles["Today"], 0), "7 Days": ("week", tiles["This Week"], 8),
               "30 Days": ("month", None, 31)}
    counts = {}

    for label, (date_f, expected_total, max_age_days) in windows.items():
        with allure.step(f"Click '{label}'"):
            audit.filter_by_date(label)
            expect(audit.page).to_have_url(re.compile(rf"date_f={date_f}"))
            expect(audit.active_date_filter_tab).to_have_text(label)

        with allure.step(f"Verify the counts for '{label}'"):
            counts[label] = audit.total_events()
            assert audit.stat_number("Total Events") == counts[label]
            if expected_total is not None:
                assert counts[label] == expected_total, f"{label}: {counts[label]} events, tile says {expected_total}"
            for tile, value in tiles.items():
                assert audit.stat_number(tile) == value, f"{label}: the {tile} tile changed"

        with allure.step(f"Verify every event listed is within '{label}'"):
            for e in audit.entries_data():
                day = _timestamp(e["timestamp"]).date()
                if max_age_days == 0:
                    assert day in today, f"{label}: event of {e['timestamp']} listed"
                else:
                    assert day >= min(today) - timedelta(days=max_age_days), f"{label}: event of {e['timestamp']} listed"

    with allure.step("Verify 30 Days is between 7 Days and All Time"):
        assert counts["7 Days"] <= counts["30 Days"] <= total

    with allure.step("Click 'All Time'"):
        audit.filter_by_date("All Time")
        expect(audit.active_date_filter_tab).to_have_text("All Time")
        assert audit.total_events() >= total


# ---------------------------------------------------------------------------
# TC-292  Action type dropdown
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-292")
@allure.story(STORY)
@allure.title("TC-292: Choosing an action type filters the log at once; All Action Types restores it")
def test_tc292_action_dropdown(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    When  I choose "Admin Login" in the action type dropdown
    Then  the page reloads without pressing Search, with action_f=ADMIN_LOGIN, only Admin Login events, the option
          selected and the dropdown highlighted
    And   choosing "— All Action Types —" lists every action again

    Notion: KAN-TC-292 | KAN-36 AC-4
    """
    audit = logged_in_admin_audit_log_page
    total = audit.total_events()
    action = "ADMIN_LOGIN"
    label = AdminAuditLogPage.ACTION_LABELS[action]

    with allure.step("Verify the dropdown's first option and groups"):
        expect(audit.action_select.locator("option").first).to_have_text(AdminAuditLogPage.ALL_ACTIONS)
        groups = audit.action_groups.evaluate_all("gs => gs.map(g => g.label)")
        assert groups == list(AdminAuditLogPage.ACTION_GROUPS), f"Dropdown groups: {groups}"

    with allure.step(f"Choose '{label}'"):
        audit.filter_by_action(action)
        expect(audit.page).to_have_url(re.compile(rf"action_f={action}"))
        expect(audit.selected_action_option).to_have_attribute("value", action)
        expect(audit.action_select).to_have_class(HAS_VALUE)

    with allure.step(f"Verify only '{label}' events are listed"):
        filtered = audit.total_events()
        assert 0 < filtered <= total
        assert audit.stat_number("Total Events") == filtered
        actions = {e["action"] for e in audit.entries_data()}
        assert actions == {label}, f"Actions listed: {actions}"

    with allure.step("Choose '— All Action Types —'"):
        audit.clear_action_filter()
        expect(audit.selected_action_option).to_have_attribute("value", "")
        assert audit.total_events() >= total


# ---------------------------------------------------------------------------
# TC-293  Keyword search
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-293")
@allure.story(STORY)
@allure.title("TC-293: Keyword search finds events by user, table and action")
def test_tc293_keyword_search(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given the log holds Admin Login events (table admin_users) for the Super Admin
    When  I search for that username, for "admin_users" and for "ADMIN_LOGIN"
    Then  each search lists only events containing the keyword (at least one), and the keyword stays in the box

    Notion: KAN-TC-293 | KAN-36 AC-5

    Known defect (02-Nov-2026, KAN-36 EC-2): every search returns 0 events — this test fails.
    """
    audit = logged_in_admin_audit_log_page

    with allure.step("Read the username on the newest Admin Login event"):
        audit.open(action_f="ADMIN_LOGIN")
        username = audit.entries_data()[0]["details"]["username"]
        audit.open()

    problems = []
    for keyword in (username, "admin_users", "ADMIN_LOGIN"):
        with allure.step(f"Search for '{keyword}'"):
            audit.search(keyword)
            expect(audit.search_input).to_have_value(keyword)
            found = audit.total_events()
            if not found:
                problems.append(f"'{keyword}': no events found")
                continue
            for e in audit.entries_data():
                expand = audit.expand_row_by_id(e["audit_id"]).text_content()
                if keyword.lower() not in (json.dumps(e) + expand).lower():
                    problems.append(f"'{keyword}': event #{e['audit_id']} does not contain it")

    with allure.step("Verify every search found matching events"):
        assert not problems, "Search: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# TC-294  Full audit record
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-294")
@allure.story(STORY)
@allure.title("TC-294: Clicking an event opens its full audit record; another click, a second row or Esc closes it")
def test_tc294_expand_record(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    When  I click the newest event
    Then  "Full audit record — {ACTION} · {timestamp}" opens beneath it with Table, Record ID (when the row has one)
          and By chips, and JSON whose keys and values match the row's details
    And   clicking another row closes the first; clicking it again or pressing Esc closes it

    Notion: KAN-TC-294 | KAN-36 AC-9
    """
    audit = logged_in_admin_audit_log_page
    first = audit.entries_data()[0]

    with allure.step("Click the newest event"):
        audit.expand_entry(0)
        expect(audit.open_expand_row).to_have_count(1)
        expect(audit.log_entry(0)).to_have_class(EXPANDED)

    with allure.step("Verify the record's heading and chips"):
        expect(audit.expanded_record_header).to_have_text(
            re.compile(rf"Full audit record — [A-Z_]+ · {re.escape(first['timestamp'])}"))
        expect(audit.expanded_chip("Table")).to_have_text(first["table"])
        if first["record_id"]:
            expect(audit.expanded_chip("Record ID")).to_have_text(first["record_id"].replace("ID ", ""))
        else:
            expect(audit.expanded_chip("Record ID")).to_have_count(0)
        expect(audit.expanded_chip("By")).not_to_be_empty()

    with allure.step("Verify the JSON matches the row's details"):
        record = json.loads(audit.get_expanded_json_text())
        for key, value in first["details"].items():
            assert key in record, f"'{key}' is on the row but not in the record"
            if isinstance(record[key], (str, int, float)):
                assert str(record[key]) == value, f"{key}: row {value!r}, record {record[key]!r}"

    with allure.step("Click the second event"):
        audit.expand_entry(1)
        expect(audit.open_expand_row).to_have_count(1)
        expect(audit.log_entry(1)).to_have_class(EXPANDED)
        expect(audit.log_entry(0)).not_to_have_class(EXPANDED)

    with allure.step("Click the second event again"):
        audit.expand_entry(1)
        expect(audit.open_expand_row).to_have_count(0)

    with allure.step("Open a record and press Esc"):
        audit.expand_entry(0)
        expect(audit.open_expand_row).to_have_count(1)
        audit.collapse_expanded_entry()
        expect(audit.open_expand_row).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-295  Admin logins are audited
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-295")
@allure.story(STORY)
@allure.title("TC-295: Failed and successful admin logins write ADMIN_LOGIN_FAILED and Admin Login entries")
def test_tc295_admin_logins_audited(page, audit_counts_before: dict, super_admin_wrong_password: AdminLoginData,
                                    admin_login):
    """
    Given I know how many Admin Login and ADMIN_LOGIN_FAILED events the log holds
    When  I log in as the Super Admin once with a wrong password and then with the right one
    Then  each count went up, and among the newest events there is an ADMIN_LOGIN_FAILED on admin_users with no
          Record ID, the username and an ip, and an Admin Login on admin_users with ID #…, the username, an ip and
          role superadmin

    Notion: KAN-TC-295 | KAN-36 AC-11 | data: super_admin_wrong_password
    """
    data = super_admin_wrong_password

    with allure.step("Log in with a wrong password"):
        login = AdminLoginPage(page)
        login.open()
        assert login.login_past_captcha(data.username, data.password) == data.expected_error

    with allure.step("Log in with the right password"):
        admin_login()
        audit = AdminAuditLogPage(page)

    expected = {"ADMIN_LOGIN_FAILED": {"table": "admin_users", "has_record_id": False},
                "ADMIN_LOGIN": {"table": "admin_users", "has_record_id": True, "role": "superadmin"}}
    for action, exp in expected.items():
        with allure.step(f"Verify a new {action} event for {data.username}"):
            audit.open(action_f=action)
            assert audit.total_events() > audit_counts_before[action], f"No new {action} event"
            mine = [e for e in audit.entries_data()[:RECENT] if e["details"].get("username") == data.username]
            assert mine, f"No recent {action} event for {data.username}"
            e = mine[0]
            assert e["table"] == exp["table"]
            assert bool(RECORD_ID.match(e["record_id"])) == exp["has_record_id"], f"Record ID: {e['record_id']!r}"
            assert e["details"].get("ip"), f"{action} event has no ip"
            if "role" in exp:
                assert e["details"].get("role") == exp["role"]


# ---------------------------------------------------------------------------
# TC-296  Agency login is audited
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-296")
@allure.story(STORY)
@allure.title("TC-296: An agency login writes an Agency Login entry")
def test_tc296_agency_login_audited(page, audit_counts_before: dict, paid_agency_for_login, admin_login):
    """
    Given I know how many Agency Login events the log holds
    When  a paid agency logs in to the agency portal
    Then  the Agency Login count went up, and among the newest there is one on agency_registrations with ID #…,
          the agency's username, an ip and a status

    Notion: KAN-TC-296 | KAN-36 AC-11 | data: paid_agency_for_login
    """
    agency = paid_agency_for_login

    with allure.step(f"Log in to the agency portal as {agency.username}"):
        login = LoginPage(page)
        login.open()
        login.login(agency.username, agency.password)
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(rf"^{re.escape(AGENCY_HOME_URL)}"))
        page.context.clear_cookies()

    with allure.step("Log in as the Super Admin and filter the log to Agency Login"):
        admin_login()
        audit = AdminAuditLogPage(page)
        audit.open(action_f="LOGIN")

    with allure.step(f"Verify a new Agency Login event for {agency.username}"):
        assert audit.total_events() > audit_counts_before["LOGIN"], "No new Agency Login event"
        mine = [e for e in audit.entries_data()[:RECENT] if e["details"].get("username") == agency.username]
        assert mine, f"No recent Agency Login event for {agency.username}"
        e = mine[0]
        assert e["action"] == AdminAuditLogPage.ACTION_LABELS["LOGIN"]
        assert e["table"] == "agency_registrations"
        assert RECORD_ID.match(e["record_id"]), f"Record ID: {e['record_id']!r}"
        assert e["details"].get("ip") and e["details"].get("status"), f"Details: {e['details']}"


# ---------------------------------------------------------------------------
# TC-297  Append-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-297")
@allure.story(STORY)
@allure.title("TC-297: The Audit Log offers no way to change or delete an entry")
def test_tc297_no_edit_or_delete(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    Then  no event, and no opened full record, has an Edit, Delete, Remove or similar control
    And   the page has no form that posts changes

    Notion: KAN-TC-297 | KAN-36 AC-12
    """
    audit = logged_in_admin_audit_log_page

    with allure.step("Verify the event list has no edit or delete control"):
        expect(audit.log_entries.first).to_be_visible()
        expect(audit.edit_controls).to_have_count(0)
        expect(audit.page.locator("main form[method='post' i], main form[method='POST']")).to_have_count(0)

    with allure.step("Open a full record and verify it has none either"):
        audit.expand_entry(0)
        expect(audit.open_expand_row).to_have_count(1)
        expect(audit.edit_controls).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-298  Filters combine
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-298")
@allure.story(STORY)
@allure.title("TC-298: Date tab and action type combine")
def test_tc298_filters_combine(logged_in_admin_audit_log_page: AdminAuditLogPage,
                               audit_admin_login_today_data: AuditLogData):
    """
    Given I am on the Audit Log (my own login today guarantees an Admin Login event today)
    When  I click "Today" and then choose "Admin Login"
    Then  the URL has both filters, the Today tab is highlighted and Admin Login selected
    And   only Admin Login events from today are listed, no more than the Today tile and the all-time Admin Login count
    And   the date tab links keep action_f

    Notion: KAN-TC-298 | KAN-36 AC-6 | data: admin_login_today

    Known defect (02-Nov-2026, KAN-36 EC-9): the filter form has no date_f field, so choosing an action type (or
    searching) drops the date range — this test fails.
    """
    audit = logged_in_admin_audit_log_page
    data = audit_admin_login_today_data
    label = AdminAuditLogPage.ACTION_LABELS[data.action_f]

    with allure.step("Read the all-time Admin Login count"):
        audit.open(action_f=data.action_f)
        all_time = audit.total_events()
        audit.open()

    with allure.step(f"Click 'Today', then choose '{label}'"):
        audit.filter_by_date(AdminAuditLogPage.DATE_TABS[data.date_f])
        audit.filter_by_action(data.action_f)
        expect(audit.page).to_have_url(re.compile(rf"date_f={data.date_f}"))
        expect(audit.page).to_have_url(re.compile(rf"action_f={data.action_f}"))
        expect(audit.active_date_filter_tab).to_have_text(AdminAuditLogPage.DATE_TABS[data.date_f])
        expect(audit.selected_action_option).to_have_attribute("value", data.action_f)

    with allure.step("Verify only today's Admin Login events are listed"):
        combined = audit.total_events()
        assert 0 < combined <= min(audit.stat_number("Today"), all_time)
        today = _today_dates()
        for e in audit.entries_data():
            assert e["action"] == label, f"{e['action']} event listed"
            assert _timestamp(e["timestamp"]).date() in today, f"Event of {e['timestamp']} listed"

    with allure.step("Verify the date tab links keep the action type"):
        for tab in AdminAuditLogPage.DATE_TABS.values():
            expect(audit.date_filter_tab(tab)).to_have_attribute("href", re.compile(rf"action_f={data.action_f}"))


# ---------------------------------------------------------------------------
# TC-299  No matching events
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-299")
@allure.story(STORY)
@allure.title("TC-299: No matching events shows the empty state; the other tiles keep their values")
def test_tc299_no_matches(logged_in_admin_audit_log_page: AdminAuditLogPage, audit_no_match_data: AuditLogData):
    """
    Given I am on the Audit Log
    When  I search for a keyword that matches nothing
    Then  "No audit records found for the selected filters." shows, no events are listed, the header and Total Events
          show 0 and "✕ Clear all" is shown
    And   Today, This Week and Action Types keep their values

    Notion: KAN-TC-299 | KAN-36 EC-1 | data: no_match_search
    """
    audit = logged_in_admin_audit_log_page
    data = audit_no_match_data
    tiles = {label: audit.stat_number(label) for label in ("Today", "This Week", "Action Types")}

    with allure.step(f"Search for '{data.query}'"):
        audit.search(data.query)

    with allure.step("Verify the empty state"):
        expect(audit.empty_state).to_be_visible()
        expect(audit.log_entries).to_have_count(0)
        expect(audit.page_title).to_have_text(re.compile(r"^Audit Log · 0 Events$"))
        assert audit.stat_number("Total Events") == 0
        expect(audit.clear_all_link).to_be_visible()

    with allure.step("Verify the other tiles kept their values"):
        # Today and This Week can only grow while the test runs (other events being logged)
        assert audit.stat_number("Today") >= tiles["Today"]
        assert audit.stat_number("This Week") >= tiles["This Week"]
        assert audit.stat_number("Action Types") == tiles["Action Types"]


# ---------------------------------------------------------------------------
# TC-300  Pagination
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-300")
@allure.story(STORY)
@allure.title("TC-300: Pagination: 30 per page, footer and page links keep the filters")
def test_tc300_pagination(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given the log holds more than 30 events (and more than 30 Admin Login events)
    Then  page 1 is current with footer "1–30 of N · Page 1 / P"
    When  I click page 2
    Then  "Showing 31–60 of N events", footer "31–60 of N · Page 2 / P" and different events, newest first
    When  I choose Admin Login and click ›
    Then  the page links keep action_f and page 2 lists only Admin Login events
    And   the last page lists N − 30 × (P − 1) events and has no ›

    Notion: KAN-TC-300 | KAN-36 AC-10
    """
    audit = logged_in_admin_audit_log_page
    size = AdminAuditLogPage.PAGE_SIZE
    total = audit.total_events()
    pages = math.ceil(total / size)
    assert pages > 1, f"Only {total} events — pagination needs more than {size}"

    with allure.step("Verify page 1"):
        expect(audit.current_page_number).to_have_text("1")
        expect(audit.pagination_info).to_have_text(f"1–{size} of {total:,} · Page 1 / {pages}")
        page1 = {e["audit_id"] for e in audit.entries_data()}

    with allure.step("Click page 2"):
        audit.go_to_page(2)
        expect(audit.current_page_number).to_have_text("2")
        expect(audit.showing_events_text).to_have_text(_expected_showing(size + 1, min(2 * size, total), total))
        expect(audit.pagination_info).to_have_text(f"{size + 1}–{min(2 * size, total)} of {total:,} · Page 2 / {pages}")
        entries = audit.entries_data()
        assert not page1 & {e["audit_id"] for e in entries}, "Page 2 repeats events from page 1"
        stamps = [_timestamp(e["timestamp"]) for e in entries]
        assert stamps == sorted(stamps, reverse=True), "Page 2 is not newest first"

    action = "ADMIN_LOGIN"
    label = AdminAuditLogPage.ACTION_LABELS[action]
    with allure.step(f"Choose '{label}' and click ›"):
        audit.open()
        audit.filter_by_action(action)
        filtered = audit.total_events()
        filtered_pages = math.ceil(filtered / size)
        assert filtered_pages > 1, f"Only {filtered} {label} events — need more than {size}"
        for href in audit.page_links.evaluate_all("as => as.map(a => a.getAttribute('href'))"):
            assert f"action_f={action}" in href, f"Page link {href} drops the action filter"
        audit.go_to_next_page()
        expect(audit.current_page_number).to_have_text("2")
        assert {e["action"] for e in audit.entries_data()} == {label}

    with allure.step("Open the last page"):
        audit.open(action_f=action, page=filtered_pages)
        expect(audit.log_entries).to_have_count(filtered - size * (filtered_pages - 1))
        expect(audit.next_page_link).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-301  Clock, timestamps and relative times
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-301")
@allure.story(STORY)
@allure.title("TC-301: Header clock, event timestamps and relative times agree (IST)")
def test_tc301_clock_and_relative_times(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    Then  the header clock shows the current time in India (within a few minutes)
    And   "just now" is shown only for events under a minute or two old
    And   timestamps never increase down the list

    Notion: KAN-TC-301 | KAN-36 EC-3

    Known defect (02-Nov-2026, KAN-36 EC-3): the clock is in UTC, entries mix IST and UTC, and IST-stamped events
    from the last ~5½ hours show "just now" — this test fails.
    """
    audit = logged_in_admin_audit_log_page
    now = datetime.now(IST).replace(tzinfo=None)
    problems = []

    with allure.step("Compare the header clock with the time in India"):
        clock = datetime.strptime(audit.clock.inner_text().strip(), AdminAuditLogPage.CLOCK_FORMAT)
        if abs(clock - now) > timedelta(minutes=5):
            problems.append(f"clock {clock:%H:%M}, time in India {now:%H:%M}")

    with allure.step("Compare each event's relative time with its timestamp"):
        entries = audit.entries_data()
        for e in entries:
            age = now - _timestamp(e["timestamp"])
            if e["ago"] == "just now" and age > timedelta(minutes=2):
                problems.append(f"{e['timestamp']} ({age} old) shows 'just now'")
                break

    with allure.step("Verify the order"):
        stamps = [_timestamp(e["timestamp"]) for e in entries]
        if stamps != sorted(stamps, reverse=True):
            problems.append("timestamps increase down the list")

    assert not problems, "Times disagree: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# TC-618  Today / This Week tiles
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-618")
@allure.story(STORY)
@allure.title("TC-618: Today and This Week tiles open the log filtered to their date range")
def test_tc618_tiles_filter(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given I am on the Audit Log
    When  I click the Today tile, then the This Week tile
    Then  the log opens with date_f=today (Today tab highlighted) / date_f=week (7 Days tab highlighted) and
          Total Events equals the number on the tile
    And   Total Events and Action Types are not links

    Notion: KAN-TC-618 | KAN-36 AC-3
    """
    audit = logged_in_admin_audit_log_page

    for tile, date_f in (("Today", "today"), ("This Week", "week")):
        with allure.step(f"Click the {tile} tile"):
            audit.click_stat_card(tile)
            expect(audit.page).to_have_url(re.compile(rf"date_f={date_f}"))
            expect(audit.active_date_filter_tab).to_have_text(AdminAuditLogPage.DATE_TABS[date_f])

        with allure.step(f"Verify Total Events equals the {tile} tile"):
            assert audit.stat_number("Total Events") == audit.stat_number(tile) == audit.total_events()

    with allure.step("Verify Total Events and Action Types are not links"):
        for tile in ("Total Events", "Action Types"):
            assert audit.stat_card(tile).evaluate("e => e.tagName") != "A", f"{tile} is a link"


# ---------------------------------------------------------------------------
# TC-619  Clear all
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-619")
@allure.story(STORY)
@allure.title("TC-619: ✕ Clear all resets search, action type and date")
def test_tc619_clear_all(logged_in_admin_audit_log_page: AdminAuditLogPage, audit_all_filters_data: AuditLogData):
    """
    Given I am on the Audit Log with no filter, so "✕ Clear all" is not shown
    When  I open it with a search, an action type and a date range, then click "✕ Clear all"
    Then  every filter is reset (All Time, "— All Action Types —", empty search) and Total Events is the full count
    And   "✕ Clear all" is gone

    Notion: KAN-TC-619 | KAN-36 AC-7 | data: all_filters
    """
    audit = logged_in_admin_audit_log_page
    data = audit_all_filters_data
    total = audit.total_events()

    with allure.step("Verify '✕ Clear all' is not shown without filters"):
        expect(audit.clear_all_link).to_have_count(0)

    with allure.step("Open the log with search, action type and date set"):
        audit.open(date_f=data.date_f, action_f=data.action_f, q=data.query)
        expect(audit.clear_all_link).to_be_visible()

    with allure.step("Click '✕ Clear all'"):
        audit.clear_all()
        expect(audit.page).to_have_url(re.compile(rf"^{re.escape(ADMIN_AUDIT_LOG_URL)}\??$"))

    with allure.step("Verify every filter is reset"):
        expect(audit.active_date_filter_tab).to_have_text("All Time")
        expect(audit.selected_action_option).to_have_attribute("value", "")
        expect(audit.search_input).to_have_value("")
        assert audit.total_events() >= total
        expect(audit.clear_all_link).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-620  Row content per action type
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-620")
@allure.story(STORY)
@allure.title("TC-620: Each action type's events show their pill, table, Record ID and detail keys")
def test_tc620_row_content(logged_in_admin_audit_log_page: AdminAuditLogPage,
                           audit_action_types_data: AuditLogData):
    """
    Given I am on the Audit Log
    When  I choose each action type in the dropdown
    Then  its newest event shows a "DD Mon YYYY, HH:MM:SS" timestamp and a relative time, and the pill label, table,
          Record ID (present or not) and detail keys of the KAN-36 Action Types table
    And   each action type sits in its dropdown group

    Notion: KAN-TC-620 | KAN-36 AC-8 | data: action_types
    """
    audit = logged_in_admin_audit_log_page
    specs = audit_action_types_data.actions
    problems = []

    with allure.step("Verify each action type's dropdown group"):
        groups = audit.action_groups.evaluate_all(
            "gs => Object.fromEntries(gs.flatMap(g => [...g.children].map(o => [o.value, g.label])))")
        for action, group in groups.items():
            spec = specs.get(action)
            if spec is None:
                problems.append(f"{action}: not in the KAN-36 Action Types table")
            elif group != spec.group:
                problems.append(f"{action}: in group {group}, expected {spec.group}")

    for action in audit.action_values():
        spec = specs.get(action)
        if spec is None:
            continue
        with allure.step(f"Check the newest {action} event"):
            audit.open(action_f=action)
            e = audit.entries_data()[0]
            try:
                _timestamp(e["timestamp"])
            except ValueError:
                problems.append(f"{action}: timestamp {e['timestamp']!r}")
            if not AdminAuditLogPage.TIME_AGO.match(e["ago"]):
                problems.append(f"{action}: relative time {e['ago']!r}")
            if e["action"] != spec.label:
                problems.append(f"{action}: pill {e['action']!r}, expected {spec.label!r}")
            if e["table"] != spec.table:
                problems.append(f"{action}: table {e['table']!r}, expected {spec.table!r}")
            if bool(RECORD_ID.match(e["record_id"])) != spec.has_record_id:
                problems.append(f"{action}: Record ID {e['record_id']!r}")
            if tuple(e["details"]) != spec.detail_keys:
                problems.append(f"{action}: detail keys {tuple(e['details'])}, expected {spec.detail_keys}")

    assert not problems, "Rows: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# TC-621  By chip
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-621")
@allure.story(STORY)
@allure.title("TC-621: Full audit record names who did it (By chip)")
def test_tc621_by_chip(logged_in_admin_audit_log_page: AdminAuditLogPage):
    """
    Given the log holds Admin Login events (and possibly DRAFT_EXTEND events)
    When  I open the newest one's full record
    Then  By: names who did it — the Admin Login's username, the DRAFT_EXTEND's "by"

    Notion: KAN-TC-621 | KAN-36 EC-4

    Known defect (02-Nov-2026, KAN-36 EC-4): By is always "system" — this test fails.
    """
    audit = logged_in_admin_audit_log_page
    actors = {"ADMIN_LOGIN": "username", "DRAFT_EXTEND": "by"}
    problems = []

    for action, key in actors.items():
        if action not in audit.action_values():
            continue
        with allure.step(f"Open the newest {action} record"):
            audit.open(action_f=action)
            expected = audit.entries_data()[0]["details"][key]
            audit.expand_entry(0)
            by = audit.expanded_chip("By").inner_text().strip()
            if by != expected:
                problems.append(f"{action}: By {by!r}, expected {expected!r}")

    assert not problems, "By chip: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# TC-622  Page beyond the last
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-622")
@allure.story(STORY)
@allure.title("TC-622: A page number beyond the last page shows a sensible page")
def test_tc622_page_beyond_last(logged_in_admin_audit_log_page: AdminAuditLogPage,
                                audit_page_beyond_last_data: AuditLogData):
    """
    Given the log has fewer pages than the one asked for
    When  I open ?page=999
    Then  either the last page's events are shown, or the count and footer do not describe a page beyond the last

    Notion: KAN-TC-622 | KAN-36 EC-5 | data: page_beyond_last

    Known defect (02-Nov-2026, KAN-36 EC-5): "Showing 29941–1712 of 1,712 events" and "Page 999 / 58" — this test
    fails.
    """
    audit = logged_in_admin_audit_log_page
    data = audit_page_beyond_last_data
    pages = math.ceil(audit.total_events() / AdminAuditLogPage.PAGE_SIZE)
    assert data.page > pages, f"The log has {pages} pages"

    with allure.step(f"Open page {data.page}"):
        audit.open(page=data.page)

    with allure.step("Verify the page shown is sensible"):
        first, last, total = _showing(audit)
        info = AdminAuditLogPage.PAGINATION_INFO.match(audit.pagination_info.inner_text().strip())
        if audit.get_entry_count():
            return
        assert first <= last, f"Count reads 'Showing {first}–{last} of {total:,} events'"
        assert info and int(info.group(4)) <= int(info.group(5)), f"Footer: {audit.pagination_info.inner_text()!r}"


# ---------------------------------------------------------------------------
# TC-623  Count wording for 0 and 1
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-623")
@allure.story(STORY)
@allure.title("TC-623: Event counts read correctly for 0 and 1 events")
def test_tc623_count_wording(logged_in_admin_audit_log_page: AdminAuditLogPage, audit_no_match_data: AuditLogData):
    """
    Given I am on the Audit Log
    When  I search for a keyword that matches nothing
    Then  the count reads "Showing 0 of 0 events"
    When  I choose an action type with exactly one event (if there is one)
    Then  the header reads "Audit Log · 1 Event" and the count "Showing 1–1 of 1 event"

    Notion: KAN-TC-623 | KAN-36 EC-1, EC-6 | data: no_match_search

    Known defects (02-Nov-2026, KAN-36 EC-1 / EC-6): "Showing 1–0 of 0 events" and "1 Events" — this test fails.
    """
    audit = logged_in_admin_audit_log_page
    problems = []

    with allure.step("Search for a keyword that matches nothing"):
        audit.search(audit_no_match_data.query)
        text = audit.showing_events_text.inner_text().strip()
        if text != "Showing 0 of 0 events":
            problems.append(f"no events: {text!r}")

    with allure.step("Find an action type with exactly one event"):
        single = None
        for action in audit.action_values():
            audit.open(action_f=action)
            if audit.total_events() == 1:
                single = action
                break

    if single:
        with allure.step(f"Verify the wording for the one {single} event"):
            title = audit.page_title.inner_text().strip()
            text = audit.showing_events_text.inner_text().strip()
            if title != "Audit Log · 1 Event":
                problems.append(f"one event: header {title!r}")
            if text != "Showing 1–1 of 1 event":
                problems.append(f"one event: {text!r}")
    else:
        allure.attach("No action type has exactly one event", name="one event", attachment_type=allure.attachment_type.TEXT)

    assert not problems, "Count wording: " + "; ".join(problems)


# ---------------------------------------------------------------------------
# TC-624  Invalid filter values
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-624")
@allure.story(STORY)
@allure.title("TC-624: Unknown date or action filters and HTML in the search are handled safely")
def test_tc624_invalid_filters(logged_in_admin_audit_log_page: AdminAuditLogPage,
                               audit_unknown_date_data: AuditLogData, audit_unknown_action_data: AuditLogData,
                               audit_html_search_data: AuditLogData):
    """
    Given I am on the Audit Log
    When  I open it with an unknown date filter
    Then  it lists the All Time results with no date tab highlighted
    When  I open it with an unknown action type
    Then  it lists nothing, shows the empty state and the dropdown shows "— All Action Types —"
    When  I search for HTML
    Then  the box shows the text as typed and no script runs

    Notion: KAN-TC-624 | KAN-36 Field-Level Validations | data: unknown_date_filter, unknown_action_filter, html_search

    Known defect (02-Nov-2026, KAN-36 EC-10): the search is HTML-escaped twice when echoed back, so the box shows
    "&lt;script&gt;…" (and "O'Reilly & co" as "O&apos;Reilly &amp; co") — the last step fails. No script runs.
    """
    audit = logged_in_admin_audit_log_page
    total = audit.total_events()

    with allure.step(f"Open the log with date_f={audit_unknown_date_data.date_f}"):
        audit.open(date_f=audit_unknown_date_data.date_f)
        assert audit.total_events() >= total
        expect(audit.active_date_filter_tab).to_have_count(0)

    with allure.step(f"Open the log with action_f={audit_unknown_action_data.action_f}"):
        audit.open(action_f=audit_unknown_action_data.action_f)
        expect(audit.log_entries).to_have_count(0)
        expect(audit.empty_state).to_be_visible()
        expect(audit.selected_action_option).to_have_text(AdminAuditLogPage.ALL_ACTIONS)

    with allure.step(f"Search for {audit_html_search_data.query}"):
        dialogs = []
        audit.page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        audit.open()
        audit.search(audit_html_search_data.query)
        assert not dialogs, f"A script ran: {dialogs}"
        expect(audit.search_input).to_have_value(audit_html_search_data.query)
