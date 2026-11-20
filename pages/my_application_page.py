import re

import allure

from pages.base_page import BasePage
from pages.first_appeal_page import MY_APPLICATION_URL


class MyApplicationPage(BasePage):
    """Agency — My Application (/module/agency/forms/view_application.php): the submitted Form-I with a
    status banner at the top. Only the parts the appeal tests read are modelled here.

    For a refused application the banner (``.status-banner.rejected``) reads "Application Status:
    REJECTED … Review admin remarks below and file an appeal if needed.", shows the Admin Remarks (the
    reason in the refusal order) and a "File Appeal" link; the page's button row has another.
    """

    # Sections (``.vsec``), each headed "<n> <title> ✓ Completed" (dev, 20-Nov-2026)
    OPERATIONS = "Operational Details"
    FEES = "Fees & Payment"
    COMPLETED = "✓ Completed"
    FEE_LABELS = ("Jurisdiction", "Fee Amount", "Transaction Number", "Amount Paid", "Bank Name", "Branch Name",
                  "Submitted At")
    SUBMITTED_NOTE = "No changes can be made."

    @property
    def status_banner(self):
        return self.page.locator(".status-banner").first

    def section(self, title: str):
        return self.page.locator(".vsec").filter(has=self.page.locator(".sec-title", has_text=title))

    def section_badge(self, title: str):
        return self.section(title).locator(".sec-badge")

    def field_labels(self, title: str):
        return self.section(title).locator(".field-label")

    def field_value(self, title: str, label: str):
        """The value of the field labelled exactly ``label`` in section ``title``."""
        return self.section(title).locator(
            f"xpath=.//div[@class='field-item'][div[@class='field-label' and normalize-space()='{label}']]"
            "/div[contains(@class,'field-value')]")

    @property
    def form_fields(self):
        """Inputs, selects and text areas — none on the submitted application."""
        return self.page.locator("input:not([type='hidden']), select, textarea")

    @property
    def edit_links(self):
        return self.page.get_by_role("link", name="Edit", exact=True)

    @property
    def receipt_links(self):
        """Links to the payment receipt (receipt.php) — none on dev (20-Nov-2026)."""
        return self.page.locator("a[href*='receipt.php']")

    @property
    def admin_remarks(self):
        """'Admin Remarks: <the reason given in the refusal order>'."""
        return self.status_banner.locator("div").filter(has=self.page.locator("strong", has_text="Admin Remarks")).last

    @property
    def file_appeal_links(self):
        """Every 'File Appeal' link to FORM-III."""
        return self.page.locator("a[href$='appeals/first.php']")

    @allure.step("Open My Application")
    def open(self):
        self.navigate(MY_APPLICATION_URL)
        self.wait_for_load()

    def admin_remarks_text(self) -> str:
        """The refusal reason without the 'Admin Remarks:' label."""
        return self.admin_remarks.inner_text().split(":", 1)[-1].strip()

    def status(self) -> str:
        """The status word of the banner's "Application Status: <STATUS>" line — 'SUBMITTED', 'REJECTED',
        'APPROVED' … (dev, 06-Nov-2026)."""
        match = re.search(r"Application Status:\s*([A-Z_ ]+?)\s*(?:\n|$)", self.status_banner.inner_text())
        return match.group(1).strip() if match else ""
