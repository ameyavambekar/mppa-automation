import re

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

NOTICES_URL = f"{ADMIN_BASE}/notices/Admin%20notices%20manage.php"


class AdminNoticesPage(BasePage):
    """Admin — Manage Notices (/module/admin/notices/Admin notices manage.php), Administration › Notices.

    Header ``.n-page-title``: "Manage Notices" and the ``.pt-date`` clock "DD Mon YYYY · HH:MM".

    Left panel: the Add New Notice form (``.n-form-title``; title, body, badge type with the ``#badgePreview``
    chip, department, attachment with the client-side 5 MB guard ``#fileSizeError``, Pin, Active, "Add
    Notice"). ``?edit=<id>`` turns it into "Edit Notice" with "Update Notice", "✕ Cancel Edit" and a "View
    File" link for an existing attachment; an unknown id leaves the Add form.

    Right panel: filter pills (``.n-pill``, links ``?badge=<type>``; only "All (N)" carries a count — the
    number of rows listed) and the ``.ntbl`` table: #, TITLE (title + department), BADGE (``.nbadge``),
    STATUS (``button.act-tog`` — "Active" with ``.dot-on`` / "Hidden" — a POST toggle), PIN
    (``button.act-pin`` "Pinned" / "Pin" — a POST toggle), DATE ("DD Mon YYYY") and ACTIONS (Edit link,
    Del button with a confirm). With no rows the table is replaced by ``EMPTY_LIST``. Saves and toggles
    reload the page, with ``.salt-s`` / ``.salt-e`` alerts.
    """

    HEADING = "Manage Notices"
    ADD_FORM_TITLE = "Add New Notice"
    EDIT_FORM_TITLE = "Edit Notice"
    ADD_BUTTON = "Add Notice"
    UPDATE_BUTTON = "Update Notice"
    COLUMNS = ("#", "TITLE", "BADGE", "STATUS", "PIN", "DATE", "ACTIONS")
    FILTERS = ("All", "New", "Alert", "Info", "Urgent", "General")
    EMPTY_LIST = "No notices yet. Add one using the form on the left."
    DELETE_CONFIRM = "Delete this notice? This cannot be undone."
    FILE_SIZE_ERROR = "File exceeds 5 MB limit. Please choose a smaller file."
    ATTACHMENT_ACCEPT = "image/jpeg,image/png,application/pdf"
    MAX_LENGTHS = {"title": 200, "body": 2000, "dept_name": 120}
    CLOCK_FORMAT = "%d %b %Y · %H:%M"
    DATE_FORMAT = "%d %b %Y"

    # ── Sidebar ───────────────────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Page-level alerts ─────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".salt.salt-s")

    @property
    def error_alert(self):
        return self.page.locator(".salt.salt-e")

    # ── Page header ───────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator(".n-page-title span").first

    @property
    def page_clock(self):
        # "04 Nov 2026 · 06:46"
        return self.page.locator(".n-page-title .pt-date")

    # ── Form header ───────────────────────────────────────────────────────────

    @property
    def form_title(self):
        return self.page.locator(".n-form-title")

    # ── Form fields ───────────────────────────────────────────────────────────

    @property
    def title_input(self):
        return self.page.locator("input[name='title'].nfi")

    @property
    def body_textarea(self):
        return self.page.locator("textarea[name='body'].nfi")

    @property
    def badge_select(self):
        return self.page.locator("#badgeSelect")

    @property
    def badge_preview(self):
        return self.page.locator("#badgePreview")

    @property
    def dept_input(self):
        return self.page.locator("input[name='dept_name'].nfi")

    @property
    def attachment_input(self):
        return self.page.locator("input[name='attachment']")

    @property
    def pin_checkbox(self):
        return self.page.locator("#cbPin")

    @property
    def active_checkbox(self):
        return self.page.locator("#cbActive")

    @property
    def save_button(self):
        return self.page.locator("button.n-save")

    @property
    def cancel_link(self):
        return self.page.locator("a.n-cancel")

    @property
    def notice_id_input(self):
        """The form's hidden notice_id (0 when adding)."""
        return self.page.locator("form:has(#badgeSelect) input[name='notice_id']")

    @property
    def form_labels(self):
        return self.page.locator("form:has(#badgeSelect) label.nfl")

    @property
    def file_size_error(self):
        """Client-side "File exceeds 5 MB limit…" message under the attachment field."""
        return self.page.locator("#fileSizeError")

    @property
    def view_file_link(self):
        """"View File" link for the notice's current attachment (edit mode)."""
        return self.page.locator("form:has(#badgeSelect) a", has_text="View File")

    # ── Filter pills ──────────────────────────────────────────────────────────

    def filter_pill(self, label: str):
        """Filter pill by partial visible text, e.g. 'Alert', 'All'."""
        return self.page.locator(f".n-pill:has-text('{label}')").first

    @property
    def active_filter_pill(self):
        return self.page.locator(".n-pill.on")

    @property
    def filter_pills(self):
        return self.page.locator(".n-pill")

    def all_count(self) -> int:
        """N from the "All (N)" pill."""
        match = re.search(r"\((\d+)\)", self.filter_pill("All").inner_text())
        return int(match.group(1)) if match else 0

    # ── Notice table ──────────────────────────────────────────────────────────

    @property
    def notice_table(self):
        return self.page.locator(".ntbl")

    @property
    def notice_rows(self):
        return self.page.locator(".ntbl tbody tr")

    @property
    def table_headers(self):
        return self.page.locator(".ntbl thead th")

    @property
    def empty_list(self):
        return self.page.get_by_text(self.EMPTY_LIST, exact=True)

    def notice_row(self, title: str):
        """The first row whose title cell contains ``title``."""
        return self.notice_rows.filter(has=self.page.locator("td:nth-child(2) div", has_text=title)).first

    def notice_title_cell(self, title: str):
        return self.notice_row(title).locator("td:nth-child(2) div").first

    def notice_dept(self, title: str):
        return self.notice_row(title).locator("td:nth-child(2) div:nth-child(2)")

    def notice_date(self, title: str):
        return self.notice_row(title).locator("td:nth-child(6)")

    def notice_badge(self, title: str):
        return self.notice_row(title).locator(".nbadge")

    def notice_status_button(self, title: str):
        return self.notice_row(title).locator("button.act-tog")

    def notice_pin_button(self, title: str):
        return self.notice_row(title).locator("button.act-pin")

    def notice_edit_link(self, title: str):
        return self.notice_row(title).locator("a.act-edit")

    def notice_delete_button(self, title: str):
        return self.notice_row(title).locator("button.act-del")

    # ── Reading ───────────────────────────────────────────────────────────────

    def rows_data(self) -> list[dict]:
        """Every row, in page order: title, dept, badge, badge_colour, status ('Active' / 'Hidden'),
        active (bool), pin ('Pinned' / 'Pin') and date."""
        return self.notice_rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const divs = r.cells[1].querySelectorAll('div'), badge = r.querySelector('.nbadge');
            return {title: t(divs[0]), dept: t(divs[1]), badge: t(badge),
                    badge_colour: badge ? getComputedStyle(badge).backgroundColor : '',
                    status: t(r.querySelector('button.act-tog')), active: !!r.querySelector('.dot-on'),
                    pin: t(r.querySelector('button.act-pin')), date: t(r.cells[5])};
        })""")

    def badge_preview_colour(self) -> str:
        return self.badge_preview.evaluate("e => getComputedStyle(e).backgroundColor")

    def attachment_file_count(self) -> int:
        return self.attachment_input.evaluate("e => e.files.length")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Admin Notices Management page")
    def open(self):
        self.navigate(NOTICES_URL)
        self.wait_for_load()

    @allure.step("Open Manage Notices with '?{query}'")
    def open_with(self, query: str):
        """e.g. 'edit=6' or 'badge=alert'."""
        self.navigate(f"{NOTICES_URL}?{query}")
        self.wait_for_load()

    @allure.step("Click '✕ Cancel Edit'")
    def cancel_edit(self):
        self.cancel_link.click()
        self.wait_for_load()

    @allure.step("Click Del for '{title}' and dismiss the prompt")
    def delete_notice_dismiss(self, title: str) -> str:
        return self.click_and_handle_alert(self.notice_delete_button(title), action="dismiss")

    @allure.step("Fill notice title: '{title}'")
    def fill_title(self, title: str):
        self.title_input.clear()
        self.title_input.fill(title)

    @allure.step("Fill notice body: '{body}'")
    def fill_body(self, body: str):
        self.body_textarea.clear()
        self.body_textarea.fill(body)

    @allure.step("Select badge type: '{badge}'")
    def select_badge(self, badge: str):
        self.badge_select.select_option(badge)

    @allure.step("Fill department: '{dept}'")
    def fill_department(self, dept: str):
        self.dept_input.clear()
        self.dept_input.fill(dept)

    @allure.step("Upload attachment file")
    def upload_attachment(self, file_path: str):
        self.attachment_input.set_input_files(file_path)

    @allure.step("Set pin checkbox to {checked}")
    def set_pin(self, checked: bool):
        if self.pin_checkbox.is_checked() != checked:
            self.pin_checkbox.click()

    @allure.step("Set active checkbox to {checked}")
    def set_active(self, checked: bool):
        if self.active_checkbox.is_checked() != checked:
            self.active_checkbox.click()

    @allure.step("Click Save / Add Notice button")
    def submit_form(self):
        self.save_button.click()
        self.wait_for_load()

    @allure.step("Click filter pill: '{label}'")
    def click_filter(self, label: str):
        self.filter_pill(label).click()
        self.wait_for_load()

    @allure.step("Click Edit for notice: '{title}'")
    def click_edit(self, title: str):
        self.notice_edit_link(title).click()
        self.wait_for_load()

    @allure.step("Click Delete for notice and confirm: '{title}'")
    def delete_notice(self, title: str) -> str:
        return self.click_and_handle_alert(
            self.notice_delete_button(title), action="accept"
        )

    @allure.step("Toggle active status for notice: '{title}'")
    def toggle_active(self, title: str):
        self.notice_status_button(title).click()
        self.wait_for_load()

    @allure.step("Toggle pin for notice: '{title}'")
    def toggle_pin(self, title: str):
        self.notice_pin_button(title).click()
        self.wait_for_load()

    @allure.step("Add notice with title '{title}', badge '{badge}'")
    def add_notice(
        self,
        title: str,
        body: str,
        badge: str = "info",
        dept: str = "",
        active: bool = True,
        pinned: bool = False,
        attachment_path: str = None,
    ):
        self.fill_title(title)
        self.fill_body(body)
        self.select_badge(badge)
        if dept:
            self.fill_department(dept)
        if attachment_path:
            self.upload_attachment(attachment_path)
        self.set_pin(pinned)
        self.set_active(active)
        self.submit_form()

    @allure.step("Deactivate all active notices in the table")
    def deactivate_all_active(self) -> list[str]:
        """Clicks the status toggle on every Active row until none remain.

        Active rows are matched by the green ``.dot-on`` indicator — matching the
        button's 'Active' label alone is unsafe because 'Inactive' contains it as
        a substring (Playwright ``:has-text`` is a case-insensitive substring
        match).

        Returns the titles of the notices it deactivated (captured before each
        toggle), so a cleanup step can re-activate exactly those — see
        :meth:`activate_notices`.
        """
        deactivated: list[str] = []
        guard = 0
        while self.page.locator("button.act-tog:has(.dot-on)").count() > 0:
            btn = self.page.locator("button.act-tog:has(.dot-on)").first
            row = btn.locator("xpath=ancestor::tr[1]")
            title = row.locator("div[style*='font-weight:600']").first.inner_text().strip()
            btn.click()
            self.wait_for_load()
            if title:
                deactivated.append(title)
            guard += 1
            if guard > 200:
                break
        return deactivated

    # ── Cleanup helpers ───────────────────────────────────────────────────────

    @allure.step("Re-activate the given notices")
    def activate_notices(self, titles) -> int:
        """Re-activates each notice in ``titles`` that is currently inactive.

        Cleanup helper for TC-244: pass the list returned by
        :meth:`deactivate_all_active` to restore exactly those notices (leaving
        notices that were already inactive untouched). A row is only toggled if
        it still shows the grey ``.dot-off`` indicator, so the call is safe to
        repeat. Returns the number of notices re-activated.
        """
        reactivated = 0
        for title in titles:
            toggle = self.notice_status_button(title)
            if toggle.count() > 0 and toggle.locator(".dot-off").count() > 0:
                toggle.click()
                self.wait_for_load()
                reactivated += 1
        return reactivated

    @allure.step("Delete every notice whose title is in the given list")
    def delete_notices_matching(self, titles) -> int:
        """Deletes all notice rows whose title matches any entry in ``titles``.

        Cleanup helper that removes notices created by the automation suite.
        Switches to the unfiltered 'All' view first so rows hidden behind a badge
        filter are still found. Returns the number of notices deleted.
        """
        self.click_filter("All")
        deleted = 0
        for title in titles:
            guard = 0
            while self.notice_row(title).count() > 0:
                self.delete_notice(title)
                self.wait_for_load()
                deleted += 1
                guard += 1
                if guard > 50:
                    break
        return deleted

    @allure.step("Logout from admin panel")
    def logout(self):
        self.sidebar.logout()
