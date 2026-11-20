import re

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

ENCLOSURES_URL = f"{FORMS_BASE}/enclosures.php"
# Until every mandatory document is uploaded, the Premises Photos step sends the user back here with this query.
ENCLOSURES_LOCKED_STEP_URL = f"{ENCLOSURES_URL}?error=complete_enclosures_first"
PREMISES_URL = f"{FORMS_BASE}/premises.php"


class EnclosuresPage(BasePage):
    """Page object for Step 5 — Upload Documents (Enclosures) (forms/enclosures.php).

    Since 20-Nov-2026 document 1 is the PAN card uploaded at registration (``PAN_card_<PAN>.pdf``), so the
    step opens at 1/2, and the address proof type list ends with "Other", which asks for the document name.

    Since portal 2.1.0 (17-Nov-2026): four document rows numbered 1–4 in two groups. Each row has a
    PDF-only file chooser (``input[name='file<N>']`` — see ``DOCUMENTS`` for the field names). Documents
    1–2 are mandatory, 3–4 optional; the office address proof (2) has a type select (``doctype3``)
    above its chooser. Per-document locators take the 1-based number shown on the page.

    A chosen file is checked straight away (PDF, 10 KB – 2 MB); an invalid one
    is removed and an error appears under its row. "Upload Documents" uploads
    every chosen file and reloads the step with "<N> file(s) uploaded
    successfully."; with nothing chosen it shows ``NO_FILES_MESSAGE``. The
    "Mandatory Documents — N/2 uploaded" counter only changes after uploading.
    An uploaded row shows ✓ in place of its number, the file name and a
    "View ↗" link; choosing a new file and uploading replaces it.

    At 2/2 a "Next: Premises Photos →" link (premises.php) appears. Below 2/2,
    premises.php sends the user back here (?error=complete_enclosures_first).
    """

    # number → (file field name, title, mandatory)
    # Portal 2.1.0 (17-Nov-2026) cut the step to four rows: two mandatory (PAN card; office address proof,
    # whose type is chosen first in ``doctype3``) and two optional. The premises photograph, signatory and
    # key-person documents and the specimen signature are gone (the signature moved to Part F).
    DOCUMENTS = {
        1: ("file1", "PAN Card of the Agency", True),
        2: ("file3", "Office Address Proof", True),
        3: ("file10", "Training Programme / Affiliation Certificate", False),
        4: ("file11", "Any Other Relevant Documents", False),
    }
    MANDATORY = (1, 2)
    GROUPS = ("Core Documents", "Other")
    ADDRESS_PROOF_TYPES = ("Electricity (Light) Bill", "Rent / Leave and Licence Agreement",
                           "Property Ownership Document (Index-II / Property Tax Receipt)", "Other")
    # Since 20-Nov-2026: choosing "Other" shows a text box (``doctype_other3``) for the name of the document.
    ADDRESS_PROOF_OTHER = "Other"
    ADDRESS_PROOF_OTHER_PLACEHOLDER = "Type of document, e.g. Water bill, Telephone bill, NOC from owner"
    ADDRESS_PROOF_OTHER_MAXLENGTH = 80
    # Since 20-Nov-2026 the PAN card uploaded on the registration form is already document 1, saved as
    # "PAN_card_<PAN>.pdf", so an agency that has uploaded nothing here opens the step at 1/2.
    REGISTRATION_PAN_PREFIX = "PAN_card_"
    UPLOADED_AT_START = 1

    # Client-side texts
    TITLE = "Step 5 — Upload Documents (Enclosures)"
    SUBTITLE = "PDF only · minimum 10 KB, maximum 2 MB per file"
    FILE_HINT = "PDF only · 10 KB – 2 MB"
    NOTE = "Documents must be uploaded as PDF (10 KB – 2 MB each)."
    # Shortened on 20-Nov-2026 ("the working area and" dropped)
    NOTE_PHOTOS = ("Office photographs are taken in the next step (Premises Photos) — including the service-charges "
                   "display board.")
    PAN_HELP = "For a Proprietorship: PAN card of the proprietor."
    PAN_FROM_REGISTRATION = ("Taken from the PAN card you uploaded at registration — nothing more to do. "
                             "Choose a file only if you want to replace it.")
    SAVED_FILE_TOOLTIP = "Already uploaded — choose a file only to replace it"
    ADDRESS_PROOF_HELP = "Choose the document type, then upload it."
    ADDRESS_PROOF_PLACEHOLDER = "— Select type of address proof —"
    NOT_PDF_ERROR = "Only PDF files are allowed."
    # Reworded in portal 2.1.0 (17-Nov-2026)
    TOO_SMALL_ERROR = "File is too small — upload a clear, complete file."
    TOO_LARGE_ERROR = "File is larger than 2 MB."
    NO_FILES_MESSAGE = "No files selected."
    # Server message when document 2 is uploaded with no type chosen in ``doctype3`` (dev, 17-Nov-2026);
    # the file is not saved.
    ADDRESS_PROOF_TYPE_REQUIRED = "Office Address Proof: choose the type of document from the list."
    # Server message when "Other" is chosen with a name under 3 characters (dev, 20-Nov-2026). With a blank name
    # the page also adds ADDRESS_PROOF_TYPE_REQUIRED and resets the select (possible defect, KAN-TC-865).
    ADDRESS_PROOF_OTHER_NAME_REQUIRED = ('Office Address Proof: you chose "Other" — type the name of the document '
                                         '(at least 3 characters).')

    @staticmethod
    def uploaded_message(count: int) -> str:
        return f"{count} file(s) uploaded successfully."

    @staticmethod
    def counter_text(count: int) -> str:
        return f"{count}/{len(EnclosuresPage.MANDATORY)} uploaded"

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(.,'Upload Documents')]")

    @property
    def sub_title(self):
        return self.title.locator("xpath=following-sibling::p")

    @property
    def deadline_banner(self):
        """Banner '<N> days left to complete all steps and pay — deadline …' while unpaid."""
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        return self.page.get_by_role("link", name="Save & Log out")

    @property
    def back_to_part_f_link(self):
        """'← Part F' link top-right of the heading."""
        return self.page.get_by_role("link", name="← Part F")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` while that step is not yet saved (non-clickable)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def next_links(self):
        """Any 'Next …' link — none while mandatory documents are missing."""
        return self.page.get_by_role("link", name=re.compile(r"^Next"))

    @property
    def next_premises_photos_link(self):
        """'Next: Premises Photos →' (premises.php) — shown once every mandatory document is uploaded."""
        return self.page.get_by_role("link", name="Next: Premises Photos →").first

    @property
    def note(self):
        """'Note: Documents must be uploaded as PDF …' with the line about the Premises Photos step."""
        return self.page.locator("//div[strong[normalize-space()='Note:']]")

    @property
    def mandatory_counter(self):
        """'<N>/<mandatory> uploaded' next to 'Mandatory Documents'."""
        return self.page.locator("span", has_text=re.compile(rf"^\s*\d+/{len(self.MANDATORY)} uploaded\s*$"))

    @property
    def address_proof_type_select(self):
        """Type of the office address proof (ADDRESS_PROOF_TYPES), chosen before its file."""
        return self.page.locator("select[name='doctype3']")

    @property
    def address_proof_other_input(self):
        """Name of the document when the address proof type is "Other" — hidden for every other type."""
        return self.page.locator("input[name='doctype_other3']")

    @property
    def address_proof_help(self):
        """'Choose the document type, then upload it.' above the address proof type select."""
        return self.address_proof_type_select.locator("xpath=preceding-sibling::p[1]")

    @property
    def progress_fill(self):
        """Fill of the mandatory progress bar (style width:<percent>%)."""
        return self.page.locator(".prog-fill")

    @property
    def messages(self):
        """Messages shown after clicking 'Upload Documents' (success or 'No files selected.')."""
        return self.page.locator("[class*='alert']").filter(has_text=re.compile(r"\S"))

    @property
    def group_headings(self):
        return self.page.locator(".group-hdr")

    @property
    def document_rows(self):
        return self.page.locator(".doc-row")

    # ── Document rows ─────────────────────────────────────────────────────────

    def file_input(self, number: int):
        return self.page.locator(f"input[name='{self.DOCUMENTS[number][0]}']")

    def document_row(self, number: int):
        """Has the class ``done`` once the document is uploaded."""
        return self.page.locator(".doc-row").filter(has=self.file_input(number))

    def document_number(self, number: int):
        """Shows the number, or ✓ once the document is uploaded."""
        return self.document_row(number).locator(".doc-num")

    def document_title(self, number: int):
        return self.document_row(number).locator("span").first

    def required_marker(self, number: int):
        """Red '*' — on mandatory documents only."""
        return self.document_row(number).locator(".badge-req")

    def document_hint(self, number: int):
        """'PDF only · 10 KB – 2 MB' under the file chooser (the chooser sits in a ``div.fu`` widget)."""
        return self.file_input(number).locator(
            "xpath=ancestor::div[contains(concat(' ',normalize-space(@class),' '),' fu ')][1]/following-sibling::p[1]")

    def document_help(self, number: int):
        """Help line under the title (documents 1 and 2 only), e.g. PAN_HELP."""
        return self.document_row(number).locator("xpath=(.//div[span])[1]/following-sibling::p[1]")

    def file_name(self, number: int):
        """Name next to 'Choose File': 'No file chosen', the chosen file, or '✓ <saved file>' (SAVED_FILE_TOOLTIP)."""
        return self.file_input(number).locator("xpath=preceding-sibling::span[contains(@class,'fu-name')]")

    def saved_file(self, number: int) -> str:
        """File name of the document on file ('' when none), from the chooser's ``data-current``."""
        return self.file_input(number).get_attribute("data-current") or ""

    @property
    def pan_from_registration_note(self):
        """PAN_FROM_REGISTRATION on document 1 while it is the PAN card from registration."""
        return self.document_row(1).get_by_text(self.PAN_FROM_REGISTRATION)

    def has_registration_pan(self) -> bool:
        """Document 1 is the PAN card carried over from registration (not replaced on this step)."""
        return self.saved_file(1).startswith(self.REGISTRATION_PAN_PREFIX)

    def document_error(self, number: int):
        """Error under the row, shown when an invalid file is chosen."""
        return self.page.locator(f"#ferr{self.DOCUMENTS[number][0][4:]}")

    def uploaded_badge(self, number: int):
        """'✓ <file name> View ↗' — only once the document is uploaded."""
        return self.document_row(number).locator(".badge-done")

    def view_link(self, number: int):
        """'View ↗' — opens the uploaded PDF in a new tab."""
        return self.uploaded_badge(number).get_by_role("link", name="View ↗")

    def is_uploaded(self, number: int) -> bool:
        return "done" in (self.document_row(number).get_attribute("class") or "").split()

    def uploaded_count(self) -> int:
        """Mandatory documents uploaded, read from the counter."""
        return int(self.mandatory_counter.inner_text().strip().split("/")[0])

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def upload_button(self):
        """'Upload Documents'."""
        return self.page.locator("form button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Documents step (Enclosures)")
    def open(self):
        """Navigates to the Documents step (requires a logged-in agency session with Part F saved)."""
        self.navigate(ENCLOSURES_URL)

    @allure.step("Document {number}: choose {path}")
    def choose_document(self, number: int, path: str):
        self.file_input(number).set_input_files(path)

    @allure.step("Click 'Upload Documents'")
    def click_upload(self):
        self.upload_button.click()
        self.page.wait_for_load_state("networkidle")

    @allure.step("Office address proof type: {proof_type}")
    def select_address_proof_type(self, proof_type: str):
        self.address_proof_type_select.select_option(value=proof_type)

    @allure.step("Office address proof name (Other): {name}")
    def enter_address_proof_other(self, name: str):
        self.address_proof_other_input.fill(name)

    @allure.step("Upload documents {documents}")
    def upload_documents(self, documents: dict, address_proof_type: str = ADDRESS_PROOF_TYPES[0],
                         address_proof_other: str = None):
        """Chooses ``{number: path}`` and clicks 'Upload Documents'. When the office address proof (2) is
        among them, its type is chosen first (``address_proof_type``) and, for "Other", the name of the
        document (``address_proof_other``)."""
        if 2 in documents and address_proof_type:
            self.select_address_proof_type(address_proof_type)
            if address_proof_other is not None:
                self.enter_address_proof_other(address_proof_other)
        for number, path in documents.items():
            self.choose_document(number, path)
        self.click_upload()

    @allure.step("Click '← Part F'")
    def click_back_to_part_f(self):
        self.back_to_part_f_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
