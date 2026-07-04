import allure

from .base_page import BasePage
from config import NOTICES_URL

NOTICE_BOARD_URL = NOTICES_URL


class NoticeBoardPage(BasePage):
    """Public-facing Notice Board page (/module/notices.php).

    Each notice is a ``.notice-card`` carrying a type modifier class
    (``type-new`` / ``type-alert`` / ``type-info`` / ``type-urgent`` /
    ``type-general``) and an optional ``pinned`` modifier. Inside the card:
    ``.nbadge`` (badge chip), ``.pin-icon`` (📌 Pinned), ``.notice-title``,
    ``.notice-body``, ``.notice-attachment`` (download link) and
    ``.notice-dept``.
    """

    # ── Hero / header ─────────────────────────────────────────────────────────

    @property
    def board_heading(self):
        return self.page.locator(".nb-hero h1")

    @property
    def count_badge(self):
        """The '<n> Notices' badge in the hero."""
        return self.page.locator(".nb-count-badge span")

    # ── Filter & search ───────────────────────────────────────────────────────

    def filter_button(self, label: str):
        """Filter pill by partial visible text, e.g. 'All', 'Alert', 'New'."""
        return self.page.locator(f".filter-btn:has-text('{label}')").first

    @property
    def active_filter_button(self):
        return self.page.locator(".filter-btn.active")

    @property
    def search_input(self):
        return self.page.locator(".search-box input[name='q']")

    # ── Notice cards ──────────────────────────────────────────────────────────

    @property
    def notice_cards(self):
        return self.page.locator(".notice-card")

    @property
    def first_notice_card(self):
        return self.page.locator(".notice-card").first

    def notice_card(self, title: str):
        """The notice card whose title matches the given text."""
        return self.page.locator(
            f".notice-card:has(.notice-title:has-text('{title}'))"
        ).first

    def notice_badge(self, title: str):
        """The badge chip (.nbadge) inside the notice card for the given title."""
        return self.notice_card(title).locator(".nbadge")

    def notice_pin_indicator(self, title: str):
        """The '📌 Pinned' indicator inside the notice card for the given title."""
        return self.notice_card(title).locator(".pin-icon")

    def notice_attachment_link(self, title: str):
        """The '📎 View Attachment' download link inside the notice card."""
        return self.notice_card(title).locator(".notice-attachment")

    def notice_date(self, title: str):
        return self.notice_card(title).locator(".notice-date")

    # ── Empty state ───────────────────────────────────────────────────────────

    @property
    def empty_state(self):
        return self.page.locator(".empty-state")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the public Notice Board page")
    def open(self):
        self.navigate(NOTICE_BOARD_URL)
        self.wait_for_load()

    @allure.step("Filter notice board by: '{label}'")
    def filter_by(self, label: str):
        self.filter_button(label).click()
        self.wait_for_load()

    @allure.step("Search notice board for: '{query}'")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.wait_for_load()
