"""
Second Appeal (FORM-IV) — agency side (KAN-49; cases written for the old KAN-15)
=================================================================================
Covers KAN-TC-334…359 (rewritten 13-Nov-2026 for the redesigned FORM-IV, as KAN-14's FORM-III cases were on
04-Nov) on /module/agency/appeals/second.php, the Appeals card on Home and My Application. 346 (answer "filed
within 60 days") and 357 (form restored after a session timeout) are Deprecated: the limitation is worked out
by the portal and the form keeps no draft.

Test data. FORM-IV is offered only after the First Appeal is dismissed, and each agency can file once.

* Most tests open the form and FILE NOTHING — where the page asks "Submit your SECOND and FINAL appeal?" the
  test answers Cancel. They may borrow the agency parked at the map state 'first_appeal_dismissed'.
* TC-334 uses a refused agency without an appeal, TC-335 one whose First Appeal is pending.
* TC-353/354 read agencies whose Second Appeal is pending / decided (map states, read-only).
* TC-337 and TC-359 submit the form and may use up an agency for good: opt-in with RUN_APPEAL_FILING_TESTS=true.
* TC-355 (Under Review) needs a dismissed First Appeal more than 60 days old and skips until there is one.

Prepare dismissed First Appeals first (irreversible)::

    python -m utils.seed_appeals --decided 2

Known defects ("I & II Appeal" tab, logged for FORM-III and seen on FORM-IV too): #65 blank "Specify other
ground" accepted (TC-341), #66 My Application still invites an appeal (TC-353), #67 Email and Mobile both
numbered "4." (TC-336).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
import pytest
from playwright.sync_api import expect

from pages.agency_home_page import AgencyHomePage
from pages.first_appeal_page import FirstAppealPage
from pages.my_application_page import MyApplicationPage
from pages.second_appeal_page import SecondAppealPage
from test_data.first_appeal_factory import FirstAppealFactory as F
from test_data.first_appeal_factory import SecondAppealFactory as S
from utils import file_manager
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Second Appeal — agency (FORM-IV)"
IST = timezone(timedelta(hours=5, minutes=30))
DATE_FMT = "%d %b %Y"                       # 13 Nov 2026
MULTIPART_FORM = "form[enctype='multipart/form-data']"
STEP_FIRST = "First Appeal · Division"
STEP_SECOND = "Second Appeal · Commissionerate"


def _today():
    return datetime.now(IST).date()


def _squash(text: str) -> str:
    return " ".join((text or "").split())


def _nospace(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _appeal_number(sa) -> int:
    return int(sa.filed_appeal_number.inner_text().strip().lstrip("#"))


def _expect_refused_by_browser(sa: SecondAppealPage, field: str):
    """The browser's own checks stop the form at ``field`` — nothing is asked or submitted."""
    assert sa.invalid_fields() == [field], f"Fields the browser rejects: {sa.invalid_fields()}"
    prompt = sa.submit_and_handle_alert(action="dismiss")
    assert prompt == "", f"The page asked {prompt!r} instead of stopping at '{field}'"


def _expect_confirmation(sa: SecondAppealPage):
    """The form passes every check: the confirmation is asked — and answered Cancel (nothing is filed)."""
    assert sa.form_is_valid(), f"Fields the browser rejects: {sa.invalid_fields()}"
    prompt = sa.submit_and_handle_alert(action="dismiss")
    assert prompt == S.CONFIRM, f"Expected the submit confirmation, got {prompt!r}"


def _expect_not_filed(sa: SecondAppealPage):
    sa.open()
    expect(sa.appeal_form).to_have_count(1)
    expect(sa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))
    expect(sa.journey_status(STEP_SECOND)).to_have_text(re.compile("Not filed"))


def _first_appeal_card(page) -> FirstAppealPage:
    fa = FirstAppealPage(page)
    fa.open()
    expect(fa.filed_appeal_card).to_have_count(1)
    return fa


# ---------------------------------------------------------------------------
# Who is offered the form
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-334")
@allure.story(STORY)
@allure.title("TC-334: FORM-IV offers no form to a refused agency that has not filed a First Appeal")
def test_tc334_no_first_appeal(first_appeal_page):
    """
    Given a refused agency without any appeal
    When  it opens the Second Appeal page
    Then  no form is shown, only "Please file your First Appeal (FORM-III) first. …"
    And   "Appeals remaining: 2 of 2" and both appeal levels "— Not filed"

    AIO: KAN-TC-334 | data: state store agency 'rejected'
    """
    fa, _agency = first_appeal_page
    fa.open_second_appeal()
    expect(fa.page).to_have_title(S.TAB_TITLE)
    expect(fa.page.locator(MULTIPART_FORM)).to_have_count(0)
    expect(fa.blocking_note).to_have_text(F.SECOND_BEFORE_FIRST)
    expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=2))
    expect(fa.journey_status(STEP_FIRST)).to_have_text(re.compile("Not filed"))
    expect(fa.journey_status(STEP_SECOND)).to_have_text(re.compile("Not filed"))


@aio_case("KAN-TC-335")
@allure.story(STORY)
@allure.title("TC-335: FORM-IV offers no form while the First Appeal is pending")
def test_tc335_first_appeal_pending(appealed_agency_page):
    """
    Given an agency whose First Appeal #N awaits a decision
    When  it opens the Second Appeal page
    Then  no form is shown, only "Your First Appeal #N is still pending. …", with 1 of 2 appeals remaining

    AIO: KAN-TC-335 | data: state store agency 'first_appeal' (pending)
    """
    fa, _agency = appealed_agency_page
    if "Pending decision" not in fa.filed_appeal_title.text_content():
        pytest.skip("The filed First Appeal has been decided — no pending one to check.")
    n = int(fa.filed_appeal_number.inner_text().strip().lstrip("#"))
    fa.open_second_appeal()
    expect(fa.page.locator(MULTIPART_FORM)).to_have_count(0)
    expect(fa.blocking_note).to_have_text(F.SECOND_WHILE_PENDING.format(n=n))
    expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))
    expect(fa.journey_status(STEP_FIRST)).to_have_text(re.compile("Pending decision"))


# ---------------------------------------------------------------------------
# Filled in by the portal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-336")
@allure.story(STORY)
@allure.title("TC-336: FORM-IV opens from Home with its header and the appellant details read-only")
def test_tc336_opens_from_home_appellant_read_only(second_appeal_page):
    """
    Given an agency whose First Appeal was dismissed, on Home
    Then  the Appeals card shows "1 of 2 appeals remaining", Second Appeal "Not filed", the hint and
          "File Second Appeal"
    When  it clicks "File Second Appeal"
    Then  FORM-IV opens (tab title, breadcrumb, badge, heading, two header lines, only "← My Application"),
          with the two-appeals note, the journey and the addressee (the Commissioner, Maharashtra State)
    And   sections 1–4 show the agency's name, Registration No., address, e-mail and mobile as text matching
          the registration; nothing can be edited; every label has its own number (defect #67: "4." twice)

    AIO: KAN-TC-336 | data: agency with a dismissed First Appeal
    """
    sa, agency = second_appeal_page
    home = AgencyHomePage(sa.page)

    with allure.step("Home: the Appeals card offers the Second Appeal"):
        home.open()
        expect(home.appeals_remaining).to_have_text(F.HOME_REMAINING.format(n=1))
        expect(home.appeal_level_badge("Second Appeal")).to_have_text("Not filed")
        expect(home.appeals_hint).to_have_text(S.HOME_FILE_HINT)
        expect(home.second_appeal_links).to_have_text([S.HOME_FILE_LINK])

    with allure.step("Click 'File Second Appeal'"):
        home.second_appeal_links.first.click()
        sa.page.wait_for_url(re.compile(r"/agency/appeals/second\.php"))
        sa.wait_for_load()
        expect(sa.page).to_have_title(S.TAB_TITLE)
        expect(sa.breadcrumb).to_have_text(re.compile(S.BREADCRUMB))
        expect(sa.appeal_form).to_have_count(1)

    with allure.step("Verify the header, note and journey"):
        expect(sa.form_badge).to_be_visible()
        expect(sa.page_heading).to_have_text(S.HEADING)
        expect(sa.header_lines).to_have_text(S.HEADER_LINES)
        expect(sa.header_links).to_have_text(["← My Application"])
        expect(sa.two_appeals_note).to_contain_text(F.TWO_APPEALS_NOTE)
        expect(sa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))
        expect(sa.journey_status("Application")).to_have_text("Rejected")
        expect(sa.journey_status(STEP_FIRST)).to_have_text(re.compile("Rejected"))
        expect(sa.journey_status(STEP_SECOND)).to_have_text(re.compile("Not filed"))

    with allure.step("Verify the addressee and subject"):
        authority = sa.read_only_value("(c) Authority Passing the Order")
        text = _nospace(sa.addressee.text_content())
        assert _nospace(S.ADDRESSEE) in text, sa.addressee.text_content()
        assert _nospace(S.SUBJECT.format(authority=authority)) in text, sa.addressee.text_content()

    with allure.step("Verify the appellant details match the registration"):
        assert sa.get_agency_name()
        reg = sa.get_registration_no()
        assert re.fullmatch(r"\d{13}", reg), reg
        if agency.application_id:
            assert reg == agency.application_id
        if agency.email:
            assert sa.read_only_value("4. Email").lower() == agency.email.lower()
        if agency.mobile:
            assert sa.read_only_value("4. Mobile") == agency.mobile
        assert sa.read_only_value("3. Registered Address")
        expect(sa.card("1–4").locator("input, textarea, select, [contenteditable=true]")).to_have_count(0)

    with allure.step("Verify each label has its own number"):
        labels = sa.read_only_labels("1–4")
        numbers = [label.split(".")[0] for label in labels]
        assert len(set(numbers)) == len(numbers), f"Labels share a number (defect #67): {labels}"


@aio_case("KAN-TC-338")
@allure.story(STORY)
@allure.title("TC-338: Section 5 shows the First Appellate order, filled in and locked")
def test_tc338_first_appellate_order_locked(second_appeal_page):
    """
    Given an agency whose First Appeal #N was dismissed, on FORM-IV
    Then  section 5 shows Order Number FAA/<year>/<N>, the Date of Order, the authority (Deputy Commissioner,
          … <district> District) and the reason in the order — the same as FORM-III shows for the decision
    And   nothing in section 5 can be edited, with the note "These details are taken from the official order …"

    AIO: KAN-TC-338 | data: agency with a dismissed First Appeal
    """
    sa, _agency = second_appeal_page
    order_no = sa.get_order_number()
    order_date = sa.read_only_value("(b) Date of Order")
    authority = sa.read_only_value("(c) Authority Passing the Order")
    reason = sa.read_only_value("Reason given in the order")

    with allure.step("Verify the section is locked"):
        expect(sa.card("5").locator("input, textarea, select, [contenteditable=true]")).to_have_count(0)
        expect(sa.order_locked_note).to_have_text(F.ORDER_LOCKED)
        assert re.fullmatch(S.FIRST_AUTHORITY.format(district=r"[\w .&()-]+"), authority), authority
        assert reason

    with allure.step("Compare with the decided First Appeal on FORM-III"):
        fa = _first_appeal_card(sa.page)
        n = _appeal_number(fa)
        year = datetime.strptime(order_date, DATE_FMT).year
        assert order_no == f"FAA/{year}/{n}", order_no
        assert _squash(fa.filed_appeal_value("Sent to")) == authority
        decided = _squash(fa.filed_appeal_value("Decided on"))
        assert decided.startswith(order_date) and order_no in decided, decided
        remarks = _squash(fa.filed_appeal_value("Authority's remarks"))
        assert remarks in _squash(reason) or _squash(reason) in remarks, (remarks, reason)


@aio_case("KAN-TC-339")
@allure.story(STORY)
@allure.title("TC-339: Section 5 also shows the original refusal order of the Registering Authority")
def test_tc339_original_order_shown(second_appeal_page):
    """
    Given an agency whose First Appeal was dismissed, on FORM-IV
    Then  section 5 shows "Original Registering Authority Order" RA/REJ/<Application ID>/<yyyymmdd> and its date
    And   they are the order the First Appeal was filed against (FORM-III "Order appealed against")

    AIO: KAN-TC-339 | data: agency with a dismissed First Appeal
    """
    sa, _agency = second_appeal_page
    reg = sa.get_registration_no()
    original = sa.read_only_value("Original Registering Authority Order")
    original_date = sa.read_only_value("Date of Original Order")
    m = re.fullmatch(rf"RA/REJ/{reg}/(\d{{8}})", original)
    assert m, original
    assert datetime.strptime(original_date, DATE_FMT).strftime("%Y%m%d") == m.group(1)

    fa = _first_appeal_card(sa.page)
    assert _squash(fa.filed_appeal_value("Order appealed against")) == f"{original} dated {original_date}"


@aio_case("KAN-TC-345")
@allure.story(STORY)
@allure.title("TC-345: The limitation (section 9) is worked out by the portal")
def test_tc345_limitation_auto_calculated(second_appeal_page):
    """
    Given an agency whose First Appeal was dismissed, on FORM-IV
    Then  section 9 shows the date of communication (= the First Appellate order's date) and
          "✓ Yes — day N of 60", N being the days since then, with nothing to enter

    AIO: KAN-TC-345 | data: agency with a dismissed First Appeal
    """
    sa, _agency = second_appeal_page
    communicated = sa.read_only_value("(a) Date of communication of the order")
    assert communicated == sa.read_only_value("(b) Date of Order")
    days = (_today() - datetime.strptime(communicated, DATE_FMT).date()).days
    if days > F.DECISION_DAYS:
        pytest.skip(f"The order is {days} days old — TC-355 covers an appeal past 60 days.")
    assert sa.read_only_value("(b) Filed within 60 days?") == F.WITHIN_LIMIT.format(days=days)
    expect(sa.card("9").locator("input, textarea, select")).to_have_count(0)


# ---------------------------------------------------------------------------
# Grounds, facts and relief
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-340")
@allure.story(STORY)
@allure.title("TC-340: Submitting without any ground of appeal is refused")
def test_tc340_no_ground_refused(second_appeal_page, second_appeal_no_ground_data):
    """
    Given an agency on FORM-IV with everything filled except the grounds
    When  it clicks Submit
    Then  "Please tick at least one ground of appeal." is shown, no confirmation is asked and nothing is filed

    AIO: KAN-TC-340 | data: second_appeal_no_ground
    """
    sa, _agency = second_appeal_page
    data = second_appeal_no_ground_data

    with allure.step("Verify the six grounds"):
        expect(sa.card("6")).to_contain_text("Tick one or more grounds (click anywhere on the box):")
        expect(sa.page.locator("input[name='grounds[]']")).to_have_count(len(sa.GROUNDS))

    with allure.step("Submit without a ground"):
        sa.fill_appeal(data)
        assert sa.submit_and_handle_alert(action="dismiss") == data.expected_error

    with allure.step("Verify the form is kept and nothing was filed"):
        expect(sa.brief_facts_textarea).to_have_value(data.brief_facts)
        _expect_not_filed(sa)


@aio_case("KAN-TC-341")
@allure.story(STORY)
@allure.title("TC-341: Ticking 'Other' shows a required 'Specify other ground' field")
def test_tc341_other_ground_required(second_appeal_page, second_appeal_other_blank_data):
    """
    Given an agency on FORM-IV
    When  it ticks "Other — specify below"
    Then  "Specify other ground *" appears, keeps at most 300 characters and hides when unticked
    And   submitting with it blank is refused (fails like FORM-III defect "I & II Appeal" #65: the confirmation
          is asked)

    AIO: KAN-TC-341 | data: second_appeal_other_ground_blank
    """
    sa, _agency = second_appeal_page

    with allure.step("Tick 'Other' and type 301 characters"):
        sa.type_other_ground(F.other_ground_too_long())
        expect(sa.other_ground_box).to_be_visible()
        expect(sa.other_ground_box).to_contain_text("Specify other ground *")
        assert len(sa.grounds_other_input.input_value()) == F.OTHER_MAX

    with allure.step("Untick 'Other'"):
        sa.ground_checkbox("other").uncheck()
        expect(sa.other_ground_box).to_be_hidden()

    with allure.step("Submit with 'Other' ticked and nothing specified"):
        sa.fill_appeal(second_appeal_other_blank_data)
        prompt = sa.submit_and_handle_alert(action="dismiss")
        assert prompt == "" and "grounds_other" in sa.invalid_fields(), (
            f"A blank 'Specify other ground' was not stopped — the page asked {prompt!r} (as defect #65)")


@aio_case("KAN-TC-342")
@allure.story(STORY)
@allure.title("TC-342: Brief Facts is required and needs at least 20 characters")
def test_tc342_brief_facts(second_appeal_page):
    """
    Given an agency on FORM-IV with everything else valid
    When  Brief Facts is blank, then 19 characters, then 20
    Then  blank and 19 are stopped by the browser; 20 passes and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-342 | data: brief facts of 0, 19 and 20 characters
    """
    sa, _agency = second_appeal_page
    expect(sa.brief_facts_textarea).to_have_attribute("placeholder", S.BRIEF_FACTS_PLACEHOLDER)
    path = file_manager.VALID_CERTIFICATE

    with allure.step("Blank"):
        sa.fill_appeal(S.brief_facts_of_length(path, 0))
        _expect_refused_by_browser(sa, "brief_facts")

    with allure.step("19 characters"):
        sa.fill_brief_facts(S.brief_facts_of_length(path, F.FACTS_MIN - 1).brief_facts)
        _expect_refused_by_browser(sa, "brief_facts")

    with allure.step("20 characters"):
        sa.fill_brief_facts(S.brief_facts_of_length(path, F.FACTS_MIN).brief_facts)
        _expect_confirmation(sa)


@aio_case("KAN-TC-343")
@allure.story(STORY)
@allure.title("TC-343: A relief type is required, and only one can be chosen")
def test_tc343_relief_type(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency on FORM-IV with everything else valid
    Then  three relief types are offered and choosing one unselects the others
    When  it submits with no relief type
    Then  the browser stops at the relief type; nothing is asked or filed

    AIO: KAN-TC-343 | data: second_appeal_required_documents without a relief type
    """
    sa, _agency = second_appeal_page

    with allure.step("Only one relief type at a time"):
        for value in sa.RELIEFS:
            sa.select_relief_type(value)
            for other in sa.RELIEFS:
                if other == value:
                    expect(sa.relief_radio(other)).to_be_checked()
                else:
                    expect(sa.relief_radio(other)).not_to_be_checked()

    with allure.step("Submit with no relief type"):
        sa.open()                       # a fresh load: a radio cannot be unticked
        data = second_appeal_valid_data
        data.relief_type = ""
        sa.fill_appeal(data)
        _expect_refused_by_browser(sa, "relief_type")


@aio_case("KAN-TC-344")
@allure.story(STORY)
@allure.title("TC-344: Specific relief sought is required and needs at least 10 characters")
def test_tc344_relief_sought(second_appeal_page):
    """
    Given an agency on FORM-IV with a relief type and everything else valid
    When  the relief text is blank, then 9 characters, then 10
    Then  blank and 9 are stopped by the browser; 10 passes and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-344 | data: relief text of 0, 9 and 10 characters
    """
    sa, _agency = second_appeal_page
    expect(sa.relief_sought_textarea).to_have_attribute("placeholder", "State precisely the relief you are seeking…")
    path = file_manager.VALID_CERTIFICATE

    with allure.step("Blank"):
        sa.fill_appeal(S.relief_of_length(path, 0))
        _expect_refused_by_browser(sa, "relief_sought")

    with allure.step("9 characters"):
        sa.fill_relief_sought(S.relief_of_length(path, F.RELIEF_MIN - 1).relief_sought)
        _expect_refused_by_browser(sa, "relief_sought")

    with allure.step("10 characters"):
        sa.fill_relief_sought(S.relief_of_length(path, F.RELIEF_MIN).relief_sought)
        _expect_confirmation(sa)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-347")
@allure.story(STORY)
@allure.title("TC-347: Submitting without the Registering Authority's order (b) is refused")
def test_tc347_ra_order_required(second_appeal_page):
    """
    Given an agency on FORM-IV
    Then  section 10 lists (b) Order of the Registering Authority and (c) Order of the First Appellate
          Authority marked REQUIRED and (d) Any other document optional, each "PDF only · max 2 MB"
    When  it fills everything with (c) attached but not (b), and clicks Submit
    Then  the browser stops at (b); nothing is asked or filed

    AIO: KAN-TC-347 | data: second_appeal_without_ra_order
    """
    sa, _agency = second_appeal_page

    with allure.step("Verify the document slots"):
        boxes = sa.card("10").locator(".ap-up")
        expect(boxes).to_have_count(len(sa.DOC_SLOTS))
        for slot, label in S.DOC_LABELS.items():
            expect(sa.document_box(slot)).to_contain_text(label)
            expect(sa.document_box(slot)).to_contain_text("PDF only · max 2 MB")
            if slot in S.REQUIRED_SLOTS:
                expect(sa.document_box(slot)).to_contain_text("REQUIRED")
            else:
                expect(sa.document_box(slot)).not_to_contain_text("REQUIRED")

    with allure.step("Submit without (b)"):
        sa.fill_appeal(S.without_document(file_manager.VALID_CERTIFICATE, "ra_order"))
        _expect_refused_by_browser(sa, sa.DOC_SLOTS["ra_order"])


@aio_case("KAN-TC-348")
@allure.story(STORY)
@allure.title("TC-348: Submitting without the First Appellate Authority's order (c) is refused")
def test_tc348_fa1_order_required(second_appeal_page):
    """
    Given an agency on FORM-IV
    When  it fills everything with (b) attached but not (c), and clicks Submit
    Then  the browser stops at (c); nothing is asked or filed

    AIO: KAN-TC-348 | data: second_appeal_without_fa1_order
    """
    sa, _agency = second_appeal_page
    sa.fill_appeal(S.without_document(file_manager.VALID_CERTIFICATE, "fa1_order"))
    _expect_refused_by_browser(sa, sa.DOC_SLOTS["fa1_order"])


@aio_case("KAN-TC-349")
@allure.story(STORY)
@allure.title("TC-349: Every document slot offers PDF files only")
def test_tc349_pdf_only(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency on FORM-IV
    Then  every document slot's file picker offers PDF only (.pdf, application/pdf)
    When  it attaches a ~360 KB PDF as (b) and (c) and completes the form
    Then  the files are taken and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-349 | data: certificate.pdf (~360 KB)
    """
    sa, _agency = second_appeal_page

    with allure.step("Verify every slot offers PDF only"):
        for slot in sa.DOC_SLOTS:
            expect(sa.document_input(slot)).to_have_attribute("accept", ".pdf,application/pdf")

    with allure.step("Attach PDFs and complete the form"):
        sa.fill_appeal(second_appeal_valid_data)
        for slot in S.REQUIRED_SLOTS:
            assert sa.files_chosen(slot) == 1
        _expect_confirmation(sa)


@aio_case("KAN-TC-350")
@allure.story(STORY)
@allure.title("TC-350: A document over 2 MB is refused in any slot")
def test_tc350_oversized_document(second_appeal_page):
    """
    Given an agency on FORM-IV
    When  it submits with a 3 MB PDF as (b), then with a valid (b) and the 3 MB PDF as (d)
    Then  "Each document must be a PDF of 2 MB or less." is shown each time; nothing is asked or filed

    AIO: KAN-TC-350 | data: oversized.pdf (> 2 MB)
    """
    sa, _agency = second_appeal_page
    path, big = file_manager.VALID_CERTIFICATE, file_manager.OVERSIZED_FILE

    with allure.step("3 MB PDF as the Registering Authority's order (b)"):
        data = S.oversized(path, big, "ra_order")
        sa.fill_appeal(data)
        assert sa.submit_and_handle_alert(action="dismiss") == data.expected_error

    with allure.step("Valid (b), 3 MB PDF as 'Any other document' (d)"):
        data = S.oversized(path, big, "other")
        sa.upload_documents(data.documents)
        assert sa.submit_and_handle_alert(action="dismiss") == data.expected_error

    with allure.step("Verify nothing was filed"):
        _expect_not_filed(sa)


@aio_case("KAN-TC-356")
@allure.story(STORY)
@allure.title("TC-356: (d) Any other document is optional; cancelling the confirmation files nothing")
def test_tc356_optional_document_and_cancel(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency on FORM-IV with everything filled and only (b) and (c) attached
    When  it clicks Submit
    Then  "Submit your SECOND and FINAL appeal? …" is asked — (d) does not block it
    When  it answers Cancel
    Then  the form keeps every entry and, after a reload, nothing is filed (1 of 2 remaining)

    AIO: KAN-TC-356 | data: second_appeal_required_documents
    """
    sa, _agency = second_appeal_page
    data = second_appeal_valid_data

    with allure.step("Fill with (b) and (c) only and cancel the confirmation"):
        sa.fill_appeal(data)
        assert sa.files_chosen("other") == 0
        _expect_confirmation(sa)

    with allure.step("Verify the form is unchanged"):
        expect(sa.brief_facts_textarea).to_have_value(data.brief_facts)
        expect(sa.relief_sought_textarea).to_have_value(data.relief_sought)
        expect(sa.submit_button).to_have_text(S.SUBMIT_LABEL)
        expect(sa.submit_button).to_be_enabled()

    with allure.step("Reload: nothing was filed"):
        _expect_not_filed(sa)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-351")
@allure.story(STORY)
@allure.title("TC-351: Submitting without ticking the declaration is refused")
def test_tc351_declaration_required(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency on FORM-IV with everything filled but the declaration unticked
    When  it clicks Submit
    Then  the browser stops at the declaration; once ticked, the confirmation is asked (answered Cancel)

    AIO: KAN-TC-351 | data: second_appeal_required_documents, declare=False
    """
    sa, _agency = second_appeal_page
    data = second_appeal_valid_data
    data.declare = False
    expect(sa.declaration_text).to_have_text(F.DECLARATION)

    with allure.step("Submit without the declaration"):
        sa.fill_appeal(data)
        _expect_refused_by_browser(sa, "declare")

    with allure.step("Tick it and submit"):
        sa.accept_declaration()
        _expect_confirmation(sa)


@aio_case("KAN-TC-352")
@allure.story(STORY)
@allure.title("TC-352: Verification: the date is today and fixed; signatory, designation and place are required")
def test_tc352_verification(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency on FORM-IV
    Then  the Verification Date shows today (DD Mon YYYY) as text with nothing to change it
    And   Authorised signatory, Designation and Place are pre-filled
    When  each is cleared in turn (everything else valid) and Submit is clicked
    Then  the browser stops at that field each time; nothing is asked or filed

    AIO: KAN-TC-352 | data: today (IST), second_appeal_required_documents
    """
    sa, _agency = second_appeal_page

    with allure.step("The date is today and cannot be changed"):
        expect(sa.verification_date).to_have_text(_today().strftime(DATE_FMT))
        expect(sa.card("✓").locator("input[type=date], input[name*=date]")).to_have_count(0)

    fields = {"signatory_name": sa.signatory_name_input, "signatory_designation": sa.signatory_designation_input,
              "place": sa.place_input}
    with allure.step("The three fields are pre-filled"):
        prefilled = {name: box.input_value() for name, box in fields.items()}
        assert all(v.strip() for v in prefilled.values()), prefilled

    sa.fill_appeal(second_appeal_valid_data)
    for name, box in fields.items():
        with allure.step(f"Clear '{name}' and submit"):
            box.fill("")
            _expect_refused_by_browser(sa, name)
            box.fill(prefilled[name])


@aio_case("KAN-TC-358")
@allure.story(STORY)
@allure.title("TC-358: Leaving a half-filled FORM-IV asks nothing and files nothing")
def test_tc358_leave_half_filled(second_appeal_page):
    """
    Given an agency on FORM-IV that has typed its Brief Facts
    When  it clicks "← My Application"
    Then  My Application opens without any prompt
    And   back on FORM-IV the form is empty again and nothing was filed (1 of 2 remaining)

    AIO: KAN-TC-358 | data: brief facts only
    """
    sa, _agency = second_appeal_page
    page, dialogs = sa.page, []

    def on_dialog(dialog):
        dialogs.append(dialog.message)
        dialog.accept()

    with allure.step("Type Brief Facts and click '← My Application'"):
        sa.fill_brief_facts("QA automation: half-filled Second Appeal, never submitted.")
        page.on("dialog", on_dialog)
        try:
            sa.my_application_link.click()
            page.wait_for_url(re.compile(r"/forms/view_application\.php"))
        finally:
            page.remove_listener("dialog", on_dialog)
        assert dialogs == [], f"Leaving asked: {dialogs}"

    with allure.step("Back on FORM-IV: empty, nothing filed"):
        _expect_not_filed(sa)
        expect(sa.brief_facts_textarea).to_have_value("")


# ---------------------------------------------------------------------------
# After filing
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-353")
@allure.story(STORY)
@allure.title("TC-353: A filed Second Appeal can be followed on FORM-IV, Home and My Application")
def test_tc353_track_filed_second_appeal(filed_second_appeal_page):
    """
    Given an agency whose Second Appeal #N is pending
    Then  FORM-IV shows only the card "#N · Your Second Appeal — Pending decision": filed on, sent to the
          Commissioner, the First Appellate order appealed against, decision expected 60 days after filing
    And   Home shows "0 of 2 appeals remaining", Second Appeal "#N" "Pending — decision by <date>", the hint and
          "View Second Appeal"
    And   My Application no longer invites an appeal (fails like defect "I & II Appeal" #66)

    AIO: KAN-TC-353 | data: agency with a pending Second Appeal (map state 'second_appeal_pending')
    """
    sa, _agency = filed_second_appeal_page("pending")
    n = _appeal_number(sa)

    with allure.step("FORM-IV: the appeal card"):
        expect(sa.appeal_form).to_have_count(0)
        expect(sa.filed_appeal_title).to_have_text(re.compile("Your Second Appeal — Pending decision"))
        assert _squash(sa.filed_appeal_value("Sent to")) == S.SENT_TO
        assert re.fullmatch(r"FAA/\d{4}/\d+ dated \d{2} \w{3} \d{4}", _squash(sa.filed_appeal_value("Order appealed against")))
        filed = datetime.strptime(sa.filed_appeal_value("Filed on"), DATE_FMT).date()
        due = filed + timedelta(days=F.DECISION_DAYS)
        left = (due - _today()).days
        assert _squash(sa.filed_appeal_value("Decision expected by")) == f"{due.strftime(DATE_FMT)} ({left} day(s) left)"
        expect(sa.journey_status(STEP_SECOND)).to_have_text(re.compile("Pending decision"))

    with allure.step("Home"):
        home = AgencyHomePage(sa.page)
        home.open()
        expect(home.second_appeal_links).to_have_text([S.HOME_VIEW_LINK])
        expect(home.appeals_remaining).to_have_text(F.HOME_REMAINING.format(n=0))
        expect(home.appeal_level_row("Second Appeal")).to_contain_text(f"#{n}")
        expect(home.appeal_level_badge("Second Appeal")).to_have_text(
            F.HOME_PENDING_BADGE.format(date=due.strftime(DATE_FMT)))
        expect(home.appeals_hint).to_have_text(F.HOME_PENDING_HINT)

    with allure.step("My Application no longer invites an appeal"):
        my_app = MyApplicationPage(sa.page)
        my_app.open()
        expect(my_app.status_banner).not_to_contain_text(F.MY_APP_INVITE)


@aio_case("KAN-TC-354")
@allure.story(STORY)
@allure.title("TC-354: A Second Appeal cannot be filed again, pending or decided")
def test_tc354_cannot_file_twice(filed_second_appeal_page):
    """
    Given an agency whose Second Appeal is pending
    When  it opens FORM-IV and reloads it
    Then  only the appeal card is shown — no form, no Submit — with "Appeals remaining: 0 of 2"
    Given an agency whose Second Appeal was decided (rejected)
    Then  FORM-IV shows no form, "Your Second Appeal was rejected. This decision is final …" and Result
          "Final: Rejected"

    AIO: KAN-TC-354 | data: map states 'second_appeal_pending' and 'second_appeal_decided'
    """
    sa, _agency = filed_second_appeal_page("pending")
    for attempt in ("Open", "Reload"):
        with allure.step(f"Pending — {attempt} FORM-IV"):
            sa.open()
            expect(sa.appeal_form).to_have_count(0)
            expect(sa.submit_button).to_have_count(0)
            expect(sa.filed_appeal_card).to_have_count(1)
            expect(sa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=0))

    sa, _agency = filed_second_appeal_page("decided")
    with allure.step("Decided — the decision is final"):
        expect(sa.page.locator(MULTIPART_FORM)).to_have_count(0)
        expect(sa.blocking_note).to_have_text(S.DECIDED_FINAL)
        expect(sa.filed_appeal_title).to_have_text(re.compile("Your Second Appeal — Rejected"))
        expect(sa.journey_status("Result")).to_have_text(re.compile("Final: Rejected"))
        expect(sa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=0))


@aio_case("KAN-TC-355")
@allure.story(STORY)
@allure.title("TC-355: A Second Appeal more than 60 days after the First Appellate order")
def test_tc355_beyond_sixty_days(second_appeal_page, second_appeal_valid_data):
    """
    Given an agency whose First Appeal was dismissed more than 60 days ago, on FORM-IV
    Then  section 9 no longer says "✓ Yes"
    And   the form can still be completed: the confirmation is asked (answered Cancel)

    AIO: KAN-TC-355 (Under Review — needs an order over 60 days old; skips until one exists)
    """
    sa, _agency = second_appeal_page
    communicated = sa.read_only_value("(a) Date of communication of the order")
    days = (_today() - datetime.strptime(communicated, DATE_FMT).date()).days
    if days <= F.DECISION_DAYS:
        pytest.skip(f"The First Appellate order is only {days} day(s) old — needs one over 60 days.")
    assert not sa.read_only_value("(b) Filed within 60 days?").startswith("✓ Yes")
    sa.fill_appeal(second_appeal_valid_data)
    _expect_confirmation(sa)


# ---------------------------------------------------------------------------
# Filing (opt-in: RUN_APPEAL_FILING_TESTS=true — uses up an agency)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-337")
@allure.story(STORY)
@allure.title("TC-337: Filing a complete Second Appeal shows its number and the appeal card")
def test_tc337_file_complete_second_appeal(appeal_filing_allowed, second_appeal_filing_page, second_appeal_full_data):
    """
    Given an agency whose First Appeal was dismissed, on FORM-IV
    When  it files a Second Appeal with two grounds, facts, relief, all three documents and the declaration
    Then  "Submit your SECOND and FINAL appeal? …" is asked; after OK the page confirms Second Appeal #N and shows
          the card "#N · Your Second Appeal — Pending decision" with every detail
    And   "Appeals remaining: 0 of 2" and Second Appeal · Commissionerate "Pending decision"

    AIO: KAN-TC-337 | data: second_appeal_valid_with_documents (uses up the agency)
    """
    sa, agency = second_appeal_filing_page
    data = second_appeal_full_data
    order_no, order_date = sa.get_order_number(), sa.read_only_value("(b) Date of Order")

    with allure.step("Fill and submit the appeal"):
        sa.fill_appeal(data)
        assert sa.submit() == S.CONFIRM
        TestStateStore().record_agency_status(username=agency.username, status="second_appeal",
                                              data={"appeal_status": "filed"})

    with allure.step("Verify the confirmation and the appeal card"):
        n = _appeal_number(sa)
        expect(sa.success_alert).to_contain_text(f"#{n}")
        expect(sa.success_alert).to_contain_text("Second Appeal")
        expect(sa.appeal_form).to_have_count(0)
        expect(sa.filed_appeal_title).to_have_text(re.compile("Your Second Appeal — Pending decision"))
        today = _today()
        due = today + timedelta(days=F.DECISION_DAYS)
        assert sa.filed_appeal_value("Filed on") == today.strftime(DATE_FMT)
        assert _squash(sa.filed_appeal_value("Sent to")) == S.SENT_TO
        assert sa.filed_appeal_value("Order appealed against") == f"{order_no} dated {order_date}"
        assert sa.filed_appeal_value("Grounds") == "Non-consideration of material record, Violation of principles of natural justice"
        assert sa.filed_appeal_value("Relief sought") == f"{data.relief_type} — {data.relief_sought}"
        assert _squash(sa.filed_appeal_value("Decision expected by")) == (
            f"{due.strftime(DATE_FMT)} ({F.DECISION_DAYS} day(s) left)")

    with allure.step("Verify the note and the progress strip"):
        expect(sa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=0))
        expect(sa.journey_status(STEP_SECOND)).to_have_text(re.compile("Pending decision"))


@aio_case("KAN-TC-359")
@allure.story(STORY)
@allure.title("TC-359: An empty (0-byte) PDF is not accepted")
def test_tc359_empty_pdf_refused(appeal_filing_allowed, second_appeal_filing_page, second_appeal_empty_document_data):
    """
    Given an agency on FORM-IV
    When  an empty 0-byte PDF is attached as (b) and the appeal is submitted
    Then  the portal refuses it with a message and nothing is filed

    AIO: KAN-TC-359 (Under Review) | data: second_appeal_empty_ra_order (files the appeal if the portal accepts it)
    """
    sa, agency = second_appeal_filing_page
    sa.fill_appeal(second_appeal_empty_document_data)
    sa.submit()
    if sa.has_existing_appeal():
        TestStateStore().record_agency_status(username=agency.username, status="second_appeal",
                                              data={"appeal_status": "filed", "note": "filed with an empty PDF"})
        pytest.fail("The portal filed the Second Appeal with an empty PDF as (b) — it should have refused it.")
    expect(sa.error_alert).to_be_visible()
    _expect_not_filed(sa)
