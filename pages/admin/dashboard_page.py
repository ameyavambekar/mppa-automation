import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage


class AdminDashboardPage(BasePage):
    """Page object for the Admin Dashboard (post-login landing) plus the
    Audit Log and Session Management areas reachable from it.

    Sidebar navigation is delegated to the reusable ``AdminSidebar`` component
    via ``self.sidebar``. Many other selectors are scaffolds — confirm against
    the live admin portal.
    """

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Dashboard overview ────────────────────────────────────────────────────

    @property
    def dashboard_heading(self):
        return self.page.locator(
            "//div[contains(@class,'adm-page-title')]//span[contains(text(),'Dashboard Overview')]"
        )

    @property
    def admin_username(self):
        return self.page.locator(".tb-user strong")

    @property
    def role_badge(self):
        """Top-bar role badge, e.g. '👑 Super Admin' (class badge-superadmin)."""
        return self.page.locator("#adm-topbar .tb-badge")

    @property
    def sidebar_role_label(self):
        """Role label under the sidebar user card, e.g. 'Superadmin'."""
        return self.sidebar.user_role

    @property
    def logout_button(self):
        return self.sidebar.logout_link

    # ── Navigation (delegated to the sidebar component) ───────────────────────

    @property
    def audit_log_link(self):
        return self.sidebar.audit_log_link

    @property
    def session_management_link(self):
        return self.sidebar.sessions_link

    # ── Audit Log (page: /module/admin/audit/index.php) ──────────────────────
    # The audit log is a custom feed, NOT a `.stbl` table. Each entry is a
    # `.log-item` (id="row-<n>") inside the `.tb-wrap` container, with an action
    # pill (`.act-pill`), a who/what cell (`.log-user`), and detail key/value
    # pairs (`.detail-kv` → `.dk` key / `.dv` value, e.g. username / ip / role).

    @property
    def audit_log_table(self):
        """The audit log feed container."""
        return self.page.locator(".tb-wrap")

    @property
    def audit_log_rows(self):
        """All audit log entry rows."""
        return self.page.locator(".tb-wrap .log-item")

    @property
    def audit_log_first_row(self):
        """The most-recent audit log entry (top of the feed)."""
        return self.page.locator(".tb-wrap .log-item").first

    @property
    def audit_search_input(self):
        return self.page.locator("input.sinp[name='q']")

    def audit_action_chip(self, action_code: str):
        """Returns the action-type filter chip, e.g. 'ADMIN_LOGIN', 'SESSION_KILL'."""
        return self.page.locator(f"a.ach[href*='action_f={action_code}']")

    def audit_row_action(self, row):
        """The action pill within a given `.log-item` row."""
        return row.locator(".act-pill")

    def audit_row_detail_value(self, row, key: str):
        """The detail value (`.dv`) for a given key (`.dk`) within a row,
        e.g. key='username' / 'ip' / 'role'."""
        return row.locator(
            f".log-details .detail-kv:has(.dk:text-is('{key}')) .dv"
        )

    # ── Session Management (page: /module/admin/sessions/index.php) ──────────
    # The sessions page is a `.stbl` table inside `.tb-wrap`. Columns are:
    # #, Status, Agency, Username, Login IP, Login Time, Last Ping,
    # Logout/End, Duration, Reason, Action. Each row's Action cell holds a
    # POST form (hidden _action=kill_session + session_id) with a `.btn-r`
    # "🚫 Kill" button. Submitting fires a confirm('Terminate this session?')
    # dialog, so the kill action must accept that dialog.

    @property
    def session_search_input(self):
        return self.page.locator("input.sinp[name='q']")

    @property
    def kill_all_sessions_button(self):
        """The 'Kill All Active' button (fires a confirm dialog)."""
        return self.page.locator("//button[contains(@class,'btn-r') and contains(.,'Kill All')]")

    def active_session_row(self, username: str):
        """Returns the session row whose Username cell matches the given username."""
        return self.page.locator(
            "//table[contains(@class,'stbl')]//tbody//tr"
            f"[td[normalize-space()='{username}']]"
        ).first

    def kill_session_button(self, username: str):
        """Returns the '🚫 Kill' button in the given user's session row."""
        return self.active_session_row(username).locator("button.btn-r")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Audit Log")
    def open_audit_log(self):
        self.audit_log_link.click()

    @allure.step("Filter Audit Log by action: {action_code}")
    def filter_audit_by_action(self, action_code: str):
        self.audit_action_chip(action_code).click()

    @allure.step("Open Session Management")
    def open_session_management(self):
        self.session_management_link.click()

    @allure.step("Search sessions for: {query}")
    def search_sessions(self, query: str):
        self.session_search_input.fill(query)
        self.session_search_input.press("Enter")
        self.wait_for_load()

    @allure.step("Kill active session for: {username}")
    def kill_session_for(self, username: str) -> str:
        """Clicks the row's Kill button and accepts the
        confirm('Terminate this session?') dialog. Returns the dialog message."""
        return self.click_and_handle_alert(
            self.kill_session_button(username), action="accept"
        )

    @allure.step("Logout")
    def logout(self):
        self.logout_button.click()

    def get_url(self) -> str:
        return self.page.url
