"""
First Appeal (FORM-III) — agency side (KAN-14)
==============================================
Covers KAN-TC-302…333 (rewritten 04-Nov-2026 for the redesigned FORM-III) and KAN-TC-741…744 on
/module/agency/appeals/first.php, the Appeals card on Home and the status banner on My Application.

Test data. Only an agency whose application was refused can file, and each can file one First Appeal.
Refused agencies are prepared on the Officer Console and recorded as ``rejected`` in the state store;
one that has filed is ``first_appeal``.

* Most tests open FORM-III for a refused agency and FILE NOTHING — where the page asks "Submit your
  First Appeal?" the test answers Cancel.
* TC-321, 322, 327, 333 submit the form and may use up a refused agency for good: opt-in with
  RUN_APPEAL_FILING_TESTS=true.
* TC-328, 329, 331, 743 reuse an agency whose appeal awaits a decision; TC-744 needs a decided one.

Prepare the data first (only the shortfall is built; refusing, filing and deciding cannot be undone)::

    python -m utils.seed_appeals --dry-run
    python -m utils.seed_appeals                 # 5 refused, 1 pending, 1 decided — enough for the filing tests
    python -m utils.seed_appeals --refused 1     # without RUN_APPEAL_FILING_TESTS

Known defects ("I & II Appeal" tab): #64 no confirmation e-mail (TC-743), #65 blank "Specify other
ground" accepted (TC-310), #66 My Application still invites an appeal after filing (TC-328), #67 Email and
Mobile both numbered "4." (TC-304), #68 no e-mail when the appeal is decided (TC-744).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
import pytest
from playwright.sync_api import expect

from pages.agency_home_page import AgencyHomePage
from pages.first_appeal_page import FirstAppealPage, MY_APPLICATION_URL
from pages.my_application_page import MyApplicationPage
from test_data.first_appeal_factory import FirstAppealFactory as F
from utils import file_manager
from utils.aio import aio_case
from utils.email_otp import get_emails_to
from utils.state_store import TestStateStore

STORY = "First Appeal — agency (FORM-III)"
IST = timezone(timedelta(hours=5, minutes=30))
DATE_FMT = "%d %b %Y"                       # 04 Nov 2026
MULTIPART_FORM = "form[enctype='multipart/form-data']"


def _today():
    return datetime.now(IST).date()


def _squash(text: str) -> str:
    return " ".join(text.split())


def _district(fa: FirstAppealPage) -> str:
    """The district named in '(c) Authority Passing the Order' ('Registering Authority, X District')."""
    m = re.fullmatch(r"Registering Authority, (.+) District", fa.read_only_value("(c) Authority Passing the Order"))
    assert m, fa.read_only_value("(c) Authority Passing the Order")
    return m.group(1)


def _appeal_number(fa: FirstAppealPage) -> int:
    return int(fa.filed_appeal_number.inner_text().strip().lstrip("#"))


def _expect_refused_by_browser(fa: FirstAppealPage, field: str):
    """The browser's own checks stop the form at ``field`` — nothing is asked or submitted."""
    assert fa.invalid_fields() == [field], f"Fields the browser rejects: {fa.invalid_fields()}"
    prompt = fa.submit_and_handle_alert(action="dismiss")
    assert prompt == "", f"The page asked {prompt!r} instead of stopping at '{field}'"


def _expect_confirmation(fa: FirstAppealPage):
    """The form passes every check: the confirmation is asked — and answered Cancel (nothing is filed)."""
    assert fa.form_is_valid(), f"Fields the browser rejects: {fa.invalid_fields()}"
    prompt = fa.submit_and_handle_alert(action="dismiss")
    assert prompt == F.CONFIRM, f"Expected the submit confirmation, got {prompt!r}"


def _expect_not_filed(fa: FirstAppealPage):
    fa.open()
    expect(fa.appeal_form).to_have_count(1)
    expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=2))
    expect(fa.journey_status("First Appeal · Division")).to_have_text(re.compile("Not filed"))


def _submit_expecting_refusal(fa: FirstAppealPage, agency, what: str):
    """Submits (accepting the confirmation) something the portal must refuse. If it files the appeal anyway,
    the agency is recorded as having appealed and the test fails."""
    fa.submit()
    if fa.has_existing_appeal():
        TestStateStore().record_agency_status(username=agency.username, status="first_appeal",
                                              data={"appeal_status": "filed", "note": f"filed with {what}"})
        pytest.fail(f"The portal filed the First Appeal with {what} — it should have refused it.")
    expect(fa.error_alert).to_be_visible()
    _expect_not_filed(fa)


# ---------------------------------------------------------------------------
# Where the agency finds the First Appeal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-302")
@allure.story(STORY)
@allure.title("TC-302: Only a refused agency is offered the First Appeal on Home and My Application")
def test_tc302_appeal_offered_only_when_rejected(page, agency_login):
    """
    Given a refused agency (no appeal yet) and an agency whose application is Submitted
    When  each looks at Home and My Application
    Then  the refused agency sees "File First Appeal", the Appeals card (2 of 2 remaining, the order's
          reason, both levels Not filed, the 60-day hint) and "File Appeal" on My Application
    And   the Submitted agency sees no appeal button, link or Appeals card

    AIO: KAN-TC-302 | data: state store agencies 'rejected' and 'desktop_scrutiny'
    """
    home, my_app = AgencyHomePage(page), MyApplicationPage(page)

    with allure.step("Log in as the refused agency and look at Home"):
        agency_login("rejected")
        home.open()
        expect(home.first_appeal_links).to_have_text(["File First Appeal"])
        expect(home.appeals_remaining).to_have_text(F.HOME_REMAINING.format(n=2))
        expect(home.appeals_order_reason).to_contain_text("Reason given in the order:")
        expect(home.appeal_level_row("First Appeal")).to_contain_text("Divisional Appellate Authority (FORM-III)")
        expect(home.appeal_level_badge("First Appeal")).to_have_text("Not filed")
        expect(home.appeal_level_row("Second Appeal")).to_contain_text("Commissionerate (FORM-IV)")
        expect(home.appeal_level_badge("Second Appeal")).to_have_text("Not filed")
        expect(home.appeals_hint).to_have_text(F.HOME_FILE_HINT)
        reason = home.appeals_order_reason.inner_text().split(":", 1)[1]

    with allure.step("Open My Application"):
        my_app.open()
        expect(my_app.status_banner).to_contain_text(F.MY_APP_INVITE)
        assert _squash(my_app.admin_remarks_text()) == _squash(reason)
        assert my_app.file_appeal_links.count() >= 1
        expect(my_app.file_appeal_links.first).to_have_text("File Appeal")

    with allure.step("Log in as the Submitted agency: no appeal anywhere"):
        agency_login("desktop_scrutiny")
        home.open()
        expect(home.appeals_card).to_have_count(0)
        expect(home.first_appeal_links).to_have_count(0)
        my_app.open()
        expect(my_app.file_appeal_links).to_have_count(0)


@aio_case("KAN-TC-303")
@allure.story(STORY)
@allure.title("TC-303: FORM-III opens from Home with its heading, the two-appeals note and the progress strip")
def test_tc303_form_opens_from_home(page, agency_login):
    """
    Given a refused agency on Home
    When  it clicks "File First Appeal"
    Then  FORM-III opens (tab title, breadcrumb) with the FORM-III badge, heading, the two header lines and
          only a "← My Application" button
    And   the two-appeals note with "Appeals remaining: 2 of 2", the progress strip and the addressee
          (Deputy Commissioner of the agency's district) are shown

    AIO: KAN-TC-303 | data: state store agency 'rejected'
    """
    agency_login("rejected")
    home, fa = AgencyHomePage(page), FirstAppealPage(page)

    with allure.step("Click 'File First Appeal' on Home"):
        home.open()
        home.first_appeal_links.first.click()
        page.wait_for_url(re.compile(r"/agency/appeals/first\.php"))
        fa.wait_for_load()
        expect(page).to_have_title(F.TAB_TITLE)
        expect(fa.breadcrumb).to_have_text(re.compile(r"Home\s*›\s*My Application\s*›\s*First Appeal \(FORM-III\)"))
        expect(fa.appeal_form).to_have_count(1)

    with allure.step("Verify the header"):
        expect(fa.form_badge).to_be_visible()
        expect(fa.page_heading).to_have_text(F.HEADING)
        expect(fa.header_lines).to_have_text(F.HEADER_LINES)
        expect(fa.header_links).to_have_text(["← My Application"])
        expect(fa.header_links.first).to_have_attribute("href", re.compile(r"view_application\.php$"))

    with allure.step("Verify the two-appeals note and the progress strip"):
        expect(fa.two_appeals_note).to_contain_text(F.TWO_APPEALS_NOTE)
        expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=2))
        expect(fa.journey_status("Application")).to_have_text("Rejected")
        expect(fa.journey_status("First Appeal · Division")).to_have_text(re.compile(r"— Not filed"))
        expect(fa.journey_status("Second Appeal · Commissionerate")).to_have_text(re.compile(r"— Not filed"))
        expect(fa.journey_status("Result")).to_have_text(re.compile("Awaiting"))

    with allure.step("Verify the addressee and subject"):
        district = _district(fa)
        text = _squash(fa.addressee.inner_text())
        assert F.ADDRESSEE.format(district=district) in text, text
        assert F.SUBJECT.format(district=district) in text, text


# ---------------------------------------------------------------------------
# Filled in by the portal
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-304")
@allure.story(STORY)
@allure.title("TC-304: Appellant details (sections 1–4) are filled in from the registration and cannot be edited")
def test_tc304_appellant_read_only(first_appeal_page):
    """
    Given a refused agency on FORM-III
    Then  sections 1–4 show its name, Registration No. (13-digit Application ID), address, email and mobile
          as text matching the registration — nothing can be edited
    And   every label has its own number (known defect "I & II Appeal" #67: Email and Mobile are both "4.")

    AIO: KAN-TC-304 | data: state store agency 'rejected'
    """
    fa, agency = first_appeal_page

    with allure.step("Verify the values match the registration"):
        assert fa.get_agency_name()
        reg = fa.get_registration_no()
        assert re.fullmatch(r"\d{13}", reg), reg
        if agency.application_id:
            assert reg == agency.application_id
        email, mobile = fa.read_only_value("4. Email"), fa.read_only_value("4. Mobile")
        if agency.email:
            assert email.lower() == agency.email.lower()
        if agency.mobile:
            assert mobile == agency.mobile
        assert fa.read_only_value("3. Registered Address")

    with allure.step("Verify nothing in sections 1–4 can be edited"):
        expect(fa.card("1–4").locator("input, textarea, select, [contenteditable=true]")).to_have_count(0)

    with allure.step("Verify each label has its own number"):
        labels = fa.read_only_labels("1–4")
        numbers = [label.split(".")[0] for label in labels]
        assert len(set(numbers)) == len(numbers), f"Labels share a number (defect #67): {labels}"


@aio_case("KAN-TC-305")
@allure.story(STORY)
@allure.title("TC-305: Order details (section 5) are taken from the refusal order and cannot be changed")
def test_tc305_order_details_locked(first_appeal_page):
    """
    Given a refused agency on FORM-III
    Then  section 5 shows Order Number RA/REJ/<Application ID>/<yyyymmdd>, the Date of Order (same day),
          the Authority 'Registering Authority, <district> District' and the reason in the order
    And   the reason matches the Admin Remarks on My Application, nothing can be edited and the note
          'These details are taken from the official order and cannot be changed.' is shown

    AIO: KAN-TC-305 | data: state store agency 'rejected'
    """
    fa, _agency = first_appeal_page

    with allure.step("Verify the order number, date, authority and reason"):
        reg = fa.get_registration_no()
        m = re.fullmatch(rf"RA/REJ/{reg}/(\d{{8}})", fa.get_order_number())
        assert m, fa.get_order_number()
        order_date = datetime.strptime(fa.read_only_value("(b) Date of Order"), DATE_FMT).date()
        assert order_date.strftime("%Y%m%d") == m.group(1)
        _district(fa)
        reason = fa.read_only_value("Reason given in the order")
        assert reason

    with allure.step("Verify the section is locked"):
        expect(fa.card("5").locator("input, textarea, select, [contenteditable=true]")).to_have_count(0)
        expect(fa.order_locked_note).to_have_text(F.ORDER_LOCKED)

    with allure.step("Compare the reason with My Application's Admin Remarks"):
        my_app = MyApplicationPage(fa.page)
        my_app.open()
        assert _squash(my_app.admin_remarks_text()) == _squash(reason)


@aio_case("KAN-TC-316")
@allure.story(STORY)
@allure.title("TC-316: The limitation (section 9) is worked out by the portal")
def test_tc316_limitation_auto_calculated(first_appeal_page):
    """
    Given a refused agency on FORM-III
    Then  section 9 shows the date of communication (= the Date of Order) and "✓ Yes — day N of 60",
          N being the days since then, with nothing to enter

    AIO: KAN-TC-316 | data: state store agency 'rejected'
    """
    fa, _agency = first_appeal_page
    communicated = fa.read_only_value("(a) Date of communication of the order")

    with allure.step("Verify the date of communication and the day count"):
        assert communicated == fa.read_only_value("(b) Date of Order")
        days = (_today() - datetime.strptime(communicated, DATE_FMT).date()).days
        assert fa.read_only_value("(b) Filed within 60 days?") == F.WITHIN_LIMIT.format(days=days)

    with allure.step("Verify nothing can be entered"):
        expect(fa.card("9").locator("input, textarea, select")).to_have_count(0)


# ---------------------------------------------------------------------------
# Grounds, facts and relief
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-308")
@allure.story(STORY)
@allure.title("TC-308: Submitting without any ground of appeal is refused")
def test_tc308_no_ground_refused(first_appeal_page, first_appeal_no_ground_data):
    """
    Given a refused agency on FORM-III with everything filled except the grounds
    When  it clicks Submit
    Then  "Please tick at least one ground of appeal." is shown, no confirmation is asked and nothing is filed

    AIO: KAN-TC-308 | data: no_ground
    """
    fa, _agency = first_appeal_page
    data = first_appeal_no_ground_data

    with allure.step("Verify the six grounds"):
        expect(fa.card("6")).to_contain_text("Tick one or more grounds (click anywhere on the box):")
        expect(fa.page.locator("input[name='grounds[]']")).to_have_count(len(fa.GROUNDS))

    with allure.step("Submit without a ground"):
        fa.fill_appeal(data)
        assert fa.submit_and_handle_alert(action="dismiss") == data.expected_error

    with allure.step("Verify the form is kept and nothing was filed"):
        expect(fa.brief_facts_textarea).to_have_value(data.brief_facts)
        _expect_not_filed(fa)


@aio_case("KAN-TC-309")
@allure.story(STORY)
@allure.title("TC-309: Several grounds can be ticked together by clicking anywhere on their box")
def test_tc309_grounds_tick_together(first_appeal_page):
    """
    Given a refused agency on FORM-III
    When  it clicks the text of three grounds, then the first one again
    Then  all three are ticked together, and the second click unticks only the first

    AIO: KAN-TC-309 | data: error_of_law, procedural_irregularity, non_consideration
    """
    fa, _agency = first_appeal_page
    chosen = ["error_of_law", "procedural_irregularity", "non_consideration"]

    with allure.step("Click three grounds by their text"):
        for value in chosen:
            fa.click_ground_box(value)
        for value in chosen:
            expect(fa.ground_checkbox(value)).to_be_checked()

    with allure.step("Click 'Error of law' again"):
        fa.click_ground_box("error_of_law")
        expect(fa.ground_checkbox("error_of_law")).not_to_be_checked()
        expect(fa.ground_checkbox("procedural_irregularity")).to_be_checked()
        expect(fa.ground_checkbox("non_consideration")).to_be_checked()


@aio_case("KAN-TC-310")
@allure.story(STORY)
@allure.title("TC-310: Ticking 'Other' shows a required 'Specify other ground' field")
def test_tc310_other_ground_required(first_appeal_page, other_ground_blank_data):
    """
    Given a refused agency on FORM-III
    When  it ticks "Other — specify below"
    Then  "Specify other ground *" appears, keeps at most 300 characters and hides when unticked
    And   submitting with it blank is refused (known defect "I & II Appeal" #65: the confirmation is asked)

    AIO: KAN-TC-310 | data: other_ground_blank
    """
    fa, _agency = first_appeal_page

    with allure.step("Tick 'Other' and type 301 characters"):
        fa.type_other_ground(F.other_ground_too_long())
        expect(fa.other_ground_box).to_be_visible()
        expect(fa.other_ground_box).to_contain_text("Specify other ground *")
        assert len(fa.grounds_other_input.input_value()) == F.OTHER_MAX

    with allure.step("Untick 'Other'"):
        fa.ground_checkbox("other").uncheck()
        expect(fa.other_ground_box).to_be_hidden()

    with allure.step("Submit with 'Other' ticked and nothing specified"):
        fa.fill_appeal(other_ground_blank_data)
        prompt = fa.submit_and_handle_alert(action="dismiss")
        assert prompt == "" and "grounds_other" in fa.invalid_fields(), (
            f"A blank 'Specify other ground' was not stopped — the page asked {prompt!r} (defect #65)")


@aio_case("KAN-TC-311")
@allure.story(STORY)
@allure.title("TC-311: Submitting with Brief Facts blank is refused")
def test_tc311_brief_facts_blank(first_appeal_page):
    """
    Given a refused agency on FORM-III with everything filled except Brief Facts
    When  it clicks Submit
    Then  the browser stops at Brief Facts; nothing is asked or filed

    AIO: KAN-TC-311 | data: brief_facts_0_chars
    """
    fa, _agency = first_appeal_page
    expect(fa.brief_facts_textarea).to_have_attribute("placeholder", "Concise narration of the relevant facts…")
    fa.fill_appeal(F.brief_facts_of_length(file_manager.VALID_CERTIFICATE, 0))
    _expect_refused_by_browser(fa, "brief_facts")


@aio_case("KAN-TC-312")
@allure.story(STORY)
@allure.title("TC-312: Brief Facts needs at least 20 characters")
def test_tc312_brief_facts_minimum(first_appeal_page):
    """
    Given a refused agency on FORM-III with everything else valid
    When  Brief Facts has 19 characters, then 20
    Then  19 is stopped by the browser; 20 passes and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-312 | data: brief_facts_19_chars, brief_facts_20_chars
    """
    fa, _agency = first_appeal_page

    with allure.step("19 characters"):
        fa.fill_appeal(F.brief_facts_of_length(file_manager.VALID_CERTIFICATE, F.FACTS_MIN - 1))
        _expect_refused_by_browser(fa, "brief_facts")

    with allure.step("20 characters"):
        fa.fill_brief_facts(F.brief_facts_of_length(file_manager.VALID_CERTIFICATE, F.FACTS_MIN).brief_facts)
        _expect_confirmation(fa)


@aio_case("KAN-TC-313")
@allure.story(STORY)
@allure.title("TC-313: Submitting without a relief type or relief text is refused")
def test_tc313_relief_required(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III with everything else valid
    When  it submits with no relief type, then with a relief type but no relief text
    Then  the browser stops at the missing one each time; nothing is asked or filed

    AIO: KAN-TC-313 | data: valid_order_only without relief type / text
    """
    fa, _agency = first_appeal_page
    data = first_appeal_valid_data
    relief_type, data.relief_type = data.relief_type, ""

    with allure.step("Verify the relief options"):
        for value in fa.RELIEFS:
            expect(fa.relief_radio(value)).to_have_count(1)
        expect(fa.relief_sought_textarea).to_have_attribute("placeholder", "State precisely the relief you are seeking…")

    with allure.step("No relief type"):
        fa.fill_appeal(data)
        _expect_refused_by_browser(fa, "relief_type")

    with allure.step("A relief type but no relief text"):
        fa.select_relief_type(relief_type)
        fa.fill_relief_sought("")
        _expect_refused_by_browser(fa, "relief_sought")


@aio_case("KAN-TC-314")
@allure.story(STORY)
@allure.title("TC-314: Only one relief type can be chosen at a time")
def test_tc314_relief_types_exclusive(first_appeal_page):
    """
    Given a refused agency on FORM-III
    When  it chooses each relief type in turn
    Then  only the last one chosen is selected

    AIO: KAN-TC-314 | data: the three relief types
    """
    fa, _agency = first_appeal_page
    for value in fa.RELIEFS:
        with allure.step(f"Choose '{value}'"):
            fa.select_relief_type(value)
            for other in fa.RELIEFS:
                if other == value:
                    expect(fa.relief_radio(other)).to_be_checked()
                else:
                    expect(fa.relief_radio(other)).not_to_be_checked()


@aio_case("KAN-TC-315")
@allure.story(STORY)
@allure.title("TC-315: Relief sought text needs at least 10 characters")
def test_tc315_relief_minimum(first_appeal_page):
    """
    Given a refused agency on FORM-III with everything else valid
    When  the relief text has 9 characters, then 10
    Then  9 is stopped by the browser; 10 passes and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-315 | data: relief_9_chars, relief_10_chars
    """
    fa, _agency = first_appeal_page

    with allure.step("9 characters"):
        fa.fill_appeal(F.relief_of_length(file_manager.VALID_CERTIFICATE, F.RELIEF_MIN - 1))
        _expect_refused_by_browser(fa, "relief_sought")

    with allure.step("10 characters"):
        fa.fill_relief_sought(F.relief_of_length(file_manager.VALID_CERTIFICATE, F.RELIEF_MIN).relief_sought)
        _expect_confirmation(fa)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-319")
@allure.story(STORY)
@allure.title("TC-319: Submitting without the Registering Authority's order (d) is refused")
def test_tc319_order_document_required(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III
    Then  section 10 lists (d) Order of the Registering Authority first, marked REQUIRED, and the other four
          as optional, each "PDF only · max 2 MB"
    When  it fills everything and attaches (a) but not (d), and clicks Submit
    Then  the browser stops at (d); nothing is asked or filed

    AIO: KAN-TC-319 | data: valid_order_only with the order attached as (a) instead
    """
    fa, _agency = first_appeal_page
    data = first_appeal_valid_data
    data.documents["original"] = data.documents.pop("order")

    with allure.step("Verify the document slots"):
        boxes = fa.card("10").locator(".ap-up")
        expect(boxes).to_have_count(5)
        expect(boxes.first).to_contain_text("(d) Order of the Registering Authority (self-attested)")
        expect(fa.document_box("order")).to_contain_text("REQUIRED")
        for slot in ("original", "ack", "fees", "other"):
            expect(fa.document_box(slot)).not_to_contain_text("REQUIRED")
            expect(fa.document_box(slot)).to_contain_text("PDF only · max 2 MB")

    with allure.step("Submit without (d)"):
        fa.fill_appeal(data)
        _expect_refused_by_browser(fa, "doc_order")


@aio_case("KAN-TC-320")
@allure.story(STORY)
@allure.title("TC-320: Each document slot takes a PDF of up to 2 MB")
def test_tc320_pdf_accepted(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III
    Then  every document slot offers PDF files only
    When  it attaches a ~360 KB PDF as (d) and completes the form
    Then  the file is taken, no document message appears and the confirmation is asked (answered Cancel)

    AIO: KAN-TC-320 | data: certificate.pdf (~360 KB)
    """
    fa, _agency = first_appeal_page

    with allure.step("Verify every slot offers PDF only"):
        for slot in fa.DOC_SLOTS:
            expect(fa.document_input(slot)).to_have_attribute("accept", ".pdf,application/pdf")

    with allure.step("Attach a PDF as (d) and complete the form"):
        fa.fill_appeal(first_appeal_valid_data)
        assert fa.files_chosen("order") == 1
        _expect_confirmation(fa)


@aio_case("KAN-TC-323")
@allure.story(STORY)
@allure.title("TC-323: A document over 2 MB is refused in any slot")
def test_tc323_oversized_document(first_appeal_page, oversized_order_data, first_appeal_oversized_data):
    """
    Given a refused agency on FORM-III
    When  it submits with a 3 MB PDF as (d), then with a valid (d) and the 3 MB PDF as (e)
    Then  "Each document must be a PDF of 2 MB or less." is shown each time; nothing is asked or filed

    AIO: KAN-TC-323 | data: oversized_order, oversized_document
    """
    fa, _agency = first_appeal_page

    with allure.step("3 MB PDF as the required order"):
        fa.fill_appeal(oversized_order_data)
        assert fa.submit_and_handle_alert(action="dismiss") == oversized_order_data.expected_error

    with allure.step("Valid order, 3 MB PDF as 'Any other document'"):
        fa.upload_documents(first_appeal_oversized_data.documents)
        assert fa.submit_and_handle_alert(action="dismiss") == first_appeal_oversized_data.expected_error

    with allure.step("Verify nothing was filed"):
        _expect_not_filed(fa)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-324")
@allure.story(STORY)
@allure.title("TC-324: Submitting without ticking the declaration is refused")
def test_tc324_declaration_required(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III with everything filled but the declaration unticked
    When  it clicks Submit
    Then  the browser stops at the declaration; once ticked, the confirmation is asked (answered Cancel)

    AIO: KAN-TC-324 | data: valid_order_only, declare=False
    """
    fa, _agency = first_appeal_page
    data = first_appeal_valid_data
    data.declare = False

    with allure.step("Verify the declaration text"):
        expect(fa.declaration_text).to_have_text(F.DECLARATION)

    with allure.step("Submit without the declaration"):
        fa.fill_appeal(data)
        _expect_refused_by_browser(fa, "declare")

    with allure.step("Tick it and submit"):
        fa.accept_declaration()
        _expect_confirmation(fa)


@aio_case("KAN-TC-325")
@allure.story(STORY)
@allure.title("TC-325: Authorised signatory, Designation and Place are pre-filled and required")
def test_tc325_verification_fields_required(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III
    Then  Authorised signatory, Designation and Place are already filled
    When  each is cleared in turn (everything else valid) and Submit is clicked
    Then  the browser stops at that field each time; nothing is asked or filed

    AIO: KAN-TC-325 | data: valid_order_only
    """
    fa, _agency = first_appeal_page
    fields = {"signatory_name": fa.signatory_name_input, "signatory_designation": fa.signatory_designation_input,
              "place": fa.place_input}

    with allure.step("Verify the three fields are pre-filled"):
        prefilled = {name: box.input_value() for name, box in fields.items()}
        assert all(v.strip() for v in prefilled.values()), prefilled

    fa.fill_appeal(first_appeal_valid_data)
    for name, box in fields.items():
        with allure.step(f"Clear '{name}' and submit"):
            box.fill("")
            _expect_refused_by_browser(fa, name)
            box.fill(prefilled[name])


@aio_case("KAN-TC-326")
@allure.story(STORY)
@allure.title("TC-326: The verification date shows today and cannot be changed")
def test_tc326_verification_date_today(first_appeal_page):
    """
    Given a refused agency on FORM-III
    Then  the Verification Date shows today's date (DD Mon YYYY) as text, with nothing to change it

    AIO: KAN-TC-326 | data: today (IST)
    """
    fa, _agency = first_appeal_page
    expect(fa.verification_date).to_have_text(_today().strftime(DATE_FMT))
    expect(fa.card("✓").locator("input[type=date], input[name*=date]")).to_have_count(0)


@aio_case("KAN-TC-742")
@allure.story(STORY)
@allure.title("TC-742: Cancelling the submit confirmation files nothing")
def test_tc742_cancel_confirmation(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency on FORM-III with a complete appeal
    When  it clicks Submit and answers Cancel to "Submit your First Appeal?"
    Then  the form stays with every entry and the Submit button
    And   after a reload the appeal is still not filed (2 of 2 remaining, First Appeal "— Not filed")

    AIO: KAN-TC-742 | data: valid_order_only
    """
    fa, _agency = first_appeal_page
    data = first_appeal_valid_data

    with allure.step("Fill the appeal and cancel the confirmation"):
        fa.fill_appeal(data)
        _expect_confirmation(fa)

    with allure.step("Verify the form is unchanged"):
        expect(fa.brief_facts_textarea).to_have_value(data.brief_facts)
        expect(fa.relief_sought_textarea).to_have_value(data.relief_sought)
        expect(fa.submit_button).to_have_text(F.SUBMIT_LABEL)
        expect(fa.submit_button).to_be_enabled()

    with allure.step("Reload: nothing was filed"):
        _expect_not_filed(fa)


# ---------------------------------------------------------------------------
# Who can file, and after filing
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-741")
@allure.story(STORY)
@allure.title("TC-741: FORM-III shows a message, not the form, to an agency whose application is not Rejected")
def test_tc741_not_rejected_sees_message(page, agency_login):
    """
    Given agencies whose applications are Submitted and Approved
    When  each opens FORM-III and the Second Appeal page by URL
    Then  no form is shown, only "An appeal can be filed only when your application has been rejected by the
          Registering Authority. Your application status is <status>."

    AIO: KAN-TC-741 | data: state store agencies 'desktop_scrutiny' (Submitted) and 'approved'
    """
    fa = FirstAppealPage(page)
    for status, shown in (("desktop_scrutiny", "Submitted"), ("approved", "Approved")):
        with allure.step(f"As the {shown} agency"):
            agency_login(status)
            fa.open()
            expect(fa.page.locator(MULTIPART_FORM)).to_have_count(0)
            expect(fa.blocking_note).to_have_text(F.NOT_REJECTED.format(status=shown))
            expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=2))
            expect(fa.journey_status("Application")).to_have_text(shown)
            fa.open_second_appeal()
            expect(fa.page.locator(MULTIPART_FORM)).to_have_count(0)
            expect(fa.blocking_note).to_have_text(F.NOT_REJECTED.format(status=shown))


@aio_case("KAN-TC-328")
@allure.story(STORY)
@allure.title("TC-328: A filed First Appeal can be followed on FORM-III, Home and My Application")
def test_tc328_track_filed_appeal(appealed_agency_page):
    """
    Given an agency whose First Appeal is pending
    Then  FORM-III shows only the card "#N · Your First Appeal — Pending decision", decision expected 60 days
          after filing with the days left
    And   Home shows "View First Appeal", "1 of 2 appeals remaining", "#N" with "Pending — decision by <date>"
          and "Your appeal is with the authority. You will be informed here and by e-mail."
    And   My Application no longer invites an appeal (known defect "I & II Appeal" #66)

    AIO: KAN-TC-328 | data: state store agency 'first_appeal'
    """
    fa, _agency = appealed_agency_page
    if "Pending decision" not in fa.filed_appeal_title.text_content():
        pytest.skip("The filed appeal has been decided — TC-744 covers a decided appeal.")
    n = _appeal_number(fa)

    with allure.step("Verify the appeal card on FORM-III"):
        expect(fa.appeal_form).to_have_count(0)
        expect(fa.filed_appeal_title).to_have_text(re.compile(r"Your First Appeal — Pending decision"))
        filed = datetime.strptime(fa.filed_appeal_value("Filed on"), DATE_FMT).date()
        due = filed + timedelta(days=F.DECISION_DAYS)
        left = (due - _today()).days
        assert _squash(fa.filed_appeal_value("Decision expected by")) == f"{due.strftime(DATE_FMT)} ({left} day(s) left)"

    with allure.step("Verify Home"):
        home = AgencyHomePage(fa.page)
        home.open()
        expect(home.first_appeal_links).to_have_text(["View First Appeal"])
        expect(home.appeals_remaining).to_have_text(F.HOME_REMAINING.format(n=1))
        expect(home.appeal_level_row("First Appeal")).to_contain_text(f"#{n}")
        expect(home.appeal_level_badge("First Appeal")).to_have_text(F.HOME_PENDING_BADGE.format(date=due.strftime(DATE_FMT)))
        expect(home.appeals_hint).to_have_text(F.HOME_PENDING_HINT)

    with allure.step("Verify My Application shows the appeal is pending"):
        my_app = MyApplicationPage(fa.page)
        my_app.open()
        expect(my_app.status_banner).not_to_contain_text(F.MY_APP_INVITE)
        expect(my_app.file_appeal_links.filter(has_text="File Appeal")).to_have_count(0)


@aio_case("KAN-TC-329")
@allure.story(STORY)
@allure.title("TC-329: The Second Appeal page explains it needs a decided and rejected First Appeal")
def test_tc329_second_appeal_needs_rejected_first(first_appeal_page, appealed_agency_page):
    """
    Given a refused agency without an appeal and an agency with a pending First Appeal
    When  each opens the Second Appeal page
    Then  neither gets a form: the first is told to file its First Appeal first, the second that First Appeal
          #N is still pending

    AIO: KAN-TC-329 | data: state store agencies 'rejected' and 'first_appeal'
    """
    fa, _agency = first_appeal_page
    with allure.step("Refused agency without an appeal"):
        fa.open_second_appeal()
        expect(fa.page.locator(MULTIPART_FORM)).to_have_count(0)
        expect(fa.blocking_note).to_have_text(F.SECOND_BEFORE_FIRST)

    appealed, _ = appealed_agency_page
    if "Pending decision" not in appealed.filed_appeal_title.text_content():
        pytest.skip("The filed appeal has been decided — the pending message cannot be checked.")
    n = _appeal_number(appealed)
    with allure.step("Agency with a pending First Appeal"):
        appealed.open_second_appeal()
        expect(appealed.page.locator(MULTIPART_FORM)).to_have_count(0)
        expect(appealed.blocking_note).to_have_text(F.SECOND_WHILE_PENDING.format(n=n))


@aio_case("KAN-TC-331")
@allure.story(STORY)
@allure.title("TC-331: A First Appeal cannot be filed twice")
def test_tc331_cannot_file_twice(appealed_agency_page, logged_in_admin_appeals_page):
    """
    Given an agency that has filed its First Appeal
    When  it opens FORM-III and reloads it
    Then  only the appeal card is shown — no form, no Submit — with "Appeals remaining: 1 of 2"
    And   the officer's First Appeals list has the agency's Application ID in one row only

    AIO: KAN-TC-331 | data: state store agency 'first_appeal'
    """
    fa, _agency = appealed_agency_page
    for attempt in ("Open", "Reload"):
        with allure.step(f"{attempt} FORM-III"):
            fa.open()
            expect(fa.appeal_form).to_have_count(0)
            expect(fa.submit_button).to_have_count(0)
            expect(fa.filed_appeal_card).to_have_count(1)
            expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))

    with allure.step("Verify the officer's list has the agency once"):
        reg = re.search(r"RA/REJ/(\d{13})/", fa.filed_appeal_value("Order appealed against")).group(1)
        ap = logged_in_admin_appeals_page
        ap.open_view("first")
        expect(ap.rows_for_application(reg)).to_have_count(1)


@aio_case("KAN-TC-743")
@allure.story(STORY)
@allure.title("TC-743: The agency is e-mailed a confirmation of its First Appeal")
def test_tc743_confirmation_email(appealed_agency_page):
    """
    Given an agency that has filed First Appeal #N (registered e-mail is a testmail inbox)
    Then  its inbox has an e-mail about First Appeal #N (known defect "I & II Appeal" #64: none arrives)

    AIO: KAN-TC-743 | data: state store agency 'first_appeal'
    """
    fa, agency = appealed_agency_page
    n = _appeal_number(fa)
    if not (agency.email or "").endswith("@inbox.testmail.app"):
        pytest.skip(f"The agency's e-mail is not a testmail inbox: {agency.email!r}")
    filed = datetime.strptime(fa.filed_appeal_value("Filed on"), DATE_FMT).replace(tzinfo=IST)

    with allure.step(f"Read the inbox of {agency.email}"):
        emails = get_emails_to(agency.email, since_ms=int(filed.timestamp() * 1000), wait_s=30)
        about = [e for e in emails if "appeal" in f"{e.get('subject')} {e.get('text')}".lower()]
        assert about, (f"No e-mail about the First Appeal reached {agency.email} "
                       f"({len(emails)} e-mail(s) since filing) — defect #64")
        assert any(f"#{n}" in f"{e.get('subject')} {e.get('text')}" or str(n) in (e.get("subject") or "")
                   for e in about), [e.get("subject") for e in about]


@aio_case("KAN-TC-744")
@allure.story(STORY)
@allure.title("TC-744: The agency sees the decision on its First Appeal")
def test_tc744_decision_shown(decided_appeal_agency_page):
    """
    Given an agency whose First Appeal has been decided by the Divisional Appellate Authority
    Then  FORM-III and Home no longer show it as pending, and the agency has an e-mail about the order
    And   if the appeal was dismissed, the Second Appeal page offers its form

    Known defect "I & II Appeal" #68: no e-mail about the order arrives (on dev a dismissed appeal shows
    'Your First Appeal — Rejected' and the Second Appeal form opens; the e-mail step fails).

    AIO: KAN-TC-744 (Under Review) | data: a decided first appeal (python -m utils.seed_appeals)
    """
    fa, agency = decided_appeal_agency_page
    title = fa.filed_appeal_title.text_content()

    with allure.step("Verify FORM-III shows the decision"):
        expect(fa.journey_status("First Appeal · Division")).not_to_have_text(re.compile("Pending"))

    with allure.step("Verify Home shows the decision"):
        home = AgencyHomePage(fa.page)
        home.open()
        expect(home.appeal_level_badge("First Appeal")).not_to_have_text(re.compile(r"^Pending"))

    if re.search(r"dismiss|reject", title, re.IGNORECASE):
        with allure.step("Dismissed: the Second Appeal form is offered"):
            fa.open_second_appeal()
            expect(fa.page.locator(MULTIPART_FORM)).to_have_count(1)

    with allure.step("Verify the e-mail"):
        emails = get_emails_to(agency.email or "")
        assert any("order" in f"{e.get('subject')} {e.get('text')}".lower() for e in emails), (
            f"No e-mail about the order on '{_squash(title)}' reached {agency.email} "
            f"({len(emails)} e-mail(s) in the inbox)")


# ---------------------------------------------------------------------------
# Filing (opt-in: RUN_APPEAL_FILING_TESTS=true — uses up refused agencies)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-327")
@allure.story(STORY)
@allure.title("TC-327: Filing a complete First Appeal shows its number and the appeal card")
def test_tc327_file_complete_appeal(appeal_filing_allowed, first_appeal_page, first_appeal_full_data):
    """
    Given a refused agency on FORM-III
    When  it files an appeal with two grounds, facts, relief, all five documents and the declaration
    Then  "Submit your First Appeal? …" is asked; after OK the page shows "Your First Appeal (FORM-III) #N has
          been submitted …" and the card "#N · Your First Appeal — Pending decision" with every detail
    And   "Appeals remaining: 1 of 2" and First Appeal · Division "Pending decision"

    AIO: KAN-TC-327 | data: valid_with_documents (uses up the agency)
    """
    fa, agency = first_appeal_page
    data = first_appeal_full_data
    district, order_no = _district(fa), fa.get_order_number()
    order_date = fa.read_only_value("(b) Date of Order")

    with allure.step("Fill and submit the appeal"):
        fa.fill_appeal(data)
        assert fa.submit() == F.CONFIRM
        TestStateStore().record_agency_status(username=agency.username, status="first_appeal",
                                              data={"appeal_status": "filed"})

    with allure.step("Verify the confirmation and the appeal card"):
        n = _appeal_number(fa)
        expect(fa.success_alert).to_have_text(F.SUBMITTED.format(n=n))
        expect(fa.appeal_form).to_have_count(0)
        expect(fa.filed_appeal_title).to_have_text(re.compile(r"Your First Appeal — Pending decision"))
        today = _today()
        due = today + timedelta(days=F.DECISION_DAYS)
        assert fa.filed_appeal_value("Filed on") == today.strftime(DATE_FMT)
        assert _squash(fa.filed_appeal_value("Sent to")) == (
            f"Deputy Commissioner, Skill Development, Employment & Entrepreneurship, {district} District")
        assert fa.filed_appeal_value("Order appealed against") == f"{order_no} dated {order_date}"
        assert fa.filed_appeal_value("Grounds") == "Error of law, Procedural irregularity"
        assert fa.filed_appeal_value("Relief sought") == f"{data.relief_type} — {data.relief_sought}"
        assert _squash(fa.filed_appeal_value("Decision expected by")) == (
            f"{due.strftime(DATE_FMT)} ({F.DECISION_DAYS} day(s) left)")

    with allure.step("Verify the note and the progress strip"):
        expect(fa.appeals_remaining).to_have_text(F.APPEALS_REMAINING.format(n=1))
        expect(fa.journey_status("First Appeal · Division")).to_have_text(re.compile("Pending decision"))


@aio_case("KAN-TC-321")
@allure.story(STORY)
@allure.title("TC-321: A First Appeal with only the required order document can be filed")
def test_tc321_file_with_order_only(appeal_filing_allowed, logged_in_admin_appeals_page, filed_first_appeal_order_only):
    """
    Given a refused agency files an appeal with only (d) Order of the Registering Authority attached
    Then  the appeal is filed and the officer's "Review & decide" lists only the Registering Authority order

    AIO: KAN-TC-321 | data: valid_order_only (uses up the agency)
    """
    seeded = filed_first_appeal_order_only
    ap = logged_in_admin_appeals_page
    ap.open_view("first")
    appeal = next((a for a in ap.appeals_data().values() if a["reg_id"] == seeded["reg_id"]), None)
    assert appeal, f"The appeal filed for {seeded['reg_id']} is not listed under First Appeals"
    assert [d["label"] for d in appeal["docs"]] == ["Registering Authority order"], appeal["docs"]


@aio_case("KAN-TC-322")
@allure.story(STORY)
@allure.title("TC-322: A document that is not a PDF is not accepted")
def test_tc322_non_pdf_refused(appeal_filing_allowed, first_appeal_page, docx_order_data):
    """
    Given a refused agency on FORM-III (the picker offers PDF only)
    When  a .docx is sent as (d) anyway and the appeal is submitted
    Then  the portal refuses it with a message and nothing is filed

    AIO: KAN-TC-322 (Under Review) | data: docx_order (files the appeal if the portal accepts it)
    """
    fa, agency = first_appeal_page
    fa.fill_appeal(docx_order_data)
    _submit_expecting_refusal(fa, agency, "a .docx as the order document")


@aio_case("KAN-TC-333")
@allure.story(STORY)
@allure.title("TC-333: An empty (0-byte) PDF is not accepted")
def test_tc333_empty_pdf_refused(appeal_filing_allowed, first_appeal_page, empty_order_data):
    """
    Given a refused agency on FORM-III
    When  an empty 0-byte PDF is attached as (d) and the appeal is submitted
    Then  the portal refuses it with a message and nothing is filed

    AIO: KAN-TC-333 (Under Review) | data: empty_order (files the appeal if the portal accepts it)
    """
    fa, agency = first_appeal_page
    fa.fill_appeal(empty_order_data)
    _submit_expecting_refusal(fa, agency, "an empty PDF as the order document")
