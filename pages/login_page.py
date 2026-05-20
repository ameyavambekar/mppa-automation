import allure

from .base_page import BasePage

class LoginPage(BasePage):

    @property
    def login_title(self):
        return self.page.locator("//h2[contains(text(),'Login')]")

    @property
    def login_subtitle(self):
        return self.page.locator("//h2[text()='Agency Login']//following-sibling::p")

    @property
    def instructions_text(self):
        return self.page.locator("//p[text()='Important Instructions']//following-sibling::ul")

    @property
    def security_notice_text(self):
        return self.page.locator("//p[contains(text(),'Security Notice')]//following-sibling::p")

    # Locators as properties
    @property
    def username_input(self):
        return self.page.locator("input[name='username']")

    @property
    def username_mandatory_sign(self):
        return self.page.locator("//input[@name='username']//preceding-sibling::label//following-sibling::span")


    @property
    def password_input(self):
        return self.page.locator("input[name='password']")

    @property
    def password_show_toggle(self):
        return self.page.locator("//input[@id='loginPassword']//following-sibling::button")

    @property
    def password_mandatory_sign(self):
        return self.page.locator("//input[@id='loginPassword']//parent::div//preceding-sibling::label//following-sibling::span")

    @property
    def captcha_value(self):
        return self.page.locator("#captcha")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def captcha_mandatory_sign(self):
        return self.page.locator("//div[@id='captcha']//parent::div//preceding-sibling::label//following-sibling::span")

    @property
    def captcha_refresh_button(self):
        return self.page.locator("//div[@id='captcha']//following-sibling::button")

    @property
    def login_button(self):
        return self.page.locator("button[type='submit']")

    @property
    def error_message(self):
        return self.page.locator("div[class*='alert-error']")

    @property
    def admin_login_link(self):
        return self.page.locator("//a[contains(text(),'Admin Login')]")

    @property
    def agency_registration_link(self):
        return self.page.locator("//a[contains(text(),'New Agency? Register here')]")

    @property
    def forgot_password_link(self):
        return self.page.locator("//a[contains(text(),'Forgot Password')]")

    @property
    def account_locked_message(self):
        return self.page.locator("div[class*='alert']").filter(has_text="failed")


    # Actions
    def open(self):
        self.navigate("https://devmppa.sppuef.in/module/agency/auth/login.php")

    @allure.step("Fill username: {username}")
    def fill_username(self, username: str):
        self.username_input.fill(username)
        self.username_input.blur()  # trigger on-blur validation (EC-9)

    @allure.step("Fill password")
    def fill_password(self, password: str):
        self.password_input.fill(password)
        self.password_input.blur()

    @allure.step("Toggle password visibility (SHOW / HIDE)")
    def toggle_password_visibility(self):
        self.password_show_toggle.click()

    @allure.step("Read current CAPTCHA text from DOM")
    def read_captcha_value(self) -> str:
        return self.captcha_value.text_content().strip()

    @allure.step("Fill CAPTCHA from DOM value")
    def fill_captcha(self, captcha_text: str):
        """Reads the visible CAPTCHA text directly from the DOM element."""
        self.captcha_input.fill(captcha_text)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self):
        """Clicks Refresh and returns the new CAPTCHA value."""
        self.captcha_refresh_button.click()
        return self.captcha_value.text_content().strip()
    
    # Composite Actions
    @allure.step("Login as {username}")
    def login(self, username: str, password: str):
        self.fill_username(username)
        self.fill_password(password)
        captcha = self.read_captcha_value()
        self.fill_captcha(captcha)
        self.login_button.click()

    @allure.step("Click login button and handle alert")
    def click_login_and_handle_alert(self) -> str:
        """
        Clicks Login, handles any alert/confirm/prompt dialog,
        and returns the dialog message for assertions.
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        self.login_button.click()
        self.page.remove_listener("dialog", handle_dialog)  # clean up
        return dialog_message[0] if dialog_message else ""

