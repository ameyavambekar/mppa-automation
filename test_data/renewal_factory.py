"""
Data Factory — Licence Renewal (Form-II)
========================================
Answers for the agency's Renewal application form (module/agency/renewal.php) and the officer's
decision remarks (admin/licenses/renewals.php), for KAN-37 (AIO KAN-TC-399…411, 415, 832) and KAN-51
(KAN-TC-412…414, 829, 833…845).

The form has no client-side checks: whatever is filled is posted and the server lists what is wrong under
"Please correct:". ``expected_errors`` holds those lines in the order the page lists them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DOCUMENTS = Path(__file__).parent / "documents"

# Server messages ("Please correct:")
ANSWER_CHANGES = "Answer whether anything changed since registration."
ANSWER_CASES = "Answer the question about cases / suspension / cancellation."
TICK_DECLARATION = "Tick the declaration."
DESCRIBE_CHANGES = "Describe the changes (at least 20 characters)."
DESCRIBE_CASES = "Give the details of the cases (at least 20 characters)."
UPLOAD_DOCUMENT = "Upload the document supporting the changes (PDF / JPG / PNG, 10 KB – 2 MB)."
DOCUMENT_TOO_SMALL = "Supporting document is smaller than 10 KB — upload a clear, complete scan."
DOCUMENT_TOO_LARGE = "Supporting document is larger than 2 MB."
DOCUMENT_WRONG_TYPE = "Supporting document must be a PDF, JPG or PNG file."

CHANGES_TEXT = "Head office moved to a new address in the same city."
CASES_TEXT = "A labour complaint is pending before the district officer."


@dataclass
class RenewalData:
    changes_made: Optional[str] = None      # 'no' / 'yes' / None (unanswered)
    changes_details: str = ""
    cases_pending: Optional[str] = None     # 'no' / 'yes' / None (unanswered)
    cases_details: str = ""
    document: Optional[str] = None          # path to the supporting document
    declare: bool = False
    scenario_label: str = ""
    expected_errors: list[str] = field(default_factory=list)


@dataclass
class RenewalDecisionData:
    decision: str                           # 'approve' / 'reject'
    remarks: str
    scenario_label: str = ""
    expected_error: Optional[str] = None    # "Write at least N characters." when too short


@dataclass
class RenewalScope:
    """Areas for the officer-scope cases: officers are created for these (new test officers only)."""
    district: str = ""                      # the district with the most renewal applications
    division: str = ""                      # its division
    empty_division: str = ""                # a division / district with no renewal application
    empty_district: str = ""
    division_districts: tuple = ()


class RenewalFactory:

    # ── Agency form ───────────────────────────────────────────────────────────

    @staticmethod
    def no_changes() -> RenewalData:
        """The valid submission: nothing changed, nothing pending, declared (KAN-TC-405)."""
        return RenewalData(changes_made="no", cases_pending="no", declare=True,
                           scenario_label="No changes, no cases, declared")

    @staticmethod
    def blank() -> RenewalData:
        return RenewalData(scenario_label="Nothing answered",
                           expected_errors=[ANSWER_CHANGES, ANSWER_CASES, TICK_DECLARATION])

    @staticmethod
    def not_declared() -> RenewalData:
        return RenewalData(changes_made="no", cases_pending="no", scenario_label="No / No, declaration unticked",
                           expected_errors=[TICK_DECLARATION])

    @staticmethod
    def changes_without_details() -> RenewalData:
        return RenewalData(changes_made="yes", cases_pending="no", declare=True,
                           scenario_label="Changes = Yes, no description, no document",
                           expected_errors=[DESCRIBE_CHANGES, UPLOAD_DOCUMENT])

    @staticmethod
    def changes_without_document() -> RenewalData:
        return RenewalData(changes_made="yes", changes_details=CHANGES_TEXT, cases_pending="no", declare=True,
                           scenario_label="Changes = Yes with a description, no document",
                           expected_errors=[UPLOAD_DOCUMENT])

    @staticmethod
    def cases_without_details() -> RenewalData:
        return RenewalData(changes_made="no", cases_pending="yes", declare=True,
                           scenario_label="Cases = Yes, no details",
                           expected_errors=[DESCRIBE_CASES])

    @staticmethod
    def _with_document(file_name: str, error: str, label: str) -> RenewalData:
        return RenewalData(changes_made="yes", changes_details=CHANGES_TEXT, cases_pending="no",
                           document=str(DOCUMENTS / file_name), declare=True, scenario_label=label,
                           expected_errors=[error, UPLOAD_DOCUMENT])

    @classmethod
    def undersized_document(cls) -> RenewalData:
        return cls._with_document("signature_undersized.png", DOCUMENT_TOO_SMALL, "Document under 10 KB (72 B PNG)")

    @classmethod
    def oversized_document(cls) -> RenewalData:
        return cls._with_document("oversized.pdf", DOCUMENT_TOO_LARGE, "Document over 2 MB (3 MB PDF)")

    @classmethod
    def wrong_type_document(cls) -> RenewalData:
        return cls._with_document("certificate.docx", DOCUMENT_WRONG_TYPE, "Document of another type (.docx)")

    @classmethod
    def invalid_documents(cls) -> list[RenewalData]:
        return [cls.undersized_document(), cls.oversized_document(), cls.wrong_type_document()]

    # ── Officer decision ──────────────────────────────────────────────────────

    @staticmethod
    def approval() -> RenewalDecisionData:
        return RenewalDecisionData(decision="approve", remarks="Documents verified, no adverse report.",
                                   scenario_label="Approve with remarks")

    @staticmethod
    def rejection() -> RenewalDecisionData:
        return RenewalDecisionData(decision="reject",
                                   remarks="The agency did not submit the supporting documents asked for during "
                                           "verification.",
                                   scenario_label="Reject with reasons (30+ characters)")

    @staticmethod
    def short_approval() -> RenewalDecisionData:
        return RenewalDecisionData(decision="approve", remarks="ok", scenario_label="Approve, 2-character remarks",
                                   expected_error="Write at least 5 characters.")

    @staticmethod
    def short_rejection() -> RenewalDecisionData:
        return RenewalDecisionData(decision="reject", remarks="Too short", scenario_label="Reject, 9-character reasons",
                                   expected_error="Write at least 30 characters.")

    @staticmethod
    def dialog_remarks() -> RenewalDecisionData:
        """KAN-TC-838: remarks typed and then abandoned with Close / ×."""
        return RenewalDecisionData(decision="approve", remarks="Typed and then closed without confirming.",
                                   scenario_label="Remarks typed, dialog closed")

    # ── Officer scope (KAN-51 AC-13…15) ───────────────────────────────────────

    @staticmethod
    def scope_areas(rows: list[dict]) -> RenewalScope:
        """From the Super Administrator's All rows: the district with the most renewal applications, its
        division, and a district (of another division) with none."""
        from test_data.district_breakup_factory import DistrictBreakupFactory as D
        counts: dict[str, int] = {}
        for r in rows:
            if D.division_of(r["district"]):
                counts[r["district"]] = counts.get(r["district"], 0) + 1
        if not counts:
            return RenewalScope()
        district = max(counts, key=counts.get)
        division = D.division_of(district)
        empty = next(((dv, d) for dv, ds in D.DIVISIONS.items() if dv != division for d in ds if d not in counts),
                     ("", ""))
        return RenewalScope(district=district, division=division, empty_division=empty[0],
                            empty_district=empty[1], division_districts=D.DIVISIONS[division])
