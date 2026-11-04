import re

import allure

from pages.base_page import BasePage
from config import AGENCY_BASE

FIRST_APPEAL_URL = f"{AGENCY_BASE}/appeals/first.php"
SECOND_APPEAL_URL = f"{AGENCY_BASE}/appeals/second.php"
MY_APPLICATION_URL = f"{AGENCY_BASE}/forms/view_application.php"


class FirstAppealPage(BasePage):
    """Agency — First Appeal, FORM-III (/module/agency/appeals/first.php, "First Appeal — FORM-III").

    Open to an agency whose application was refused. The page shows the two-appeals note ("Appeals
    remaining: N of 2"), a four-step journey (``.ap-track .ap-step``: Application · First Appeal ·
    Division · Second Appeal · Commissionerate · Result) and, while no first appeal is on file, the form
    ``#apForm`` (``multipart/form-data``, posts back to itself) in numbered cards (``.ap-card``):

    * 1–4 Appellant and 5 Details of Order Appealed Against — read-only boxes (``.ap-ro``: a ``small``
      label, then the value) taken from the agency and the refusal order; they cannot be changed
    * 6  Grounds of Appeal — ``grounds[]`` checkboxes (at least one; "Other" reveals ``grounds_other``)
    * 7  Brief Facts — ``brief_facts`` (required, at least 20 characters)
    * 8  Relief Sought — ``relief_type`` radios + ``relief_sought`` (required, at least 10 characters)
    * 9  Limitation — read-only: date of communication and "Filed within 60 days?"
    * 10 Documents — PDF only, max 2 MB each; (d) Order of the Registering Authority is required
    * Verification — signatory / designation / place (pre-filled from the application), the date, and
      the required ``declare`` tick

    Submitting asks for confirmation (browser confirm()); with no ground ticked or a file over 2 MB it
    shows an alert() instead.

    Locators are ``@property`` methods, actions are ``@allure.step`` decorated, and all assertions stay in
    the tests (use ``expect()`` against these locators).
    """

    GROUNDS = (
        "error_of_law", "procedural_irregularity", "jurisdictional_error",
        "non_consideration", "natural_justice", "other",
    )
    RELIEFS = (
        "Setting Aside the Order",
        "Modification of Order",
        "Remand for Fresh Consideration",
    )
    # logical document slot → file input name (Section 10)
    DOC_SLOTS = {
        "order":    "doc_order",      # (d) Order of the Registering Authority (self-attested) — REQUIRED
        "original": "doc_original",   # (a) Original application (self-attested)
        "ack":      "doc_ack",        # (b) Acknowledgement issued by the Registering Authority
        "fees":     "doc_fees",       # (c) Fee receipt
        "other":    "doc_other",      # (e) Any other document
    }
    # read-only box labels (Sections 1–5, 9)
    APPELLANT_FIELDS = ("1. Name of Agency", "2. Registration No.", "3. Registered Address", "4. Email", "4. Mobile")
    ORDER_FIELDS = ("(a) Order Number", "(b) Date of Order", "(c) Authority Passing the Order", "Reason given in the order")
    LIMITATION_FIELDS = ("(a) Date of communication of the order", "(b) Filed within 60 days?")

    # ── Page header, note and journey ─────────────────────────────────────────

    @property
    def breadcrumb(self):
        """'Home › My Application › First Appeal (FORM-III)' under the site header."""
        return self.page.locator(".border-b .max-w-6xl").first

    @property
    def form_badge(self):
        return self.page.get_by_text("FORM-III · See Rule 8", exact=True)

    @property
    def page_heading(self):
        return self.page.locator(".ap-wrap h2")

    @property
    def header_lines(self):
        """The two lines under the heading: 'To be decided by the …' and 'Under Section 7(1) …'."""
        return self.page.locator(".ap-wrap h2 ~ p")

    @property
    def header_links(self):
        """Every link / button in the page header (only '← My Application')."""
        return self.page.locator(".ap-wrap > div").first.locator("a, button")

    @property
    def blocking_note(self):
        """The note shown instead of the form when no appeal can be filed — e.g. 'An appeal can be filed only
        when your application has been rejected …' (or, on the Second Appeal page, why it is not open yet)."""
        return self.page.locator(".ap-note").filter(has_not_text="You can file only TWO")

    @property
    def my_application_link(self):
        return self.page.locator(".ap-wrap").get_by_role("link", name="← My Application")

    @property
    def two_appeals_note(self):
        return self.page.locator(".ap-note").filter(has_text="You can file only TWO appeals")

    @property
    def appeals_remaining(self):
        """"Appeals remaining: N of 2"."""
        return self.two_appeals_note.get_by_text(re.compile(r"^Appeals remaining:"))

    @property
    def journey_steps(self):
        return self.page.locator(".ap-track .ap-step")

    def journey_step(self, title: str):
        """'Application', 'First Appeal · Division', 'Second Appeal · Commissionerate' or 'Result'."""
        return self.journey_steps.filter(has=self.page.locator("b", has_text=re.compile(rf"^{re.escape(title)}$")))

    def journey_status(self, title: str):
        return self.journey_step(title).locator("span")

    @property
    def notes(self):
        """Every note box on the page (``.ap-note``) — e.g. the two-appeals note, or the appeal on file."""
        return self.page.locator(".ap-note")

    # ── Form ──────────────────────────────────────────────────────────────────

    @property
    def appeal_form(self):
        return self.page.locator("#apForm")

    @property
    def addressee(self):
        """The 'To, The First Appellate Authority, …' card."""
        return self.appeal_form.locator(".ap-card").first

    def card(self, number: str):
        """A numbered card by its ``.ap-num`` label: '1–4', '5', '6' … '10', or '✓' (Verification)."""
        return self.appeal_form.locator(".ap-card").filter(
            has=self.page.locator(".ap-num", has_text=re.compile(rf"^{re.escape(number)}$")))

    def read_only_field(self, label: str):
        """A read-only box (``.ap-ro``) by its label, e.g. '2. Registration No.' or '(a) Order Number'."""
        return self.page.locator(".ap-ro").filter(
            has=self.page.locator("small", has_text=re.compile(rf"^{re.escape(label)}$")))

    @property
    def order_locked_note(self):
        return self.page.locator(".ap-lock")

    def ground_checkbox(self, value: str):
        """A grounds-of-appeal checkbox by its value (one of GROUNDS)."""
        return self.page.locator(f"input[name='grounds[]'][value='{value}']")

    def ground_box(self, value: str):
        """The clickable box (``label.ap-chk``) around a ground checkbox."""
        return self.page.locator("label.ap-chk").filter(has=self.ground_checkbox(value))

    @property
    def other_ground_box(self):
        return self.page.locator("#otherBox")

    @property
    def grounds_other_input(self):
        return self.page.locator("input[name='grounds_other']")

    @property
    def brief_facts_textarea(self):
        return self.page.locator("textarea[name='brief_facts']")

    def relief_radio(self, value: str):
        """A relief-type radio by its value (one of RELIEFS)."""
        return self.page.locator(f"input[name='relief_type'][value='{value}']")

    @property
    def relief_sought_textarea(self):
        return self.page.locator("textarea[name='relief_sought']")

    def document_input(self, slot: str):
        """A file input by logical slot (one of DOC_SLOTS keys)."""
        return self.page.locator(f"input[name='{self.DOC_SLOTS[slot]}']")

    def document_box(self, slot: str):
        return self.page.locator(".ap-up").filter(has=self.document_input(slot))

    @property
    def signatory_name_input(self):
        return self.page.locator("input[name='signatory_name']")

    @property
    def signatory_designation_input(self):
        return self.page.locator("input[name='signatory_designation']")

    @property
    def place_input(self):
        return self.page.locator("input[name='place']")

    @property
    def verification_date(self):
        """The read-only Date in the Verification card."""
        return self.card("✓").locator(".ap-ro")

    @property
    def declaration_checkbox(self):
        return self.page.locator("input[name='declare']")

    @property
    def declaration_text(self):
        return self.page.locator("label.ap-chk").filter(has=self.declaration_checkbox)

    @property
    def submit_button(self):
        return self.page.locator("#apForm button.ap-btn")

    @property
    def submit_note(self):
        """'The authority will decide your appeal within 60 days. A confirmation e-mail … <email>.'"""
        return self.submit_button.locator("xpath=following-sibling::p[1]")

    # ── Messages ──────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        """'Your First Appeal (FORM-III) #N has been submitted to the reviewing authority. …' (after filing)."""
        return self.page.locator(".alert-success")

    @property
    def error_alert(self):
        return self.page.locator(".alert-error, .ui-alert-error")

    # ── The appeal on file (shown instead of the form) ────────────────────────

    @property
    def filed_appeal_card(self):
        """'#N · Your First Appeal — Pending decision' with its Filed on / Sent to / Order appealed against /
        Grounds / Relief sought / Decision expected by rows (``.ap-row``: ``.k`` label, then the value)."""
        return self.page.locator(".ap-card").filter(has=self.page.locator(".ap-title", has_text="Your First Appeal"))

    @property
    def filed_appeal_number(self):
        """'#N'."""
        return self.filed_appeal_card.locator(".ap-num")

    @property
    def filed_appeal_title(self):
        return self.filed_appeal_card.locator(".ap-title")

    def filed_appeal_row(self, label: str):
        """A row of the appeal on file by its label, e.g. 'Grounds' or 'Decision expected by'."""
        return self.filed_appeal_card.locator(".ap-row").filter(
            has=self.page.locator(".k", has_text=re.compile(rf"^{re.escape(label)}$")))

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the First Appeal (FORM-III) page")
    def open(self):
        self.navigate(FIRST_APPEAL_URL)
        self.wait_for_load()

    @allure.step("Open the Second Appeal (FORM-IV) page")
    def open_second_appeal(self):
        """The Second Appeal page shares this page's header, note and journey; only its blocking note is read
        here (the FORM-IV form itself is KAN-15)."""
        self.navigate(SECOND_APPEAL_URL)
        self.wait_for_load()

    @allure.step("Click the box of the ground '{value}'")
    def click_ground_box(self, value: str):
        """Clicks the label text (not the small checkbox) — the whole box toggles the ground."""
        self.ground_box(value).get_by_text(re.compile(r"\w")).first.click()

    @allure.step("Type into 'Specify other ground' key by key")
    def type_other_ground(self, text: str):
        """Types like a user, so the field's 300-character limit applies."""
        self.ground_checkbox("other").check()
        self.grounds_other_input.fill("")
        self.grounds_other_input.press_sequentially(text)

    @allure.step("Tick grounds of appeal: {grounds}")
    def select_grounds(self, grounds):
        """grounds: an iterable of GROUNDS values to tick."""
        for value in grounds:
            self.ground_checkbox(value).check()

    @allure.step("Specify the 'Other' ground: {text}")
    def specify_other_ground(self, text: str):
        """Ticks 'Other' (if not already) and fills the revealed text box."""
        self.ground_checkbox("other").check()
        self.grounds_other_input.fill(text)

    @allure.step("Fill brief facts")
    def fill_brief_facts(self, text: str):
        self.brief_facts_textarea.fill(text)

    @allure.step("Select relief type: {relief_type}")
    def select_relief_type(self, relief_type: str):
        self.relief_radio(relief_type).check()

    @allure.step("Fill the specific relief sought")
    def fill_relief_sought(self, text: str):
        self.relief_sought_textarea.fill(text)

    @allure.step("Upload document '{slot}': {path}")
    def upload_document(self, slot: str, path: str):
        self.document_input(slot).set_input_files(path)

    @allure.step("Upload supporting documents")
    def upload_documents(self, documents: dict):
        """documents: mapping of DOC_SLOTS key → file path."""
        for slot, path in documents.items():
            self.upload_document(slot, path)

    @allure.step("Fill verification: place={place}, signatory={signatory_name}, designation={signatory_designation}")
    def fill_verification(self, place: str = None, signatory_name: str = None, signatory_designation: str = None):
        """Only the values given are typed; the pre-filled ones are kept otherwise."""
        if signatory_name is not None:
            self.signatory_name_input.fill(signatory_name)
        if signatory_designation is not None:
            self.signatory_designation_input.fill(signatory_designation)
        if place is not None:
            self.place_input.fill(place)

    @allure.step("Tick the verification declaration")
    def accept_declaration(self):
        self.declaration_checkbox.check()

    @allure.step("Click 'Submit First Appeal' and answer the prompt ({action})")
    def submit_and_handle_alert(self, action: str = "accept") -> str:
        """Clicks Submit and returns the confirm() / alert() text ('' if none). Accepting the confirm
        posts the form; the page reloads."""
        return self.click_and_handle_alert(self.submit_button, action=action)

    @allure.step("Submit the First Appeal (accept the confirmation)")
    def submit(self) -> str:
        """Clicks Submit, accepts the confirmation and waits for the page to reload; returns the prompt text."""
        with self.page.expect_navigation():
            message = self.click_and_handle_alert(self.submit_button, action="accept")
        self.wait_for_load()
        return message

    # ── Composite actions ─────────────────────────────────────────────────────

    @allure.step("Fill the First Appeal form")
    def fill_appeal(self, data):
        """Fills every editable section from a ``FirstAppealData`` value object — but does not submit."""
        self.select_grounds([g for g in data.grounds if g != "other"])
        if "other" in data.grounds:
            self.specify_other_ground(data.grounds_other)
        self.fill_brief_facts(data.brief_facts)
        if data.relief_type:
            self.select_relief_type(data.relief_type)
        self.fill_relief_sought(data.relief_sought)
        if data.documents:
            self.upload_documents(data.documents)
        self.fill_verification(data.place, data.signatory_name, data.signatory_designation)
        if data.declare:
            self.accept_declaration()

    @allure.step("File the First Appeal")
    def file_appeal(self, data) -> str:
        """Fills the whole form and submits it (accepting the confirmation); returns the prompt text."""
        self.fill_appeal(data)
        return self.submit()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def read_only_value(self, label: str) -> str:
        """The value of a read-only box, without its label."""
        box = self.read_only_field(label)
        return box.evaluate("e => [...e.childNodes].filter(n => n.nodeName !== 'SMALL')"
                            ".map(n => n.textContent).join('').replace(/\\s+/g, ' ').trim()")

    def get_agency_name(self) -> str:
        return self.read_only_value("1. Name of Agency")

    def get_registration_no(self) -> str:
        return self.read_only_value("2. Registration No.")

    def get_order_number(self) -> str:
        return self.read_only_value("(a) Order Number")

    def filed_appeal_value(self, label: str) -> str:
        return self.filed_appeal_row(label).locator("span:not(.k)").inner_text().strip()

    def form_is_valid(self) -> bool:
        """Whether the browser's built-in checks accept the form as filled (required / minlength)."""
        return self.appeal_form.evaluate("f => f.checkValidity()")

    def invalid_fields(self) -> list[str]:
        """Names of the fields the browser's built-in checks reject (a radio group is named once)."""
        return self.appeal_form.evaluate(
            "f => [...new Set([...f.elements].filter(e => e.name && !e.checkValidity()).map(e => e.name))]")

    def read_only_labels(self, card_number: str) -> list[str]:
        """Labels of the read-only boxes in a card, in page order (e.g. '1–4')."""
        return self.card(card_number).locator(".ap-ro small").all_text_contents()

    def files_chosen(self, slot: str) -> int:
        return self.document_input(slot).evaluate("e => e.files.length")

    def has_existing_appeal(self) -> bool:
        """Whether a first appeal is already on file (the form is no longer offered)."""
        return self.appeal_form.count() == 0 or "Not filed" not in self.journey_status("First Appeal · Division").inner_text()
