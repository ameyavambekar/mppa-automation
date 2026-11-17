"""
Prepares the desktop scrutiny test data the agency-side compliance tests need (KAN-48 / KAN-12):

* **untouched submissions** — applications in Desktop scrutiny nobody has reviewed yet. The review-loop tests take
  one up (TC-752 onward, and any test that needs an application waiting for its first review).
* **awaiting corrections** — applications with Compliance 1 sent (Part A On Hold, items to correct, reply not yet
  sent). Tests that correct or reply consume one each: TC-757/758/760 and TC-769/772 (``agency_with_corrections``).
* **a hearing** — the ``hearing_scheduled`` map state (Compliance 2 show cause issued, hearing scheduled), parked
  for TC-770 through ``utils.map_states.MapStateDriver``. The driver is the same one the map tests use.

``ReviewSeeder.top_up`` counts what is ready, builds only the shortfall (a paid application for each one missing,
through the agency portal) and then sends Compliance 1 on the first ``compliance_1`` untouched submissions. Those
agencies are left unparked, so the review-loop tests can take them on. A parked agency is never moved here.

    python -m utils.seed_review --dry-run
    python -m utils.seed_review --untouched 2 --compliance-1 2 --park-hearing

Building and paying an application, and sending a notice, cannot be undone on dev.
"""

from __future__ import annotations

from dataclasses import dataclass

from pages.admin.application_review_page import AdminApplicationReviewPage, ReviewStage
from test_data.application_review_factory import ReviewLoopFactory
from test_data.compliance_map_factory import MAP_STATES
from utils.appeal_seeder import AppealSeeder
from utils.map_states import MapStateDriver
from utils.review_loop import record_loop_stage
from utils.state_store import UserRecord


@dataclass
class ReviewPlan:
    build: int      # new applications to build and pay
    send: int       # untouched submissions to send Compliance 1 to

    def __str__(self):
        return f"build {self.build} new application(s), send Compliance 1 on {self.send}"


def plan(have_untouched: int, untouched_target: int, compliance_1: int) -> ReviewPlan:
    """Builds only the shortfall, so that ``untouched_target`` untouched submissions are left after the
    ``compliance_1`` notices have been sent."""
    needed = compliance_1 + untouched_target
    return ReviewPlan(build=max(0, needed - have_untouched), send=compliance_1)


class ReviewSeeder(AppealSeeder):
    """Uses the appeal seeder's session, submission and review-page helpers (one Super Admin page, a fresh context
    per agency). Use as a context manager, like ``AppealSeeder``."""

    def __enter__(self):
        super().__enter__()
        self.review = AdminApplicationReviewPage(self.admin)
        return self

    # ── Counting ──────────────────────────────────────────────────────────────

    def untouched(self) -> list[UserRecord]:
        """Untouched submissions: the state store's Desktop scrutiny agencies whose review page reads NEW."""
        found = []
        for user in self._untouched_submissions():
            if (user.status_data or {}).get("loop") not in (None, ReviewStage.NEW):
                continue
            try:
                view_id = self._review_view_id(user.application_id)
            except Exception:
                continue
            self.review.open(view_id)
            if self.review.stage() == ReviewStage.NEW:
                found.append(user)
        return found

    # ── Sending Compliance 1 ──────────────────────────────────────────────────

    def send_compliance_1(self, agency: UserRecord) -> None:
        """Puts Part A On Hold (the loop's own reason and remark), saves, and sends Compliance 1. Leaves the agency
        unparked at ``with_agency``, where the review-loop tests find it. Raises when the page does not show that."""
        d = ReviewLoopFactory.loop()
        self.review.open(self._review_view_id(agency.application_id))
        self.review.save_review_with_hold(d.hold_item, d.hold_reason, d.hold_remark)
        record_loop_stage(agency, ReviewStage.HELD)
        self.review.run_flow("deficiency")
        stage = self.review.stage()
        record_loop_stage(agency, stage)
        if stage != ReviewStage.WITH_AGENCY:
            raise RuntimeError(f"Sending Compliance 1 on {agency.username} left it at '{stage}', "
                               f"not '{ReviewStage.WITH_AGENCY}'.")
        self.log(f"sent Compliance 1 on {agency.username} ({agency.application_id})")

    # ── Hearing ───────────────────────────────────────────────────────────────

    def park_hearing(self):
        """Parks an agency at ``hearing_scheduled`` (TC-770), generating it when none is parked there."""
        driver = MapStateDriver(self.admin, self.browser, self.store, log=self.log)
        agency = driver.ensure(MAP_STATES["hearing_scheduled"], generate=True)
        self.log(f"parked {agency.username} at 'hearing_scheduled'")
        return agency

    # ── Top up ────────────────────────────────────────────────────────────────

    def top_up(self, untouched_target: int, compliance_1: int, park_hearing: bool = False,
               dry_run: bool = False) -> ReviewPlan:
        have = self.untouched()
        p = plan(len(have), untouched_target, compliance_1)
        self.log(f"untouched submissions now: {len(have)}; {p}; park hearing: {park_hearing}")
        if dry_run:
            return p

        for _ in range(p.build):
            user = self._new_submission()
            have.append(user)
            self.log(f"built and paid {user.username} ({user.application_id})")

        for agency in have[:p.send]:
            self.send_compliance_1(agency)

        if park_hearing:
            self.park_hearing()
        return p
