import re
from datetime import datetime

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

ADMIN_LICENSES_URL = f"{ADMIN_BASE}/licenses/licenses.php"


class AdminLicensesPage(BasePage):
    """Admin — Agency Licenses & Certificates (/module/admin/licenses/licenses.php), Registry ›
    Licences & certificates.

    Lists every approved agency's certificate with its validity, status filter chips (Approved /
    Active / Expiring / Expired / Revoked — ``?status=``), search (``q``), sortable columns, an
    expandable detail row per agency, the Issue / Renew modal (``#iss-mod``), the certificate action
    dialog (``#caModal`` — suspend / lift / expire / cancel / reinstate, each with a reason) and the
    certificate history (``#chModal``).

    Table rows are keyed by agency name (matched exactly — "Skillsphere" and "Skillsphere123" are
    different agencies). Each main row is followed by a hidden ``tr.det-row`` that opens when the row
    is clicked. A confirmed certificate action shows a toast and reloads the page 0.9 s later.
    """

    # ?status= values accepted by the filter chips ('all' is the Approved chip)
    STATUS_FILTERS = ("all", "active", "expiring", "expired", "revoked")
    COLUMNS = ("#", "Agency", "Registration No.", "Valid From", "Valid Upto", "Days Left", "Status",
               "Certificate", "Actions")
    EMPTY_TABLE = "No approved agencies found."
    HISTORY_EMPTY = "No certificate actions yet."
    # Certificate action → (row button, dialog title, explanation, confirm button, minimum reason length)
    CERTIFICATE_ACTIONS = {
        "suspend": ("Suspend", "Suspend certificate", "The agency cannot operate during the suspension.",
                    "Suspend", 20),
        "lift": ("Lift suspension", "Lift suspension", "The certificate becomes active again immediately.",
                 "Lift suspension", 10),
        "expire": ("Expire", "Expire certificate",
                   "The certificate becomes expired today. The agency must apply for renewal.", "Expire now", 20),
        "cancel": ("Cancel", "Cancel registration certificate",
                   "Cancels the registration (Sec 6). The agency may appeal.", "Cancel certificate", 20),
        "reinstate": ("Reinstate", "Reinstate certificate", "Makes the certificate active again.", "Reinstate", 20),
    }

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Topbar / page header ──────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        # e.g. "Super Administrator"
        return self.page.locator("#adm-topbar .tb-role")

    @property
    def page_title(self):
        # "Agency Licenses & Certificates (9 approved agencies)" — the count follows the chosen chip
        return self.page.locator(".adm-page-title span").first

    @property
    def page_clock(self):
        # "03 Nov 2026 · 11:07"
        return self.page.locator(".adm-page-title .pg-date")

    @property
    def info_box(self):
        # "Who can do what: District officer — …"
        return self.page.locator(".info-box")

    # ── Status filter chips ───────────────────────────────────────────────────

    def stat_chip(self, status: str):
        """status: one of STATUS_FILTERS ('all' is the 'Approved' chip)."""
        return self.page.locator(f"a.sc[href*='status={status}&']")

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
        return self.page.locator("#adm-main input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("#adm-main button[type='submit']", has_text="Search")

    @property
    def issue_renew_button(self):
        # "Issue / Renew License" — opens the modal in Issue mode
        return self.page.locator("#adm-main button[onclick='openIssue()']")

    @property
    def renewal_applications_link(self):
        return self.page.locator("#adm-main a.btn-p[href*='renewals.php']")

    @property
    def toast(self):
        # Portal.toast — e.g. "Certificate suspended until 04 Nov 2026, 11:24 AM. …"
        return self.page.locator("#uiToasts .ui-toast")

    # ── Licences table ────────────────────────────────────────────────────────

    @property
    def licenses_table(self):
        return self.page.locator("table.tb")

    @property
    def table_headers(self):
        return self.page.locator("table.tb thead th")

    def table_header(self, label: str):
        """A column header by its label, e.g. 'Registration No.', 'Days Left'."""
        return self.table_headers.filter(has_text=label)

    @property
    def license_rows(self):
        """Main data rows only (detail rows and the empty-table row excluded)."""
        return self.page.locator("table.tb tbody tr:not(.det-row):not(:has(td[colspan]))")

    @property
    def empty_table_row(self):
        # "No approved agencies found."
        return self.page.locator("table.tb tbody td[colspan]")

    def table_data(self) -> list[dict]:
        """Every main row read in one go: agency, registration_no (the agency's Application ID),
        valid_upto ("DD Mon YYYY"), status (the ``.lb`` label, e.g. "Active") and email (from the
        detail row)."""
        return self.license_rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const c = r.cells, det = r.nextElementSibling;
            const email = det ? [...det.querySelectorAll('.df')].find(f => t(f.querySelector('.dk')) === 'Email') : null;
            return {agency: t(c[1].querySelector('div')), registration_no: t(c[2].querySelector('.mppa')),
                    valid_upto: t(c[4]).replace(/\\s*✓$/, ''), status: t(r.querySelector('.lb')),
                    email: email ? t(email.querySelector('.dv')) : ''};
        })""")

    def rows_with_status(self, status: str):
        """Status labels of all main rows in a given state.
        status: 'active', 'expiring', 'expired' or 'revoked' (the label's ``lb-<status>`` class)."""
        return self.license_rows.locator(f".lb.lb-{status}")

    def sort_link(self, field: str):
        """Column-header sort link. field: 'agency_name', 'eff_start',
        'eff_valid_upto' or 'days_left'."""
        return self.page.locator(f"table.tb thead a[href*='sort={field}&']")

    def license_row(self, agency_name: str):
        name = re.compile(rf"^\s*{re.escape(agency_name)}\s*$")
        return self.license_rows.filter(
            has=self.page.locator("td:nth-child(2) > div:first-child").filter(has_text=name))

    def _cell(self, agency_name: str, index: int):
        return self.license_row(agency_name).locator("td").nth(index)

    def agency_location(self, agency_name: str):
        # "City, State" under the agency name
        return self._cell(agency_name, 1).locator("div").nth(1)

    def registration_no(self, agency_name: str):
        return self._cell(agency_name, 2).locator(".mppa")

    def registration_cell(self, agency_name: str):
        # The Application ID, plus "✓ approvals" when the dates come from the approval record
        return self._cell(agency_name, 2)

    def valid_from_cell(self, agency_name: str):
        return self._cell(agency_name, 3)

    def valid_upto_cell(self, agency_name: str):
        return self._cell(agency_name, 4)

    def days_left_cell(self, agency_name: str):
        # e.g. "1823 days" / "12d overdue", plus the bar
        return self._cell(agency_name, 5)

    def days_left_bar_fill(self, agency_name: str):
        return self.license_row(agency_name).locator(".bar-f")

    def status_badge(self, agency_name: str):
        # Class lb-active / lb-expiring / lb-expired / lb-revoked; text e.g. "Active", "Expiring (26d)",
        # "Suspended till 04 Nov 2026", "Cancelled"
        return self.license_row(agency_name).locator(".lb")

    def view_certificate_link(self, agency_name: str):
        # "View Cert" — the MPPA FORM-II certificate in a new tab
        return self._cell(agency_name, 7).locator("a")

    def action_buttons(self, agency_name: str):
        """Every button / link in the row's Actions cell."""
        return self._cell(agency_name, 8).locator("button, a")

    def action_button(self, agency_name: str, label: str):
        """An Actions-cell button by its exact label: Suspend, Lift suspension, Expire, Cancel, Reinstate,
        History, Issue, Renew, Revoke or View."""
        return self.action_buttons(agency_name).filter(has_text=re.compile(rf"^\s*{re.escape(label)}\s*$"))

    def renew_button(self, agency_name: str):
        # "Renew" when the dates come from the approval record, otherwise "Issue" — both open the modal
        return self._cell(agency_name, 8).locator("button[onclick*='openRenew']")

    def view_application_link(self, agency_name: str):
        return self.action_button(agency_name, "View")

    def revoke_button(self, agency_name: str):
        return self.action_button(agency_name, "Revoke")

    # ── Expandable detail row ─────────────────────────────────────────────────

    def detail_row(self, agency_name: str):
        """The hidden detail row right after the agency's main row (gets the
        'open' class when expanded)."""
        return self.license_row(agency_name).locator("xpath=following-sibling::tr[1]")

    def detail_field(self, agency_name: str, key: str):
        """A detail value by its label, e.g. 'Registration No.', 'Agency Status', 'Email', 'PAN',
        'Approval Date', 'Valid From (approvals)', 'Valid Upto (approvals)', 'Days Remaining',
        'Approved By', 'Remarks'."""
        return self.detail_row(agency_name).locator(
            f"//div[@class='df'][div[@class='dk' and normalize-space(text())='{key}']]/div[@class='dv']"
        )

    def detail_view_certificate_link(self, agency_name: str):
        return self.detail_row(agency_name).locator("a", has_text="View Full Certificate")

    def detail_view_application_link(self, agency_name: str):
        return self.detail_row(agency_name).locator("a", has_text="View Full Application")

    # ── Issue / Renew modal (#iss-mod) ────────────────────────────────────────

    @property
    def issue_modal(self):
        return self.page.locator("#iss-mod")

    @property
    def issue_modal_title(self):
        # "Issue License" or "Renew — <agency name>"
        return self.page.locator("#mod-ttl-txt")

    @property
    def issue_modal_note(self):
        return self.issue_modal.get_by_text("Saving will update")

    @property
    def modal_agency_select(self):
        # Disabled (pre-selected) when opened from a row's Issue / Renew button
        return self.page.locator("#mod-agency")

    @property
    def modal_agency_options(self):
        return self.modal_agency_select.locator("option")

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
        # Hidden — the licence number is no longer entered
        return self.page.locator("#mod-lic")

    @property
    def modal_valid_from_input(self):
        return self.page.locator("#mod-start")

    @property
    def modal_valid_upto_input(self):
        return self.page.locator("#mod-upto")

    def modal_quick_duration_button(self, years: int):
        """years: 1, 2, 3 or 5 — sets Valid Upto to start date + N years."""
        return self.issue_modal.locator(f"button[onclick='setDur({years})']")

    @property
    def modal_notes_textarea(self):
        return self.page.locator("#mod-notes")

    @property
    def modal_save_button(self):
        # "Save — Updates agency_approvals"
        return self.issue_modal.locator("button[type='submit']")

    @property
    def modal_cancel_button(self):
        return self.issue_modal.locator("button[type='button']", has_text="Cancel")

    @property
    def modal_close_button(self):
        # ✕ in the modal title
        return self.issue_modal.locator(".mod-ttl button")

    # ── Certificate action dialog (#caModal) ──────────────────────────────────

    @property
    def action_dialog(self):
        return self.page.locator("#caModal")

    @property
    def action_dialog_title(self):
        # "<Action title> — <agency>", e.g. "Suspend certificate — Yadneshdix"
        return self.page.locator("#caTitle")

    @property
    def action_dialog_explanation(self):
        return self.page.locator("#caSub")

    @property
    def suspension_period(self):
        # "Suspend for *" block — shown for Suspend only
        return self.page.locator("#caPeriod")

    @property
    def suspension_period_number(self):
        return self.page.locator("#caN")

    @property
    def suspension_period_unit(self):
        # days / months / years
        return self.page.locator("#caUnit")

    @property
    def action_reason_input(self):
        # Placeholder "At least N characters (shown to the agency)"
        return self.page.locator("#caReason")

    @property
    def action_error(self):
        # "Write at least N characters."
        return self.page.locator("#caErr")

    @property
    def action_confirm_button(self):
        return self.page.locator("#caGo")

    @property
    def action_close_button(self):
        return self.action_dialog.locator("button.sbtn-o")

    @property
    def action_dialog_x_button(self):
        return self.action_dialog.locator(".smod-cls")

    # ── Certificate history (#chModal) ────────────────────────────────────────

    @property
    def history_dialog(self):
        return self.page.locator("#chModal")

    @property
    def history_title(self):
        # "Certificate history — <agency>"
        return self.page.locator("#chTitle")

    @property
    def history_body(self):
        # A timeline, or "No certificate actions yet."
        return self.page.locator("#chBody")

    @property
    def history_entries(self):
        """Timeline entries, newest first; each has .t-title (e.g. "Suspended — until 2026-11-04 11:24"),
        .t-meta ("2026-11-03 16:54 · System Administrator (superadmin)") and .t-body (the details)."""
        return self.history_body.locator("li")

    @property
    def history_close_button(self):
        return self.history_dialog.locator(".smod-cls")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Licences & certificates (status={status}, q={query})")
    def open(self, status: str = None, query: str = None):
        params = []
        if status is not None:
            params.append(f"status={status}")
        if query is not None:
            params.append(f"q={query}")
        self.navigate(ADMIN_LICENSES_URL + ("?" + "&".join(params) if params else ""))

    @allure.step("Click Renewal applications")
    def open_renewal_applications(self):
        with self.page.expect_navigation():
            self.renewal_applications_link.click()

    @allure.step("Filter licences by status: {status}")
    def filter_by_status(self, status: str):
        """status: one of STATUS_FILTERS."""
        self.stat_chip(status).click()

    @allure.step("Search licences for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()

    @allure.step("Sort table by: {field}")
    def sort_by(self, field: str):
        self.sort_link(field).click()

    @allure.step("Toggle detail row for agency: {agency_name}")
    def toggle_detail_row(self, agency_name: str):
        self.license_row(agency_name).locator("td").first.click()

    @allure.step("Open certificate for agency: {agency_name}")
    def open_certificate(self, agency_name: str):
        """Clicks 'View Cert' and returns the new tab's Page object
        (the certificate opens with target=_blank)."""
        with self.page.context.expect_page() as new_page_info:
            self.view_certificate_link(agency_name).click()
        return new_page_info.value

    @allure.step("Open the full certificate from the details of: {agency_name}")
    def open_detail_certificate(self, agency_name: str):
        """Clicks 'View Full Certificate (MPPA FORM-II)' in the open detail row; returns the new tab."""
        with self.page.context.expect_page() as new_page_info:
            self.detail_view_certificate_link(agency_name).click()
        return new_page_info.value

    @allure.step("Open full application view for agency: {agency_name}")
    def open_application_view(self, agency_name: str):
        self.view_application_link(agency_name).click()

    @allure.step("Revoke license for agency '{agency_name}' (confirm dialog: {action})")
    def revoke_license(self, agency_name: str, action: str = "accept") -> str:
        """Clicks the row's Revoke button and answers the
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

    @allure.step("Fill modal Valid From: {date}")
    def fill_modal_valid_from(self, date: str):
        """date in yyyy-mm-dd format ('' clears it)."""
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
        """Clicks Save. A valid form posts and reloads the page — use ``save_modal_and_wait`` for that."""
        self.modal_save_button.click()

    @allure.step("Save the Issue / Renew modal and wait for the page to reload")
    def save_modal_and_wait(self):
        with self.page.expect_navigation():
            self.modal_save_button.click()

    @allure.step("Cancel the Issue / Renew modal")
    def cancel_modal(self):
        self.modal_cancel_button.click()

    @allure.step("Close the Issue / Renew modal with ✕")
    def close_modal(self):
        self.modal_close_button.click()

    @allure.step("Click outside the Issue / Renew modal")
    def click_outside_modal(self):
        self.issue_modal.click(position={"x": 5, "y": 5})

    @allure.step("Press Escape")
    def press_escape(self):
        self.page.keyboard.press("Escape")

    @allure.step("Renew license for agency: {agency_name}")
    def renew_license(self, agency_name: str, valid_from: str = None,
                      valid_upto: str = None, duration_years: int = None,
                      notes: str = None):
        """Opens the Renew modal from the agency's row (dates arrive pre-filled), overrides only the
        supplied values and saves (the page reloads)."""
        self.open_renew_modal(agency_name)
        if valid_from is not None:
            self.fill_modal_valid_from(valid_from)
        if valid_upto is not None:
            self.fill_modal_valid_upto(valid_upto)
        elif duration_years is not None:
            self.click_quick_duration(duration_years)
        if notes is not None:
            self.fill_modal_notes(notes)
        self.save_modal_and_wait()

    # -- Certificate actions --

    @allure.step("Open the {action} dialog for agency: {agency_name}")
    def open_certificate_action(self, agency_name: str, action: str):
        """action: a key of CERTIFICATE_ACTIONS."""
        self.action_button(agency_name, self.CERTIFICATE_ACTIONS[action][0]).click()

    @allure.step("Set the suspension period: {number} {unit}")
    def set_suspension_period(self, number: int, unit: str):
        """unit: days, months or years."""
        self.suspension_period_number.fill(str(number))
        self.suspension_period_unit.select_option(unit)

    @allure.step("Fill the reason: {reason}")
    def fill_action_reason(self, reason: str):
        self.action_reason_input.fill(reason)

    @allure.step("Click the dialog's confirm button (browser confirmation: {answer})")
    def confirm_certificate_action(self, answer: str = "accept") -> tuple[str, str]:
        """Clicks the dialog's confirm button and answers the browser confirmation ("<Action title>?").
        Accepting waits for the success toast and the page reload. Returns (confirmation message, toast
        text); the confirmation is "" when none appeared (e.g. the reason was too short)."""
        if answer != "accept":
            return self.click_and_handle_alert(self.action_confirm_button, action=answer), ""
        messages = []

        def handle_dialog(dialog):
            messages.append(dialog.message)
            dialog.accept()

        self.page.once("dialog", handle_dialog)
        with self.page.expect_navigation():
            self.action_confirm_button.click()
            self.toast.first.wait_for()
            toast = self.toast.first.text_content().strip()
        return (messages[0] if messages else ""), toast

    @allure.step("Close the certificate action dialog")
    def close_action_dialog(self):
        self.action_close_button.click()

    @allure.step("Click outside the certificate action dialog")
    def click_outside_action_dialog(self):
        self.action_dialog.click(position={"x": 5, "y": 5})

    @allure.step("{action} the certificate of {agency_name}")
    def certificate_action(self, agency_name: str, action: str, reason: str, period: tuple = None) -> tuple[str, str]:
        """Opens the action's dialog, fills it and confirms. period: (number, unit) for suspend.
        Returns (confirmation message, toast text)."""
        self.open_certificate_action(agency_name, action)
        if period:
            self.set_suspension_period(*period)
        self.fill_action_reason(reason)
        return self.confirm_certificate_action()

    @allure.step("Open the certificate history of: {agency_name}")
    def open_history(self, agency_name: str):
        """Clicks History and waits for the timeline to load."""
        self.action_button(agency_name, "History").click()
        self.page.wait_for_function("() => document.getElementById('chBody').textContent.trim() !== 'Loading…'")

    @allure.step("Close the certificate history")
    def close_history(self):
        self.history_close_button.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_agency_name(self, row_index: int = 0) -> str:
        """Agency name shown in the given main row (0-based)."""
        cell = self.license_rows.nth(row_index).locator("td").nth(1).locator("div").first
        return cell.text_content().strip()

    def agency_names(self) -> list[str]:
        """Agency names of the listed rows, in table order."""
        return [n.strip() for n in self.license_rows.locator("td:nth-child(2) > div:first-child").all_text_contents()]

    def agencies_with_status(self, status: str) -> list[str]:
        """Names of the listed agencies whose label has class ``lb-<status>``."""
        return self.license_rows.evaluate_all(
            """(rows, s) => rows.filter(r => r.querySelector('.lb.lb-' + s))
                 .map(r => r.cells[1].querySelector('div').textContent.trim())""", status)

    def agency_id(self, agency_name: str) -> str:
        """The agency's id from its row (``togDet(<id>)``)."""
        return re.search(r"\d+", self.license_row(agency_name).get_attribute("onclick")).group()

    def row_action_labels(self, agency_name: str) -> list[str]:
        return [t.strip() for t in self.action_buttons(agency_name).all_text_contents()]

    def column_values(self, index: int) -> list[str]:
        """Text of one column (0-based cell index) for every listed row."""
        return [" ".join(t.split()) for t in self.license_rows.locator(f"td:nth-child({index + 1})").all_text_contents()]

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

    def history_data(self) -> list[dict]:
        """The open history's entries, newest first: title, meta and body."""
        return self.history_entries.evaluate_all("""items => items.map(li => {
            const t = s => (li.querySelector(s) || {textContent: ''}).textContent.trim();
            return {title: t('.t-title'), meta: t('.t-meta'), body: t('.t-body')};
        })""")
