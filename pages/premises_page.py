import re

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PREMISES_URL = f"{FORMS_BASE}/premises.php"


class PremisesPage(BasePage):
    """Page object for the Premises Photos step (forms/premises.php, progress node "Photos").

    One card per photo, keyed by ``data-key`` (see ``PHOTOS``), grouped under
    "Head office". Each card has "Take photo" (camera view with Capture /
    Cancel; falls back to the file chooser when no camera can be opened) and
    "Choose from device" (JPG / PNG). A photo is saved as soon as it is taken
    or chosen, together with the browser's GPS location — there is no upload
    button. Saved cards show the photo, "Location: <lat>, <lng> (±<N> m) · Map"
    and a green "Uploaded" badge.

    The classroom and working-area cards have a Yes / No question, saved as soon
    as it is answered: No hides the photo and marks the card "Not applicable".

    Errors appear in ``message_box``. "Save & continue to Declaration" is checked
    by the server and moves on to the next step.
    """

    # data-key → (title, mandatory photo, Yes / No question or None)
    PHOTOS = {
        "signboard": ("Notice board / signboard with the agency name", True, None),
        "exterior": ("Office premises — outside view", True, None),
        "interior": ("Office — inside view", True, None),
        "classroom": ("Classroom / training room", False, "Does your agency have a classroom / training room?"),
        "working_area": ("Working area", False, "Does your agency have a separate working area?"),
    }
    REQUIRED = ("signboard", "exterior", "interior")
    CONDITIONAL = ("classroom", "working_area")

    # Client-side texts
    TITLE = "Premises photographs"
    SUBTITLE = "These photos are checked by the officer during Physical Verification."
    NOTE = ("Take the photos at your office. Each photo is saved with your current GPS location, so allow location "
            "access when the browser asks. Use Take photo on a mobile phone for best results. JPG / PNG, up to 3 MB "
            "each. The location must be in Maharashtra.")
    HELP = "The photo is saved with your current location."
    NO_PHOTO = "No photo yet"
    BADGE_REQUIRED = "Required"
    BADGE_UPLOADED = "Uploaded"
    BADGE_NOT_APPLICABLE = "Not applicable"
    NOT_IMAGE_ERROR = "Only JPG or PNG photos are allowed."
    TOO_LARGE_ERROR = "The photo is larger than 3 MB."
    NO_LOCATION_SUPPORT_ERROR = "This browser cannot read your location. Use a mobile phone or a different browser."
    LOCATION_DENIED_ERROR = "Location permission is required. Allow location access for this site and try again."
    # Server message on "Save & continue to Declaration" with a photo or answer missing.
    MISSING_PHOTOS_ERROR = "Head office: answer both questions and add every required photo before continuing."

    @staticmethod
    def location_text(lat: float, lng: float) -> re.Pattern:
        """'Location: <lat>, <lng> (±<N> m) · Map' as shown on a saved card (5 decimals)."""
        return re.compile(rf"Location: {lat:.5f}, {lng:.5f} \(±\d+ m\) · Map")

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("h2", has_text=self.TITLE)

    @property
    def sub_title(self):
        return self.title.locator("xpath=following-sibling::p[1]")

    @property
    def note(self):
        return self.page.locator(".ui-alert-warn")

    @property
    def deadline_banner(self):
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        return self.page.get_by_role("link", name="Save & Log out")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` while that step is not yet saved (non-clickable)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def message_box(self):
        """Errors (location, file type, server) — empty until something goes wrong."""
        return self.page.locator("#ppMsg")

    @property
    def office_headings(self):
        """'Head office', then any branch offices."""
        return self.page.locator("h3.pp-office")

    @property
    def cards(self):
        return self.page.locator(".pp-card")

    # ── Photo cards ───────────────────────────────────────────────────────────

    def card(self, key: str):
        """Has the class ``is-done`` once the photo is saved or the card is not applicable."""
        return self.page.locator(f".pp-card[data-key='{key}']")

    def card_title(self, key: str):
        return self.card(key).locator(".pp-title")

    def card_hint(self, key: str):
        return self.card(key).locator(".pp-hint")

    def badge(self, key: str):
        """'Required' (amber), 'Uploaded' (green) or 'Not applicable' (gray)."""
        return self.card(key).locator("[data-badge]")

    def card_body(self, key: str):
        """Thumbnail, location and buttons — hidden when a conditional question is answered No."""
        return self.card(key).locator("[data-body]")

    def thumbnail(self, key: str):
        """'No photo yet', 'Getting location…', 'Uploading…' or the saved photo."""
        return self.card(key).locator("[data-thumb]")

    def photo(self, key: str):
        return self.thumbnail(key).locator("img")

    def location(self, key: str):
        """'Location: <lat>, <lng> (±<N> m) · Map' once saved."""
        return self.card(key).locator("[data-geo]")

    def map_link(self, key: str):
        """Opens Google Maps at the photo's location in a new tab."""
        return self.location(key).get_by_role("link", name="Map")

    def take_photo_button(self, key: str):
        return self.card(key).locator("[data-camera]")

    def choose_label(self, key: str):
        """'Choose from device' — wraps the file input."""
        return self.card(key).locator("label.ui-btn")

    def file_input(self, key: str):
        return self.card(key).locator("[data-file]")

    def help_text(self, key: str):
        return self.card(key).locator(".ui-help")

    def question(self, key: str):
        """Yes / No question of a conditional card."""
        return self.card(key).locator(".pp-q")

    def answer_radio(self, key: str, yes: bool):
        return self.page.locator(f"input[name='q_{key}'][value='{'1' if yes else '0'}']")

    def is_done(self, key: str) -> bool:
        return "is-done" in (self.card(key).get_attribute("class") or "").split()

    # ── Camera & navigation ───────────────────────────────────────────────────

    @property
    def camera_dialog(self):
        """Camera view — has the class ``is-open`` while shown."""
        return self.page.locator("#ppCam")

    @property
    def capture_button(self):
        return self.page.locator("#ppShoot")

    @property
    def cancel_camera_button(self):
        return self.page.locator("#ppCamClose")

    @property
    def back_to_documents_link(self):
        """'Back: Documents' (enclosures.php)."""
        return self.page.get_by_role("link", name="Back: Documents")

    @property
    def finish_button(self):
        """'Save & continue to Declaration'."""
        return self.page.locator("#ppFinish")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Premises Photos step")
    def open(self):
        """Navigates to Premises Photos (requires a logged-in agency session with all six documents uploaded)."""
        self.navigate(PREMISES_URL)

    @allure.step("Photo '{key}': choose {path}")
    def choose_photo(self, key: str, path: str):
        """Picks a file with 'Choose from device'; the page saves it straight away."""
        self.file_input(key).set_input_files(path)

    @allure.step("Photo '{key}': click 'Take photo'")
    def click_take_photo(self, key: str):
        self.take_photo_button(key).click()

    @allure.step("Click 'Capture'")
    def capture(self):
        self.capture_button.click()

    @allure.step("Answer '{key}' question: {yes}")
    def answer(self, key: str, yes: bool):
        """Answers a conditional card's Yes / No question; the page saves it straight away."""
        with self.page.expect_response(lambda r: "premises.php" in r.url and r.request.method == "POST"):
            self.answer_radio(key, yes).check()

    @allure.step("Click 'Save & continue to Declaration'")
    def click_finish(self):
        self.finish_button.click()

    @allure.step("Click 'Back: Documents'")
    def click_back_to_documents(self):
        self.back_to_documents_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
