import allure

from .base_page import BasePage


class HomePage(BasePage):

    # ── Navigation bar ────────────────────────────────────────────────────────

    @property
    def logout_button(self):
        return self.page.locator("//div[@class='text-blue-200']//following-sibling::a")

    @property
    def nav_home_link(self):
        return self.page.get_by_role("link", name="Home")

    @property
    def nav_notices_link(self):
        return self.page.get_by_role("link", name="Notices")

    @property
    def nav_guidelines_link(self):
        return self.page.get_by_role("link", name="Guidelines")

    @property
    def nav_downloads_link(self):
        return self.page.get_by_role("link", name="Downloads")

    @property
    def nav_contact_us_link(self):
        return self.page.get_by_role("link", name="Contact Us")

    # ── Hero section ──────────────────────────────────────────────────────────

    @property
    def continue_application_button(self):
        return self.page.locator(
            "//a[contains(normalize-space(.),'Continue Application')] | "
            "//button[contains(normalize-space(.),'Continue Application')]"
        ).first

    # ── My Application Status Card ────────────────────────────────────────────

    @property
    def application_status_card(self):
        return self.page.locator(".status-card").first

    @property
    def application_status_badge(self):
        # e.g. "IN PROGRESS", "SUBMITTED", "APPROVED", "REJECTED"
        return self.page.locator("//span[contains(@class,'sbadge')]").first

    @property
    def registration_id_value(self):
        return self.page.locator("//div[@class='sc-regid']//strong").first

    @property
    def registration_date_text(self):
        return self.page.locator("//div[@class='sc-regid']//span | //div[@class='sc-regid']//small").first

    @property
    def status_message_text(self):
        return self.page.locator(
            "//div[contains(@class,'status-message') or contains(@class,'status-description')]"
        ).first

    # ── Form Completion Progress ──────────────────────────────────────────────

    @property
    def form_completion_progress_section(self):
        return self.page.locator(
            "//div[contains(.,'Form Completion Progress')]"
        ).first

    @property
    def completion_percentage(self):
        return self.page.locator(
            "//div[contains(.,'Form Completion Progress')]//span[contains(text(),'%')]"
        ).first

    @property
    def progress_bar(self):
        return self.page.locator(
            "//div[contains(@class,'progress-bar') or @role='progressbar']"
        ).first

    def part_step(self, part_label: str):
        """Returns the step tile for a given label, e.g. 'Part A', 'Docs', 'Decl.', 'Auth.'"""
        return self.page.locator(
            f"//div[contains(@class,'part') or contains(@class,'step')]"
            f"[contains(normalize-space(.),'{part_label}')]"
        ).first

    @property
    def continue_filling_form_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Continue Filling Form')]")

    @property
    def no_application_prompt(self):
        """Shown when the user has pre-registered but not yet started the 8-step wizard."""
        return self.page.locator(
            "//p[contains(text(),'not yet submitted')] | "
            "//div[contains(text(),'not yet submitted')] | "
            "//p[contains(text(),'begin')] | "
            "//a[contains(text(),'begin')]"
        ).first

    # ── Track Application Card ────────────────────────────────────────────────

    @property
    def track_application_card(self):
        return self.page.locator(
            "//div[contains(@class,'card') and contains(.,'Track Application')]"
        ).first

    @property
    def track_now_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'TRACK NOW')]")

    # ── Notice Board ──────────────────────────────────────────────────────────

    @property
    def notice_board_section(self):
        return self.page.locator(
            "//div[contains(normalize-space(.),('NOTICE BOARD'))]"
        ).first

    @property
    def notice_items(self):
        return self.page.locator(
            "//div[contains(@class,'notice-item')] | "
            "//li[contains(@class,'notice')]"
        )

    @property
    def notice_type_badges(self):
        return self.page.locator(
            "//span[normalize-space(text())='NEW' or "
            "normalize-space(text())='ALERT' or "
            "normalize-space(text())='INFO' or "
            "normalize-space(text())='URGENT']"
        )

    @property
    def view_all_notices_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'View all notices')]")

    @property
    def no_notices_placeholder(self):
        return self.page.locator(
            "//p[contains(text(),'No notices available')] | "
            "//div[contains(text(),'No notices available')]"
        ).first

    # ── Quick Links ───────────────────────────────────────────────────────────

    @property
    def quick_links_section(self):
        return self.page.locator(
            "//div[contains(normalize-space(.),('QUICK LINKS'))]"
        ).first

    def quick_link(self, text: str):
        return self.page.locator(f"//a[contains(normalize-space(.),'{text}')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Home page directly")
    def open(self):
        import os
        base = os.getenv("MPPA_BASE_URL", "https://devmppa.sppuef.in/module/agency/auth")
        self.navigate(f"{base}/home.php")

    @allure.step("Click 'Continue Application'")
    def click_continue_application(self):
        self.continue_application_button.click()

    @allure.step("Click 'Continue Filling Form'")
    def click_continue_filling_form(self):
        self.continue_filling_form_link.click()

    @allure.step("Click 'TRACK NOW'")
    def click_track_now(self):
        self.track_now_link.click()

    @allure.step("Click Quick Link: '{text}'")
    def click_quick_link(self, text: str):
        self.quick_link(text).click()

    @allure.step("Click 'View all notices'")
    def click_view_all_notices(self):
        self.view_all_notices_link.click()

    @allure.step("Logout")
    def logout(self):
        self.logout_button.click()
