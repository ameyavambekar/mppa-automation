import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage


class AdminAgenciesPage(BasePage):
    """Admin — All Agencies list (/module/admin/agency/list.php).

    Lists every registered agency with status filter tabs (``?status=`` query
    param), a client-side real-time search box (hides non-matching rows via
    ``display:none``), and per-row View / Status actions. Both actions are
    disabled (rendered as inert spans) until the agency submits its form.

    The Change Status modal (``#mod-status``) offers all six statuses plus a
    remarks textarea. Row locators are keyed by username (column 4), which is
    unique per agency account.
    """

    STATUS_FILTERS = ("all", "submitted", "approved", "rejected", "suspended")
    MODAL_STATUSES = ("submitted", "approved", "active", "rejected", "suspended", "inactive")

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Page header ───────────────────────────────────────────────────────────

    @property
    def page_title(self):
        # "🏢 All Agencies (27)"
        return self.page.locator(".adm-page-title span").first

    # ── Filter tabs & search ──────────────────────────────────────────────────

    def filter_tab(self, status: str):
        """status: one of STATUS_FILTERS."""
        return self.page.locator(f"a.filter-tab[href='?status={status}']")

    @property
    def active_filter_tab(self):
        return self.page.locator("a.filter-tab.on")

    def filter_tab_count(self, status: str):
        return self.filter_tab(status).locator("span")

    @property
    def search_input(self):
        # Client-side filter — hides rows as you type (no submit needed)
        return self.page.locator("input.ssrch")

    # ── Agencies table ────────────────────────────────────────────────────────

    @property
    def agencies_table(self):
        return self.page.locator("table.stbl")

    @property
    def table_headers(self):
        return self.page.locator("table.stbl thead th")

    def table_header(self, label: str):
        return self.page.locator(
            f"//table[contains(@class,'stbl')]//thead//th[normalize-space(text())='{label}']"
        )

    @property
    def agency_rows(self):
        return self.page.locator("#ag-tbody > tr")

    @property
    def visible_agency_rows(self):
        """Rows not hidden by the client-side search filter."""
        return self.page.locator("#ag-tbody > tr:visible")

    def agency_row(self, username: str):
        return self.page.locator(
            f"//tbody[@id='ag-tbody']/tr[td[4][normalize-space(text())='{username}']]"
        )

    def rows_with_status(self, status: str):
        """Main rows whose status badge shows the given status text."""
        return self.page.locator(
            f"//tbody[@id='ag-tbody']/tr[td[9]/span[normalize-space(text())='{status}']]"
        )

    def viewable_rows_with_status(self, status: str):
        """Rows in the given status whose View/Status actions are enabled
        (i.e. the agency has submitted its form)."""
        return self.page.locator(
            f"//tbody[@id='ag-tbody']/tr[td[9]/span[normalize-space(text())='{status}']"
            f" and .//a[contains(@class,'btn-view-on')]]"
        )

    # -- Cells within a row --

    def reg_id_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(1)

    def agency_name_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(2).locator("p").first

    def email_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(4)

    def pan_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(5)

    def reg_ip_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(6)

    def registered_on_cell(self, username: str):
        return self.agency_row(username).locator("td").nth(7)

    def status_badge(self, username: str):
        return self.agency_row(username).locator("td").nth(8).locator("span")

    def view_button(self, username: str):
        # Enabled variant — a link to ../dashboard/agency_view.php?id=N
        return self.agency_row(username).locator("a.btn-view-on")

    def view_button_disabled(self, username: str):
        return self.agency_row(username).locator("span.btn-view-off")

    def status_button(self, username: str):
        return self.agency_row(username).locator("button.btn-status-on")

    def status_button_disabled(self, username: str):
        return self.agency_row(username).locator("span.btn-status-off")

    # ── Change Status modal (#mod-status) ─────────────────────────────────────

    @property
    def status_modal(self):
        return self.page.locator("#mod-status")

    @property
    def status_modal_username(self):
        return self.page.locator("#ms-username")

    @property
    def status_modal_select(self):
        return self.page.locator("#ms-status")

    @property
    def status_modal_remarks(self):
        return self.status_modal.locator("textarea[name='remarks']")

    @property
    def status_modal_update_button(self):
        return self.status_modal.locator("button[type='submit']")

    @property
    def status_modal_cancel_button(self):
        return self.status_modal.locator("//button[normalize-space(text())='Cancel']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the All Agencies list directly")
    def open(self):
        import os
        base = os.getenv("MPPA_ADMIN_BASE_URL", "https://devmppa.sppuef.in/module/admin")
        self.navigate(f"{base}/agency/list.php")

    @allure.step("Filter agencies by status tab: {status}")
    def filter_by_status(self, status: str):
        self.filter_tab(status).click()

    @allure.step("Type into the real-time search box: {query}")
    def search(self, query: str):
        # Filtering happens on input — no submit button
        self.search_input.fill(query)

    @allure.step("Clear the search box")
    def clear_search(self):
        self.search_input.fill("")

    @allure.step("Click 'View' for agency: {username}")
    def click_view(self, username: str):
        self.view_button(username).click()

    @allure.step("Open the Change Status modal for agency: {username}")
    def open_status_modal(self, username: str):
        self.status_button(username).click()

    @allure.step("Change status of '{username}' to '{new_status}'")
    def change_status(self, username: str, new_status: str, remarks: str = ""):
        """Changes an agency's status through the list's Change Status modal.
        new_status: one of MODAL_STATUSES."""
        self.open_status_modal(username)
        self.status_modal_select.select_option(value=new_status)
        if remarks:
            self.status_modal_remarks.fill(remarks)
        self.status_modal_update_button.click()
        self.wait_for_load()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_row_status(self, username: str) -> str:
        return self.status_badge(username).text_content().strip()

    def get_username_of_row(self, row) -> str:
        """Username (column 4) of a row locator."""
        return row.locator("td").nth(3).text_content().strip()

    def get_first_viewable_username(self, status: str) -> str:
        """Username of the first form-submitted agency in the given status,
        or '' when none exists."""
        rows = self.viewable_rows_with_status(status)
        if rows.count() == 0:
            return ""
        return self.get_username_of_row(rows.first)

    def get_filter_tab_count(self, status: str) -> int:
        return int(self.filter_tab_count(status).text_content().strip().replace(",", ""))
