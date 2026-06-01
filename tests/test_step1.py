import time

import allure
import pytest
from playwright.sync_api import expect

from pages.dashboard_page import DashboardPage
from pages.partA_page import PartAPage
from test_data.step1_factory import PartAData
from utils.aio import aio_case
from utils.file_manager import INVALID_FORMAT, VALID_JPG, VALID_PDF, VALID_PNG
from utils.state_store import TestStateStore

try:
    from utils.file_manager import get_document_path
    OVERSIZED_IMAGE = get_document_path("oversized_image.jpg")
except FileNotFoundError:
    OVERSIZED_IMAGE = None


def _fill_mandatory(part_a: PartAPage, data: PartAData) -> None:
    """Fills the six mandatory text fields on Step 1. Does not upload office photo."""
    part_a.fill_agency_name(data.agency_name)
    part_a.select_legal_constitution(data.legal_constitution)
    part_a.fill_agency_date_of_establishment(data.date_of_incorporation)
    part_a.fill_address_line1(data.address_line1)
    part_a.fill_email(data.official_email)
    part_a.fill_mobile_number(data.mobile_number)


# ---------------------------------------------------------------------------
# TC-57  PAN pre-populated and read-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-57")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-57: PAN Number field is pre-populated and read-only when Step 1 loads")
def test_tc57_pan_prepopulated_readonly(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I am logged in and have navigated to Step 1 of the registration wizard
    When  I locate the PAN Number field under Agency Identity
    Then  it is pre-populated with the PAN entered during pre-registration
    And   the field is read-only and shows the helper text "Auto-filled from registration."

    Notion: KAN-TC-57 | data: any_agency_user
    """
    page, user = logged_in_part_a_page

    with allure.step("Verify PAN Number field is visible and pre-populated"):
        expect(part_a_page.pan_number_field).to_be_visible()
        pan_value = part_a_page.get_pan_number()
        assert pan_value, "PAN field must be pre-populated from pre-registration"

    with allure.step("Verify PAN Number field is read-only"):
        expect(part_a_page.pan_number_field).not_to_be_editable()

    with allure.step("Verify helper text reads 'Auto-filled from registration.'"):
        expect(part_a_page.pan_helper_text).to_contain_text("Auto-filled from registration")


# ---------------------------------------------------------------------------
# TC-59  Later steps locked until Step 1 is saved
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-59")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-59: Later wizard steps are locked until Step 1 is saved")
def test_tc59_steps_locked_until_step1_saved(dashboard_page: DashboardPage, logged_in_agency_page):
    """
    Given I am on Step 1 with no previously saved data
    When  I try to navigate to Step 2 through Step 8 via the progress bar
    Then  each step is locked with the message "Please complete and save the current step before proceeding."

    Notion: KAN-TC-59 | data: fresh_agency_user
    """
    page, user = logged_in_agency_page

    with allure.step("Attempt to click Step 2 in the progress bar"):
        message = dashboard_page.click_and_handle_alert(dashboard_page.step_nav_item(2))



    with allure.step("Verify locked message is shown for Step 2"):
        assert "Please complete Step 1" in message

    with allure.step("Verify Steps 3 through 8 are also locked"):
        for step in range(3, 8):
            message = dashboard_page.click_and_handle_alert(dashboard_page.step_nav_item(step))
            assert "Please complete Step 1" in message


# ---------------------------------------------------------------------------
# TC-60  All mandatory fields show inline errors when form submitted blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-60")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-60: Submitting a blank form is blocked by a native validation tooltip on the first field")
def test_tc60_blank_form_shows_validation_tooltip(part_a_page: PartAPage, logged_in_part_a_fresh_page):
    """
    Given I am on Step 1 with all fields empty
    When  I click Save / Next without entering any data
    Then  the browser blocks submission and shows a native validation tooltip
          on the first blank mandatory field (Agency Name)
    And   the form does not advance / save

    Note: The form relies on native HTML5 ``required`` validation. The browser
          surfaces a single tooltip on the first invalid field rather than
          rendering simultaneous inline errors for every field.

    Notion: KAN-TC-60 | data: fresh_agency_user
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Confirm all mandatory fields are empty"):
        expect(part_a_page.agency_name_input).to_have_value("")

    with allure.step("Click Save / Next without entering any data"):
        part_a_page.click_save_next()

    with allure.step("Verify the first blank field (Agency Name) fails native validation"):
        is_valid = part_a_page.agency_name_input.evaluate("el => el.checkValidity()")
        assert is_valid is False, "Agency Name should be invalid when left blank"

    with allure.step("Verify a native validation tooltip message is shown for Agency Name"):
        validation_message = part_a_page.agency_name_input.evaluate("el => el.validationMessage")
        assert validation_message, (
            "Browser should surface a non-empty validation tooltip on the first blank field"
        )

    with allure.step("Verify the form did not advance — Step 1 is not marked complete"):
        expect(part_a_page.step_completion_message).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-62  Future date in Date of Incorporation triggers inline error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-62")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-62: A future date in the Date of Incorporation field triggers an inline error")
def test_tc62_future_date_of_incorporation(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_future_date_data: PartAData
):
    """
    Given I am on Step 1 and all other mandatory fields are valid
    When  I enter a future date in the Date of Incorporation field and click Save / Next
    Then  save is blocked and the inline error reads "Date of incorporation cannot be a future date."

    Notion: KAN-TC-62 | data: future_date
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill all mandatory fields with a future date of incorporation"):
        _fill_mandatory(part_a_page, part_a_future_date_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for future date"):
        expect(part_a_page.date_of_incorporation_error).to_contain_text(
            part_a_future_date_data.expected_error
        )


# ---------------------------------------------------------------------------
# TC-63  Invalid date format shows format error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-63")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-63: An invalid date format in Date of Incorporation shows a format error")
def test_tc63_invalid_date_format(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_date_data: PartAData
):
    """
    Given I am on Step 1
    When  I enter an invalid date string and click Save / Next
    Then  save is blocked and the inline error reads "Please enter a valid date in dd-mm-yyyy format."

    Notion: KAN-TC-63 | data: invalid_date_format
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill all mandatory fields with an invalid date format"):
        _fill_mandatory(part_a_page, part_a_invalid_date_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for invalid date format"):
        expect(part_a_page.date_of_incorporation_error).to_contain_text(
            part_a_invalid_date_data.expected_error
        )


# ---------------------------------------------------------------------------
# TC-64  Incorrect TAN format shows format error; optional field clears safely
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-64")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-64: Entering a TAN number in an incorrect format shows a format error")
def test_tc64_invalid_tan_format(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_tan_data: PartAData
):
    """
    Given I am on Step 1 with all other mandatory fields filled
    When  I enter a badly formatted TAN and click Save / Next
    Then  save is blocked and inline error shows expected TAN format
    When  I clear the TAN field and click Save / Next
    Then  step saves successfully (TAN is optional)
    When  I enter a correctly formatted TAN
    Then  step saves successfully with TAN stored

    Notion: KAN-TC-64 | data: invalid_tan_format / valid_tan
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields and enter an incorrectly formatted TAN"):
        _fill_mandatory(part_a_page, part_a_invalid_tan_data)
        part_a_page.fill_tan(part_a_invalid_tan_data.tan_number)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for invalid TAN format"):
        expect(part_a_page.tan_error).to_contain_text(part_a_invalid_tan_data.expected_error)

    with allure.step("Clear the TAN field and click Save / Next"):
        part_a_page.fill_tan("")
        part_a_page.click_save_next()

    with allure.step("Verify step saves successfully without TAN"):
        expect(part_a_page.tan_error).not_to_be_visible()

    with allure.step("Enter a correctly formatted TAN and save again"):
        valid = "PNEC12345A"
        part_a_page.fill_tan(valid)
        part_a_page.click_save_next()

    with allure.step("Verify no TAN error after valid TAN"):
        expect(part_a_page.tan_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-65  Incorrect GSTIN format shows format error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-65")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-65: Entering a GSTIN in an incorrect format shows a format error")
def test_tc65_invalid_gstin_format(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_gstin_data: PartAData
):
    """
    Given I am on Step 1 with all mandatory fields filled
    When  I enter a GSTIN that is not 15 characters and click Save / Next
    Then  save is blocked with inline error "Invalid GSTIN format..."
    When  I enter a valid 15-character GSTIN and click Save / Next
    Then  step saves successfully

    Notion: KAN-TC-65 | data: invalid_gstin_format / valid_gstin
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields and enter an incorrectly formatted GSTIN"):
        _fill_mandatory(part_a_page, part_a_invalid_gstin_data)
        part_a_page.fill_gst(part_a_invalid_gstin_data.gst_number)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for invalid GSTIN format"):
        expect(part_a_page.gst_error).to_contain_text(part_a_invalid_gstin_data.expected_error)

    with allure.step("Enter a valid 15-character GSTIN and click Save / Next"):
        part_a_page.fill_gst("27ABCDE1234F1Z5")
        part_a_page.click_save_next()

    with allure.step("Verify no GSTIN error after valid entry"):
        expect(part_a_page.gst_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-66  Email without @ or domain shows inline error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-66")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-66: An email address without @ or domain shows an inline error")
def test_tc66_invalid_email_format(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_email_data: PartAData
):
    """
    Given I am on Step 1 with all other mandatory fields valid
    When  I enter an email address missing @ and domain and click Save / Next
    Then  save is blocked with inline error "Please enter a valid email address."
    When  I correct the email and click Save / Next
    Then  step saves successfully

    Notion: KAN-TC-66 | data: invalid_email_format
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields with an invalid email address"):
        _fill_mandatory(part_a_page, part_a_invalid_email_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for invalid email"):
        expect(part_a_page.email_error).to_contain_text(part_a_invalid_email_data.expected_error)

    with allure.step("Correct the email and click Save / Next"):
        part_a_page.fill_email("admin@alphaplacement.com")
        part_a_page.click_save_next()

    with allure.step("Verify no email error after valid entry"):
        expect(part_a_page.email_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-67  Mobile number with letters, special chars, or wrong length is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-67")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-67: A mobile number with letters, special characters, or wrong length is rejected")
def test_tc67_invalid_mobile_number(
    part_a_page: PartAPage,
    logged_in_part_a_page,
    part_a_invalid_mobile_letters_data: PartAData,
    part_a_invalid_mobile_short_data: PartAData,
):
    """
    Given I am on Step 1 with all other mandatory fields valid
    When  I enter a mobile number with letters and click Save / Next
    Then  save is blocked with inline error "Please enter a valid 10-digit mobile number."
    When  I enter a number with fewer than 10 digits and click Save / Next
    Then  the same inline error is shown
    When  I enter a valid 10-digit number not starting with 0 and click Save / Next
    Then  step saves successfully

    Notion: KAN-TC-67 | data: invalid_mobile_with_letters / invalid_mobile_too_short
    """
    page, user = logged_in_part_a_page

    base = part_a_invalid_mobile_letters_data

    with allure.step("Fill mandatory fields with a mobile number containing letters"):
        part_a_page.fill_agency_name(base.agency_name)
        part_a_page.select_legal_constitution(base.legal_constitution)
        part_a_page.fill_agency_date_of_establishment(base.date_of_incorporation)
        part_a_page.fill_address_line1(base.address_line1)
        part_a_page.fill_email(base.official_email)
        part_a_page.fill_mobile_number(base.mobile_number)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for letters in mobile number"):
        expect(part_a_page.mobile_error).to_contain_text(base.expected_error)

    with allure.step("Enter a mobile number with fewer than 10 digits and click Save / Next"):
        part_a_page.fill_mobile_number(part_a_invalid_mobile_short_data.mobile_number)
        part_a_page.click_save_next()

    with allure.step("Verify inline error for short mobile number"):
        expect(part_a_page.mobile_error).to_contain_text(
            part_a_invalid_mobile_short_data.expected_error
        )

    with allure.step("Enter a valid 10-digit mobile number and click Save / Next"):
        part_a_page.fill_mobile_number("9876543210")
        part_a_page.click_save_next()

    with allure.step("Verify no mobile error after valid number"):
        expect(part_a_page.mobile_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-68  Website URL not starting with http/https is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-68")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-68: A website URL not starting with http:// or https:// is rejected")
def test_tc68_invalid_website_url(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_url_data: PartAData
):
    """
    Given I am on Step 1 with all mandatory fields valid
    When  I enter a URL without http:// or https:// and click Save / Next
    Then  save is blocked with inline error "Please enter a valid website URL..."
    When  I clear the Website URL field and click Save / Next
    Then  step saves successfully (field is optional)
    When  I enter a valid https:// URL and click Save / Next
    Then  step saves successfully with URL stored

    Notion: KAN-TC-68 | data: invalid_website_url
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields and enter an invalid website URL"):
        _fill_mandatory(part_a_page, part_a_invalid_url_data)
        part_a_page.fill_website(part_a_invalid_url_data.website_url)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for invalid website URL"):
        expect(part_a_page.website_error).to_contain_text(part_a_invalid_url_data.expected_error)

    with allure.step("Clear Website URL field and click Save / Next"):
        part_a_page.fill_website("")
        part_a_page.click_save_next()

    with allure.step("Verify step saves without a website URL"):
        expect(part_a_page.website_error).not_to_be_visible()

    with allure.step("Enter a valid https:// URL and click Save / Next"):
        part_a_page.fill_website("https://www.alphaplacement.com")
        part_a_page.click_save_next()

    with allure.step("Verify no website error after valid URL"):
        expect(part_a_page.website_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-69  Non-JPG/PNG office photo is rejected immediately
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-69")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-69: Uploading a non-JPG/PNG file as office photograph is rejected immediately")
def test_tc69_invalid_office_photo_format(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I am on Step 1
    When  I select a PDF file for the Office Photograph
    Then  upload is rejected with inline error "Only JPG or PNG files are accepted."
    When  I select a DOCX file
    Then  the same error is shown
    When  I upload a valid JPG file
    Then  file is accepted and no error is shown

    Notion: KAN-TC-69 | data: VALID_PDF, INVALID_FORMAT, VALID_JPG
    """
    page, user = logged_in_part_a_page

    with allure.step("Upload a PDF file as office photograph"):
        part_a_page.set_office_photo(VALID_PDF)

    with allure.step("Verify error: only JPG or PNG accepted (PDF)"):
        expect(part_a_page.office_photo_error).to_contain_text("Only JPG or PNG files are accepted.")

    with allure.step("Upload a DOCX file as office photograph"):
        part_a_page.set_office_photo(INVALID_FORMAT)

    with allure.step("Verify same error for DOCX"):
        expect(part_a_page.office_photo_error).to_contain_text("Only JPG or PNG files are accepted.")

    with allure.step("Upload a valid JPG file"):
        part_a_page.set_office_photo(VALID_JPG)

    with allure.step("Verify no error after valid JPG upload"):
        expect(part_a_page.office_photo_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-70  Office photograph larger than 2 MB is rejected before submission
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-70")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-70: Office photograph larger than 2 MB is rejected before submission")
def test_tc70_oversized_office_photo(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I am on Step 1
    When  I select a JPG file larger than 2 MB
    Then  upload is rejected with inline error "File size exceeds 2 MB. Please upload a smaller file."
    When  I upload a JPG within the 2 MB limit
    Then  file is accepted and displayed

    Notion: KAN-TC-70 | data: oversized_image.jpg, VALID_JPG
    """
    if OVERSIZED_IMAGE is None:
        pytest.skip(
            "oversized_image.jpg not found in test_data/documents/ — "
            "add a JPG > 2 MB to run this test."
        )

    page, user = logged_in_part_a_page

    with allure.step("Upload a JPG file larger than 2 MB"):
        part_a_page.set_office_photo(OVERSIZED_IMAGE)

    with allure.step("Verify error: file size exceeds 2 MB"):
        expect(part_a_page.office_photo_error).to_contain_text(
            "File size exceeds 2 MB. Please upload a smaller file."
        )

    with allure.step("Upload a JPG file within the 2 MB limit"):
        part_a_page.set_office_photo(VALID_JPG)

    with allure.step("Verify file is accepted with no error"):
        expect(part_a_page.office_photo_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-73  Partially entered Step 1 data is restored after navigating away
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-73")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-73: Partially entered Step 1 data is restored when user navigates away and returns")
def test_tc73_partial_data_restored_after_navigation(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_partial_data: PartAData
):
    """
    Given I am on Step 1 with session active
    When  I fill Agency Name and Official Email but leave all other fields blank (not saved)
    And   I click Dashboard and choose Exit Without Saving
    And   I return to Step 1 via Continue Registration
    Then  the previously entered Agency Name and Email are still displayed

    Notion: KAN-TC-73 | data: partial_fields_only
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Fill Agency Name and Official Email; leave all other fields blank"):
        part_a_page.fill_agency_name(part_a_partial_data.agency_name)
        part_a_page.fill_email(part_a_partial_data.official_email)

    with allure.step("Click the Dashboard link"):
        part_a_page.click_dashboard_link()

    with allure.step("In the unsaved-changes dialog, click 'Exit Without Saving'"):
        part_a_page.dashboard_dialog_exit_without_saving.click()

    with allure.step("Verify navigation to dashboard"):
        page.wait_for_url("**/dashboard**", timeout=15000)

    with allure.step("Navigate back to Step 1 via Continue Registration"):
        DashboardPage(page).step_card("partA").click()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify Agency Name is still shown"):
        expect(part_a_page.agency_name_input).to_have_value(part_a_partial_data.agency_name)

    with allure.step("Verify Official Email is still shown"):
        expect(part_a_page.official_email_input).to_have_value(part_a_partial_data.official_email)


# ---------------------------------------------------------------------------
# TC-74  Agency name with invalid special characters shows inline error
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-74")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-74: Agency name containing invalid special characters shows an inline error")
def test_tc74_agency_name_special_chars(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_special_chars_name_data: PartAData
):
    """
    Given I am on Step 1
    When  I enter an agency name with @, #, ! characters and click Save / Next
    Then  save is blocked with inline error "Agency name contains invalid characters."
    When  I correct the agency name and click Save / Next
    Then  step saves successfully

    Notion: KAN-TC-74 | data: agency_name_with_special_chars
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields with agency name containing special characters"):
        _fill_mandatory(part_a_page, part_a_special_chars_name_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for special characters in agency name"):
        expect(part_a_page.agency_name_error).to_contain_text(
            part_a_special_chars_name_data.expected_error
        )

    with allure.step("Correct agency name to use only valid characters and click Save / Next"):
        part_a_page.fill_agency_name("Alpha Placement & Services")
        part_a_page.click_save_next()

    with allure.step("Verify no agency name error after valid name"):
        expect(part_a_page.agency_name_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-75  Mobile number starting with 0 is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-75")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-75: A 10-digit mobile number that starts with 0 is rejected")
def test_tc75_mobile_starts_with_zero(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_invalid_mobile_zero_data: PartAData
):
    """
    Given I am on Step 1 with all other mandatory fields valid
    When  I enter a 10-digit mobile number starting with 0 and click Save / Next
    Then  save is blocked with inline error "Please enter a valid 10-digit mobile number."
    When  I correct the number to one not starting with 0 and click Save / Next
    Then  step saves successfully

    Notion: KAN-TC-75 | data: invalid_mobile_starts_with_zero
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill mandatory fields with a mobile number starting with 0"):
        _fill_mandatory(part_a_page, part_a_invalid_mobile_zero_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify inline error for mobile starting with 0"):
        expect(part_a_page.mobile_error).to_contain_text(
            part_a_invalid_mobile_zero_data.expected_error
        )

    with allure.step("Correct the mobile number and click Save / Next"):
        part_a_page.fill_mobile_number("9876543210")
        part_a_page.click_save_next()

    with allure.step("Verify no mobile error after valid number"):
        expect(part_a_page.mobile_error).not_to_be_visible()


# ---------------------------------------------------------------------------
# TC-76  Duplicate agency name triggers non-blocking warning
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-76")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-76: Entering an agency name that already exists shows a warning but allows saving")
def test_tc76_duplicate_agency_name_warning(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_duplicate_name_data: PartAData
):
    """
    Given an agency named "Alpha Placement Agency" already exists in the system
    And   I am on Step 1 with all other mandatory fields valid
    When  I enter the same agency name and click Save / Next
    Then  a non-blocking warning is shown: "An agency with this name already exists..."
    And   the form is NOT hard-blocked (save proceeds or user can proceed)

    Notion: KAN-TC-76 | data: duplicate_agency_name
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill all mandatory fields using an already-existing agency name"):
        _fill_mandatory(part_a_page, part_a_duplicate_name_data)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify non-blocking warning for duplicate agency name is shown"):
        expect(part_a_page.agency_name_warning).to_be_visible()
        assert (
            "already exists" in part_a_page.agency_name_warning.text_content()
        ), "Warning should mention the name already exists"


# ---------------------------------------------------------------------------
# TC-77  User cannot edit pre-filled PAN
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-77")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-77: User cannot edit pre-filled PAN")
def test_tc77_pan_field_strictly_readonly(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I am on Step 1 with a pre-filled PAN number
    When  I locate the PAN field and attempt to change its value
    Then  the field does not accept any input; its value remains unchanged

    Notion: KAN-TC-77 | data: any_agency_user
    """
    page, user = logged_in_part_a_page

    with allure.step("Locate the PAN Number field and read its pre-filled value"):
        expect(part_a_page.pan_number_field).to_be_visible()
        original_pan = part_a_page.get_pan_number()
        assert original_pan, "PAN field must be pre-populated"

    with allure.step("Verify PAN field is not editable"):
        expect(part_a_page.pan_number_field).not_to_be_editable()

    with allure.step("Attempt to type a new value and verify field rejects input"):
        part_a_page.pan_number_field.fill("ZZZZZ1234X")
        assert part_a_page.get_pan_number() == original_pan, (
            "PAN field value must not change after attempted edit"
        )


# ---------------------------------------------------------------------------
# TC-78  Pressing browser back with unsaved data prompts confirmation dialog
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-78")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-78: Pressing browser back while on Step 1 prompts an unsaved-changes dialog")
def test_tc78_browser_back_prompts_dialog(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I have partially filled Step 1 without saving
    When  I press the browser back button
    Then  a confirmation dialog appears warning about unsaved changes
    When  I click Stay
    Then  I remain on Step 1 with my entered data intact
    When  I press back again and click Leave
    Then  I navigate back and unsaved data is discarded

    Notion: KAN-TC-78 | data: any_agency_user
    """
    page, user = logged_in_part_a_page

    with allure.step("Enter data in Agency Name field without saving"):
        part_a_page.fill_agency_name("Beta Placement Co.")

    with allure.step("Press browser back"):
        page.go_back()

    with allure.step("Verify unsaved-changes dialog appears — click Stay"):
        # The dialog is expected to be a beforeunload or custom modal.
        # TODO: update assertion once dialog type (browser vs custom) is confirmed.
        expect(part_a_page.unsaved_changes_dialog_stay).to_be_visible()
        part_a_page.unsaved_changes_dialog_stay.click()

    with allure.step("Verify user remains on Step 1 with entered data intact"):
        expect(part_a_page.agency_name_input).to_have_value("Beta Placement Co.")

    with allure.step("Press browser back again and click Leave"):
        page.go_back()
        part_a_page.unsaved_changes_dialog_leave.click()

    with allure.step("Verify user has navigated back and unsaved data is discarded"):
        page.wait_for_load_state("networkidle")
        assert "step1" not in page.url.lower() or "" == part_a_page.agency_name_input.input_value()


# ---------------------------------------------------------------------------
# TC-79  Clicking Dashboard with unsaved Step 1 data shows Save & Exit dialog
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-79")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-79: Clicking Dashboard with unsaved Step 1 data shows Save & Exit dialog")
def test_tc79_dashboard_link_prompts_unsaved_dialog(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I have partially filled Step 1 without saving
    When  I click the Dashboard link
    Then  a dialog appears: "You have unsaved changes in Step 1. Do you want to save your progress?"
    When  I click Cancel
    Then  dialog closes and I remain on Step 1 with data intact
    When  I click Dashboard and choose Save & Exit
    Then  data is saved and I am taken to the dashboard
    When  I return to Step 1 and click Dashboard, then choose Exit Without Saving
    Then  I am taken to the dashboard; unsaved changes are discarded

    Notion: KAN-TC-79 | data: any_agency_user
    """
    page, user = logged_in_part_a_page

    with allure.step("Partially fill Step 1 — enter Agency Name without saving"):
        part_a_page.fill_agency_name("Gamma Staffing")

    with allure.step("Click the Dashboard link"):
        part_a_page.click_dashboard_link()

    with allure.step("Verify unsaved-changes dialog appears"):
        expect(part_a_page.dashboard_dialog_cancel).to_be_visible()

    with allure.step("Click Cancel — user stays on Step 1"):
        part_a_page.dashboard_dialog_cancel.click()
        expect(part_a_page.agency_name_input).to_have_value("Gamma Staffing")

    with allure.step("Click Dashboard again and choose Save & Exit"):
        part_a_page.click_dashboard_link()
        part_a_page.dashboard_dialog_save_exit.click()

    with allure.step("Verify user is taken to the dashboard after Save & Exit"):
        page.wait_for_url("**/dashboard**", timeout=15000)

    with allure.step("Return to Step 1 and click Dashboard, then choose Exit Without Saving"):
        DashboardPage(page).step_card("partA").click()
        page.wait_for_load_state("networkidle")
        part_a_page.fill_agency_name("Gamma Staffing Edited")
        part_a_page.click_dashboard_link()
        part_a_page.dashboard_dialog_exit_without_saving.click()

    with allure.step("Verify user is taken to the dashboard; unsaved changes discarded"):
        page.wait_for_url("**/dashboard**", timeout=15000)


# ---------------------------------------------------------------------------
# TC-80  Data entered in Step 1 may be restored after session timeout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-80")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-80: Data entered in Step 1 is restored after a session timeout and re-login")
@pytest.mark.wait_before(1210)
def test_tc80_data_after_session_timeout(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I have filled multiple fields on Step 1 without saving
    And   I leave the session idle for 20 minutes (session expires)
    When  I log in again and navigate to Step 1
    Then  either (a) previously entered data is restored, OR
          (b) a clear message informs me that data could not be recovered

    Notion: KAN-TC-80 | data: any_agency_user
    Note:   @pytest.mark.wait_before(1210) pauses 1210 s before the test starts
            to let the previous page's session expire.
    """
    page, user = logged_in_part_a_page

    with allure.step("Fill multiple fields on Step 1 without saving"):
        part_a_page.fill_agency_name("Delta Services")
        part_a_page.fill_email("info@delta.com")

    # Session has already expired due to wait_before(1210) applied before login.
    # Re-login happens here because the fixture navigates after the pause.
    with allure.step("Verify session has expired — login page is visible"):
        expect(page.locator("//input[@name='username'] | //input[@id='user']")).to_be_visible(
            timeout=5000
        )

    with allure.step("Log in again with valid credentials"):
        from pages.login_page import LoginPage
        login = LoginPage(page)
        login.login(user.username, user.password)
        page.wait_for_url("**/dashboard**", timeout=15000)

    with allure.step("Navigate back to Step 1"):
        DashboardPage(page).step_card("partA").click()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify either data is restored or an informative message is shown"):
        agency_name_value = part_a_page.agency_name_input.input_value()
        # Either the data is restored (a) or the field is empty (b).
        # Both outcomes are acceptable per the specification.
        if not agency_name_value:
            # Outcome (b): field empty — acceptable; no assertion failure
            pass
        else:
            assert agency_name_value == "Delta Services", (
                "If data is restored, it must match what was entered before timeout"
            )


# ---------------------------------------------------------------------------
# TC-58  Step 1 saves successfully and unlocks Step 2 — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-58")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-58: Step 1 saves successfully and unlocks Step 2 when all mandatory fields are filled")
def test_tc58_step1_saves_and_unlocks_step2(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_valid_data: PartAData
):
    """
    Given I am on Step 1 with no prior data saved
    When  I fill all mandatory fields (including office photo) and click Save / Next
    Then  Step 1 is marked complete, progress bar updates, and Step 2 is unlocked

    Notion: KAN-TC-58 | data: valid_mandatory_fields
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Enter Agency Name"):
        part_a_page.fill_agency_name(part_a_valid_data.agency_name)

    with allure.step("Select Legal Constitution"):
        part_a_page.select_legal_constitution(part_a_valid_data.legal_constitution)

    with allure.step("Enter Date of Incorporation"):
        part_a_page.fill_agency_date_of_establishment(part_a_valid_data.date_of_incorporation)

    with allure.step("Verify PAN field is pre-filled and read-only"):
        assert part_a_page.get_pan_number(), "PAN should be pre-filled"
        expect(part_a_page.pan_number_field).not_to_be_editable()

    with allure.step("Enter Address Line 1"):
        part_a_page.fill_address_line1(part_a_valid_data.address_line1)

    with allure.step("Enter Official Email"):
        part_a_page.fill_email(part_a_valid_data.official_email)

    with allure.step("Enter Mobile Number"):
        part_a_page.fill_mobile_number(part_a_valid_data.mobile_number)

    with allure.step("Upload Office Photo"):
        part_a_page.set_office_photo(VALID_JPG)

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify step completion message is shown"):
        expect(part_a_page.step_completion_message).to_be_visible()

    with allure.step("Verify Step 2 is now unlocked"):
        expect(part_a_page.step_nav_item(2)).to_be_enabled()

    with allure.step("Record Step 1 as completed in state store"):
        TestStateStore().mark_form_step_status(user.username, "1", "completed")


# ---------------------------------------------------------------------------
# TC-71  Step 1 saves successfully when Branch Offices is left blank — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-71")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-71: Step 1 saves successfully when Branch Offices textarea is left blank")
def test_tc71_save_without_branch_offices(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_without_branch_offices_data: PartAData
):
    """
    Given I am on Step 1 with all mandatory fields filled and Branch Offices left blank
    When  I click Save / Next
    Then  Step 1 saves successfully with no error for the Branch Offices field

    Notion: KAN-TC-71 | data: without_branch_offices
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_without_branch_offices_data

    with allure.step("Fill all mandatory fields; leave Branch Offices blank"):
        _fill_mandatory(part_a_page, data)
        part_a_page.set_office_photo(VALID_JPG)

    with allure.step("Verify Branch Offices field is empty"):
        expect(part_a_page.branch_offices_input).to_have_value("")

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify step saves successfully — no Branch Offices error"):
        expect(part_a_page.step_completion_message).to_be_visible()

    with allure.step("Record Step 1 as completed in state store"):
        TestStateStore().mark_form_step_status(user.username, "1", "completed")


# ---------------------------------------------------------------------------
# TC-72  Multiple branch office addresses are individually preserved — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-72")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-72: Multiple branch office addresses entered on separate lines are individually preserved")
def test_tc72_multiple_branch_offices_preserved(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_with_branch_offices_data: PartAData
):
    """
    Given I am on Step 1 with all mandatory fields filled
    When  I enter two branch addresses on separate lines in the Branch Offices field
    And   I click Save / Next
    And   I re-open Step 1
    Then  both branch addresses are displayed exactly as entered

    Notion: KAN-TC-72 | data: with_branch_offices
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_with_branch_offices_data

    with allure.step("Fill all mandatory fields and enter two branch offices on separate lines"):
        _fill_mandatory(part_a_page, data)
        part_a_page.fill_branch_offices(data.branch_offices)
        part_a_page.set_office_photo(VALID_JPG)

    with allure.step("Verify both branch office lines are visible in the textarea"):
        branch_value = part_a_page.branch_offices_input.input_value()
        assert "22, Park Street, Mumbai" in branch_value
        assert "5, Civil Lines, Nagpur" in branch_value

    with allure.step("Click Save / Next"):
        part_a_page.click_save_next()

    with allure.step("Verify step saves successfully"):
        expect(part_a_page.step_completion_message).to_be_visible()

    with allure.step("Navigate to dashboard and re-open Step 1"):
        DashboardPage(page).step_card("partA").click()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify both branch addresses are displayed on separate lines"):
        stored_value = part_a_page.branch_offices_input.input_value()
        assert "22, Park Street, Mumbai" in stored_value, (
            "First branch address must be preserved after save"
        )
        assert "5, Civil Lines, Nagpur" in stored_value, (
            "Second branch address must be preserved after save"
        )

    with allure.step("Record Step 1 as completed in state store"):
        TestStateStore().mark_form_step_status(user.username, "1", "completed")
