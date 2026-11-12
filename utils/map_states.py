"""
Generates and finds agencies at every state of the MPPA Compliance & Appeals Map.

``MapStateDriver.ensure(state)`` returns the agency parked at ``state`` (``test_data.compliance_map_factory.
MAP_STATES``) after checking the portal still shows it there. When none is (or the parked one has moved on), it
can generate one: it takes an untouched submission (one the state store knows, or a newly built and paid one —
with a branch office when the state needs it) and runs the state's ``path`` — the officer's steps as the Super
Admin on ``agency_view.php`` and Appeals, the agency's steps in its own browser context — then checks where the
portal shows it and parks it there (state store ``map_state``). Parked agencies are left out of
``get_agency_users_in_status``, so the review-loop and appeal tests never move them on.

Every generating step is irreversible on dev (review decisions, notices, refusal, approval and certificate,
appeals and appellate orders). The tests generate only with RUN_MAP_STATE_TESTS=true.
"""

from __future__ import annotations

from dataclasses import dataclass

import allure
from playwright.sync_api import Page

from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.application_review_page import AdminApplicationReviewPage, ReviewStage
from pages.admin.applications_page import AdminApplicationsPage
from pages.agency_home_page import AgencyHomePage
from pages.corrections_page import AgencyCorrectionsPage
from pages.first_appeal_page import FirstAppealPage
from pages.login_page import LoginPage
from pages.my_application_page import MyApplicationPage
from pages.second_appeal_page import SecondAppealPage
from test_data.application_review_factory import ReviewLoopFactory
from test_data.compliance_map_factory import MAP_STATES, MapState
from test_data.first_appeal_factory import AppealOutcomeFactory, FirstAppealFactory, SecondAppealFactory
from utils import file_manager
from utils.review_loop import record_loop_stage
from utils.state_store import TestStateStore, UserRecord

# action → what it does, for the report
ACTIONS = {
    "hold": "Officer: save the review with Part A On Hold",
    "approve_all": "Officer: save the review with every item approved",
    "send_c1": "Officer: send Compliance 1",
    "correct": "Agency: correct every item on hold (reply not sent)",
    "reply": "Agency: send the reply",
    "take_reply_hold": "Officer: take the reply into review, keep Part A On Hold",
    "take_reply_approve": "Officer: take the reply into review, approve every item",
    "show_cause": "Officer: issue the show cause notice and schedule the hearing",
    "window": "Officer: record the hearing and give a window to correct",
    "refuse": "Officer: pass the refusal order",
    "approve_desktop": "Officer: approve Desktop Scrutiny",
    "verify_head_office": "Officer: approve the head office photos and mark it verified",
    "verify_offices": "Officer: approve every office's photos and mark each verified",
    "final_approval": "Officer: give final approval — issue the certificate",
    "file_first_appeal": "Agency: file the First Appeal (FORM-III)",
    "first_hearing": "Divisional Appellate Authority: schedule the First Appeal hearing",
    "decide_first": "Divisional Appellate Authority: pass the appellate order",
    "file_second_appeal": "Agency: file the Second Appeal (FORM-IV)",
    "decide_second": "Commissionerate: pass the second appellate order",
}
APPEAL_HEARING_VENUE = "QA automation — Divisional Office, Room 12 (map test data)"


class MapStateError(RuntimeError):
    pass


class MapStateDriver:
    """``admin_page`` is logged in to the Officer Console as the Super Admin; ``browser`` opens the agencies'
    own contexts (and builds new submissions when none is left)."""

    def __init__(self, admin_page, browser, store: TestStateStore = None, log=print):
        self.admin = admin_page
        self.browser = browser
        self.store = store or TestStateStore()
        self.log = log
        self.review = AdminApplicationReviewPage(admin_page)
        self.appeals = AdminAppealsPage(admin_page)
        self.loop = ReviewLoopFactory.loop()

    # ── Finding ───────────────────────────────────────────────────────────────

    def ensure(self, state: MapState | str, generate: bool) -> UserRecord | None:
        """The agency parked at ``state`` that the portal still shows there; else a newly generated one when
        ``generate``; else None. A parked agency found elsewhere is released (it no longer stands there)."""
        state = MAP_STATES[state] if isinstance(state, str) else state
        for agency in self.store.get_map_users(state.key):
            seen = self.where(state, agency)
            if seen is None:
                return agency
            self.store.unpark_map_state(username=agency.username)
            self.log(f"{agency.username} was parked at '{state.key}' but {seen} — released")
        return self.generate(state) if generate else None

    def where(self, state: MapState, agency: UserRecord) -> str | None:
        """None when the portal shows ``agency`` at ``state``; otherwise what it shows instead."""
        facts = agency.map_state or {}
        if state.appeal:
            return self._appeal_mismatch(state, agency, facts)
        view_id = facts.get("view_id")
        if not view_id:
            return "no review page is recorded for it"
        self.review.open(view_id)
        if state.loop == ReviewStage.APPROVED:
            subtitle = self.review.stage_subtitle.inner_text().strip()
            return None if subtitle == ReviewLoopFactory.APPROVED_STAGE else f"the review page reads '{subtitle}'"
        stage = self.review.stage()
        if stage != state.loop:
            return f"its review page is at '{stage}'"
        if state.after_hearing is not None and self.review.after_hearing() != state.after_hearing:
            return f"it is {'after' if self.review.after_hearing() else 'before'} the show cause hearing"
        if state.loop == ReviewStage.DESKTOP_APPROVAL_DUE and state.after_hearing is False:
            had_c1 = "Deficiency" in self.review.history()
            if had_c1 != ("send_c1" in state.path):
                return "its history " + ("has" if had_c1 else "has no") + " Compliance 1"
        if state.loop == ReviewStage.PHYSICAL:
            branch_bars = any(b["key"].startswith("ph_b") for b in self.review.review_data())
            if branch_bars != bool(state.branches):
                return "its Stage 2 shows " + ("branch office" if branch_bars else "head office") + " photos"
        return None

    def _appeal_mismatch(self, state: MapState, agency: UserRecord, facts: dict) -> str | None:
        key = "appeal_id" if state.appeal == "first" else "second_appeal_id"
        if not facts.get(key):
            return f"no {state.appeal} appeal is recorded for it"
        self.appeals.open_view(state.appeal)
        appeal = self.appeals.appeals_data().get(str(facts[key]))
        if not appeal:
            return f"{state.appeal} appeal #{facts[key]} is not listed"
        decided = bool(appeal.get("decided"))
        if state.disposal and not decided:
            return f"{state.appeal} appeal #{facts[key]} is not decided"
        if not state.disposal and decided:
            return f"{state.appeal} appeal #{facts[key]} is decided ({appeal.get('status')})"
        if state.key == "first_appeal_hearing" and not appeal.get("hearings"):
            return f"first appeal #{facts[key]} has no hearing"
        if state.key == "first_appeal_pending" and appeal.get("hearings"):
            return f"first appeal #{facts[key]} has a hearing scheduled"
        if state.key == "first_appeal_dismissed" and facts.get("second_appeal_id"):
            return "a Second Appeal was filed"
        return None

    def appeal(self, agency: UserRecord, kind: str = "first") -> dict:
        """The ``APPEALS`` entry of the agency's ``kind`` appeal (opens that Appeals view)."""
        key = "appeal_id" if kind == "first" else "second_appeal_id"
        self.appeals.open_view(kind)
        return self.appeals.appeals_data().get(str((agency.map_state or {}).get(key)), {})

    # ── Generating ────────────────────────────────────────────────────────────

    def generate(self, state: MapState) -> UserRecord:
        """Takes an untouched submission along ``state.path`` and parks it there. Raises ``MapStateError`` with
        the step that failed (the agency is then left where it stopped, recorded but not parked)."""
        agency = self._untouched_submission(state.branches)
        facts = {"view_id": self._review_view_id(agency.application_id), "path": list(state.path)}
        action = "start"
        with allure.step(f"Generate an agency at '{state.key}' ({state.step}: {state.title}) — {agency.username}"):
            try:
                for action in state.path:
                    name, _, arg = action.partition(":")
                    with allure.step(f"{ACTIONS[name]}{f' ({arg})' if arg else ''}"):
                        getattr(self, f"_do_{name}")(agency, facts, *([arg] if arg else []))
            except Exception as e:
                self._record_stop(agency, facts)
                raise MapStateError(f"Generating '{state.key}' with {agency.username} stopped at '{action}': {e}") from e
        self.store.park_map_state(username=agency.username, state=state.key, **facts)
        data = {"seeded": "compliance_map", "map_state": state.key}
        if state.review:
            data["review"] = state.review
        self.store.record_agency_status(username=agency.username, status=state.status, data=data)
        parked = self.store.get_user_by_username(agency.username)
        seen = self.where(state, parked)
        if seen is not None:
            self.store.unpark_map_state(username=agency.username)
            raise MapStateError(f"Generated '{state.key}' with {agency.username}, but {seen}.")
        self.log(f"parked {agency.username} ({agency.application_id}) at '{state.key}'")
        return parked

    def _untouched_submission(self, branches: int) -> UserRecord:
        """An untouched submission the state store knows (with ``branches`` branch offices), or a new one."""
        for user in self.store.get_agency_users_in_status("desktop_scrutiny", review="under_review"):
            if ((user.status_data or {}).get("loop") not in (None, ReviewStage.NEW)
                    or (user.step_data.get("part_a") or {}).get("branches", 0) != branches):
                continue
            view_id = self._find_view_id(user.application_id, steps=("review",))
            if view_id is None:
                continue
            self.review.open(view_id)
            if self.review.stage() == ReviewStage.NEW:
                return user
        from fixtures.notifications_fixtures import submit_application   # builds through the agency portal
        with allure.step(f"Build and pay a new application ({branches} branch office(s))"):
            context = self.browser.new_context(viewport={"width": 1280, "height": 800})
            context.set_default_timeout(30000)
            try:
                user = submit_application(context.new_page(), branches=branches)
            finally:
                context.close()
        self.store.record_agency_status(username=user.username, status="desktop_scrutiny",
                                        data={"review": "under_review", "loop": ReviewStage.NEW})
        self._stay_logged_in()
        return self.store.get_user_by_username(user.username)

    def _stay_logged_in(self) -> None:
        """Logs the Super Admin in again when the console logged itself out while an agency was built (it
        does after about 15 idle minutes)."""
        from fixtures.drafts_fixtures import _admin_login
        AdminApplicationsPage(self.admin).open("desktop", "review")
        if "login" in self.admin.url:
            self.log("the Officer Console logged out while a new application was built — logging in again")
            _admin_login(self.admin)

    def _find_view_id(self, application_id: str, steps=(None,)) -> int | None:
        """The review page id of ``application_id`` under Desktop scrutiny, found with the list's Search (the
        unfiltered list fails to load on dev once any application was given a post-hearing window)."""
        applications = AdminApplicationsPage(self.admin)
        for step in steps:
            applications.open("desktop", step, query=application_id)
            ids = applications.review_view_ids()
            if application_id in ids:
                return ids[application_id]
        return None

    def _review_view_id(self, application_id: str) -> int:
        view_id = self._find_view_id(application_id, steps=(None, *AdminApplicationsPage.REVIEW_STEPS))
        if view_id is None:
            raise MapStateError(f"Application {application_id} is not listed under Desktop scrutiny")
        return view_id

    def _record_stop(self, agency: UserRecord, facts: dict) -> None:
        """Records where a failed generation left the agency, so the review-loop tests can tell."""
        try:
            self.review.open(facts["view_id"])
            record_loop_stage(agency, self.review.stage())
        except Exception:
            pass

    # ── Agency session ────────────────────────────────────────────────────────

    def _as_agency(self, agency: UserRecord, work):
        context = self.browser.new_context(viewport={"width": 1366, "height": 900})
        context.set_default_timeout(30000)
        page = context.new_page()
        try:
            login = LoginPage(page)
            login.open()
            login.login(agency.username, agency.password)
            page.wait_for_load_state("networkidle")
            if "login" in page.url:
                raise MapStateError(f"agency {agency.username} could not log in")
            result = work(page)
            page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
            return result
        finally:
            context.close()

    # ── Actions: officer, review loop ─────────────────────────────────────────

    def _open(self, facts):
        self.review.open(facts["view_id"])

    def _do_hold(self, agency, facts):
        self._open(facts)
        self.review.save_review_with_hold(self.loop.hold_item, self.loop.hold_reason, self.loop.hold_remark)

    def _do_approve_all(self, agency, facts):
        self._open(facts)
        self.review.save_review_all_approved()

    def _do_send_c1(self, agency, facts):
        self._open(facts)
        self.review.run_flow("deficiency")

    def _do_take_reply_hold(self, agency, facts):
        self._open(facts)
        self.review.run_flow("accept_reply")
        self.review.save_review_with_hold(self.loop.hold_item, self.loop.hold_reason, self.loop.hold_remark)

    def _do_take_reply_approve(self, agency, facts):
        self._open(facts)
        self.review.run_flow("accept_reply")
        self.review.save_review_all_approved()

    def _do_show_cause(self, agency, facts):
        self._open(facts)
        d = self.loop
        self.review.issue_show_cause(d.scn_reason, d.scn_grounds, d.hearing_venue, d.hearing_minutes_ahead)

    def _do_window(self, agency, facts):
        self._open(facts)
        self.review.grant_window(self.loop.attendance, self.loop.window_days, self.loop.hearing_record)

    def _do_refuse(self, agency, facts):
        self._open(facts)
        self.review.refuse(self.loop.refusal_reason, self.loop.speaking_order, self.loop.division_note)

    # ── Actions: officer, approval ────────────────────────────────────────────

    def _do_approve_desktop(self, agency, facts):
        self._open(facts)
        self.review.approve_desktop_scrutiny()
        if self.review.stage() != ReviewStage.PHYSICAL:
            raise MapStateError(f"Approve Desktop Scrutiny left the page at '{self.review.stage()}'")

    def _verify_offices(self, limit: int):
        """Approves the open office's photos and marks it verified, ``limit`` offices at most."""
        verified = 0
        while verified < limit:
            if any(b["orig"] != "approved" for b in self.review.review_data()):
                self.review.save_review_all_approved()
            if not self.review.mark_offices_verified(limit=1):
                break
            verified += 1
        if not verified:
            raise MapStateError("no office could be marked verified")

    def _do_verify_head_office(self, agency, facts):
        self._open(facts)
        self._verify_offices(limit=1)

    def _do_verify_offices(self, agency, facts):
        self._open(facts)
        self._verify_offices(limit=10)

    def _do_final_approval(self, agency, facts):
        self._open(facts)
        self.review.final_approval()
        # The registration number is the Application ID (dev, 06-Nov-2026)
        self.store.record_certificate_no(username=agency.username, certificate_no=agency.application_id)

    # ── Actions: agency, corrections ──────────────────────────────────────────

    def _do_correct(self, agency, facts):
        def work(page):
            corrections = AgencyCorrectionsPage(page)
            corrections.open()
            problems = corrections.answer_open_items(self.loop.correction_note,
                                                     blanks={"email": agency.email, "mobile": agency.mobile})
            if problems:
                raise MapStateError("; ".join(problems))
        self._as_agency(agency, work)

    def _do_reply(self, agency, facts):
        def work(page):
            corrections = AgencyCorrectionsPage(page)
            corrections.open()
            reply = corrections.send_reply(self.loop.reply_text)
            if not reply.get("ok"):
                raise MapStateError(f"reply not sent: {reply.get('msg')}")
        self._as_agency(agency, work)

    # ── Actions: appeals ──────────────────────────────────────────────────────

    def _do_file_first_appeal(self, agency, facts):
        def work(page):
            form = FirstAppealPage(page)
            form.open()
            form.file_appeal(FirstAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE))
        self._as_agency(agency, work)
        self.appeals.open_view("first")
        appeal = self.appeals.appeal_for(agency.application_id, "first")
        if not appeal:
            raise MapStateError("the First Appeal is not listed under First Appeals — Division")
        facts["appeal_id"] = int(appeal["id"])

    def _do_first_hearing(self, agency, facts):
        self.appeals.open_view("first")
        message = self.appeals.schedule_hearing(facts["appeal_id"], APPEAL_HEARING_VENUE)
        self.appeals.open_view("first")
        appeal = self.appeals.appeals_data().get(str(facts["appeal_id"]), {})
        if not appeal.get("hearings"):
            raise MapStateError(f"no hearing was recorded (page said: '{message}')")

    def _do_decide_first(self, agency, facts, disposal):
        self.appeals.open_view("first")
        order = AppealOutcomeFactory.order(disposal)
        prompt = self.appeals.decide(facts["appeal_id"], order.disposal, order.reasons)
        if not prompt:
            raise MapStateError("the appellate order was not asked to be confirmed")

    def _do_file_second_appeal(self, agency, facts):
        def work(page):
            form = SecondAppealPage(page)
            form.open()
            if form.appeal_form.count() == 0:
                raise MapStateError(f"FORM-IV is not offered: {form.blocking_note.all_inner_texts()}")
            form.file_appeal(SecondAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE))
        self._as_agency(agency, work)
        self.appeals.open_view("second")
        appeal = self.appeals.appeal_for(agency.application_id, "second")
        if not appeal:
            raise MapStateError("the Second Appeal is not listed under Second Appeals — Commissionerate")
        facts["second_appeal_id"] = int(appeal["id"])

    def _do_decide_second(self, agency, facts, disposal):
        self.appeals.open_view("second")
        order = AppealOutcomeFactory.order(disposal)
        prompt = self.appeals.decide(facts["second_appeal_id"], order.disposal, order.reasons)
        if not prompt:
            raise MapStateError("the second appellate order was not asked to be confirmed")


# ── What the map tests get (fixtures.compliance_map_fixtures: agency_at, officer_at) ──

@dataclass
class AgencyView:
    """The parked agency logged in on its own page, with the officer's driver for looking things up."""
    page: Page
    agency: UserRecord
    driver: MapStateDriver

    @property
    def facts(self) -> dict:
        return self.agency.map_state or {}

    @property
    def home(self) -> AgencyHomePage:
        return AgencyHomePage(self.page)

    @property
    def my_app(self) -> MyApplicationPage:
        return MyApplicationPage(self.page)

    @property
    def corrections(self) -> AgencyCorrectionsPage:
        return AgencyCorrectionsPage(self.page)

    @property
    def first_appeal(self) -> FirstAppealPage:
        return FirstAppealPage(self.page)

    @property
    def second_appeal(self) -> SecondAppealPage:
        return SecondAppealPage(self.page)


@dataclass
class OfficerView:
    """The parked agency seen from the Officer Console (Super Admin)."""
    agency: UserRecord
    driver: MapStateDriver

    @property
    def facts(self) -> dict:
        return self.agency.map_state or {}

    @property
    def review(self) -> AdminApplicationReviewPage:
        return self.driver.review

    @property
    def appeals(self) -> AdminAppealsPage:
        return self.driver.appeals

    def open_review(self) -> AdminApplicationReviewPage:
        self.review.open(self.facts["view_id"])
        return self.review
