import re
from datetime import datetime

import allure

from config import ADMIN_BASE
from pages.admin.components.notifications_bell import AdminNotificationsBell
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

ADMIN_NOTIFICATIONS_URL = f"{ADMIN_BASE}/notifications/index.php"


class AdminNotificationsPage(BasePage):
    """Page object for the officer Notifications page (module/admin/notifications/index.php,
    "Notifications — MPPA Officer Console").

    Header: "Notifications", the subtitle "<jurisdiction> · <n> unread" (e.g. "Maharashtra State ·
    9 unread"), the filter buttons "All" (``index.php``) and "Unread" (``?f=unread``) — the active one
    is ``ui-btn-primary`` — and "Mark all read" (a POST form, ``do=read_all``).

    List: one ``a.nt-item`` per notification (``unread`` while unread, ``data-id`` = notification
    id), newest first and not paginated. Each has a coloured dot (``.nt-dot``) for its type, the title
    (``.nt-title``), the body (``.nt-body``), the meta line (``.nt-meta``) "<type label> · <agency>
    (<Registration ID>) · DD Mon YYYY, HH:MM AM/PM" and, while unread, a blue "New" badge. Clicking
    one marks it read (``notifications.read``, in the background) and opens the agency
    (``../dashboard/agency_view.php?id=<agency id>``).

    The top-bar bell is ``self.bell`` and the left nav ``self.sidebar``.
    """

    PAGE_TITLE = "Notifications — MPPA Officer Console"
    HEADING = "Notifications"
    STATE_JURISDICTION = "Maharashtra State"
    ALL_LABEL = "All"
    UNREAD_LABEL = "Unread"
    MARK_ALL_READ = "Mark all read"
    NEW_BADGE = "New"
    UNREAD_FILTER = "unread"
    AGENCY_VIEW_LINK = re.compile(r"\.\./dashboard/agency_view\.php\?id=\d+$")
    META_DATE_FORMAT = "%d %b %Y, %I:%M %p"

    # Dot colour of each notification type (the page's own type → colour map)
    BLUE, GREEN, RED, AMBER, GRAY = "#2e5aa8", "#079455", "#d92d20", "#dc6803", "#98a2b3"
    TYPE_COLOURS = {"new": BLUE, "reply": GREEN, "branch": BLUE, "escalate": RED, "appeal": AMBER, "sla": RED,
                    "due": AMBER, "hearing": AMBER, "decision": GREEN, "compliance": AMBER, "info": GRAY}
    # Meta-line label of the types seen on dev → type
    META_TYPES = {"New application": "new", "45-day SLA": "sla", "Appeal": "appeal", "Decision": "decision"}

    @staticmethod
    def subtitle(jurisdiction: str, unread: int) -> str:
        return f"{jurisdiction} · {unread} unread"

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    @property
    def bell(self) -> AdminNotificationsBell:
        return AdminNotificationsBell(self.page)

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("main h2")

    @property
    def subtitle_text(self):
        """'<jurisdiction> · <n> unread'."""
        return self.page.locator("main h2 + p")

    @property
    def all_filter(self):
        return self.page.locator("main a.ui-btn[href='index.php']")

    @property
    def unread_filter(self):
        return self.page.locator("main a.ui-btn[href='?f=unread']")

    @property
    def mark_all_read_button(self):
        return self.page.locator("main form:has(input[name='do'][value='read_all']) button[type='submit']")

    @property
    def logout_link(self):
        """Top-bar 'Logout'."""
        return self.page.locator("#adm-topbar a[href$='/auth/logout.php']")

    # ── List ──────────────────────────────────────────────────────────────────

    @property
    def items(self):
        return self.page.locator("a.nt-item")

    @property
    def unread_items(self):
        return self.page.locator("a.nt-item.unread")

    @property
    def read_items(self):
        return self.page.locator("a.nt-item:not(.unread)")

    @property
    def new_badges(self):
        return self.page.locator("a.nt-item .ui-badge")

    def item_by_id(self, notification_id: str):
        return self.page.locator(f"a.nt-item[data-id='{notification_id}']")

    def item_with_title(self, title: str):
        return self.items.filter(has=self.page.locator(".nt-title", has_text=title))

    def item_dot(self, item):
        return item.locator(".nt-dot")

    def item_title(self, item):
        return item.locator(".nt-title")

    def item_body(self, item):
        return item.locator(".nt-body")

    def item_meta(self, item):
        return item.locator(".nt-meta")

    def item_badge(self, item):
        return item.locator(".ui-badge")

    # ── Reads (no assertions) ─────────────────────────────────────────────────

    def unread_count(self) -> int:
        """The <n> of the subtitle '<jurisdiction> · <n> unread'."""
        return int(re.search(r"(\d+) unread", self.subtitle_text.inner_text()).group(1))

    def meta_parts(self, item) -> list[str]:
        """The meta line split on ' · ': [type label, (agency (Registration ID),) date]."""
        return [p.strip() for p in self.item_meta(item).inner_text().split("·")]

    def item_time(self, item) -> datetime:
        return datetime.strptime(self.meta_parts(item)[-1], self.META_DATE_FORMAT)

    def dot_colour(self, item) -> str:
        """The dot's background as '#rrggbb'."""
        rgb = self.item_dot(item).evaluate("e => getComputedStyle(e).backgroundColor")
        return "#" + "".join(f"{int(v):02x}" for v in re.findall(r"\d+", rgb)[:3])

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Notifications page")
    def open(self, unread_only: bool = False):
        self.navigate(ADMIN_NOTIFICATIONS_URL + ("?f=unread" if unread_only else ""))

    @allure.step("Open the Notifications page with filter f={value}")
    def open_with_filter(self, value: str):
        self.navigate(f"{ADMIN_NOTIFICATIONS_URL}?f={value}")

    @allure.step("Click the 'Unread' filter")
    def show_unread(self):
        with self.page.expect_navigation():
            self.unread_filter.click()

    @allure.step("Click the 'All' filter")
    def show_all(self):
        with self.page.expect_navigation():
            self.all_filter.click()

    @allure.step("Click 'Mark all read'")
    def mark_all_read(self):
        with self.page.expect_navigation():
            self.mark_all_read_button.click()

    @allure.step("Click the notification")
    def open_item(self, item):
        """Clicks the notification and waits for the agency page it opens; it is marked read as it is clicked."""
        with self.page.expect_request(lambda r: "notifications.read" in r.url):
            with self.page.expect_navigation():
                item.click()

    @allure.step("Log out from the top bar")
    def logout(self):
        with self.page.expect_navigation():
            self.logout_link.click()
