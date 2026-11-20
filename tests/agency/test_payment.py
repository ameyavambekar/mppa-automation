"""KAN-11 — Payment (fee, receipt and the submitted application).

Only the cases that need no new payment are automated here: they use an agency that is already paid
(``logged_in_agency_home_page``), an unpaid one at Preview (``logged_in_preview_page``) or no login.
Paying from Preview is KAN-TC-513 (tests/agency/test_preview.py); the KAN-11 cases that pay
(873, 874 for new areas, 875, 878, 884, 885) are not automated — each payment uses an agency up.
"""
import re
from datetime import datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from config import USER_MANUAL_URL
from pages.agency_home_page import AGENCY_HOME_URL, AgencyHomePage
from pages.dashboard_page import DASHBOARD_URL, DashboardPage
from pages.declaration_page import DECLARATION_URL, PREVIEW_URL
from pages.first_appeal_page import MY_APPLICATION_URL
from pages.login_page import LoginPage
from pages.my_application_page import MyApplicationPage
from pages.partA_page import PART_A_URL
from pages.payment_success_page import PAYMENT_SUCCESS_URL
from pages.preview_page import PreviewPage
from pages.receipt_page import RECEIPT_URL, ReceiptPage
from utils.aio import aio_case

STORY = "Payment"
IST = timezone(timedelta(hours=5, minutes=30))
ON_USER_MANUAL = re.compile(rf"^{re.escape(USER_MANUAL_URL)}")
ON_PREVIEW = re.compile(rf"^{re.escape(PREVIEW_URL)}")
ON_LOGIN = re.compile(r"/auth/login\.php")
NOT_LOGGED_IN = re.compile(r"/auth/login\.php\?reason=not_logged_in")
AMOUNT = re.compile(r"^₹ [\d,]+\.00$")


def _expect_generated_now_in_ist(text: str) -> None:
    """'Receipt Generated' is the time the receipt is opened, in Indian time (within 15 minutes)."""
    generated = datetime.strptime(text.strip(), ReceiptPage.GENERATED_FORMAT)
    now = datetime.now(IST).replace(tzinfo=None)
    assert abs(generated - now) <= timedelta(minutes=15), \
        f"'Receipt Generated {text}' is not the current Indian time ({now:%d %b %Y, %I:%M %p})"


def _application_id(page) -> str:
    """The Application ID from Home's top bar ('<username> (<Application ID>)') — the fixture lands on Home."""
    match = re.search(r"\((\d{13})\)", AgencyHomePage(page).user_text.inner_text())
    assert match, "Home's top bar shows no 13-digit Application ID"
    return match.group(1)


def _open_receipt(receipt: ReceiptPage, application_id: str) -> None:
    receipt.open()
    receipt.wait_for_load()
    expect(receipt.page).to_have_title(ReceiptPage.page_title(application_id))


# ---------------------------------------------------------------------------
# TC-874  Amount paid = fee for the Part C area
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-874")
@allure.story(STORY)
@allure.title("TC-874: The amount paid is the registration fee for the agency's Part C area")
def test_tc874_amount_paid_is_area_fee(logged_in_agency_home_page, payment_receipt_page: ReceiptPage,
                                       submitted_application_page: MyApplicationPage, payment_fee_for_area):
    """
    Given an agency whose application is paid
    When  I compare its Part C area with the receipt and View my application
    Then  Amount Paid on the receipt, and Fee Amount and Amount Paid on the application, are the fee for that
          area (₹ 2,000 / ₹ 4,000 / ₹ 10,000)

    Checks an agency that is already paid, so it covers the areas of the agencies paid so far (Within
    Maharashtra on dev); paying once per area is not automated.

    Notion: KAN-TC-874 | KAN-11 AC-2 | data: the agency's own area
    """
    page, user = logged_in_agency_home_page
    application_id = _application_id(page)
    application = submitted_application_page

    with allure.step("Read the Part C area on View my application"):
        application.open()
        area = application.field_value(MyApplicationPage.OPERATIONS, "Area of Placement Operations").inner_text().strip()
        fee = payment_fee_for_area(area)
        allure.attach(f"{area}: {fee.amount_text}", "Part C area and fee", allure.attachment_type.TEXT)

    with allure.step(f"Verify Fee Amount and Amount Paid are {fee.amount_text}"):
        expect(application.field_value(MyApplicationPage.FEES, "Fee Amount")).to_have_text(fee.amount_text)
        expect(application.field_value(MyApplicationPage.FEES, "Amount Paid")).to_have_text(fee.amount_text)

    with allure.step(f"Verify the receipt's Amount Paid is {fee.amount_text}"):
        _open_receipt(payment_receipt_page, application_id)
        expect(payment_receipt_page.value("Amount Paid")).to_have_text(fee.amount_text)


# ---------------------------------------------------------------------------
# TC-876  Receipt content
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-876")
@allure.story(STORY)
@allure.title("TC-876: The payment receipt shows the application, the amount paid and the payment details")
def test_tc876_receipt_content(logged_in_agency_home_page, payment_receipt_page: ReceiptPage):
    """
    Given an agency whose application is paid
    When  I open the receipt
    Then  it shows "Payment Confirmed", the Application ID, agency name, jurisdiction, the amount paid, the dev
          transaction / bank / branch, the time it was generated in Indian time, the footer, and "Print Receipt"
          opens the print dialog

    Notion: KAN-TC-876 | KAN-11 AC-4
    """
    page, user = logged_in_agency_home_page
    application_id = _application_id(page)
    receipt = payment_receipt_page

    with allure.step("Open the receipt — titled with the Application ID"):
        _open_receipt(receipt, application_id)

    with allure.step("Verify the heading"):
        expect(receipt.title).to_have_text(ReceiptPage.TITLE)
        expect(receipt.subtitle).to_have_text(ReceiptPage.SUBTITLE)
        expect(receipt.confirmed_badge).to_have_text(ReceiptPage.CONFIRMED)

    with allure.step("Verify the rows, in order"):
        expect(receipt.labels).to_have_text(list(ReceiptPage.LABELS))

    with allure.step("Verify the values"):
        expect(receipt.value("Application ID")).to_have_text(application_id)
        expect(receipt.value("Agency Name")).to_have_text(user.agency_name)
        expect(receipt.value("Jurisdiction")).to_have_text(re.compile(r"\S"))
        expect(receipt.value("Amount Paid")).to_have_text(AMOUNT)
        expect(receipt.value("Transaction / DD No.")).to_have_text(ReceiptPage.DEV_TRANSACTION)
        expect(receipt.value("Bank Name")).to_have_text(ReceiptPage.DEV_BANK)
        expect(receipt.value("Branch Name")).to_have_text(ReceiptPage.DEV_BRANCH)

    with allure.step("Verify 'Receipt Generated' is the current Indian time"):
        _expect_generated_now_in_ist(receipt.value("Receipt Generated").inner_text())

    with allure.step("Verify the note below the table"):
        expect(receipt.footer_note).to_have_text(re.compile(r"\s+".join(map(re.escape, ReceiptPage.FOOTER.split()))))

    with allure.step("Click 'Print Receipt' — the print dialog is called"):
        page.evaluate("() => { window.__printCalls = 0; window.print = () => { window.__printCalls += 1; }; }")
        receipt.click_print()
        assert page.evaluate("() => window.__printCalls") == 1, "'Print Receipt' did not call window.print()"


# ---------------------------------------------------------------------------
# TC-877  Receipt link on Home / My Dashboard
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-877")
@allure.story(STORY)
@allure.title("TC-877: A paid agency can open its receipt again from Home or My Dashboard")
def test_tc877_receipt_link_after_payment(logged_in_agency_home_page, agency_home: AgencyHomePage,
                                          dashboard_page: DashboardPage, payment_receipt_page: ReceiptPage):
    """
    Given an agency whose application is paid
    When  I look for the receipt on Home and My Dashboard
    Then  a link opens the receipt for my Application ID (User Manual: "again anytime from your dashboard")

    Known defect: no page links to the receipt ("Step 8 — Fees & Payment" #20, 20-Nov-2026).

    Notion: KAN-TC-877 | KAN-11 AC-5
    """
    page, user = logged_in_agency_home_page
    application_id = _application_id(page)

    with allure.step("Look for a receipt link on Home and My Dashboard"):
        home_links = agency_home.receipt_links.count()
        dashboard_page.open()
        dashboard_links = dashboard_page.receipt_links.count()
        assert home_links or dashboard_links, \
            "neither Home nor My Dashboard links to the payment receipt (receipt.php)"

    with allure.step("Follow the receipt link — the receipt for the Application ID opens"):
        if not dashboard_links:
            page.goto(AGENCY_HOME_URL)
        links = dashboard_page.receipt_links if dashboard_links else agency_home.receipt_links
        page.goto(links.first.evaluate("a => a.href"))
        expect(page).to_have_title(ReceiptPage.page_title(application_id))


# ---------------------------------------------------------------------------
# TC-879  Download application PDF
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-879")
@allure.story(STORY)
@allure.title("TC-879: \"Download application PDF\" downloads the application as submitted")
def test_tc879_download_application_pdf(logged_in_agency_home_page, dashboard_page: DashboardPage):
    """
    Given an agency whose application is paid
    When  I click "Download application PDF" on My Dashboard
    Then  download_pdf.php opens in a new tab and serves a PDF of the application

    Known defect: download_pdf.php returns HTTP 500 with an empty page ("Agency Dashboard" #10, 20-Nov-2026).

    Notion: KAN-TC-879 | KAN-11 AC-6
    """
    page, user = logged_in_agency_home_page

    with allure.step("Open My Dashboard — 'Download application PDF' opens download_pdf.php in a new tab"):
        dashboard_page.open()
        expect(page).to_have_url(DASHBOARD_URL)
        link = dashboard_page.download_pdf_link
        expect(link).to_contain_text("Complete Form-I as submitted")
        expect(link).to_have_attribute("href", DashboardPage.DOWNLOAD_PDF_HREF)
        expect(link).to_have_attribute("target", "_blank")

    with allure.step("Fetch the link — a PDF is served"):
        response = page.request.get(link.evaluate("a => a.href"))
        served = response.headers.get("content-type", "")
        body = response.body()
        allure.attach(f"HTTP {response.status} · {served} · {len(body)} bytes", "download_pdf.php",
                      allure.attachment_type.TEXT)
        assert response.status == 200, f"download_pdf.php returned HTTP {response.status} ({len(body)} bytes)"
        assert served.startswith("application/pdf"), f"expected a PDF, got {served!r}"
        assert body.startswith(b"%PDF"), "the response is not a PDF file"


# ---------------------------------------------------------------------------
# TC-880  Locked once paid
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-880")
@allure.story(STORY)
@allure.title("TC-880: Once paid, the application can no longer be edited")
def test_tc880_paid_application_locked(logged_in_agency_home_page, submitted_application_page: MyApplicationPage):
    """
    Given an agency whose application is paid
    When  I log in and open Preview, Part A, Declaration and the payment success page directly
    Then  login lands on Home, each of those pages redirects to the User Manual, and View my application is
          read-only

    Notion: KAN-TC-880 | KAN-11 AC-7
    """
    page, user = logged_in_agency_home_page

    with allure.step("Verify login landed on Home"):
        expect(page).to_have_url(re.compile(rf"^{re.escape(AGENCY_HOME_URL)}"))

    for label, url in (("Preview", PREVIEW_URL), ("Part A", PART_A_URL), ("Declaration", DECLARATION_URL),
                       ("the payment success page", PAYMENT_SUCCESS_URL)):
        with allure.step(f"Open {label} directly — the User Manual opens instead"):
            page.goto(url)
            expect(page).to_have_url(ON_USER_MANUAL)

    with allure.step("Open View my application — submitted, read-only"):
        submitted_application_page.open()
        expect(page).to_have_url(MY_APPLICATION_URL)
        expect(submitted_application_page.status_banner).to_contain_text(MyApplicationPage.SUBMITTED_NOTE)
        expect(submitted_application_page.form_fields).to_have_count(0)
        expect(submitted_application_page.edit_links).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-881  View my application — Fees & Payment
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-881")
@allure.story(STORY)
@allure.title("TC-881: View my application shows the payment details")
def test_tc881_view_application_payment(logged_in_agency_home_page, submitted_application_page: MyApplicationPage,
                                        payment_receipt_page: ReceiptPage):
    """
    Given an agency whose application is paid
    When  I open View my application
    Then  "Fees & Payment" is "✓ Completed" and shows the jurisdiction, fee, transaction, amount paid, bank,
          branch and submission time — the same as the receipt

    Notion: KAN-TC-881 | KAN-11 AC-8
    """
    page, user = logged_in_agency_home_page
    application_id = _application_id(page)
    application = submitted_application_page
    section = MyApplicationPage.FEES

    with allure.step("Read the receipt"):
        _open_receipt(payment_receipt_page, application_id)
        receipt = {label: payment_receipt_page.value(label).inner_text().strip()
                   for label in ("Jurisdiction", "Amount Paid", "Transaction / DD No.", "Bank Name", "Branch Name")}

    with allure.step("Open View my application — 'Fees & Payment' is completed"):
        application.open()
        expect(application.section_badge(section)).to_have_text(MyApplicationPage.COMPLETED)
        expect(application.field_labels(section)).to_have_text(list(MyApplicationPage.FEE_LABELS))

    with allure.step("Verify the values match the receipt"):
        expect(application.field_value(section, "Jurisdiction")).to_have_text(receipt["Jurisdiction"])
        expect(application.field_value(section, "Fee Amount")).to_have_text(receipt["Amount Paid"])
        expect(application.field_value(section, "Amount Paid")).to_have_text(receipt["Amount Paid"])
        expect(application.field_value(section, "Transaction Number")).to_have_text(receipt["Transaction / DD No."])
        expect(application.field_value(section, "Bank Name")).to_have_text(receipt["Bank Name"])
        expect(application.field_value(section, "Branch Name")).to_have_text(receipt["Branch Name"])
        expect(application.field_value(section, "Submitted At")).to_have_text(
            re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4}, \d{2}:\d{2}$"))


# ---------------------------------------------------------------------------
# TC-882  Logged out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-882")
@allure.story(STORY)
@allure.title("TC-882: The receipt and My Dashboard ask a logged-out user to log in")
def test_tc882_logged_out(page, login_page: LoginPage):
    """
    Given no agency is logged in
    When  I open the receipt and My Dashboard
    Then  the Agency Login page opens — for the receipt with "Please log in to access the portal."

    Notion: KAN-TC-882 | KAN-11 AC-9
    """
    with allure.step("Open receipt.php — the login page asks me to log in"):
        page.context.clear_cookies()
        page.goto(RECEIPT_URL)
        expect(page).to_have_url(NOT_LOGGED_IN)
        expect(login_page.alert_info).to_have_text(LoginPage.NOT_LOGGED_IN_MESSAGE)
        expect(page.locator("td.label")).to_have_count(0)

    with allure.step("Open dashboard.php — the login page opens"):
        page.goto(DASHBOARD_URL)
        expect(page).to_have_url(ON_LOGIN)
        expect(login_page.login_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-883  Receipt before payment
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-883")
@allure.story(STORY)
@allure.title("TC-883: Opening the receipt before paying keeps the agency logged in")
def test_tc883_receipt_before_payment(logged_in_preview_page, preview_page: PreviewPage):
    """
    Given an agency that is logged in and has not paid
    When  I open receipt.php and then view_application.php directly
    Then  no receipt is shown, I am not sent to the login page, and Preview still opens afterwards

    Known defect: the agency is sent to login.php?reason=not_logged_in and logged out
    ("Step 8 — Fees & Payment" #21, 20-Nov-2026).

    Notion: KAN-TC-883 | KAN-11 EC-1
    """
    page, user = logged_in_preview_page

    for label, url in (("receipt.php", RECEIPT_URL), ("view_application.php", MY_APPLICATION_URL)):
        with allure.step(f"Open {label} — no receipt and no login page"):
            page.goto(url)
            page.wait_for_load_state("networkidle")
            expect(page).not_to_have_url(ON_LOGIN)
            expect(page).not_to_have_title(re.compile(r"^Payment Receipt"))

        with allure.step("Open Preview — still logged in"):
            preview_page.open()
            expect(page).to_have_url(ON_PREVIEW)
            expect(preview_page.title).to_have_text(PreviewPage.TITLE)
