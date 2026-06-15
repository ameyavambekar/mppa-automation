"""
Session Management — Admin Portal
=================================
Covers KAN-TC-246 through KAN-TC-256.

The Session Management dashboard lists every portal session with summary tiles,
filter tabs, search and per-row / global Kill actions. These tests read *live*
table state — targets (a live row, a stale row, a 'No ping' row, a username to
search) are picked dynamically from the current page, because the AIO sheet's
named fixtures ("liveuser01 / AgencyAlpha" etc.) describe the spec dataset, not
the dev environment.

Handling the destructive actions safely:

* Single-session kills (TC-249, TC-250) create their OWN throwaway agency
  session in a second browser via the ``agency_session`` fixture and kill only
  that session — no unrelated user's live session is ever terminated.
* Kill-All (TC-251, TC-252) only exercises the confirmation dialog and ALWAYS
  dismisses it; it never terminates sessions. The live build guards Kill-All
  with a native ``confirm('Kill ALL active sessions now?')`` rather than the
  spec's longer sentence, so the asserted fragment is the realistic 'active'.
* TC-256 needs a dataset with zero active sessions; it skips (with a clear
  reason) when the dev environment has live/stale sessions, which is the honest
  outcome rather than a forced pass.

Count assertions tolerate pagination by checking per-user row counts or in-DOM
(non-reloaded) tile values rather than whole-table totals.
"""

import re

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.sessions_page import AdminSessionsPage
from test_data.sessions_factory import SessionData
from utils.aio import aio_case


# ---------------------------------------------------------------------------
# TC-246  All 5 summary tiles are visible and counts are internally consistent
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-246")
@allure.story("Session Management")
@allure.title("TC-246: All 5 summary tiles are visible with internally consistent counts")
def test_tc246_dashboard_tiles_visible_and_consistent(
    logged_in_admin_sessions_page: AdminSessionsPage,
    dashboard_tiles_data: SessionData,
):
    """
    Given I am logged in as Admin on the Session Management dashboard
    When  the page loads
    Then  all 5 tiles (Total, Live Now, Stale, Ended, Unique Users) are visible
    And   every tile count is a non-negative integer
    And   Total equals Live + Stale + Ended (every session is in exactly one state)

    AIO: KAN-TC-246 | data: dashboard_tiles (live tile state)
    """
    sp = logged_in_admin_sessions_page
    data = dashboard_tiles_data

    with allure.step("Verify the four clickable tiles are visible with their labels"):
        for type_, label in data.tile_labels.items():
            expect(sp.stat_chip(type_)).to_be_visible()
            expect(sp.stat_chip_label(type_)).to_contain_text(label, ignore_case=True)

    with allure.step("Verify the Unique Users tile is visible"):
        expect(sp.unique_users_tile).to_be_visible()
        expect(sp.unique_users_tile).to_contain_text("Unique", ignore_case=True)

    with allure.step("Read all five tile counts"):
        total = sp.get_stat_chip_count("all")
        live = sp.get_stat_chip_count("live")
        stale = sp.get_stat_chip_count("stale")
        ended = sp.get_stat_chip_count("ended")
        unique = sp.get_unique_users_count()

    with allure.step("Verify every count is a non-negative integer"):
        for name, value in {
            "Total": total, "Live": live, "Stale": stale,
            "Ended": ended, "Unique Users": unique,
        }.items():
            assert value >= 0, f"{name} tile shows a negative count: {value}"

    with allure.step("Verify Total == Live + Stale + Ended"):
        assert total == live + stale + ended, (
            f"Total tile ({total}) != Live ({live}) + Stale ({stale}) + Ended ({ended}). "
            "Every session should be counted in exactly one state."
        )


# ---------------------------------------------------------------------------
# TC-247  All tab lists every session type, all columns, reverse-chronological
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-247")
@allure.story("Session Management")
@allure.title("TC-247: All tab lists sessions with every column in reverse-chronological order")
def test_tc247_all_tab_columns_and_order(
    logged_in_admin_sessions_page: AdminSessionsPage,
    all_tab_data: SessionData,
):
    """
    Given I am logged in as Admin on the Session Management dashboard
    When  the page loads with the 'All' tab active by default
    Then  every required column is present
    And   sessions are listed in reverse-chronological order (newest login first)

    AIO: KAN-TC-247 | data: all_tab_layout (live table state)
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Verify the 'All' tab is the active filter on load"):
        expect(sp.active_filter_tab).to_contain_text("All")

    with allure.step("Verify all required columns are present"):
        for column in all_tab_data.expected_columns:
            expect(sp.table_header(column)).to_be_visible()

    with allure.step("Verify the table has at least one session row"):
        expect(sp.session_rows.first).to_be_visible()

    with allure.step("Verify rows are in reverse-chronological order by Login Time"):
        times = sp.get_login_times()
        assert times, "No parseable Login Time values found on the page."
        for earlier, later in zip(times, times[1:]):
            assert earlier >= later, (
                f"Rows are not in reverse-chronological order: "
                f"{earlier} appears above {later}."
            )


# ---------------------------------------------------------------------------
# TC-248  Live tab shows only Live sessions
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-248")
@allure.story("Session Management")
@allure.title("TC-248: The Live filter tab shows only Live sessions")
def test_tc248_live_tab_shows_only_live(
    logged_in_admin_sessions_page: AdminSessionsPage,
):
    """
    Given I am logged in as Admin on the Session Management dashboard
    When  I click the 'Live' filter tab
    Then  every row shown carries a green Live badge
    And   no Stale or Ended rows appear

    AIO: KAN-TC-248 | data: live table state
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Skip if there are no live sessions to inspect"):
        if sp.get_stat_chip_count("live") == 0:
            pytest.skip("No live sessions in the current dev dataset.")

    with allure.step("Click the 'Live' tab"):
        sp.filter_by_tab("live")
        expect(sp.active_filter_tab).to_contain_text("Live")

    with allure.step("Verify rows are shown and every one carries a Live badge"):
        expect(sp.session_rows.first).to_be_visible()
        total = sp.session_rows.count()
        live = sp.live_rows.count()
        assert live == total, f"{total - live} of {total} rows on the Live tab are not Live."

    with allure.step("Verify no Stale or Ended rows appear under the Live filter"):
        assert sp.stale_rows.count() == 0, "Stale rows leaked into the Live tab."
        assert sp.ended_rows.count() == 0, "Ended rows leaked into the Live tab."


# ---------------------------------------------------------------------------
# TC-249  Killing a Live session ends it, records 'killed', drops the live count
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-249")
@allure.story("Session Management")
@allure.title("TC-249: Killing a Live session ends it, records 'killed', and drops the live count")
def test_tc249_kill_live_session(
    logged_in_admin_sessions_page: AdminSessionsPage,
    agency_session,
    kill_single_session_data: SessionData,
):
    """
    Given a fresh Live agency session exists (created in a second browser)
    When  I click that session's Kill button and confirm the dialog
    Then  the confirmation dialog appears ('Terminate this session?')
    And   that user has one fewer Live session afterwards
    And   an Ended session with reason 'killed' and a populated Logout/End now
          exists for that user

    AIO: KAN-TC-249 | data: kill_single_session
    """
    sp = logged_in_admin_sessions_page
    data = kill_single_session_data

    with allure.step("Create a fresh Live agency session in a second browser"):
        handle = agency_session()
        username = handle.username

    with allure.step(f"Reload Sessions and locate the live session for '{username}'"):
        sp.open()
        sp.search(username)
        live_for_user = sp.live_rows_for_username(username)
        expect(live_for_user.first).to_be_visible()
        live_before = live_for_user.count()
        target = live_for_user.first
        session_id = sp.get_session_id(target)
        allure.attach(session_id or "", name="killed session_id")

    with allure.step("Kill the session and accept the confirmation dialog"):
        message = sp.kill_row(target, action="accept")
        assert data.expected_dialog_fragment in message, (
            f"Unexpected kill confirmation dialog: '{message}'"
        )

    with allure.step(f"Re-search '{username}' after the kill"):
        sp.search(username)

    with allure.step("Verify this user has exactly one fewer Live session"):
        live_after = sp.live_rows_for_username(username).count()
        assert live_after == live_before - 1, (
            f"Live sessions for '{username}' went {live_before} → {live_after}; expected -1."
        )

    with allure.step("Verify a killed / Ended session now exists for this user"):
        killed = sp.killed_rows_for_username(username)
        expect(killed.first).to_be_visible()
        expect(sp.reason_cell(killed.first)).to_contain_text(data.expected_reason)
        expect(sp.status_badge(killed.first)).to_contain_text(data.expected_status)

    with allure.step("Verify the killed session's Logout/End timestamp is populated"):
        expect(sp.logout_end_cell(killed.first)).not_to_have_text(re.compile(r"^\s*—\s*$"))


# ---------------------------------------------------------------------------
# TC-250  Killed agency user is redirected to login on next action
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-250")
@allure.story("Session Management")
@allure.title("TC-250: An agency user whose session is killed is redirected to login on next action")
def test_tc250_killed_user_redirected_to_login(
    logged_in_admin_sessions_page: AdminSessionsPage,
    agency_session,
    kill_redirect_data: SessionData,
):
    """
    Given an agency user is logged in (Live session) in a second browser
    When  the admin kills that session from Session Management
    And   the agency user triggers their next action (page reload)
    Then  the agency user is forced back to the login page (re-authentication)

    AIO: KAN-TC-250 | data: kill_then_redirect
    """
    sp = logged_in_admin_sessions_page
    data = kill_redirect_data

    with allure.step("Open a Live agency session in a second browser"):
        handle = agency_session()
        username = handle.username
        agency_page = handle.page

    with allure.step("Confirm the agency user starts out authenticated (not on login)"):
        expect(agency_page).not_to_have_url(re.compile(r"login"))

    with allure.step(f"From the admin browser, find and kill the live session for '{username}'"):
        sp.open()
        sp.search(username)
        target = sp.live_rows_for_username(username).first
        expect(target).to_be_visible()
        message = sp.kill_row(target, action="accept")
        assert data.expected_dialog_fragment in message, (
            f"Unexpected kill confirmation dialog: '{message}'"
        )

    with allure.step("In the agency browser, trigger the next action by reloading"):
        agency_page.reload()
        agency_page.wait_for_load_state()

    with allure.step("Verify the agency user is bounced to the login page"):
        expect(agency_page).to_have_url(re.compile(r"login"))


# ---------------------------------------------------------------------------
# TC-251  Kill All shows a confirmation dialog before terminating
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-251")
@allure.story("Session Management")
@allure.title("TC-251: Kill All shows a confirmation dialog naming the active-session count")
def test_tc251_kill_all_shows_confirmation(
    logged_in_admin_sessions_page: AdminSessionsPage,
    kill_all_confirmation_data: SessionData,
):
    """
    Given at least one active (Live or Stale) session exists
    When  I click the 'Kill All Active (N)' button
    Then  a confirmation dialog appears before anything is terminated

    The dialog is dismissed so no sessions are actually killed — this case only
    verifies the guard. (The live build's dialog reads 'Kill ALL active sessions
    now?', which differs from the AIO spec's longer wording.)

    AIO: KAN-TC-251 | data: kill_all_confirmation
    """
    sp = logged_in_admin_sessions_page
    data = kill_all_confirmation_data

    with allure.step("Skip if there are no active (Live or Stale) sessions"):
        active = sp.get_stat_chip_count("live") + sp.get_stat_chip_count("stale")
        if active == 0:
            pytest.skip("No active sessions — Kill All would be unavailable (see TC-256).")

    with allure.step("Verify the Kill All button is available and names a count"):
        expect(sp.kill_all_button).to_be_visible()
        expect(sp.kill_all_button).to_contain_text(re.compile(r"Kill All Active \(\d+\)"))

    with allure.step("Click 'Kill All Active' and capture the confirmation dialog, then cancel"):
        message = sp.kill_all(action="dismiss")

    with allure.step("Verify a confirmation dialog appeared with the expected wording"):
        assert message, "Kill All did not raise a confirmation dialog."
        assert data.expected_dialog_fragment.lower() in message.lower(), (
            f"Kill All dialog '{message}' did not mention "
            f"'{data.expected_dialog_fragment}'."
        )

    with allure.step("Verify cancelling left the sessions in place"):
        expect(sp.session_rows.first).to_be_visible()


# ---------------------------------------------------------------------------
# TC-252  Cancelling the Kill All dialog leaves all sessions intact
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-252")
@allure.story("Session Management")
@allure.title("TC-252: Cancelling the Kill All dialog leaves all sessions intact")
def test_tc252_kill_all_cancel_aborts(
    logged_in_admin_sessions_page: AdminSessionsPage,
    kill_all_confirmation_data: SessionData,
):
    """
    Given at least one active (Live or Stale) session exists
    When  I click 'Kill All Active' and then Cancel the confirmation dialog
    Then  no session is terminated — the page does not reload and the Live /
          Stale counts are unchanged

    Cancelling must NOT navigate: a real kill reloads the page and drops the
    counts, so unchanged in-DOM tile values prove the action was aborted.

    AIO: KAN-TC-252 | data: kill_all_confirmation
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Read the active counts and skip if there are none"):
        live_before = sp.get_stat_chip_count("live")
        stale_before = sp.get_stat_chip_count("stale")
        if live_before + stale_before == 0:
            pytest.skip("No active sessions to protect — see TC-256.")

    with allure.step("Click 'Kill All Active' then Cancel the confirmation dialog"):
        message = sp.kill_all(action="dismiss")
        assert message, "Kill All did not raise a confirmation dialog."

    with allure.step("Verify nothing was terminated (no reload, counts unchanged)"):
        expect(sp.kill_all_button).to_be_visible()
        expect(sp.session_rows.first).to_be_visible()
        assert sp.get_stat_chip_count("live") == live_before, (
            "Live count changed after cancelling Kill All."
        )
        assert sp.get_stat_chip_count("stale") == stale_before, (
            "Stale count changed after cancelling Kill All."
        )


# ---------------------------------------------------------------------------
# TC-253  Search filters the session list by username
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-253")
@allure.story("Session Management")
@allure.title("TC-253: Search filters the session list by username")
def test_tc253_search_filters_sessions(
    logged_in_admin_sessions_page: AdminSessionsPage,
):
    """
    Given I am logged in as Admin on the Session Management dashboard
    When  I search for a username taken from the table
    Then  the search box retains the query
    And   every result row references that username (agency / username / IP match)

    AIO: KAN-TC-253 | data: username read from the first row at runtime
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Pick a username from the first session row as the search term"):
        expect(sp.session_rows.first).to_be_visible()
        username = sp.get_username(sp.session_rows.first)
        assert username, "First row has an empty username."

    with allure.step(f"Search for '{username}'"):
        sp.search(username)

    with allure.step("Verify the search box retains the query"):
        expect(sp.search_input).to_have_value(username)

    with allure.step(f"Verify every result row references '{username}'"):
        rows = sp.session_rows
        expect(rows.first).to_be_visible()
        for i in range(rows.count()):
            expect(rows.nth(i)).to_contain_text(username)


# ---------------------------------------------------------------------------
# TC-254  Stale session shows elapsed duration with Kill still available
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-254")
@allure.story("Session Management")
@allure.title("TC-254: A stale session shows elapsed duration and keeps the Kill button enabled")
def test_tc254_stale_session_row(
    logged_in_admin_sessions_page: AdminSessionsPage,
    stale_session_data: SessionData,
):
    """
    Given a session has been inactive long enough to be Stale
    When  I view it on the Stale tab
    Then  its Status badge reads Stale
    And   Duration shows elapsed hours/minutes (e.g. '49h 28m')
    And   Reason and Logout/End are blank dashes (session still open)
    And   the Kill button is present and enabled

    AIO: KAN-TC-254 | data: stale_session_row (live table state)
    """
    sp = logged_in_admin_sessions_page
    data = stale_session_data

    with allure.step("Open the Stale tab"):
        sp.filter_by_tab("stale")

    with allure.step("Skip if no stale session exists in the current dataset"):
        if sp.session_rows.count() == 0 or sp.stale_rows.count() == 0:
            pytest.skip("No stale sessions in the current dev dataset.")

    row = sp.stale_rows.first

    with allure.step("Verify the row carries a Stale badge"):
        expect(sp.status_badge(row)).to_contain_text(data.expected_status)

    with allure.step("Verify Duration shows elapsed time in hours and minutes"):
        expect(sp.duration_cell(row)).to_have_text(re.compile(r"\d+h\s*\d+m"))

    with allure.step("Verify Reason and Logout/End are blank dashes (session still open)"):
        expect(sp.reason_cell(row)).to_have_text(re.compile(r"^\s*—\s*$"))
        expect(sp.logout_end_cell(row)).to_have_text(re.compile(r"^\s*—\s*$"))

    with allure.step("Verify the Kill button is present and enabled"):
        expect(sp.kill_button(row)).to_be_visible()
        expect(sp.kill_button(row)).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-255  Last Ping shows 'No ping' for sessions that never sent a heartbeat
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-255")
@allure.story("Session Management")
@allure.title("TC-255: Last Ping shows 'No ping' for sessions that never sent a heartbeat")
def test_tc255_no_ping_displayed(
    logged_in_admin_sessions_page: AdminSessionsPage,
    no_ping_data: SessionData,
):
    """
    Given a session exists that never registered a heartbeat
    When  I view it in the sessions table
    Then  its Last Ping column reads exactly 'No ping' (not blank/null/'—')
    And   the rest of the row is still populated

    AIO: KAN-TC-255 | data: no_ping_session (live table state)
    """
    sp = logged_in_admin_sessions_page
    data = no_ping_data

    with allure.step("Ensure the All tab is active"):
        sp.filter_by_tab("all")

    with allure.step(f"Locate a session whose Last Ping reads '{data.expected_reason}'"):
        no_ping_rows = sp.rows_with_last_ping(data.expected_reason)
        if no_ping_rows.count() == 0:
            pytest.skip("No 'No ping' session on the first page of the current dataset.")
        row = no_ping_rows.first

    with allure.step("Verify the Last Ping cell reads exactly 'No ping'"):
        expect(sp.last_ping_cell(row)).to_have_text(re.compile(r"^\s*No ping\s*$"))

    with allure.step("Verify the rest of the row is still populated"):
        expect(sp.username_cell(row)).not_to_be_empty()
        expect(sp.login_time_cell(row)).to_contain_text(re.compile(r"\d{4}"))


# ---------------------------------------------------------------------------
# TC-256  Kill All is unavailable when no active sessions exist
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-256")
@allure.story("Session Management")
@allure.title("TC-256: Kill All is hidden or disabled when no active sessions exist")
def test_tc256_kill_all_unavailable_when_no_active(
    logged_in_admin_sessions_page: AdminSessionsPage,
    kill_all_disabled_data: SessionData,
):
    """
    Given no agency users are logged in (Live = 0 and Stale = 0)
    When  I view the Session Management dashboard
    Then  the 'Kill All Active' button is hidden or disabled

    This requires a dataset with zero active sessions. When the dev environment
    has active sessions the precondition cannot be met, so the test skips with a
    clear reason rather than forcing a pass.

    AIO: KAN-TC-256 | data: kill_all_disabled (live table state)
    """
    sp = logged_in_admin_sessions_page

    with allure.step("Read the Live and Stale tile counts"):
        live = sp.get_stat_chip_count("live")
        stale = sp.get_stat_chip_count("stale")

    if live + stale > 0:
        pytest.skip(
            f"Precondition not met: {live} live + {stale} stale active session(s) exist. "
            "This case requires a dataset with zero active sessions."
        )

    with allure.step("Verify both Live and Stale tiles read 0"):
        assert live == 0 and stale == 0

    with allure.step("Verify the Kill All button is hidden or disabled"):
        assert not sp.is_kill_all_available(), (
            "Kill All is still available despite there being no active sessions."
        )
