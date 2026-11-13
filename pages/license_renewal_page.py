import allure

from config import AGENCY_BASE
from pages.base_page import BasePage

RENEWAL_URL = f"{AGENCY_BASE}/renewal.php"


class LicenseRenewalPage(BasePage):
    """Agency — Renewal of Registration Certificate (Form-II) (module/agency/renewal.php).

    A header card (``.rw-head``: title and note) with three facts (``.rw-kv``: Registration No., Valid up
    to, Days left). Below it, one of:

    - the "Renewal application" form, from 90 days before expiry (and once expired) while no renewal is
      pending: question 1 (``changes_made`` no/yes + ``changes_details``), question 2 (``cases_pending``
      no/yes + ``cases_details``), 3 the supporting document (``document``), the fee box (``.rw-fee``),
      the declaration (``declare``) and "Pay ₹2,000 & submit renewal". The form has no client-side checks:
      it POSTs to itself and the server lists what is wrong under "Please correct:" (``.rw-err``), keeping
      the answers (the file must be chosen again);
    - "Latest renewal application #N — filed <date> · <status>" once one is filed (With the department /
      Renewed / Rejected + "Reason: <officer's reasons>" — after a rejection the form is shown again), followed by "Renewal opens 90 days before expiry — on <date>." while that is still ahead;
    - "No registration certificate was found for your agency." when no certificate was issued.

    A successful submission shows "Submitted. Renewal application #N submitted. …" (``.rw-ok``). Logged out
    (or before Form-I is submitted) the page redirects to the agency login (``?reason=not_logged_in``).
    """

    TITLE = "Renewal of Registration Certificate (Form-II)"
    NOTE = ("A certificate can be renewed from 90 days before its expiry date. "
            "After approval it is valid for 5 more years.")
    FACT_LABELS = ("Registration No.", "Valid up to", "Days left")
    NO_VALUE = "—"
    NO_CERTIFICATE = "No registration certificate was found for your agency."
    WINDOW_DAYS = 90
    RENEWAL_YEARS = 5
    FORM_TITLE = "Renewal application"
    QUESTION_1 = ("1. Has anything changed since registration (address, key persons, constitution, "
                  "branches)? *")
    QUESTION_2 = ("2. Is any criminal case, complaint, suspension or cancellation pending against the agency "
                  "or its key persons? *")
    QUESTION_3 = "3. Supporting document (required if anything changed)"
    CHANGES_PLACEHOLDER = "If Yes — describe the changes"
    CASES_PLACEHOLDER = "If Yes — give the details"
    DOCUMENT_HELP = "PDF, JPG or PNG · minimum 10 KB, maximum 2 MB"
    DOCUMENT_ACCEPT = ".pdf,.jpg,.jpeg,.png"
    FEE_LABEL = "Renewal fee — Within Maharashtra (Rule 3(3)(d))"
    FEE = "₹2,000"
    DECLARATION = ("I declare that the information given is true and that the agency continues to comply with "
                   "the Act and the Rules.")
    SUBMIT_LABEL = "Pay ₹2,000 & submit renewal"
    ERRORS_HEADING = "Please correct:"
    BACK_LABEL = "Back to my dashboard"
    WITH_DEPARTMENT = "With the department"
    RENEWED = "Renewed"
    REJECTED = "Rejected"
    CERTIFICATE_LINK_LABEL = "View / download the certificate"

    @staticmethod
    def rejection_reason(reasons: str) -> str:
        return f"Reason: {reasons}"

    @staticmethod
    def window_message(opens_on: str) -> str:
        """'Renewal opens 90 days before expiry — on <dd Mon yyyy>.'"""
        return f"Renewal opens 90 days before expiry — on {opens_on}."

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def header(self):
        """The first card: title, note and the three facts (the form card has its own ``.rw-head``)."""
        return self.page.locator(".rw-card").first

    @property
    def title(self):
        return self.header.locator(".rw-head h1")

    @property
    def note(self):
        return self.header.locator(".rw-head p")

    @property
    def facts(self):
        """The three header facts, each '<label><value>' (the label is a <small>)."""
        return self.page.locator(".rw-kv > div")

    def fact(self, label: str):
        return self.facts.filter(has=self.page.locator("small", has_text=label))

    @property
    def back_to_dashboard_link(self):
        return self.page.get_by_role("link", name=self.BACK_LABEL)

    # ── Messages below the header ─────────────────────────────────────────────

    @property
    def errors_box(self):
        """'Please correct:' and one line per problem the server found."""
        return self.page.locator(".rw-err")

    @property
    def success_box(self):
        return self.page.locator(".rw-ok")

    @property
    def latest_application(self):
        """'Latest renewal application #N — filed <date> · <status badge>' (+ the renewed-to line)."""
        return self.page.locator(".rw-body").filter(has_text="Latest renewal application #")

    @property
    def latest_application_status(self):
        return self.latest_application.locator(".ui-badge")

    @property
    def certificate_link(self):
        return self.latest_application.get_by_role("link", name=self.CERTIFICATE_LINK_LABEL)

    @property
    def window_notice(self):
        """'Renewal opens 90 days before expiry — on <date>.'"""
        return self.page.locator(".rw-body").filter(has_text="Renewal opens 90 days before expiry")

    @property
    def no_certificate_notice(self):
        return self.page.locator(".rw-body").filter(has_text=self.NO_CERTIFICATE)

    # ── Renewal application form ──────────────────────────────────────────────

    @property
    def form(self):
        return self.page.locator("form:has(input[name='declare'])")

    @property
    def form_title(self):
        return self.page.get_by_text(self.FORM_TITLE, exact=True)

    @property
    def question_labels(self):
        """The three question labels (1 changes, 2 cases, 3 supporting document)."""
        return self.form.locator(".rw-q label.t")

    def changes_radio(self, answer: str):
        """answer: 'no' or 'yes'."""
        return self.form.locator(f"input[name='changes_made'][value='{answer}']")

    @property
    def changes_radios(self):
        return self.form.locator("input[name='changes_made']")

    @property
    def changes_details(self):
        return self.form.locator("textarea[name='changes_details']")

    def cases_radio(self, answer: str):
        """answer: 'no' or 'yes'."""
        return self.form.locator(f"input[name='cases_pending'][value='{answer}']")

    @property
    def cases_radios(self):
        return self.form.locator("input[name='cases_pending']")

    @property
    def cases_details(self):
        return self.form.locator("textarea[name='cases_details']")

    @property
    def document_input(self):
        return self.form.locator("input[name='document']")

    @property
    def document_help(self):
        return self.form.get_by_text(self.DOCUMENT_HELP)

    @property
    def fee_box(self):
        return self.form.locator(".rw-fee")

    @property
    def fee_amount(self):
        return self.fee_box.locator("b")

    @property
    def declaration_checkbox(self):
        return self.form.locator("input[name='declare']")

    @property
    def declaration_label(self):
        return self.form.locator("label:has(input[name='declare'])")

    @property
    def submit_button(self):
        return self.page.get_by_role("button", name=self.SUBMIT_LABEL)

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Renewal page")
    def open(self):
        self.navigate(RENEWAL_URL)
        self.wait_for_load()

    @allure.step("Answer question 1 (anything changed): {answer}")
    def answer_changes(self, answer: str):
        self.changes_radio(answer).check()

    @allure.step("Describe the changes: {text}")
    def describe_changes(self, text: str):
        self.changes_details.fill(text)

    @allure.step("Answer question 2 (cases pending): {answer}")
    def answer_cases(self, answer: str):
        self.cases_radio(answer).check()

    @allure.step("Give the details of the cases: {text}")
    def describe_cases(self, text: str):
        self.cases_details.fill(text)

    @allure.step("Choose the supporting document: {path}")
    def choose_document(self, path: str):
        self.document_input.set_input_files(path)

    @allure.step("Tick the declaration")
    def tick_declaration(self):
        self.declaration_checkbox.check()

    @allure.step("Fill the renewal form")
    def fill_form(self, data) -> None:
        """Fills what ``data`` (a ``RenewalData``) gives; None / "" leaves a field untouched."""
        if data.changes_made:
            self.answer_changes(data.changes_made)
        if data.changes_details:
            self.describe_changes(data.changes_details)
        if data.cases_pending:
            self.answer_cases(data.cases_pending)
        if data.cases_details:
            self.describe_cases(data.cases_details)
        if data.document:
            self.choose_document(data.document)
        if data.declare:
            self.tick_declaration()

    @allure.step("Click 'Pay ₹2,000 & submit renewal'")
    def submit(self):
        """Posts the form; the page reloads with the server's answer (on dev no payment page appears)."""
        with self.page.expect_navigation():
            self.submit_button.click()
        self.wait_for_load()

    @allure.step("Click 'Back to my dashboard'")
    def back_to_dashboard(self):
        with self.page.expect_navigation():
            self.back_to_dashboard_link.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def fact_value(self, label: str) -> str:
        """A header fact's value, without its label."""
        return " ".join(self.fact(label).evaluate(
            "d => [...d.childNodes].filter(n => n.nodeName !== 'SMALL').map(n => n.textContent).join(' ')"
        ).split())

    def error_messages(self) -> list[str]:
        """The problems listed under 'Please correct:', in order."""
        lines = [" ".join(line.split()) for line in self.errors_box.inner_text().splitlines()]
        return [line for line in lines if line and line != self.ERRORS_HEADING]

    def state(self) -> str:
        """Where the agency stands on this page: 'form', 'pending', 'renewed', 'not_open', 'no_certificate'
        or 'login' (redirected away)."""
        if "renewal.php" not in self.page.url:
            return "login"
        if self.declaration_checkbox.count():
            return "form"
        if self.no_certificate_notice.count():
            return "no_certificate"
        if self.latest_application.count():
            text = self.latest_application.inner_text()
            if self.WITH_DEPARTMENT in text:
                return "pending"
            if self.RENEWED in text:
                return "renewed"
            return "decided"
        return "not_open"
