"""
Fixtures — desktop scrutiny review loop (KAN-12)
================================================
The officer side runs on the primary page, logged in as the Super Admin (``admin_review``); the agency side
on a second browser (``agency_session``).

Applications are found by where they stand in the loop. ``application_at(stage)`` takes the state-store
agencies in Desktop scrutiny, opens each review page and reads the stage from it (``ReviewStage``) — those
recorded at that stage (``status_data.loop``) are tried first. Each loop test moves one application one step
on and records the new stage, so a run of the chain (RUN_REVIEW_WORKFLOW_TESTS=true) takes one untouched
submission all the way to a refusal order — which then serves the First Appeal tests. Only agencies the state
store knows are touched.
"""

import os

import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.admin.application_review_page import AdminApplicationReviewPage, ReviewStage
from pages.admin.applications_page import AdminApplicationsPage
from pages.agency_home_page import AgencyHomePage
from pages.corrections_page import AgencyCorrectionsPage
from pages.login_page import LoginPage
from test_data.application_review_factory import ReviewLoopFactory
from test_data.refusal_factory import RefusalData
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
    store.record_agency_status(username=agency.username, status="desktop_scrutiny",
                               data={"review": _CONSOLE_STEP.get(stage, "under_review"), "loop": stage})


def _review_view_ids(page, view: str, steps=()) -> dict[str, int]:
    applications = AdminApplicationsPage(page)
    ids = {}
    for step in (None, *steps):
        applications.open(view, step)
        ids.update(applications.review_view_ids())
    return ids


# ── Officer side ───────────────────────────────────────────────────────────────

@pytest.fixture
def admin_review(page) -> AdminApplicationReviewPage:
    """The application review page object on the primary page, logged in as the Super Admin; logs out on
    teardown."""
    _admin_login(page)
    yield AdminApplicationReviewPage(page)
    _admin_logout(page)


@pytest.fixture
def application_at(admin_review):
    """``find(*stages, after_hearing=None) -> (AdminApplicationReviewPage, UserRecord)``: opens the review page
    of a state-store agency's application standing at one of ``stages`` (``ReviewStage`` values) — in the
    second round of the loop (after the show cause notice) when ``after_hearing`` is True, the first when
    False. Skips when none is found."""
    review = admin_review

    def find(*stages, after_hearing=None):
        ids = _review_view_ids(review.page, "desktop", AdminApplicationsPage.REVIEW_STEPS)
        agencies = [u for u in TestStateStore().get_agency_users_in_status("desktop_scrutiny")
                    if u.application_id in ids]
        agencies.sort(key=lambda u: 0 if (u.status_data or {}).get("loop") in stages else 1)
        for agency in agencies:
            review.open(ids[agency.application_id])
            stage = review.stage()
            if stage in stages and (after_hearing is None or review.after_hearing() == after_hearing):
                return review, agency
            if (agency.status_data or {}).get("loop") not in (None, stage):
                record_loop_stage(agency, stage)
        where = " / ".join(stages) + ("" if after_hearing is None else
                                      " after the hearing" if after_hearing else " before the hearing")
        pytest.skip(f"No state-store application at '{where}' in Desktop scrutiny — run the earlier review-loop "
                    f"tests (RUN_REVIEW_WORKFLOW_TESTS=true) or submit a new application.")

    return find


@pytest.fixture
def new_application_review(application_at) -> tuple[AdminApplicationReviewPage, UserRecord]:
    """The review page of a state-store agency's application that nobody has reviewed yet."""
    return application_at(ReviewStage.NEW)


@pytest.fixture
def refused_application_review(admin_review) -> tuple[AdminApplicationReviewPage, UserRecord]:
    """The review page of a state-store agency's application refused at the end of the review loop (its
    history has a show cause notice) — e.g. one prepared by ``python -m utils.seed_appeals``."""
    review = admin_review
    ids = _review_view_ids(review.page, "rejected")
    store = TestStateStore()
    for agency in store.get_agency_users_in_status(["rejected", "first_appeal", "second_appeal"]):
        if agency.application_id not in ids:
            continue
        review.open(ids[agency.application_id])
        if review.stage() == ReviewStage.REFUSED and review.after_hearing():
            return review, agency
    pytest.skip("No state-store application refused through the review loop — run 'python -m utils.seed_appeals' "
                "(or the review-loop chain with RUN_REVIEW_WORKFLOW_TESTS=true) first.")


@pytest.fixture
def review_workflow_allowed():
    """Skips unless RUN_REVIEW_WORKFLOW_TESTS=true. Each review-loop step moves a real application on and cannot
    be undone; a full run takes one untouched submission to a refusal order."""
    if os.getenv("RUN_REVIEW_WORKFLOW_TESTS", "false").lower() != "true":
        pytest.skip("Moves an application through the review loop (irreversible) — set RUN_REVIEW_WORKFLOW_TESTS=true "
                    "to run.")


@pytest.fixture
def review_loop_data() -> RefusalData:
    return ReviewLoopFactory.loop()


# ── Agency side ────────────────────────────────────────────────────────────────

@pytest.fixture
def agency_session(second_browser):
    """``login(agency) -> page``: a second browser logged in as ``agency`` (on Home). Logs out and closes on
    teardown."""
    opened = []

    def login(agency: UserRecord):
        browser = second_browser()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.set_default_timeout(30000)
        page = context.new_page()
        opened.append((context, page))
        lp = LoginPage(page)
        lp.open()
        lp.login(agency.username, agency.password)
        page.wait_for_load_state("networkidle")
        if "login" in page.url:
            pytest.skip(f"Agency {agency.username} could not log in.")
        return page

    yield login
    for context, page in opened:
        try:
            page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        except Exception:
            pass
        context.close()


@pytest.fixture
def agency_with_corrections(application_at, agency_session):
    """``open(after_hearing) -> (AgencyCorrectionsPage, AgencyHomePage, UserRecord, AdminApplicationReviewPage)``
    for an application awaiting the agency's corrections — after Compliance 1 (``after_hearing`` False) or in
    the window after the hearing (True). The agency is logged in on a second browser, on Home."""

    def open_(after_hearing: bool):
        review, agency = application_at(ReviewStage.WITH_AGENCY, after_hearing=after_hearing)
        page = agency_session(agency)
        home = AgencyHomePage(page)
        return AgencyCorrectionsPage(page), home, agency, review

    return open_
