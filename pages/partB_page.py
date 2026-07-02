import allure

from pages.base_page import BasePage
from config import FORMS_BASE


class PartBPage(BasePage):
    """Step 2 — Key Persons (Part B).

    The page renders one ``.person-row`` block per key person (Director /
    Designated Partner / Proprietor), indexed from 0 (``#row0``, ``#row1`` …).
    All per-person locators therefore take a ``row`` index.

    Two variants exist depending on the agency's legal constitution:
    - Company / LLP: DIN/DPIN + PAN fields, address optional, no proof upload.
    - Other types:   no DIN/PAN, address textarea + address proof upload required.
    """

    # ── Page headings ─────────────────────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 2')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 2')]/following-sibling::p")

    @property
    def variant_badge(self):
        # e.g. "LLP" / "Company" / "Proprietorship"
        return self.page.locator(".badge-variant")

    @property
    def section_header(self):
        # e.g. "🏢 Part B(a) — Directors / Designated Partners"
        return self.page.locator(".section-header")

    @property
    def validation_legend(self):
        return self.page.locator("//span[contains(text(),'Mandatory field')]/parent::div")

    # ── Navigation ────────────────────────────────────────────────────────────

    @property
    def breadcrumb_dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")

    @property
    def back_to_step1_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Step 1')]").first

    @property
    def next_step3_link(self):
        # Top-right "Next: Step 3 →" shortcut
        return self.page.locator("//a[contains(normalize-space(.),'Next: Step 3')]")

    @property
    def proceed_to_step3_link(self):
        # Green button next to the submit button at the bottom of the form
        return self.page.locator("//a[contains(normalize-space(.),'Proceed to Step 3')]")

    # ── Person rows ───────────────────────────────────────────────────────────

    @property
    def person_rows(self):
        return self.page.locator(".person-row")

    def person_row(self, row: int):
        return self.page.locator(f"#row{row}")

    def person_row_number(self, row: int):
        return self.person_row(row).locator(".person-row-num")

    def remove_person_button(self, row: int):
        return self.person_row(row).locator(".remove-btn")

    @property
    def add_person_button(self):
        # "+ Add Another Director" / "+ Add Another Partner" etc.
        return self.page.locator("//button[contains(normalize-space(.),'Add Another')]")

    # ── Per-row fields ────────────────────────────────────────────────────────

    def full_name_input(self, row: int):
        return self.person_row(row).locator("input[name='p_name[]']")

    def din_input(self, row: int):
        return self.person_row(row).locator("input[name='p_din[]']")

    def pan_input(self, row: int):
        return self.person_row(row).locator("input[name='p_pan[]']")

    def aadhaar_input(self, row: int):
        return self.page.locator(f"#aadhaar{row}")

    def aadhaar_counter(self, row: int):
        # e.g. "12/12 digits ✓"
        return self.page.locator(f"#aadhaarCountText{row}")

    def nationality_select(self, row: int):
        return self.page.locator(f"#natSelect{row}")

    def passport_input(self, row: int):
        return self.page.locator(f"#passportField{row}")

    def passport_badge(self, row: int):
        # "Optional" / "★ Mandatory"
        return self.page.locator(f"#passportBadge{row}")

    def passport_hint(self, row: int):
        return self.page.locator(f"#passportHint{row}")

    def foreign_national_bar(self, row: int):
        # "🌍 Foreign national — Passport number is mandatory."
        return self.page.locator(f"#foreignBar{row}")

    def address_input(self, row: int):
        # Company/LLP variant: plain text input. Other variant: textarea (#addr{row}).
        return self.person_row(row).locator(
            "input[name='p_address[]'], textarea[name='p_address[]']"
        )

    def address_proof_input(self, row: int):
        # File upload — only present for the non-company variant
        return self.person_row(row).locator("input[type='file'][name='p_address_proof[]']")

    def email_input(self, row: int):
        return self.person_row(row).locator("input[name='p_email[]']")

    def country_code_select(self, row: int):
        return self.page.locator(f"#cc{row}")

    def mobile_input(self, row: int):
        return self.page.locator(f"#mob{row}")

    # ── Per-row inline validation messages ───────────────────────────────────

    def full_name_error(self, row: int):
        return self.full_name_input(row).locator("xpath=following-sibling::div[contains(@class,'field-error')]")

    def full_name_ok(self, row: int):
        return self.full_name_input(row).locator("xpath=following-sibling::div[contains(@class,'field-ok')]")

    def din_error(self, row: int):
        return self.page.locator(f"#dinErr{row}")

    def din_ok(self, row: int):
        return self.page.locator(f"#dinOk{row}")

    def pan_error(self, row: int):
        return self.page.locator(f"#panErr{row}")

    def pan_ok(self, row: int):
        return self.page.locator(f"#panOk{row}")

    def aadhaar_error(self, row: int):
        return self.page.locator(f"#aadhaarErr{row}")

    def aadhaar_ok(self, row: int):
        return self.page.locator(f"#aadhaarOk{row}")

    def passport_error(self, row: int):
        return self.page.locator(f"#passportErr{row}")

    def address_error(self, row: int):
        return self.page.locator(f"#addrErr{row}")

    def address_ok(self, row: int):
        return self.page.locator(f"#addrOk{row}")

    def address_proof_error(self, row: int):
        return self.page.locator(f"#fileErr{row}")

    def email_error(self, row: int):
        return self.page.locator(f"#emailErr{row}")

    def email_ok(self, row: int):
        return self.page.locator(f"#emailOk{row}")

    def mobile_error(self, row: int):
        return self.page.locator(f"#mobErr{row}")

    def mobile_ok(self, row: int):
        return self.page.locator(f"#mobOk{row}")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        # "💾 Save Part B" / "💾 Update Part B"
        return self.page.locator("button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Part-B Key Persons page directly")
    def open(self):
        self.navigate(f"{FORMS_BASE}/partB.php")

    @allure.step("Row {row}: Fill Full Name: {name}")
    def fill_full_name(self, row: int, name: str):
        self.full_name_input(row).fill(name)
        self.full_name_input(row).blur()

    @allure.step("Row {row}: Fill DIN / DPIN: {din}")
    def fill_din(self, row: int, din: str):
        self.din_input(row).fill(din)
        self.din_input(row).blur()

    @allure.step("Row {row}: Fill PAN: {pan}")
    def fill_pan(self, row: int, pan: str):
        self.pan_input(row).fill(pan)
        self.pan_input(row).blur()

    @allure.step("Row {row}: Fill Aadhaar: {aadhaar}")
    def fill_aadhaar(self, row: int, aadhaar: str):
        self.aadhaar_input(row).fill(aadhaar)
        self.aadhaar_input(row).blur()

    @allure.step("Row {row}: Select Nationality: {nationality}")
    def select_nationality(self, row: int, nationality: str):
        self.nationality_select(row).select_option(value=nationality)

    @allure.step("Row {row}: Fill Passport Number: {passport}")
    def fill_passport(self, row: int, passport: str):
        self.passport_input(row).fill(passport)
        self.passport_input(row).blur()

    @allure.step("Row {row}: Fill Residential Address")
    def fill_address(self, row: int, address: str):
        self.address_input(row).fill(address)
        self.address_input(row).blur()

    @allure.step("Row {row}: Set Address Proof: {path}")
    def set_address_proof(self, row: int, path: str):
        self.address_proof_input(row).set_input_files(path)

    @allure.step("Row {row}: Fill Email: {email}")
    def fill_email(self, row: int, email: str):
        self.email_input(row).fill(email)
        self.email_input(row).blur()

    @allure.step("Row {row}: Select Country Code: {code}")
    def select_country_code(self, row: int, code: str):
        self.country_code_select(row).select_option(value=code)

    @allure.step("Row {row}: Fill Mobile Number: {mobile}")
    def fill_mobile(self, row: int, mobile: str):
        self.mobile_input(row).fill(mobile)
        self.mobile_input(row).blur()

    @allure.step("Click '+ Add Another' person row")
    def click_add_person(self):
        self.add_person_button.click()

    @allure.step("Row {row}: Click '✕ Remove'")
    def click_remove_person(self, row: int):
        self.remove_person_button(row).click()

    @allure.step("Click Save / Update Part B")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click Save / Update Part B and handle alert")
    def click_submit_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.submit_button, action=action)

    @allure.step("Click 'Proceed to Step 3'")
    def click_proceed_to_step3(self):
        self.proceed_to_step3_link.click()

    @allure.step("Click '← Step 1'")
    def click_back_to_step1(self):
        self.back_to_step1_link.click()

    @allure.step("Row {row}: Fill complete key-person details")
    def fill_key_person(self, row: int, name: str, aadhaar: str, email: str, mobile: str,
                        din: str = None, pan: str = None, nationality: str = "Indian",
                        passport: str = None, address: str = None,
                        address_proof_path: str = None, country_code: str = "+91"):
        """Fills one person row end-to-end. DIN/PAN apply to the Company/LLP
        variant; address_proof_path applies to the non-company variant.
        Passport is only fillable for non-Indian nationalities (the field is
        disabled otherwise)."""
        self.fill_full_name(row, name)
        if din is not None:
            self.fill_din(row, din)
        if pan is not None:
            self.fill_pan(row, pan)
        self.fill_aadhaar(row, aadhaar)
        self.select_nationality(row, nationality)
        if passport is not None:
            self.fill_passport(row, passport)
        if address is not None:
            self.fill_address(row, address)
        if address_proof_path is not None:
            self.set_address_proof(row, address_proof_path)
        self.fill_email(row, email)
        if country_code != "+91":
            self.select_country_code(row, country_code)
        self.fill_mobile(row, mobile)
