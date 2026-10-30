import re

import allure
from playwright.sync_api import expect

from config import AUTH_BASE
from pages.forgot_password_page import FORGOT_PASSWORD_URL, ForgotPasswordPage
from pages.login_page import LoginPage
from pages.reset_password_page import RESET_PASSWORD_URL, ResetPasswordPage
from test_data.forgot_password_factory import ForgotPasswordData, ForgotPasswordFactory
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Forgot Password"
LOGIN_URL = f"{AUTH_BASE}/login.php"
PASSWORD_RESET_LOGIN = re.compile(re.escape(f"{LOGIN_URL}?reason={LoginPage.REASON_PASSWORD_RESET}"))
MET = re.compile(r"\bok\b")
FAILED_ATTEMPTS = 5


def _expect_rule(forgot: ForgotPasswordPage, field, error_box, data: ForgotPasswordData) -> None:
    """Enters ``data.value`` into ``field``, leaves it, and checks the message under it."""
    with allure.step(f"{data.scenario_label}: enter '{data.value}' and leave the field"):
        forgot.enter_and_leave(field, data.value)
        expect(error_box).to_have_text(data.expected_error)


def _expect_typed(forgot: ForgotPasswordPage, field, error_box, data: ForgotPasswordData) -> None:
    """Types ``data.value`` key by key, checks what the field keeps, and — when a message is expected —
    leaves the field and checks the message under it."""
    with allure.step(f"{data.scenario_label}: type '{data.value}'"):
        forgot.type_into(field, data.value)
        expect(field).to_have_value(data.kept)
        if data.expected_error is not None:
            field.blur()
            expect(error_box).to_have_text(data.expected_error)


def _change_password(reset: ResetPasswordPage, user, new_password: str) -> None:
    """Sets ``new_password`` and, once the portal confirms the change, records it in the state store."""
    reset.set_password(new_password)
    if PASSWORD_RESET_LOGIN.search(reset.page.url):
        TestStateStore().update_password(username=user.username, password=new_password)


def _expect_on_forgot_password(forgot: ForgotPasswordPage) -> None:
    expect(forgot.page).to_have_url(re.compile(re.escape(FORGOT_PASSWORD_URL)))
    expect(forgot.heading).to_have_text(ForgotPasswordPage.HEADING)


# ---------------------------------------------------------------------------
# TC-557  Open from Login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-557")
@allure.story(STORY)
@allure.title("TC-557: \"Forgot Password?\" on Agency Login opens the Forgot password page")
def test_tc557_open_from_login(logged_out_login_page: LoginPage):
    """
    Given I am logged out on the Agency Login page
    When  I click "Forgot Password?"
    Then  Forgot password opens with the breadcrumb, the heading, the four fields, the captcha and
          "Verify and continue", and "Back to login" returns to Login

    Notion: KAN-TC-557 | KAN-43 AC-1
    """
    login = logged_out_login_page
    forgot = ForgotPasswordPage(login.page)

    with allure.step("Click \"Forgot Password?\""):
        login.forgot_password_link.click()
        _expect_on_forgot_password(forgot)

    with allure.step("Verify the page"):
        expect(forgot.breadcrumb).to_have_text("›".join(ForgotPasswordPage.BREADCRUMB))
        expect(forgot.intro).to_have_text(ForgotPasswordPage.INTRO)
        for field in (forgot.username_input, forgot.email_input, forgot.pan_input, forgot.captcha_input):
            expect(field).to_be_visible()
            expect(field).to_have_value("")
        expect(forgot.captcha_image).to_be_visible()
        expect(forgot.captcha_refresh_button).to_be_visible()
        expect(forgot.verify_button).to_have_text(ForgotPasswordPage.VERIFY_LABEL)
        expect(forgot.back_to_login_link).to_be_visible()

    with allure.step("Click \"Back to login\""):
        forgot.back_to_login_link.click()
        expect(login.page).to_have_url(re.compile(re.escape(LOGIN_URL)))
        expect(login.login_title).to_be_visible()


# ---------------------------------------------------------------------------
# TC-558  Required fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-558")
@allure.story(STORY)
@allure.title("TC-558: Verify and continue with empty fields shows a message under each field and sends nothing")
def test_tc558_required_fields(forgot_password_page: ForgotPasswordPage, valid_username_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I click "Verify and continue" with every field empty, then again with only Username filled
    Then  nothing is sent; each empty field shows its message and the cursor goes to the first one

    Notion: KAN-TC-558 | KAN-43 AC-2 | data: valid_username
    Known defect (30-Oct-2026): the empty Username message reads "Enter your username or registered
    e-mail address." although the field takes only a username — this test fails.
    """
    forgot = forgot_password_page

    with allure.step("Leave every field empty and click \"Verify and continue\""):
        forgot.verify()
        _expect_on_forgot_password(forgot)
        expect(forgot.verify_button).to_have_text(ForgotPasswordPage.VERIFY_LABEL)
        expect(forgot.email_error).to_have_text(ForgotPasswordPage.EMAIL_REQUIRED)
        expect(forgot.pan_error).to_have_text(ForgotPasswordPage.PAN_REQUIRED)
        expect(forgot.captcha_error).to_have_text(ForgotPasswordPage.CAPTCHA_REQUIRED)
        expect(forgot.username_input).to_be_focused()
        expect(forgot.username_error).to_have_text(ForgotPasswordPage.USERNAME_REQUIRED)

    with allure.step("Fill in Username only and click \"Verify and continue\""):
        forgot.fill_form(username=valid_username_data.value)
        forgot.verify()
        expect(forgot.username_error).to_have_text("")
        expect(forgot.email_error).to_have_text(ForgotPasswordPage.EMAIL_REQUIRED)
        expect(forgot.pan_error).to_have_text(ForgotPasswordPage.PAN_REQUIRED)
        expect(forgot.captcha_error).to_have_text(ForgotPasswordPage.CAPTCHA_REQUIRED)
        expect(forgot.email_input).to_be_focused()


# ---------------------------------------------------------------------------
# TC-559  Username rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-559")
@allure.story(STORY)
@allure.title("TC-559: Username accepts 6–30 letters, numbers or underscore and refuses an e-mail address")
def test_tc559_username_rules(forgot_password_page: ForgotPasswordPage,
                              invalid_username_data: list[ForgotPasswordData],
                              username_typed_with_space_data: ForgotPasswordData,
                              username_as_email_data: ForgotPasswordData,
                              valid_username_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I enter usernames that break each rule, type one with a space, enter an e-mail address and a
          valid username
    Then  each broken rule shows its message, the space is removed as I type, the e-mail address is
          refused and the valid username shows no message

    Notion: KAN-TC-559 | KAN-43 AC-3 | data: username_5_characters, username_31_characters,
            username_with_hyphen, username_typed_with_space, username_as_email, valid_username
    """
    forgot = forgot_password_page
    for data in invalid_username_data:
        _expect_rule(forgot, forgot.username_input, forgot.username_error, data)
    _expect_typed(forgot, forgot.username_input, forgot.username_error, username_typed_with_space_data)
    _expect_rule(forgot, forgot.username_input, forgot.username_error, username_as_email_data)
    _expect_rule(forgot, forgot.username_input, forgot.username_error, valid_username_data)


# ---------------------------------------------------------------------------
# TC-560  Registered e-mail rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-560")
@allure.story(STORY)
@allure.title("TC-560: Registered e-mail must be a valid address and is made small letters without spaces")
def test_tc560_email_rules(forgot_password_page: ForgotPasswordPage, invalid_email_data: list[ForgotPasswordData],
                           email_typed_with_space_and_capitals_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I enter e-mail addresses that break each rule and type one with a space and capitals
    Then  each broken rule shows its message; the typed address loses the space and the capitals and
          shows no message

    Notion: KAN-TC-560 | KAN-43 AC-3 | data: email_without_at, email_without_domain_ending,
            email_with_two_dots, email_starting_with_dot, email_typed_with_space_and_capitals
    Known defect (30-Oct-2026): when a typed space is removed the cursor jumps to the start of the field
    ("A b@Gmail.com" becomes "b@gamail.com") — this test fails.
    """
    forgot = forgot_password_page
    for data in invalid_email_data:
        _expect_rule(forgot, forgot.email_input, forgot.email_error, data)
    _expect_typed(forgot, forgot.email_input, forgot.email_error, email_typed_with_space_and_capitals_data)


# ---------------------------------------------------------------------------
# TC-561  PAN rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-561")
@allure.story(STORY)
@allure.title("TC-561: PAN must be 5 letters, 4 numbers and 1 letter and is made capitals")
def test_tc561_pan_rules(forgot_password_page: ForgotPasswordPage, pan_typed_in_small_letters_data: ForgotPasswordData,
                         invalid_pan_data: list[ForgotPasswordData], pan_pasted_too_long_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I type a PAN in small letters, enter PANs in the wrong format and paste one a character too long
    Then  the small letters become capitals, the wrong formats show the PAN message, and I am told the
          pasted PAN is too long

    Notion: KAN-TC-561 | KAN-43 AC-3 | data: pan_typed_in_small_letters, pan_9_characters,
            pan_numbers_first, pan_pasted_too_long
    Known defect (30-Oct-2026): a longer pasted PAN is cut to 10 characters without a message — this
    test fails.
    """
    forgot = forgot_password_page
    _expect_typed(forgot, forgot.pan_input, forgot.pan_error, pan_typed_in_small_letters_data)
    for data in invalid_pan_data:
        _expect_rule(forgot, forgot.pan_input, forgot.pan_error, data)

    data = pan_pasted_too_long_data
    with allure.step(f"{data.scenario_label}: paste '{data.value}' and leave the field"):
        forgot.enter_and_leave(forgot.pan_input, data.value)
        expect(forgot.pan_error, "the pasted PAN was cut to 10 characters without a message").not_to_have_text("")


# ---------------------------------------------------------------------------
# TC-562  Captcha field
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-562")
@allure.story(STORY)
@allure.title("TC-562: Captcha takes 6 characters in capitals and Refresh shows a new image")
def test_tc562_captcha_field(forgot_password_page: ForgotPasswordPage,
                             captcha_typed_with_symbols_data: ForgotPasswordData,
                             captcha_too_short_data: ForgotPasswordData,
                             captcha_with_0_and_1_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I click Refresh, type a captcha with small letters and symbols, enter 3 characters, enter one
          with 0 and 1 and look at the label
    Then  a new image is shown, only 6 capitals and numbers stay, the short captcha shows its message, the
          0-and-1 captcha is told 0 and 1 are not used, and the label reads "Captcha *"

    Notion: KAN-TC-562 | KAN-43 AC-3 | data: captcha_typed_with_symbols, captcha_3_characters,
            captcha_with_0_and_1
    Known defects (30-Oct-2026): a captcha with 0 or 1 gets "The captcha has exactly 6 letters and
    numbers.", and the label has no red * — this test fails.
    """
    forgot = forgot_password_page

    with allure.step("Click \"Refresh\""):
        old_src = forgot.captcha_image.get_attribute("src")
        new_src = forgot.refresh_captcha()
        assert new_src != old_src, "Refresh did not load a new captcha image"
        expect(forgot.captcha_image).to_be_visible()

    _expect_typed(forgot, forgot.captcha_input, forgot.captcha_error, captcha_typed_with_symbols_data)
    _expect_rule(forgot, forgot.captcha_input, forgot.captcha_error, captcha_too_short_data)

    data = captcha_with_0_and_1_data
    with allure.step(f"{data.scenario_label}: enter '{data.value}' and leave the field"):
        forgot.enter_and_leave(forgot.captcha_input, data.value)
        expect(forgot.captcha_error).to_contain_text("0")
        expect(forgot.captcha_error).to_contain_text("1")

    with allure.step("Look at the Captcha label"):
        expect(forgot.captcha_label).to_have_text(ForgotPasswordPage.FIELD_LABELS[3])


# ---------------------------------------------------------------------------
# TC-563  E-mail confirmation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-563")
@allure.story(STORY)
@allure.title("TC-563: Account is confirmed with a one-time code or link sent to the registered e-mail")
def test_tc563_email_confirmation(forgot_password_page: ForgotPasswordPage, reset_agency):
    """
    Given I am on Forgot password
    When  I enter the agency's username, registered e-mail, PAN and the captcha
    Then  the next page asks for a one-time code (or says a link was sent) and does not offer a new
          password yet

    Notion: KAN-TC-563 | KAN-43 AC-4 | data: the reset agency from the state store
    Known defect (30-Oct-2026): "Set a new password" opens straight away and nothing is sent to the
    e-mail — anyone who knows the username, e-mail and PAN can change the password. This test fails.
    Once a code or link is added, extend it to read the code from the testmail inbox.
    """
    forgot = forgot_password_page

    with allure.step("Enter the agency's details and click \"Verify and continue\""):
        forgot.submit_details(reset_agency.username, reset_agency.email, reset_agency.pan)
        expect(forgot.server_error).to_have_count(0)
        expect(forgot.captcha_error).to_have_count(0)

    with allure.step("Verify the page asks for the code sent to the e-mail"):
        reset = ResetPasswordPage(forgot.page)
        expect(reset.password_input, "Set a new password opened without an e-mail code or link").to_be_hidden()
        expect(forgot.page.locator("body")).to_contain_text(re.compile(r"code|link", re.I))


# ---------------------------------------------------------------------------
# TC-564  Set a new password opens
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-564")
@allure.story(STORY)
@allure.title("TC-564: Correct details open Set a new password for the account with the e-mail masked")
def test_tc564_set_new_password_opens(forgot_password_page: ForgotPasswordPage, reset_agency):
    """
    Given I am on Forgot password
    When  I enter the agency's username, registered e-mail, PAN and the captcha
    Then  the button reads "Sending…" and Set a new password opens for that account, its e-mail masked,
          with both password fields, the six rules and "Change password" disabled

    Notion: KAN-TC-564 | KAN-43 AC-4 | data: the reset agency from the state store
    """
    forgot = forgot_password_page
    reset = ResetPasswordPage(forgot.page)

    with allure.step("Enter the agency's details and click \"Verify and continue\""):
        forgot.submit_details(reset_agency.username, reset_agency.email, reset_agency.pan)
        assert forgot.verify_label_when_sent() == ForgotPasswordPage.SENDING_LABEL
        expect(forgot.page).to_have_url(re.compile(re.escape(RESET_PASSWORD_URL)))

    with allure.step("Verify the page"):
        expect(reset.breadcrumb).to_have_text("›".join(ResetPasswordPage.BREADCRUMB))
        expect(reset.heading).to_have_text(ResetPasswordPage.HEADING)
        expect(reset.head_text).to_have_text(ResetPasswordPage.account_line(reset_agency.username, reset_agency.email))
        expect(reset.field_labels).to_have_text(list(ResetPasswordPage.FIELD_LABELS))
        for field_id, field in (("rpPw", reset.password_input), ("rpPw2", reset.confirm_input)):
            expect(field).to_have_attribute("type", "password")
            expect(field).to_have_value("")
            expect(reset.show_button(field_id)).to_have_text("Show")
        expect(reset.rules).to_have_text(list(ResetPasswordPage.RULES))
        expect(reset.change_button).to_have_text(ResetPasswordPage.CHANGE_LABEL)
        expect(reset.change_button).to_be_disabled()
        expect(reset.back_to_login_link).to_be_visible()


# ---------------------------------------------------------------------------
# TC-565  Wrong details
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-565")
@allure.story(STORY)
@allure.title("TC-565: Wrong details or a wrong captcha keep the user on Forgot password without revealing which detail")
def test_tc565_wrong_details(forgot_password_page: ForgotPasswordPage, wrong_details_agency,
                             unknown_username_data: ForgotPasswordData, wrong_captcha_data: ForgotPasswordData):
    """
    Given I am on Forgot password
    When  I send a wrong PAN, then a username that does not exist, then the right details with a wrong captcha
    Then  the first two get the same message that does not say which detail was wrong, every answer shows
          a new captcha, and Set a new password never opens

    Notion: KAN-TC-565 | KAN-43 AC-5 | data: wrong_pan, unknown_username, wrong_captcha
    """
    forgot = forgot_password_page
    user = wrong_details_agency
    wrong_pan = ForgotPasswordFactory.wrong_pan(user.pan).value

    with allure.step("Send the right username and e-mail with a wrong PAN"):
        before = forgot.captcha_image.screenshot()
        forgot.submit_details(user.username, user.email, wrong_pan)
        _expect_on_forgot_password(forgot)
        expect(forgot.server_error).to_be_visible()
        wrong_pan_message = forgot.server_error.inner_text()
        for detail in ("PAN is wrong", "PAN does not match", "wrong PAN"):
            assert detail.lower() not in wrong_pan_message.lower(), f"The message names the PAN: {wrong_pan_message!r}"
        assert forgot.captcha_image.screenshot() != before, "No new captcha after the refusal"

    with allure.step("Send a username that does not exist"):
        forgot.open()
        forgot.submit_details(unknown_username_data.value, user.email, user.pan)
        _expect_on_forgot_password(forgot)
        expect(forgot.server_error).to_have_text(wrong_pan_message)

    with allure.step("Send the right details with a wrong captcha"):
        forgot.open()
        before = forgot.captcha_image.screenshot()
        forgot.submit_details(user.username, user.email, user.pan, captcha=wrong_captcha_data.value)
        _expect_on_forgot_password(forgot)
        expect(forgot.captcha_error).to_have_text(wrong_captcha_data.expected_error)
        assert forgot.captcha_image.screenshot() != before, "No new captcha after the wrong captcha"


# ---------------------------------------------------------------------------
# TC-566  New password checklist
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-566")
@allure.story(STORY)
@allure.title("TC-566: New password checklist, strength meter and match message enable Change password only when all pass")
def test_tc566_password_checklist(verified_reset_page: ResetPasswordPage,
                                  password_checklist_data: dict[str, ForgotPasswordData]):
    """
    Given I am on Set a new password
    When  I type passwords that meet some and then all of the rules, a different and then the same
          confirmation, add a space, and click Show
    Then  the checklist ticks the rules met, the meter turns from red to green, the match message follows
          the confirmation, "Change password" is enabled only when everything passes, and Show reveals
          the password

    Notion: KAN-TC-566 | KAN-43 AC-6 | data: small_letters_only, all_rules, confirmation_mismatch, with_space
    """
    reset = verified_reset_page
    data = password_checklist_data

    with allure.step(f"Type '{data['small_letters'].value}'"):
        reset.type_password(data["small_letters"].value)
        for key in ResetPasswordPage.RULE_KEYS:
            if key in ("len", "low", "nospace"):
                expect(reset.rule(key)).to_have_class(MET)
            else:
                expect(reset.rule(key)).not_to_have_class(MET)
        expect(reset.meter).to_have_css("background-color", ResetPasswordPage.RED)
        expect(reset.change_button).to_be_disabled()

    with allure.step(f"Type '{data['all_rules'].value}'"):
        reset.type_password(data["all_rules"].value)
        for key in ResetPasswordPage.RULE_KEYS:
            expect(reset.rule(key)).to_have_class(MET)
        expect(reset.meter).to_have_css("background-color", ResetPasswordPage.GREEN)

    with allure.step("Type a different confirmation"):
        reset.type_confirmation(data["mismatch"].value)
        expect(reset.match_message).to_have_text(ResetPasswordPage.NO_MATCH)
        expect(reset.match_message).to_have_css("color", ResetPasswordPage.NO_MATCH_RED)
        expect(reset.change_button).to_be_disabled()

    with allure.step("Type the same confirmation"):
        reset.type_confirmation(data["all_rules"].value)
        expect(reset.match_message).to_have_text(ResetPasswordPage.MATCH)
        expect(reset.match_message).to_have_css("color", ResetPasswordPage.MATCH_GREEN)
        expect(reset.change_button).to_be_enabled()

    with allure.step("Add a space to New password"):
        reset.type_password(data["with_space"].value)
        expect(reset.rule("nospace")).not_to_have_class(MET)
        expect(reset.change_button).to_be_disabled()

    with allure.step("Click \"Show\" on each field"):
        for field_id, field in (("rpPw", reset.password_input), ("rpPw2", reset.confirm_input)):
            reset.toggle_show(field_id)
            expect(field).to_have_attribute("type", "text")
            expect(reset.show_button(field_id)).to_have_text("Hide")


# ---------------------------------------------------------------------------
# TC-567  Change password
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-567")
@allure.story(STORY)
@allure.title("TC-567: Change password changes it, opens Login with a success message and only the new password works")
def test_tc567_change_password(verified_reset_page: ResetPasswordPage, reset_agency,
                               new_password_data: ForgotPasswordData):
    """
    Given I am on Set a new password
    When  I set a new password that meets every rule and log in with the old and then the new password
    Then  the button reads "Saving…", Login opens with "Your password has been changed. Log in with your
          new password.", the old password is refused and the new one logs in

    Notion: KAN-TC-567 | KAN-43 AC-7 | data: new_password (recorded in the state store)
    """
    reset = verified_reset_page
    old_password = reset_agency.password
    login = LoginPage(reset.page)

    with allure.step("Set a new password and click \"Change password\""):
        _change_password(reset, reset_agency, new_password_data.value)
        assert reset.change_label_when_sent() == ResetPasswordPage.SAVING_LABEL
        expect(reset.page).to_have_url(PASSWORD_RESET_LOGIN)
        expect(login.alert_success).to_have_text(LoginPage.PASSWORD_RESET_MESSAGE)

    with allure.step("Log in with the old password"):
        login.login(reset_agency.username, old_password)
        expect(reset.page).to_have_url(re.compile(re.escape(LOGIN_URL)))
        expect(login.error_message).to_be_visible()

    with allure.step("Log in with the new password"):
        login.open()
        login.login(reset_agency.username, new_password_data.value)
        expect(reset.page).not_to_have_url(re.compile(re.escape(LOGIN_URL)))


# ---------------------------------------------------------------------------
# TC-568  Set a new password without a request
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-568")
@allure.story(STORY)
@allure.title("TC-568: Set a new password cannot be opened without verifying an account")
def test_tc568_reset_without_request(page):
    """
    Given I have not started a password reset
    When  I open reset_password.php directly and click "Start again"
    Then  "This link can't be used" is shown with no password fields, and Start again opens Forgot password

    Notion: KAN-TC-568 | KAN-43 AC-8
    """
    page.context.clear_cookies()
    reset = ResetPasswordPage(page)

    with allure.step("Open reset_password.php directly"):
        reset.open()
        expect(reset.heading).to_have_text(ResetPasswordPage.INVALID_HEADING)
        expect(reset.head_text).to_have_text(ResetPasswordPage.INVALID_TEXT)
        expect(reset.password_input).to_have_count(0)
        expect(reset.back_to_login_link).to_be_visible()

    with allure.step("Click \"Start again\""):
        reset.start_again_link.click()
        _expect_on_forgot_password(ForgotPasswordPage(page))


# ---------------------------------------------------------------------------
# TC-569  A used reset
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-569")
@allure.story(STORY)
@allure.title("TC-569: A reset that has been used cannot change the password again")
def test_tc569_reset_used_once(verified_reset_page: ResetPasswordPage, reset_agency,
                               new_password_data: ForgotPasswordData):
    """
    Given I am on Set a new password
    When  I change the password and open reset_password.php again
    Then  "This link can't be used" is shown and the password cannot be changed again

    Notion: KAN-TC-569 | KAN-43 EC-1 | data: new_password (recorded in the state store)
    """
    reset = verified_reset_page

    with allure.step("Change the password"):
        _change_password(reset, reset_agency, new_password_data.value)
        expect(reset.page).to_have_url(PASSWORD_RESET_LOGIN)

    with allure.step("Open reset_password.php again"):
        reset.open()
        expect(reset.heading).to_have_text(ResetPasswordPage.INVALID_HEADING)
        expect(reset.password_input).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-571  Same as the current password
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-571")
@allure.story(STORY)
@allure.title("TC-571: New password cannot be the same as the current password")
def test_tc571_same_as_current(verified_reset_page: ResetPasswordPage, reset_agency):
    """
    Given I am on Set a new password
    When  I enter the current password in both fields and click "Change password"
    Then  the password is not changed and a message says the new password must be different

    Notion: KAN-TC-571 | KAN-43 EC-3 | data: the reset agency's current password
    """
    reset = verified_reset_page

    with allure.step("Enter the current password in both fields and click \"Change password\""):
        _change_password(reset, reset_agency, reset_agency.password)
        expect(reset.page, "the current password was accepted as the new one").to_have_url(
            re.compile(re.escape(RESET_PASSWORD_URL)))
        expect(reset.server_error).to_contain_text(re.compile(r"different|same|current|previous", re.I))


# ---------------------------------------------------------------------------
# TC-572  Password length
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-572")
@allure.story(STORY)
@allure.title("TC-572: New password must be 8 to 64 characters")
def test_tc572_password_length(verified_reset_page: ResetPasswordPage,
                               password_length_data: dict[int, ForgotPasswordData]):
    """
    Given I am on Set a new password
    When  I type passwords of 7, 8 and 64 characters that meet the other rules, then try a 65th character
    Then  7 characters fail "8–64 characters", 8 and 64 pass it, and no more than 64 can be entered

    Notion: KAN-TC-572 | KAN-43 EC-4 | data: password_7_characters, password_8_characters, password_64_characters
    """
    reset = verified_reset_page

    with allure.step("Type 7 characters"):
        reset.type_password(password_length_data[7].value)
        reset.type_confirmation(password_length_data[7].value)
        expect(reset.rule("len")).not_to_have_class(MET)
        expect(reset.change_button).to_be_disabled()

    for n in (8, 64):
        with allure.step(f"Type {n} characters"):
            reset.type_password(password_length_data[n].value)
            expect(reset.rule("len")).to_have_class(MET)

    with allure.step("Try to type a 65th character"):
        reset.password_input.press("End")
        reset.password_input.press_sequentially("y")
        expect(reset.password_input).to_have_value(password_length_data[64].value)


# ---------------------------------------------------------------------------
# TC-573  Paste
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-573")
@allure.story(STORY)
@allure.title("TC-573: Passwords can be pasted into the new-password fields")
def test_tc573_paste_password(verified_reset_page: ResetPasswordPage, clipboard_access,
                              new_password_data: ForgotPasswordData):
    """
    Given I am on Set a new password with a valid password on the clipboard
    When  I paste it into New password and Confirm new password
    Then  both fields hold it, the rules are ticked and "Passwords match." is shown

    Notion: KAN-TC-573 | KAN-43 Known Defects (NIST SP 800-63B) | data: new_password (not saved)
    Known defect (30-Oct-2026): paste, copy, cut and drop are blocked on both fields — this test fails.
    """
    reset = verified_reset_page
    password = new_password_data.value

    with allure.step("Put a valid password on the clipboard and paste it into both fields"):
        reset.page.evaluate("text => navigator.clipboard.writeText(text)", password)
        reset.paste_into("rpPw")
        reset.paste_into("rpPw2")

    with allure.step("Verify both fields hold the pasted password"):
        expect(reset.password_input, "paste is blocked in New password").to_have_value(password)
        expect(reset.confirm_input).to_have_value(password)
        for key in ResetPasswordPage.RULE_KEYS:
            expect(reset.rule(key)).to_have_class(MET)
        expect(reset.match_message).to_have_text(ResetPasswordPage.MATCH)


# ---------------------------------------------------------------------------
# TC-570  Repeated wrong details
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-570")
@allure.story(STORY)
@allure.title("TC-570: Repeated wrong details are limited")
def test_tc570_repeated_wrong_details(network_lockout_allowed, forgot_password_page: ForgotPasswordPage,
                                      wrong_details_agency):
    """
    Given I am on Forgot password
    When  I send the right username and e-mail with a wrong PAN five times, then the right details
    Then  the attempts are refused for a time with a message saying so, and the right details are still refused

    Notion: KAN-TC-570 | KAN-43 EC-2 | data: wrong_pan × 5
    The limit is per network: once reached, Forgot password refuses everyone on this network for an
    hour ("Too many attempts from this network. Please try again after an hour."). So this test runs
    only when RUN_NETWORK_LOCKOUT_TESTS=true, and it is kept last in the file.
    """
    forgot = forgot_password_page
    user = wrong_details_agency
    wrong_pan = ForgotPasswordFactory.wrong_pan(user.pan).value
    limited = re.compile(r"too many|try again (later|in|after)|locked|wait", re.I)

    with allure.step(f"Send a wrong PAN {FAILED_ATTEMPTS} times"):
        for attempt in range(1, FAILED_ATTEMPTS + 1):
            forgot.open()
            forgot.submit_details(user.username, user.email, wrong_pan)
            _expect_on_forgot_password(forgot)
        expect(forgot.server_error, f"no limit after {FAILED_ATTEMPTS} wrong attempts").to_contain_text(limited)

    with allure.step("Send the right details"):
        forgot.open()
        forgot.submit_details(user.username, user.email, user.pan)
        _expect_on_forgot_password(forgot)
        expect(forgot.server_error).to_contain_text(limited)
