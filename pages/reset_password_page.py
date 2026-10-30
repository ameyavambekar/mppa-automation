import allure

from config import AUTH_BASE
from pages.base_page import BasePage

RESET_PASSWORD_URL = f"{AUTH_BASE}/reset_password.php"


class ResetPasswordPage(BasePage):
    """Page object for Set a new password (module/agency/auth/reset_password.php).

    Opens only after Forgot password confirmed an account (the request lives in the PHP session —
    there is no token in the URL). The head reads "For account <username> (<masked e-mail>)". New
    password (``#rpPw``) has a strength meter (``#rpMeter``, red / orange / green) and a six-rule
    checklist (``#rpRules li[data-r]``, class ``ok`` when met); Confirm new password (``#rpPw2``) shows
    ``#rpMatch``. Each field has a Show / Hide button; paste, copy, cut and drop are blocked.
    "Change password" (``#rpGo``) is enabled only when all six rules pass and both fields match. Without
    a confirmed request the page shows "This link can't be used" with Start again and Back to login.
    """

    HEADING = "Set a new password"
    BREADCRUMB = ("Home", "Agency login", "Set a new password")
    FIELD_LABELS = ("New password", "Confirm new password")
    RULES = ("8–64 characters", "A capital letter", "A small letter", "A number", "A special character",
             "No spaces")
    RULE_KEYS = ("len", "up", "low", "num", "sp", "nospace")
    PASSWORD_MAX_LENGTH = 64
    CHANGE_LABEL = "Change password"
    SAVING_LABEL = "Saving…"
    BACK_TO_LOGIN = "Back to login"
    MATCH = "Passwords match."
    NO_MATCH = "Passwords do not match."
    RED, ORANGE, GREEN = "rgb(217, 45, 32)", "rgb(220, 104, 3)", "rgb(7, 148, 85)"  # meter colours
    MATCH_GREEN, NO_MATCH_RED = "rgb(6, 118, 71)", "rgb(180, 35, 24)"

    INVALID_HEADING = "This link can't be used"
    INVALID_TEXT = "The password reset request is invalid, already used, or has expired. Please start again."
    START_AGAIN = "Start again"

    @staticmethod
    def masked_email(email: str) -> str:
        """The e-mail as the head shows it: the first two characters, a * for each other character before
        the @, then the domain (e.g. km***********@inbox.testmail.app)."""
        local, domain = email.split("@")
        return f"{local[:2]}{'*' * (len(local) - 2)}@{domain}"

    @classmethod
    def account_line(cls, username: str, email: str) -> str:
        return f"For account {username} ({cls.masked_email(email)})."

    # ── Head ──────────────────────────────────────────────────────────────────

    @property
    def breadcrumb(self):
        """The breadcrumb bar; its text is ``BREADCRUMB`` joined by '›'."""
        return self.page.locator("div.max-w-6xl").filter(has=self.page.locator("a", has_text="Agency login")).first

    @property
    def heading(self):
        return self.page.locator(".fp-head h1")

    @property
    def head_text(self):
        """'For account …' — or the invalid-request text."""
        return self.page.locator(".fp-head p")

    # ── Form ──────────────────────────────────────────────────────────────────

    @property
    def form(self):
        return self.page.locator("#rpForm")

    @property
    def field_labels(self):
        return self.form.locator(".fp-field > label")

    @property
    def password_input(self):
        return self.page.locator("#rpPw")

    @property
    def confirm_input(self):
        return self.page.locator("#rpPw2")

    def show_button(self, field_id: str):
        """The Show / Hide button of ``rpPw`` or ``rpPw2``."""
        return self.page.locator(f"button[data-toggle='{field_id}']")

    @property
    def meter(self):
        return self.page.locator("#rpMeter")

    @property
    def rules(self):
        return self.page.locator("#rpRules li")

    def rule(self, key: str):
        """One checklist item by its ``data-r`` key (see ``RULE_KEYS``)."""
        return self.page.locator(f"#rpRules li[data-r='{key}']")

    @property
    def match_message(self):
        return self.page.locator("#rpMatch")

    @property
    def change_button(self):
        return self.page.locator("#rpGo")

    @property
    def server_error(self):
        return self.page.locator(".fp-err")

    @property
    def back_to_login_link(self):
        return self.page.locator(".fp-foot a", has_text=self.BACK_TO_LOGIN)

    @property
    def start_again_link(self):
        return self.page.locator(".fp-body a", has_text=self.START_AGAIN)

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Set a new password directly")
    def open(self):
        self.navigate(RESET_PASSWORD_URL)
        self.wait_for_load()

    @allure.step("Type the new password")
    def type_password(self, value: str):
        self.password_input.fill(value)

    @allure.step("Type the password confirmation")
    def type_confirmation(self, value: str):
        self.confirm_input.fill(value)

    @allure.step("Click 'Show' on {field_id}")
    def toggle_show(self, field_id: str):
        self.show_button(field_id).click()

    @allure.step("Paste from the clipboard into {field_id}")
    def paste_into(self, field_id: str):
        self.page.locator(f"#{field_id}").focus()
        self.page.keyboard.press("ControlOrMeta+V")

    def record_change_label(self):
        """Keeps the button's text at the moment the form is sent (see ``change_label_when_sent``)."""
        self.page.evaluate("""() => document.querySelector('#rpForm').addEventListener('submit', () =>
            sessionStorage.setItem('rpGoLabel', document.querySelector('#rpGo').textContent))""")

    def change_label_when_sent(self) -> str:
        return self.page.evaluate("() => sessionStorage.getItem('rpGoLabel')")

    @allure.step("Click 'Change password'")
    def change_password(self):
        self.record_change_label()
        self.change_button.click()
        self.page.wait_for_load_state()

    @allure.step("Set the new password")
    def set_password(self, password: str):
        self.type_password(password)
        self.type_confirmation(password)
        self.change_password()
