import allure

from pages.base_page import BasePage


class AdminSidebar(BasePage):
    """Reusable page-object component for the admin portal left sidebar (#adm-sb).

    The sidebar appears on every authenticated admin page (dashboard, audit
    log, sessions, agencies, …). Wrapping it once means each admin page object
    can expose ``self.sidebar`` instead of re-declaring the same nav locators.

    Since the "MPPA Officer Console" redesign it is ``nav#adm-sb`` ("Main menu")
    with sections Main, Applications, Registry, Enforcement, Reports and
    Administration. Items are ``a.ni`` links (icon, ``.ni-lbl`` label, optional
    ``.bc`` count); "Applications" is a collapsible ``details.ni-group`` whose
    ``summary.ni`` holds the link and whose ``a.ni-subitem`` children filter the
    list by stage (``?view=<key>``, see ``APPLICATION_VIEWS``). The officer's
    card (``.sb-foot``: avatar, name, role) and the "Log out" icon link
    (``a.sb-out``) sit at the bottom.

    Conventions match the project's page objects: locators are ``@property``
    methods, actions are ``@allure.step`` decorated, and assertions stay in the
    tests (use ``expect()`` against these locators).

    Usage
    -----
        sidebar = AdminSidebar(page)              # or admin_dashboard_page.sidebar
        sidebar.go_to_audit_log()
        expect(sidebar.user_role).to_have_text("Super Administrator")
        expect(sidebar.active_item).to_contain_text("Audit log")
        assert sidebar.badge_count("Notifications") == "9"
    """

    ROOT = "#adm-sb"

    SECTIONS = ("Main", "Applications", "Registry", "Enforcement", "Reports", "Administration")
    # Applications sub-items: ?view=<key> → label
    APPLICATION_VIEWS = {
        "all": "All applications",
        "desktop": "Desktop scrutiny",
        "physical": "Physical verification",
        "branches": "Branch offices",
        "on_hold": "On hold",
        "approved": "Approved",
        "rejected": "Rejected",
        "suspended": "Suspended",
    }

    # ── Root & user card ──────────────────────────────────────────────────────

    @property
    def root(self):
        return self.page.locator(self.ROOT)

    @property
    def user_avatar(self):
        """First letter of the officer's name."""
        return self.page.locator(f"{self.ROOT} .sb-foot .av")

    @property
    def user_name(self):
        return self.page.locator(f"{self.ROOT} .sb-foot .nm")

    @property
    def user_role(self):
        """Role label under the user card, e.g. 'Super Administrator'."""
        return self.page.locator(f"{self.ROOT} .sb-foot .rl")

    # ── Generic accessors ─────────────────────────────────────────────────────

    @property
    def nav_items(self):
        """All top-level nav items in the sidebar (links, plus the Applications group header)."""
        return self.page.locator(f"{self.ROOT} a.ni, {self.ROOT} summary.ni")

    @property
    def active_item(self):
        """The currently highlighted nav item (a.ni.active)."""
        return self.page.locator(f"{self.ROOT} a.ni.active")

    def section_header(self, title: str):
        """A section header (.nsec) by its title, e.g. 'Agency Data', 'Account'."""
        return self.page.locator(f"{self.ROOT} p.nsec", has_text=title)

    def nav_link(self, label: str):
        """A top-level nav item by its visible label, e.g. 'Audit log', 'Active sessions'."""
        return self.nav_items.filter(has=self.page.locator(".ni-lbl", has_text=label))

    def _link(self, href_attr_selector: str):
        """A nav item by an href attribute-selector fragment, e.g. "href$='/x.php'"."""
        return self.page.locator(f"{self.ROOT} a.ni[{href_attr_selector}]")

    # ── Named nav items (href-based — stable against label/emoji changes) ─────

    @property
    def overview_link(self):
        """'Dashboard'."""
        return self._link("href$='/admin/index.php'")

    @property
    def notifications_link(self):
        return self._link("href$='/notifications/index.php'")

    @property
    def applications_group(self):
        """The collapsible Applications group (``details`` — has the ``open`` attribute while expanded)."""
        return self.page.locator(f"{self.ROOT} details.ni-group")

    @property
    def agencies_link(self):
        """'Applications' — the group header's link (all applications)."""
        return self.page.locator(f"{self.ROOT} summary.ni a.ni-link[href*='/agency/list.php']")

    def application_view_link(self, view: str):
        """Applications sub-item; view: a key of ``APPLICATION_VIEWS``."""
        return self.page.locator(f"{self.ROOT} a.ni-subitem[href$='list.php?view={view}']")

    @property
    def registrations_in_progress_link(self):
        return self._link("href$='/drafts/index.php'")

    @property
    def approved_link(self):
        return self._link("href$='/agency/approve.php'")

    @property
    def renewals_link(self):
        return self._link("href$='/licenses/renewals.php'")

    @property
    def compliance_link(self):
        return self._link("href$='/compliance/index.php'")

    @property
    def appeals_link(self):
        return self._link("href$='/appeals/index.php'")

    @property
    def job_seekers_link(self):
        """'Job seekers (Form-V)'."""
        return self._link("href$='/job_seekers/index.php'")

    @property
    def district_breakup_link(self):
        return self._link("href$='/reports/district_breakup.php'")

    @property
    def officers_link(self):
        """'Officers & access'."""
        return self._link("href$='/users/index.php'")

    @property
    def notices_link(self):
        return self._link("href*='/notices/'")

    @property
    def sessions_link(self):
        return self._link("href$='/sessions/index.php'")

    @property
    def licenses_link(self):
        return self._link("href$='/licenses/licenses.php'")

    @property
    def admin_users_link(self):
        """'Legacy admin tools' (admins/index.php — the old admin user management)."""
        return self._link("href$='/admins/index.php'")

    @property
    def permissions_link(self):
        """No longer in the sidebar since the redesign; admins/permissions.php is opened directly."""
        return self._link("href$='/admins/permissions.php'")

    @property
    def audit_log_link(self):
        return self._link("href$='/audit/index.php'")

    @property
    def logout_link(self):
        """'Log out' icon link on the officer's card."""
        return self.page.locator(f"{self.ROOT} a.sb-out")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Sidebar → navigate to '{label}'")
    def navigate_to(self, label: str):
        self.nav_link(label).click()

    @allure.step("Sidebar → Overview")
    def go_to_overview(self):
        self.overview_link.click()

    @allure.step("Sidebar → Notifications")
    def go_to_notifications(self):
        self.notifications_link.click()

    @allure.step("Sidebar → Applications")
    def go_to_agencies(self):
        self.agencies_link.click()

    @allure.step("Sidebar → Applications → '{view}'")
    def go_to_application_view(self, view: str):
        """Expands the Applications group if needed, then opens the sub-item."""
        if self.applications_group.get_attribute("open") is None:
            self.applications_group.locator("summary .ni-chev").click()
        self.application_view_link(view).click()

    @allure.step("Sidebar → Registrations in progress")
    def go_to_registrations_in_progress(self):
        self.registrations_in_progress_link.click()

    @allure.step("Sidebar → Approved")
    def go_to_approved(self):
        self.approved_link.click()

    @allure.step("Sidebar → Appeals")
    def go_to_appeals(self):
        self.appeals_link.click()

    @allure.step("Sidebar → Notices")
    def go_to_notices(self):
        self.notices_link.click()

    @allure.step("Sidebar → Sessions")
    def go_to_sessions(self):
        self.sessions_link.click()

    @allure.step("Sidebar → Licenses")
    def go_to_licenses(self):
        self.licenses_link.click()

    @allure.step("Sidebar → Officers & access")
    def go_to_officers(self):
        self.officers_link.click()

    @allure.step("Sidebar → Legacy admin tools")
    def go_to_admin_users(self):
        self.admin_users_link.click()

    @allure.step("Sidebar → Permissions")
    def go_to_permissions(self):
        self.permissions_link.click()

    @allure.step("Sidebar → Audit Log")
    def go_to_audit_log(self):
        self.audit_log_link.click()

    @allure.step("Sidebar → Logout")
    def logout(self):
        self.logout_link.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def badge_count(self, label: str) -> str:
        """Returns the badge count text (.bc) for a nav item, or '' if none."""
        badge = self.nav_link(label).locator(".bc")
        return badge.first.text_content().strip() if badge.count() else ""

    def is_item_active(self, label: str) -> bool:
        """Whether the nav item with the given label is the active one."""
        classes = self.nav_link(label).first.get_attribute("class") or ""
        return "active" in classes.split()
