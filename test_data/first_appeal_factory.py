"""
Data Factory — First Appeal Management (FORM-III)
=================================================
Two value objects power this module's tests:

* ``FirstAppealData``  — what an *agency* enters when it files a FORM-III appeal
  on ``/module/agency/appeals/first.php``. The appellant, the order appealed
  against and the limitation are filled in by the portal from the refusal order,
  so only the grounds, facts, relief, documents and verification are entered.
  The Order of the Registering Authority (``documents["order"]``) is required.

* ``AppealOutcomeData`` — what an *officer* records when deciding an appeal.

Each value object carries ``scenario_label`` and ``expected_error`` meta fields,
matching the other factories in this project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Agency-side: filing a FORM-III appeal ──────────────────────────────────────

@dataclass
class FirstAppealData:
    grounds: list[str] = field(default_factory=list)   # FirstAppealPage.GROUNDS values
    grounds_other: str = ""
    brief_facts: str = ""                 # at least 20 characters
    relief_type: str = ""                 # FirstAppealPage.RELIEFS value
    relief_sought: str = ""               # at least 10 characters
    documents: dict[str, str] = field(default_factory=dict)  # DOC_SLOTS key → path ("order" is required)
    # Verification — None keeps the value the portal pre-fills from the application
    place: Optional[str] = None
    signatory_name: Optional[str] = None
    signatory_designation: Optional[str] = None
    declare: bool = True
    scenario_label: str = ""
    expected_error: Optional[str] = None


class FirstAppealFactory:
    """Builds FORM-III filing payloads (all text marked as QA automation test data)."""

    NO_GROUND_ALERT = "Please tick at least one ground of appeal."
    TOO_LARGE_ALERT = "Each document must be a PDF of 2 MB or less."
    CONFIRM = ("Submit your First Appeal?\n\nYou can file only TWO appeals in total and this one cannot be "
               "edited after submission.")
    APPEALS_REMAINING = "Appeals remaining: {n} of 2"
    ORDER_LOCKED = "These details are taken from the official order and cannot be changed."
    WITHIN_LIMIT = "✓ Yes — day {days} of 60"

    @staticmethod
    def valid_with_documents(file_path: str) -> FirstAppealData:
        """A complete appeal carrying all five documents (``file_path`` reused for every slot), so the
        officer's view lists a full set of labelled documents."""
        return FirstAppealData(
            grounds=["error_of_law", "procedural_irregularity"],
            brief_facts="QA automation (appeal test data): the application was refused without considering "
                        "the corrected Part A details already on record; this appeal is filed with all "
                        "supporting documents.",
            relief_type="Setting Aside the Order",
            relief_sought="Set aside the refusal order and direct registration (QA automation).",
            documents={slot: file_path for slot in ("order", "original", "ack", "fees", "other")},
            scenario_label="valid_with_documents",
        )

    @staticmethod
    def valid_order_only(file_path: str) -> FirstAppealData:
        """A complete appeal with only the required document — the Order of the Registering Authority."""
        return FirstAppealData(
            grounds=["natural_justice"],
            brief_facts="QA automation (appeal test data): the agency was not given a fair chance to explain "
                        "the Part A details before the refusal order.",
            relief_type="Remand for Fresh Consideration",
            relief_sought="Remand the matter for fresh consideration (QA automation).",
            documents={"order": file_path},
            scenario_label="valid_order_only",
        )

    @staticmethod
    def other_ground(file_path: str) -> FirstAppealData:
        """An appeal on the 'Other' ground with its specified text."""
        return FirstAppealData(
            grounds=["other"],
            grounds_other="QA automation: the refusal order cites a deficiency that was already corrected.",
            brief_facts="QA automation (appeal test data): the Part A deficiency named in the order had been "
                        "corrected in the reply to the deficiency notice.",
            relief_type="Modification of Order",
            relief_sought="Modify the refusal order (QA automation).",
            documents={"order": file_path},
            scenario_label="other_ground",
        )

    @staticmethod
    def no_ground(file_path: str) -> FirstAppealData:
        """Everything filled except the grounds — the page refuses to submit."""
        data = FirstAppealFactory.valid_order_only(file_path)
        data.grounds = []
        data.scenario_label = "no_ground"
        data.expected_error = FirstAppealFactory.NO_GROUND_ALERT
        return data

    @staticmethod
    def oversized_document(file_path: str, oversized_path: str) -> FirstAppealData:
        """A PDF over 2 MB in one optional slot — the page refuses to submit."""
        data = FirstAppealFactory.valid_order_only(file_path)
        data.documents["other"] = oversized_path
        data.scenario_label = "oversized_document"
        data.expected_error = FirstAppealFactory.TOO_LARGE_ALERT
        return data


# ── Officer side: passing the appellate order ──────────────────────────────────

@dataclass
class AppealOutcomeData:
    disposal: str = ""                    # AdminAppealsPage.FIRST_DISPOSALS value ("" = none chosen)
    reasons: str = ""                     # speaking order — at least 50 characters
    scenario_label: str = ""
    expected_error: Optional[str] = None


class AppealOutcomeFactory:

    MIN_REASONS = 50
    NO_DISPOSAL = "Select the appellate order (disposal)."
    SHORT_REASONS = "Write the reasons of the order (at least 50 characters)."
    CONFIRM = "Pass this order?\n\n{label}\n{desc}"
    IMPACT_DEFAULT = "Choose an option to see its effect on the application."
    # disposal → effect shown under the select (and in the confirmation)
    IMPACT = {
        "allowed": "District order reversed. Status becomes APPROVED and the certificate is issued.",
        "allowed_conditions": "Approved; the applicant must comply with the conditions written in the order within 15 days.",
        "remanded": "Case sent back to the District to re-evaluate after a fresh site visit or paper verification.",
        "dismissed_upheld": "District refusal confirmed. Opens the 60-day window for the Second Appeal.",
        "dismissed_default": "The appellant did not appear for the hearing without valid reason.",
        "delay_rejected": "Filed beyond 60 days without sufficient cause. Case permanently closed.",
    }
    AUDIT_TABLE = "agency_appeals"
    AUDIT_FILED = "1st Appeal"

    _REASONS = ("QA automation appellate order (appeal test data): the appellant's grounds were examined against "
                "the record; the Part A deficiency named in the refusal order was not cured, so the refusal stands.")

    @staticmethod
    def dismissed_upheld() -> AppealOutcomeData:
        """Dismiss the appeal and uphold the refusal — the agency can then file a Second Appeal."""
        return AppealOutcomeData(disposal="dismissed_upheld", reasons=AppealOutcomeFactory._REASONS,
                                 scenario_label="dismissed_upheld")

    @staticmethod
    def no_disposal() -> AppealOutcomeData:
        return AppealOutcomeData(disposal="", reasons=AppealOutcomeFactory._REASONS, scenario_label="no_disposal",
                                 expected_error=AppealOutcomeFactory.NO_DISPOSAL)

    @staticmethod
    def blank_reasons() -> AppealOutcomeData:
        return AppealOutcomeData(disposal="dismissed_upheld", reasons="", scenario_label="blank_reasons",
                                 expected_error=AppealOutcomeFactory.SHORT_REASONS)

    @staticmethod
    def short_reasons() -> AppealOutcomeData:
        """49 characters — one short of the minimum."""
        return AppealOutcomeData(disposal="dismissed_upheld", reasons=("QA automation reasons " * 3)[:49],
                                 scenario_label="short_reasons", expected_error=AppealOutcomeFactory.SHORT_REASONS)
