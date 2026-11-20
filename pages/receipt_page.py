import re

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

RECEIPT_URL = f"{FORMS_BASE}/receipt.php"


class ReceiptPage(BasePage):
    """Page object for the payment receipt (forms/receipt.php), opened by "Print Receipt"
    on the payment success page. Page title "Payment Receipt — <Application ID>"; a
    table of label / value rows (see ``LABELS``) and a "Print Receipt" button
    (``window.print()``). On dev the bank is "Dev Test Bank (bypass — not a real payment)".

    Only a logged-in agency whose application is paid gets the receipt. Logged out it redirects to
    login.php?reason=not_logged_in; an unpaid agency is sent there too and logged out (defect
    "Step 8 — Fees & Payment" #21, 20-Nov-2026). No page links to it after payment (#20).
    """

    TITLE = "MPPA Portal — Payment Receipt"
    SUBTITLE = "Maharashtra Private Placement Agencies Registration Portal"
    CONFIRMED = "Payment Confirmed"
    LABELS = ("Application ID", "Agency Name", "Jurisdiction", "Amount Paid", "Transaction / DD No.", "Bank Name",
              "Branch Name", "Receipt Generated")
    DEV_BANK = "Dev Test Bank (bypass — not a real payment)"
    DEV_BRANCH = "Dev Test Branch"
    # 'DEV-F3EE20FFA56F' on dev (20-Nov-2026)
    DEV_TRANSACTION = re.compile(r"^DEV-[0-9A-F]{12}$")
    # '20 Nov 2026, 04:01 PM' — the time the receipt is opened, in Indian time (20-Nov-2026)
    GENERATED_FORMAT = "%d %b %Y, %I:%M %p"
    FOOTER = ("This is a system-generated receipt for the registration/renewal fee paid on the MPPA Portal.\n"
              "Please retain this receipt for your records and future correspondence.")
    PRINT_LABEL = "Print Receipt"

    @staticmethod
    def page_title(application_id: str) -> str:
        return f"Payment Receipt — {application_id}"

    @staticmethod
    def amount_text(amount: int) -> str:
        """'₹ 2,000.00'."""
        return f"₹ {amount:,.2f}"

    @property
    def title(self):
        return self.page.locator("h1")

    @property
    def subtitle(self):
        return self.page.locator(".receipt-head p")

    @property
    def confirmed_badge(self):
        """'Payment Confirmed'."""
        return self.page.locator(".receipt-badge")

    @property
    def labels(self):
        """The row labels (``td.label``), in page order."""
        return self.page.locator("td.label")

    def value(self, label: str):
        return self.page.locator(f"//tr[td[1][normalize-space()='{label}']]/td[2]")

    @property
    def footer_note(self):
        return self.page.locator(".footer-note")

    @property
    def print_button(self):
        return self.page.get_by_role("button", name=self.PRINT_LABEL)

    @allure.step("Click 'Print Receipt'")
    def click_print(self):
        """Calls ``window.print()`` — the browser's print dialog."""
        self.print_button.click()

    @allure.step("Open the payment receipt")
    def open(self):
        """Navigates to the receipt (requires a logged-in agency session whose application is paid)."""
        self.navigate(RECEIPT_URL)
