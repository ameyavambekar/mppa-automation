import os
import re
from datetime import date

import allure
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partC_page import PART_C_URL, PartCPage
from pages.partF_page import PART_F_URL, PartFPage
from test_data.partF_factory import CertificateData, PartFData, PartFFactory, TypedInput
from utils.aio import aio_case
from utils.file_manager import (CERTIFICATE_JPG, CERTIFICATE_PNG, OVERSIZED_FILE, OVERSIZED_IMAGE,
                                SIGNATURE_JPG, SIGNATURE_PNG, UNSUPPORTED_CERTIFICATE, UNSUPPORTED_SPREADSHEET,
                                VALID_CERTIFICATE)
from utils.state_store import TestStateStore

STORY = "Step 4 - Certificates, Licences & Signature"
ON_PART_F = re.compile(rf"{re.escape(PART_F_URL)}")


def _fill_certificate(part_f: PartFPage, cert: str, data: CertificateData) -> None:
    """Answers Yes, then fills the given number, types the date as digits and chooses the document."""
    part_f.select_certificate(cert, True)
    if data.number is not None:
        part_f.fill_certificate_number(cert, data.number)
    if data.date is not None:
        part_f.type_key_by_key(part_f.certificate_date_input(cert), data.date.typed)
        expect(part_f.certificate_date_input(cert)).to_have_value(data.date.shown)
    if data.document is not None:
        part_f.set_certificate_document(cert, data.document)


def _fill(part_f: PartFPage, data: PartFData) -> None:
    for cert, cert_data in data.certificates.items():
        _fill_certificate(part_f, cert, cert_data)
    if data.signature is not None:
        part_f.set_signature(data.signature)
    if data.place:
        part_f.select_place(data.place)


def _chosen_files(field) -> int:
    return field.evaluate("e => e.files.length")


def _expect_part_f_saved(page, part_f: PartFPage, user) -> None:
    """A successful save stays on Part F with the saved message and "Next: Documents →"."""
    expect(part_f.success_message).to_have_text(PartFPage.SAVED_MESSAGE)
    expect(page).to_have_url(ON_PART_F)
    expect(part_f.next_documents_link).to_be_visible()
    expect(part_f.client_errors).to_be_hidden()
    TestStateStore().mark_form_step_status(username=user.username, step="part_f", status="completed")


def _expect_blocked(page, part_f: PartFPage, *messages: str) -> None:
    """The save was blocked client-side: still on Part F, each message is in the summary box."""
    expect(page).to_have_url(ON_PART_F)
    expect(part_f.client_errors).to_be_visible()
    expect(part_f.client_errors).to_contain_text(PartFPage.ERRORS_HEADING)
    for message in messages:
        expect(part_f.client_errors).to_contain_text(f"• {message}")


def _labels(cert: str) -> tuple[str, str]:
    _, number_label, date_label = PartFPage.CERTIFICATES[cert]
    return number_label, date_label


# ---------------------------------------------------------------------------
# TC-143  All certificates "No" — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-143")
@allure.story(STORY)
@allure.title("TC-143: Part F saves when every certificate is answered \"No\" and a Place is chosen")
def test_tc143_all_no_saves(part_f_page: PartFPage, logged_in_part_f_page, part_f_all_no_data: PartFData):
    """
    Given every certificate is answered No
    When  I choose a Place and click "Save Part F & Continue"
    Then  Part F is saved with no certificate-related error

    Notion: KAN-TC-143 | KAN-21 AC-4, EC-1 | data: all_no
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify all six certificates are No with their fields hidden"):
        for cert in PartFPage.CERTIFICATES:
            expect(part_f_page.certificate_radio(cert, False)).to_be_checked()
            expect(part_f_page.certificate_body(cert)).to_be_hidden()

    with allure.step(f"Select Place '{part_f_all_no_data.place}'"):
        _fill(part_f_page, part_f_all_no_data)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-144  All six certificates — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-144")
@allure.story(STORY)
@allure.title("TC-144: Part F saves with all six certificates answered \"Yes\" and fully filled in")
def test_tc144_all_six_saves(part_f_page: PartFPage, logged_in_part_f_page, part_f_all_six_data: PartFData):
    """
    Given I am on Part F
    When  I answer Yes for all six certificates, fill each one, upload a signature, choose a Place and save
    Then  no error is shown and Part F is saved

    Notion: KAN-TC-144 | KAN-21 AC-7 | data: all_six
    """
    page, user = logged_in_part_f_page
    data = part_f_all_six_data

    for cert, cert_data in data.certificates.items():
        with allure.step(f"Answer Yes for '{cert}' and fill it"):
            _fill_certificate(part_f_page, cert, cert_data)

    with allure.step("Upload a signature and select a Place"):
        part_f_page.set_signature(data.signature)
        part_f_page.select_place(data.place)
        expect(part_f_page.field_errors).to_have_count(0)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-146  Missing required fields — errors and summary box
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-146")
@allure.story(STORY)
@allure.title("TC-146: Saving with required fields missing shows an inline error on each and an error summary")
def test_tc146_missing_fields_errors(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given the Contractor Licence is answered Yes with its fields blank and no Place is chosen
    When  I click "Save Part F & Continue"
    Then  each of the four required fields shows its error, the summary box lists them,
          and Licence / Certificate No. gets the focus

    Notion: KAN-TC-146 | KAN-21 AC-5
    """
    page, user = logged_in_part_f_page
    number_label, date_label = _labels("cl")
    errors = (PartFPage.required_error(number_label), PartFPage.required_error(date_label),
              PartFPage.DOCUMENT_REQUIRED_ERROR, PartFPage.PLACE_REQUIRED_ERROR)

    with allure.step("Answer Yes for the Contractor Licence; leave its fields and Place blank"):
        part_f_page.select_certificate("cl", True)
        expect(part_f_page.certificate_body("cl")).to_be_visible()

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify each field's error"):
        expect(part_f_page.field_error(part_f_page.certificate_number_input("cl"))).to_have_text(errors[0])
        expect(part_f_page.field_error(part_f_page.certificate_date_input("cl"))).to_have_text(errors[1])
        expect(part_f_page.field_error(part_f_page.certificate_file_input("cl"))).to_have_text(errors[2])
        expect(part_f_page.field_error(part_f_page.place_select)).to_have_text(errors[3])

    with allure.step("Verify the summary box and the focus"):
        _expect_blocked(page, part_f_page, *errors)
        expect(part_f_page.certificate_number_input("cl")).to_be_focused()


# ---------------------------------------------------------------------------
# TC-147  Date of Application is read-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-147")
@allure.story(STORY)
@allure.title("TC-147: Date of Application shows today's date and cannot be edited")
def test_tc147_application_date_read_only(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I look at Date of Application and try to type a different date
    Then  it shows today's date with its hint and stays unchanged

    Notion: KAN-TC-147 | KAN-21 EC-10
    """
    page, user = logged_in_part_f_page
    today = date.today().strftime("%d/%m/%Y")
    field = part_f_page.application_date_input

    with allure.step(f"Verify Date of Application shows today ({today}) with its hint"):
        expect(field).to_have_value(today)
        expect(part_f_page.application_date_hint).to_have_text(PartFPage.APPLICATION_DATE_HINT)

    with allure.step("Try to type a different date"):
        expect(field).not_to_be_editable()
        field.click()
        page.keyboard.type("01012020")
        expect(field).to_have_value(today)


# ---------------------------------------------------------------------------
# TC-148  Place is mandatory — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-148")
@allure.story(STORY)
@allure.title("TC-148: Leaving Place unselected blocks saving")
def test_tc148_place_required(part_f_page: PartFPage, logged_in_part_f_page, part_f_all_no_data: PartFData):
    """
    Given every certificate is answered No
    When  I save without a Place, then choose one and save
    Then  the first save is blocked with "Place is required." and the second succeeds

    Notion: KAN-TC-148 | data: all_no
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify Place shows the placeholder and the 36 districts"):
        expect(part_f_page.place_select).to_have_value("")
        expect(part_f_page.place_options.first).to_have_text(PartFPage.PLACE_PLACEHOLDER)
        expect(part_f_page.place_options).to_have_count(37)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_f_page.field_error(part_f_page.place_select)).to_have_text(PartFPage.PLACE_REQUIRED_ERROR)
        _expect_blocked(page, part_f_page, PartFPage.PLACE_REQUIRED_ERROR)

    with allure.step(f"Select '{part_f_all_no_data.place}' and save"):
        part_f_page.select_place(part_f_all_no_data.place)
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-149  JPG / PNG signature accepted
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-149")
@allure.story(STORY)
@allure.title("TC-149: A JPG or PNG signature under 2 MB is accepted")
def test_tc149_signature_jpg_png_accepted(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I choose a JPG, then a PNG signature
    Then  each file is kept with no error

    Notion: KAN-TC-149 | data: signature_valid.jpg, signature_valid.png
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify the signature title and hint"):
        expect(part_f_page.signature_title).to_have_text("Signature Upload on Official Letter Head")
        expect(part_f_page.signature_hint).to_have_text(PartFPage.SIGNATURE_HINT)

    for path in (SIGNATURE_JPG, SIGNATURE_PNG):
        with allure.step(f"Choose {os.path.basename(path)} — kept, no error"):
            part_f_page.set_signature(path)
            expect(part_f_page.field_error(part_f_page.signature_input)).to_have_count(0)
            assert _chosen_files(part_f_page.signature_input) == 1, "The signature file was not kept"


# ---------------------------------------------------------------------------
# TC-150  PDF signature rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-150")
@allure.story(STORY)
@allure.title("TC-150: A PDF chosen as the signature is rejected immediately")
def test_tc150_signature_pdf_rejected(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I choose a PDF as the signature
    Then  "Only JPG or PNG allowed for the signature." is shown and the file is removed

    Notion: KAN-TC-150 | KAN-21 EC-8 | data: certificate.pdf
    """
    page, user = logged_in_part_f_page

    with allure.step("Choose a PDF as the signature"):
        part_f_page.set_signature(VALID_CERTIFICATE)

    with allure.step("Verify the error and that the file was removed"):
        expect(part_f_page.field_error(part_f_page.signature_input)).to_have_text(PartFPage.SIGNATURE_TYPE_ERROR)
        assert _chosen_files(part_f_page.signature_input) == 0, "The PDF was kept"


# ---------------------------------------------------------------------------
# TC-151  Signature over 2 MB rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-151")
@allure.story(STORY)
@allure.title("TC-151: A signature larger than 2 MB is rejected immediately")
def test_tc151_signature_too_large(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I choose a JPG larger than 2 MB as the signature
    Then  "File is too large — max 2 MB." is shown and the file is removed

    Notion: KAN-TC-151 | KAN-21 EC-7 | data: oversized_image.jpg
    """
    page, user = logged_in_part_f_page

    with allure.step("Choose a signature larger than 2 MB"):
        part_f_page.set_signature(OVERSIZED_IMAGE)

    with allure.step("Verify the error and that the file was removed"):
        expect(part_f_page.field_error(part_f_page.signature_input)).to_have_text(PartFPage.FILE_TOO_LARGE_ERROR)
        assert _chosen_files(part_f_page.signature_input) == 0, "The oversized file was kept"


# ---------------------------------------------------------------------------
# TC-154  Certificate without its date
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-154")
@allure.story(STORY)
@allure.title("TC-154: A certificate answered \"Yes\" without its date blocks saving")
def test_tc154_certificate_date_required(
    part_f_page: PartFPage, logged_in_part_f_page, part_f_contractor_licence_data: PartFData
):
    """
    Given a Place is chosen
    When  I answer Yes for the Contractor Licence, fill its number and document but not its date, and save
    Then  the save is blocked with "Date of Issue is required."

    Notion: KAN-TC-154 | data: contractor_licence without date
    """
    page, user = logged_in_part_f_page
    data = part_f_contractor_licence_data
    data.certificates["cl"].date = None
    error = PartFPage.required_error(_labels("cl")[1])

    with allure.step("Fill the Contractor Licence without its date, and the Place"):
        _fill(part_f_page, data)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_f_page.field_error(part_f_page.certificate_date_input("cl"))).to_have_text(error)
        _expect_blocked(page, part_f_page, error)


# ---------------------------------------------------------------------------
# TC-155  Certificate without its document
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-155")
@allure.story(STORY)
@allure.title("TC-155: A certificate answered \"Yes\" without its document blocks saving")
def test_tc155_certificate_document_required(
    part_f_page: PartFPage, logged_in_part_f_page, part_f_contractor_licence_data: PartFData
):
    """
    Given a Place is chosen
    When  I answer Yes for the Contractor Licence, fill its number and date but upload nothing, and save
    Then  the save is blocked with "Please upload the document."

    Notion: KAN-TC-155 | data: contractor_licence without document
    """
    page, user = logged_in_part_f_page
    data = part_f_contractor_licence_data
    data.certificates["cl"].document = None

    with allure.step("Fill the Contractor Licence without its document, and the Place"):
        _fill(part_f_page, data)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_f_page.field_error(part_f_page.certificate_file_input("cl"))).to_have_text(
            PartFPage.DOCUMENT_REQUIRED_ERROR)
        _expect_blocked(page, part_f_page, PartFPage.DOCUMENT_REQUIRED_ERROR)


# ---------------------------------------------------------------------------
# TC-156  Certificate with nothing filled in
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-156")
@allure.story(STORY)
@allure.title("TC-156: A certificate answered \"Yes\" with nothing filled in shows all three errors at once")
def test_tc156_certificate_all_three_errors(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given a Place is chosen
    When  I answer Yes for the Contractor Licence, leave its fields blank and save
    Then  its number, date and document errors are all shown at once

    Notion: KAN-TC-156 | KAN-21 EC-2
    """
    page, user = logged_in_part_f_page
    number_label, date_label = _labels("cl")
    errors = (PartFPage.required_error(number_label), PartFPage.required_error(date_label),
              PartFPage.DOCUMENT_REQUIRED_ERROR)

    with allure.step("Answer Yes for the Contractor Licence and select a Place"):
        part_f_page.select_certificate("cl", True)
        part_f_page.select_place(PartFFactory.PLACE)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify all three errors"):
        expect(part_f_page.certificate_block("cl").locator("p.fld-err")).to_have_text(list(errors))
        _expect_blocked(page, part_f_page, *errors)


# ---------------------------------------------------------------------------
# TC-157  Valid certificate documents accepted
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-157")
@allure.story(STORY)
@allure.title("TC-157: A PDF, JPG or PNG certificate document under 2 MB is accepted")
def test_tc157_certificate_documents_accepted(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given the Contractor Licence is answered Yes
    When  I choose a PDF, then a JPG, then a PNG
    Then  each file is kept with no error

    Notion: KAN-TC-157 | data: certificate.pdf, certificate.jpg, certificate.png
    """
    page, user = logged_in_part_f_page
    field = part_f_page.certificate_file_input("cl")

    with allure.step("Answer Yes for the Contractor Licence and verify the upload hint"):
        part_f_page.select_certificate("cl", True)
        expect(part_f_page.certificate_file_hint("cl")).to_have_text(PartFPage.CERT_FILE_HINT)

    for path in (VALID_CERTIFICATE, CERTIFICATE_JPG, CERTIFICATE_PNG):
        with allure.step(f"Choose {os.path.basename(path)} — kept, no error"):
            part_f_page.set_certificate_document("cl", path)
            expect(part_f_page.field_error(field)).to_have_count(0)
            assert _chosen_files(field) == 1, "The document was not kept"


# ---------------------------------------------------------------------------
# TC-158  XLSX / DOCX certificate rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-158")
@allure.story(STORY)
@allure.title("TC-158: An XLSX or DOCX certificate document is rejected immediately")
def test_tc158_certificate_wrong_type(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given the Contractor Licence is answered Yes
    When  I choose an XLSX, then a DOCX file
    Then  "Only PDF, JPG or PNG allowed." is shown each time and the file is removed

    Notion: KAN-TC-158 | KAN-21 EC-6 | data: certificate.xlsx, certificate.docx
    """
    page, user = logged_in_part_f_page
    field = part_f_page.certificate_file_input("cl")

    with allure.step("Answer Yes for the Contractor Licence"):
        part_f_page.select_certificate("cl", True)

    for path in (UNSUPPORTED_SPREADSHEET, UNSUPPORTED_CERTIFICATE):
        with allure.step(f"Choose {os.path.basename(path)} — rejected and removed"):
            part_f_page.set_certificate_document("cl", path)
            expect(part_f_page.field_error(field)).to_have_text(PartFPage.CERT_FILE_TYPE_ERROR)
            assert _chosen_files(field) == 0, "The wrong-type file was kept"


# ---------------------------------------------------------------------------
# TC-159  Certificate over 2 MB rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-159")
@allure.story(STORY)
@allure.title("TC-159: A certificate document larger than 2 MB is rejected immediately")
def test_tc159_certificate_too_large(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given the Contractor Licence is answered Yes
    When  I choose a PDF larger than 2 MB
    Then  "File is too large — max 2 MB." is shown and the file is removed

    Notion: KAN-TC-159 | KAN-21 EC-7 | data: oversized.pdf
    """
    page, user = logged_in_part_f_page
    field = part_f_page.certificate_file_input("cl")

    with allure.step("Answer Yes for the Contractor Licence and choose a 3 MB PDF"):
        part_f_page.select_certificate("cl", True)
        part_f_page.set_certificate_document("cl", OVERSIZED_FILE)

    with allure.step("Verify the error and that the file was removed"):
        expect(part_f_page.field_error(field)).to_have_text(PartFPage.FILE_TOO_LARGE_ERROR)
        assert _chosen_files(field) == 0, "The oversized file was kept"


# ---------------------------------------------------------------------------
# TC-160  Future Date of Issue — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-160")
@allure.story(STORY)
@allure.title("TC-160: A Date of Issue in the future blocks saving")
def test_tc160_future_date(part_f_page: PartFPage, logged_in_part_f_page, part_f_future_date_data: PartFData):
    """
    Given the Contractor Licence is answered Yes with its number and document, and a Place is chosen
    When  I save with a date after today, then with a past date
    Then  the first save is blocked with the date error and the second succeeds

    Notion: KAN-TC-160 | KAN-21 EC-5 | data: future_date
    """
    page, user = logged_in_part_f_page
    data = part_f_future_date_data
    data.certificates["cl"].date = None
    date_field = part_f_page.certificate_date_input("cl")
    error = PartFPage.date_invalid_error(_labels("cl")[1])

    with allure.step("Fill the Contractor Licence number and document, and the Place"):
        _fill(part_f_page, data)

    with allure.step(f"Type '{data.invalid_values[0]}' and save"):
        part_f_page.type_key_by_key(date_field, data.invalid_values[0])
        part_f_page.click_submit()
        expect(part_f_page.field_error(date_field)).to_have_text(error)
        _expect_blocked(page, part_f_page, error)

    with allure.step(f"Type '{data.valid_values[0]}' and save"):
        part_f_page.type_key_by_key(date_field, data.valid_values[0])
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-161  Impossible / pre-1900 / incomplete dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-161")
@allure.story(STORY)
@allure.title("TC-161: An impossible date or a year before 1900 blocks saving")
def test_tc161_invalid_dates(part_f_page: PartFPage, logged_in_part_f_page, part_f_invalid_dates_data: PartFData):
    """
    Given the Contractor Licence is answered Yes with its number and document, and a Place is chosen
    When  I save with 31/02/2024, then 01/01/1899, then 01/01/20
    Then  each save is blocked with the date error

    Notion: KAN-TC-161 | KAN-21 EC-5 | data: invalid_dates
    """
    page, user = logged_in_part_f_page
    data = part_f_invalid_dates_data
    data.certificates["cl"].date = None
    date_field = part_f_page.certificate_date_input("cl")
    error = PartFPage.date_invalid_error(_labels("cl")[1])

    with allure.step("Fill the Contractor Licence number and document, and the Place"):
        _fill(part_f_page, data)

    for typed in data.invalid_values:
        with allure.step(f"Type '{typed}' and save — blocked"):
            part_f_page.type_key_by_key(date_field, typed)
            part_f_page.click_submit()
            expect(part_f_page.field_error(date_field)).to_have_text(error)
            _expect_blocked(page, part_f_page, error)


# ---------------------------------------------------------------------------
# TC-162  Yes → No clears the errors — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-162")
@allure.story(STORY)
@allure.title("TC-162: Switching a certificate from \"Yes\" back to \"No\" hides its fields and clears their errors")
def test_tc162_yes_to_no_clears_errors(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given a Place is chosen
    When  I save with the Contractor Licence answered Yes and blank, switch it to No, and save again
    Then  the first save shows its three errors; after No they are gone and Part F saves

    Notion: KAN-TC-162 | KAN-21 AC-3, EC-9
    """
    page, user = logged_in_part_f_page
    block = part_f_page.certificate_block("cl")

    with allure.step("Answer Yes for the Contractor Licence, select a Place and save"):
        part_f_page.select_certificate("cl", True)
        part_f_page.select_place(PartFFactory.PLACE)
        part_f_page.click_submit()
        expect(block.locator("p.fld-err")).to_have_count(3)

    with allure.step("Switch the answer to No — fields hidden, errors cleared"):
        part_f_page.select_certificate("cl", False)
        expect(part_f_page.certificate_body("cl")).to_be_hidden()
        expect(block.locator("p.fld-err")).to_have_count(0)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-163  One certificate doesn't require the others — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-163")
@allure.story(STORY)
@allure.title("TC-163: Answering \"Yes\" for one certificate does not make the others required")
def test_tc163_one_certificate_only(part_f_page: PartFPage, logged_in_part_f_page, part_f_lin_only_data: PartFData):
    """
    Given a Place is chosen
    When  I answer Yes only for the LIN, fill it and save
    Then  the other five stay No with their fields hidden and Part F saves

    Notion: KAN-TC-163 | data: lin_only
    """
    page, user = logged_in_part_f_page

    with allure.step("Fill the LIN and the Place"):
        _fill(part_f_page, part_f_lin_only_data)

    with allure.step("Verify the other five certificates stay No"):
        for cert in PartFPage.CERTIFICATES:
            if cert != "lin":
                expect(part_f_page.certificate_radio(cert, False)).to_be_checked()
                expect(part_f_page.certificate_body(cert)).to_be_hidden()

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-166  "← Part C"
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-166")
@allure.story(STORY)
@allure.title("TC-166: \"← Part C\" returns to Part C with its saved data intact")
def test_tc166_back_to_part_c(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I click "← Part C"
    Then  Part C opens without a dialog and shows its saved values

    Notion: KAN-TC-166 | KAN-21 AC-8
    """
    page, user = logged_in_part_f_page
    part_c = PartCPage(page)

    with allure.step("Click '← Part C'"):
        message = part_f_page.click_and_handle_alert(part_f_page.back_to_part_c_link)
        assert message == "", f"Unexpected dialog: {message}"

    with allure.step("Verify Part C opens with its saved values"):
        expect(page).to_have_url(re.compile(rf"{re.escape(PART_C_URL)}"))
        expect(part_c.title).to_have_text("Step 3 — Part C: Operations & Infrastructure")
        expect(part_c.placement_type_select).not_to_have_value("")


# ---------------------------------------------------------------------------
# TC-462  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-462")
@allure.story(STORY)
@allure.title("TC-462: Part F shows the heading, progress bar, back link, three sections and save button")
def test_tc462_page_layout(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I look at the page
    Then  the heading, subtitle, "← Part C", progress bar, sections, note, six certificates and save button are shown

    Notion: KAN-TC-462 | KAN-21 AC-1
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify the heading, subtitle and '← Part C'"):
        expect(part_f_page.title).to_contain_text("Step 4 — Certificates, Licences & Signature")
        expect(part_f_page.title).to_contain_text("(Form-I Part F)")
        expect(part_f_page.sub_title).to_have_text(PartFPage.SUBTITLE)
        expect(part_f_page.back_to_part_c_link).to_be_visible()

    with allure.step("Verify the progress bar"):
        expect(part_f_page.progress_step("Register")).to_contain_text("✓")
        for label in ("Part A", "Part B", "Part C"):
            expect(part_f_page.completed_step_link(label)).to_contain_text("✓")
        expect(part_f_page.progress_step("Part F").or_(part_f_page.completed_step_link("Part F"))).to_be_visible()
        for label in ("Documents", "Photos", "Declaration", "Preview", "Payment"):
            expect(part_f_page.progress_step(label)).to_be_visible()

    with allure.step("Verify the sections, the note and the six certificates"):
        expect(part_f_page.section_headings).to_have_text(list(PartFPage.SECTIONS))
        expect(part_f_page.certificates_note).to_contain_text("Certificates are optional.")
        for cert, (title, _, _) in PartFPage.CERTIFICATES.items():
            expect(part_f_page.certificate_title(cert)).to_have_text(title)

    with allure.step("Verify the save button"):
        expect(part_f_page.submit_button).to_have_text("Save Part F & Continue")


# ---------------------------------------------------------------------------
# TC-463  Default state of a never-saved Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-463")
@allure.story(STORY)
@allure.title("TC-463: Part F opens with every certificate answered \"No\", today's application date and no Place")
def test_tc463_default_state(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given Part F has never been saved
    When  I open Part F
    Then  all six certificates are No with hidden fields, Date of Application is today and read-only,
          Place is unselected and no signature is chosen

    Notion: KAN-TC-463 | KAN-21 AC-2 | data: user with a never-saved Part F
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify the six certificates are No with their fields hidden"):
        for cert in PartFPage.CERTIFICATES:
            expect(part_f_page.certificate_radio(cert, False)).to_be_checked()
            expect(part_f_page.certificate_body(cert)).to_be_hidden()

    with allure.step("Verify Date of Application, Place and the signature"):
        expect(part_f_page.application_date_input).to_have_value(date.today().strftime("%d/%m/%Y"))
        expect(part_f_page.application_date_input).not_to_be_editable()
        expect(part_f_page.place_select).to_have_value("")
        assert _chosen_files(part_f_page.signature_input) == 0, "A signature is already chosen"


# ---------------------------------------------------------------------------
# TC-464  Each certificate's Yes shows its own fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-464")
@allure.story(STORY)
@allure.title("TC-464: Answering \"Yes\" for each certificate shows its own number, date and upload fields")
def test_tc464_certificate_fields(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given I am on Part F
    When  I answer Yes to each certificate question
    Then  each shows its own number, date and upload labels, all marked required

    Notion: KAN-TC-464 | KAN-21 AC-3
    """
    page, user = logged_in_part_f_page

    for cert, (title, number_label, date_label) in PartFPage.CERTIFICATES.items():
        with allure.step(f"Answer Yes for '{title}'"):
            expect(part_f_page.certificate_question(cert)).to_contain_text(PartFPage.QUESTIONS[cert])
            part_f_page.select_certificate(cert, True)
            expect(part_f_page.certificate_body(cert)).to_be_visible()
            expect(part_f_page.certificate_labels(cert)).to_have_text(
                [f"{number_label} *", f"{date_label} (DD/MM/YYYY) *", "Upload Document *"])


# ---------------------------------------------------------------------------
# TC-465  Errors use each certificate's labels
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-465")
@allure.story(STORY)
@allure.title("TC-465: Required-field errors use each certificate's own labels")
def test_tc465_errors_use_certificate_labels(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given a Place is chosen
    When  I answer Yes for all six certificates, leave them blank and save
    Then  each certificate shows "<its number label> is required.", "<its date label> is required."
          and "Please upload the document."

    Notion: KAN-TC-465
    """
    page, user = logged_in_part_f_page

    with allure.step("Answer Yes for all six certificates and select a Place"):
        for cert in PartFPage.CERTIFICATES:
            part_f_page.select_certificate(cert, True)
        part_f_page.select_place(PartFFactory.PLACE)

    with allure.step("Click 'Save Part F & Continue'"):
        part_f_page.click_submit()

    for cert, (title, number_label, date_label) in PartFPage.CERTIFICATES.items():
        with allure.step(f"Verify the errors under '{title}'"):
            expect(part_f_page.certificate_block(cert).locator("p.fld-err")).to_have_text([
                PartFPage.required_error(number_label), PartFPage.required_error(date_label),
                PartFPage.DOCUMENT_REQUIRED_ERROR,
            ])


# ---------------------------------------------------------------------------
# TC-466  Certificate number rules — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-466")
@allure.story(STORY)
@allure.title("TC-466: A certificate number must be at least 3 characters and start with a letter or digit")
def test_tc466_certificate_number_rules(
    part_f_page: PartFPage, logged_in_part_f_page, part_f_psara_number_data: PartFData
):
    """
    Given the PSARA Licence is answered Yes with its date and document, and a Place is chosen
    When  I save with "AB", "-ABC123" and "PSARA#123", then with a valid number
    Then  the too-short and invalid-character errors are shown, and the valid number saves

    Notion: KAN-TC-466 | KAN-21 EC-3 | data: psara_number_rules
    """
    page, user = logged_in_part_f_page
    data = part_f_psara_number_data
    number_label = _labels("sec")[0]
    errors = (PartFPage.number_too_short_error(number_label), PartFPage.number_invalid_error(number_label),
              PartFPage.number_invalid_error(number_label))
    field = part_f_page.certificate_number_input("sec")

    with allure.step("Fill the PSARA Licence date and document, and the Place"):
        _fill(part_f_page, data)

    for value, error in zip(data.invalid_values, errors):
        with allure.step(f"Save with '{value}' — '{error}'"):
            part_f_page.fill_certificate_number("sec", value)
            part_f_page.click_submit()
            expect(part_f_page.field_error(field)).to_have_text(error)
            _expect_blocked(page, part_f_page, error)

    with allure.step(f"Save with '{data.valid_values[0]}'"):
        part_f_page.fill_certificate_number("sec", data.valid_values[0])
        part_f_page.click_submit()

    with allure.step("Verify Part F is saved"):
        _expect_part_f_saved(page, part_f_page, user)


# ---------------------------------------------------------------------------
# TC-467  Date typing help
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-467")
@allure.story(STORY)
@allure.title("TC-467: Typing a date adds the slashes and removes anything but digits")
def test_tc467_date_typing(part_f_page: PartFPage, logged_in_part_f_page, part_f_date_typed_cases: list[TypedInput]):
    """
    Given the Contractor Licence is answered Yes
    When  I type dates digit by digit, with letters, past the end, and with my own slashes
    Then  the field shows the DD/MM/YYYY date each time

    Notion: KAN-TC-467 | KAN-21 EC-4 | data: date_typed_cases
    Known defect (28-Oct-2026): typing the slashes yourself shows 01//01/202 — the last step fails.
    """
    page, user = logged_in_part_f_page
    field = part_f_page.certificate_date_input("cl")

    with allure.step("Answer Yes for the Contractor Licence"):
        part_f_page.select_certificate("cl", True)

    for case in part_f_date_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            part_f_page.type_key_by_key(field, case.typed)
            expect(field).to_have_value(case.shown)


# ---------------------------------------------------------------------------
# TC-468  Save & Log out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-468")
@allure.story(STORY)
@allure.title("TC-468: \"Save & Log out\" logs the user out so they can continue later")
def test_tc468_save_and_logout(part_f_page: PartFPage, logged_in_part_f_page):
    """
    Given my application is unpaid
    When  I click "Save & Log out" in the deadline banner and log in again
    Then  I am logged out, and after logging in I can open Part F again

    Notion: KAN-TC-468 | KAN-21 AC-9
    """
    page, user = logged_in_part_f_page

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(part_f_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(part_f_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        part_f_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again and open Part F"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        part_f_page.open()
        expect(part_f_page.title).to_contain_text("Certificates, Licences & Signature")


# ---------------------------------------------------------------------------
# TC-469  Reopening a saved Part F — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-469")
@allure.story(STORY)
@allure.title("TC-469: A saved Part F reopens editable, shows saved documents as \"Uploaded\" and \"No\" removes them")
def test_tc469_saved_part_f_reopens(
    part_f_page: PartFPage, logged_in_part_f_page, part_f_contractor_licence_data: PartFData
):
    """
    Given I have saved Part F with a Contractor Licence document
    When  I reopen Part F, save without a new document, then save the Contractor Licence as No
    Then  Part F is editable with the saved values and the document shown as "Uploaded";
          it is not required again; after saving No the document is no longer on file

    Notion: KAN-TC-469 | KAN-21 AC-10 | data: contractor_licence
    """
    page, user = logged_in_part_f_page
    data = part_f_contractor_licence_data
    cert_data = data.certificates["cl"]

    with allure.step("Save Part F with the Contractor Licence filled in"):
        _fill(part_f_page, data)
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)

    with allure.step("Reopen Part F — editable, with the saved values and the document 'Uploaded'"):
        part_f_page.open()
        expect(part_f_page.submit_button).to_be_visible()
        expect(part_f_page.certificate_radio("cl", True)).to_be_checked()
        expect(part_f_page.certificate_number_input("cl")).to_be_editable()
        expect(part_f_page.certificate_number_input("cl")).to_have_value(cert_data.number)
        expect(part_f_page.certificate_date_input("cl")).to_have_value(cert_data.date.shown)
        expect(part_f_page.saved_document_note("cl")).to_have_text(PartFPage.SAVED_DOCUMENT_NOTE)
        expect(part_f_page.saved_document_link("cl")).to_be_visible()

    with allure.step("Save without choosing a new document — not required again"):
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)

    with allure.step("Reopen, answer No for the Contractor Licence and save"):
        part_f_page.open()
        part_f_page.select_certificate("cl", False)
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)

    with allure.step("Reopen and answer Yes — the document is no longer on file"):
        part_f_page.open()
        part_f_page.select_certificate("cl", True)
        expect(part_f_page.saved_document_note("cl")).to_have_count(0)
        assert not part_f_page.has_saved_document("cl"), "The document is still on file"


# ---------------------------------------------------------------------------
# TC-470  Answers shown right after a save — saves Part F
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-470")
@allure.story(STORY)
@allure.title("TC-470: Right after saving, each certificate shows the answer that was just saved")
def test_tc470_answers_after_save(
    part_f_page: PartFPage, logged_in_part_f_page, part_f_contractor_licence_data: PartFData
):
    """
    Given Part F is saved with the Contractor Licence answered No
    When  I save it as Yes (filled in), then save it as No again
    Then  the page shown after each save has the answer that was just saved

    Notion: KAN-TC-470 | KAN-21 known defect #16 | data: contractor_licence
    Known defect (28-Oct-2026, #16 in the MPPA sheet): the previously saved answer is shown — this test fails.
    """
    page, user = logged_in_part_f_page

    with allure.step("Precondition: save Part F with the Contractor Licence answered No"):
        part_f_page.select_place(PartFFactory.PLACE)
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)
        part_f_page.open()

    with allure.step("Answer Yes for the Contractor Licence, fill it and save"):
        _fill(part_f_page, part_f_contractor_licence_data)
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)

    with allure.step("Verify the reloaded page shows Yes with the fields visible"):
        expect(part_f_page.certificate_radio("cl", True)).to_be_checked()
        expect(part_f_page.certificate_body("cl")).to_be_visible()

    with allure.step("Answer No and save"):
        part_f_page.select_certificate("cl", False)
        part_f_page.click_submit()
        _expect_part_f_saved(page, part_f_page, user)

    with allure.step("Verify the reloaded page shows No with the fields hidden"):
        expect(part_f_page.certificate_radio("cl", False)).to_be_checked()
        expect(part_f_page.certificate_body("cl")).to_be_hidden()
