import os
import re

import allure
import pytest
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.enclosures_page import ENCLOSURES_LOCKED_STEP_URL, ENCLOSURES_URL, PREMISES_URL, EnclosuresPage
from pages.login_page import LoginPage
from pages.partC_page import PartCPage
from pages.partF_page import PART_F_URL, PartFPage
from test_data.enclosures_factory import DocumentUploads
from utils.aio import aio_case
from utils.state_store import TestStateStore

STORY = "Step 5 - Upload Documents (Enclosures)"
ON_ENCLOSURES = re.compile(rf"{re.escape(ENCLOSURES_URL)}")
PART_F_LOCKED_STEP_URL = f"{PART_F_URL}?error=complete_partF_first"


def _record_uploads(enclosures: EnclosuresPage, user) -> None:
    """Every upload uses the user up for the Documents tests: record it in the state store."""
    status = "completed" if enclosures.uploaded_count() == len(EnclosuresPage.MANDATORY) else "in_progress"
    TestStateStore().mark_form_step_status(username=user.username, step="enclosures", status=status)


def _upload(enclosures: EnclosuresPage, page, user, documents: dict) -> None:
    """Uploads ``{number: path}`` and checks the success message."""
    enclosures.upload_documents(documents)
    _record_uploads(enclosures, user)
    expect(page).to_have_url(ON_ENCLOSURES)
    expect(enclosures.messages).to_have_text([EnclosuresPage.uploaded_message(len(documents))])


def _expect_uploaded(enclosures: EnclosuresPage, number: int, path: str) -> None:
    """Row ``number`` shows ✓, the file name and 'View ↗'."""
    expect(enclosures.document_row(number)).to_have_class(re.compile(r"\bdone\b"))
    expect(enclosures.document_number(number)).to_have_text("✓")
    expect(enclosures.uploaded_badge(number)).to_contain_text(os.path.basename(path))
    expect(enclosures.view_link(number)).to_have_attribute("target", "_blank")


def _expect_not_uploaded(enclosures: EnclosuresPage, number: int) -> None:
    expect(enclosures.document_row(number)).not_to_have_class(re.compile(r"\bdone\b"))
    expect(enclosures.document_number(number)).to_have_text(str(number))
    expect(enclosures.uploaded_badge(number)).to_have_count(0)


ALL = len(EnclosuresPage.MANDATORY)   # 2 since portal 2.1.0 (17-Nov-2026)
START = EnclosuresPage.UPLOADED_AT_START   # 1 since 20-Nov-2026: the PAN card from registration


def _expect_registration_pan(enclosures: EnclosuresPage) -> None:
    """Document 1 is the PAN card carried over from registration: ✓, 'PAN_card_<PAN>.pdf', 'View ↗' and
    the note saying nothing more is needed."""
    expect(enclosures.document_row(1)).to_have_class(re.compile(r"\bdone\b"))
    expect(enclosures.document_number(1)).to_have_text("✓")
    expect(enclosures.uploaded_badge(1)).to_contain_text(EnclosuresPage.REGISTRATION_PAN_PREFIX)
    expect(enclosures.view_link(1)).to_have_attribute("target", "_blank")
    expect(enclosures.pan_from_registration_note).to_be_visible()


def _expect_rejected(enclosures: EnclosuresPage, number: int, error: str) -> None:
    """The chosen file was rejected straight away and removed from the chooser."""
    expect(enclosures.document_error(number)).to_have_text(error)
    expect(enclosures.document_error(number)).to_be_visible()
    assert enclosures.file_input(number).evaluate("e => e.files.length") == 0, "The rejected file was kept"


# ---------------------------------------------------------------------------
# TC-379  Documents locked until Part F is saved
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-379")
@allure.story(STORY)
@allure.title("TC-379: The Documents step cannot be used before Part F is saved")
def test_tc379_documents_locked_until_part_f_saved(enclosures_page: EnclosuresPage, logged_in_part_f_page):
    """
    Given Part C is saved and Part F is not
    When  I look at the progress bar on Part F, then open the Documents step by URL
    Then  Documents is not a clickable step and I am sent back to Part F

    Notion: KAN-TC-379 | KAN-9 AC-10 | data: agency with Part C saved, Part F never saved
    """
    page, user = logged_in_part_f_page
    part_f = PartFPage(page)

    with allure.step("Verify Documents in the progress bar is not a link"):
        expect(enclosures_page.progress_step("Documents")).to_be_visible()
        expect(enclosures_page.completed_step_link("Documents")).to_have_count(0)

    with allure.step("Open the Documents step directly by URL"):
        enclosures_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify the user is sent back to Part F"):
        expect(page).to_have_url(PART_F_LOCKED_STEP_URL)
        expect(part_f.title).to_contain_text("Certificates, Licences & Signature")
        expect(enclosures_page.title).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-380  Both mandatory documents — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-380")
@allure.story(STORY)
@allure.title("TC-380: Uploading the office address proof completes the mandatory documents (2/2)")
def test_tc380_all_mandatory_documents(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_only_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file (1/2)
    When  I choose the office address proof's type and a PDF for it (document 2) and click "Upload Documents"
    Then  "1 file(s) uploaded successfully." is shown, the counter reads 2/2 with the bar full,
          documents 1 and 2 show ✓, their file names and "View ↗",
          and a "Next: Premises Photos →" link appears

    Since 20-Nov-2026 the PAN card (document 1) is carried over from registration.

    Notion: KAN-TC-380 | KAN-9 AC-2, AC-4, AC-11, AC-12 | data: address_proof_only
    """
    page, user = logged_in_enclosures_page
    data = enclosures_address_proof_only_data

    with allure.step("Upload document 2"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify the counter reads 2/2 with the bar full"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*100%"))

    with allure.step("Verify documents 1 and 2 are uploaded"):
        _expect_registration_pan(enclosures_page)
        _expect_uploaded(enclosures_page, 2, data.documents[2])

    with allure.step("Verify 'Next: Premises Photos →' links to premises.php"):
        expect(enclosures_page.next_premises_photos_link).to_be_visible()
        expect(enclosures_page.next_premises_photos_link).to_have_attribute("href", re.compile(r"premises\.php$"))


# ---------------------------------------------------------------------------
# TC-381  Counter changes only after uploading — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-381")
@allure.story(STORY)
@allure.title("TC-381: The mandatory counter starts at 1/2 and changes only after \"Upload Documents\"")
def test_tc381_counter_after_upload(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_only_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I choose the office address proof's type and file without uploading, then click "Upload Documents"
    Then  the counter reads 1/2 (bar half full) until "Upload Documents", then 2/2 (bar full)

    Notion: KAN-TC-381 | KAN-9 AC-2, AC-12 | data: address_proof_only
    """
    page, user = logged_in_enclosures_page
    data = enclosures_address_proof_only_data

    with allure.step("Verify the counter reads 1/2 with the bar half full"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*50%"))

    with allure.step("Choose document 2 and its type without uploading — the counter stays 1/2"):
        enclosures_page.select_address_proof_type(data.address_proof_type)
        enclosures_page.choose_document(2, data.documents[2])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))

    with allure.step("Click 'Upload Documents' — 2/2"):
        enclosures_page.click_upload()
        _record_uploads(enclosures_page, user)
        expect(enclosures_page.messages).to_have_text([EnclosuresPage.uploaded_message(1)])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*100%"))


# ---------------------------------------------------------------------------
# TC-382  Premises Photos locked until 2/2 — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-382")
@allure.story(STORY)
@allure.title("TC-382: The Premises Photos step is locked until both mandatory documents are uploaded")
def test_tc382_premises_photos_locked_until_both(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_only_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file (1/2)
    When  I open Premises Photos by URL, log out and back in, then upload the office address proof
    Then  I am sent back to the Documents step and login lands there, until 2/2 shows
          "Next: Premises Photos →", which opens the Premises Photos step

    Notion: KAN-TC-382 | KAN-9 AC-11 | data: address_proof_only
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify the counter reads 1/2 and there is no 'Next: Premises Photos →' link"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
        expect(enclosures_page.next_premises_photos_link).to_have_count(0)

    with allure.step("Open the Premises Photos step directly by URL — sent back to Documents"):
        page.goto(PREMISES_URL)
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(ENCLOSURES_LOCKED_STEP_URL)
        expect(enclosures_page.title).to_have_text(EnclosuresPage.TITLE)

    with allure.step("Click 'Save & Log out' and log in again — login lands on Documents"):
        enclosures_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        expect(page).to_have_url(ON_ENCLOSURES)

    with allure.step("Upload the office address proof — 2/2 and 'Next: Premises Photos →'"):
        _upload(enclosures_page, page, user, enclosures_address_proof_only_data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))
        expect(enclosures_page.next_premises_photos_link).to_be_visible()

    with allure.step("Click 'Next: Premises Photos →' — the Premises Photos step opens"):
        enclosures_page.next_premises_photos_link.click()
        page.wait_for_load_state("networkidle")
        expect(page).to_have_url(re.compile(rf"{re.escape(PREMISES_URL)}"))


# ---------------------------------------------------------------------------
# TC-383  Optional documents don't count — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-383")
@allure.story(STORY)
@allure.title("TC-383: Optional documents 3–4 upload without changing the mandatory counter")
def test_tc383_optional_documents(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_only_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I upload documents 3 and 4 only
    Then  both are shown as uploaded, the counter still reads 1/2 and there is no Next link

    Notion: KAN-TC-383 | KAN-9 AC-2, AC-6 | data: optional_only
    """
    page, user = logged_in_enclosures_page
    data = enclosures_optional_only_data

    with allure.step("Upload documents 3 and 4"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify both are uploaded and the counter still reads 1/2"):
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
        expect(enclosures_page.next_premises_photos_link).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-384  Not a PDF
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-384")
@allure.story(STORY)
@allure.title("TC-384: A file that is not a PDF is rejected as soon as it is chosen")
def test_tc384_not_pdf_rejected(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_not_pdf_data: DocumentUploads
):
    """
    Given I am on the Documents step
    When  I choose a JPG for document 3, a PNG for document 1 and a DOCX for document 4
    Then  each shows "Only PDF files are allowed." and the file is removed

    Notion: KAN-TC-384 | KAN-9 AC-3, EC-1 | data: not_pdf
    """
    page, user = logged_in_enclosures_page

    for number, path in enclosures_not_pdf_data.invalid_files:
        with allure.step(f"Choose {os.path.basename(path)} for document {number} — rejected"):
            enclosures_page.choose_document(number, path)
            _expect_rejected(enclosures_page, number, EnclosuresPage.NOT_PDF_ERROR)


# ---------------------------------------------------------------------------
# TC-385  Over 2 MB
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-385")
@allure.story(STORY)
@allure.title("TC-385: A PDF larger than 2 MB is rejected as soon as it is chosen")
def test_tc385_pdf_too_large(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_too_large_data: DocumentUploads
):
    """
    Given I am on the Documents step
    When  I choose a 3 MB PDF for document 2
    Then  "File is larger than 2 MB." is shown and the file is removed

    Notion: KAN-TC-385 | KAN-9 AC-3, EC-3 | data: too_large
    """
    page, user = logged_in_enclosures_page
    number, path = enclosures_too_large_data.invalid_files[0]

    with allure.step(f"Choose {os.path.basename(path)} for document {number}"):
        enclosures_page.choose_document(number, path)

    with allure.step("Verify the error and that the file was removed"):
        _expect_rejected(enclosures_page, number, EnclosuresPage.TOO_LARGE_ERROR)


# ---------------------------------------------------------------------------
# TC-386  Uploaded state persists — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-386")
@allure.story(STORY)
@allure.title("TC-386: Uploaded documents are shown as uploaded when the Documents step is reopened")
def test_tc386_uploaded_state_persists(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_document_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I upload document 3, open Part F and come back
    Then  document 3 still shows ✓, its file name and "View ↗" (opening a new tab), and the counter reads 1/2

    Notion: KAN-TC-386 | KAN-9 AC-9 | data: optional_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_optional_document_data.documents[3]

    with allure.step("Upload document 3"):
        _upload(enclosures_page, page, user, {3: path})
        _expect_uploaded(enclosures_page, 3, path)

    with allure.step("Open Part F, then come back to the Documents step"):
        PartFPage(page).open()
        enclosures_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify document 3 is still uploaded and the counter reads 1/2"):
        _expect_uploaded(enclosures_page, 3, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
        expect(enclosures_page.view_link(3)).to_have_attribute("href", re.compile(r"serve_enclosure\.php"))


# ---------------------------------------------------------------------------
# TC-387  Replacing a document — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-387")
@allure.story(STORY)
@allure.title("TC-387: Uploading a new file replaces an uploaded document, including the PAN card from registration")
def test_tc387_replace_document(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_replacement_data: DocumentUploads
):
    """
    Given document 1 is the PAN card carried over from registration
    When  I choose a PDF with a different name for it and click "Upload Documents"
    Then  document 1 shows the new file name, "View ↗" points to a new upload, and the counter stays 1/2

    Notion: KAN-TC-387 | KAN-9 AC-9, AC-12 | data: replacement
    """
    page, user = logged_in_enclosures_page
    data = enclosures_replacement_data

    with allure.step("Verify document 1 is the PAN card from registration and its chooser is available"):
        _expect_registration_pan(enclosures_page)
        expect(enclosures_page.file_name(1)).to_have_attribute("title", EnclosuresPage.SAVED_FILE_TOOLTIP)
        expect(enclosures_page.file_input(1)).to_be_enabled()
        old_link = enclosures_page.view_link(1).get_attribute("href")

    with allure.step(f"Upload {os.path.basename(data.replacement)} for document 1"):
        _upload(enclosures_page, page, user, {1: data.replacement})

    with allure.step("Verify the new file replaced the old one"):
        _expect_uploaded(enclosures_page, 1, data.replacement)
        expect(enclosures_page.view_link(1)).not_to_have_attribute("href", old_link)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))


# ---------------------------------------------------------------------------
# TC-388  "← Part F" — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-388")
@allure.story(STORY)
@allure.title("TC-388: \"← Part F\" returns to Part F with its data intact and keeps the uploaded documents")
def test_tc388_back_to_part_f(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_document_data: DocumentUploads
):
    """
    Given document 3 is uploaded
    When  I click "← Part F", then open the Documents step again
    Then  Part F opens without a dialog with its saved Place, and document 3 is still uploaded

    Notion: KAN-TC-388 | KAN-9 AC-7 | data: optional_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_optional_document_data.documents[3]
    part_f = PartFPage(page)

    with allure.step("Precondition: upload document 3"):
        _upload(enclosures_page, page, user, {3: path})

    with allure.step("Click '← Part F'"):
        message = enclosures_page.click_and_handle_alert(enclosures_page.back_to_part_f_link)
        assert message == "", f"Unexpected dialog: {message}"

    with allure.step("Verify Part F opens with its saved values"):
        expect(page).to_have_url(re.compile(rf"{re.escape(PART_F_URL)}"))
        expect(part_f.title).to_contain_text("Certificates, Licences & Signature")
        expect(part_f.place_select).not_to_have_value("")

    with allure.step("Open the Documents step again — document 3 is still uploaded"):
        enclosures_page.open()
        _expect_uploaded(enclosures_page, 3, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))


# ---------------------------------------------------------------------------
# TC-389  Upload with nothing chosen
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-389")
@allure.story(STORY)
@allure.title("TC-389: \"Upload Documents\" with no file chosen shows \"No files selected.\"")
def test_tc389_upload_nothing_chosen(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given no file is chosen
    When  I click "Upload Documents"
    Then  I stay on the Documents step with "No files selected." and the counter unchanged

    Notion: KAN-TC-389 | KAN-9 AC-5, EC-4
    """
    page, user = logged_in_enclosures_page

    with allure.step("Click 'Upload Documents' with every chooser empty"):
        enclosures_page.click_upload()

    with allure.step("Verify the message and that nothing changed"):
        expect(page).to_have_url(ON_ENCLOSURES)
        expect(enclosures_page.messages).to_have_text([EnclosuresPage.NO_FILES_MESSAGE])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))


# ---------------------------------------------------------------------------
# TC-394  Same file twice — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-394")
@allure.story(STORY)
@allure.title("TC-394: Uploading the same file twice to the same document is accepted as a replacement")
def test_tc394_same_file_twice(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_document_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I upload the same PDF for document 3 twice
    Then  each upload succeeds, document 3 stays uploaded and the counter stays 1/2

    Notion: KAN-TC-394 | KAN-9 EC-6 | data: optional_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_optional_document_data.documents[3]

    for attempt in ("first", "second"):
        with allure.step(f"Upload {os.path.basename(path)} for document 3 ({attempt} time)"):
            _upload(enclosures_page, page, user, {3: path})
            _expect_uploaded(enclosures_page, 3, path)
            expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))


# ---------------------------------------------------------------------------
# TC-395  Training certificate optional regardless of Part C — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-395")
@allure.story(STORY)
@allure.title("TC-395: The training certificate is shown as optional even when Part C says no training")
def test_tc395_training_certificate_optional(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_only_data: DocumentUploads
):
    """
    Given Part C was saved with "Does the agency provide training?" = No
    When  I open the Documents step and upload document 2 only (document 1 is the PAN card from registration)
    Then  document 3 (training certificate) is an optional row and the counter reads 2/2 without it

    Notion: KAN-TC-395 | KAN-9 EC-5 | data: address_proof_only
    """
    page, user = logged_in_enclosures_page
    part_c = PartCPage(page)

    with allure.step("Precondition: Part C was saved with training = No"):
        part_c.open()
        page.wait_for_load_state("networkidle")
        if not part_c.training_radio("0").is_checked():
            pytest.skip(f"{user.username}'s Part C was saved with training = Yes")
        enclosures_page.open()

    with allure.step("Verify document 3 is shown as optional"):
        expect(enclosures_page.document_title(3)).to_have_text(EnclosuresPage.DOCUMENTS[3][1])
        expect(enclosures_page.required_marker(3)).to_have_count(0)

    with allure.step("Upload document 2 only — 2/2"):
        _upload(enclosures_page, page, user, enclosures_address_proof_only_data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))
        _expect_not_uploaded(enclosures_page, 3)


# ---------------------------------------------------------------------------
# TC-396  Uploads persist across sessions — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-396")
@allure.story(STORY)
@allure.title("TC-396: After logging out and back in, the counter and upload states are as left")
def test_tc396_uploads_persist_across_sessions(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_document_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I upload document 3, click "Save & Log out", log in again and open the Documents step
    Then  documents 1 (PAN card) and 3 are uploaded, 2 and 4 are not, and the counter reads 1/2

    Notion: KAN-TC-396 | KAN-9 AC-8, AC-9 | data: optional_document
    """
    page, user = logged_in_enclosures_page
    data = enclosures_optional_document_data

    with allure.step("Upload document 3"):
        _upload(enclosures_page, page, user, data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))

    with allure.step("Click 'Save & Log out', log in again and open the Documents step"):
        enclosures_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        enclosures_page.open()

    with allure.step("Verify documents 1 and 3 are uploaded and 2 and 4 are not"):
        _expect_registration_pan(enclosures_page)
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        for number in set(EnclosuresPage.DOCUMENTS) - set(data.documents) - {1}:
            _expect_not_uploaded(enclosures_page, number)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))


# ---------------------------------------------------------------------------
# TC-397  Under 10 KB
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-397")
@allure.story(STORY)
@allure.title("TC-397: An empty or tiny PDF (under 10 KB) is rejected as soon as it is chosen")
def test_tc397_pdf_too_small(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_too_small_data: DocumentUploads
):
    """
    Given I am on the Documents step
    When  I choose a 298-byte PDF, then a 0-byte PDF, for document 4
    Then  each shows "File is too small — upload a clear, complete file." and is removed

    Notion: KAN-TC-397 | KAN-9 AC-3, EC-2 | data: too_small
    """
    page, user = logged_in_enclosures_page

    for number, path in enclosures_too_small_data.invalid_files:
        with allure.step(f"Choose {os.path.basename(path)} for document {number} — rejected"):
            enclosures_page.choose_document(number, path)
            _expect_rejected(enclosures_page, number, EnclosuresPage.TOO_SMALL_ERROR)


# ---------------------------------------------------------------------------
# TC-471  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-471")
@allure.story(STORY)
@allure.title("TC-471: The Documents step shows the heading, note, counter, four documents and upload button")
def test_tc471_page_layout(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given I have saved Part F
    When  I open the Documents step
    Then  the heading, subtitle, "← Part F", progress bar, note, counter, four documents in two groups
          (with the address proof type select) and the "Upload Documents" button are shown

    Portal 2.1.0 (17-Nov-2026): four documents in "Core Documents" and "Other"; the note points to the
    Premises Photos step for office photographs. 20-Nov-2026: shorter note, PAN help line, address proof
    type "Other".

    Notion: KAN-TC-471 | KAN-9 AC-1, AC-12, AC-13
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify the heading, subtitle and '← Part F'"):
        expect(enclosures_page.title).to_have_text(EnclosuresPage.TITLE)
        expect(enclosures_page.sub_title).to_have_text(EnclosuresPage.SUBTITLE)
        expect(enclosures_page.back_to_part_f_link).to_be_visible()

    with allure.step("Verify the progress bar"):
        expect(enclosures_page.progress_step("Register")).to_contain_text("✓")
        for label in ("Part A", "Part B", "Part C", "Part F"):
            expect(enclosures_page.completed_step_link(label)).to_contain_text("✓")
        for label in ("Documents", "Photos", "Declaration", "Preview", "Payment"):
            expect(enclosures_page.progress_step(label)).to_be_visible()

    with allure.step("Verify the note and the counter"):
        expect(enclosures_page.note).to_contain_text(EnclosuresPage.NOTE)
        expect(enclosures_page.note).to_contain_text(EnclosuresPage.NOTE_PHOTOS)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))

    with allure.step("Verify the groups and the four documents"):
        expect(enclosures_page.group_headings).to_have_text(list(EnclosuresPage.GROUPS))
        expect(enclosures_page.document_rows).to_have_count(len(EnclosuresPage.DOCUMENTS))
        for number, (_, title, mandatory) in EnclosuresPage.DOCUMENTS.items():
            expect(enclosures_page.document_title(number)).to_have_text(title)
            expect(enclosures_page.required_marker(number)).to_have_count(1 if mandatory else 0)
            expect(enclosures_page.document_hint(number)).to_have_text(EnclosuresPage.FILE_HINT)
        expect(enclosures_page.document_help(1)).to_have_text(EnclosuresPage.PAN_HELP)

    with allure.step("Verify the office address proof type select"):
        expect(enclosures_page.address_proof_help).to_have_text(EnclosuresPage.ADDRESS_PROOF_HELP)
        expect(enclosures_page.address_proof_type_select.locator("option")).to_have_text(
            [EnclosuresPage.ADDRESS_PROOF_PLACEHOLDER, *EnclosuresPage.ADDRESS_PROOF_TYPES])
        expect(enclosures_page.address_proof_type_select).to_have_value("")
        expect(enclosures_page.address_proof_other_input).to_be_hidden()

    with allure.step("Verify the upload button"):
        expect(enclosures_page.upload_button).to_have_text("Upload Documents")


# ---------------------------------------------------------------------------
# TC-472  Default state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-472")
@allure.story(STORY)
@allure.title("TC-472: The Documents step opens with the PAN card from registration and 1/2 uploaded")
def test_tc472_default_state(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given nothing has been uploaded on the Documents step
    When  I open it
    Then  the counter reads 1/2 with the bar half full, document 1 is the PAN card from registration
          ("✓ PAN_card_<PAN>.pdf", "View ↗" and the carried-over note), documents 2–4 show their numbers
          with no file, and there is no "Next: Premises Photos →" link

    Until 20-Nov-2026 the step opened at 0/2 with every document empty.

    Notion: KAN-TC-472 | KAN-9 AC-2, AC-12
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify the counter"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*50%"))

    with allure.step("Verify document 1 is the PAN card from registration"):
        _expect_registration_pan(enclosures_page)
        expect(enclosures_page.file_name(1)).to_have_text(re.compile(
            rf"^✓\s*{re.escape(EnclosuresPage.REGISTRATION_PAN_PREFIX)}\w+\.pdf$"))
        expect(enclosures_page.file_name(1)).to_have_attribute("title", EnclosuresPage.SAVED_FILE_TOOLTIP)

    with allure.step("Verify documents 2–4 are empty"):
        for number in sorted(set(EnclosuresPage.DOCUMENTS) - {1}):
            _expect_not_uploaded(enclosures_page, number)
            expect(enclosures_page.file_name(number)).to_have_text("No file chosen")
        expect(enclosures_page.address_proof_type_select).to_have_value("")

    with allure.step("Verify there is no 'Next: Premises Photos →' link"):
        expect(enclosures_page.next_premises_photos_link).to_have_count(0)
        expect(enclosures_page.next_links).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-473  Several documents at once — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-473")
@allure.story(STORY)
@allure.title("TC-473: Several documents chosen together are uploaded with one click")
def test_tc473_several_documents_at_once(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_several_at_once_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I choose PDFs for documents 2, 3 and 4 and click "Upload Documents" once
    Then  "3 file(s) uploaded successfully." is shown, all three are uploaded and the counter reads 2/2

    Notion: KAN-TC-473 | KAN-9 AC-4 | data: several_at_once
    """
    page, user = logged_in_enclosures_page
    data = enclosures_several_at_once_data

    with allure.step("Upload documents 2, 3 and 4 together"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify all three are uploaded and the counter reads 2/2"):
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))


# ---------------------------------------------------------------------------
# TC-474  Save & Log out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-474")
@allure.story(STORY)
@allure.title("TC-474: \"Save & Log out\" logs the user out so they can continue later")
def test_tc474_save_and_logout(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given my application is unpaid
    When  I click "Save & Log out" in the deadline banner and log in again
    Then  I am logged out, and after logging in I can open the Documents step again

    Notion: KAN-TC-474 | KAN-9 AC-8
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify the deadline banner and 'Save & Log out'"):
        expect(enclosures_page.deadline_banner).to_contain_text("to complete all steps and pay — deadline")
        expect(enclosures_page.save_and_logout_link).to_be_visible()

    with allure.step("Click 'Save & Log out'"):
        enclosures_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))

    with allure.step("Log in again and open the Documents step"):
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        enclosures_page.open()
        expect(enclosures_page.title).to_have_text(EnclosuresPage.TITLE)


# ---------------------------------------------------------------------------
# TC-851  Office address proof type — uploads document 2
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-851")
@allure.story(STORY)
@allure.title("TC-851: The office address proof is uploaded only after its document type is chosen, and the type is kept")
def test_tc851_address_proof_type(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_data: DocumentUploads
):
    """
    Given the office address proof (document 2) is not uploaded
    When  I upload a PDF for it with no type chosen, then choose "Rent / Leave and Licence Agreement" and upload
          it again, and reload the page
    Then  the first upload is refused with "Office Address Proof: choose the type of document from the list.",
          the second is saved, and after the reload the document is still uploaded with its type selected

    Portal 2.1.0 (17-Nov-2026) added the type select (``doctype3``); "Other" was added on 20-Nov-2026.

    Notion: KAN-TC-851 | KAN-9 AC-13, EC-7 | data: address_proof
    """
    page, user = logged_in_enclosures_page
    data = enclosures_address_proof_data
    counter_before = enclosures_page.uploaded_count()

    with allure.step("Verify the type select starts unselected"):
        expect(enclosures_page.address_proof_help).to_have_text(EnclosuresPage.ADDRESS_PROOF_HELP)
        expect(enclosures_page.address_proof_type_select).to_have_value("")
        _expect_not_uploaded(enclosures_page, 2)

    with allure.step("Upload document 2 with no type chosen"):
        enclosures_page.upload_documents(data.documents, address_proof_type=None)

    with allure.step("Verify the upload is refused and nothing is saved"):
        expect(page).to_have_url(ON_ENCLOSURES)
        expect(enclosures_page.messages).to_have_text([data.expected_error])
        _expect_not_uploaded(enclosures_page, 2)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(counter_before))

    with allure.step(f"Choose '{data.address_proof_type}' and upload document 2 again"):
        enclosures_page.upload_documents(data.documents, address_proof_type=data.address_proof_type)
        _record_uploads(enclosures_page, user)

    with allure.step("Verify document 2 is uploaded"):
        expect(enclosures_page.messages).to_have_text([EnclosuresPage.uploaded_message(1)])
        _expect_uploaded(enclosures_page, 2, data.documents[2])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(counter_before + 1))

    with allure.step("Reload and verify the document and its type are kept"):
        page.reload(wait_until="networkidle")
        _expect_uploaded(enclosures_page, 2, data.documents[2])
        expect(enclosures_page.address_proof_type_select).to_have_value(data.address_proof_type)


# ---------------------------------------------------------------------------
# TC-864  "Other" address proof type shows the name box
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-864")
@allure.story(STORY)
@allure.title("TC-864: Choosing \"Other\" as the address proof type shows a box for the name of the document")
def test_tc864_address_proof_other_box(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given the office address proof (document 2) is not uploaded
    When  I choose "Other" as its type, then "Electricity (Light) Bill"
    Then  a focused text box for the name of the document (placeholder, at most 80 characters) appears for
          "Other" and is hidden again for the other type

    Added 20-Nov-2026 (the "Other" type is new).

    Notion: KAN-TC-864 | KAN-9 AC-13
    """
    page, user = logged_in_enclosures_page
    other = enclosures_page.address_proof_other_input

    with allure.step("Verify no name box is shown before a type is chosen"):
        expect(enclosures_page.address_proof_type_select).to_have_value("")
        expect(other).to_be_hidden()

    with allure.step("Choose 'Other' — the name box appears and is focused"):
        enclosures_page.select_address_proof_type(EnclosuresPage.ADDRESS_PROOF_OTHER)
        expect(other).to_be_visible()
        expect(other).to_be_focused()
        expect(other).to_have_attribute("placeholder", EnclosuresPage.ADDRESS_PROOF_OTHER_PLACEHOLDER)
        expect(other).to_have_attribute("maxlength", str(EnclosuresPage.ADDRESS_PROOF_OTHER_MAXLENGTH))

    with allure.step(f"Choose '{EnclosuresPage.ADDRESS_PROOF_TYPES[0]}' — the name box is hidden"):
        enclosures_page.select_address_proof_type(EnclosuresPage.ADDRESS_PROOF_TYPES[0])
        expect(other).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-865  "Other" address proof needs the name of the document — uploads document 2
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-865")
@allure.story(STORY)
@allure.title("TC-865: An address proof of type \"Other\" is refused without the name of the document")
def test_tc865_address_proof_other_name_required(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_address_proof_other_data: DocumentUploads
):
    """
    Given only the PAN card from registration is on file
    When  I upload document 2 as "Other" with a blank name, then with "WB", then with "Water bill", and reload
    Then  the first two are refused with only 'Office Address Proof: you chose "Other" — type the name of the
          document (at least 3 characters).', nothing is saved and "Other" stays selected; the third is saved
          (2/2), and after the reload the select shows "Other" with "Water bill"

    On 20-Nov-2026 the blank-name refusal also showed "Office Address Proof: choose the type of document from
    the list." and reset the select (defect sheet, Documents tab #12); those checks are made after the rest
    of the case has run so the save is still covered.

    Notion: KAN-TC-865 | KAN-9 AC-13, EC-8 | data: address_proof_other
    """
    page, user = logged_in_enclosures_page
    data = enclosures_address_proof_other_data
    problems = []

    for name in data.invalid_other_names:
        with allure.step(f"Upload document 2 as 'Other' with the name '{name}' — refused"):
            enclosures_page.upload_documents(data.documents, address_proof_type=data.address_proof_type,
                                             address_proof_other=name)
            expect(page).to_have_url(ON_ENCLOSURES)
            expect(enclosures_page.messages.first).to_contain_text(data.expected_error)
            _expect_not_uploaded(enclosures_page, 2)
            expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(START))
            shown = enclosures_page.messages.all_inner_texts()
            if any(EnclosuresPage.ADDRESS_PROOF_TYPE_REQUIRED in text for text in shown):
                problems.append(f"name '{name}': the refusal also says "
                                f"'{EnclosuresPage.ADDRESS_PROOF_TYPE_REQUIRED}' although 'Other' was chosen")
            selected = enclosures_page.address_proof_type_select.input_value()
            if selected != data.address_proof_type:
                problems.append(f"name '{name}': the type select was reset to '{selected}' after the refusal")

    with allure.step(f"Upload document 2 as 'Other' named '{data.address_proof_other}' — saved"):
        enclosures_page.upload_documents(data.documents, address_proof_type=data.address_proof_type,
                                         address_proof_other=data.address_proof_other)
        _record_uploads(enclosures_page, user)
        expect(enclosures_page.messages).to_have_text([EnclosuresPage.uploaded_message(1)])
        _expect_uploaded(enclosures_page, 2, data.documents[2])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(ALL))

    with allure.step("Reload and verify the type and the name are kept"):
        page.reload(wait_until="networkidle")
        expect(enclosures_page.address_proof_type_select).to_have_value(data.address_proof_type)
        expect(enclosures_page.address_proof_other_input).to_be_visible()
        expect(enclosures_page.address_proof_other_input).to_have_value(data.address_proof_other)

    with allure.step("Verify the refusals named only the missing document name and kept 'Other' selected"):
        assert not problems, "Defect Documents #12 — refusing an 'Other' address proof without a name:\n" + "\n".join(problems)
