import allure

from pages.base_page import BasePage


class PartCPage(BasePage):
    """Step 3 — Operational & Infrastructure Details (Part C).

    Most inputs are radio/checkbox "option cards" — a <label class="option-card">
    wrapping the input. Selection styling is applied to the card via JS
    (``selected-card`` for radios, ``checked-card`` for checkboxes), so card
    locators are exposed alongside the raw inputs for state assertions.

    Validation failures on submit surface as JS ``alert()`` dialogs — use
    ``click_submit_and_handle_alert()`` for those scenarios.
    """

    # ── Page headings ─────────────────────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 3')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 3')]/following-sibling::p")

    # ── Navigation ────────────────────────────────────────────────────────────

    @property
    def breadcrumb_dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")

    @property
    def back_to_step2_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Step 2')]").first

    @property
    def next_step4_link(self):
        # Top-right "Next: Step 4 →" shortcut
        return self.page.locator("//a[contains(normalize-space(.),'Next: Step 4')]")

    @property
    def proceed_to_step4_link(self):
        # Green button next to the submit button at the bottom of the form
        return self.page.locator("//a[contains(normalize-space(.),'Proceed to Step 4')]")

    # ── 1. Nature of Placement Activity ──────────────────────────────────────

    @property
    def placement_type_group(self):
        return self.page.locator("#placementGroup")

    def placement_type_radio(self, value: str):
        """value: 'B2B', 'B2C' or 'Both'."""
        return self.page.locator(f"input[name='placementType'][value='{value}']")

    def placement_type_card(self, value: str):
        return self.page.locator(
            f"//input[@name='placementType' and @value='{value}']/ancestor::label"
        )

    # ── 2. Sectors / Industries Served ────────────────────────────────────────

    @property
    def sectors_textarea(self):
        return self.page.locator("#sectorField")

    @property
    def sectors_error(self):
        return self.page.locator("#sectorErr")

    # ── 3. Training Provided ──────────────────────────────────────────────────

    @property
    def training_yes_radio(self):
        return self.page.locator("input[name='training'][value='yes']")

    @property
    def training_no_radio(self):
        return self.page.locator("input[name='training'][value='no']")

    @property
    def training_yes_card(self):
        return self.page.locator("//input[@name='training' and @value='yes']/ancestor::label")

    @property
    def training_no_card(self):
        return self.page.locator("//input[@name='training' and @value='no']/ancestor::label")

    @property
    def training_details_block(self):
        # Hidden unless training = Yes (gets the 'show' class)
        return self.page.locator("#trainingDetails")

    def training_mode_radio(self, value: str):
        """value: 'inhouse' or 'outsourced'."""
        return self.page.locator(f"input[name='mode'][value='{value}']")

    def training_mode_card(self, value: str):
        return self.page.locator(
            f"//input[@name='mode' and @value='{value}']/ancestor::label"
        )

    @property
    def training_capacity_input(self):
        return self.page.locator("#capacityField")

    @property
    def training_sectors_input(self):
        return self.page.locator("input[name='trainingSector']")

    # ── 4. Infrastructure Available ───────────────────────────────────────────

    def infrastructure_checkbox(self, option: str):
        """option: 'Office', 'Digital', 'Training' or 'Mobilisation'."""
        return self.page.locator(f"#infra_{option}")

    def infrastructure_card(self, option: str):
        return self.page.locator(f"//input[@id='infra_{option}']/ancestor::label")

    @property
    def infrastructure_checkboxes(self):
        return self.page.locator("input[name='infra[]']")

    @property
    def infrastructure_error(self):
        return self.page.locator("#infraErr")

    # ── 5. Placement Services Offered Through ────────────────────────────────

    @property
    def service_mode_group(self):
        return self.page.locator("#serviceModeGroup")

    def service_mode_radio(self, value: str):
        """value: 'online', 'offline' or 'both'."""
        return self.page.locator(f"input[name='serviceMode'][value='{value}']")

    def service_mode_card(self, value: str):
        return self.page.locator(
            f"//input[@name='serviceMode' and @value='{value}']/ancestor::label"
        )

    # ── 6. Any Other Services ─────────────────────────────────────────────────

    @property
    def other_services_textarea(self):
        return self.page.locator("textarea[name='otherServices']")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        # "💾 Save Part C" / "💾 Update Part C"
        return self.page.locator("button[type='submit']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Part-C Operational Details page directly")
    def open(self):
        import os
        base = os.getenv("MPPA_FORMS_BASE_URL", "https://devmppa.sppuef.in/module/agency/forms")
        self.navigate(f"{base}/partC.php")

    @allure.step("Select Nature of Placement Activity: {value}")
    def select_placement_type(self, value: str):
        """value: 'B2B', 'B2C' or 'Both'."""
        self.placement_type_card(value).click()

    @allure.step("Fill Sectors / Industries Served: {sectors}")
    def fill_sectors(self, sectors: str):
        self.sectors_textarea.fill(sectors)
        self.sectors_textarea.blur()

    @allure.step("Select Training Provided: Yes")
    def select_training_yes(self):
        self.training_yes_card.click()

    @allure.step("Select Training Provided: No")
    def select_training_no(self):
        self.training_no_card.click()

    @allure.step("Select Training Mode: {value}")
    def select_training_mode(self, value: str):
        """value: 'inhouse' or 'outsourced'. Only visible when training = Yes."""
        self.training_mode_card(value).click()

    @allure.step("Fill Annual Training Capacity: {capacity}")
    def fill_training_capacity(self, capacity: str):
        self.training_capacity_input.fill(str(capacity))
        self.training_capacity_input.blur()

    @allure.step("Fill Training Sectors: {sectors}")
    def fill_training_sectors(self, sectors: str):
        self.training_sectors_input.fill(sectors)
        self.training_sectors_input.blur()

    @allure.step("Set infrastructure '{option}' to {checked}")
    def set_infrastructure(self, option: str, checked: bool = True):
        """Clicks the option card only when the checkbox state differs, so it is
        safe to call regardless of the saved/pre-checked state."""
        if self.infrastructure_checkbox(option).is_checked() != checked:
            self.infrastructure_card(option).click()

    @allure.step("Select Placement Services Offered Through: {value}")
    def select_service_mode(self, value: str):
        """value: 'online', 'offline' or 'both'."""
        self.service_mode_card(value).click()

    @allure.step("Fill Any Other Services")
    def fill_other_services(self, services: str):
        self.other_services_textarea.fill(services)
        self.other_services_textarea.blur()

    @allure.step("Click Save Part C")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click Save Part C and handle alert")
    def click_submit_and_handle_alert(self, action: str = "dismiss") -> str:
        return self.click_and_handle_alert(self.submit_button, action=action)

    @allure.step("Click 'Proceed to Step 4'")
    def click_proceed_to_step4(self):
        self.proceed_to_step4_link.click()

    @allure.step("Click '← Step 2'")
    def click_back_to_step2(self):
        self.back_to_step2_link.click()

    @allure.step("Fill the complete Part-C form")
    def fill_part_c_form(self, placement_type: str, sectors: str,
                         training: bool = False, training_mode: str = None,
                         training_capacity: str = None, training_sectors: str = None,
                         infrastructure: list = None, service_mode: str = "online",
                         other_services: str = None):
        """Fills all Part-C sections. Training sub-fields are only filled when
        training is True (the block is hidden otherwise). infrastructure is a
        list of options from: 'Office', 'Digital', 'Training', 'Mobilisation'."""
        self.select_placement_type(placement_type)
        self.fill_sectors(sectors)
        if training:
            self.select_training_yes()
            if training_mode is not None:
                self.select_training_mode(training_mode)
            if training_capacity is not None:
                self.fill_training_capacity(training_capacity)
            if training_sectors is not None:
                self.fill_training_sectors(training_sectors)
        else:
            self.select_training_no()
        for option in (infrastructure or []):
            self.set_infrastructure(option, True)
        self.select_service_mode(service_mode)
        if other_services is not None:
            self.fill_other_services(other_services)
