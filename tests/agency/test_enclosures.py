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
    status = "completed" if enclosures.uploaded_count() == 6 else "in_progress"
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
# TC-380  All six mandatory documents — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-380")
@allure.story(STORY)
@allure.title("TC-380: Uploading all six mandatory documents brings the counter to 6/6")
def test_tc380_all_mandatory_documents(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_all_mandatory_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I choose a PDF for each of documents 1–6 and click "Upload Documents"
    Then  "6 file(s) uploaded successfully." is shown, the counter reads 6/6 with the bar full,
          every mandatory row shows ✓, its file name and "View ↗",
          and a "Next: Premises Photos →" link appears

    Notion: KAN-TC-380 | KAN-9 AC-2, AC-4, AC-11 | data: all_mandatory
    """
    page, user = logged_in_enclosures_page
    data = enclosures_all_mandatory_data

    with allure.step("Upload documents 1–6"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify the counter reads 6/6 with the bar full"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(6))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*100%"))

    for number, path in data.documents.items():
        with allure.step(f"Verify document {number} is uploaded"):
            _expect_uploaded(enclosures_page, number, path)

    with allure.step("Verify 'Next: Premises Photos →' links to premises.php"):
        expect(enclosures_page.next_premises_photos_link).to_be_visible()
        expect(enclosures_page.next_premises_photos_link).to_have_attribute("href", re.compile(r"premises\.php$"))


# ---------------------------------------------------------------------------
# TC-381  Counter changes only after uploading — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-381")
@allure.story(STORY)
@allure.title("TC-381: The mandatory counter changes only after \"Upload Documents\", one step per mandatory document")
def test_tc381_counter_after_upload(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_first_document_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I choose document 1 without uploading, upload it, then upload document 2
    Then  the counter stays 0/6 until "Upload Documents", then reads 1/6, then 2/6

    Notion: KAN-TC-381 | KAN-9 AC-2 | data: first_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_first_document_data.documents[1]

    with allure.step("Verify the counter reads 0/6 with an empty bar"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*0%"))

    with allure.step("Choose document 1 without uploading — the counter stays 0/6"):
        enclosures_page.choose_document(1, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))

    with allure.step("Click 'Upload Documents' — 1/6"):
        enclosures_page.click_upload()
        _record_uploads(enclosures_page, user)
        expect(enclosures_page.messages).to_have_text([EnclosuresPage.uploaded_message(1)])
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(1))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*17%"))

    with allure.step("Upload document 2 — 2/6"):
        _upload(enclosures_page, page, user, {2: path})
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(2))


# ---------------------------------------------------------------------------
# TC-382  Premises Photos locked until 6/6 — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-382")
@allure.story(STORY)
@allure.title("TC-382: The Premises Photos step is locked until all six mandatory documents are uploaded")
def test_tc382_premises_photos_locked_until_six(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_all_mandatory_data: DocumentUploads
):
    """
    Given fewer than six mandatory documents are uploaded
    When  I open Premises Photos by URL, log out and back in, then upload the remaining mandatory documents
    Then  I am sent back to the Documents step and login lands there, until 6/6 shows
          "Next: Premises Photos →", which opens the Premises Photos step

    Notion: KAN-TC-382 | KAN-9 AC-11 | data: all_mandatory
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify there is no 'Next: Premises Photos →' link"):
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

    with allure.step("Upload the six mandatory documents — 6/6 and 'Next: Premises Photos →'"):
        _upload(enclosures_page, page, user, enclosures_all_mandatory_data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(6))
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
@allure.title("TC-383: Optional documents 7–8 upload without changing the mandatory counter")
def test_tc383_optional_documents(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_optional_only_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I upload documents 7 and 8 only
    Then  both are shown as uploaded and the counter still reads 0/6

    Notion: KAN-TC-383 | KAN-9 AC-2, AC-6 | data: optional_only
    """
    page, user = logged_in_enclosures_page
    data = enclosures_optional_only_data

    with allure.step("Upload documents 7 and 8"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify both are uploaded and the counter still reads 0/6"):
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))


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
    When  I choose a JPG for document 3, a PNG for document 1 and a DOCX for document 8
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
    Then  "File is larger than 2 MB — please upload a smaller PDF." is shown and the file is removed

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
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_first_document_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I upload document 1, open Part F and come back
    Then  document 1 still shows ✓, its file name and "View ↗" (opening a new tab), and the counter reads 1/6

    Notion: KAN-TC-386 | KAN-9 AC-9 | data: first_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_first_document_data.documents[1]

    with allure.step("Upload document 1"):
        _upload(enclosures_page, page, user, {1: path})
        _expect_uploaded(enclosures_page, 1, path)

    with allure.step("Open Part F, then come back to the Documents step"):
        PartFPage(page).open()
        enclosures_page.open()
        page.wait_for_load_state("networkidle")

    with allure.step("Verify document 1 is still uploaded and the counter reads 1/6"):
        _expect_uploaded(enclosures_page, 1, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(1))
        expect(enclosures_page.view_link(1)).to_have_attribute("href", re.compile(r"serve_enclosure\.php"))


# ---------------------------------------------------------------------------
# TC-387  Replacing a document — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-387")
@allure.story(STORY)
@allure.title("TC-387: Uploading a new file to an uploaded document replaces it")
def test_tc387_replace_document(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_replacement_data: DocumentUploads
):
    """
    Given document 1 is uploaded
    When  I choose a PDF with a different name for it and click "Upload Documents"
    Then  document 1 shows the new file name, "View ↗" points to a new upload, and the counter stays 1/6

    Notion: KAN-TC-387 | KAN-9 AC-9 | data: replacement
    """
    page, user = logged_in_enclosures_page
    data = enclosures_replacement_data

    with allure.step("Precondition: upload document 1"):
        _upload(enclosures_page, page, user, data.documents)
        old_link = enclosures_page.view_link(1).get_attribute("href")

    with allure.step("Verify the chooser is still available on the uploaded row"):
        _expect_uploaded(enclosures_page, 1, data.documents[1])
        expect(enclosures_page.file_input(1)).to_be_enabled()

    with allure.step(f"Upload {os.path.basename(data.replacement)} for document 1"):
        _upload(enclosures_page, page, user, {1: data.replacement})

    with allure.step("Verify the new file replaced the old one"):
        _expect_uploaded(enclosures_page, 1, data.replacement)
        expect(enclosures_page.view_link(1)).not_to_have_attribute("href", old_link)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(1))


# ---------------------------------------------------------------------------
# TC-388  "← Part F" — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-388")
@allure.story(STORY)
@allure.title("TC-388: \"← Part F\" returns to Part F with its data intact and keeps the uploaded documents")
def test_tc388_back_to_part_f(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_first_document_data: DocumentUploads
):
    """
    Given document 1 is uploaded
    When  I click "← Part F", then open the Documents step again
    Then  Part F opens without a dialog with its saved Place, and document 1 is still uploaded

    Notion: KAN-TC-388 | KAN-9 AC-7 | data: first_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_first_document_data.documents[1]
    part_f = PartFPage(page)

    with allure.step("Precondition: upload document 1"):
        _upload(enclosures_page, page, user, {1: path})

    with allure.step("Click '← Part F'"):
        message = enclosures_page.click_and_handle_alert(enclosures_page.back_to_part_f_link)
        assert message == "", f"Unexpected dialog: {message}"

    with allure.step("Verify Part F opens with its saved values"):
        expect(page).to_have_url(re.compile(rf"{re.escape(PART_F_URL)}"))
        expect(part_f.title).to_contain_text("Certificates, Licences & Signature")
        expect(part_f.place_select).not_to_have_value("")

    with allure.step("Open the Documents step again — document 1 is still uploaded"):
        enclosures_page.open()
        _expect_uploaded(enclosures_page, 1, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(1))


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
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))


# ---------------------------------------------------------------------------
# TC-394  Same file twice — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-394")
@allure.story(STORY)
@allure.title("TC-394: Uploading the same file twice to the same document is accepted as a replacement")
def test_tc394_same_file_twice(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_first_document_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I upload the same PDF for document 1 twice
    Then  each upload succeeds, document 1 stays uploaded and the counter stays 1/6

    Notion: KAN-TC-394 | KAN-9 EC-6 | data: first_document
    """
    page, user = logged_in_enclosures_page
    path = enclosures_first_document_data.documents[1]

    for attempt in ("first", "second"):
        with allure.step(f"Upload {os.path.basename(path)} for document 1 ({attempt} time)"):
            _upload(enclosures_page, page, user, {1: path})
            _expect_uploaded(enclosures_page, 1, path)
            expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(1))


# ---------------------------------------------------------------------------
# TC-395  Training certificate optional regardless of Part C — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-395")
@allure.story(STORY)
@allure.title("TC-395: The training certificate is shown as optional even when Part C says no training")
def test_tc395_training_certificate_optional(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_all_mandatory_data: DocumentUploads
):
    """
    Given Part C was saved with "Does the agency provide training?" = No
    When  I open the Documents step and upload documents 1–6 only
    Then  document 7 is an optional row and the counter reads 6/6 without it

    Notion: KAN-TC-395 | KAN-9 EC-5 | data: all_mandatory
    """
    page, user = logged_in_enclosures_page
    part_c = PartCPage(page)

    with allure.step("Precondition: Part C was saved with training = No"):
        part_c.open()
        page.wait_for_load_state("networkidle")
        if not part_c.training_radio("0").is_checked():
            pytest.skip(f"{user.username}'s Part C was saved with training = Yes")
        enclosures_page.open()

    with allure.step("Verify document 7 is shown as optional"):
        expect(enclosures_page.document_title(7)).to_have_text(EnclosuresPage.DOCUMENTS[7][1])
        expect(enclosures_page.required_marker(7)).to_have_count(0)

    with allure.step("Upload documents 1–6 only — 6/6"):
        _upload(enclosures_page, page, user, enclosures_all_mandatory_data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(6))
        _expect_not_uploaded(enclosures_page, 7)


# ---------------------------------------------------------------------------
# TC-396  Uploads persist across sessions — uploads
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-396")
@allure.story(STORY)
@allure.title("TC-396: After logging out and back in, the counter and upload states are as left")
def test_tc396_uploads_persist_across_sessions(
    enclosures_page: EnclosuresPage, logged_in_enclosures_page, enclosures_first_three_data: DocumentUploads
):
    """
    Given no document has been uploaded
    When  I upload documents 1–3, click "Save & Log out", log in again and open the Documents step
    Then  documents 1–3 are uploaded, 4–6 are not, and the counter reads 3/6

    Notion: KAN-TC-396 | KAN-9 AC-9 | data: first_three
    """
    page, user = logged_in_enclosures_page
    data = enclosures_first_three_data

    with allure.step("Upload documents 1–3"):
        _upload(enclosures_page, page, user, data.documents)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(3))

    with allure.step("Click 'Save & Log out', log in again and open the Documents step"):
        enclosures_page.save_and_logout()
        expect(page).to_have_url(re.compile(r"/auth/login\.php\?reason=logged_out"))
        LoginPage(page).login(user.username, user.password)
        page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
        enclosures_page.open()

    with allure.step("Verify documents 1–3 are uploaded and 4–6 are not"):
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        for number in (4, 5, 6):
            _expect_not_uploaded(enclosures_page, number)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(3))


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
    When  I choose a 298-byte PDF, then a 0-byte PDF, for document 5
    Then  each shows "File is smaller than 10 KB — upload a clear, complete scan." and is removed

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
@allure.title("TC-471: The Documents step shows the heading, note, counter, eight documents and upload button")
def test_tc471_page_layout(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given I have saved Part F
    When  I open the Documents step
    Then  the heading, subtitle, "← Part F", progress bar, note, counter, eight documents in three groups
          and the "Upload Documents" button are shown

    Notion: KAN-TC-471 | KAN-9 AC-1
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
        expect(enclosures_page.note).to_contain_text("Tip: photos (e.g. the office photograph) can be converted to PDF")
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))

    with allure.step("Verify the groups and the eight documents"):
        expect(enclosures_page.group_headings).to_have_text(list(EnclosuresPage.GROUPS))
        expect(enclosures_page.document_rows).to_have_count(8)
        for number, (_, title, mandatory) in EnclosuresPage.DOCUMENTS.items():
            expect(enclosures_page.document_title(number)).to_have_text(title)
            expect(enclosures_page.required_marker(number)).to_have_count(1 if mandatory else 0)
            expect(enclosures_page.document_hint(number)).to_have_text(EnclosuresPage.FILE_HINT)

    with allure.step("Verify the upload button"):
        expect(enclosures_page.upload_button).to_have_text("Upload Documents")


# ---------------------------------------------------------------------------
# TC-472  Default state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-472")
@allure.story(STORY)
@allure.title("TC-472: The Documents step opens with 0/6 uploaded and every document empty")
def test_tc472_default_state(enclosures_page: EnclosuresPage, logged_in_enclosures_page):
    """
    Given no document has ever been uploaded
    When  I open the Documents step
    Then  the counter reads 0/6 with an empty bar, each row shows its number with no file,
          and there is no "Next: Premises Photos →" link

    Notion: KAN-TC-472 | KAN-9 AC-2
    """
    page, user = logged_in_enclosures_page

    with allure.step("Verify the counter"):
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(0))
        expect(enclosures_page.progress_fill).to_have_attribute("style", re.compile(r"width:\s*0%"))

    with allure.step("Verify every row is empty"):
        for number in EnclosuresPage.DOCUMENTS:
            _expect_not_uploaded(enclosures_page, number)

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
    Given no document has been uploaded
    When  I choose PDFs for documents 1, 2 and 7 and click "Upload Documents" once
    Then  "3 file(s) uploaded successfully." is shown, all three are uploaded and the counter reads 2/6

    Notion: KAN-TC-473 | KAN-9 AC-4 | data: several_at_once
    """
    page, user = logged_in_enclosures_page
    data = enclosures_several_at_once_data

    with allure.step("Upload documents 1, 2 and 7 together"):
        _upload(enclosures_page, page, user, data.documents)

    with allure.step("Verify all three are uploaded and the counter reads 2/6"):
        for number, path in data.documents.items():
            _expect_uploaded(enclosures_page, number, path)
        expect(enclosures_page.mandatory_counter).to_have_text(EnclosuresPage.counter_text(2))


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
