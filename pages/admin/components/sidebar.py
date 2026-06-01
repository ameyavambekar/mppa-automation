import allure

from pages.base_page import BasePage


class AdminSidebar(BasePage):
    """Reusable page-object component for the admin portal left sidebar (#adm-sb).

    The sidebar appears on every authenticated admin page (dashboard, audit
    log, sessions, agencies, …). Wrapping it once means each admin page object
    can expose ``self.sidebar`` instead of re-declaring the same nav locators.

    Conventions match the project's page objects: locators are ``@property``
    methods, actions are ``@allure.step`` decorated, and assertions stay in the
    tests (use ``expect()`` against these locators).

    Usage
    -----
        sidebar = AdminSidebar(page)              # or admin_dashboard_page.sidebar
        sidebar.go_to_audit_log()
        expect(sidebar.user_role).to_have_text("Superadmin")
        expect(sidebar.active_item).to_contain_text("Audit Log")
        assert sidebar.badge_count("Sessions") == "306"
    """

    ROOT = "#adm-sb"

    # ── Root & user card ──────────────────────────────────────────────────────

    @property
    def root(self):
        return self.page.locator(self.ROOT)

    @property
    def user_avatar(self):
        return self.page.locator(f"{self.ROOT} .sb-user .av")

    @property
    def user_name(self):
        return self.page.locator(f"{self.ROOT} .sb-user .nm")

    @property
    def user_role(self):
        """Role label under the user card, e.g. 'Superadmin'."""
        return self.page.locator(f"{self.ROOT} .sb-user .rl")

    # ── Generic accessors ─────────────────────────────────────────────────────

    @property
    def nav_items(self):
        """All nav-item links in the sidebar."""
        return self.page.locator(f"{self.ROOT} a.ni")

    @property
    def active_item(self):
        """The currently highlighted nav item (a.ni.active)."""
        return self.page.locator(f"{self.ROOT} a.ni.active")

    def section_header(self, title: str):
        """A section header (.nsec) by its title, e.g. 'Agency Data', 'Account'."""
        return self.page.locator(f"{self.ROOT} p.nsec", has_text=title)

    def nav_link(self, label: str):
        """A nav item by its visible label, e.g. 'Audit Log', 'Sessions'."""
        return self.page.locator(f"{self.ROOT} a.ni", has_text=label)

    def _link(self, href_attr_selector: str):
        """A nav item by an href attribute-selector fragment, e.g. "href$='/x.php'"."""
        return self.page.locator(f"{self.ROOT} a.ni[{href_attr_selector}]")

    # ── Named nav items (href-based — stable against label/emoji changes) ─────

    @property
    def overview_link(self):
        return self._link("href$='/admin/index.php'")

    @property
    def agencies_link(self):
        return self._link("href$='/agency/list.php'")

    @property
    def approved_link(self):
        return self._link("href$='/agency/approve.php'")

    @property
    def appeals_link(self):
        return self._link("href$='/appeals/index.php'")

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
        return self._link("href$='/admins/index.php'")

    @property
    def permissions_link(self):
        return self._link("href$='/admins/permissions.php'")

    @property
    def audit_log_link(self):
        return self._link("href$='/audit/index.php'")

    @property
    def logout_link(self):
        return self._link("href$='/auth/logout.php'")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Sidebar → navigate to '{label}'")
    def navigate_to(self, label: str):
        self.nav_link(label).click()

    @allure.step("Sidebar → Overview")
    def go_to_overview(self):
        self.overview_link.click()

    @allure.step("Sidebar → Agencies")
    def go_to_agencies(self):
        self.agencies_link.click()

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

    @allure.step("Sidebar → Admin Users")
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
