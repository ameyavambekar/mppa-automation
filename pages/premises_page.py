import re

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PREMISES_URL = f"{FORMS_BASE}/premises.php"
# Until the photos are saved (locked), the Declaration step sends the user back here with this query.
PREMISES_LOCKED_STEP_URL = f"{PREMISES_URL}?error=complete_premises_first"
DECLARATION_URL = f"{FORMS_BASE}/declaration.php"


class PremisesPage(BasePage):
    """Page object for the Premises Photos step (forms/premises.php, progress node "Photos").

    One card per photo, keyed by ``data-key`` (see ``PHOTOS``), grouped under
    "Head office". Each card has "Take photo" (camera view with Capture /
    Cancel; falls back to the file chooser when no camera can be opened) and
    "Choose from device" (JPG / PNG). A photo is saved as soon as it is taken
    or chosen, together with the browser's GPS location — there is no upload
    button. Saved cards show the photo, "Location: <lat>, <lng> (±<N> m) · Map"
    and a green "Uploaded" badge.

    The classroom card has a Yes / No question, saved as soon as it is answered: No hides the
    photo and marks the card "Not applicable". (Before portal 2.1.0 the working area had one too.)

    Errors appear in ``message_box``.

    Since 20-Nov-2026 a bar under the heading (repeated at the bottom) has "← Documents", "Save" / "Edit" and
    "Next: Declaration →". "Save" is checked by the server: it lists what is missing ("Add these before
    continuing:" + one line per item), or locks the page (``#ppPage.pp-locked``, kept on the server) — photo
    buttons and answers are disabled, "Edit" replaces "Save" and "Next: Declaration →" is enabled. "Edit"
    unlocks it again. Until the step is saved, Next is greyed out and declaration.php sends the user back to
    ``PREMISES_LOCKED_STEP_URL``.
    """

    # data-key → (title, mandatory photo, Yes / No question or None)
    PHOTOS = {
        "signboard": ("Notice board / signboard with the agency name", True, None),
        "exterior": ("Office premises — outside view", True, None),
        "interior": ("Office — inside view", True, None),
        "classroom": ("Classroom / training room", False, "Does your agency have a classroom / training room?"),
        # Portal 2.1.0 (17-Nov-2026) added the service charges display board; the working area card (a required
        # photo on 17-Nov, a Yes / No card before that) is gone since 20-Nov-2026.
        "charges_board": ("Service charges display board", True, None),
    }
    REQUIRED = ("signboard", "exterior", "interior", "charges_board")
    CONDITIONAL = ("classroom",)

    # Client-side texts
    TITLE = "Premises photographs"
    SUBTITLE = "These photos are checked by the officer during Physical Verification."
    NOTE = ("Take the photos at your office. Each photo is saved with your current GPS location, so allow location "
            "access when the browser asks. Use Take photo on a mobile phone for best results. JPG / PNG, up to 3 MB "
            "each. The location must be in Maharashtra.")
    HELP = "The photo is saved with your current location."
    CHARGES_BOARD_HINT = ("The board at the office showing the service charges / fees charged to job seekers and "
                          "employers — the charges must be clearly readable.")
    NO_PHOTO = "No photo yet"
    BADGE_REQUIRED = "Required"
    BADGE_UPLOADED = "Uploaded"
    BADGE_NOT_APPLICABLE = "Not applicable"
    NOT_IMAGE_ERROR = "Only JPG or PNG photos are allowed."
    TOO_LARGE_ERROR = "The photo is larger than 3 MB."
    NO_LOCATION_SUPPORT_ERROR = "This browser cannot read your location. Use a mobile phone or a different browser."
    LOCATION_DENIED_ERROR = "Location permission is required. Allow location access for this site and try again."
    # "Save" with something missing (20-Nov-2026): MISSING_INTRO, then one line per item in page order.
    MISSING_INTRO = "Add these before continuing:"
    SAVE_FIRST_ERROR = "Click Save first — the Declaration opens after the photos are saved."
    NEXT_OFF_TOOLTIP = "Click Save first"
    LOCK_NOTE = "The photos are saved and locked. Click Next: Declaration to continue, or Edit to change a photo."
    SAVED_TOAST = 'Premises photos saved and locked. Click "Next: Declaration" to continue, or "Edit" to change a photo.'
    EDIT_TOAST = 'You can now change the photos. Click "Save" when you are done.'

    @staticmethod
    def missing_answer_line(key: str) -> str:
        """Line in the Save refusal for an unanswered Yes / No question."""
        return f"Head office — answer: {PremisesPage.PHOTOS[key][2]}"

    @staticmethod
    def missing_photo_line(key: str) -> str:
        """Line in the Save refusal for a missing photo."""
        return f"Head office — {PremisesPage.PHOTOS[key][0]}"

    @staticmethod
    def photo_saved_toast(key: str) -> str:
        """Toast after a photo is saved, e.g. 'Office — inside view saved.'"""
        return f"{PremisesPage.PHOTOS[key][0]} saved."

    @staticmethod
    def outside_maharashtra_error(lat: float, lng: float) -> str:
        """Message when a photo's location is outside Maharashtra (photo not saved)."""
        return (f"The photo location ({lat:.4f}, {lng:.4f}) is outside Maharashtra. "
                "Photos must be taken at the agency premises.")

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

    @property
    def container(self):
        """Page body — has the class ``pp-locked`` once the photos are saved."""
        return self.page.locator("#ppPage")

    @property
    def lock_note(self):
        """LOCK_NOTE — shown only while the page is locked."""
        return self.page.locator(".pp-lock-note")

    @property
    def toasts(self):
        return self.page.locator("#uiToasts .ui-toast")

    def toast(self, text: str):
        return self.toasts.filter(has_text=text)

    def is_locked(self) -> bool:
        return "pp-locked" in (self.container.get_attribute("class") or "").split()

    # ── Photo cards ───────────────────────────────────────────────────────────

    def card(self, key: str, branch: int = 0):
        """Has the class ``is-done`` once the photo is saved or the card is not applicable. ``branch`` 0 is the
        head office; branch office n has its own signboard / exterior / interior cards (``data-branch="n"``,
        no Yes / No questions — dev, 06-Nov-2026)."""
        if branch:
            return self.page.locator(f".pp-card[data-key='{key}'][data-branch='{branch}']")
        return self.page.locator(f".pp-card[data-key='{key}']:not([data-branch])")

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

    def thumbnail(self, key: str, branch: int = 0):
        """'No photo yet', 'Getting location…', 'Uploading…' or the saved photo."""
        return self.card(key, branch).locator("[data-thumb]")

    def photo(self, key: str, branch: int = 0):
        return self.thumbnail(key, branch).locator("img")

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

    def file_input(self, key: str, branch: int = 0):
        return self.card(key, branch).locator("[data-file]")

    def help_text(self, key: str):
        return self.card(key).locator(".ui-help")

    def question(self, key: str):
        """Yes / No question of a conditional card."""
        return self.card(key).locator(".pp-q")

    def answer_radio(self, key: str, yes: bool):
        return self.page.locator(f"input[name='q_{key}'][value='{'1' if yes else '0'}']")

    def is_done(self, key: str, branch: int = 0) -> bool:
        return "is-done" in (self.card(key, branch).get_attribute("class") or "").split()

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
    def save_buttons(self):
        """'Save' in the top and bottom bars — hidden while the page is locked."""
        return self.page.locator("[data-save]")

    @property
    def save_button(self):
        return self.save_buttons.first

    @property
    def edit_buttons(self):
        """'Edit' in the top and bottom bars — shown only while the page is locked."""
        return self.page.locator("[data-edit]")

    @property
    def edit_button(self):
        return self.edit_buttons.first

    @property
    def next_declaration_links(self):
        """'Next: Declaration →' in both bars — class ``is-off`` (greyed out) until the page is saved."""
        return self.page.locator("a[data-next]")

    @property
    def next_declaration_link(self):
        return self.next_declaration_links.first

    @property
    def back_to_documents_link(self):
        """'← Documents' (enclosures.php) in the top bar (was 'Back: Documents' until 20-Nov-2026)."""
        return self.page.get_by_role("link", name="← Documents").first

    @property
    def photo_actions(self):
        """'Take photo' / 'Choose from device' areas — click-blocked while the page is locked."""
        return self.page.locator(".pp-actions")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Premises Photos step")
    def open(self):
        """Navigates to Premises Photos (requires a logged-in agency session with both mandatory documents uploaded)."""
        self.navigate(PREMISES_URL)

    @allure.step("Photo '{key}' (office {branch}): choose {path}")
    def choose_photo(self, key: str, path: str, branch: int = 0):
        """Picks a file with 'Choose from device'; the page saves it straight away. ``branch`` 0 = head office."""
        self.file_input(key, branch).set_input_files(path)

    def branch_numbers(self) -> list[int]:
        """The branch offices that have photo cards (1, 2 …)."""
        return sorted({int(b) for b in self.page.locator(".pp-card[data-branch]").evaluate_all(
            "cs => cs.map(c => c.getAttribute('data-branch'))")})

    @allure.step("Photo '{key}': click 'Take photo'")
    def click_take_photo(self, key: str):
        self.take_photo_button(key).click()

    @allure.step("Click 'Capture'")
    def capture(self):
        self.capture_button.click()

    @allure.step("Answer '{key}' question: {yes}")
    def answer(self, key: str, yes: bool):
        """Answers a conditional card's Yes / No question; the page saves it straight away. An answer that
        is already selected is left alone (checking it again sends nothing)."""
        if self.answer_radio(key, yes).is_checked():
            return
        with self.page.expect_response(lambda r: "premises.php" in r.url and r.request.method == "POST"):
            self.answer_radio(key, yes).check()

    @allure.step("Click 'Save'")
    def click_save(self):
        """Clicks 'Save' and waits for the server's answer (locks the page, or lists what is missing)."""
        with self.page.expect_response(lambda r: "premises.php" in r.url and r.request.method == "POST"):
            self.save_button.click()

    @allure.step("Click 'Edit'")
    def click_edit(self):
        with self.page.expect_response(lambda r: "premises.php" in r.url and r.request.method == "POST"):
            self.edit_button.click()

    @allure.step("Click 'Next: Declaration →'")
    def click_next_declaration(self):
        self.next_declaration_link.click()

    @allure.step("Click the greyed-out 'Next: Declaration →'")
    def click_next_declaration_while_off(self):
        """The link ignores pointer clicks while greyed out (CSS pointer-events: none); this sends the click the
        page's own handler reacts to (SAVE_FIRST_ERROR)."""
        self.next_declaration_link.dispatch_event("click")

    @allure.step("Click '← Documents'")
    def click_back_to_documents(self):
        self.back_to_documents_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()
