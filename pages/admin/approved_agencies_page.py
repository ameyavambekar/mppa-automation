import re
from datetime import datetime

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE


class AdminApprovedAgenciesPage(BasePage):
    """Admin — Approved Agencies dashboard (/module/admin/agency/approve.php).

    Lists every approved agency with its MPPA registration number, approval
    metadata, certificate validity and current standing. Provides status filter
    chips (Total / Active / Expiring / Expired / Suspended / Revoked — applied
    via the ``?status=`` query param), a search toolbar, sortable columns,
    expandable per-agency detail rows, and per-row actions (View Certificate,
    Full Application, Revoke / Reinstate).

    Table rows are keyed by agency name. Each main row (``onclick="togDet(id)"``)
    is followed by a hidden ``tr.det-row#det-<id>`` detail row that toggles open
    when the main row is clicked.

    Revoking goes through the in-page Revoke modal (``#revoke-mod``) — clicking a
    row's 🚫 Revoke button opens it; it carries a *required* reason textarea and
    POSTs ``_action=revoke_license``. (This differs from the Licenses dashboard,
    which revokes via a JS ``confirm()`` dialog.) Revoked rows instead expose a
    Reinstate action.
    """

    # ?status= values accepted by the filter chips ('all' is the 'Total' chip)
    STATUS_FILTERS = ("all", "active", "expiring", "expired", "suspended", "revoked")

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
        # "✅ Approved Agencies (4 records)"
        return self.page.locator(".adm-page-title span").first

    # ── Status filter chips ───────────────────────────────────────────────────

    def stat_chip(self, status: str):
        """status: one of STATUS_FILTERS ('all' is the 'Total' chip)."""
        return self.page.locator(f"a.sc[href*='status={status}']")

    def stat_chip_count(self, status: str):
        """The big number on a filter chip."""
        return self.stat_chip(status).locator(".n")

    def stat_chip_label(self, status: str):
        """The label text on a filter chip, e.g. 'Total', 'Active', 'Suspended'."""
        return self.stat_chip(status).locator(".l")

    @property
    def selected_stat_chip(self):
        # The currently applied filter (carries the 'sel' class)
        return self.page.locator("a.sc.sel")

    # ── Toolbar ───────────────────────────────────────────────────────────────

    @property
    def search_input(self):
        return self.page.locator("input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("//button[normalize-space(text())='Search']")

    # ── Approved agencies table ───────────────────────────────────────────────

    @property
    def agencies_table(self):
        return self.page.locator("table.tb")

    @property
    def table_headers(self):
        return self.page.locator("table.tb thead th")

    def table_header(self, label: str):
        """A column header by its label, e.g. 'MPPA Reg No.', 'Days Left'."""
        return self.page.locator(
            f"//table[contains(@class,'tb')]//thead//th[contains(normalize-space(.),'{label}')]"
        )

    @property
    def agency_rows(self):
        """Main data rows only (detail rows excluded)."""
        return self.page.locator("table.tb tbody tr:not(.det-row)")

    def rows_with_status(self, status: str):
        """Status badges of all main rows in a given state. status: 'active',
        'expiring', 'expired', 'suspended' or 'revoked'."""
        return self.page.locator(f"table.tb tbody tr:not(.det-row) .lb.lb-{status}")

    def sort_link(self, field: str):
        """Column-header sort link. field: 'mppa_number', 'agency_name',
        'approved_at', 'valid_upto' or 'days_left'."""
        return self.page.locator(f"table.tb thead a[href*='sort={field}']")

    def agency_row(self, agency_name: str):
        return self.page.locator("table.tb tbody tr:not(.det-row)", has_text=agency_name)

    def mppa_reg_no(self, agency_name: str):
        return self.agency_row(agency_name).locator(".mppa")

    def agency_name_cell(self, agency_name: str):
        return self.agency_row(agency_name).locator("td").nth(2)

    def approved_on_cell(self, agency_name: str):
        return self.agency_row(agency_name).locator("td").nth(3)

    def approved_by_cell(self, agency_name: str):
        # Admin chip + approval IP
        return self.agency_row(agency_name).locator("td").nth(4)

    def approved_by_chip(self, agency_name: str):
        return self.approved_by_cell(agency_name).locator(".admin-chip")

    def valid_till_cell(self, agency_name: str):
        return self.agency_row(agency_name).locator("td").nth(5)

    def days_left_cell(self, agency_name: str):
        # e.g. "1821 days" / "14d overdue" / "Suspended", plus a progress bar
        return self.agency_row(agency_name).locator("td").nth(6)

    def days_left_bar_fill(self, agency_name: str):
        return self.agency_row(agency_name).locator(".bar-f")

    def status_badge(self, agency_name: str):
        # Carries class lb-active / lb-expiring / lb-expired / lb-suspended / lb-revoked
        return self.agency_row(agency_name).locator(".lb")

    def view_certificate_link(self, agency_name: str):
        # "📜 Cert" — opens the MPPA certificate in a new tab
        return self.agency_row(agency_name).locator("a.btn-v")

    def view_application_link(self, agency_name: str):
        # "👁" — full application view
        return self.agency_row(agency_name).locator("a.btn-g")

    def revoke_button(self, agency_name: str):
        # "🚫 Revoke" — opens the Revoke modal (rendered for non-revoked rows)
        return self.agency_row(agency_name).locator("button.btn-r")

    def reinstate_button(self, agency_name: str):
        # "↻ Reinstate" — only rendered for already-revoked rows
        return self.agency_row(agency_name).locator(
            "//button[contains(normalize-space(.),'Reinstate')]"
        )

    # ── Expandable detail row ─────────────────────────────────────────────────

    def detail_row(self, agency_name: str):
        """The hidden detail row right after the agency's main row (gets the
        'open' class when expanded)."""
        return self.agency_row(agency_name).locator("xpath=following-sibling::tr[1]")

    def detail_field(self, agency_name: str, key: str):
        """A detail value by its label, e.g. 'PAN', 'Email', 'Approved On',
        'Valid Till', 'Days Remaining', 'Approval IP', 'Jurisdiction',
        'Admin Remarks'."""
        return self.detail_row(agency_name).locator(
            f"//div[@class='df'][div[@class='dk' and normalize-space(text())='{key}']]/div[@class='dv']"
        )

    def detail_view_certificate_link(self, agency_name: str):
        return self.detail_row(agency_name).locator(
            "//a[contains(normalize-space(.),'View MPPA Certificate')]"
        )

    def detail_view_application_link(self, agency_name: str):
        return self.detail_row(agency_name).locator(
            "//a[contains(normalize-space(.),'Full Application')]"
        )

    # ── Revoke modal (#revoke-mod) ────────────────────────────────────────────

    @property
    def revoke_modal(self):
        return self.page.locator("#revoke-mod")

    @property
    def revoke_modal_agency_name(self):
        # The agency name echoed in the modal title (#rev-name)
        return self.page.locator("#rev-name")

    @property
    def revoke_reason_textarea(self):
        return self.revoke_modal.locator("textarea[name='reason']")

    @property
    def revoke_confirm_button(self):
        # "🚫 Confirm Revoke"
        return self.revoke_modal.locator("button[type='submit']")

    @property
    def revoke_cancel_button(self):
        return self.revoke_modal.locator("//button[normalize-space(text())='Cancel']")

    @property
    def revoke_close_button(self):
        return self.revoke_modal.locator("//button[normalize-space(text())='✕']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Approved Agencies dashboard directly")
    def open(self):
        self.navigate(f"{ADMIN_BASE}/agency/approve.php")

    @allure.step("Filter approved agencies by status: {status}")
    def filter_by_status(self, status: str):
        """status: one of STATUS_FILTERS."""
        self.stat_chip(status).click()

    @allure.step("Search approved agencies for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()

    @allure.step("Sort table by: {field}")
    def sort_by(self, field: str):
        self.sort_link(field).click()

    @allure.step("Toggle detail row for agency: {agency_name}")
    def toggle_detail_row(self, agency_name: str):
        self.agency_row(agency_name).click()

    @allure.step("Open certificate for agency: {agency_name}")
    def open_certificate(self, agency_name: str):
        """Clicks '📜 Cert' and returns the new tab's Page object (the
        certificate opens with target=_blank)."""
        with self.page.context.expect_page() as new_page_info:
            self.view_certificate_link(agency_name).click()
        return new_page_info.value

    @allure.step("Open full application view for agency: {agency_name}")
    def open_application_view(self, agency_name: str):
        self.view_application_link(agency_name).click()

    # -- Revoke modal actions --

    @allure.step("Open the Revoke modal for agency: {agency_name}")
    def open_revoke_modal(self, agency_name: str):
        self.revoke_button(agency_name).click()

    @allure.step("Fill the revocation reason")
    def fill_revoke_reason(self, reason: str):
        self.revoke_reason_textarea.fill(reason)

    @allure.step("Confirm the revocation")
    def confirm_revoke(self):
        self.revoke_confirm_button.click()
        self.wait_for_load()

    @allure.step("Cancel the Revoke modal")
    def cancel_revoke_modal(self):
        self.revoke_cancel_button.click()

    @allure.step("Revoke license for agency: {agency_name}")
    def revoke_agency(self, agency_name: str, reason: str):
        """Opens the Revoke modal from the agency's row, fills the required
        reason and submits."""
        self.open_revoke_modal(agency_name)
        self.fill_revoke_reason(reason)
        self.confirm_revoke()

    @allure.step("Reinstate agency: {agency_name}")
    def reinstate_agency(self, agency_name: str):
        """Clicks the '↻ Reinstate' action on an already-revoked agency's row."""
        self.reinstate_button(agency_name).click()
        self.wait_for_load()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_agency_name(self, row_index: int = 0) -> str:
        """Agency name shown in the given main row (0-based)."""
        cell = self.agency_rows.nth(row_index).locator("td").nth(2).locator("div").first
        return cell.text_content().strip()

    def get_row_status(self, agency_name: str) -> str:
        return self.status_badge(agency_name).text_content().strip()

    def get_mppa_reg_no(self, agency_name: str) -> str:
        return self.mppa_reg_no(agency_name).text_content().strip()

    def get_valid_till(self, agency_name: str) -> str:
        """Agency's 'Valid Till' date as an ISO yyyy-mm-dd string, parsed from
        the table's 'dd Mon yyyy' display format."""
        match = re.search(r"\d{1,2} \w{3} \d{4}", self.valid_till_cell(agency_name).text_content())
        return datetime.strptime(match.group(), "%d %b %Y").date().isoformat()

    def get_revoke_reason_validation_message(self) -> str:
        """The native HTML5 validation message on the required reason textarea
        (non-empty after attempting to confirm with no reason given)."""
        return self.revoke_reason_textarea.evaluate("el => el.validationMessage")

    def get_stat_chip_count(self, status: str) -> int:
        """Numeric count on a filter chip."""
        return int(self.stat_chip_count(status).text_content().strip().replace(",", ""))

    def count_rows_with_status(self, status: str) -> int:
        """Number of table rows currently in the given state."""
        return self.rows_with_status(status).count()
