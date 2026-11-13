"""KAN-37 — Licence Renewal (Form-II), agency side: Home's renewal prompts and module/agency/renewal.php.

Agencies are found by reading their renewal page (see fixtures/renewal_fixtures.py). Tests that need an expired
certificate skip unless one exists — with RUN_RENEWAL_TESTS=true a certificate is expired first. KAN-TC-405
submits a renewal and only runs with RUN_RENEWAL_TESTS=true (irreversible on dev).
"""

import re
from datetime import datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from config import AUTH_BASE
from pages.admin.renewals_page import AdminRenewalsPage
from pages.agency_home_page import AGENCY_HOME_URL, AgencyHomePage
from pages.certificate_page import CertificatePage
from pages.license_renewal_page import RENEWAL_URL, LicenseRenewalPage
from utils.aio import aio_case

STORY = "Licence Renewal"
IST = timezone(timedelta(hours=5, minutes=30))
DATE = r"\d{2} [A-Z][a-z]{2} \d{4}"
ON_HOME = re.compile(rf"^{re.escape(AGENCY_HOME_URL)}")
ON_RENEWAL = re.compile(rf"^{re.escape(RENEWAL_URL)}")
ON_LOGIN_NOT_LOGGED_IN = re.compile(rf"^{re.escape(AUTH_BASE)}/login\.php\?reason=not_logged_in")
REGISTRATION_NO = re.compile(r"^\d{13,14}$")


def _today():
    return datetime.now(IST).date()


def _parse(text: str):
    return datetime.strptime(re.search(DATE, text).group(), "%d %b %Y").date()


def _fmt(day) -> str:
    return day.strftime("%d %b %Y")


def _open_home(page) -> AgencyHomePage:
    home = AgencyHomePage(page)
    home.open()
    home.dismiss_testing_notice()
    return home


# ── Expired certificate ───────────────────────────────────────────────────────

@aio_case("KAN-TC-399")
@allure.story(STORY)
@allure.title("TC-399: Home shows the expired-certificate alert with Start renewal links")
def test_tc399_home_expired_alert(expired_renewal_agency):
    """
    Given my registration certificate has expired and no renewal is pending
    When  I open Home
    Then  a red alert says the certificate has expired with "Start renewal", the certificate card shows the
          Expired chip, "Expired N days ago", the certificate facts, View certificate and Start renewal, and both
          Start renewal links open the renewal page

    Notion: KAN-TC-399 | KAN-37 AC-1
    """
    page, _ = expired_renewal_agency

    with allure.step("Open Home"):
        home = _open_home(page)

    with allure.step("Verify the expired-certificate alert"):
        expect(home.next_step_heading).to_have_text(AgencyHomePage.EXPIRED_HEADING)
        expect(home.next_step_text).to_have_text(AgencyHomePage.EXPIRED_TEXT)
        expect(home.start_renewal_button).to_be_visible()

    with allure.step("Verify the Registration certificate (Form-II) card"):
        expect(home.certificate_chip).to_have_text("Expired")
        expect(home.certificate_subtitle).to_have_text(re.compile(r"^Expired \d+ days? ago$"))
        expect(home.certificate_field("Certificate no.")).to_have_text(REGISTRATION_NO)
        expect(home.certificate_field("Valid from")).to_have_text(re.compile(rf"^{DATE}$"))
        expect(home.certificate_field("Valid until")).to_have_text(re.compile(rf"^{DATE}$"))
        expect(home.certificate_buttons).to_have_text(
            [AgencyHomePage.VIEW_CERTIFICATE_LABEL, AgencyHomePage.START_RENEWAL_LABEL])

    with allure.step("Click Start renewal in the alert — the renewal page opens"):
        home.start_renewal()
        expect(page).to_have_url(ON_RENEWAL)

    with allure.step("Back on Home, click Start renewal on the certificate card — the renewal page opens"):
        _open_home(page)
        home.start_renewal_from_certificate()
        expect(page).to_have_url(ON_RENEWAL)


@aio_case("KAN-TC-400")
@allure.story(STORY)
@allure.title("TC-400: Renewal page header shows the registration number, validity and days overdue")
def test_tc400_header_overdue(renewal_page: LicenseRenewalPage, expired_renewal_agency):
    """
    Given my registration certificate has expired
    When  I open agency/renewal.php
    Then  the title and note are shown; Registration No. is my certificate number, Valid up to its expiry date
          and Days left "N days overdue"; "Back to my dashboard" opens Home

    Notion: KAN-TC-400 | KAN-37 AC-2
    """
    page, _ = expired_renewal_agency

    with allure.step("Verify the title and note"):
        expect(renewal_page.title).to_have_text(LicenseRenewalPage.TITLE)
        expect(renewal_page.note).to_have_text(LicenseRenewalPage.NOTE)

    with allure.step("Verify the three facts"):
        for label in LicenseRenewalPage.FACT_LABELS:
            expect(renewal_page.fact(label)).to_be_visible()
        registration_no = renewal_page.fact_value("Registration No.")
        valid_up_to = renewal_page.fact_value("Valid up to")
        assert REGISTRATION_NO.match(registration_no), f"Registration No. is '{registration_no}'"
        expiry = _parse(valid_up_to)
        overdue = (_today() - expiry).days
        assert renewal_page.fact_value("Days left") == f"{overdue} days overdue", \
            f"Days left '{renewal_page.fact_value('Days left')}' for an expiry of {valid_up_to}"

    with allure.step("Click Back to my dashboard — Home opens"):
        renewal_page.back_to_dashboard()
        expect(page).to_have_url(ON_HOME)

    with allure.step("Verify the facts match the certificate card on Home"):
        home = AgencyHomePage(page)
        home.dismiss_testing_notice()
        expect(home.certificate_field("Certificate no.")).to_have_text(registration_no)
        expect(home.certificate_field("Valid until")).to_have_text(valid_up_to)


@aio_case("KAN-TC-401")
@allure.story(STORY)
@allure.title("TC-401: The renewal application form is shown for an expired certificate")
def test_tc401_form_shown(renewal_page: LicenseRenewalPage, expired_renewal_agency):
    """
    Given my registration certificate has expired and no renewal is pending
    When  I open agency/renewal.php
    Then  the Renewal application form shows the two questions (nothing selected) with their boxes, the
          supporting document, the ₹2,000 fee, an unticked declaration and "Pay ₹2,000 & submit renewal"

    Notion: KAN-TC-401 | KAN-37 AC-3
    """
    with allure.step("Verify the form is shown"):
        expect(renewal_page.form_title).to_be_visible()
        expect(renewal_page.form).to_be_visible()

    with allure.step("Verify questions 1–3"):
        expect(renewal_page.question_labels).to_have_text(
            [LicenseRenewalPage.QUESTION_1, LicenseRenewalPage.QUESTION_2, LicenseRenewalPage.QUESTION_3])
        for answer in ("no", "yes"):
            expect(renewal_page.changes_radio(answer)).not_to_be_checked()
            expect(renewal_page.cases_radio(answer)).not_to_be_checked()
        expect(renewal_page.changes_details).to_have_attribute("placeholder", LicenseRenewalPage.CHANGES_PLACEHOLDER)
        expect(renewal_page.cases_details).to_have_attribute("placeholder", LicenseRenewalPage.CASES_PLACEHOLDER)
        expect(renewal_page.document_input).to_be_visible()
        expect(renewal_page.document_help).to_be_visible()

    with allure.step("Verify the fee, the declaration and the button"):
        expect(renewal_page.fee_box).to_contain_text(LicenseRenewalPage.FEE_LABEL)
        expect(renewal_page.fee_amount).to_have_text(LicenseRenewalPage.FEE)
        expect(renewal_page.declaration_label).to_have_text(LicenseRenewalPage.DECLARATION)
        expect(renewal_page.declaration_checkbox).not_to_be_checked()
        expect(renewal_page.submit_button).to_be_visible()


# ── Who sees no form ──────────────────────────────────────────────────────────

@aio_case("KAN-TC-402")
@allure.story(STORY)
@allure.title("TC-402: Renewal is not open while more than 90 days of validity remain")
def test_tc402_not_open_yet(renewal_page: LicenseRenewalPage, not_open_renewal_agency):
    """
    Given my certificate is valid for more than 90 more days
    When  I open agency/renewal.php
    Then  the header shows the days left and the page says when renewal opens (expiry − 90 days); no form

    Notion: KAN-TC-402 | KAN-37 AC-4
    """
    with allure.step("Verify the header facts"):
        expect(renewal_page.title).to_have_text(LicenseRenewalPage.TITLE)
        expect(renewal_page.fact("Registration No.")).to_be_visible()
        expiry = _parse(renewal_page.fact_value("Valid up to"))
        days_left = (expiry - _today()).days
        assert days_left > LicenseRenewalPage.WINDOW_DAYS, f"Certificate valid up to {expiry}: only {days_left} days left"
        assert renewal_page.fact_value("Days left") == f"{days_left} days", \
            f"Days left '{renewal_page.fact_value('Days left')}', expected '{days_left} days'"

    with allure.step("Verify when renewal opens, and that there is no form"):
        opens_on = _fmt(expiry - timedelta(days=LicenseRenewalPage.WINDOW_DAYS))
        expect(renewal_page.window_notice).to_have_text(LicenseRenewalPage.window_message(opens_on))
        expect(renewal_page.form).to_have_count(0)
        expect(renewal_page.submit_button).to_have_count(0)


@aio_case("KAN-TC-403")
@allure.story(STORY)
@allure.title("TC-403: Agencies without a registration certificate see no renewal form")
def test_tc403_no_certificate(renewal_page: LicenseRenewalPage, no_certificate_agencies, renewal_agency_login):
    """
    Given agency A is in Desktop scrutiny and agency B's application was refused
    When  each opens agency/renewal.php
    Then  the facts show "—", the page says no registration certificate was found and no form is shown

    Notion: KAN-TC-403 | KAN-37 AC-5
    """
    _, users = no_certificate_agencies
    for user, stage in zip(users, ("in Desktop scrutiny", "refused")):
        with allure.step(f"Log in as {user.username} ({stage}) and open the renewal page"):
            renewal_agency_login(user)
            renewal_page.open()

        with allure.step(f"Verify {user.username} sees no certificate and no form"):
            for label in LicenseRenewalPage.FACT_LABELS:
                assert renewal_page.fact_value(label) == LicenseRenewalPage.NO_VALUE, \
                    f"{label} is '{renewal_page.fact_value(label)}' for {user.username}"
            expect(renewal_page.no_certificate_notice).to_have_text(LicenseRenewalPage.NO_CERTIFICATE)
            expect(renewal_page.form).to_have_count(0)
            expect(renewal_page.submit_button).to_have_count(0)


@aio_case("KAN-TC-404")
@allure.story(STORY)
@allure.title("TC-404: Opening the renewal page while logged out redirects to the agency login")
def test_tc404_logged_out_redirect(page, renewal_page: LicenseRenewalPage):
    """
    Given no agency session in the browser
    When  I open module/agency/renewal.php
    Then  I am redirected to the agency login with reason=not_logged_in

    Notion: KAN-TC-404 | KAN-37 AC-6
    """
    with allure.step("Clear the session and open the renewal page"):
        page.context.clear_cookies()
        renewal_page.open()

    with allure.step("Verify the redirect to the agency login"):
        expect(page).to_have_url(ON_LOGIN_NOT_LOGGED_IN)


@aio_case("KAN-TC-832")
@allure.story(STORY)
@allure.title("TC-832: An agency that has not submitted Form-I is sent to login from the renewal page")
def test_tc832_no_form_i_redirect(page, renewal_page: LicenseRenewalPage, agency_without_form_i):
    """
    Given I registered but have not submitted Form-I, and I am logged in
    When  I open module/agency/renewal.php
    Then  I am redirected to the agency login with reason=not_logged_in

    Notion: KAN-TC-832 | KAN-37 EC-8
    """
    with allure.step("Open the renewal page"):
        renewal_page.open()

    with allure.step("Verify the redirect to the agency login"):
        expect(page).to_have_url(ON_LOGIN_NOT_LOGGED_IN)


# ── Server checks (nothing is submitted) ──────────────────────────────────────

def _submit_and_expect_errors(renewal_page: LicenseRenewalPage, data) -> None:
    with allure.step(f"Fill the form ({data.scenario_label}) and submit"):
        renewal_page.fill_form(data)
        renewal_page.submit()

    with allure.step(f"Verify the server lists: {data.expected_errors}"):
        expect(renewal_page.errors_box).to_contain_text(LicenseRenewalPage.ERRORS_HEADING)
        assert renewal_page.error_messages() == data.expected_errors, \
            f"{data.scenario_label}: listed {renewal_page.error_messages()}"
        expect(renewal_page.success_box).to_have_count(0)
        expect(renewal_page.form).to_be_visible()


@aio_case("KAN-TC-406")
@allure.story(STORY)
@allure.title("TC-406: Declaring changes requires a description and a supporting document")
def test_tc406_changes_need_details_and_document(renewal_page: LicenseRenewalPage, expired_renewal_agency,
                                                renewal_changes_without_details_data,
                                                renewal_changes_without_document_data):
    """
    Given my certificate has expired and I answer Yes to question 1
    When  I submit without a description and without a document, then with a description only
    Then  the server asks for the description (20+ characters) and the document, then for the document only;
          nothing is submitted

    Notion: KAN-TC-406 | KAN-37 AC-8 | Data: Changes = Yes, no description / with a description, no document
    """
    _submit_and_expect_errors(renewal_page, renewal_changes_without_details_data)
    _submit_and_expect_errors(renewal_page, renewal_changes_without_document_data)


@aio_case("KAN-TC-407")
@allure.story(STORY)
@allure.title("TC-407: Declaring pending cases requires details")
def test_tc407_cases_need_details(renewal_page: LicenseRenewalPage, expired_renewal_agency,
                                  renewal_cases_without_details_data):
    """
    Given my certificate has expired and I answer Yes to question 2
    When  I submit without the details
    Then  the server asks for the details of the cases (20+ characters); nothing is submitted

    Notion: KAN-TC-407 | KAN-37 AC-9 | Data: Cases = Yes, no details
    """
    _submit_and_expect_errors(renewal_page, renewal_cases_without_details_data)


@aio_case("KAN-TC-408")
@allure.story(STORY)
@allure.title("TC-408: A blank renewal form is rejected by the server")
def test_tc408_blank_form_rejected(renewal_page: LicenseRenewalPage, expired_renewal_agency,
                                   renewal_blank_data, renewal_not_declared_data):
    """
    Given my certificate has expired
    When  I submit the form without answering anything, then with No / No but no declaration
    Then  the server asks for both answers and the declaration, then for the declaration only; nothing is
          submitted

    Notion: KAN-TC-408 | KAN-37 EC-3 | Data: Nothing answered / No, No, unticked
    """
    _submit_and_expect_errors(renewal_page, renewal_blank_data)
    _submit_and_expect_errors(renewal_page, renewal_not_declared_data)


@aio_case("KAN-TC-409")
@allure.story(STORY)
@allure.title("TC-409: A supporting document outside PDF / JPG / PNG, 10 KB – 2 MB is rejected")
def test_tc409_invalid_documents(renewal_page: LicenseRenewalPage, expired_renewal_agency,
                                 renewal_invalid_documents_data):
    """
    Given my certificate has expired and I declare changes with a description
    When  I submit a document under 10 KB, one over 2 MB and one of another type
    Then  the server rejects each with its own message (and asks for the document); the file chooser offers
          only .pdf, .jpg, .jpeg and .png

    Notion: KAN-TC-409 | KAN-37 EC-4 | Data: 72 B PNG, 3 MB PDF, .docx
    """
    for data in renewal_invalid_documents_data:
        _submit_and_expect_errors(renewal_page, data)

    with allure.step("Verify the file chooser's filter"):
        expect(renewal_page.document_input).to_have_attribute("accept", LicenseRenewalPage.DOCUMENT_ACCEPT)


@aio_case("KAN-TC-410")
@allure.story(STORY)
@allure.title("TC-410: A rejected submission keeps the answers and the declaration")
def test_tc410_answers_kept(renewal_page: LicenseRenewalPage, expired_renewal_agency,
                            renewal_changes_without_document_data):
    """
    Given my certificate has expired
    When  I answer Yes with a description, No, tick the declaration and submit without a document
    Then  the errors are listed and the form still holds my answers and the declaration; no file is chosen

    Notion: KAN-TC-410 | KAN-37 AC-15 | Data: Changes = Yes with a description, no document
    """
    data = renewal_changes_without_document_data
    _submit_and_expect_errors(renewal_page, data)

    with allure.step("Verify the answers are kept"):
        expect(renewal_page.changes_radio("yes")).to_be_checked()
        expect(renewal_page.changes_details).to_have_value(data.changes_details)
        expect(renewal_page.cases_radio("no")).to_be_checked()
        expect(renewal_page.declaration_checkbox).to_be_checked()
        expect(renewal_page.document_input).to_have_value("")


# ── Submission (irreversible) ─────────────────────────────────────────────────

@aio_case("KAN-TC-405")
@allure.story(STORY)
@allure.title("TC-405: Submitting a renewal with no changes and no pending cases files it with the department")
def test_tc405_submit_renewal(page, renewal_chain_allowed, renewal_page: LicenseRenewalPage,
                              expired_renewal_agency, renewal_no_changes_data, admin_renewals_page: AdminRenewalsPage,
                              renewal_officer_login):
    """
    Given my certificate has expired and no renewal is pending
    When  I answer No / No, tick the declaration and click "Pay ₹2,000 & submit renewal"
    Then  the renewal is submitted (no payment page on dev) and shown as with the department, Home notifies me,
          and the officer sees it under Pending decision

    Notion: KAN-TC-405 | KAN-37 AC-7 | Data: No changes, no cases, declared — irreversible (RUN_RENEWAL_TESTS)
    """
    _, user = expired_renewal_agency

    with allure.step("Fill the form (No / No, declared) and submit"):
        renewal_page.fill_form(renewal_no_changes_data)
        renewal_page.submit()

    with allure.step("Verify the submission message and the latest application"):
        expect(renewal_page.success_box).to_have_text(re.compile(
            r"^Submitted\.\s*Renewal application #\d+ submitted\. You will be informed by e-mail\.$"))
        number = re.search(r"#(\d+)", renewal_page.success_box.inner_text()).group(1)
        expect(renewal_page.latest_application).to_contain_text(
            f"Latest renewal application #{number} — filed {_fmt(_today())}")
        expect(renewal_page.latest_application).to_contain_text(LicenseRenewalPage.WITH_DEPARTMENT)
        expect(renewal_page.form).to_have_count(0)

    with allure.step("Verify the notification on Home"):
        home = _open_home(page)
        expect(home.notification(AgencyHomePage.RENEWAL_RECEIVED_NOTIFICATION.format(n=number))).to_have_count(1)

    with allure.step("As an officer, verify the application is listed under Pending decision"):
        renewal_officer_login()
        admin_renewals_page.open(tab="submitted")
        expect(admin_renewals_page.row(user.application_id)).to_have_count(1)
        expect(admin_renewals_page.status_badge(user.application_id)).to_have_text(
            re.compile(rf"^{AdminRenewalsPage.PENDING}"))


@aio_case("KAN-TC-411")
@allure.story(STORY)
@allure.title("TC-411: No second renewal can be filed while one is with the department")
def test_tc411_pending_blocks_second(renewal_page: LicenseRenewalPage, pending_renewal_agency):
    """
    Given I have filed a renewal the officer has not decided yet
    When  I open agency/renewal.php
    Then  the page shows the latest application as with the department; no form and no Pay button

    Notion: KAN-TC-411 | KAN-37 EC-5
    """
    with allure.step("Verify the latest application is with the department"):
        expect(renewal_page.latest_application).to_contain_text(
            re.compile(rf"Latest renewal application #\d+ — filed {DATE}\s*·\s*{LicenseRenewalPage.WITH_DEPARTMENT}"))

    with allure.step("Verify there is no form"):
        expect(renewal_page.form).to_have_count(0)
        expect(renewal_page.submit_button).to_have_count(0)


# ── After approval ────────────────────────────────────────────────────────────

@aio_case("KAN-TC-415")
@allure.story(STORY)
@allure.title("TC-415: The agency sees the renewed certificate after approval")
def test_tc415_renewed_certificate(page, renewal_page: LicenseRenewalPage, renewed_renewal_agency):
    """
    Given my renewal was approved
    When  I open Home, the renewal page and the certificate
    Then  Home shows the agency as registered up to the new expiry with an Active certificate valid from the
          approval date, a renewal notification, the renewal page shows the renewal as Renewed with when the next
          one opens, and the certificate is valid up to the new expiry

    Notion: KAN-TC-415 | KAN-37 AC-14, EC-9 | Known defect: Licence Renewal Application #16 (Valid from keeps
    the original date) — this test fails on the last step
    """
    new_expiry = renewal_page.fact_value("Valid up to")

    with allure.step("Open Home and verify the registered banner"):
        home = _open_home(page)
        expect(home.next_step_heading).to_have_text(AgencyHomePage.REGISTERED_HEADING)
        expect(home.next_step_text).to_have_text(f"Certificate valid until {new_expiry}.")
        expect(home.view_certificate_button).to_be_visible()
        expect(home.start_renewal_button).to_have_count(0)

    with allure.step("Verify the certificate card"):
        expect(home.certificate_chip).to_have_text("Active")
        expect(home.certificate_subtitle).to_have_text("Valid")
        expect(home.certificate_field("Valid until")).to_have_text(new_expiry)
        expect(home.certificate_buttons).to_have_text(
            [AgencyHomePage.VIEW_CERTIFICATE_LABEL, AgencyHomePage.DOWNLOAD_PDF_LABEL])

    with allure.step("Verify the renewal notification"):
        title = AgencyHomePage.RENEWED_NOTIFICATION.format(valid_until=new_expiry)
        expect(home.notification_title(title)).to_have_text(title)
        expect(home.notification_message(title)).to_have_text(
            AgencyHomePage.RENEWED_NOTIFICATION_TEXT.format(valid_until=new_expiry))
        approved_on = re.search(DATE, home.notification_time(title).inner_text()).group()

    with allure.step("Open the renewal page and verify the renewed application"):
        renewal_page.open()
        expect(renewal_page.latest_application).to_contain_text(
            re.compile(rf"Latest renewal application #\d+ — filed {DATE}\s*·\s*{LicenseRenewalPage.RENEWED}"))
        expect(renewal_page.latest_application).to_contain_text(f"Certificate renewed up to {new_expiry}.")
        expect(renewal_page.certificate_link).to_be_visible()
        opens_on = _fmt(_parse(new_expiry) - timedelta(days=LicenseRenewalPage.WINDOW_DAYS))
        expect(renewal_page.window_notice).to_have_text(LicenseRenewalPage.window_message(opens_on))
        expect(renewal_page.form).to_have_count(0)

    with allure.step("Open the certificate and verify its validity"):
        certificate = CertificatePage(page)
        certificate.open()
        expect(certificate.validity).to_contain_text(CertificatePage.validity_line(_parse(new_expiry)))

    with allure.step(f"Verify Valid from on Home is the approval date ({approved_on}) — defect #16"):
        home = _open_home(page)
        expect(home.certificate_field("Valid from")).to_have_text(approved_on)
