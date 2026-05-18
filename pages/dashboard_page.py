import allure

from .base_page import BasePage


class DashboardPage(BasePage):

    # ── Logout ────────────────────────────────────────────────────────────────

    @property
    def logout_button(self):
        return self.page.locator("//div[@class='text-blue-200']//following-sibling::a")

    # ── My Application Status Card ────────────────────────────────────────────

    @property
    def application_status_card(self):
        return self.page.locator("//div[contains(.,'My Application Status')]").first

    @property
    def registration_id_value(self):
        # Registration IDs: MPPA/YYYY/NNNNNN
        return self.page.locator("//td[contains(text(),'Reg') or contains(text(),'Registration')]//following-sibling::td | //span[contains(text(),'MPPA/') or contains(text(),'MPPA-')]").first

    @property
    def application_status_badge(self):
        return self.page.locator("//span[contains(@class,'badge') or contains(@class,'status-badge')]").first

    @property
    def status_message_text(self):
        return self.page.locator("//div[contains(@class,'status-message') or contains(@class,'status-description')]").first

    @property
    def view_full_application_link(self):
        return self.page.locator("//a[contains(text(),'View Full Application')]")

    @property
    def no_application_prompt(self):
        return self.page.locator("//p[contains(text(),'not yet submitted')] | //div[contains(text(),'not yet submitted')]").first

    # ── Progress Tracker ──────────────────────────────────────────────────────

    @property
    def progress_tracker(self):
        return self.page.locator("//div[contains(@class,'progress-tracker') or contains(@class,'stepper') or contains(@class,'step-indicator')]").first

    @property
    def completion_percentage(self):
        return self.page.locator("//span[contains(@class,'percent') or contains(text(),'%')]").first

    def part_step(self, part_label: str):
        """Returns the step node for a given part label, e.g. 'Part A', 'Docs'."""
        return self.page.locator(f"//div[contains(@class,'step') and contains(.,'{part_label}')]").first

    # ── My Application Card ───────────────────────────────────────────────────

    @property
    def my_application_card(self):
        return self.page.locator("//div[contains(@class,'card') and contains(.,'My Application') and not(contains(.,'Status'))]").first

    @property
    def view_details_link(self):
        return self.page.locator("//a[contains(text(),'VIEW DETAILS')]")

    # ── Track Application Card ────────────────────────────────────────────────

    @property
    def track_application_card(self):
        return self.page.locator("//div[contains(@class,'card') and contains(.,'Track Application')]").first

    @property
    def track_now_link(self):
        return self.page.locator("//a[contains(text(),'TRACK NOW')]")

    @property
    def track_modal(self):
        return self.page.locator("//div[contains(@class,'modal')]").filter(has_text="Track Application Status")

    @property
    def track_modal_title(self):
        return self.page.locator("//h5[contains(text(),'Track Application Status')] | //h4[contains(text(),'Track Application Status')]")

    @property
    def track_modal_input(self):
        return self.page.locator("//input[@placeholder[contains(.,'MPPA') or contains(.,'Registration')]]")

    @property
    def track_modal_track_button(self):
        return self.page.locator("//div[contains(@class,'modal')]//button[normalize-space(text())='TRACK']")

    @property
    def track_modal_close_button(self):
        return self.page.locator("//div[contains(@class,'modal')]//button[contains(@class,'close') or normalize-space(text())='×' or normalize-space(text())='✕']")

    # ── Notice Board ──────────────────────────────────────────────────────────

    @property
    def notice_board_section(self):
        return self.page.locator("//div[contains(@class,'notice-board') or (contains(@class,'card') and contains(.,'Notice Board'))]").first

    @property
    def notice_items(self):
        return self.page.locator("//div[contains(@class,'notice-item')] | //li[contains(@class,'notice')]")

    @property
    def notice_type_badges(self):
        return self.page.locator("//span[text()='NEW' or text()='ALERT' or text()='INFO' or text()='URGENT']")

    @property
    def view_all_notices_link(self):
        return self.page.locator("//a[contains(text(),'View all notices')]")

    @property
    def no_notices_placeholder(self):
        return self.page.locator("//p[contains(text(),'No notices available')] | //div[contains(text(),'No notices available')]").first

    # ── Quick Links ───────────────────────────────────────────────────────────

    @property
    def quick_links_section(self):
        return self.page.locator("//div[contains(@class,'quick-links') or (contains(@class,'card') and contains(.,'Quick Links'))]").first

    def quick_link(self, text: str):
        return self.page.locator(f"//a[contains(normalize-space(.),'{text}')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Logout")
    def logout(self):
        self.logout_button.click()

    @allure.step("Click 'View Full Application'")
    def click_view_full_application(self):
        self.view_full_application_link.click()

    @allure.step("Click 'VIEW DETAILS'")
    def click_view_details(self):
        self.view_details_link.click()

    @allure.step("Open Track Application modal")
    def open_track_modal(self):
        self.track_now_link.click()

    @allure.step("Submit track request for '{registration_id}'")
    def track_application(self, registration_id: str):
        self.track_modal_input.fill(registration_id)
        self.track_modal_track_button.click()

    @allure.step("Close Track Application modal")
    def close_track_modal(self):
        self.track_modal_close_button.click()

    @allure.step("Click Quick Link: '{text}'")
    def click_quick_link(self, text: str):
        self.quick_link(text).click()
