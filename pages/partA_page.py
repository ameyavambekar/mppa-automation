import allure

from pages.base_page import BasePage


class PartAPage(BasePage):

    # ── Page headings ─────────────────────────────────────────────────────────

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 1')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 1')]//following-sibling::p")

    # ── Navigation ────────────────────────────────────────────────────────────

    @property
    def dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")

    # ── Agency Identity fields ────────────────────────────────────────────────

    @property
    def agency_name_input(self):
        return self.page.locator("input[name='agency_name']")

    @property
    def legal_constitution_select(self):
        return self.page.locator("select[name='agency_type']")

    @property
    def date_of_incorporation_input(self):
        return self.page.locator("input[name='date_of_establishment']")

    @property
    def pan_number_field(self):
        return self.page.locator("input[readonly]")

    @property
    def pan_helper_text(self):
        return self.page.locator(".helper-text").first

    @property
    def tan_number_input(self):
        return self.page.locator("input[name='tan_number']")

    @property
    def gst_number_input(self):
        return self.page.locator("input[name='gst_number']")

    # ── Address & contact fields ──────────────────────────────────────────────

    @property
    def address_line1_input(self):
        return self.page.locator("input[name='address_line1']")

    @property
    def address_line2_input(self):
        return self.page.locator("input[name='address_line2']")

    @property
    def branch_offices_input(self):
        return self.page.locator("input[name='branch_offices']")

    @property
    def official_email_input(self):
        return self.page.locator("input[name='email']")

    @property
    def mobile_number_input(self):
        return self.page.locator("input[name='mobile']")

    @property
    def website_url_input(self):
        return self.page.locator("input[name='website']")

    # ── File upload ───────────────────────────────────────────────────────────

    @property
    def office_photo_upload_button(self):
        return self.page.locator("input[name='office_photo']")

    # ── Submit ────────────────────────────────────────────────────────────────

    @property
    def submit_button(self):
        return self.page.locator("button[type='submit']")

    # ── Inline validation errors ──────────────────────────────────────────────

    @property
    def agency_name_error(self):
        # TODO: identify selector for agency name inline validation error
        return self.page.locator("TODO-agency-name-error")

    @property
    def legal_constitution_error(self):
        # TODO: identify selector for legal constitution inline validation error
        return self.page.locator("TODO-legal-constitution-error")

    @property
    def date_of_incorporation_error(self):
        # TODO: identify selector for date of incorporation inline validation error
        return self.page.locator("TODO-date-of-incorporation-error")

    @property
    def address_line1_error(self):
        # TODO: identify selector for address line 1 inline validation error
        return self.page.locator("TODO-address-line1-error")

    @property
    def email_error(self):
        # TODO: identify selector for official email inline validation error
        return self.page.locator("TODO-email-error")

    @property
    def mobile_error(self):
        # TODO: identify selector for mobile number inline validation error
        return self.page.locator("TODO-mobile-error")

    @property
    def tan_error(self):
        # TODO: identify selector for TAN number inline validation error
        return self.page.locator("TODO-tan-error")

    @property
    def gst_error(self):
        # TODO: identify selector for GST number inline validation error
        return self.page.locator("TODO-gst-error")

    @property
    def website_error(self):
        # TODO: identify selector for website URL inline validation error
        return self.page.locator("TODO-website-error")

    @property
    def office_photo_error(self):
        # TODO: identify selector for office photo upload inline validation error
        return self.page.locator("//div[contains(@class,'alert-error')]")

    @property
    def agency_name_warning(self):
        # TODO: identify selector for non-blocking duplicate agency name warning banner
        return self.page.locator("TODO-agency-name-warning")

    # ── Step progress & wizard navigation ────────────────────────────────────

    @property
    def step_completion_message(self):
        # TODO: identify selector for "Step 1 of 8 Completed" success message
        return self.page.locator("TODO-step-completion-message")

    def step_nav_item(self, step_number: int):
        """Returns the clickable step indicator for step_number in the wizard progress bar."""
        return self.page.locator(f"//p[contains(text(),'Step 0{step_number}')]").first

    @property
    def step_locked_message(self):
        # TODO: identify selector for "Please complete and save the current step before proceeding." tooltip/message
        return self.page.locator("TODO-step-locked-message")

    # ── Unsaved-changes dialogs (browser back button) ────────────────────────

    @property
    def unsaved_changes_dialog_stay(self):
        # TODO: identify selector for "Stay" button in the browser-back unsaved-changes dialog
        return self.page.locator("TODO-dialog-stay-button")

    @property
    def unsaved_changes_dialog_leave(self):
        # TODO: identify selector for "Leave" button in the browser-back unsaved-changes dialog
        return self.page.locator("TODO-dialog-leave-button")

    # ── Unsaved-changes dialogs (← Dashboard) ────────────────────────────────

    @property
    def dashboard_dialog_cancel(self):
        # TODO: identify selector for "Cancel" button in the "← Dashboard" unsaved-changes dialog
        return self.page.locator("TODO-dashboard-dialog-cancel")

    @property
    def dashboard_dialog_save_exit(self):
        # TODO: identify selector for "Save & Exit" button in the "← Dashboard" dialog
        return self.page.locator("TODO-dashboard-dialog-save-exit")

    @property
    def dashboard_dialog_exit_without_saving(self):
        # TODO: identify selector for "Exit Without Saving" button in the "← Dashboard" dialog
        return self.page.locator("TODO-dashboard-dialog-exit-without-saving")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Fill Agency Name: {name}")
    def fill_agency_name(self, name: str):
        self.agency_name_input.fill(name)
        self.agency_name_input.blur()

    @allure.step("Select Legal Constitution: {legal_constitution}")
    def select_legal_constitution(self, legal_constitution: str):
        self.legal_constitution_select.select_option(value=legal_constitution)

    @allure.step("Fill Date of Incorporation: {date}")
    def fill_agency_date_of_establishment(self, date: str):
        self.date_of_incorporation_input.fill(date)
        self.date_of_incorporation_input.blur()

    def get_pan_number(self) -> str:
        return self.pan_number_field.get_attribute("value")

    @allure.step("Fill TAN: {tan}")
    def fill_tan(self, tan: str):
        self.tan_number_input.fill(tan)
        self.tan_number_input.blur()

    @allure.step("Fill GST: {gst}")
    def fill_gst(self, gst: str):
        self.gst_number_input.fill(gst)
        self.gst_number_input.blur()

    @allure.step("Fill Address Line 1: {address1}")
    def fill_address_line1(self, address1: str):
        self.address_line1_input.fill(address1)
        self.address_line1_input.blur()

    @allure.step("Fill Address Line 2: {address2}")
    def fill_address_line2(self, address2: str):
        self.address_line2_input.fill(address2)
        self.address_line2_input.blur()

    @allure.step("Fill Branch Offices")
    def fill_branch_offices(self, offices: str):
        self.branch_offices_input.fill(offices)

    @allure.step("Fill Official Email: {email}")
    def fill_email(self, email: str):
        self.official_email_input.fill(email)
        self.official_email_input.blur()

    @allure.step("Fill Mobile Number: {mobile}")
    def fill_mobile_number(self, mobile: str):
        self.mobile_number_input.fill(mobile)
        self.mobile_number_input.blur()

    @allure.step("Fill Website URL: {url}")
    def fill_website(self, url: str):
        self.website_url_input.fill(url)
        self.website_url_input.blur()

    @allure.step("Upload Office Photo via file chooser: {path}")
    def upload_office_photo(self, path: str):
        with self.page.expect_file_chooser() as fc_info:
            self.office_photo_upload_button.click()
        fc_info.value.set_files(path)

    @allure.step("Set Office Photo: {path}")
    def set_office_photo(self, path: str):
        """Sets office photo directly via set_input_files (no file-chooser dialog)."""
        self.office_photo_upload_button.set_input_files(path)

    @allure.step("Click Save / Next")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click Save / Next")
    def click_save_next(self):
        self.submit_button.click()

    @allure.step("Click Dashboard link")
    def click_dashboard_link(self):
        self.dashboard_link.click()


    upload_photo_error = "Failed to upload office photo."
