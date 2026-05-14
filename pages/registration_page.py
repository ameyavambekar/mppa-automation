
import allure
from playwright.sync_api import expect

from pages.base_page import BasePage
from utils import email_otp

REGISTER_URL = "https://devmppa.sppuef.in/module/agency/auth/register.php"

class RegistrationPage(BasePage):

    # Locators as properties
    """ Section 1 — Login Credentials """
    @property
    def page_title(self):
        return self.page.locator("//h2[contains(text(),'Registration')]")

    @property
    def page_subtitle(self):
        return self.page.locator("//h2[contains(text(),'Registration')]//following-sibling::p")

    @property
    def mandatory_field_badge(self):
        return self.page.locator("//h2[contains(text(),'Registration')]//parent::div//following-sibling::div")

    @property
    def username_input(self):
        return self.page.locator("#username")

    @property
    def password_input(self):
        return self.page.locator("//input[@id='password']")

    @property
    def password_length_error(self):
        return self.page.locator("//span[@id='chk-len' and contains(@class,'err')]")

    @property
    def password_length_correct(self):
        return self.page.locator("//span[@id='chk-len' and contains(@class,'ok')]")

    @property
    def password_uppercase_error(self):
        return self.page.locator("//span[@id='chk-upper' and contains(@class,'err')]")

    @property
    def password_uppercase_correct(self):
        return self.page.locator("//span[@id='chk-upper' and contains(@class,'ok')]")

    @property
    def password_number_error(self):
        return self.page.locator("//span[@id='chk-num' and contains(@class,'err')]")

    @property
    def password_number_correct(self):
        return self.page.locator("//span[@id='chk-num' and contains(@class,'ok')]")

    @property
    def password_symbol_error(self):
        return self.page.locator("//span[@id='chk-sym' and contains(@class,'err')]")

    @property
    def password_symbol_correct(self):
        return self.page.locator("//span[@id='chk-sym' and contains(@class,'ok')]")

    @property
    def password_show_toggle(self):
        return self.page.locator("//input[@id='password']//following-sibling::button")

    @property
    def confirm_password_show_toggle(self):
        return self.page.locator("//input[@id='confirmPassword']//following-sibling::button")

    @property
    def confirm_password_input(self):
        return self.page.locator("//input[@id='confirmPassword']")


    '''Section 2 — Contact & Identity Verification'''
    @property
    def email_input(self):
        return self.page.locator("#email")

    @property
    def email_helper(self):
        return self.page.locator("#emailHint")

    @property
    def otp_button(self):
        return self.page.locator("#otpBtn")

    @property
    def otp_countdown_timer(self):
        return self.page.locator("//button[contains(text(),'Resend')]")

    @property
    def email_otp_input(self):
        return self.page.locator("#emailOTP")

    @property
    def verify_otp_button(self):
        return self.page.locator("#verifyOtpBtn")

    @property
    def email_verified_tag(self):
        return self.page.locator("#verifiedTag")

    @property
    def pan_input(self):
        return self.page.locator("#pan")

    @property
    def pan_helper(self):
        """TC-16 / TC-17 — Inline error shown below the PAN field."""
        return self.page.locator("#panHelper")

    @property
    def district_select(self):
        return self.page.locator("#districtId")


    # Section 3 — CAPTCHA
    @property
    def captcha_value(self):
        return self.page.locator("#captcha")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def captcha_hint(self):
        return self.page.locator("#captchaHint")

    @property
    def captcha_refresh_button(self):
        return self.page.locator("//button[contains(text(),'Refresh')]")

    # Section 4 — Declaration
    @property
    def declaration_text_block(self):
        return self.page.locator("//p[contains(text(),'Self-Declaration')]//following-sibling::ol")

    @property
    def declaration_checkbox(self):
        return self.page.locator("#declarationCheck")

    @property
    def declaration_error(self):
        return self.page.locator("#declErr")

    @property
    def submit_button(self):
        return self.page.locator("#submitBtn")

    # Footer
    @property
    def login_link(self):
        return self.page.locator("//a[contains(text(),'Already registered? Login')]")

    @property
    def support_footer(self):
        return self.page.locator("//p[contains(text(),'technical issues')]")

    # Error / confirmation elements
    @property
    def registration_success_message(self):
        """AC-6 — On-screen success message after successful submission."""
        return self.page.locator("//div[@id='successOverlay']//h3")

    @property
    def registration_id_text(self):
        """AC-6 — On-screen Registration ID after successful submission."""
        return self.page.locator("#dispRegId")

    @property
    def proceed_to_login(self):
        """AC-6 — On-screen success message after successful submission."""
        return self.page.locator("//div[@id='dispRegIdParsed']//following-sibling::a")

    @property
    def username_helper(self):
        return self.page.locator("#usernameHelper")

    @property
    def password_helper(self):
        return self.page.locator("#pwdHint")

    @property
    def confirm_password_helper(self):
        return self.page.locator("#confirmHint")



    @property
    def server_error(self):
        return self.page.locator("#serverError")

    # Actions

    @allure.step("Open Pre-Registration page")
    def open(self):
        self.navigate(REGISTER_URL)
        self.wait_for_load()

    # Section 1

    @allure.step("Fill username: {username}")
    def fill_username(self, username: str):
        self.username_input.fill(username)
        self.username_input.blur()   # trigger on-blur validation (EC-9)

    @allure.step("Fill password")
    def fill_password(self, password: str):
        self.password_input.fill(password)

    @allure.step("Clear password")
    def clear_password(self):
        self.password_input.clear()

    @allure.step("Fill password and blur to trigger validation")
    def fill_password_and_blur(self, password: str):
        """
        Fills the password field and immediately blurs it so that
        on-blur complexity errors are triggered (used by TC-07).
        """
        self.password_input.fill(password)
        self.password_input.blur()

    @allure.step("Fill confirm password")
    def fill_confirm_password(self, confirm_password: str):
        self.confirm_password_input.fill(confirm_password)

    @allure.step("Toggle show password")
    def toggle_password_visibility(self):
        self.password_show_toggle.click()

    @allure.step("Toggle show confirm password")
    def toggle_confirm_password_visibility(self):
        self.confirm_password_show_toggle.click()

    @allure.step("Fill confirm password and blur to trigger validation")
    def fill_confirm_password_and_blur(self, confirm_password: str):
        """
        Fills the confirm-password field and blurs it so on-blur
        mismatch errors are triggered (used by TC-08).
        """
        self.confirm_password_input.fill(confirm_password)
        self.confirm_password_input.blur()

    @allure.step("Fill Section 1 — Login Credentials")
    def fill_credentials(self, username: str, password: str, confirm_password: str = None):
        self.fill_username(username)
        self.fill_password(password)
        self.fill_confirm_password(confirm_password or password)

    @allure.step("Toggle password visibility (SHOW / HIDE)")
    def toggle_password_visibility(self):
        """
        TC-09 / EC-5 — Clicks the show/hide button on the Password field.
        First click reveals the password (type → text);
        second click re-masks it (type → password).
        """
        self.password_show_toggle.click()

    @allure.step("Toggle confirm password visibility (SHOW / HIDE)")
    def toggle_confirm_password_visibility(self):
        """
        TC-09 / EC-5 — Clicks the show/hide button on the Confirm Password field.
        """
        self.confirm_password_show_toggle.click()


    # Section 2

    @allure.step("Fill email and trigger OTP")
    def fill_email_and_request_otp(self, email: str):
        self.email_input.wait_for(state="visible")
        self.email_input.fill(email)
        self.email_input.blur()
        self.otp_button.click()


    @allure.step("Enter OTP and verify email")
    def enter_otp_and_verify_email(self):
        otp_code = email_otp.get_otp_from_testmail()
        self.email_otp_input.fill(otp_code)
        self.email_otp_input.blur()
        self.verify_otp_button.click()

    @allure.step("Submit incorrect otp and handle alert")
    def submit_otp_and_handle_alert(self) -> str:
        """
        Clicks Submit, handles any alert/confirm/prompt dialog,
        and returns the dialog message for assertions.
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        self.email_otp_input.fill("000000")
        self.verify_otp_button.click()
        self.page.remove_listener("dialog", handle_dialog)  # clean up
        return dialog_message[0] if dialog_message else ""

    @allure.step("Read PAN field value from DOM")
    def get_pan_value(self) -> str:
        """
        TC-15 — Returns the current value of the PAN input so tests can
        assert that lowercase input was auto-uppercased by the application.
        """
        return self.pan_input.input_value()

    @allure.step("Fill PAN: {pan}")
    def fill_pan(self, pan: str):
        self.pan_input.fill(pan)
        self.pan_input.blur()

    @allure.step("Select district: {district}")
    def select_district(self, district: str):
        if district:
            self.district_select.select_option(label=district)

    @allure.step("Attempt to submit with no district selected (blur dropdown)")
    def blur_district(self):
        """TC-18 — Triggers on-blur validation on the district dropdown."""
        self.district_select.focus()
        self.district_select.blur()

    @allure.step("Fill Section 2 — Contact & Identity")
    def fill_contact_identity(self, email: str, pan: str, district: str):
        self.fill_email_and_request_otp(email)
        self.enter_otp_and_verify_email()
        self.fill_pan(pan)
        self.select_district(district)

    # Section 3
    @allure.step("Read current CAPTCHA text from DOM")
    def read_captcha_value(self) -> str:
        """
        TC-19 / TC-21 — Returns the CAPTCHA string currently rendered in #captcha.
        Because the CAPTCHA is exposed as plain text in the DOM (not an image),
        we read it directly rather than using OCR.
        """
        return self.captcha_value.text_content().strip()

    @allure.step("Fill CAPTCHA from DOM value")
    def fill_captcha(self, captcha_text:str):
        """Reads the visible CAPTCHA text directly from the DOM element."""
        self.captcha_input.fill(captcha_text)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self):
        """EC-1 — Clicks Refresh and returns the new CAPTCHA value."""
        self.captcha_refresh_button.click()
        return self.captcha_value.text_content().strip()

    # Section 4

    @allure.step("Accept Declaration & Undertaking")
    def accept_declaration(self):
        self.declaration_checkbox.check()

    @allure.step("Submit Registration form")
    def submit(self):
        self.submit_button.click()

    @allure.step("Click Already Registered? Login-> link")
    def click_login_link(self):
        self.login_link.click()


    @allure.step("Submit form and handle alert")
    def submit_and_handle_alert(self, action: str = "accept", prompt_text: str = None) -> str:
        """
        Clicks Submit, handles any alert/confirm/prompt dialog,
        and returns the dialog message for assertions.
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            if action == "dismiss":
                dialog.dismiss()
            else:
                dialog.accept(prompt_text or "")

        self.page.on("dialog", handle_dialog)
        self.submit_button.click()
        self.page.remove_listener("dialog", handle_dialog)  # clean up

        return dialog_message[0] if dialog_message else ""

    # ── Composite action ──────────────────────────────────────────────────────

    def complete_registration(self, data):
        """
        Convenience method used by happy-path tests.
        Accepts an AgencyRegistrationData object.
        Does NOT click Submit — keeps that in the test for flexibility.
        """
        self.fill_credentials(data.username, data.password, data.confirm_password)
        self.fill_email_and_request_otp(data.email)
        self.enter_otp_and_verify_email()
        self.fill_pan(data.pan_number)
        self.select_district(data.district)
        self.fill_captcha()
        self.accept_declaration()


    duplicate_pan_error = "A registration with this PAN number already exists."
    district_not_selected_error = "Please select your district." #Alert Pop-up
    declaration_error_message = "You must accept the declaration to proceed."