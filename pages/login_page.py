import allure

from .base_page import BasePage
from config import AUTH_BASE


class LoginPage(BasePage):
    """Page object for the Agency Login screen (module/agency/auth/login.php)."""

    # ── Reason banners (login.php?reason=<key>) ──────────────────────────────
    # The server renders one ``.reason-alert.<severity>`` banner per reason key.

    REASON_SESSION_EXPIRED = "session_expired"   # .reason-alert.warn
    REASON_LOGGED_OUT = "logged_out"             # .reason-alert.success
    REASON_PASSWORD_RESET = "password_reset"     # .reason-alert.success
    REASON_NOT_LOGGED_IN = "not_logged_in"       # .reason-alert.info

    # Session length is server-configured (20 min on prod, shorter on dev), so
    # only the stable prefix of the session-expired text is matched.
    SESSION_EXPIRED_MESSAGE = "Your session expired after"
    LOGGED_OUT_MESSAGE = "You have been logged out successfully."
    PASSWORD_RESET_MESSAGE = "Your password has been changed. Log in with your new password."
    NOT_LOGGED_IN_MESSAGE = "Please log in to access the portal."
    WRONG_CAPTCHA_MESSAGE = "Incorrect captcha. Please try again."

    # ── Static page text (AIO KAN-TC-44) ─────────────────────────────────────

    TITLE_TEXT = "Agency Login"
    SUBTITLE_TEXT = "Access the Placement Agency Regulation Portal"
    INSTRUCTIONS = (
        "Use the username and password created during registration.",
        "Session expires 20 minutes after login.",
        "Do not share your credentials with anyone.",
        "Captcha refreshes automatically after a wrong attempt.",
    )
    SECURITY_NOTICE_TEXT = "This is a restricted government system. Unauthorized access is punishable under the IT Act, 2000."
    FOOTER_TEXT = "Placement Agency Regulation Portal | Government System"
    REGISTER_LINK_TEXT = "New Agency? Register →"

    # ── Global Header & Breadcrumb ───────────────────────────────────────────

    @property
    def gov_banner_text(self):
        """Top strip 'Official Government Portal — Skills, Employment, …' (.site-strip)."""
        return self.page.locator(".site-strip")

    @property
    def gov_seal(self):
        """Government of Maharashtra seal in the header (.site-seal)."""
        return self.page.locator("img.site-seal")

    @property
    def gov_header_title(self):
        """Portal name in header ('Placement Agency Regulation Portal')."""
        return self.page.locator(".site-head .site-name")

    @property
    def gov_header_department(self):
        """Department line under the portal name in the header."""
        return self.page.locator(".site-head .site-dept")

    @property
    def header_helpline(self):
        """Helpline number block on the right of the header (.site-help)."""
        return self.page.locator(".site-head .site-help")

    @property
    def breadcrumb_home_link(self):
        """Breadcrumb 'Home' link to the public index page."""
        return self.page.locator("//div[contains(@class,'max-w-6xl')]//a[normalize-space()='Home']")

    @property
    def breadcrumb_agency_portal_link(self):
        """Breadcrumb 'Agency Portal' link."""
        return self.page.locator("//div[contains(@class,'max-w-6xl')]//a[normalize-space()='Agency Portal']")

    @property
    def breadcrumb_current(self):
        """Breadcrumb current-page label ('Login')."""
        return self.page.locator("//div[contains(@class,'max-w-6xl')]/span[normalize-space()='Login']")

    # ── Instructions & Security Notice ───────────────────────────────────────

    @property
    def instructions_heading(self):
        """'Login Instructions' card heading."""
        return self.page.locator("//p[normalize-space()='Login Instructions']")

    @property
    def instructions_text(self):
        """Unordered list of instruction bullet points."""
        return self.page.locator("//p[normalize-space()='Login Instructions']/following-sibling::ul")

    @property
    def instructions_items(self):
        """List items inside the instructions card (4 bullets)."""
        return self.page.locator("//p[normalize-space()='Login Instructions']/following-sibling::ul/li")

    @property
    def security_notice_heading(self):
        """'Security Notice' heading."""
        return self.page.locator("//p[normalize-space()='Security Notice']")

    @property
    def security_notice_text(self):
        """Description paragraph in the Security Notice box."""
        return self.page.locator("//p[normalize-space()='Security Notice']/following-sibling::p")

    # ── Login Card Heading ───────────────────────────────────────────────────

    @property
    def login_title(self):
        """Main heading 'Agency Login'."""
        return self.page.locator("//h2[normalize-space()='Agency Login']")

    @property
    def login_subtitle(self):
        """Subtitle under login title ('Access the Placement Agency Regulation Portal')."""
        return self.page.locator("//h2[normalize-space()='Agency Login']/following-sibling::p")

    # ── Form Fields & Labels ─────────────────────────────────────────────────

    @property
    def login_form(self):
        """The login <form> (#loginForm)."""
        return self.page.locator("#loginForm")

    @property
    def honeypot_field(self):
        """Hidden anti-bot field (input[name='hp_field']); must stay empty."""
        return self.page.locator("input[name='hp_field']")

    @property
    def username_label(self):
        """Label 'Username, registered e-mail or Application ID *'."""
        return self.page.locator("//label[contains(.,'Username')]")

    @property
    def username_input(self):
        """Username / e-mail / Application ID input (#usernameField, maxlength 100)."""
        return self.page.locator("#usernameField")

    @property
    def username_mandatory_sign(self):
        """Mandatory asterisk on Username label."""
        return self.page.locator("//label[contains(.,'Username')]/span[contains(@class,'req')]")

    @property
    def password_input(self):
        """Password input (#loginPassword, maxlength 64, paste/copy/cut blocked)."""
        return self.page.locator("#loginPassword")

    @property
    def password_show_toggle(self):
        """Show / Hide password toggle button (#pwdToggleBtn; gains class 'showing' when visible)."""
        return self.page.locator("#pwdToggleBtn")

    @property
    def password_eye_icon(self):
        """Icon span inside the toggle button (#pwdEyeIcon; currently rendered empty)."""
        return self.page.locator("#pwdEyeIcon")

    @property
    def password_toggle_text(self):
        """Text inside password toggle button (#pwdToggleText: SHOW or HIDE)."""
        return self.page.locator("#pwdToggleText")

    @property
    def password_mandatory_sign(self):
        """Mandatory asterisk on Password label."""
        return self.page.locator("//label[contains(.,'Password')]/span[contains(@class,'req')]")

    # ── CAPTCHA ──────────────────────────────────────────────────────────────

    @property
    def captcha_image(self):
        """Server-side CAPTCHA image (#captchaImg); clicking it refreshes the captcha."""
        return self.page.locator("#captchaImg")

    @property
    def captcha_value(self):
        """Alias of ``captcha_image`` — the value only lives in the PHP session, never in the DOM."""
        return self.captcha_image

    @property
    def captcha_input(self):
        """CAPTCHA input (#captchaInput; maxlength 6, auto-uppercased, A-Z0-9 only)."""
        return self.page.locator("#captchaInput")

    @property
    def captcha_mandatory_sign(self):
        """Mandatory asterisk on Captcha label."""
        return self.page.locator("//label[contains(.,'Captcha')]/span[contains(@class,'req')]")

    @property
    def captcha_refresh_button(self):
        """'⟳ Refresh' button that regenerates the CAPTCHA and clears the input (.cap-refresh)."""
        return self.page.locator("button.cap-refresh")

    @property
    def captcha_hint(self):
        """Helper text under CAPTCHA input ('Click the image or ⟳ Refresh to get a new captcha')."""
        return self.page.locator("#captchaInput ~ p")

    # ── Submit & Alerts ──────────────────────────────────────────────────────

    @property
    def login_button(self):
        """'Login to Portal' submit button (#loginBtn); disabled with class 'not-ready'
        until username, password and a 6-char captcha are filled."""
        return self.page.locator("#loginBtn")

    @property
    def reason_alert(self):
        """Any reason banner above the form (.reason-alert)."""
        return self.page.locator(".reason-alert")

    @property
    def error_message(self):
        """Error banner (.reason-alert.error / legacy .alert-error)."""
        return self.page.locator(".reason-alert.error, .alert-error")

    @property
    def alert_info(self):
        """Info banner (.reason-alert.info / legacy .alert-info), e.g. 'Please log in to access the portal.'"""
        return self.page.locator(".reason-alert.info, .alert-info")

    @property
    def alert_warn(self):
        """Warning banner (.reason-alert.warn), e.g. the session-expired notice."""
        return self.page.locator(".reason-alert.warn")

    @property
    def alert_success(self):
        """Success banner (.reason-alert.success), e.g. logged out / password changed."""
        return self.page.locator(".reason-alert.success")

    @property
    def session_expired_message(self):
        """'Your session expired after NN minutes. Please log in again.' banner."""
        return self.alert_warn.filter(has_text=self.SESSION_EXPIRED_MESSAGE)

    @property
    def logged_out_message(self):
        """'You have been logged out successfully.' banner."""
        return self.alert_success.filter(has_text=self.LOGGED_OUT_MESSAGE)

    @property
    def wrong_captcha_message(self):
        """'Incorrect captcha. Please try again.' shown after submitting a wrong CAPTCHA."""
        return self.page.get_by_text(self.WRONG_CAPTCHA_MESSAGE)

    @property
    def account_locked_message(self):
        """Error banner shown once the account is locked after repeated failed attempts."""
        return self.page.locator(".reason-alert, .alert-error").filter(has_text="failed")

    # ── Links ────────────────────────────────────────────────────────────────

    @property
    def forgot_password_link(self):
        """'Forgot Password?' link (forgot_password.php)."""
        return self.page.locator("a[href='forgot_password.php']")

    @property
    def agency_registration_link(self):
        """'New Agency? Register →' link (register.php)."""
        return self.page.locator("a[href='register.php']")

    @property
    def incomplete_registration_card(self):
        """Notice box starting 'Registration not finished yet?' (7-day completion window)."""
        return self.page.locator("//div[strong[normalize-space()='Registration not finished yet?']]")

    @property
    def resume_registration_link(self):
        """'Forgot password? Continue with email OTP' link inside the notice box (resume.php)."""
        return self.page.locator("a[href='resume.php']")

    @property
    def admin_link_label(self):
        """'Administrator?' label in the admin link bar."""
        return self.page.locator(".admin-link-bar > span")

    @property
    def admin_login_link(self):
        """'Admin Login' button linking to the admin auth module (a.admin-link-btn)."""
        return self.page.locator("a.admin-link-btn")

    # ── Footer ───────────────────────────────────────────────────────────────

    @property
    def footer_text(self):
        """Footer copyright line ('© YYYY Placement Agency Regulation Portal | Government System')."""
        return self.page.locator(
            "//footer//p[contains(text(),'Placement Agency Regulation Portal | Government System')]"
        )

    @property
    def footer_version(self):
        """Portal version label in footer ('Version x.y.z')."""
        return self.page.locator("//footer//p[contains(text(),'Version')]")

    @property
    def footer_important_links(self):
        """Links under 'Important Links' (Privacy Policy, Terms of Use, Accessibility Statement)."""
        return self.page.locator("//footer//p[normalize-space()='Important Links']/following-sibling::p/a")

    @property
    def footer_helpline(self):
        """Helpline line in the footer 'Connect' column."""
        return self.page.locator("//footer//p[starts-with(normalize-space(),'Helpline:')]")

    @property
    def footer_email(self):
        """Support e-mail line in the footer 'Connect' column."""
        return self.page.locator("//footer//p[starts-with(normalize-space(),'Email:')]")

    # ── Actions ──────────────────────────────────────────────────────────────

    def open(self, reason: str = None):
        """Navigates to the Agency Login page, optionally with a ``?reason=`` banner key."""
        url = f"{AUTH_BASE}/login.php"
        self.navigate(f"{url}?reason={reason}" if reason else url)

    @allure.step("Fill username: {username}")
    def fill_username(self, username: str):
        """Fills the username input and triggers blur for on-input sanitisation."""
        self.username_input.fill(username)
        self.username_input.blur()

    @allure.step("Fill password")
    def fill_password(self, password: str):
        """Fills the password input."""
        self.password_input.fill(password)
        self.password_input.blur()

    @allure.step("Toggle password visibility (SHOW / HIDE)")
    def toggle_password_visibility(self):
        """Clicks the password visibility button."""
        self.password_show_toggle.click()

    @allure.step("Get CAPTCHA image src attribute")
    def get_captcha_image_src(self) -> str:
        """Returns the current src URL of the CAPTCHA image element."""
        return self.captcha_image.get_attribute("src") or ""

    @allure.step("Read current CAPTCHA value via OCR")
    def read_captcha_value(self, max_attempts: int = 5) -> str:
        """Reads the CAPTCHA by OCR-ing #captchaImg (see BasePage.read_image_captcha)."""
        return self.read_image_captcha(self.captcha_image, self.refresh_captcha, max_attempts)

    @allure.step("Fill CAPTCHA: '{captcha_text}'")
    def fill_captcha(self, captcha_text: str):
        """Fills the CAPTCHA input field."""
        self.captcha_input.fill(captcha_text)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self) -> str:
        """Clicks '⟳ Refresh' and returns the new CAPTCHA image src (input is cleared by the page)."""
        old_src = self.get_captcha_image_src()
        self.captcha_refresh_button.click()
        self._wait_for_src_change(self.captcha_image, old_src)
        return self.get_captcha_image_src()

    @allure.step("Click CAPTCHA image directly to refresh")
    def click_captcha_image(self) -> str:
        """Clicks the captcha image to trigger a refresh and returns the new src."""
        old_src = self.get_captcha_image_src()
        self.captcha_image.click()
        self._wait_for_src_change(self.captcha_image, old_src)
        return self.get_captcha_image_src()

    # ── Composite Actions ────────────────────────────────────────────────────

    def _click_login_button(self):
        """Clicks Login, forcing the click when the button is still disabled."""
        if not self.login_button.is_disabled():
            self.login_button.click()
        else:
            self.login_button.click(force=True)

    @allure.step("Login as {username}")
    def login(self, username: str, password: str, captcha: str = None, max_attempts: int = 3):
        """Enters credentials, fills CAPTCHA, and submits login form.

        With no ``captcha`` the value is read by OCR; if the server answers
        'Incorrect captcha', the new CAPTCHA is read and the form resubmitted,
        up to ``max_attempts`` submissions. An explicit ``captcha`` is
        submitted once, as-is (wrong-CAPTCHA tests rely on that).
        """
        attempts = 1 if captcha else max_attempts
        for attempt in range(1, attempts + 1):
            with allure.step(f"Submit attempt {attempt}/{attempts}"):
                self.fill_username(username)
                self.fill_password(password)
                self.fill_captcha(captcha or self.read_captcha_value())
                self._click_login_button()
                self.page.wait_for_load_state()
            if captcha or not self.wrong_captcha_message.is_visible():
                return

    @allure.step("Click login button and handle alert or inline error")
    def click_login_and_handle_alert(self) -> str:
        """Clicks Login, handles any native alert dialog if fired, or returns inline error text."""
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        self._click_login_button()
        self.page.remove_listener("dialog", handle_dialog)
        if dialog_message:
            return dialog_message[0]

        if self.error_message.is_visible():
            return self.error_message.text_content().strip()
        return ""

    @allure.step("Reload Login Page")
    def reload(self):
        """Reloads the current page."""
        self.page.reload()

    def get_url(self) -> str:
        """Returns the current page URL."""
        return self.page.url
