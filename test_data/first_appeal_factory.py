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

    # Page texts (KAN-14)
    TAB_TITLE = "First Appeal — FORM-III | Placement Agency Regulation Portal"
    BREADCRUMB = "Home › My Application › First Appeal (FORM-III)"
    HEADING = "First Appeal — Divisional Level"
    HEADER_LINES = ["To be decided by the Divisional Appellate Authority",
                    "Under Section 7(1) of the Maharashtra Private Placement Agencies (Regulation) Act, 2025"]
    TWO_APPEALS_NOTE = ("You can file only TWO appeals in total — one First Appeal and, only if it is rejected, one "
                        "Second Appeal. The decision on the Second Appeal is final.")
    ADDRESSEE = ("To, The First Appellate Authority, Deputy Commissioner, Skill Development, Employment & "
                 "Entrepreneurship, {district} District, Maharashtra.")
    SUBJECT = "Subject: Appeal against the order of the Registering Authority — Registering Authority, {district} District"
    DECLARATION = ("I verify that the facts stated above are true and correct to the best of my knowledge and belief. "
                   "I understand that I can file only two appeals in total, and that a false or frivolous appeal is an "
                   "offence under the Act.")
    SUBMIT_LABEL = "Submit First Appeal to the Division (FORM-III)"
    SUBMITTED = ("Your First Appeal (FORM-III) #{n} has been submitted to the reviewing authority. A confirmation "
                 "e-mail with all details has been sent to you.")
    NOT_REJECTED = ("An appeal can be filed only when your application has been rejected by the Registering "
                    "Authority. Your application status is {status}.")
    SECOND_BEFORE_FIRST = ("Please file your First Appeal (FORM-III) first. A Second Appeal is possible only after "
                           "the First Appeal is decided and rejected.")
    SECOND_WHILE_PENDING = "Your First Appeal #{n} is still pending. You can file a Second Appeal only if it is rejected."
    DECISION_DAYS = 60
    OTHER_MAX = 300
    FACTS_MIN = 20
    RELIEF_MIN = 10
    # Home › Appeals card and My Application
    HOME_REMAINING = "{n} of 2 appeals remaining"
    HOME_FILE_HINT = ("File your appeal to the Divisional Appellate Authority within 60 days of the order. Only two "
                      "appeals are allowed in total.")
    HOME_PENDING_HINT = "Your appeal is with the authority. You will be informed here and by e-mail."
    HOME_PENDING_BADGE = "Pending — decision by {date}"
    MY_APP_INVITE = "Review admin remarks below and file an appeal if needed."

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

    @staticmethod
    def oversized_order(oversized_path: str) -> FirstAppealData:
        """The required order itself is over 2 MB — the page refuses to submit."""
        data = FirstAppealFactory.valid_order_only(oversized_path)
        data.scenario_label = "oversized_order"
        data.expected_error = FirstAppealFactory.TOO_LARGE_ALERT
        return data

    @staticmethod
    def other_ground_blank(file_path: str) -> FirstAppealData:
        """'Other' ticked with nothing specified — must be refused (defect "I & II Appeal" #65: it is not)."""
        data = FirstAppealFactory.other_ground(file_path)
        data.grounds_other = ""
        data.scenario_label = "other_ground_blank"
        return data

    @staticmethod
    def other_ground_too_long() -> str:
        """301 characters for 'Specify other ground' (limit 300)."""
        return ("QA automation other ground " * 12)[:FirstAppealFactory.OTHER_MAX + 1]

    @staticmethod
    def brief_facts_of_length(file_path: str, length: int) -> FirstAppealData:
        """A valid appeal whose Brief Facts are exactly ``length`` characters (minimum 20)."""
        data = FirstAppealFactory.valid_order_only(file_path)
        data.brief_facts = "QA automation facts, appeal test data only"[:length]
        data.scenario_label = f"brief_facts_{length}_chars"
        return data

    @staticmethod
    def relief_of_length(file_path: str, length: int) -> FirstAppealData:
        """A valid appeal whose relief text is exactly ``length`` characters (minimum 10)."""
        data = FirstAppealFactory.valid_order_only(file_path)
        data.relief_sought = "QA-relief-sought-test"[:length]
        data.scenario_label = f"relief_{length}_chars"
        return data

    @staticmethod
    def invalid_order_document(path: str, label: str) -> FirstAppealData:
        """A valid appeal whose required order is not an acceptable PDF (a .docx, an empty file) — the
        portal must refuse it."""
        data = FirstAppealFactory.valid_order_only(path)
        data.scenario_label = label
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

    # Reasons for each appellate order (first or second appeal), each well over the 50-character minimum
    _ORDER_REASONS = {
        "allowed": "the refusal order did not consider the corrected Part A details already on record, so it "
                   "is set aside and the application is to be approved.",
        "allowed_conditions": "the application is approved on condition that the agency files its updated Part A "
                              "details with the Registering Authority within 15 days.",
        "remanded": "the record does not show a fresh verification of Part A; the case is sent back to the "
                    "District for re-scrutiny after a paper verification.",
        "dismissed_upheld": "the appellant's grounds were examined against the record; the Part A deficiency "
                            "named in the refusal order was not cured, so the refusal stands.",
        "dismissed_default": "the appellant did not appear for the hearing on the date fixed and gave no valid "
                             "reason for the absence, so the appeal is dismissed for default.",
        "delay_rejected": "the appeal was filed beyond the limitation period without sufficient cause for the "
                          "delay; condonation is refused and the case is closed.",
        "final_dismissal": "the grounds raised against the First Appellate order are not made out on the record; "
                           "the Second Appeal is dismissed and the case is closed under Sec 7(3).",
    }

    @staticmethod
    def order(disposal: str) -> AppealOutcomeData:
        """The appellate order ``disposal`` (a FIRST_DISPOSALS or SECOND_DISPOSALS value) with its reasons."""
        reasons = f"QA automation appellate order (map test data): {AppealOutcomeFactory._ORDER_REASONS[disposal]}"
        return AppealOutcomeData(disposal=disposal, reasons=reasons, scenario_label=disposal)


class SecondAppealFactory:
    """Builds FORM-IV filing payloads (``FirstAppealData`` with ``SecondAppealPage.DOC_SLOTS`` documents).
    Texts as seen on dev, 06-Nov-2026 and 13-Nov-2026 (KAN-15 cases, now linked to KAN-49)."""

    SUBMIT_LABEL = "Submit Second — and final — Appeal to the Commissionerate (FORM-IV)"
    HEADING = "Second Appeal — Commissionerate (State) Level"
    ADDRESSEE = ("To, The Second Appellate Authority, Commissioner, Skill Development, Employment & "
                 "Entrepreneurship, Maharashtra State, Maharashtra.")
    SUBJECT = "Subject: Appeal against the order of the First Appellate Authority — {authority}"
    TAB_TITLE = "Second Appeal — FORM-IV | Placement Agency Regulation Portal"
    BREADCRUMB = r"Home\s*›\s*My Application\s*›\s*Second Appeal \(FORM-IV\)"
    FORM_BADGE = "FORM-IV · See Rule 6(10)"
    HEADER_LINES = ["To be decided by the Commissionerate (Second Appellate Authority)",
                    "Under Section 7(2) of the Maharashtra Private Placement Agencies (Regulation) Act, 2025"]
    CONFIRM = "Submit your SECOND and FINAL appeal?\n\nNo further appeal will be possible after this one."
    SENT_TO = "Commissioner, Skill Development, Employment & Entrepreneurship, Maharashtra State"
    FIRST_AUTHORITY = "Deputy Commissioner, Skill Development, Employment & Entrepreneurship, {district} District"
    DECIDED_FINAL = ("Your Second Appeal was rejected. This decision is final and no further appeal can be filed on "
                     "the portal.")
    BRIEF_FACTS_PLACEHOLDER = "Concise narration of the relevant facts, including why the First Appellate order is incorrect…"
    # Home › Appeals card
    HOME_FILE_HINT = "Your First Appeal was dismissed. You can file the Second (final) Appeal."
    HOME_FILE_LINK = "File Second Appeal"
    HOME_VIEW_LINK = "View Second Appeal"
    DOC_LABELS = {
        "ra_order": "(b) Order of the Registering Authority",
        "fa1_order": "(c) Order of the First Appellate Authority",
        "other": "(d) Any other document",
    }
    REQUIRED_SLOTS = ("ra_order", "fa1_order")

    @staticmethod
    def valid_required_documents(file_path: str) -> FirstAppealData:
        """A complete Second Appeal with only the two required documents, (b) and (c)."""
        return FirstAppealData(
            grounds=["error_of_law"],
            brief_facts="QA automation (second appeal test data): the First Appellate Authority did not deal with "
                        "the corrected Part A details placed on record.",
            relief_type="Remand for Fresh Consideration",
            relief_sought="Remand the matter for fresh consideration (QA automation).",
            documents={slot: file_path for slot in SecondAppealFactory.REQUIRED_SLOTS},
            scenario_label="second_appeal_required_documents",
        )

    @staticmethod
    def no_ground(file_path: str) -> FirstAppealData:
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.grounds = []
        data.scenario_label = "second_appeal_no_ground"
        data.expected_error = FirstAppealFactory.NO_GROUND_ALERT
        return data

    @staticmethod
    def other_ground_blank(file_path: str) -> FirstAppealData:
        """'Other' ticked with nothing specified — must be refused."""
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.grounds, data.grounds_other = ["other"], ""
        data.scenario_label = "second_appeal_other_ground_blank"
        return data

    @staticmethod
    def without_document(file_path: str, slot: str) -> FirstAppealData:
        """A complete Second Appeal missing the required document ``slot`` ('ra_order' or 'fa1_order')."""
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.documents.pop(slot)
        data.scenario_label = f"second_appeal_without_{slot}"
        return data

    @staticmethod
    def brief_facts_of_length(file_path: str, length: int) -> FirstAppealData:
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.brief_facts = "QA automation facts, appeal test data only"[:length]
        data.scenario_label = f"second_appeal_brief_facts_{length}_chars"
        return data

    @staticmethod
    def relief_of_length(file_path: str, length: int) -> FirstAppealData:
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.relief_sought = "QA-relief-sought-test"[:length]
        data.scenario_label = f"second_appeal_relief_{length}_chars"
        return data

    @staticmethod
    def oversized(file_path: str, oversized_path: str, slot: str) -> FirstAppealData:
        """A PDF over 2 MB in ``slot`` — the page refuses to submit."""
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.documents[slot] = oversized_path
        data.scenario_label = f"second_appeal_oversized_{slot}"
        data.expected_error = FirstAppealFactory.TOO_LARGE_ALERT
        return data

    @staticmethod
    def invalid_document(file_path: str, bad_path: str, label: str) -> FirstAppealData:
        """A complete Second Appeal whose (b) document is not an acceptable PDF — the portal must refuse it."""
        data = SecondAppealFactory.valid_required_documents(file_path)
        data.documents["ra_order"] = bad_path
        data.scenario_label = label
        return data

    @staticmethod
    def valid_with_documents(file_path: str) -> FirstAppealData:
        """A complete Second Appeal with all three documents (``file_path`` reused for every slot)."""
        return FirstAppealData(
            grounds=["non_consideration", "natural_justice"],
            brief_facts="QA automation (map test data): the First Appellate Authority upheld the refusal without "
                        "considering the corrected Part A details placed on record with the First Appeal.",
            relief_type="Setting Aside the Order",
            relief_sought="Set aside the First Appellate order and the refusal, and direct registration (QA automation).",
            documents={slot: file_path for slot in ("ra_order", "fa1_order", "other")},
            scenario_label="second_appeal_valid_with_documents",
        )

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
