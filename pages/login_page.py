from .base_page import BasePage

class LoginPage(BasePage):

    @property
    def login_title(self):
        return self.page.locator("//h2[text()='Agency Login']")

    # Locators as properties
    @property
    def username_input(self):
        return self.page.locator("input[name='username']")

    @property
    def password_input(self):
        return self.page.locator("#loginPassword")

    @property
    def submit_button(self):
        return self.page.locator("button[type='submit']")

    @property
    def captcha_value(self):
        return self.page.locator("div[id*='captcha']")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def error_message(self):
        return self.page.locator("div[class*='alert-error']")



    # Actions
    def open(self):
        self.navigate("https://mppa.sppuef.in/module/agency/auth/login.php")

    def login(self, username: str, password: str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.captcha_input.fill(self.captcha_value.text_content())
        self.submit_button.click()