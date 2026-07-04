import allure

from .base_page import BasePage
from config import AUTH_BASE


class HomePage(BasePage):

    # ── Navigation bar ────────────────────────────────────────────────────────

    @property
    def logout_button(self):
        return self.page.locator("//a[text()='Logout']").first

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

    @property
    def view_full_application(self):
        return self.page.locator("//a[contains(text(),'View Full Application')]").first

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
    def form_completion_progress_label(self):
        return self.page.locator(".prog-label").first

    @property
    def form_completion_percentage(self):
        return self.page.locator(".prog-pct").first

    @property
    def progress_bar(self):
        return self.page.locator(".prog-track").first

    def part_step(self, part_label: str):
        """Returns the step tile for a given label, e.g. 'Part A', 'Docs', 'Decl.', 'Auth.'"""
        return self.page.locator(f"//span[contains(text(),'{part_label}')]//preceding-sibling::div//parent::div").first

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

    # ── Hero Section (Expired State) ─────────────────────────────────────────

    @property
    def renew_now_hero_button(self):
        return self.page.locator("//a[contains(normalize-space(.),'Renew Now')]").first

    @property
    def view_cert_hero_button(self):
        return self.page.locator("//a[contains(normalize-space(.),'View Cert')]").first

    # ── Expired Certificate Card ──────────────────────────────────────────────

    @property
    def expired_cert_card(self):
        return self.page.locator(".cert-card.expired").first

    @property
    def expired_cert_title(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//div[contains(text(),'Certificate Expired')]"
        ).first

    @property
    def expired_cert_subtitle(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//div[contains(text(),'Renew immediately')]"
        ).first

    @property
    def expired_cert_badge(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//span[contains(@class,'sbadge-rejected')]"
        ).first

    @property
    def expired_cert_mppa_number(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//span[contains(@class,'mppa-badge')]"
        ).first

    @property
    def expired_cert_valid_from_value(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//div[text()='Valid From']/following-sibling::div"
        ).first

    @property
    def expired_cert_valid_until_value(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//div[text()='Valid Until']/following-sibling::div"
        ).first

    @property
    def expired_cert_days_overdue_text(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//span[contains(text(),'days overdue')]"
        ).first

    @property
    def view_expired_cert_button(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//a[contains(@class,'cert-btn-view')]"
        ).first

    @property
    def start_renewal_from_cert_button(self):
        return self.page.locator(
            "//div[contains(@class,'cert-card') and contains(@class,'expired')]"
            "//a[contains(@class,'cert-btn-renew')]"
        ).first

    # ── Renewal Service Card ──────────────────────────────────────────────────

    @property
    def renewal_service_card(self):
        return self.page.locator("a.service-card.red").first

    @property
    def renewal_service_card_title(self):
        return self.page.locator(
            "//a[contains(@class,'service-card') and contains(@class,'red')]"
            "//p[contains(@class,'card-title')]"
        ).first

    @property
    def renewal_service_card_expiry_date(self):
        return self.page.locator(
            "//a[contains(@class,'service-card') and contains(@class,'red')]"
            "//p[contains(@class,'card-desc')]//strong"
        ).first

    # ── Sidebar Expired Warning ───────────────────────────────────────────────

    @property
    def cert_expired_sidebar_warning(self):
        return self.page.locator(
            "//p[contains(text(),'Certificate Expired!')]/parent::div"
        ).first

    @property
    def cert_expired_sidebar_title(self):
        return self.page.locator(
            "//p[contains(text(),'Certificate Expired!')]"
        ).first

    @property
    def cert_expired_sidebar_message(self):
        return self.page.locator(
            "//p[contains(text(),'Certificate Expired!')]/following-sibling::p"
        ).first

    @property
    def cert_expired_sidebar_renew_button(self):
        return self.page.locator(
            "//p[contains(text(),'Certificate Expired!')]/following-sibling::a"
        ).first

    # ── Track Application Card ────────────────────────────────────────────────

    @property
    def track_application_card(self):
        return self.page.locator("//span[contains(text(),'Track Now')]//parent::div").first

    @property
    def track_application_card_text(self):
        return self.page.locator("//p[text()='Track Application']//following-sibling::p")

    @property
    def track_now_link(self):
        return self.page.locator("//span[contains(text(),'Track Now')]")

    @property
    def track_application_modal(self):
        return self.page.locator("//h3[contains(text(),'Track Application Status')]//parent::div//parent::div").first

    @property
    def track_application_input(self):
        return self.page.locator("#trackInput")

    @property
    def track_application_button(self):
        return self.page.locator("//button[text()='Track']")

    @property
    def track_application_close_button(self):
        return self.page.locator("//h3[contains(text(),'Track Application Status')]//following-sibling::button")

    @property
    def track_application_error(self):
        return self.page.locator("//div[@id='trackResult']//div")

    # ── Notice Board ──────────────────────────────────────────────────────────

    @property
    def notice_board_section(self):
        return self.page.locator("//div[contains(text(),'Notice Board')]").first

    @property
    def notice_items(self):
        return self.page.locator("//div[@class='notice-item']")

    @property
    def notice_type_badges(self):
        return self.page.locator("//div[@class='notice-item']//span[@class='notice-badge']")

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
        return self.page.locator("//div[contains(text(),'Quick Links')]").first

    def quick_link(self, text: str):
        return self.page.locator(f"//a[contains(normalize-space(.),'{text}')]")

    # ──  Submit Appeal ───────────────────────────────────────────────────────────────
    @property
    def submit_appeal_card(self):
        return self.page.locator("//p[text()='Submit Appeal']//parent::a")


    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Home page directly")
    def open(self):
        self.navigate(f"{AUTH_BASE}/home.php")

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

    def enter_registration_id(self, registration_id_value:str):
        self.track_application_input.fill(registration_id_value)


    no_application_found_with_id = "⚠️No application found with ID: 2627521016"
    invalid_registration_id_format = "⚠️Invalid ID format. Expected 10-digit ID e.g. 2627100001."

    def click_view_full_application(self):
        self.view_full_application.click()

    @allure.step("Click 'Renew Now' (hero)")
    def click_renew_now_hero(self):
        self.renew_now_hero_button.click()

    @allure.step("Click 'View Cert' (hero)")
    def click_view_cert_hero(self):
        self.view_cert_hero_button.click()

    @allure.step("Click 'View (Expired)' on certificate card")
    def click_view_expired_cert(self):
        self.view_expired_cert_button.click()

    @allure.step("Click 'Start Renewal' on certificate card")
    def click_start_renewal_from_cert(self):
        self.start_renewal_from_cert_button.click()

    @allure.step("Click renewal service card")
    def click_renewal_service_card(self):
        self.renewal_service_card.click()

    @allure.step("Click 'Start Renewal' in sidebar warning")
    def click_start_renewal_from_sidebar(self):
        self.cert_expired_sidebar_renew_button.click()
