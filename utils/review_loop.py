"""
Where an application stands in the desktop scrutiny review loop (KAN-12), kept in the state store
(``status_data.loop``). The review-loop tests, their fixtures and the map driver record each step here, so the
next test can find an application at the stage it needs.
"""

from pages.admin.application_review_page import ReviewStage
from test_data.application_review_factory import ReviewLoopFactory
from utils.state_store import TestStateStore, UserRecord

# Loop stage → the console's review step (Applications › Desktop scrutiny), for the state store
_CONSOLE_STEP = {ReviewStage.WITH_AGENCY: "with_agency", ReviewStage.HEARING_DUE: "show_cause"}


def record_loop_stage(agency: UserRecord, stage: str) -> None:
    """Records where ``agency``'s application now stands in the loop (``status_data.loop``)."""
    store = TestStateStore()
    if stage == ReviewStage.REFUSED:
        store.record_agency_status(username=agency.username, status="rejected",
                                   data={"seeded": "review_loop_tests", "reason": ReviewLoopFactory.loop().refusal_reason})
        return
    if stage == ReviewStage.APPROVED:
        store.record_agency_status(username=agency.username, status="approved",
                                   data={"seeded": "review_loop_tests", "path": "approved_after_compliance_1_reply"})
        return
    if stage == ReviewStage.PHYSICAL:
        store.record_agency_status(username=agency.username, status="physical_verification",
                                   data={"review": "under_review", "loop": stage})
        return
    store.record_agency_status(username=agency.username, status="desktop_scrutiny",
                               data={"review": _CONSOLE_STEP.get(stage, "under_review"), "loop": stage})
