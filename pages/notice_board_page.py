from urllib.parse import urlencode

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

    INTRO = "Important announcements, alerts, and updates from the department."
    SEARCH_PLACEHOLDER = "Search notices…"
    SEARCH_LABEL = "Search"
    SEARCH_MAX_LENGTH = 100
    SEARCH_PATTERN_TITLE = "Special characters and HTML tags are not allowed"
    NO_NOTICES = "No notices found."
    # Filter pills: label -> ``type`` query value. The active pill carries ``active`` (All) or
    # ``active-<type>`` (the others).
    FILTERS = {"All": "all", "New": "new", "Alert": "alert", "Info": "info", "Urgent": "urgent"}

    @staticmethod
    def no_notices_for(query: str) -> str:
        return f'No notices found for "{query}".'

    # ── Hero / header ─────────────────────────────────────────────────────────

    @property
    def board_heading(self):
        return self.page.locator(".nb-hero h1")

    @property
    def intro(self):
        return self.page.locator(".nb-hero p")

    @property
    def count_badge(self):
        """The '<n> Notices' badge in the hero."""
        return self.page.locator(".nb-count-badge span")

    # ── Top bar ───────────────────────────────────────────────────────────────

    def top_bar_link(self, label: str):
        return self.page.locator(".nav-right").get_by_role("link", name=label, exact=True)

    # ── Filter & search ───────────────────────────────────────────────────────

    def filter_button(self, label: str):
        """Filter pill by partial visible text, e.g. 'All', 'Alert', 'New'."""
        return self.page.locator(f".filter-btn:has-text('{label}')").first

    @property
    def active_filter_button(self):
        return self.page.locator(".filter-btn.active")

    @property
    def filter_pills(self):
        return self.page.locator(".filter-btn")

    def pill(self, notice_type: str):
        """Filter pill for a ``type`` query value ('all', 'new', 'alert', 'info', 'urgent')."""
        return self.page.locator(f".filter-btn[href='?type={notice_type}']")

    @property
    def highlighted_pills(self):
        """Pills carrying any ``active`` / ``active-<type>`` class."""
        return self.page.locator(".filter-btn[class*='active']")

    @property
    def search_input(self):
        return self.page.locator(".search-box input[name='q']")

    @property
    def search_button(self):
        return self.page.locator(".search-box button[type='submit']")

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

    def card_part(self, index: int, part: str):
        """``part`` of the index-th card: 'nbadge', 'pin-icon', 'notice-date', 'notice-title',
        'notice-body', 'notice-attachment' or 'notice-dept'."""
        return self.notice_cards.nth(index).locator(f".{part}")

    @property
    def attachment_links(self):
        return self.page.locator(".notice-card a.notice-attachment")

    @allure.step("Read the notice cards")
    def read_cards(self) -> list[dict]:
        """Every card on the page, in order: type (from its ``type-<x>`` class), badge, badge colour,
        pinned, date, title, body and dept ('' when absent)."""
        return self.notice_cards.evaluate_all("""cards => cards.map(c => {
            const text = sel => (c.querySelector(sel)?.innerText || '').trim();
            const badge = c.querySelector('.nbadge');
            return {
                type: ([...c.classList].find(k => k.startsWith('type-')) || '').slice(5),
                badge: text('.nbadge'),
                badge_colour: badge ? getComputedStyle(badge).backgroundColor : '',
                pinned: !!c.querySelector('.pin-icon'),
                date: text('.notice-date'),
                title: text('.notice-title'),
                body: text('.notice-body'),
                dept: text('.notice-dept'),
            };
        })""")

    # ── Empty state ───────────────────────────────────────────────────────────

    @property
    def empty_state(self):
        return self.page.locator(".empty-state")

    @property
    def empty_state_text(self):
        return self.page.locator(".empty-state p")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the public Notice Board page")
    def open(self):
        self.navigate(NOTICE_BOARD_URL)
        self.wait_for_load()

    @allure.step("Open the Notice Board with type='{notice_type}', q='{query}'")
    def open_with(self, notice_type: str, query: str = None):
        """Opens the board straight from a URL (``?type=…&q=…``), as a bookmark or typed address would."""
        params = {"type": notice_type} if query is None else {"type": notice_type, "q": query}
        self.navigate(f"{NOTICE_BOARD_URL}?{urlencode(params)}")
        self.wait_for_load()

    @allure.step("Filter notice board by: '{label}'")
    def filter_by(self, label: str):
        self.filter_button(label).click()
        self.wait_for_load()

    @allure.step("Click the '{label}' filter pill")
    def click_pill(self, label: str):
        with self.page.expect_navigation():
            self.pill(self.FILTERS[label]).click()

    @allure.step("Search notice board for: '{query}'")
    def search(self, query: str):
        self.search_input.fill(query)
        self.search_input.press("Enter")
        self.wait_for_load()

    @allure.step("Search for '{query}' with the Search button")
    def search_with_button(self, query: str):
        self.search_input.fill(query)
        with self.page.expect_navigation():
            self.search_button.click()
