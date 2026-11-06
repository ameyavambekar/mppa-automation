"""
Data Factory — desktop scrutiny review loop (KAN-12)
====================================================
What the officer and the agency enter, and what the pages say, at each step of the review loop on
``/module/admin/dashboard/agency_view.php`` and the agency's Corrections page: review (Approve / On Hold) →
Compliance 1 → the agency corrects and replies → reply taken into review → show cause notice and hearing →
window to correct → the agency replies again → second reply into review → refusal order.

The happy-path texts are ``RefusalFactory.failed_correction()`` (the same loop prepares appeal test data);
this module adds the client-side checks and the texts the pages show. Texts as seen on dev, 05-Nov-2026.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from test_data.refusal_factory import RefusalData, RefusalFactory


@dataclass
class ReviewCheckData:
    """One attempt the page should refuse on the client: what is entered and the error expected."""
    item: str = "part_a"                  # review bar key
    choice: str = "on_hold"
    reason: str | None = None             # reason option value (None leaves it as it is)
    remark: str | None = None
    fields: dict = field(default_factory=dict)   # form fields for the show cause / refusal / reply checks
    scenario_label: str = ""
    expected_error: str | None = None
    expected_problem: str | None = None   # the review bar's own problem line


class ReviewLoopFactory:

    # ── Review page ───────────────────────────────────────────────────────────
    STAGE_UNDER_REVIEW = "Stage 1 — Desktop Scrutiny · Under review"
    TRACK = ["1. Review", "2. Compliance 1", "3. Compliance 2", "4. Decision"]
    CHOICES = ["approved", "on_hold"]
    HOLD_REASONS = ["Select the reason…", "Fee Shortfall / Wrong Tier Selected",
                    "Missing / Unclear Owner Identity Proof", "Invalid Entity Registration Papers",
                    "Missing Statutory Labour Licenses", "Invalid Office Address Proof",
                    "Bad / Unclear Geo-Tagged Photos", "Defective Self-Declaration",
                    "Incomplete Application Form Details", "Others (free text remarks required)"]
    REMARK_PLACEHOLDER = "Details for the agency (required for Others — at least 50 characters)"
    REMARK_MAX = 1000
    ALL_SAVED = "All changes saved"
    HOLD_SAVE_ERROR = "On Hold needs a reason"
    FLOW_BLOCKED_TITLE = "Save your review first"
    FLOW_BLOCKED_ERROR = "Save your review first, then continue."
    NEXT_ITEMS = ["part_c", "part_f"]       # items marked without saving in the unsaved-changes checks

    # ── Compliance 1 ──────────────────────────────────────────────────────────
    SEND_C1 = "Send Compliance 1 (1)"
    C1_CONFIRM = "Send Compliance 1 (deficiency notice) for 1 item(s)? The agency gets 15 working days."
    C1_HISTORY = ("Compliance 1 — deficiency notice issued for 1 item(s). Correct them and reply within 15 working "
                  "days. The 45-day clock is paused until you reply.")
    AWAITING_AGENCY = "— awaiting the agency."
    HOLD_ITEM_LABEL = "Part A — Agency details"
    AWAITING_BADGE = "Awaiting agency"

    # ── Agency side ───────────────────────────────────────────────────────────
    HOME_ACTION_REQUIRED = "Action required: the officer has asked for corrections"
    HOME_STAGE_C1 = "Compliance 1 — deficiency notice, awaiting reply"
    HOME_CLOCK_PAUSED = "45-day clock paused (Rule 4(4))"
    CORR_OPEN_BADGE = "Correction needed"
    CORR_DONE_BADGE = "Corrected"
    CORR_LOCKED = "Submitted and locked. This item can no longer be changed."
    CORR_SAVE_CONFIRM = "Save these corrections? After saving, this section is locked and cannot be edited again."
    CORR_ALL_DONE = "All items corrected — send your reply below"
    REPLY_CONFIRM = "Submit your corrections and reply to the officer? You cannot change anything after this."
    REPLY_SENT = "Your corrections and reply have been submitted — the officer is reviewing them."
    # The reply box has minlength="10": the browser blocks the submit ("Please lengthen this text to 10
    # characters or more …" in Chrome) before the page's own "Please write at least 10 characters." toast.
    REPLY_TOO_SHORT = "10 characters"

    # ── Reply into review, show cause, window ─────────────────────────────────
    TAKE_REPLY = "Take reply into review"
    ACCEPT_REPLY_1 = "Reply to Compliance 1 received — review the corrected items again."
    ACCEPT_REPLY_2 = ("Post-hearing reply received — review the corrected items, then approve or issue the speaking "
                      "refusal order.")
    SCN_CONFIRM = "Issue the show cause notice and schedule a personal hearing?"
    SCN_HISTORY = "Compliance 2 — pre-refusal show cause notice (Sec 4(3) proviso). You must appear IN PERSON"
    SCN_GROUND_LABEL = "Inadequate / Unsatisfactory Rectification"
    WINDOW_CONFIRM = "Give the agency access to correct the items on hold again?"
    WINDOW_DAYS = ["3", "4", "5", "6", "7"]

    # ── Refusal ───────────────────────────────────────────────────────────────
    REFUSE_CONFIRM = "Issue the speaking REFUSAL ORDER? The agency can file a First Appeal."
    REFUSE_HISTORY = ("Speaking refusal order issued (Sec 4(3)(b), Rule 4(8)). You may file a First Appeal to the "
                      "Divisional Appellate Authority within 60 days.")
    REFUSED_STAGE = RefusalFactory.REFUSED_STAGE
    REJECTED_BADGE = "Rejected"       # shown upper-case by CSS
    READ_ONLY = "Read only. This application is rejected."
    LOOP_HISTORY = ["Submitted", "Deficiency", "Agency Reply", "Accept Reply", "Scn Hearing", "Grant Window",
                    "Agency Reply", "Accept Reply", "Division Report", "Refuse"]

    # ── Approval after the reply to Compliance 1 ──────────────────────────────
    # Texts as seen on dev, 06-Nov-2026
    APPROVE_DESKTOP_CONFIRM = ("All items are approved. Clear Desktop Scrutiny and move the application to Physical "
                               "Verification?")
    DESKTOP_CLEARED = "Desktop scrutiny cleared — application moved to Physical Verification."
    HEAD_OFFICE_VERIFIED_CONFIRM = "Mark Head office as physically verified?"
    HEAD_OFFICE_VERIFIED = "physically verified."          # "Head office (<district>) physically verified."
    FINAL_APPROVAL_CONFIRM = "Give FINAL APPROVAL and issue the Form-II registration certificate?"
    APPROVED_STAGE = "Approved — Certificate Issued · Closed"

    @staticmethod
    def certificate_issued(application_id: str) -> str:
        """The final "Clear" history entry — the registration number is the Application ID."""
        return (f"Physical verification cleared — Form-II registration certificate issued (Registration No. "
                f"{application_id}).")

    @staticmethod
    def loop() -> RefusalData:
        """Part A On Hold through the whole loop, refused at the end (also used to seed appeal data)."""
        return RefusalFactory.failed_correction()

    # ── Client-side checks ────────────────────────────────────────────────────

    @staticmethod
    def hold_without_reason() -> ReviewCheckData:
        return ReviewCheckData(choice="on_hold", reason="", scenario_label="on_hold_without_reason",
                               expected_problem="Select a reason",
                               expected_error=ReviewLoopFactory.HOLD_SAVE_ERROR)

    @staticmethod
    def others_short_remark() -> ReviewCheckData:
        remark = "QA short note."
        return ReviewCheckData(choice="on_hold", reason="others", remark=remark,
                               scenario_label="others_remark_under_50",
                               expected_problem=f"Others: write at least 50 characters ({len(remark)}/50)",
                               expected_error="at least 50 characters")

    @staticmethod
    def unchanged_without_note() -> ReviewCheckData:
        return ReviewCheckData(fields={"note": ""}, scenario_label="correction_unchanged_without_note")

    @staticmethod
    def short_reply() -> ReviewCheckData:
        return ReviewCheckData(fields={"text": "Short"}, scenario_label="reply_under_10_characters",
                               expected_error=ReviewLoopFactory.REPLY_TOO_SHORT)

    @staticmethod
    def show_cause_checks() -> list[ReviewCheckData]:
        """Show cause form attempts the page refuses, in order: no ground, details too short, no hearing time."""
        grounds = RefusalFactory.failed_correction().scn_grounds
        return [
            ReviewCheckData(fields={"reason": "", "grounds": grounds, "minutes_ahead": 30},
                            scenario_label="scn_without_ground",
                            expected_error="Select the ground of the show cause notice."),
            ReviewCheckData(fields={"reason": "inadequate_reply", "grounds": "Too short.", "minutes_ahead": 30},
                            scenario_label="scn_details_under_20",
                            expected_error="Write the details of the notice (at least 20 characters)."),
            ReviewCheckData(fields={"reason": "inadequate_reply", "grounds": grounds, "minutes_ahead": None},
                            scenario_label="scn_without_hearing_time",
                            expected_error="Choose the hearing date and time."),
        ]

    @staticmethod
    def refusal_checks() -> list[ReviewCheckData]:
        """Refusal form attempts the page refuses, in order: no ground, speaking order under 100 characters,
        Division report under 20 characters."""
        r = RefusalFactory.failed_correction()
        short_order = "QA automation: speaking order that is far too short to be valid."
        return [
            ReviewCheckData(fields={"reason": "", "speaking_order": r.speaking_order, "division_note": r.division_note},
                            scenario_label="refusal_without_ground", expected_error="Select the ground of refusal."),
            ReviewCheckData(fields={"reason": r.refusal_reason, "speaking_order": short_order,
                                    "division_note": r.division_note},
                            scenario_label="speaking_order_under_100",
                            expected_error=f"The speaking order needs at least 100 characters ({len(short_order)} "
                                           f"written)."),
            ReviewCheckData(fields={"reason": r.refusal_reason, "speaking_order": r.speaking_order,
                                    "division_note": "Short note."},
                            scenario_label="division_note_under_20",
                            expected_error="Write the report for the Divisional Officer (at least 20 characters)."),
        ]
