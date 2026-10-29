import re

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

ENCLOSURES_URL = f"{FORMS_BASE}/enclosures.php"
# Below 6/6, the Premises Photos step sends the user back here with this query.
ENCLOSURES_LOCKED_STEP_URL = f"{ENCLOSURES_URL}?error=complete_enclosures_first"
PREMISES_URL = f"{FORMS_BASE}/premises.php"


class EnclosuresPage(BasePage):
    """Page object for Step 5 — Upload Documents (Enclosures) (forms/enclosures.php).

    Eight document rows numbered 1–8 in three groups. Each row has a PDF-only
    file chooser (``input[name='file<N>']`` — the field numbers skip 2, 8 and 9,
    see ``DOCUMENTS``). Documents 1–6 are mandatory, 7–8 optional. Per-document
    locators take the 1-based number shown on the page.

    A chosen file is checked straight away (PDF, 10 KB – 2 MB); an invalid one
    is removed and an error appears under its row. "Upload Documents" uploads
    every chosen file and reloads the step with "<N> file(s) uploaded
    successfully."; with nothing chosen it shows ``NO_FILES_MESSAGE``. The
    "Mandatory Documents — N/6 uploaded" counter only changes after uploading.
    An uploaded row shows ✓ in place of its number, the file name and a
    "View ↗" link; choosing a new file and uploading replaces it.

    At 6/6 a "Next: Premises Photos →" link (premises.php) appears. Below 6/6,
    premises.php sends the user back here (?error=complete_enclosures_first).
    """

    # number → (file field name, title, mandatory)
    DOCUMENTS = {
        1: ("file1", "PAN Card of the Agency", True),
        2: ("file3", "Office Address Proof", True),
        3: ("file4", "Office / Premises Photograph", True),
        4: ("file5", "Authorised Signatory — Signature & PAN in Letterhead", True),
        5: ("file6", "Address Proof of Key Persons", True),
        6: ("file7", "Specimen Signature of Authorised Signatory", True),
        7: ("file10", "Training Programme / Affiliation Certificate", False),
        8: ("file11", "Any Other Relevant Documents", False),
    }
    MANDATORY = (1, 2, 3, 4, 5, 6)
    GROUPS = ("Core Documents", "Key Persons", "Other")

    # Client-side texts
    TITLE = "Step 5 — Upload Documents (Enclosures)"
    SUBTITLE = "All uploads centralised here — PDF only · minimum 10 KB, maximum 2 MB per file"
    FILE_HINT = "PDF only · 10 KB – 2 MB"
    NOTE = ("Every document must be uploaded in PDF format only, with a size between 10 KB and 2 MB per file. "
            "JPG / PNG images and files above 2 MB will not be accepted.")
    NOT_PDF_ERROR = "Only PDF files are allowed."
    TOO_SMALL_ERROR = "File is smaller than 10 KB — upload a clear, complete scan."
    TOO_LARGE_ERROR = "File is larger than 2 MB — please upload a smaller PDF."
    NO_FILES_MESSAGE = "No files selected."

    @staticmethod
    def uploaded_message(count: int) -> str:
        return f"{count} file(s) uploaded successfully."

    @staticmethod
    def counter_text(count: int) -> str:
        return f"{count}/6 uploaded"

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
        """'Next: Premises Photos →' (premises.php) — shown once all six mandatory documents are uploaded."""
        return self.page.get_by_role("link", name="Next: Premises Photos →").first

    @property
    def note(self):
        """'Note: Every document must be uploaded in PDF format only …' with the tip."""
        return self.page.locator("//div[strong[normalize-space()='Note:']]")

    @property
    def mandatory_counter(self):
        """'<N>/6 uploaded' next to 'Mandatory Documents'."""
        return self.page.locator("span", has_text=re.compile(r"^\s*\d+/6 uploaded\s*$"))

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
        return self.file_input(number).locator("xpath=following-sibling::p[not(@id)][1]")

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

    @allure.step("Upload documents {documents}")
    def upload_documents(self, documents: dict):
        """Chooses ``{number: path}`` and clicks 'Upload Documents'."""
        for number, path in documents.items():
            self.choose_document(number, path)
        self.click_upload()

    @allure.step("Click '← Part F'")
    def click_back_to_part_f(self):
        self.back_to_part_f_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
