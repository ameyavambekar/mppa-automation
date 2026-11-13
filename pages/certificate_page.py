import re

import allure

from config import AGENCY_BASE
from pages.base_page import BasePage

CERTIFICATE_URL = f"{AGENCY_BASE}/certificate.php"


class CertificatePage(BasePage):
    """Agency — Form-II registration certificate (module/agency/certificate.php), opened from Home's
    "View certificate". Carries a validity banner "✓ Valid certificate — expires <dd/mm/yyyy>"."""

    @staticmethod
    def validity_line(expires) -> str:
        """expires: a date — the banner writes it dd/mm/yyyy."""
        return f"Valid certificate — expires {expires:%d/%m/%Y}"

    @property
    def validity(self):
        return self.page.get_by_text(re.compile(r"(Valid|Expired) certificate"))

    @allure.step("Open the registration certificate")
    def open(self):
        self.navigate(CERTIFICATE_URL)
        self.wait_for_load()
