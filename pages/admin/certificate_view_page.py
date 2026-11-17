import re

import allure

from pages.base_page import BasePage


class AdminCertificatePage(BasePage):
    """Admin copy of the Form-II certificate (opened from Approved agencies → "📜 Cert", in a new tab). The page
    is headed "ADMIN VIEW — Agency #N" and carries the same certificate as the agency's copy, with a status banner
    (``.info-banner``, class ok / warn), two tick-box sections (business classification first, then area of
    operation), the Print and Download PDF buttons (``.tbtn``) and the top bar and ID strip, which are not printed.
    """

    @property
    def top_bar(self):
        return self.page.locator(".top-bar")

    @property
    def id_strip(self):
        return self.page.locator(".id-strip")

    @property
    def print_buttons(self):
        return self.page.locator(".tbtn", has_text="Print")

    @property
    def banner(self):
        return self.page.locator(".info-banner")

    @property
    def classification_rows(self):
        return self.page.locator(".chk-section").nth(0).locator(".chk-row")

    @property
    def area_rows(self):
        return self.page.locator(".chk-section").nth(1).locator(".chk-row")

    @allure.step("Read the certificate text")
    def body_text(self) -> str:
        # text_content, not inner_text: the page's CSS uppercases some labels ("CERT. NO.") and inner_text follows it
        return self.page.text_content("body") or ""

    def ticked_labels(self, rows) -> list[str]:
        """The labels of the rows whose box carries a tick (✓), in page order."""
        ticked = rows.filter(has=self.page.locator(".chk-box", has_text="✓")).all_inner_texts()
        return [re.sub(r"^✓\s*", "", t).strip() for t in ticked]
