import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PART_B_URL = f"{FORMS_BASE}/partB.php"


class PartBPage(BasePage):
    """Page object for Step 2 — Part B: Key Persons (forms/partB.php).

    One ``.person-card`` per key person, ``#person_0``, ``#person_1`` … in the
    order they were added. Per-person locators take that ``index``; the card
    title is "<label> <index + 1>" (e.g. "Director 1"). Removing a card does not
    renumber the others, so indexes can have gaps (person_0, person_2).

    The person label (Director, Partner, Proprietor …) and the fields follow the
    agency type saved in Part A:
    - Company types: DIN / DPIN + PAN fields per person, no address-proof upload.
    - Other types:   no DIN / PAN. Whether an address-proof upload is shown has
                     not been verified on the redesigned page.

    Only Full Name and Nationality carry ``required``; the other starred fields
    are enforced server-side. Aadhaar, DIN and mobile strip non-digits as you
    type; PAN is upper-cased and stripped to A–Z / 0–9; passport is upper-cased.

    A rejected save reloads Part B with everything kept and an error box
    (``server_errors``) listing one "Person N: <message>" line per problem. A
    saved Part B reopens read-only until "Edit this section" (?edit=1) is clicked;
    a successful save lands on Part C (partC.php?prev_saved=1).
    """

    NATIONALITIES = ("Indian", "Foreign")
    NATIONALITY_LABELS = ("Indian", "Foreign National")
    # The first card offers +91 only; cards added with "Add Another …" offer all of these.
    COUNTRY_CODES = ("+91", "+1", "+44", "+61", "+971", "+65")

    # Client-side texts
    AADHAAR_HINT = "Cannot start with 0 or 1"
    PERSONAL_EMAIL_HINT = "Must differ from the official agency email"
    MOBILE_PATTERN_TITLE = "10-digit mobile number starting with 6, 7, 8 or 9"
    AT_LEAST_ONE_PERSON_ALERT = "At least one person is required."

    # Server-side errors — each is shown as "Person N: <message>" (see person_error)
    ERRORS_HEADING = "Please correct the following — everything you entered is kept:"
    NAME_FORMAT_ERROR = "Full name must be at least 3 characters, letters only."
    AADHAAR_REQUIRED_ERROR = "Aadhaar Card Number is mandatory."
    AADHAAR_LENGTH_ERROR = "Aadhaar must be exactly 12 digits."
    AADHAAR_PREFIX_ERROR = "Aadhaar cannot start with 0 or 1."
    DIN_REQUIRED_ERROR = "DIN/DPIN is required for Private Limited Company."
    DIN_LENGTH_ERROR = "DIN/DPIN must be 8 digits."
    PAN_REQUIRED_ERROR = "PAN is required for Private Limited Company."
    PAN_FORMAT_ERROR = "PAN format invalid (e.g. ABCDE1234F)."
    PASSPORT_REQUIRED_ERROR = "Passport is mandatory for foreign nationals."
    MOBILE_REQUIRED_ERROR = "Mobile number is required."
    ADDRESS_REQUIRED_ERROR = "Residential address is required."
    ADDRESS_LENGTH_ERROR = "Address is too short (minimum 10 characters)."
    EMAIL_SAME_AS_OFFICIAL_ERROR = "Personal email must differ from the official agency email."
    # Required by KAN-19 EC-1 (KAN-TC-112); not observed — the server currently saves duplicates.
    DUPLICATE_AADHAAR_ERROR = "This Aadhaar number has already been entered for another key person in this application."

    @staticmethod
    def person_error(person: int, message: str) -> str:
        """Error-box line for the ``person``-th card (1-based, in page order)."""
        return f"Person {person}: {message}"

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        """Heading 'Step 2 — Part B: Key Persons'."""
        return self.page.locator("//h2[contains(text(),'Part B')]")

    @property
    def sub_title(self):
        """'Nationality verified via Aadhaar / Passport' under the heading."""
        return self.title.locator("xpath=following-sibling::p")

    @property
    def deadline_banner(self):
        """Banner '<N> days left to complete all steps and pay — deadline …' shown
        above the wizard while the registration is unpaid."""
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        """'Save & Log out' link inside the deadline banner (../auth/logout.php)."""
        return self.page.get_by_role("link", name="Save & Log out")

    @property
    def back_to_part_a_link(self):
        """'← Part A' link top-right of the heading."""
        return self.page.get_by_role("link", name="← Part A")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` ('Register', 'Part A', 'Part B', …, 'Payment')
        while that step is not yet saved (a plain, non-clickable item)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a '✓ <label>' link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def edit_section_link(self):
        """'Edit this section' (?edit=1) — shown when a saved Part B is reopened; the
        form is read-only (its fieldset disabled) until it is clicked."""
        return self.page.locator("a.pB-edit-link")

    @property
    def next_part_c_link(self):
        """'Next: Part C →' — shown once Part B is saved."""
        return self.page.get_by_role("link", name="Next: Part C →").first

    @property
    def server_errors(self):
        """Error box after a rejected save: ERRORS_HEADING, then one 'Person N: …' line per problem."""
        return self.page.locator(".alert-e")

    @property
    def category_banner(self):
        """'Category of Key Persons: <label> (based on your agency type: <type>)'."""
        return self.page.locator(".category-banner")

    @property
    def person_label(self):
        """Bold person label inside the category banner, e.g. 'Director'."""
        return self.category_banner.locator("strong")

    @property
    def guidance_note(self):
        """Note starting 'Aadhaar is mandatory for every person. …' under the banner."""
        return self.page.locator("//p[contains(normalize-space(),'Aadhaar is mandatory for every person')]")

    # ── Person cards ──────────────────────────────────────────────────────────

    @property
    def persons_container(self):
        return self.page.locator("#personsContainer")

    @property
    def person_cards(self):
        return self.page.locator(".person-card")

    def person_card(self, index: int):
        return self.page.locator(f"#person_{index}")

    def person_title(self, index: int):
        """Card title, e.g. 'Director 1'."""
        return self.person_card(index).locator(".person-title")

    def remove_person_button(self, index: int):
        """'✕ Remove' — only on cards added with 'Add Another …', never on the first card."""
        return self.person_card(index).locator(".person-remove")

    @property
    def add_person_button(self):
        """'Add Another <label>' (e.g. 'Add Another Director')."""
        return self.page.locator("button.btn-add")

    # ── Per-person fields ─────────────────────────────────────────────────────

    def full_name_input(self, index: int):
        """Max 150, required."""
        return self.person_card(index).locator("input[name='p_name[]']")

    def personal_email_input(self, index: int):
        """Optional, type=email, max 254."""
        return self.person_card(index).locator("input[name='p_email[]']")

    def personal_email_hint(self, index: int):
        return self.personal_email_input(index).locator("xpath=following-sibling::p[contains(@class,'hlp')]")

    def nationality_select(self, index: int):
        """'Indian' (default) / 'Foreign' (shown as 'Foreign National')."""
        return self.page.locator(f"#natSelect{index}")

    def nationality_options(self, index: int):
        return self.nationality_select(index).locator("option")

    def din_input(self, index: int):
        """Company types only. 8 digits."""
        return self.person_card(index).locator("input[name='p_din[]']")

    def pan_input(self, index: int):
        """Company types only. 10 chars, upper-cased."""
        return self.person_card(index).locator("input[name='p_pan[]']")

    def aadhaar_input(self, index: int):
        """12 digits."""
        return self.person_card(index).locator("input[name='p_aadhaar[]']")

    def aadhaar_hint(self, index: int):
        return self.aadhaar_input(index).locator("xpath=following-sibling::p[contains(@class,'hlp')]")

    def passport_wrapper(self, index: int):
        """Passport block — hidden while nationality is Indian."""
        return self.page.locator(f"#passportWrap{index}")

    def passport_input(self, index: int):
        """Max 20, upper-cased. Cleared when nationality goes back to Indian."""
        return self.passport_wrapper(index).locator("input[name='p_passport[]']")

    def country_code_select(self, index: int):
        return self.person_card(index).locator("select[name='p_country_code[]']")

    def country_code_options(self, index: int):
        return self.country_code_select(index).locator("option")

    def mobile_input(self, index: int):
        """10 digits, pattern [6-9][0-9]{9}."""
        return self.person_card(index).locator("input[name='p_mobile[]']")

    def address_input(self, index: int):
        """Residential Address textarea."""
        return self.person_card(index).locator("textarea[name='p_address[]']")

    def address_proof_input(self, index: int):
        """Address-proof upload — not rendered for company types; unverified for others."""
        return self.person_card(index).locator("input[type='file']")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        """'Save Part B & Continue'."""
        return self.page.locator("button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Part B — Key Persons")
    def open(self):
        """Navigates to Part B (requires a logged-in agency session with Part A saved)."""
        self.navigate(PART_B_URL)

    @allure.step("Make Part B editable ('Edit this section' if shown)")
    def make_editable(self):
        if self.edit_section_link.is_visible():
            self.edit_section_link.click()
            self.page.wait_for_load_state("networkidle")

    def person_indexes(self) -> list[int]:
        """Indexes of the cards on the page (from their ``person_<n>`` ids), in page order."""
        return [int(card_id.split("_")[1])
                for card_id in self.person_cards.evaluate_all("els => els.map(e => e.id)")]

    @allure.step("Remove every added person, keeping the first card")
    def remove_added_persons(self):
        for index in self.person_indexes()[1:]:
            self.click_remove_person(index)

    @allure.step("Person {index}: Fill Full Name: {name}")
    def fill_full_name(self, index: int, name: str):
        self.full_name_input(index).fill(name)
        self.full_name_input(index).blur()

    @allure.step("Type '{text}' key by key")
    def type_key_by_key(self, field, text: str):
        """Clears ``field`` and types ``text`` one key at a time, like a user.

        Unlike fill(), each key runs the field's oninput clean-up before the next
        one, so stripped characters don't count against maxlength."""
        field.fill("")
        field.press_sequentially(text)

    @allure.step("Person {index}: Fill Personal Email: {email}")
    def fill_personal_email(self, index: int, email: str):
        self.personal_email_input(index).fill(email)
        self.personal_email_input(index).blur()

    @allure.step("Person {index}: Select Nationality: {nationality}")
    def select_nationality(self, index: int, nationality: str):
        self.nationality_select(index).select_option(value=nationality)

    @allure.step("Person {index}: Fill DIN / DPIN: {din}")
    def fill_din(self, index: int, din: str):
        self.din_input(index).fill(din)
        self.din_input(index).blur()

    @allure.step("Person {index}: Fill PAN: {pan}")
    def fill_pan(self, index: int, pan: str):
        self.pan_input(index).fill(pan)
        self.pan_input(index).blur()

    @allure.step("Person {index}: Fill Aadhaar: {aadhaar}")
    def fill_aadhaar(self, index: int, aadhaar: str):
        self.aadhaar_input(index).fill(aadhaar)
        self.aadhaar_input(index).blur()

    @allure.step("Person {index}: Fill Passport Number: {passport}")
    def fill_passport(self, index: int, passport: str):
        self.passport_input(index).fill(passport)
        self.passport_input(index).blur()

    @allure.step("Person {index}: Select Country Code: {code}")
    def select_country_code(self, index: int, code: str):
        self.country_code_select(index).select_option(value=code)

    @allure.step("Person {index}: Fill Mobile Number: {mobile}")
    def fill_mobile(self, index: int, mobile: str):
        self.mobile_input(index).fill(mobile)
        self.mobile_input(index).blur()

    @allure.step("Person {index}: Fill Residential Address")
    def fill_address(self, index: int, address: str):
        self.address_input(index).fill(address)
        self.address_input(index).blur()

    @allure.step("Person {index}: Set Address Proof: {path}")
    def set_address_proof(self, index: int, path: str):
        self.address_proof_input(index).set_input_files(path)

    @allure.step("Click 'Add Another' person")
    def click_add_person(self):
        self.add_person_button.click()

    @allure.step("Person {index}: Click '✕ Remove'")
    def click_remove_person(self, index: int):
        self.remove_person_button(index).click()

    @allure.step("Click 'Save Part B & Continue'")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click 'Save Part B & Continue' and handle alert")
    def click_submit_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.submit_button, action=action)

    @allure.step("Click '← Part A'")
    def click_back_to_part_a(self):
        self.back_to_part_a_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()

    @allure.step("Person {index}: Fill complete key-person details")
    def fill_key_person(self, index: int, name: str, aadhaar: str, mobile: str, address: str,
                        email: str = None, din: str = None, pan: str = None,
                        nationality: str = "Indian", passport: str = None,
                        country_code: str = "+91", address_proof_path: str = None):
        """Fills one person card end-to-end. DIN/PAN apply to company types only.
        Passport is only shown for nationality 'Foreign'; the first card offers
        +91 only, so ``country_code`` can differ only on added cards."""
        self.fill_full_name(index, name)
        if email is not None:
            self.fill_personal_email(index, email)
        self.select_nationality(index, nationality)
        if din is not None:
            self.fill_din(index, din)
        if pan is not None:
            self.fill_pan(index, pan)
        self.fill_aadhaar(index, aadhaar)
        if passport is not None:
            self.fill_passport(index, passport)
        if country_code != "+91":
            self.select_country_code(index, country_code)
        self.fill_mobile(index, mobile)
        self.fill_address(index, address)
        if address_proof_path is not None:
            self.set_address_proof(index, address_proof_path)
