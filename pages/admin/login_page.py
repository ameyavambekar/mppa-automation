import allure

from pages.base_page import BasePage
from utils.captcha_solver import solve_admin_captcha_image
from config import ADMIN_BASE

ADMIN_LOGIN_URL = f"{ADMIN_BASE}/auth/login.php"


class AdminLoginPage(BasePage):
    """Page object for the Admin / Super Admin login screen.

    Mirrors the agency ``LoginPage`` but targets the admin auth module and adds
    admin-specific elements (restricted banner, role badge, back-to-agency link).

    The page shows a ``ui-alert`` banner chosen by the ``?reason=`` query parameter
    (logout, idle timeout, maximum session duration, no session); the texts are below.
    """

    LOGIN_SUCCESS = "Login Successful!"
    LOGGED_OUT_MESSAGE = "You have been logged out successfully."
    IDLE_TIMEOUT_MESSAGE = ("You were logged out automatically after 15 minutes of inactivity. "
                            "Please log in again.")
    IDLE_TIMEOUT_MINUTES = 15
    SESSION_MAX_DURATION_MESSAGE = ("Your session reached its maximum duration and has ended. "
                                    "Please log in again.")
    NOT_LOGGED_IN_MESSAGE = "Please log in to continue."
    WRONG_CAPTCHA_MESSAGE = "Captcha is incorrect. Please try again."
    # The Security Code on screen stops being accepted after a while (seen after 15 minutes).
    CAPTCHA_EXPIRED_MESSAGE = "Captcha expired. Please refresh and try again."
    # Any admin username, the Super Admin included, is locked once it has 5 wrong passwords in a row:
    # those 5 are answered "Invalid username or password.", every attempt after them gets the lock message.
    LOCKOUT_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    ACCOUNT_LOCKED_MESSAGE = "Too many wrong attempts. For security this account is locked for 15 minutes."

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
    def captcha_image(self):
        """Server-side CAPTCHA image (#captchaImg); clicking it refreshes the captcha."""
        return self.page.locator("#captchaImg")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def captcha_refresh_button(self):
        return self.page.locator("//button[contains(text(),'Refresh')]")

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
    def login_success_message(self):
        """"Login Successful!" — shown briefly before the redirect to the dashboard."""
        return self.page.locator("div[class*='alert']").filter(has_text=self.LOGIN_SUCCESS)

    @property
    def logged_out_message(self):
        """?reason=logged_out banner, after Logout."""
        return self.page.locator("div[class*='alert']").filter(has_text=self.LOGGED_OUT_MESSAGE)

    @property
    def session_expired_message(self):
        """?reason=idle_timeout banner, after 15 minutes without activity."""
        return self.page.locator("div[class*='alert']").filter(has_text="minutes of inactivity")

    @property
    def session_max_duration_message(self):
        """?reason=session_expired banner, once the session reaches its maximum duration."""
        return self.page.locator("div[class*='alert']").filter(has_text="maximum duration")

    @property
    def not_logged_in_message(self):
        """?reason=not_logged_in banner, when an admin page is opened without a session."""
        return self.page.locator("div[class*='alert']").filter(has_text=self.NOT_LOGGED_IN_MESSAGE)

    @property
    def session_terminated_message(self):
        # Not seen on dev yet: no ?reason= value shows a killed-session banner (02-Nov-2026).
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

    @allure.step("Read current CAPTCHA value via OCR")
    def read_captcha_value(self, max_attempts: int = 5) -> str:
        """Reads the CAPTCHA from #captchaImg with the admin reader (template matching for the
        admin page's pixel font; see utils.captcha_solver and BasePage.read_image_captcha)."""
        return self.read_image_captcha(self.captcha_image, self._refresh_captcha_image, max_attempts,
                                       solve=solve_admin_captcha_image)

    @allure.step("Fill CAPTCHA")
    def fill_captcha(self, captcha_text: str):
        self.captcha_input.fill(captcha_text)

    @allure.step("Type CAPTCHA key by key")
    def type_captcha(self, captcha_text: str):
        """Types the code one key at a time, so the field's upper-casing runs as a user would see it."""
        self.captcha_input.press_sequentially(captcha_text)

    def _refresh_captcha_image(self):
        """Clicks Refresh and waits for a new #captchaImg to be requested."""
        old_src = self.captcha_image.get_attribute("src") or ""
        self.captcha_refresh_button.click()
        self._wait_for_src_change(self.captcha_image, old_src)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self) -> str:
        """Clicks Refresh and returns the new CAPTCHA value (read via OCR)."""
        self._refresh_captcha_image()
        return self.read_captcha_value()

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
        """Fills credentials with a caller-supplied CAPTCHA and submits.

        The CAPTCHA is validated server-side: a wrong/stale value reloads the
        page with an inline ``alert-error`` ("Captcha is incorrect. Please try
        again."), a fresh CAPTCHA image, the username retained and the password
        and CAPTCHA inputs cleared. Used for TC-171 and TC-176."""
        self.fill_username(username)
        self.fill_password(password)
        self.fill_captcha(captcha_text)
        self.admin_login_button.click()

    @allure.step("Admin login as {username}, retrying when the CAPTCHA is misread")
    def login_past_captcha(self, username: str, password: str, max_attempts: int = 6) -> str:
        """Submits the login until the server gets past the CAPTCHA check and returns the error
        shown ("" when the login went through). OCR sometimes misreads the code; those attempts are
        rejected with WRONG_CAPTCHA_MESSAGE (or CAPTCHA_EXPIRED_MESSAGE) before the password is
        checked, so they don't count towards the account lockout and are simply retried."""
        message = ""
        for _ in range(max_attempts):
            with self.page.expect_navigation():
                self.login(username, password)
            message = self.error_message.first.text_content().strip() if self.error_message.count() else ""
            if message not in (self.WRONG_CAPTCHA_MESSAGE, self.CAPTCHA_EXPIRED_MESSAGE):
                return message
        return message

    @allure.step("Reload Admin Login page")
    def reload(self):
        self.page.reload()

    def get_url(self) -> str:
        return self.page.url
