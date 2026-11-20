import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PART_C_URL = f"{FORMS_BASE}/partC.php"


class PartCPage(BasePage):
    """Page object for Step 3 — Part C: Operations & Infrastructure (forms/partC.php).

    Sections, top to bottom: Placement Services (placement type, service mode,
    sectors), Service Charges (agency type radios — choose one — and charges-displayed radio),
    Online & Digital Platform, Training Centre, Mobilization Centre, Other
    Services and the optional agency website.

    The Yes/No radios for digital platform, training and mobilization default
    to No; choosing Yes un-hides a ``.cond-block`` (it drops the
    ``hidden-block`` class). Ticking an "address is same as registered office"
    box hides that block's address field.

    "Select All" ticks every sector except "Other"; ticking "Other" shows the
    "Please specify the other sector" input.

    Validation is client-side and inline — no alert() dialogs. Each invalid
    field gets a ``p.fld-err`` message (see ``field_error``), shown on blur /
    change for touched fields and for every field on submit. A blocked submit
    also fills the ``client_errors`` summary box. The form is ``novalidate``.

    A successful save stays on Part C (partC.php?edit=1) with the
    ``success_message`` "Part C saved." and "Next: Part F →" links. A saved
    Part C reopens with "Edit this section" (?edit=1) — see ``make_editable``.
    """

    # "Area of Placement Operations" radios (portal 2.1.0, 17-Nov-2026; was a Domestic / International
    # select) → registration fee shown on each card
    PLACEMENT_TYPES = ("Within Maharashtra", "Across India", "India and Overseas")
    PLACEMENT_FEES = {"Within Maharashtra": "₹2,000", "Across India": "₹4,000", "India and Overseas": "₹10,000"}
    AREA_DECLARATION = ("I declare that the selected area of operation represents the geographical scope of "
                        "placement activities proposed to be undertaken by the agency.")
    SERVICE_MODES = ("Online Only", "Offline Only", "Both Online & Offline")
    TRAINING_MODES = ("Online", "Offline", "Hybrid")
    SECTORS = (
        "IT / Software", "BPO / KPO", "Banking / Finance / Insurance",
        "Healthcare / Nursing", "Manufacturing / Engineering",
        "Construction / Real Estate", "Retail / Sales", "Hospitality / Tourism",
        "Education / Training", "Agriculture / Horticulture", "Security Services",
        "Domestic Workers / Household", "Drivers / Logistics",
        "Media / Entertainment", "Skilled Trades / Technical", "Other",
    )
    # "Type of Private Placement Agency * (choose one)": service_model[] radios since
    # 18-Nov-2026 (checkboxes before), so only one value is saved.
    SERVICE_MODEL_LABEL = "Type of Private Placement Agency"
    SERVICE_MODEL_CHOOSE_ONE = "(choose one)"
    SERVICE_MODEL_OPTIONS = {
        "b2b": ("Business to Business", "collects service charges from employer"),
        "b2c": ("Business to job seeker", "collects service charges from job seekers"),
        "both": ("Business to job seeker and Business", "collects service charges from employer and job seeker both"),
    }
    SERVICE_MODELS = tuple(SERVICE_MODEL_OPTIONS)

    # Client-side texts
    SAVED_MESSAGE = "Part C saved."
    ERRORS_HEADING = "Please fix the following before saving:"
    CHARGES_DISPLAYED_HINT = "Rule 7(2): service charges must be displayed outside the office and on the website."

    # Inline field errors (also listed as "• <message>" in the summary box)
    PLACEMENT_TYPE_REQUIRED_ERROR = "Please select the Area of Placement Operations."
    AREA_DECLARATION_REQUIRED_ERROR = "Tick the declaration about the area of operation."
    SECTION_DESCRIPTIONS = (
        "Area of operation, constitution details and the sectors you place candidates in.",
        "Who pays your service charges, and whether the charges are displayed.",
        "Website, app or social media used for placement.",
        "Only if your agency trains candidates.",
        "Only if your agency has a centre for mobilising candidates.",
        "Any other placement-related services and your website (optional).",
    )

    @staticmethod
    def applicable_fee_text(placement_type: str) -> str:
        """Line shown under the area radios once one is chosen."""
        return f"Applicable registration fee: {PartCPage.PLACEMENT_FEES[placement_type]} plus applicable taxes"
    PLACEMENT_TYPE_INVALID_ERROR = "Invalid placement type selected."
    SERVICE_MODE_REQUIRED_ERROR = "Please select the service mode."
    SERVICE_MODE_INVALID_ERROR = "Invalid service mode selected."
    SECTORS_REQUIRED_ERROR = "Select at least one sector."
    SECTOR_OTHER_REQUIRED_ERROR = 'Please specify the "Other" sector.'
    MIN_2_CHARS_ERROR = "Must be at least 2 characters."
    SECTOR_OTHER_MAX_ERROR = "Cannot exceed 200 characters."
    SECTOR_OTHER_CHARS_ERROR = "Contains invalid characters (letters, numbers and . , & ( ) / - # : + ' @ % only)."
    YES_NO_REQUIRED_ERROR = "Please choose Yes or No."
    DIGITAL_DETAILS_REQUIRED_ERROR = "Please provide the online platform details."
    DIGITAL_DETAILS_MIN_ERROR = "Details must be at least 10 characters (currently {n})."
    DIGITAL_DETAILS_MAX_ERROR = "Details cannot exceed 1000 characters."
    TRAINING_MODE_REQUIRED_ERROR = "Select the training mode."
    TRAINING_CAPACITY_REQUIRED_ERROR = "Enter the annual training capacity."
    TRAINING_CAPACITY_RANGE_ERROR = "Enter a whole number between 1 and 999999."
    TRAINING_SECTORS_REQUIRED_ERROR = "Enter the training sectors."
    TRAINING_SECTORS_MAX_ERROR = "Cannot exceed 300 characters."
    TRAINING_SECTORS_CHARS_ERROR = "Contains invalid characters."
    TRAINING_ADDRESS_REQUIRED_ERROR = "Training centre address is mandatory."
    MOBILIZATION_ADDRESS_REQUIRED_ERROR = "Mobilization centre address is mandatory."
    ADDRESS_MIN_ERROR = "Address must be at least 10 characters (currently {n})."
    ADDRESS_MAX_ERROR = "Address cannot exceed 400 characters."
    ADDRESS_CHARS_ERROR = "Address contains invalid characters."
    OTHER_SERVICES_MAX_ERROR = "Cannot exceed 1000 characters."
    OTHER_SERVICES_TEXT_ERROR = "Please enter some descriptive text."
    WEBSITE_INVALID_ERROR = "Enter a valid website address (e.g. www.youragency.in)."

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        """Heading 'Step 3 — Part C: Operations & Infrastructure'."""
        return self.page.locator("//h2[contains(text(),'Part C')]")

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
    def back_to_part_b_link(self):
        """'← Part B' link top-right of the heading."""
        return self.page.get_by_role("link", name="← Part B")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` ('Register', 'Part A', …, 'Payment')
        while that step is not yet saved (a plain, non-clickable item)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def completed_step_link(self, label: str):
        """Progress-bar item for a saved step — a link back to that step."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::a")

    @property
    def edit_section_link(self):
        """'Edit this section' (?edit=1) — shown when a saved Part C is reopened."""
        return self.page.get_by_role("link", name="Edit this section")

    @property
    def success_message(self):
        """'Part C saved.' — shown after a successful save."""
        return self.page.locator(".alert-s")

    @property
    def next_part_f_link(self):
        """'Next: Part F →' — shown once Part C is saved."""
        return self.page.get_by_role("link", name="Next: Part F →").first

    @property
    def client_errors(self):
        """Summary box after a blocked submit: ERRORS_HEADING, then '• <message>' per error."""
        return self.page.locator("#clientErr")

    @property
    def form(self):
        return self.page.locator("#partCForm")

    @property
    def fieldset(self):
        """Wraps every field — disabled while the section is read-only."""
        return self.page.locator("fieldset.pC-fieldset")

    @property
    def section_headings(self):
        """'Placement Services', 'Service Charges', … 'Other Services', in page order (``section.pc-sec``
        headers since portal 2.1.0; each header also has a numbered badge and a one-line description)."""
        return self.form.locator("section.pc-sec > header h3")

    @property
    def section_descriptions(self):
        return self.form.locator("section.pc-sec > header p")

    # ── Inline errors ─────────────────────────────────────────────────────────

    def field_error(self, name: str):
        """Inline ``p.fld-err`` for the field named ``name`` (e.g. 'placement_type',
        'training_capacity', 'has_digital_platform'). Use ``sectors_error`` and
        ``sector_other_error`` for the sector fields. Since portal 2.1.0 the area radios and their
        declaration share one block, so 'placement_type' is the area error only (see
        ``area_declaration_error``)."""
        if name == "placement_type":
            return self.placement_type_error
        return self.page.locator(
            f"//*[@name='{name}']/ancestor::div[contains(@class,'fld')][1]/p[contains(@class,'fld-err')]"
        )

    @property
    def form_fields(self):
        """Every input, select and textarea in the form — all disabled while Part C is read-only."""
        return self.form.locator("input, select, textarea")

    @property
    def field_errors(self):
        """Every inline error currently shown."""
        return self.page.locator("p.fld-err")

    # ── Placement Services ────────────────────────────────────────────────────

    @property
    def placement_type_select(self):
        """The old Type of Placement select — gone since portal 2.1.0 (17-Nov-2026); see
        ``placement_type_radio``. Kept until the Part C tests are reworked."""
        return self.page.locator("select[name='placement_type']")

    def placement_type_radio(self, placement_type: str):
        """'Area of Placement Operations' radio, one of PLACEMENT_TYPES."""
        return self.page.locator(f"input[name='placement_type'][value='{placement_type}']")

    @property
    def placement_type_radios(self):
        return self.page.locator("input[name='placement_type']")

    @property
    def checked_placement_type(self):
        """The chosen area radio — none until an area is chosen."""
        return self.page.locator("input[name='placement_type']:checked")

    @property
    def area_block(self):
        """The 'Area of Placement Operations *' block: the three radio cards (each with its fee), the
        applicable-fee line once one is chosen, the declaration and their errors."""
        return self.page.locator("#areaFld")

    def placement_type_card(self, placement_type: str):
        """The radio card '<area> / Registration fee ₹N + applicable taxes'."""
        return self.placement_type_radio(placement_type).locator("xpath=ancestor::label[1]")

    @property
    def placement_type_error(self):
        return self.area_block.locator("p.fld-err").filter(has_text="Area of Placement Operations")

    @property
    def area_declaration_error(self):
        return self.area_block.locator("p.fld-err").filter(has_text="declaration")

    @property
    def area_declaration_checkbox(self):
        """AREA_DECLARATION, required, under the area radios."""
        return self.page.locator("input[name='area_declaration']")

    @property
    def service_mode_select(self):
        """SERVICE_MODES, required."""
        return self.page.locator("select[name='service_mode']")

    @property
    def sectors_field(self):
        return self.page.locator("#sectorsFld")

    @property
    def select_all_sectors_checkbox(self):
        """Ticks every sector except 'Other'; ticks itself once all of those are ticked."""
        return self.page.locator("#selectAllSectors")

    @property
    def sectors_grid(self):
        """Gets the ``grp-invalid`` class while SECTORS_REQUIRED_ERROR is shown."""
        return self.page.locator("#sectorsGrid")

    @property
    def sector_checkboxes(self):
        return self.page.locator("input.sector-item")

    def sector_checkbox(self, sector: str):
        """``sector``: one of SECTORS."""
        return self.page.locator(f"input.sector-item[value='{sector}']")

    @property
    def sectors_error(self):
        return self.sectors_field.locator("xpath=./p[contains(@class,'fld-err')]")

    @property
    def sector_other_wrapper(self):
        """Hidden unless the 'Other' sector is ticked."""
        return self.page.locator("#sectorOtherWrap")

    @property
    def sector_other_input(self):
        """Max 200."""
        return self.page.locator("input[name='sector_other']")

    @property
    def sector_other_error(self):
        return self.sector_other_wrapper.locator("p.fld-err")

    # ── Service Charges ───────────────────────────────────────────────────────

    @property
    def service_model_field(self):
        return self.page.locator("#modelFld")

    @property
    def service_model_radios(self):
        return self.page.locator("input[name='service_model[]']")

    def service_model_radio(self, model: str):
        """``model``: one of SERVICE_MODELS ('b2b', 'b2c', 'both')."""
        return self.page.locator(f"input[name='service_model[]'][value='{model}']")

    def service_model_option(self, model: str):
        """The ``<label class="model-opt">`` card around a service-model radio (title + description)."""
        return self.service_model_radio(model).locator("xpath=ancestor::label[1]")

    def charges_displayed_radio(self, value: str):
        """``value``: 'yes' or 'no'. Neither is selected by default."""
        return self.page.locator(f"input[name='charges_displayed'][value='{value}']")

    @property
    def charges_displayed_hint(self):
        return self.charges_displayed_radio("yes").locator(
            "xpath=ancestor::div[contains(@class,'fld')][1]/p[contains(@class,'hlp')]"
        )

    # ── Online & Digital Platform ─────────────────────────────────────────────

    def digital_platform_radio(self, value: str):
        """``value``: '1' (Yes) or '0' (No, default)."""
        return self.page.locator(f"input[name='has_digital_platform'][value='{value}']")

    @property
    def digital_block(self):
        """Has the ``hidden-block`` class unless digital platform = Yes."""
        return self.page.locator("#digitalBlock")

    @property
    def digital_platform_details_textarea(self):
        """Min 10, max 1000."""
        return self.page.locator("textarea[name='digital_platform_details']")

    # ── Training Centre ───────────────────────────────────────────────────────

    def training_radio(self, value: str):
        """``value``: '1' (Yes) or '0' (No, default)."""
        return self.page.locator(f"input[name='training_provided'][value='{value}']")

    @property
    def training_block(self):
        """Has the ``hidden-block`` class unless training = Yes."""
        return self.page.locator("#trainingBlock")

    @property
    def training_mode_select(self):
        """TRAINING_MODES."""
        return self.page.locator("select[name='training_mode']")

    @property
    def training_capacity_input(self):
        """Digits only (non-digits stripped as you type), max 6, 1–999999."""
        return self.page.locator("input[name='training_capacity']")

    @property
    def training_sectors_input(self):
        """Min 2, max 300."""
        return self.page.locator("input[name='training_sectors']")

    @property
    def training_address_same_checkbox(self):
        """'Training centre address is same as registered office address'."""
        return self.page.locator("#trainAddrSame")

    @property
    def training_address_field(self):
        """Hidden while the same-address box is ticked."""
        return self.page.locator("#trainingAddrField")

    @property
    def training_address_textarea(self):
        """Min 10, max 400."""
        return self.page.locator("textarea[name='training_address']")

    # ── Mobilization Centre ───────────────────────────────────────────────────

    def mobilization_radio(self, value: str):
        """``value``: '1' (Yes) or '0' (No, default)."""
        return self.page.locator(f"input[name='mobilization_provided'][value='{value}']")

    @property
    def mobilization_block(self):
        """Has the ``hidden-block`` class unless mobilization = Yes."""
        return self.page.locator("#mobBlock")

    @property
    def mobilization_address_same_checkbox(self):
        """'Mobilization centre address is same as registered office address'."""
        return self.page.locator("#mobAddrSame")

    @property
    def mobilization_address_field(self):
        """Hidden while the same-address box is ticked."""
        return self.page.locator("#mobAddrField")

    @property
    def mobilization_address_textarea(self):
        """Min 10, max 400."""
        return self.page.locator("textarea[name='mobilization_address']")

    # ── Other Services & website ──────────────────────────────────────────────

    @property
    def other_services_textarea(self):
        """Optional, max 1000, must contain a letter."""
        return self.page.locator("textarea[name='other_services']")

    @property
    def website_input(self):
        """'Website / URL of the agency' — optional, max 300. (Field name is google_maps_url.)"""
        return self.page.locator("input[name='google_maps_url']")

    def char_counter(self, field):
        """'<len> / <maxlength>' counter right after a textarea or the website input."""
        return field.locator("xpath=following-sibling::div[contains(@class,'cnt')][1]")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        """'Save Part C & Continue' — becomes 'Saving…' and disabled once submitted."""
        return self.page.locator("#partCForm button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Part C — Operations & Infrastructure")
    def open(self):
        """Navigates to Part C (requires a logged-in agency session with Part B saved)."""
        self.navigate(PART_C_URL)

    @allure.step("Make Part C editable ('Edit this section' if shown)")
    def make_editable(self):
        if self.edit_section_link.is_visible():
            self.edit_section_link.click()
            self.page.wait_for_load_state("networkidle")

    @allure.step("Focus a field and leave it without changing it")
    def touch(self, field):
        field.focus()
        field.blur()

    @allure.step("Type '{text}' key by key")
    def type_key_by_key(self, field, text: str):
        """Clears ``field`` and types ``text`` one key at a time, like a user, so the
        field's oninput clean-up runs after every key."""
        field.fill("")
        field.press_sequentially(text)

    @staticmethod
    def _choose(radio):
        """Selects a Yes/No radio. Since portal 2.1.0 the input is invisible (opacity 0,
        pointer-events none) inside its ``<label>`` button, so the label is clicked."""
        radio.locator("xpath=ancestor::label[1]").click()

    @allure.step("Select Area of Placement Operations: {placement_type}")
    def select_placement_type(self, placement_type: str):
        self.placement_type_radio(placement_type).check()

    @allure.step("Tick the area-of-operation declaration")
    def tick_area_declaration(self):
        self.area_declaration_checkbox.check()

    @allure.step("Select Service Mode: {service_mode}")
    def select_service_mode(self, service_mode: str):
        self.service_mode_select.select_option(value=service_mode)

    @allure.step("Set sector '{sector}' to {checked}")
    def set_sector(self, sector: str, checked: bool = True):
        self.sector_checkbox(sector).set_checked(checked)

    @allure.step("Set 'Select All' sectors to {checked}")
    def set_select_all_sectors(self, checked: bool = True):
        self.select_all_sectors_checkbox.set_checked(checked)

    @allure.step("Fill Other Sector: {sector}")
    def fill_sector_other(self, sector: str):
        self.sector_other_input.fill(sector)
        self.sector_other_input.blur()

    @allure.step("Select Type of Private Placement Agency: '{model}'")
    def select_service_model(self, model: str):
        self._choose(self.service_model_radio(model))

    @allure.step("Service charges displayed: {displayed}")
    def select_charges_displayed(self, displayed: bool):
        self._choose(self.charges_displayed_radio("yes" if displayed else "no"))

    @allure.step("Uses a digital platform: {uses}")
    def select_digital_platform(self, uses: bool):
        self._choose(self.digital_platform_radio("1" if uses else "0"))

    @allure.step("Fill Online Platform Details")
    def fill_digital_platform_details(self, details: str):
        self.digital_platform_details_textarea.fill(details)
        self.digital_platform_details_textarea.blur()

    @allure.step("Provides training: {provided}")
    def select_training(self, provided: bool):
        self._choose(self.training_radio("1" if provided else "0"))

    @allure.step("Select Training Mode: {mode}")
    def select_training_mode(self, mode: str):
        self.training_mode_select.select_option(value=mode)

    @allure.step("Fill Annual Training Capacity: {capacity}")
    def fill_training_capacity(self, capacity: str):
        self.training_capacity_input.fill(str(capacity))
        self.training_capacity_input.blur()

    @allure.step("Fill Training Sectors: {sectors}")
    def fill_training_sectors(self, sectors: str):
        self.training_sectors_input.fill(sectors)
        self.training_sectors_input.blur()

    @allure.step("Training address same as registered office: {same}")
    def set_training_address_same(self, same: bool = True):
        self.training_address_same_checkbox.set_checked(same)

    @allure.step("Fill Training Centre Address")
    def fill_training_address(self, address: str):
        self.training_address_textarea.fill(address)
        self.training_address_textarea.blur()

    @allure.step("Has a mobilization centre: {provided}")
    def select_mobilization(self, provided: bool):
        self._choose(self.mobilization_radio("1" if provided else "0"))

    @allure.step("Mobilization address same as registered office: {same}")
    def set_mobilization_address_same(self, same: bool = True):
        self.mobilization_address_same_checkbox.set_checked(same)

    @allure.step("Fill Mobilization Centre Address")
    def fill_mobilization_address(self, address: str):
        self.mobilization_address_textarea.fill(address)
        self.mobilization_address_textarea.blur()

    @allure.step("Fill Other Services")
    def fill_other_services(self, services: str):
        self.other_services_textarea.fill(services)
        self.other_services_textarea.blur()

    @allure.step("Fill Website / URL: {url}")
    def fill_website(self, url: str):
        self.website_input.fill(url)
        self.website_input.blur()

    @allure.step("Click 'Save Part C & Continue'")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click '← Part B'")
    def click_back_to_part_b(self):
        self.back_to_part_b_link.click()

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()

    @allure.step("Fill the complete Part-C form")
    def fill_part_c_form(self, placement_type: str, service_mode: str, sectors: list,
                         service_model: str, charges_displayed: bool,
                         sector_other: str = None,
                         digital_platform_details: str = None,
                         training: bool = False, training_mode: str = None,
                         training_capacity: str = None, training_sectors: str = None,
                         training_address: str = None,
                         mobilization: bool = False, mobilization_address: str = None,
                         other_services: str = None, website: str = None):
        """Fills Part C end-to-end.

        - ``sector_other`` is filled only when 'Other' is in ``sectors``.
        - A digital platform is selected (Yes) only when ``digital_platform_details`` is given.
        - With ``training`` / ``mobilization`` True, a None address ticks the
          "same as registered office" box instead of filling the address.
        """
        if placement_type:
            self.select_placement_type(placement_type)
        self.tick_area_declaration()
        self.select_service_mode(service_mode)
        for sector in sectors:
            self.set_sector(sector, True)
        if sector_other is not None:
            self.fill_sector_other(sector_other)
        if service_model:
            self.select_service_model(service_model)
        self.select_charges_displayed(charges_displayed)

        self.select_digital_platform(digital_platform_details is not None)
        if digital_platform_details is not None:
            self.fill_digital_platform_details(digital_platform_details)

        self.select_training(training)
        if training:
            self.select_training_mode(training_mode)
            self.fill_training_capacity(training_capacity)
            self.fill_training_sectors(training_sectors)
            if training_address is None:
                self.set_training_address_same(True)
            else:
                self.set_training_address_same(False)
                self.fill_training_address(training_address)

        self.select_mobilization(mobilization)
        if mobilization:
            if mobilization_address is None:
                self.set_mobilization_address_same(True)
            else:
                self.set_mobilization_address_same(False)
                self.fill_mobilization_address(mobilization_address)

        if other_services is not None:
            self.fill_other_services(other_services)
        if website is not None:
            self.fill_website(website)
