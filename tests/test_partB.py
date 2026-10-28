import re

import allure
import pytest
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partA_page import PART_A_LOCKED_STEP_URL, PartAPage
from pages.partB_page import PART_B_URL, PartBPage
from test_data.partB_factory import KeyPersonData, PartBFactory, TypedInput
from test_data.partA_factory import PartAData, PartAFactory
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Step 2 - Key Persons"
LABEL = PartBFactory.PERSON_LABEL
# A successful save lands on Part C (partC.php?prev_saved=1).
PART_C_URL = re.compile(rf"{re.escape(FORMS_BASE)}/partC\.php")
ON_PART_B = re.compile(rf"{re.escape(PART_B_URL)}")


def _fill_person(part_b: PartBPage, index: int, data: KeyPersonData) -> None:
    part_b.fill_key_person(
        index, data.full_name, data.aadhaar, data.mobile, data.address,
        email=data.email, din=data.din, pan=data.pan, nationality=data.nationality,
        passport=data.passport, country_code=data.country_code,
    )


def _add_person(part_b: PartBPage) -> int:
    """Clicks 'Add Another …' and returns the new card's index."""
    part_b.click_add_person()
    return part_b.person_indexes()[-1]


def _expect_server_errors(part_b: PartBPage, page, *messages: str, person: int = 1) -> None:
    """Part B was reloaded with the error box listing each message for ``person``."""
    expect(page).to_have_url(ON_PART_B)
    expect(part_b.server_errors).to_contain_text(PartBPage.ERRORS_HEADING)
    for message in messages:
        expect(part_b.server_errors).to_contain_text(PartBPage.person_error(person, message))


def _expect_blocked_by_browser(part_b: PartBPage, page, field, check: str) -> None:
    """The browser refused to submit because ``field`` fails ``validity.<check>``."""
    assert field.evaluate(f"e => e.validity.{check}"), f"{check} not reported for the field"
    expect(page).to_have_url(ON_PART_B)
    expect(part_b.server_errors).to_have_count(0)


def _expect_part_b_saved(page, user) -> None:
    expect(page).to_have_url(PART_C_URL)
    TestStateStore().mark_form_step_status(username=user.username, step="part_b", status="completed")


def _expect_typed(part_b: PartBPage, index: int, case: TypedInput) -> None:
    field = getattr(part_b, case.field)(index)
    part_b.type_key_by_key(field, case.typed)
    expect(field).to_have_value(case.shown)


# ---------------------------------------------------------------------------
# TC-81  Part B is not accessible until Part A is saved
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-81")
@allure.story(STORY)
@allure.title("TC-81: Part B is not accessible until Part A is saved")
def test_tc81_part_b_locked_until_part_a_saved(part_b_page: PartBPage, fresh_agency_user_page):
    """
    Given I am logged in and Part A has not been saved
    When  I look at the progress bar and open Part B directly by URL
    Then  Part B is not a clickable step and I am redirected back to Part A

    Notion: KAN-TC-81 | KAN-19 AC-1 | data: fresh_agency_user
    """
    page, user = fresh_agency_user_page

    with allure.step("Verify Part B in the progress bar is not a link"):
        expect(part_b_page.progress_step("Part B")).to_be_visible()
        expect(part_b_page.completed_step_link("Part B")).to_have_count(0)

    with allure.step("Open Part B directly by URL"):
        part_b_page.open()

    with allure.step("Verify the user is redirected to Part A"):
        expect(page).to_have_url(PART_A_LOCKED_STEP_URL)
        expect(part_b_page.title).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-82  Part B opens after Part A is saved — DESTRUCTIVE (uses up a fresh user)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-82")
@allure.story(STORY)
@allure.title("TC-82: Part B opens after Part A is saved")
def test_tc82_part_b_opens_after_part_a_saved(
    part_a_page: PartAPage, part_b_page: PartBPage, logged_in_part_a_fresh_mh_page, part_a_valid_data: PartAData
):
    """
    Given I am on Part A with every mandatory field filled (Private Limited Company)
    When  I save Part A
    Then  Part A shows ✓ in the progress bar, Part B is the active stage
    And   Part B shows "Step 2 — Part B: Key Persons" with its subtitle

    Notion: KAN-TC-82 | KAN-19 AC-1 | data: valid_mandatory_fields (Part A)
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_valid_data, user)

    with allure.step("Fill every mandatory Part A field"):
        part_a_page.select_legal_constitution(data.legal_constitution)
        part_a_page.fill_agency_date_of_establishment(data.date_of_establishment)
        part_a_page.fill_incorporation_no(data.incorporation_no)
        part_a_page.set_incorporation_certificate(data.incorporation_certificate)
        part_a_page.fill_tan(data.tan_number)
        part_a_page.set_tan_certificate(data.tan_certificate)
        part_a_page.fill_gst(data.gstin)
        part_a_page.set_gst_certificate(data.gst_certificate)
        part_a_page.fill_address_line1(data.address_line1)
        part_a_page.set_taluka(data.taluka)
        part_a_page.fill_city(data.city)
        part_a_page.fill_pincode(data.pincode)
        part_a_page.fill_authorised_signatory(data.authorised_signatory)
        part_a_page.fill_designation(data.designation)

    with allure.step("Save Part A"):
        part_a_page.click_save_next()
        page.wait_for_load_state("networkidle")
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )

    with allure.step("Open Part B"):
        part_b_page.open()
        expect(page).to_have_url(ON_PART_B)

    with allure.step("Verify Part A shows ✓ and Part B is the active stage"):
        expect(part_b_page.completed_step_link("Part A")).to_contain_text("✓")
        expect(part_b_page.progress_step("Part B")).to_be_visible()

    with allure.step("Verify the heading and subtitle"):
        expect(part_b_page.title).to_have_text("Step 2 — Part B: Key Persons")
        expect(part_b_page.sub_title).to_have_text("Nationality verified via Aadhaar / Passport")


# ---------------------------------------------------------------------------
# TC-83  Category banner reflects the agency type from Part A
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-83")
@allure.story(STORY)
@allure.title("TC-83: Category of Key Persons banner reflects the agency type from Part A")
def test_tc83_category_banner_reflects_agency_type(part_b_page: PartBPage, part_b_login_as):
    """
    Given Part A is saved as Private Limited Company
    When  I open Part B
    Then  the banner, the first card title and the add button all say "Director"
    And   for a Proprietorship agency they all say "Proprietor"

    Notion: KAN-TC-83 | KAN-19 AC-2 | data: Private Limited Company, Proprietorship users
    """
    for agency_type, label in ((PartBFactory.AGENCY_TYPE, PartBFactory.PERSON_LABEL),
                               (PartBFactory.PROPRIETORSHIP_AGENCY_TYPE, PartBFactory.PROPRIETORSHIP_LABEL)):
        with allure.step(f"Log in as a {agency_type} agency and open Part B"):
            part_b_login_as(agency_type)

        with allure.step(f"Verify the banner names '{label}' and '{agency_type}'"):
            expect(part_b_page.category_banner).to_contain_text(f"Category of Key Persons: {label}")
            expect(part_b_page.category_banner).to_contain_text(f"(based on your agency type: {agency_type})")

        with allure.step(f"Verify '{label} 1' and 'Add Another {label}'"):
            expect(part_b_page.person_title(0)).to_have_text(f"{label} 1")
            expect(part_b_page.add_person_button).to_have_text(f"Add Another {label}")

        if label == PartBFactory.PERSON_LABEL:
            with allure.step("Verify the guidance note for Private Limited Company"):
                expect(part_b_page.guidance_note).to_contain_text(
                    "Aadhaar is mandatory for every person. Passport is required only for foreign nationals. "
                    "DIN/DPIN and PAN are required for each Director under Private Limited Company."
                )


# ---------------------------------------------------------------------------
# TC-84  All mandatory fields are validated on save
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-84")
@allure.story(STORY)
@allure.title("TC-84: All mandatory fields in a key person entry are validated on save")
def test_tc84_mandatory_fields_validated_on_save(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_blank_data: KeyPersonData
):
    """
    Given Director 1 is empty
    When  I save, then fill only Full Name and save again
    Then  the browser first blocks the save on Full Name
    And   the server then rejects DIN / DPIN, PAN, Aadhaar, Mobile and Residential Address
    And   Personal Email ID (optional) is not reported

    Notion: KAN-TC-84 | KAN-19 AC-5 | data: blank
    """
    page, user = logged_in_part_b_page

    with allure.step("Clear every field of Director 1"):
        _fill_person(part_b_page, 0, part_b_blank_data)
        part_b_page.fill_personal_email(0, "")

    with allure.step("Click 'Save Part B & Continue' — the browser blocks on Full Name"):
        part_b_page.click_submit()
        _expect_blocked_by_browser(part_b_page, page, part_b_page.full_name_input(0), "valueMissing")

    with allure.step("Enter Full Name only and save"):
        part_b_page.fill_full_name(0, PartBFactory.valid_director().full_name)
        part_b_page.click_submit()

    with allure.step("Verify the server lists every blank mandatory field"):
        _expect_server_errors(
            part_b_page, page,
            PartBPage.AADHAAR_REQUIRED_ERROR, PartBPage.DIN_REQUIRED_ERROR, PartBPage.PAN_REQUIRED_ERROR,
            PartBPage.MOBILE_REQUIRED_ERROR, PartBPage.ADDRESS_REQUIRED_ERROR,
        )
        expect(part_b_page.server_errors).not_to_contain_text("mail")


# ---------------------------------------------------------------------------
# TC-85  Full Name accepts a valid legal name
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-85")
@allure.story(STORY)
@allure.title("TC-85: Full Name field accepts a valid legal name")
def test_tc85_full_name_accepts_valid_name(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_long_name_data: KeyPersonData
):
    """
    Given I am on Part B
    When  I enter a valid name, then type more than 150 characters
    Then  the name is kept as entered, and only 150 characters are kept

    Notion: KAN-TC-85 | data: full_name_too_long
    """
    page, user = logged_in_part_b_page
    data = part_b_long_name_data

    with allure.step("Verify the Full Name placeholder"):
        expect(part_b_page.full_name_input(0)).to_have_attribute("placeholder", "Full legal name as per Aadhaar")

    with allure.step(f"Enter '{data.full_name}' and leave the field"):
        part_b_page.fill_full_name(0, data.full_name)
        expect(part_b_page.full_name_input(0)).to_have_value(data.full_name)

    with allure.step("Type 151 characters — only 150 are kept"):
        long_name = data.invalid_values[0]
        part_b_page.type_key_by_key(part_b_page.full_name_input(0), long_name)
        expect(part_b_page.full_name_input(0)).to_have_value(long_name[:150])


# ---------------------------------------------------------------------------
# TC-86  Error shown when Full Name is left blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-86")
@allure.story(STORY)
@allure.title("TC-86: Error shown when Full Name is left blank")
def test_tc86_full_name_blank(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given I am on Part B
    When  I leave Full Name blank and click "Save Part B & Continue"
    Then  the browser blocks the submit on Full Name (required field)

    Notion: KAN-TC-86 | KAN-19 AC-5
    """
    page, user = logged_in_part_b_page

    with allure.step("Clear Full Name"):
        part_b_page.fill_full_name(0, "")

    with allure.step("Click 'Save Part B & Continue'"):
        part_b_page.click_submit()

    with allure.step("Verify the browser blocks the submit on Full Name"):
        _expect_blocked_by_browser(part_b_page, page, part_b_page.full_name_input(0), "valueMissing")


# ---------------------------------------------------------------------------
# TC-87  Error shown when Full Name contains invalid characters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-87")
@allure.story(STORY)
@allure.title("TC-87: Error shown when Full Name contains invalid characters")
def test_tc87_full_name_invalid_characters(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_invalid_name_data: KeyPersonData
):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with a name containing digits, then one containing a symbol
    Then  each save is rejected with "Full name must be at least 3 characters, letters only."

    Notion: KAN-TC-87 | data: full_name_invalid_characters
    """
    page, user = logged_in_part_b_page
    data = part_b_invalid_name_data
    _fill_person(part_b_page, 0, data)

    for name in data.invalid_values:
        with allure.step(f"Save with Full Name '{name}'"):
            part_b_page.fill_full_name(0, name)
            part_b_page.click_submit()

        with allure.step("Verify the name is rejected and kept"):
            _expect_server_errors(part_b_page, page, data.expected_error)
            expect(part_b_page.full_name_input(0)).to_have_value(name)


# ---------------------------------------------------------------------------
# TC-88  Aadhaar accepts a valid 12-digit number
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-88")
@allure.story(STORY)
@allure.title("TC-88: Aadhaar field accepts a valid 12-digit number")
def test_tc88_aadhaar_accepts_valid_number(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_aadhaar_max_length_case: TypedInput
):
    """
    Given I am on Part B
    When  I enter a valid 12-digit Aadhaar, then type a 13th digit
    Then  the 12 digits are kept and the 13th is dropped
    And   the hint "Cannot start with 0 or 1" is shown

    Notion: KAN-TC-88 | data: aadhaar_max_length_case
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify the placeholder and hint"):
        expect(part_b_page.aadhaar_input(0)).to_have_attribute("placeholder", "12-digit Aadhaar")
        expect(part_b_page.aadhaar_hint(0)).to_have_text(PartBPage.AADHAAR_HINT)

    with allure.step("Enter a valid Aadhaar"):
        valid = PartBFactory.valid_director().aadhaar
        part_b_page.fill_aadhaar(0, valid)
        expect(part_b_page.aadhaar_input(0)).to_have_value(valid)

    with allure.step("Enter 13 digits — only 12 are kept"):
        _expect_typed(part_b_page, 0, part_b_aadhaar_max_length_case)


# ---------------------------------------------------------------------------
# TC-89  Error shown when Aadhaar is left blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-89")
@allure.story(STORY)
@allure.title("TC-89: Error shown when Aadhaar number is left blank")
def test_tc89_aadhaar_blank(part_b_page: PartBPage, logged_in_part_b_page, part_b_aadhaar_blank_data: KeyPersonData):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with Aadhaar empty
    Then  the save is rejected with "Aadhaar Card Number is mandatory."

    Notion: KAN-TC-89 | data: aadhaar_blank
    """
    page, user = logged_in_part_b_page
    data = part_b_aadhaar_blank_data

    with allure.step("Fill Director 1 with Aadhaar empty and save"):
        _fill_person(part_b_page, 0, data)
        part_b_page.click_submit()

    with allure.step("Verify the Aadhaar error"):
        _expect_server_errors(part_b_page, page, data.expected_error)


# ---------------------------------------------------------------------------
# TC-90  Error shown when Aadhaar has fewer than 12 digits
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-90")
@allure.story(STORY)
@allure.title("TC-90: Error shown when Aadhaar number has fewer than 12 digits")
def test_tc90_aadhaar_too_short(part_b_page: PartBPage, logged_in_part_b_page, part_b_aadhaar_short_data: KeyPersonData):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with an 8-digit Aadhaar
    Then  the save is rejected with "Aadhaar must be exactly 12 digits."

    Notion: KAN-TC-90 | data: aadhaar_too_short
    """
    page, user = logged_in_part_b_page
    data = part_b_aadhaar_short_data

    with allure.step(f"Fill Director 1 with Aadhaar '{data.aadhaar}' and save"):
        _fill_person(part_b_page, 0, data)
        expect(part_b_page.aadhaar_input(0)).to_have_value(data.aadhaar)
        part_b_page.click_submit()

    with allure.step("Verify the Aadhaar length error"):
        _expect_server_errors(part_b_page, page, data.expected_error)


# ---------------------------------------------------------------------------
# TC-91  Error shown when Aadhaar starts with 0 or 1
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-91")
@allure.story(STORY)
@allure.title("TC-91: Error shown when Aadhaar number starts with 0 or 1")
def test_tc91_aadhaar_starts_with_0_or_1(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_aadhaar_prefix_data: KeyPersonData
):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with an Aadhaar starting with 0, then one starting with 1
    Then  each save is rejected with "Aadhaar cannot start with 0 or 1."

    Notion: KAN-TC-91 | data: aadhaar_starts_with_0_or_1
    """
    page, user = logged_in_part_b_page
    data = part_b_aadhaar_prefix_data
    _fill_person(part_b_page, 0, data)

    for aadhaar in data.invalid_values:
        with allure.step(f"Save with Aadhaar '{aadhaar}'"):
            part_b_page.fill_aadhaar(0, aadhaar)
            part_b_page.click_submit()

        with allure.step("Verify the Aadhaar prefix error"):
            _expect_server_errors(part_b_page, page, data.expected_error)


# ---------------------------------------------------------------------------
# TC-92  Aadhaar does not accept non-numeric characters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-92")
@allure.story(STORY)
@allure.title("TC-92: Aadhaar field does not accept non-numeric characters")
def test_tc92_aadhaar_digits_only(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_aadhaar_typed_cases: list[TypedInput]
):
    """
    Given I am on Part B
    When  I type letters, symbols and a mixed value into Aadhaar
    Then  everything except digits is removed immediately

    Notion: KAN-TC-92 | KAN-19 EC-2 | data: aadhaar_typed_cases
    """
    page, user = logged_in_part_b_page

    for case in part_b_aadhaar_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            _expect_typed(part_b_page, 0, case)


# ---------------------------------------------------------------------------
# TC-93  Passport hidden when nationality is Indian
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-93")
@allure.story(STORY)
@allure.title("TC-93: Passport Number field is hidden when nationality is Indian")
def test_tc93_passport_hidden_for_indian(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given I am on Part B
    When  I look at Nationality
    Then  it offers "Indian" and "Foreign National", with Indian selected
    And   no Passport Number field is shown

    Notion: KAN-TC-93 | KAN-19 AC-6
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify the Nationality options and default"):
        expect(part_b_page.nationality_options(0)).to_have_text(list(PartBPage.NATIONALITY_LABELS))
        expect(part_b_page.nationality_select(0)).to_have_value("Indian")

    with allure.step("Verify Passport Number is hidden"):
        expect(part_b_page.passport_wrapper(0)).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-94  Passport appears and is mandatory for a foreign national
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-94")
@allure.story(STORY)
@allure.title("TC-94: Passport Number field appears and is mandatory for a foreign national")
def test_tc94_passport_mandatory_for_foreign_national(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_foreign_national_data: KeyPersonData
):
    """
    Given every other mandatory field of Director 1 is valid
    When  I select "Foreign National" and save without a passport
    Then  "Passport Number *" is shown and the save is rejected with
          "Passport is mandatory for foreign nationals."
    And   a passport typed in lower case is upper-cased and limited to 20 characters

    Notion: KAN-TC-94 | KAN-19 AC-6 | data: foreign_national
    """
    page, user = logged_in_part_b_page
    data = part_b_foreign_national_data

    with allure.step("Select Foreign National"):
        part_b_page.select_nationality(0, data.nationality)
        expect(part_b_page.passport_wrapper(0)).to_be_visible()
        expect(part_b_page.passport_wrapper(0)).to_contain_text("Passport Number *")

    with allure.step("Fill every other field, leave Passport Number blank and save"):
        _fill_person(part_b_page, 0, KeyPersonData(**{**data.__dict__, "passport": ""}))
        part_b_page.click_submit()

    with allure.step("Verify the passport error"):
        _expect_server_errors(part_b_page, page, data.expected_error)

    with allure.step(f"Enter '{data.passport}' — shown upper-cased"):
        part_b_page.select_nationality(0, data.nationality)
        part_b_page.fill_passport(0, data.passport)
        expect(part_b_page.passport_input(0)).to_have_value(data.passport.upper())

    with allure.step("Type 21 characters — only 20 are kept"):
        too_long = data.invalid_values[0]
        part_b_page.type_key_by_key(part_b_page.passport_input(0), too_long)
        expect(part_b_page.passport_input(0)).to_have_value(too_long[:20])


# ---------------------------------------------------------------------------
# TC-95  Changing nationality back to Indian hides and clears the passport
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-95")
@allure.story(STORY)
@allure.title("TC-95: Changing nationality back to Indian hides and clears the Passport field")
def test_tc95_passport_cleared_when_back_to_indian(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_passport_cleared_data: KeyPersonData
):
    """
    Given I selected Foreign National and entered a passport number
    When  I change Nationality back to Indian, then to Foreign National again
    Then  the Passport field is hidden, and comes back empty

    Notion: KAN-TC-95 | KAN-19 EC-4 | data: passport_cleared_for_indian
    """
    page, user = logged_in_part_b_page
    data = part_b_passport_cleared_data

    with allure.step("Select Foreign National and enter a passport number"):
        part_b_page.select_nationality(0, data.nationality)
        part_b_page.fill_passport(0, data.passport)
        expect(part_b_page.passport_input(0)).to_have_value(data.passport)

    with allure.step("Change Nationality back to Indian"):
        part_b_page.select_nationality(0, "Indian")
        expect(part_b_page.passport_wrapper(0)).to_be_hidden()

    with allure.step("Select Foreign National again — the passport is empty"):
        part_b_page.select_nationality(0, data.nationality)
        expect(part_b_page.passport_input(0)).to_be_visible()
        expect(part_b_page.passport_input(0)).to_have_value("")


# ---------------------------------------------------------------------------
# TC-96  Residential Address accepts a valid address
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-96")
@allure.story(STORY)
@allure.title("TC-96: Residential Address accepts a valid address of sufficient length")
def test_tc96_address_accepts_valid_address(part_b_page: PartBPage, logged_in_part_b_page, part_b_valid_data: KeyPersonData):
    """
    Given I am on Part B
    When  I enter a complete residential address and leave the field
    Then  the address is kept as entered

    Notion: KAN-TC-96 | data: valid_director
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify the placeholder"):
        expect(part_b_page.address_input(0)).to_have_attribute(
            "placeholder", "House no., Street, Locality, City, State — PIN Code"
        )

    with allure.step("Enter a complete address"):
        part_b_page.fill_address(0, part_b_valid_data.address)
        expect(part_b_page.address_input(0)).to_have_value(part_b_valid_data.address)


# ---------------------------------------------------------------------------
# TC-97  Error shown when Residential Address is blank or too short
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-97")
@allure.story(STORY)
@allure.title("TC-97: Error shown when Residential Address is blank or fewer than 10 characters")
def test_tc97_address_blank_or_too_short(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_address_invalid_data: KeyPersonData
):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with the address empty, then with "12 MG Rd"
    Then  the saves are rejected with "Residential address is required." and
          "Address is too short (minimum 10 characters)."

    Notion: KAN-TC-97 | data: address_blank_then_short
    """
    page, user = logged_in_part_b_page
    data = part_b_address_invalid_data

    with allure.step("Save with the address empty"):
        _fill_person(part_b_page, 0, data)
        part_b_page.click_submit()
        _expect_server_errors(part_b_page, page, data.expected_error)

    with allure.step(f"Save with the address '{data.invalid_values[0]}'"):
        part_b_page.fill_address(0, data.invalid_values[0])
        part_b_page.click_submit()
        _expect_server_errors(part_b_page, page, PartBPage.ADDRESS_LENGTH_ERROR)


# ---------------------------------------------------------------------------
# TC-102  Personal Email ID accepts a valid email
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-102")
@allure.story(STORY)
@allure.title("TC-102: Personal Email ID accepts a valid email")
def test_tc102_personal_email_accepts_valid_email(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_personal_email_data: KeyPersonData
):
    """
    Given I am on Part B
    When  I look at Personal Email ID and enter a valid email
    Then  the field is optional, shows its placeholder and hint, and keeps the email

    Notion: KAN-TC-102 | data: with_personal_email
    """
    page, user = logged_in_part_b_page
    data = part_b_personal_email_data

    with allure.step("Verify the field is optional, with placeholder and hint"):
        expect(part_b_page.personal_email_input(0)).not_to_have_attribute("required", "")
        expect(part_b_page.personal_email_input(0)).to_have_attribute("placeholder", "Personal email (not official)")
        expect(part_b_page.personal_email_hint(0)).to_have_text(PartBPage.PERSONAL_EMAIL_HINT)

    with allure.step(f"Enter '{data.email}'"):
        part_b_page.fill_personal_email(0, data.email)
        expect(part_b_page.personal_email_input(0)).to_have_value(data.email)
        assert part_b_page.personal_email_input(0).evaluate("e => e.validity.valid")


# ---------------------------------------------------------------------------
# TC-103  Personal Email ID optional but must be valid when entered — saves Part B
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-103")
@allure.story(STORY)
@allure.title("TC-103: Personal Email ID is optional but must be a valid email when entered")
def test_tc103_personal_email_optional_but_valid(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_malformed_email_data: KeyPersonData
):
    """
    Given every mandatory field of Director 1 is valid
    When  I save with a malformed email, then with the email left blank
    Then  the browser blocks each malformed email
    And   with the email blank Part B saves (no email error)

    Malformed emails are checked first: the blank-email save succeeds and leaves Part B.

    Notion: KAN-TC-103 | data: malformed_emails
    """
    page, user = logged_in_part_b_page
    data = part_b_malformed_email_data
    _fill_person(part_b_page, 0, data)

    for email in data.invalid_values:
        with allure.step(f"Save with Personal Email ID '{email}' — the browser blocks it"):
            part_b_page.fill_personal_email(0, email)
            part_b_page.click_submit()
            _expect_blocked_by_browser(part_b_page, page, part_b_page.personal_email_input(0), "typeMismatch")

    with allure.step("Clear Personal Email ID and save"):
        part_b_page.fill_personal_email(0, "")
        part_b_page.click_submit()

    with allure.step("Verify Part B saved without an email error"):
        _expect_part_b_saved(page, user)


# ---------------------------------------------------------------------------
# TC-104  Mobile accepts a valid number with the default country code
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-104")
@allure.story(STORY)
@allure.title("TC-104: Mobile Number field accepts a valid number with country code")
def test_tc104_mobile_accepts_valid_number(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_mobile_max_length_case: TypedInput
):
    """
    Given I am on Part B
    When  I enter a valid mobile number, then an 11-digit one
    Then  the country code is +91, the number is valid, and only 10 digits are kept

    Notion: KAN-TC-104 | data: mobile_max_length_case
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify the country code is +91"):
        expect(part_b_page.country_code_select(0)).to_have_value("+91")

    with allure.step("Enter a valid mobile number"):
        mobile = PartBFactory.valid_director().mobile
        part_b_page.fill_mobile(0, mobile)
        expect(part_b_page.mobile_input(0)).to_have_value(mobile)
        assert part_b_page.mobile_input(0).evaluate("e => e.validity.valid")

    with allure.step("Enter 11 digits — only 10 are kept"):
        _expect_typed(part_b_page, 0, part_b_mobile_max_length_case)


# ---------------------------------------------------------------------------
# TC-105  Error shown when Mobile Number is left blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-105")
@allure.story(STORY)
@allure.title("TC-105: Error shown when Mobile Number is left blank")
def test_tc105_mobile_blank(part_b_page: PartBPage, logged_in_part_b_page, part_b_mobile_blank_data: KeyPersonData):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with Mobile Number empty
    Then  the save is rejected with "Mobile number is required."

    Notion: KAN-TC-105 | data: mobile_blank
    """
    page, user = logged_in_part_b_page
    data = part_b_mobile_blank_data

    with allure.step("Fill Director 1 with Mobile empty and save"):
        _fill_person(part_b_page, 0, data)
        part_b_page.click_submit()

    with allure.step("Verify the mobile error"):
        _expect_server_errors(part_b_page, page, data.expected_error)


# ---------------------------------------------------------------------------
# TC-106  Mobile Number must start with 6, 7, 8 or 9
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-106")
@allure.story(STORY)
@allure.title("TC-106: Mobile Number must start with 6, 7, 8 or 9")
def test_tc106_mobile_must_start_with_6_to_9(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_mobile_wrong_format_data: KeyPersonData
):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with a mobile starting with 0, starting with 5, and with 5 digits
    Then  the browser blocks each one with "10-digit mobile number starting with 6, 7, 8 or 9"

    Notion: KAN-TC-106 | data: mobile_wrong_format
    """
    page, user = logged_in_part_b_page
    data = part_b_mobile_wrong_format_data
    _fill_person(part_b_page, 0, data)

    with allure.step("Verify the mobile field's format hint"):
        expect(part_b_page.mobile_input(0)).to_have_attribute("title", PartBPage.MOBILE_PATTERN_TITLE)

    for mobile in data.invalid_values:
        with allure.step(f"Save with mobile '{mobile}' — the browser blocks it"):
            part_b_page.fill_mobile(0, mobile)
            part_b_page.click_submit()
            _expect_blocked_by_browser(part_b_page, page, part_b_page.mobile_input(0), "patternMismatch")


# ---------------------------------------------------------------------------
# TC-107  Mobile rejects non-numeric characters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-107")
@allure.story(STORY)
@allure.title("TC-107: Mobile Number field rejects non-numeric characters in real-time")
def test_tc107_mobile_digits_only(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_mobile_typed_cases: list[TypedInput]
):
    """
    Given I am on Part B
    When  I type a letter, a symbol, then digits into Mobile Number
    Then  the letter and symbol are removed and the digits are kept

    Notion: KAN-TC-107 | data: mobile_typed_cases
    """
    page, user = logged_in_part_b_page

    for case in part_b_mobile_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            _expect_typed(part_b_page, 0, case)


# ---------------------------------------------------------------------------
# TC-108  First entry's country code is +91 and does not follow nationality
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-108")
@allure.story(STORY)
@allure.title("TC-108: First entry's mobile country code is +91 and does not follow nationality")
def test_tc108_first_entry_country_code(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given I am on Part B
    When  I open Director 1's country codes and change Nationality to Foreign National
    Then  +91 is the only option and stays selected

    Notion: KAN-TC-108 | KAN-19 EC-8
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify Director 1 offers only +91"):
        expect(part_b_page.country_code_options(0)).to_have_count(1)
        expect(part_b_page.country_code_select(0)).to_have_value("+91")

    with allure.step("Change Nationality to Foreign National — the code stays +91"):
        part_b_page.select_nationality(0, "Foreign")
        expect(part_b_page.country_code_select(0)).to_have_value("+91")


# ---------------------------------------------------------------------------
# TC-109  "Add Another Director" appends a new blank entry
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-109")
@allure.story(STORY)
@allure.title("TC-109: Clicking \"Add Another Director\" appends a new blank entry")
def test_tc109_add_another_director(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given only Director 1 is shown
    When  I click "Add Another Director" twice
    Then  two blank cards with the full field set and a Remove button are appended,
          titled in sequence

    Numbers continue from the page's counter, so titles are checked against each
    card's index rather than hard-coded "Director 2" / "Director 3".

    Notion: KAN-TC-109 | KAN-19 AC-7
    """
    page, user = logged_in_part_b_page

    with allure.step("Click 'Add Another Director'"):
        second = _add_person(part_b_page)

    with allure.step("Verify the new card is blank with every field and a Remove button"):
        expect(part_b_page.person_cards).to_have_count(2)
        expect(part_b_page.person_title(second)).to_have_text(f"{LABEL} {second + 1}")
        for field in (part_b_page.full_name_input, part_b_page.personal_email_input, part_b_page.din_input,
                      part_b_page.pan_input, part_b_page.aadhaar_input, part_b_page.mobile_input,
                      part_b_page.address_input):
            expect(field(second)).to_be_visible()
            expect(field(second)).to_have_value("")
        expect(part_b_page.nationality_select(second)).to_have_value("Indian")
        expect(part_b_page.passport_wrapper(second)).to_be_hidden()
        expect(part_b_page.remove_person_button(second)).to_be_visible()

    with allure.step("Click 'Add Another Director' again"):
        third = _add_person(part_b_page)

    with allure.step("Verify the third card follows in sequence"):
        expect(part_b_page.person_cards).to_have_count(3)
        assert third == second + 1
        expect(part_b_page.person_title(third)).to_have_text(f"{LABEL} {third + 1}")


# ---------------------------------------------------------------------------
# TC-110  Removing an added entry removes only that entry
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-110")
@allure.story(STORY)
@allure.title("TC-110: Removing an added entry removes only that entry")
def test_tc110_remove_added_entry(part_b_page: PartBPage, logged_in_part_b_page, part_b_valid_data: KeyPersonData):
    """
    Given Director 1 plus two added Directors
    When  I remove the middle one and add another
    Then  only that card is removed, the others keep their data and titles
    And   the new card's number keeps counting up (no renumbering)

    Notion: KAN-TC-110 | KAN-19 AC-8, EC-6 | data: valid_director
    """
    page, user = logged_in_part_b_page

    with allure.step("Add two Directors and name the last one"):
        middle = _add_person(part_b_page)
        last = _add_person(part_b_page)
        part_b_page.fill_full_name(last, part_b_valid_data.full_name)

    with allure.step("Remove the middle Director"):
        part_b_page.click_remove_person(middle)

    with allure.step("Verify only that card was removed and nothing was renumbered"):
        assert part_b_page.person_indexes() == [0, last]
        expect(part_b_page.person_title(0)).to_have_text(f"{LABEL} 1")
        expect(part_b_page.person_title(last)).to_have_text(f"{LABEL} {last + 1}")
        expect(part_b_page.full_name_input(last)).to_have_value(part_b_valid_data.full_name)

    with allure.step("Add another Director — its number keeps counting up"):
        newest = _add_person(part_b_page)
        expect(part_b_page.person_title(newest)).to_have_text(f"{LABEL} {last + 2}")


# ---------------------------------------------------------------------------
# TC-111  The first key person entry cannot be removed
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-111")
@allure.story(STORY)
@allure.title("TC-111: The first key person entry cannot be removed")
def test_tc111_first_entry_cannot_be_removed(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given only Director 1 is shown
    When  I look for its Remove button, then add and remove a Director
    Then  Director 1 never has a Remove button and always remains

    Notion: KAN-TC-111 | KAN-19 AC-4, EC-5
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify Director 1 has no Remove button"):
        expect(part_b_page.person_cards).to_have_count(1)
        expect(part_b_page.remove_person_button(0)).to_have_count(0)

    with allure.step("Add a Director, then remove it"):
        added = _add_person(part_b_page)
        part_b_page.click_remove_person(added)

    with allure.step("Verify only Director 1 remains, still without a Remove button"):
        expect(part_b_page.person_cards).to_have_count(1)
        expect(part_b_page.person_title(0)).to_have_text(f"{LABEL} 1")
        expect(part_b_page.remove_person_button(0)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-112  Save blocked when two entries share an Aadhaar number
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-112")
@allure.story(STORY)
@allure.title("TC-112: Save blocked when the same Aadhaar number is used for two different entries")
def test_tc112_duplicate_aadhaar_blocked(
    part_b_page: PartBPage, logged_in_part_b_page,
    part_b_valid_data: KeyPersonData, part_b_duplicate_aadhaar_data: KeyPersonData,
):
    """
    Given Director 1 and Director 2 are valid but share an Aadhaar number
    When  I save
    Then  the save is rejected with the duplicate-Aadhaar error on Director 2

    Known defect (28 Oct 2026): the server accepts the duplicate and saves Part B.

    Notion: KAN-TC-112 | KAN-19 EC-1 | data: duplicate_aadhaar_director
    """
    page, user = logged_in_part_b_page

    with allure.step("Fill Director 1 and a second Director with the same Aadhaar"):
        _fill_person(part_b_page, 0, part_b_valid_data)
        second = _add_person(part_b_page)
        _fill_person(part_b_page, second, part_b_duplicate_aadhaar_data)

    with allure.step("Click 'Save Part B & Continue'"):
        part_b_page.click_submit()
        page.wait_for_load_state("networkidle")
        if PART_C_URL.search(page.url):
            TestStateStore().mark_form_step_status(username=user.username, step="part_b", status="completed")

    with allure.step("Verify the save is rejected for the duplicate Aadhaar"):
        _expect_server_errors(part_b_page, page, part_b_duplicate_aadhaar_data.expected_error, person=2)


# ---------------------------------------------------------------------------
# TC-113  Part B is saved and the wizard continues — saves Part B
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-113")
@allure.story(STORY)
@allure.title("TC-113: Part B is saved and the wizard continues after a valid save")
def test_tc113_valid_save_continues_to_part_c(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_valid_data: KeyPersonData
):
    """
    Given Director 1 has every mandatory field valid
    When  I click "Save Part B & Continue"
    Then  Part B is saved, I land on Part C and Part B shows ✓ in the progress bar

    Notion: KAN-TC-113 | KAN-19 AC-9 | data: valid_director
    """
    page, user = logged_in_part_b_page

    with allure.step("Fill every mandatory field of Director 1"):
        _fill_person(part_b_page, 0, part_b_valid_data)

    with allure.step("Click 'Save Part B & Continue'"):
        part_b_page.click_submit()

    with allure.step("Verify Part B is saved and Part C opens"):
        _expect_part_b_saved(page, user)

    with allure.step("Verify Part B shows ✓ in the progress bar"):
        expect(part_b_page.completed_step_link("Part B")).to_be_visible()
        expect(part_b_page.completed_step_link("Part B")).to_contain_text("✓")


# ---------------------------------------------------------------------------
# TC-114  Saved Part B data is restored — saves Part B
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-114")
@allure.story(STORY)
@allure.title("TC-114: Saved Part B data is restored when the user returns to Part B")
def test_tc114_saved_data_restored(
    part_b_page: PartBPage, logged_in_part_b_page,
    part_b_valid_data: KeyPersonData, part_b_second_valid_data: KeyPersonData,
):
    """
    Given I saved Part B with two Directors
    When  I reopen Part B, go to Part A, and open Part B again
    Then  both Directors are shown with every value exactly as saved

    Notion: KAN-TC-114 | KAN-19 AC-10 | data: valid_director, second_valid_director
    """
    page, user = logged_in_part_b_page
    people = (part_b_valid_data, part_b_second_valid_data)

    with allure.step("Fill two Directors and save"):
        _fill_person(part_b_page, 0, people[0])
        _fill_person(part_b_page, _add_person(part_b_page), people[1])
        part_b_page.click_submit()
        _expect_part_b_saved(page, user)

    for visit in ("Reopen Part B", "Go to Part A, then open Part B again"):
        with allure.step(visit):
            if visit.startswith("Go to"):
                part_b_page.click_back_to_part_a()
                page.wait_for_load_state("networkidle")
            part_b_page.open()

        with allure.step("Verify both Directors are restored"):
            expect(part_b_page.person_cards).to_have_count(2)
            for index, person in enumerate(people):
                expect(part_b_page.full_name_input(index)).to_have_value(person.full_name)
                expect(part_b_page.din_input(index)).to_have_value(person.din)
                expect(part_b_page.pan_input(index)).to_have_value(person.pan)
                expect(part_b_page.aadhaar_input(index)).to_have_value(person.aadhaar)
                expect(part_b_page.mobile_input(index)).to_have_value(person.mobile)
                expect(part_b_page.address_input(index)).to_have_value(person.address)


# ---------------------------------------------------------------------------
# TC-119  Heading, banners and field hints
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-119")
@allure.story(STORY)
@allure.title("TC-119: Part B heading, banners and field hints are displayed correctly")
def test_tc119_static_texts(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given I am on Part B
    When  I look at the page
    Then  the heading, subtitle, back link, deadline banner, progress bar and
          field hints show the expected texts

    Notion: KAN-TC-119
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify the heading, subtitle and '← Part A' link"):
        expect(part_b_page.title).to_have_text("Step 2 — Part B: Key Persons")
        expect(part_b_page.sub_title).to_have_text("Nationality verified via Aadhaar / Passport")
        expect(part_b_page.back_to_part_a_link).to_be_visible()

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(part_b_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(part_b_page.save_and_logout_link).to_be_visible()

    with allure.step("Verify every progress-bar stage"):
        # Saved steps (Part A, and Part B once saved) are '✓' links; Register's ✓ is not a link.
        for label in ("Register", "Part C", "Part F", "Documents", "Photos", "Declaration", "Preview", "Payment"):
            expect(part_b_page.progress_step(label)).to_be_visible()
        expect(part_b_page.completed_step_link("Part A")).to_be_visible()
        expect(part_b_page.progress_step("Part B").or_(part_b_page.completed_step_link("Part B"))).to_be_visible()

    with allure.step("Verify the field hints"):
        expect(part_b_page.aadhaar_hint(0)).to_have_text(PartBPage.AADHAAR_HINT)
        expect(part_b_page.personal_email_hint(0)).to_have_text(PartBPage.PERSONAL_EMAIL_HINT)


# ---------------------------------------------------------------------------
# TC-437  DIN / DPIN and PAN shown for company agency types
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-437")
@allure.story(STORY)
@allure.title("TC-437: DIN / DPIN and PAN fields are shown for company agency types")
def test_tc437_din_pan_shown_for_company(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given Part A is saved as Private Limited Company
    When  I look at Director 1 and add Director 2
    Then  both have DIN / DPIN and PAN Number, and there is no address-proof upload

    Notion: KAN-TC-437 | KAN-19 AC-3
    """
    page, user = logged_in_part_b_page

    with allure.step("Verify DIN / DPIN and PAN on Director 1"):
        expect(part_b_page.din_input(0)).to_have_attribute("placeholder", "8-digit DIN / DPIN")
        expect(part_b_page.pan_input(0)).to_have_attribute("placeholder", "e.g. ABCDE1234F")
        expect(part_b_page.person_card(0)).to_contain_text("DIN / DPIN *")
        expect(part_b_page.person_card(0)).to_contain_text("PAN Number *")

    with allure.step("Verify there is no address-proof upload"):
        expect(part_b_page.address_proof_input(0)).to_have_count(0)

    with allure.step("Add Director 2 — it has DIN / DPIN and PAN too"):
        added = _add_person(part_b_page)
        expect(part_b_page.din_input(added)).to_be_visible()
        expect(part_b_page.pan_input(added)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-438  DIN / DPIN accepts digits only, up to 8
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-438")
@allure.story(STORY)
@allure.title("TC-438: DIN / DPIN accepts digits only, up to 8")
def test_tc438_din_digits_only(part_b_page: PartBPage, logged_in_part_b_page, part_b_din_typed_cases: list[TypedInput]):
    """
    Given I am on Part B
    When  I type letters and symbols, 8 digits, then 9 digits into DIN / DPIN
    Then  non-digits are removed and only 8 digits are kept

    Notion: KAN-TC-438 | data: din_typed_cases
    """
    page, user = logged_in_part_b_page

    for case in part_b_din_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            _expect_typed(part_b_page, 0, case)


# ---------------------------------------------------------------------------
# TC-439  Error shown when DIN / DPIN or PAN is left blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-439")
@allure.story(STORY)
@allure.title("TC-439: Error shown when DIN / DPIN or PAN is left blank")
def test_tc439_din_pan_blank(part_b_page: PartBPage, logged_in_part_b_page, part_b_din_pan_blank_data: KeyPersonData):
    """
    Given every other mandatory field of Director 1 is valid
    When  I save with DIN / DPIN and PAN empty, then with a 5-digit DIN
    Then  the saves are rejected with the DIN / DPIN and PAN required errors,
          then "DIN/DPIN must be 8 digits."

    Notion: KAN-TC-439 | data: din_and_pan_blank
    """
    page, user = logged_in_part_b_page
    data = part_b_din_pan_blank_data

    with allure.step("Save with DIN / DPIN and PAN empty"):
        _fill_person(part_b_page, 0, data)
        part_b_page.click_submit()
        _expect_server_errors(part_b_page, page, PartBPage.DIN_REQUIRED_ERROR, PartBPage.PAN_REQUIRED_ERROR)

    with allure.step(f"Save with DIN / DPIN '{data.invalid_values[0]}'"):
        part_b_page.fill_din(0, data.invalid_values[0])
        part_b_page.fill_pan(0, PartBFactory.valid_director().pan)
        part_b_page.click_submit()
        _expect_server_errors(part_b_page, page, data.expected_error)


# ---------------------------------------------------------------------------
# TC-440  PAN upper-cased and limited to 10 letters and digits
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-440")
@allure.story(STORY)
@allure.title("TC-440: PAN is converted to upper case and limited to 10 letters and digits")
def test_tc440_pan_normalised(part_b_page: PartBPage, logged_in_part_b_page, part_b_pan_typed_cases: list[TypedInput]):
    """
    Given I am on Part B
    When  I type a lower-case PAN, one with spaces and symbols, and 11 characters
    Then  the field shows the upper-case 10-character PAN each time

    Notion: KAN-TC-440 | data: pan_typed_cases
    """
    page, user = logged_in_part_b_page

    for case in part_b_pan_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            _expect_typed(part_b_page, 0, case)


# ---------------------------------------------------------------------------
# TC-441  Added entries offer additional mobile country codes
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-441")
@allure.story(STORY)
@allure.title("TC-441: Added entries offer additional mobile country codes")
def test_tc441_added_entries_country_codes(part_b_page: PartBPage, logged_in_part_b_page):
    """
    Given only Director 1 is shown
    When  I add a Director and open its country codes
    Then  it offers +91, +1, +44, +61, +971 and +65 with +91 selected
    And   Director 1 still offers +91 only

    Notion: KAN-TC-441 | KAN-19 EC-7
    """
    page, user = logged_in_part_b_page

    with allure.step("Add a Director"):
        added = _add_person(part_b_page)

    with allure.step("Verify the added Director's country codes"):
        codes = part_b_page.country_code_options(added).evaluate_all("els => els.map(e => e.value)")
        assert tuple(codes) == PartBPage.COUNTRY_CODES, f"Country codes: {codes}"
        expect(part_b_page.country_code_select(added)).to_have_value("+91")

    with allure.step("Verify Director 1 still offers +91 only"):
        expect(part_b_page.country_code_options(0)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-442  Personal email must differ from the official email — saves Part B
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-442")
@allure.story(STORY)
@allure.title("TC-442: Personal Email ID must differ from the official agency email")
def test_tc442_personal_email_differs_from_official(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_personal_email_data: KeyPersonData
):
    """
    Given every mandatory field of Director 1 is valid
    When  I save with the agency's official email as Personal Email ID, then with another email
    Then  the first save is rejected with "Personal email must differ from the official agency email."
    And   the second save succeeds

    Notion: KAN-TC-442 | data: with_personal_email (official email from the state store)
    """
    page, user = logged_in_part_b_page
    data = part_b_personal_email_data

    with allure.step("Save with the official agency email"):
        _fill_person(part_b_page, 0, KeyPersonData(**{**data.__dict__, "email": user.email}))
        part_b_page.click_submit()
        _expect_server_errors(part_b_page, page, PartBPage.EMAIL_SAME_AS_OFFICIAL_ERROR)

    with allure.step(f"Save with '{data.email}'"):
        part_b_page.fill_personal_email(0, data.email)
        part_b_page.click_submit()

    with allure.step("Verify Part B saved"):
        _expect_part_b_saved(page, user)


# ---------------------------------------------------------------------------
# TC-443  "← Part A" and "Save & Log out" leave without a prompt
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-443")
@allure.story(STORY)
@allure.title("TC-443: \"← Part A\" and \"Save & Log out\" leave Part B without a prompt")
def test_tc443_exit_links_without_prompt(
    part_b_page: PartBPage, logged_in_part_b_page, part_b_unsaved_name_data: KeyPersonData
):
    """
    Given I typed a Full Name on Part B without saving
    When  I click "← Part A", reopen Part B, then click "Save & Log out" and log in again
    Then  no dialog is shown, the unsaved name is gone, and saved data is unchanged

    Notion: KAN-TC-443 | data: unsaved_name
    """
    page, user = logged_in_part_b_page
    saved_name = part_b_page.full_name_input(0).input_value()

    with allure.step(f"Type '{part_b_unsaved_name_data.full_name}' without saving and click '← Part A'"):
        part_b_page.fill_full_name(0, part_b_unsaved_name_data.full_name)
        message = part_b_page.click_and_handle_alert(part_b_page.back_to_part_a_link)
        assert message == "", f"Unexpected dialog: {message}"
        page.wait_for_url("**/partA.php*")

    with allure.step("Open Part B again — the unsaved name is not shown"):
        part_b_page.open()
        expect(part_b_page.full_name_input(0)).to_have_value(saved_name)

    with allure.step("Click 'Save & Log out'"):
        message = part_b_page.click_and_handle_alert(part_b_page.save_and_logout_link)
        assert message == "", f"Unexpected dialog: {message}"
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again and open Part B — saved data is unchanged"):
        login = LoginPage(page)
        login.login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        part_b_page.open()
        expect(part_b_page.full_name_input(0)).to_have_value(saved_name)
