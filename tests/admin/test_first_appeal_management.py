"""
First Appeal Management — Officer Console + agency FORM-III
===========================================================
Covers KAN-TC-360 through KAN-TC-368, rewritten 04-Nov-2026 for the redesigned
pages: the officer's Appeals (/module/admin/appeals/index.php — views + the
"Review & decide" pop-up) and the agency's First Appeal FORM-III
(/module/agency/appeals/first.php).

Test data. An appeal can only be filed by an agency whose application was
refused, and each such agency can file one first appeal. Refused agencies are
prepared on the Officer Console and recorded as ``rejected`` in the state store;
fixtures that file (``pending_first_appeal`` when no appeal is pending) use one
up and record it as ``first_appeal``.

* Read-only tests — TC-360, 361, 362, 364, 367, 368 — reuse an appeal already
  awaiting decision (``pending_first_appeal`` files one only when none is
  pending); TC-368 opens FORM-III for a refused agency without filing.
* TC-363 passes an appellate order (irreversible, uses up the pending appeal):
  opt-in with RUN_APPEAL_DECISION_TESTS=true.
* TC-365 / TC-366 check the audit log and the agency's e-mail for an appeal
  that has already been decided (skip when none has).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.audit_log_page import AdminAuditLogPage
from pages.first_appeal_page import FirstAppealPage
from test_data.first_appeal_factory import AppealOutcomeData, AppealOutcomeFactory, FirstAppealFactory
from utils.aio import aio_case
from utils.email_otp import get_emails_to

STORY = "First Appeal Management"
O = AppealOutcomeFactory
IST = timezone(timedelta(hours=5, minutes=30))
DOC_LABELS = ["Registering Authority order", "Original application", "Acknowledgement", "Fee receipt", "Other document"]
GROUND_LABELS = {"error_of_law": "Error of law", "procedural_irregularity": "Procedural irregularity",
                 "jurisdictional_error": "Jurisdictional error", "non_consideration": "Non-consideration of material record",
                 "natural_justice": "Violation of principles of natural justice", "other": "Other (specified)"}


def _grounds_text(appeal: dict) -> str:
    g = appeal["grounds"]
    return ", ".join(GROUND_LABELS.get(k, k) for k in g["checkboxes"]) + (f" — {g['other']}" if g.get("other") else "")


def _audit_entries_for_appeal(page, appeal_id: int, max_pages: int = 40) -> list[str]:
    """Texts of the last 30 days' audit entries on table agency_appeals for this appeal ('ID #<id>'). Pages back
    (newest first) until the filing ('1st Appeal'), the appeal's oldest entry, is found — a busy day of seeding
    can push it several pages down."""
    audit = AdminAuditLogPage(page)
    found = []
    for n in range(1, max_pages + 1):
        audit.open(date_f="month", page=n)
        items = audit.log_entries
        if items.count() == 0:
            break
        found += [t for t in items.all_inner_texts()
                  if O.AUDIT_TABLE in t and re.search(rf"\bID #{appeal_id}\b", t)]
        if any(O.AUDIT_FILED in t for t in found):
            break
    return found


# ---------------------------------------------------------------------------
# TC-360  First Appeals list
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-360")
@allure.story(STORY)
@allure.title("TC-360: First Appeals — Division lists every first appeal with its agency, area, dates, hearing and status")
def test_tc360_first_appeals_listed_with_fields(logged_in_admin_appeals_page: AdminAppealsPage, pending_first_appeal: dict):
    """
    Given at least one first appeal awaits a decision
    When  I open Appeals › First Appeals — Division
    Then  the table has the columns #, Agency, District, Appeal, Filed, Decision due, Hearing, Status
    And   every row shows the appeal number, agency name and 13-digit Application ID, district and division,
          'First · Division', the filing date, the days left to decide, the hearing and the status
    And   the pending appeal's row matches what was filed, with 'Pending' and 'Review & decide'
    And   the tab count equals the number of rows

    AIO: KAN-TC-360 | data: pending_first_appeal
    """
    ap, appeal = logged_in_admin_appeals_page, pending_first_appeal

    with allure.step("Verify the table columns"):
        headers = ap.table_headers.evaluate_all("hs => hs.map(h => h.textContent.trim())")
        assert [h.lower() for h in headers] == [c.lower() for c in ap.APPEAL_COLUMNS], headers

    rows = ap.appeal_rows_data()
    allure.attach("\n".join(map(str, rows)), name="first appeal rows")
    with allure.step("Verify the tab count equals the rows listed"):
        assert ap.view_count("first") == len(rows), (ap.view_count("first"), len(rows))

    with allure.step("Verify every row's fields"):
        for r in rows:
            assert r["id"].isdigit(), r
            assert r["agency"] and re.fullmatch(r"\d{13}", r["application_id"]), r
            assert r["district"] and r["division"].endswith("Division"), r
            assert r["type"] == "First · Division", r
            assert re.fullmatch(r"\d{2} [A-Z][a-z]{2} \d{4}", r["filed"]), r
            assert r["status"] and r["hearing"], r
            assert re.fullmatch(r"\d+ days left|\d+ days overdue", r["due"]) or r["status"] != "Pending", r

    with allure.step(f"Verify the row of appeal #{appeal['id']}"):
        row = next(r for r in rows if r["id"] == str(appeal["id"]))
        filed = datetime.strptime(appeal["filed"][:10], "%Y-%m-%d").strftime("%d %b %Y")
        assert (row["agency"], row["application_id"], row["district"], row["filed"]) == \
               (appeal["agency"], appeal["reg_id"], appeal["district"], filed), row
        assert row["division"] == f"{appeal['division']} Division", row
        assert row["due"] == f"{appeal['days_left']} days left", row
        assert (row["status"], row["button"]) == ("Pending", "Review & decide"), row


# ---------------------------------------------------------------------------
# TC-361  The filed FORM-III, read-only
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-361")
@allure.story(STORY)
@allure.title("TC-361: Review & decide shows every FORM-III field as filed, read-only")
def test_tc361_form_iii_fields_read_only(logged_in_admin_appeals_page: AdminAppealsPage, pending_first_appeal: dict):
    """
    Given a first appeal awaits a decision
    When  I click 'Review & decide' on it
    Then  the pop-up is titled 'First Appeal (FORM-III) #N — <agency>' with the division and filing date
    And   it shows the Appellant, Order appealed against, Grounds / facts / relief, Limitation, Documents and
          Hearing sections with exactly the values the agency filed
    And   none of the filed values can be edited (no inputs inside the FORM-III sections)

    AIO: KAN-TC-361 | data: pending_first_appeal
    """
    ap, a = logged_in_admin_appeals_page, pending_first_appeal
    g, lim = a["grounds"], a["limitation"]
    ap.open_appeal(a["id"])

    with allure.step("Verify the title, subtitle and chips"):
        expect(ap.modal_title).to_have_text(f"First Appeal (FORM-III) #{a['id']} — {a['agency']}")
        expect(ap.modal_subtitle).to_have_text(
            f"Divisional Appellate Authority, {a['division']} Division · filed {a['filed'][:10]}")
        expect(ap.modal_chips).to_have_text(["First · Division", a["reg_id"], f"{a['days_left']} days left to decide"])

    with allure.step("Verify every section is shown"):
        for title in ap.SECTIONS:
            expect(ap.modal_section(title)).to_have_count(1)

    expected = {
        "Agency": a["agency"], "Registration ID": a["reg_id"], "District": a["district"],
        "Contact": f"{a['email']} · {a['mobile']}", "Address": a["address"],
        "Order No.": a["order_no"], "Order date": a["order_date"], "Passed by": g["order_authority"],
        "Grounds": _grounds_text(a), "Brief facts": g["brief_facts"],
        "Relief sought": f"{g['relief_type']} — {g['relief_sought']}",
        "Order communicated on": lim["comm_date"], "Filed within time": "Yes" if lim["within_time"] == "yes" else None,
    }
    seeded = a.get("seeded")
    with allure.step("Verify every field shows the filed value"):
        shown = {label: ap.modal_value(label) for label in expected}
        allure.attach("\n".join(f"{k}: {v}" for k, v in shown.items()), name="FORM-III as shown")
        for label, value in expected.items():
            if value is not None:
                assert shown[label] == value, f"{label}: shown {shown[label]!r}, filed {value!r}"
        if seeded:
            assert (shown["Registration ID"], shown["Order No."]) == (seeded["reg_id"], seeded["order_number"])

    with allure.step("Verify the filed sections have no editable fields"):
        assert ap.editable_fields_in_body() == 0, "The filed FORM-III can be edited in the pop-up"


# ---------------------------------------------------------------------------
# TC-362  Documents as labelled links
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-362")
@allure.story(STORY)
@allure.title("TC-362: Each uploaded document is a labelled link that opens the PDF")
def test_tc362_documents_are_labelled_download_links(logged_in_admin_appeals_page: AdminAppealsPage,
                                                     pending_first_appeal: dict):
    """
    Given a first appeal was filed with all five documents
    When  I open it with 'Review & decide'
    Then  10 · Documents lists 'Registering Authority order', 'Original application', 'Acknowledgement',
          'Fee receipt' and 'Other document', each opening in a new tab
    And   every link serves its PDF

    AIO: KAN-TC-362 | data: pending_first_appeal (valid_with_documents)
    """
    ap, a = logged_in_admin_appeals_page, pending_first_appeal
    ap.open_appeal(a["id"])

    with allure.step("Verify the five labelled links"):
        expect(ap.document_links).to_have_text(DOC_LABELS)
        links = ap.document_links.evaluate_all("ls => ls.map(l => ({href: l.getAttribute('href'), target: l.target}))")
        for link in links:
            assert re.fullmatch(r"/serve_enclosure\.php\?t=[0-9a-f]{40}", link["href"]), link
            assert link["target"] == "_blank", link

    with allure.step("Verify each link serves a PDF"):
        base = ap.page.url.split("/module/")[0]
        for label, link in zip(DOC_LABELS, links):
            res = ap.page.request.get(base + link["href"])
            assert res.ok, f"{label}: HTTP {res.status}"
            assert res.body()[:5] == b"%PDF-", f"{label}: not a PDF ({res.headers.get('content-type')})"


# ---------------------------------------------------------------------------
# TC-363  Passing the appellate order (opt-in)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-363")
@allure.story(STORY)
@allure.title("TC-363: Passing an appellate order records the result, order number, officer and time")
def test_tc363_record_outcome_persists(appeal_decisions_allowed, logged_in_admin_appeals_page: AdminAppealsPage,
                                       pending_first_appeal: dict, dismissed_upheld_data: AppealOutcomeData):
    """
    Given a first appeal awaits a decision
    When  I choose 'Appeal Dismissed — Refusal Upheld', write the reasons and save, accepting
          'Pass this order? … <disposal> … <effect>'
    Then  the appeal leaves Awaiting decision and its status is no longer Pending
    And   the pop-up shows a Decision section with the result, an order number, the date and officer, and the
          reasons, and no decision form

    Irreversible — runs only with RUN_APPEAL_DECISION_TESTS=true.

    AIO: KAN-TC-363 | data: dismissed_upheld
    """
    ap, a, d = logged_in_admin_appeals_page, pending_first_appeal, dismissed_upheld_data
    label = ap.FIRST_DISPOSALS[d.disposal]
    ap.open_appeal(a["id"])

    with allure.step("Choose the disposal and verify its effect is shown"):
        ap.choose_disposal(d.disposal)
        expect(ap.disposal_impact).to_have_text(O.IMPACT[d.disposal])
        ap.fill_reasons(d.reasons)
        expect(ap.decision_remarks_count).to_have_text(f"{len(d.reasons.strip())} / 50 characters")

    with allure.step("Save and accept the confirmation"):
        before = datetime.now(IST).replace(tzinfo=None, second=0, microsecond=0)
        message = ap.save_order("accept")
        assert message == O.CONFIRM.format(label=label, desc=O.IMPACT[d.disposal]), message

    with allure.step("Verify the appeal left Awaiting decision"):
        ap.open_view("queue")
        expect(ap.appeal_row(a["id"])).to_have_count(0)

    with allure.step("Verify the status in First Appeals"):
        ap.open_view("first")
        row = next(r for r in ap.appeal_rows_data() if r["id"] == str(a["id"]))
        allure.attach(str(row), name="row after the order")
        assert row["status"] != "Pending", row

    with allure.step("Verify the Decision section and that the form is gone"):
        ap.open_appeal(a["id"])
        expect(ap.modal_section("Decision")).to_have_count(1)
        expect(ap.decide_box).to_be_hidden()
        decided = ap.modal_value("Decided")
        allure.attach("\n".join(f"{k}: {ap.modal_value(k)}" for k in ("Result", "Order No.", "Decided", "Remarks")),
                      name="decision as shown")
        assert ap.modal_value("Result"), "No result shown"
        assert ap.modal_value("Order No."), "No order number shown"
        when = datetime.strptime(decided[:16], "%Y-%m-%d %H:%M")
        assert before - timedelta(minutes=2) <= when <= before + timedelta(minutes=5), decided
        assert " by " in decided, f"The officer is not named: {decided!r}"
        assert ap.modal_value("Remarks") == d.reasons


# ---------------------------------------------------------------------------
# TC-364  The order needs a disposal and 50 characters of reasons
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-364")
@allure.story(STORY)
@allure.title("TC-364: Saving an appellate order without a disposal or 50 characters of reasons is refused")
def test_tc364_blank_remarks_blocked(logged_in_admin_appeals_page: AdminAppealsPage, pending_first_appeal: dict,
                                     invalid_outcome_cases: list[AppealOutcomeData]):
    """
    Given a first appeal awaits a decision and is open in 'Review & decide'
    When  I click 'Save appellate order' with no disposal, then with blank reasons, then with 49 characters
    Then  each time an error toast explains what is missing and no confirmation is asked
    And   the appeal still awaits a decision

    AIO: KAN-TC-364 | data: no_disposal, blank_reasons, short_reasons
    """
    ap, a = logged_in_admin_appeals_page, pending_first_appeal
    for case in invalid_outcome_cases:
        with allure.step(f"Save with {case.scenario_label}"):
            ap.open_view("first")
            ap.open_appeal(a["id"])
            if case.disposal:
                ap.choose_disposal(case.disposal)
            ap.fill_reasons(case.reasons)
            prompt = ap.save_order(action="dismiss")
            assert prompt == "", f"A confirmation was asked: {prompt!r}"
            expect(ap.toast).to_contain_text(case.expected_error)
            expect(ap.decide_box).to_be_visible()

    with allure.step("Verify the appeal still awaits a decision"):
        ap.open_view("queue")
        expect(ap.appeal_row(a["id"])).to_have_count(1)
        assert ap.appeals_data()[str(a["id"])]["decided"] is None


# ---------------------------------------------------------------------------
# TC-365  Audit log
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-365")
@allure.story(STORY)
@allure.title("TC-365: The audit log records the appellate order")
def test_tc365_audit_log_captures_outcome(logged_in_admin_appeals_page: AdminAppealsPage, decided_first_appeal: dict):
    """
    Given a first appeal has been decided
    When  I look at the audit log's entries for that appeal (table agency_appeals, ID #N)
    Then  besides the filing ('1st Appeal') there is an entry for the appellate order

    AIO: KAN-TC-365 | data: decided_first_appeal
    """
    ap, a = logged_in_admin_appeals_page, decided_first_appeal
    entries = _audit_entries_for_appeal(ap.page, a["id"])
    allure.attach("\n\n".join(entries), name=f"audit entries for appeal #{a['id']}")
    with allure.step("Verify the filing and the order are both logged"):
        assert any(O.AUDIT_FILED in e for e in entries), "The filing is not in the audit log"
        assert any(O.AUDIT_FILED not in e for e in entries), \
            f"No audit entry for the appellate order on appeal #{a['id']} ({a['status']}, {a['decided']})"


# ---------------------------------------------------------------------------
# TC-366  E-mail to the agency
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-366")
@allure.story(STORY)
@allure.title("TC-366: The agency is e-mailed the appellate order")
def test_tc366_email_on_outcome(decided_first_appeal: dict):
    """
    Given a first appeal has been decided
    When  I read the agency's inbox from the time of the decision
    Then  an e-mail about the appeal's order has arrived

    AIO: KAN-TC-366 | data: decided_first_appeal
    """
    a = decided_first_appeal
    decided = datetime.strptime(a["decided"][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    since = int((decided - timedelta(minutes=1)).timestamp() * 1000)
    emails = get_emails_to(a["email"], since_ms=since, wait_s=60)
    allure.attach("\n".join(f"{e['timestamp']} | {e['subject']}" for e in emails) or "(none)", name="inbox")
    if not emails and not a["email"].endswith("@inbox.testmail.app"):
        pytest.skip(f"The agency's address {a['email']} is not a testmail inbox.")
    with allure.step("Verify an e-mail about the appeal's order arrived"):
        assert any(re.search(r"appeal", (e.get("subject") or "") + (e.get("text") or ""), re.IGNORECASE) for e in emails), \
            f"No e-mail about appeal #{a['id']} reached {a['email']} since {decided:%d %b %Y %H:%M}"


# ---------------------------------------------------------------------------
# TC-367  One first appeal per agency
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-367")
@allure.story(STORY)
@allure.title("TC-367: An agency's first appeal is listed once and cannot be filed again")
def test_tc367_multiple_appeals_independent_rows(logged_in_admin_appeals_page: AdminAppealsPage, appealed_agency_page):
    """
    Given an agency has filed its first appeal
    When  it opens First Appeal (FORM-III) again
    Then  the form is not offered; its appeal '#N' is shown with its status, and 'Appeals remaining: 1 of 2'
    And   First Appeals — Division lists that agency's application exactly once, under the same appeal number
    And   no application has more than one first appeal

    AIO: KAN-TC-367 | data: appealed_agency_page
    """
    ap = logged_in_admin_appeals_page
    fa, agency = appealed_agency_page

    with allure.step("Verify FORM-III shows the appeal on file instead of the form"):
        expect(fa.appeal_form).to_have_count(0)
        expect(fa.filed_appeal_card).to_have_count(1)
        expect(fa.appeals_remaining).to_have_text(FirstAppealFactory.APPEALS_REMAINING.format(n=1))
        expect(fa.journey_status("First Appeal · Division")).not_to_have_text(re.compile("Not filed"))
        number = fa.filed_appeal_number.inner_text().strip().lstrip("#")

    with allure.step("Verify the officer's list has the agency once, under that number"):
        rows = ap.appeal_rows_data()
        mine = [r for r in rows if r["application_id"] == agency.application_id]
        assert [r["id"] for r in mine] == [number], mine
        ids = [r["application_id"] for r in rows]
        assert len(ids) == len(set(ids)), f"An application has more than one first appeal: {ids}"


# ---------------------------------------------------------------------------
# TC-368  The Order document is required
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-368")
@allure.story(STORY)
@allure.title("TC-368: A first appeal cannot be submitted without the Order of the Registering Authority")
def test_tc368_no_documents_placeholder(first_appeal_page, first_appeal_valid_data):
    """
    Given a refused agency is on First Appeal (FORM-III)
    When  it fills every section and attaches other documents but not '(d) Order of the Registering Authority'
          and clicks Submit
    Then  the browser stops the form at the Order document (marked REQUIRED); nothing is asked or filed
    And   the appeal is still not filed

    AIO: KAN-TC-368 | data: valid_order_only without the order document
    """
    fa, _agency = first_appeal_page
    data = first_appeal_valid_data
    path = data.documents.pop("order")
    data.documents["original"] = path

    with allure.step("Verify the Order document is marked REQUIRED"):
        expect(fa.document_box("order")).to_contain_text("REQUIRED")
        expect(fa.document_input("order")).to_have_attribute("required", "")

    with allure.step("Fill everything except the Order document and submit"):
        fa.fill_appeal(data)
        assert fa.invalid_fields() == ["doc_order"], fa.invalid_fields()
        prompt = fa.submit_and_handle_alert(action="dismiss")
        assert prompt == "", f"The page asked {prompt!r} instead of stopping at the missing document"

    with allure.step("Verify nothing was filed"):
        fa.open()
        expect(fa.appeal_form).to_have_count(1)
        expect(fa.journey_status("First Appeal · Division")).to_have_text(re.compile("Not filed"))
