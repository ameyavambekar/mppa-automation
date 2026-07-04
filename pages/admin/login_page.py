import allure

from pages.base_page import BasePage
from config import ADMIN_BASE

ADMIN_LOGIN_URL = f"{ADMIN_BASE}/auth/login.php"


class AdminLoginPage(BasePage):
    """Page object for the Admin / Super Admin login screen.

    Mirrors the agency ``LoginPage`` but targets the admin auth module and adds
    admin-specific elements (restricted banner, role badge, back-to-agency link).
    """

    # ── Headings & banners ────────────────────────────────────────────────────

    @property
    def restricted_banner(self):
        return self.page.locator("//*[contains(text(),'RESTRICTED')]")

    @property
    def admin_login_heading(self):
        return self.page.locator("//h2[contains(text(),'Admin Login')]")

    # ── Credential fields ─────────────────────────────────────────────────────

    @property
    def username_input(self):
        return self.page.locator("input[name='username']")

    @property
    def password_input(self):
        return self.page.locator("input[name='password']")

    @property
    def password_show_toggle(self):
        return self.page.locator("#pwToggle")

    # ── CAPTCHA ───────────────────────────────────────────────────────────────

    @property
    def captcha_value(self):
        return self.page.locator("#captcha")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def captcha_refresh_button(self):
        return self.page.locator("//button[contains(text(),'Refresh')]")

    @property
    def captcha_hidden_input(self):
        """Hidden field holding the expected CAPTCHA code (#captcha_code_hidden)."""
        return self.page.locator("#captcha_code_hidden")

    # ── Buttons & links ───────────────────────────────────────────────────────

    @property
    def admin_login_button(self):
        return self.page.locator("button[type='submit']")

    @property
    def back_to_agency_login_link(self):
        return self.page.locator("//a[contains(text(),'Back to Agency Login')]")

    # ── Messages ──────────────────────────────────────────────────────────────

    @property
    def error_message(self):
        return self.page.locator("div[class*='alert-error']")

    @property
    def alert_info(self):
        return self.page.locator("div[class*='alert-info']")

    @property
    def account_locked_message(self):
        return self.page.locator("div[class*='alert']").filter(has_text="locked")

    @property
    def session_expired_message(self):
        # TODO: confirm selector for the "Your session has expired..." banner
        return self.page.locator("div[class*='alert']").filter(has_text="session has expired")

    @property
    def session_terminated_message(self):
        # TODO: confirm selector for the "Your session was terminated by an administrator." banner
        return self.page.locator("div[class*='alert']").filter(has_text="terminated by an administrator")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Admin Login page")
    def open(self):
        self.navigate(ADMIN_LOGIN_URL)

    @allure.step("Fill admin username: {username}")
    def fill_username(self, username: str):
        self.username_input.fill(username)
        self.username_input.blur()

    @allure.step("Fill admin password")
    def fill_password(self, password: str):
        self.password_input.fill(password)
        self.password_input.blur()

    @allure.step("Toggle password visibility (SHOW / HIDE)")
    def toggle_password_visibility(self):
        self.password_show_toggle.click()

    @allure.step("Read current CAPTCHA text from DOM")
    def read_captcha_value(self) -> str:
        return self.captcha_value.text_content().strip()

    @allure.step("Fill CAPTCHA")
    def fill_captcha(self, captcha_text: str):
        self.captcha_input.fill(captcha_text)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self) -> str:
        """Clicks Refresh and returns the new CAPTCHA value."""
        self.captcha_refresh_button.click()
        return self.captcha_value.text_content().strip()

    # ── Composite actions ─────────────────────────────────────────────────────

    @allure.step("Admin login as {username}")
    def login(self, username: str, password: str):
        """Fills credentials, reads + fills the live CAPTCHA, and submits."""
        self.fill_username(username)
        self.fill_password(password)
        captcha = self.read_captcha_value()
        self.fill_captcha(captcha)
        self.admin_login_button.click()

    @allure.step("Admin login as {username} with an explicit CAPTCHA value")
    def login_with_captcha(self, username: str, password: str, captcha_text: str):
        """Fills credentials with a caller-supplied CAPTCHA (used for wrong-CAPTCHA tests)."""
        self.fill_username(username)
        self.fill_password(password)
        self.fill_captcha(captcha_text)
        self.admin_login_button.click()

    @allure.step("Click ADMIN LOGIN and handle any alert dialog")
    def click_login_and_handle_alert(self) -> str:
        """Clicks ADMIN LOGIN, handles an alert/confirm/prompt dialog, returns its message."""
        return self.click_and_handle_alert(self.admin_login_button, action="dismiss")

    @allure.step("Admin login as {username} with CAPTCHA '{captcha_text}', handling the alert")
    def login_with_captcha_and_handle_alert(
        self, username: str, password: str, captcha_text: str
    ) -> str:
        """Fills credentials + an explicit CAPTCHA, submits, and returns the alert message.

        The portal validates the CAPTCHA client-side: a wrong value fires
        ``alert("Captcha Incorrect. Please try again.")`` and regenerates the
        CAPTCHA instead of showing an inline error. Use this for wrong/stale
        CAPTCHA scenarios (TC-171, TC-176)."""
        self.fill_username(username)
        self.fill_password(password)
        self.fill_captcha(captcha_text)
        return self.click_and_handle_alert(self.admin_login_button, action="dismiss")

    @allure.step("Reload Admin Login page")
    def reload(self):
        self.page.reload()

    def get_url(self) -> str:
        return self.page.url
