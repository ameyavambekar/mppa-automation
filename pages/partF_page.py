import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PART_F_URL = f"{FORMS_BASE}/partF.php"


class PartFPage(BasePage):
    """Page object for Step 4 — Part F: Certificates, Licences & Signature (forms/partF.php).

    Six certificate blocks, each keyed by an id in ``CERTIFICATES`` ('cl', 'sec',
    'em', 'lin', 'epf', 'esic'). Each has a Yes/No question (default No); "Yes"
    reveals a number, a DD/MM/YYYY date and a document upload, all required.
    When Part C's area of placement operations is "India and Overseas", the RA
    certificate ('em') is forced to Yes with its No disabled and ``RA_COMPULSORY_NOTE``
    under it (``ra_compulsory``) — seen 20-Nov-2026.
    Then the signature upload, the read-only Date of Application (today) and a Place
    dropdown of Maharashtra districts.

    Since 20-Nov-2026 every file input sits in a ``div.fu`` widget ("Choose File"
    button + file name); the help text ``p.hlp`` follows that widget. The signature
    takes a JPG, JPEG or PNG up to 5 MB: the page removes the white background in the
    browser (assets/js/signature_clean.js), swaps the chosen file for the cleaned PNG and
    shows it in ``signature_preview``; images it cannot clean (smaller than 150 × 40
    pixels, unreadable, no clear background) are rejected and cleared.

    The date fields keep only digits and "/" and add the slashes as you type,
    so type dates as digits (typing the slashes yourself doubles them).

    Validation is client-side and runs on submit — no alert() dialogs. Each
    invalid field gets a ``p.fld-err`` message (see ``field_error``) and the
    ``client_errors`` summary box lists them all. A chosen file is checked as
    soon as it is picked: a wrong type or a file over 2 MB is rejected and cleared.
    The 10 KB minimum is not checked by the page — the server rejects a smaller file
    on save and reloads Part F unsaved with its messages in ``server_errors``.

    The "Office Premises Document" section (``premises_*``, once shown for offline Service
    Modes) is no longer on Part F for any Service Mode since 20-Nov-2026; Documents
    (enclosures.php) asks every agency for an Office Address Proof instead.

    A successful save stays on Part F with ``SAVED_MESSAGE`` and "Next: Documents →"
    links. A saved Part F reopens editable (no "Edit this section"). A saved
    certificate document shows "Uploaded View ↗" (``has_saved_document``) and is no
    longer required; saving that certificate as No removes it. The signature is
    required (``SIGNATURE_REQUIRED_ERROR``); a saved one shows "✓ <file name>" in the
    upload widget (``saved_signature_name``) and is not required again.
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
        "esic": "Is your agency registered with ESIC?",   # shortened in portal 2.1.0 (17-Nov-2026)
    }
    # Yes/No radio name per certificate id
    _FLAGS = {"cl": "contract_labour_applicable", "sec": "security_applicable", "em": "emigration_applicable",
              "lin": "lin_applicable", "epf": "epf_applicable", "esic": "esic_applicable"}

    SECTIONS = ("Certificate & Licence Details", "Authorised Signatory — Signature", "Application Details")
    PREMISES_SECTION = "Office Premises Document"
    # SECTIONS when Part C's Service Mode includes offline work
    OFFLINE_SECTIONS = (SECTIONS[0], PREMISES_SECTION, *SECTIONS[1:])
    PLACE_PLACEHOLDER = "-- Select place (district) --"

    # Client-side texts
    SAVED_MESSAGE = "Part F saved. Proceed to document uploads."
    SAVED_DOCUMENT_NOTE = "Uploaded View ↗ (choose a file only to replace it)"
    SUBTITLE = "Dates must be in DD/MM/YYYY format"
    CERT_FILE_HINT = "PDF, JPG or PNG · 10 KB – 2 MB"
    RA_COMPULSORY_NOTE = "Compulsory — your area of placement operations (Part C) is India and Overseas."
    # Signature — since 20-Nov-2026: JPG, JPEG or PNG up to 5 MB, white background removed in the
    # browser, required.
    SIGNATURE_TITLE = "Upload Signature *"
    SIGNATURE_GUIDANCE = ("Sign on plain white paper with a dark (blue or black) pen, then scan or photograph it "
                          "and upload the image. The white background is removed automatically — you will see "
                          "the result before saving.")
    SIGNATURE_HINT = "JPG, JPEG or PNG · up to 5 MB · background removed automatically"
    SIGNATURE_ACCEPT = ".jpg,.jpeg,.png,image/jpeg,image/png"
    SIGNATURE_PREVIEW_HEADING = "Background removed — this is how your signature will appear:"
    APPLICATION_DATE_HINT = "Today's date (system date) — filled in automatically."
    ERRORS_HEADING = "Please fix the following before saving:"
    DOCUMENT_REQUIRED_ERROR = "Please upload the document."
    CERT_FILE_TYPE_ERROR = "Only PDF, JPG or PNG allowed."
    SIGNATURE_TYPE_ERROR = "Only a JPG, JPEG or PNG image is allowed for the signature."
    SIGNATURE_TOO_LARGE_ERROR = "The signature image is larger than 5 MB."
    SIGNATURE_REQUIRED_ERROR = "Upload the signature (JPG, JPEG or PNG)."
    # Shown by signature_clean.js in the browser when it cannot clean the image
    SIGNATURE_TOO_SMALL_ERROR = "The image is too small — upload a clear signature (at least 150 × 40 pixels)."
    SIGNATURE_UNREADABLE_ERROR = "The image could not be read — choose a JPG, JPEG or PNG file."
    SIGNATURE_BACKGROUND_ERROR = ("The background could not be removed — photograph the signature on plain white "
                                  "paper in good light.")
    # A saved signature shows "✓ <file name>" in the upload widget with this tooltip (seen 20-Nov-2026)
    SIGNATURE_SAVED_TOOLTIP = "Already uploaded — choose a file only to replace it"
    NO_FILE_CHOSEN = "No file chosen"
    FILE_TOO_LARGE_ERROR = "File is too large — max 2 MB."
    PLACE_REQUIRED_ERROR = "Place is required."
    PREMISES_TITLE = "Office Premises Owner Registration Document / Lease / Leave & Licence Agreement"
    PREMISES_NOTE = ("Shown because your service mode includes offline operations. Upload the ownership "
                     "registration document, or the lease / leave & licence agreement for your office premises.")
    PREMISES_REQUIRED_ERROR = "Please upload the office premises document."

    # Server-side texts (shown in ``server_errors`` after a rejected save)
    FILE_TOO_SMALL_ERROR = "File is too small — upload a clear, complete scan (minimum 10 KB)."

    @staticmethod
    def certificate_too_small_errors(name: str) -> tuple[str, ...]:
        """Server messages for a certificate document under 10 KB; ``name`` is e.g. 'Contractor Licence'.
        Since portal 2.1.0 (17-Nov-2026) only this one message is shown (no "<name>: Document upload is
        required." line)."""
        return (f"{name} document: {PartFPage.FILE_TOO_SMALL_ERROR}",)

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
    def server_errors(self):
        """Red box at the top after the server rejects a save (e.g. a file under 10 KB).
        Same ``alert-e`` class as ``client_errors``, which is excluded."""
        return self.page.locator(".alert-e:not(#clientErr)")

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

    @staticmethod
    def _file_hint(file_input):
        """``p.hlp`` after the ``div.fu`` widget that wraps ``file_input``."""
        return file_input.locator(
            "xpath=ancestor::div[contains(concat(' ',normalize-space(@class),' '),' fu ')][1]"
            "/following-sibling::p[contains(@class,'hlp')][1]")

    def certificate_file_hint(self, cert: str):
        return self._file_hint(self.certificate_file_input(cert))

    def saved_document_note(self, cert: str):
        """'Uploaded View ↗ (choose a file only to replace it)' — only while a document is on file."""
        return self.certificate_file_input(cert).locator(
            "xpath=ancestor::div[contains(@class,'fld')][1]//p[contains(normalize-space(),'Uploaded')]")

    @property
    def ra_compulsory(self):
        """RA_COMPULSORY_NOTE under the RA question — only when Part C's area is "India and Overseas"."""
        return self.certificate_block("em").get_by_text(self.RA_COMPULSORY_NOTE)

    def is_ra_compulsory(self) -> bool:
        """True when the RA certificate is forced to Yes (its No is disabled)."""
        return self.certificate_radio("em", False).is_disabled()

    def saved_document_link(self, cert: str):
        """'View ↗' link to the saved document."""
        return self.saved_document_note(cert).get_by_role("link", name="View ↗")

    def has_saved_document(self, cert: str) -> bool:
        """True when ``cert`` has a saved document on file ("Uploaded View ↗")."""
        return self.certificate_file_input(cert).get_attribute("data-has-file") == "1"

    # ── Signature & application details ───────────────────────────────────────

    @property
    def signature_input(self):
        """'Upload Signature *' — JPG, JPEG or PNG; replaced by the cleaned PNG once the background is removed."""
        return self.page.locator("#sigFile")

    @property
    def signature_file_name(self):
        """File name shown in the upload widget ("No file chosen" when empty)."""
        return self.signature_input.locator("xpath=preceding-sibling::span[contains(@class,'fu-name')]")

    @staticmethod
    def saved_signature_text(file_name: str) -> str:
        """What the upload widget shows for a saved signature: '✓ <file name>'."""
        return f"✓ {file_name}"

    def saved_signature_name(self) -> str:
        """File name of the signature on file ('' when none) — the input's ``data-current``."""
        return self.signature_input.get_attribute("data-current") or ""

    def has_saved_signature(self) -> bool:
        return self.signature_input.get_attribute("data-has-file") == "1"

    @property
    def signature_preview(self):
        """'Background removed — …' box with the cleaned signature; hidden until an image is cleaned."""
        return self.page.locator("#sigAuto")

    @property
    def signature_preview_image(self):
        return self.page.locator("#sigAutoImg")

    @property
    def signature_title(self):
        return self.signature_input.locator("xpath=ancestor::div[contains(@class,'cert-block')][1]/div[contains(@class,'cert-title')]")

    @property
    def signature_hint(self):
        return self._file_hint(self.signature_input)

    @property
    def signature_guidance(self):
        """Paragraph under the title explaining how to make a transparent PNG signature (SIGNATURE_GUIDANCE)."""
        return self.signature_input.locator(
            "xpath=ancestor::div[contains(@class,'fld')][1]/preceding-sibling::p[1]")

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

    # ── Office premises document (offline service modes only) ─────────────────

    @property
    def premises_file_input(self):
        """Office premises document upload (#premFile, PDF/JPG/PNG, 10 KB – 2 MB, required).
        ``data-has-file`` is "1" once a document is on file."""
        return self.page.locator("#premFile")

    @property
    def premises_block(self):
        return self.premises_file_input.locator("xpath=ancestor::div[contains(@class,'cert-block')][1]")

    @property
    def premises_title(self):
        """PREMISES_TITLE."""
        return self.premises_block.locator(".cert-title")

    @property
    def premises_note(self):
        """PREMISES_NOTE, above the upload."""
        return self.premises_block.locator("xpath=./p")

    @property
    def premises_label(self):
        """'Upload Document *'."""
        return self.premises_block.locator(".fld label")

    @property
    def premises_hint(self):
        """CERT_FILE_HINT under the upload."""
        return self.premises_block.locator("p.hlp")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Part F — Certificates, Licences & Signature")
    def open(self):
        """Navigates to Part F (requires a logged-in agency session with Part C saved)."""
        self.navigate(PART_F_URL)

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

    @allure.step("Choose office premises document {path}")
    def set_premises_document(self, path: str):
        self.premises_file_input.set_input_files(path)

    @allure.step("Choose signature {path}")
    def set_signature(self, path: str):
        """Chooses the signature and waits until the page has either cleaned it (the input then holds
        the cleaned file and ``data-cleaned`` names it) or rejected it (the input is emptied and a
        field error is shown)."""
        self.signature_input.set_input_files(path)
        self.page.wait_for_function(
            """() => {
                const i = document.getElementById('sigFile');
                const f = i.files[0];
                if (f) return i.dataset.cleaned === f.name + f.size;
                const err = i.closest('.fld').querySelector('.fld-err');
                return !!err && err.offsetParent !== null && err.textContent.trim() !== '';
            }""", timeout=20000)

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
