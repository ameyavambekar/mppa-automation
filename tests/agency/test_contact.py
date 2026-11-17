import re
from dataclasses import asdict

import allure
from playwright.sync_api import expect

from pages.contact_page import ContactPage
from test_data.contact_factory import ContactData
from utils.aio import aio_case

STORY = "Contact Us"
SENT = re.compile(r"\bsuccess\b")
FORM_FIELDS = ("name", "email", "mobile", "application_id", "query_type", "message")


def _fill(contact: ContactPage, data: ContactData) -> None:
    contact.fill_form(**{k: v for k, v in asdict(data).items() if k in FORM_FIELDS})


def _validation_message(field) -> str:
    return field.evaluate("e => e.validationMessage")


def _is_missing(field) -> bool:
    """The browser flags the required field as empty (its message wording varies by browser and locale)."""
    return field.evaluate("e => e.validity.valueMissing")


def _is_valid(field) -> bool:
    return field.evaluate("e => e.checkValidity()")


def _record_sends(page) -> list:
    """Collects the requests other than GET the page makes from now on — how a sent message leaves the browser."""
    sent = []
    page.on("request", lambda request: sent.append(request) if request.method != "GET" else None)
    return sent


def _expect_not_sent(contact: ContactPage, field) -> None:
    """The browser stopped the send at ``field``: it has the focus and the form never started sending."""
    expect(field).to_be_focused()
    expect(contact.send_button).to_have_text(ContactPage.SEND_LABEL)
    expect(contact.send_button).to_be_enabled()
    expect(contact.alert).not_to_have_class(SENT)


def _expect_confirmed(contact: ContactPage) -> None:
    """The success message is shown and the form is cleared and ready again."""
    expect(contact.alert).to_have_class(SENT)
    expect(contact.alert).to_contain_text(ContactPage.SENT_HEADING)
    expect(contact.alert).to_contain_text(ContactPage.SENT_TEXT)
    for field in (contact.name_input, contact.email_input, contact.mobile_input, contact.application_id_input,
                  contact.query_type_select, contact.message_input):
        expect(field).to_have_value("")
    expect(contact.character_note).to_have_text(ContactPage.characters_left(ContactPage.MESSAGE_MAX_LENGTH))
    expect(contact.send_button).to_have_text(ContactPage.SEND_LABEL)
    expect(contact.send_button).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-543  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-543")
@allure.story(STORY)
@allure.title("TC-543: Contact Us shows the hero, the message form, contact information, office hours and response times")
def test_tc543_layout(agency_contact_page: ContactPage):
    """
    Given I am on the Contact Us page
    When  it loads
    Then  I see the hero, the message form, Contact Information, Office Hours and Expected Response Time,
          and "Contact Us" is highlighted in the top menu

    Notion: KAN-TC-543 | KAN-42 AC-1
    """
    contact = agency_contact_page

    with allure.step("Verify the hero"):
        expect(contact.hero_label).to_have_text(ContactPage.HERO_LABEL, use_inner_text=True)
        expect(contact.heading).to_have_text(ContactPage.HEADING)
        expect(contact.intro).to_have_text(ContactPage.INTRO)

    with allure.step("Verify the form and the right-hand column"):
        expect(contact.card_titles).to_have_text(
            [ContactPage.FORM_TITLE, ContactPage.CONTACT_INFO_TITLE, ContactPage.OFFICE_HOURS_TITLE])
        expect(contact.form).to_be_visible()
        expect(contact.response_time_box).to_be_visible()

    with allure.step("Verify \"Contact Us\" is highlighted in the top menu"):
        expect(contact.nav_link(ContactPage.HEADING)).to_have_class(re.compile(r"\bactive\b"))


# ---------------------------------------------------------------------------
# TC-544  Form fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-544")
@allure.story(STORY)
@allure.title("TC-544: Message form shows the fields, the query types and the character counter")
def test_tc544_form_fields(agency_contact_page: ContactPage):
    """
    Given I am on the Contact Us page
    When  I look at the message form and open Query Type
    Then  I see the six fields (four required), "500 characters remaining", "Send Message", the fields
          empty, and the eight query types after "— Select Query Type —"

    Notion: KAN-TC-544 | KAN-42 AC-2
    """
    contact = agency_contact_page

    with allure.step("Verify the fields, the counter and the button"):
        expect(contact.field_labels).to_have_text(list(ContactPage.FIELD_LABELS))
        for field in (contact.name_input, contact.email_input, contact.mobile_input, contact.application_id_input,
                      contact.query_type_select, contact.message_input):
            expect(field).to_have_value("")
        expect(contact.character_note).to_have_text(ContactPage.characters_left(ContactPage.MESSAGE_MAX_LENGTH))
        expect(contact.send_button).to_have_text(ContactPage.SEND_LABEL)

    with allure.step("Verify the query types"):
        expect(contact.query_type_options).to_have_text(list(ContactPage.QUERY_TYPES))


# ---------------------------------------------------------------------------
# TC-545  Required fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-545")
@allure.story(STORY)
@allure.title("TC-545: Send Message with a required field empty does not send the message")
def test_tc545_required_fields(agency_contact_page: ContactPage, valid_message_data: ContactData):
    """
    Given the message form is empty
    When  I click Send Message, filling one more required field each time
    Then  the message is not sent and the browser points to the next empty required field

    Notion: KAN-TC-545 | KAN-42 AC-3 | data: valid_message
    """
    contact = agency_contact_page
    data = valid_message_data

    with allure.step("Click Send Message with every field empty"):
        contact.send()
        _expect_not_sent(contact, contact.name_input)
        assert _is_missing(contact.name_input)

    with allure.step("Fill in Full Name and click Send Message"):
        contact.fill_form(name=data.name)
        contact.send()
        _expect_not_sent(contact, contact.email_input)
        assert _is_missing(contact.email_input)

    with allure.step("Fill in Email ID and click Send Message"):
        contact.fill_form(email=data.email)
        contact.send()
        _expect_not_sent(contact, contact.query_type_select)
        assert _is_missing(contact.query_type_select)

    with allure.step("Choose a Query Type and click Send Message"):
        contact.fill_form(query_type=data.query_type)
        contact.send()
        _expect_not_sent(contact, contact.message_input)
        assert _is_missing(contact.message_input)


# ---------------------------------------------------------------------------
# TC-546  Full Name rule
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-546")
@allure.story(STORY)
@allure.title("TC-546: Full Name accepts letters, spaces, hyphens, apostrophes and periods only")
def test_tc546_full_name_rule(agency_contact_page: ContactPage, invalid_name_data: list[ContactData],
                              name_with_punctuation_data: ContactData):
    """
    Given the rest of the form is filled in correctly
    When  I enter a name with digits, then with HTML, then with a hyphen, an apostrophe and a period
    Then  the first two are refused with the name rule and not sent; the third is accepted

    Notion: KAN-TC-546 | KAN-42 AC-4 | data: name_with_digits, name_with_html, name_with_punctuation
    """
    contact = agency_contact_page

    for data in invalid_name_data:
        with allure.step(f"Enter '{data.name}' and click Send Message"):
            _fill(contact, data)
            contact.send()
            _expect_not_sent(contact, contact.name_input)
            expect(contact.name_input).to_have_attribute("title", data.expected_error)

    with allure.step(f"Enter '{name_with_punctuation_data.name}' and verify it is accepted"):
        contact.fill_form(name=name_with_punctuation_data.name)
        assert _is_valid(contact.name_input), _validation_message(contact.name_input)


# ---------------------------------------------------------------------------
# TC-547  Email ID rule
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-547")
@allure.story(STORY)
@allure.title("TC-547: Email ID must be a valid e-mail address")
def test_tc547_email_rule(agency_contact_page: ContactPage, email_without_at_data: ContactData,
                          valid_message_data: ContactData):
    """
    Given the rest of the form is filled in correctly
    When  I enter an address without "@", then a valid address
    Then  the first is refused (the browser says it is missing an "@") and not sent; the second is accepted

    Notion: KAN-TC-547 | KAN-42 AC-4 | data: email_without_at, valid_message
    """
    contact = agency_contact_page
    data = email_without_at_data

    with allure.step(f"Enter '{data.email}' and click Send Message"):
        _fill(contact, data)
        contact.send()
        _expect_not_sent(contact, contact.email_input)
        assert data.expected_error in _validation_message(contact.email_input), \
            _validation_message(contact.email_input)

    with allure.step(f"Enter '{valid_message_data.email}' and verify it is accepted"):
        contact.fill_form(email=valid_message_data.email)
        assert _is_valid(contact.email_input), _validation_message(contact.email_input)


# ---------------------------------------------------------------------------
# TC-548  Mobile Number rule
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-548")
@allure.story(STORY)
@allure.title("TC-548: Mobile Number accepts only 10 digits starting with 6, 7, 8 or 9")
def test_tc548_mobile_rule(agency_contact_page: ContactPage, mobile_typed_with_letters_data: ContactData,
                           invalid_mobile_data: list[ContactData], valid_message_data: ContactData):
    """
    Given the rest of the form is filled in correctly
    When  I type letters and digits, then enter a number starting with 5, then a short number, then a
          valid number
    Then  only digits are kept; the starting-with-5 and short numbers are refused and not sent; the
          valid number is accepted

    Notion: KAN-TC-548 | KAN-42 AC-4 | data: mobile_typed_with_letters, mobile_starting_with_5,
            mobile_too_short, valid_message
    """
    contact = agency_contact_page
    typed = mobile_typed_with_letters_data

    with allure.step(f"Type '{typed.typed}' and verify only the digits stay"):
        contact.mobile_input.press_sequentially(typed.typed)
        expect(contact.mobile_input).to_have_value(typed.kept)

    for data in invalid_mobile_data:
        with allure.step(f"Enter '{data.mobile}' and click Send Message"):
            _fill(contact, data)
            contact.send()
            _expect_not_sent(contact, contact.mobile_input)
            expect(contact.mobile_input).to_have_attribute("title", data.expected_error)

    with allure.step(f"Enter '{valid_message_data.mobile}' and verify it is accepted"):
        contact.fill_form(mobile=valid_message_data.mobile)
        assert _is_valid(contact.mobile_input), _validation_message(contact.mobile_input)


# ---------------------------------------------------------------------------
# TC-549  Application ID
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-549")
@allure.story(STORY)
@allure.title("TC-549: Application ID accepts the agency's 13-digit Application ID")
def test_tc549_application_id(agency_contact_page: ContactPage, agency_application_id: str,
                              application_id_typed_with_letters_data: ContactData):
    """
    Given I am logged in as an agency with an Application ID
    When  I type letters and digits into Application ID, then enter my Application ID
    Then  only digits are kept, and my Application ID is accepted

    Notion: KAN-TC-549 | KAN-42 AC-4 | data: application_id_typed_with_letters, the agency's Application ID

    Known defect (29-Oct-2026, defect sheet "Agency homepage" #80): the field demands exactly 14 digits while
    Application IDs are 13 — this test fails.
    """
    contact = agency_contact_page
    typed = application_id_typed_with_letters_data

    with allure.step(f"Type '{typed.typed}' and verify only the digits stay"):
        contact.application_id_input.press_sequentially(typed.typed)
        expect(contact.application_id_input).to_have_value(typed.kept)

    with allure.step(f"Enter the agency's Application ID ({agency_application_id}) and verify it is accepted"):
        contact.fill_form(application_id=agency_application_id)
        assert _is_valid(contact.application_id_input), \
            f"{agency_application_id} refused: {contact.application_id_input.get_attribute('title')}"


# ---------------------------------------------------------------------------
# TC-550  Character counter
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-550")
@allure.story(STORY)
@allure.title("TC-550: Message counter shows the characters left out of 500")
def test_tc550_character_counter(agency_contact_page: ContactPage, short_message_data: ContactData):
    """
    Given Your Message is empty
    When  I type a message, then delete it
    Then  the counter shows 500, then 500 minus the message length, then 500 again

    Notion: KAN-TC-550 | KAN-42 AC-4, Display Rules | data: short_message
    """
    contact = agency_contact_page
    message = short_message_data.message
    limit = ContactPage.MESSAGE_MAX_LENGTH

    with allure.step("Verify the counter starts at 500"):
        expect(contact.character_note).to_have_text(ContactPage.characters_left(limit))

    with allure.step(f"Type '{message}'"):
        contact.message_input.press_sequentially(message)
        expect(contact.character_note).to_have_text(ContactPage.characters_left(limit - len(message)))

    with allure.step("Delete the message"):
        contact.message_input.fill("")
        expect(contact.character_note).to_have_text(ContactPage.characters_left(limit))


# ---------------------------------------------------------------------------
# TC-551  Send a message
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-551")
@allure.story(STORY)
@allure.title("TC-551: Send Message delivers the query to the helpdesk and confirms it")
def test_tc551_send_message(agency_contact_page: ContactPage, valid_message_data: ContactData):
    """
    Given the message form is filled in correctly
    When  I click Send Message
    Then  the button reads "Sending…" and is disabled, the query is sent to the portal, and the success
          message is shown with the form cleared

    Notion: KAN-TC-551 | KAN-42 AC-5 | data: valid_message

    The helpdesk's inbox is not reachable from the tests, so delivery is checked as the request that
    carries the query to the portal and its answer.

    Known defect (29-Oct-2026, defect sheet "Agency homepage" #79): the page only simulates sending — no request
    is made (api/contact.php answers 404) yet the success message is shown — this test fails.
    """
    contact = agency_contact_page
    sent = _record_sends(contact.page)

    with allure.step("Fill in the form and click Send Message"):
        _fill(contact, valid_message_data)
        contact.send()

    with allure.step("Verify the button reads \"Sending…\" and is disabled"):
        expect(contact.send_button).to_have_text(ContactPage.SENDING_LABEL)
        expect(contact.send_button).to_be_disabled()

    with allure.step("Verify the success message and the cleared form"):
        _expect_confirmed(contact)

    with allure.step("Verify the query was sent to the portal and accepted"):
        assert sent, "No request left the browser — the message was not sent"
        response = sent[-1].response()
        assert response is not None and response.ok, \
            f"{sent[-1].url} returned {response.status if response else 'no response'}"
        assert valid_message_data.message in (sent[-1].post_data or ""), "The request does not carry the message"


# ---------------------------------------------------------------------------
# TC-552  Contact information, office hours, response times
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-552")
@allure.story(STORY)
@allure.title("TC-552: Contact information, office hours and response times are shown, with working phone and e-mail links")
def test_tc552_contact_information(agency_contact_page: ContactPage):
    """
    Given I am on the Contact Us page
    When  I read the right-hand column
    Then  I see the helpdesk number, support e-mail, fax and office address, the phone and e-mail links,
          the office hours with the holidays note, and the expected response times

    Notion: KAN-TC-552 | KAN-42 AC-6
    """
    contact = agency_contact_page

    with allure.step("Verify Contact Information"):
        for label, value in ContactPage.INFO.items():
            expect(contact.info_value(label)).to_have_text(value)
        for line in ContactPage.ADDRESS_LINES:
            expect(contact.info_value("Office Address")).to_contain_text(line)

    with allure.step("Verify the phone and e-mail links"):
        expect(contact.phone_link).to_have_attribute("href", ContactPage.PHONE_HREF)
        expect(contact.email_link).to_have_attribute("href", ContactPage.EMAIL_HREF)

    with allure.step("Verify Office Hours"):
        for row, (days, hours) in enumerate(ContactPage.OFFICE_HOURS):
            expect(contact.office_hours_rows.nth(row).locator("td")).to_have_text([days, hours])
        expect(contact.office_hours_card).to_contain_text(ContactPage.HOLIDAYS_NOTE)

    with allure.step("Verify Expected Response Time"):
        for line in ContactPage.RESPONSE_TIMES:
            expect(contact.response_time_box).to_contain_text(line)


# ---------------------------------------------------------------------------
# TC-553  Logged out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-553")
@allure.story(STORY)
@allure.title("TC-553: Logged-out visitors see the same Contact Us page")
def test_tc553_logged_out(logged_out_contact_page):
    """
    Given I am logged out
    When  I open the Contact Us page
    Then  I see the same form, contact information and office hours as a logged-in agency, with Login
          and Register in the top bar

    Notion: KAN-TC-553 | KAN-42 AC-7
    """
    contact, agency_view = logged_out_contact_page

    with allure.step("Verify the top bar shows Login and Register"):
        expect(contact.top_bar_link("Login")).to_be_visible()
        expect(contact.top_bar_link("Register")).to_be_visible()
        expect(contact.top_bar_link("Logout")).to_have_count(0)

    with allure.step("Verify the same form, contact information and office hours as for an agency"):
        expect(contact.heading).to_have_text(ContactPage.HEADING)
        expect(contact.field_labels).to_have_text(agency_view["labels"])
        expect(contact.card_titles).to_have_text(agency_view["cards"])
        assert contact.card(ContactPage.CONTACT_INFO_TITLE).inner_text() == agency_view["contact_info"]
        assert contact.office_hours_card.inner_text() == agency_view["office_hours"]
        expect(contact.send_button).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-554  HTML in the message
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-554")
@allure.story(STORY)
@allure.title("TC-554: HTML tags typed or pasted into Your Message are removed")
def test_tc554_html_removed_from_message(agency_contact_page: ContactPage, message_with_html_data: ContactData):
    """
    Given I am on the Contact Us page
    When  I type, then paste, text with HTML tags into Your Message
    Then  the tags are removed and the counter counts what is left

    Notion: KAN-TC-554 | KAN-42 EC-1 | data: message_with_html
    """
    contact = agency_contact_page
    data = message_with_html_data
    left = ContactPage.characters_left(ContactPage.MESSAGE_MAX_LENGTH - len(data.kept))

    with allure.step(f"Type '{data.typed}'"):
        contact.message_input.press_sequentially(data.typed)
        expect(contact.message_input).to_have_value(data.kept)
        expect(contact.character_note).to_have_text(left)

    with allure.step(f"Paste '{data.typed}'"):
        contact.message_input.fill(data.typed)
        expect(contact.message_input).to_have_value(data.kept)
        expect(contact.character_note).to_have_text(left)


# ---------------------------------------------------------------------------
# TC-555  Length limits
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-555")
@allure.story(STORY)
@allure.title("TC-555: Fields stop accepting text at their length limit")
def test_tc555_length_limits(agency_contact_page: ContactPage, over_length_limits_data: ContactData):
    """
    Given I am on the Contact Us page
    When  I type 101 letters into Full Name, 11 digits into Mobile Number and 501 characters into Your Message
    Then  only the first 100, 10 and 500 are kept, and the counter shows 0

    Notion: KAN-TC-555 | KAN-42 EC-2 | data: over_length_limits
    """
    contact = agency_contact_page
    data = over_length_limits_data

    for field, text, limit in ((contact.name_input, data.name, 100), (contact.mobile_input, data.mobile, 10),
                               (contact.message_input, data.message, ContactPage.MESSAGE_MAX_LENGTH)):
        with allure.step(f"Type {len(text)} characters and verify only {limit} are kept"):
            field.press_sequentially(text)
            expect(field).to_have_value(text[:limit])

    with allure.step("Verify the counter shows 0"):
        expect(contact.character_note).to_have_text(ContactPage.characters_left(0))


# ---------------------------------------------------------------------------
# TC-556  Double click
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-556")
@allure.story(STORY)
@allure.title("TC-556: Clicking Send Message twice quickly sends one message")
def test_tc556_double_click_sends_once(agency_contact_page: ContactPage, valid_message_data: ContactData):
    """
    Given the message form is filled in correctly
    When  I double-click Send Message
    Then  the button is disabled after the first click, one success message is shown and the query is
          sent once

    Notion: KAN-TC-556 | KAN-42 EC-3 | data: valid_message

    The helpdesk's inbox is not reachable from the tests, so "sent once" is checked as the requests
    that leave the browser.

    Known defect (29-Oct-2026, defect sheet "Agency homepage" #79): the page only simulates sending, so no request
    is made — this test fails.
    """
    contact = agency_contact_page
    sent = _record_sends(contact.page)

    with allure.step("Fill in the form and double-click Send Message"):
        _fill(contact, valid_message_data)
        contact.send_button.dblclick()

    with allure.step("Verify the button is disabled and one success message is shown"):
        expect(contact.send_button).to_be_disabled()
        _expect_confirmed(contact)

    with allure.step("Verify the query was sent once"):
        assert len(sent) == 1, f"{len(sent)} requests left the browser: {[r.url for r in sent]}"
