import allure

from config import AUTH_BASE
from pages.base_page import BasePage

FORGOT_PASSWORD_URL = f"{AUTH_BASE}/forgot_password.php"


class ForgotPasswordPage(BasePage):
    """Page object for Forgot password (module/agency/auth/forgot_password.php) — logged out.

    One ``.fp-card``: the form asks for the username (``#fpId``), the registered e-mail (``#fpEm``),
    the PAN (``#fpPan``) and an image captcha (``#fpCapImg`` + Refresh, input ``#fpCap``). Each field
    has a message box under it (``#fpIdErr`` …, empty until a rule fails) that is filled on blur and on
    "Verify and continue" (``#fpGo``). Fields are cleaned as you type: no spaces in the username, the
    e-mail in small letters, the PAN and captcha in capitals (letters and numbers only, cut to 10 and
    6). A server-side refusal shows in ``.fp-err`` above the form. Correct details open
    reset_password.php.
    """

    HEADING = "Forgot your password?"
    INTRO = ("Confirm your account with the username, the e-mail address and the PAN you registered with. "
             "You can then set a new password straight away.")
    BREADCRUMB = ("Home", "Agency login", "Forgot password")
    FIELD_LABELS = ("Username *", "Registered e-mail *", "PAN of the agency *", "Captcha *")
    VERIFY_LABEL = "Verify and continue"
    SENDING_LABEL = "Sending…"
    BACK_TO_LOGIN = "Back to login"

    # KAN-43 AC-2 / AC-3 messages
    USERNAME_REQUIRED = "Enter your username."
    EMAIL_REQUIRED = "Enter the e-mail address you registered with."
    PAN_REQUIRED = "Enter the PAN of the agency."
    CAPTCHA_REQUIRED = "Enter the characters shown in the captcha."
    USERNAME_LENGTH = "A username has 6 to 30 characters."
    USERNAME_CHARACTERS = "A username can contain only letters, numbers and underscore (_)."
    USERNAME_NOT_EMAIL = "Enter your username here (not the e-mail)."
    EMAIL_INVALID = "Enter a valid e-mail address (for example name@gmail.com)."
    EMAIL_DOMAIN = "The domain after @ is not valid (for example gmail.com or nic.in)."
    EMAIL_DOUBLE_DOT = "The e-mail address cannot contain two dots in a row."
    EMAIL_EDGE_DOT = "The part before @ cannot start or end with a dot."
    PAN_FORMAT = "PAN has 10 characters: 5 letters, 4 numbers, 1 letter (e.g. ABCDE1234F)."
    CAPTCHA_FORMAT = "The captcha has exactly 6 letters and numbers."

    # The server's refusal of a wrong captcha, shown under the captcha (the details are not checked).
    CAPTCHA_MISMATCH = "The captcha did not match. A new one is shown — please try again."

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def breadcrumb(self):
        """The breadcrumb bar; its text is ``BREADCRUMB`` joined by '›'."""
        return self.page.locator("div.max-w-6xl").filter(has=self.page.locator("a", has_text="Agency login")).first

    @property
    def heading(self):
        return self.page.locator(".fp-head h1")

    @property
    def intro(self):
        return self.page.locator(".fp-head p")

    # ── Form ──────────────────────────────────────────────────────────────────

    @property
    def field_labels(self):
        return self.page.locator(".fp-field > label")

    @property
    def captcha_label(self):
        return self.page.locator("label[for='fpCap']")

    @property
    def username_input(self):
        return self.page.locator("#fpId")

    @property
    def email_input(self):
        return self.page.locator("#fpEm")

    @property
    def pan_input(self):
        return self.page.locator("#fpPan")

    @property
    def captcha_input(self):
        return self.page.locator("#fpCap")

    @property
    def captcha_image(self):
        return self.page.locator("#fpCapImg")

    @property
    def captcha_refresh_button(self):
        return self.page.locator(".fp-cap button", has_text="Refresh")

    @property
    def username_error(self):
        return self.page.locator("#fpIdErr")

    @property
    def email_error(self):
        return self.page.locator("#fpEmErr")

    @property
    def pan_error(self):
        return self.page.locator("#fpPanErr")

    @property
    def captcha_error(self):
        return self.page.locator("#fpCapErr")

    @property
    def verify_button(self):
        return self.page.locator("#fpGo")

    @property
    def server_error(self):
        """The refusal box above the form after a submit (``.fp-err``)."""
        return self.page.locator(".fp-err")

    @property
    def back_to_login_link(self):
        return self.page.locator(".fp-foot a", has_text=self.BACK_TO_LOGIN)

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Forgot password page")
    def open(self):
        self.navigate(FORGOT_PASSWORD_URL)
        self.wait_for_load()

    @allure.step("Fill in the form")
    def fill_form(self, username: str = None, email: str = None, pan: str = None, captcha: str = None):
        """Fills the given fields; ``None`` leaves a field as it is."""
        for field, value in ((self.username_input, username), (self.email_input, email),
                             (self.pan_input, pan), (self.captcha_input, captcha)):
            if value is not None:
                field.fill(value)

    @allure.step("Enter '{value}' and leave the field")
    def enter_and_leave(self, field, value: str):
        field.fill(value)
        field.blur()

    @allure.step("Type '{value}'")
    def type_into(self, field, value: str):
        """Types key by key, so the as-you-type clean-up runs on every character."""
        field.fill("")
        field.press_sequentially(value)

    @allure.step("Click 'Refresh' on the captcha")
    def refresh_captcha(self) -> str:
        """Clicks Refresh and returns the new captcha image src."""
        old_src = self.captcha_image.get_attribute("src") or ""
        self.captcha_refresh_button.click()
        self._wait_for_src_change(self.captcha_image, old_src)
        return self.captcha_image.get_attribute("src") or ""

    @allure.step("Read the captcha via OCR")
    def read_captcha_value(self, max_attempts: int = 5) -> str:
        return self.read_image_captcha(self.captcha_image, self.refresh_captcha, max_attempts)

    def record_verify_label(self):
        """Keeps the button's text at the moment the form is sent, for ``verify_label_when_sent`` — the
        page leaves before the label can be read. Runs after the page's own submit handler."""
        self.page.evaluate("""() => document.querySelector('#fpGo').form.addEventListener('submit', e => {
            if (!e.defaultPrevented) sessionStorage.setItem('fpGoLabel', document.querySelector('#fpGo').textContent);
        })""")

    def verify_label_when_sent(self) -> str:
        return self.page.evaluate("() => sessionStorage.getItem('fpGoLabel')")

    @allure.step("Click 'Verify and continue'")
    def verify(self):
        """Clicks the button; a field that breaks a rule keeps the form on the page."""
        self.verify_button.click()

    @allure.step("Click 'Verify and continue' and wait for the answer")
    def verify_and_wait(self):
        """Clicks the button on a form that passes every rule, so it is sent, and waits for the next page."""
        self.record_verify_label()
        with self.page.expect_navigation():
            self.verify_button.click()
        self.wait_for_load()

    @allure.step("Submit the details of {username}")
    def submit_details(self, username: str, email: str, pan: str, captcha: str = None, max_attempts: int = 4):
        """Fills the form and clicks "Verify and continue". With no ``captcha`` the value is read by OCR;
        a refusal that names the captcha (an OCR misread) is retried with the new captcha, up to
        ``max_attempts`` submissions. An explicit ``captcha`` is submitted once, as-is."""
        attempts = 1 if captcha else max_attempts
        for attempt in range(1, attempts + 1):
            with allure.step(f"Submit attempt {attempt}/{attempts}"):
                self.fill_form(username, email, pan, captcha or self.read_captcha_value())
                self.verify_and_wait()
            if captcha or not self.refused_for_captcha():
                return

    def refused_for_captcha(self) -> bool:
        return self.page.url.startswith(FORGOT_PASSWORD_URL) and self.captcha_error.inner_text() == self.CAPTCHA_MISMATCH
