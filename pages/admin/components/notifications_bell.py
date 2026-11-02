import allure

from pages.base_page import BasePage


class AdminNotificationsBell(BasePage):
    """Reusable page-object component for the notifications bell in the admin top bar.

    The bell (``#tbBell``) is on every Officer Console page. Its ``aria-label`` is
    "Notifications (<n> unread)" and its count (``#tbBellN``) is hidden when nothing is unread
    ("99+" above 99). Clicking it toggles the dropdown (``#tbDrop``, ``aria-expanded`` on the
    bell), which loads the latest 10 notifications into ``#tbDropList`` ("Loading…" until then,
    "No notifications yet." when there are none). Each entry is ``a.tb-n`` (``unread`` while
    unread) with a coloured dot, the bold title, "<agency> · " and the time
    ("YYYY-MM-DD HH:MM"); clicking one marks it read (``notifications.read``) and opens its
    agency. The header has "Mark all read" (``#tbReadAll``) and the footer "View all
    notifications". A click anywhere outside closes the dropdown.

    Usage
    -----
        bell = AdminNotificationsBell(page)        # or admin_notifications_page.bell
        bell.open()
        expect(bell.items).to_have_count(10)
    """

    ROOT = "#adm-topbar"
    LABEL = "Notifications ({n} unread)"
    LOADING = "Loading…"
    EMPTY = "No notifications yet."
    MARK_ALL_READ = "Mark all read"
    VIEW_ALL = "View all notifications"
    LATEST = 10

    @staticmethod
    def label(unread: int) -> str:
        return AdminNotificationsBell.LABEL.format(n=unread)

    # ── Locators ──────────────────────────────────────────────────────────────

    @property
    def button(self):
        return self.page.locator("#tbBell")

    @property
    def count(self):
        """Unread count on the bell (hidden at 0)."""
        return self.page.locator("#tbBellN")

    @property
    def dropdown(self):
        return self.page.locator("#tbDrop")

    @property
    def dropdown_title(self):
        return self.page.locator("#tbDrop .tb-drop-h b")

    @property
    def mark_all_read_button(self):
        return self.page.locator("#tbReadAll")

    @property
    def items(self):
        return self.page.locator("#tbDropList a.tb-n")

    @property
    def unread_items(self):
        return self.page.locator("#tbDropList a.tb-n.unread")

    def item_title(self, index: int):
        return self.items.nth(index).locator("b")

    def item_time(self, index: int):
        return self.items.nth(index).locator("small")

    @property
    def empty_message(self):
        return self.page.locator("#tbDropList .tb-empty")

    @property
    def view_all_link(self):
        return self.page.locator("#tbDrop a.tb-drop-f")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the notifications bell")
    def open(self):
        """Clicks the bell and waits until the dropdown has loaded its list."""
        with self.page.expect_response(lambda r: "notifications.list" in r.url):
            self.button.click()
        self.page.wait_for_function("() => !/Loading/.test(document.querySelector('#tbDropList').textContent)")

    @allure.step("Close the notifications dropdown by clicking outside it")
    def close_by_clicking_outside(self, outside):
        """outside: a locator for something on the page that is not a link (e.g. the page heading)."""
        outside.click()

    @allure.step("Click a notification in the bell dropdown")
    def click_item(self, item):
        """Clicks the entry (one of ``items``) and waits for the agency page it opens; the entry is marked
        read as it is clicked."""
        with self.page.expect_request(lambda r: "notifications.read" in r.url):
            with self.page.expect_navigation():
                item.click()

    @allure.step("Click 'Mark all read' in the bell dropdown")
    def mark_all_read(self):
        """Marks every notification read and waits for the dropdown to reload."""
        with self.page.expect_response(lambda r: "notifications.list" in r.url):
            self.mark_all_read_button.click()
