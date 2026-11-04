"""
Data Factory — Admin Compliance cases
=====================================
Centralises the Open compliance case and case action test data for KAN-46
(AIO KAN-TC-644…677).

Hearing dates are generated relative to now (IST) so they stay in the future on
any run date. ``hearing_at`` is the ``YYYY-MM-DDTHH:MM`` value the dialog's
datetime-local input takes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class ComplianceCaseData:
    trigger: str = "complaint"             # complaint / inspection / overdue_return / other
    details: str = ""
    high_risk: bool = False                # True = Route B (interim suspension)
    reasons: Optional[str] = None          # Reasons in writing — Route B
    scenario_label: str = ""
    expected_message: Optional[str] = None  # toast on success
    expected_error: Optional[str] = None    # toast / validation message when refused


@dataclass
class CaseActionData:
    action: str                            # hearing / window / drop / cancel
    remarks: str = ""
    hearing_at: Optional[str] = None       # YYYY-MM-DDTHH:MM — hearing only
    hearing_mode: Optional[str] = None     # virtual / personal — hearing only
    window_days: Optional[str] = None      # 3 / 5 / 7 — window only
    scenario_label: str = ""
    expected_message: Optional[str] = None
    expected_error: Optional[str] = None


class ComplianceFactory:

    # ── Messages (toasts and History) ─────────────────────────────────────────

    ROUTE_A_OPENED = "pre-cancellation show cause notice issued; agency remains active during the inquiry."
    ROUTE_B_OPENED = "interim suspension ordered (max 6 months) and 15-day show cause notice issued."
    DROPPED = "Proceedings dropped — agency remains fully ACTIVE."
    REVOKED = "Suspension revoked — agency status restored to ACTIVE."
    CANCELLED = ("Speaking cancellation order issued. Registration CANCELLED; the agency may file a First "
                 "Appeal within 60 days.")
    NOT_ALLOWED = "Action not allowed at this step."

    # ── Date helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def now_ist() -> datetime:
        return datetime.now(IST).replace(tzinfo=None)

    @classmethod
    def hearing_slot(cls, days_ahead: int = 7, hour: int = 11) -> str:
        """A datetime-local value ``days_ahead`` days from today at ``hour``:00 (IST)."""
        return (cls.now_ist() + timedelta(days=days_ahead)).replace(hour=hour, minute=0).strftime("%Y-%m-%dT%H:%M")

    # ── Open compliance case ──────────────────────────────────────────────────

    @classmethod
    def route_a(cls) -> ComplianceCaseData:
        return ComplianceCaseData(trigger="complaint",
                                  details="Automation — complaint of unpaid wages from candidates.",
                                  scenario_label="route_a", expected_message=cls.ROUTE_A_OPENED)

    @classmethod
    def route_b(cls) -> ComplianceCaseData:
        return ComplianceCaseData(trigger="inspection",
                                  details="Automation — surprise inspection found no office at the address.",
                                  high_risk=True, reasons="Automation — immediate risk to candidates' safety.",
                                  scenario_label="route_b", expected_message=cls.ROUTE_B_OPENED)

    @classmethod
    def route_b_without_reasons(cls, reasons: str = "") -> ComplianceCaseData:
        data = cls.route_b()
        data.reasons, data.scenario_label = reasons, "route_b_without_reasons"
        data.expected_error = "Reasons in writing are mandatory for interim suspension (Sec 6(2))."
        return data

    @classmethod
    def short_details(cls) -> ComplianceCaseData:
        """9 characters — one short of the 10 the server needs."""
        return ComplianceCaseData(details="Too short", scenario_label="details_9_chars",
                                  expected_error="Describe the complaint / finding (at least 10 characters).")

    @classmethod
    def long_text(cls) -> ComplianceCaseData:
        """About 1,000 characters ending with HTML, a script tag, quotes and Marathi text."""
        tail = " <b>bold</b> <script>alert(1)</script> \"quotes\" 'apostrophes' तक्रार"
        details = ("Automation long text — " + "candidates were charged fees and not placed. " * 21)[:1000 - len(tail)] + tail
        return ComplianceCaseData(details=details, scenario_label="long_text_html_marathi",
                                  expected_message=cls.ROUTE_A_OPENED)

    @staticmethod
    def second_case_error(open_case_no: str) -> str:
        return f"Case {open_case_no} is already open for this agency."

    # ── Case actions ──────────────────────────────────────────────────────────

    @classmethod
    def hearing(cls, mode: str = "virtual", days_ahead: int = 7, hour: int = 11) -> CaseActionData:
        hearing_at = cls.hearing_slot(days_ahead, hour)
        when = datetime.strptime(hearing_at, "%Y-%m-%dT%H:%M")
        return CaseActionData("hearing", "Automation — hearing scheduled.", hearing_at=hearing_at, hearing_mode=mode,
                              scenario_label=f"hearing_{mode}",
                              expected_message=f"Mandatory hearing (Sec 6(4)) scheduled on "
                                               f"{when.strftime('%d %b %Y, %I:%M %p')} ({mode}).")

    @classmethod
    def hearing_without_date(cls) -> CaseActionData:
        return CaseActionData("hearing", "Automation — hearing without a date.", hearing_at="", hearing_mode="virtual",
                              scenario_label="hearing_without_date",
                              expected_error="Choose a future date and time for the hearing.")

    @classmethod
    def hearing_in_past(cls) -> CaseActionData:
        data = cls.hearing_without_date()
        data.hearing_at, data.scenario_label = cls.hearing_slot(days_ahead=-1, hour=10), "hearing_yesterday"
        return data

    @classmethod
    def window(cls, days: str = "3") -> CaseActionData:
        return CaseActionData("window", f"Automation — {days} days to file the overdue return.", window_days=days,
                              scenario_label=f"window_{days}_days",
                              expected_message=f"Post-hearing window of {days} days granted to submit proof of "
                                               f"compliance.")

    @classmethod
    def drop(cls) -> CaseActionData:
        return CaseActionData("drop", "Automation — complaint not substantiated.", scenario_label="drop",
                              expected_message=cls.DROPPED)

    @classmethod
    def revoke(cls) -> CaseActionData:
        return CaseActionData("drop", "Automation — risk addressed, suspension revoked.", scenario_label="revoke",
                              expected_message=cls.REVOKED)

    @classmethod
    def cancellation(cls) -> CaseActionData:
        return CaseActionData("cancel", "Automation — repeated violations proved at the hearing.",
                              scenario_label="cancellation", expected_message=cls.CANCELLED)

    @staticmethod
    def blank_remarks() -> CaseActionData:
        return CaseActionData("drop", "   ", scenario_label="remarks_spaces",
                              expected_error="Remarks / reasons are required.")

    @staticmethod
    def cleanup_remarks() -> str:
        return "Automation cleanup — closing the test case."
