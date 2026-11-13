import re

import allure

from config import ADMIN_BASE
from pages.base_page import BasePage

ADMIN_RENEWALS_URL = f"{ADMIN_BASE}/licenses/renewals.php"


class AdminRenewalsPage(BasePage):
    """Officer Console — Renewal applications (/module/admin/licenses/renewals.php), opened from Licences &
    certificates → "Renewal applications".

    Tabs (``.rn-tab``, ``?tab=``) Pending decision (submitted), Renewed (approved), Rejected and All, each with
    a count. One table row per renewal application: #, Agency (name + registration no.), District, Current
    validity ("Up to <date>", + "Renewed to <date>" once approved), Applied, Declarations, Fee (+ payment
    reference), Status (+ "<date> · <officer>" once decided) and the actions Approve / Reject (pending only)
    and Application (agency_view.php).

    Approve / Reject open the decision dialog (``#rnModal``): remarks of at least 5 characters to approve and
    30 to reject, checked in the browser ("Write at least N characters." in ``#rnErr``, nothing sent). Confirm
    calls ``renewals.decide``, shows a toast and reloads the page 0.9 s later.
    """

    HEADING = "Renewal applications"
    NOTE = "Approve → the certificate is renewed for 5 years and shows in Licences & certificates."
    TITLE = "Renewal applications — MPPA Officer Console"
    TABS = {"submitted": "Pending decision", "approved": "Renewed", "rejected": "Rejected", "all": "All"}
    COLUMNS = ("#", "Agency", "District", "Current validity", "Applied", "Declarations", "Fee", "Status",
               "Action")
    APPROVE_LABEL = "Approve"
    REJECT_LABEL = "Reject"
    APPLICATION_LABEL = "Application"
    MIN_REMARKS = {"approve": 5, "reject": 30}
    DIALOG_TITLE = {"approve": "Approve renewal — {name}", "reject": "Reject renewal — {name}"}
    DIALOG_NOTE = {
        "approve": ("The certificate will be valid for 5 more years from its current expiry date (or from today "
                    "if already expired)."),
        "reject": "Write the reasons — the agency is informed by e-mail.",
    }
    REMARKS_PLACEHOLDER = {"approve": "e.g. Documents verified, no adverse report.",
                           "reject": "At least 30 characters"}
    PENDING = "Pending"

    @staticmethod
    def too_short(decision: str) -> str:
        return f"Write at least {AdminRenewalsPage.MIN_REMARKS[decision]} characters."

    @staticmethod
    def approved_toast(valid_upto: str) -> str:
        return f"Renewal approved — certificate valid up to {valid_upto}."

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("#adm-main h2")

    @property
    def note(self):
        return self.page.locator("#adm-main h2 + p")

    @property
    def licenses_link(self):
        return self.page.locator("#adm-main").get_by_role("link", name="Licences & certificates")

    # ── Tabs ──────────────────────────────────────────────────────────────────

    @property
    def tabs(self):
        return self.page.locator(".rn-tabs .rn-tab")

    def tab(self, tab: str):
        """tab: a key of TABS."""
        return self.page.locator(f".rn-tabs .rn-tab[href='?tab={tab}']")

    def tab_count(self, tab: str):
        return self.tab(tab).locator("span")

    @property
    def selected_tab(self):
        return self.page.locator(".rn-tabs .rn-tab.is-on")

    # ── Table ─────────────────────────────────────────────────────────────────

    @property
    def table_headers(self):
        return self.page.locator("#adm-main table.ui-table thead th")

    @property
    def rows(self):
        return self.page.locator("#adm-main table.ui-table tbody tr")

    def row(self, registration_no: str):
        """The row of the agency with this registration no. (shown under its name)."""
        return self.rows.filter(has=self.page.locator(".ui-mono", has_text=re.compile(rf"^\s*{registration_no}\s*$")))

    def cell(self, registration_no: str, column: str):
        """column: one of COLUMNS."""
        return self.row(registration_no).locator("td").nth(self.COLUMNS.index(column))

    def agency_name(self, registration_no: str):
        return self.cell(registration_no, "Agency").locator("strong")

    def status_badge(self, registration_no: str):
        return self.cell(registration_no, "Status").locator(".ui-badge")

    def decided_by(self, registration_no: str):
        """'<dd Mon yyyy> · <officer>' under the status once decided."""
        return self.cell(registration_no, "Status").locator("div")

    def action_buttons(self, registration_no: str):
        return self.cell(registration_no, "Action").locator("a, button")

    def approve_button(self, registration_no: str):
        return self.row(registration_no).get_by_role("button", name=self.APPROVE_LABEL)

    def reject_button(self, registration_no: str):
        return self.row(registration_no).get_by_role("button", name=self.REJECT_LABEL)

    def application_link(self, registration_no: str):
        return self.row(registration_no).get_by_role("link", name=self.APPLICATION_LABEL)

    # ── Decision dialog ───────────────────────────────────────────────────────

    @property
    def dialog(self):
        return self.page.locator("#rnModal")

    @property
    def dialog_title(self):
        return self.page.locator("#rnTitle")

    @property
    def dialog_note(self):
        return self.page.locator("#rnSub")

    @property
    def remarks_input(self):
        return self.page.locator("#rnRemarks")

    @property
    def dialog_error(self):
        return self.page.locator("#rnErr")

    @property
    def confirm_button(self):
        return self.page.locator("#rnGo")

    @property
    def close_button(self):
        return self.dialog.get_by_role("button", name="Close")

    @property
    def toast(self):
        return self.page.locator("#uiToasts .ui-toast")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Renewal applications (tab={tab})")
    def open(self, tab: str = None):
        self.navigate(ADMIN_RENEWALS_URL + (f"?tab={tab}" if tab else ""))
        self.wait_for_load()

    @allure.step("Click the '{tab}' tab")
    def open_tab(self, tab: str):
        with self.page.expect_navigation():
            self.tab(tab).click()

    @allure.step("Click {decision} on the renewal of {registration_no}")
    def open_decision(self, registration_no: str, decision: str):
        """decision: 'approve' or 'reject'."""
        button = self.approve_button if decision == "approve" else self.reject_button
        button(registration_no).click()
        self.dialog.locator(".smod-box").wait_for()

    @allure.step("Write the remarks: {remarks}")
    def fill_remarks(self, remarks: str):
        self.remarks_input.fill(remarks)

    @allure.step("Click Confirm")
    def confirm(self):
        """Clicks Confirm without waiting — use when the remarks are too short (nothing is sent)."""
        self.confirm_button.click()

    @allure.step("Confirm the decision and wait for the page to reload")
    def confirm_and_wait(self) -> str:
        """Clicks Confirm, waits for the toast and the reload; returns the toast text."""
        with self.page.expect_navigation(timeout=30000):
            self.confirm_button.click()
            self.toast.first.wait_for(timeout=20000)
            toast = " ".join(self.toast.first.inner_text().split())
        self.wait_for_load()
        return toast

    @allure.step("Close the decision dialog")
    def close_dialog(self):
        self.close_button.click()

    @allure.step("Open the agency's application")
    def open_application(self, registration_no: str):
        with self.page.expect_navigation():
            self.application_link(registration_no).click()

    @allure.step("{decision} the renewal of {registration_no}")
    def decide(self, registration_no: str, decision: str, remarks: str) -> str:
        """Opens the dialog, writes the remarks and confirms. Returns the toast text."""
        self.open_decision(registration_no, decision)
        self.fill_remarks(remarks)
        return self.confirm_and_wait()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_tab_count(self, tab: str) -> int:
        return int(self.tab_count(tab).inner_text().strip())

    def cell_text(self, registration_no: str, column: str) -> str:
        return " ".join(self.cell(registration_no, column).inner_text().split())

    def action_labels(self, registration_no: str) -> list[str]:
        return [t.strip() for t in self.action_buttons(registration_no).all_inner_texts()]
