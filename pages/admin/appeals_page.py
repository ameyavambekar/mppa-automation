import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage


class AdminAppealsPage(BasePage):
    """Admin — Appeals Management (/module/admin/appeals/index.php).

    Lists FORM-III (first) and FORM-IV (second) appeals with 8 stat chips,
    server-side type/status filter tabs (``?type=`` / ``?status=`` query
    params) and a search form. Clicking a row (or its Review button) opens
    the full-detail modal (``#mod``): the appeal rendered as the filed
    FORM-III/IV document, followed by the decision action panel.

    In the action panel the Confirm & Save button stays disabled until a
    decision button (Allow / Allow Partial / Reject / Under Review) is
    selected; remarks are mandatory (native ``required`` textarea). Rows are
    keyed by the appeal id baked into the row's ``openAppeal(N)`` handler.
    """

    # status values used by badges and the ?status= filter
    STATUSES = ("submitted", "under_review", "allowed", "rejected", "partially_allowed")
    # decision values posted by the action panel
    DECISIONS = ("allow", "allow_partial", "reject", "under_review")
    # decision value → action-panel button class
    _DECISION_CLASSES = {
        "allow": "dec-allow",
        "allow_partial": "dec-partial",
        "reject": "dec-reject",
        "under_review": "dec-review",
    }
    STAT_LABELS = ("Total", "Pending", "Reviewing", "Allowed", "Partial",
                   "Rejected", "1st Appeal", "2nd Appeal")

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Page header & stat chips ──────────────────────────────────────────────

    @property
    def page_title(self):
        # "⚖️ Appeals Management (6)"
        return self.page.locator(".adm-page-title span").first

    def stat_chip(self, label: str):
        """label: one of STAT_LABELS."""
        return self.page.locator(
            f"//div[@class='sc'][div[@class='l' and normalize-space(text())='{label}']]"
        )

    def stat_chip_count(self, label: str):
        return self.stat_chip(label).locator(".n")

    # ── Toolbar: search & filter tabs ─────────────────────────────────────────

    @property
    def search_input(self):
        return self.page.locator("input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("//button[normalize-space(text())='Search']")

    def type_filter_tab(self, label: str):
        """label: 'All Types', '1st Appeal (FORM-III)' or '2nd Appeal (FORM-IV)'."""
        return self.page.locator(f"//a[contains(@class,'ftab') and normalize-space(text())='{label}']")

    def status_filter_tab(self, status: str):
        """status: one of STATUSES — targets the ?status= href."""
        return self.page.locator(f"a.ftab[href*='status={status}&']")

    @property
    def active_filter_tabs(self):
        return self.page.locator("a.ftab.active")

    # ── Appeals table (rows keyed by appeal id) ───────────────────────────────

    @property
    def appeals_table(self):
        return self.page.locator("table.stbl")

    @property
    def table_headers(self):
        return self.page.locator("table.stbl thead th")

    def table_header(self, label: str):
        return self.page.locator(
            f"//table[contains(@class,'stbl')]//thead//th[normalize-space(text())='{label}']"
        )

    @property
    def appeal_rows(self):
        return self.page.locator("table.stbl tbody tr")

    def appeal_row(self, appeal_id: int):
        return self.page.locator(f"table.stbl tbody tr[onclick='openAppeal({appeal_id})']")

    def rows_with_status(self, status: str):
        """Status badges of all rows in a given state (class sb-{status})."""
        return self.page.locator(f"table.stbl tbody .sb.sb-{status}")

    # -- Cells within a row --

    def agency_name_cell(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("td").nth(1).locator("div").first

    def agency_email_cell(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("td").nth(1).locator("div").nth(1)

    def reg_id_cell(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("td").nth(2)

    def form_type_badge(self, appeal_id: int):
        # "FORM-III" (.type-first) or "FORM-IV" (.type-second)
        return self.appeal_row(appeal_id).locator(".type-badge")

    def order_ref_cell(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("td").nth(4)

    def filed_on_cell(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("td").nth(5)

    def status_badge(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator(".sb")

    def reviewed_cell(self, appeal_id: int):
        # "—" until a decision is taken
        return self.appeal_row(appeal_id).locator("td").nth(7)

    def review_button(self, appeal_id: int):
        return self.appeal_row(appeal_id).locator("//button[contains(normalize-space(.),'Review')]")

    # ── Review modal (#mod): header & form document ───────────────────────────

    @property
    def review_modal(self):
        return self.page.locator("#mod")

    @property
    def modal_form_badge(self):
        # "FORM-III" / "FORM-IV"
        return self.page.locator("#mod-form-badge")

    @property
    def modal_status_badge(self):
        # e.g. "Pending Review" (class sb-{status})
        return self.page.locator("#mod-status-badge")

    @property
    def modal_title(self):
        # "Appeal #7 — Ameya Ambekar"
        return self.page.locator("#mod-title")

    @property
    def modal_subtitle(self):
        # "FORM-IV — Second Appeal (See Rule 6(10)) · Filed: 2026-05-23"
        return self.page.locator("#mod-subtitle")

    @property
    def modal_close_button(self):
        return self.review_modal.locator("//button[normalize-space(text())='✕']")

    @property
    def form_document(self):
        # The rendered FORM-III / FORM-IV document
        return self.page.locator("#mod-form-doc")

    @property
    def form_document_header(self):
        # "APPLICATION FOR FIRST/SECOND APPEAL" header block
        return self.form_document.locator(".form-doc-header")

    def form_section_title(self, title: str):
        """A section header inside the form document, e.g.
        'Section 6 · Grounds of Appeal', 'Verification'."""
        return self.form_document.locator(
            f"//div[contains(@class,'form-section-title') and contains(normalize-space(.),'{title}')]"
        )

    def form_field(self, label: str):
        """A field value (.fld-val) by its label, e.g. '2. Registration Number',
        '(a) Order Number / Ref', 'Filed On', 'Submitted IP'."""
        return self.form_document.locator(
            f"//div[@class='fld' or @class='fld full'][div[contains(@class,'fld-lbl')]"
            f"[contains(normalize-space(text()),'{label}')]]//div[contains(@class,'fld-val')]"
        )

    @property
    def grounds_items(self):
        # Ticked grounds-of-appeal entries in Section 6
        return self.form_document.locator(".chk-item-v")

    @property
    def document_chips(self):
        # Section 10 enclosure links
        return self.form_document.locator(".doc-chip")

    @property
    def no_documents_note(self):
        return self.form_document.locator("//span[contains(text(),'No documents uploaded')]")

    # ── Review modal: action panel ────────────────────────────────────────────

    @property
    def action_panel(self):
        return self.page.locator(".action-panel")

    @property
    def previous_decision_box(self):
        # Only shown when the appeal was already decided once
        return self.page.locator("#prev-dec-box .prev-decision-box")

    def decision_button(self, decision: str):
        """decision: one of DECISIONS ('allow', 'allow_partial', 'reject',
        'under_review'). Selected state carries the 'selected' class."""
        return self.page.locator(f".dec-btn.{self._DECISION_CLASSES[decision]}")

    @property
    def decision_preview(self):
        # "Decision: Allow Appeal" strip shown after selecting a decision
        return self.page.locator("#dec-preview")

    @property
    def decision_remarks_textarea(self):
        return self.page.locator("#dec-remarks")

    @property
    def hearing_date_input(self):
        return self.page.locator("#dec-hearing")

    @property
    def confirm_decision_button(self):
        # Disabled until a decision button is selected
        return self.page.locator("#dec-submit")

    @property
    def modal_cancel_button(self):
        return self.action_panel.locator("//button[normalize-space(text())='Cancel']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Appeals Management page directly")
    def open(self):
        import os
        base = os.getenv("MPPA_ADMIN_BASE_URL", "https://devmppa.sppuef.in/module/admin")
        self.navigate(f"{base}/appeals/index.php")

    @allure.step("Search appeals for: {query}")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_button.click()

    @allure.step("Filter appeals by type tab: {label}")
    def filter_by_type(self, label: str):
        self.type_filter_tab(label).click()

    @allure.step("Filter appeals by status: {status}")
    def filter_by_status(self, status: str):
        self.status_filter_tab(status).click()

    @allure.step("Open the review modal for appeal #{appeal_id}")
    def open_review_modal(self, appeal_id: int):
        self.review_button(appeal_id).click()

    @allure.step("Close the review modal")
    def close_review_modal(self):
        self.modal_close_button.click()

    @allure.step("Select decision: {decision}")
    def select_decision(self, decision: str):
        """decision: one of DECISIONS. Enables the Confirm & Save button and
        shows the decision preview strip."""
        self.decision_button(decision).click()

    @allure.step("Fill decision remarks")
    def fill_decision_remarks(self, remarks: str):
        self.decision_remarks_textarea.fill(remarks)

    @allure.step("Fill hearing date: {date}")
    def fill_hearing_date(self, date: str):
        """date in yyyy-mm-dd format. Optional — for scheduling a hearing."""
        self.hearing_date_input.fill(date)

    @allure.step("Click 'Confirm & Save Decision'")
    def confirm_decision(self):
        self.confirm_decision_button.click()
        self.wait_for_load()

    @allure.step("Cancel the review modal")
    def cancel_review(self):
        self.modal_cancel_button.click()

    @allure.step("Review appeal #{appeal_id}: decision={decision}")
    def review_appeal(self, appeal_id: int, decision: str, remarks: str,
                      hearing_date: str = None):
        """Opens the review modal, selects a decision, fills the mandatory
        remarks (and optional hearing date) and confirms."""
        self.open_review_modal(appeal_id)
        self.select_decision(decision)
        self.fill_decision_remarks(remarks)
        if hearing_date is not None:
            self.fill_hearing_date(hearing_date)
        self.confirm_decision()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_stat_count(self, label: str) -> int:
        """Numeric value on a stat chip, e.g. get_stat_count('Pending')."""
        return int(self.stat_chip_count(label).text_content().strip())

    def get_row_status(self, appeal_id: int) -> str:
        return self.status_badge(appeal_id).text_content().strip()

    def get_appeal_id_of_row(self, row) -> int:
        """Appeal id from a row locator's openAppeal(N) handler."""
        import re
        match = re.search(r"openAppeal\((\d+)\)", row.get_attribute("onclick") or "")
        return int(match.group(1)) if match else -1

    def get_first_appeal_id_with_status(self, status: str) -> int:
        """Appeal id of the newest row in the given status, or -1 if none.
        status: one of STATUSES."""
        rows = self.page.locator(
            f"//table[contains(@class,'stbl')]//tbody/tr[.//span[contains(@class,'sb-{status}')]]"
        )
        if rows.count() == 0:
            return -1
        return self.get_appeal_id_of_row(rows.first)

    def get_remarks_validation_message(self) -> str:
        """Native HTML5 validation message on the required remarks textarea
        (non-empty after attempting to save with blank remarks)."""
        return self.decision_remarks_textarea.evaluate("el => el.validationMessage")
