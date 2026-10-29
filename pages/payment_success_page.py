from config import FORMS_BASE
from pages.base_page import BasePage

PAYMENT_SUCCESS_URL = f"{FORMS_BASE}/payment_success.php"


class PaymentSuccessPage(BasePage):
    """Page object for the page Payment ends on (forms/payment_success.php).

    On the dev site no payment is taken: "Confirm & Proceed to Payment" on Preview
    posts to payment_init.php, which redirects straight here
    (``payment_success.php?dev_confirm=1``). The page shows the generated
    Application ID with a "Print Receipt" link (receipt.php, new tab) and
    "Go to Dashboard →". Once paid, the application is submitted and the
    Form-I step pages are no longer offered to the agency.
    """

    TITLE = "Payment Successful — Application Submitted!"
    MESSAGE = ("Your application has been submitted to the department for review. "
               "You will be notified by email once it is processed.")
    ID_LABEL = "Application ID"
    RECEIPT_LABEL = "Print Receipt"
    DASHBOARD_LABEL = "Go to Dashboard →"

    @property
    def title(self):
        return self.page.locator("h2")

    @property
    def message(self):
        return self.page.locator("h2 + p")

    @property
    def application_id_label(self):
        return self.page.locator(f"//div[normalize-space()='{self.ID_LABEL}']")

    @property
    def application_id(self):
        """The generated Application ID (13 digits)."""
        return self.application_id_label.locator("xpath=following-sibling::div[1]")

    @property
    def receipt_link(self):
        """'Print Receipt' — receipt.php in a new tab."""
        return self.page.get_by_role("link", name=self.RECEIPT_LABEL)

    @property
    def dashboard_link(self):
        return self.page.get_by_role("link", name=self.DASHBOARD_LABEL)
