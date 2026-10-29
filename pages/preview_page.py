import allure

from pages.base_page import BasePage
from pages.declaration_page import PREVIEW_URL


class PreviewPage(BasePage):
    """Page object for the Application Preview step (forms/preview.php, progress node "Preview").

    A read-only summary in seven ``.prev-section`` blocks, each headed by a
    ``.prev-title`` (see ``SECTIONS``). Every section but Registration Details has an
    "Edit" link to its step; Registration Details carries a "Locked — cannot be
    changed" badge instead. Values are ``.prev-row`` label / value pairs; Part B adds
    one ``.person-card`` per key person, Enclosures one ``.enc-card`` per document.
    Uploaded files open through ``a.file-link`` in a new tab.

    Below the sections, a fee box and the "Confirm & Proceed to Payment — ₹ <amount>"
    button, which posts ``#payForm`` (draft token + fee amount) to payment_init.php.
    The page is only reachable once both signed declaration forms are uploaded —
    until then preview.php redirects to Declaration.
    """

    TITLE = "Step 7 — Application Preview"
    SUBTITLE = "Review all details carefully. After payment, your Application ID will be generated."
    BACK_LABEL = "← Declaration"
    INTRO = ("Review all information below before proceeding to payment. Use the Edit links to correct any mistakes. "
             "Once payment is made, the application cannot be edited.")
    LOCKED_BADGE = "Locked — cannot be changed"
    EDIT_LABEL = "Edit"

    REGISTRATION = "Registration Details"
    PART_A = "Part A — Agency Details"
    PART_B = "Part B — Key Persons"
    PART_C = "Part C — Operations"
    PART_F = "Part F — Certificates"
    ENCLOSURES = "Enclosures"
    DECLARATION = "Declaration & Authorisation"
    SECTIONS = (REGISTRATION, PART_A, PART_B, PART_C, PART_F, ENCLOSURES, DECLARATION)
    # Section → the page its "Edit" link opens
    EDIT_TARGETS = {PART_A: "partA.php", PART_B: "partB.php", PART_C: "partC.php", PART_F: "partF.php",
                    ENCLOSURES: "enclosures.php", DECLARATION: "declaration.php"}

    # Row labels, in page order
    REGISTRATION_LABELS = ("Agency Name", "Username", "Email", "PAN Number", "GSTIN", "Mobile", "Alt. Phone", "PAN File")
    PART_A_LABELS = ("Agency Type", "Date of Estab.", "Incorporation No.", "TAN", "GSTIN", "Address Line 1",
                     "Address Line 2", "City / Village", "Taluka", "District", "State", "Pincode", "Office in MH",
                     "Auth. Signatory", "Designation", "Aadhaar (Signatory)", "Google Maps")
    PERSON_LABELS = ("PAN", "Aadhaar", "Nationality", "Mobile", "Address", "DIN/DPIN")
    PART_C_LABELS = ("Placement Type", "Sectors", "Digital Platform", "Training", "Mobilization", "Service Mode",
                     "Type of Agency", "Charges displayed")
    # Part F certificate rows: (number label, date label) → Part F certificate key (see PartFPage.CERTIFICATES)
    CERTIFICATE_ROWS = {("Contract Labour Cert", "Contract Labour Date"): "cl",
                        ("Emigration Cert", "Emigration Date"): "em",
                        ("Security Licence", "Security Date"): "sec",
                        ("LIN Number", "LIN Date"): "lin"}
    PART_F_LABELS = (*(label for pair in CERTIFICATE_ROWS for label in pair), "Application Date", "Place")
    ENCLOSURE_TITLES = ("PAN Card of the Agency", "Office Address Proof", "Office / Premises Photograph",
                        "Authorised Signatory — Signature & PAN in Letterhead", "Address Proof of Key Persons",
                        "Specimen Signature of Authorised Signatory")
    SIGNED_FORM_LABELS = ("Self-Declaration", "Authorisation")
    EMPTY = "—"
    ACCEPTED = "Accepted"
    VIEW_LABEL = "View"
    VIEW_PAN_LABEL = "View PAN"
    VIEW_SIGNED_LABEL = "View signed PDF"
    FEE_LABEL = "Registration Fee"
    APPLICATION_ID_NOTE = "Your Application ID will be generated after payment"
    PAYMENT_NOTE = "Secure payment via MAHARASHTRA E-CHALLAN / Payment Gateway · Fee is non-refundable once paid"
    PAYMENT_ACTION = "payment_init.php"

    @staticmethod
    def fee_text(amount: int) -> str:
        """'₹ 2,000' — the amount as the page prints it."""
        return f"₹ {amount:,}"

    @staticmethod
    def pay_label(amount: int) -> str:
        return f"Confirm & Proceed to Payment — {PreviewPage.fee_text(amount)}"

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("h2")

    @property
    def sub_title(self):
        return self.page.locator("h2 + p")

    @property
    def back_link(self):
        """'← Declaration' — goes to the Declaration step (declaration.php)."""
        return self.page.get_by_role("link", name=self.BACK_LABEL)

    @property
    def intro(self):
        """The amber 'Review all information below…' box."""
        return self.page.locator("//div[strong[starts-with(normalize-space(),'Review all information below')]]")

    @property
    def deadline_banner(self):
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        return self.page.get_by_role("link", name="Save & Log out")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` while that step is not yet complete (non-clickable)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a completed step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    # ── Sections ──────────────────────────────────────────────────────────────

    @property
    def section_titles(self):
        """Every section's ``.prev-title`` (its text includes the Edit link / Locked badge)."""
        return self.page.locator(".prev-title")

    def section(self, title: str):
        return self.page.locator(".prev-section").filter(
            has=self.page.locator(".prev-title", has_text=title))

    def locked_badge(self, title: str):
        return self.section(title).locator(".prev-title span")

    def edit_link(self, title: str):
        return self.section(title).locator("a.edit-link")

    def rows(self, title: str):
        """The section's own label / value rows (Part B's person-card rows excluded)."""
        return self.section(title).locator(":scope > .prev-row")

    def row_labels(self, title: str):
        return self.rows(title).locator(".prev-label")

    def value(self, title: str, label: str):
        """The value cell of the row labelled exactly ``label`` in section ``title``."""
        return self.section(title).locator(
            f"xpath=./div[@class='prev-row'][span[@class='prev-label' and normalize-space()='{label}']]"
            "/span[@class='prev-val']")

    def file_links(self, title: str = None):
        """'View' / 'View PAN' / 'View signed PDF' links — of one section, or of the whole page."""
        return (self.section(title) if title else self.page).locator("a.file-link")

    # Part B
    @property
    def person_cards(self):
        return self.section(self.PART_B).locator(".person-card")

    def person_name(self, index: int):
        """'<n>. <Full name>'."""
        return self.person_cards.nth(index).locator(".person-name")

    def person_value(self, index: int, label: str):
        return self.person_cards.nth(index).locator(
            f"xpath=./div[@class='prev-row'][span[contains(@class,'prev-label') and normalize-space()='{label}']]"
            "/span[@class='prev-val']")

    # Enclosures
    @property
    def enclosure_cards(self):
        """One card per uploaded document; class ``ok`` and a '✓' mark once uploaded."""
        return self.section(self.ENCLOSURES).locator(".enc-card")

    def enclosure_card(self, title: str):
        return self.enclosure_cards.filter(has_text=title)

    def enclosure_mark(self, title: str):
        return self.enclosure_card(title).locator(".enc-num")

    # Declaration & Authorisation
    def signed_form_badge(self, label: str):
        return self.value(self.DECLARATION, label).locator(".badge-done")

    # ── Fee & payment ─────────────────────────────────────────────────────────

    @property
    def fee_box(self):
        return self.page.locator(".fee-box")

    @property
    def fee_amount(self):
        return self.fee_box.locator(".fee-amt")

    @property
    def fee_category(self):
        """'<category> — <scope> · Rule … · one-time, non-refundable'."""
        return self.fee_box.locator(".fee-amt + div")

    @property
    def application_id_note(self):
        return self.fee_box.locator(".fee-amt + div + div")

    @property
    def pay_form(self):
        """``POST payment_init.php`` with the hidden draft_token and fee_amount."""
        return self.page.locator("#payForm")

    @property
    def fee_amount_input(self):
        return self.pay_form.locator("input[name='fee_amount']")

    @property
    def pay_button(self):
        return self.page.locator("#payBtn")

    @property
    def payment_note(self):
        return self.page.locator("//p[contains(normalize-space(),'Secure payment via')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Preview step")
    def open(self):
        """Navigates to Preview (requires a logged-in agency session whose Declaration step is complete)."""
        self.navigate(PREVIEW_URL)

    @allure.step("Click 'Edit' on '{title}'")
    def click_edit(self, title: str):
        self.edit_link(title).click()

    @allure.step("Click 'Confirm & Proceed to Payment'")
    def confirm_and_pay(self):
        """Posts the payment form and waits for the page it leads to (on dev: the payment success page).
        This submits the application — the agency can no longer be used for the Form-I step tests."""
        with self.page.expect_navigation(timeout=60000):
            self.pay_button.click()

    @allure.step("Click '← Declaration'")
    def click_back(self):
        self.back_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
