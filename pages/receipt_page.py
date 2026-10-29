import allure

from config import FORMS_BASE
from pages.base_page import BasePage

RECEIPT_URL = f"{FORMS_BASE}/receipt.php"


class ReceiptPage(BasePage):
    """Page object for the payment receipt (forms/receipt.php), opened by "Print Receipt"
    on the payment success page. Page title "Payment Receipt — <Application ID>"; a
    table of label / value rows (see ``LABELS``) and a "Print Receipt" button
    (``window.print()``). On dev the bank is "Dev Test Bank (bypass — not a real payment)".
    """

    TITLE = "MPPA Portal — Payment Receipt"
    LABELS = ("Application ID", "Agency Name", "Jurisdiction", "Amount Paid", "Transaction / DD No.", "Bank Name",
              "Branch Name", "Receipt Generated")
    DEV_BANK = "Dev Test Bank (bypass — not a real payment)"
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

    def value(self, label: str):
        return self.page.locator(f"//tr[td[1][normalize-space()='{label}']]/td[2]")

    @property
    def print_button(self):
        return self.page.get_by_role("button", name=self.PRINT_LABEL)

    @allure.step("Open the payment receipt")
    def open(self):
        """Navigates to the receipt (requires a logged-in agency session whose application is paid)."""
        self.navigate(RECEIPT_URL)
