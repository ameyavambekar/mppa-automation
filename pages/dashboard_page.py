import allure

from config import FORMS_BASE
from .base_page import BasePage

DASHBOARD_URL = f"{FORMS_BASE}/dashboard.php"


class DashboardPage(BasePage):
    """Application dashboard (forms/dashboard.php).

    Since the portal redesign, login no longer lands here: incomplete
    registrations go straight to the Form-I wizard (see ``PartAPage``), and
    dashboard.php sends them back to the login page. Only submitted / paid
    applications may still reach it — locators below are unverified for that.

    For a paid agency it is "My Dashboard" (dev, 20-Nov-2026): status "UNDER REVIEW", the registration
    details, Step 0 – Step 8 ticked, and ``.qa-tile`` links — "My Dashboard" (home.php), "View my
    application" (view_application.php), "Download application PDF" (download_pdf.php, new tab; HTTP 500,
    defect "Agency Dashboard" #10) and "Helpdesk". It has no link to the payment receipt (defect
    "Step 8 — Fees & Payment" #20).
    """

    VIEW_APPLICATION_LABEL = "View my application"
    DOWNLOAD_PDF_LABEL = "Download application PDF"
    DOWNLOAD_PDF_HREF = "download_pdf.php"

    # ── My Dashboard (paid agency) ────────────────────────────────────────────

    def tile(self, label: str):
        """A ``.qa-tile`` link by its bold title, e.g. 'Download application PDF'."""
        return self.page.locator("a.qa-tile").filter(has=self.page.locator("b", has_text=label))

    @property
    def download_pdf_link(self):
        return self.tile(self.DOWNLOAD_PDF_LABEL)

    @property
    def receipt_links(self):
        """Links to the payment receipt (receipt.php) — none on dev (20-Nov-2026)."""
        return self.page.locator("a[href*='receipt.php']")

    @allure.step("Open My Dashboard")
    def open(self):
        self.navigate(DASHBOARD_URL)
        self.wait_for_load()

    # ── Logout ────────────────────────────────────────────────────────────────

    @property
    def logout_button(self):
        return self.page.locator("//a[text()='Logout']").first

    # On View Application Dashboard

    @property
    def steps_completed(self):
        return self.page.locator("//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p//p[contains(text(),'Application Progress')]//following-sibling::p").first

    @property
    def completion_percentage(self):
        return self.page.locator("//p[text()='Completed']//preceding-sibling::span").first

    def step_card(self, part_label: str):
        """Returns the step node for a given step label, e.g. 'partA', 'partB','partC', 'enclosures', 'declaration','authorization','partE','partF' etc."""
        return self.page.locator(f"//div[contains(text(),'Registration Steps')]//following-sibling::div[1]//div[contains(@onclick,'{part_label}')]").first

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
    def submitted_application_read_only_preview(self):
        return self.page.locator("//div//strong[contains(text(), 'Read-Only Preview')]")

    def step_nav_item(self, step_number: int):
        """Returns the clickable step indicator for step_number in the wizard progress bar."""
        return self.page.locator(f"//p[contains(text(),'Step 0{step_number}')]").first


    @property
    def home_link(self):
        return self.page.get_by_role("link", name="← Home")

    def get_url(self) -> str:
        return self.page.url
