"""
Data Factory — Admin Agencies Management (KAN-25)
==================================================
Test data for the Officer Console's Applications list (agency/list.php) and an application's page
(dashboard/agency_view.php), AIO cases KAN-TC-194 through KAN-TC-211.

The redesigned console (dev, 17-Nov-2026) has no Change Status modal and no Approve / Reject / Suspend
buttons on the agency page any more — decisions go through the review workflow (KAN-12) and Compliance cases
(KAN-46) — so the status-change data of the old suite is gone. What remains is read-only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class AgencySearchData:
    """TC-207 — search the Applications list by each field of one listed application."""
    fields: tuple[str, ...] = ()
    no_match_query: str = ""
    scenario_label: str = ""
    expected_error: str | None = None


@dataclass
class RegistrationInfoData:
    """TC-196 — what each Registration Info value must look like."""
    patterns: dict[str, re.Pattern] = field(default_factory=dict)
    complete_value: str = ""
    scenario_label: str = ""
    expected_error: str | None = None


@dataclass
class CompletionData:
    """TC-197 — the Completion Status panel of a submitted application."""
    total_steps: int = 8
    allowed_statuses: tuple[str, ...] = ()
    submitted_status_expected: str = ""
    scenario_label: str = ""
    expected_error: str | None = None


class AgenciesFactory:

    # ── TC-207 — search by name, Application ID, e-mail and PAN ───────────────

    @staticmethod
    def search_by_each_field() -> AgencySearchData:
        return AgencySearchData(
            fields=("agency", "application_id", "email", "pan"),
            no_match_query="zz-no-such-agency-qa",
            scenario_label="search_by_each_field",
        )

    # ── TC-196 — Registration Info values ─────────────────────────────────────

    @staticmethod
    def registration_info_formats() -> RegistrationInfoData:
        return RegistrationInfoData(
            patterns={
                "Reg ID": re.compile(r"^\d{13}$"),
                "Username": re.compile(r"^\S+$"),
                "Email": re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
                "PAN": re.compile(r"^[A-Z]{5}\d{4}[A-Z]$"),
                "Registered": re.compile(r"^\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}$"),
                "Last Login": re.compile(r"^(\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}|Never|—|-)$"),
                "Reg. IP": re.compile(r"^[0-9a-fA-F:.]+$"),
            },
            complete_value="Yes",
            scenario_label="registration_info_formats",
        )

    # ── TC-197 — Completion Status of a submitted application ────────────────

    @staticmethod
    def completion_of_submitted() -> CompletionData:
        return CompletionData(
            total_steps=8,
            allowed_statuses=("SUBMITTED", "PENDING", "COMPLETE"),
            submitted_status_expected="PENDING",  # a submitted (paid) application has no PENDING step
            scenario_label="completion_of_submitted",
        )
