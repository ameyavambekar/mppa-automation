"""
Registrations in Progress — Admin Portal
========================================
Covers KAN-TC-601 through KAN-TC-617 (Jira KAN-45), except TC-613 (automatic
deletion after the deadline), which is manual.

The page lists every agency that has registered but not paid (a "draft"), with
filter chips, search, a details panel per draft and Extend deadline / Delete draft.
The drafts are live dev data, so most tests read them from the page. Where a test
compares a draft with what the agency entered, it uses an agency the state store
knows (``known_draft``).

Changing data:
* TC-609 extends the deadline of the oldest known draft by 3 days (it keeps that
  agency usable for longer; nothing else changes).
* TC-611 registers a throwaway agency and deletes its draft; the agency is then
  removed from the state store.
* TC-610 only cancels the Delete confirmation.

TC-616 checks that a draft's deadline is 7 days after its registration; on dev
(02-Nov-2026) the deadline is shown 5 h 30 min earlier (KAN-45 EC-1).
"""

import re
from datetime import datetime, timedelta

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.drafts_page import ADMIN_DRAFTS_URL, AdminDraftsPage
from pages.admin.login_page import AdminLoginPage
from test_data.drafts_factory import DraftsData
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Registrations in Progress"
ACTIVE = re.compile(r"\bon\b")
OPEN = re.compile(r"\bopen\b")
DATE = re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2} [AP]M$")


def _date(text: str) -> datetime:
    return datetime.strptime(text, AdminDraftsPage.DATE_FORMAT)


# ---------------------------------------------------------------------------
# TC-601  Page loads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-601")
@allure.story(STORY)
@allure.title("TC-601: Registrations in Progress loads with intro, filter chips, search and the drafts table")
def test_tc601_page_loads(logged_in_admin_drafts_page: AdminDraftsPage):
    """
    Given I am logged in to the Officer Console as the Super Administrator
    When  I click "Registrations in progress" in the sidebar
    Then  the page shows the heading, the intro (7 days to finish and pay, deleted automatically after that,
          listed under Agencies only after payment), the five chips with counts, the search box and the table
    And   "All drafts" is active and its count equals the number of rows and the sidebar badge

    Notion: KAN-TC-601 | KAN-45 AC-1
    """
    dp = logged_in_admin_drafts_page

    with allure.step("Click 'Registrations in progress' in the sidebar"):
        dp.sidebar.go_to_registrations_in_progress()
        expect(dp.page).to_have_url(ADMIN_DRAFTS_URL)

    with allure.step("Verify the title, heading, clock and intro"):
        expect(dp.page).to_have_title(AdminDraftsPage.PAGE_TITLE)
        expect(dp.heading).to_have_text(AdminDraftsPage.HEADING)
        expect(dp.clock).to_have_text(re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4} · \d{2}:\d{2}$"))
        for part in AdminDraftsPage.INTRO_PARTS:
            expect(dp.intro).to_contain_text(part)

    with allure.step("Verify the five filter chips"):
        expect(dp.chips).to_have_count(len(AdminDraftsPage.FILTERS))
        for filter_, label in AdminDraftsPage.FILTERS.items():
            expect(dp.chip_label(filter_)).to_have_text(label)
            expect(dp.chip_count(filter_)).to_have_text(re.compile(r"^\d+$"))

    with allure.step("Verify the search box and the table columns"):
        expect(dp.search_input).to_have_attribute("placeholder", AdminDraftsPage.SEARCH_PLACEHOLDER)
        expect(dp.search_button).to_be_visible()
        expect(dp.column_headers).to_have_text(list(AdminDraftsPage.COLUMNS))

    with allure.step("Verify 'All drafts' is active and its count equals the rows and the sidebar badge"):
        expect(dp.active_chip).to_have_count(1)
        expect(dp.chip("all")).to_have_class(ACTIVE)
        total = dp.chip_number("all")
        expect(dp.rows).to_have_count(total)
        assert dp.sidebar.badge_count("Registrations in progress") == str(total)


# ---------------------------------------------------------------------------
# TC-602  Newest registration first
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-602")
@allure.story(STORY)
@allure.title("TC-602: Drafts are listed newest registration first")
def test_tc602_newest_first(logged_in_admin_drafts_page: AdminDraftsPage):
    """
    Given I am on Registrations in Progress
    When  I read the Registered column
    Then  each draft registered at the same time as or before the one above it

    Notion: KAN-TC-602 | KAN-45 AC-2
    """
    dp = logged_in_admin_drafts_page

    with allure.step("Read every draft's registration time"):
        registered = [_date(r["registered"]) for r in dp.table_data()]

    with allure.step(f"Verify the {len(registered)} drafts are newest first"):
        assert registered, "No drafts are listed"
        assert registered == sorted(registered, reverse=True), "Drafts are not listed newest registration first"


# ---------------------------------------------------------------------------
# TC-603  Row content
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-603")
@allure.story(STORY)
@allure.title("TC-603: Each draft row shows agency, contact, district, progress, dates and a deadline pill")
def test_tc603_row_content(logged_in_admin_drafts_page: AdminDraftsPage):
    """
    Given I am on Registrations in Progress
    Then  every row shows the agency name and "@username[ · <agency type>]", e-mail and mobile, a district,
          "N/7 steps · next: <step>" with N of 7 bar segments filled (or "✓ All steps done — awaiting payment"),
          and Registered / Last activity as DD Mon YYYY, HH:MM AM/PM
    And   the Deadline pill is "N day(s) left" (ok) or, under 24 hours, "N hour(s) left" (warn) — for drafts
          ready to pay too

    Notion: KAN-TC-603 | KAN-45 AC-3
    """
    dp = logged_in_admin_drafts_page
    rows = dp.table_data()
    problems = []

    with allure.step(f"Check all {len(rows)} rows"):
        for r in rows:
            who = r["sub"]
            if not r["agency"] or not re.match(r"^@\S+( · .+)?$", r["sub"] or ""):
                problems.append(f"{who}: agency '{r['agency']}' / '{r['sub']}'")
            if not re.match(r"^\S+@\S+\s+\d{10}$", r["contact"]):
                problems.append(f"{who}: contact '{r['contact']}'")
            if not r["district"]:
                problems.append(f"{who}: no district")
            for column in ("registered", "last_activity"):
                if not DATE.match(r[column]):
                    problems.append(f"{who}: {column} '{r[column]}'")
            progress = AdminDraftsPage.PROGRESS.match(r["progress"])
            if r["progress"] != AdminDraftsPage.READY:
                if not progress:
                    problems.append(f"{who}: progress '{r['progress']}'")
                elif progress.group(2) not in AdminDraftsPage.STEPS:
                    problems.append(f"{who}: next step '{progress.group(2)}'")
                elif (r["bar_total"], r["bar_done"]) != (AdminDraftsPage.TOTAL_STEPS, int(progress.group(1))):
                    problems.append(f"{who}: bar {r['bar_done']}/{r['bar_total']} for '{r['progress']}'")
            days, hours = AdminDraftsPage.DAYS_LEFT.match(r["pill"]), AdminDraftsPage.HOURS_LEFT.match(r["pill"])
            if not ((days and "ok" in r["pill_class"]) or (hours and "warn" in r["pill_class"]
                                                           and int(hours.group(1)) < 24)):
                problems.append(f"{who}: deadline pill '{r['pill']}' ({r['pill_class']})")

    with allure.step("Verify no row is malformed"):
        assert not problems, f"{len(problems)} row problem(s):\n" + "\n".join(problems[:30])


# ---------------------------------------------------------------------------
# TC-604  Filter chips
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-604")
@allure.story(STORY)
@allure.title("TC-604: Filter chips list only matching drafts and their counts agree")
def test_tc604_filter_chips(logged_in_admin_drafts_page: AdminDraftsPage):
    """
    Given I am on Registrations in Progress
    When  I click each chip
    Then  the URL has ?f=<filter>, that chip is highlighted and as many rows are listed as its count
    And   Filling form lists no ready draft, Ready to pay only ready drafts, < 24 h left only hour pills
    And   Filling form + Ready to pay = All drafts

    Notion: KAN-TC-604 | KAN-45 AC-4
    """
    dp = logged_in_admin_drafts_page
    counts = {f: dp.chip_number(f) for f in AdminDraftsPage.FILTERS}

    for filter_, label in AdminDraftsPage.FILTERS.items():
        with allure.step(f"Click '{label}'"):
            dp.choose_filter(filter_)

        with allure.step(f"Verify '{label}' is active and lists {counts[filter_]} draft(s)"):
            expect(dp.page).to_have_url(re.compile(rf"\?f={filter_}&q=$"))
            expect(dp.chip(filter_)).to_have_class(ACTIVE)
            expect(dp.active_chip).to_have_count(1)
            expect(dp.rows).to_have_count(counts[filter_])

        with allure.step(f"Verify the drafts listed match '{label}'"):
            rows = dp.table_data()
            if filter_ == "progress":
                assert all(r["progress"] != AdminDraftsPage.READY for r in rows), "A ready draft is under Filling form"
            elif filter_ == "ready":
                assert all(r["progress"] == AdminDraftsPage.READY for r in rows), "A draft under Ready to pay is not ready"
            elif filter_ == "urgent":
                wrong = [r["sub"] for r in rows if not AdminDraftsPage.HOURS_LEFT.match(r["pill"])]
                assert not wrong, f"Drafts under < 24 h left without an hours pill: {wrong}"

    with allure.step("Verify Filling form + Ready to pay = All drafts"):
        assert counts["progress"] + counts["ready"] == counts["all"], counts


# ---------------------------------------------------------------------------
# TC-605  Search by username, e-mail, mobile, PAN
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-605")
@allure.story(STORY)
@allure.title("TC-605: Search finds a draft by username, e-mail, mobile or PAN and keeps the filter")
def test_tc605_search(known_draft):
    """
    Given an unpaid draft of an agency whose details I know
    When  I search for its username, then its e-mail, mobile and PAN
    Then  each time its draft is listed, the text stays in the box and "All drafts" stays active
    When  I choose "Filling form" and search for the username
    Then  the filter is kept (f=progress) and the draft is listed

    Notion: KAN-TC-605 | KAN-45 AC-5 | data: an agency from the state store
    """
    dp, agency = known_draft
    dp.choose_filter("all")

    for field, value in (("username", agency.username), ("e-mail", agency.email), ("mobile", agency.mobile),
                         ("PAN", agency.pan)):
        with allure.step(f"Search for the {field}"):
            dp.search(value)

        with allure.step(f"Verify the draft is listed and the search is kept ({field})"):
            expect(dp.row_for(agency.username)).to_have_count(1)
            expect(dp.search_input).to_have_value(value)
            expect(dp.chip("all")).to_have_class(ACTIVE)
            assert dp.rows.count() <= dp.chip_number("all")

    with allure.step("Choose 'Filling form' and search for the username"):
        dp.choose_filter("progress")
        dp.search(agency.username)

    with allure.step("Verify the filter is kept and the draft is listed"):
        expect(dp.page).to_have_url(re.compile(r"\?f=progress&q="))
        expect(dp.chip("progress")).to_have_class(ACTIVE)
        expect(dp.row_for(agency.username)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-606  Search with no match
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-606")
@allure.story(STORY)
@allure.title("TC-606: Search with no match shows \"No registrations in progress.\"")
def test_tc606_search_no_match(logged_in_admin_drafts_page: AdminDraftsPage, no_match_search_data: DraftsData):
    """
    Given I am on Registrations in Progress
    When  I search for text no draft contains
    Then  no rows are listed and the table shows "No registrations in progress."

    Notion: KAN-TC-606 | KAN-45 AC-5 | data: no_match_search
    """
    dp = logged_in_admin_drafts_page

    with allure.step(f"Search for '{no_match_search_data.query}'"):
        dp.search(no_match_search_data.query)

    with allure.step("Verify no draft is listed"):
        expect(dp.rows).to_have_count(0)
        expect(dp.empty_row).to_have_text(no_match_search_data.expected_message)


# ---------------------------------------------------------------------------
# TC-607  Row details
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-607")
@allure.story(STORY)
@allure.title("TC-607: Clicking a draft row opens its details; clicking again closes them")
def test_tc607_row_details(known_draft):
    """
    Given an unpaid draft of an agency whose details I know
    When  I click its row
    Then  the details panel opens with Agency, Username, Email, Mobile, PAN, Agency type / fee, Deadline and
          Draft ref. matching the agency; a ✓/○ chip per step (✓ Register, ○ Payment); document links;
          Extend deadline (+3 / +7 selected / +15 days) and Delete draft
    When  I click the row again
    Then  the panel closes

    Notion: KAN-TC-607 | KAN-45 AC-6 | data: an agency from the state store
    """
    dp, agency = known_draft
    dp.open(filter_="all", query=agency.username)
    row = dp.row_for(agency.username)

    with allure.step("Click the draft's row"):
        expect(dp.details(row)).to_be_hidden()
        dp.toggle_details(row)

    with allure.step("Verify the details match the agency"):
        expect(dp.details(row)).to_have_class(OPEN)
        expect(dp.detail_value(row, "Agency")).to_have_text(dp.agency_name(row).inner_text())
        expect(dp.detail_value(row, "Username")).to_have_text(agency.username)
        expect(dp.detail_value(row, "Email")).to_have_text(re.compile(rf"^{re.escape(agency.email)}( \(not OTP-verified\))?$"))
        expect(dp.detail_value(row, "Mobile")).to_have_text(agency.mobile)
        expect(dp.detail_value(row, "PAN")).to_have_text(agency.pan)
        expect(dp.detail_value(row, "Agency type / fee")).not_to_be_empty()
        expect(dp.detail_value(row, "Deadline")).to_have_text(re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2} [AP]M"))
        expect(dp.detail_value(row, "Draft ref.")).to_have_text(re.compile(r"^[0-9a-f]{12}…$"))

    with allure.step("Verify a chip per step, the document links and the actions"):
        expect(dp.step_chips(row)).to_have_count(len(AdminDraftsPage.STEPS))
        for step in AdminDraftsPage.STEPS:
            expect(dp.step_chip(row, step)).to_have_count(1)
        expect(dp.step_chip(row, "Register")).to_have_text(re.compile(r"^✓"))
        expect(dp.step_chip(row, "Payment")).to_have_text(re.compile(r"^○"))
        expect(dp.document_links(row).first).to_be_visible()
        assert dp.extend_days_select(row).locator("option").evaluate_all("os => os.map(o => o.value)") == \
            list(AdminDraftsPage.EXTEND_DAYS)
        expect(dp.extend_days_select(row)).to_have_value(AdminDraftsPage.DEFAULT_EXTEND_DAYS)
        expect(dp.extend_button(row)).to_be_visible()
        expect(dp.delete_button(row)).to_be_visible()

    with allure.step("Click the row again"):
        dp.toggle_details(row)

    with allure.step("Verify the details panel closes"):
        expect(dp.details(row)).not_to_have_class(OPEN)
        expect(dp.details(row)).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-608  Documents open
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-608")
@allure.story(STORY)
@allure.title("TC-608: Uploaded documents open in a new tab")
def test_tc608_document_opens(known_draft):
    """
    Given a draft's details panel is open
    When  I click the "PAN card" link
    Then  the uploaded file opens in a new tab

    Notion: KAN-TC-608 | KAN-45 AC-7 | data: an agency from the state store
    Note:   The file is fetched through the link's URL rather than opened in a tab: headless Chromium never
            finishes loading a PDF tab.
    """
    dp, agency = known_draft
    dp.open(filter_="all", query=agency.username)
    row = dp.row_for(agency.username)
    dp.toggle_details(row)
    link = dp.document_links(row).filter(has_text="PAN card").first

    with allure.step("Verify 'PAN card' opens in a new tab"):
        expect(link).to_be_visible()
        expect(link).to_have_attribute("target", "_blank")
        expect(link).to_have_attribute("href", re.compile(r"/serve_enclosure\.php\?t=[0-9a-f]+$"))

    with allure.step("Verify its URL serves the uploaded file"):
        response = dp.page.request.get(link.evaluate("a => a.href"))
        served = response.headers.get("content-type", "")
        assert response.ok, f"{response.status} for the PAN card"
        assert re.match(r"^(application/pdf|image/)", served), f"expected a PDF or image, got {served!r}"


# ---------------------------------------------------------------------------
# TC-609  Extend deadline
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-609")
@allure.story(STORY)
@allure.title("TC-609: Extend deadline moves the draft's deadline later by the chosen days")
def test_tc609_extend_deadline(known_draft, admin_audit_log_page: AdminAuditLogPage,
                               extend_deadline_data: DraftsData):
    """
    Given a draft's details panel is open
    When  I choose +3 days and click "Extend deadline"
    Then  the page shows "Deadline extended by 3 day(s).", the draft's deadline is 3 days later and marked
          "(+3d extended)"
    And   the newest Audit log entry is DRAFT_EXTEND for that draft, 3 days, by the officer

    Notion: KAN-TC-609 | KAN-45 AC-8 | data: extend_3_days (the oldest known draft)
    """
    dp, agency = known_draft
    days = extend_deadline_data.extend_days
    dp.open(filter_="all", query=agency.username)
    row = dp.row_for(agency.username)
    before = dp.deadline(row)
    token = dp.detail_value(row, "Draft ref.").inner_text().rstrip("…")

    with allure.step("Open the draft's details"):
        dp.toggle_details(row)

    with allure.step(f"Choose +{days} days and click 'Extend deadline'"):
        dp.extend_deadline(row, days)

    with allure.step("Verify the confirmation and the new deadline"):
        expect(dp.message(extend_deadline_data.expected_message)).to_be_visible()
        dp.open(filter_="all", query=agency.username)
        row = dp.row_for(agency.username)
        assert dp.deadline(row) == before + timedelta(days=int(days)), f"{before} → {dp.deadline(row)}"
        expect(dp.detail_value(row, "Deadline")).to_contain_text(re.compile(r"\(\+\d+d extended\)"))
        expect(dp.deadline_pill(row)).to_have_text(AdminDraftsPage.DAYS_LEFT)

    with allure.step("Open the Audit log"):
        admin_audit_log_page.open()

    with allure.step("Verify the newest entry is DRAFT_EXTEND for this draft"):
        entry = admin_audit_log_page.log_entry(0)
        expect(admin_audit_log_page.entry_action_pill(entry)).to_contain_text(AdminDraftsPage.AUDIT_EXTEND)
        expect(entry).to_contain_text(token[:8])
        expect(admin_audit_log_page.entry_detail_value(entry, "days")).to_have_text(days)


# ---------------------------------------------------------------------------
# TC-610  Cancel Delete draft
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-610")
@allure.story(STORY)
@allure.title("TC-610: Cancelling Delete draft keeps the draft")
def test_tc610_delete_cancel(known_draft, delete_confirmation_data: DraftsData):
    """
    Given a draft's details panel is open
    When  I click "Delete draft"
    Then  a confirm dialog asks "Delete this unfinished registration and ALL its uploaded files? This cannot
          be undone."
    When  I cancel
    Then  the draft is still listed and the All drafts count is unchanged

    Notion: KAN-TC-610 | KAN-45 AC-9 | data: delete_confirmation
    """
    dp, agency = known_draft
    total = dp.chip_number("all")
    dp.open(filter_="all", query=agency.username)
    row = dp.row_for(agency.username)
    dp.toggle_details(row)

    with allure.step("Click 'Delete draft' and cancel"):
        message = dp.delete_draft_cancel(row)

    with allure.step("Verify the confirmation text"):
        assert message == delete_confirmation_data.expected_message, message

    with allure.step("Verify the draft is kept"):
        dp.open(filter_="all", query=agency.username)
        expect(dp.row_for(agency.username)).to_have_count(1)
        expect(dp.chip_count("all")).to_have_text(str(total))


# ---------------------------------------------------------------------------
# TC-611  Delete draft
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-611")
@allure.story(STORY)
@allure.title("TC-611: Confirming Delete draft deletes the draft")
def test_tc611_delete_draft(throwaway_draft, admin_audit_log_page: AdminAuditLogPage,
                            delete_confirmation_data: DraftsData):
    """
    Given a newly registered agency's draft
    When  I open its details, click "Delete draft" and confirm
    Then  the draft is not listed under any filter and the All drafts count and sidebar badge drop by 1
    And   the newest Audit log entry records the deletion

    Notion: KAN-TC-611 | KAN-45 AC-9 | data: a throwaway agency registered by the fixture
    """
    dp, agency = throwaway_draft
    row = dp.row_for(agency.username)
    expect(row).to_have_count(1)
    total = dp.chip_number("all")
    token = dp.detail_value(row, "Draft ref.").inner_text().rstrip("…")

    with allure.step("Open the draft's details, click 'Delete draft' and confirm"):
        dp.toggle_details(row)
        message = dp.delete_draft(row)
        assert message == delete_confirmation_data.expected_message, message
        TestStateStore().delete_user(username=agency.username)

    with allure.step("Verify the draft is gone from every filter"):
        for filter_ in AdminDraftsPage.FILTERS:
            dp.open(filter_=filter_, query=agency.username)
            expect(dp.rows).to_have_count(0)

    with allure.step(f"Verify All drafts and the sidebar badge show {total - 1}"):
        dp.open()
        expect(dp.chip_count("all")).to_have_text(str(total - 1))
        assert dp.sidebar.badge_count("Registrations in progress") == str(total - 1)

    with allure.step("Verify the newest Audit log entry records the deletion"):
        admin_audit_log_page.open()
        entry = admin_audit_log_page.log_entry(0)
        expect(admin_audit_log_page.entry_action_pill(entry)).to_contain_text(re.compile(r"DRAFT.*DELETE", re.I))
        expect(entry).to_contain_text(token[:8])


# ---------------------------------------------------------------------------
# TC-612  Paid agency not listed
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-612")
@allure.story(STORY)
@allure.title("TC-612: A paid agency is not listed under Registrations in Progress")
def test_tc612_paid_agency_not_listed(logged_in_admin_drafts_page: AdminDraftsPage, paid_agency):
    """
    Given an agency that has paid (it has an Application ID)
    When  I search Registrations in Progress for its username
    Then  no draft is listed ("No registrations in progress.")

    Notion: KAN-TC-612 | KAN-45 AC-10 | data: a paid agency from the state store
    """
    dp = logged_in_admin_drafts_page

    with allure.step(f"Search for the paid agency {paid_agency.username}"):
        dp.search(paid_agency.username)

    with allure.step("Verify it is not listed"):
        expect(dp.row_for(paid_agency.username)).to_have_count(0)
        expect(dp.rows).to_have_count(0)
        expect(dp.empty_row).to_have_text(AdminDraftsPage.EMPTY_SEARCH)


# ---------------------------------------------------------------------------
# TC-614  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-614")
@allure.story(STORY)
@allure.title("TC-614: Registrations in Progress needs an officer session")
def test_tc614_needs_a_session(no_admin_session, admin_drafts_page: AdminDraftsPage, admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the Registrations in Progress URL
    Then  I am sent to the Admin Login page with "Please log in to continue."

    Notion: KAN-TC-614 | KAN-45 AC-12
    """
    with allure.step("Open the page without a session"):
        admin_drafts_page.open()

    with allure.step("Verify the Admin Login page opens with 'Please log in to continue.'"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        assert "reason=not_logged_in" in admin_login_page.get_url()


# ---------------------------------------------------------------------------
# TC-615  Unknown filter value
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-615")
@allure.story(STORY)
@allure.title("TC-615: Unknown filter value shows All drafts")
def test_tc615_unknown_filter(logged_in_admin_drafts_page: AdminDraftsPage, unknown_drafts_filter_data: DraftsData):
    """
    Given I am on Registrations in Progress
    When  I open it with ?f=bogus
    Then  "All drafts" is active and every draft is listed

    Notion: KAN-TC-615 | KAN-45 field-level validation | data: unknown_filter
    """
    dp = logged_in_admin_drafts_page
    total = dp.chip_number("all")

    with allure.step(f"Open the page with ?f={unknown_drafts_filter_data.filter_value}"):
        dp.open(filter_=unknown_drafts_filter_data.filter_value)

    with allure.step("Verify All drafts is active and every draft is listed"):
        expect(dp.chip("all")).to_have_class(ACTIVE)
        expect(dp.active_chip).to_have_count(1)
        expect(dp.rows).to_have_count(total)


# ---------------------------------------------------------------------------
# TC-616  Deadline = registration + 7 days
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-616")
@allure.story(STORY)
@allure.title("TC-616: A draft's deadline is 7 days after its registration time")
def test_tc616_deadline_is_seven_days_after_registration(logged_in_admin_drafts_page: AdminDraftsPage,
                                                         deadline_rule_data: DraftsData):
    """
    Given I am on Registrations in Progress
    When  I compare each draft's Registered time with its Deadline (drafts whose deadline was not extended)
    Then  the Deadline is exactly 7 days after the Registered time (both shown in the same time zone)

    Notion: KAN-TC-616 | KAN-45 EC-1 | data: deadline_rule
    Known defect (02-Nov-2026): the Deadline is 5 h 30 min earlier — it is shown in UTC, Registered in IST —
    this test fails.
    """
    dp = logged_in_admin_drafts_page
    rows = [r for r in dp.table_data() if r["deadline"] and "extended" not in r["deadline"]]

    with allure.step(f"Compare Registered + {deadline_rule_data.deadline_days} days with the Deadline "
                     f"of {len(rows)} drafts"):
        assert rows, "No draft with an unextended deadline is listed"
        wrong = [f"{r['sub']}: registered {r['registered']}, deadline {r['deadline']}" for r in rows
                 if _date(r["deadline"]) - _date(r["registered"]) != timedelta(days=deadline_rule_data.deadline_days)]
        assert not wrong, f"{len(wrong)} of {len(rows)} deadlines are not 7 days after registration:\n" + \
            "\n".join(wrong[:10])


# ---------------------------------------------------------------------------
# TC-617  Empty filter message
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-617")
@allure.story(STORY)
@allure.title("TC-617: An empty filter shows \"No registrations in progress for this filter.\"")
def test_tc617_empty_filter_message(logged_in_admin_drafts_page: AdminDraftsPage):
    """
    Given a filter chip shows 0 (e.g. Expired)
    When  I click it
    Then  no rows are listed and the table shows "No registrations in progress for this filter."

    Notion: KAN-TC-617 | KAN-45 EC-6
    """
    dp = logged_in_admin_drafts_page
    empty = [f for f in AdminDraftsPage.FILTERS if dp.chip_number(f) == 0]
    if not empty:
        pytest.skip("Every filter has drafts — no empty filter to check.")

    with allure.step(f"Click '{AdminDraftsPage.FILTERS[empty[0]]}' (0 drafts)"):
        dp.choose_filter(empty[0])

    with allure.step("Verify the empty-filter message"):
        expect(dp.rows).to_have_count(0)
        expect(dp.empty_row).to_have_text(AdminDraftsPage.EMPTY_FILTER)
