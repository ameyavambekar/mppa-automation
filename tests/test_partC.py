import re

import allure
import pytest
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.partB_page import PART_B_URL, PartBPage
from pages.partC_page import PART_C_URL, PartCPage
from test_data.partC_factory import PartCData, PartCFactory, TypedInput
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Step 3 - Operations & Infrastructure"
ON_PART_C = re.compile(rf"{re.escape(PART_C_URL)}")
PART_F_URL = re.compile(rf"{re.escape(FORMS_BASE)}/partF\.php")


def _fill(part_c: PartCPage, data: PartCData) -> None:
    part_c.fill_part_c_form(
        data.placement_type, data.service_mode, data.sectors, data.service_models, data.charges_displayed,
        sector_other=data.sector_other, digital_platform_details=data.digital_platform_details,
        training=data.training, training_mode=data.training_mode, training_capacity=data.training_capacity,
        training_sectors=data.training_sectors, training_address=data.training_address,
        mobilization=data.mobilization, mobilization_address=data.mobilization_address,
        other_services=data.other_services, website=data.website,
    )


def _expect_part_c_saved(page, part_c: PartCPage, user) -> None:
    """A successful save stays on Part C with "Part C saved." and "Next: Part F →"."""
    expect(part_c.success_message).to_have_text(PartCPage.SAVED_MESSAGE)
    expect(page).to_have_url(ON_PART_C)
    expect(part_c.next_part_f_link).to_be_visible()
    expect(part_c.client_errors).to_be_hidden()
    TestStateStore().mark_form_step_status(username=user.username, step="part_c", status="completed")


def _reopen(page, part_c: PartCPage) -> None:
    part_c.open()
    page.wait_for_load_state("networkidle")
    part_c.make_editable()


def _expect_blocked(page, part_c: PartCPage, *messages: str) -> None:
    """The save was blocked client-side: still on Part C, each message is in the summary box."""
    expect(page).to_have_url(ON_PART_C)
    expect(part_c.client_errors).to_be_visible()
    expect(part_c.client_errors).to_contain_text(PartCPage.ERRORS_HEADING)
    for message in messages:
        expect(part_c.client_errors).to_contain_text(f"• {message}")


# ---------------------------------------------------------------------------
# TC-120  Part C saves with the mandatory fields — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-120")
@allure.story(STORY)
@allure.title("TC-120: Part C saves successfully when all mandatory fields are filled")
def test_tc120_minimal_save(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given I am on Part C with every Yes/No question at No
    When  I fill only the mandatory fields and click "Save Part C & Continue"
    Then  Part C is saved ("Part C saved.") and shows ✓ in the progress bar on Part F

    Notion: KAN-TC-120 | KAN-20 AC-8 | data: minimal
    """
    page, user = logged_in_part_c_page
    data = part_c_minimal_data

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, data)

    with allure.step("Verify digital platform, training and mobilization are No with their fields hidden"):
        for radio in (part_c_page.digital_platform_radio("0"), part_c_page.training_radio("0"),
                      part_c_page.mobilization_radio("0")):
            expect(radio).to_be_checked()
        for block in (part_c_page.digital_block, part_c_page.training_block, part_c_page.mobilization_block):
            expect(block).to_be_hidden()

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Click 'Next: Part F →' — Part C shows ✓ in the progress bar"):
        part_c_page.next_part_f_link.click()
        expect(page).to_have_url(PART_F_URL)
        expect(part_c_page.completed_step_link("Part C")).to_contain_text("✓")


# ---------------------------------------------------------------------------
# TC-122  Blank save shows every mandatory error and the summary box
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-122")
@allure.story(STORY)
@allure.title("TC-122: Saving a blank Part C shows an inline error on every mandatory field and an error summary")
def test_tc122_blank_save_shows_all_errors(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given nothing is entered on Part C
    When  I click "Save Part C & Continue"
    Then  the save is blocked with inline errors on Type of Placement, Service Mode and Sectors Served
    And   the summary box lists all three and Type of Placement gets the focus

    Notion: KAN-TC-122 | KAN-20 AC-6 | data: none
    """
    page, user = logged_in_part_c_page

    with allure.step("Verify no errors are shown before saving"):
        expect(part_c_page.field_errors).to_have_count(0)
        expect(part_c_page.client_errors).to_be_hidden()

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify the three inline errors"):
        expect(part_c_page.field_error("placement_type")).to_have_text(PartCPage.PLACEMENT_TYPE_REQUIRED_ERROR)
        expect(part_c_page.field_error("service_mode")).to_have_text(PartCPage.SERVICE_MODE_REQUIRED_ERROR)
        expect(part_c_page.sectors_error).to_have_text(PartCPage.SECTORS_REQUIRED_ERROR)
        expect(part_c_page.sectors_grid).to_have_class(re.compile(r"\bgrp-invalid\b"))
        expect(part_c_page.field_errors).to_have_count(3)

    with allure.step("Verify the summary box and the focus"):
        _expect_blocked(page, part_c_page, PartCPage.PLACEMENT_TYPE_REQUIRED_ERROR,
                        PartCPage.SERVICE_MODE_REQUIRED_ERROR, PartCPage.SECTORS_REQUIRED_ERROR)
        expect(part_c_page.placement_type_select).to_be_focused()


# ---------------------------------------------------------------------------
# TC-124  Type of Placement is mandatory
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-124")
@allure.story(STORY)
@allure.title("TC-124: Leaving Type of Placement unselected blocks saving")
def test_tc124_placement_type_required(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given every other mandatory field is filled
    When  I save with Type of Placement at "-- Select --", then select a type
    Then  the save is blocked with "Please select the type of placement." and the error clears

    Notion: KAN-TC-124 | data: minimal without placement type
    """
    page, user = logged_in_part_c_page
    data = part_c_minimal_data

    with allure.step("Fill every mandatory field except Type of Placement"):
        _fill(part_c_page, data)
        part_c_page.placement_type_select.select_option(value="")

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_c_page.field_error("placement_type")).to_have_text(PartCPage.PLACEMENT_TYPE_REQUIRED_ERROR)
        _expect_blocked(page, part_c_page, PartCPage.PLACEMENT_TYPE_REQUIRED_ERROR)

    with allure.step(f"Select '{data.placement_type}' — the error disappears"):
        part_c_page.select_placement_type(data.placement_type)
        expect(part_c_page.field_error("placement_type")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-125  At least one sector is mandatory
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-125")
@allure.story(STORY)
@allure.title("TC-125: Leaving every sector unticked blocks saving")
def test_tc125_sector_required(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given every other mandatory field is filled
    When  I save with no sector ticked, then tick one
    Then  the save is blocked with "Select at least one sector." and the error clears

    Notion: KAN-TC-125 | data: minimal without sectors
    """
    page, user = logged_in_part_c_page
    data = part_c_minimal_data
    data.sectors = []

    with allure.step("Fill every mandatory field except the sectors"):
        _fill(part_c_page, data)

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_c_page.sectors_error).to_have_text(PartCPage.SECTORS_REQUIRED_ERROR)
        expect(part_c_page.sectors_grid).to_have_class(re.compile(r"\bgrp-invalid\b"))
        _expect_blocked(page, part_c_page, PartCPage.SECTORS_REQUIRED_ERROR)

    with allure.step("Tick 'Healthcare / Nursing' — the error disappears"):
        part_c_page.set_sector("Healthcare / Nursing")
        expect(part_c_page.sectors_error).to_have_count(0)
        expect(part_c_page.sectors_grid).not_to_have_class(re.compile(r"\bgrp-invalid\b"))


# ---------------------------------------------------------------------------
# TC-127  Training "Yes" reveals mandatory fields — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-127")
@allure.story(STORY)
@allure.title("TC-127: Selecting \"Yes\" for training reveals Mode, Capacity, Sectors and Address — all mandatory")
def test_tc127_training_fields_mandatory(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_training_data: PartCData
):
    """
    Given every other mandatory field is filled
    When  I select Yes for training, save with its fields blank, then fill them and save
    Then  the training fields appear, the first save is blocked with four errors, the second save succeeds

    Notion: KAN-TC-127 | KAN-20 AC-3 | data: with_training
    """
    page, user = logged_in_part_c_page
    data = part_c_training_data

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, PartCFactory.minimal())

    with allure.step("Verify training is No and its fields are hidden"):
        expect(part_c_page.training_radio("0")).to_be_checked()
        expect(part_c_page.training_block).to_be_hidden()

    with allure.step("Select Yes — the training fields appear"):
        part_c_page.select_training(True)
        for field in (part_c_page.training_mode_select, part_c_page.training_capacity_input,
                      part_c_page.training_sectors_input, part_c_page.training_address_same_checkbox,
                      part_c_page.training_address_textarea):
            expect(field).to_be_visible()
        expect(part_c_page.training_address_same_checkbox).not_to_be_checked()

    with allure.step("Save with the training fields blank"):
        part_c_page.click_submit()
        _expect_blocked(page, part_c_page, PartCPage.TRAINING_MODE_REQUIRED_ERROR,
                        PartCPage.TRAINING_CAPACITY_REQUIRED_ERROR, PartCPage.TRAINING_SECTORS_REQUIRED_ERROR,
                        PartCPage.TRAINING_ADDRESS_REQUIRED_ERROR)

    with allure.step("Fill the training fields and save"):
        part_c_page.select_training_mode(data.training_mode)
        part_c_page.fill_training_capacity(data.training_capacity)
        part_c_page.fill_training_sectors(data.training_sectors)
        part_c_page.fill_training_address(data.training_address)
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-128  Training back to "No" — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-128")
@allure.story(STORY)
@allure.title("TC-128: Switching training from \"Yes\" back to \"No\" hides the training fields so they no longer block saving")
def test_tc128_training_back_to_no(part_c_page: PartCPage, logged_in_part_c_page, part_c_training_data: PartCData):
    """
    Given every other mandatory field is filled
    When  I select Yes for training, fill only the capacity, switch back to No and save
    Then  the training fields are hidden and Part C saves without training errors

    Notion: KAN-TC-128 | KAN-20 AC-3, EC-9 | data: with_training (capacity only)
    """
    page, user = logged_in_part_c_page

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, PartCFactory.minimal())

    with allure.step(f"Select Yes for training and fill only the capacity '{part_c_training_data.training_capacity}'"):
        part_c_page.select_training(True)
        part_c_page.fill_training_capacity(part_c_training_data.training_capacity)
        expect(part_c_page.training_capacity_input).to_have_value(part_c_training_data.training_capacity)

    with allure.step("Switch training back to No — the fields are hidden"):
        part_c_page.select_training(False)
        expect(part_c_page.training_block).to_be_hidden()

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-130  Annual Training Capacity input rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-130")
@allure.story(STORY)
@allure.title("TC-130: Annual Training Capacity keeps digits only, allows at most 6 and rejects 0")
def test_tc130_training_capacity_rules(
    part_c_page: PartCPage, logged_in_part_c_page,
    part_c_training_capacity_typed_cases: list[TypedInput], part_c_training_capacity_zero_data: PartCData,
):
    """
    Given training is Yes
    When  I type letters, symbols, 7 digits, a negative and a decimal, then 0, then 999999
    Then  only up to 6 digits are kept, 0 shows the range error and 999999 clears it

    Notion: KAN-TC-130 | KAN-20 EC-4, EC-5 | data: training_capacity_typed_cases, training_capacity_zero
    """
    page, user = logged_in_part_c_page
    data = part_c_training_capacity_zero_data

    with allure.step("Select Yes for training"):
        part_c_page.select_training(True)

    for case in part_c_training_capacity_typed_cases:
        with allure.step(f"Type '{case.typed}' — field shows '{case.shown}'"):
            part_c_page.type_key_by_key(part_c_page.training_capacity_input, case.typed)
            expect(part_c_page.training_capacity_input).to_have_value(case.shown)

    with allure.step(f"Enter '{data.invalid_values[0]}' and leave the field"):
        part_c_page.fill_training_capacity(data.invalid_values[0])
        expect(part_c_page.field_error("training_capacity")).to_have_text(data.expected_error)

    with allure.step(f"Enter '{data.valid_values[0]}' — the error disappears"):
        part_c_page.fill_training_capacity(data.valid_values[0])
        expect(part_c_page.field_error("training_capacity")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-135  Service Mode is mandatory
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-135")
@allure.story(STORY)
@allure.title("TC-135: Leaving Service Mode unselected blocks saving")
def test_tc135_service_mode_required(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given every other mandatory field is filled
    When  I save with Service Mode at "-- Select --", then select a mode
    Then  the save is blocked with "Please select the service mode." and the error clears

    Notion: KAN-TC-135 | data: minimal without service mode
    """
    page, user = logged_in_part_c_page

    with allure.step("Fill every mandatory field except Service Mode"):
        _fill(part_c_page, part_c_minimal_data)
        part_c_page.service_mode_select.select_option(value="")

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify the save is blocked"):
        expect(part_c_page.field_error("service_mode")).to_have_text(PartCPage.SERVICE_MODE_REQUIRED_ERROR)
        _expect_blocked(page, part_c_page, PartCPage.SERVICE_MODE_REQUIRED_ERROR)

    with allure.step("Select 'Both Online & Offline' — the error disappears"):
        part_c_page.select_service_mode("Both Online & Offline")
        expect(part_c_page.field_error("service_mode")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-136  Optional fields left blank — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-136")
@allure.story(STORY)
@allure.title("TC-136: Leaving Other Services and Website blank does not block saving")
def test_tc136_optional_fields_blank(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given every mandatory field is filled
    When  I leave Other Services and Website / URL blank and save
    Then  no error is shown for them and Part C is saved

    Notion: KAN-TC-136 | data: minimal
    """
    page, user = logged_in_part_c_page

    with allure.step("Fill the mandatory fields; leave Other Services and Website blank"):
        _fill(part_c_page, part_c_minimal_data)
        expect(part_c_page.other_services_textarea).to_have_value("")
        expect(part_c_page.website_input).to_have_value("")

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-137  Other Services is saved and restored — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-137")
@allure.story(STORY)
@allure.title("TC-137: Other Services text is saved and shown again when Part C is reopened")
def test_tc137_other_services_restored(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_other_services_data: PartCData
):
    """
    Given every mandatory field is filled
    When  I enter Other Services, save and reopen Part C
    Then  the counter shows 52 / 1000 and the text is shown again after reopening

    Notion: KAN-TC-137 | data: with_other_services
    """
    page, user = logged_in_part_c_page
    data = part_c_other_services_data

    with allure.step(f"Fill the mandatory fields and Other Services '{data.other_services}'"):
        _fill(part_c_page, data)
        expect(part_c_page.char_counter(part_c_page.other_services_textarea)).to_have_text(
            f"{len(data.other_services)} / 1000")

    with allure.step("Save Part C"):
        part_c_page.click_submit()
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Reopen Part C — Other Services is restored"):
        _reopen(page, part_c_page)
        expect(part_c_page.other_services_textarea).to_have_value(data.other_services)


# ---------------------------------------------------------------------------
# TC-138  "← Part B" returns to Part B
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-138")
@allure.story(STORY)
@allure.title("TC-138: \"← Part B\" returns to Part B with its saved data intact")
def test_tc138_back_to_part_b(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given I am on Part C
    When  I click "← Part B"
    Then  Part B opens without a dialog and shows the saved key person

    Notion: KAN-TC-138 | KAN-20 AC-9
    """
    page, user = logged_in_part_c_page
    part_b = PartBPage(page)

    with allure.step("Click '← Part B'"):
        message = part_c_page.click_and_handle_alert(part_c_page.back_to_part_b_link)
        assert message == "", f"Unexpected dialog: {message}"

    with allure.step("Verify Part B opens with the saved key person"):
        expect(page).to_have_url(re.compile(rf"{re.escape(PART_B_URL)}"))
        expect(part_b.title).to_have_text("Step 2 — Part B: Key Persons")
        expect(part_b.full_name_input(0)).not_to_have_value("")


# ---------------------------------------------------------------------------
# TC-142  Every section filled — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-142")
@allure.story(STORY)
@allure.title("TC-142: Part C saves with every section filled: Other sector, all three Yes blocks and website")
def test_tc142_full_save_restored(part_c_page: PartCPage, logged_in_part_c_page, part_c_full_data: PartCData):
    """
    Given I am on Part C
    When  I fill every section (all sectors incl. Other, all agency types, all three Yes blocks, website) and save
    Then  Part C is saved and every value is shown again when I reopen it

    Notion: KAN-TC-142 | KAN-20 AC-8 | data: full
    """
    page, user = logged_in_part_c_page
    data = part_c_full_data

    with allure.step("Fill every section"):
        _fill(part_c_page, data)

    with allure.step("Save Part C"):
        part_c_page.click_submit()
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Reopen Part C"):
        _reopen(page, part_c_page)

    with allure.step("Verify Placement Services"):
        expect(part_c_page.placement_type_select).to_have_value(data.placement_type)
        expect(part_c_page.service_mode_select).to_have_value(data.service_mode)
        for sector in data.sectors:
            expect(part_c_page.sector_checkbox(sector)).to_be_checked()
        expect(part_c_page.sector_other_input).to_have_value(data.sector_other)

    with allure.step("Verify Service Charges"):
        for model in data.service_models:
            expect(part_c_page.service_model_checkbox(model)).to_be_checked()
        expect(part_c_page.charges_displayed_radio("yes")).to_be_checked()

    with allure.step("Verify the digital platform, training and mobilization blocks"):
        expect(part_c_page.digital_platform_radio("1")).to_be_checked()
        expect(part_c_page.digital_platform_details_textarea).to_have_value(data.digital_platform_details)
        expect(part_c_page.training_radio("1")).to_be_checked()
        expect(part_c_page.training_mode_select).to_have_value(data.training_mode)
        expect(part_c_page.training_capacity_input).to_have_value(data.training_capacity)
        expect(part_c_page.training_sectors_input).to_have_value(data.training_sectors)
        expect(part_c_page.training_address_textarea).to_have_value(data.training_address)
        expect(part_c_page.mobilization_radio("1")).to_be_checked()
        expect(part_c_page.mobilization_address_same_checkbox).to_be_checked()

    with allure.step("Verify Other Services and Website"):
        expect(part_c_page.other_services_textarea).to_have_value(data.other_services)
        expect(part_c_page.website_input).to_have_value(data.website)


# ---------------------------------------------------------------------------
# TC-444  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-444")
@allure.story(STORY)
@allure.title("TC-444: Part C shows the heading, progress bar, back link, six sections and save button")
def test_tc444_page_layout(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given I am on Part C
    When  I look at the page
    Then  the heading, "← Part B", progress bar, six section headings and save button are shown

    Notion: KAN-TC-444 | KAN-20 AC-1
    """
    page, user = logged_in_part_c_page

    with allure.step("Verify the heading and '← Part B'"):
        expect(part_c_page.title).to_have_text("Step 3 — Part C: Operations & Infrastructure")
        expect(part_c_page.back_to_part_b_link).to_be_visible()

    with allure.step("Verify the progress bar"):
        expect(part_c_page.progress_step("Register")).to_contain_text("✓")
        expect(part_c_page.completed_step_link("Part A")).to_contain_text("✓")
        expect(part_c_page.completed_step_link("Part B")).to_contain_text("✓")
        expect(part_c_page.progress_step("Part C").or_(part_c_page.completed_step_link("Part C"))).to_be_visible()
        for label in ("Part F", "Documents", "Photos", "Declaration", "Preview", "Payment"):
            expect(part_c_page.progress_step(label)).to_be_visible()

    with allure.step("Verify the six sections, in order"):
        expect(part_c_page.section_headings).to_have_text([
            "Placement Services", "Service Charges", "Online & Digital Platform",
            "Training Centre", "Mobilization Centre", "Other Services",
        ])

    with allure.step("Verify the save button"):
        expect(part_c_page.submit_button).to_have_text("Save Part C & Continue")


# ---------------------------------------------------------------------------
# TC-445  Default state of a never-saved Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-445")
@allure.story(STORY)
@allure.title("TC-445: Part C opens with no selections and every Yes/No question set to No")
def test_tc445_default_state(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given Part C has never been saved
    When  I open Part C
    Then  nothing is selected or ticked, the three Yes/No questions are No, and conditional fields are hidden

    Notion: KAN-TC-445 | KAN-20 AC-2 | data: user with a never-saved Part C
    """
    page, user = logged_in_part_c_page

    with allure.step("Verify the dropdowns show '-- Select --'"):
        expect(part_c_page.placement_type_select).to_have_value("")
        expect(part_c_page.service_mode_select).to_have_value("")

    with allure.step("Verify no checkbox is ticked"):
        expect(part_c_page.select_all_sectors_checkbox).not_to_be_checked()
        for boxes in (part_c_page.sector_checkboxes, part_c_page.service_model_checkboxes):
            for index in range(boxes.count()):
                expect(boxes.nth(index)).not_to_be_checked()

    with allure.step("Verify the radios"):
        expect(part_c_page.charges_displayed_radio("yes")).not_to_be_checked()
        expect(part_c_page.charges_displayed_radio("no")).not_to_be_checked()
        for radio in (part_c_page.digital_platform_radio("0"), part_c_page.training_radio("0"),
                      part_c_page.mobilization_radio("0")):
            expect(radio).to_be_checked()

    with allure.step("Verify the conditional fields are hidden"):
        for block in (part_c_page.sector_other_wrapper, part_c_page.digital_block,
                      part_c_page.training_block, part_c_page.mobilization_block):
            expect(block).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-446  Select All
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-446")
@allure.story(STORY)
@allure.title("TC-446: \"Select All\" ticks every sector except Other and follows the individual boxes")
def test_tc446_select_all_sectors(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given no sector is ticked
    When  I tick Select All, untick and re-tick one sector, then untick Select All
    Then  Select All ticks all 15 sectors except Other and follows the individual boxes

    Notion: KAN-TC-446 | KAN-20 AC-5, EC-2
    """
    page, user = logged_in_part_c_page
    regular = [s for s in PartCPage.SECTORS if s != "Other"]

    with allure.step("Tick Select All"):
        part_c_page.set_select_all_sectors(True)

    with allure.step("Verify all 15 sectors are ticked, Other is not and its field stays hidden"):
        for sector in regular:
            expect(part_c_page.sector_checkbox(sector)).to_be_checked()
        expect(part_c_page.sector_checkbox("Other")).not_to_be_checked()
        expect(part_c_page.sector_other_wrapper).to_be_hidden()

    with allure.step("Untick 'Retail / Sales' — Select All unticks"):
        part_c_page.set_sector("Retail / Sales", False)
        expect(part_c_page.select_all_sectors_checkbox).not_to_be_checked()

    with allure.step("Tick 'Retail / Sales' again — Select All ticks"):
        part_c_page.set_sector("Retail / Sales", True)
        expect(part_c_page.select_all_sectors_checkbox).to_be_checked()

    with allure.step("Untick Select All — every sector unticks"):
        part_c_page.set_select_all_sectors(False)
        for sector in regular:
            expect(part_c_page.sector_checkbox(sector)).not_to_be_checked()


# ---------------------------------------------------------------------------
# TC-447  "Other" sector field — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-447")
@allure.story(STORY)
@allure.title("TC-447: Ticking Other shows a mandatory \"specify\" field; unticking it hides the field")
def test_tc447_other_sector_field(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given every other mandatory field is filled
    When  I tick Other and save with the specify field blank, then untick Other and save
    Then  the field appears and blocks the first save; once hidden it no longer blocks saving

    Notion: KAN-TC-447 | KAN-20 EC-3 | data: minimal
    """
    page, user = logged_in_part_c_page

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, part_c_minimal_data)

    with allure.step("Tick Other — the specify field appears"):
        part_c_page.set_sector("Other", True)
        expect(part_c_page.sector_other_input).to_be_visible()
        expect(part_c_page.sector_other_input).to_have_attribute("maxlength", "200")

    with allure.step("Save with the specify field blank"):
        part_c_page.click_submit()
        expect(part_c_page.sector_other_error).to_have_text(PartCPage.SECTOR_OTHER_REQUIRED_ERROR)
        _expect_blocked(page, part_c_page, PartCPage.SECTOR_OTHER_REQUIRED_ERROR)

    with allure.step("Untick Other — the field is hidden"):
        part_c_page.set_sector("Other", False)
        expect(part_c_page.sector_other_wrapper).to_be_hidden()

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-448  "Other" sector text rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-448")
@allure.story(STORY)
@allure.title("TC-448: The Other sector text must be 2–200 allowed characters")
def test_tc448_other_sector_text_rules(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_sector_other_invalid_data: PartCData
):
    """
    Given Other is ticked
    When  I enter one character, then a disallowed character, then valid text
    Then  the length error, then the character error is shown, and valid text clears it

    Notion: KAN-TC-448 | data: sector_other_invalid
    """
    page, user = logged_in_part_c_page
    data = part_c_sector_other_invalid_data
    errors = (PartCPage.MIN_2_CHARS_ERROR, PartCPage.SECTOR_OTHER_CHARS_ERROR)

    with allure.step("Tick Other"):
        part_c_page.set_sector("Other", True)

    for value, error in zip(data.invalid_values, errors):
        with allure.step(f"Enter '{value}' — '{error}'"):
            part_c_page.fill_sector_other(value)
            expect(part_c_page.sector_other_error).to_have_text(error)

    with allure.step(f"Enter '{data.valid_values[0]}' — the error disappears"):
        part_c_page.fill_sector_other(data.valid_values[0])
        expect(part_c_page.sector_other_error).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-449  Digital platform details — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-449")
@allure.story(STORY)
@allure.title("TC-449: Selecting \"Yes\" for a digital platform requires at least 10 characters of details")
def test_tc449_digital_platform_details(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_digital_platform_data: PartCData
):
    """
    Given every other mandatory field is filled
    When  I select Yes for digital platform, save blank, enter 9 characters, then valid details and save
    Then  the details field appears, blank and short values are rejected, and valid details save

    Notion: KAN-TC-449 | data: with_digital_platform
    """
    page, user = logged_in_part_c_page
    data = part_c_digital_platform_data

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, PartCFactory.minimal())

    with allure.step("Select Yes — Online Platform Details appears with a 0 / 1000 counter"):
        part_c_page.select_digital_platform(True)
        expect(part_c_page.digital_platform_details_textarea).to_be_visible()
        expect(part_c_page.char_counter(part_c_page.digital_platform_details_textarea)).to_have_text("0 / 1000")

    with allure.step("Save with the details blank"):
        part_c_page.click_submit()
        _expect_blocked(page, part_c_page, PartCPage.DIGITAL_DETAILS_REQUIRED_ERROR)

    with allure.step(f"Enter '{data.invalid_values[0]}' (9 characters)"):
        part_c_page.fill_digital_platform_details(data.invalid_values[0])
        expect(part_c_page.field_error("digital_platform_details")).to_have_text(data.expected_error)

    with allure.step("Enter valid details and save"):
        part_c_page.fill_digital_platform_details(data.digital_platform_details)
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-450  Training address same as registered office — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-450")
@allure.story(STORY)
@allure.title("TC-450: \"Training centre address is same as registered office\" hides the address and removes its requirement")
def test_tc450_training_same_address(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_training_same_address_data: PartCData
):
    """
    Given training is Yes with Mode, Capacity and Sectors filled
    When  I tick "same as registered office" and save, reopen, untick it and save blank
    Then  the address is hidden and not required; unticked, it is shown again and required

    Notion: KAN-TC-450 | KAN-20 AC-4 | data: training_same_address
    """
    page, user = logged_in_part_c_page
    data = part_c_training_same_address_data

    with allure.step("Fill the mandatory fields and training, ticking 'same as registered office'"):
        _fill(part_c_page, data)
        expect(part_c_page.training_address_same_checkbox).to_be_checked()
        expect(part_c_page.training_address_field).to_be_hidden()

    with allure.step("Save Part C"):
        part_c_page.click_submit()
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Reopen Part C and untick 'same as registered office'"):
        _reopen(page, part_c_page)
        part_c_page.set_training_address_same(False)
        expect(part_c_page.training_address_textarea).to_be_visible()

    with allure.step("Save with the address blank"):
        part_c_page.fill_training_address("")
        part_c_page.click_submit()
        _expect_blocked(page, part_c_page, PartCPage.TRAINING_ADDRESS_REQUIRED_ERROR)


# ---------------------------------------------------------------------------
# TC-451  Mobilization centre address — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-451")
@allure.story(STORY)
@allure.title("TC-451: Selecting \"Yes\" for a mobilization centre requires an address unless it is the registered office")
def test_tc451_mobilization_address(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_mobilization_same_address_data: PartCData
):
    """
    Given every other mandatory field is filled
    When  I select Yes for mobilization, save with the address blank, then tick "same as registered office" and save
    Then  the address is required until the box is ticked, then hidden, and Part C saves

    Notion: KAN-TC-451 | data: mobilization_same_address
    """
    page, user = logged_in_part_c_page

    with allure.step("Fill the mandatory fields"):
        _fill(part_c_page, PartCFactory.minimal())

    with allure.step("Select Yes for mobilization — the checkbox and address appear"):
        part_c_page.select_mobilization(True)
        expect(part_c_page.mobilization_address_same_checkbox).to_be_visible()
        expect(part_c_page.mobilization_address_same_checkbox).not_to_be_checked()
        expect(part_c_page.mobilization_address_textarea).to_be_visible()

    with allure.step("Save with the address blank"):
        part_c_page.click_submit()
        _expect_blocked(page, part_c_page, PartCPage.MOBILIZATION_ADDRESS_REQUIRED_ERROR)

    with allure.step("Tick 'same as registered office' — the address is hidden"):
        part_c_page.set_mobilization_address_same(True)
        expect(part_c_page.mobilization_address_field).to_be_hidden()

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify Part C is saved"):
        _expect_part_c_saved(page, part_c_page, user)


# ---------------------------------------------------------------------------
# TC-452  Centre address rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-452")
@allure.story(STORY)
@allure.title("TC-452: Centre addresses must be 10–400 allowed characters")
def test_tc452_centre_address_rules(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_centre_address_invalid_data: PartCData
):
    """
    Given mobilization is Yes with the same-address box unticked
    When  I enter 9 characters, then angle brackets, then an address with a semicolon
    Then  the length error, then the character error is shown, and the valid address clears it

    Notion: KAN-TC-452 | KAN-20 EC-7 | data: centre_address_invalid
    """
    page, user = logged_in_part_c_page
    data = part_c_centre_address_invalid_data
    errors = (PartCPage.ADDRESS_MIN_ERROR.format(n=len(data.invalid_values[0])), PartCPage.ADDRESS_CHARS_ERROR)

    with allure.step("Select Yes for mobilization"):
        part_c_page.select_mobilization(True)

    for value, error in zip(data.invalid_values, errors):
        with allure.step(f"Enter '{value}' — '{error}'"):
            part_c_page.fill_mobilization_address(value)
            expect(part_c_page.field_error("mobilization_address")).to_have_text(error)

    with allure.step(f"Enter '{data.valid_values[0]}' — the error disappears"):
        part_c_page.fill_mobilization_address(data.valid_values[0])
        expect(part_c_page.field_error("mobilization_address")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-453  Training Sectors rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-453")
@allure.story(STORY)
@allure.title("TC-453: Training Sectors must be 2–300 allowed characters")
def test_tc453_training_sectors_rules(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_training_sectors_invalid_data: PartCData
):
    """
    Given training is Yes
    When  I enter one character, then a disallowed character, then valid text
    Then  the length error, then the character error is shown, and valid text clears it

    Notion: KAN-TC-453 | data: training_sectors_invalid
    """
    page, user = logged_in_part_c_page
    data = part_c_training_sectors_invalid_data
    errors = (PartCPage.MIN_2_CHARS_ERROR, PartCPage.TRAINING_SECTORS_CHARS_ERROR)

    with allure.step("Select Yes for training"):
        part_c_page.select_training(True)

    for value, error in zip(data.invalid_values, errors):
        with allure.step(f"Enter '{value}' — '{error}'"):
            part_c_page.fill_training_sectors(value)
            expect(part_c_page.field_error("training_sectors")).to_have_text(error)

    with allure.step(f"Enter '{data.valid_values[0]}' — the error disappears"):
        part_c_page.fill_training_sectors(data.valid_values[0])
        expect(part_c_page.field_error("training_sectors")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-454  Website format
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-454")
@allure.story(STORY)
@allure.title("TC-454: Website / URL must be a valid web address when filled")
def test_tc454_website_format(part_c_page: PartCPage, logged_in_part_c_page, part_c_website_cases: PartCData):
    """
    Given I am on Part C
    When  I enter websites without a domain ending or with a space, then valid ones
    Then  the invalid ones show the website error and the valid ones don't

    Notion: KAN-TC-454 | data: website_cases
    """
    page, user = logged_in_part_c_page
    data = part_c_website_cases

    for value in data.invalid_values:
        with allure.step(f"Enter '{value}' — the website error is shown"):
            part_c_page.fill_website(value)
            expect(part_c_page.field_error("google_maps_url")).to_have_text(data.expected_error)

    for value in data.valid_values:
        with allure.step(f"Enter '{value}' — no error"):
            part_c_page.fill_website(value)
            expect(part_c_page.field_error("google_maps_url")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-455  Other Services needs letters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-455")
@allure.story(STORY)
@allure.title("TC-455: Other Services must contain descriptive text when filled")
def test_tc455_other_services_needs_letters(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_other_services_no_letters_data: PartCData
):
    """
    Given I am on Part C
    When  I enter only digits and symbols in Other Services, then text with letters
    Then  "Please enter some descriptive text." is shown, then cleared

    Notion: KAN-TC-455 | data: other_services_no_letters
    """
    page, user = logged_in_part_c_page
    data = part_c_other_services_no_letters_data

    with allure.step(f"Enter '{data.invalid_values[0]}'"):
        part_c_page.fill_other_services(data.invalid_values[0])
        expect(part_c_page.field_error("other_services")).to_have_text(data.expected_error)

    with allure.step(f"Enter '{data.valid_values[0]}' — the error disappears"):
        part_c_page.fill_other_services(data.valid_values[0])
        expect(part_c_page.field_error("other_services")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-456  Live validation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-456")
@allure.story(STORY)
@allure.title("TC-456: Inline errors appear only for fields the user has touched, and clear as soon as they are fixed")
def test_tc456_live_validation(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given nothing is entered on Part C
    When  I leave Type of Placement empty, type one character in Training Sectors, then a second
    Then  only the touched fields show errors, and the Training Sectors error clears while typing

    Notion: KAN-TC-456 | KAN-20 AC-7
    """
    page, user = logged_in_part_c_page

    with allure.step("Focus Type of Placement and leave it empty"):
        part_c_page.touch(part_c_page.placement_type_select)
        expect(part_c_page.field_error("placement_type")).to_have_text(PartCPage.PLACEMENT_TYPE_REQUIRED_ERROR)
        expect(part_c_page.field_error("service_mode")).to_have_count(0)
        expect(part_c_page.sectors_error).to_have_count(0)

    with allure.step("Select Yes for training, enter 'I' in Training Sectors and leave it"):
        part_c_page.select_training(True)
        part_c_page.fill_training_sectors("I")
        expect(part_c_page.field_error("training_sectors")).to_have_text(PartCPage.MIN_2_CHARS_ERROR)
        for name in ("training_mode", "training_capacity", "training_address"):
            expect(part_c_page.field_error(name)).to_have_count(0)

    with allure.step("Type a second character — the error disappears while typing"):
        part_c_page.training_sectors_input.press("End")
        part_c_page.training_sectors_input.press_sequentially("T")
        expect(part_c_page.training_sectors_input).to_have_value("IT")
        expect(part_c_page.field_error("training_sectors")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-457  Whitespace-only text is blank
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-457")
@allure.story(STORY)
@allure.title("TC-457: Text made only of spaces is treated as blank")
def test_tc457_spaces_only_is_blank(part_c_page: PartCPage, logged_in_part_c_page, part_c_training_data: PartCData):
    """
    Given every other mandatory field is filled and training is Yes with Mode, Capacity and Address
    When  I enter only spaces in Training Sectors and save
    Then  the save is blocked with "Enter the training sectors."

    Notion: KAN-TC-457 | KAN-20 EC-6 | data: with_training, Training Sectors = 3 spaces
    """
    page, user = logged_in_part_c_page
    data = part_c_training_data
    data.training_sectors = "   "

    with allure.step("Fill Part C with Training Sectors as three spaces"):
        _fill(part_c_page, data)

    with allure.step("Click 'Save Part C & Continue'"):
        part_c_page.click_submit()

    with allure.step("Verify the save is blocked with the required error"):
        expect(part_c_page.field_error("training_sectors")).to_have_text(PartCPage.TRAINING_SECTORS_REQUIRED_ERROR)
        _expect_blocked(page, part_c_page, PartCPage.TRAINING_SECTORS_REQUIRED_ERROR)


# ---------------------------------------------------------------------------
# TC-458  Character counters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-458")
@allure.story(STORY)
@allure.title("TC-458: Character counters turn to a warning near the limit and the limit cannot be exceeded")
def test_tc458_character_counters(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given I am on Part C
    When  I enter 899, then 900, then 1001 characters in Other Services
    Then  the counter warns from 900 and only 1000 characters are kept

    Notion: KAN-TC-458 | KAN-20 EC-8
    """
    page, user = logged_in_part_c_page
    field = part_c_page.other_services_textarea
    counter = part_c_page.char_counter(field)
    warn = re.compile(r"\bwarn\b")

    with allure.step("Enter 899 characters — normal counter"):
        field.fill("a" * 899)
        expect(counter).to_have_text("899 / 1000")
        expect(counter).not_to_have_class(warn)

    with allure.step("Add one character — warning counter"):
        field.press_sequentially("a")
        expect(counter).to_have_text("900 / 1000")
        expect(counter).to_have_class(warn)

    with allure.step("Enter 1001 characters — only 1000 are kept"):
        field.fill("")
        field.press_sequentially("a" * 1001, delay=0)
        expect(field).to_have_value("a" * 1000)
        expect(counter).to_have_text("1000 / 1000")


# ---------------------------------------------------------------------------
# TC-459  Save & Log out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-459")
@allure.story(STORY)
@allure.title("TC-459: \"Save & Log out\" logs the user out so they can continue later")
def test_tc459_save_and_logout(part_c_page: PartCPage, logged_in_part_c_page):
    """
    Given my application is unpaid
    When  I click "Save & Log out" in the deadline banner and log in again
    Then  I am logged out, and after logging in I can open Part C again

    Notion: KAN-TC-459 | KAN-20 AC-10
    """
    page, user = logged_in_part_c_page

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(part_c_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(part_c_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        part_c_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again and open Part C"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        part_c_page.open()
        expect(part_c_page.title).to_have_text("Step 3 — Part C: Operations & Infrastructure")


# ---------------------------------------------------------------------------
# TC-460  Service Charges are saved and restored — saves Part C
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-460")
@allure.story(STORY)
@allure.title("TC-460: Service Charges selections are saved and shown again when Part C is reopened")
def test_tc460_service_charges_restored(
    part_c_page: PartCPage, logged_in_part_c_page, part_c_service_charges_data: PartCData
):
    """
    Given I am on Part C
    When  I tick two agency types, answer No to charges displayed, save and reopen
    Then  the Rule 7(2) hint is shown, and the same two boxes and No are restored

    Notion: KAN-TC-460 | data: service_charges
    """
    page, user = logged_in_part_c_page
    data = part_c_service_charges_data

    with allure.step("Fill Part C with two agency types and charges displayed = No"):
        _fill(part_c_page, data)
        expect(part_c_page.charges_displayed_hint).to_have_text(PartCPage.CHARGES_DISPLAYED_HINT)

    with allure.step("Save Part C"):
        part_c_page.click_submit()
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Reopen Part C — the selections are restored"):
        _reopen(page, part_c_page)
        for model in PartCPage.SERVICE_MODELS:
            box = part_c_page.service_model_checkbox(model)
            expect(box).to_be_checked() if model in data.service_models else expect(box).not_to_be_checked()
        expect(part_c_page.charges_displayed_radio("no")).to_be_checked()


# ---------------------------------------------------------------------------
# TC-461  A saved Part C reopens read-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-461")
@allure.story(STORY)
@allure.title("TC-461: A saved Part C reopens read-only until \"Edit this section\" is clicked")
def test_tc461_saved_part_c_read_only(part_c_page: PartCPage, logged_in_part_c_page, part_c_minimal_data: PartCData):
    """
    Given I have saved Part C
    When  I open Part C, then click "Edit this section"
    Then  every field is disabled with no save button, "Edit this section" and "Next: Part F →" shown
    And   after Edit every field is enabled with the same saved values and the save button is back

    Notion: KAN-TC-461 | KAN-20 AC-11 | data: minimal
    """
    page, user = logged_in_part_c_page
    fields = part_c_page.form_fields

    with allure.step("Precondition: save Part C with the mandatory fields"):
        _fill(part_c_page, part_c_minimal_data)
        part_c_page.click_submit()
        _expect_part_c_saved(page, part_c_page, user)

    with allure.step("Open Part C again"):
        part_c_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify Part C is read-only"):
        expect(part_c_page.edit_section_link).to_be_visible()
        expect(part_c_page.next_part_f_link).to_be_visible()
        expect(part_c_page.submit_button).to_be_hidden()
        assert fields.count() > 0, "No form fields found"
        for index in range(fields.count()):
            expect(fields.nth(index)).to_be_disabled()

    with allure.step("Verify Type of Placement keeps its saved value and can't be changed"):
        saved_values = fields.evaluate_all("els => els.map(e => e.type === 'checkbox' || e.type === 'radio' ? e.checked : e.value)")
        expect(part_c_page.placement_type_select).not_to_have_value("")
        expect(part_c_page.placement_type_select).to_be_disabled()

    with allure.step("Click 'Edit this section'"):
        part_c_page.make_editable()
        expect(page).to_have_url(re.compile(rf"{re.escape(PART_C_URL)}\?edit=1"))

    with allure.step("Verify every field is enabled with the same saved values"):
        expect(part_c_page.edit_section_link).to_have_count(0)
        expect(part_c_page.submit_button).to_be_visible()
        for index in range(fields.count()):
            expect(fields.nth(index)).to_be_enabled()
        values = fields.evaluate_all("els => els.map(e => e.type === 'checkbox' || e.type === 'radio' ? e.checked : e.value)")
        assert values == saved_values, "Values changed after 'Edit this section'"
