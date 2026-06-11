import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage


class AdminAuditLogPage(BasePage):
    """Admin — Audit Log (/module/admin/audit/index.php).

    The log is a custom card feed, not a ``.stbl`` table: each event is a
    ``.log-item`` (id ``row-<n>``) with time / action-pill / who-what /
    details-preview cells, followed by a hidden ``.log-expand`` row
    (id ``exp-<n>``) holding the full record header and raw JSON. Clicking a
    log item opens its expand row and closes any other (Escape closes all).

    Filtering is done server-side via query params: ``q`` (search),
    ``date_f`` (today/week/month), ``action_f`` (action type) and ``page``.
    Entry locators are offered both by position (``log_entry(0)`` = newest)
    and by audit record id (``log_entry_by_id(894)``).
    """

    # action_f filter values seen on the page (chips row)
    ACTION_TYPES = (
        "ADMIN_CREATE", "ADMIN_DELETE", "ADMIN_LOGIN", "ADMIN_PERM_UPDATE",
        "ADMIN_STATUS_CHANGE", "ADMIN_TOGGLE", "AGENCY_APPROVE",
        "AGENCY_REINSTATE", "AGENCY_REJECT", "AGENCY_REVOKE", "AGENCY_SUSPEND",
        "FINAL_SUBMIT", "LOGIN", "REGISTER", "SAVE_AUTHORISATION",
        "SAVE_DECLARATION", "SAVE_ENCLOSURES", "SAVE_PART_A", "SAVE_PART_B",
        "SAVE_PART_C", "SAVE_PART_D", "SAVE_PART_E", "SAVE_PART_F",
        "SECOND_APPEAL", "SESSION_KILL", "STATUS_CHANGE", "SUBMIT_FIRST_APPEAL",
    )

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Topbar / page header ──────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        return self.page.locator("#adm-topbar .tb-badge")

    @property
    def page_title(self):
        # "📋 Audit Log · 869 Events"
        return self.page.locator(".adm-page-title span").first

    # ── Stat cards ────────────────────────────────────────────────────────────

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
        return self.page.locator("//div[contains(text(),'Showing') and contains(text(),'events')]")

    # ── Action-type chips ─────────────────────────────────────────────────────

    @property
    def action_chips(self):
        return self.page.locator(".action-chips .ach")

    def action_chip(self, action: str):
        """action: one of ACTION_TYPES (matches the ?action_f= value)."""
        return self.page.locator(f".action-chips a.ach[href*='action_f={action}&']")

    @property
    def all_actions_chip(self):
        return self.page.locator("//div[@class='action-chips']/a[normalize-space(text())='All']")

    @property
    def selected_action_chip(self):
        return self.page.locator(".action-chips .ach.sel")

    # ── Log feed entries ──────────────────────────────────────────────────────

    @property
    def log_feed(self):
        return self.page.locator(".tb-wrap")

    @property
    def log_entries(self):
        """All main log rows on the current page (newest first)."""
        return self.page.locator(".log-item")

    def log_entry(self, index: int):
        """Main log row by position on the page (0 = newest)."""
        return self.log_entries.nth(index)

    def log_entry_by_id(self, audit_id: int):
        """Main log row by audit record id (the trailing number in #row-<n>)."""
        return self.page.locator(f"#row-{audit_id}")

    # -- Cells within a log entry (pass the entry locator) --

    def entry_timestamp(self, entry):
        # e.g. "01 Jun 2026, 07:13:34"
        return entry.locator(".dt")

    def entry_time_ago(self, entry):
        # e.g. "just now" / "1d ago"
        return entry.locator(".ago")

    def entry_action_pill(self, entry):
        # e.g. "🔐 Admin Login"
        return entry.locator(".act-pill")

    def entry_table_name(self, entry):
        # e.g. "📁 admin_users"
        return entry.locator(".tname")

    def entry_record_id(self, entry):
        # e.g. "ID #1"
        return entry.locator(".rid")

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
        # "🔐 Full audit record — ADMIN_LOGIN · 01 Jun 2026, 07:13:34"
        return self.open_expand_row.locator("//span[contains(text(),'Full audit record')]")

    @property
    def expanded_raw_json(self):
        return self.open_expand_row.locator(".raw-json")

    # ── Pagination ────────────────────────────────────────────────────────────

    @property
    def pagination(self):
        return self.page.locator(".pag")

    @property
    def current_page_number(self):
        return self.page.locator(".pag .cur")

    def page_link(self, number: int):
        return self.page.locator(f".pag a[href='?page={number}']").first

    @property
    def next_page_link(self):
        return self.page.locator("//div[@class='pag']/a[contains(normalize-space(.),'Next')]")

    @property
    def pagination_info(self):
        # "1–30 of 869 · Page 1 / 29"
        return self.page.locator(".pag-info")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Audit Log page directly")
    def open(self):
        import os
        base = os.getenv("MPPA_ADMIN_BASE_URL", "https://devmppa.sppuef.in/module/admin")
        self.navigate(f"{base}/audit/index.php")

    @allure.step("Search audit log for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()

    @allure.step("Filter audit log by date: {label}")
    def filter_by_date(self, label: str):
        """label: 'All Time', 'Today', '7 Days' or '30 Days'."""
        self.date_filter_tab(label).click()

    @allure.step("Filter audit log by action: {action}")
    def filter_by_action(self, action: str):
        """action: one of ACTION_TYPES."""
        self.action_chip(action).click()

    @allure.step("Clear the action filter (All)")
    def clear_action_filter(self):
        self.all_actions_chip.click()

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
        self.page_link(number).click()

    @allure.step("Go to next audit log page")
    def go_to_next_page(self):
        self.next_page_link.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_expanded_json_text(self) -> str:
        """Raw JSON text of the currently expanded record."""
        return self.expanded_raw_json.text_content()

    def get_entry_count(self) -> int:
        """Number of log entries on the current page."""
        return self.log_entries.count()
