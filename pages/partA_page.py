from pages.base_page import BasePage


class PartAPage(BasePage):

    @property
    def title(self):
        return self.page.locator("//h2[contains(text(),'Step 1')]")

    @property
    def sub_title(self):
        return self.page.locator("//h2[contains(text(),'Step 1')]//following-sibling::p")

    @property
    def dashboard_link(self):
        return self.page.locator("//a[text()='Dashboard']")


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
    def tan_number_input(self):
        return self.page.locator("input[name='tan_number']")

    @property
    def gst_number_input(self):
        return self.page.locator("input[name='gst_number']")

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

    @property
    def office_photo_upload_button(self):
        return self.page.locator("input[name='office_photo']")

    @property
    def submit_button(self):
        return self.page.locator("button[type='submit']")


    def fill_agency_name(self, name:str):
        self.agency_name_input.fill(name)

    def select_legal_constitution(self, legal_constitution:str):
        self.select_legal_constitution.select_option(value=legal_constitution)

    def fill_agency_date_of_establishment(self, date: str):
        self.date_of_incorporation_input.fill(date)

    def get_pan_number(self) -> str:
        return self.pan_number_field.get_attribute("value")

    def fill_tan(self, tan:str):
        self.tan_number_input.fill(tan)

    def fill_gst(self, gst:str):
        self.gst_number_input.fill(gst)

    def fill_address_line1(self, address1:str):
        self.address_line1_input.fill(address1)

    def fill_address_line2(self, address2:str):
        self.address_line2_input.fill(address2)

    def fill_branch_offices(self, offices:str):
        self.branch_offices_input.fill(offices)

    def fill_email(self, email:str):
        self.official_email_input.fill(email)

    def fill_mobile_number(self, mobile:str):
        self.mobile_number_input.fill(mobile)

    def fill_website(self, url: str):
        self.website_url_input.fill(url)

    def upload_office_photo(self, path:str):
        with self.page.expect_file_chooser() as fc_info:
            self.office_photo_upload_button.click()  # button that opens file dialog

        file_chooser = fc_info.value
        file_chooser.set_files(path)

    def click_submit(self):
        self.submit_button.click()
