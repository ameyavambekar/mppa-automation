"""
Application review — desktop scrutiny and compliance (KAN-12 officer side, KAN-48 agency side)
==============================================================================================
Covers KAN-TC-745…768: the officer's review of a submitted application on
/module/admin/dashboard/agency_view.php and the compliance loop that follows (flowchart C2–C10) —
review (Approve / On Hold) → Compliance 1 → the agency corrects and replies (Corrections page) → the reply
is taken into review → show cause notice and personal hearing → window to correct → the agency replies
again → the second reply is taken into review → speaking refusal order.

Read-only (always run): TC-745…749 open an application nobody has reviewed yet and save nothing (the
client refuses the incomplete review); TC-750/751 read an application refused through the loop (prepare one
with ``python -m utils.seed_appeals`` if none exists).

The loop chain TC-752…768 runs only with RUN_REVIEW_WORKFLOW_TESTS=true. Each test moves one application
one step on and cannot be undone; the tests find their application by the stage its review page shows
(``ReviewStage``), so run them in file order — a full run takes one untouched submission to a refusal
order (recorded as ``rejected``, ready for the First Appeal tests). The negative tests in the chain are
refused on the client and change nothing. TC-755…758 need an item still to correct; when TC-758 has used the
last one, ``agency_with_corrections`` sends Compliance 1 on an untouched submission first, so they can run on
their own.

The approval path (the reply to Compliance 1 cures the deficiency → Approve Desktop Scrutiny → Physical
Verification → final approval) is the last test in the file, behind the same flag. It corrects and replies as
the agency itself, so it takes an application with an item still to correct — after a full chain run that is
an untouched submission, which it sends to Compliance 1 first.

Compliance states (read only, always run). The compliance half of the MPPA Compliance & Appeals Map (Procedure 1:
C1–C10 and the approval branch, ``test_data.compliance_map_factory.MAP_STATES`` with ``procedure == "Compliance"``)
has one test per state and side at the end of this file: what the agency sees on Home, My Application and
Corrections (KAN-TC-773…790, story KAN-48, fixture ``agency_at``) and what the Officer Console shows — review page,
Applications lists, Licences & certificates (KAN-TC-801…818, story KAN-12, fixture ``officer_at``). Each state has
its own agency, parked there in the state store (``map_state``) on 06-Nov-2026 and left there; the tests only read
it. A state with no parked agency is skipped — run with RUN_MAP_STATE_TESTS=true to generate one first
(IRREVERSIBLE on dev). The loop chain above never uses a parked agency. The appeal states of the map are in
``tests/test_appeals_map.py`` (KAN-49) and ``tests/admin/test_appeals_map.py`` (KAN-50).

Known defects in the compliance states (defect sheet "MPPA", logged 06-Nov-2026):
- "Agency homepage" #81: Home still shows the 45-day clock paused after the reply (TC-778 fails on it).
- "Super admin" #89: an application given a post-hearing window (C7 onwards, including those later refused or
  approved) makes every Applications list it is in fail to load — "The list could not be loaded (Ref …)" — even
  when searched by its own ID (TC-810, TC-811, TC-815 fail on it). Lists are searched by Application ID anyway:
  Approved / All applications fail unfiltered ("Super admin" #70).
- Not asserted: "Agency homepage" #82 (the officer's note "Post-hearing reply received — …" on the agency's
  timeline), "I & II Appeal" #71 (after the show cause notice Corrections badges the item still On Hold "Accepted by
  officer"), "Super admin" #90 (with every item approved after the first reply the show cause form is still shown
  beside "Approve Desktop Scrutiny").
"""

import re
from datetime import datetime, timedelta

import allure
from playwright.sync_api import expect

from pages.admin.application_review_page import AdminApplicationReviewPage, ReviewStage
from pages.admin.applications_page import AdminApplicationsPage
from pages.admin.licenses_page import AdminLicensesPage
from test_data.application_review_factory import ReviewLoopFactory as F
from test_data.compliance_map_factory import ComplianceMapFactory as M
from test_data.first_appeal_factory import FirstAppealFactory as FA
from utils.aio import aio_case
from utils.map_states import AgencyView, OfficerView
from utils.review_loop import record_loop_stage
from utils.state_store import TestStateStore

STORY = "Application review — desktop scrutiny loop"
COMPLIANCE_STORY = "Compliance loop — agency side"
HOLD = F.HOLD_ITEM_LABEL
HOLD_KEY = F.loop().hold_item
HEAD_OFFICE_BARS = {"ph_signboard", "ph_exterior", "ph_interior"}
DATE = r"\d{2} \w{3} \d{4}"                      # 06 Nov 2026
NO_ACTION = "No action is needed from you now."


def _listed_under(review: AdminApplicationReviewPage, step: str, application_id: str):
    applications = AdminApplicationsPage(review.page)
    # searched by ID: on dev the unfiltered list fails to load once any application had a post-hearing window
    applications.open("desktop", step, query=application_id)
    return applications.row_by_application_id(application_id)


def _agency_corrects_and_replies(corrections, agency, data, label=HOLD):
    """The agency saves ``label`` with a note (filling any required field the section left blank from its
    record) and sends its reply."""
    corrections.open()
    corrections.open_section(label)
    corrections.fill_blank_fields(label, {"email": agency.email, "mobile": agency.mobile})
    corrections.save_section(label, data.correction_note)
    expect(corrections.item_badge(label)).to_have_text(F.CORR_DONE_BADGE)
    return corrections.submit_reply(data.reply_text)


# ═══════════════════════════════════════════════════════════════════════════
# Read-only
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-745")
@allure.story(STORY)
@allure.title("TC-745: Review page of a new submission shows the review step and every item Not reviewed")
def test_tc745_new_submission_review_page(new_application_review):
    """
    Given I am logged in as the Super Administrator
    And   a state-store agency's application nobody has reviewed yet
    When  I open its review page from Applications › Desktop scrutiny
    Then  it shows "Stage 1 — Desktop Scrutiny · Under review", the four-step track with Review current,
          every item "Not reviewed", "All changes saved · N not reviewed" and no next-step button

    AIO: KAN-TC-745 | KAN-12 C2
    """
    review, agency = new_application_review
    bars = review.review_data()

    with allure.step("Verify the header and the processing stage"):
        expect(review.main).to_contain_text(agency.application_id)
        expect(review.main).to_contain_text(re.compile("submitted", re.I))
        expect(review.stage_subtitle).to_have_text(F.STAGE_UNDER_REVIEW)
        expect(review.compliance_track.locator("b")).to_have_text(F.TRACK)
        expect(review.compliance_track.first).to_have_class(re.compile(r"\bon\b"))

    with allure.step("Verify every item is Not reviewed and the save bar counts them"):
        assert bars and all(b["orig"] == "pending" for b in bars), bars
        assert {"part_a", "part_c", "part_f", "declaration", "authorisation"} <= {b["key"] for b in bars}
        expect(review.review_summary).to_have_text(f"{F.ALL_SAVED} · {len(bars)} not reviewed")
        expect(review.decision_block).to_contain_text(f"Review the remaining {len(bars)} item(s)")
        expect(review.flow_buttons).to_have_count(0)


@aio_case("KAN-TC-746")
@allure.story(STORY)
@allure.title("TC-746: Every review item offers Approve or On Hold with the listed reasons")
def test_tc746_review_choices_and_reasons(new_application_review):
    """
    Given the review page of an application nobody has reviewed yet
    When  I look at each review item
    Then  each offers Approve and On Hold, the nine On Hold reasons (with Others) and a remark box of at most
          1000 characters with the "required for Others" hint

    AIO: KAN-TC-746 | KAN-12 C2
    """
    review, _ = new_application_review

    with allure.step("Read every review item"):
        bars = review.review_data()

    with allure.step("Verify the choices, reasons and remark box of each"):
        for bar in bars:
            assert bar["choices"] == F.CHOICES, bar
            assert bar["reasons"] == F.HOLD_REASONS, bar
            assert bar["remark_placeholder"] == F.REMARK_PLACEHOLDER, bar
            assert bar["remark_max"] == F.REMARK_MAX, bar


@aio_case("KAN-TC-747")
@allure.story(STORY)
@allure.title("TC-747: On Hold without a reason cannot be saved")
def test_tc747_hold_without_reason_not_saved(new_application_review):
    """
    Given the review page of an application nobody has reviewed yet
    When  I put Part A On Hold without a reason and click Save review
    Then  Part A shows "Select a reason", the save bar counts 1 unsaved change and 1 needing a reason, and
          the review is not saved

    AIO: KAN-TC-747 | KAN-12 C2 (negative)
    """
    review, _ = new_application_review
    check = F.hold_without_reason()

    with allure.step("Put Part A On Hold without a reason"):
        review.mark_item(check.item, check.choice, check.reason)
        expect(review.review_bar_problem(check.item)).to_have_text(check.expected_problem)
        expect(review.review_summary).to_contain_text("1 unsaved change(s)")
        expect(review.review_summary).to_contain_text("1 need a reason")

    with allure.step("Click Save review"):
        error = review.save_review_expecting_refusal()
        assert check.expected_error in error, f"expected '{check.expected_error}', got '{error}'"

    with allure.step("Verify nothing was saved"):
        review.reload_discarding_changes()
        expect(review.review_bar(check.item)).to_have_attribute("data-orig", "pending")


@aio_case("KAN-TC-748")
@allure.story(STORY)
@allure.title("TC-748: On Hold for \"Others\" needs at least 50 characters of details")
def test_tc748_others_needs_50_characters(new_application_review):
    """
    Given the review page of an application nobody has reviewed yet
    When  I put Part A On Hold for "Others" with a remark under 50 characters and click Save review
    Then  Part A shows "Others: write at least 50 characters (n/50)" and the review is not saved

    AIO: KAN-TC-748 | KAN-12 C2 (negative)
    """
    review, _ = new_application_review
    check = F.others_short_remark()

    with allure.step(f"Put Part A On Hold for Others with '{check.remark}'"):
        review.mark_item(check.item, check.choice, check.reason, check.remark)
        expect(review.review_bar_problem(check.item)).to_have_text(check.expected_problem)

    with allure.step("Click Save review"):
        error = review.save_review_expecting_refusal()
        assert check.expected_error in error, f"expected '{check.expected_error}', got '{error}'"

    with allure.step("Verify nothing was saved"):
        review.reload_discarding_changes()
        expect(review.review_bar(check.item)).to_have_attribute("data-orig", "pending")


@aio_case("KAN-TC-749")
@allure.story(STORY)
@allure.title("TC-749: Unsaved review choices are counted on the save bar")
def test_tc749_unsaved_changes_counted(new_application_review):
    """
    Given the review page of an application nobody has reviewed yet (N items)
    When  I approve two items without saving
    Then  the save bar reads "2 unsaved change(s) · N-2 not reviewed"
    And   leaving the page asks to confirm, and afterwards both items are Not reviewed again

    AIO: KAN-TC-749 | KAN-12 C2 (edge)
    """
    review, _ = new_application_review
    total = review.review_bars.count()

    with allure.step("Approve two items without saving"):
        for key in F.NEXT_ITEMS:
            review.mark_item(key, "approved")
        expect(review.review_summary).to_have_text(f"2 unsaved change(s) · {total - 2} not reviewed")

    with allure.step("Reload, leaving the unsaved changes"):
        prompt = review.reload_discarding_changes()
        assert prompt == "beforeunload", f"no leave-page prompt with unsaved changes (got '{prompt}')"

    with allure.step("Verify both items are Not reviewed again"):
        for key in F.NEXT_ITEMS:
            expect(review.review_bar(key)).to_have_attribute("data-orig", "pending")
        expect(review.review_summary).to_have_text(f"{F.ALL_SAVED} · {total} not reviewed")


@aio_case("KAN-TC-750")
@allure.story(STORY)
@allure.title("TC-750: A refused application is read-only")
def test_tc750_refused_application_read_only(refused_application_review):
    """
    Given an application refused at the end of the review loop
    When  I open its review page
    Then  it shows REJECTED, "Stage Refused", "Refused · Closed" and the read-only banner
    And   there is no Save review bar, no Approve / On Hold choice and no next-step button

    AIO: KAN-TC-750 | KAN-12 C10
    """
    review, _ = refused_application_review

    with allure.step("Verify the refused state"):
        expect(review.main).to_contain_text(F.REJECTED_BADGE)
        expect(review.main).to_contain_text(F.REFUSED_STAGE)
        expect(review.stage_subtitle).to_have_text("Refused · Closed")
        expect(review.read_only_banner).to_contain_text(F.READ_ONLY)

    with allure.step("Verify nothing can be reviewed or decided"):
        expect(review.save_review_button).to_have_count(0)
        expect(review.page.locator(".rv[data-key] input[type=radio]:enabled")).to_have_count(0)
        expect(review.flow_buttons).to_have_count(0)
        expect(review.refuse_button).to_have_count(0)


@aio_case("KAN-TC-751")
@allure.story(STORY)
@allure.title("TC-751: A refused application's history records the whole review loop")
def test_tc751_refused_history_records_loop(refused_application_review):
    """
    Given an application refused at the end of the review loop
    When  I read its Processing history
    Then  it lists, oldest first: Submitted, Deficiency, Agency Reply, Accept Reply, Scn Hearing, Grant Window,
          Agency Reply, Accept Reply, Division Report, Refuse — each with its notice text

    AIO: KAN-TC-751 | KAN-12 C3–C10
    """
    review, _ = refused_application_review

    with allure.step("Read the history"):
        history = review.history()
        loop = history[:history.index("Refuse") + 1] if "Refuse" in history else history

    with allure.step("Verify the steps up to the refusal and their order (appeal entries may follow)"):
        assert loop == F.LOOP_HISTORY, history

    with allure.step("Verify the notice texts"):
        expect(review.history_entry("Deficiency")).to_contain_text(F.C1_HISTORY)
        expect(review.history_entry("Scn Hearing")).to_contain_text(F.SCN_HISTORY)
        expect(review.history_entry("Refuse")).to_contain_text(F.REFUSE_HISTORY)


# ═══════════════════════════════════════════════════════════════════════════
# Review loop chain — RUN_REVIEW_WORKFLOW_TESTS=true, in this order
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-752")
@allure.story(STORY)
@allure.title("TC-752: Saving the review with an item On Hold offers Compliance 1")
def test_tc752_save_review_with_hold(review_workflow_allowed, new_application_review, review_loop_data):
    """
    Given an application nobody has reviewed yet
    When  I put Part A On Hold (Incomplete Application Form Details + remark), approve every other item and
          click Save review
    Then  the review is saved ("All changes saved"), Part A is On Hold and every other item Approved
    And   "Decision & next step" offers "Send Compliance 1 (1)"

    AIO: KAN-TC-752 | KAN-12 C2
    """
    review, agency = new_application_review
    d = review_loop_data

    with allure.step("Save the review with Part A On Hold"):
        review.save_review_with_hold(d.hold_item, d.hold_reason, d.hold_remark)
        record_loop_stage(agency, ReviewStage.HELD)

    with allure.step("Verify the saved review"):
        expect(review.review_summary).to_have_text(F.ALL_SAVED)
        bars = review.review_data()
        assert {b["key"]: b["orig"] for b in bars if b["orig"] != "approved"} == {d.hold_item: "on_hold"}, bars

    with allure.step("Verify Compliance 1 is offered"):
        expect(review.flow_button("deficiency")).to_have_text(F.SEND_C1)
        expect(review.flow_button("deficiency")).to_have_attribute("data-confirm", F.C1_CONFIRM)


@aio_case("KAN-TC-753")
@allure.story(STORY)
@allure.title("TC-753: Next steps are blocked while a review change is unsaved")
def test_tc753_flow_blocked_with_unsaved_change(review_workflow_allowed, application_at):
    """
    Given an application whose review is saved with Part A On Hold (Compliance 1 not sent)
    When  I change another item without saving and click "Send Compliance 1"
    Then  the button is blocked ("Save your review first") and nothing is sent
    And   after reloading without saving, "Send Compliance 1 (1)" is offered again

    AIO: KAN-TC-753 | KAN-12 C3 (edge)
    """
    review, _ = application_at(ReviewStage.HELD)

    with allure.step("Change an item without saving"):
        review.mark_item(F.NEXT_ITEMS[0], "on_hold", "incomplete_form")
        expect(review.flow_button("deficiency")).to_have_class(re.compile(r"\bis-blocked\b"))
        expect(review.flow_button("deficiency")).to_have_attribute("title", F.FLOW_BLOCKED_TITLE)

    with allure.step("Click Send Compliance 1"):
        error = review.run_flow_expecting_refusal("deficiency")
        assert F.FLOW_BLOCKED_ERROR in error, f"expected '{F.FLOW_BLOCKED_ERROR}', got '{error}'"

    with allure.step("Reload without saving"):
        review.reload_discarding_changes()
        assert review.stage() == ReviewStage.HELD
        expect(review.flow_button("deficiency")).not_to_have_class(re.compile(r"\bis-blocked\b"))


@aio_case("KAN-TC-754")
@allure.story(STORY)
@allure.title("TC-754: Sending Compliance 1 returns the items on hold to the agency")
def test_tc754_send_compliance_1(review_workflow_allowed, application_at):
    """
    Given an application whose review is saved with Part A On Hold
    When  I click "Send Compliance 1 (1)" and confirm
    Then  the confirmation says the agency gets 15 working days for 1 item
    And   the page shows the reply date "— awaiting the agency", Part A "Awaiting agency" in "Requested
          corrections (round 1)" and the "Deficiency" history entry
    And   the application is listed under Desktop scrutiny › Compliance — with agency

    AIO: KAN-TC-754 | KAN-12 C3
    """
    review, agency = application_at(ReviewStage.HELD)

    with allure.step("Send Compliance 1"):
        prompt = review.run_flow("deficiency")
        record_loop_stage(agency, ReviewStage.WITH_AGENCY)
        assert prompt == F.C1_CONFIRM, prompt

    with allure.step("Verify the application waits for the agency"):
        expect(review.processing_panel).to_contain_text(F.AWAITING_AGENCY)
        expect(review.requested_corrections).to_contain_text("Requested corrections (round 1)")
        expect(review.requested_corrections).to_contain_text(HOLD)
        expect(review.requested_corrections).to_contain_text(F.AWAITING_BADGE)
        expect(review.flow_buttons.locator("visible=true")).to_have_count(0)

    with allure.step("Verify the history"):
        expect(review.history_entry("Deficiency")).to_contain_text(F.C1_HISTORY)
        expect(review.history_entry("Deficiency")).to_contain_text(HOLD)

    with allure.step("Verify the application is listed under Compliance — with agency"):
        expect(_listed_under(review, "agency", agency.application_id)).to_have_count(1)


@aio_case("KAN-TC-755")
@allure.story(STORY)
@allure.title("TC-755: The agency's Home asks for corrections after Compliance 1")
def test_tc755_agency_home_action_required(review_workflow_allowed, agency_with_corrections):
    """
    Given the agency's application has a Compliance 1 notice it has not answered
    When  the agency opens Home
    Then  it reads "Action required: the officer has asked for corrections" with "1 item(s) need your
          attention · reply by …"
    And   Application progress shows "Compliance 1 — deficiency notice, awaiting reply" and "45-day clock
          paused (Rule 4(4))"

    AIO: KAN-TC-755 | KAN-12 C3/C4
    """
    _, home, _, _ = agency_with_corrections(after_hearing=False, open_items=True)

    with allure.step("Open Home"):
        home.open()

    with allure.step("Verify the action-required banner"):
        expect(home.next_step_heading).to_contain_text(F.HOME_ACTION_REQUIRED)
        expect(home.next_step_text).to_contain_text(re.compile(r"1 item\(s\) need your attention · reply by \d{2} \w{3} \d{4}"))

    with allure.step("Verify Application progress"):
        expect(home.progress_subtitle).to_contain_text(F.HOME_STAGE_C1)
        expect(home.progress_card).to_contain_text(F.HOME_CLOCK_PAUSED)


@aio_case("KAN-TC-756")
@allure.story(STORY)
@allure.title("TC-756: Corrections lists the items on hold and hides the reply until they are answered")
def test_tc756_corrections_lists_items(review_workflow_allowed, agency_with_corrections, review_loop_data):
    """
    Given the agency's application has a Compliance 1 notice it has not answered
    When  the agency opens Corrections
    Then  it reads "1 item(s) still to correct · Reply by YYYY-MM-DD"
    And   Part A — Agency details shows "Correction needed", the officer's reason and remark and "Correct details"
    And   the reply form is not shown

    AIO: KAN-TC-756 | KAN-12 C4
    """
    corrections, _, _, _ = agency_with_corrections(after_hearing=False, open_items=True)
    d = review_loop_data

    with allure.step("Open Corrections"):
        corrections.open()

    with allure.step("Verify the item on hold"):
        expect(corrections.subtitle).to_have_text(re.compile(r"1 item\(s\) still to correct · Reply by \d{4}-\d{2}-\d{2}"))
        expect(corrections.item_badge(HOLD)).to_have_text(F.CORR_OPEN_BADGE)
        expect(corrections.item_remarks(HOLD)).to_contain_text("Incomplete Application Form Details")
        expect(corrections.item_remarks(HOLD)).to_contain_text(d.hold_remark)
        expect(corrections.correct_details_button(HOLD)).to_be_visible()

    with allure.step("Verify the reply form is hidden"):
        expect(corrections.reply_section).to_be_hidden()


@aio_case("KAN-TC-757")
@allure.story(STORY)
@allure.title("TC-757: Saving a correction unchanged without a note is refused")
def test_tc757_unchanged_correction_needs_note(review_workflow_allowed, agency_with_corrections):
    """
    Given the agency's application has a Compliance 1 notice it has not answered
    When  the agency opens Part A with "Correct details"
    Then  the fields show the submitted values
    When  it saves without changing anything and without a note
    Then  an error is shown and Part A stays "Correction needed"

    Fails on dev (05-Nov-2026): the form opens with e-mail and mobile blank — defect #69 ("I & II Appeal" tab).

    AIO: KAN-TC-757 | KAN-12 C4 (negative)
    """
    corrections, _, agency, _ = agency_with_corrections(after_hearing=False, open_items=True)

    with allure.step("Open Part A for correction"):
        corrections.open()
        corrections.open_section(HOLD)

    with allure.step("Verify the submitted e-mail and mobile are filled in"):
        expect(corrections.section_field(HOLD, "email")).to_have_value(agency.email)
        expect(corrections.section_field(HOLD, "mobile")).to_have_value(agency.mobile)

    with allure.step("Save without a change and without a note"):
        corrections.save_section(HOLD, "")
        expect(corrections.section_error(HOLD)).to_be_visible()
        corrections.open()
        expect(corrections.item_badge(HOLD)).to_have_text(F.CORR_OPEN_BADGE)


@aio_case("KAN-TC-758")
@allure.story(STORY)
@allure.title("TC-758: The agency answers a correction with a note")
def test_tc758_correction_saved_with_note(review_workflow_allowed, agency_with_corrections, review_loop_data):
    """
    Given the agency's application has a Compliance 1 notice it has not answered
    When  the agency saves Part A with a note and confirms
    Then  the confirmation warns the section is then locked
    And   Part A shows "Corrected" and "Submitted and locked", and the reply form appears

    AIO: KAN-TC-758 | KAN-12 C4
    """
    corrections, _, agency, _ = agency_with_corrections(after_hearing=False, open_items=True)
    d = review_loop_data

    with allure.step("Save Part A with a note"):
        corrections.open()
        corrections.open_section(HOLD)
        corrections.fill_blank_fields(HOLD, {"email": agency.email, "mobile": agency.mobile})
        prompt = corrections.save_section(HOLD, d.correction_note)
        assert prompt == F.CORR_SAVE_CONFIRM, prompt

    with allure.step("Verify Part A is corrected and locked"):
        expect(corrections.item_badge(HOLD)).to_have_text(F.CORR_DONE_BADGE)
        expect(corrections.item_locked_note(HOLD)).to_have_text(F.CORR_LOCKED)
        expect(corrections.subtitle).to_contain_text(F.CORR_ALL_DONE)
        expect(corrections.reply_section).to_be_visible()


@aio_case("KAN-TC-759")
@allure.story(STORY)
@allure.title("TC-759: A reply shorter than 10 characters is not sent")
def test_tc759_short_reply_not_sent(review_workflow_allowed, agency_with_corrections):
    """
    Given every item of the agency's Compliance 1 is corrected and the reply is not sent
    When  the agency submits a reply of 5 characters
    Then  the submit is blocked with a message asking for at least 10 characters (the browser's own, as the box
          has minlength 10) and nothing is sent

    AIO: KAN-TC-759 | KAN-12 C4 (negative)
    """
    corrections, _, _, _ = agency_with_corrections(after_hearing=False, open_items=False)
    check = F.short_reply()

    with allure.step("Open Corrections"):
        corrections.open()
        expect(corrections.reply_section).to_be_visible()

    with allure.step(f"Submit the reply '{check.fields['text']}'"):
        prompt, toast = corrections.submit_reply(check.fields["text"])
        assert not prompt, f"the short reply was offered for sending: {prompt}"
        assert check.expected_error in toast, f"expected '{check.expected_error}', got '{toast}'"

    with allure.step("Verify the reply was not sent"):
        corrections.open()
        expect(corrections.reply_section).to_be_visible()


@aio_case("KAN-TC-760")
@allure.story(STORY)
@allure.title("TC-760: The agency sends its reply and the officer can take it into review")
def test_tc760_agency_reply_reaches_officer(review_workflow_allowed, agency_with_corrections, review_loop_data):
    """
    Given every item of the agency's Compliance 1 is corrected and the reply is not sent
    When  the agency submits its reply and confirms
    Then  Corrections reads "Your corrections and reply have been submitted — the officer is reviewing them."
    And   the officer's review page shows the "Agency Reply" entry and offers "Take reply into review"

    AIO: KAN-TC-760 | KAN-12 C4
    """
    corrections, _, agency, review = agency_with_corrections(after_hearing=False, open_items=False)
    d = review_loop_data

    with allure.step("Send the reply"):
        corrections.open()
        prompt, _ = corrections.submit_reply(d.reply_text)
        assert prompt == F.REPLY_CONFIRM, prompt
        record_loop_stage(agency, ReviewStage.REPLY_RECEIVED)
        expect(corrections.subtitle).to_have_text(F.REPLY_SENT)

    with allure.step("Verify the officer sees the reply"):
        review.page.reload()
        review.wait_for_load()
        expect(review.history_entry("Agency Reply")).to_contain_text(d.reply_text)
        expect(review.history_entry("Agency Reply")).to_contain_text(HOLD)
        expect(review.flow_button("accept_reply")).to_contain_text(F.TAKE_REPLY)


@aio_case("KAN-TC-761")
@allure.story(STORY)
@allure.title("TC-761: A reply that does not cure the deficiency leads to the show cause notice")
def test_tc761_reply_still_on_hold_leads_to_show_cause(review_workflow_allowed, application_at, review_loop_data):
    """
    Given the agency has replied to Compliance 1
    When  I take the reply into review, keep Part A On Hold and save
    Then  the history shows "Reply to Compliance 1 received — review the corrected items again."
    And   the show cause form appears and Compliance 1 is not offered again

    AIO: KAN-TC-761 | KAN-12 C5
    """
    review, agency = application_at(ReviewStage.REPLY_RECEIVED, after_hearing=False)
    d = review_loop_data

    with allure.step("Take the reply into review"):
        review.run_flow("accept_reply")
        record_loop_stage(agency, ReviewStage.IN_REVIEW)
        expect(review.history_entry("Accept Reply")).to_contain_text(F.ACCEPT_REPLY_1)

    with allure.step("Keep Part A On Hold and save"):
        review.save_review_with_hold(d.hold_item, d.hold_reason, d.hold_remark)
        record_loop_stage(agency, ReviewStage.SHOW_CAUSE_DUE)

    with allure.step("Verify the show cause form"):
        expect(review.issue_scn_button).to_be_visible()
        expect(review.scn_reason_select).to_be_visible()
        expect(review.scn_grounds_input).to_be_visible()
        expect(review.hearing_mode_radio("personal")).to_be_attached()
        expect(review.hearing_at_input).to_be_visible()
        expect(review.hearing_venue_input).to_be_visible()
        expect(review.flow_button("deficiency")).to_have_count(0)


@aio_case("KAN-TC-762")
@allure.story(STORY)
@allure.title("TC-762: The show cause notice needs a ground, details and a hearing time")
def test_tc762_show_cause_client_checks(review_workflow_allowed, application_at):
    """
    Given Part A is still On Hold after the reply to Compliance 1 and no show cause notice is issued
    When  I click Issue without a ground, with details under 20 characters, and without a hearing time
    Then  each is refused with its message and nothing is issued

    AIO: KAN-TC-762 | KAN-12 C6 (negative)
    """
    review, _ = application_at(ReviewStage.SHOW_CAUSE_DUE)

    for check in F.show_cause_checks():
        with allure.step(f"Try '{check.scenario_label}'"):
            review.fill_show_cause(check.fields["reason"], check.fields["grounds"], "",
                                   check.fields["minutes_ahead"])
            error = review.issue_show_cause_expecting_refusal()
            assert error == check.expected_error, f"{check.scenario_label}: expected '{check.expected_error}', got '{error}'"

    with allure.step("Verify nothing was issued"):
        review.page.reload()
        review.wait_for_load()
        assert review.stage() == ReviewStage.SHOW_CAUSE_DUE


@aio_case("KAN-TC-763")
@allure.story(STORY)
@allure.title("TC-763: Issuing the show cause notice schedules a personal hearing")
def test_tc763_issue_show_cause(review_workflow_allowed, application_at, review_loop_data):
    """
    Given Part A is still On Hold after the reply to Compliance 1 and no show cause notice is issued
    When  I issue the show cause notice (Inadequate / Unsatisfactory Rectification) with a personal hearing
    Then  the confirmation asks to schedule a personal hearing
    And   the "Scn Hearing" history entry gives the hearing date and time, the venue and the grounds
    And   the hearing record form is shown and the application is listed under Show cause / hearing

    AIO: KAN-TC-763 | KAN-12 C6
    """
    review, agency = application_at(ReviewStage.SHOW_CAUSE_DUE)
    d = review_loop_data

    with allure.step("Issue the show cause notice"):
        prompt = review.issue_show_cause(d.scn_reason, d.scn_grounds, d.hearing_venue, d.hearing_minutes_ahead)
        record_loop_stage(agency, ReviewStage.HEARING_DUE)
        assert prompt == F.SCN_CONFIRM, prompt

    with allure.step("Verify the history entry"):
        entry = review.history_entry("Scn Hearing")
        expect(entry).to_contain_text(F.SCN_HISTORY)
        expect(entry).to_contain_text(d.hearing_venue)
        expect(entry).to_contain_text(f"{F.SCN_GROUND_LABEL} — {d.scn_grounds}")

    with allure.step("Verify the hearing record form"):
        expect(review.grant_window_button).to_be_visible()

    with allure.step("Verify the application is listed under Show cause / hearing"):
        expect(_listed_under(review, "hearing", agency.application_id)).to_have_count(1)


@aio_case("KAN-TC-764")
@allure.story(STORY)
@allure.title("TC-764: Recording the hearing gives the agency a window to correct")
def test_tc764_grant_window(review_workflow_allowed, application_at, review_loop_data):
    """
    Given a show cause notice is issued and the hearing is not recorded
    When  I record the hearing (attended), give 3 days and confirm
    Then  the form offers 3 to 7 days
    And   the "Grant Window" entry gives 3 days, a reply date 3 days ahead and the hearing record

    AIO: KAN-TC-764 | KAN-12 C7
    """
    review, agency = application_at(ReviewStage.HEARING_DUE)
    d = review_loop_data

    with allure.step("Verify the window form"):
        assert review.select_options(review.window_days_select) == F.WINDOW_DAYS
        expect(review.attendance_select).to_be_visible()
        expect(review.hearing_record_input).to_be_visible()

    with allure.step("Record the hearing and give 3 days"):
        prompt = review.grant_window(d.attendance, d.window_days, d.hearing_record)
        record_loop_stage(agency, ReviewStage.WITH_AGENCY)
        assert prompt == F.WINDOW_CONFIRM, prompt

    with allure.step("Verify the history entry"):
        due = (datetime.now() + timedelta(days=int(d.window_days))).strftime("%d %b %Y")
        entry = review.history_entry("Grant Window")
        expect(entry).to_contain_text(f"You have {d.window_days} days to correct")
        expect(entry).to_contain_text(f"reply by {due}")
        expect(entry).to_contain_text(d.hearing_record)


@aio_case("KAN-TC-765")
@allure.story(STORY)
@allure.title("TC-765: The agency corrects again within the window and replies")
def test_tc765_agency_replies_again(review_workflow_allowed, agency_with_corrections, review_loop_data):
    """
    Given the window to correct after the hearing is open
    When  the agency saves Part A with a note and sends its reply
    Then  both are accepted
    And   the officer sees "Requested corrections (round 2)", a second "Agency Reply" and "Take reply into review"

    AIO: KAN-TC-765 | KAN-12 C8
    """
    corrections, _, agency, review = agency_with_corrections(after_hearing=True, open_items=True)
    d = review_loop_data

    with allure.step("Correct Part A and reply"):
        _, toast = _agency_corrects_and_replies(corrections, agency, d)
        record_loop_stage(agency, ReviewStage.REPLY_RECEIVED)
        expect(corrections.subtitle).to_have_text(F.REPLY_SENT)

    with allure.step("Verify the officer sees the second reply"):
        review.page.reload()
        review.wait_for_load()
        expect(review.requested_corrections).to_contain_text("Requested corrections (round 2)")
        assert review.history().count("Agency Reply") == 2, review.history()
        expect(review.flow_button("accept_reply")).to_contain_text(F.TAKE_REPLY)


@aio_case("KAN-TC-766")
@allure.story(STORY)
@allure.title("TC-766: A second reply that does not cure the deficiency leads to the refusal order")
def test_tc766_second_reply_still_on_hold_leads_to_refusal(review_workflow_allowed, application_at, review_loop_data):
    """
    Given the agency has replied within the window after the hearing
    When  I take the reply into review, keep Part A On Hold and save
    Then  the history shows "Post-hearing reply received — …"
    And   the refusal form appears (ground, speaking order with a 0 / 100 counter, Division report) and no new
          show cause form

    AIO: KAN-TC-766 | KAN-12 C9
    """
    review, agency = application_at(ReviewStage.REPLY_RECEIVED, after_hearing=True)
    d = review_loop_data

    with allure.step("Take the reply into review"):
        review.run_flow("accept_reply")
        record_loop_stage(agency, ReviewStage.IN_REVIEW)
        expect(review.history_entry("Accept Reply")).to_contain_text(F.ACCEPT_REPLY_2)

    with allure.step("Keep Part A On Hold and save"):
        review.save_review_with_hold(d.hold_item, d.hold_reason, d.hold_remark)
        record_loop_stage(agency, ReviewStage.REFUSAL_DUE)

    with allure.step("Verify the refusal form"):
        expect(review.refuse_button).to_be_visible()
        expect(review.refusal_reason_select).to_be_visible()
        expect(review.speaking_order_input).to_be_visible()
        expect(review.division_note_input).to_be_visible()
        expect(review.issue_scn_button).to_have_count(0)


@aio_case("KAN-TC-767")
@allure.story(STORY)
@allure.title("TC-767: The refusal order needs a ground, a 100-character speaking order and a Division report")
def test_tc767_refusal_client_checks(review_workflow_allowed, application_at):
    """
    Given Part A is still On Hold after the post-hearing reply and the application is not refused
    When  I click Refuse without a ground, with a speaking order under 100 characters, and with a Division
          report under 20 characters
    Then  each is refused with its message and nothing is refused

    AIO: KAN-TC-767 | KAN-12 C10 (negative)
    """
    review, _ = application_at(ReviewStage.REFUSAL_DUE)

    for check in F.refusal_checks():
        with allure.step(f"Try '{check.scenario_label}'"):
            review.fill_refusal(check.fields["reason"], check.fields["speaking_order"], check.fields["division_note"])
            error = review.refuse_expecting_refusal()
            assert error == check.expected_error, f"{check.scenario_label}: expected '{check.expected_error}', got '{error}'"

    with allure.step("Verify the application is not refused"):
        review.page.reload()
        review.wait_for_load()
        assert review.stage() == ReviewStage.REFUSAL_DUE


@aio_case("KAN-TC-768")
@allure.story(STORY)
@allure.title("TC-768: Passing the speaking refusal order refuses the application")
def test_tc768_refusal_order(review_workflow_allowed, application_at, review_loop_data):
    """
    Given Part A is still On Hold after the post-hearing reply
    When  I pass the speaking refusal order (Failed 15-Day Deficiency Correction) with the Division report
    Then  the confirmation says the agency can file a First Appeal
    And   the application shows REJECTED, "Stage Refused" and the read-only banner
    And   the history has "Refuse" (Sec 4(3)(b), Rule 4(8), First Appeal within 60 days, the speaking order)
          and "Division Report" (the note and the items not corrected)

    AIO: KAN-TC-768 | KAN-12 C10
    """
    review, agency = application_at(ReviewStage.REFUSAL_DUE)
    d = review_loop_data

    with allure.step("Pass the refusal order"):
        prompt = review.refuse(d.refusal_reason, d.speaking_order, d.division_note)
        record_loop_stage(agency, ReviewStage.REFUSED)
        assert prompt == F.REFUSE_CONFIRM, prompt

    with allure.step("Verify the application is refused"):
        expect(review.main).to_contain_text(F.REJECTED_BADGE)
        expect(review.main).to_contain_text(F.REFUSED_STAGE)
        expect(review.read_only_banner).to_contain_text(F.READ_ONLY)

    with allure.step("Verify the history"):
        expect(review.history_entry("Refuse")).to_contain_text(F.REFUSE_HISTORY)
        expect(review.history_entry("Refuse")).to_contain_text(d.speaking_order)
        expect(review.history_entry("Division Report")).to_contain_text(d.division_note)
        expect(review.history_entry("Division Report")).to_contain_text(HOLD)


# ═══════════════════════════════════════════════════════════════════════════
# End to end — RUN_REVIEW_WORKFLOW_TESTS=true
# ═══════════════════════════════════════════════════════════════════════════

# AIO key not assigned yet (KAN-TC-769…772 belong to KAN-48) — add @aio_case once the case exists.
@allure.story(STORY)
@allure.title("A Compliance 1 reply marked not corrected leads to the Compliance 2 show cause notice and hearing")
def test_show_cause_after_uncured_compliance_1_reply(review_workflow_allowed, agency_with_corrections,
                                                     review_loop_data):
    """
    Given the agency's application has a Compliance 1 notice with Part A On Hold
    When  the agency corrects Part A and replies
    And   I take the reply into review, mark Part A not corrected (On Hold with a reason) and approve the rest
    Then  the review is saved with only Part A On Hold, and the show cause form appears instead of Compliance 1
          or the approval
    When  I issue the show cause notice (Inadequate / Unsatisfactory Rectification) with a personal hearing
    Then  the "Scn Hearing" history entry gives the grounds and the venue, the hearing record form is shown and
          the application is listed under Desktop scrutiny › Show cause / hearing

    End to end: covers what TC-758, TC-760, TC-761 and TC-763 do one step each. It corrects and replies as the
    agency itself, so it takes an application with an item still to correct — or sends Compliance 1 on an
    untouched submission first. Irreversible.
    """
    corrections, _, agency, review = agency_with_corrections(after_hearing=False, open_items=True)
    d = review_loop_data

    with allure.step("The agency corrects Part A and replies"):
        _agency_corrects_and_replies(corrections, agency, d)
        record_loop_stage(agency, ReviewStage.REPLY_RECEIVED)
        expect(corrections.subtitle).to_have_text(F.REPLY_SENT)

    with allure.step("Take the reply into review"):
        review.page.reload()
        review.wait_for_load()
        expect(review.history_entry("Agency Reply")).to_contain_text(d.reply_text)
        review.run_flow("accept_reply")
        record_loop_stage(agency, ReviewStage.IN_REVIEW)
        expect(review.history_entry("Accept Reply")).to_contain_text(F.ACCEPT_REPLY_1)

    with allure.step("Mark Part A not corrected (On Hold), approve the rest and save"):
        review.save_review_with_hold(d.hold_item, d.hold_reason, d.hold_remark)
        record_loop_stage(agency, ReviewStage.SHOW_CAUSE_DUE)
        bars = review.review_data()
        assert {b["key"]: b["orig"] for b in bars if b["orig"] != "approved"} == {d.hold_item: "on_hold"}, bars

    with allure.step("Verify the show cause form replaces Compliance 1 and the approval"):
        assert review.stage() == ReviewStage.SHOW_CAUSE_DUE, review.stage()
        expect(review.issue_scn_button).to_be_visible()
        expect(review.scn_reason_select).to_be_visible()
        expect(review.hearing_at_input).to_be_visible()
        expect(review.hearing_venue_input).to_be_visible()
        expect(review.flow_button("deficiency")).to_have_count(0)
        expect(review.approve_desktop_button).to_have_count(0)

    with allure.step("Issue the show cause notice with a personal hearing"):
        prompt = review.issue_show_cause(d.scn_reason, d.scn_grounds, d.hearing_venue, d.hearing_minutes_ahead)
        record_loop_stage(agency, ReviewStage.HEARING_DUE)
        assert prompt == F.SCN_CONFIRM, prompt

    with allure.step("Verify the notice and the hearing"):
        expect(review.stage_subtitle).to_have_text(F.STAGE_C2_HEARING)
        entry = review.history_entry("Scn Hearing")
        expect(entry).to_contain_text(F.SCN_HISTORY)
        expect(entry).to_contain_text(d.hearing_venue)
        expect(entry).to_contain_text(f"{F.SCN_GROUND_LABEL} — {d.scn_grounds}")
        expect(review.grant_window_button).to_be_visible()
        assert review.after_hearing(), review.history()

    with allure.step("Verify the application is listed under Show cause / hearing"):
        expect(_listed_under(review, "hearing", agency.application_id)).to_have_count(1)


# ═══════════════════════════════════════════════════════════════════════════
# Approval path — RUN_REVIEW_WORKFLOW_TESTS=true
# ═══════════════════════════════════════════════════════════════════════════

# AIO key not assigned yet (KAN-TC-769…772 belong to KAN-48) — add @aio_case once the case exists.
@allure.story(STORY)
@allure.title("A reply to Compliance 1 that cures the deficiency leads to approval and a certificate")
def test_approval_after_compliance_1_reply(review_workflow_allowed, application_at, agency_with_corrections,
                                          review_loop_data):
    """
    Given the agency's application has a Compliance 1 notice with Part A On Hold
    When  the agency corrects Part A and replies
    And   I take the reply into review, approve every item and save
    Then  "Approve Desktop Scrutiny" is offered
    When  I approve Desktop Scrutiny
    Then  the application moves to Stage 2 — Physical Verification
    When  I approve the premises photographs, mark every office verified and give final approval
    Then  the application is listed under Applications › Approved

    An application left with "Approve Desktop Scrutiny" offered (a run stopped after the review was saved) is
    taken up from there instead of using up another submission.

    Note (dev, 06-Nov-2026): with every item approved, the show cause form ("Compliance 1 did not resolve the
    items") is still shown beside "Approve Desktop Scrutiny" — attached, not asserted, until the expected
    behaviour is confirmed.

    Irreversible: it approves a real application on dev and issues its certificate.
    """
    d = review_loop_data
    found = application_at(ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=False, required=False)
    if found:
        review, agency = found
        allure.attach(f"{agency.username} ({agency.application_id})", name="Taken up at Approve Desktop Scrutiny",
                      attachment_type=allure.attachment_type.TEXT)
    else:
        corrections, _, agency, review = agency_with_corrections(after_hearing=False, open_items=True)

        with allure.step("The agency corrects Part A and replies"):
            _agency_corrects_and_replies(corrections, agency, d)
            record_loop_stage(agency, ReviewStage.REPLY_RECEIVED)
            expect(corrections.subtitle).to_have_text(F.REPLY_SENT)

        with allure.step("Take the reply into review"):
            review.page.reload()
            review.wait_for_load()
            review.run_flow("accept_reply")
            record_loop_stage(agency, ReviewStage.IN_REVIEW)
            expect(review.history_entry("Accept Reply")).to_contain_text(F.ACCEPT_REPLY_1)

        with allure.step("Approve every item and save"):
            review.save_review_all_approved()
            record_loop_stage(agency, review.stage())

    with allure.step("Verify Approve Desktop Scrutiny is offered"):
        expect(review.approve_desktop_button).to_be_visible()
        assert review.stage() == ReviewStage.DESKTOP_APPROVAL_DUE
        allure.attach(f"show cause form visible: {review.issue_scn_button.is_visible()}",
                      name="Show cause form beside the approval", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Approve Desktop Scrutiny — the application moves to Physical Verification"):
        prompt = review.approve_desktop_scrutiny()
        assert prompt == F.APPROVE_DESKTOP_CONFIRM, prompt
        assert review.stage() == ReviewStage.PHYSICAL, review.stage_subtitle.inner_text()
        record_loop_stage(agency, ReviewStage.PHYSICAL)
        expect(review.stage_subtitle).to_contain_text(review.STAGE_2)
        expect(review.main).to_contain_text(F.DESKTOP_CLEARED)

    with allure.step("Approve the premises photographs and mark every office verified"):
        if any(b["orig"] != "approved" for b in review.review_data()):
            review.save_review_all_approved()
        prompts = review.mark_offices_verified()
        assert prompts and prompts[0] == F.HEAD_OFFICE_VERIFIED_CONFIRM, prompts
        expect(review.history_entry("Unit Clear")).to_contain_text(F.HEAD_OFFICE_VERIFIED)
        expect(review.final_approval_button).to_be_visible()

    with allure.step("Give final approval — issue the certificate"):
        prompt = review.final_approval()
        record_loop_stage(agency, ReviewStage.APPROVED)
        assert prompt == F.FINAL_APPROVAL_CONFIRM, prompt

    with allure.step("Verify the application is approved and the certificate issued"):
        expect(review.stage_subtitle).to_have_text(F.APPROVED_STAGE)
        expect(review.history_entry("Clear")).to_contain_text(F.certificate_issued(agency.application_id))
        expect(review.flow_buttons).to_have_count(0)

    with allure.step("Verify Licences & certificates lists the agency as Active"):
        # Applications › Approved (and All applications) list nothing on dev, 06-Nov-2026
        licences = AdminLicensesPage(review.page)
        licences.open()
        licences.search(agency.application_id)
        rows = [r for r in licences.table_data() if r["registration_no"] == agency.application_id]
        assert len(rows) == 1, licences.table_data()
        assert rows[0]["status"].lower() == "active", rows[0]
        # The registration number is the Application ID
        TestStateStore().record_certificate_no(username=agency.username, certificate_no=agency.application_id)


# ═══════════════════════════════════════════════════════════════════════════
# Compliance states — agency side (KAN-48): one parked agency per state, read only
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# Shared checks — agency side
# ---------------------------------------------------------------------------
def _expect_my_app_status(v: AgencyView, status: str):
    with allure.step(f"My Application shows {status}"):
        v.my_app.open()
        expect(v.my_app.status_banner).to_contain_text(re.compile(rf"Application Status:\s*{status}\b"))


def _expect_under_review_stage_1(v: AgencyView):
    with allure.step("Home: under review in Stage 1 — Desktop Scrutiny, nothing to do"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_UNDER_REVIEW)
        expect(v.home.next_step_heading).to_have_text(M.NEXT_UNDER_REVIEW_1)
        expect(v.home.next_step_text).to_contain_text(NO_ACTION)
        expect(v.home.progress_subtitle).to_have_text(M.PROGRESS_UNDER_REVIEW_1)


def _expect_no_corrections(v: AgencyView):
    with allure.step("Corrections: no corrections requested"):
        v.corrections.open()
        expect(v.corrections.subtitle).to_have_text(M.CORR_NONE)


def _expect_nothing_to_do(v: AgencyView):
    """After a reply is taken into review: under review, no corrections asked, no hearing announced."""
    with allure.step("Home: under review, no corrections asked and no hearing"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_UNDER_REVIEW)
        expect(v.home.next_step_heading).not_to_contain_text(M.ACTION_REQUIRED)
        expect(v.home.next_step_heading).not_to_contain_text(M.NEXT_HEARING.strip())
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)
    with allure.step("Corrections: nothing to correct, no reply form"):
        v.corrections.open()
        expect(v.corrections.items.filter(has_text=M.CORR_NEEDED)).to_have_count(0)
        expect(v.corrections.reply_section).to_be_hidden()


def _expect_corrected_not_replied(v: AgencyView):
    with allure.step("Corrections: Part A corrected and locked, reply form shown"):
        v.corrections.open()
        expect(v.corrections.item_badge(HOLD)).to_have_text(F.CORR_DONE_BADGE)
        expect(v.corrections.item_locked_note(HOLD)).to_have_text(F.CORR_LOCKED)
        expect(v.corrections.subtitle).to_contain_text(M.CORR_ALL_DONE)
        expect(v.corrections.reply_section).to_be_visible()
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)


def _expect_reply_with_officer(v: AgencyView):
    with allure.step("Home: the reply is with the officer"):
        v.home.open()
        expect(v.home.next_step_heading).to_have_text(M.NEXT_REPLY_WITH_OFFICER)
        expect(v.home.next_step_text).to_contain_text(re.compile(rf"Submitted on {DATE}"))
        expect(v.home.timeline_titles.first).to_have_text(M.TIMELINE_REPLY)
    with allure.step("Corrections: corrections and reply submitted, nothing open"):
        v.corrections.open()
        expect(v.corrections.subtitle).to_have_text(M.CORR_REPLY_SENT)
        expect(v.corrections.item_badge(HOLD)).to_have_text(F.CORR_DONE_BADGE)
        expect(v.corrections.reply_section).to_be_hidden()


def _expect_stage_2(v: AgencyView):
    with allure.step("Home: under review in Stage 2 — Physical Verification"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_UNDER_REVIEW)
        expect(v.home.next_step_heading).to_have_text(M.NEXT_UNDER_REVIEW_2)
        expect(v.home.next_step_text).to_contain_text(NO_ACTION)
        expect(v.home.progress_subtitle).to_have_text(M.PROGRESS_STAGE_2)


# ---------------------------------------------------------------------------
# C1–C10 — agency side
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-773")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-773: C1 — a submitted application not reviewed yet: nothing for the agency to do")
def test_tc773_submitted(agency_at):
    """
    Given the agency parked at 'submitted' (C1: submitted, not reviewed yet)
    When  it opens Home, My Application and Corrections
    Then  Home shows Stage 1 — Desktop Scrutiny under review with no action needed
    And   My Application shows SUBMITTED and Corrections has no corrections requested

    AIO: KAN-TC-773 | KAN-48 AC-9 | data: map state 'submitted'
    """
    v = agency_at("submitted")
    _expect_under_review_stage_1(v)
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)
    _expect_no_corrections(v)


@aio_case("KAN-TC-774")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-774: C2 — review saved with an item On Hold: the agency sees nothing until Compliance 1 is sent")
def test_tc774_review_held(agency_at):
    """
    Given the agency parked at 'review_held' (C2: review saved with Part A On Hold, Compliance 1 not sent)
    When  it opens Home, My Application and Corrections
    Then  it sees the same as an unreviewed application: no corrections requested, the item On Hold not shown

    AIO: KAN-TC-774 | KAN-48 AC-9 | data: map state 'review_held'
    """
    v = agency_at("review_held")
    _expect_under_review_stage_1(v)
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)
    _expect_no_corrections(v)


@aio_case("KAN-TC-775")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-775: C2 — review saved with every item approved: still under review for the agency")
def test_tc775_review_all_approved(agency_at):
    """
    Given the agency parked at 'review_all_approved' (C2: every item approved, Desktop Scrutiny not yet approved)
    When  it opens Home, My Application and Corrections
    Then  it is still under review in Stage 1 with nothing to do

    AIO: KAN-TC-775 | KAN-48 AC-9 | data: map state 'review_all_approved'
    """
    v = agency_at("review_all_approved")
    _expect_under_review_stage_1(v)
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)
    _expect_no_corrections(v)


@aio_case("KAN-TC-776")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-776: C3 — Compliance 1 sent: Home asks for corrections and Corrections lists the item")
def test_tc776_compliance_1_sent(agency_at):
    """
    Given the agency parked at 'compliance_1_sent' (C3: deficiency notice for Part A, not answered)
    When  it opens Home and Corrections
    Then  Home reads "Action required: the officer has asked for corrections" with the reply date, Application
          progress "Compliance 1 — deficiency notice, awaiting reply" and "45-day clock paused (Rule 4(4))"
    And   Corrections lists Part A as "Correction needed" and hides the reply form

    AIO: KAN-TC-776 | KAN-48 AC-1, AC-2 | data: map state 'compliance_1_sent'
    """
    v = agency_at("compliance_1_sent")
    with allure.step("Home: action required"):
        v.home.open()
        expect(v.home.next_step_heading).to_contain_text(M.ACTION_REQUIRED)
        expect(v.home.next_step_text).to_contain_text(re.compile(rf"1 item\(s\) need your attention · reply by {DATE}"))
        expect(v.home.progress_subtitle).to_contain_text(M.PROGRESS_C1)
        expect(v.home.progress_card).to_contain_text(M.CLOCK_PAUSED)
    with allure.step("Corrections: Part A needs correcting"):
        v.corrections.open()
        expect(v.corrections.subtitle).to_have_text(re.compile(r"1 item\(s\) still to correct · Reply by \d{4}-\d{2}-\d{2}"))
        expect(v.corrections.item_badge(HOLD)).to_have_text(M.CORR_NEEDED)
        expect(v.corrections.reply_section).to_be_hidden()
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)


@aio_case("KAN-TC-777")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-777: C4 — items corrected, reply not sent: Corrections offers the reply")
def test_tc777_compliance_1_corrected(agency_at):
    """
    Given the agency parked at 'compliance_1_corrected' (C4: Part A corrected, reply not sent)
    When  it opens Corrections
    Then  Part A shows "Corrected" and is locked, and "All items corrected — send your reply below" with the form

    AIO: KAN-TC-777 | KAN-48 AC-5 | data: map state 'compliance_1_corrected'
    """
    _expect_corrected_not_replied(agency_at("compliance_1_corrected"))


@aio_case("KAN-TC-778")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-778: C4 — reply to Compliance 1 sent: the reply is with the officer and the 45-day clock resumes")
def test_tc778_compliance_1_replied(agency_at):
    """
    Given the agency parked at 'compliance_1_replied' (C4: corrected and replied, not yet taken into review)
    When  it opens Home and Corrections
    Then  Home reads "Your reply is with the officer" and the timeline shows "Your reply sent"
    And   Corrections reads "Your corrections and reply have been submitted — the officer is reviewing them."
    And   Application progress no longer shows the 45-day clock paused

    Fails on dev (06-Nov-2026): Home still shows "45-day clock paused (Rule 4(4))" and "Compliance 1 — deficiency
    notice, awaiting reply" after the reply — defect "Agency homepage" #81.

    AIO: KAN-TC-778 | KAN-48 AC-5 | data: map state 'compliance_1_replied'
    """
    v = agency_at("compliance_1_replied")
    _expect_reply_with_officer(v)
    with allure.step("Home: the 45-day clock is no longer paused"):
        v.home.open()
        expect(v.home.progress_card).not_to_contain_text(M.CLOCK_PAUSED)


@aio_case("KAN-TC-779")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-779: C5 — reply reviewed with an item still On Hold: nothing for the agency to do yet")
def test_tc779_show_cause_due(agency_at):
    """
    Given the agency parked at 'show_cause_due' (C5: reply taken into review, Part A still On Hold, no show cause
          notice yet)
    When  it opens Home, My Application and Corrections
    Then  it is under review with no corrections asked and no hearing announced

    AIO: KAN-TC-779 | KAN-48 AC-9 | data: map state 'show_cause_due'
    """
    _expect_nothing_to_do(agency_at("show_cause_due"))


@aio_case("KAN-TC-780")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-780: C5 — reply reviewed with every item approved: nothing for the agency to do")
def test_tc780_compliance_1_cured(agency_at):
    """
    Given the agency parked at 'compliance_1_cured' (C5: reply taken into review, every item approved)
    When  it opens Home, My Application and Corrections
    Then  it is under review with no corrections asked and no hearing announced

    AIO: KAN-TC-780 | KAN-48 AC-9 | data: map state 'compliance_1_cured'
    """
    _expect_nothing_to_do(agency_at("compliance_1_cured"))


@aio_case("KAN-TC-781")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-781: C6 — show cause notice issued: Home announces the personal hearing")
def test_tc781_hearing_scheduled(agency_at):
    """
    Given the agency parked at 'hearing_scheduled' (C6: show cause notice issued, hearing scheduled)
    When  it opens Home and Corrections
    Then  Home reads "Show cause hearing on <date, time>", Application progress "Compliance 2 — show cause notice &
          hearing scheduled" with "(in person — attendance is compulsory)", the venue and the grounds
    And   Corrections reads "This round of corrections is closed."

    AIO: KAN-TC-781 | KAN-48 AC-6 | data: map state 'hearing_scheduled'
    """
    v = agency_at("hearing_scheduled")
    with allure.step("Home: the hearing"):
        v.home.open()
        expect(v.home.next_step_heading).to_have_text(re.compile(rf"^Show cause hearing on {DATE}, \d{{1,2}}:\d{{2}} [AP]M$"))
        expect(v.home.next_step_text).to_contain_text("Attend the hearing as described in the notice below.")
        expect(v.home.progress_subtitle).to_contain_text(M.PROGRESS_C2_HEARING)
        expect(v.home.progress_card).to_contain_text(M.HEARING_IN_PERSON)
        expect(v.home.progress_card).to_contain_text(f"Venue: {F.loop().hearing_venue}")
        expect(v.home.progress_card).to_contain_text("Grounds:")
    with allure.step("Corrections: the round is closed"):
        v.corrections.open()
        expect(v.corrections.subtitle).to_have_text(M.CORR_CLOSED)
        expect(v.corrections.reply_section).to_be_hidden()
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)


@aio_case("KAN-TC-782")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-782: C7 — window given after the hearing: the items are open to correct again")
def test_tc782_window_open(agency_at):
    """
    Given the agency parked at 'window_open' (C7: hearing recorded, window to correct given)
    When  it opens Home and Corrections
    Then  the timeline shows "Post-hearing window granted" with the number of days and the reply date
    And   Corrections lists Part A as "Correction needed" again

    AIO: KAN-TC-782 | KAN-48 AC-7 | data: map state 'window_open'
    """
    v = agency_at("window_open")
    with allure.step("Home: the window in the timeline"):
        v.home.open()
        expect(v.home.timeline_note(M.TIMELINE_WINDOW).first).to_contain_text(re.compile(
            rf"Hearing held — agency attended\. You have \d+ days to correct the items below and reply by {DATE}"))
    with allure.step("Corrections: Part A needs correcting again"):
        v.corrections.open()
        expect(v.corrections.item_badge(HOLD)).to_have_text(M.CORR_NEEDED)
        expect(v.corrections.reply_section).to_be_hidden()
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)


@aio_case("KAN-TC-783")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-783: C8 — items corrected again, reply not sent: Corrections offers the second reply")
def test_tc783_window_corrected(agency_at):
    """
    Given the agency parked at 'window_corrected' (C8: Part A corrected in the window, reply not sent)
    When  it opens Corrections
    Then  Part A shows "Corrected" and is locked, and the reply form is shown

    AIO: KAN-TC-783 | KAN-48 AC-7 | data: map state 'window_corrected'
    """
    _expect_corrected_not_replied(agency_at("window_corrected"))


@aio_case("KAN-TC-784")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-784: C8 — second reply sent: the reply is with the officer")
def test_tc784_window_replied(agency_at):
    """
    Given the agency parked at 'window_replied' (C8: corrected and replied in the window)
    When  it opens Home and Corrections
    Then  Home reads "Your reply is with the officer" and Corrections reads that the reply was submitted

    AIO: KAN-TC-784 | KAN-48 AC-7 | data: map state 'window_replied'
    """
    _expect_reply_with_officer(agency_at("window_replied"))


@aio_case("KAN-TC-785")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-785: C9 — second reply reviewed with an item still On Hold: nothing for the agency to do yet")
def test_tc785_refusal_due(agency_at):
    """
    Given the agency parked at 'refusal_due' (C9: second reply taken into review, Part A still On Hold)
    When  it opens Home, My Application and Corrections
    Then  it is under review with no corrections asked and no hearing announced

    AIO: KAN-TC-785 | KAN-48 AC-9 | data: map state 'refusal_due'
    """
    _expect_nothing_to_do(agency_at("refusal_due"))


@aio_case("KAN-TC-786")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-786: C9 — second reply reviewed with every item approved: nothing for the agency to do")
def test_tc786_window_cured(agency_at):
    """
    Given the agency parked at 'window_cured' (C9: second reply taken into review, every item approved)
    When  it opens Home, My Application and Corrections
    Then  it is under review with no corrections asked and no hearing announced

    AIO: KAN-TC-786 | KAN-48 AC-9 | data: map state 'window_cured'
    """
    _expect_nothing_to_do(agency_at("window_cured"))


@aio_case("KAN-TC-787")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-787: C10 — refused: Home, My Application and both appeal forms show the refusal")
def test_tc787_refused(agency_at):
    """
    Given the agency parked at 'refused' (C10: refusal order passed, no appeal filed)
    When  it opens Home, My Application, FORM-III and FORM-IV
    Then  Home shows "Refused", "Your application was refused", "Refused · Closed", the refusal order in the
          timeline and "2 of 2 appeals remaining"
    And   My Application shows REJECTED with the reason in the order
    And   FORM-III offers the form with both appeals remaining; FORM-IV says the First Appeal comes first

    AIO: KAN-TC-787 | KAN-48 AC-10 | data: map state 'refused'
    """
    v = agency_at("refused")
    with allure.step("Home: refused, two appeals remaining"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_REFUSED)
        expect(v.home.next_step_heading).to_have_text(M.NEXT_REFUSED)
        expect(v.home.progress_subtitle).to_contain_text(M.PROGRESS_REFUSED)
        expect(v.home.timeline_titles.first).to_have_text(M.TIMELINE_REFUSED)
        expect(v.home.appeals_remaining).to_have_text(FA.HOME_REMAINING.format(n=2))
    _expect_my_app_status(v, M.MY_APP_REJECTED)
    with allure.step("My Application: the reason in the refusal order"):
        expect(v.my_app.admin_remarks).to_contain_text(F.loop().speaking_order)
    with allure.step("FORM-III: the form, both appeals remaining"):
        v.first_appeal.open()
        expect(v.first_appeal.appeal_form).to_have_count(1)
        expect(v.first_appeal.appeals_remaining).to_have_text(FA.APPEALS_REMAINING.format(n=2))
        expect(v.first_appeal.journey_status(M.STEP_FIRST)).to_have_text(re.compile("Not filed"))
    with allure.step("FORM-IV: the First Appeal comes first"):
        v.second_appeal.open()
        expect(v.second_appeal.appeal_form).to_have_count(0)
        expect(v.second_appeal.blocking_note).to_contain_text(M.SECOND_BEFORE_FIRST)


# ---------------------------------------------------------------------------
# Approval branch — agency side
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-788")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-788: Stage 2 — desktop scrutiny cleared: Home shows Physical Verification")
def test_tc788_physical_verification(agency_at):
    """
    Given the agency parked at 'physical_verification' (Desktop Scrutiny approved, Stage 2 open)
    When  it opens Home, My Application and Corrections
    Then  Home shows Stage 2 — Physical Verification under review and "Desktop scrutiny cleared — application moved
          to Physical Verification." in the timeline
    And   My Application shows SUBMITTED and Corrections has no corrections requested

    AIO: KAN-TC-788 | KAN-48 AC-11 | data: map state 'physical_verification'
    """
    v = agency_at("physical_verification")
    _expect_stage_2(v)
    with allure.step("Home: desktop scrutiny cleared in the timeline"):
        expect(v.home.timeline_note(M.TIMELINE_STAGE_CLEARED).first).to_have_text(M.DESKTOP_CLEARED)
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)
    _expect_no_corrections(v)


@aio_case("KAN-TC-789")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-789: Stage 2 — head office verified, branch office still being verified")
def test_tc789_branch_verification(agency_at):
    """
    Given the agency parked at 'branch_verification' (one branch office; head office marked verified)
    When  it opens Home and My Application
    Then  Home is still in Stage 2 with "Office verified — Head office (<district>) physically verified." newest
          in the timeline and no certificate yet; My Application shows SUBMITTED

    AIO: KAN-TC-789 | KAN-48 AC-11 | data: map state 'branch_verification'
    """
    v = agency_at("branch_verification")
    _expect_stage_2(v)
    with allure.step("Home: head office verified, no certificate"):
        expect(v.home.timeline_titles.first).to_have_text(M.TIMELINE_OFFICE_VERIFIED)
        expect(v.home.timeline_notes.first).to_have_text(re.compile(rf"^Head office \(.+\) {re.escape(M.HEAD_OFFICE_VERIFIED)}$"))
        expect(v.home.view_certificate_button).to_have_count(0)
    _expect_my_app_status(v, M.MY_APP_SUBMITTED)


@aio_case("KAN-TC-790")
@allure.story(COMPLIANCE_STORY)
@allure.title("TC-790: Approved — Home shows the agency registered with its Form-II certificate")
def test_tc790_approved(agency_at):
    """
    Given the agency parked at 'approved' (final approval given, certificate issued)
    When  it opens Home and My Application
    Then  Home shows "Registered", "Your agency is registered" with the certificate's validity and "View
          certificate", "Approved — Certificate Issued · Closed", and the certificate (Registration No. = the
          Application ID) newest in the timeline
    And   My Application shows APPROVED

    AIO: KAN-TC-790 | KAN-48 AC-12 | data: map state 'approved'
    """
    v = agency_at("approved")
    with allure.step("Home: registered"):
        v.home.open()
        expect(v.home.status_badge).to_have_text(M.BADGE_REGISTERED)
        expect(v.home.next_step_heading).to_have_text(M.NEXT_REGISTERED)
        expect(v.home.next_step_text).to_contain_text(re.compile(rf"Certificate valid until {DATE}"))
        expect(v.home.view_certificate_button).to_be_visible()
        expect(v.home.progress_subtitle).to_have_text(M.PROGRESS_APPROVED)
        expect(v.home.timeline_notes.first).to_have_text(F.certificate_issued(v.agency.application_id))
    _expect_my_app_status(v, M.MY_APP_APPROVED)


# ═══════════════════════════════════════════════════════════════════════════
# Compliance states — officer side (KAN-12): one parked application per state, read only
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# Shared checks — officer side
# ---------------------------------------------------------------------------
def _expect_stage(review: AdminApplicationReviewPage, stage: str, after_hearing: bool = None):
    assert review.stage() == stage, f"The review page is at '{review.stage()}', not '{stage}'"
    if after_hearing is not None:
        assert review.after_hearing() == after_hearing, review.history()


def _expect_newest_history(review: AdminApplicationReviewPage, title: str):
    history = review.history()
    assert history and history[-1] == title, f"Newest history entry is not '{title}': {history}"


def _bars(review: AdminApplicationReviewPage) -> dict:
    return {b["key"]: b["orig"] for b in review.review_data()}


def _expect_all_approved(review: AdminApplicationReviewPage):
    bars = _bars(review)
    assert bars and all(orig == "approved" for orig in bars.values()), bars
    expect(review.approve_desktop_button).to_be_visible()


def _expect_listed(o: OfficerView, view: str, step: str = None, label: str = ""):
    where = label or f"Desktop scrutiny › {step}"
    with allure.step(f"Applications › {where} lists the application (searched by its Application ID)"):
        applications = AdminApplicationsPage(o.review.page)
        applications.open(view, step, query=o.agency.application_id)
        # dev 06-Nov-2026: an application given a post-hearing window breaks the list it is in
        expect(applications.load_error, "The list did not load").to_have_count(0)
        expect(applications.row_by_application_id(o.agency.application_id)).to_have_count(1)
        return applications.row_by_application_id(o.agency.application_id)


def _expect_awaiting_agency(o: OfficerView, newest: str, after_hearing: bool):
    with allure.step(f"Review page: awaiting the agency, newest history '{newest}'"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.WITH_AGENCY, after_hearing)
        expect(review.main).to_contain_text(F.AWAITING_AGENCY)
        _expect_newest_history(review, newest)
    return review


# ---------------------------------------------------------------------------
# C1–C10 — officer side
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-801")
@allure.story(STORY)
@allure.title("TC-801: C1 — a submitted application not reviewed yet: no next step before the review is saved")
def test_tc801_submitted(officer_at):
    """
    Given the application parked at 'submitted' (C1)
    When  the officer opens its review page
    Then  it reads "Stage 1 — Desktop Scrutiny · Under review", every item is pending, the history is only
          "Submitted", and neither "Send Compliance 1" nor "Approve Desktop Scrutiny" is offered
    And   Applications › Desktop scrutiny › review lists it

    AIO: KAN-TC-801 | KAN-12 AC-1, AC-15 | data: map state 'submitted'
    """
    o = officer_at("submitted")
    with allure.step("Review page: nothing reviewed yet"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.NEW)
        expect(review.stage_subtitle).to_have_text(M.STAGE_UNDER_REVIEW)
        assert review.history() == ["Submitted"], review.history()
        expect(review.flow_button("deficiency")).to_be_hidden()
        expect(review.approve_desktop_button).to_be_hidden()
    _expect_listed(o, "desktop", "review")


@aio_case("KAN-TC-802")
@allure.story(STORY)
@allure.title("TC-802: C2 — review saved with an item On Hold: Send Compliance 1 is offered")
def test_tc802_review_held(officer_at):
    """
    Given the application parked at 'review_held' (C2: Part A On Hold, Compliance 1 not sent)
    When  the officer opens its review page
    Then  Part A is On Hold, "Send Compliance 1 (1)" is offered and the history has no "Deficiency"
    And   Applications › Desktop scrutiny › review lists it

    AIO: KAN-TC-802 | KAN-12 AC-4, AC-15 | data: map state 'review_held'
    """
    o = officer_at("review_held")
    with allure.step("Review page: Send Compliance 1 offered"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.HELD)
        assert _bars(review).get(HOLD_KEY) == "on_hold", _bars(review)
        expect(review.flow_button("deficiency")).to_contain_text(F.SEND_C1)
        assert "Deficiency" not in review.history(), review.history()
    _expect_listed(o, "desktop", "review")


@aio_case("KAN-TC-803")
@allure.story(STORY)
@allure.title("TC-803: C2 — review saved with every item approved: Approve Desktop Scrutiny is offered")
def test_tc803_review_all_approved(officer_at):
    """
    Given the application parked at 'review_all_approved' (C2: every item approved)
    When  the officer opens its review page
    Then  every item is approved, "Approve Desktop Scrutiny" is offered and the history has no "Deficiency"
    And   Applications › Desktop scrutiny › review lists it

    AIO: KAN-TC-803 | KAN-12 AC-15, AC-16 | data: map state 'review_all_approved'
    """
    o = officer_at("review_all_approved")
    with allure.step("Review page: Approve Desktop Scrutiny offered"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=False)
        _expect_all_approved(review)
        assert "Deficiency" not in review.history(), review.history()
    _expect_listed(o, "desktop", "review")


@aio_case("KAN-TC-804")
@allure.story(STORY)
@allure.title("TC-804: C3 — Compliance 1 sent: the application waits for the agency")
def test_tc804_compliance_1_sent(officer_at):
    """
    Given the application parked at 'compliance_1_sent' (C3)
    When  the officer opens its review page
    Then  it reads "— awaiting the agency." and the newest history entry is the deficiency notice
    And   Applications › Desktop scrutiny › agency lists it

    AIO: KAN-TC-804 | KAN-12 AC-5, AC-15 | data: map state 'compliance_1_sent'
    """
    o = officer_at("compliance_1_sent")
    review = _expect_awaiting_agency(o, "Deficiency", after_hearing=False)
    expect(review.history_entry("Deficiency")).to_contain_text(F.C1_HISTORY)
    _expect_listed(o, "desktop", "agency")


@aio_case("KAN-TC-805")
@allure.story(STORY)
@allure.title("TC-805: C4 — agency corrected but has not replied: still waiting for the agency")
def test_tc805_compliance_1_corrected(officer_at):
    """
    Given the application parked at 'compliance_1_corrected' (C4: corrected, no reply)
    When  the officer opens its review page
    Then  it still reads "— awaiting the agency." with "Deficiency" newest (no "Agency Reply")
    And   Applications › Desktop scrutiny › agency lists it

    AIO: KAN-TC-805 | KAN-12 AC-5, AC-15 | data: map state 'compliance_1_corrected'
    """
    o = officer_at("compliance_1_corrected")
    _expect_awaiting_agency(o, "Deficiency", after_hearing=False)
    _expect_listed(o, "desktop", "agency")


@aio_case("KAN-TC-806")
@allure.story(STORY)
@allure.title("TC-806: C4 — agency replied: Take reply into review is offered")
def test_tc806_compliance_1_replied(officer_at):
    """
    Given the application parked at 'compliance_1_replied' (C4: the agency replied)
    When  the officer opens its review page
    Then  "Take reply into review" is offered and the newest history entry is "Agency Reply"

    AIO: KAN-TC-806 | KAN-12 AC-8 | data: map state 'compliance_1_replied'
    """
    o = officer_at("compliance_1_replied")
    with allure.step("Review page: Take reply into review offered"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.REPLY_RECEIVED, after_hearing=False)
        expect(review.flow_button("accept_reply")).to_contain_text(F.TAKE_REPLY)
        _expect_newest_history(review, "Agency Reply")


@aio_case("KAN-TC-807")
@allure.story(STORY)
@allure.title("TC-807: C5 — reply taken with an item still On Hold: the show cause form is offered")
def test_tc807_show_cause_due(officer_at):
    """
    Given the application parked at 'show_cause_due' (C5: reply taken, Part A still On Hold)
    When  the officer opens its review page
    Then  Part A is On Hold, the show cause form and "Issue show cause notice" are offered, "Accept Reply" is the
          newest history entry and there is no "Scn Hearing" yet

    AIO: KAN-TC-807 | KAN-12 AC-10 | data: map state 'show_cause_due'
    """
    o = officer_at("show_cause_due")
    with allure.step("Review page: the show cause form"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.SHOW_CAUSE_DUE, after_hearing=False)
        assert _bars(review).get(HOLD_KEY) == "on_hold", _bars(review)
        expect(review.scn_reason_select).to_be_visible()
        expect(review.issue_scn_button).to_be_visible()
        _expect_newest_history(review, "Accept Reply")


@aio_case("KAN-TC-808")
@allure.story(STORY)
@allure.title("TC-808: C5 — reply taken with every item approved: Approve Desktop Scrutiny is offered")
def test_tc808_compliance_1_cured(officer_at):
    """
    Given the application parked at 'compliance_1_cured' (C5: reply taken, every item approved)
    When  the officer opens its review page
    Then  every item is approved and "Approve Desktop Scrutiny" is offered; the history has "Deficiency" and
          "Accept Reply" and no "Scn Hearing"

    AIO: KAN-TC-808 | KAN-12 AC-16 | data: map state 'compliance_1_cured'
    """
    o = officer_at("compliance_1_cured")
    with allure.step("Review page: Approve Desktop Scrutiny offered after the reply"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=False)
        _expect_all_approved(review)
        history = review.history()
        assert "Deficiency" in history and "Accept Reply" in history, history


@aio_case("KAN-TC-809")
@allure.story(STORY)
@allure.title("TC-809: C6 — show cause notice issued: hearing record and window form offered")
def test_tc809_hearing_scheduled(officer_at):
    """
    Given the application parked at 'hearing_scheduled' (C6)
    When  the officer opens its review page
    Then  it reads "Stage 1 — Desktop Scrutiny · Compliance 2 — show cause notice & hearing scheduled", the hearing
          record and window form is offered and "Scn Hearing" is the newest history entry
    And   Applications › Desktop scrutiny › hearing lists it

    AIO: KAN-TC-809 | KAN-12 AC-10, AC-15 | data: map state 'hearing_scheduled'
    """
    o = officer_at("hearing_scheduled")
    with allure.step("Review page: Compliance 2, hearing due"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.HEARING_DUE, after_hearing=True)
        expect(review.stage_subtitle).to_have_text(F.STAGE_C2_HEARING)
        expect(review.grant_window_button).to_be_visible()
        _expect_newest_history(review, "Scn Hearing")
        expect(review.history_entry("Scn Hearing")).to_contain_text(F.SCN_HISTORY)
    _expect_listed(o, "desktop", "hearing")


@aio_case("KAN-TC-810")
@allure.story(STORY)
@allure.title("TC-810: C7 — window given after the hearing: the application waits for the agency again")
def test_tc810_window_open(officer_at):
    """
    Given the application parked at 'window_open' (C7)
    When  the officer opens its review page
    Then  it reads "— awaiting the agency." with "Grant Window" newest
    And   Applications › Desktop scrutiny › agency lists it

    Fails on dev (06-Nov-2026): an application given a post-hearing window makes every Applications list it is
    in fail to load ("The list could not be loaded (Ref …)"), even when searched by its own ID — defect
    "Super admin" #89.

    AIO: KAN-TC-810 | KAN-12 AC-11, AC-15 | data: map state 'window_open'
    """
    o = officer_at("window_open")
    _expect_awaiting_agency(o, "Grant Window", after_hearing=True)
    _expect_listed(o, "desktop", "agency")


@aio_case("KAN-TC-811")
@allure.story(STORY)
@allure.title("TC-811: C8 — agency corrected again but has not replied: still waiting for the agency")
def test_tc811_window_corrected(officer_at):
    """
    Given the application parked at 'window_corrected' (C8: corrected in the window, no reply)
    When  the officer opens its review page
    Then  it still reads "— awaiting the agency." with "Grant Window" newest
    And   Applications › Desktop scrutiny › agency lists it

    Fails on dev (06-Nov-2026) on the same list defect as TC-810.

    AIO: KAN-TC-811 | KAN-12 AC-11, AC-15 | data: map state 'window_corrected'
    """
    o = officer_at("window_corrected")
    _expect_awaiting_agency(o, "Grant Window", after_hearing=True)
    _expect_listed(o, "desktop", "agency")


@aio_case("KAN-TC-812")
@allure.story(STORY)
@allure.title("TC-812: C8 — second reply received: Take reply into review is offered")
def test_tc812_window_replied(officer_at):
    """
    Given the application parked at 'window_replied' (C8: the agency replied in the window)
    When  the officer opens its review page
    Then  "Take reply into review" is offered, "Agency Reply" is newest and the history has "Scn Hearing"

    AIO: KAN-TC-812 | KAN-12 AC-9 | data: map state 'window_replied'
    """
    o = officer_at("window_replied")
    with allure.step("Review page: Take reply into review offered after the hearing"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.REPLY_RECEIVED, after_hearing=True)
        expect(review.flow_button("accept_reply")).to_contain_text(F.TAKE_REPLY)
        _expect_newest_history(review, "Agency Reply")


@aio_case("KAN-TC-813")
@allure.story(STORY)
@allure.title("TC-813: C9 — second reply taken with an item still On Hold: only the refusal form is offered")
def test_tc813_refusal_due(officer_at):
    """
    Given the application parked at 'refusal_due' (C9: second reply taken, Part A still On Hold)
    When  the officer opens its review page
    Then  the refusal form (speaking order) and "Issue refusal order" are offered, the hearing record and window
          form is not, and "Accept Reply" is newest

    AIO: KAN-TC-813 | KAN-12 AC-12 | data: map state 'refusal_due'
    """
    o = officer_at("refusal_due")
    with allure.step("Review page: the refusal form"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.REFUSAL_DUE, after_hearing=True)
        expect(review.speaking_order_input).to_be_visible()
        expect(review.refuse_button).to_be_visible()
        expect(review.grant_window_button).to_be_hidden()
        _expect_newest_history(review, "Accept Reply")


@aio_case("KAN-TC-814")
@allure.story(STORY)
@allure.title("TC-814: C9 — second reply taken with every item approved: Approve Desktop Scrutiny is offered")
def test_tc814_window_cured(officer_at):
    """
    Given the application parked at 'window_cured' (C9: second reply taken, every item approved)
    When  the officer opens its review page
    Then  every item is approved and "Approve Desktop Scrutiny" is offered after the hearing

    AIO: KAN-TC-814 | KAN-12 AC-16 | data: map state 'window_cured'
    """
    o = officer_at("window_cured")
    with allure.step("Review page: Approve Desktop Scrutiny offered after the hearing"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.DESKTOP_APPROVAL_DUE, after_hearing=True)
        _expect_all_approved(review)


@aio_case("KAN-TC-815")
@allure.story(STORY)
@allure.title("TC-815: C10 — refused: the review page is closed and the application is listed as rejected")
def test_tc815_refused(officer_at):
    """
    Given the application parked at 'refused' (C10)
    When  the officer opens its review page, Applications › Rejected and Appeals › Rejected applications
    Then  the review page reads "Stage Refused" / "Refused · Closed", is read-only, and "Refuse" (the speaking
          refusal order) is newest
    And   both lists show the application

    Fails on dev (06-Nov-2026): Applications › Rejected does not load — the refused application was given a
    post-hearing window, the same list defect as TC-810. Appeals › Rejected applications lists it.

    AIO: KAN-TC-815 | KAN-12 AC-13, AC-15 | data: map state 'refused'
    """
    o = officer_at("refused")
    with allure.step("Review page: refused and read-only"):
        review = o.open_review()
        expect(review.main).to_contain_text(F.REFUSED_STAGE)
        expect(review.stage_subtitle).to_have_text(M.PROGRESS_REFUSED)
        expect(review.read_only_banner).to_contain_text(F.READ_ONLY)
        _expect_newest_history(review, "Refuse")
        expect(review.history_entry("Refuse")).to_contain_text(F.REFUSE_HISTORY)
    with allure.step("Appeals › Rejected applications lists the application"):
        o.appeals.open_view("rejections")
        expect(o.appeals.rows_for_application(o.agency.application_id)).to_have_count(1)
    _expect_listed(o, "rejected", label="Rejected")


# ---------------------------------------------------------------------------
# Approval branch — officer side
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-816")
@allure.story(STORY)
@allure.title("TC-816: Stage 2 — desktop scrutiny approved: Physical Verification with head office photos")
def test_tc816_physical_verification(officer_at):
    """
    Given the application parked at 'physical_verification' (no branch office)
    When  the officer opens its review page
    Then  it reads "Stage 2 — Physical Verification" with the head office's photo bars (signboard, exterior,
          interior) pending review, none for a branch office
    And   "Mark Head office verified" is not offered yet — it appears once the photos are approved (dev,
          06-Nov-2026)
    And   Applications › Physical verification lists it

    AIO: KAN-TC-816 | KAN-12 AC-17 | data: map state 'physical_verification'
    """
    o = officer_at("physical_verification")
    with allure.step("Review page: Stage 2, head office photos pending"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.PHYSICAL)
        expect(review.stage_subtitle).to_contain_text(M.STAGE_2)
        bars = {b["key"]: b["orig"] for b in review.review_data()}
        assert HEAD_OFFICE_BARS <= set(bars), bars
        assert not any(k.startswith("ph_b") for k in bars), bars
        assert all(bars[k] == "pending" for k in HEAD_OFFICE_BARS), bars
        expect(review.office_verified_buttons).to_have_count(0)
    _expect_listed(o, "physical", label="Physical verification")


@aio_case("KAN-TC-817")
@allure.story(STORY)
@allure.title("TC-817: Stage 2 — branch office verification after the head office is verified")
def test_tc817_branch_verification(officer_at):
    """
    Given the application parked at 'branch_verification' (one branch office; head office verified)
    When  the officer opens its review page and Applications › Branch office verification
    Then  the review page is in Stage 2 with branch office 1's photo bars
    And   the list shows the application with "Branch 1 — <district>"

    AIO: KAN-TC-817 | KAN-12 AC-17 | data: map state 'branch_verification'
    """
    o = officer_at("branch_verification")
    with allure.step("Review page: Stage 2, branch office photos"):
        review = o.open_review()
        _expect_stage(review, ReviewStage.PHYSICAL)
        expect(review.stage_subtitle).to_contain_text(M.STAGE_2)
        keys = set(_bars(review))
        assert any(k.startswith("ph_b1_") for k in keys), keys
    row = _expect_listed(o, "branches", label="Branch office verification")
    expect(row).to_contain_text(M.BRANCH_ROW)


@aio_case("KAN-TC-818")
@allure.story(STORY)
@allure.title("TC-818: Approved — final approval given and the Form-II certificate issued")
def test_tc818_approved(officer_at):
    """
    Given the application parked at 'approved'
    When  the officer opens its review page, Licences & certificates and Applications › Approved
    Then  the review page reads "Approved — Certificate Issued · Closed" with the certificate (Registration No. =
          the Application ID) newest in the history
    And   Licences & certificates lists it with that Registration No.
    And   Applications › Approved lists it

    Applications › Approved is searched by the Application ID: the unfiltered list fails to load on dev
    (06-Nov-2026, defect #70, and any list holding an application given a post-hearing window).

    AIO: KAN-TC-818 | KAN-12 AC-18 | data: map state 'approved'
    """
    o = officer_at("approved")
    application_id = o.agency.application_id
    with allure.step("Review page: approved, certificate issued"):
        review = o.open_review()
        expect(review.stage_subtitle).to_have_text(F.APPROVED_STAGE)
        expect(review.history_items.first).to_contain_text(F.certificate_issued(application_id))
    with allure.step("Licences & certificates lists the certificate"):
        licences = AdminLicensesPage(o.review.page)
        licences.open(query=application_id)
        expect(licences.license_rows.filter(has_text=application_id)).to_have_count(1)
    _expect_listed(o, "approved", label="Approved")
