import re
from datetime import datetime

import allure

from config import ADMIN_BASE
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

ADMIN_DRAFTS_URL = f"{ADMIN_BASE}/drafts/index.php"


class AdminDraftsPage(BasePage):
    """Page object for Registrations in Progress (module/admin/drafts/index.php,
    "Registrations in Progress — Super Admin"): agencies that registered but have not paid.

    Header: ``.adm-page-title`` "Registrations in Progress (not paid yet)" with a clock (``.pg-date``),
    then a flash message after Extend / Delete, the intro (``.dr-note``: 7 days to finish and pay,
    deleted automatically after that) and five filter chips (``a.dr-chip``, ``on`` when active; count
    ``.n``, label ``.l``), each linking to ``?f=<filter>&q=<search>`` (see ``FILTERS``).

    Search: a GET form with the hidden ``f`` and the text box ``q``.

    Table (not paginated, newest registration first): one ``tr[onclick]`` per draft — Agency (name,
    "@username[ · <agency type>]"), Contact (email, mobile), District, Progress (7-segment ``.dr-bar``,
    "N/7 steps · next: <step>" or "✓ All steps done — awaiting payment"), Registered, Last activity,
    Deadline (``.dr-pill`` ``ok`` "N day(s) left", ``warn`` "N hour(s) left", ``late`` "Expired 1d ago"
    until the draft is deleted, ``ready`` "✓ All steps done — awaiting payment") and "▾". Clicking a row toggles the details row after it (``tr.dr-det``,
    ``open`` while shown): the ``.dr-grid`` fields (see ``DETAIL_LABELS``), a ``.dr-step`` chip per step
    (``ok`` ✓ / ``no`` ○), a link per uploaded document (``a.dr-doc``, new tab), "Extend deadline"
    (``add_days`` +3 / +7 / +15, POST ``act=extend``) and "Delete draft" (POST ``act=delete`` behind a
    ``confirm()``). An empty table shows ``EMPTY_FILTER`` or, when searching, ``EMPTY_SEARCH``.
    """

    PAGE_TITLE = "Registrations in Progress — Super Admin"
    HEADING = "Registrations in Progress (not paid yet)"
    INTRO_PARTS = ("registered but not paid yet", "7 days", "deleted automatically", "only after payment")
    SEARCH_PLACEHOLDER = "Search agency, username, email, mobile, PAN, district…"
    COLUMNS = ("Agency", "Contact", "District", "Progress", "Registered", "Last activity", "Deadline", "")
    # ?f= value → chip label
    FILTERS = {"all": "All drafts", "progress": "Filling form", "ready": "Ready to pay", "urgent": "< 24 h left",
               "expired": "Expired"}
    STEPS = ("Register", "Part A", "Part B", "Part C", "Part F", "Documents", "Declaration", "Payment")
    DETAIL_LABELS = ("Agency", "Username", "Email", "Mobile", "PAN", "Agency type / fee", "Deadline", "Draft ref.")
    TOTAL_STEPS = 7
    READY = "✓ All steps done — awaiting payment"
    NOT_VERIFIED = "(not OTP-verified)"
    PART_A_NOT_FILLED = "— (Part A not filled)"
    EXTEND_DAYS = ("3", "7", "15")
    DEFAULT_EXTEND_DAYS = "7"
    EXTEND_LABEL = "Extend deadline"
    DELETE_LABEL = "Delete draft"
    DELETE_CONFIRM = "Delete this unfinished registration and ALL its uploaded files? This cannot be undone."
    EMPTY_FILTER = "No registrations in progress for this filter."
    EMPTY_SEARCH = "No registrations in progress."
    DATE_FORMAT = "%d %b %Y, %I:%M %p"
    PROGRESS = re.compile(r"^(\d)/7 steps · next: (.+)$")
    DAYS_LEFT = re.compile(r"^(\d+) day\(s\) left$")
    HOURS_LEFT = re.compile(r"^(\d+) hour\(s\) left$")
    # Past the deadline but not deleted yet (``late`` pill); listed under Expired only
    EXPIRED = re.compile(r"^Expired \d+[dhm] ago$")
    AUDIT_EXTEND = "DRAFT_EXTEND"

    @staticmethod
    def extended_message(days: str) -> str:
        return f"Deadline extended by {days} day(s)."

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("main .adm-page-title span").first

    @property
    def clock(self):
        return self.page.locator("main .adm-page-title .pg-date")

    @property
    def intro(self):
        return self.page.locator("main .dr-note")

    def message(self, text: str):
        """A flash message shown after Extend / Delete."""
        return self.page.locator("main").get_by_text(text, exact=True)

    @property
    def chips(self):
        return self.page.locator("main a.dr-chip")

    def chip(self, filter_: str):
        """filter_: a key of ``FILTERS``."""
        return self.page.locator(f"main a.dr-chip[href^='?f={filter_}&']")

    def chip_count(self, filter_: str):
        return self.chip(filter_).locator(".n")

    def chip_label(self, filter_: str):
        return self.chip(filter_).locator(".l")

    @property
    def active_chip(self):
        return self.page.locator("main a.dr-chip.on")

    @property
    def search_input(self):
        return self.page.locator("main form input[name='q']")

    @property
    def search_filter_input(self):
        """The hidden ``f`` the search keeps."""
        return self.page.locator("main form input[name='f']")

    @property
    def search_button(self):
        return self.page.locator("main form").get_by_role("button", name="Search")

    # ── Table ─────────────────────────────────────────────────────────────────

    @property
    def column_headers(self):
        return self.page.locator("main table thead th")

    @property
    def rows(self):
        return self.page.locator("main tbody tr[onclick]")

    @property
    def empty_row(self):
        return self.page.locator("main tbody tr:not([onclick]):not(.dr-det)")

    def row_for(self, username: str):
        """The draft row of ``username`` (matched on its '@username')."""
        return self.rows.filter(has=self.page.locator("td:first-child div", has_text=re.compile(
            rf"^@{re.escape(username)}( · .+)?$")))

    def cell(self, row, column: str):
        return row.locator("td").nth(self.COLUMNS.index(column))

    def agency_name(self, row):
        return self.cell(row, "Agency").locator("div").first

    def agency_sub(self, row):
        """'@username' or '@username · <agency type>'."""
        return self.cell(row, "Agency").locator("div").nth(1)

    def progress_bar_segments(self, row):
        return self.cell(row, "Progress").locator(".dr-bar i")

    def progress_bar_done(self, row):
        return self.cell(row, "Progress").locator(".dr-bar i.ok")

    def deadline_pill(self, row):
        return self.cell(row, "Deadline").locator(".dr-pill")

    def details(self, row):
        """The details row that follows ``row``."""
        return row.locator("xpath=following-sibling::tr[1][contains(@class,'dr-det')]")

    def detail_value(self, row, label: str):
        """A ``.dr-grid`` value by its label (see ``DETAIL_LABELS``)."""
        return self.details(row).locator(".dr-grid > div").filter(
            has=self.page.locator("small", has_text=re.compile(rf"^{re.escape(label)}$"))).locator("b")

    def step_chips(self, row):
        return self.details(row).locator(".dr-step")

    def step_chip(self, row, step: str):
        return self.step_chips(row).filter(has_text=re.compile(rf"^[✓○] {re.escape(step)}\b"))

    def document_links(self, row):
        return self.details(row).locator("a.dr-doc")

    def extend_days_select(self, row):
        return self.details(row).locator("select[name='add_days']")

    def extend_button(self, row):
        return self.details(row).get_by_role("button", name=self.EXTEND_LABEL)

    def delete_button(self, row):
        return self.details(row).get_by_role("button", name=self.DELETE_LABEL)

    # ── Reads (no assertions) ─────────────────────────────────────────────────

    def usernames(self) -> list[str]:
        return [t.lstrip("@").split(" · ")[0].strip()
                for t in self.page.locator("main tbody tr[onclick] td:first-child div:nth-child(2)").all_inner_texts()]

    def table_data(self) -> list[dict]:
        """Every row read in one go: agency, sub ('@username[ · type]'), contact, district, progress,
        bar_done / bar_total (filled / all progress segments), registered, last_activity, pill, pill_class
        and deadline (the details panel's Deadline text)."""
        return self.rows.evaluate_all("""rows => rows.map(r => {
            const c = r.cells, d = c[0].querySelectorAll('div'), pill = c[6].querySelector('.dr-pill');
            const grid = r.nextElementSibling ? [...r.nextElementSibling.querySelectorAll('.dr-grid > div')] : [];
            const dl = grid.find(x => x.querySelector('small')?.textContent.trim() === 'Deadline');
            return {agency: d[0]?.innerText.trim(), sub: d[1]?.innerText.trim(), contact: c[1].innerText.trim(),
                    district: c[2].innerText.trim(), progress: c[3].innerText.replace(/\\s+/g, ' ').trim(),
                    bar_done: c[3].querySelectorAll('.dr-bar i.ok').length,
                    bar_total: c[3].querySelectorAll('.dr-bar i').length,
                    registered: c[4].innerText.trim(), last_activity: c[5].innerText.trim(),
                    pill: pill ? pill.innerText.trim() : '', pill_class: pill ? pill.className : '',
                    deadline: dl ? dl.querySelector('b').innerText.trim() : ''};
        })""")

    def chip_number(self, filter_: str) -> int:
        return int(self.chip_count(filter_).inner_text())

    def date_in(self, row, column: str) -> datetime:
        return datetime.strptime(self.cell(row, column).inner_text().strip(), self.DATE_FORMAT)

    def deadline(self, row) -> datetime:
        """The details panel's Deadline (without a '(+Nd extended)' note)."""
        text = self.detail_value(row, "Deadline").inner_text()
        return datetime.strptime(re.sub(r"\s*\(.*\)$", "", text).strip(), self.DATE_FORMAT)

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Registrations in Progress")
    def open(self, filter_: str = None, query: str = None):
        params = []
        if filter_ is not None:
            params.append(f"f={filter_}")
        if query is not None:
            params.append(f"q={query}")
        self.navigate(ADMIN_DRAFTS_URL + ("?" + "&".join(params) if params else ""))

    @allure.step("Click the '{filter_}' chip")
    def choose_filter(self, filter_: str):
        with self.page.expect_navigation():
            self.chip(filter_).click()

    @allure.step("Search drafts for '{query}'")
    def search(self, query: str):
        self.search_input.fill(query)
        with self.page.expect_navigation():
            self.search_button.click()

    @allure.step("Click the draft row")
    def toggle_details(self, row):
        self.cell(row, "Agency").click()

    @allure.step("Extend the deadline by {days} day(s)")
    def extend_deadline(self, row, days: str):
        """days: one of ``EXTEND_DAYS``. The page reloads with ``extended_message(days)``."""
        self.extend_days_select(row).select_option(days)
        with self.page.expect_navigation():
            self.extend_button(row).click()

    @allure.step("Click 'Delete draft' and cancel the confirmation")
    def delete_draft_cancel(self, row) -> str:
        """Returns the confirm() message."""
        return self.click_and_handle_alert(self.delete_button(row), action="dismiss")

    @allure.step("Click 'Delete draft' and confirm")
    def delete_draft(self, row) -> str:
        """Accepts the confirm(), waits for the page to reload and returns the confirm() message."""
        with self.page.expect_navigation():
            message = self.click_and_handle_alert(self.delete_button(row), action="accept")
        return message
