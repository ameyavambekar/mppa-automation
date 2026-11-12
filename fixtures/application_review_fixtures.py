"""
Fixtures — desktop scrutiny review loop (KAN-12)
================================================
The officer side runs on the primary page, logged in as the Super Admin (``admin_review``); the agency side
on a second browser (``review_agency_session``).

Applications are found by where they stand in the loop. ``application_at(stage)`` takes the state-store
agencies in Desktop scrutiny, opens each review page and reads the stage from it (``ReviewStage``) — those
recorded at that stage (``status_data.loop``) are tried first. Each loop test moves one application one step
on and records the new stage, so a run of the chain (RUN_REVIEW_WORKFLOW_TESTS=true) takes one untouched
submission all the way to a refusal order — which then serves the First Appeal tests. Only agencies the state
store knows are touched.
"""

import os

import allure
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
from utils import failure_pages
from utils.review_loop import record_loop_stage
from utils.state_store import TestStateStore, UserRecord


def _review_view_ids(page, view: str, steps=(), application_ids=()) -> dict[str, int]:
    """Application ID → review page id for the applications listed in ``view`` (and its ``steps``). When a list
    fails to load — on dev any list holding an application given a post-hearing window does (06-Nov-2026) —
    each of ``application_ids`` is searched for by its ID instead."""
    applications = AdminApplicationsPage(page)
    ids, failed = {}, False
    for step in (None, *steps):
        applications.open(view, step)
        failed = failed or applications.load_error.count() > 0
        ids.update(applications.review_view_ids())
    if failed:
        for application_id in application_ids:
            if application_id and application_id not in ids:
                applications.open(view, query=application_id)
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
    """``find(*stages, after_hearing=None, accept=None, wanted="", required=True)
    -> (AdminApplicationReviewPage, UserRecord)``: opens the review page of a state-store agency's application
    standing at one of ``stages`` (``ReviewStage`` values) — in the second round of the loop (after the show
    cause notice) when ``after_hearing`` is True, the first when False. ``accept(agency) -> bool``, when given,
    is asked about each match and can pass it over (``wanted`` describes what it looks for, for the skip
    message). Skips when none is found — or returns None when ``required`` is False."""
    review = admin_review

    def find(*stages, after_hearing=None, accept=None, wanted="", required=True):
        candidates = TestStateStore().get_agency_users_in_status("desktop_scrutiny")
        ids = _review_view_ids(review.page, "desktop", AdminApplicationsPage.REVIEW_STEPS,
                               application_ids=[u.application_id for u in candidates])
        agencies = [u for u in candidates if u.application_id in ids]
        agencies.sort(key=lambda u: 0 if (u.status_data or {}).get("loop") in stages else 1)
        for agency in agencies:
            review.open(ids[agency.application_id])
            stage = review.stage()
            if stage in stages and (after_hearing is None or review.after_hearing() == after_hearing):
                if accept is None or accept(agency):
                    return review, agency
                continue
            if (agency.status_data or {}).get("loop") not in (None, stage):
                record_loop_stage(agency, stage)
        if not required:
            return None
        where =" / ".join(stages) + ("" if after_hearing is None else
                                      " after the hearing" if after_hearing else " before the hearing")
        where += f", {wanted}" if wanted else ""
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
def review_agency_session(second_browser, request):
    """``login(agency) -> page``: a second browser logged in as ``agency`` (on Home). Logs out and closes on
    teardown. (Session Management has its own ``agency_session``; this one takes the agency to log in.)"""
    opened = []

    def login(agency: UserRecord):
        browser = second_browser()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.set_default_timeout(30000)
        page = context.new_page()
        failure_pages.register(request.node, page, f"agency {agency.username}")
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


def _send_compliance_1(application_at, data: RefusalData) -> tuple[AdminApplicationReviewPage, UserRecord]:
    """Takes an untouched submission to Compliance 1 with ``data.hold_item`` On Hold — what TC-752 and TC-754
    do. Skips when there is no untouched submission."""
    review, agency = application_at(ReviewStage.NEW)
    with allure.step(f"Prepare: send Compliance 1 on {agency.username}'s application ({data.hold_item} On Hold)"):
        review.save_review_with_hold(data.hold_item, data.hold_reason, data.hold_remark)
        record_loop_stage(agency, ReviewStage.HELD)
        review.run_flow("deficiency")
        stage = review.stage()
        record_loop_stage(agency, stage)
        if stage != ReviewStage.WITH_AGENCY:
            pytest.fail(f"Sending Compliance 1 on {agency.username}'s application left it at '{stage}', "
                        f"not '{ReviewStage.WITH_AGENCY}'.")
    return review, agency


@pytest.fixture
def agency_with_corrections(application_at, review_agency_session, review_loop_data):
    """``open(after_hearing, open_items) -> (AgencyCorrectionsPage, AgencyHomePage, UserRecord,
    AdminApplicationReviewPage)`` for an application awaiting the agency — after Compliance 1 (``after_hearing``
    False) or in the window after the hearing (True). The agency is logged in on a second browser, on Home.

    The officer's page reads the same ("awaiting the agency") before and after the agency corrects its items,
    so the agency's Corrections page decides: ``open_items`` True wants an application with an item still to
    correct, False one whose items are all corrected and whose reply is not sent yet.

    Each run of the chain leaves one application with an item still to correct, and TC-758 corrects it. When
    none is left before the hearing, an untouched submission is taken to Compliance 1 here (irreversible, like
    the chain itself). The window after the hearing cannot be prepared that way, so that case skips."""

    def open_(after_hearing: bool, open_items: bool):
        sessions, passed_over = {}, []

        def accept(agency: UserRecord) -> bool:
            page = review_agency_session(agency)
            sessions[agency.username] = page
            corrections = AgencyCorrectionsPage(page)
            corrections.open()
            still_open = corrections.open_items()
            ok = bool(still_open) if open_items else (not still_open and corrections.reply_section.is_visible())
            if not ok:
                passed_over.append(f"{agency.username}: \"{corrections.subtitle.inner_text().strip()}\"")
            return ok

        wanted = "with an item still to correct" if open_items else "corrected, reply not sent"
        found = application_at(ReviewStage.WITH_AGENCY, after_hearing=after_hearing, accept=accept, wanted=wanted,
                               required=False)
        if found:
            review, agency = found
            page = sessions[agency.username]
        elif open_items and not after_hearing:
            review, agency = _send_compliance_1(application_at, review_loop_data)
            page = review_agency_session(agency)
        else:
            where = f"with_agency {'after' if after_hearing else 'before'} the hearing, {wanted}"
            seen = f" Passed over — {'; '.join(passed_over)}." if passed_over else ""
            pytest.skip(f"No state-store application at '{where}' in Desktop scrutiny.{seen} Run the earlier "
                        f"review-loop tests (RUN_REVIEW_WORKFLOW_TESTS=true) first.")
        home = AgencyHomePage(page)
        home.open()
        return AgencyCorrectionsPage(page), home, agency, review

    return open_
