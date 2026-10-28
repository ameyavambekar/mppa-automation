import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PART_F_URL = f"{FORMS_BASE}/partF.php"


class PartFPage(BasePage):
    """Page object for Step 4 — Part F: Certificates, Licences & Signature (forms/partF.php).

    Six certificate blocks, each keyed by an id in ``CERTIFICATES`` ('cl', 'sec',
    'em', 'lin', 'epf', 'esic'). Each has a Yes/No question (default No); "Yes"
    reveals a number, a DD/MM/YYYY date and a document upload, all required.
    Then the specimen signature upload (JPG/PNG), the read-only Date of
    Application (today) and a Place dropdown of Maharashtra districts.

    The date fields keep only digits and "/" and add the slashes as you type,
    so type dates as digits (typing the slashes yourself doubles them).

    Validation is client-side and runs on submit — no alert() dialogs. Each
    invalid field gets a ``p.fld-err`` message (see ``field_error``) and the
    ``client_errors`` summary box lists them all. A chosen file is checked as
    soon as it is picked: a wrong type or a file over 2 MB is rejected and cleared.

    A successful save stays on Part F with ``SAVED_MESSAGE`` and "Next: Documents →"
    links. A saved Part F reopens editable (no "Edit this section"). A saved
    certificate document shows "Uploaded View ↗" (``has_saved_document``) and is no
    longer required; saving that certificate as No removes it. The signature is
    optional (a save without one succeeds).
    """

    # id → (block title, number label, date label); the labels appear in the error messages.
    CERTIFICATES = {
        "cl": ("Contractor Licence (under Section 12 of CLA, 1970)", "Licence / Certificate No.", "Date of Issue"),
        "sec": ("PSARA Licence (under Private Security Agencies Regulation Act, 2005)", "PSARA Licence No.",
                "Date of Issue"),
        "em": ("Recruiting Agent (RA) Certificate of Registration (under Emigration Act, 1983)",
               "RA Registration Certificate No.", "Date of Issue"),
        "lin": ("Shram Suvidha Labour Identification Number (LIN)", "LIN Number", "Date of Allotment"),
        "epf": ("EPF Establishment Code Allotment Letter", "EPFO Establishment Code Number", "Date of Allotment"),
        "esic": ("ESIC Code Allotment Letter", "ESIC Code Number", "Date of Allotment"),
    }
    QUESTIONS = {
        "cl": "Do you supply or deploy contract manpower/labour to third-party organizations?",
        "sec": "Do you recruit, train, or supply security personnel or security guards?",
        "em": "Do you recruit or place job seekers for overseas/international employment opportunities?",
        "lin": "Has a Labour Identification Number (LIN) been assigned to your establishment on the Shram Suvidha Portal?",
        "epf": "Is your agency registered with EPFO (or do you employ 20 or more staff/contract workers)?",
        "esic": "Is your agency registered with ESIC (or do you employ 10 or more covered employees)?",
    }
    # Yes/No radio name per certificate id
    _FLAGS = {"cl": "contract_labour_applicable", "sec": "security_applicable", "em": "emigration_applicable",
              "lin": "lin_applicable", "epf": "epf_applicable", "esic": "esic_applicable"}

    SECTIONS = ("Certificate & Licence Details", "Authorised Signatory — Specimen Signature", "Application Details")
    PLACE_PLACEHOLDER = "-- Select place (district) --"

    # Client-side texts
    SAVED_MESSAGE = "Part F saved. Proceed to document uploads."
    SAVED_DOCUMENT_NOTE = "Uploaded View ↗ (choose a file only to replace it)"
    SUBTITLE = "Dates must be in DD/MM/YYYY format"
    CERT_FILE_HINT = "PDF, JPG or PNG · 10 KB – 2 MB"
    SIGNATURE_HINT = "JPG or PNG ONLY — PDF not accepted for signatures · 10 KB – 2 MB"
    APPLICATION_DATE_HINT = "Today's date (system date) — filled in automatically."
    ERRORS_HEADING = "Please fix the following before saving:"
    DOCUMENT_REQUIRED_ERROR = "Please upload the document."
    CERT_FILE_TYPE_ERROR = "Only PDF, JPG or PNG allowed."
    SIGNATURE_TYPE_ERROR = "Only JPG or PNG allowed for the signature."
    FILE_TOO_LARGE_ERROR = "File is too large — max 2 MB."
    PLACE_REQUIRED_ERROR = "Place is required."

    @staticmethod
    def required_error(label: str) -> str:
        """'<label> is required.' — for a certificate's number or date label."""
        return f"{label} is required."

    @staticmethod
    def number_too_short_error(label: str) -> str:
        return f"{label} must be at least 3 characters."

    @staticmethod
    def number_invalid_error(label: str) -> str:
        return f"{label} contains invalid characters."

    @staticmethod
    def date_invalid_error(label: str) -> str:
        return f"{label} must be a valid DD/MM/YYYY date, not in the future."

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        """Heading 'Step 4 — Certificates, Licences & Signature (Form-I Part F)'."""
        return self.page.locator("//h2[contains(.,'Part F')]")

    @property
    def sub_title(self):
        """'Dates must be in DD/MM/YYYY format' under the heading."""
        return self.title.locator("xpath=following-sibling::p")

    @property
    def deadline_banner(self):
        """Banner '<N> days left to complete all steps and pay — deadline …' while unpaid."""
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        """'Save & Log out' link inside the deadline banner (../auth/logout.php)."""
        return self.page.get_by_role("link", name="Save & Log out")

    @property
    def back_to_part_c_link(self):
        """'← Part C' link top-right of the heading."""
        return self.page.get_by_role("link", name="← Part C")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` while that step is not yet saved (non-clickable)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def success_message(self):
        """SAVED_MESSAGE — shown after a successful save."""
        return self.page.locator(".alert-s")

    @property
    def next_documents_link(self):
        """'Next: Documents →' — shown once Part F is saved."""
        return self.page.get_by_role("link", name="Next: Documents →").first

    @property
    def client_errors(self):
        """Summary box after a blocked submit: ERRORS_HEADING, then '• <message>' per error."""
        return self.page.locator("#clientErr")

    @property
    def form(self):
        return self.page.locator("#partFForm")

    @property
    def form_fields(self):
        """Every input, select and textarea in the form."""
        return self.form.locator("input, select, textarea")

    @property
    def section_headings(self):
        """The three section headings, in page order (SECTIONS)."""
        return self.form.locator(".sec")

    @property
    def certificates_note(self):
        """Note starting 'Certificates are optional. …' above the certificates."""
        return self.form.locator("//p[contains(normalize-space(),'Certificates are optional')]")

    # ── Inline errors ─────────────────────────────────────────────────────────

    def field_error(self, field):
        """Inline ``p.fld-err`` under ``field`` (any locator inside a ``.fld`` box)."""
        return field.locator("xpath=ancestor::div[contains(@class,'fld')][1]/p[contains(@class,'fld-err')]")

    @property
    def field_errors(self):
        """Every inline error currently shown."""
        return self.page.locator("p.fld-err")

    # ── Certificates ──────────────────────────────────────────────────────────

    def certificate_block(self, cert: str):
        return self.page.locator(f"#blk_{cert}")

    def certificate_title(self, cert: str):
        return self.certificate_block(cert).locator(".cert-title")

    def certificate_question(self, cert: str):
        return self.certificate_block(cert).locator(".cert-q")

    def certificate_radio(self, cert: str, applies: bool):
        """The Yes ('1') or No ('0') radio of ``cert``."""
        return self.page.locator(f"input[name='{self._FLAGS[cert]}'][value='{'1' if applies else '0'}']")

    def certificate_body(self, cert: str):
        """Number, date and upload — has the ``hidden-block`` class while the answer is No."""
        return self.page.locator(f"#body_{cert}")

    def certificate_number_input(self, cert: str):
        """Max 100."""
        return self.page.locator(f"#certNo_{cert}")

    def certificate_date_input(self, cert: str):
        """DD/MM/YYYY, max 10; digits and '/' only, slashes added as you type."""
        return self.page.locator(f"#certDate_{cert}")

    def certificate_file_input(self, cert: str):
        return self.page.locator(f"#certFile_{cert}")

    def certificate_labels(self, cert: str):
        """Labels of the number, date and upload fields, in order."""
        return self.certificate_body(cert).locator("label")

    def certificate_file_hint(self, cert: str):
        return self.certificate_file_input(cert).locator("xpath=following-sibling::p[contains(@class,'hlp')]")

    def saved_document_note(self, cert: str):
        """'Uploaded View ↗ (choose a file only to replace it)' — only while a document is on file."""
        return self.certificate_file_input(cert).locator("xpath=preceding-sibling::p[contains(normalize-space(),'Uploaded')]")

    def saved_document_link(self, cert: str):
        """'View ↗' link to the saved document."""
        return self.saved_document_note(cert).get_by_role("link", name="View ↗")

    def has_saved_document(self, cert: str) -> bool:
        """True when ``cert`` has a saved document on file ("Uploaded View ↗")."""
        return self.certificate_file_input(cert).get_attribute("data-has-file") == "1"

    # ── Signature & application details ───────────────────────────────────────

    @property
    def signature_input(self):
        """'Signature Upload on Official Letter Head' — JPG / PNG only."""
        return self.page.locator("#sigFile")

    @property
    def signature_title(self):
        return self.signature_input.locator("xpath=ancestor::div[contains(@class,'cert-block')][1]/div[contains(@class,'cert-title')]")

    @property
    def signature_hint(self):
        return self.signature_input.locator("xpath=following-sibling::p[contains(@class,'hlp')]")

    @property
    def application_date_input(self):
        """Read-only, today's date as DD/MM/YYYY."""
        return self.page.locator("#appDate")

    @property
    def application_date_hint(self):
        return self.application_date_input.locator("xpath=following-sibling::p[contains(@class,'hlp')]")

    @property
    def place_select(self):
        """Maharashtra districts; PLACE_PLACEHOLDER by default."""
        return self.page.locator("#placeInp")

    @property
    def place_options(self):
        return self.place_select.locator("option")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        """'Save Part F & Continue' — becomes 'Saving…' and disabled once submitted."""
        return self.page.locator("#partFForm button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Part F — Certificates, Licences & Signature")
    def open(self):
        """Navigates to Part F (requires a logged-in agency session with Part C saved)."""
        self.navigate(PART_F_URL)

    @allure.step("Clear the Part F form (nothing is saved)")
    def clear_form(self):
        """Returns every field to its first-visit state client-side: every certificate
        answered No with empty fields, no files chosen and Place unselected."""
        for cert in self.CERTIFICATES:
            self.certificate_radio(cert, True).check()
            self.certificate_number_input(cert).fill("")
            self.certificate_date_input(cert).fill("")
            self.certificate_file_input(cert).set_input_files([])
            self.certificate_radio(cert, False).check()
        self.signature_input.set_input_files([])
        self.place_select.select_option(value="")

    @allure.step("Certificate '{cert}' applies: {applies}")
    def select_certificate(self, cert: str, applies: bool):
        self.certificate_radio(cert, applies).check()

    @allure.step("Certificate '{cert}': fill number {number}")
    def fill_certificate_number(self, cert: str, number: str):
        self.certificate_number_input(cert).fill(number)
        self.certificate_number_input(cert).blur()

    @allure.step("Certificate '{cert}': fill date {date}")
    def fill_certificate_date(self, cert: str, date: str):
        """Sets the whole DD/MM/YYYY value at once (like pasting)."""
        self.certificate_date_input(cert).fill(date)
        self.certificate_date_input(cert).blur()

    @allure.step("Type '{text}' key by key")
    def type_key_by_key(self, field, text: str):
        """Clears ``field`` and types ``text`` one key at a time, like a user."""
        field.fill("")
        field.press_sequentially(text)

    @allure.step("Certificate '{cert}': choose document {path}")
    def set_certificate_document(self, cert: str, path: str):
        self.certificate_file_input(cert).set_input_files(path)

    @allure.step("Choose signature {path}")
    def set_signature(self, path: str):
        self.signature_input.set_input_files(path)

    @allure.step("Select Place: {place}")
    def select_place(self, place: str):
        self.place_select.select_option(value=place)

    @allure.step("Certificate '{cert}': answer Yes and fill it")
    def fill_certificate(self, cert: str, number: str = None, date: str = None, document: str = None):
        """Answers Yes, then fills whichever of number / date / document are given."""
        self.select_certificate(cert, True)
        if number is not None:
            self.fill_certificate_number(cert, number)
        if date is not None:
            self.fill_certificate_date(cert, date)
        if document is not None:
            self.set_certificate_document(cert, document)

    @allure.step("Click 'Save Part F & Continue'")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click '← Part C'")
    def click_back_to_part_c(self):
        self.back_to_part_c_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
