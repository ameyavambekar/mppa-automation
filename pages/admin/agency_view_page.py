import re

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE


class AdminAgencyViewPage(BasePage):
    """Admin — Agency detail view (/module/admin/dashboard/agency_view.php?id=N).

    Header (Registration ID + status badge), step-by-step Form-I data in the
    main area, and right-sidebar panels: Registration Info (8 metadata
    fields), Completion Status (per-step badges + percentage bar) and Update
    Status (remarks + Approve / Reject / Suspend, with an MPPA number preview
    for submitted agencies).

    NOTE: unlike the list page, no HTML capture of this view exists yet —
    locators here are text-anchored best guesses from the AIO spec and the
    admin portal's shared styles. Verify against the live page and tighten
    selectors on first run (same approach as PartAPage's TODO locators).
    """

    MPPA_PATTERN = re.compile(r"MPPA/MH/\d{4}/(\d+)")

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def page_heading(self):
        # Page title strip with the Registration ID
        return self.page.locator(".adm-page-title").first

    @property
    def header_status_badge(self):
        # TODO: verify — first status pill (.sb) in the header/title area
        return self.page.locator(".adm-page-title .sb, .adm-page-title span[class*='sb-']").first

    @property
    def back_to_list_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Back to List')]")

    @property
    def download_zip_button(self):
        return self.page.locator("//*[self::a or self::button][contains(normalize-space(.),'Download ZIP')]")

    @property
    def generate_pdf_button(self):
        return self.page.locator("//*[self::a or self::button][contains(normalize-space(.),'Generate PDF')]")

    # ── Alerts ────────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".salt-s, .alert-success")

    @property
    def error_alert(self):
        return self.page.locator(".salt-e, .alert-error")

    # ── Registration Info sidebar ─────────────────────────────────────────────

    @property
    def registration_info_panel(self):
        return self.page.locator(
            "//*[contains(text(),'Registration Info')]/ancestor::div[contains(@class,'scard') or contains(@class,'panel')][1]"
        )

    def info_field(self, label: str):
        """A Registration Info value by its label, e.g. 'Username', 'Email',
        'PAN', 'Last Login', 'Completion'."""
        return self.registration_info_panel.locator(
            f"//*[contains(normalize-space(text()),'{label}')]/following-sibling::*[1]"
        )

    # ── Completion Status panel ───────────────────────────────────────────────

    @property
    def completion_panel(self):
        return self.page.locator(
            "//*[contains(text(),'Completion Status')]/ancestor::div[contains(@class,'scard') or contains(@class,'panel')][1]"
        )

    @property
    def completion_percentage(self):
        # e.g. "37%"
        return self.completion_panel.locator("text=/\\d+\\s*%/").first

    @property
    def step_status_badges(self):
        # One badge per wizard step: SUBMITTED / PENDING / COMPLETE
        return self.completion_panel.locator(".sb, span[class*='sb-']")

    # ── Form-I data area ──────────────────────────────────────────────────────

    @property
    def not_submitted_placeholders(self):
        # Placeholder shown for steps the agency hasn't submitted yet
        return self.page.get_by_text("Not yet submitted")

    def form_step_section(self, title: str):
        """A Form-I step section by its heading text, e.g. 'Part A'."""
        return self.page.locator(
            f"//*[contains(@class,'section-header') or self::h2 or self::h3][contains(normalize-space(.),'{title}')]"
        )

    # ── Update Status panel ───────────────────────────────────────────────────

    @property
    def update_status_panel(self):
        return self.page.locator(
            "//*[contains(text(),'Update Status')]/ancestor::div[contains(@class,'scard') or contains(@class,'panel')][1]"
        )

    @property
    def remarks_textarea(self):
        return self.page.locator("textarea[name='remarks']")

    @property
    def approve_button(self):
        return self.page.locator("//button[contains(normalize-space(.),'Approve')]")

    @property
    def reject_button(self):
        return self.page.locator("//button[contains(normalize-space(.),'Reject')]")

    @property
    def suspend_button(self):
        return self.page.locator("//button[contains(normalize-space(.),'Suspend')]")

    @property
    def mppa_preview(self):
        # "On approval, Reg ID will become: MPPA/MH/2026/000046"
        return self.page.locator("//*[contains(text(),'On approval')]")

    @property
    def already_approved_warning(self):
        # "This agency is already approved. A new MPPA number will NOT be assigned."
        return self.page.locator("//*[contains(text(),'already approved')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open agency detail view for id: {agency_id}")
    def open(self, agency_id: int):
        self.navigate(f"{ADMIN_BASE}/dashboard/agency_view.php?id={agency_id}")

    @allure.step("Click '← Back to List'")
    def click_back_to_list(self):
        self.back_to_list_link.click()

    @allure.step("Fill remarks")
    def fill_remarks(self, remarks: str):
        self.remarks_textarea.fill(remarks)

    @allure.step("Click 'Approve Application' and handle any confirm dialog")
    def approve_and_handle_alert(self, action: str = "accept") -> str:
        return self.click_and_handle_alert(self.approve_button, action=action)

    @allure.step("Click 'Reject Application' and handle any confirm dialog")
    def reject_and_handle_alert(self, action: str = "accept") -> str:
        return self.click_and_handle_alert(self.reject_button, action=action)

    @allure.step("Click 'Suspend Agency' and handle any confirm dialog")
    def suspend_and_handle_alert(self, action: str = "accept") -> str:
        return self.click_and_handle_alert(self.suspend_button, action=action)

    @allure.step("Click 'Download ZIP' and wait for the download")
    def download_zip(self):
        """Returns the Playwright Download object."""
        with self.page.expect_download() as download_info:
            self.download_zip_button.click()
        return download_info.value

    @allure.step("Click 'Generate PDF'")
    def generate_pdf(self):
        """The PDF either opens in a new tab or downloads — returns
        ('page', Page) or ('download', Download) accordingly."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        try:
            with self.page.context.expect_page(timeout=10000) as page_info:
                self.generate_pdf_button.click()
            return "page", page_info.value
        except PlaywrightTimeoutError:
            with self.page.expect_download(timeout=10000) as download_info:
                self.generate_pdf_button.click()
            return "download", download_info.value

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_previewed_mppa_number(self) -> str:
        """The full MPPA number shown in the preview block, e.g.
        'MPPA/MH/2026/000046', or '' when no preview is shown."""
        if self.mppa_preview.count() == 0:
            return ""
        match = self.MPPA_PATTERN.search(self.mppa_preview.first.text_content())
        return match.group() if match else ""

    @staticmethod
    def mppa_sequence_number(mppa: str) -> int:
        """The trailing sequence as an int, e.g. 'MPPA/MH/2026/000046' → 46."""
        return int(mppa.rsplit("/", 1)[1])
