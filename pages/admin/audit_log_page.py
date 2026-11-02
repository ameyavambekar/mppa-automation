import re
from urllib.parse import urlencode

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

ADMIN_AUDIT_LOG_URL = f"{ADMIN_BASE}/audit/index.php"


class AdminAuditLogPage(BasePage):
    """Admin — Audit Log (/module/admin/audit/index.php, "Audit Log — Admin").

    Header ``.adm-page-title``: "Audit Log · {N} Events" and a clock (``.pg-date``, "DD Mon YYYY · HH:MM"),
    then four stat cards (``.sc-row .sc``, count ``.n``, label ``.l``): Total Events (follows the filters),
    Today and This Week (links to ``?date_f=today`` / ``?date_f=week``) and Action Types.

    The log is a card feed, not a ``.stbl`` table: each event is a ``.log-item`` with time / action-pill /
    who-what / details-preview cells, followed by a hidden ``.log-expand`` (id ``exp-<audit id>``) holding
    the full record header, Table / Record ID / By chips and raw JSON. Clicking a log item opens its expand
    row and closes any other (Escape closes all).

    Filtering is done server-side via the GET form ``#filterForm``: ``q`` (search), ``date_f``
    (today/week/month, empty = All Time), ``action_f`` (chosen in ``#actionSelect``, which submits as soon
    as it changes) and ``page`` (30 events per page). "✕ Clear all" (``?``) shows while any filter is set;
    no matches show ``EMPTY``.
    Entry locators are offered both by position (``log_entry(0)`` = newest)
    and by audit record id (``log_entry_by_id(894)``).
    """

    PAGE_TITLE = "Audit Log — Admin"
    SEARCH_PLACEHOLDER = "Search action, table, user, data…"
    ALL_ACTIONS = "— All Action Types —"
    ACTION_GROUPS = ("── Agency ──", "── Sessions ──", "── Admin ──", "── Other ──")
    DATE_TABS = {"": "All Time", "today": "Today", "week": "7 Days", "month": "30 Days"}
    STAT_CARDS = ("Total Events", "Today", "This Week", "Action Types")
    CLEAR_ALL = "✕ Clear all"
    EMPTY = "No audit records found for the selected filters."
    PAGE_SIZE = 30
    TIMESTAMP_FORMAT = "%d %b %Y, %H:%M:%S"
    CLOCK_FORMAT = "%d %b %Y · %H:%M"
    TIME_AGO = re.compile(r"^(just now|\d+[mhd] ago)$")
    SHOWING = re.compile(r"^Showing ([\d,]+)–([\d,]+) of ([\d,]+) events?$")
    PAGINATION_INFO = re.compile(r"^([\d,]+)–([\d,]+) of ([\d,]+) · Page (\d+) / (\d+)$")

    # action_f value → pill label. The action dropdown (#actionSelect) only lists the codes the log
    # already holds (13 on 02-Nov-2026), so a code appears once its first event is logged; codes
    # without a friendly label show the raw code.
    ACTION_LABELS = {
        "AGENCY_APPROVE": "Agency Approved", "LOGIN": "Agency Login", "ADMIN_LOGIN": "Admin Login",
        "ADMIN_LOGIN_FAILED": "ADMIN_LOGIN_FAILED", "CERTIFICATE_EXPIRE": "CERTIFICATE_EXPIRE",
        "DRAFT_DELETE": "DRAFT_DELETE", "DRAFT_EXTEND": "DRAFT_EXTEND", "DRAFT_LOGIN": "DRAFT_LOGIN",
        "JOB_SEEKER_APPROVED": "JOB_SEEKER_APPROVED", "PASSWORD_RESET_DONE": "PASSWORD_RESET_DONE",
        "PASSWORD_RESET_VERIFIED": "PASSWORD_RESET_VERIFIED", "PAYMENT_COMMIT": "PAYMENT_COMMIT",
        "SECTION_REVIEW_SAVE": "SECTION_REVIEW_SAVE",
    }

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Topbar / page header ──────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        return self.page.locator("#adm-topbar .tb-role")

    @property
    def page_title(self):
        # "Audit Log · 1,712 Events"
        return self.page.locator(".adm-page-title span").first

    @property
    def clock(self):
        # "02 Nov 2026 · 11:58"
        return self.page.locator(".adm-page-title .pg-date")

    # ── Stat cards ────────────────────────────────────────────────────────────

    @property
    def stat_cards(self):
        return self.page.locator(".sc-row .sc")

    def stat_card(self, label: str):
        """label: 'Total Events', 'Today', 'This Week' or 'Action Types'.
        'Today' and 'This Week' are clickable date filters."""
        return self.page.locator(f"//div[contains(@class,'sc-row')]/*[div[@class='l' and normalize-space(text())='{label}']]")

    def stat_card_count(self, label: str):
        return self.stat_card(label).locator(".n")

    # ── Toolbar: search & date filters ────────────────────────────────────────

    @property
    def search_input(self):
        return self.page.locator("input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("//button[normalize-space(text())='Search']")

    def date_filter_tab(self, label: str):
        """label: 'All Time', 'Today', '7 Days' or '30 Days'."""
        return self.page.locator(f"//a[contains(@class,'ftab') and normalize-space(text())='{label}']")

    @property
    def active_date_filter_tab(self):
        return self.page.locator("a.ftab.active")

    @property
    def showing_events_text(self):
        # "Showing 1–30 of 869 events"
        return self.page.locator("//div[contains(text(),'Showing') and contains(text(),'event')]")

    @property
    def clear_all_link(self):
        """'✕ Clear all' (href '?'), shown only while a filter is set."""
        return self.page.locator("a", has_text=self.CLEAR_ALL)

    # ── Action-type dropdown ──────────────────────────────────────────────────

    @property
    def action_select(self):
        """'— All Action Types —' plus one option per action code (value = the ?action_f= code),
        grouped (Agency, Sessions, Admin, Other). Changing it submits the filter form."""
        return self.page.locator("#actionSelect")

    @property
    def action_groups(self):
        return self.action_select.locator("optgroup")

    @property
    def action_options(self):
        """The action options, without '— All Action Types —'."""
        return self.action_select.locator("option:not([value=''])")

    def action_option(self, action: str):
        """action: an action code — listed only once the log holds an event of that type."""
        return self.action_select.locator(f"option[value='{action}']")

    @property
    def selected_action_option(self):
        """The chosen option ('— All Action Types —' when unfiltered)."""
        return self.action_select.locator("option:checked")

    # ── Log feed entries ──────────────────────────────────────────────────────

    @property
    def log_feed(self):
        return self.page.locator(".tb-wrap")

    @property
    def empty_state(self):
        return self.log_feed.get_by_text(self.EMPTY)

    @property
    def log_entries(self):
        """All main log rows on the current page (newest first)."""
        return self.page.locator(".log-item")

    def log_entry(self, index: int):
        """Main log row by position on the page (0 = newest)."""
        return self.log_entries.nth(index)

    def log_entry_by_id(self, audit_id: int):
        """Main log row by audit record id (the number in its expand row's id, exp-<n>)."""
        return self.page.locator(f".log-item[onclick*=\"'exp-{audit_id}'\"]")

    # -- Cells within a log entry (pass the entry locator) --

    def entry_timestamp(self, entry):
        # e.g. "01 Jun 2026, 07:13:34"
        return entry.locator(".dt")

    def entry_time_ago(self, entry):
        # e.g. "just now" / "1d ago"
        return entry.locator(".ago")

    def entry_action_pill(self, entry):
        # e.g. "Admin Login"
        return entry.locator(".act-pill")

    def entry_table_name(self, entry):
        # e.g. "admin_users"
        return entry.locator(".tname")

    def entry_record_id(self, entry):
        # e.g. "ID #1"
        return entry.locator(".rid")

    def entry_detail_keys(self, entry):
        return entry.locator(".detail-kv .dk")

    def entry_detail_value(self, entry, key: str):
        """A details-preview value by its key, e.g. 'username', 'ip', 'role',
        'status'."""
        return entry.locator(
            f"//div[@class='detail-kv'][span[@class='dk' and normalize-space(text())='{key}']]/span[contains(@class,'dv')]"
        )

    # -- Expand row (full record) --

    @property
    def expanded_entry(self):
        # The currently expanded main row (only one at a time)
        return self.page.locator(".log-item.expanded")

    @property
    def open_expand_row(self):
        return self.page.locator(".log-expand.open")

    def expand_row(self, entry):
        """The hidden expand row right after a main log row."""
        return entry.locator("xpath=following-sibling::div[contains(@class,'log-expand')][1]")

    def expand_row_by_id(self, audit_id: int):
        return self.page.locator(f"#exp-{audit_id}")

    @property
    def expanded_record_header(self):
        # "Full audit record — ADMIN_LOGIN · 01 Jun 2026, 07:13:34"
        return self.open_expand_row.locator("//span[contains(text(),'Full audit record')]")

    def expanded_chip(self, label: str):
        """The value of an open record's chip: label 'Table', 'Record ID' or 'By'."""
        return self.open_expand_row.locator(f"//span[starts-with(normalize-space(.),'{label}:')]/strong")

    @property
    def expanded_raw_json(self):
        return self.open_expand_row.locator(".raw-json")

    @property
    def edit_controls(self):
        """Any button, link or menu on the feed or an open record that could change an entry."""
        return self.page.locator("main .tb-wrap").locator("button, a, input, select, [contenteditable='true']").filter(
            has_text=re.compile(r"edit|delete|remove|modify", re.I))

    # ── Pagination ────────────────────────────────────────────────────────────

    @property
    def pagination(self):
        return self.page.locator(".pag")

    @property
    def current_page_number(self):
        return self.page.locator(".pag .cur")

    def page_link(self, number: int):
        return self.pagination.locator("a").filter(has_text=re.compile(rf"^{number}$")).first

    @property
    def page_links(self):
        return self.pagination.locator("a")

    @property
    def next_page_link(self):
        """The '›' next-page link (absent on the last page)."""
        return self.pagination.locator("a", has_text="›")

    @property
    def pagination_info(self):
        # "1–30 of 869 · Page 1 / 29"
        return self.page.locator(".pag-info")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Audit Log page directly")
    def open(self, date_f: str = None, action_f: str = None, q: str = None, page: int = None):
        """Opens the log, optionally with filters already set (each one is a GET parameter)."""
        params = {"date_f": date_f, "action_f": action_f, "q": q, "page": page}
        query = urlencode({k: v for k, v in params.items() if v is not None})
        self.navigate(f"{ADMIN_AUDIT_LOG_URL}?{query}" if query else ADMIN_AUDIT_LOG_URL)

    @allure.step("Search audit log for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        with self.page.expect_navigation():
            self.search_button.click()

    @allure.step("Filter audit log by date: {label}")
    def filter_by_date(self, label: str):
        """label: 'All Time', 'Today', '7 Days' or '30 Days'."""
        with self.page.expect_navigation():
            self.date_filter_tab(label).click()

    @allure.step("Click the '{label}' stat card")
    def click_stat_card(self, label: str):
        """label: 'Today' or 'This Week' (the other cards are not links)."""
        with self.page.expect_navigation():
            self.stat_card(label).click()

    @allure.step("Filter audit log by action: {action}")
    def filter_by_action(self, action: str):
        """action: an action code from the dropdown; the feed reloads filtered to it."""
        with self.page.expect_navigation():
            self.action_select.select_option(value=action)

    @allure.step("Clear the action filter (All)")
    def clear_action_filter(self):
        with self.page.expect_navigation():
            self.action_select.select_option(value="")

    @allure.step("Click '✕ Clear all'")
    def clear_all(self):
        with self.page.expect_navigation():
            self.clear_all_link.click()

    @allure.step("Expand log entry at index {index}")
    def expand_entry(self, index: int):
        """Clicks a main log row to open its full-record expand row. Clicking
        an already-expanded row collapses it instead."""
        self.log_entry(index).click()

    @allure.step("Expand log entry with audit id {audit_id}")
    def expand_entry_by_id(self, audit_id: int):
        self.log_entry_by_id(audit_id).click()

    @allure.step("Collapse any expanded entry (Escape)")
    def collapse_expanded_entry(self):
        self.page.keyboard.press("Escape")

    @allure.step("Go to audit log page {number}")
    def go_to_page(self, number: int):
        with self.page.expect_navigation():
            self.page_link(number).click()

    @allure.step("Go to next audit log page")
    def go_to_next_page(self):
        with self.page.expect_navigation():
            self.next_page_link.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_expanded_json_text(self) -> str:
        """Raw JSON text of the currently expanded record."""
        return self.expanded_raw_json.text_content()

    def get_entry_count(self) -> int:
        """Number of log entries on the current page."""
        return self.log_entries.count()

    def total_events(self) -> int:
        """N from the header 'Audit Log · N Events'."""
        return int(re.search(r"([\d,]+) Events?", self.page_title.inner_text()).group(1).replace(",", ""))

    def stat_number(self, label: str) -> int:
        return int(self.stat_card_count(label).inner_text().replace(",", ""))

    def action_values(self) -> list[str]:
        """The action codes offered in the dropdown, in order."""
        return self.action_options.evaluate_all("os => os.map(o => o.value)")

    def entries_data(self) -> list[dict]:
        """Every entry on the page read in one go: timestamp, ago, action (pill text), table, record_id
        ('' when the event has none), details ({key: value}) and audit_id (from the expand row's id).
        Text is read as written in the page (the keys are upper-cased only by CSS)."""
        return self.log_entries.evaluate_all("""items => items.map(i => {
            const t = (el) => el ? el.textContent.replace(/\\s+/g, ' ').trim() : '';
            return {
            timestamp: t(i.querySelector('.dt')),
            ago: t(i.querySelector('.ago')),
            action: t(i.querySelector('.act-pill')),
            table: t(i.querySelector('.tname')),
            record_id: t(i.querySelector('.rid')),
            details: Object.fromEntries([...i.querySelectorAll('.detail-kv')].map(kv =>
                [t(kv.querySelector('.dk')), t(kv.querySelector('.dv'))])),
            audit_id: Number((i.getAttribute('onclick').match(/exp-(\\d+)/) || [])[1]),
        }; })""")
