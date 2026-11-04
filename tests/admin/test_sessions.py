"""
Session Management — Admin Portal (KAN-32)
==========================================
Covers KAN-TC-246…256 and 715, 717…722 (Administration › Active sessions,
/module/admin/sessions/index.php), logged in as the Super Admin. Rewritten
04-Nov-2026 for the updated cases: tiles are the filter links, search is a form
(?q=), 20 rows per page with a range line, and Kill / Kill All use the browser
prompts "Terminate this session?" / "Kill ALL active sessions now?".

Targets (a username to search, an open or ended row) are read from the live
list. The single-session kill tests (TC-249, TC-250) kill only a session they
open themselves in a second browser (``agency_session``).

Kill All (TC-251, TC-256) ends EVERY open agency session on dev, so those two
run only with RUN_KILL_ALL_TESTS=true (``kill_all_allowed``).

Only agencies with a submitted application (they land on home.php) are listed;
a user still in the Form-I wizard never gets a session row, so ``agency_session``
logs in one of those. A Live row shows "Online" in Logout / End, a Stale one "—".

Not automated: KAN-TC-716 (Live vs Stale threshold), 723 (agency idle timeout)
and 724 (kill from a stale tab) are under review.

Known failures on dev (04-Nov-2026), page behaviour — MPPA sheet, "Super admin" tab:
  TC-246, TC-248  #78 open sessions counted as Live Now are badged Stale ("No ping")
  TC-249, TC-250  #77 Kill posts kill_session but the session stays Live and the agency stays logged in
  TC-253          #79 every search lists "No sessions found."
  TC-255          #78 open No ping sessions are badged Stale but the Stale tab is empty
  TC-718          #80 the search box shows O&apos;Brien (escaped twice)
  TC-719          #81 ?page=999 shows "Page 999 of 16" and "19961–302 of 302"
  TC-720          #82 ?type=bogus highlights no tab or tile
  TC-721          #83 the clock shows UTC, not IST
  TC-722          #84 the title is "Sessions — Admin"
"""

import math
import re
from datetime import timedelta

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.sessions_page import SESSIONS_URL, AdminSessionsPage
from test_data.sessions_factory import SessionData, SessionsFactory
from utils.aio import aio_case

STORY = "Session Management"
F = SessionsFactory
KILL_ALL = re.compile(r"Kill All Active \((\d+)\)")


def _tiles(sp: AdminSessionsPage) -> dict:
    return {t: sp.get_stat_chip_count(t) for t in sp.TYPE_FILTERS}


def _kill_all_n(sp: AdminSessionsPage) -> int:
    return int(KILL_ALL.search(sp.kill_all_button.inner_text()).group(1))


def _pages(total: int) -> int:
    return max(1, math.ceil(total / F.PAGE_SIZE))


def _range_re(start: int, end: int, total: int, page: int, pages: int):
    return re.compile(rf"^\s*{start}–{end} of {total} sessions\s*·\s*Page {page} of {pages}\s*$")


def _own_open_row(sp: AdminSessionsPage, username: str) -> dict:
    """The newest open row of ``username`` on page 1 of All — the session the test just opened."""
    sp.open()
    rows = [r for r in sp.rows_data() if r["username"] == username and r["killable"]]
    assert rows, f"No open session for {username} on page 1 of the All list"
    return rows[0]


# ---------------------------------------------------------------------------
# TC-246  Tiles
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-246")
@allure.story(STORY)
@allure.title("TC-246: Session tiles show accurate counts that match the filtered lists")
def test_tc246_tiles_match_lists(logged_in_admin_sessions_page: AdminSessionsPage,
                                 dashboard_tiles_data: SessionData):
    """
    Given I am on Session Management
    Then  Total = Live Now + Stale + Ended and Total equals the rows of the All list
    And   Unique Users equals the distinct usernames on every page of the All list
    And   each status tile's list has as many sessions as the tile, all with that status badge

    AIO: KAN-TC-246 | KAN-32 AC-2 | data: {dashboard_tiles_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Read the five tiles"):
        tiles = _tiles(sp)
        unique = sp.get_unique_users_count()
        allure.attach(f"{tiles} unique={unique}", name="tiles")

    with allure.step("Verify Total = Live Now + Stale + Ended"):
        assert tiles["all"] == tiles["live"] + tiles["stale"] + tiles["ended"], tiles

    with allure.step("Read every page of the All list"):
        rows = sp.all_rows("all")

    with allure.step("Verify Total and Unique Users against the list"):
        assert len(rows) == tiles["all"]
        assert len({r["username"] for r in rows}) == unique

    for type_ in ("ended", "stale", "live"):
        with allure.step(f"Click the {F.TILE_LABELS[type_]} tile and verify its list"):
            sp.open()
            sp.filter_by_chip(type_)
            assert sp.range_total() == tiles[type_], f"{type_}: list {sp.range_total()} vs tile {tiles[type_]}"
            badges = {r["status"] for r in sp.rows_data()}
            assert badges <= {F.STATUS_BADGE[type_]}, f"{type_} list shows badges {badges}"


# ---------------------------------------------------------------------------
# TC-247  All list
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-247")
@allure.story(STORY)
@allure.title("TC-247: The All list shows every session, newest login first, 20 per page")
def test_tc247_all_list(logged_in_admin_sessions_page: AdminSessionsPage, all_tab_data: SessionData):
    """
    Given more than 20 sessions exist
    Then  the All tab and Total tile are highlighted, the heading and range line show page 1 of P
    And   the columns are as specified and 20 rows are listed newest login first, every column filled
    When  I click ›
    Then  rows 21–40 continue the order and ‹ appears

    AIO: KAN-TC-247 | KAN-32 AC-3 | data: {all_tab_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    total = sp.get_stat_chip_count("all")
    pages = _pages(total)
    if total <= F.PAGE_SIZE:
        pytest.skip(f"Needs more than {F.PAGE_SIZE} sessions (dev has {total}).")

    with allure.step("Verify the All tab, heading and range line"):
        expect(sp.active_filter_tab).to_have_text("All")
        expect(sp.selected_stat_chip).to_contain_text("Total")
        expect(sp.page_title).to_have_text(f"{F.HEADING} · Page 1 of {pages}")
        expect(sp.pagination_info).to_have_text(_range_re(1, F.PAGE_SIZE, total, 1, pages))

    with allure.step("Verify the column headers"):
        assert sp.table_headers.evaluate_all("els => els.map(e => e.textContent.trim())") == list(F.COLUMNS)

    with allure.step("Verify the 20 rows"):
        rows = sp.rows_data()
        assert len(rows) == F.PAGE_SIZE
        logins = [sp.parse_time(r["login"]) for r in rows]
        assert logins == sorted(logins, reverse=True), "Not newest login first"
        for r in rows:
            assert r["agency"] and r["username"] and r["ip"] and r["ping"] and r["duration"], r
            if r["killable"]:
                assert r["end"] in F.OPEN_END and r["reason"] == "—", r
            else:
                sp.parse_time(r["end"])
                assert r["reason"] not in ("", "—") and r["action"] == "—", r

    with allure.step("Click › and verify page 2"):
        sp.go_to_next_page()
        expect(sp.page).to_have_url(re.compile(r"page=2"))
        rows2 = sp.rows_data()
        assert rows2[0]["num"] == str(F.PAGE_SIZE + 1)
        assert sp.parse_time(rows2[0]["login"]) <= logins[-1]
        expect(sp.page_title).to_have_text(f"{F.HEADING} · Page 2 of {pages}")
        expect(sp.pagination.locator("a", has_text="‹")).to_be_visible()


# ---------------------------------------------------------------------------
# TC-248  Status tabs
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-248")
@allure.story(STORY)
@allure.title("TC-248: Live, Stale and Ended tabs list only sessions of that status")
def test_tc248_status_tabs(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given sessions of at least two statuses exist
    When  I click the Ended, Stale and Live tabs (and the Ended tile)
    Then  each URL has ?type=…, the tab and tile are highlighted, only rows with that badge are listed,
          the range line equals the tile and page 2 keeps the filter

    AIO: KAN-TC-248 | KAN-32 AC-4
    """
    sp = logged_in_admin_sessions_page
    tiles = _tiles(sp)

    def check(type_):
        expect(sp.page).to_have_url(re.compile(rf"type={type_}"))
        expect(sp.active_filter_tab).to_have_text(F.TAB_LABELS[type_])
        expect(sp.selected_stat_chip).to_contain_text(F.TILE_LABELS[type_])
        if tiles[type_] == 0:
            expect(sp.empty_list).to_be_visible()
            return
        assert sp.range_total() == tiles[type_]
        rows = sp.rows_data()
        assert {r["status"] for r in rows} == {F.STATUS_BADGE[type_]}, {r["status"] for r in rows}
        if type_ == "ended":
            assert not any(r["killable"] for r in rows)

    with allure.step("Click the 'Ended' tab"):
        sp.filter_by_tab("ended")
        check("ended")

    with allure.step("Click page 2 of a list with more than 20 rows"):
        type_ = "ended" if tiles["ended"] > F.PAGE_SIZE else "live"
        sp.filter_by_tab(type_)
        if tiles[type_] > F.PAGE_SIZE:
            sp.go_to_next_page()
            expect(sp.page).to_have_url(re.compile(rf"type={type_}.*page=2"))
            expect(sp.active_filter_tab).to_have_text(F.TAB_LABELS[type_])

    with allure.step("Click the Ended tile"):
        sp.open()
        sp.filter_by_chip("ended")
        check("ended")

    with allure.step("Click the 'Stale' tab"):
        sp.filter_by_tab("stale")
        check("stale")

    with allure.step("Click the 'Live' tab"):
        sp.filter_by_tab("live")
        check("live")


# ---------------------------------------------------------------------------
# TC-249  Kill one session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-249")
@allure.story(STORY)
@allure.title("TC-249: Kill ends one open session after confirmation and records it")
def test_tc249_kill_one_session(logged_in_admin_sessions_page: AdminSessionsPage, agency_session,
                                kill_single_session_data: SessionData):
    """
    Given an agency user is logged in in a second browser
    When  I click Kill on their session and Cancel "Terminate this session?"
    Then  nothing changes
    When  I click Kill again and OK
    Then  the session is Ended now with a killed reason and no Kill button, the tiles and Kill All count
          move by one, and the Audit log records the kill

    AIO: KAN-TC-249 | KAN-32 AC-7 | data: {kill_single_session_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    data = kill_single_session_data

    with allure.step("Open an agency session in a second browser"):
        handle = agency_session()
        target = _own_open_row(sp, handle.username)
        sid = target["session_id"]
        tiles, n = _tiles(sp), _kill_all_n(sp)
        allure.attach(f"session {sid}: {target}\ntiles {tiles}, Kill All {n}", name="before")

    with allure.step("Click Kill and Cancel the prompt"):
        assert sp.kill_row(sp.row_by_session_id(sid), action="dismiss") == data.expected_dialog_fragment
        expect(sp.row_by_session_id(sid)).to_have_count(1)

    with allure.step("Click Kill and OK the prompt"):
        assert sp.kill_row(sp.row_by_session_id(sid), action="accept") == data.expected_dialog_fragment
        expect(sp.row_by_session_id(sid)).to_have_count(0)

    with allure.step("Verify the row is Ended now"):
        row = next(r for r in sp.rows_data() if r["username"] == handle.username)
        allure.attach(str(row), name="killed row")
        assert row["status"] == data.expected_status and row["action"] == "—" and not row["killable"], row
        assert abs(sp.parse_time(row["end"]) - F.now_ist()) <= timedelta(minutes=F.DURATION_TOLERANCE_MINUTES)

    with allure.step("Verify the tiles and Kill All count"):
        after = _tiles(sp)
        assert after["ended"] == tiles["ended"] + 1, (tiles, after)
        assert after["live"] + after["stale"] == tiles["live"] + tiles["stale"] - 1, (tiles, after)
        assert _kill_all_n(sp) == n - 1

    with allure.step("Verify the reason shows it was killed"):
        assert data.expected_reason in row["reason"].lower(), row["reason"]

    with allure.step("Verify the Audit log records the kill"):
        audit = AdminAuditLogPage(sp.page)
        audit.open(date_f="today")
        expect(audit.log_feed).to_contain_text(re.compile("kill", re.I))
        expect(audit.log_feed).to_contain_text(handle.username)


# ---------------------------------------------------------------------------
# TC-250  Killed agency user is logged out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-250")
@allure.story(STORY)
@allure.title("TC-250: An agency user whose session is killed is logged out on their next action")
def test_tc250_killed_user_logged_out(logged_in_admin_sessions_page: AdminSessionsPage, agency_session,
                                      kill_redirect_data: SessionData):
    """
    Given an agency user is logged in in a second browser
    When  an officer kills their session and the agency user reloads
    Then  the agency login page opens; Back shows no agency page
    And   a message says the session was ended by an administrator

    AIO: KAN-TC-250 | KAN-32 AC-8 | data: {kill_redirect_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    data = kill_redirect_data

    with allure.step("Open an agency session in a second browser"):
        handle = agency_session()
        agency = handle.page
        expect(agency).not_to_have_url(re.compile(r"login"))
        sid = _own_open_row(sp, handle.username)["session_id"]

    with allure.step("Kill the session from Session Management"):
        sp.kill_row(sp.row_by_session_id(sid), action="accept")

    with allure.step("Reload the agency page"):
        agency.reload()
        agency.wait_for_load_state()
        expect(agency).to_have_url(re.compile(r"login"))
        login_text = agency.locator("body").inner_text()

    with allure.step("Press Back"):
        agency.go_back()
        agency.wait_for_load_state()
        agency.reload()
        expect(agency).to_have_url(re.compile(r"login"))

    with allure.step("Verify the login page said the session was ended by an administrator"):
        allure.attach(login_text[:1500], name="agency login page")
        assert data.expected_error in login_text.lower(), "No message about the administrator ending the session"


# ---------------------------------------------------------------------------
# TC-251  Kill All Active  (opt-in)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-251")
@allure.story(STORY)
@allure.title("TC-251: Kill All Active ends every open session")
def test_tc251_kill_all(kill_all_allowed, logged_in_admin_sessions_page: AdminSessionsPage, agency_session,
                        kill_all_confirmation_data: SessionData):
    """
    Given two agency users are logged in in other browsers
    When  I click "Kill All Active (N)" and OK "Kill ALL active sessions now?"
    Then  every open session is Ended, Live Now and Stale show 0, Ended rises by N, the button shows (0),
          the agency users are logged out and the Audit log records the bulk kill

    AIO: KAN-TC-251 | KAN-32 AC-9 | data: {kill_all_confirmation_data.scenario_label} | RUN_KILL_ALL_TESTS=true
    """
    sp = logged_in_admin_sessions_page
    data = kill_all_confirmation_data

    with allure.step("Open two agency sessions in other browsers"):
        handles = [agency_session(), agency_session()]
        sp.open()
        tiles, n = _tiles(sp), _kill_all_n(sp)
        allure.attach(f"tiles {tiles}, Kill All {n}", name="before")
        assert n == tiles["live"] + tiles["stale"] and n >= 2

    with allure.step("Click Kill All Active and OK the prompt"):
        assert sp.kill_all(action="accept") == data.expected_dialog_fragment

    with allure.step("Verify every open session is Ended"):
        after = _tiles(sp)
        assert (after["live"], after["stale"]) == (0, 0), after
        assert after["ended"] == tiles["ended"] + n, (tiles, after)
        expect(sp.killable_rows).to_have_count(0)

    with allure.step("Verify the agency users are logged out"):
        for h in handles:
            h.page.reload()
            expect(h.page).to_have_url(re.compile(r"login"))

    with allure.step("Verify the Audit log records the bulk kill"):
        audit = AdminAuditLogPage(sp.page)
        audit.open(date_f="today")
        expect(audit.log_feed).to_contain_text(re.compile("kill", re.I))


# ---------------------------------------------------------------------------
# TC-252  Kill All — Cancel
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-252")
@allure.story(STORY)
@allure.title("TC-252: Kill All Active asks for confirmation; Cancel changes nothing")
def test_tc252_kill_all_cancel(logged_in_admin_sessions_page: AdminSessionsPage,
                               kill_all_confirmation_data: SessionData):
    """
    Given at least one session is open
    When  I click "Kill All Active (N)" and Cancel "Kill ALL active sessions now?"
    Then  the page does not reload and the tiles, N and the open sessions are unchanged

    AIO: KAN-TC-252 | KAN-32 AC-9 | data: {kill_all_confirmation_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    data = kill_all_confirmation_data
    if sp.killable_rows.count() == 0:
        pytest.skip("No open session on page 1 — nothing for Kill All to end.")
    tiles, n, url = _tiles(sp), _kill_all_n(sp), sp.page.url
    open_ids = [r["session_id"] for r in sp.rows_data() if r["killable"]]

    with allure.step("Click Kill All Active and Cancel the prompt"):
        assert sp.kill_all(action="dismiss") == data.expected_dialog_fragment

    with allure.step("Verify nothing changed"):
        assert sp.page.url == url
        sp.open()
        assert _tiles(sp) == tiles and _kill_all_n(sp) == n
        for sid in open_ids:
            expect(sp.row_by_session_id(sid)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-253  Search
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-253")
@allure.story(STORY)
@allure.title("TC-253: Search lists the sessions matching an agency name, username or IP")
def test_tc253_search(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given a username, part of an agency name and a Login IP read from the list
    When  I search for each (the agency part in a different case)
    Then  only matching sessions are listed, the box keeps the text and the URL has q=
    And   searching on the Ended tab keeps the tab, page 2 keeps the search, and an empty search lists all

    AIO: KAN-TC-253 | KAN-32 AC-6
    """
    sp = logged_in_admin_sessions_page
    total = sp.get_stat_chip_count("all")
    first = sp.rows_data()[0]
    username, ip = first["username"], first["ip"]
    agency_part = first["agency"].split()[0].lower()
    allure.attach(f"username {username}, agency part {agency_part}, ip {ip}", name="search terms")

    def matches(field, value, exact=True):
        rows = sp.rows_data()
        assert rows, f"No sessions listed for '{value}'"
        bad = [r[field] for r in rows if (r[field] != value if exact else value not in r[field].lower())]
        assert not bad, f"Rows not matching '{value}': {bad[:5]}"

    with allure.step(f"Search for the username '{username}'"):
        sp.search(username)
        expect(sp.page).to_have_url(re.compile(rf"q={re.escape(username)}"))
        expect(sp.search_input).to_have_value(username)
        matches("username", username)

    with allure.step(f"Search for '{agency_part}'"):
        sp.search(agency_part)
        matches("agency", agency_part, exact=False)

    with allure.step(f"Search for the IP '{ip}'"):
        sp.search(ip)
        matches("ip", ip)
        many = sp.range_total() > F.PAGE_SIZE

    with allure.step("Search on the Ended tab"):
        sp.open()
        sp.filter_by_tab("ended")
        ended_user = sp.rows_data()[0]["username"]
        sp.search(ended_user)
        expect(sp.active_filter_tab).to_have_text("Ended")
        matches("username", ended_user)
        assert {r["status"] for r in sp.rows_data()} == {"Ended"}

    if many:
        with allure.step("Open page 2 of the IP search"):
            sp.open_with(f"type=all&q={ip}")
            expect(sp.page.locator(".pag a", has_text="›")).to_have_attribute("href", re.compile(r"q="))
            sp.go_to_next_page()
            matches("ip", ip)

    with allure.step("Clear the box and click Search"):
        sp.open()
        sp.search("")
        assert sp.range_total() == total


# ---------------------------------------------------------------------------
# TC-254  Duration, Logout / End and Reason
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-254")
@allure.story(STORY)
@allure.title("TC-254: Duration, Logout / End and Reason are shown correctly for open and ended sessions")
def test_tc254_duration_end_reason(logged_in_admin_sessions_page: AdminSessionsPage,
                                   stale_session_data: SessionData):
    """
    Given an open session logged in more than a day ago and an ended session
    Then  the open one shows the time since login, — in Logout / End and Reason, and a Kill button
    And   the ended one shows Login Time to Logout / End, a reason and — in Action

    AIO: KAN-TC-254 | KAN-32 Session Table Columns, EC-1 | data: {stale_session_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    now = F.now_ist()
    tolerance = timedelta(minutes=F.DURATION_TOLERANCE_MINUTES)
    rows = sp.all_rows("all")
    old_open = [r for r in rows if r["killable"] and now - sp.parse_time(r["login"]) > timedelta(hours=F.OPEN_FOR_HOURS)]
    ended = [r for r in rows if r["status"] == "Ended" and r["end"] != "—"]
    if not old_open or not ended:
        pytest.skip("Needs an open session older than a day and an ended session.")

    with allure.step("Verify the open session's row"):
        r = old_open[0]
        allure.attach(str(r), name="open row")
        assert abs(F.parse_duration(r["duration"]) - (now - sp.parse_time(r["login"]))) <= tolerance, r
        assert r["end"] in F.OPEN_END and r["reason"] == "—" and r["killable"], r

    with allure.step("Verify the ended sessions' rows"):
        for r in ended:
            spent = sp.parse_time(r["end"]) - sp.parse_time(r["login"])
            assert abs(F.parse_duration(r["duration"]) - spent) <= tolerance, r
            assert r["reason"] in F.END_REASONS and r["action"] == "—", r


# ---------------------------------------------------------------------------
# TC-255  No ping
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-255")
@allure.story(STORY)
@allure.title("TC-255: Last Ping shows \"No ping\" for a session that never sent a heartbeat")
def test_tc255_no_ping(logged_in_admin_sessions_page: AdminSessionsPage, no_ping_data: SessionData):
    """
    Given sessions that never sent a heartbeat
    Then  Last Ping shows "No ping" and the other columns are filled
    And   the open ones older than a day are badged Stale and listed on the Stale tab

    AIO: KAN-TC-255 | KAN-32 EC-1 | data: {no_ping_data.scenario_label}
    """
    sp = logged_in_admin_sessions_page
    now = F.now_ist()
    rows = sp.all_rows("all")
    no_ping = [r for r in rows if r["ping"] == no_ping_data.expected_reason]
    if not no_ping:
        pytest.skip("No session without a heartbeat.")

    with allure.step("Verify the No ping rows are complete"):
        for r in no_ping:
            assert all(r[k] for k in ("status", "agency", "username", "ip", "login", "end", "duration", "reason")), r

    old = [r for r in no_ping if r["killable"] and now - sp.parse_time(r["login"]) > timedelta(hours=F.OPEN_FOR_HOURS)]
    if old:
        with allure.step(f"Verify the {len(old)} open No ping sessions older than a day are Stale"):
            assert {r["status"] for r in old} == {no_ping_data.expected_status}, {r["status"] for r in old}
            stale_ids = {r["session_id"] for r in sp.all_rows("stale")}
            missing = [r["session_id"] for r in old if r["session_id"] not in stale_ids]
            allure.attach(f"{len(missing)} of {len(old)} missing from the Stale tab", name="stale tab")
            assert not missing, f"{len(missing)} of {len(old)} are not on the Stale tab"


# ---------------------------------------------------------------------------
# TC-256  No open sessions  (opt-in)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-256")
@allure.story(STORY)
@allure.title("TC-256: With no open sessions, Kill All Active (0) is disabled or hidden")
def test_tc256_no_open_sessions(kill_all_allowed, logged_in_admin_sessions_page: AdminSessionsPage,
                                kill_all_disabled_data: SessionData):
    """
    Given no agency session is open (Kill All is used first if needed)
    Then  Live Now and Stale show 0, "Kill All Active (0)" is disabled or hidden,
          and the Live and Stale tabs show "No sessions found."

    AIO: KAN-TC-256 | KAN-32 EC-5 | data: {kill_all_disabled_data.scenario_label} | RUN_KILL_ALL_TESTS=true
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Make sure no session is open"):
        if _kill_all_n(sp) > 0:
            sp.kill_all(action="accept")
        tiles = _tiles(sp)
        assert (tiles["live"], tiles["stale"]) == (0, 0), tiles

    with allure.step("Verify the Live and Stale tabs are empty"):
        for type_ in ("live", "stale"):
            sp.filter_by_tab(type_)
            expect(sp.empty_list).to_have_text(kill_all_disabled_data.expected_error)

    with allure.step("Verify Kill All Active (0) is disabled or hidden"):
        assert not sp.is_kill_all_available(), "Kill All Active (0) is still enabled"


# ---------------------------------------------------------------------------
# TC-715  Page loads from the sidebar
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-715")
@allure.story(STORY)
@allure.title("TC-715: Session Management page loads from the sidebar")
def test_tc715_page_loads_from_sidebar(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on the Officer Console dashboard
    When  I click "Active sessions" under Administration
    Then  Session Management opens with the link highlighted, the heading and clock, five tiles (Total
          selected), the tabs (All selected), the search box, Kill All Active (N) and the list

    AIO: KAN-TC-715 | KAN-32 AC-1
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Click 'Active sessions' in the sidebar of the dashboard"):
        sp.page.goto(ADMIN_DASHBOARD_URL)
        sp.sidebar.go_to_sessions()
        expect(sp.page).to_have_url(SESSIONS_URL)
        expect(sp.sidebar.active_item).to_contain_text("Active sessions")

    with allure.step("Verify the header"):
        expect(sp.page_title).to_have_text(re.compile(rf"^{F.HEADING} · Page 1 of \d+$"))
        expect(sp.clock).to_have_text(re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4} · \d{2}:\d{2}$"))

    with allure.step("Verify the tiles, tabs, search and Kill All"):
        expect(sp.stat_tiles).to_have_count(5)
        expect(sp.selected_stat_chip).to_contain_text("Total")
        expect(sp.unique_users_tile).to_contain_text("Unique Users")
        expect(sp.filter_tabs).to_have_text(list(F.TAB_LABELS.values()))
        expect(sp.active_filter_tab).to_have_text("All")
        expect(sp.search_input).to_have_attribute("placeholder", F.SEARCH_PLACEHOLDER)
        expect(sp.search_button).to_be_visible()
        expect(sp.kill_all_button).to_have_text(re.compile(r"^\s*Kill All Active \(\d+\)\s*$"))

    with allure.step("Verify the list"):
        expect(sp.sessions_table).to_be_visible()
        expect(sp.pagination_info).to_have_text(re.compile(r"of \d+ sessions"))


# ---------------------------------------------------------------------------
# TC-717  Needs a session
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-717")
@allure.story(STORY)
@allure.title("TC-717: Session Management needs an admin session")
def test_tc717_needs_a_session(no_admin_session, admin_sessions_page: AdminSessionsPage,
                               admin_login_page: AdminLoginPage):
    """
    Given no officer is logged in in this browser
    When  I open the Session Management URL
    Then  the Admin Login page opens with "Please log in to continue."

    AIO: KAN-TC-717 | KAN-32 AC-10
    """
    with allure.step("Open the page without a session"):
        admin_sessions_page.open()

    with allure.step("Verify the Admin Login page"):
        expect(admin_login_page.not_logged_in_message).to_have_text(AdminLoginPage.NOT_LOGGED_IN_MESSAGE)
        expect(admin_sessions_page.sessions_table).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-718  Search text with quotes or HTML
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-718")
@allure.story(STORY)
@allure.title("TC-718: Search text with quotes or HTML is shown as typed")
def test_tc718_special_search_text(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on Session Management
    When  I search for O'Brien and for <b>x</b>
    Then  the box shows each exactly as typed, "No sessions found." is shown and no HTML runs

    AIO: KAN-TC-718 | KAN-32 EC-4
    """
    sp = logged_in_admin_sessions_page
    for text in F.SPECIAL_SEARCHES:
        with allure.step(f"Search for {text}"):
            sp.search(text)
            expect(sp.empty_list).to_be_visible()
            expect(sp.page.locator("b", has_text=re.compile(r"^x$"))).to_have_count(0)
            expect(sp.search_input).to_have_value(text)


# ---------------------------------------------------------------------------
# TC-719  Page number beyond the last / not a number
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-719")
@allure.story(STORY)
@allure.title("TC-719: A page number beyond the last page or not a number is handled")
def test_tc719_bad_page_numbers(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on Session Management
    When  I open ?page=0 and ?page=abc
    Then  page 1 is shown with "1–20 of N sessions · Page 1 of P"
    When  I open ?page=999
    Then  the last page is shown with a correct range line — never "Page 999 of P"

    AIO: KAN-TC-719 | KAN-32 EC-7
    """
    sp = logged_in_admin_sessions_page
    total = sp.get_stat_chip_count("all")
    pages = _pages(total)

    for value in F.BAD_PAGES:
        with allure.step(f"Open ?page={value}"):
            sp.open_with(f"page={value}")
            expect(sp.pagination_info).to_have_text(_range_re(1, min(F.PAGE_SIZE, total), total, 1, pages))

    with allure.step(f"Open ?page={F.PAGE_BEYOND_LAST}"):
        sp.open_with(f"page={F.PAGE_BEYOND_LAST}")
        allure.attach(sp.pagination_info.inner_text() if sp.pagination_info.count() else "(none)", name="range line")
        expect(sp.page_title).to_have_text(f"{F.HEADING} · Page {pages} of {pages}")
        expect(sp.pagination_info).to_have_text(
            _range_re((pages - 1) * F.PAGE_SIZE + 1, total, total, pages, pages))


# ---------------------------------------------------------------------------
# TC-720  Unknown status filter
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-720")
@allure.story(STORY)
@allure.title("TC-720: An unknown status filter shows the All list")
def test_tc720_unknown_filter(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on Session Management
    When  I open ?type=bogus
    Then  all sessions are listed with the All tab and the Total tile highlighted

    AIO: KAN-TC-720 | KAN-32 EC-8
    """
    sp = logged_in_admin_sessions_page
    total = sp.get_stat_chip_count("all")

    with allure.step(f"Open ?type={F.UNKNOWN_TYPE}"):
        sp.open_with(f"type={F.UNKNOWN_TYPE}")

    with allure.step("Verify the All list"):
        assert sp.range_total() == total
        expect(sp.active_filter_tab).to_have_text("All")
        expect(sp.selected_stat_chip).to_contain_text("Total")


# ---------------------------------------------------------------------------
# TC-721  Clock in IST
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-721")
@allure.story(STORY)
@allure.title("TC-721: Page clock shows the current IST time")
def test_tc721_clock_in_ist(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on Session Management
    Then  the date and time next to the heading is the current IST time (within 2 minutes)

    AIO: KAN-TC-721 | KAN-32 EC-9
    """
    from datetime import datetime
    sp = logged_in_admin_sessions_page
    shown = sp.clock.inner_text().strip()
    now = F.now_ist()
    allure.attach(f"page: {shown}\nIST:  {now:%d %b %Y · %H:%M}", name="clock")

    with allure.step(f"Verify '{shown}' is within 2 minutes of IST"):
        assert abs(datetime.strptime(shown, F.CLOCK_FORMAT) - now) <= timedelta(minutes=F.CLOCK_TOLERANCE_MINUTES)


# ---------------------------------------------------------------------------
# TC-722  Page title
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-722")
@allure.story(STORY)
@allure.title("TC-722: Page title matches the other Officer Console pages")
def test_tc722_page_title(logged_in_admin_sessions_page: AdminSessionsPage):
    """
    Given I am on Session Management
    Then  the browser tab title is "Active Sessions — MPPA Officer Console"

    AIO: KAN-TC-722 | KAN-32 EC-10
    """
    with allure.step(f"Verify the title is '{F.EXPECTED_TITLE}'"):
        expect(logged_in_admin_sessions_page.page).to_have_title(F.EXPECTED_TITLE)
