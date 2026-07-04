import allure

from pages.base_page import BasePage
from config import FORMS_BASE


class LicenseRenewalPage(BasePage):
    """Part-D: Renewal Details page (Licence Renewal Application)."""

    # ── Breadcrumb ────────────────────────────────────────────────────────────

    @property
    def breadcrumb_home_link(self):
        return self.page.locator("//div[contains(@class,'max-w-6xl')]//a[text()='Home']").first

    @property
    def breadcrumb_dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']").first

    @property
    def breadcrumb_current_step(self):
        return self.page.locator("//span[contains(text(),'Renewal Details')]").first

    # ── Renewal Banner ────────────────────────────────────────────────────────

    @property
    def renewal_banner(self):
        return self.page.locator(".renewal-banner")

    @property
    def renewal_banner_title(self):
        return self.page.locator(".renewal-banner-title")

    @property
    def renewal_banner_subtitle(self):
        return self.page.locator(".renewal-banner-sub")

    @property
    def renewal_only_badge(self):
        return self.page.locator(".renewal-badge")

    # ── Alerts ────────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".alert-renewal.success")

    @property
    def error_alert(self):
        return self.page.locator(".alert-renewal.error")

    # ── Saved Summary Box ─────────────────────────────────────────────────────

    @property
    def summary_box(self):
        return self.page.locator(".summary-box")

    @property
    def summary_box_title(self):
        return self.page.locator(".summary-box-title")

    def summary_value(self, key: str):
        """Returns the value cell for a summary row, e.g. 'Existing Registration Number',
        'Date of Expiry', 'Suspension / Cancellation in Past',
        'Suspension / Cancellation Details'."""
        return self.page.locator(
            f"//span[@class='summary-key' and contains(text(),'{key}')]"
            f"/following-sibling::span[@class='summary-val']"
        )

    @property
    def summary_registration_number(self):
        return self.summary_value("Existing Registration Number")

    @property
    def summary_expiry_date(self):
        return self.summary_value("Date of Expiry")

    @property
    def summary_expiry_chip(self):
        # e.g. "203 days left" / "Expired 12d ago"
        return self.page.locator("#expiryChip")

    @property
    def summary_suspension_flag(self):
        return self.summary_value("Suspension / Cancellation in Past")

    @property
    def summary_suspension_details(self):
        return self.summary_value("Suspension / Cancellation Details")

    # ── Form Card Header ──────────────────────────────────────────────────────

    @property
    def card_header_title(self):
        return self.page.locator(".card-header-title")

    @property
    def card_header_subtitle(self):
        return self.page.locator(".card-header-sub")

    # ── Field 1: Existing Registration Number ─────────────────────────────────

    @property
    def registration_number_input(self):
        return self.page.locator("#regNumber")

    @property
    def registration_number_label(self):
        return self.page.locator("//div[contains(text(),'Existing Registration Number')]").first

    @property
    def registration_number_helper_note(self):
        return self.page.locator("//input[@id='regNumber']/following-sibling::div[contains(@class,'helper-note')]")

    # ── Field 2: Date of Expiry ───────────────────────────────────────────────

    @property
    def expiry_date_input(self):
        return self.page.locator("#expiryDate")

    @property
    def expiry_date_label(self):
        return self.page.locator("//div[contains(text(),'Date of Expiry of Registration')]").first

    @property
    def expiry_status_text(self):
        # e.g. "✓ Valid — 203 days remaining" / "⚠ Registration has already expired (12 days ago)"
        return self.page.locator("#expiryStatus")

    # ── Field 3: Suspension / Cancellation ────────────────────────────────────

    @property
    def suspension_label(self):
        return self.page.locator("//div[contains(text(),'Whether any suspension / cancellation')]").first

    @property
    def suspension_yes_radio(self):
        return self.page.locator("#suspYes")

    @property
    def suspension_no_radio(self):
        return self.page.locator("#suspNo")

    @property
    def suspension_yes_card(self):
        return self.page.locator("#cardYes")

    @property
    def suspension_no_card(self):
        return self.page.locator("#cardNo")

    @property
    def suspension_details_block(self):
        return self.page.locator("#suspDetailsBlock")

    @property
    def suspension_details_textarea(self):
        return self.page.locator("#suspDetails")

    @property
    def suspension_char_count(self):
        # e.g. "1000 / 1000 characters"
        return self.page.locator("#charCount")

    @property
    def no_suspension_note(self):
        return self.page.locator("#noSuspNote")

    # ── Action Bar ────────────────────────────────────────────────────────────

    @property
    def back_to_step3_link(self):
        return self.page.locator(".btn-back")

    @property
    def save_button(self):
        # "💾 Save Part D" / "💾 Update Part D"
        return self.page.locator("#saveBtn")

    @property
    def submit_and_finish_link(self):
        return self.page.locator(".btn-next")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Part-D Renewal Details page directly")
    def open(self):
        self.navigate(f"{FORMS_BASE}/partD.php")

    @allure.step("Fill Existing Registration Number: {registration_number}")
    def fill_registration_number(self, registration_number: str):
        self.registration_number_input.fill(registration_number)
        self.registration_number_input.blur()

    @allure.step("Fill Date of Expiry: {expiry_date}")
    def fill_expiry_date(self, expiry_date: str):
        """expiry_date in yyyy-mm-dd format, e.g. '2026-12-31'."""
        self.expiry_date_input.fill(expiry_date)
        self.expiry_date_input.blur()

    @allure.step("Select suspension / cancellation in the past: Yes")
    def select_suspension_yes(self):
        self.suspension_yes_radio.check()

    @allure.step("Select suspension / cancellation in the past: No")
    def select_suspension_no(self):
        self.suspension_no_radio.check()

    @allure.step("Fill suspension / cancellation details")
    def fill_suspension_details(self, details: str):
        self.suspension_details_textarea.fill(details)
        self.suspension_details_textarea.blur()

    @allure.step("Click 'Save Part D'")
    def click_save(self):
        self.save_button.click()

    @allure.step("Click 'Save Part D' and handle alert")
    def click_save_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.save_button, action=action)

    @allure.step("Click 'Submit & Finish'")
    def click_submit_and_finish(self):
        self.submit_and_finish_link.click()

    @allure.step("Click '← Step 3'")
    def click_back_to_step3(self):
        self.back_to_step3_link.click()

    @allure.step("Click 'Dashboard' breadcrumb")
    def click_breadcrumb_dashboard(self):
        self.breadcrumb_dashboard_link.click()

    @allure.step("Fill the complete Part-D renewal form")
    def fill_renewal_form(self, registration_number: str, expiry_date: str,
                          has_suspension: bool = False, suspension_details: str = ""):
        """Fills all Part-D fields. suspension_details is only entered when
        has_suspension is True (the textarea is hidden otherwise)."""
        self.fill_registration_number(registration_number)
        self.fill_expiry_date(expiry_date)
        if has_suspension:
            self.select_suspension_yes()
            self.fill_suspension_details(suspension_details)
        else:
            self.select_suspension_no()
