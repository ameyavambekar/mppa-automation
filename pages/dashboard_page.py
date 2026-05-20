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
        return self.page.locator(".status-card").first

    @property
    def registration_id_value(self):
        # Registration IDs: MPPA/YYYY/NNNNNN
        return self.page.locator("//div[@class='sc-regid']//strong").first

    @property
    def application_status_badge(self):
        return self.page.locator("//span[contains(@class,'sbadge')]").first

    @property
    def status_message_text(self):
        return self.page.locator("//div[contains(@class,'status-message') or contains(@class,'status-description')]").first

    @property
    def continue_filling_form_link(self):
        return self.page.locator("//a[contains(text(),'Continue Filling Form')]")

    @property
    def no_application_prompt(self):
        return self.page.locator("//p[contains(text(),'not yet submitted')] | //div[contains(text(),'not yet submitted')]").first

    # ── Progress Tracker ──────────────────────────────────────────────────────

    @property
    def steps_completed(self):
        return self.page.locator("//p[contains(text(),'Application Progress')]//following-sibling::p").first

    @property
    def completion_percentage(self):
        return self.page.locator("//p[text()='Completed']//preceding-sibling::span").first

    def step_card(self, part_label: str):
        """Returns the step node for a given step label, e.g. 'partA', 'partB','partC', 'enclosures', 'declaration','authorization','partE','partF' etc."""
        return self.page.locator(f"//div[contains(text(),'Registration Steps')]//following-sibling::div[1]//div[contains(@onclick,'{part_label}')]").first    @property

