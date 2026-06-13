"""
Data Factory — Admin Agencies Management
=========================================
Centralises status-change test data for the All Agencies dashboard and the
agency detail view. Each method maps to one of the AIO test cases
KAN-TC-194 through KAN-TC-211.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AgencyStatusData:
    new_status: str = ""
    remarks: str = ""
    scenario_label: str = ""
    expected_error: Optional[str] = None


class AgenciesFactory:

    # Remark used by the status restorer / cleanup paths
    CLEANUP_REMARKS = "Automation cleanup — restoring original status."

    # ── TC-202 — Approve with optional remarks ────────────────────────────────

    @staticmethod
    def approve_with_remarks() -> AgencyStatusData:
        return AgencyStatusData(
            new_status="approved",
            remarks="Application reviewed and approved.",
            scenario_label="approve_with_remarks",
        )

    # ── TC-203 — Reject with blank remarks (blocked) ─────────────────────────

    @staticmethod
    def reject_blank_remarks() -> AgencyStatusData:
        return AgencyStatusData(
            new_status="rejected",
            remarks="",
            scenario_label="reject_blank_remarks",
            expected_error="Remarks are required",
        )

    # ── TC-204 — Suspend with blank remarks (blocked) ─────────────────────────

    @staticmethod
    def suspend_blank_remarks() -> AgencyStatusData:
        return AgencyStatusData(
            new_status="suspended",
            remarks="",
            scenario_label="suspend_blank_remarks",
            expected_error="Remarks are required",
        )

    # ── TC-205 — Reject with valid remarks (audit trail) ──────────────────────

    @staticmethod
    def reject_with_remarks() -> AgencyStatusData:
        return AgencyStatusData(
            new_status="rejected",
            remarks="Missing required documents.",
            scenario_label="reject_with_remarks",
        )

    # ── TC-206 / TC-211 — Suspend with valid remarks ──────────────────────────

    @staticmethod
    def suspend_with_remarks() -> AgencyStatusData:
        return AgencyStatusData(
            new_status="suspended",
            remarks="Suspended pending compliance review (automated test).",
            scenario_label="suspend_with_remarks",
        )
