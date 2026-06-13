import re
from datetime import datetime

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage


class AdminLicensesPage(BasePage):
    """Admin — Agency Licenses & Certificates dashboard
    (/module/admin/licenses/licenses.php).

    Lists all approved agencies with certificate validity, status filter chips
    (Approved / Active / Expiring / Expired / Revoked — applied via the
    ``?status=`` query param), a search toolbar, expandable per-agency detail
    rows, and the Issue / Renew License modal (``#iss-mod``).

    Table rows are keyed by agency name. Each main row is followed by a hidden
    ``tr.det-row`` detail row that toggles open when the main row is clicked.
    Revoking a license fires a JS ``confirm()`` dialog — handled via the
    base-page dialog pattern.
    """

    # ?status= values accepted by the filter chips
    STATUS_FILTERS = ("all", "active", "expiring", "expired", "revoked")

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
        # "📋 Agency Licenses & Certificates (3 approved agencies)"
        return self.page.locator(".adm-page-title span").first

    @property
    def info_box(self):
        # "ℹ️ How this works: ..." explainer banner
        return self.page.locator(".info-box")

    # ── Status filter chips ───────────────────────────────────────────────────

    def stat_chip(self, status: str):
        """status: one of STATUS_FILTERS ('all' is the 'Approved' chip)."""
        return self.page.locator(f"a.sc[href*='status={status}']")

    def stat_chip_count(self, status: str):
        """The big number on a filter chip."""
        return self.stat_chip(status).locator(".n")

    def stat_chip_label(self, status: str):
        """The label text on a filter chip, e.g. 'Approved', 'Expiring (30d)'."""
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

    @property
    def issue_renew_button(self):
        # "📋 Issue / Renew License" — opens the modal in Issue mode
        return self.page.locator("//button[contains(normalize-space(.),'Issue / Renew License')]")

    # ── Alerts ────────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".salt-s")

    @property
    def error_alert(self):
        return self.page.locator(".salt-e")

    # ── Licenses table ────────────────────────────────────────────────────────

    @property
    def licenses_table(self):
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
    def license_rows(self):
        """Main data rows only (detail rows excluded)."""
        return self.page.locator("table.tb tbody tr:not(.det-row)")

    def rows_with_status(self, status: str):
        """Status badges of all main rows in a given state.
        status: 'active', 'expiring', 'expired' or 'revoked'."""
        return self.page.locator(f"table.tb tbody tr:not(.det-row) .lb.lb-{status}")

    def sort_link(self, field: str):
        """Column-header sort link. field: 'agency_name', 'eff_start',
        'eff_valid_upto' or 'days_left'."""
        return self.page.locator(f"table.tb thead a[href*='sort={field}']")

    def license_row(self, agency_name: str):
        return self.page.locator("table.tb tbody tr:not(.det-row)", has_text=agency_name)

    def mppa_reg_no(self, agency_name: str):
        return self.license_row(agency_name).locator(".mppa")

    def license_no_cell(self, agency_name: str):
        # Shows the license number, or italic "Auto" when none recorded
        return self.license_row(agency_name).locator("td").nth(3)

    def valid_from_cell(self, agency_name: str):
        return self.license_row(agency_name).locator("td").nth(4)

    def valid_upto_cell(self, agency_name: str):
        return self.license_row(agency_name).locator("td").nth(5)

    def days_left_cell(self, agency_name: str):
        # e.g. "1823 days" / "12d overdue", plus the progress bar
        return self.license_row(agency_name).locator("td").nth(6)

    def days_left_bar_fill(self, agency_name: str):
        return self.license_row(agency_name).locator(".bar-f")

    def status_badge(self, agency_name: str):
        # Carries class lb-active / lb-expiring / lb-expired / lb-revoked
        return self.license_row(agency_name).locator(".lb")

    def view_certificate_link(self, agency_name: str):
        # "📜 View Cert" — opens MPPA FORM-II certificate in a new tab
        return self.license_row(agency_name).locator("a.btn-o")

    def renew_button(self, agency_name: str):
        return self.license_row(agency_name).locator("//button[contains(normalize-space(.),'Renew')]")

    def revoke_button(self, agency_name: str):
        # Only rendered for rows with an issued license (e.g. expired ones)
        return self.license_row(agency_name).locator("form button[type='submit']")

    def view_application_link(self, agency_name: str):
        # "👁 View" — full application view
        return self.license_row(agency_name).locator("a.btn-g")

    # ── Expandable detail row ─────────────────────────────────────────────────

    def detail_row(self, agency_name: str):
        """The hidden detail row right after the agency's main row (gets the
        'open' class when expanded)."""
        return self.license_row(agency_name).locator("xpath=following-sibling::tr[1]")

    def detail_field(self, agency_name: str, key: str):
        """A detail value by its label, e.g. 'Email', 'PAN', 'Approval Date',
        'Days Remaining', 'Approved By', 'Valid Upto (approvals)'."""
        return self.detail_row(agency_name).locator(
            f"//div[@class='df'][div[@class='dk' and normalize-space(text())='{key}']]/div[@class='dv']"
        )

    def detail_view_certificate_link(self, agency_name: str):
        return self.detail_row(agency_name).locator("//a[contains(normalize-space(.),'View Full Certificate')]")

    def detail_view_application_link(self, agency_name: str):
        return self.detail_row(agency_name).locator("//a[contains(normalize-space(.),'View Full Application')]")

    # ── Issue / Renew modal (#iss-mod) ────────────────────────────────────────

    @property
    def issue_modal(self):
        return self.page.locator("#iss-mod")

    @property
    def issue_modal_title(self):
        # "📋 Issue License" or "🔄 Renew — <agency name>"
        return self.page.locator("#mod-ttl-txt")

    @property
    def modal_agency_select(self):
        # Disabled (pre-selected) when opened via a row's Renew button
        return self.page.locator("#mod-agency")

    @property
    def modal_selected_agency_option(self):
        # The currently selected <option> in the agency dropdown
        return self.modal_agency_select.locator("option:checked")

    @property
    def modal_quick_duration_buttons(self):
        # All four +N Year(s) shortcut buttons
        return self.issue_modal.locator("button[onclick^='setDur']")

    @property
    def modal_license_number_input(self):
        return self.page.locator("#mod-lic")

    @property
    def modal_valid_from_input(self):
        return self.page.locator("#mod-start")

    @property
    def modal_valid_upto_input(self):
        return self.page.locator("#mod-upto")

    def modal_quick_duration_button(self, years: int):
        """years: 1, 2, 3 or 5 — sets Valid Upto to start date + N years."""
        label = f"+{years} Year" + ("s" if years > 1 else "")
        return self.issue_modal.locator(f"//button[normalize-space(text())='{label}']")

    @property
    def modal_notes_textarea(self):
        return self.page.locator("#mod-notes")

    @property
    def modal_save_button(self):
        # "💾 Save — Updates agency_approvals"
        return self.issue_modal.locator("button[type='submit']")

    @property
    def modal_cancel_button(self):
        return self.issue_modal.locator("//button[normalize-space(text())='Cancel']")

    @property
    def modal_close_button(self):
        return self.issue_modal.locator("//button[normalize-space(text())='✕']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Licenses dashboard directly")
    def open(self):
        import os
        base = os.getenv("MPPA_ADMIN_BASE_URL", "https://devmppa.sppuef.in/module/admin")
        self.navigate(f"{base}/licenses/licenses.php")

    @allure.step("Filter licenses by status: {status}")
    def filter_by_status(self, status: str):
        """status: one of STATUS_FILTERS."""
        self.stat_chip(status).click()

    @allure.step("Search licenses for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()

    @allure.step("Sort table by: {field}")
    def sort_by(self, field: str):
        self.sort_link(field).click()

    @allure.step("Toggle detail row for agency: {agency_name}")
    def toggle_detail_row(self, agency_name: str):
        self.license_row(agency_name).click()

    @allure.step("Open certificate for agency: {agency_name}")
    def open_certificate(self, agency_name: str):
        """Clicks '📜 View Cert' and returns the new tab's Page object
        (the certificate opens with target=_blank)."""
        with self.page.context.expect_page() as new_page_info:
            self.view_certificate_link(agency_name).click()
        return new_page_info.value

    @allure.step("Open full application view for agency: {agency_name}")
    def open_application_view(self, agency_name: str):
        self.view_application_link(agency_name).click()

    @allure.step("Revoke license for agency '{agency_name}' (confirm dialog: {action})")
    def revoke_license(self, agency_name: str, action: str = "accept") -> str:
        """Clicks the row's revoke (🚫) button and answers the
        'Revoke this license?' confirm dialog. Returns the dialog message."""
        return self.click_and_handle_alert(self.revoke_button(agency_name), action=action)

    # -- Issue / Renew modal actions --

    @allure.step("Open the Issue License modal")
    def open_issue_modal(self):
        self.issue_renew_button.click()

    @allure.step("Open the Renew modal for agency: {agency_name}")
    def open_renew_modal(self, agency_name: str):
        """Opens the modal pre-filled with the agency's current validity dates
        (agency select is locked in this mode)."""
        self.renew_button(agency_name).click()

    @allure.step("Select agency in modal: {agency_id}")
    def select_modal_agency(self, agency_id: str):
        self.modal_agency_select.select_option(value=str(agency_id))

    @allure.step("Fill modal License Number: {license_number}")
    def fill_modal_license_number(self, license_number: str):
        self.modal_license_number_input.fill(license_number)

    @allure.step("Fill modal Valid From: {date}")
    def fill_modal_valid_from(self, date: str):
        """date in yyyy-mm-dd format."""
        self.modal_valid_from_input.fill(date)

    @allure.step("Fill modal Valid Upto: {date}")
    def fill_modal_valid_upto(self, date: str):
        """date in yyyy-mm-dd format."""
        self.modal_valid_upto_input.fill(date)

    @allure.step("Click quick duration: +{years} year(s)")
    def click_quick_duration(self, years: int):
        self.modal_quick_duration_button(years).click()

    @allure.step("Fill modal Remarks / Notes")
    def fill_modal_notes(self, notes: str):
        self.modal_notes_textarea.fill(notes)

    @allure.step("Save the Issue / Renew modal")
    def save_modal(self):
        self.modal_save_button.click()

    @allure.step("Cancel the Issue / Renew modal")
    def cancel_modal(self):
        self.modal_cancel_button.click()

    @allure.step("Issue license to agency {agency_id}")
    def issue_license(self, agency_id: str, valid_from: str, valid_upto: str = None,
                      duration_years: int = None, license_number: str = None,
                      notes: str = None):
        """Opens the Issue modal and submits it. Provide either valid_upto
        (yyyy-mm-dd) or duration_years (1/2/3/5 — uses the quick-duration
        buttons)."""
        self.open_issue_modal()
        self.select_modal_agency(agency_id)
        if license_number is not None:
            self.fill_modal_license_number(license_number)
        self.fill_modal_valid_from(valid_from)
        if valid_upto is not None:
            self.fill_modal_valid_upto(valid_upto)
        elif duration_years is not None:
            self.click_quick_duration(duration_years)
        if notes is not None:
            self.fill_modal_notes(notes)
        self.save_modal()

    @allure.step("Renew license for agency: {agency_name}")
    def renew_license(self, agency_name: str, valid_from: str = None,
                      valid_upto: str = None, duration_years: int = None,
                      license_number: str = None, notes: str = None):
        """Opens the Renew modal from the agency's row (dates arrive
        pre-filled) and overrides only the supplied values before saving."""
        self.open_renew_modal(agency_name)
        if license_number is not None:
            self.fill_modal_license_number(license_number)
        if valid_from is not None:
            self.fill_modal_valid_from(valid_from)
        if valid_upto is not None:
            self.fill_modal_valid_upto(valid_upto)
        elif duration_years is not None:
            self.click_quick_duration(duration_years)
        if notes is not None:
            self.fill_modal_notes(notes)
        self.save_modal()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_agency_name(self, row_index: int = 0) -> str:
        """Agency name shown in the given main row (0-based)."""
        cell = self.license_rows.nth(row_index).locator("td").nth(1).locator("div").first
        return cell.text_content().strip()

    def get_row_validity_dates(self, agency_name: str) -> tuple:
        """(valid_from, valid_upto) for an agency's row as ISO yyyy-mm-dd
        strings, parsed from the table's 'dd Mon yyyy' display format."""
        def _iso(cell_text: str) -> str:
            match = re.search(r"\d{1,2} \w{3} \d{4}", cell_text)
            return datetime.strptime(match.group(), "%d %b %Y").date().isoformat()

        return (
            _iso(self.valid_from_cell(agency_name).text_content()),
            _iso(self.valid_upto_cell(agency_name).text_content()),
        )

    def get_modal_agency_validation_message(self) -> str:
        """The native HTML5 validation message on the required agency select
        (non-empty after attempting to save with no agency chosen)."""
        return self.modal_agency_select.evaluate("el => el.validationMessage")

    def get_stat_chip_count(self, status: str) -> int:
        """Numeric count on a filter chip."""
        return int(self.stat_chip_count(status).text_content().strip())

    def count_rows_with_status(self, status: str) -> int:
        """Number of table rows currently in the given license state."""
        return self.rows_with_status(status).count()
