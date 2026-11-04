"""
Data Factory — Admin Notices Management
=========================================
Centralises all notice test data. Each method maps to one of the
Notion test cases KAN-TC-233 through KAN-TC-245.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class NoticeData:
    title: str
    body: str
    badge: str = "info"           # new | alert | info | urgent | general
    dept: str = ""
    active: bool = True
    pinned: bool = False
    attachment_path: Optional[str] = None
    scenario_label: str = ""
    expected_error: Optional[str] = None


class NoticesFactory:

    # Title used by TC-245's "count increments" step (kept as a constant so the
    # cleanup helper can find and delete it).
    EXTRA_ALERT_TITLE: str = "Filter Tab Count Update Test — Alert"

    # Badge colours (background) in the form preview, the admin list and on the public board (KAN-31 AC-5)
    BADGE_COLOURS = {"new": "rgb(185, 28, 28)", "alert": "rgb(217, 119, 6)", "info": "rgb(29, 78, 216)",
                     "urgent": "rgb(124, 58, 237)", "general": "rgb(71, 85, 105)"}
    # Officer Console page-title form (EC-7) and the allowed clock difference from IST (EC-4)
    EXPECTED_TITLE = "Notices — MPPA Officer Console"
    CLOCK_TOLERANCE_MINUTES = 2
    MISSING_NOTICE_ID = 999999
    BODY_REQUIRED = "Notice body is required."
    BADGE_OUTSIDE_LIST = "breaking"

    @staticmethod
    def today_ist() -> datetime:
        return datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)

    # ── TC-233 — Valid mandatory fields ───────────────────────────────────────

    @staticmethod
    def valid_notice() -> NoticeData:
        return NoticeData(
            title="Automation Test Notice — Mandatory Fields",
            body="This notice was created by an automated test to verify mandatory-field submission.",
            badge="alert",
            dept="Registering Authority",
            scenario_label="valid_notice",
        )

    # ── TC-234 — Active notice visible on public board ────────────────────────

    @staticmethod
    def active_notice() -> NoticeData:
        return NoticeData(
            title="Active Notice — Public Board Visibility Test",
            body="This active notice should appear on the agency-facing notice board.",
            badge="new",
            dept="Portal Administration",
            active=True,
            scenario_label="active_notice",
        )

    # ── TC-235 — Inactive notice hidden from public board ────────────────────

    @staticmethod
    def inactive_notice() -> NoticeData:
        return NoticeData(
            title="Inactive Notice — Public Board Visibility Test",
            body="This inactive notice must NOT appear on the agency-facing notice board.",
            badge="info",
            active=False,
            scenario_label="inactive_notice",
        )

    # ── TC-236 — Pinned notice at top of public board ─────────────────────────

    @staticmethod
    def pinned_notice() -> NoticeData:
        return NoticeData(
            title="Pinned Notice — Top Of Board Test",
            body="This pinned notice must always appear at the very top of the public board.",
            badge="new",
            active=True,
            pinned=True,
            scenario_label="pinned_notice",
        )

    # ── TC-237 — Per-badge-type colour check ─────────────────────────────────

    @staticmethod
    def badge_notice(badge: str) -> NoticeData:
        titles = {
            "new":     "Colour Test — NEW Badge Notice",
            "alert":   "Colour Test — ALERT Badge Notice",
            "info":    "Colour Test — INFO Badge Notice",
            "urgent":  "Colour Test — URGENT Badge Notice",
            "general": "Colour Test — GENERAL Badge Notice",
        }
        return NoticeData(
            title=titles[badge],
            body=f"Automated notice to verify the {badge.upper()} badge colour on the public board.",
            badge=badge,
            active=True,
            scenario_label=f"badge_{badge}",
        )

    # ── TC-238 — Edit pre-fills form; saving updates everywhere ──────────────

    @staticmethod
    def notice_to_edit() -> NoticeData:
        return NoticeData(
            title="Edit Test — Original Notice Title",
            body="Original notice body before edit.",
            badge="info",
            active=True,
            scenario_label="notice_to_edit",
        )

    EDITED_TITLE: str = "Edit Test — Updated Notice Title"

    # ── TC-239 — Delete removes notice permanently ────────────────────────────

    @staticmethod
    def notice_to_delete() -> NoticeData:
        return NoticeData(
            title="Delete Test — Notice To Be Removed",
            body="This notice will be deleted by the automated test.",
            badge="info",
            active=True,
            scenario_label="notice_to_delete",
        )

    # ── TC-240 — PDF attachment accessible as download link ──────────────────

    @staticmethod
    def notice_with_attachment(attachment_path: str) -> NoticeData:
        return NoticeData(
            title="Attachment Test — Notice With PDF",
            body="This notice has a valid PDF attachment linked to it.",
            badge="info",
            active=True,
            attachment_path=attachment_path,
            scenario_label="notice_with_attachment",
        )

    # ── TC-241 — Blank title shows validation error ───────────────────────────

    @staticmethod
    def blank_title() -> NoticeData:
        return NoticeData(
            title="",
            body="Notice body submitted without a title.",
            badge="info",
            scenario_label="blank_title",
            expected_error="Notice title is required.",
        )

    # ── TC-242 — Invalid attachment format triggers error ─────────────────────

    @staticmethod
    def invalid_attachment(attachment_path: str) -> NoticeData:
        return NoticeData(
            title="Attachment Test — Invalid File Format",
            body="This notice attempts to upload a .docx file as an attachment.",
            badge="info",
            attachment_path=attachment_path,
            scenario_label="invalid_attachment",
            expected_error="Attachment must be JPG, PNG or PDF.",
        )

    # ── TC-243 — Oversized attachment triggers size error ─────────────────────

    @staticmethod
    def oversized_attachment(attachment_path: str) -> NoticeData:
        return NoticeData(
            title="Attachment Test — Oversized File",
            body="This notice attempts to upload a file larger than 5 MB.",
            badge="info",
            attachment_path=attachment_path,
            scenario_label="oversized_attachment",
            expected_error="File exceeds 5 MB limit. Please choose a smaller file.",
        )

    # ── TC-700 / TC-701 — Status and Pin toggles in the list ─────────────────

    @staticmethod
    def toggle_status_notice() -> NoticeData:
        return NoticeData(title="Toggle Status Test — Notice", body="Automated notice for the status button.",
                          badge="info", active=True, scenario_label="toggle_status")

    @staticmethod
    def toggle_pin_notice() -> NoticeData:
        return NoticeData(title="Toggle Pin Test — Notice", body="Automated notice for the Pin button.",
                          badge="info", active=True, pinned=False, scenario_label="toggle_pin")

    # ── TC-702 — Cancel Edit ──────────────────────────────────────────────────

    CANCELLED_TITLE: str = "Cancel Edit Test — Should Not Be Saved"

    @staticmethod
    def notice_to_cancel_edit() -> NoticeData:
        return NoticeData(title="Cancel Edit Test — Original Title", body="Automated notice for Cancel Edit.",
                          badge="urgent", dept="NIC Technical Team", scenario_label="cancel_edit")

    # ── TC-705 — Blank body ───────────────────────────────────────────────────

    @classmethod
    def blank_body(cls) -> NoticeData:
        return NoticeData(title="Body Validation Test — Blank Body", body="", badge="info",
                          scenario_label="blank_body", expected_error=cls.BODY_REQUIRED)

    # ── TC-706 — Maximum lengths ──────────────────────────────────────────────

    MAX_LENGTH_PREFIX: str = "Max Length Test "

    @classmethod
    def over_max_lengths(cls) -> NoticeData:
        """One character over each limit (title 200, body 2,000, department 120)."""
        return NoticeData(title=(cls.MAX_LENGTH_PREFIX + "a" * 200)[:201], body="b" * 2001, dept="c" * 121,
                          badge="info", scenario_label="one_over_max_lengths")

    # ── TC-707 — Badge outside the list ───────────────────────────────────────

    @classmethod
    def badge_outside_list(cls) -> NoticeData:
        return NoticeData(title="Badge Validation Test — Unknown Badge", body="Automated notice with a tampered "
                          "badge type.", badge=cls.BADGE_OUTSIDE_LIST, scenario_label="badge_outside_list")

    # ── TC-712 — Long text, HTML, quotes, Marathi ─────────────────────────────

    SPECIAL_PREFIX: str = "Special Text Test "

    @classmethod
    def special_text(cls) -> NoticeData:
        tail = " <b>bold</b> \"quotes\" 'apostrophes' सूचना"
        return NoticeData(title=(cls.SPECIAL_PREFIX + "x" * 200)[:200 - len(tail)] + tail,
                          body="<b>bold</b> <script>window.__xss = 1</script> \"quotes\" 'apostrophes' सूचना",
                          badge="general", dept="कौशल्य विकास विभाग", scenario_label="html_quotes_marathi")

    # ── Cleanup support ───────────────────────────────────────────────────────

    @classmethod
    def all_test_titles(cls) -> list[str]:
        """Every notice title the automation suite can create.

        Used by the cleanup helper to delete only notices produced by these
        tests. ``invalid_attachment`` / ``oversized_attachment`` titles are
        included even though those notices should never save — listing them is
        harmless and guards against a portal that wrongly persisted them.
        """
        titles = [
            cls.valid_notice().title,
            cls.active_notice().title,
            cls.inactive_notice().title,
            cls.pinned_notice().title,
            cls.notice_to_edit().title,
            cls.EDITED_TITLE,
            cls.notice_to_delete().title,
            cls.notice_with_attachment("").title,
            cls.invalid_attachment("").title,
            cls.oversized_attachment("").title,
            cls.EXTRA_ALERT_TITLE,
            cls.toggle_status_notice().title,
            cls.toggle_pin_notice().title,
            cls.notice_to_cancel_edit().title,
            cls.CANCELLED_TITLE,
            cls.blank_body().title,
            cls.MAX_LENGTH_PREFIX,
            cls.badge_outside_list().title,
            cls.SPECIAL_PREFIX,
        ]
        titles += [
            cls.badge_notice(b).title
            for b in ("new", "alert", "info", "urgent", "general")
        ]
        return titles
