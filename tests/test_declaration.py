import re
from datetime import datetime, timezone

import allure
from playwright.sync_api import expect
from pypdf import PdfReader

from config import FORMS_BASE
from pages.declaration_page import DECLARATION_URL, PREVIEW_LOCKED_URL, PREVIEW_URL, DeclarationPage
from pages.enclosures_page import ENCLOSURES_URL
from pages.login_page import LoginPage
from pages.premises_page import PREMISES_URL, PremisesPage
from test_data.declaration_factory import DeclarationData
from utils.aio import aio_case

STORY = "Declaration & Authorisation"
ON_DECLARATION = re.compile(rf"{re.escape(DECLARATION_URL)}")


def _read_pdf(download) -> tuple[int, str]:
    """Page count and the text of a downloaded PDF, with all whitespace collapsed to single spaces."""
    reader = PdfReader(download.path())
    text = " ".join(page.extract_text() for page in reader.pages)
    return len(reader.pages), re.sub(r"\s+", " ", text)


def _squash(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _file_stem(agency: str) -> str:
    """The agency name as the download's file name has it: anything but letters, digits and '-' becomes '_'."""
    return re.sub(r"[^A-Za-z0-9-]", "_", agency)


def _today_in(text: str) -> bool:
    """The forms print today's date (dd/mm/yyyy); accept the local or the UTC date around midnight."""
    return any(d.strftime("%d/%m/%Y") in text for d in (datetime.now(), datetime.now(timezone.utc)))


def _expect_untouched(declaration: DeclarationPage) -> None:
    expect(declaration.counter).to_have_text(DeclarationPage.counter_text(0))
    for key in DeclarationPage.FORMS:
        expect(declaration.badge(key)).to_have_text(DeclarationPage.BADGE_PENDING)


def _expect_ready(declaration: DeclarationPage, key: str, path: str) -> None:
    expect(declaration.zone_line1(key)).to_have_text(f"✓ {DeclarationPage.chosen_text(path)}")
    expect(declaration.zone_line2(key)).to_have_text(DeclarationPage.ready_text(path))
    expect(declaration.upload_zone(key)).to_have_class(re.compile(r"\bhas\b"))


def _expect_rejected(declaration: DeclarationPage, key: str, path: str, error: str) -> None:
    expect(declaration.zone_line1(key)).to_have_text(f"✗ {DeclarationPage.chosen_text(path)}")
    expect(declaration.zone_line2(key)).to_have_text(error)
    expect(declaration.upload_zone(key)).to_have_class(re.compile(r"\bbad\b"))
    expect(declaration.file_input(key)).to_have_value("")


# ---------------------------------------------------------------------------
# TC-490  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-490")
@allure.story(STORY)
@allure.title("TC-490: Declaration shows the heading, instructions, both form cards and \"Upload & Continue\"")
def test_tc490_page_layout(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given I have completed the Premises Photos step
    When  I open the Declaration step
    Then  the heading, back button, progress bar, instruction tiles, note, progress card, both form cards
          and "Upload & Continue" are shown

    Notion: KAN-TC-490 | KAN-10 AC-1
    """
    page, user = logged_in_declaration_page

    with allure.step("Verify the heading, subtitle and back button"):
        expect(declaration_page.title).to_have_text(DeclarationPage.TITLE)
        expect(declaration_page.sub_title).to_have_text(DeclarationPage.SUBTITLE)
        expect(declaration_page.back_link).to_have_text(DeclarationPage.BACK_LABEL)

    with allure.step("Verify the progress bar"):
        expect(declaration_page.progress_step("Register")).to_contain_text("✓")
        for label in ("Part A", "Part B", "Part C", "Part F", "Documents", "Photos"):
            expect(declaration_page.completed_step_link(label)).to_contain_text("✓")
        for label in ("Declaration", "Preview", "Payment"):
            expect(declaration_page.progress_step(label)).to_be_visible()

    with allure.step("Verify the four instruction tiles, in order"):
        expect(declaration_page.step_tiles).to_have_count(len(DeclarationPage.STEP_TILES))
        for index, (heading, hint) in enumerate(DeclarationPage.STEP_TILES):
            expect(declaration_page.step_tiles.nth(index).locator("b")).to_have_text(heading)
            expect(declaration_page.step_tiles.nth(index).locator("span")).to_have_text(hint)

    with allure.step("Verify the note and tip"):
        expect(declaration_page.note).to_contain_text(DeclarationPage.NOTE)
        expect(declaration_page.tip).to_have_text(DeclarationPage.TIP)

    with allure.step("Verify the 'Signed forms uploaded' card"):
        expect(declaration_page.progress_card).to_contain_text(DeclarationPage.PROGRESS_LABEL)

    for key, (title, rule, summary, download, _) in DeclarationPage.FORMS.items():
        with allure.step(f"Verify the {title} card"):
            expect(declaration_page.card_title(key)).to_have_text(title)
            expect(declaration_page.card_rule(key)).to_have_text(rule)
            expect(declaration_page.read_toggle(key)).to_have_text(summary)
            expect(declaration_page.download_link(key)).to_have_text(download)
            expect(declaration_page.zone_line1(key)).to_have_text(DeclarationPage.zone_label(key))

    with allure.step("Verify 'Upload & Continue'"):
        expect(declaration_page.submit_button).to_have_text(DeclarationPage.SUBMIT_LABEL)
        expect(declaration_page.submit_button).to_be_enabled()


# ---------------------------------------------------------------------------
# TC-491  Default state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-491")
@allure.story(STORY)
@allure.title("TC-491: Declaration opens with 0 / 2 forms uploaded and both forms PENDING")
def test_tc491_default_state(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given no signed form has been uploaded
    When  I open the Declaration step
    Then  the counter reads 0 / 2, both cards are PENDING with their text expanded, and both upload zones are empty

    Notion: KAN-TC-491 | KAN-10 AC-2
    """
    page, user = logged_in_declaration_page

    with allure.step("Verify the counter reads 0 / 2"):
        expect(declaration_page.counter).to_have_text(DeclarationPage.counter_text(0))

    for key in DeclarationPage.FORMS:
        with allure.step(f"Verify FORM-I({key[1:].upper()}) is PENDING with its text expanded and an empty zone"):
            expect(declaration_page.badge(key)).to_have_text(DeclarationPage.BADGE_PENDING)
            expect(declaration_page.read_section(key)).to_have_attribute("open", "")
            expect(declaration_page.form_text(key)).to_be_visible()
            expect(declaration_page.zone_line1(key)).to_have_text(DeclarationPage.zone_label(key))
            expect(declaration_page.zone_line2(key)).to_have_text(DeclarationPage.ZONE_HINT)
            expect(declaration_page.file_input(key)).to_have_value("")


# ---------------------------------------------------------------------------
# TC-492  Form texts collapse and expand
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-492")
@allure.story(STORY)
@allure.title("TC-492: The declaration and authorisation texts can be collapsed and expanded")
def test_tc492_form_text_toggle(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given I am on the Declaration step
    When  I click "Read the declaration text", then "Read the authorisation text", twice each
    Then  each form's wording is shown, hidden, then shown again

    Notion: KAN-TC-492 | KAN-10 AC-3
    """
    page, user = logged_in_declaration_page

    with allure.step("Verify the FORM-I(A) text"):
        for text in ("FORM-I (A)", "(see rule 3 (3))", "Self-Declaration",
                     DeclarationPage.IA_TEXT_START, DeclarationPage.IA_TEXT_SECOND):
            expect(declaration_page.form_text("ia")).to_contain_text(text)

    with allure.step("Verify the FORM-I(B) text"):
        for text in ("FORM-I (B)", "(see rule 3 (1))", "Letter of Authorization", DeclarationPage.IB_TEXT_START):
            expect(declaration_page.form_text("ib")).to_contain_text(text)

    for key in DeclarationPage.FORMS:
        with allure.step(f"Collapse the FORM-I({key[1:].upper()}) text"):
            declaration_page.toggle_text(key)
            expect(declaration_page.read_section(key)).not_to_have_attribute("open", "")
            expect(declaration_page.form_text(key)).to_be_hidden()
        with allure.step(f"Expand the FORM-I({key[1:].upper()}) text again"):
            declaration_page.toggle_text(key)
            expect(declaration_page.read_section(key)).to_have_attribute("open", "")
            expect(declaration_page.form_text(key)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-493  Download pre-filled FORM-I(A)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-493")
@allure.story(STORY)
@allure.title("TC-493: \"Download Pre-filled FORM-I(A)\" downloads the self-declaration filled with the agency's details")
def test_tc493_download_form_ia(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given I am on the Declaration step
    When  I click "Download Pre-filled FORM-I(A)"
    Then  a one-page PDF named after my agency is downloaded, with my agency's name, email, mobile number
          and today's date filled into the self-declaration

    Notion: KAN-TC-493 | KAN-10 AC-4
    """
    page, user = logged_in_declaration_page
    agency = _squash(user.agency_name)

    with allure.step("Verify the link opens in a new tab"):
        expect(declaration_page.download_link("ia")).to_have_attribute("target", "_blank")

    with allure.step("Click 'Download Pre-filled FORM-I(A)'"):
        download = declaration_page.download_form("ia")

    with allure.step("Verify the file name"):
        assert download.suggested_filename == f"MPPA_FormIA_SelfDeclaration_{_file_stem(agency)}.pdf"

    pages, text = _read_pdf(download)
    allure.attach(text, name="FORM-I(A) text", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Verify the PDF has one page with the form heading, header and footer"):
        assert pages == 1
        for expected in ("FORM-I (A)", "(see rule 3 (3))", "Self-Declaration",
                         "MPPA Portal | FORM-I(A) — Self-Declaration", f"Page 1 of 1 | {agency} | Generated:",
                         "# This format may change on portal."):
            assert expected in text, f"'{expected}' not in FORM-I(A)"

    with allure.step("Verify the agency's details are filled in"):
        for expected in (f"of {agency}", f"Email: {user.email}", f"Telephone Number/Mobile Number: {user.mobile}",
                         "Place :", "Agency Seal / Stamp", "Signature of the Applicant"):
            assert expected in text, f"'{expected}' not in FORM-I(A)"
        assert _today_in(text), "today's date not in FORM-I(A)"


# ---------------------------------------------------------------------------
# TC-494  Download pre-filled FORM-I(B)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-494")
@allure.story(STORY)
@allure.title("TC-494: \"Download Pre-filled FORM-I(B)\" downloads the letter of authorization filled with the agency's details")
def test_tc494_download_form_ib(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given I am on the Declaration step
    When  I click "Download Pre-filled FORM-I(B)"
    Then  a two-page PDF named after my agency is downloaded, addressed to the Registering Authority of my area,
          with my agency's name and PAN filled in, the Aadhaar number left blank and the signature boxes on page 2

    Notion: KAN-TC-494 | KAN-10 AC-4
    """
    page, user = logged_in_declaration_page
    agency = _squash(user.agency_name)

    with allure.step("Click 'Download Pre-filled FORM-I(B)'"):
        download = declaration_page.download_form("ib")

    with allure.step("Verify the file name"):
        assert download.suggested_filename == f"MPPA_FormIB_Authorization_{_file_stem(agency)}.pdf"

    pages, text = _read_pdf(download)
    allure.attach(text, name="FORM-I(B) text", attachment_type=allure.attachment_type.TEXT)

    with allure.step("Verify the PDF has two pages with the form heading, header and footer"):
        assert pages == 2
        for expected in ("FORM-I (B)", "(see rule 3 (1))", "Letter of Authorization",
                         "MPPA Portal | FORM-I(B) — Letter of Authorization", f"Page 1 of 2 | {agency} | Generated:",
                         f"Page 2 of 2 | {agency} | Generated:", "# This format may change on portal."):
            assert expected in text, f"'{expected}' not in FORM-I(B)"

    with allure.step("Verify the addressee and the agency's details"):
        # The area is filled in, but from the Part A office city rather than the registration district
        # (open question on KAN-10), so only its presence is checked.
        assert re.search(r"To, The Registering Authority, \[Area/ \S.*? District as specified\] Maharashtra\.", text), \
            "the Registering Authority's area is not filled in"
        assert f"on behalf of the entity named {agency}" in text
        assert f"and PAN {user.pan}" in text
        assert re.search(r"holding Aadhaar Number _+ \(copy to be attached with this letter\)", text), \
            "the Aadhaar number should be left blank"

    with allure.step("Verify the signature section"):
        for expected in ("Signature of Authorized Representative", "Yours faithfully,", "Seal of the Company"):
            assert expected in text, f"'{expected}' not in FORM-I(B)"
        assert _today_in(text), "today's date not in FORM-I(B)"


# ---------------------------------------------------------------------------
# TC-495  Choose a signed form by click and by drag & drop
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-495")
@allure.story(STORY)
@allure.title("TC-495: Choosing a signed PDF shows it as ready to upload")
def test_tc495_choose_signed_forms(
    declaration_page: DeclarationPage, logged_in_declaration_page, declaration_signed_forms_data: DeclarationData
):
    """
    Given no signed form has been uploaded
    When  I choose the signed FORM-I(A) with the file chooser and drop the signed FORM-I(B) onto its zone
    Then  each zone shows "✓ <file name>" and "<N> KB — ready to upload", and nothing is uploaded yet

    Notion: KAN-TC-495 | KAN-10 AC-5 | data: signed_forms
    """
    page, user = logged_in_declaration_page
    files = declaration_signed_forms_data.files

    with allure.step("Choose the signed FORM-I(A)"):
        declaration_page.choose_file("ia", files["ia"])
        _expect_ready(declaration_page, "ia", files["ia"])

    with allure.step("Drag & drop the signed FORM-I(B)"):
        declaration_page.drop_file("ib", files["ib"])
        _expect_ready(declaration_page, "ib", files["ib"])

    with allure.step("Verify nothing is uploaded yet"):
        _expect_untouched(declaration_page)


# ---------------------------------------------------------------------------
# TC-497  Upload & Continue with nothing chosen
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-497")
@allure.story(STORY)
@allure.title("TC-497: \"Upload & Continue\" with no file chosen asks for the signed PDFs")
def test_tc497_nothing_chosen(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given no signed form is chosen
    When  I click "Upload & Continue"
    Then  an alert says "Please choose the signed PDF file(s) to upload." and I stay on the Declaration step

    Notion: KAN-TC-497 | KAN-10 AC-7
    """
    page, user = logged_in_declaration_page

    with allure.step("Click 'Upload & Continue' without choosing a file"):
        message = declaration_page.submit_and_handle_alert()

    with allure.step("Verify the alert and that nothing was submitted"):
        assert message == DeclarationPage.NOTHING_CHOSEN_ALERT
        expect(page).to_have_url(ON_DECLARATION)
        expect(declaration_page.submit_button).to_have_text(DeclarationPage.SUBMIT_LABEL)
        expect(declaration_page.submit_button).to_be_enabled()
        _expect_untouched(declaration_page)


# ---------------------------------------------------------------------------
# TC-498  Back navigation
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-498")
@allure.story(STORY)
@allure.title("TC-498: \"← Step 5\" and the progress bar lead back to earlier steps")
def test_tc498_back_navigation(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given I am on the Declaration step
    When  I click "← Step 5", then return and click "✓ Photos" in the progress bar
    Then  the Documents step opens, then the Premises Photos step with its saved photos

    Notion: KAN-TC-498 | KAN-10 AC-8
    """
    page, user = logged_in_declaration_page
    premises = PremisesPage(page)

    with allure.step("Click '← Step 5' — the Documents step opens"):
        declaration_page.click_back()
        expect(page).to_have_url(re.compile(rf"{re.escape(ENCLOSURES_URL)}"))

    with allure.step("Return to the Declaration step"):
        declaration_page.open()
        expect(declaration_page.title).to_have_text(DeclarationPage.TITLE)

    with allure.step("Click '✓ Photos' — Premises Photos opens with the saved photos"):
        declaration_page.completed_step_link("Photos").click()
        expect(page).to_have_url(re.compile(rf"{re.escape(PREMISES_URL)}"))
        for key in PremisesPage.REQUIRED:
            expect(premises.photo(key)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-499  Save & Log out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-499")
@allure.story(STORY)
@allure.title("TC-499: \"Save & Log out\" logs the user out and login returns to the Declaration step")
def test_tc499_save_and_logout(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given my application is unpaid
    When  I click "Save & Log out" and log in again
    Then  login lands on the Declaration step

    Notion: KAN-TC-499 | KAN-10 AC-9
    """
    page, user = logged_in_declaration_page

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(declaration_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(declaration_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        declaration_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again — lands on the Declaration step"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        expect(page).to_have_url(ON_DECLARATION)
        expect(declaration_page.title).to_have_text(DeclarationPage.TITLE)


# ---------------------------------------------------------------------------
# TC-500  Preview locked
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-500")
@allure.story(STORY)
@allure.title("TC-500: Preview cannot be opened before the signed forms are uploaded")
def test_tc500_preview_locked(declaration_page: DeclarationPage, logged_in_declaration_page):
    """
    Given no signed form has been uploaded
    When  I open preview.php directly
    Then  I am sent back to declaration.php?error=complete_declaration_first

    Notion: KAN-TC-500 | KAN-10 AC-10
    """
    page, user = logged_in_declaration_page

    with allure.step("Open preview.php directly"):
        page.goto(PREVIEW_URL)

    with allure.step("Verify the Declaration step opens instead"):
        expect(page).to_have_url(PREVIEW_LOCKED_URL)
        expect(declaration_page.title).to_have_text(DeclarationPage.TITLE)


# ---------------------------------------------------------------------------
# TC-501  Not a PDF
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-501")
@allure.story(STORY)
@allure.title("TC-501: A signed form that is not a PDF is rejected")
def test_tc501_not_pdf(declaration_page: DeclarationPage, logged_in_declaration_page, declaration_not_pdf_data: DeclarationData):
    """
    Given no signed form has been uploaded
    When  I choose a JPG for FORM-I(A) and drop a PNG onto FORM-I(B)
    Then  each zone shows "✗ <file name>" and "Only scanned PDF files are allowed.", and no file is kept

    Notion: KAN-TC-501 | KAN-10 EC-1 | data: not_pdf
    """
    page, user = logged_in_declaration_page
    files, error = declaration_not_pdf_data.invalid_files, declaration_not_pdf_data.expected_error

    with allure.step("Choose a JPG for FORM-I(A)"):
        declaration_page.choose_file("ia", files["ia"])
        _expect_rejected(declaration_page, "ia", files["ia"], error)

    with allure.step("Drag & drop a PNG onto FORM-I(B)"):
        declaration_page.drop_file("ib", files["ib"])
        _expect_rejected(declaration_page, "ib", files["ib"], error)

    with allure.step("Verify nothing is uploaded"):
        _expect_untouched(declaration_page)


# ---------------------------------------------------------------------------
# TC-502  Larger than 2 MB
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-502")
@allure.story(STORY)
@allure.title("TC-502: A signed PDF larger than 2 MB is rejected")
def test_tc502_too_large(declaration_page: DeclarationPage, logged_in_declaration_page, declaration_too_large_data: DeclarationData):
    """
    Given no signed form has been uploaded
    When  I choose a 3 MB PDF for FORM-I(A), then a PDF under 2 MB
    Then  the first is rejected with "File is 3.00 MB — maximum is 2 MB. Please compress it." and not kept;
          the second is ready to upload

    Notion: KAN-TC-502 | KAN-10 EC-2 | data: too_large
    """
    page, user = logged_in_declaration_page
    data = declaration_too_large_data

    with allure.step("Choose a 3 MB PDF for FORM-I(A)"):
        declaration_page.choose_file("ia", data.invalid_files["ia"])
        _expect_rejected(declaration_page, "ia", data.invalid_files["ia"], data.expected_error)

    with allure.step("Choose a PDF under 2 MB"):
        declaration_page.choose_file("ia", data.files["ia"])
        _expect_ready(declaration_page, "ia", data.files["ia"])
