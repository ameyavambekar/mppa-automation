import re
from urllib.parse import parse_qs

import allure
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.declaration_page import DECLARATION_URL, PREVIEW_LOCKED_URL, PREVIEW_URL, DeclarationPage
from pages.login_page import LoginPage
from pages.partA_page import PartAPage
from pages.partB_page import PartBPage
from pages.partC_page import PartCPage
from pages.partF_page import PartFPage
from pages.payment_success_page import PAYMENT_SUCCESS_URL, PaymentSuccessPage
from pages.premises_page import PREMISES_URL
from pages.preview_page import PreviewPage
from pages.receipt_page import ReceiptPage
from test_data.preview_factory import PreviewData
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Application Preview"
ON_PREVIEW = re.compile(rf"{re.escape(PREVIEW_URL)}")
DATE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
APPLICATION_ID = re.compile(r"^\s*\d{13}\s*$")


def _record_paid(user) -> None:
    """Paying submits the application and uses the agency up for every Form-I step test: record it."""
    TestStateStore().mark_form_step_status(username=user.username, step="payment", status="completed")


def _yes_no(checked: bool) -> str:
    return "Yes" if checked else "No"


def _expect_served(page, link, content_type: str = None) -> None:
    """The link opens in a new tab and its URL serves a file (of ``content_type`` when given)."""
    expect(link).to_have_attribute("target", "_blank")
    response = page.request.get(link.evaluate("a => a.href"))
    served = response.headers.get("content-type", "")
    assert response.ok, f"{link.evaluate('a => a.href')} returned {response.status}"
    assert not served.startswith("text/html"), f"expected a file, got {served!r}"
    if content_type:
        assert served.startswith(content_type), f"expected {content_type}, got {served!r}"


# ---------------------------------------------------------------------------
# TC-504  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-504")
@allure.story(STORY)
@allure.title("TC-504: Preview shows the heading, the seven review sections, the fee and \"Confirm & Proceed to Payment\"")
def test_tc504_page_layout(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given both signed forms are uploaded
    When  the Preview step opens
    Then  the heading, back button, intro, progress bar, the seven sections in order, the fee box and the
          payment button are shown

    Notion: KAN-TC-504 | KAN-39 AC-1
    """
    page, user = logged_in_preview_page

    with allure.step("Verify the heading, subtitle and back button"):
        expect(preview_page.title).to_have_text(PreviewPage.TITLE)
        expect(preview_page.sub_title).to_have_text(PreviewPage.SUBTITLE)
        expect(preview_page.back_link).to_have_text(PreviewPage.BACK_LABEL)

    with allure.step("Verify the progress bar"):
        expect(preview_page.progress_step("Register")).to_contain_text("✓")
        for label in ("Part A", "Part B", "Part C", "Part F", "Documents", "Photos", "Declaration"):
            expect(preview_page.completed_step_link(label)).to_contain_text("✓")
        for label in ("Preview", "Payment"):
            expect(preview_page.progress_step(label)).to_be_visible()
        expect(preview_page.completed_step_link("Payment")).to_have_count(0)

    with allure.step("Verify the intro line"):
        expect(preview_page.intro).to_have_text(PreviewPage.INTRO)

    with allure.step("Verify the seven sections, in order"):
        expect(preview_page.section_titles).to_have_count(len(PreviewPage.SECTIONS))
        for index, title in enumerate(PreviewPage.SECTIONS):
            expect(preview_page.section_titles.nth(index)).to_contain_text(title)

    with allure.step("Verify the fee box and the payment button"):
        expect(preview_page.fee_box).to_contain_text(PreviewPage.FEE_LABEL)
        expect(preview_page.pay_button).to_contain_text("Confirm & Proceed to Payment —")
        expect(preview_page.pay_button).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-505  Registration Details locked
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-505")
@allure.story(STORY)
@allure.title("TC-505: Registration Details are locked and show the details the agency registered with")
def test_tc505_registration_locked(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given I am on the Preview step
    When  I look at Registration Details
    Then  it is marked "Locked — cannot be changed", has no Edit link, and shows the registered details
          with a "View PAN" link to the PAN file

    Notion: KAN-TC-505 | KAN-39 AC-2
    """
    page, user = logged_in_preview_page
    section = PreviewPage.REGISTRATION

    with allure.step("Verify the Locked badge and that there is no Edit link"):
        expect(preview_page.locked_badge(section)).to_have_text(PreviewPage.LOCKED_BADGE)
        expect(preview_page.edit_link(section)).to_have_count(0)

    with allure.step("Verify the rows, in order"):
        expect(preview_page.row_labels(section)).to_have_text(list(PreviewPage.REGISTRATION_LABELS))

    with allure.step("Verify the values match the registration"):
        registered = {"Agency Name": user.agency_name, "Username": user.username, "Email": user.email,
                      "PAN Number": user.pan, "Mobile": user.mobile, "Alt. Phone": user.alt_phone}
        for label, value in registered.items():
            if value is not None:
                expect(preview_page.value(section, label)).to_have_text(value)

    with allure.step("Verify 'View PAN' serves the PAN file"):
        link = preview_page.file_links(section)
        expect(link).to_have_text(PreviewPage.VIEW_PAN_LABEL)
        _expect_served(page, link)


# ---------------------------------------------------------------------------
# TC-506  Part A, Part C and Part F values
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-506")
@allure.story(STORY)
@allure.title("TC-506: Preview shows the values saved in Part A, Part C and Part F")
def test_tc506_saved_values(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given Part A, Part C and Part F are saved
    When  I compare each step's saved form with its section on the Preview step
    Then  every value matches, and dates are dd/mm/yyyy

    Notion: KAN-TC-506 | KAN-39 AC-3
    """
    page, user = logged_in_preview_page

    with allure.step("Read the values saved in Part A"):
        part_a = PartAPage(page)
        part_a.open()
        page.wait_for_load_state("networkidle")
        saved_a = {
            "Agency Type": part_a.legal_constitution_select.input_value(),
            "Date of Estab.": part_a.date_of_establishment_input.input_value(),
            "Incorporation No.": part_a.incorporation_no_input.input_value(),
            "TAN": part_a.tan_number_input.input_value(),
            "GSTIN": part_a.gst_number_input.input_value(),
            "Address Line 1": part_a.address_line1_input.input_value(),
            "Address Line 2": part_a.address_line2_input.input_value(),
            "City / Village": part_a.city_input.input_value(),
            "Taluka": part_a.taluka_select.input_value(),
            "District": part_a.district_display.input_value(),
            "State": part_a.head_office_state_select.input_value(),
            "Pincode": part_a.pincode_input.input_value(),
            "Auth. Signatory": part_a.authorised_signatory_input.input_value(),
            "Designation": part_a.designation_input.input_value(),
            "Aadhaar (Signatory)": part_a.aadhaar_input.input_value(),
        }

    with allure.step("Read the values saved in Part C"):
        part_c = PartCPage(page)
        part_c.open()
        page.wait_for_load_state("networkidle")
        saved_c = {
            "Placement Type": part_c.placement_type_select.input_value(),
            "Service Mode": part_c.service_mode_select.input_value(),
            "Digital Platform": _yes_no(part_c.digital_platform_radio("1").is_checked()),
            "Training": _yes_no(part_c.training_radio("1").is_checked()),
            "Mobilization": _yes_no(part_c.mobilization_radio("1").is_checked()),
            "Charges displayed": _yes_no(part_c.charges_displayed_radio("yes").is_checked()),
        }
        sectors = [box.get_attribute("value") for box in part_c.sector_checkboxes.all() if box.is_checked()]

    with allure.step("Read the Place saved in Part F"):
        part_f = PartFPage(page)
        part_f.open()
        page.wait_for_load_state("networkidle")
        place = part_f.place_select.input_value()

    with allure.step("Open the Preview step"):
        preview_page.open()

    with allure.step("Verify the Part A section"):
        expect(preview_page.row_labels(PreviewPage.PART_A)).to_have_text(list(PreviewPage.PART_A_LABELS))
        for label, value in saved_a.items():
            expect(preview_page.value(PreviewPage.PART_A, label)).to_have_text(value)
        expect(preview_page.value(PreviewPage.PART_A, "Date of Estab.")).to_have_text(DATE)

    with allure.step("Verify the Part C section"):
        expect(preview_page.row_labels(PreviewPage.PART_C)).to_have_text(list(PreviewPage.PART_C_LABELS))
        for label, value in saved_c.items():
            expect(preview_page.value(PreviewPage.PART_C, label)).to_have_text(value)
        assert sectors, "no sector is saved in Part C"
        for sector in sectors:
            expect(preview_page.value(PreviewPage.PART_C, "Sectors")).to_contain_text(sector)

    with allure.step("Verify the Part F section"):
        expect(preview_page.row_labels(PreviewPage.PART_F)).to_have_text(list(PreviewPage.PART_F_LABELS))
        expect(preview_page.value(PreviewPage.PART_F, "Place")).to_have_text(place)
        expect(preview_page.value(PreviewPage.PART_F, "Application Date")).to_have_text(DATE)


# ---------------------------------------------------------------------------
# TC-507  Part B key persons
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-507")
@allure.story(STORY)
@allure.title("TC-507: Part B shows one numbered card per key person")
def test_tc507_key_persons(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given key persons are saved in Part B
    When  I open the Preview step
    Then  Part B shows the person type and one card per key person, numbered, with the saved PAN, Aadhaar,
          nationality, mobile (+91 …), address and DIN/DPIN

    Notion: KAN-TC-507 | KAN-39 AC-3
    """
    page, user = logged_in_preview_page

    with allure.step("Read the key persons saved in Part B"):
        part_b = PartBPage(page)
        part_b.open()
        page.wait_for_load_state("networkidle")
        persons = [{
            "name": part_b.full_name_input(i).input_value(),
            "PAN": part_b.pan_input(i).input_value(),
            "Aadhaar": part_b.aadhaar_input(i).input_value(),
            "Nationality": part_b.nationality_select(i).input_value(),
            "Mobile": f"{part_b.country_code_select(i).input_value()} {part_b.mobile_input(i).input_value()}",
            "Address": part_b.address_input(i).input_value(),
            "DIN/DPIN": part_b.din_input(i).input_value(),
        } for i in range(part_b.person_cards.count())]
        assert persons, "no key person is saved in Part B"

    with allure.step("Open the Preview step"):
        preview_page.open()

    with allure.step("Verify the person type and one card per key person"):
        expect(preview_page.value(PreviewPage.PART_B, "Person Type")).to_have_text(re.compile(r"\S"))
        expect(preview_page.person_cards).to_have_count(len(persons))

    for index, person in enumerate(persons):
        with allure.step(f"Verify card {index + 1}: {person['name']}"):
            expect(preview_page.person_name(index)).to_have_text(f"{index + 1}. {person['name']}")
            for label in PreviewPage.PERSON_LABELS:
                expect(preview_page.person_value(index, label)).to_have_text(person[label])


# ---------------------------------------------------------------------------
# TC-508  Enclosures
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-508")
@allure.story(STORY)
@allure.title("TC-508: Enclosures show all six documents with ✓ and a \"View\" link to the saved file")
def test_tc508_enclosures(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given the six documents are uploaded
    When  I look at Enclosures on the Preview step
    Then  each document has a card with ✓ and a "View" link that serves the saved file in a new tab

    Notion: KAN-TC-508 | KAN-39 AC-4
    """
    page, user = logged_in_preview_page

    with allure.step("Verify there are six document cards"):
        expect(preview_page.enclosure_cards).to_have_count(len(PreviewPage.ENCLOSURE_TITLES))

    for title in PreviewPage.ENCLOSURE_TITLES:
        with allure.step(f"Verify '{title}'"):
            card = preview_page.enclosure_card(title)
            expect(card).to_have_class(re.compile(r"\bok\b"))
            expect(preview_page.enclosure_mark(title)).to_have_text("✓")
            link = card.locator("a.file-link")
            expect(link).to_have_text(PreviewPage.VIEW_LABEL)
            _expect_served(page, link)


# ---------------------------------------------------------------------------
# TC-509  Signed forms
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-509")
@allure.story(STORY)
@allure.title("TC-509: Declaration & Authorisation shows both signed forms as Accepted with \"View signed PDF\"")
def test_tc509_signed_forms(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given both signed forms are uploaded
    When  I look at Declaration & Authorisation on the Preview step
    Then  Self-Declaration and Authorisation read "Accepted", and each "View signed PDF" serves a PDF in a new tab

    Notion: KAN-TC-509 | KAN-39 AC-4
    """
    page, user = logged_in_preview_page
    section = PreviewPage.DECLARATION

    with allure.step("Verify the rows"):
        expect(preview_page.row_labels(section)).to_have_text(list(PreviewPage.SIGNED_FORM_LABELS))

    for label in PreviewPage.SIGNED_FORM_LABELS:
        with allure.step(f"Verify {label}"):
            expect(preview_page.signed_form_badge(label)).to_have_text(PreviewPage.ACCEPTED)
            link = preview_page.value(section, label).locator("a.file-link")
            expect(link).to_have_text(PreviewPage.VIEW_SIGNED_LABEL)
            _expect_served(page, link, "application/pdf")


# ---------------------------------------------------------------------------
# TC-510  Edit links
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-510")
@allure.story(STORY)
@allure.title("TC-510: Each section's \"Edit\" link opens its step")
def test_tc510_edit_links(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given I am on the Preview step
    When  I click "Edit" on each section in turn
    Then  that section's step opens

    Notion: KAN-TC-510 | KAN-39 AC-5
    """
    page, user = logged_in_preview_page

    for title, target in PreviewPage.EDIT_TARGETS.items():
        with allure.step(f"Click 'Edit' on {title} — {target} opens"):
            preview_page.open()
            expect(preview_page.edit_link(title)).to_have_text(PreviewPage.EDIT_LABEL)
            preview_page.click_edit(title)
            expect(page).to_have_url(re.compile(rf"{re.escape(f'{FORMS_BASE}/{target}')}"))


# ---------------------------------------------------------------------------
# TC-511  Back navigation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-511")
@allure.story(STORY)
@allure.title("TC-511: \"← Declaration\" returns to the Declaration step")
def test_tc511_back_navigation(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given I am on the Preview step
    When  I click "← Declaration", then return and click "✓ Photos" in the progress bar
    Then  the Declaration step opens, then the Premises Photos step

    Notion: KAN-TC-511 | KAN-39 AC-6
    """
    page, user = logged_in_preview_page

    with allure.step("Click '← Declaration' — the Declaration step opens"):
        preview_page.click_back()
        expect(page).to_have_url(re.compile(rf"{re.escape(DECLARATION_URL)}"))
        expect(DeclarationPage(page).title).to_have_text(DeclarationPage.TITLE)

    with allure.step("Return to the Preview step"):
        preview_page.open()
        expect(preview_page.title).to_have_text(PreviewPage.TITLE)

    with allure.step("Click '✓ Photos' — Premises Photos opens"):
        preview_page.completed_step_link("Photos").click()
        expect(page).to_have_url(re.compile(rf"{re.escape(PREMISES_URL)}"))


# ---------------------------------------------------------------------------
# TC-512  Registration fee
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-512")
@allure.story(STORY)
@allure.title("TC-512: The registration fee block shows the amount, category and rule, and the button shows the same amount")
def test_tc512_registration_fee(preview_page: PreviewPage, logged_in_preview_page, preview_fee_data: PreviewData):
    """
    Given the agency operates only within Maharashtra
    When  I look at the fee block on the Preview step
    Then  it shows ₹ 2,000 with the "Within Maharashtra" category and rule, the payment button shows the same
          amount, and the payment form posts that amount to payment_init.php

    Notion: KAN-TC-512 | KAN-39 AC-7 | data: within_maharashtra
    """
    page, user = logged_in_preview_page
    amount = preview_fee_data.fee_amount

    with allure.step("Verify the fee box"):
        expect(preview_page.fee_box).to_contain_text(PreviewPage.FEE_LABEL)
        expect(preview_page.fee_amount).to_have_text(PreviewPage.fee_text(amount))
        expect(preview_page.fee_category).to_have_text(preview_fee_data.fee_category)
        expect(preview_page.application_id_note).to_have_text(PreviewPage.APPLICATION_ID_NOTE)

    with allure.step("Verify the payment button and the line below it"):
        expect(preview_page.pay_button).to_have_text(PreviewPage.pay_label(amount))
        expect(preview_page.payment_note).to_have_text(PreviewPage.PAYMENT_NOTE)

    with allure.step("Verify the payment form posts the same amount to payment_init.php"):
        expect(preview_page.pay_form).to_have_attribute("action", PreviewPage.PAYMENT_ACTION)
        expect(preview_page.pay_form).to_have_attribute("method", re.compile("post", re.IGNORECASE))
        expect(preview_page.fee_amount_input).to_have_value(str(amount))


# ---------------------------------------------------------------------------
# TC-513  Confirm & Proceed to Payment — submits the application
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-513")
@allure.story(STORY)
@allure.title("TC-513: \"Confirm & Proceed to Payment\" starts the Payment step")
def test_tc513_confirm_and_pay(preview_page: PreviewPage, logged_in_preview_page, preview_fee_data: PreviewData):
    """
    Given I have reviewed my application on the Preview step
    When  I click "Confirm & Proceed to Payment — ₹ 2,000"
    Then  the draft and the fee are posted to payment_init.php, and (on dev, where no payment is taken) the
          success page shows "Payment Successful — Application Submitted!" with a 13-digit Application ID,
          "Print Receipt" and "Go to Dashboard →"; after logging in again the receipt shows that Application ID,
          the agency and the amount paid

    Known defect: paying ends the session, so "Print Receipt" and "Go to Dashboard →" on the success page
    lead to the login page; the receipt is therefore checked after logging in again.

    Notion: KAN-TC-513 | KAN-39 AC-8 | data: within_maharashtra
    """
    page, user = logged_in_preview_page
    amount = preview_fee_data.fee_amount
    success = PaymentSuccessPage(page)

    with allure.step("Click 'Confirm & Proceed to Payment' — the draft and the fee are posted to payment_init.php"):
        expect(preview_page.pay_button).to_have_text(PreviewPage.pay_label(amount))
        with page.expect_request(lambda r: r.method == "POST" and r.url.endswith(PreviewPage.PAYMENT_ACTION)) as sent:
            preview_page.confirm_and_pay()
        _record_paid(user)
        posted = parse_qs(sent.value.post_data)
        assert posted.get("fee_amount") == [str(amount)], f"posted fee_amount {posted.get('fee_amount')}"
        assert posted.get("draft_token", [""])[0], "no draft_token was posted"

    with allure.step("Verify the payment success page"):
        expect(page).to_have_url(re.compile(rf"{re.escape(PAYMENT_SUCCESS_URL)}"))
        expect(success.title).to_have_text(PaymentSuccessPage.TITLE)
        expect(success.message).to_have_text(PaymentSuccessPage.MESSAGE)
        expect(success.application_id_label).to_be_visible()
        expect(success.application_id).to_have_text(APPLICATION_ID)

    with allure.step("Verify 'Print Receipt' and 'Go to Dashboard →'"):
        expect(success.receipt_link).to_have_attribute("href", "receipt.php")
        expect(success.receipt_link).to_have_attribute("target", "_blank")
        expect(success.dashboard_link).to_have_attribute("href", "dashboard.php")

    application_id = success.application_id.inner_text().strip()
    TestStateStore().record_application_id(username=user.username, application_id=application_id)

    with allure.step("Log in again — the application is submitted"):
        page.context.clear_cookies()
        login = LoginPage(page)
        login.open()
        login.login(user.username, user.password)
        page.wait_for_load_state("networkidle")
        expect(page.locator("body")).to_contain_text(f"{user.username} ({application_id})")

    with allure.step("Verify the receipt shows the Application ID, the agency and the amount paid"):
        receipt = ReceiptPage(page)
        receipt.open()
        expect(page).to_have_title(ReceiptPage.page_title(application_id))
        expect(receipt.title).to_have_text(ReceiptPage.TITLE)
        expect(receipt.value("Application ID")).to_have_text(application_id)
        expect(receipt.value("Agency Name")).to_have_text(user.agency_name)
        expect(receipt.value("Amount Paid")).to_have_text(ReceiptPage.amount_text(amount))
        expect(receipt.value("Bank Name")).to_have_text(ReceiptPage.DEV_BANK)
        expect(receipt.print_button).to_be_visible()


# ---------------------------------------------------------------------------
# TC-514  Preview locked until the Declaration step is complete
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-514")
@allure.story(STORY)
@allure.title("TC-514: Preview is locked until both signed forms are uploaded")
def test_tc514_preview_locked(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given the signed forms are not both uploaded
    When  I open preview.php directly
    Then  I am sent back to declaration.php?error=complete_declaration_first

    Notion: KAN-TC-514 | KAN-39 AC-9, EC-1
    """
    page, user = logged_in_declaration_page

    with allure.step("Open preview.php directly"):
        page.goto(PREVIEW_URL)

    with allure.step("Verify the Declaration step opens instead"):
        expect(page).to_have_url(PREVIEW_LOCKED_URL)
        expect(declaration_page.title).to_have_text(DeclarationPage.TITLE)


# ---------------------------------------------------------------------------
# TC-515  Part F certificates not given
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-515")
@allure.story(STORY)
@allure.title("TC-515: Part F certificates that were not given are shown as \"—\"")
def test_tc515_certificates_not_given(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given Part F was saved with certificates answered No
    When  I open the Preview step
    Then  each of those certificates' number and date show "—", and Application Date and Place are shown

    Notion: KAN-TC-515 | KAN-39 EC-2
    """
    page, user = logged_in_preview_page

    with allure.step("Read which certificates Part F has answered No"):
        part_f = PartFPage(page)
        part_f.open()
        page.wait_for_load_state("networkidle")
        not_given = [rows for rows, cert in PreviewPage.CERTIFICATE_ROWS.items()
                     if part_f.certificate_radio(cert, False).is_checked()]
        assert not_given, "every certificate shown on Preview is answered Yes in Part F"

    with allure.step("Open the Preview step"):
        preview_page.open()

    for number_label, date_label in not_given:
        with allure.step(f"Verify {number_label} and {date_label} show '—'"):
            expect(preview_page.value(PreviewPage.PART_F, number_label)).to_have_text(PreviewPage.EMPTY)
            expect(preview_page.value(PreviewPage.PART_F, date_label)).to_have_text(PreviewPage.EMPTY)

    with allure.step("Verify Application Date and Place are shown"):
        expect(preview_page.value(PreviewPage.PART_F, "Application Date")).to_have_text(DATE)
        expect(preview_page.value(PreviewPage.PART_F, "Place")).not_to_have_text(PreviewPage.EMPTY)
        expect(preview_page.value(PreviewPage.PART_F, "Place")).to_have_text(re.compile(r"\S"))


# ---------------------------------------------------------------------------
# TC-516  Save & Log out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-516")
@allure.story(STORY)
@allure.title("TC-516: \"Save & Log out\" from Preview keeps the application and login returns to it")
def test_tc516_save_and_logout(preview_page: PreviewPage, logged_in_preview_page):
    """
    Given my application is unpaid
    When  I click "Save & Log out" on the Preview step and log in again
    Then  login lands on the Preview step

    Notion: KAN-TC-516 | KAN-39 AC-10
    """
    page, user = logged_in_preview_page

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(preview_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(preview_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        preview_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again — lands on the Preview step"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        expect(page).to_have_url(ON_PREVIEW)
        expect(preview_page.title).to_have_text(PreviewPage.TITLE)
