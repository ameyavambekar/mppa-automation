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

    @property
    def status_banner(self):
        return self.page.locator(".status-banner").first

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
