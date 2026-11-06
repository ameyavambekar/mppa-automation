"""
Application review — desktop scrutiny review loop (KAN-12)
==========================================================
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
refused on the client and change nothing.
"""

import re
from datetime import datetime, timedelta

import allure
from playwright.sync_api import expect

from fixtures.application_review_fixtures import record_loop_stage
from pages.admin.application_review_page import AdminApplicationReviewPage, ReviewStage
from pages.admin.applications_page import AdminApplicationsPage
from test_data.application_review_factory import ReviewLoopFactory as F
from utils.aio import aio_case

STORY = "Application review — desktop scrutiny loop"
HOLD = F.HOLD_ITEM_LABEL


def _listed_under(review: AdminApplicationReviewPage, step: str, application_id: str):
    applications = AdminApplicationsPage(review.page)
    applications.open("desktop", step)
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
    _, home, _, _ = agency_with_corrections(after_hearing=False)

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
    corrections, _, _, _ = agency_with_corrections(after_hearing=False)
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
    corrections, _, agency, _ = agency_with_corrections(after_hearing=False)

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
    corrections, _, agency, _ = agency_with_corrections(after_hearing=False)
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
    corrections, _, _, _ = agency_with_corrections(after_hearing=False)
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
    corrections, _, agency, review = agency_with_corrections(after_hearing=False)
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
    corrections, _, agency, review = agency_with_corrections(after_hearing=True)
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
