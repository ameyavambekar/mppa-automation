import re
from datetime import datetime

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE


class AdminSessionsPage(BasePage):
    """Admin — Session Management dashboard (/module/admin/sessions/index.php).

    Lists every portal session (agency logins) with five summary tiles
    (Total / Live Now / Stale / Ended / Unique Users), four filter tabs
    (All / Live / Stale / Ended applied via the ``?type=`` query param), a
    server-side search box (``?q=`` — agency, username or IP), a paginated
    table (20 rows/page) and per-row Kill plus a global Kill-All action.

    Rows are not individually keyed in the markup, so helpers locate rows by
    username (column 4), by status badge (``badge-live`` / ``badge-stale`` /
    ``badge-ended``) or by the ``session_id`` carried in a live/stale row's Kill
    form. Ended rows have no Kill form (the Action cell is an inert ``—``).

    Both Kill and Kill-All fire a native JS ``confirm()`` dialog — handled via
    the base-page dialog pattern. ``kill_all()`` defaults to *dismiss* so the
    destructive path is never taken by accident.
    """

    # ?type= values accepted by the tabs / tiles ('all' = the Total tile)
    TYPE_FILTERS = ("all", "live", "stale", "ended")

    # Table columns, in display order
    COLUMNS = (
        "#", "Status", "Agency", "Username", "Login IP", "Login Time",
        "Last Ping", "Logout / End", "Duration", "Reason", "Action",
    )

    # 0-based <td> index of each column within a row
    _COL_INDEX = {
        "status": 1, "agency": 2, "username": 3, "login_ip": 4,
        "login_time": 5, "last_ping": 6, "logout_end": 7, "duration": 8,
        "reason": 9, "action": 10,
    }

    _LOGIN_TIME_FMT = "%d %b %Y, %H:%M"

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Topbar / page header ──────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        # e.g. "👑 Super Admin"
        return self.page.locator("#adm-topbar .tb-badge")

    @property
    def page_title(self):
        # "🔌 Session Management · Page 1 of 19"
        return self.page.locator(".adm-page-title span").first

    # ── Summary tiles ─────────────────────────────────────────────────────────

    def stat_chip(self, type_: str):
        """A clickable summary tile. type_: one of TYPE_FILTERS."""
        return self.page.locator(f"a.sc[href*='type={type_}']")

    def stat_chip_count(self, type_: str):
        return self.stat_chip(type_).locator(".n")

    def stat_chip_label(self, type_: str):
        return self.stat_chip(type_).locator(".l")

    @property
    def unique_users_tile(self):
        """The Unique Users tile — a non-clickable ``div.sc`` (no ?type= link)."""
        return self.page.locator(".sc-row div.sc")

    @property
    def unique_users_count(self):
        return self.unique_users_tile.locator(".n")

    @property
    def selected_stat_chip(self):
        return self.page.locator("a.sc.sel")

    # ── Toolbar ───────────────────────────────────────────────────────────────

    @property
    def search_input(self):
        return self.page.locator("input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("button.btn-p", has_text="Search")

    def filter_tab(self, type_: str):
        """A filter tab pill. type_: one of TYPE_FILTERS."""
        return self.page.locator(f"a.ftab[href*='type={type_}']")

    @property
    def active_filter_tab(self):
        return self.page.locator("a.ftab.active")

    @property
    def kill_all_form(self):
        return self.page.locator(
            "//form[.//input[@name='_action' and @value='kill_all']]"
        )

    @property
    def kill_all_button(self):
        # "🚫 Kill All Active (N)"
        return self.kill_all_form.locator("button[type='submit']")

    # ── Sessions table ────────────────────────────────────────────────────────

    @property
    def sessions_table(self):
        return self.page.locator("table.stbl")

    @property
    def table_headers(self):
        return self.page.locator("table.stbl thead th")

    def table_header(self, label: str):
        return self.page.locator(
            f"//table[contains(@class,'stbl')]//thead//th[normalize-space(text())='{label}']"
        )

    @property
    def session_rows(self):
        return self.page.locator("table.stbl tbody tr")

    @property
    def live_rows(self):
        return self.page.locator("table.stbl tbody tr:has(.badge-live)")

    @property
    def stale_rows(self):
        return self.page.locator("table.stbl tbody tr:has(.badge-stale)")

    @property
    def ended_rows(self):
        return self.page.locator("table.stbl tbody tr:has(.badge-ended)")

    @property
    def killable_rows(self):
        """Rows exposing a per-row Kill button — i.e. active (live/stale)
        sessions the admin can terminate. Excludes ended rows (no Kill button)
        and any empty-state row. This is a more reliable 'are there active
        sessions?' signal than the summary tiles, which can read 0 while active
        rows still render in the table. The global Kill-All button lives in the
        toolbar (not the table), so it is never counted here."""
        return self.page.locator("table.stbl tbody tr:has(button.btn-r)")

    def rows_for_username(self, username: str):
        """All rows whose Username column equals ``username``."""
        return self.page.locator(
            f"//table[contains(@class,'stbl')]/tbody/tr[td[4][normalize-space()='{username}']]"
        )

    def live_rows_for_username(self, username: str):
        return self.page.locator(
            f"//table[contains(@class,'stbl')]/tbody/tr"
            f"[td[4][normalize-space()='{username}'] and .//span[contains(@class,'badge-live')]]"
        )

    def killed_rows_for_username(self, username: str):
        """Ended rows for ``username`` whose Reason column reads 'killed'."""
        return self.page.locator(
            f"//table[contains(@class,'stbl')]/tbody/tr"
            f"[td[4][normalize-space()='{username}']"
            f" and .//span[contains(@class,'badge-ended')]"
            f" and td[10][contains(normalize-space(),'killed')]]"
        )

    def row_by_session_id(self, session_id: str):
        """The live/stale row whose Kill form carries this ``session_id``
        (ended rows have no form and won't match)."""
        return self.page.locator(
            f"//table[contains(@class,'stbl')]/tbody/tr"
            f"[.//input[@name='session_id' and @value='{session_id}']]"
        )

    def rows_with_last_ping(self, text: str):
        """Rows whose Last Ping column equals ``text`` (e.g. 'No ping')."""
        return self.page.locator(
            f"//table[contains(@class,'stbl')]/tbody/tr[td[7][normalize-space()='{text}']]"
        )

    # -- Cells within a given row locator --

    def _cell(self, row, name: str):
        return row.locator("td").nth(self._COL_INDEX[name])

    def status_badge(self, row):
        return row.locator("span[class*='badge-']")

    def status_cell(self, row):
        return self._cell(row, "status")

    def agency_cell(self, row):
        return self._cell(row, "agency")

    def username_cell(self, row):
        return self._cell(row, "username")

    def login_ip_cell(self, row):
        return self._cell(row, "login_ip")

    def login_time_cell(self, row):
        return self._cell(row, "login_time")

    def last_ping_cell(self, row):
        return self._cell(row, "last_ping")

    def logout_end_cell(self, row):
        return self._cell(row, "logout_end")

    def duration_cell(self, row):
        return self._cell(row, "duration")

    def reason_cell(self, row):
        return self._cell(row, "reason")

    def kill_button(self, row):
        """The row's 🚫 Kill submit button (absent on ended rows)."""
        return row.locator("button.btn-r")

    # ── Pagination ────────────────────────────────────────────────────────────

    @property
    def pagination(self):
        return self.page.locator(".pag")

    @property
    def pagination_info(self):
        # "1–20 of 379 sessions · Page 1 of 19"
        return self.page.locator(".pag-info")

    @property
    def current_page(self):
        return self.page.locator(".pag .cur")

    def page_link(self, number: int):
        return self.pagination.locator(f"a[href*='page={number}']")

    @property
    def next_page_link(self):
        """The '›' next-page link (absent on the last page and when the
        result set fits on a single page)."""
        return self.pagination.locator("a", has_text="›")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Session Management dashboard directly")
    def open(self):
        self.navigate(f"{ADMIN_BASE}/sessions/index.php")

    @allure.step("Filter sessions by tab: {type_}")
    def filter_by_tab(self, type_: str):
        """type_: one of TYPE_FILTERS."""
        self.filter_tab(type_).click()
        self.wait_for_load()

    @allure.step("Filter sessions by tile: {type_}")
    def filter_by_chip(self, type_: str):
        self.stat_chip(type_).click()
        self.wait_for_load()

    @allure.step("Search sessions for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()
        self.wait_for_load()

    @allure.step("Clear the session search")
    def clear_search(self):
        self.search("")

    @allure.step("Kill the given session row (confirm dialog: {action})")
    def kill_row(self, row, action: str = "accept") -> str:
        """Clicks a row's 🚫 Kill button and answers the 'Terminate this
        session?' confirm dialog. Returns the dialog message. Accepting submits
        the form and reloads the page."""
        message = self.click_and_handle_alert(self.kill_button(row), action=action)
        if action == "accept":
            self.wait_for_load()
        return message

    @allure.step("Click 'Kill All Active' (confirm dialog: {action})")
    def kill_all(self, action: str = "dismiss") -> str:
        """Clicks the global 'Kill All Active' button and answers its confirm
        dialog. Defaults to *dismiss* (abort) so the destructive path is opt-in;
        pass action='accept' to actually terminate every active session.
        Returns the dialog message."""
        message = self.click_and_handle_alert(self.kill_all_button, action=action)
        if action == "accept":
            self.wait_for_load()
        return message

    def _walk_pages(self, type_: str = "all"):
        """Generator that walks EVERY page of the given tab, yielding once per
        page with that page loaded so the caller can read its rows. Follows the
        '›' next-page link until it disappears on the last page, then resets to
        page 1 of the tab. A 5000-page hard ceiling guards against an unexpected
        non-terminating strip; the next-link check is the real exit.

        Counts read inside the loop reflect a live snapshot — if sessions are
        killed/created mid-walk the totals can drift, so call the public
        counters on a quiescent dataset (they are read-only themselves)."""
        self.filter_by_tab(type_)
        pages_walked = 0
        while pages_walked < 5000:
            yield
            pages_walked += 1
            if self.next_page_link.count() == 0:
                break
            self.next_page_link.first.click()
            self.wait_for_load()
        self.filter_by_tab(type_)  # back to page 1

    @allure.step("Count killable (live/stale) sessions across all table pages")
    def count_killable_sessions(self) -> int:
        """Total number of killable (live + stale) sessions, counted from the
        actual table rows across EVERY page — not the summary tiles, which can
        read 0 while active rows still render (see TC-256). Each killable row
        carries a per-row Kill button; ended rows do not."""
        total = 0
        for _ in self._walk_pages("all"):
            total += self.killable_rows.count()
        return total

    @allure.step("Tally live / stale / ended sessions across all table pages")
    def count_sessions_by_status(self) -> dict:
        """Per-status session totals read from the actual table rows across
        EVERY page, by parsing each row's status badge (``badge-live`` /
        ``badge-stale`` / ``badge-ended``). Returns::

            {"live": int, "stale": int, "ended": int}

        The three buckets partition the table — every row carries exactly one
        status badge — so their sum is the whole-table session total and
        ``live + stale`` equals ``count_killable_sessions()``. Derived from the
        rows themselves, so it stays correct even when the summary tiles drift
        from the table (see TC-256)."""
        totals = {"live": 0, "stale": 0, "ended": 0}
        for _ in self._walk_pages("all"):
            totals["live"] += self.live_rows.count()
            totals["stale"] += self.stale_rows.count()
            totals["ended"] += self.ended_rows.count()
        return totals

    @allure.step("Go to results page {number}")
    def go_to_page(self, number: int):
        self.page_link(number).first.click()
        self.wait_for_load()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_stat_chip_count(self, type_: str) -> int:
        return int(self.stat_chip_count(type_).text_content().strip().replace(",", ""))

    def get_unique_users_count(self) -> int:
        return int(self.unique_users_count.text_content().strip().replace(",", ""))

    def get_active_filter(self) -> str:
        return self.active_filter_tab.text_content().strip()

    def get_session_id(self, row) -> str:
        """The session_id carried by a live/stale row's Kill form."""
        return row.locator("input[name='session_id']").get_attribute("value")

    def get_username(self, row) -> str:
        return self.username_cell(row).text_content().strip()

    def get_login_times(self) -> list:
        """Parsed Login Time of every row on the current page, top to bottom.
        Unparseable cells are skipped."""
        times = []
        cells = self.session_rows.locator("td:nth-child(6)")
        for i in range(cells.count()):
            raw = cells.nth(i).text_content().strip()
            match = re.search(r"\d{1,2} \w{3} \d{4}, \d{2}:\d{2}", raw)
            if match:
                times.append(datetime.strptime(match.group(), self._LOGIN_TIME_FMT))
        return times

    def is_kill_all_available(self) -> bool:
        """True when the Kill-All button is present AND enabled (i.e. there are
        active sessions to terminate)."""
        if self.kill_all_button.count() == 0:
            return False
        return self.kill_all_button.is_enabled()
