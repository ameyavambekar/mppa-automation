import allure

from config import ADMIN_BASE
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

ADMIN_APPLICATIONS_URL = f"{ADMIN_BASE}/agency/list.php"


class AdminApplicationsPage(BasePage):
    """Page object for the Officer Console's Applications lists (module/admin/agency/list.php, "<view> — MPPA
    Officer Console"): submitted (paid) applications by review stage.

    Header: three stage cards (``a.al-q``, ``is-on`` when active, count ``.al-q-n``) — Desktop scrutiny
    (Stage 1), Physical verification and Branch office verification (Stage 2) — and the tabs (``a.al-tab``)
    All applications, On hold — with agency, Approved, Rejected and Suspended / cancelled, each linking to
    ``?view=<view>`` (see ``VIEWS``). A stage view adds step links (``a.al-step``) by review state,
    ``&s=<step>`` (see ``REVIEW_STEPS``), and a District filter.

    Table: one row per application — Application (``.al-name`` agency, ``.al-mono`` Application ID,
    ``.al-meta`` e-mail [" · N branch office(s)"]), District, Current step (``.ui-badge``: "Under review",
    "Compliance 2 — show cause notice & hearing scheduled", "Refused", … and the stage), Compliance
    (C1 / C2), 45-day period (``td.sla``: "N of 45 days left", or "Decided <date>") and Review / View /
    Delete. The Branch office view shows Head office and Branch office(s) in your area instead. An empty
    list shows ``EMPTY`` (``td.al-empty``).
    """

    # ?view= value → stage card / tab label
    VIEWS = {"desktop": "Desktop scrutiny", "physical": "Physical verification",
             "branches": "Branch office verification", "all": "All applications",
             "on_hold": "On hold — with agency", "approved": "Approved", "rejected": "Rejected",
             "suspended": "Suspended / cancelled"}
    STAGE_VIEWS = ("desktop", "physical", "branches")
    # &s= value → step link label (stage views only)
    REVIEW_STEPS = {"review": "Under review", "agency": "Compliance — with agency", "hearing": "Show cause / hearing"}
    EMPTY = "No applications in this list."

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Header ────────────────────────────────────────────────────────────────

    def view_link(self, view: str):
        """A stage card or tab by its ``?view=`` value."""
        return self.page.locator(f"#adm-main a.al-q[href='?view={view}'], #adm-main a.al-tab[href='?view={view}']")

    def step_link(self, view: str, step: str):
        return self.page.locator(f"#adm-main a.al-step[href='?view={view}&s={step}']")

    # ── Table ─────────────────────────────────────────────────────────────────

    @property
    def rows(self):
        """Application rows (not the empty-list row)."""
        return self.page.locator("#adm-main table tbody tr:not(:has(td.al-empty))")

    @property
    def empty_row(self):
        return self.page.locator("#adm-main table tbody td.al-empty")

    def row_by_application_id(self, application_id: str):
        return self.rows.filter(has=self.page.locator(".al-mono", has_text=application_id))

    def table_data(self) -> list[dict]:
        """Every row read in one go: agency, application_id, email, district (the second column — the head
        office in the Branch office view), badge (the first ``.ui-badge``) and period (the 45-day period
        cell)."""
        return self.rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const c = r.cells;
            return {agency: t(c[0].querySelector('.al-name')), application_id: t(c[0].querySelector('.al-mono')),
                    email: t(c[0].querySelector('.al-meta')).split(' · ')[0], district: t(c[1]),
                    badge: t(r.querySelector('.ui-badge')), period: t(r.querySelector('td.sla'))};
        })""")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Applications '{view}' (step '{step}')")
    def open(self, view: str = "all", step: str = None):
        self.navigate(f"{ADMIN_APPLICATIONS_URL}?view={view}" + (f"&s={step}" if step else ""))
