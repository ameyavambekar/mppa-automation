"""
Data Factory — Notice Board (agency / public view)
====================================================
Search inputs for the Notice Board tests, KAN-TC-531 through KAN-TC-542 (KAN-41).
The notices themselves are whatever the admin has published, so the tests read the
expected results off the board instead of hard-coding them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NoticeSearchData:
    query: str
    notice_type: str = "all"      # all | new | alert | info | urgent (the filter pill)
    scenario_label: str = ""
    expected_error: Optional[str] = None


class NoticeBoardFactory:

    # Badge text -> card type class, and the date format on every card
    BADGES = {"NEW": "new", "ALERT": "alert", "INFO": "info", "URGENT": "urgent"}
    DATE_PATTERN = r"^\d{2} [A-Z][a-z]{2} \d{4}$"

    # ── TC-535 / TC-539 — search a word from a notice title ──────────────────

    @staticmethod
    def title_word() -> NoticeSearchData:
        return NoticeSearchData(query="renewal", scenario_label="title_word")

    @staticmethod
    def title_word_in_capitals() -> NoticeSearchData:
        return NoticeSearchData(query="RENEWAL", scenario_label="title_word_in_capitals")

    # ── TC-535 — a word that appears only in a notice's text ─────────────────

    @staticmethod
    def body_only_word() -> NoticeSearchData:
        return NoticeSearchData(query="unavailable", scenario_label="body_only_word")

    # ── TC-536 / TC-539 — search within the Alert filter ─────────────────────

    @staticmethod
    def word_within_alert() -> NoticeSearchData:
        return NoticeSearchData(query="renewal", notice_type="alert", scenario_label="word_within_alert")

    # ── TC-537 — no match ─────────────────────────────────────────────────────

    @staticmethod
    def no_match() -> NoticeSearchData:
        return NoticeSearchData(query="zzzqqq", scenario_label="no_match")

    # ── TC-540 — HTML / special characters ───────────────────────────────────

    @staticmethod
    def html_tag() -> NoticeSearchData:
        return NoticeSearchData(
            query="<script>",
            scenario_label="html_tag",
            expected_error="Special characters and HTML tags are not allowed",
        )

    # ── TC-541 — over the 100-character limit ────────────────────────────────

    @staticmethod
    def over_max_length() -> NoticeSearchData:
        return NoticeSearchData(query="a" * 101, scenario_label="over_max_length")

    # ── TC-542 — unknown filter type in the URL ──────────────────────────────

    @staticmethod
    def unknown_type() -> NoticeSearchData:
        return NoticeSearchData(query="", notice_type="bogus", scenario_label="unknown_type")
