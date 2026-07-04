"""
Data Factory — Admin Notices Management
=========================================
Centralises all notice test data. Each method maps to one of the
Notion test cases KAN-TC-233 through KAN-TC-245.
"""

from __future__ import annotations

from dataclasses import dataclass
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

    # ── TC-233 — Valid mandatory fields ───────────────────────────────────────

    @staticmethod
    def valid_notice() -> NoticeData:
        return NoticeData(
            title="Automation Test Notice — Mandatory Fields",
            body="This notice was created by an automated test to verify mandatory-field submission.",
            badge="alert",
            scenario_label="valid_notice",
        )

    # ── TC-234 — Active notice visible on public board ────────────────────────

    @staticmethod
    def active_notice() -> NoticeData:
        return NoticeData(
            title="Active Notice — Public Board Visibility Test",
            body="This active notice should appear on the agency-facing notice board.",
            badge="info",
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
            expected_error="Failed to upload attachment.",
        )

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
        ]
        titles += [
            cls.badge_notice(b).title
            for b in ("new", "alert", "info", "urgent", "general")
        ]
        return titles
