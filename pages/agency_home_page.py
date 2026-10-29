import allure

from config import MODULE_ROOT
from pages.base_page import BasePage

AGENCY_HOME_URL = f"{MODULE_ROOT}/home.php"


class AgencyHomePage(BasePage):
    """Page object for the agency Home page (module/home.php) — where login lands once the
    application is submitted (paid). Not the old auth/home.php (``pages/home_page.py``), which
    is gone since the portal redesign.

    A welcome block (``.hd-welcome``: agency name, Application ID, status badge, registration
    date), a next-step banner (``.hd-next``), the "Application progress" card (stage tracker
    ``.ui-steps .st`` + timeline ``.ui-timeline li``) and the Notifications card (``#agNotes``,
    "Mark all read" ``#agNotesRead``). The side column holds three ``.hd-tile`` links, the
    Notice board (``.notice-item``), Quick links (``.hd-links``) and "Need help?".
    """

    EYEBROW = "Agency dashboard"
    UNDER_REVIEW = "Under review"
    VIEW_SUBMITTED_LABEL = "View Submitted Application"
    VIEW_MY_APPLICATION_LABEL = "View my application"
    STAGE_1_HEADING = "Your application is under review — Stage 1 — Desktop Scrutiny"
    STAGE_1_TEXT = "No action is needed from you now. A decision is due within 45 day(s)."
    PROGRESS_TITLE = "Application progress"
    STAGE_1_PROGRESS = "Stage 1 — Desktop Scrutiny · Under review"
    DECISION_BADGE = "Decision expected within 45 days"
    STAGES = ("Submitted", "Desktop scrutiny", "Physical verification", "Certificate")
    SUBMITTED_EVENT = "Application submitted"
    SUBMITTED_EVENT_NOTE = "Application submitted — 45-day SLA started."
    NOTIFICATIONS_TITLE = "Notifications"
    MARK_ALL_READ_LABEL = "Mark all read"
    SUBMITTED_NOTIFICATION = "Your application has been received and submitted to the Registering Authority"
    OPEN_LABEL = "Open"
    NOTICE_BOARD_TITLE = "Notice board"
    NOTICE_LIMIT = 5
    NOTICE_TEXT_LIMIT = 100
    NOTICE_BADGES = ("NEW", "ALERT", "INFO")
    VIEW_ALL_NOTICES_LABEL = "View all notices →"
    QUICK_LINKS_TITLE = "Quick links"
    FOOTER_LINKS = ("Privacy Policy", "Terms of Use", "Accessibility Statement")
    FOOTER_TEXTS = ("Placement Agency Regulation Portal", "Skills, Employment, Entrepreneurship and Innovation Department",
                    "Government of Maharashtra", "Helpline: 1800-XXX-XXXX", "Email: support@placementportal.gov.in",
                    "© 2026 Placement Agency Regulation Portal | Government System")

    # Page each link opens (path from the module root)
    VIEW_APPLICATION_PATH = "agency/forms/view_application.php"
    TILES = {"My application": VIEW_APPLICATION_PATH,
             "Corrections": "agency/forms/corrections.php",
             "Helpdesk": "contact.php"}
    QUICK_LINKS = ("Document checklist", "User manual (PDF)", "Frequently asked questions", "Contact helpdesk")
    NAV_LINKS = {"About Portal": "about.php",
                 "Downloads": "agency/forms/download.php",
                 "Notices": "notices.php",
                 "Contact Us": "contact.php",
                 "Home": "home.php"}
    # Unread notifications are drawn on this background (inline style; there is no class)
    UNREAD_BACKGROUND = "#f5f8ff"

    @staticmethod
    def url_of(path: str) -> str:
        return f"{MODULE_ROOT}/{path}"

    # ── Top bar ───────────────────────────────────────────────────────────────

    @property
    def user_text(self):
        """'<username> (<Application ID>)' (desktop top bar)."""
        return self.page.locator(".nav-right .nav-user-text")

    def nav_link(self, label: str):
        return self.page.locator(".nav-links a.nav-link", has_text=label)

    @property
    def logout_link(self):
        return self.page.locator(".nav-right").get_by_role("link", name="Logout")

    @property
    def login_link(self):
        """'Login' in the top bar — shown instead of the user and Logout once logged out, when home.php
        is the public landing page."""
        return self.page.locator(".nav-right").get_by_role("link", name="Login", exact=True)

    @property
    def welcome_block(self):
        return self.page.locator(".hd-welcome")

    # ── Welcome block ─────────────────────────────────────────────────────────

    @property
    def eyebrow(self):
        return self.page.locator(".hd-welcome .hd-eyebrow")

    @property
    def agency_name(self):
        return self.page.locator(".hd-welcome .hd-name")

    @property
    def application_id(self):
        return self.page.locator(".hd-welcome .hd-meta .hd-mono")

    @property
    def status_badge(self):
        return self.page.locator(".hd-welcome .hd-meta .ui-badge")

    @property
    def registered(self):
        """'Registered<dd Mon yyyy>' — the label is a <b> run straight into the date."""
        return self.page.locator(".hd-welcome .hd-meta span:has(b)")

    @property
    def view_submitted_button(self):
        return self.page.locator(".hd-welcome").get_by_role("link", name=self.VIEW_SUBMITTED_LABEL)

    # ── Next-step banner ──────────────────────────────────────────────────────

    @property
    def next_step_heading(self):
        return self.page.locator(".hd-next h3")

    @property
    def next_step_text(self):
        return self.page.locator(".hd-next p")

    @property
    def next_step_button(self):
        return self.page.locator(".hd-next").get_by_role("link", name=self.VIEW_MY_APPLICATION_LABEL)

    # ── Application progress ──────────────────────────────────────────────────

    @property
    def progress_card(self):
        return self.page.locator(".ui-card").filter(
            has=self.page.locator(".ui-card-title", has_text=self.PROGRESS_TITLE))

    @property
    def progress_subtitle(self):
        return self.progress_card.locator(".ui-card-sub")

    @property
    def progress_badge(self):
        return self.progress_card.locator(".ui-card-head .ui-badge")

    @property
    def stages(self):
        """Stage tracker items; class ``is-done`` (✓) or ``is-current``, else not reached."""
        return self.progress_card.locator(".ui-steps .st")

    def stage(self, label: str):
        return self.stages.filter(has_text=label)

    @property
    def timeline_items(self):
        return self.progress_card.locator(".ui-timeline li")

    def timeline_item(self, title: str):
        return self.timeline_items.filter(has=self.page.locator(".t-title", has_text=title))

    def timeline_time(self, title: str):
        """'<dd Mon yyyy, hh:mm AM/PM>'."""
        return self.timeline_item(title).locator(".t-meta")

    def timeline_note(self, title: str):
        return self.timeline_item(title).locator(".t-body")

    # ── Notifications ─────────────────────────────────────────────────────────

    @property
    def notifications_card(self):
        return self.page.locator("#agNotes")

    @property
    def notifications_subtitle(self):
        """'<n> new' while any notification is unread."""
        return self.notifications_card.locator(".ui-card-sub")

    @property
    def mark_all_read_button(self):
        return self.page.locator("#agNotesRead")

    _NOTIFICATION_ROWS = "#agNotes > div:not(.ui-card-head) > div"

    @property
    def notifications(self):
        """One row per notification: title, message, '<date-time> · Open'."""
        return self.page.locator(self._NOTIFICATION_ROWS)

    @property
    def unread_notifications(self):
        return self.page.locator(f"{self._NOTIFICATION_ROWS}[style*='{self.UNREAD_BACKGROUND}']")

    def notification(self, title: str):
        return self.notifications.filter(has_text=title)

    def _notification_part(self, title: str, index: int):
        return self.notification(title).locator(":scope > div > div").nth(index)

    def notification_title(self, title: str):
        return self._notification_part(title, 0)

    def notification_message(self, title: str):
        return self._notification_part(title, 1)

    def notification_time(self, title: str):
        """'<dd Mon yyyy, hh:mm AM/PM> · Open'."""
        return self._notification_part(title, 2)

    def notification_open_link(self, title: str):
        return self.notification(title).get_by_role("link", name=self.OPEN_LABEL)

    # ── Side column ───────────────────────────────────────────────────────────

    @property
    def tiles(self):
        return self.page.locator(".hd-tiles a.hd-tile")

    def tile(self, label: str):
        return self.tiles.filter(has_text=label)

    def side_card(self, title: str):
        return self.page.locator(".hd-side-card").filter(
            has=self.page.locator("p.section-title", has_text=title))

    @property
    def notices(self):
        return self.side_card(self.NOTICE_BOARD_TITLE).locator(".notice-item")

    def notice_badge(self, index: int):
        return self.notices.nth(index).locator(".notice-badge")

    def notice_text(self, index: int):
        """The notice's text (first 100 characters, '…' when cut)."""
        return self.notices.nth(index).locator("div")

    @property
    def view_all_notices_link(self):
        return self.side_card(self.NOTICE_BOARD_TITLE).get_by_role("link", name=self.VIEW_ALL_NOTICES_LABEL)

    def quick_link(self, label: str):
        return self.side_card(self.QUICK_LINKS_TITLE).get_by_role("link", name=label, exact=True)

    # ── Footer ────────────────────────────────────────────────────────────────

    @property
    def footer(self):
        return self.page.locator("footer")

    def footer_link(self, label: str):
        return self.footer.get_by_role("link", name=label)

    # ── "Portal Under Testing" notice (dev only) ──────────────────────────────

    @property
    def testing_notice(self):
        """The modal shown after login on dev; it covers the page until "I understand" is clicked."""
        return self.page.locator("#tpop .tp-card")

    @property
    def testing_notice_button(self):
        return self.page.locator("#tpop button.tp-btn")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Dismiss the 'Portal Under Testing' notice if shown")
    def dismiss_testing_notice(self):
        """Clicks "I understand" when the notice opens (on a short timer, once per session)."""
        try:
            self.testing_notice_button.wait_for(state="visible", timeout=3000)
        except Exception:
            return
        self.testing_notice_button.click()
        self.testing_notice.wait_for(state="hidden")

    @allure.step("Open the agency Home page")
    def open(self):
        """Navigates to Home (requires a logged-in agency session whose application is submitted)."""
        self.navigate(AGENCY_HOME_URL)

    @allure.step("Click 'Mark all read'")
    def mark_all_read(self):
        """Marks every notification read; the page reloads once the server answers."""
        with self.page.expect_navigation():
            self.mark_all_read_button.click()

    @allure.step("Click 'Logout'")
    def logout(self):
        self.logout_link.click()
        self.page.wait_for_load_state()
