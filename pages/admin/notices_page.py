import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

NOTICES_URL = f"{ADMIN_BASE}/notices/Admin%20notices%20manage.php"


class AdminNoticesPage(BasePage):
    """Admin Notices Management page object.

    Left panel: Add / Edit notice form.
    Right panel: Notice list table with badge-type filter pills.
    """

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

    # ── Filter pills ──────────────────────────────────────────────────────────

    def filter_pill(self, label: str):
        """Filter pill by partial visible text, e.g. 'Alert', 'All'."""
        return self.page.locator(f".n-pill:has-text('{label}')").first

    @property
    def active_filter_pill(self):
        return self.page.locator(".n-pill.on")

    # ── Notice table ──────────────────────────────────────────────────────────

    @property
    def notice_table(self):
        return self.page.locator(".ntbl")

    @property
    def notice_rows(self):
        return self.page.locator(".ntbl tbody tr")

    def notice_row(self, title: str):
        return self.page.locator(
            f".ntbl tbody tr:has-text('{title}')"
        ).first

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

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Admin Notices Management page")
    def open(self):
        self.navigate(NOTICES_URL)
        self.wait_for_load()

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
