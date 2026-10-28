import dataclasses
import os
import re
import time
from datetime import date

import allure
import pytest
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partA_page import PART_A_LOCKED_STEP_URL, PartAPage
from test_data.partA_factory import PartAData, PartAFactory, TypedInput
from utils.aio import aio_case
from utils.file_manager import OVERSIZED_FILE, UNDERSIZED_FILE, UNSUPPORTED_CERTIFICATE, VALID_CERTIFICATE
from utils.state_store import TestStateStore

# Wizard pages after Part A, in order (forms/<name>.php); all locked until Part A is saved.
LATER_STEP_PAGES = ("partB", "partC", "partF", "enclosures", "declaration", "preview")

# Fields the server must reject when Part A is saved blank (KAN-TC-60).
MANDATORY_FIELD_NAMES = (
    "agency_type", "date_of_establishment", "incorporation_no", "incorporation_file",
    "tan_number", "tan_file", "gstin", "gst_file", "address_line1", "taluka", "city",
    "pincode", "authorized_signatory", "designation",
)
MH_OFFICE_FIELD_NAMES = ("mh_address_line1", "mh_district_id", "mh_mandal_taluka", "mh_city", "mh_pincode")

IS_BAD = re.compile(r"\bis-bad\b")
SHOWN = re.compile(r"\bshow\b")
PIN_ERR = re.compile(r"\bpin-err\b")


def _fill_part_a(part_a: PartAPage, data: PartAData) -> None:
    """Fills every Part A field that ``data`` has a value for, top to bottom."""
    if data.legal_constitution:
        part_a.select_legal_constitution(data.legal_constitution)
    if data.date_of_establishment:
        part_a.fill_agency_date_of_establishment(data.date_of_establishment)
    if data.incorporation_no:
        part_a.fill_incorporation_no(data.incorporation_no)
    if data.incorporation_certificate:
        part_a.set_incorporation_certificate(data.incorporation_certificate)
    if data.tan_number:
        part_a.fill_tan(data.tan_number)
    if data.tan_certificate:
        part_a.set_tan_certificate(data.tan_certificate)
    if data.gstin:
        part_a.fill_gst(data.gstin)
    if data.gst_certificate:
        part_a.set_gst_certificate(data.gst_certificate)
    if data.state != "Maharashtra":
        part_a.select_head_office_state(data.state)
        part_a.fill_district(data.district)
    if data.address_line1:
        part_a.fill_address_line1(data.address_line1)
    if data.address_line2:
        part_a.fill_address_line2(data.address_line2)
    if data.taluka:
        part_a.set_taluka(data.taluka)
    if data.city:
        part_a.fill_city(data.city)
    if data.pincode:
        part_a.fill_pincode(data.pincode)
    if data.mh_office:
        mh = data.mh_office
        part_a.fill_mh_office(mh.address, mh.district, mh.taluka, mh.city, mh.pincode)
    for b in data.branches:
        part_a.add_branch(b.address, b.district, b.taluka, b.city, b.pincode, b.premise_type, b.premise_other)
    if data.authorised_signatory:
        part_a.fill_authorised_signatory(data.authorised_signatory)
    if data.designation:
        part_a.fill_designation(data.designation)
    if data.aadhaar:
        part_a.fill_aadhaar(data.aadhaar)


def _clear_branches(part_a: PartAPage) -> None:
    """Removes any branch cards (e.g. re-rendered by the server after a rejected save)."""
    while part_a.branch_cards.count():
        part_a.remove_branch(0)


def _expect_part_a_saved(page) -> None:
    """Part A is saved once Part B opens instead of redirecting back to Part A."""
    page.goto(f"{FORMS_BASE}/partB.php")
    expect(page).not_to_have_url(PART_A_LOCKED_STEP_URL)


def _expect_part_a_not_saved(page) -> None:
    page.goto(f"{FORMS_BASE}/partB.php")
    expect(page).to_have_url(PART_A_LOCKED_STEP_URL)


def _date_box_text(dd_mm_yyyy: str) -> str:
    """'15-03-2018' -> '15/03/2018', as the read-only date box shows it."""
    return dd_mm_yyyy.replace("-", "/")


# ---------------------------------------------------------------------------
# TC-57  PAN pre-populated and read-only — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-57")
@pytest.mark.deprecated(reason="PAN field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-57: PAN Number field is pre-populated and read-only when Step 1 loads")
def test_tc57_pan_prepopulated_readonly():
    """
    Deprecated — tested the pre-filled, read-only PAN Number field, which Part A
    no longer has. The original steps are in git history.

    Notion: KAN-TC-57
    """


# ---------------------------------------------------------------------------
# TC-58  Part A saves successfully and unlocks Part B — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-58")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-58: Part A saves successfully and unlocks Part B when all mandatory fields are filled")
def test_tc58_step1_saves_and_unlocks_step2(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_valid_data: PartAData
):
    """
    Given I am on Part A with no prior data saved (head office in Maharashtra)
    When  I fill every mandatory field, upload the TAN, GST and incorporation
          certificates and click "Save Part A & Continue"
    Then  Part A is saved and Part B no longer redirects back to Part A

    Notion: KAN-TC-58 | KAN-8 AC-5 | data: valid_mandatory_fields
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_valid_data, user)

    with allure.step(f"Select Agency Type / Legal Constitution: {data.legal_constitution}"):
        part_a_page.select_legal_constitution(data.legal_constitution)
        expect(part_a_page.incorporation_no_required_mark).to_be_visible()
        expect(part_a_page.incorporation_certificate_required_mark).to_be_visible()

    with allure.step("Pick the Date of Establishment from the calendar"):
        part_a_page.fill_agency_date_of_establishment(data.date_of_establishment)
        expect(part_a_page.date_of_establishment_input).to_have_value(_date_box_text(data.date_of_establishment))

    with allure.step("Enter the Incorporation No. and upload the certificate"):
        part_a_page.fill_incorporation_no(data.incorporation_no)
        part_a_page.set_incorporation_certificate(data.incorporation_certificate)

    with allure.step("Enter the TAN and upload the TAN certificate"):
        part_a_page.fill_tan(data.tan_number)
        part_a_page.set_tan_certificate(data.tan_certificate)

    with allure.step("Enter the GSTIN and upload the GST certificate"):
        part_a_page.fill_gst(data.gstin)
        part_a_page.set_gst_certificate(data.gst_certificate)
        expect(part_a_page.gstin_hint).to_have_text(PartAPage.GSTIN_VALID_HINT)

    with allure.step("Fill the Registered Office Address (State: Maharashtra)"):
        part_a_page.fill_address_line1(data.address_line1)
        part_a_page.set_taluka(data.taluka)
        part_a_page.fill_city(data.city)
        part_a_page.fill_pincode(data.pincode)
        expect(part_a_page.district_display).not_to_be_editable()
        expect(part_a_page.pincode_hint).to_have_text(PartAPage.PIN_VALID_HINT)

    with allure.step("Fill the Authorised Signatory Details"):
        part_a_page.fill_authorised_signatory(data.authorised_signatory)
        part_a_page.fill_designation(data.designation)

    with allure.step("Click 'Save Part A & Continue'"):
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved — Part B opens instead of redirecting back"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-59  Later steps locked until Step 1 is saved
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-59")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-59: Later wizard steps are locked until Step 1 is saved")
def test_tc59_steps_locked_until_step1_saved(fresh_agency_user_page):
    """
    Given I am on Step 1 with no previously saved data
    When  I try to open any later wizard step directly by URL
    Then  I am redirected back to Step 1 — Part A (?error=complete_partA_first)

    The progress bar is no longer clickable and no locked-step message is
    shown since the portal redesign; the lock is enforced by the redirect.

    Notion: KAN-TC-59 | data: fresh_agency_user
    """
    page, user = fresh_agency_user_page

    for step_page in LATER_STEP_PAGES:
        with allure.step(f"Open {step_page}.php directly"):
            page.goto(f"{FORMS_BASE}/{step_page}.php")

        with allure.step(f"Verify {step_page}.php redirects back to Part A"):
            expect(page).to_have_url(PART_A_LOCKED_STEP_URL)


# ---------------------------------------------------------------------------
# TC-60  Saving a blank Part A highlights every mandatory field
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-60")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-60: Saving a blank Part A highlights every mandatory field and does not save")
def test_tc60_blank_form_shows_validation_tooltip(part_a_page: PartAPage, logged_in_part_a_fresh_page):
    """
    Given I am on Part A with no data entered
    When  I click "Save Part A & Continue"
    Then  the save is rejected and every mandatory field is highlighted in red at once
    And   the page scrolls to the first highlighted field
    And   Part A is not saved (Part B still redirects back)

    Notion: KAN-TC-60 | KAN-8 AC-3, EC-7 | data: fresh_agency_user
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Verify the form is empty apart from the data from registration"):
        expect(part_a_page.legal_constitution_select).to_have_value("")
        expect(part_a_page.date_of_establishment_input).to_have_value("")
        if user.district == "Other":
            # "Other" at registration names no Maharashtra district, so District stays empty (see TC-426).
            expect(part_a_page.district_display).to_have_value("")
        else:
            expect(part_a_page.district_display).not_to_have_value("")

    with allure.step("Click 'Save Part A & Continue' without entering any data"):
        part_a_page.click_save_next()

    with allure.step("Verify every mandatory field is highlighted in red"):
        highlighted = set(part_a_page.rejected_fields.evaluate_all("els => els.map(e => e.name)"))
        missing = sorted(set(MANDATORY_FIELD_NAMES) - highlighted)
        assert not missing, f"Mandatory fields not highlighted: {missing}; highlighted: {sorted(highlighted)}"

    with allure.step("Verify the page scrolled to the first highlighted field"):
        expect(part_a_page.rejected_fields.first).to_be_in_viewport()

    with allure.step("Verify Part A was not saved"):
        _expect_part_a_not_saved(page)


# ---------------------------------------------------------------------------
# TC-62  A future Date of Establishment cannot be selected and is rejected on save
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-62")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-62: A future Date of Establishment cannot be selected and is rejected on save")
def test_tc62_future_date_of_incorporation(
    part_a_page: PartAPage, logged_in_part_a_mh_page, part_a_future_date_data: PartAData
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I open the Date of Establishment calendar
    Then  dates after today cannot be selected and the box cannot be typed into
    When  a future date is forced into the box and I click Save
    Then  the save is blocked with "Date of Establishment cannot be in the future."

    Notion: KAN-TC-62 | KAN-8 EC-10 | data: future_date
    """
    page, user = logged_in_part_a_mh_page
    data = PartAFactory.for_user(part_a_future_date_data, user)

    with allure.step("Verify the date box cannot be typed into"):
        expect(part_a_page.date_of_establishment_input).not_to_be_editable()

    with allure.step("Verify the calendar does not allow dates after today"):
        expect(part_a_page.date_native_input).to_have_attribute("max", date.today().isoformat())

    with allure.step("Fill all other mandatory fields"):
        _fill_part_a(part_a_page, data)

    with allure.step(f"Force '{data.forced_date_text}' into the date box and click Save"):
        part_a_page.force_date_of_establishment_text(data.forced_date_text)
        message = part_a_page.click_save_and_handle_alert()

    with allure.step("Verify the future-date pop-up blocks the save"):
        assert data.expected_error in message, f"Expected '{data.expected_error}', got: {message!r}"


# ---------------------------------------------------------------------------
# TC-63  Date of Establishment accepts only calendar dates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-63")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-63: Date of Establishment accepts only calendar dates; any other format is rejected on save")
def test_tc63_invalid_date_format(
    part_a_page: PartAPage, logged_in_part_a_mh_page, part_a_invalid_date_data: PartAData
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I try to type a date into the Date of Establishment box
    Then  nothing can be typed — the box is filled only from the calendar (DD/MM/YYYY)
    When  a value in another format is forced into the box and I click Save
    Then  the save is blocked with "Date of Establishment must be in DD/MM/YYYY format."

    Notion: KAN-TC-63 | KAN-8 field validation | data: invalid_date_format
    """
    page, user = logged_in_part_a_mh_page
    data = PartAFactory.for_user(part_a_invalid_date_data, user)

    with allure.step(f"Verify '{data.invalid_value}' cannot be typed — the date box is read-only"):
        expect(part_a_page.date_of_establishment_input).not_to_be_editable()

    with allure.step("Fill all mandatory fields, picking the date from the calendar"):
        _fill_part_a(part_a_page, data)
        expect(part_a_page.date_of_establishment_input).to_have_value(_date_box_text(data.date_of_establishment))

    with allure.step(f"Force '{data.forced_date_text}' into the date box and click Save"):
        part_a_page.force_date_of_establishment_text(data.forced_date_text)
        message = part_a_page.click_save_and_handle_alert()

    with allure.step("Verify the date-format pop-up blocks the save"):
        assert data.expected_error in message, f"Expected '{data.expected_error}', got: {message!r}"


# ---------------------------------------------------------------------------
# TC-64  TAN is mandatory and must match the TAN format — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-64")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-64: TAN Number is mandatory and must match the TAN format")
def test_tc64_invalid_tan_format(
    part_a_page: PartAPage,
    logged_in_part_a_fresh_mh_page,
    part_a_invalid_tan_data: PartAData,
    part_a_tan_typed_lowercase: TypedInput,
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I type a lower-case TAN with separators
    Then  it is upper-cased with only letters and digits kept
    When  I save with an incorrectly formatted TAN, and then with no TAN
    Then  each save is rejected and the TAN field is highlighted in red
    When  I save with a valid TAN and TAN certificate
    Then  Part A saves successfully

    Notion: KAN-TC-64 | KAN-8 field validation | data: invalid_tan_format
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_invalid_tan_data, user)
    typed = part_a_tan_typed_lowercase

    with allure.step(f"Type '{typed.typed}' into TAN Number"):
        part_a_page.type_into(typed.field, typed.typed)
        expect(part_a_page.tan_number_input).to_have_value(typed.shown)

    with allure.step(f"Fill all mandatory fields with an incorrectly formatted TAN '{data.invalid_value}' and save"):
        _fill_part_a(part_a_page, data)
        part_a_page.fill_tan(data.invalid_value)
        part_a_page.click_save_next()

    with allure.step("Verify the save is rejected and TAN is highlighted"):
        expect(part_a_page.rejected_field("tan_number")).to_have_count(1)

    with allure.step("Fill all mandatory fields with TAN left blank and save"):
        _fill_part_a(part_a_page, data)
        part_a_page.fill_tan("")
        part_a_page.click_save_next()

    with allure.step("Verify the save is rejected and TAN is highlighted (TAN is mandatory)"):
        expect(part_a_page.rejected_field("tan_number")).to_have_count(1)

    with allure.step(f"Fill all mandatory fields with a valid TAN '{data.tan_number}' and certificate, then save"):
        _fill_part_a(part_a_page, data)
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-65  GSTIN live format hint; invalid GSTIN rejected on save — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-65")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-65: GSTIN shows a live format hint and an invalid GSTIN is rejected on save")
def test_tc65_invalid_gstin_format(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_invalid_gstin_data: PartAData
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I type a partial GSTIN, then 15 characters that don't match the format
    Then  the hint shows "n/15 characters", then "✗ Invalid GSTIN format"
    When  I save with the invalid GSTIN
    Then  the save is rejected and GSTIN is highlighted in red
    When  I save with a valid GSTIN and GST certificate
    Then  the hint shows "✓ Valid GSTIN format" and Part A saves

    Notion: KAN-TC-65 | KAN-8 EC-8 | data: invalid_gstin_format
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_invalid_gstin_data, user)

    with allure.step(f"Type a partial GSTIN '{data.partial_value}'"):
        part_a_page.fill_gst(data.partial_value)
        expect(part_a_page.gstin_hint).to_have_text(f"{len(data.partial_value)}/15 characters")

    with allure.step(f"Complete it to an invalid 15-character GSTIN '{data.invalid_value}'"):
        part_a_page.fill_gst(data.invalid_value)
        expect(part_a_page.gstin_hint).to_have_text(data.expected_error)

    with allure.step("Fill all other mandatory fields, keep the invalid GSTIN and save"):
        _fill_part_a(part_a_page, data)
        part_a_page.fill_gst(data.invalid_value)
        part_a_page.click_save_next()

    with allure.step("Verify the save is rejected and GSTIN is highlighted"):
        expect(part_a_page.rejected_field("gstin")).to_have_count(1)

    with allure.step(f"Fill all mandatory fields with a valid GSTIN '{data.gstin}' and certificate, then save"):
        _fill_part_a(part_a_page, data)
        expect(part_a_page.gstin_hint).to_have_text(PartAPage.GSTIN_VALID_HINT)
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-66  Email without @ or domain — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-66")
@pytest.mark.deprecated(reason="Official Email field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-66: An email address without @ or domain is blocked by a native validation tooltip")
def test_tc66_invalid_email_format():
    """
    Deprecated — tested the Official Email field, which Part A no longer has.
    The original steps are in git history.

    Notion: KAN-TC-66
    """


# ---------------------------------------------------------------------------
# TC-67  Mobile number with letters / wrong length — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-67")
@pytest.mark.deprecated(reason="Mobile Number field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-67: A mobile number with letters, special characters, or wrong length is rejected")
def test_tc67_invalid_mobile_number():
    """
    Deprecated — tested the Mobile Number field, which Part A no longer has.
    The original steps are in git history.

    Notion: KAN-TC-67
    """


# ---------------------------------------------------------------------------
# TC-68  Website URL without http/https — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-68")
@pytest.mark.deprecated(reason="Website URL field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-68: A website URL not starting with http:// or https:// is blocked by a native validation tooltip")
def test_tc68_invalid_website_url():
    """
    Deprecated — tested the Website URL field, which Part A no longer has.
    The original steps are in git history.

    Notion: KAN-TC-68
    """


# ---------------------------------------------------------------------------
# TC-69  Non-JPG/PNG office photo — DEPRECATED (see TC-432)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-69")
@pytest.mark.deprecated(reason="Office photograph upload removed; certificate file types are covered by KAN-TC-432")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-69: Uploading a non-JPG/PNG file as office photograph is rejected immediately")
def test_tc69_invalid_office_photo_format():
    """
    Deprecated — tested the office photograph upload, which Part A no longer has.
    Certificate upload file types are tested by test_tc432. The original steps are
    in git history.

    Notion: KAN-TC-69
    """


# ---------------------------------------------------------------------------
# TC-70  Office photograph larger than 2 MB — DEPRECATED (see TC-433)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-70")
@pytest.mark.deprecated(reason="Office photograph upload removed; certificate size limits are covered by KAN-TC-433")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-70: Office photograph larger than 2 MB is rejected before submission")
def test_tc70_oversized_office_photo():
    """
    Deprecated — tested the office photograph size limit; Part A no longer has the
    upload. Certificate size limits are tested by test_tc433. The original steps
    are in git history.

    Notion: KAN-TC-70
    """


# ---------------------------------------------------------------------------
# TC-71  Part A saves with no branch office — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-71")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-71: Part A saves successfully when no branch office is added")
def test_tc71_save_without_branch_offices(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_without_branch_offices_data: PartAData
):
    """
    Given I am on Part A
    When  I fill every mandatory field, add no branch office and click Save
    Then  Part A saves successfully (branch offices are optional)

    Notion: KAN-TC-71 | KAN-8 AC-7 | data: without_branch_offices
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_without_branch_offices_data, user)

    with allure.step("Fill all mandatory fields; add no branch office"):
        _fill_part_a(part_a_page, data)
        expect(part_a_page.branch_cards).to_have_count(0)

    with allure.step("Click 'Save Part A & Continue'"):
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-72  Multiple branch offices are each preserved after save — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-72")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-72: Multiple branch offices added as cards are each preserved after save")
def test_tc72_multiple_branch_offices_preserved(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_with_branch_offices_data: PartAData
):
    """
    Given I am on Part A with all mandatory fields filled
    When  I add two branch offices with "Add Branch Office", fill them and save
    And   I re-open Part A
    Then  both branch cards are shown with every value exactly as entered

    Notion: KAN-TC-72 | KAN-8 AC-7 | data: with_branch_offices
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_with_branch_offices_data, user)

    with allure.step("Fill all mandatory fields and add two branch offices"):
        _fill_part_a(part_a_page, data)

    with allure.step("Verify two numbered branch cards are shown"):
        expect(part_a_page.branch_cards).to_have_count(len(data.branches))
        expect(part_a_page.branch_numbers).to_have_text([str(n) for n in range(1, len(data.branches) + 1)])

    with allure.step("Click 'Save Part A & Continue'"):
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Re-open Part A"):
        part_a_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify each branch office is shown exactly as entered"):
        expect(part_a_page.branch_cards).to_have_count(len(data.branches))
        for i, b in enumerate(data.branches):
            expect(part_a_page.branch_field(i, "address")).to_have_value(b.address)
            district = part_a_page.branch_field(i, "district_id").evaluate("s => s.options[s.selectedIndex].text")
            assert district == b.district, f"Branch {i + 1} district: expected {b.district!r}, got {district!r}"
            expect(part_a_page.branch_field(i, "mandal_taluka")).to_have_value(b.taluka)
            expect(part_a_page.branch_field(i, "city")).to_have_value(b.city)
            expect(part_a_page.branch_field(i, "pincode")).to_have_value(b.pincode)
            expect(part_a_page.branch_field(i, "office_premise_type")).to_have_value(b.premise_type)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-73  Partially entered Step 1 data restored after "← Dashboard" — DEPRECATED (see TC-429)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-73")
@pytest.mark.deprecated(reason="'← Dashboard' link and unsaved-changes dialog removed; data persistence is covered by KAN-TC-429")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-73: Partially entered Step 1 data is restored when user navigates away and returns")
def test_tc73_partial_data_restored_after_navigation():
    """
    Deprecated — navigated away through the '← Dashboard' link and its unsaved-changes
    dialog, both removed from Part A. Data persistence is tested by test_tc429. The
    original steps are in git history.

    Notion: KAN-TC-73
    """


# ---------------------------------------------------------------------------
# TC-74  Agency name with special characters — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-74")
@pytest.mark.deprecated(reason="Agency Name input removed — the name is read-only from registration")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-74: Agency name containing invalid special characters shows an inline error")
def test_tc74_agency_name_special_chars():
    """
    Deprecated — tested the Agency Name input; Part A now shows the name read-only
    from registration. The original steps are in git history.

    Notion: KAN-TC-74
    """


# ---------------------------------------------------------------------------
# TC-75  Mobile number starting with 0 — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-75")
@pytest.mark.deprecated(reason="Mobile Number field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-75: A 10-digit mobile number that starts with 0 is rejected")
def test_tc75_mobile_starts_with_zero():
    """
    Deprecated — tested the Mobile Number field, which Part A no longer has.
    The original steps are in git history.

    Notion: KAN-TC-75
    """


# ---------------------------------------------------------------------------
# TC-76  Duplicate agency name warning — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-76")
@pytest.mark.deprecated(reason="Agency Name input removed — the duplicate-name warning no longer applies on Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-76: Entering an agency name that already exists shows a warning but allows saving")
def test_tc76_duplicate_agency_name_warning():
    """
    Deprecated — tested a warning for a duplicate Agency Name input, which Part A no
    longer has. The original steps are in git history.

    Notion: KAN-TC-76
    """


# ---------------------------------------------------------------------------
# TC-77  User cannot edit pre-filled PAN — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-77")
@pytest.mark.deprecated(reason="PAN field removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-77: User cannot edit pre-filled PAN")
def test_tc77_pan_field_strictly_readonly():
    """
    Deprecated — tested that the pre-filled PAN could not be edited; Part A no longer
    has a PAN field. The original steps are in git history.

    Notion: KAN-TC-77
    """


# ---------------------------------------------------------------------------
# TC-78  Browser back leaves Part A without a confirmation dialog
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-78")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-78: Pressing browser back on Part A leaves the page without a confirmation dialog")
def test_tc78_browser_back_prompts_dialog(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_unsaved_signatory_data: PartAData
):
    """
    Given I have entered a value on Part A without saving
    When  I press the browser back button
    Then  no confirmation dialog is shown and the browser navigates back
    And   when I return to Part A the unsaved value is not present

    Notion: KAN-TC-78 | KAN-8 EC-3 | data: unsaved_signatory
    """
    page, user = logged_in_part_a_page
    data = part_a_unsaved_signatory_data

    with allure.step(f"Enter '{data.authorised_signatory}' as Authorised Signatory without saving"):
        part_a_page.fill_authorised_signatory(data.authorised_signatory)

    with allure.step("Press the browser back button"):
        message = part_a_page.go_back_and_handle_alert(action="dismiss")

    with allure.step("Verify no confirmation dialog was shown"):
        assert message == "", f"Expected no unsaved-changes dialog, got: {message!r}"

    with allure.step("Return to Part A"):
        part_a_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify the unsaved value is not present"):
        expect(part_a_page.authorised_signatory_input).not_to_have_value(data.authorised_signatory)


# ---------------------------------------------------------------------------
# TC-79  "← Dashboard" with unsaved data — DEPRECATED
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-79")
@pytest.mark.deprecated(reason="'← Dashboard' link and its Save & Exit dialog removed from Part A")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-79: Clicking Dashboard with unsaved Step 1 data shows Save & Exit dialog")
def test_tc79_dashboard_link_prompts_unsaved_dialog():
    """
    Deprecated — tested the '← Dashboard' link and its Save & Exit / Exit Without
    Saving / Cancel dialog, both removed from Part A. The original steps are in git
    history.

    Notion: KAN-TC-79
    """


# ---------------------------------------------------------------------------
# TC-80  Data entered in Part A after a session timeout and re-login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-80")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-80: Data entered in Part A is restored after a session timeout and re-login")
def test_tc80_data_after_session_timeout(
    part_a_page: PartAPage, logged_in_part_a_page, part_a_session_timeout_data: PartAData
):
    """
    Given I have filled fields on Part A without saving
    And   I leave the session idle for 20 minutes (session expires)
    When  I interact with the page, log in again and open Part A
    Then  either (a) the previously entered data is restored, OR
          (b) the form is blank (unsaved data could not be preserved)

    Notion: KAN-TC-80 | KAN-8 EC-2 | data: session_timeout_partial
    Note:   waits 20 minutes inside the test.
    """
    page, user = logged_in_part_a_page
    data = part_a_session_timeout_data
    login = LoginPage(page)

    with allure.step("Fill fields on Part A without saving"):
        part_a_page.fill_incorporation_no(data.incorporation_no)
        part_a_page.fill_authorised_signatory(data.authorised_signatory)

    with allure.step("Wait 20 minutes (1200 seconds) without any interaction"):
        time.sleep(1200)

    with allure.step("Interact with the portal — reload the page"):
        page.reload()

    with allure.step("Verify the session expired — login page with the session-expired banner"):
        expect(login.session_expired_message).to_be_visible()

    with allure.step("Log in again with valid credentials"):
        login.login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)

    with allure.step("Open Step 1 — Part A"):
        part_a_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify the data is either restored exactly or the form is blank"):
        restored = part_a_page.incorporation_no_input.input_value()
        # (a) restored — must match exactly; (b) blank — accepted per KAN-8 EC-2.
        if restored:
            assert restored == data.incorporation_no, (
                "If data is restored, it must match what was entered before the timeout"
            )
            expect(part_a_page.authorised_signatory_input).to_have_value(data.authorised_signatory)


# ---------------------------------------------------------------------------
# TC-426  Agency name and district from registration are read-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-426")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-426: Agency name and head office district from registration are shown read-only on Part A")
def test_tc426_registration_details_read_only(part_a_page: PartAPage, logged_in_part_a_fresh_page):
    """
    Given I have a pre-registered agency (head office in Maharashtra) that has not started Form-I
    When  I land on Part A
    Then  the agency name is shown read-only under the heading
    And   the head office District is pre-filled from registration, read-only,
          with the hint "Selected at registration — it decides your Registering Authority"
          (empty when "Other" was chosen as the district at registration)

    Notion: KAN-TC-426 | KAN-8 AC-2 | data: fresh_agency_user
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Verify the agency name is shown under the heading"):
        expect(part_a_page.agency_name_display).not_to_be_empty()
        if user.agency_name:
            expect(part_a_page.agency_name_display).to_have_text(user.agency_name)

    with allure.step("Verify the head office State is Maharashtra"):
        expect(part_a_page.head_office_state_select).to_have_value("Maharashtra")

    with allure.step(f"Verify District is carried over from registration ('{user.district}') and read-only"):
        if user.district == "Other":
            # "Other" at registration names no Maharashtra district, so nothing is carried over.
            expect(part_a_page.district_display).to_have_value("")
        elif user.district:
            expect(part_a_page.district_display).to_have_value(user.district)
        else:
            expect(part_a_page.district_display).not_to_have_value("")
        expect(part_a_page.district_display).not_to_be_editable()
        expect(part_a_page.district_hint).to_have_text(PartAPage.DISTRICT_FROM_REGISTRATION_HINT)


# ---------------------------------------------------------------------------
# TC-427  Head office outside Maharashtra shows the Primary Maharashtra Office block
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-427")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-427: Choosing a head office state outside Maharashtra shows the Primary Maharashtra Office block")
def test_tc427_head_office_outside_maharashtra(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_outside_maharashtra_data: PartAData
):
    """
    Given I am on Part A with the head office in Maharashtra
    When  I select a head office state other than Maharashtra
    Then  the Primary Maharashtra Office block appears and its fields become mandatory
    And   the head office District and Taluka become free text and the pincode is not limited to Maharashtra
    When  I switch the state back to Maharashtra
    Then  the block is hidden and District / Taluka are restored

    Notion: KAN-TC-427 | KAN-8 AC-4 | data: head_office_outside_maharashtra
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_outside_maharashtra_data

    with allure.step(f"Select head office State: {data.state}"):
        part_a_page.select_head_office_state(data.state)

    with allure.step("Verify the Primary Maharashtra Office block is shown with mandatory fields"):
        expect(part_a_page.mh_office_section).to_have_class(SHOWN)
        expect(part_a_page.mh_office_section).to_contain_text(PartAPage.MH_OFFICE_REQUIRED_TEXT)
        for field in (part_a_page.mh_address_line1_input, part_a_page.mh_district_select,
                      part_a_page.mh_taluka_select, part_a_page.mh_city_input, part_a_page.mh_pincode_input):
            expect(field).to_be_visible()
            expect(field).to_have_attribute("required", "")

    with allure.step("Verify head office District / Taluka are free text and the pincode is not limited to Maharashtra"):
        expect(part_a_page.district_input).to_be_visible()
        expect(part_a_page.district_display).to_be_hidden()
        expect(part_a_page.taluka_input).to_be_visible()
        expect(part_a_page.taluka_select).to_be_hidden()
        expect(part_a_page.district_hint).to_have_text(PartAPage.DISTRICT_OTHER_STATE_HINT)
        expect(part_a_page.pincode_hint).to_have_text(PartAPage.PIN_OTHER_STATE_HINT)
        expect(part_a_page.pincode_mh_tag).to_be_hidden()

    with allure.step(f"Choose District '{data.mh_office.district}' in the Maharashtra office block"):
        part_a_page.select_mh_district(data.mh_office.district)
        expect(part_a_page.mh_taluka_select).to_contain_text(data.mh_office.taluka)

    with allure.step("Switch the head office State back to Maharashtra"):
        part_a_page.select_head_office_state("Maharashtra")

    with allure.step("Verify the block is hidden and District / Taluka are restored"):
        expect(part_a_page.mh_office_section).not_to_have_class(SHOWN)
        expect(part_a_page.district_display).to_be_visible()
        expect(part_a_page.district_display).not_to_be_editable()
        expect(part_a_page.taluka_select).to_be_visible()
        expect(part_a_page.district_hint).to_have_text(PartAPage.DISTRICT_FROM_REGISTRATION_HINT)


# ---------------------------------------------------------------------------
# TC-428  Head office outside Maharashtra needs a Maharashtra office — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-428")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-428: Part A cannot be saved with a head office outside Maharashtra and no Maharashtra office")
def test_tc428_maharashtra_office_mandatory(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_outside_maharashtra_data: PartAData
):
    """
    Given I fill all mandatory fields with a head office outside Maharashtra
    When  I save without filling the Primary Maharashtra Office block
    Then  the save is rejected and the block's empty fields are highlighted in red
    When  I fill the Maharashtra office and save
    Then  Part A saves successfully

    Notion: KAN-TC-428 | KAN-8 EC-1 | data: head_office_outside_maharashtra
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_outside_maharashtra_data

    with allure.step(f"Fill all mandatory fields with head office in {data.state}; leave the Maharashtra office empty"):
        _fill_part_a(part_a_page, dataclasses.replace(data, mh_office=None))

    with allure.step("Click 'Save Part A & Continue'"):
        part_a_page.click_save_next()

    with allure.step("Verify the Maharashtra office fields are highlighted"):
        for name in MH_OFFICE_FIELD_NAMES:
            expect(part_a_page.rejected_field(name)).to_have_count(1)

    with allure.step("Fill all mandatory fields including the Primary Maharashtra Office, then save"):
        _fill_part_a(part_a_page, data)
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-429  Unsaved Part A data restored after "Save & Log out" or closing the tab
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-429")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-429: Unsaved Part A data is restored after \"Save & Log out\" or closing the tab")
def test_tc429_partial_data_persists(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_partial_data: PartAData
):
    """
    Given I have filled some Part A fields without saving
    When  I click "Save & Log out", log in again and open Part A
    Then  the values are restored exactly as entered
    When  I enter another value, close the tab and open the portal again
    Then  Part A shows all previously entered values

    Notion: KAN-TC-429 | KAN-8 AC-6 | data: partial_fields_only
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_partial_data
    login = LoginPage(page)

    with allure.step("Fill some Part A fields without saving"):
        part_a_page.fill_incorporation_no(data.incorporation_no)
        part_a_page.fill_authorised_signatory(data.authorised_signatory)

    with allure.step("Click 'Save & Log out'"):
        part_a_page.save_and_logout()
        expect(login.logged_out_message).to_be_visible()

    with allure.step("Log in again and open Part A"):
        login.login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        part_a_page.open()

    with allure.step("Verify the values are restored"):
        expect(part_a_page.incorporation_no_input).to_have_value(data.incorporation_no)
        expect(part_a_page.authorised_signatory_input).to_have_value(data.authorised_signatory)

    with allure.step(f"Enter Designation '{data.designation}', close the tab and open Part A in a new tab"):
        part_a_page.fill_designation(data.designation)
        new_tab = page.context.new_page()
        page.close()
        part_a_new_tab = PartAPage(new_tab)
        part_a_new_tab.open()

    with allure.step("Verify all previously entered values are shown"):
        try:
            expect(part_a_new_tab.incorporation_no_input).to_have_value(data.incorporation_no)
            expect(part_a_new_tab.authorised_signatory_input).to_have_value(data.authorised_signatory)
            expect(part_a_new_tab.designation_input).to_have_value(data.designation)
        finally:
            new_tab.close()


# ---------------------------------------------------------------------------
# TC-430  Incorporation details are not mandatory for a Proprietorship — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-430")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-430: Incorporation details are not mandatory for a Proprietorship")
def test_tc430_proprietorship_incorporation_optional(
    part_a_page: PartAPage,
    logged_in_part_a_fresh_mh_page,
    part_a_proprietorship_data: PartAData,
    part_a_valid_data: PartAData,
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I select Proprietorship
    Then  the Incorporation No. and Certificate are no longer marked mandatory
    When  I select another type
    Then  they are marked mandatory again
    When  I select Proprietorship, leave both empty and save
    Then  Part A saves successfully

    Notion: KAN-TC-430 | KAN-8 AC-8 | data: proprietorship_without_incorporation
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_proprietorship_data, user)

    with allure.step(f"Select '{data.legal_constitution}'"):
        part_a_page.select_legal_constitution(data.legal_constitution)

    with allure.step("Verify the incorporation fields are not marked mandatory"):
        expect(part_a_page.incorporation_no_required_mark).to_be_hidden()
        expect(part_a_page.incorporation_certificate_required_mark).to_be_hidden()

    with allure.step(f"Select '{part_a_valid_data.legal_constitution}'"):
        part_a_page.select_legal_constitution(part_a_valid_data.legal_constitution)

    with allure.step("Verify the incorporation fields are marked mandatory again"):
        expect(part_a_page.incorporation_no_required_mark).to_be_visible()
        expect(part_a_page.incorporation_certificate_required_mark).to_be_visible()

    with allure.step(f"Select '{data.legal_constitution}' again, fill the rest without incorporation details and save"):
        _fill_part_a(part_a_page, data)
        expect(part_a_page.incorporation_no_input).to_have_value("")
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-431  Branch premise type "Other" requires "Please Specify" — DESTRUCTIVE
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-431")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-431: Selecting \"Other\" as a branch office premise type requires \"Please Specify\"")
def test_tc431_branch_premise_other_requires_specify(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_branch_premise_other_data: PartAData
):
    """
    Given I am on Part A with all mandatory fields filled and one branch office added
    When  I select "Other" as its Office Premise Type
    Then  a mandatory "Please Specify" field appears; another type hides it
    When  I save with "Other" and "Please Specify" empty
    Then  the save is rejected and "Please Specify" is highlighted in red
    When  I fill "Please Specify" and save
    Then  Part A saves successfully

    Notion: KAN-TC-431 | KAN-8 EC-4 | data: branch_premise_other
    """
    page, user = logged_in_part_a_fresh_mh_page
    data = PartAFactory.for_user(part_a_branch_premise_other_data, user)
    branch = data.branches[0]

    with allure.step("Fill all mandatory fields and add a branch office with premise type Other"):
        _fill_part_a(part_a_page, dataclasses.replace(data, branches=[]))
        part_a_page.add_branch(branch.address, branch.district, branch.taluka, branch.city, branch.pincode,
                               branch.premise_type)

    with allure.step("Verify 'Please Specify' is shown and mandatory"):
        expect(part_a_page.branch_field(0, "office_premise_other")).to_be_visible()

    with allure.step(f"Select another premise type: {PartAPage.PREMISE_TYPES[1]}"):
        part_a_page.select_branch_premise(0, PartAPage.PREMISE_TYPES[1])
        expect(part_a_page.branch_field(0, "office_premise_other")).to_be_hidden()

    with allure.step("Select Other again, leave 'Please Specify' empty and save"):
        part_a_page.select_branch_premise(0, branch.premise_type)
        part_a_page.click_save_next()

    with allure.step("Verify the save is rejected and 'Please Specify' is highlighted"):
        expect(part_a_page.branch_field(0, "office_premise_other")).to_have_class(IS_BAD)

    with allure.step(f"Fill 'Please Specify' ('{branch.premise_other}') and save"):
        _clear_branches(part_a_page)
        _fill_part_a(part_a_page, data)
        part_a_page.click_save_next()

    with allure.step("Verify Part A is saved"):
        _expect_part_a_saved(page)

    with allure.step("Record Part A as completed in state store"):
        TestStateStore().mark_form_step_status(
            username=user.username, step="part_a", status="completed", data=PartAFactory.state_store_data(data)
        )


# ---------------------------------------------------------------------------
# TC-432  Certificate uploads accept only PDF, JPG and PNG
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-432")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-432: Certificate uploads accept only PDF, JPG and PNG files")
def test_tc432_certificate_file_types(
    part_a_page: PartAPage, logged_in_part_a_fresh_mh_page, part_a_valid_data: PartAData
):
    """
    Given I am on Part A with all other mandatory fields filled
    When  I look at the incorporation, TAN and GST certificate uploads
    Then  each offers only PDF, JPG and PNG files
    When  a DOCX file is chosen for each and I save
    Then  the files are rejected, each certificate field is highlighted and Part A is not saved

    Notion: KAN-TC-432 | KAN-8 EC-5 | data: certificate.docx
    """
    page, user = logged_in_part_a_fresh_mh_page
    certificates = {
        "incorporation_file": part_a_page.incorporation_certificate_input,
        "tan_file": part_a_page.tan_certificate_input,
        "gst_file": part_a_page.gst_certificate_input,
    }

    with allure.step("Verify each certificate upload offers only PDF, JPG and PNG"):
        for file_input in certificates.values():
            expect(file_input).to_have_attribute("accept", PartAPage.CERTIFICATE_ACCEPT)

    with allure.step("Fill all mandatory fields"):
        _fill_part_a(part_a_page, PartAFactory.for_user(part_a_valid_data, user))

    with allure.step(f"Choose {os.path.basename(UNSUPPORTED_CERTIFICATE)} for each certificate"):
        for file_input in certificates.values():
            message = part_a_page.set_file_and_handle_alert(file_input, UNSUPPORTED_CERTIFICATE)
            assert message == "", f"The DOCX is within 10 KB – 2 MB, so no size pop-up was expected: {message!r}"

    with allure.step("Click 'Save Part A & Continue'"):
        part_a_page.click_save_next()

    with allure.step("Verify each certificate field is highlighted"):
        for name in certificates:
            expect(part_a_page.rejected_field(name)).to_have_count(1)

    with allure.step("Verify Part A was not saved"):
        _expect_part_a_not_saved(page)


# ---------------------------------------------------------------------------
# TC-433  Certificate files outside 10 KB – 2 MB are rejected on selection
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-433")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-433: Certificate files larger than 2 MB or smaller than 10 KB are rejected on selection")
def test_tc433_certificate_size_limits(part_a_page: PartAPage, logged_in_part_a_page):
    """
    Given I am on Part A
    When  I choose a certificate file larger than 2 MB, or smaller than 10 KB
    Then  a pop-up names the file and the limit, and the field is cleared
    When  I choose a file within the limits
    Then  it is accepted without a pop-up
    And   the same applies to the TAN, incorporation and GST certificates

    Notion: KAN-TC-433 | KAN-8 EC-6 | data: oversized.pdf, valid_doc.pdf, certificate.pdf
    """
    page, user = logged_in_part_a_page
    certificates = {
        "TAN certificate": part_a_page.tan_certificate_input,
        "incorporation certificate": part_a_page.incorporation_certificate_input,
        "GST certificate": part_a_page.gst_certificate_input,
    }

    for label, file_input in certificates.items():
        with allure.step(f"{label}: choose a file larger than 2 MB"):
            message = part_a_page.set_file_and_handle_alert(file_input, OVERSIZED_FILE)
            assert PartAPage.FILE_TOO_LARGE_ALERT in message and os.path.basename(OVERSIZED_FILE) in message, (
                f"Expected the too-large pop-up for {os.path.basename(OVERSIZED_FILE)}, got: {message!r}"
            )
            expect(file_input).to_have_value("")

        with allure.step(f"{label}: choose a file smaller than 10 KB"):
            message = part_a_page.set_file_and_handle_alert(file_input, UNDERSIZED_FILE)
            assert PartAPage.FILE_TOO_SMALL_ALERT in message and os.path.basename(UNDERSIZED_FILE) in message, (
                f"Expected the too-small pop-up for {os.path.basename(UNDERSIZED_FILE)}, got: {message!r}"
            )
            expect(file_input).to_have_value("")

        with allure.step(f"{label}: choose a file within the limits"):
            message = part_a_page.set_file_and_handle_alert(file_input, VALID_CERTIFICATE)
            assert message == "", f"Expected no pop-up for a valid file, got: {message!r}"
            expect(file_input).not_to_have_value("")


# ---------------------------------------------------------------------------
# TC-434  A pincode outside the Maharashtra range is flagged
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-434")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-434: A pincode outside the Maharashtra range is flagged")
def test_tc434_pincode_outside_maharashtra(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_pincode_out_of_range_data: PartAData
):
    """
    Given my head office is in Maharashtra
    When  I enter a head office pincode outside 400000–445999
    Then  the field is marked invalid and the hint reads "✗ Not a valid Maharashtra pincode (400000–445999)"
    When  I enter a pincode inside the range
    Then  the hint reads "✓ Valid Maharashtra pincode"
    And   an out-of-range pincode on a branch card is marked invalid

    Notion: KAN-TC-434 | KAN-8 EC-9 | data: pincode_outside_maharashtra
    """
    page, user = logged_in_part_a_fresh_page
    data = part_a_pincode_out_of_range_data

    with allure.step(f"Enter head office pincode {data.invalid_value}"):
        part_a_page.fill_pincode(data.invalid_value)

    with allure.step("Verify the pincode is marked invalid"):
        expect(part_a_page.pincode_input).to_have_class(PIN_ERR)
        expect(part_a_page.pincode_hint).to_have_text(data.expected_error)

    with allure.step(f"Enter head office pincode {data.pincode}"):
        part_a_page.fill_pincode(data.pincode)

    with allure.step("Verify the pincode is accepted"):
        expect(part_a_page.pincode_input).not_to_have_class(PIN_ERR)
        expect(part_a_page.pincode_hint).to_have_text(PartAPage.PIN_VALID_HINT)

    with allure.step(f"Add a branch office and enter pincode {data.invalid_value}"):
        part_a_page.click_add_branch()
        part_a_page.fill_branch_field(0, "pincode", data.invalid_value)

    with allure.step("Verify the branch pincode is marked invalid"):
        expect(part_a_page.branch_field(0, "pincode")).to_have_class(PIN_ERR)


# ---------------------------------------------------------------------------
# TC-435  Branch office cards can be removed and are renumbered
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-435")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-435: Branch office cards can be removed and the remaining cards are renumbered")
def test_tc435_branch_remove_and_renumber(part_a_page: PartAPage, logged_in_part_a_fresh_page):
    """
    Given I am on Part A
    When  I add three branch offices and remove the second one
    Then  that card is removed and the remaining cards are numbered 1 and 2

    Notion: KAN-TC-435 | KAN-8 AC-7 | data: fresh_agency_user
    """
    page, user = logged_in_part_a_fresh_page

    with allure.step("Click 'Add Branch Office' three times"):
        for _ in range(3):
            part_a_page.click_add_branch()

    with allure.step("Verify three cards numbered 1, 2 and 3"):
        expect(part_a_page.branch_cards).to_have_count(3)
        expect(part_a_page.branch_numbers).to_have_text(["1", "2", "3"])

    with allure.step("Remove Branch Office 2"):
        part_a_page.remove_branch(1)

    with allure.step("Verify two cards remain, numbered 1 and 2"):
        expect(part_a_page.branch_cards).to_have_count(2)
        expect(part_a_page.branch_numbers).to_have_text(["1", "2"])


# ---------------------------------------------------------------------------
# TC-436  Part A text fields convert and restrict input as you type
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-436")
@allure.story("Step 1 - Agency Identity")
@allure.title("TC-436: Part A text fields convert and restrict input as you type")
def test_tc436_as_you_type_input_rules(
    part_a_page: PartAPage, logged_in_part_a_fresh_page, part_a_as_you_type_cases: list[TypedInput]
):
    """
    Given I am on Part A
    When  I type raw input into the Incorporation No., TAN, GSTIN, Aadhaar and Pincode fields
    Then  each field shows the value upper-cased and/or stripped to its allowed characters and length

    Notion: KAN-TC-436 | KAN-8 field validations | data: as_you_type_cases
    """
    page, user = logged_in_part_a_fresh_page

    for case in part_a_as_you_type_cases:
        with allure.step(f"Type '{case.typed}' into {case.field} — expect '{case.shown}'"):
            part_a_page.type_into(case.field, case.typed)
            expect(getattr(part_a_page, case.field)).to_have_value(case.shown)

    with allure.step("Verify the upper-cased GSTIN is recognised as valid"):
        expect(part_a_page.gstin_hint).to_have_text(PartAPage.GSTIN_VALID_HINT)
