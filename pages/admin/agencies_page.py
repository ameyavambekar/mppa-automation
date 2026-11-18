import re

import allure

from pages.admin.applications_page import AdminApplicationsPage


class AdminAgenciesPage(AdminApplicationsPage):
    """Agencies management (KAN-25) on the Officer Console's Applications list
    (/module/admin/agency/list.php, "All applications — MPPA Officer Console").

    The old "All Agencies" list (``table.stbl`` / ``#ag-tbody``, status tabs ``?status=``, live search and the
    Change Status modal) was replaced by the Applications list; this page object adds what the KAN-25 tests
    read on top of ``AdminApplicationsPage`` (shared with the review-loop and District breakup tests):

    * heading "Applications" (``.al-title``), three stage cards and five tabs (labels in ``STAGE_LABELS`` /
      ``TAB_LABELS``, read on dev 17-Nov-2026 — the On hold tab now reads "Revert for compliance — with agency");
    * the search form: District select and ``q`` ("Search name, registration ID, PAN, e-mail"), submitted with
      the Search button — the list is filtered on the server, not as you type;
    * one row per submitted (paid) application, keyed here by its 13-digit Application ID: agency
      (``.al-name``), e-mail (``.al-meta``), district, current step badge, Review / View link and a Delete
      button (``deleteAgency``) — the tests never click Delete.

    Applications still being filled in are not listed here; they are under Registrations in progress.
    """

    TITLE = "Applications"
    PAGE_TITLE = re.compile(r"^.+ — MPPA Officer Console$")
    STAGE_LABELS = {"desktop": "Desktop scrutiny", "physical": "Physical verification",
                    "branches": "Branch office verification"}
    TAB_LABELS = {v: AdminApplicationsPage.VIEWS[v] for v in ("all", "on_hold", "approved", "rejected", "suspended")}
    COLUMNS = ("Application", "District", "Current step", "Compliance", "45-day period", "Action")
    SEARCH_PLACEHOLDER = "Search name, registration ID, PAN, e-mail"

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("#adm-main .al-title")

    @property
    def stage_cards(self):
        return self.page.locator("#adm-main a.al-q")

    @property
    def tabs(self):
        return self.page.locator("#adm-main a.al-tab")

    @property
    def active_tab(self):
        return self.page.locator("#adm-main a.al-tab.is-on")

    # ── Search ────────────────────────────────────────────────────────────────

    @property
    def search_input(self):
        return self.page.locator("#adm-main input[name='q']")

    @property
    def search_button(self):
        return self.page.locator("#adm-main form:has(input[name='q']) button[type='submit']")

    # ── Table ─────────────────────────────────────────────────────────────────

    @property
    def table_headers(self):
        return self.page.locator("#adm-main table thead th")

    def row(self, application_id: str):
        return self.row_by_application_id(application_id)

    def agency_name_cell(self, application_id: str):
        return self.row(application_id).locator(".al-name")

    def email_cell(self, application_id: str):
        return self.row(application_id).locator(".al-meta").first

    def district_cell(self, application_id: str):
        return self.row(application_id).locator("td").nth(1)

    def current_step_badge(self, application_id: str):
        return self.row(application_id).locator(".ui-badge").first

    def review_link(self, application_id: str):
        """"Review" (or "View") — opens the application's page (agency_view.php?id=N)."""
        return self.row(application_id).locator("a[href*='agency_view.php']")

    def delete_button(self, application_id: str):
        """Deletes the agency (``deleteAgency``) — irreversible; located only to check it exists."""
        return self.row(application_id).locator("button[aria-label='Delete']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Search the Applications list for '{query}'")
    def search(self, query: str):
        """Types into the search box and clicks Search (the list reloads filtered on the server)."""
        self.search_input.fill(query)
        self.search_button.click()
        self.page.wait_for_load_state("networkidle")

    @allure.step("Clear the search and click Search")
    def clear_search(self):
        self.search(query="")

    @allure.step("Click Review / View for application {application_id}")
    def click_review(self, application_id: str):
        self.review_link(application_id).click()
        self.page.wait_for_load_state("networkidle")

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def application_ids(self) -> list[str]:
        """Application IDs of the listed rows, in page order."""
        return [r["application_id"] for r in self.table_data()]

    def ids_in_view(self, view: str) -> list[str]:
        """Opens a stage card or tab and returns its Application IDs."""
        self.open(view)
        self.page.wait_for_load_state("networkidle")
        return self.application_ids()
