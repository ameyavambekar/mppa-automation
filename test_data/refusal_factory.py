"""
Data Factory — refusing an application on the Officer Console (appeal test data)
================================================================================
An application can only be refused at the end of the full desktop-scrutiny loop on
``/module/admin/dashboard/agency_view.php``: Part A put On Hold → Compliance 1 → the agency replies →
Part A still On Hold → show cause notice with a personal hearing → a further window to correct → the
agency replies again → Part A still On Hold → refusal order. ``RefusalData`` carries every text and
choice the officer and the agency enter on the way. All text is marked as QA automation test data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RefusalData:
    # Review — the item put On Hold (every other item is approved)
    hold_item: str = "part_a"
    hold_reason: str = "incomplete_form"
    hold_remark: str = ""
    # Agency's reply to each compliance notice
    correction_note: str = ""
    reply_text: str = ""
    # Compliance 2 — show cause notice and personal hearing
    scn_reason: str = "inadequate_reply"
    scn_grounds: str = ""
    hearing_minutes_ahead: int = 4
    hearing_venue: str = ""
    # Hearing record and the further window to correct
    attendance: str = "attended"
    window_days: str = "3"
    hearing_record: str = ""
    # Refusal order
    refusal_reason: str = "failed_correction"
    speaking_order: str = ""              # to the agency — at least 100 characters
    division_note: str = ""               # to the Division — at least 20 characters
    scenario_label: str = ""
    expected_error: str | None = None


class RefusalFactory:

    REFUSED_STAGE = "Stage Refused"

    @staticmethod
    def failed_correction() -> RefusalData:
        """Part A deficiency never cured — refused under Sec 4(3)(b) and Rule 4(8). The reason in the order
        is what FORM-III later shows as 'Reason given in the order'."""
        return RefusalData(
            hold_remark="QA automation: Part A details incomplete (appeal test data).",
            correction_note="QA automation: no change — details are correct as submitted (appeal test data).",
            reply_text="QA automation reply: corrections submitted (appeal test data).",
            scn_grounds="QA automation: the reply did not cure the Part A deficiency (appeal test data).",
            hearing_venue="QA automation — District Skill Development Office, Room 1",
            hearing_record="QA automation: hearing held, agency attended; 3 days to correct Part A (appeal test data).",
            speaking_order=("QA automation speaking order (appeal test data): the agency was given a deficiency notice "
                            "for Part A, a show cause notice and a personal hearing, and a further window to correct. "
                            "The details it resubmitted still did not cure the deficiency, so the application is "
                            "refused under Sec 4(3)(b) and Rule 4(8)."),
            division_note="QA automation: refused for appeal test data — Part A deficiency not cured.",
            scenario_label="failed_correction",
        )
