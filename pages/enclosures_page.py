import allure

from pages.base_page import BasePage
from config import FORMS_BASE


class EnclosuresPage(BasePage):
    """Step 5 — Enclosures / Supporting Documents.

    Eleven uniform document rows, each with a file input named ``file1`` …
    ``file11``. Slots 1–5 are mandatory (all must be uploaded to unlock
    Step 6); slots 6–11 are optional. Per-slot locators take the 1-based
    slot number.
    """

    # Slot number → document title, as listed on the page
    DOCUMENTS = {
        1: "Proof of Identity & Address",
        2: "Certificate of Incorporation / Registration",
        3: "Office Address Proof",
        4: "Geo-tagged Placement Agency Photos",
        5: "Fee Payment Acknowledgement",
        6: "Training Details",
        7: "Contract Labour Registration Certificate",
        8: "Emigration Act Certificate",
        9: "Private Security Agency License",
        10: "LIN / EPFO / ESI Certificate",
        11: "Other Documents",
    }
    REQUIRED_SLOTS = (1, 2, 3, 4, 5)
    OPTIONAL_SLOTS = (6, 7, 8, 9, 10, 11)

    # ── Page headings ─────────────────────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 5')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 5')]/following-sibling::p")

    @property
    def section_header(self):
        return self.page.locator(".section-header")

    @property
    def note_box(self):
        # "📌 Note — Documents marked Required (1–5) must all be uploaded..."
        return self.page.locator("//p[contains(text(),'Documents marked')]/parent::div")

    # ── Navigation ────────────────────────────────────────────────────────────

    @property
    def breadcrumb_dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")

    @property
    def back_to_step4_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Step 4')]").first

    # ── Mandatory-upload progress ─────────────────────────────────────────────

    @property
    def progress_text(self):
        # e.g. "0/5 mandatory" / "5/5 mandatory"
        return self.page.locator("//span[contains(text(),'mandatory')]")

    @property
    def progress_bar_fill(self):
        return self.page.locator("//span[contains(text(),'mandatory')]/preceding-sibling::div/div")

    # ── Document rows (1-based slot number) ───────────────────────────────────

    @property
    def doc_rows(self):
        return self.page.locator(".doc-row")

    def doc_row(self, slot: int):
        return self.page.locator(f"//input[@name='file{slot}']/ancestor::div[contains(@class,'doc-row')]")

    def doc_number_badge(self, slot: int):
        # Carries class 'required' (blue) or 'uploaded' (green) per state
        return self.doc_row(slot).locator(".doc-num")

    def doc_title(self, slot: int):
        return self.doc_row(slot).locator("p").first

    def doc_required_badge(self, slot: int):
        return self.doc_row(slot).locator(".badge-req")

    def doc_optional_badge(self, slot: int):
        return self.doc_row(slot).locator(".badge-opt")

    def doc_uploaded_badge(self, slot: int):
        return self.doc_row(slot).locator(".badge-done")

    def file_input(self, slot: int):
        return self.page.locator(f"input[name='file{slot}']")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def upload_documents_button(self):
        # "📤 Upload Documents"
        return self.page.locator("button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Enclosures page directly")
    def open(self):
        self.navigate(f"{FORMS_BASE}/enclosures.php")

    @allure.step("Set document in slot {slot}: {path}")
    def set_document(self, slot: int, path: str):
        self.file_input(slot).set_input_files(path)

    @allure.step("Set all required documents (slots 1–5)")
    def set_required_documents(self, paths):
        """paths: a single file path used for all five required slots, or a
        dict mapping slot number → file path."""
        if isinstance(paths, dict):
            for slot, path in paths.items():
                self.set_document(slot, path)
        else:
            for slot in self.REQUIRED_SLOTS:
                self.set_document(slot, paths)

    @allure.step("Click 'Upload Documents'")
    def click_upload_documents(self):
        self.upload_documents_button.click()

    @allure.step("Click 'Upload Documents' and handle alert")
    def click_upload_documents_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.upload_documents_button, action=action)

    @allure.step("Click '← Step 4'")
    def click_back_to_step4(self):
        self.back_to_step4_link.click()

    @allure.step("Upload all required documents and submit")
    def upload_required_documents(self, paths):
        """Sets the five required documents (see set_required_documents) and
        clicks 'Upload Documents'."""
        self.set_required_documents(paths)
        self.click_upload_documents()
