"""
Data Factory — MPPA Compliance & Appeals Map
============================================
Every state an application can stand in on the map (Procedure 1: desktop scrutiny and compliance, C1–C10 and
the approval branch; Procedure 2: First and Second Appeal, A1–A6), how to get an untouched submission there
(``path``: the actions ``utils.map_states.MapStateDriver`` runs, in order) and what each side should see once
it is there.

Each state has one agency-side check and one officer-side check. Compliance states (``procedure ==
"Compliance"``: C1–C10 and the approval branch) are tested with the review loop in
``tests/admin/test_application_review.py`` (agency side KAN-48, officer side KAN-12); appeal states (A3–A6) in
``tests/test_appeals_map.py`` (KAN-49) and ``tests/admin/test_appeals_map.py`` (KAN-50). A state's agency is
generated once and parked there (state store ``map_state``), so both checks — and anyone looking for "an agency at
state X" — find it again.

Texts as seen on dev, 06-Nov-2026, where an agency was at that state; the rest (marked ``documented``) follow
the portal's own wording for the step (the appellate order's effect text, KAN-15 / KAN-30) and are confirmed by
the first generating run.
"""

from __future__ import annotations

from dataclasses import dataclass

from pages.admin.application_review_page import ReviewStage

# ── Paths: actions from an untouched submission (MapStateDriver.ACTIONS) ──────────
_C1 = ("hold", "send_c1")
_C1_CORRECTED = _C1 + ("correct",)
_C1_REPLIED = _C1_CORRECTED + ("reply",)
_SCN_DUE = _C1_REPLIED + ("take_reply_hold",)
_HEARING = _SCN_DUE + ("show_cause",)
_WINDOW = _HEARING + ("window",)
_W_CORRECTED = _WINDOW + ("correct",)
_W_REPLIED = _W_CORRECTED + ("reply",)
_REFUSAL_DUE = _W_REPLIED + ("take_reply_hold",)
_REFUSED = _REFUSAL_DUE + ("refuse",)
_FIRST_APPEAL = _REFUSED + ("file_first_appeal",)
_FIRST_DISMISSED = _FIRST_APPEAL + ("decide_first:dismissed_upheld",)
_SECOND_APPEAL = _FIRST_DISMISSED + ("file_second_appeal",)
_APPROVAL = ("approve_all", "approve_desktop")


@dataclass(frozen=True)
class MapState:
    key: str
    step: str                       # where it is on the map: "C3", "A5" …
    title: str
    path: tuple[str, ...]           # MapStateDriver actions from an untouched submission
    status: str                     # state-store agency_status once there
    review: str | None = None       # status_data["review"] (Applications › Desktop scrutiny step)
    loop: str | None = None         # ReviewStage the officer's review page shows
    after_hearing: bool | None = None
    branches: int = 0               # branch offices the submission needs
    appeal: str | None = None       # "first" / "second": the appeal this state is about
    disposal: str | None = None     # appellate order passed at this state

    @property
    def procedure(self) -> str:
        return "Compliance" if self.step.startswith("C") else "Appeals"


def _s(key, step, title, path, status, **kw) -> MapState:
    return MapState(key=key, step=step, title=title, path=path, status=status, **kw)


MAP_STATES: dict[str, MapState] = {s.key: s for s in (
    # ── Procedure 1 — desktop scrutiny and compliance ───────────────────────────
    _s("submitted", "C1", "Submitted, not reviewed yet", (), "desktop_scrutiny",
       review="under_review", loop=ReviewStage.NEW),
    _s("review_held", "C2", "Review saved with an item On Hold (Compliance 1 not sent)", ("hold",),
       "desktop_scrutiny", review="under_review", loop=ReviewStage.HELD),
    _s("review_all_approved", "C2", "Review saved with every item approved", ("approve_all",), "desktop_scrutiny",
       review="under_review", loop=ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=False),
    _s("compliance_1_sent", "C3", "Compliance 1 (deficiency notice) sent — items to correct", _C1,
       "desktop_scrutiny", review="with_agency", loop=ReviewStage.WITH_AGENCY, after_hearing=False),
    _s("compliance_1_corrected", "C4", "Items corrected, reply not sent", _C1_CORRECTED, "desktop_scrutiny",
       review="with_agency", loop=ReviewStage.WITH_AGENCY, after_hearing=False),
    _s("compliance_1_replied", "C4", "Reply to Compliance 1 sent", _C1_REPLIED, "desktop_scrutiny",
       review="with_agency", loop=ReviewStage.REPLY_RECEIVED, after_hearing=False),
    _s("show_cause_due", "C5", "Reply reviewed, item still On Hold — show cause form", _SCN_DUE,
       "desktop_scrutiny", loop=ReviewStage.SHOW_CAUSE_DUE, after_hearing=False),
    _s("compliance_1_cured", "C5", "Reply reviewed, every item approved", _C1_REPLIED + ("take_reply_approve",),
       "desktop_scrutiny", loop=ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=False),
    _s("hearing_scheduled", "C6", "Compliance 2 — show cause notice issued, hearing scheduled", _HEARING,
       "desktop_scrutiny", review="show_cause", loop=ReviewStage.HEARING_DUE, after_hearing=True),
    _s("window_open", "C7", "Hearing recorded, window to correct given", _WINDOW, "desktop_scrutiny",
       review="show_cause", loop=ReviewStage.WITH_AGENCY, after_hearing=True),
    _s("window_corrected", "C8", "Items corrected again, reply not sent", _W_CORRECTED, "desktop_scrutiny",
       review="show_cause", loop=ReviewStage.WITH_AGENCY, after_hearing=True),
    _s("window_replied", "C8", "Second reply sent", _W_REPLIED, "desktop_scrutiny",
       loop=ReviewStage.REPLY_RECEIVED, after_hearing=True),
    _s("refusal_due", "C9", "Second reply reviewed, item still On Hold — refusal form", _REFUSAL_DUE,
       "desktop_scrutiny", loop=ReviewStage.REFUSAL_DUE, after_hearing=True),
    _s("window_cured", "C9", "Second reply reviewed, every item approved", _W_REPLIED + ("take_reply_approve",),
       "desktop_scrutiny", loop=ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=True),
    _s("refused", "C10", "Refusal order passed", _REFUSED, "rejected", loop=ReviewStage.REFUSED),
    # ── Approval branch ─────────────────────────────────────────────────────────
    _s("physical_verification", "C2+", "Desktop scrutiny cleared — Stage 2, Physical Verification", _APPROVAL,
       "physical_verification", review="under_review", loop=ReviewStage.PHYSICAL),
    _s("branch_verification", "C2+", "Head office verified — branch office verification",
       _APPROVAL + ("verify_head_office",), "branch_verification", review="under_review",
       loop=ReviewStage.PHYSICAL, branches=1),
    _s("approved", "C2+", "Final approval — Form-II certificate issued",
       _APPROVAL + ("verify_offices", "final_approval"), "approved", loop=ReviewStage.APPROVED),
    # ── Procedure 2 — First and Second Appeal ───────────────────────────────────
    _s("first_appeal_pending", "A3", "First Appeal (FORM-III) filed, pending decision", _FIRST_APPEAL,
       "first_appeal", appeal="first"),
    _s("first_appeal_hearing", "A4", "First Appeal hearing scheduled", _FIRST_APPEAL + ("first_hearing",),
       "first_appeal", appeal="first"),
    _s("first_appeal_allowed", "A5", "First Appeal allowed — order set aside", _FIRST_APPEAL + ("decide_first:allowed",),
       "approved", appeal="first", disposal="allowed"),
    _s("first_appeal_allowed_conditions", "A5", "First Appeal allowed with conditions",
       _FIRST_APPEAL + ("decide_first:allowed_conditions",), "approved", appeal="first",
       disposal="allowed_conditions"),
    _s("first_appeal_remanded", "A5", "First Appeal remanded for re-scrutiny", _FIRST_APPEAL + ("decide_first:remanded",),
       "desktop_scrutiny", appeal="first", disposal="remanded"),
    _s("first_appeal_dismissed", "A5", "First Appeal dismissed — refusal upheld", _FIRST_DISMISSED, "first_appeal",
       appeal="first", disposal="dismissed_upheld"),
    _s("first_appeal_dismissed_default", "A5", "First Appeal dismissed for default of appearance",
       _FIRST_APPEAL + ("decide_first:dismissed_default",), "first_appeal", appeal="first",
       disposal="dismissed_default"),
    _s("first_appeal_delay_rejected", "A5", "First Appeal rejected for delay — case closed",
       _FIRST_APPEAL + ("decide_first:delay_rejected",), "first_appeal", appeal="first",
       disposal="delay_rejected"),
    _s("second_appeal_pending", "A6", "Second Appeal (FORM-IV) filed, pending decision", _SECOND_APPEAL,
       "second_appeal", appeal="second"),
    _s("second_appeal_decided", "A6", "Second appellate order passed — final dismissal",
       _SECOND_APPEAL + ("decide_second:final_dismissal",), "second_appeal", appeal="second",
       disposal="final_dismissal"),
)}


class ComplianceMapFactory:
    """What each side sees at a map state. Texts as seen on dev, 06-Nov-2026, unless marked documented."""

    STATES = MAP_STATES

    # ── Agency — Home ──────────────────────────────────────────────────────────
    BADGE_UNDER_REVIEW = "Under review"
    BADGE_REFUSED = "Refused"
    BADGE_REGISTERED = "Registered"
    NEXT_UNDER_REVIEW_1 = "Your application is under review — Stage 1 — Desktop Scrutiny"
    NEXT_UNDER_REVIEW_2 = "Your application is under review — Stage 2 — Physical Verification"
    NEXT_REPLY_WITH_OFFICER = "Your reply is with the officer"
    NEXT_HEARING = "Show cause hearing on "                 # + "<dd Mon yyyy, hh:mm AM>"
    NEXT_REFUSED = "Your application was refused"
    NEXT_REGISTERED = "Your agency is registered"
    PROGRESS_UNDER_REVIEW_1 = "Stage 1 — Desktop Scrutiny · Under review"
    PROGRESS_C1 = "Stage 1 — Desktop Scrutiny · Compliance 1 — deficiency notice, awaiting reply"
    PROGRESS_C2_HEARING = "Stage 1 — Desktop Scrutiny · Compliance 2 — show cause notice & hearing scheduled"
    PROGRESS_STAGE_2 = "Stage 2 — Physical Verification · Under review"
    PROGRESS_REFUSED = "Refused · Closed"
    PROGRESS_APPROVED = "Approved — Certificate Issued · Closed"
    ACTION_REQUIRED = "Action required: the officer has asked for corrections"
    CLOCK_PAUSED = "45-day clock paused (Rule 4(4))"
    TIMELINE_C1 = "Compliance 1 — deficiency notice"
    TIMELINE_REPLY = "Your reply sent"
    TIMELINE_REPLY_TAKEN = "Reply taken into review"
    TIMELINE_SCN = "Compliance 2 — show cause notice & hearing"
    TIMELINE_WINDOW = "Post-hearing window granted"
    TIMELINE_REFUSED = "Refusal order issued"
    TIMELINE_STAGE_CLEARED = "Stage cleared"
    TIMELINE_OFFICE_VERIFIED = "Office verified"
    TIMELINE_APPEAL_FILED = "Appeal filed"
    TIMELINE_APPEAL_DISMISSED = "Appeal dismissed"
    DESKTOP_CLEARED = "Desktop scrutiny cleared — application moved to Physical Verification."
    HEAD_OFFICE_VERIFIED = "physically verified."
    HEARING_IN_PERSON = "(in person — attendance is compulsory)"
    NEXT_APPEAL_HEARING = "Appeal hearing on "               # + "<dd Mon yyyy, hh:mm AM> — in person"
    APPEAL_HEARING_IN_PERSON = "— in person"
    APPEAR_AT = "Appear at: "                               # + the venue
    APPEAL_HEARING_TITLE = "Appeal hearing"
    APPEAL_HEARING_MODE = "In-person hearing"
    WINDOW_NOTE = "Hearing held — agency attended. You have 3 days to correct the items below and reply by"
    REMAINING = "{n} of 2 appeals remaining"
    APPEAL_FILED = "First Appeal #{n} filed — sent to "
    APPEAL_DISMISSED = "First Appeal #{n} DISMISSED (Order FAA/{year}/{n})."

    # ── Agency — My Application and Corrections ───────────────────────────────
    MY_APP_SUBMITTED = "SUBMITTED"
    MY_APP_REJECTED = "REJECTED"
    MY_APP_APPROVED = "APPROVED"
    CORR_NONE = "There are no corrections requested for your application."
    CORR_CLOSED = "This round of corrections is closed."
    CORR_NEEDED = "Correction needed"
    CORR_ALL_DONE = "All items corrected — send your reply below"
    CORR_REPLY_SENT = "Your corrections and reply have been submitted — the officer is reviewing them."
    HOLD_ITEM_LABEL = "Part A — Agency details"

    # ── Agency — FORM-III / FORM-IV journey ───────────────────────────────────
    STEP_FIRST = "First Appeal · Division"
    STEP_SECOND = "Second Appeal · Commissionerate"
    JOURNEY_NOT_FILED = "— Not filed"
    JOURNEY_PENDING = "Pending decision"
    JOURNEY_REJECTED = "Rejected"
    APPEALS_REMAINING = "Appeals remaining: {n} of 2"
    SECOND_BEFORE_FIRST = ("Please file your First Appeal (FORM-III) first. A Second Appeal is possible only after "
                           "the First Appeal is decided and rejected.")
    SECOND_WHILE_PENDING = "Your First Appeal #{n} is still pending. You can file a Second Appeal only if it is rejected."
    FAA_ORDER = "FAA/{year}/{n}"

    # ── Officer ────────────────────────────────────────────────────────────────
    STAGE_UNDER_REVIEW = "Stage 1 — Desktop Scrutiny · Under review"
    STAGE_C2_HEARING = PROGRESS_C2_HEARING
    STAGE_2 = "Stage 2 — Physical Verification"
    APPROVED_STAGE = PROGRESS_APPROVED
    AWAITING_AGENCY = "— awaiting the agency."
    TAKE_REPLY = "Take reply into review"
    SEND_C1 = "Send Compliance 1"
    BRANCH_ROW = "Branch 1 — "                                # Applications › Branch office verification
    APPEAL_PENDING = "Pending"
    APPEAL_HEARING_STAGE = "Hearing stage"                  # row status once the appeal hearing is scheduled
    # documented — the order's effect, as the page shows it under the disposal select (AppealOutcomeFactory.IMPACT)
    ORDER_EFFECT = {
        "allowed": "approved",                 # "Status becomes APPROVED and the certificate is issued."
        "allowed_conditions": "approved",      # "Approved; … comply with the conditions … within 15 days."
        "remanded": "desktop_scrutiny",        # "Case sent back to the District to re-evaluate …"
        "dismissed_upheld": "rejected",        # "District refusal confirmed. Opens the 60-day window …"
        "dismissed_default": "rejected",
        "delay_rejected": "rejected",          # "… Case permanently closed."
        "final_dismissal": "rejected",         # "Second Appeal rejected. Case closed permanently under Sec 7(3)."
    }

    @staticmethod
    def state(key: str) -> MapState:
        return MAP_STATES[key]
