import allure

from .base_page import BasePage


class DashboardPage(BasePage):

    # ── Logout ────────────────────────────────────────────────────────────────

    @property
    def logout_button(self):
        return self.page.locator("//div[@class='text-blue-200']//following-sibling::a")

    # On View Application Dashboard

    @property
    def steps_completed(self):
        return self.page.locator("//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p").first

    @property
    def completion_percentage(self):
        return self.page.locator("//p[text()='Completed']//preceding-sibling::span").first

    def step_card(self, part_label: str):
        """Returns the step node for a given step label, e.g. 'partA', 'partB','partC', 'enclosures', 'declaration','authorization','partE','partF' etc."""
        return self.page.locator(f"//div[contains(text(),'Registration Steps')]//following-sibling::div[1]//div[contains(@onclick,'{part_label}')]").first    @property

    @property
    def preview_and_submit_card(self):
        return self.page.get_by_text("🔒 Preview & Submit Complete")

    @property
    def need_help_card(self):
        return self.page.get_by_text("Need Help? For queries,")

    @property
    def preview_and_submit_button(self):
        return self.page.locator("//div[@class='action-bar'][1]//p[contains(text(),'Complete')]//parent::div//following-sibling::div//button")

    @property
    def about_step8_card(self):
        return self.page.get_by_text("💰 About Step 8 — Fees •")


    @property
    def home_link(self):
        return self.page.get_by_role("link", name="← Home")

