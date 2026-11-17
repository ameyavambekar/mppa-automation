"""
MPPA Appeals Map — agency side (KAN-49)
=======================================
One test per appeal state of the MPPA Compliance & Appeals Map (Procedure 2, A3–A6:
``test_data.compliance_map_factory.MAP_STATES`` with ``procedure == "Appeals"``, KAN-TC-791…800): what a refused
agency sees on Home, My Application, FORM-III and FORM-IV while its appeal stands there. The officer's side of the
same states is ``tests/admin/test_appeals_map.py`` (KAN-50).

The compliance states of the map (Procedure 1, C1–C10 and the approval branch) are tested with the compliance
loop in ``tests/admin/test_application_review.py`` — agency side KAN-48 (KAN-TC-773…790), officer side KAN-12
(KAN-TC-801…818).

Test data. Each state has its own agency, parked there in the state store (``map_state``) and left there, so the
tests read it again and again without moving it. ``agency_at(state)`` checks on the Officer Console (as the Super
Admin) that the application still stands there, then logs the agency in on a second browser. A state with no
parked agency is skipped — run with RUN_MAP_STATE_TESTS=true to generate one first. Generating an appeal state is
IRREVERSIBLE on dev and slow: a whole review loop to the refusal order first, then the appeal and the appellate
order; a new agency is built and paid when no untouched submission is left.

Every state was generated on dev on 06-Nov-2026 (one agency each) and all 10 cases are Published.

Known defects (defect sheet "MPPA", logged 06-Nov-2026): "I & II Appeal" #70 — FORM-IV is still offered after a
First Appeal is rejected for delay, although the order reads "Case permanently closed." (TC-798 fails on it);
"Agency homepage" #83 — Home still invites "one appeal" to the Division while the First Appeal is pending or after
it is dismissed (not asserted). Earlier: "I & II Appeal" #64 (no confirmation e-mail after filing), #66 (My
Application still invites an appeal after filing), #68 (no e-mail about the appellate order).
"""

import re

import allure
from playwright.sync_api import expect

from test_data.compliance_map_factory import ComplianceMapFactory as M
from test_data.first_appeal_factory import AppealOutcomeFactory, FirstAppealFactory as F
from utils.aio import aio_case
from utils.map_states import APPEAL_HEARING_VENUE, AgencyView

STORY = "Appeals Map — agency"
DATE = r"\d{2} \w{3} \d{4}"                      # 06 Nov 2026


# ---------------------------------------------------------------------------
# Shared checks
# ---------------------------------------------------------------------------
def _expect_status(v: AgencyView, status: str):
    with allure.step(f"My Application shows {status}"):
        v.my_app.open()
        expect(v.my_app.status_banner).to_contain_text(re.compile(rf"Application Status:\s*{status}\b"))


def _first_appeal(v: AgencyView) -> dict:
    """The agency's First Appeal as the Officer Console lists it (id, order number, remarks …)."""
    appeal = v.driver.appeal(v.agency, "first")
    assert appeal, f"No First Appeal is listed for {v.agency.application_id}"
    return appeal


def _expect_first_appeal_decided(v: AgencyView, disposal: str) -> dict:
    """FORM-III shows the decided First Appeal: its order number and the reasons of the order."""
    appeal = _first_appeal(v)
    with allure.step(f"FORM-III: First Appeal #{appeal['id']} decided ({disposal}), order {appeal['order']}"):
        v.first_appeal.open()
        expect(v.first_appeal.appeal_form).to_have_count(0)
        expect(v.first_appeal.filed_appeal_row("Decided on")).to_contain_text(f"Order No. {appeal['order']}")
        expect(v.first_appeal.filed_appeal_row("Authority's remarks")).to_contain_text(
            AppealOutcomeFactory.order(disposal).reasons)
    return appeal


# ---------------------------------------------------------------------------
# Procedure 2 — First and Second Appeal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-791")
@allure.story(STORY)
@allure.title("TC-791: A3 — First Appeal filed: pending with the Division, Second Appeal not open")
def test_tc791_first_appeal_pending(agency_at):
    """
    Given the agency parked at 'first_appeal_pending' (A3: FORM-III filed, no hearing, not decided)
    When  it opens Home, FORM-III and FORM-IV
    Then  Home shows "First Appeal #N filed — sent to …" and "1 of 2 appeals remaining"
    And   FORM-III shows "#N · Your First Appeal — Pending decision" instead of the form
    And   FORM-IV reads "Your First Appeal #N is still pending. You can file a Second Appeal only if it is rejected."

    AIO: KAN-TC-791 | KAN-49 AC-1 | data: map state 'first_appeal_pending'
    """
    v = agency_at("first_appeal_pending")
    n = v.facts["appeal_id"]
    with allure.step(f"Home: First Appeal #{n} filed, one appeal remaining"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_REFUSED)
        expect(v.home.timeline_note(M.TIMELINE_APPEAL_FILED).first).to_contain_text(M.APPEAL_FILED.format(n=n))
        expect(v.home.appeals_remaining).to_have_text(F.HOME_REMAINING.format(n=1))
    with allure.step("FORM-III: the appeal on file, pending"):
        v.first_appeal.open()
        expect(v.first_appeal.appeal_form).to_have_count(0)
        expect(v.first_appeal.filed_appeal_number).to_have_text(f"#{n}")
        expect(v.first_appeal.filed_appeal_title).to_contain_text(re.compile(M.JOURNEY_PENDING, re.I))
        expect(v.first_appeal.journey_status(M.STEP_FIRST)).to_have_text(M.JOURNEY_PENDING)
        expect(v.first_appeal.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))
    with allure.step("FORM-IV: not open while the First Appeal is pending"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(0)
        expect(v.second_appeal.blocking_note).to_contain_text(M.SECOND_WHILE_PENDING.format(n=n))


@aio_case("KAN-TC-792")
@allure.story(STORY)
@allure.title("TC-792: A4 — First Appeal hearing scheduled: the appeal stays pending")
def test_tc792_first_appeal_hearing(agency_at):
    """
    Given the agency parked at 'first_appeal_hearing' (A4: the Division scheduled the appeal hearing)
    When  it opens Home, FORM-III and FORM-IV
    Then  Home's next step reads "Appeal hearing on <date, time> — in person" / "Appear at: <venue>"
    And   Home and FORM-III show the "Appeal hearing" card (In-person hearing, the venue)
    And   the First Appeal is still "Pending decision" and FORM-IV is still closed

    AIO: KAN-TC-792 | KAN-49 AC-1 | data: map state 'first_appeal_hearing'
    """
    v = agency_at("first_appeal_hearing")
    n = v.facts["appeal_id"]
    with allure.step("Home: the appeal hearing is the next step"):
        v.home.open()
        expect(v.home.next_step_heading).to_contain_text(
            re.compile(rf"^{re.escape(M.NEXT_APPEAL_HEARING)}{DATE}, \d{{1,2}}:\d{{2}} [AP]M {re.escape(M.APPEAL_HEARING_IN_PERSON)}"))
        expect(v.home.next_step_banner).to_contain_text(M.APPEAR_AT + APPEAL_HEARING_VENUE)
        expect(v.home.appeal_hearing_card).to_contain_text(APPEAL_HEARING_VENUE)
    with allure.step("FORM-III: still pending, with the hearing"):
        v.first_appeal.open()
        expect(v.first_appeal.appeal_form).to_have_count(0)
        expect(v.first_appeal.journey_status(M.STEP_FIRST)).to_have_text(M.JOURNEY_PENDING)
        card = v.first_appeal.appeal_hearing_card
        expect(card).to_contain_text(M.APPEAL_HEARING_TITLE)
        expect(card).to_contain_text(M.APPEAL_HEARING_MODE)
        expect(card).to_contain_text(APPEAL_HEARING_VENUE)
    with allure.step("FORM-IV: still closed"):
        v.second_appeal.open()
        expect(v.second_appeal.blocking_note).to_contain_text(M.SECOND_WHILE_PENDING.format(n=n))


@aio_case("KAN-TC-793")
@allure.story(STORY)
@allure.title("TC-793: A5 — First Appeal allowed (order set aside): the application is approved")
def test_tc793_first_appeal_allowed(agency_at):
    """
    Given the agency parked at 'first_appeal_allowed' (A5: appeal allowed, refusal set aside)
    When  it opens My Application, Home and FORM-III
    Then  My Application shows APPROVED, Home shows "Registered", and FORM-III shows the decided appeal with its
          order number and reasons

    AIO: KAN-TC-793 | KAN-49 AC-2 | data: map state 'first_appeal_allowed'
    """
    v = agency_at("first_appeal_allowed")
    _expect_status(v, M.MY_APP_APPROVED)
    with allure.step("Home: registered"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_REGISTERED)
    _expect_first_appeal_decided(v, "allowed")


@aio_case("KAN-TC-794")
@allure.story(STORY)
@allure.title("TC-794: A5 — First Appeal allowed with conditions: approved, with the conditions to comply with")
def test_tc794_first_appeal_allowed_conditions(agency_at):
    """
    Given the agency parked at 'first_appeal_allowed_conditions' (A5: appeal allowed with conditions)
    When  it opens My Application, Home and FORM-III
    Then  My Application shows APPROVED, Home shows "Registered", and FORM-III shows the order with its conditions

    AIO: KAN-TC-794 | KAN-49 AC-2 | data: map state 'first_appeal_allowed_conditions'
    """
    v = agency_at("first_appeal_allowed_conditions")
    _expect_status(v, M.MY_APP_APPROVED)
    with allure.step("Home: registered"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_REGISTERED)
    _expect_first_appeal_decided(v, "allowed_conditions")


@aio_case("KAN-TC-795")
@allure.story(STORY)
@allure.title("TC-795: A5 — First Appeal remanded: the application is back in desktop scrutiny")
def test_tc795_first_appeal_remanded(agency_at):
    """
    Given the agency parked at 'first_appeal_remanded' (A5: appeal remanded for re-scrutiny)
    When  it opens My Application, Home and FORM-III
    Then  My Application shows SUBMITTED, Home shows Stage 1 — Desktop Scrutiny under review, and FORM-III shows
          the decided appeal

    AIO: KAN-TC-795 | KAN-49 AC-3 | data: map state 'first_appeal_remanded'
    """
    v = agency_at("first_appeal_remanded")
    _expect_status(v, M.MY_APP_SUBMITTED)
    with allure.step("Home: back in Stage 1"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_UNDER_REVIEW)
        expect(v.home.next_step_heading).to_have_text(M.NEXT_UNDER_REVIEW_1)
    _expect_first_appeal_decided(v, "remanded")


@aio_case("KAN-TC-796")
@allure.story(STORY)
@allure.title("TC-796: A5 — First Appeal dismissed, refusal upheld: FORM-IV opens with the order details locked")
def test_tc796_first_appeal_dismissed(agency_at):
    """
    Given the agency parked at 'first_appeal_dismissed' (A5: dismissed, refusal upheld, no Second Appeal yet)
    When  it opens Home, FORM-III and FORM-IV
    Then  Home shows "First Appeal #N DISMISSED (Order FAA/<year>/<N>)."
    And   FORM-III shows "Your First Appeal — Rejected" with the order number and the authority's remarks
    And   FORM-IV offers the form with the First Appellate order filled in and locked

    AIO: KAN-TC-796 | KAN-49 AC-4 | data: map state 'first_appeal_dismissed'
    """
    v = agency_at("first_appeal_dismissed")
    appeal = _first_appeal(v)
    n, order = appeal["id"], appeal["order"]
    with allure.step("Home: the dismissal in the timeline"):
        v.home.open()
        expect(v.home.timeline_note(M.TIMELINE_APPEAL_DISMISSED).first).to_contain_text(
            f"First Appeal #{n} DISMISSED (Order {order}).")
    _expect_first_appeal_decided(v, "dismissed_upheld")
    with allure.step("FORM-III: rejected"):
        expect(v.first_appeal.filed_appeal_title).to_contain_text(re.compile(M.JOURNEY_REJECTED, re.I))
        expect(v.first_appeal.journey_status(M.STEP_FIRST)).to_have_text(M.JOURNEY_REJECTED)
    with allure.step("FORM-IV: the form, with the First Appellate order locked"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(1)
        assert v.second_appeal.get_order_number() == order
        expect(v.second_appeal.order_locked_note.first).to_contain_text(F.ORDER_LOCKED)


@aio_case("KAN-TC-797")
@allure.story(STORY)
@allure.title("TC-797: A5 — First Appeal dismissed for default of appearance: decided, application still refused")
def test_tc797_first_appeal_dismissed_default(agency_at):
    """
    Given the agency parked at 'first_appeal_dismissed_default' (A5: dismissed for default of appearance)
    When  it opens My Application and FORM-III
    Then  My Application shows REJECTED, and FORM-III shows the decided appeal, no longer pending

    AIO: KAN-TC-797 | KAN-49 AC-5 | data: map state 'first_appeal_dismissed_default'
    """
    v = agency_at("first_appeal_dismissed_default")
    _expect_status(v, M.MY_APP_REJECTED)
    _expect_first_appeal_decided(v, "dismissed_default")
    expect(v.first_appeal.journey_status(M.STEP_FIRST)).not_to_have_text(M.JOURNEY_PENDING)


@aio_case("KAN-TC-798")
@allure.story(STORY)
@allure.title("TC-798: A5 — First Appeal rejected for delay: the case is closed and FORM-IV is not offered")
def test_tc798_first_appeal_delay_rejected(agency_at):
    """
    Given the agency parked at 'first_appeal_delay_rejected' (A5: delay condonation rejected, case closed)
    When  it opens My Application, FORM-III and FORM-IV
    Then  My Application shows REJECTED, FORM-III shows the decided appeal and FORM-IV offers no form

    Fails on dev (06-Nov-2026): FORM-IV still offers the Second Appeal form, although the order's effect reads
    "… Case permanently closed." — defect "I & II Appeal" #70.

    AIO: KAN-TC-798 | KAN-49 AC-5 | data: map state 'first_appeal_delay_rejected'
    """
    v = agency_at("first_appeal_delay_rejected")
    _expect_status(v, M.MY_APP_REJECTED)
    _expect_first_appeal_decided(v, "delay_rejected")
    with allure.step("FORM-IV: no Second Appeal"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(0)


@aio_case("KAN-TC-799")
@allure.story(STORY)
@allure.title("TC-799: A6 — Second Appeal filed: pending with the Commissionerate, no appeal left")
def test_tc799_second_appeal_pending(agency_at):
    """
    Given the agency parked at 'second_appeal_pending' (A6: FORM-IV filed, not decided)
    When  it opens FORM-IV and My Application
    Then  FORM-IV shows the Second Appeal "Pending decision" instead of the form and "Appeals remaining: 0 of 2"
    And   My Application shows REJECTED

    AIO: KAN-TC-799 | KAN-49 AC-6 | data: map state 'second_appeal_pending'
    """
    v = agency_at("second_appeal_pending")
    with allure.step("FORM-IV: the Second Appeal pending, no appeal left"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(0)
        expect(v.second_appeal.journey_status(M.STEP_SECOND)).to_have_text(M.JOURNEY_PENDING)
        expect(v.second_appeal.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=0))
    _expect_status(v, M.MY_APP_REJECTED)


@aio_case("KAN-TC-800")
@allure.story(STORY)
@allure.title("TC-800: A6 — second appellate order passed (final dismissal): the case is closed")
def test_tc800_second_appeal_decided(agency_at):
    """
    Given the agency parked at 'second_appeal_decided' (A6: final dismissal by the Commissionerate)
    When  it opens FORM-IV and My Application
    Then  FORM-IV shows the Second Appeal decided (no longer pending) and offers no form
    And   My Application shows REJECTED

    AIO: KAN-TC-800 | KAN-49 AC-7 | data: map state 'second_appeal_decided'
    """
    v = agency_at("second_appeal_decided")
    with allure.step("FORM-IV: decided, no form"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(0)
        expect(v.second_appeal.journey_status(M.STEP_SECOND)).not_to_have_text(M.JOURNEY_PENDING)
        expect(v.second_appeal.journey_status(M.STEP_SECOND)).not_to_have_text(re.compile("Not filed"))
    _expect_status(v, M.MY_APP_REJECTED)
