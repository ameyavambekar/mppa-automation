"""
Prepares First Appeal test data on dev: refused agencies, pending First Appeals and decided ones.

The appeal tests need agencies in states no other test reaches:

* ``rejected``     — application refused, no appeal yet. FORM-III tests open it without filing; each filing
                     test (RUN_APPEAL_FILING_TESTS) uses one up for good.
* a pending First Appeal — FORM-III tracking tests (KAN-14) and the officer's review tests (KAN-29).
* a decided First Appeal — KAN-TC-744 (agency sees the decision), KAN-29's audit / e-mail tests and,
  being dismissed, the Second Appeal (KAN-15).

``AppealSeeder.top_up`` counts what the state store and the Officer Console already hold and builds only
the shortfall, in this order:

1. **Refuse** applications that are untouched in Desktop scrutiny (``desktop_scrutiny`` / ``under_review``
   in the state store; when none is left, one more agency is built and pays). Refusing runs the whole loop on
   ``agency_view.php``: Part A On Hold → Compliance 1 → the agency answers → show cause notice and hearing →
   window to correct → the agency answers again → refusal order (``RefusalFactory.failed_correction``).
2. **File** First Appeals (all five documents, so KAN-29's ``pending_first_appeal`` can reuse them) for
   refused agencies.
3. **Decide** the oldest pending ones as "Appeal Dismissed — Refusal Upheld".

Only agencies the state store knows are touched (never "yadnesh" or any other portal user), and only as the
Super Admin from ``.env`` plus the agencies' own logins. Refusing, filing and deciding cannot be undone.

    python -m utils.seed_appeals --refused 5 --pending 1 --decided 1 [--dry-run]
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from config import ADMIN_LOGOUT_URL
from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.admin.applications_page import AdminApplicationsPage
from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.application_review_page import AdminApplicationReviewPage
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.corrections_page import AgencyCorrectionsPage
from pages.first_appeal_page import FirstAppealPage
from pages.login_page import LoginPage
from test_data.first_appeal_factory import AppealOutcomeFactory, FirstAppealFactory
from test_data.refusal_factory import RefusalData, RefusalFactory
from utils import file_manager
from utils.agency_status_sync import sync_agency_statuses
from utils.state_store import TestStateStore, UserRecord


@dataclass
class AppealCounts:
    refused: int        # refused, not yet appealed
    pending: int        # First Appeal awaiting decision
    decided: int        # First Appeal with an appellate order

    def __str__(self):
        return f"refused {self.refused}, pending first appeals {self.pending}, decided first appeals {self.decided}"


@dataclass
class SeedPlan:
    refuse: int
    file: int
    decide: int

    def __bool__(self):
        return bool(self.refuse or self.file or self.decide)

    def __str__(self):
        return f"refuse {self.refuse} application(s), file {self.file} First Appeal(s), decide {self.decide}"


def plan(counts: AppealCounts, refused: int, pending: int, decided: int) -> SeedPlan:
    """What to build so that ``refused`` / ``pending`` / ``decided`` are ready. Each decision uses up a pending
    appeal and each filing a refused agency, so those are built on top."""
    decide = max(decided - counts.decided, 0)
    file = max(pending + decide - counts.pending, 0)
    refuse = max(refused + file - counts.refused, 0)
    return SeedPlan(refuse=refuse, file=file, decide=decide)


class AppealSeeder:
    """Drives the Officer Console (one Super Admin page) and the agency portal (a fresh context per agency) to
    prepare appeal test data. Use as a context manager: it logs the Super Admin in and out."""

    def __init__(self, browser, store: TestStateStore = None, log=print):
        self.browser = browser
        self.store = store or TestStateStore()
        self.log = log
        self.refusal: RefusalData = RefusalFactory.failed_correction()
        self._context = None
        self.admin = None

    # ── Session ───────────────────────────────────────────────────────────────

    def __enter__(self):
        username, password = os.getenv("ADMIN_SUPER_USERNAME"), os.getenv("ADMIN_SUPER_PASSWORD")
        if not (username and password):
            admin = self.store.get_any_super_admin()
            if admin is None:
                raise SystemExit("Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env (or seed a super_admin).")
            username, password = admin.username, admin.password
        self._context = self.browser.new_context(viewport={"width": 1400, "height": 900})
        self._context.set_default_timeout(30000)
        self.admin = self._context.new_page()
        login = AdminLoginPage(self.admin)
        login.open()
        error = login.login_past_captcha(username, password)
        if error:
            raise SystemExit(f"Admin login as {username} failed: {error}")
        self.admin.wait_for_url(ADMIN_DASHBOARD_URL)
        return self

    def __exit__(self, *exc):
        try:
            self.admin.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
        finally:
            self._context.close()

    def _agency_session(self, agency: UserRecord):
        """A fresh context logged in as ``agency``; the caller closes it. None when the login fails."""
        context = self.browser.new_context(viewport={"width": 1400, "height": 900})
        context.set_default_timeout(30000)
        page = context.new_page()
        login = LoginPage(page)
        login.open()
        login.login(agency.username, agency.password)
        page.wait_for_load_state("networkidle")
        if "login" in page.url:
            context.close()
            return None, None
        return context, page

    # ── Counting ──────────────────────────────────────────────────────────────

    def _store_appeals(self) -> list[dict]:
        """First Appeals on the console (APPEALS data) filed by agencies the state store knows."""
        known = {u.application_id for u in self.store.get_agency_users_in_status("first_appeal") if u.application_id}
        appeals = AdminAppealsPage(self.admin)
        appeals.open_view("first")
        return [a for a in appeals.appeals_data().values() if a.get("type") == "first" and a.get("reg_id") in known]

    def counts(self, sync: bool = True) -> AppealCounts:
        if sync:
            sync_agency_statuses(self.admin, self.store)
        appeals = self._store_appeals()
        return AppealCounts(refused=len(self.store.get_agency_users_in_status("rejected")),
                            pending=sum(1 for a in appeals if a.get("can_decide") and not a.get("decided")),
                            decided=sum(1 for a in appeals if a.get("decided")))

    # ── Refusing ──────────────────────────────────────────────────────────────

    def _untouched_submissions(self) -> list[UserRecord]:
        return [u for u in self.store.get_agency_users_in_status("desktop_scrutiny", review="under_review")
                if u.application_id]

    def _new_submission(self) -> UserRecord:
        """Pays for one more application (an unpaid agency from the store, or a newly built one)."""
        from fixtures.notifications_fixtures import submit_application   # builds through the agency portal
        context = self.browser.new_context(viewport={"width": 1280, "height": 800})
        context.set_default_timeout(30000)
        try:
            user = submit_application(context.new_page())
        finally:
            context.close()
        self.store.record_agency_status(username=user.username, status="desktop_scrutiny", data={"review": "under_review"})
        return user

    def _review_view_id(self, application_id: str) -> int:
        applications = AdminApplicationsPage(self.admin)
        applications.open("desktop")
        link = applications.row_by_application_id(application_id).get_by_role("link", name="Review")
        return int(link.get_attribute("href").split("id=")[1].split("&")[0])

    def _agency_answers(self, agency: UserRecord):
        """The agency answers every open correction unchanged and sends its reply."""
        context, page = self._agency_session(agency)
        if page is None:
            raise RuntimeError(f"agency {agency.username} could not log in")
        try:
            corrections = AgencyCorrectionsPage(page)
            corrections.open()
            problems = corrections.answer_open_items(self.refusal.correction_note,
                                                     blanks={"email": agency.email, "mobile": agency.mobile})
            if problems:
                raise RuntimeError("; ".join(problems))
            reply = corrections.send_reply(self.refusal.reply_text)
            if not reply.get("ok"):
                raise RuntimeError(f"reply not sent: {reply.get('msg')}")
            page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        finally:
            context.close()

    def refuse(self, agency: UserRecord) -> None:
        """Drives ``agency``'s untouched application through the review loop to a refusal order and records
        the agency as ``rejected``. Raises with the failing step."""
        r = self.refusal
        review = AdminApplicationReviewPage(self.admin)
        view_id = self._review_view_id(agency.application_id)
        step = "review"
        try:
            review.open(view_id)
            review.save_review_with_hold(r.hold_item, r.hold_reason, r.hold_remark)
            step = "Compliance 1"
            review.run_flow("deficiency")
            step = "agency reply 1"
            self._agency_answers(agency)
            step = "take reply 1 into review"
            review.open(view_id)
            review.run_flow("accept_reply")
            review.save_review_with_hold(r.hold_item, r.hold_reason, r.hold_remark)
            step = "show cause notice"
            review.issue_show_cause(r.scn_reason, r.scn_grounds, r.hearing_venue, r.hearing_minutes_ahead)
            step = "window to correct"
            review.grant_window(r.attendance, r.window_days, r.hearing_record)
            step = "agency reply 2"
            self._agency_answers(agency)
            step = "take reply 2 into review"
            review.open(view_id)
            review.run_flow("accept_reply")
            review.save_review_with_hold(r.hold_item, r.hold_reason, r.hold_remark)
            step = "refusal order"
            review.refuse(r.refusal_reason, r.speaking_order, r.division_note)
        except Exception as e:
            raise RuntimeError(f"refusing {agency.username} failed at '{step}': {e}") from e
        text = review.main_text()
        if RefusalFactory.REFUSED_STAGE not in text and "REJECTED" not in text:
            raise RuntimeError(f"{agency.username}: the refusal order did not show the application as refused")
        self.store.record_agency_status(username=agency.username, status="rejected",
                                        data={"seeded": "appeal_seeder", "reason": r.refusal_reason})

    # ── Filing and deciding ───────────────────────────────────────────────────

    def file_first_appeal(self, agency: UserRecord) -> bool:
        """Files a complete First Appeal (all five documents) for a refused agency; records it as
        ``first_appeal``. False when the agency could not log in or had already filed."""
        context, page = self._agency_session(agency)
        if page is None:
            return False
        try:
            fa = FirstAppealPage(page)
            fa.open()
            if fa.has_existing_appeal():
                self.store.record_agency_status(username=agency.username, status="first_appeal")
                return False
            fa.file_appeal(FirstAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE))
            fa.open()
            if not fa.has_existing_appeal():
                raise RuntimeError(f"filing for {agency.username} was not confirmed — FORM-III still offers the form")
            self.store.record_agency_status(username=agency.username, status="first_appeal",
                                            data={"appeal_status": "filed", "seeded": "appeal_seeder"})
            page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
            return True
        finally:
            context.close()

    def decide_oldest_pending(self) -> int:
        """Dismisses the oldest pending First Appeal of a state-store agency (refusal upheld); returns its id."""
        pending = [a for a in self._store_appeals() if a.get("can_decide") and not a.get("decided")]
        if not pending:
            raise RuntimeError("no pending First Appeal of a state-store agency to decide")
        appeal = min(pending, key=lambda a: int(a["id"]))
        outcome = AppealOutcomeFactory.dismissed_upheld()
        appeals = AdminAppealsPage(self.admin)
        appeals.open_view("first")
        prompt = appeals.decide(int(appeal["id"]), outcome.disposal, outcome.reasons)
        if not prompt:
            raise RuntimeError(f"appeal #{appeal['id']}: the order was not asked to be confirmed")
        return int(appeal["id"])

    # ── Top-up ────────────────────────────────────────────────────────────────

    def top_up(self, refused: int, pending: int, decided: int, dry_run: bool = False) -> AppealCounts:
        before = self.counts()
        todo = plan(before, refused, pending, decided)
        self.log(f"Ready now: {before}.")
        self.log(f"Plan: {todo}." if todo else "Nothing to build.")
        if dry_run or not todo:
            return before

        for n in range(1, todo.refuse + 1):
            pool = self._untouched_submissions()
            agency = pool[0] if pool else self._new_submission()
            self.log(f"  refusing {n}/{todo.refuse}: {agency.username} ({agency.application_id}) …")
            self.refuse(agency)
            self.log("    refused")

        filed = 0
        for agency in self.store.get_agency_users_in_status("rejected"):
            if filed == todo.file:
                break
            if self.file_first_appeal(agency):
                filed += 1
                self.log(f"  filed First Appeal {filed}/{todo.file} for {agency.username}")
        if filed < todo.file:
            raise RuntimeError(f"only {filed} of {todo.file} First Appeals could be filed")

        for n in range(1, todo.decide + 1):
            appeal_id = self.decide_oldest_pending()
            self.log(f"  decided {n}/{todo.decide}: First Appeal #{appeal_id} dismissed (refusal upheld)")

        after = self.counts()
        self.log(f"Ready now: {after}.")
        return after
