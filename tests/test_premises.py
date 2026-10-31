import re

import allure
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.enclosures_page import EnclosuresPage, ENCLOSURES_URL
from pages.login_page import LoginPage
from pages.premises_page import PREMISES_URL, PremisesPage
from test_data.premises_factory import PremisesData, PremisesFactory
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Premises Photos"
ON_PREMISES = re.compile(rf"{re.escape(PREMISES_URL)}")
UPLOAD_TIMEOUT = 30000   # location lookup + upload
LAT, LNG = PremisesFactory.LOCATION


def _record(user, status: str = "in_progress") -> None:
    """Any saved photo or answer uses the user up for the Premises tests: record it in the state store."""
    TestStateStore().mark_form_step_status(username=user.username, step="premises", status=status)


def _expect_saved(premises: PremisesPage, key: str) -> None:
    """The card shows the photo, the Pune location with a Map link and a green 'Uploaded' badge."""
    expect(premises.photo(key)).to_be_visible(timeout=UPLOAD_TIMEOUT)
    expect(premises.badge(key)).to_have_text(PremisesPage.BADGE_UPLOADED)
    expect(premises.badge(key)).to_have_class(re.compile(r"\bui-badge-green\b"))
    expect(premises.location(key)).to_have_text(PremisesPage.location_text(LAT, LNG))
    expect(premises.map_link(key)).to_have_attribute("target", "_blank")


def _save_photo(premises: PremisesPage, user, key: str, path: str) -> None:
    premises.choose_photo(key, path)
    _record(user)
    _expect_saved(premises, key)


def _expect_empty(premises: PremisesPage, key: str) -> None:
    expect(premises.thumbnail(key)).to_have_text(PremisesPage.NO_PHOTO)
    expect(premises.photo(key)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-475  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-475")
@allure.story(STORY)
@allure.title("TC-475: Premises Photos shows the heading, location note, Head office cards and navigation buttons")
def test_tc475_page_layout(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given I have uploaded all six mandatory documents
    When  I open the Premises Photos step
    Then  the heading, subtitle, progress bar, note, Head office cards and the two buttons are shown

    Notion: KAN-TC-475 | KAN-38 AC-1
    """
    page, user = logged_in_premises_page

    with allure.step("Verify the heading and subtitle"):
        expect(premises_page.title).to_have_text(PremisesPage.TITLE)
        expect(premises_page.sub_title).to_have_text(PremisesPage.SUBTITLE)

    with allure.step("Verify the progress bar"):
        expect(premises_page.progress_step("Register")).to_contain_text("✓")
        for label in ("Part A", "Part B", "Part C", "Part F", "Documents"):
            expect(premises_page.completed_step_link(label)).to_contain_text("✓")
        for label in ("Photos", "Declaration", "Preview", "Payment"):
            expect(premises_page.progress_step(label)).to_be_visible()

    with allure.step("Verify the note"):
        expect(premises_page.note).to_have_text(PremisesPage.NOTE)

    with allure.step("Verify the Head office cards, in order"):
        expect(premises_page.office_headings.first).to_have_text("Head office")
        expect(premises_page.cards).to_have_count(len(PremisesPage.PHOTOS))
        for index, (key, (title, mandatory, question)) in enumerate(PremisesPage.PHOTOS.items()):
            expect(premises_page.cards.nth(index)).to_have_attribute("data-key", key)
            expect(premises_page.card_title(key)).to_contain_text(title)
            if mandatory:
                expect(premises_page.card_title(key)).to_contain_text("*")
            if question:
                expect(premises_page.question(key)).to_contain_text(question)
            expect(premises_page.take_photo_button(key)).to_have_text("Take photo")
            expect(premises_page.choose_label(key)).to_contain_text("Choose from device")
            expect(premises_page.help_text(key)).to_have_text(PremisesPage.HELP)

    with allure.step("Verify the two buttons"):
        expect(premises_page.back_to_documents_link).to_be_visible()
        expect(premises_page.finish_button).to_have_text("Save & continue to Declaration")


# ---------------------------------------------------------------------------
# TC-476  Default state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-476")
@allure.story(STORY)
@allure.title("TC-476: Premises Photos opens with every card empty and both questions unanswered")
def test_tc476_default_state(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given no photo has been saved and no question answered
    When  I open the Premises Photos step
    Then  every card shows "No photo yet" with a "Required" badge and no location, and both questions are unanswered

    Notion: KAN-TC-476 | KAN-38 AC-2
    """
    page, user = logged_in_premises_page

    for key in PremisesPage.PHOTOS:
        with allure.step(f"Verify card '{key}' is empty"):
            _expect_empty(premises_page, key)
            expect(premises_page.badge(key)).to_have_text(PremisesPage.BADGE_REQUIRED)
            expect(premises_page.location(key)).to_have_text("")

    for key in PremisesPage.CONDITIONAL:
        with allure.step(f"Verify the '{key}' question is unanswered"):
            expect(premises_page.answer_radio(key, True)).not_to_be_checked()
            expect(premises_page.answer_radio(key, False)).not_to_be_checked()


# ---------------------------------------------------------------------------
# TC-477  Take photo — saves a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-477")
@allure.story(STORY)
@allure.title("TC-477: \"Take photo\" saves a photo with the current location")
def test_tc477_take_photo(logged_in_premises_camera_page):
    """
    Given camera and location access are allowed (fake camera, location Pune)
    When  I click "Take photo" on the signboard card, then "Capture"
    Then  the photo is saved with my location, a Map link and a green "Uploaded" badge

    Notion: KAN-TC-477 | KAN-38 AC-3
    """
    page, user = logged_in_premises_camera_page
    premises = PremisesPage(page)

    with allure.step("Click 'Take photo' — the camera view opens"):
        premises.click_take_photo("signboard")
        expect(premises.camera_dialog).to_have_class(re.compile(r"\bis-open\b"))
        expect(premises.capture_button).to_be_visible()
        expect(premises.cancel_camera_button).to_be_visible()

    with allure.step("Click 'Capture'"):
        premises.capture()
        _record(user)
        expect(premises.camera_dialog).not_to_have_class(re.compile(r"\bis-open\b"))

    with allure.step("Verify the photo is saved with the location"):
        _expect_saved(premises, "signboard")
        expect(premises.map_link("signboard")).to_have_attribute(
            "href", f"https://www.google.com/maps?q={LAT},{LNG}")


# ---------------------------------------------------------------------------
# TC-478  Choose from device — saves photos
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-478")
@allure.story(STORY)
@allure.title("TC-478: \"Choose from device\" saves a JPG or PNG with the current location")
def test_tc478_choose_from_device(
    premises_page: PremisesPage, logged_in_premises_page, premises_jpg_and_png_data: PremisesData
):
    """
    Given location access is allowed
    When  I choose a JPG for the outside view and a PNG for the inside view
    Then  each is saved straight away with my location and an "Uploaded" badge

    Notion: KAN-TC-478 | KAN-38 AC-4 | data: jpg_and_png
    """
    page, user = logged_in_premises_page

    for key, path in premises_jpg_and_png_data.photos.items():
        with allure.step(f"Choose a photo for '{key}'"):
            _save_photo(premises_page, user, key, path)


# ---------------------------------------------------------------------------
# TC-479  Location denied — saves a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-479")
@allure.story(STORY)
@allure.title("TC-479: A photo is not saved when location access is denied")
def test_tc479_location_denied(premises_page: PremisesPage, logged_in_premises_page, location_access):
    """
    Given location access is blocked for the site
    When  I choose a photo for the inside view, then allow location access and choose it again
    Then  the first try is not saved and asks for location permission; the second is saved

    Notion: KAN-TC-479 | KAN-38 AC-5
    """
    page, user = logged_in_premises_page

    with allure.step("Block location access and choose a photo"):
        location_access.block()
        premises_page.choose_photo("interior", PremisesFactory.PHOTO_JPG)

    with allure.step("Verify the photo is not saved and the location message is shown"):
        expect(premises_page.message_box).to_have_text(PremisesPage.LOCATION_DENIED_ERROR, timeout=UPLOAD_TIMEOUT)
        _expect_empty(premises_page, "interior")
        expect(premises_page.badge("interior")).to_have_text(PremisesPage.BADGE_REQUIRED)

    with allure.step("Allow location access and choose the photo again"):
        location_access.allow()
        _save_photo(premises_page, user, "interior", PremisesFactory.PHOTO_JPG)


# ---------------------------------------------------------------------------
# TC-480  Conditional photos — saves answers and a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-480")
@allure.story(STORY)
@allure.title("TC-480: Answering the classroom and working-area questions shows or hides their photos")
def test_tc480_conditional_photos(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given both questions are unanswered
    When  I answer No, then Yes for the classroom, and Yes for the working area with a photo, then reload
    Then  No hides the photo as "Not applicable", Yes shows it as "Required", and both answers and the photo are kept

    Notion: KAN-TC-480 | KAN-38 AC-6
    """
    page, user = logged_in_premises_page

    with allure.step("Answer No for the classroom — 'Not applicable'"):
        premises_page.answer("classroom", False)
        _record(user)
        expect(premises_page.card_body("classroom")).to_be_hidden()
        expect(premises_page.badge("classroom")).to_have_text(PremisesPage.BADGE_NOT_APPLICABLE)

    with allure.step("Answer Yes for the classroom — 'Required' again"):
        premises_page.answer("classroom", True)
        expect(premises_page.card_body("classroom")).to_be_visible()
        _expect_empty(premises_page, "classroom")
        expect(premises_page.badge("classroom")).to_have_text(PremisesPage.BADGE_REQUIRED)

    with allure.step("Answer Yes for the working area and save a photo"):
        premises_page.answer("working_area", True)
        _save_photo(premises_page, user, "working_area", PremisesFactory.PHOTO_JPG)

    with allure.step("Reload — both answers and the photo are kept"):
        page.reload()
        page.wait_for_load_state("networkidle")
        expect(premises_page.answer_radio("classroom", True)).to_be_checked()
        expect(premises_page.answer_radio("working_area", True)).to_be_checked()
        expect(premises_page.photo("working_area")).to_be_visible()


# ---------------------------------------------------------------------------
# TC-481  Save & continue — completes the step
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-481")
@allure.story(STORY)
@allure.title("TC-481: \"Save & continue to Declaration\" goes to the Declaration step when every required photo is saved")
def test_tc481_save_and_continue(
    premises_page: PremisesPage, logged_in_premises_page, premises_required_only_data: PremisesData
):
    """
    Given location access is allowed
    When  I save the three required photos, answer No to both questions and click "Save & continue to Declaration"
    Then  the Declaration step opens

    Notion: KAN-TC-481 | KAN-38 AC-7 | data: required_only
    """
    page, user = logged_in_premises_page
    data = premises_required_only_data

    for key, path in data.photos.items():
        with allure.step(f"Save the '{key}' photo"):
            _save_photo(premises_page, user, key, path)

    for key, yes in data.answers.items():
        with allure.step(f"Answer '{key}': {'Yes' if yes else 'No'}"):
            premises_page.answer(key, yes)
            expect(premises_page.badge(key)).to_have_text(PremisesPage.BADGE_NOT_APPLICABLE)

    with allure.step("Click 'Save & continue to Declaration' — the Declaration step opens"):
        premises_page.click_finish()
        page.wait_for_url(re.compile(r"/forms/declaration"), timeout=15000)
        _record(user, "completed")


# ---------------------------------------------------------------------------
# TC-482  Save & continue refused with photos missing — saves a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-482")
@allure.story(STORY)
@allure.title("TC-482: \"Save & continue to Declaration\" is refused while a required photo or answer is missing")
def test_tc482_save_refused_when_incomplete(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given only the signboard photo is saved and both questions are unanswered
    When  I click "Save & continue to Declaration"
    Then  I stay on Premises Photos with "Head office: answer both questions and add every required photo
          before continuing." and the button can be clicked again

    Notion: KAN-TC-482 | KAN-38 AC-7
    """
    page, user = logged_in_premises_page

    with allure.step("Save only the signboard photo"):
        _save_photo(premises_page, user, "signboard", PremisesFactory.PHOTO_JPG)

    with allure.step("Click 'Save & continue to Declaration'"):
        premises_page.click_finish()

    with allure.step("Verify the step is refused with the missing-photos message"):
        expect(premises_page.message_box).to_have_text(PremisesPage.MISSING_PHOTOS_ERROR)
        expect(page).to_have_url(ON_PREMISES)
        expect(premises_page.finish_button).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-483  Back: Documents
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-483")
@allure.story(STORY)
@allure.title("TC-483: \"Back: Documents\" returns to the Documents step with the uploads intact")
def test_tc483_back_to_documents(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given I am on the Premises Photos step
    When  I click "Back: Documents", then "Next: Premises Photos →"
    Then  the Documents step shows 6/6 uploaded, and Premises Photos opens again

    Notion: KAN-TC-483 | KAN-38 AC-8
    """
    page, user = logged_in_premises_page
    enclosures = EnclosuresPage(page)

    with allure.step("Click 'Back: Documents'"):
        premises_page.click_back_to_documents()

    with allure.step("Verify the Documents step shows 6/6 uploaded"):
        expect(page).to_have_url(re.compile(rf"{re.escape(ENCLOSURES_URL)}"))
        expect(enclosures.mandatory_counter).to_have_text(EnclosuresPage.counter_text(6))

    with allure.step("Click 'Next: Premises Photos →' — Premises Photos opens again"):
        enclosures.next_premises_photos_link.click()
        expect(page).to_have_url(ON_PREMISES)
        expect(premises_page.title).to_have_text(PremisesPage.TITLE)


# ---------------------------------------------------------------------------
# TC-484  Save & Log out — saves a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-484")
@allure.story(STORY)
@allure.title("TC-484: \"Save & Log out\" logs the user out so they can continue later")
def test_tc484_save_and_logout(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given my application is unpaid and the signboard photo is saved
    When  I click "Save & Log out" and log in again
    Then  login lands on Premises Photos with the signboard photo still saved

    Notion: KAN-TC-484 | KAN-38 AC-9
    """
    page, user = logged_in_premises_page

    with allure.step("Precondition: save the signboard photo"):
        _save_photo(premises_page, user, "signboard", PremisesFactory.PHOTO_JPG)

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(premises_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(premises_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        premises_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again — lands on Premises Photos with the photo kept"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        expect(page).to_have_url(ON_PREMISES)
        expect(premises_page.photo("signboard")).to_be_visible()


# ---------------------------------------------------------------------------
# TC-485  Camera fallback — saves a photo
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-485")
@allure.story(STORY)
@allure.title("TC-485: \"Take photo\" falls back to the file chooser when the camera cannot be opened")
def test_tc485_camera_fallback(premises_page: PremisesPage, logged_in_premises_page):
    """
    Given the browser cannot open a camera
    When  I click "Take photo" on the inside-view card and choose a JPG
    Then  the file chooser opens instead of the camera view and the photo is saved

    Notion: KAN-TC-485 | KAN-38 EC-1
    """
    page, user = logged_in_premises_page

    with allure.step("Click 'Take photo' — the file chooser opens"):
        with page.expect_file_chooser() as chooser_info:
            premises_page.click_take_photo("interior")
        expect(premises_page.camera_dialog).not_to_have_class(re.compile(r"\bis-open\b"))

    with allure.step("Choose a JPG — the photo is saved"):
        chooser_info.value.set_files(PremisesFactory.PHOTO_JPG)
        _record(user)
        _expect_saved(premises_page, "interior")


# ---------------------------------------------------------------------------
# TC-486  Not JPG / PNG
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-486")
@allure.story(STORY)
@allure.title("TC-486: A file that is not JPG or PNG is rejected")
def test_tc486_not_jpg_or_png(premises_page: PremisesPage, logged_in_premises_page, premises_not_images_data: PremisesData):
    """
    Given I am on the Premises Photos step
    When  I choose a PDF, then a HEIC file, for the outside view
    Then  "Only JPG or PNG photos are allowed." is shown each time and nothing is saved

    Notion: KAN-TC-486 | KAN-38 EC-2 | data: not_images
    """
    page, user = logged_in_premises_page

    for path in premises_not_images_data.invalid_files:
        with allure.step(f"Choose {path.rsplit('.', 1)[-1].upper()} — rejected"):
            premises_page.choose_photo("exterior", path)
            expect(premises_page.message_box).to_have_text(PremisesPage.NOT_IMAGE_ERROR)
            _expect_empty(premises_page, "exterior")


# ---------------------------------------------------------------------------
# TC-487  Yes → No after a photo — completes the step
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-487")
@allure.story(STORY)
@allure.title("TC-487: Changing a conditional answer from Yes to No marks the card \"Not applicable\"")
def test_tc487_yes_to_no_after_photo(
    premises_page: PremisesPage, logged_in_premises_page, premises_required_only_data: PremisesData
):
    """
    Given the classroom question is answered Yes with a photo saved
    When  I change the answer to No and complete the step
    Then  the card is "Not applicable" with its location cleared, and it does not block the step

    Notion: KAN-TC-487 | KAN-38 EC-3 | data: required_only
    """
    page, user = logged_in_premises_page

    with allure.step("Precondition: answer Yes for the classroom and save a photo"):
        premises_page.answer("classroom", True)
        _save_photo(premises_page, user, "classroom", PremisesFactory.PHOTO_JPG)

    with allure.step("Change the answer to No"):
        premises_page.answer("classroom", False)
        expect(premises_page.card_body("classroom")).to_be_hidden()
        expect(premises_page.badge("classroom")).to_have_text(PremisesPage.BADGE_NOT_APPLICABLE)
        expect(premises_page.location("classroom")).to_have_text("")

    with allure.step("Save the required photos, answer No for the working area and save & continue"):
        for key, path in premises_required_only_data.photos.items():
            _save_photo(premises_page, user, key, path)
        premises_page.answer("working_area", False)
        premises_page.click_finish()

    with allure.step("Verify the classroom card did not block the step"):
        page.wait_for_url(re.compile(r"/forms/declaration"), timeout=15000)
        _record(user, "completed")


# ---------------------------------------------------------------------------
# TC-488  Photo taken outside Maharashtra rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-488")
@allure.story(STORY)
@allure.title("TC-488: A photo taken outside Maharashtra is rejected")
def test_tc488_outside_maharashtra(premises_page: PremisesPage, logged_in_premises_page, location_access):
    """
    Given location access is allowed and my location is outside Maharashtra
    When  I choose a photo for the inside view
    Then  the photo is not saved, the card shows "No photo yet" again, and the message box reads
          "The photo location (<lat>, <lng>) is outside Maharashtra. Photos must be taken at the agency premises."

    Notion: KAN-TC-488 | KAN-38 EC-4 | data: location Perth, Australia (-31.9502, 115.8609)
    """
    page, user = logged_in_premises_page
    lat, lng = PremisesFactory.OUTSIDE_LOCATION

    with allure.step(f"Set the browser location to ({lat}, {lng}) and choose a photo for the inside view"):
        location_access.allow(PremisesFactory.OUTSIDE_LOCATION)
        premises_page.choose_photo("interior", PremisesFactory.PHOTO_JPG)

    with allure.step("Verify the outside-Maharashtra message and that the photo is not saved"):
        expect(premises_page.message_box).to_have_text(
            PremisesPage.outside_maharashtra_error(lat, lng), timeout=UPLOAD_TIMEOUT)
        _expect_empty(premises_page, "interior")
        expect(premises_page.badge("interior")).to_have_text(PremisesPage.BADGE_REQUIRED)

    with allure.step("Reload and verify nothing was saved"):
        premises_page.open()
        _expect_empty(premises_page, "interior")
        expect(premises_page.badge("interior")).to_have_text(PremisesPage.BADGE_REQUIRED)
