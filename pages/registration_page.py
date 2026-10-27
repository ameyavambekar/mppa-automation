
import allure
from playwright.sync_api import expect

from pages.base_page import BasePage
from utils import email_otp
from config import AUTH_BASE, USER_MANUAL_URL

REGISTER_URL = f"{AUTH_BASE}/register.php"

class RegistrationPage(BasePage):

    # ── User Manual (user_manual.php) ────────────────────────────────────────
    # The strip / header block is the shared portal chrome and is identical on
    # user_manual.php and register.php.

    @property
    def manual_top_alert_bar(self):
        """'Official Government Portal — …' strip above the header."""
        return self.page.locator(".site-strip")

    @property
    def manual_gov_header(self):
        """Header banner with Maharashtra seal and portal title."""
        return self.page.locator("header.site-head")

    @property
    def manual_emblem_image(self):
        """Maharashtra seal image in the header."""
        return self.page.locator("header.site-head img.site-seal")

    @property
    def manual_portal_title(self):
        """'Placement Agency Regulation Portal' name in header."""
        return self.page.locator("header.site-head .site-name")

    @property
    def manual_portal_subtitle(self):
        """Department subtitle under portal title in header."""
        return self.page.locator("header.site-head .site-dept")

    @property
    def manual_helpline_label(self):
        """'Helpline' label in header."""
        return self.page.locator("header.site-head .site-help span")

    @property
    def manual_helpline_number(self):
        """Helpline phone number ('1800-XXX-XXXX') in header."""
        return self.page.locator("header.site-head .site-help strong")

    @property
    def manual_breadcrumb(self):
        """Breadcrumb navigation container."""
        return self.page.locator(".bg-white.border-b")

    @property
    def manual_breadcrumb_home_link(self):
        """'Home' link in breadcrumb pointing to index.php."""
        return self.page.locator(".bg-white.border-b a[href*='index.php']")

    @property
    def manual_breadcrumb_agency_portal_link(self):
        """'Agency Portal' link in breadcrumb."""
        return self.page.locator("//div[contains(@class,'border-b')]//a[contains(text(),'Agency Portal')]")

    @property
    def manual_breadcrumb_current_page(self):
        """'User Manual' active text in breadcrumb."""
        return self.page.locator(".bg-white.border-b span.font-medium")

    @property
    def manual_title(self):
        """'Registration User Manual' heading."""
        return self.page.locator(".um-head h2")

    @property
    def manual_subtitle(self):
        """Introductory paragraph below the manual heading."""
        return self.page.locator(".um-head p")

    @property
    def manual_card(self):
        """White card container holding the manual and agreement form."""
        return self.page.locator(".um-card")

    @property
    def manual_scroll_container(self):
        """Scrollable container containing all 5 manual sections."""
        return self.page.locator("#manualScroll")

    def manual_section_heading(self, section_title_or_number: str):
        """Returns locator for a section heading in the manual (e.g. '1. Before You Begin')."""
        return self.page.locator(f"//div[@id='manualScroll']//h3[contains(text(),'{section_title_or_number}')]")

    def manual_section_list(self, section_number: int):
        """Returns ordered list element for section_number (1 to 5)."""
        return self.page.locator(f"//div[@id='manualScroll']//h3[contains(text(),'{section_number}.')]/following-sibling::ol[1]")

    @property
    def manual_form(self):
        """Agreement form containing the confirmation checkbox and proceed button."""
        return self.page.locator("#manualForm")

    @property
    def manual_agree_label(self):
        """Text label wrapping the agreement checkbox."""
        return self.page.locator(".um-agree-label")

    @property
    def manual_agree_checkbox(self):
        """'I have read and agree to the User Manual above...' checkbox."""
        return self.page.locator("#agreeManual")

    @property
    def manual_proceed_button(self):
        """'Proceed to Registration →' button."""
        return self.page.locator("#startBtn")

    @property
    def manual_footer(self):
        """Footer container on the user manual page."""
        return self.page.locator("footer.bg-gray-900")

    @property
    def manual_footer_privacy_policy_link(self):
        """'Privacy Policy' link in footer."""
        return self.page.locator("//footer//a[contains(text(),'Privacy Policy')]")

    @property
    def manual_footer_terms_of_use_link(self):
        """'Terms of Use' link in footer."""
        return self.page.locator("//footer//a[contains(text(),'Terms of Use')]")

    @property
    def manual_footer_accessibility_link(self):
        """'Accessibility Statement' link in footer."""
        return self.page.locator("//footer//a[contains(text(),'Accessibility Statement')]")

    @property
    def manual_footer_helpline(self):
        """Helpline text in footer."""
        return self.page.locator("//footer//p[contains(text(),'Helpline: 1800-XXX-XXXX')]")

    @property
    def manual_footer_email(self):
        """Support email text in footer."""
        return self.page.locator("//footer//p[contains(text(),'support@placementportal.gov.in')]")

    @property
    def manual_footer_copyright(self):
        """Copyright text in footer."""
        return self.page.locator("//footer//p[contains(text(),'Placement Agency Regulation Portal | Government System')]")

    @property
    def manual_footer_version(self):
        """Version text in footer ('Version 2.1.0')."""
        return self.page.locator("//footer//p[contains(text(),'Version 2.1.0')]")

    # ── Registration page header (register.php) ──────────────────────────────

    @property
    def breadcrumb_current_page(self):
        """'New Registration' active text in breadcrumb."""
        return self.page.locator(".bg-white.border-b span.font-medium")

    @property
    def page_title(self):
        """'New Agency Registration Form' heading."""
        return self.page.locator("//h2[contains(text(),'Registration')]")

    @property
    def page_subtitle(self):
        return self.page.locator("//h2[contains(text(),'Registration')]//following-sibling::p")

    @property
    def mandatory_field_badge(self):
        """'* Marked fields are mandatory' badge."""
        return self.page.locator("//h2[contains(text(),'Registration')]//parent::div//following-sibling::div")

    @property
    def resume_banner(self):
        """'Already started a registration?' banner above the form."""
        return self.page.locator("//strong[contains(text(),'Already started a registration?')]/ancestor::div[2]")

    @property
    def resume_login_link(self):
        """'Login & Continue' link in the resume banner (login.php)."""
        return self.page.locator("a[href='login.php']", has_text="Login & Continue")

    def section_header(self, section_number: int):
        """Numbered section header (1 Agency & Login … 5 Declaration & Undertaking)."""
        return self.page.locator("#registrationForm .section-header").nth(section_number - 1)

    # ── Section 1 — Agency & Login Credentials ───────────────────────────────

    @property
    def agency_name_input(self):
        return self.page.locator("#agencyName")

    @property
    def agency_name_helper(self):
        return self.page.locator("#agencyName + .helper-text")

    @property
    def username_input(self):
        return self.page.locator("#username")

    @property
    def username_helper(self):
        return self.page.locator("#usernameHelper")

    @property
    def password_input(self):
        return self.page.locator("#password")

    @property
    def password_helper(self):
        """Strength label ('Very Weak' … 'Strong' / 'No spaces allowed.')."""
        return self.page.locator("#pwdHint")

    @property
    def password_strength_bar(self):
        return self.page.locator("#pwdStrengthBar")

    @property
    def password_rules_list(self):
        """Checklist of password rules below the strength bar."""
        return self.page.locator("#pwRules")

    def password_rule(self, rule: str):
        """
        Single rule in the checklist; gets class 'ok' once satisfied.
        rule: 'len' | 'up' | 'low' | 'num' | 'sym' | 'sp'
        """
        return self.page.locator(f"#pwRules li[data-r='{rule}']")

    @property
    def password_show_toggle(self):
        return self.page.locator("//input[@id='password']/following-sibling::button")

    @property
    def confirm_password_input(self):
        return self.page.locator("#confirmPassword")

    @property
    def confirm_password_helper(self):
        return self.page.locator("#confirmHint")

    @property
    def confirm_password_paste_error(self):
        return self.page.locator("#confirmPasteErr")

    @property
    def confirm_password_show_toggle(self):
        return self.page.locator("//input[@id='confirmPassword']//following-sibling::button")

    # Legacy complexity check aliases mapped to the #pwRules checklist items
    @property
    def password_length_error(self):
        return self.password_rule("len")

    @property
    def password_length_correct(self):
        return self.password_rule("len")

    @property
    def password_uppercase_error(self):
        return self.password_rule("up")

    @property
    def password_uppercase_correct(self):
        return self.password_rule("up")

    @property
    def password_number_error(self):
        return self.password_rule("num")

    @property
    def password_number_correct(self):
        return self.password_rule("num")

    @property
    def password_symbol_error(self):
        return self.password_rule("sym")

    @property
    def password_symbol_correct(self):
        return self.password_rule("sym")

    # ── Section 2 — Contact & Identity Verification ──────────────────────────

    @property
    def email_input(self):
        return self.page.locator("#email")

    @property
    def email_helper(self):
        """Static 'Enter a valid official email…' helper below the email field."""
        return self.page.locator("//input[@id='email']/parent::div/following-sibling::p[1]")

    # Email OTP — only rendered when EMAIL_OTP_ENABLED is true on the server
    # (currently disabled on dev). See is_email_otp_enabled().

    @property
    def email_otp_hint(self):
        return self.page.locator("#otpHint")

    @property
    def otp_button(self):
        return self.page.locator("#otpBtn")

    @property
    def otp_countdown_timer(self):
        return self.page.locator("#otpBtn")

    @property
    def email_otp_box(self):
        return self.page.locator("#emailOTPBox")

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
    def mobile_input(self):
        return self.page.locator("#mobile")

    @property
    def mobile_helper(self):
        """'Valid Indian mobile number starting with 6, 7, 8 or 9' helper."""
        return self.page.locator("//input[@id='mobile']/parent::div/following-sibling::p[contains(@class,'helper-text')]")

    # Mobile OTP — only rendered when MOBILE_OTP_ENABLED is true on the server
    # (currently disabled on dev). See is_mobile_otp_enabled().

    @property
    def mobile_otp_button(self):
        return self.page.locator("#mobileOtpBtn")

    @property
    def mobile_otp_box(self):
        return self.page.locator("#mobileOTPBox")

    @property
    def mobile_otp_input(self):
        return self.page.locator("#mobileOTP")

    @property
    def mobile_otp_hint(self):
        return self.page.locator("#mobileOtpHint")

    @property
    def verify_mobile_otp_button(self):
        return self.page.locator("#verifyMobileOtpBtn")

    @property
    def mobile_verified_tag(self):
        return self.page.locator("#mobileVerifiedTag")

    @property
    def alt_phone_input(self):
        return self.page.locator("#altPhone")

    @property
    def alt_phone_helper(self):
        return self.page.locator("#altPhone + .helper-text")

    @property
    def pan_input(self):
        return self.page.locator("#pan")

    @property
    def pan_helper(self):
        """TC-16 / TC-17 — Inline helper / status shown below the PAN field."""
        return self.page.locator("#panHelper")

    @property
    def district_select(self):
        return self.page.locator("#districtId")

    @property
    def district_helper(self):
        return self.page.locator("#districtId + .helper-text")

    @property
    def city_box(self):
        """City / Town box — shown only when district 'Other' (value 999) is selected."""
        return self.page.locator("#cityBox")

    @property
    def city_name_input(self):
        return self.page.locator("#cityName")

    @property
    def city_label(self):
        """'City / Town * (since you selected "Other")' label."""
        return self.page.locator("#cityBox label")

    # ── Section 3 — Document Upload ──────────────────────────────────────────
    # Only the 'Upload File' mode is offered; the live-photo (camera) option is
    # commented out in the page markup.

    @property
    def pan_upload_mode_file(self):
        return self.page.locator("input[name='panUploadMode'][value='file']")

    @property
    def pan_file_input(self):
        return self.page.locator("#panFile")

    @property
    def pan_file_helper(self):
        """'PDF, JPG or PNG — max 2 MB' helper; shows '✓ <name>' or an error after selection."""
        return self.page.locator("#panFileHelper")

    @property
    def auth_upload_mode_file(self):
        return self.page.locator("input[name='authUploadMode'][value='file']")

    @property
    def auth_sign_file_input(self):
        return self.page.locator("#authSignFile")

    @property
    def auth_sign_file_helper(self):
        """'Signed letterhead — PDF, JPG or PNG — max 5 MB' helper; updates after selection."""
        return self.page.locator("#authSignFileHelper")

    # ── Section 4 — CAPTCHA ──────────────────────────────────────────────────

    @property
    def captcha_wrapper(self):
        return self.page.locator("#captchaImgWrap")

    @property
    def captcha_value(self):
        return self.page.locator("#captchaImgWrap")

    @property
    def captcha_input(self):
        return self.page.locator("#captchaInput")

    @property
    def captcha_hint(self):
        """'Click ⟳ Refresh to load a new captcha image' hint. Wrong-captcha errors appear in server_error."""
        return self.page.locator("//input[@id='captchaInput']/parent::div/following-sibling::p[1]")

    @property
    def captcha_refresh_button(self):
        return self.page.locator("button[onclick='refreshCaptcha()']")

    # ── Section 5 — Declaration & Undertaking ────────────────────────────────

    @property
    def declaration_text_block(self):
        return self.page.locator("//p[contains(text(),'Self-Declaration')]//following-sibling::ol")

    @property
    def declaration_box(self):
        return self.page.locator("#declBox")

    @property
    def declaration_checkbox(self):
        return self.page.locator("#declarationCheck")

    @property
    def declaration_error(self):
        return self.page.locator("#declErr")

    @property
    def submit_button(self):
        return self.page.locator("#submitBtn")

    # ── Footer & Navigation Links ────────────────────────────────────────────

    @property
    def login_link(self):
        """
        The only login.php link on the page — 'Login & Continue' in the resume
        banner (the old 'Already Registered? Login →' link was removed).
        """
        return self.resume_login_link

    @property
    def support_footer(self):
        return self.page.locator("//p[contains(text(),'support@placementportal.gov.in')]")

    # ── Confirmation & Error Elements ────────────────────────────────────────

    @property
    def success_overlay(self):
        return self.page.locator("#successOverlay")

    @property
    def registration_success_message(self):
        """AC-6 — 'Registration Started!' heading after successful submission.
        No ID is shown here any more; the Application ID is issued after payment."""
        return self.page.locator("//div[@id='successOverlay']//h3")

    @property
    def redirect_countdown(self):
        """Seconds left before the overlay auto-redirects to Part A (starts at 30)."""
        return self.page.locator("#redirectCountdown")

    @property
    def continue_to_part_a_button(self):
        return self.page.locator("#partABtn")

    @property
    def submit_loader(self):
        """'Submitting registration…' overlay shown while the POST is in flight."""
        return self.page.locator("#loader")

    @property
    def server_error(self):
        return self.page.locator("#serverError")

    # Actions

    @allure.step("Open Registration User Manual page")
    def open_user_manual(self):
        """Navigates to user_manual.php and waits for network idle."""
        self.navigate(USER_MANUAL_URL)
        self.wait_for_load()

    @allure.step("Scroll Registration User Manual")
    def scroll_user_manual(self):
        """Scrolls the manual content container to the bottom and scrolls agreement into view."""
        self.manual_scroll_container.evaluate("el => el.scrollTop = el.scrollHeight")
        self.manual_agree_checkbox.scroll_into_view_if_needed()

    @allure.step("Check 'I have read and agree to User Manual'")
    def check_agree_user_manual(self):
        self.manual_agree_checkbox.check()

    @allure.step("Uncheck 'I have read and agree to User Manual'")
    def uncheck_agree_user_manual(self):
        self.manual_agree_checkbox.uncheck()

    @allure.step("Click 'Proceed to Registration →'")
    def click_proceed_to_registration(self):
        self.manual_proceed_button.click()
        self.page.wait_for_url("**/register.php**", timeout=15000)
        self.wait_for_load()

    @allure.step("Accept User Manual and proceed to Registration")
    def accept_manual_and_proceed(self):
        """Checks the agreement checkbox and submits the user manual form."""
        self.scroll_user_manual()
        self.check_agree_user_manual()
        self.click_proceed_to_registration()

    @allure.step("Open Pre-Registration page")
    def open(self):
        self.navigate(REGISTER_URL)
        self.wait_for_load()
        if "user_manual.php" in self.page.url:
            self.accept_manual_and_proceed()
        self.page.wait_for_selector("#registrationForm", state="visible", timeout=15000)

    def ensure_on_registration_page(self):
        """Ensures the browser is on register.php with registrationForm visible."""
        if "register.php" not in self.page.url or not self.page.locator("#registrationForm").is_visible():
            self.open()

    @allure.step("Start a fresh browser session (clear cookies)")
    def start_new_session(self):
        """Drops the session cookie so the User Manual gate applies again on the next visit."""
        self.page.context.clear_cookies()

    @allure.step("Go to register.php without accepting the User Manual")
    def goto_register_url(self):
        """Unlike open(), lands wherever the server redirects (user_manual.php in a fresh session)."""
        self.navigate(REGISTER_URL)
        self.wait_for_load()

    def first_invalid_field_id(self) -> str:
        """id of the first field failing the browser's built-in validation, or '' if none."""
        return self.page.evaluate(
            "() => { const f = document.querySelector('#registrationForm :invalid'); return f ? f.id : ''; }"
        )

    def get_validation_message(self, field) -> str:
        """Browser's own validation message for a field (e.g. 'Please fill out this field.')."""
        return field.evaluate("el => el.validationMessage")

    def get_selected_file_count(self, file_input) -> int:
        return file_input.evaluate("el => el.files.length")

    # Section 1

    @allure.step("Fill Agency Name: {name}")
    def fill_agency_name(self, name: str):
        self.agency_name_input.fill(name)

    @allure.step("Type Agency Name key by key")
    def type_agency_name(self, name: str):
        """Types character by character so the 150-char maxlength applies like real input."""
        self.agency_name_input.clear()
        self.agency_name_input.press_sequentially(name)

    @allure.step("Fill username: {username}")
    def fill_username(self, username: str):
        self.username_input.fill(username)
        self.username_input.blur()   # trigger on-blur / live validation (EC-9)

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
        self.confirm_password_input.wait_for(state="attached")
        if self.confirm_password_input.is_disabled():
            self.page.wait_for_function("() => !document.getElementById('confirmPassword').disabled")
        self.confirm_password_input.fill(confirm_password)

    @allure.step("Toggle show password")
    def toggle_password_visibility(self):
        """Clicks SHOW / HIDE button on the password field."""
        self.password_show_toggle.click()

    @allure.step("Toggle show confirm password")
    def toggle_confirm_password_visibility(self):
        """Clicks SHOW / HIDE button on confirm password field if present."""
        if self.confirm_password_show_toggle.count() > 0:
            self.confirm_password_show_toggle.click()

    @allure.step("Fill confirm password and blur to trigger validation")
    def fill_confirm_password_and_blur(self, confirm_password: str):
        """
        Fills the confirm-password field and blurs it so on-blur
        mismatch errors are triggered (used by TC-08).
        """
        self.fill_confirm_password(confirm_password)
        self.confirm_password_input.blur()

    @allure.step("Paste into Confirm Password via the clipboard")
    def paste_into_confirm_password(self, text: str):
        """Real clipboard paste (Ctrl/Cmd+V) so the page's onpaste blocker is what stops it."""
        self.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
        self.page.evaluate("t => navigator.clipboard.writeText(t)", text)
        self.confirm_password_input.focus()
        self.page.keyboard.press("ControlOrMeta+V")

    @allure.step("Fill Section 1 — Login Credentials")
    def fill_credentials(self, username: str, password: str, confirm_password: str = None):
        self.fill_username(username)
        self.fill_password(password)
        self.fill_confirm_password(confirm_password or password)


    # Section 2

    def is_email_otp_enabled(self) -> bool:
        """Reads the page's EMAIL_OTP_ENABLED flag; the OTP widgets exist only when it's true."""
        return self.page.evaluate("() => typeof EMAIL_OTP_ENABLED !== 'undefined' && !!EMAIL_OTP_ENABLED")

    def is_mobile_otp_enabled(self) -> bool:
        """Reads the page's MOBILE_OTP_ENABLED flag; the OTP widgets exist only when it's true."""
        return self.page.evaluate("() => typeof MOBILE_OTP_ENABLED !== 'undefined' && !!MOBILE_OTP_ENABLED")

    @allure.step("Fill email: {email}")
    def fill_email(self, email: str):
        self.email_input.wait_for(state="visible")
        self.email_input.fill(email)
        self.email_input.blur()

    @allure.step("Fill email and trigger OTP")
    def fill_email_and_request_otp(self, email: str):
        """Requires EMAIL_OTP_ENABLED — #otpBtn is not rendered otherwise."""
        self.fill_email(email)
        self.otp_button.click()

    @allure.step("Fill email and verify via OTP if enabled")
    def fill_email_and_verify_if_required(self, email: str):
        """Fills the email and runs the OTP round-trip only when the page has email OTP switched on."""
        if self.is_email_otp_enabled():
            self.fill_email_and_request_otp(email)
            self.enter_otp_and_verify_email()
        else:
            self.fill_email(email)


    @allure.step("Enter OTP and verify email")
    def enter_otp_and_verify_email(self, otp_code: str = None):
        if otp_code is None:
            existing_val = self.email_otp_input.input_value().strip()
            if existing_val and len(existing_val) == 6:
                otp_code = existing_val
            else:
                try:
                    otp_code = email_otp.get_otp_from_testmail(retries=2, delay=2)
                except Exception:
                    otp_code = "123456"
        self.email_otp_input.fill(otp_code)
        self.email_otp_input.blur()
        self.verify_otp_button.click()

    @allure.step("Submit incorrect otp and handle alert")
    def submit_otp_and_handle_alert(self, wrong_otp: str = "000000") -> str:
        """
        Clicks Submit, handles any alert/confirm/prompt dialog,
        and returns the dialog message for assertions.
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        self.email_otp_input.fill(wrong_otp)
        self.verify_otp_button.click()
        self.page.wait_for_timeout(500)
        self.page.remove_listener("dialog", handle_dialog)  # clean up
        return dialog_message[0] if dialog_message else ""

    @allure.step("Fill Mobile: {mobile}")
    def fill_mobile(self, mobile: str):
        self.mobile_input.fill(mobile)
        self.mobile_input.blur()

    @allure.step("Request and verify mobile OTP")
    def request_and_verify_mobile_otp(self, otp_code: str = None):
        """
        Requires MOBILE_OTP_ENABLED. With no otp_code, uses the dev OTP the
        server pre-fills into #mobileOTP (there is no SMS inbox helper).
        """
        self.mobile_otp_button.click()
        self.mobile_otp_box.wait_for(state="visible")
        if otp_code is None:
            self.page.wait_for_function("() => document.getElementById('mobileOTP').value.length === 6")
            otp_code = self.mobile_otp_input.input_value().strip()
        self.mobile_otp_input.fill(otp_code)
        self.verify_mobile_otp_button.click()

    @allure.step("Fill Mobile and verify via OTP if enabled: {mobile}")
    def fill_mobile_and_verify_if_required(self, mobile: str):
        self.fill_mobile(mobile)
        if self.is_mobile_otp_enabled():
            self.request_and_verify_mobile_otp()

    @allure.step("Fill Alternate Phone: {alt_phone}")
    def fill_alt_phone(self, alt_phone: str):
        self.alt_phone_input.fill(alt_phone)
        self.alt_phone_input.blur()

    @allure.step("Type Mobile key by key: {mobile}")
    def type_mobile(self, mobile: str):
        """Types character by character so the on-input digit filter and maxlength apply."""
        self.mobile_input.clear()
        self.mobile_input.press_sequentially(mobile)

    @allure.step("Type Alternate Phone key by key: {alt_phone}")
    def type_alt_phone(self, alt_phone: str):
        """Types character by character so the on-input character filter and maxlength apply."""
        self.alt_phone_input.clear()
        self.alt_phone_input.press_sequentially(alt_phone)

    @allure.step("Upload PAN document")
    def upload_pan_document(self, file_info=None):
        payload = file_info or {
            "name": "pan_card.pdf",
            "mimeType": "application/pdf",
            "buffer": b"%PDF-1.4 dummy pan document content",
        }
        self.pan_file_input.set_input_files(payload)

    @allure.step("Upload Authorised Signatory document")
    def upload_auth_sign_document(self, file_info=None):
        payload = file_info or {
            "name": "auth_sign.pdf",
            "mimeType": "application/pdf",
            "buffer": b"%PDF-1.4 dummy auth sign document content",
        }
        self.auth_sign_file_input.set_input_files(payload)

    @allure.step("Remove the selected PAN document")
    def clear_pan_document(self):
        self.pan_file_input.set_input_files([])

    @allure.step("Remove the selected Authorised Signatory document")
    def clear_auth_sign_document(self):
        self.auth_sign_file_input.set_input_files([])

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

    @allure.step("Fill City / Town: {city}")
    def fill_city_name(self, city: str):
        """Only applicable after selecting district 'Other' (value 999)."""
        self.city_name_input.fill(city)
        self.city_name_input.blur()

    @allure.step("Type City / Town key by key: {city}")
    def type_city_name(self, city: str):
        """Types character by character so the on-input character filter applies."""
        self.city_name_input.clear()
        self.city_name_input.press_sequentially(city)

    @allure.step("Fill Section 2 — Contact & Identity")
    def fill_contact_identity(self, email: str, pan: str, district: str, mobile: str = "9876543210",
                              alt_phone: str = "02224567890", city_name: str = None):
        self.fill_email_and_verify_if_required(email)
        self.fill_mobile_and_verify_if_required(mobile)
        self.fill_alt_phone(alt_phone)
        self.fill_pan(pan)
        self.select_district(district)
        if city_name:                    # City / Town is only shown for district "Other"
            self.fill_city_name(city_name)

    # Section 3

    @allure.step("Fill Section 3 — Document Upload")
    def fill_document_upload(self, pan_file=None, auth_sign_file=None):
        self.upload_pan_document(pan_file)
        self.upload_auth_sign_document(auth_sign_file)

    # Section 4
    @allure.step("Read current CAPTCHA text from DOM")
    def read_captcha_value(self) -> str:
        """
        Returns the CAPTCHA string currently rendered in #captchaImgWrap SVG.
        """
        import re
        text = self.captcha_wrapper.text_content().strip()
        chars = re.findall(r'[A-Za-z0-9]', text)
        return "".join(chars)

    @allure.step("Fill CAPTCHA from DOM value")
    def fill_captcha(self, captcha_text: str = None):
        """Reads visible CAPTCHA text or uses provided text and fills input."""
        val = captcha_text if captcha_text is not None else self.read_captcha_value()
        self.captcha_input.fill(val)

    @allure.step("Refresh CAPTCHA")
    def refresh_captcha(self) -> str:
        """EC-1 — Clicks Refresh and returns the new CAPTCHA value."""
        old_val = self.read_captcha_value()
        self.captcha_refresh_button.click()
        for _ in range(25):
            self.page.wait_for_timeout(200)
            new_val = self.read_captcha_value()
            if new_val and new_val != old_val:
                return new_val
        return self.read_captcha_value()

    # Section 5

    @allure.step("Accept Declaration & Undertaking")
    def accept_declaration(self):
        self.declaration_checkbox.check()

    @allure.step("Submit Registration form")
    def submit(self):
        self.submit_button.click()

    @allure.step("Click 'Login & Continue' link")
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
        self.page.evaluate("() => { const f = document.getElementById('registrationForm'); if (f) f.noValidate = true; }")
        self.submit_button.click()
        self.page.wait_for_timeout(500)
        self.page.remove_listener("dialog", handle_dialog)  # clean up

        return dialog_message[0] if dialog_message else ""

    # ── Composite action ──────────────────────────────────────────────────────

    def complete_registration(self, data):
        """
        Convenience method used by happy-path tests.
        Accepts an AgencyRegistrationData object.
        Does NOT click Submit — keeps that in the test for flexibility.
        """
        agency_name = getattr(data, "agency_name", "Maharashtra Placement Agency")
        mobile = getattr(data, "mobile", "9876543210")
        alt_phone = getattr(data, "alt_phone", "02224567890")
        self.fill_agency_name(agency_name)
        self.fill_credentials(data.username, data.password, data.confirm_password)
        self.fill_contact_identity(data.email, data.pan_number, data.district, mobile, alt_phone,
                                   getattr(data, "city_name", None))
        self.fill_document_upload()
        self.fill_captcha()
        self.accept_declaration()


    duplicate_pan_error = "This PAN number is already registered (or a registration with it is in progress). If this is your PAN, please contact support."
    incorrect_captcha_error = "Incorrect captcha. Please try again."
    district_not_selected_error = "Please select your district." #Alert Pop-up
    city_not_entered_error = "Please enter your city/town name." #Alert Pop-up
    pan_file_missing_error = "Please upload your PAN card file." #Alert Pop-up
    auth_sign_file_missing_error = "Please upload the Authorised Signatory letterhead file." #Alert Pop-up
    pan_file_too_large_error = "File exceeds 2 MB limit." #Inline (#panFileHelper)
    auth_sign_file_too_large_error = "File exceeds 5 MB limit." #Inline (#authSignFileHelper)
    unsupported_file_type_error = "Only PDF, JPG, PNG files are allowed." #Inline
    confirm_paste_error = "Paste not allowed — type your password manually." #Inline (#confirmPasteErr)
    declaration_error_message = "You must accept the declaration to proceed with registration."
    manual_agree_alert_message = "Please confirm you have read and agree to the User Manual."