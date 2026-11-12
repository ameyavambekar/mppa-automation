"""
MPPA Appeals Map — officer side (KAN-50)
========================================
One test per appeal state of the MPPA Compliance & Appeals Map (Procedure 2, A3–A6:
``test_data.compliance_map_factory.MAP_STATES`` with ``procedure == "Appeals"``, KAN-TC-819…828): what the Officer
Console shows for an appeal standing there — Appeals (First Appeals — Division, Second Appeals — Commissionerate,
Hearings & appointments, the appeal's "Review & decide" dialog) and where the appellate order leaves the
application (its review page). The agency's side of the same states is ``tests/test_appeals_map.py`` (KAN-49).

The compliance states of the map (Procedure 1, C1–C10 and the approval branch) are tested with the review loop in
``tests/admin/test_application_review.py`` — officer side KAN-12 (KAN-TC-801…818), agency side KAN-48
(KAN-TC-773…790).

Test data. Each state has its own application, parked there in the state store (``map_state``, with the review
page id and appeal ids) and left there; the tests only read. ``officer_at(state)`` checks the application still
stands there. A state with no parked application is skipped — run with RUN_MAP_STATE_TESTS=true to generate one
first. Generating an appeal state is IRREVERSIBLE on dev and slow (a whole review loop to the refusal order first).

Every state was generated on dev on 06-Nov-2026 (one application each) and all 10 cases are Published.

Known defects: "I & II Appeal" #68 (no e-mail to the agency about the appellate order) — not asserted here.
"""

import re

import allure
from playwright.sync_api import expect

from pages.admin.appeals_page import AdminAppealsPage
from test_data.application_review_factory import ReviewLoopFactory as R
from test_data.compliance_map_factory import ComplianceMapFactory as M
from utils.aio import aio_case
from utils.map_states import APPEAL_HEARING_VENUE, OfficerView

STORY = "Appeals Map — officer"


# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------
def _appeal(o: OfficerView, kind: str) -> tuple[int, dict, dict]:
    """(appeal id, its APPEALS entry, its row) on the ``kind`` view ('first' / 'second')."""
    n = int(o.facts["appeal_id" if kind == "first" else "second_appeal_id"])
    o.appeals.open_view(kind)
    entry = o.appeals.appeals_data().get(str(n))
    assert entry, f"{kind} appeal #{n} is not listed"
    row = next((r for r in o.appeals.appeal_rows_data() if r["id"] == str(n)), None)
    assert row, f"No row for {kind} appeal #{n}"
    return n, entry, row


def _expect_decided(o: OfficerView, kind: str, disposal: str) -> tuple[int, dict, dict]:
    labels = AdminAppealsPage.FIRST_DISPOSALS if kind == "first" else AdminAppealsPage.SECOND_DISPOSALS
    with allure.step(f"Appeals: the {kind} appeal is decided — {labels[disposal]}"):
        n, entry, row = _appeal(o, kind)
        assert entry.get("decided"), entry
        assert not entry.get("can_decide"), "The decided appeal can still be decided"
        assert (entry.get("remarks") or "").startswith(labels[disposal]), entry.get("remarks")
        assert row["status"] != M.APPEAL_PENDING, row
        if kind == "first":
            assert entry.get("order") == f"FAA/{entry['decided'][:4]}/{n}", entry.get("order")
    return n, entry, row


def _expect_application_refused(o: OfficerView):
    with allure.step("Review page: still refused"):
        review = o.open_review()
        expect(review.main).to_contain_text(R.REFUSED_STAGE)


def _expect_application_approved(o: OfficerView):
    with allure.step("Review page: approved, certificate issued"):
        review = o.open_review()
        expect(review.stage_subtitle).to_have_text(R.APPROVED_STAGE)


# ---------------------------------------------------------------------------
# Procedure 2 — First and Second Appeal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-819")
@allure.story(STORY)
@allure.title("TC-819: A3 — First Appeal filed: pending in the Division's queue with the hearing and order forms")
def test_tc819_first_appeal_pending(officer_at):
    """
    Given the application parked at 'first_appeal_pending' (A3)
    When  the officer opens Appeals › First Appeals — Division and the appeal
    Then  its row shows "N days left", Hearing "Not yet" and Status "Pending"
    And   "Review & decide" opens "First Appeal (FORM-III) #N" with the hearing form and the appellate order

    AIO: KAN-TC-819 | KAN-50 AC-1 | data: map state 'first_appeal_pending'
    """
    o = officer_at("first_appeal_pending")
    with allure.step("First Appeals — Division: the appeal is pending"):
        n, entry, row = _appeal(o, "first")
        assert row["status"] == M.APPEAL_PENDING, row
        assert re.search(r"\d+ days? left", row["due"]), row
        assert row["hearing"] == "Not yet", row
        assert entry.get("can_decide") and not entry.get("decided"), entry
    with allure.step("Review & decide: hearing and order forms"):
        o.appeals.open_appeal(n)
        expect(o.appeals.modal_title).to_contain_text(f"First Appeal (FORM-III) #{n}")
        expect(o.appeals.hearing_date_input).to_be_visible()
        expect(o.appeals.disposal_select).to_be_visible()


@aio_case("KAN-TC-820")
@allure.story(STORY)
@allure.title("TC-820: A4 — First Appeal hearing scheduled: listed under Hearings, no second hearing")
def test_tc820_first_appeal_hearing(officer_at):
    """
    Given the application parked at 'first_appeal_hearing' (A4)
    When  the officer opens First Appeals — Division, Hearings & appointments and the appeal
    Then  the appeal has its hearing and is undecided, its row's status reads "Hearing stage"; Hearings &
          appointments lists the application
    And   the appeal no longer offers "Schedule the hearing" (one hearing per level) but can still be decided

    AIO: KAN-TC-820 | KAN-50 AC-2 | data: map state 'first_appeal_hearing'
    """
    o = officer_at("first_appeal_hearing")
    with allure.step("First Appeals — Division: the hearing is recorded"):
        n, entry, row = _appeal(o, "first")
        assert entry.get("hearings") and not entry.get("decided"), entry
        assert row["status"] == M.APPEAL_HEARING_STAGE and row["hearing"] != "Not yet", row
    with allure.step("Hearings & appointments lists the hearing"):
        o.appeals.open_view("hearings")
        expect(o.appeals.main).to_contain_text(f"First Appeal #{n}")
        expect(o.appeals.main).to_contain_text(o.agency.application_id)
        expect(o.appeals.main).to_contain_text(APPEAL_HEARING_VENUE)
    with allure.step("Review & decide: no second hearing, the order can be passed"):
        o.appeals.open_view("first")
        o.appeals.open_appeal(n)
        expect(o.appeals.schedule_hearing_button).to_be_hidden()
        expect(o.appeals.disposal_select).to_be_visible()


@aio_case("KAN-TC-821")
@allure.story(STORY)
@allure.title("TC-821: A5 — First Appeal allowed (order set aside): decided, application approved")
def test_tc821_first_appeal_allowed(officer_at):
    """
    Given the application parked at 'first_appeal_allowed' (A5)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided (order FAA/<year>/<id>, "Appeal Allowed — Order Set Aside") and cannot be decided
          again, and the application reads "Approved — Certificate Issued · Closed"

    AIO: KAN-TC-821 | KAN-50 AC-3 | data: map state 'first_appeal_allowed'
    """
    o = officer_at("first_appeal_allowed")
    _expect_decided(o, "first", "allowed")
    _expect_application_approved(o)


@aio_case("KAN-TC-822")
@allure.story(STORY)
@allure.title("TC-822: A5 — First Appeal allowed with conditions: decided, application approved")
def test_tc822_first_appeal_allowed_conditions(officer_at):
    """
    Given the application parked at 'first_appeal_allowed_conditions' (A5)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided ("Appeal Allowed with Conditions") and the application is approved

    AIO: KAN-TC-822 | KAN-50 AC-3 | data: map state 'first_appeal_allowed_conditions'
    """
    o = officer_at("first_appeal_allowed_conditions")
    _expect_decided(o, "first", "allowed_conditions")
    _expect_application_approved(o)


@aio_case("KAN-TC-823")
@allure.story(STORY)
@allure.title("TC-823: A5 — First Appeal remanded: decided, application back in desktop scrutiny")
def test_tc823_first_appeal_remanded(officer_at):
    """
    Given the application parked at 'first_appeal_remanded' (A5)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided ("Remanded Back for Re-Scrutiny") and the review page is back in Stage 1 — Desktop
          Scrutiny and no longer read-only

    AIO: KAN-TC-823 | KAN-50 AC-3 | data: map state 'first_appeal_remanded'
    """
    o = officer_at("first_appeal_remanded")
    _expect_decided(o, "first", "remanded")
    with allure.step("Review page: back in Stage 1"):
        review = o.open_review()
        expect(review.stage_subtitle).to_contain_text("Stage 1 — Desktop Scrutiny")
        expect(review.read_only_banner).to_have_count(0)


@aio_case("KAN-TC-824")
@allure.story(STORY)
@allure.title("TC-824: A5 — First Appeal dismissed, refusal upheld: decided, application still refused")
def test_tc824_first_appeal_dismissed(officer_at):
    """
    Given the application parked at 'first_appeal_dismissed' (A5, no Second Appeal filed)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided ("Appeal Dismissed — Refusal Upheld", order FAA/<year>/<id>, Status "Dismissed")
          and the application is still refused

    AIO: KAN-TC-824 | KAN-50 AC-3 | data: map state 'first_appeal_dismissed'
    """
    o = officer_at("first_appeal_dismissed")
    _, _, row = _expect_decided(o, "first", "dismissed_upheld")
    assert row["status"] == "Dismissed", row
    _expect_application_refused(o)


@aio_case("KAN-TC-825")
@allure.story(STORY)
@allure.title("TC-825: A5 — First Appeal dismissed for default: decided, application still refused")
def test_tc825_first_appeal_dismissed_default(officer_at):
    """
    Given the application parked at 'first_appeal_dismissed_default' (A5)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided ("Dismissed for Default of Appearance") and the application is still refused

    AIO: KAN-TC-825 | KAN-50 AC-3 | data: map state 'first_appeal_dismissed_default'
    """
    o = officer_at("first_appeal_dismissed_default")
    _expect_decided(o, "first", "dismissed_default")
    _expect_application_refused(o)


@aio_case("KAN-TC-826")
@allure.story(STORY)
@allure.title("TC-826: A5 — First Appeal rejected for delay: decided, case closed")
def test_tc826_first_appeal_delay_rejected(officer_at):
    """
    Given the application parked at 'first_appeal_delay_rejected' (A5)
    When  the officer opens First Appeals — Division and the application's review page
    Then  the appeal is decided ("Delay Condonation Rejected") and the application is still refused

    AIO: KAN-TC-826 | KAN-50 AC-3 | data: map state 'first_appeal_delay_rejected'
    """
    o = officer_at("first_appeal_delay_rejected")
    _expect_decided(o, "first", "delay_rejected")
    _expect_application_refused(o)


@aio_case("KAN-TC-827")
@allure.story(STORY)
@allure.title("TC-827: A6 — Second Appeal filed: pending in the Commissionerate's queue")
def test_tc827_second_appeal_pending(officer_at):
    """
    Given the application parked at 'second_appeal_pending' (A6)
    When  the officer opens Appeals › Second Appeals — Commissionerate and the appeal
    Then  its row shows Status "Pending" and it can be decided
    And   its disposals include "Final Second Appeal Dismissal" and not "Appeal Dismissed — Refusal Upheld"

    AIO: KAN-TC-827 | KAN-50 AC-4 | data: map state 'second_appeal_pending'
    """
    o = officer_at("second_appeal_pending")
    with allure.step("Second Appeals — Commissionerate: the appeal is pending"):
        n, entry, row = _appeal(o, "second")
        assert row["status"] == M.APPEAL_PENDING, row
        assert entry.get("can_decide") and not entry.get("decided"), entry
    with allure.step("Review & decide: the second appellate disposals"):
        o.appeals.open_appeal(n)
        options = o.appeals.disposal_select.locator("option").evaluate_all("os => os.map(o => o.value)")
        assert "final_dismissal" in options and "dismissed_upheld" not in options, options


@aio_case("KAN-TC-828")
@allure.story(STORY)
@allure.title("TC-828: A6 — second appellate order passed (final dismissal): decided, case closed")
def test_tc828_second_appeal_decided(officer_at):
    """
    Given the application parked at 'second_appeal_decided' (A6: final dismissal)
    When  the officer opens Second Appeals — Commissionerate and the application's review page
    Then  the appeal is decided ("Final Second Appeal Dismissal") and cannot be decided again, and the application
          is still refused

    AIO: KAN-TC-828 | KAN-50 AC-4 | data: map state 'second_appeal_decided'
    """
    o = officer_at("second_appeal_decided")
    _expect_decided(o, "second", "final_dismissal")
    _expect_application_refused(o)
