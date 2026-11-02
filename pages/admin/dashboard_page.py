import allure

from config import ADMIN_BASE
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

ADMIN_DASHBOARD_URL = f"{ADMIN_BASE}/index.php"


class AdminDashboardPage(BasePage):
    """Page object for the Admin Dashboard (module/admin/index.php, "Dashboard — MPPA Officer
    Console") — where admin login lands — plus the Audit Log and Session Management helpers the
    admin login tests reach from it.

    Top bar (``#adm-topbar``): role (``.tb-role``, e.g. "Super Administrator"), "MPPA Officer
    Console", area (``.tb-area``, "· Maharashtra"), the notifications bell (``#tbBell``, unread
    count ``#tbBellN``, dropdown ``#tbDrop``), the officer's name (``.tb-user``) and Logout.
    Sidebar navigation is delegated to the reusable ``AdminSidebar`` component (``self.sidebar``).

    Main area (``#adm-main``):
      * header — crumb "<role> · <dd Mon yyyy>", title "<area> — Dashboard", a Division filter
        (``select[name=division]``; choosing a division adds a District filter) and "Applications";
      * an error alert when the dashboard data cannot be loaded;
      * six KPI cards (``a.kpi``), each linking to ``?metric=<key>#kpiDetail``;
      * "Needs your attention" (unread notifications for the officer's area);
      * "Applications over the last 12 months" (trend chart) and "Status mix" (donut + counts);
      * "Work queue" (pending applications table) and "Performance" (stats + funnel).
    """

    # ── Texts ─────────────────────────────────────────────────────────────────

    CONSOLE_TITLE = "MPPA Officer Console"
    PAGE_TITLE = "Dashboard — MPPA Officer Console"
    SUPER_ADMIN_ROLE = "Super Administrator"
    STATE_AREA = "Maharashtra"
    STATE_DIVISION_LABEL = "All divisions (State)"
    ALL_DISTRICTS_LABEL = "All districts"
    APPLICATIONS_LABEL = "Applications"
    # "The dashboard could not be loaded (Ref <id>). Please make sure the latest database updates
    # have been imported." — shown when the dashboard's data query fails (KPIs then read 0)
    LOAD_ERROR_PREFIX = "The dashboard could not be loaded"

    # KPI cards: ?metric=<key> → label
    KPIS = {
        "total": "Total applications",
        "pending": "Pending decision",
        "approved": "Approved",
        "refused": "Refused",
        "overdue": "Beyond 45-day SLA",
        "appeals": "Appeals pending",
    }
    KPI_MORE = "View list ›"

    ATTENTION_TITLE = "Needs your attention"
    ALL_NOTIFICATIONS_LABEL = "All notifications"
    TREND_TITLE = "Applications over the last 12 months"
    TREND_LEGEND = ("Submitted", "Approved")
    STATUS_MIX_TITLE = "Status mix"
    STATUS_MIX = ("Desktop scrutiny", "Physical verification", "Approved", "Refused", "Suspended")
    WORK_QUEUE_TITLE = "Work queue"
    WORK_QUEUE_HEADERS = ("Registration ID", "Agency", "District", "Stage", "Status", "SLA", "")
    NO_PENDING = "No pending applications."
    PERFORMANCE_TITLE = "Performance"
    PERFORMANCE_STATS = ("Average time to decide", "Decided applications", "Open compliance cases",
                         "Registrations in progress")
    FUNNEL = ("Submitted", "Cleared desktop", "Approved")

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Top bar ───────────────────────────────────────────────────────────────

    @property
    def role_badge(self):
        """Top-bar role, e.g. 'Super Administrator'. Visible on every admin page once logged in."""
        return self.page.locator("#adm-topbar .tb-role")

    @property
    def console_title(self):
        return self.page.locator("#adm-topbar h1")

    @property
    def area_label(self):
        """'· Maharashtra' (the officer's area)."""
        return self.page.locator("#adm-topbar .tb-area")

    @property
    def admin_username(self):
        """The officer's full name in the top bar."""
        return self.page.locator("#adm-topbar .tb-user")

    @property
    def topbar_logout_link(self):
        return self.page.locator("#adm-topbar a[href$='/auth/logout.php']")

    @property
    def notifications_bell(self):
        """Bell button; its aria-label is 'Notifications (<n> unread)'."""
        return self.page.locator("#tbBell")

    @property
    def notifications_bell_count(self):
        return self.page.locator("#tbBellN")

    @property
    def notifications_dropdown(self):
        return self.page.locator("#tbDrop")

    @property
    def notifications_dropdown_list(self):
        """Filled when the bell is opened ('Loading…' until then)."""
        return self.page.locator("#tbDropList")

    @property
    def mark_all_notifications_read_button(self):
        return self.page.locator("#tbReadAll")

    @property
    def view_all_notifications_link(self):
        return self.page.locator("#tbDrop a.tb-drop-f")

    @property
    def sidebar_role_label(self):
        """Role under the sidebar's user card, e.g. 'Super Administrator'."""
        return self.sidebar.user_role

    @property
    def logout_button(self):
        """Sidebar 'Log out' (the top bar has its own ``topbar_logout_link``)."""
        return self.sidebar.logout_link

    # ── Dashboard header ──────────────────────────────────────────────────────

    @property
    def crumb(self):
        """'<role> · <dd Mon yyyy>' ('Maharashtra › <role> · <date>' once a division is chosen)."""
        return self.page.locator("#adm-main .db-crumb")

    @property
    def dashboard_heading(self):
        """'Maharashtra State — Dashboard', or '<division> — Dashboard'."""
        return self.page.locator("#adm-main h2.db-title")

    @property
    def division_select(self):
        """Options: 'All divisions (State)' and the six divisions; choosing one reloads the page."""
        return self.page.locator(".db-switch select[name='division']")

    @property
    def district_select(self):
        """Only shown once a division is chosen: 'All districts' and that division's districts."""
        return self.page.locator(".db-switch select[name='district']")

    @property
    def applications_button(self):
        return self.page.locator(".db-switch").get_by_role("link", name=self.APPLICATIONS_LABEL)

    @property
    def load_error(self):
        return self.page.locator("#adm-main .ui-alert-error")

    # ── KPI cards ─────────────────────────────────────────────────────────────

    @property
    def kpi_cards(self):
        return self.page.locator("#adm-main .kpis a.kpi")

    def kpi_card(self, metric: str):
        """metric: a key of ``KPIS`` (e.g. 'pending')."""
        return self.page.locator(f"#adm-main .kpis a.kpi[href*='metric={metric}#']")

    def kpi_label(self, metric: str):
        return self.kpi_card(metric).locator(".kpi-lbl")

    def kpi_value(self, metric: str):
        return self.kpi_card(metric).locator(".kpi-val")

    def kpi_sub(self, metric: str):
        """E.g. 'Submitted & paid', '<n> desktop · <n> physical', '<n>% of applications'."""
        return self.kpi_card(metric).locator(".kpi-sub")

    @property
    def kpi_detail(self):
        """Records behind the chosen KPI (``?metric=<key>#kpiDetail``)."""
        return self.page.locator("#kpiDetail")

    # ── Cards ─────────────────────────────────────────────────────────────────

    def card(self, title: str):
        return self.page.locator("#adm-main .ui-card").filter(
            has=self.page.locator(".ui-card-title", has_text=title))

    def card_subtitle(self, title: str):
        return self.card(title).locator(".ui-card-sub")

    @property
    def attention_items(self):
        """One link per unread notification: bold '<title>: <agency> (<Registration ID>)', then
        '<message> · <dd Mon, hh:mm AM/PM>'; opens dashboard/agency_view.php?id=<n>."""
        return self.card(self.ATTENTION_TITLE).locator(":scope > div:not(.ui-card-head) > a")

    def attention_item(self, text: str):
        return self.attention_items.filter(has_text=text)

    @property
    def all_notifications_button(self):
        return self.card(self.ATTENTION_TITLE).get_by_role("link", name=self.ALL_NOTIFICATIONS_LABEL)

    @property
    def trend_chart(self):
        return self.card(self.TREND_TITLE).locator("svg[aria-label='Trend chart']")

    @property
    def status_mix_chart(self):
        """Donut; its centre reads '<n> applications'."""
        return self.card(self.STATUS_MIX_TITLE).locator("svg[aria-label='Status mix']")

    def status_mix_count(self, label: str):
        """label: one of ``STATUS_MIX``."""
        return self.card(self.STATUS_MIX_TITLE).locator(".donut-list > div").filter(
            has=self.page.locator("span", has_text=label)).locator("b")

    @property
    def work_queue_table(self):
        return self.card(self.WORK_QUEUE_TITLE).locator("table.ui-table")

    @property
    def work_queue_headers(self):
        return self.work_queue_table.locator("thead th")

    @property
    def work_queue_rows(self):
        """Pending applications, most urgent first; a single 'No pending applications.' row when empty."""
        return self.work_queue_table.locator("tbody tr")

    def performance_stat(self, label: str):
        """label: one of ``PERFORMANCE_STATS``; '—' when nothing has been decided yet."""
        return self.card(self.PERFORMANCE_TITLE).locator(".perf-stats > div").filter(
            has=self.page.locator("small", has_text=label)).locator("b")

    def funnel_count(self, label: str):
        """label: one of ``FUNNEL``."""
        return self.card(self.PERFORMANCE_TITLE).locator(".fn-row").filter(
            has=self.page.locator("span", has_text=label)).locator(":scope > b")

    # ── Audit Log (page: /module/admin/audit/index.php) ──────────────────────
    # The audit log is a custom feed, NOT a `.stbl` table. Each entry is a
    # `.log-item` inside the `.tb-wrap` container, with an action pill
    # (`.act-pill`), a who/what cell (`.log-user`), and detail key/value pairs
    # (`.detail-kv` → `.dk` key / `.dv` value, e.g. username / ip / role).
    # The action type is chosen in a dropdown (#actionSelect, name action_f)
    # that submits the filter form as soon as it changes.

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

    @property
    def audit_action_select(self):
        """Action-type dropdown; option values are action codes, e.g. 'ADMIN_LOGIN', 'SESSION_KILL'
        (only codes already in the log are listed)."""
        return self.page.locator("#actionSelect")

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
    # Logout / End, Duration, Reason, Action. Each row's Action cell holds a
    # POST form (hidden _action=kill_session + session_id) with a `.btn-r`
    # "Kill" button. Submitting fires a confirm('Terminate this session?')
    # dialog, so the kill action must accept that dialog.

    @property
    def session_search_input(self):
        return self.page.locator("input.sinp[name='q']")

    @property
    def kill_all_sessions_button(self):
        """The 'Kill All Active (<n>)' button (fires a confirm dialog)."""
        return self.page.locator("//button[contains(@class,'btn-r') and contains(.,'Kill All')]")

    def active_session_row(self, username: str):
        """Returns the session row whose Username cell matches the given username."""
        return self.page.locator(
            "//table[contains(@class,'stbl')]//tbody//tr"
            f"[td[normalize-space()='{username}']]"
        ).first

    def kill_session_button(self, username: str):
        """Returns the 'Kill' button in the given user's session row."""
        return self.active_session_row(username).locator("button.btn-r")

    # ── Navigation (delegated to the sidebar component) ───────────────────────

    @property
    def audit_log_link(self):
        return self.sidebar.audit_log_link

    @property
    def session_management_link(self):
        return self.sidebar.sessions_link

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Reload the current page")
    def reload(self):
        self.page.reload()

    @allure.step("Leave the console idle until it logs out by itself")
    def wait_for_idle_logout(self, timeout_seconds: int):
        """Does nothing on the page while it polls the session; returns once the console has sent
        the browser to the Admin Login page with ?reason=idle_timeout."""
        self.page.wait_for_url(lambda url: "reason=idle_timeout" in url, timeout=timeout_seconds * 1000)

    @allure.step("Open the Admin Dashboard")
    def open(self):
        """Navigates to the dashboard (requires a logged-in admin session)."""
        self.navigate(ADMIN_DASHBOARD_URL)

    @allure.step("Choose division: {division}")
    def select_division(self, division: str):
        """division: an option label, e.g. 'Pune Division' or 'All divisions (State)'; the page reloads."""
        with self.page.expect_navigation():
            self.division_select.select_option(label=division)

    @allure.step("Choose district: {district}")
    def select_district(self, district: str):
        """district: an option label of the chosen division, e.g. 'Pune' or 'All districts'."""
        with self.page.expect_navigation():
            self.district_select.select_option(label=district)

    @allure.step("Open KPI '{metric}'")
    def open_kpi(self, metric: str):
        self.kpi_card(metric).click()
        self.wait_for_load()

    @allure.step("Open the notifications bell")
    def open_notifications_bell(self):
        self.notifications_bell.click()

    @allure.step("Open Audit Log")
    def open_audit_log(self):
        self.audit_log_link.click()

    @allure.step("Filter Audit Log by action: {action_code}")
    def filter_audit_by_action(self, action_code: str):
        """Chooses the action in the dropdown, which reloads the feed filtered to it."""
        with self.page.expect_navigation():
            self.audit_action_select.select_option(value=action_code)

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
