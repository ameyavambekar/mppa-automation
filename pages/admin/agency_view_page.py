import re

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE


class AdminAgencyViewPage(BasePage):
    """Admin — an application's page (/module/admin/dashboard/agency_view.php?id=N), opened with Review / View on
    the Applications list. Locators read on dev 17-Nov-2026.

    * Header ``header.avh``: eyebrow "Application for registration · Form-I", the Registration ID as the title
      (``h1.avh-title``, also the "Registration ID" chip), a status pill (Submitted / Approved / …), Stage,
      District, Type and Submitted items, and the links Back to list, Download documents (ZIP) and
      Application PDF (opens in a new tab).
    * An approved application shows a read-only notice and no decision buttons.
    * "Application processing" (``#wfPanel``) — the review workflow (covered by the KAN-12 review-loop tests).
    * Form-I data, one ``.av-section`` per step (``STEP_SECTIONS``), then the Registration Info and Completion
      Status panels.

    The browser tab title is "View Agency — <Registration ID> | Admin".
    """

    TAB_TITLE = re.compile(r"^View Agency — \d{13} \| Admin$")
    EYEBROW = "Application for registration · Form-I"
    STEP_SECTIONS = (
        "Step 1 · Part A — Basic Details",
        "Step 2 · Part B — Constitution and Management Details",
        "Step 3 · Part C — Operations & Infrastructure",
        "Step 4 · Part E — Jurisdiction & Fee Payment",
        "Step 5 · Part F — Certificates & Signature",
        "Step 6 · Enclosures — Uploaded Documents",
        "Step 7 · Self Declaration & Undertaking",
        "Step 8 · Authorisation & Consent",
    )
    INFO_FIELDS = ("Reg ID", "Username", "Email", "PAN", "Registered", "Last Login", "Reg. IP", "Complete")
    COMPLETION_STEPS = ("Part A — Basic Details", "Part B — Key Persons", "Part C — Operations",
                        "Part E — Fee Payment", "Part F — Certificates", "Enclosures", "Declaration",
                        "Authorisation")
    READ_ONLY_NOTICE = "This application is approved — the certificate has been issued."

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    @property
    def content(self):
        """The main content area (agency name, registration no., stage …)."""
        return self.page.locator("#adm-main")

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def header(self):
        return self.page.locator("header.avh")

    @property
    def eyebrow(self):
        return self.header.locator(".avh-eyebrow")

    @property
    def title(self):
        """The Registration ID shown as the page heading."""
        return self.header.locator("h1.avh-title")

    @property
    def registration_chip(self):
        return self.header.locator(".avh-chip[title='Registration ID']")

    @property
    def status_pill(self):
        return self.header.locator(".av-status-pill")

    def header_item(self, label: str):
        """A header fact by its bold label — 'Stage', 'District', 'Type' or 'Submitted'."""
        return self.header.locator(".avh-item").filter(has=self.page.locator(f"b:text-is('{label}')"))

    @property
    def back_to_list_link(self):
        return self.header.locator("a[href*='agency/list.php']")

    @property
    def download_zip_link(self):
        return self.header.locator("a[href*='action=download_zip']")

    @property
    def application_pdf_link(self):
        return self.header.locator("a[href*='action=generate_pdf']")

    # ── Read-only notice and decision area ────────────────────────────────────

    @property
    def read_only_notice(self):
        return self.content.locator(".ui-alert-info").filter(has_text="Read only")

    @property
    def processing_panel(self):
        return self.page.locator("#wfPanel")

    @property
    def processing_status(self):
        return self.processing_panel.locator(".ui-card-sub").first

    @property
    def decision_buttons(self):
        """Approve / clear / refuse / revert controls of the review workflow (none on a closed application)."""
        return self.page.locator("#wfActions button, #wfActions input[type='submit'], "
                                 "form[action*='agency_view'] button[name='act']")

    # ── Form-I sections ───────────────────────────────────────────────────────

    @property
    def full_application(self):
        """Under review, the Form-I steps sit in a collapsed block "Full application — approved in Desktop
        Scrutiny (read only)"; on a closed application they are shown directly."""
        return self.content.locator("details.av-full")

    @property
    def step_titles(self):
        """The eight "Step N · …" headings, wherever they sit."""
        return self.content.locator("h3").filter(has_text=re.compile(r"^\s*Step \d"))

    @property
    def section_titles(self):
        return self.content.locator(".av-section > h3")

    def section(self, title: str):
        return self.content.locator(".av-section").filter(
            has=self.page.locator(f"h3:text-is('{title}')"))

    # ── Registration Info ─────────────────────────────────────────────────────

    @property
    def info_panel(self):
        return self.section("Registration Info")

    def info_row(self, label: str):
        """A Registration Info row by its label (without the colon), e.g. 'Username'."""
        return self.info_panel.locator(f"xpath=.//div[span[1][normalize-space()='{label}:']]")

    @property
    def info_labels(self):
        return self.info_panel.locator("xpath=.//div[span][count(*)<=2]/span[1]")

    # ── Completion Status ─────────────────────────────────────────────────────

    @property
    def completion_panel(self):
        return self.section("Completion Status")

    @property
    def completion_summary(self):
        """First row of the panel — "N/8 steps complete" and the percentage."""
        return self.completion_panel.locator("xpath=./div[1]/div[1]")

    def completion_row(self, step: str):
        return self.completion_panel.locator(
            f"xpath=./div[span[1][normalize-space()='{step}']]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the application page for view id {view_id}")
    def open(self, view_id: int):
        self.navigate(f"{ADMIN_BASE}/dashboard/agency_view.php?id={view_id}")

    @allure.step("Click 'Back to list'")
    def click_back_to_list(self):
        self.back_to_list_link.click()
        self.page.wait_for_load_state("networkidle")

    @allure.step("Expand 'Full application' if it is collapsed")
    def expand_full_application(self):
        if self.full_application.count() and not self.full_application.evaluate("d => d.open"):
            self.full_application.locator("summary").click()

    @allure.step("Click 'Download documents (ZIP)' and wait for the download")
    def download_zip(self):
        """Returns the Playwright Download object."""
        with self.page.expect_download() as download_info:
            self.download_zip_link.click()
        return download_info.value

    @allure.step("Click 'Application PDF' and capture what the new tab receives")
    def open_application_pdf(self):
        """Clicks Application PDF (it opens a new tab) and returns ``(response, new_tab)`` — the Playwright Response
        for the PDF request and the tab, which the caller closes. (``page.request`` is not used: on dev it does not
        carry the officer's session and gets the login page.)"""
        with self.page.context.expect_page() as tab_info:
            with self.page.context.expect_event(
                    "response", predicate=lambda r: "action=generate_pdf" in r.url) as response_info:
                self.application_pdf_link.click()
        return response_info.value, tab_info.value

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def info_value(self, label: str) -> str:
        """The value of a Registration Info row, e.g. info_value('PAN') → 'ABCDE1234L'."""
        text = " ".join(self.info_row(label).first.text_content().split())
        return text.split(":", 1)[1].strip() if ":" in text else text

    def completion_counts(self) -> tuple[int, int, int]:
        """(steps complete, steps total, percent) from the summary row."""
        text = " ".join(self.completion_summary.text_content().split())
        steps = re.search(r"(\d+)\s*/\s*(\d+)", text)
        pct = re.search(r"(\d+)\s*%", text)
        if not steps or not pct:
            return (-1, -1, -1)
        return int(steps.group(1)), int(steps.group(2)), int(pct.group(1))

    def completion_statuses(self) -> dict[str, str]:
        """{step name: status}, e.g. {'Part A — Basic Details': 'PENDING', …}."""
        out = {}
        for row in self.completion_panel.locator("xpath=./div[span]").all():
            spans = [" ".join(s.split()) for s in row.locator("xpath=./span").all_text_contents()]
            if len(spans) >= 2:
                out[spans[0]] = spans[1]
        return out
