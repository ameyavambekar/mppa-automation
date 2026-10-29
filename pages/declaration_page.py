import base64
import mimetypes
import os

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

DECLARATION_URL = f"{FORMS_BASE}/declaration.php"
PREVIEW_URL = f"{FORMS_BASE}/preview.php"
# Where preview.php sends the user while the signed forms are missing.
PREVIEW_LOCKED_URL = f"{DECLARATION_URL}?error=complete_declaration_first"


class DeclarationPage(BasePage):
    """Page object for the Declaration & Authorisation step (forms/declaration.php, progress node "Declaration").

    Two cards, keyed ``"ia"`` (FORM-I(A) — Self-Declaration) and ``"ib"`` (FORM-I(B) —
    Letter of Authorization). Each has a PENDING badge, the form text in an open
    ``<details>``, a "Download Pre-filled FORM-I(…)" link (a PDF, opened in a new tab)
    and an upload zone that takes a click or a drag & drop.

    Choosing a file is checked in the browser straight away (PDF only, at most 2 MB);
    the zone's two lines then show the result. Nothing is uploaded until
    "Upload & Continue", which submits both zones in one form and alerts when
    neither has a file.
    """

    # key → (card title, rule, read-text summary, download label, upload input id)
    FORMS = {
        "ia": ("FORM-I(A) — Self-Declaration", "see rule 3 (3)", "Read the declaration text",
               "Download Pre-filled FORM-I(A)", "declPdf"),
        "ib": ("FORM-I(B) — Letter of Authorization", "see rule 3 (1)", "Read the authorisation text",
               "Download Pre-filled FORM-I(B)", "authPdf"),
    }
    MAX_BYTES = 2 * 1024 * 1024

    # Page texts
    TITLE = "Step 6 — Declaration & Authorisation"
    SUBTITLE = "Two signed forms are required before you can go to the Preview and Payment."
    BACK_LABEL = "← Step 5"
    STEP_TILES = (
        ("1. Download", "Pre-filled FORM-I(A) and FORM-I(B)"),
        ("2. Print", "On your agency's official letterhead"),
        ("3. Sign & stamp", "By the authorised signatory"),
        ("4. Scan & upload", "As a PDF, max 2 MB each"),
    )
    NOTE = ("Note: Upload the scanned copy of the signed form as a PDF only. Each file must be 2 MB or smaller. "
            "JPG / PNG photos and files above 2 MB will not be accepted.")
    TIP = ("Tip: scan in black & white or grayscale at 150–200 DPI to keep the PDF small and clear. If the file is too "
           "big, use any free \"compress PDF\" tool before uploading.")
    PROGRESS_LABEL = "Signed forms uploaded"
    BADGE_PENDING = "PENDING"
    ZONE_HINT = "Scanned PDF only · Max 2 MB"
    SUBMIT_LABEL = "Upload & Continue"
    UPLOADING_LABEL = "Uploading…"
    # Client-side texts
    NOT_PDF_ERROR = "Only scanned PDF files are allowed."
    NOTHING_CHOSEN_ALERT = "Please choose the signed PDF file(s) to upload."

    # Opening words of each form's text on the page
    IA_TEXT_START = ("I, [Name], in my capacity as the [Designation] of [Private Placement Agency Name], do hereby "
                     "solemnly affirm")
    IA_TEXT_SECOND = "I understand that if the information given by me is proved false"
    IB_TEXT_START = "I/We hereby authorize Smt/Shri ________ with designation _______ holding Aadhaar Number ________"

    @staticmethod
    def counter_text(uploaded: int) -> str:
        return f"{uploaded} / 2"

    @staticmethod
    def zone_label(key: str) -> str:
        """The upload zone's first line before a file is chosen (the trailing '*' marks it required)."""
        return f"Upload signed FORM-I({key[1:].upper()}) — click or drag & drop *"

    @staticmethod
    def chosen_text(path: str) -> str:
        """First line of a zone once ``path`` is accepted or rejected — '✓ <name>' / '✗ <name>' (prefix added by the test)."""
        return os.path.basename(path)

    @staticmethod
    def ready_text(path: str) -> str:
        """'<N> KB — ready to upload' as the page rounds it (JavaScript toFixed(0))."""
        return f"{int(os.path.getsize(path) / 1024 + 0.5)} KB — ready to upload"

    @staticmethod
    def too_large_error(path: str) -> str:
        """'File is <N.NN> MB — maximum is 2 MB. Please compress it.'"""
        return f"File is {os.path.getsize(path) / 1048576:.2f} MB — maximum is 2 MB. Please compress it."

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator(".dc-head h2")

    @property
    def sub_title(self):
        return self.page.locator(".dc-head p")

    @property
    def back_link(self):
        """'← Step 5' — goes to the Documents step (enclosures.php)."""
        return self.page.locator("a.dc-back")

    @property
    def deadline_banner(self):
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        return self.page.get_by_role("link", name="Save & Log out")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` while that step is not yet saved (non-clickable)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def step_tiles(self):
        """The four 'how it works' tiles: <b> title, <span> hint."""
        return self.page.locator(".dc-step")

    @property
    def note(self):
        """The PDF / 2 MB note; its tip is in ``tip``."""
        return self.page.locator(".dc-note .t")

    @property
    def tip(self):
        return self.note.locator("small")

    @property
    def progress_card(self):
        return self.page.locator(".dc-prog")

    @property
    def counter(self):
        """'<n> / 2' in the 'Signed forms uploaded' card."""
        return self.progress_card.locator(".row span").nth(1)

    # ── Form cards ────────────────────────────────────────────────────────────

    def card(self, key: str):
        return self.page.locator(".dc-card").nth(list(self.FORMS).index(key))

    def card_title(self, key: str):
        return self.card(key).locator(".dc-card-h .tt")

    def card_rule(self, key: str):
        return self.card(key).locator(".dc-card-h .sub")

    def badge(self, key: str):
        return self.card(key).locator(".dc-pill")

    def read_section(self, key: str):
        """The <details> holding the form text — has the ``open`` attribute while expanded."""
        return self.card(key).locator("details.dc-read")

    def read_toggle(self, key: str):
        return self.read_section(key).locator("summary")

    def form_text(self, key: str):
        return self.read_section(key).locator(".dc-text")

    def download_link(self, key: str):
        return self.card(key).locator("a.dc-dl")

    def upload_zone(self, key: str):
        """The drop zone; has the class ``has`` once a valid file is chosen, ``bad`` after a rejected one."""
        return self.card(key).locator("label.dc-drop")

    def zone_line1(self, key: str):
        """'Upload signed FORM-I(…) — click or drag & drop *', then '✓ <file>' or '✗ <file>'."""
        return self.upload_zone(key).locator(".l1")

    def zone_line2(self, key: str):
        """'Scanned PDF only · Max 2 MB', then '<N> KB — ready to upload' or the error."""
        return self.upload_zone(key).locator(".l2")

    def file_input(self, key: str):
        return self.page.locator(f"#{self.FORMS[key][4]}")

    @property
    def submit_button(self):
        """'Upload & Continue' — disabled and reads 'Uploading…' while the form is sent."""
        return self.page.locator("button.dc-submit")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Declaration step")
    def open(self):
        """Navigates to Declaration (requires a logged-in agency session with Premises Photos completed)."""
        self.navigate(DECLARATION_URL)

    @allure.step("FORM-I({key}): choose {path}")
    def choose_file(self, key: str, path: str):
        """Picks a file with the zone's file chooser; nothing is uploaded until 'Upload & Continue'."""
        self.file_input(key).set_input_files(path)

    @allure.step("FORM-I({key}): drag & drop {path}")
    def drop_file(self, key: str, path: str):
        """Drops ``path`` onto the upload zone, as dragging it from the desktop does."""
        with open(path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        data_transfer = self.page.evaluate_handle(
            """([name, b64, type]) => {
                const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
                const dt = new DataTransfer();
                dt.items.add(new File([bytes], name, { type }));
                return dt;
            }""",
            [os.path.basename(path), content, mime],
        )
        self.upload_zone(key).dispatch_event("drop", {"dataTransfer": data_transfer})

    @allure.step("Toggle the FORM-I({key}) text")
    def toggle_text(self, key: str):
        self.read_toggle(key).click()

    @allure.step("Click 'Download Pre-filled FORM-I({key})'")
    def download_form(self, key: str):
        """Clicks the download link and returns the Playwright Download (the PDF is sent as an
        attachment, so no new tab stays open)."""
        with self.page.expect_download() as download_info:
            self.download_link(key).click()
        return download_info.value

    @allure.step("Click 'Upload & Continue' and handle the alert")
    def submit_and_handle_alert(self) -> str:
        """Clicks 'Upload & Continue'; returns the alert's message, or '' when none appeared."""
        return self.click_and_handle_alert(self.submit_button)

    @allure.step("Click '← Step 5'")
    def click_back(self):
        self.back_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
