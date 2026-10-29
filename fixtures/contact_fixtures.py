import re

import pytest

from fixtures.agency_home_fixtures import NO_SUBMITTED_AGENCY, _login_to_home, _submitted_agencies
from pages.contact_page import ContactPage
from test_data.contact_factory import ContactData, ContactFactory


def _open_as_agency(page) -> ContactPage:
    """Logs in as a submitted agency (the dev testing notice dismissed on Home) and opens Contact Us."""
    for user in _submitted_agencies():
        if _login_to_home(page, user):
            contact = ContactPage(page)
            contact.open()
            return contact
    pytest.skip(NO_SUBMITTED_AGENCY)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def agency_contact_page(page) -> ContactPage:
    """Contact Us, logged in as an agency whose application is submitted (so it has an Application ID)."""
    return _open_as_agency(page)


@pytest.fixture
def agency_application_id(agency_contact_page) -> str:
    """The logged-in agency's Application ID, read from '<username> (<Application ID>)' in the top bar."""
    return re.search(r"\((\d+)\)", agency_contact_page.user_text.inner_text()).group(1)


@pytest.fixture
def logged_out_contact_page(page):
    """Yields (contact, agency_view) — Contact Us opened logged out, and the text of the form labels and
    the right-hand cards an agency saw on it just before (logged in, then cookies cleared)."""
    contact = _open_as_agency(page)
    agency_view = {"labels": contact.field_labels.all_inner_texts(),
                   "cards": contact.card_titles.all_inner_texts(),
                   "contact_info": contact.card(ContactPage.CONTACT_INFO_TITLE).inner_text(),
                   "office_hours": contact.office_hours_card.inner_text()}
    page.context.clear_cookies()
    contact.open()
    yield contact, agency_view


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def valid_message_data() -> ContactData:
    return ContactFactory.valid_message()


@pytest.fixture
def invalid_name_data() -> list[ContactData]:
    return [ContactFactory.name_with_digits(), ContactFactory.name_with_html()]


@pytest.fixture
def name_with_punctuation_data() -> ContactData:
    return ContactFactory.name_with_punctuation()


@pytest.fixture
def email_without_at_data() -> ContactData:
    return ContactFactory.email_without_at()


@pytest.fixture
def mobile_typed_with_letters_data() -> ContactData:
    return ContactFactory.mobile_typed_with_letters()


@pytest.fixture
def invalid_mobile_data() -> list[ContactData]:
    return [ContactFactory.mobile_starting_with_5(), ContactFactory.mobile_too_short()]


@pytest.fixture
def application_id_typed_with_letters_data() -> ContactData:
    return ContactFactory.application_id_typed_with_letters()


@pytest.fixture
def short_message_data() -> ContactData:
    return ContactFactory.short_message()


@pytest.fixture
def message_with_html_data() -> ContactData:
    return ContactFactory.message_with_html()


@pytest.fixture
def over_length_limits_data() -> ContactData:
    return ContactFactory.over_length_limits()
