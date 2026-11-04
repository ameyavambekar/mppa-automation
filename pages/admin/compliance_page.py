import re

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

ADMIN_COMPLIANCE_URL = f"{ADMIN_BASE}/compliance/index.php"


class AdminCompliancePage(BasePage):
    """Admin — Compliance cases (/module/admin/compliance/index.php), Enforcement › Compliance cases.

    The case table is filled by script (``compliance.list``) after the page loads. "Open new case" opens the
    ``#newCase`` dialog (``compliance.open``); a row's Open button loads the case (``compliance.get``) into the
    ``#caseBox`` dialog, whose form takes one of the case's allowed actions (``compliance.action``). Both
    dialogs report the result in a toast (``#uiToasts .ui-toast``, class ``is-success`` / ``is-error``); on
    success the dialog closes and the table is reloaded.

    Route B (``high_risk=1``) and the cancellation order ask a browser confirm first.
    """

    TITLE = "Compliance Cases — MPPA Officer Console"
    HEADING = "Compliance cases"
    SUBTITLE = "Complaints, surprise inspections and overdue returns (Sec 6, 9, 11 · Rules 7 & 8)"
    COLUMNS = ("Case No.", "Agency", "District", "Route", "Status", "Opened", "")
    EMPTY_TABLE = "No compliance cases."
    TRIGGERS = {"complaint": "Complaint", "inspection": "Surprise inspection",
                "overdue_return": "Overdue statutory return", "other": "Other information"}
    RISK_OPTIONS = {
        "0": "No — administrative / curable lapse (Route A: regular inquiry, agency stays active)",
        "1": "Yes — fraud, ghost office, impersonation, worker exploitation (Route B: interim suspension)",
    }
    RISK_REASONS_LABEL = "Reasons in writing (mandatory for suspension)"
    RISK_HELP = ("Interim suspension is valid for a maximum of 6 months. "
                 "A 15-day show cause notice is issued automatically.")
    SUSPEND_CONFIRM = "This will SUSPEND the agency immediately. Continue?"
    CANCEL_CONFIRM = "Cancel this agency's registration?"
    # Case action (radio value) → label
    ACTIONS = {"hearing": "Schedule mandatory hearing", "window": "Grant 3–7 day window",
               "drop": "Drop proceedings / revoke suspension", "cancel": "Issue cancellation order"}
    # Case status (as the list badge shows it, underscores → spaces) → badge colour
    STATUS_BADGES = {"under inquiry": "amber", "hearing scheduled": "blue", "post hearing window": "blue",
                     "suspended": "red", "cancelled": "red", "closed dropped": "green", "closed revoked": "green"}

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Page header ───────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("#adm-main h2").first

    @property
    def subtitle(self):
        return self.page.locator("#adm-main h2 + p")

    @property
    def open_new_case_button(self):
        return self.page.locator("#adm-main button[onclick=\"openModal2('newCase')\"]")

    @property
    def toasts(self):
        return self.page.locator("#uiToasts .ui-toast")

    @property
    def new_toast(self):
        """The toast that appeared after the last ``_mark_toasts()`` call."""
        return self.page.locator("#uiToasts .ui-toast:not([data-seen])").first

    # ── Case table ────────────────────────────────────────────────────────────

    @property
    def table_headers(self):
        return self.page.locator("#adm-main table.ui-table thead th")

    @property
    def case_rows(self):
        """Case rows (the empty-table row excluded)."""
        return self.page.locator("#rows tr:not(:has(td[colspan]))")

    @property
    def empty_table_row(self):
        # "No compliance cases."
        return self.page.locator("#rows td[colspan]")

    def case_row(self, case_no: str):
        return self.case_rows.filter(has=self.page.locator("td.ui-mono", has_text=re.compile(rf"^{re.escape(case_no)}$")))

    def route_badge(self, case_no: str):
        # "High risk" (red) or "Regular" (gray)
        return self.case_row(case_no).locator("td").nth(3).locator(".ui-badge")

    def status_badge(self, case_no: str):
        # The status with underscores turned into spaces, e.g. "under inquiry" (class ui-badge-amber)
        return self.case_row(case_no).locator("td").nth(4).locator(".ui-badge")

    def opened_cell(self, case_no: str):
        # "YYYY-MM-DD HH:MM:SS"
        return self.case_row(case_no).locator("td").nth(5)

    def open_button(self, case_no: str):
        return self.case_row(case_no).locator("button", has_text="Open")

    # ── Open compliance case dialog (#newCase) ────────────────────────────────

    @property
    def new_case_dialog(self):
        # Shown while it has the 'is-open' class
        return self.page.locator("#newCase")

    @property
    def new_case_title(self):
        return self.new_case_dialog.locator(".ui-card-title")

    @property
    def new_case_close_button(self):
        return self.new_case_dialog.locator("button", has_text="Close")

    @property
    def agency_select(self):
        # Required; "Select an approved agency" then "<Name> — <Application ID>"
        return self.page.locator("#ncForm select[name='agency_id']")

    @property
    def agency_options(self):
        """The agency choices (the "Select an approved agency" placeholder excluded)."""
        return self.agency_select.locator("option:not([value=''])")

    @property
    def trigger_select(self):
        return self.page.locator("#ncForm select[name='trigger_type']")

    @property
    def details_input(self):
        return self.page.locator("#ncForm textarea[name='trigger_details']")

    @property
    def risk_select(self):
        # Immediate public risk? (Sec 6(2)) — "0" Route A, "1" Route B
        return self.page.locator("#ncForm select[name='high_risk']")

    @property
    def risk_box(self):
        # Reasons in writing — shown only for Route B
        return self.page.locator("#riskBox")

    @property
    def risk_reasons_label(self):
        return self.risk_box.locator(".ui-label")

    @property
    def risk_reasons_input(self):
        return self.page.locator("#ncForm textarea[name='risk_reasons']")

    @property
    def risk_help(self):
        return self.risk_box.locator(".ui-help")

    @property
    def open_case_button(self):
        return self.page.locator("#ncForm button[type='submit']")

    def new_case_label(self, field: str):
        """The label above a New case field: 'agency_id', 'trigger_type', 'trigger_details' or 'high_risk'."""
        return self.page.locator(f"#ncForm .ui-field:has([name='{field}']) .ui-label")

    # ── Case dialog (#caseBox) ────────────────────────────────────────────────

    @property
    def case_dialog(self):
        return self.page.locator("#caseBox")

    @property
    def case_title(self):
        # "<Case No.> — <Agency>"
        return self.page.locator("#cTitle")

    @property
    def case_close_button(self):
        return self.case_dialog.locator(".ui-card-head button", has_text="Close")

    def case_field(self, label: str):
        """A detail line by its label: 'Status', 'Trigger', 'Reasons for suspension', 'Suspension valid until'
        or 'Hearing'. Its text is "<label>: <value>"."""
        return self.page.locator("#cBody > p").filter(has=self.page.locator("strong", has_text=f"{label}:"))

    @property
    def action_form(self):
        # Absent once the case is closed (no allowed actions)
        return self.page.locator("#caForm")

    @property
    def action_radios(self):
        return self.page.locator("#caForm input[name='action']")

    @property
    def action_labels(self):
        return self.page.locator("#caForm label:has(input[name='action'])")

    def action_radio(self, action: str):
        """action: a key of ACTIONS."""
        return self.page.locator(f"#caForm input[name='action'][value='{action}']")

    @property
    def hearing_fields(self):
        # Hearing date & time + Mode — shown for "Schedule mandatory hearing"
        return self.page.locator("#caHear")

    @property
    def hearing_at_input(self):
        return self.page.locator("#caForm input[name='hearing_at']")

    @property
    def hearing_mode_select(self):
        return self.page.locator("#caForm select[name='hearing_mode']")

    @property
    def window_field(self):
        # Window (days) — shown for "Grant 3–7 day window"
        return self.page.locator("#caWin")

    @property
    def window_days_select(self):
        return self.page.locator("#caForm select[name='window_days']")

    @property
    def remarks_label(self):
        return self.page.locator("#caForm .ui-field:has(textarea[name='remarks']) .ui-label")

    @property
    def remarks_input(self):
        return self.page.locator("#caForm textarea[name='remarks']")

    @property
    def submit_button(self):
        return self.page.locator("#caForm button[type='submit']")

    @property
    def history_heading(self):
        return self.page.locator("#cBody h4", has_text="History")

    @property
    def history_entries(self):
        """Newest first; each has .t-title (event, e.g. "opened"), .t-meta ("<time> · <officer>") and .t-body."""
        return self.page.locator("#cBody .ui-timeline li")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Compliance cases")
    def open(self, wait_for_table: bool = True):
        """Opens the page and waits for the script to fill the case table (pass False when no officer is
        logged in — the page then sends you to the login page)."""
        self.navigate(ADMIN_COMPLIANCE_URL)
        if wait_for_table:
            self.wait_for_table()

    def wait_for_table(self):
        self.page.wait_for_function("() => document.querySelectorAll('#rows tr').length > 0")

    def _mark_toasts(self):
        """Marks the toasts on screen so ``new_toast`` only finds the next one."""
        self.page.evaluate("() => document.querySelectorAll('#uiToasts .ui-toast').forEach(t => t.dataset.seen = '1')")

    def _click_and_answer(self, button, answer: str) -> tuple[str, str]:
        """Clicks a submit button, answers a browser confirm if one appears and returns (confirm message, toast
        text). The toast is "" when the confirm was dismissed or the browser blocked the submit (required field)."""
        self._mark_toasts()
        messages = []

        def handle_dialog(dialog):
            messages.append(dialog.message)
            dialog.accept() if answer == "accept" else dialog.dismiss()

        form_valid = button.evaluate("b => b.form.checkValidity()")
        self.page.on("dialog", handle_dialog)
        try:
            button.click()
            toast = ""
            if form_valid and not (messages and answer != "accept"):
                self.new_toast.wait_for()
                toast = self.new_toast.text_content().strip()
        finally:
            self.page.remove_listener("dialog", handle_dialog)
        return (messages[0] if messages else ""), toast

    @allure.step("Click 'Open new case'")
    def open_new_case(self):
        self.open_new_case_button.click()

    @allure.step("Close the Open compliance case dialog")
    def close_new_case(self):
        self.new_case_close_button.click()

    @allure.step("Choose the agency: {agency_name}")
    def select_agency(self, agency_name: str):
        option = self.agency_options.filter(has_text=re.compile(rf"^{re.escape(agency_name)} — "))
        self.agency_select.select_option(value=option.get_attribute("value"))

    @allure.step("Choose the trigger: {trigger}")
    def select_trigger(self, trigger: str):
        """trigger: a key of TRIGGERS."""
        self.trigger_select.select_option(trigger)

    @allure.step("Fill the details of the complaint / finding")
    def fill_details(self, details: str):
        self.details_input.fill(details)

    @allure.step("Immediate public risk? → {high_risk}")
    def set_high_risk(self, high_risk: bool):
        self.risk_select.select_option("1" if high_risk else "0")

    @allure.step("Fill the reasons in writing")
    def fill_risk_reasons(self, reasons: str):
        self.risk_reasons_input.fill(reasons)

    @allure.step("Fill the Open compliance case form")
    def fill_new_case(self, agency_name: str = None, trigger: str = None, details: str = None,
                      high_risk: bool = False, reasons: str = None):
        """Fills only the supplied fields (the dialog must be open)."""
        if agency_name is not None:
            self.select_agency(agency_name)
        if trigger is not None:
            self.select_trigger(trigger)
        if details is not None:
            self.fill_details(details)
        self.set_high_risk(high_risk)
        if reasons is not None:
            self.fill_risk_reasons(reasons)

    @allure.step("Click 'Open case' (confirm: {answer})")
    def submit_new_case(self, answer: str = "accept") -> tuple[str, str]:
        """Returns (confirm message — Route B only, toast text)."""
        return self._click_and_answer(self.open_case_button, answer)

    @allure.step("Open a compliance case for {agency_name} (high risk: {high_risk})")
    def open_case_for(self, agency_name: str, trigger: str, details: str, high_risk: bool = False,
                      reasons: str = None) -> tuple[str, str]:
        """Opens the dialog, fills it and submits (accepting the Route B confirm). Waits for the new row and
        returns (case number, toast text); the case number is "" when the case was refused."""
        self.open_new_case()
        self.fill_new_case(agency_name, trigger, details, high_risk, reasons)
        _, toast = self.submit_new_case()
        # Success reads "Case <no>: …"; a refusal can name a case too ("Case <no> is already open …")
        match = re.match(r"Case (CMP/\d{4}/\w+): ", toast)
        if not match:
            return "", toast
        self.case_row(match.group(1)).wait_for()
        return match.group(1), toast

    @allure.step("Open the case: {case_no}")
    def open_case(self, case_no: str) -> dict:
        """Clicks Open on the row and waits for the case dialog. Returns the case record the page loaded
        (``compliance.get`` — includes fields the dialog does not show, e.g. scn_due_at)."""
        with self.page.expect_response(lambda r: "r=compliance.get" in r.url) as response:
            self.open_button(case_no).click()
        self.page.locator("#caseBox.is-open").wait_for()
        return response.value.json()["data"]["case"]

    @allure.step("Close the case dialog")
    def close_case(self):
        self.case_close_button.click()

    @allure.step("Choose the action: {action}")
    def choose_action(self, action: str):
        """action: a key of ACTIONS."""
        self.action_radio(action).check()

    @allure.step("Set the hearing: {hearing_at} ({mode})")
    def set_hearing(self, hearing_at: str = None, mode: str = None):
        """hearing_at: 'YYYY-MM-DDTHH:MM' (datetime-local); mode: 'virtual' or 'personal'."""
        if hearing_at is not None:
            self.hearing_at_input.fill(hearing_at)
        if mode is not None:
            self.hearing_mode_select.select_option(mode)

    @allure.step("Choose the window: {days} days")
    def set_window_days(self, days: str):
        self.window_days_select.select_option(str(days))

    @allure.step("Fill the remarks / speaking order")
    def fill_remarks(self, remarks: str):
        self.remarks_input.fill(remarks)

    @allure.step("Click Submit (confirm: {answer})")
    def submit_action(self, answer: str = "accept") -> tuple[str, str]:
        """Returns (confirm message — cancellation order only, toast text)."""
        return self._click_and_answer(self.submit_button, answer)

    @allure.step("Take the action '{action}' on {case_no}")
    def take_action(self, case_no: str, action: str, remarks: str, hearing_at: str = None, mode: str = None,
                    window_days: str = None, answer: str = "accept") -> tuple[str, str]:
        """Opens the case, fills the action and submits. Returns (confirm message, toast text)."""
        self.open_case(case_no)
        self.choose_action(action)
        if action == "hearing":
            self.set_hearing(hearing_at, mode)
        if action == "window" and window_days is not None:
            self.set_window_days(window_days)
        self.fill_remarks(remarks)
        return self.submit_action(answer)

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def rows_data(self) -> list[dict]:
        """Every case row: case_no, agency, reg_id, district, route, route_class, status, status_class, opened."""
        return self.case_rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const c = r.cells, rb = c[3].querySelector('.ui-badge'), sb = c[4].querySelector('.ui-badge');
            return {case_no: t(c[0]), agency: t(c[1].firstChild), reg_id: t(c[1].querySelector('div')),
                    district: t(c[2]), route: t(rb), route_class: rb ? rb.className : '', status: t(sb),
                    status_class: sb ? sb.className : '', opened: t(c[5]), open: t(c[6])};
        })""")

    def cases_for(self, agency_name: str) -> list[dict]:
        return [r for r in self.rows_data() if r["agency"] == agency_name]

    def agency_option_names(self) -> list[str]:
        """Agency names offered in the New case dialog ("<Name> — <Application ID>" → Name)."""
        return [t.rsplit(" — ", 1)[0].strip() for t in self.agency_options.all_text_contents()]

    def allowed_actions(self) -> list[str]:
        """Radio values of the open case dialog, e.g. ['hearing', 'drop']."""
        return [r.get_attribute("value") for r in self.action_radios.all()]

    def history_data(self) -> list[dict]:
        """The open case's History, newest first: title, meta and body."""
        return self.history_entries.evaluate_all("""items => items.map(li => {
            const t = s => (li.querySelector(s) || {textContent: ''}).textContent.trim();
            return {title: t('.t-title'), meta: t('.t-meta'), body: t('.t-body')};
        })""")

    def validation_message(self, locator) -> str:
        """The browser's validation message on a form field ('' when the field is valid)."""
        return locator.evaluate("el => el.validationMessage")
