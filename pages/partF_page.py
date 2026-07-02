import allure

from pages.base_page import BasePage
from config import FORMS_BASE


class PartFPage(BasePage):
    """Step 4 — Additional Information (Part F).

    Four optional certificate/licence blocks (number + date of issue + document
    upload each), followed by mandatory application details (date, place) and
    the authorised person's signature upload.
    """

    # ── Page headings ─────────────────────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 4')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 4')]/following-sibling::p")

    @property
    def certificate_section_header(self):
        return self.page.locator("//div[contains(@class,'section-header') and contains(text(),'Certificate')]")

    @property
    def signature_section_header(self):
        return self.page.locator("//div[contains(@class,'section-header') and contains(text(),'Signature')]")

    # ── Navigation ────────────────────────────────────────────────────────────

    @property
    def breadcrumb_dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")

    @property
    def back_to_step3_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Step 3')]").first

    @property
    def next_step5_link(self):
        # Top-right "Next: Step 5 →" shortcut (enclosures page)
        return self.page.locator("//a[contains(normalize-space(.),'Next: Step 5')]")

    # ── Contract Labour (R&A) Act Certificate ─────────────────────────────────

    @property
    def contract_labour_cert_input(self):
        return self.page.locator("input[name='contractLabourCert']")

    @property
    def contract_labour_date_input(self):
        return self.page.locator("input[name='contractLabourDate']")

    @property
    def contract_labour_file_input(self):
        return self.page.locator("input[name='f1']")

    # ── Emigration Clearance Certificate ──────────────────────────────────────

    @property
    def emigration_cert_input(self):
        return self.page.locator("input[name='emigrationCert']")

    @property
    def emigration_date_input(self):
        return self.page.locator("input[name='emigrationDate']")

    @property
    def emigration_file_input(self):
        return self.page.locator("input[name='f2']")

    # ── Security Agency Licence ───────────────────────────────────────────────

    @property
    def security_license_input(self):
        return self.page.locator("input[name='securityLicense']")

    @property
    def security_date_input(self):
        return self.page.locator("input[name='securityDate']")

    @property
    def security_file_input(self):
        return self.page.locator("input[name='f3']")

    # ── LIN (Labour Identification Number) ────────────────────────────────────

    @property
    def lin_number_input(self):
        return self.page.locator("input[name='linNumber']")

    @property
    def lin_date_input(self):
        return self.page.locator("input[name='linDate']")

    @property
    def lin_file_input(self):
        return self.page.locator("input[name='f4']")

    # ── Application Details & Signature ───────────────────────────────────────

    @property
    def application_date_input(self):
        return self.page.locator("input[name='applicationDate']")

    @property
    def place_input(self):
        return self.page.locator("input[name='place']")

    @property
    def signature_file_input(self):
        return self.page.locator("input[name='fsig']")

    @property
    def signature_uploaded_note(self):
        # "✅ Signature already uploaded" — shown only when a signature is on file
        return self.page.locator("//p[contains(text(),'Signature already uploaded')]")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        # "💾 Save Part F" / "💾 Update Part F"
        return self.page.locator("button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Part-F Additional Information page directly")
    def open(self):
        self.navigate(f"{FORMS_BASE}/partF.php")

    @allure.step("Fill Contract Labour Certificate No.: {number}")
    def fill_contract_labour_cert(self, number: str):
        self.contract_labour_cert_input.fill(number)
        self.contract_labour_cert_input.blur()

    @allure.step("Fill Contract Labour Date of Issue: {date}")
    def fill_contract_labour_date(self, date: str):
        """date in yyyy-mm-dd format."""
        self.contract_labour_date_input.fill(date)
        self.contract_labour_date_input.blur()

    @allure.step("Set Contract Labour document: {path}")
    def set_contract_labour_document(self, path: str):
        self.contract_labour_file_input.set_input_files(path)

    @allure.step("Fill Emigration Certificate No.: {number}")
    def fill_emigration_cert(self, number: str):
        self.emigration_cert_input.fill(number)
        self.emigration_cert_input.blur()

    @allure.step("Fill Emigration Date of Issue: {date}")
    def fill_emigration_date(self, date: str):
        """date in yyyy-mm-dd format."""
        self.emigration_date_input.fill(date)
        self.emigration_date_input.blur()

    @allure.step("Set Emigration document: {path}")
    def set_emigration_document(self, path: str):
        self.emigration_file_input.set_input_files(path)

    @allure.step("Fill Security Agency Licence No.: {number}")
    def fill_security_license(self, number: str):
        self.security_license_input.fill(number)
        self.security_license_input.blur()

    @allure.step("Fill Security Agency Licence Date of Issue: {date}")
    def fill_security_date(self, date: str):
        """date in yyyy-mm-dd format."""
        self.security_date_input.fill(date)
        self.security_date_input.blur()

    @allure.step("Set Security Agency Licence document: {path}")
    def set_security_document(self, path: str):
        self.security_file_input.set_input_files(path)

    @allure.step("Fill LIN Number: {number}")
    def fill_lin_number(self, number: str):
        self.lin_number_input.fill(number)
        self.lin_number_input.blur()

    @allure.step("Fill LIN Date of Issue: {date}")
    def fill_lin_date(self, date: str):
        """date in yyyy-mm-dd format."""
        self.lin_date_input.fill(date)
        self.lin_date_input.blur()

    @allure.step("Set LIN document: {path}")
    def set_lin_document(self, path: str):
        self.lin_file_input.set_input_files(path)

    @allure.step("Fill Date of Application: {date}")
    def fill_application_date(self, date: str):
        """date in yyyy-mm-dd format."""
        self.application_date_input.fill(date)
        self.application_date_input.blur()

    @allure.step("Fill Place: {place}")
    def fill_place(self, place: str):
        self.place_input.fill(place)
        self.place_input.blur()

    @allure.step("Set Signature: {path}")
    def set_signature(self, path: str):
        self.signature_file_input.set_input_files(path)

    @allure.step("Click Save Part F")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click Save Part F and handle alert")
    def click_submit_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.submit_button, action=action)

    @allure.step("Click '← Step 3'")
    def click_back_to_step3(self):
        self.back_to_step3_link.click()

    @allure.step("Click 'Next: Step 5'")
    def click_next_step5(self):
        self.next_step5_link.click()

    @allure.step("Fill a certificate block: {certificate}")
    def fill_certificate(self, certificate: str, number: str = None,
                         issue_date: str = None, document_path: str = None):
        """Fills one certificate block by key: 'contract_labour', 'emigration',
        'security' or 'lin'. Only the supplied values are touched — all
        certificate fields are optional."""
        fillers = {
            "contract_labour": (self.fill_contract_labour_cert,
                                self.fill_contract_labour_date,
                                self.set_contract_labour_document),
            "emigration": (self.fill_emigration_cert,
                           self.fill_emigration_date,
                           self.set_emigration_document),
            "security": (self.fill_security_license,
                         self.fill_security_date,
                         self.set_security_document),
            "lin": (self.fill_lin_number,
                    self.fill_lin_date,
                    self.set_lin_document),
        }
        fill_number, fill_date, set_document = fillers[certificate]
        if number is not None:
            fill_number(number)
        if issue_date is not None:
            fill_date(issue_date)
        if document_path is not None:
            set_document(document_path)

    @allure.step("Fill the complete Part-F form")
    def fill_part_f_form(self, application_date: str, place: str,
                         signature_path: str = None, certificates: dict = None):
        """Fills Part F end-to-end. certificates maps a certificate key
        ('contract_labour', 'emigration', 'security', 'lin') to a dict of
        kwargs for fill_certificate, e.g.::

            certificates={"lin": {"number": "LIN123", "issue_date": "2026-01-15",
                                  "document_path": files.valid_pdf}}
        """
        for certificate, details in (certificates or {}).items():
            self.fill_certificate(certificate, **details)
        self.fill_application_date(application_date)
        self.fill_place(place)
        if signature_path is not None:
            self.set_signature(signature_path)
