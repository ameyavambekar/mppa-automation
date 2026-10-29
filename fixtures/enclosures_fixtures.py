import pytest

from config import FORMS_BASE
from pages.enclosures_page import EnclosuresPage
from pages.login_page import LoginPage
from test_data.enclosures_factory import DocumentUploads, EnclosuresFactory
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore


def _login_and_open_enclosures(page, user) -> EnclosuresPage:
    """Logs in and opens the Documents step."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    enclosures = EnclosuresPage(page)
    enclosures.open()
    page.wait_for_load_state("networkidle")
    return enclosures


def _already_uploaded(enclosures: EnclosuresPage, store: TestStateStore, user) -> bool:
    """True when the state store missed uploads (counter above 0 or any uploaded row);
    records them so the user is skipped from now on."""
    if enclosures.uploaded_count() == 0 and not any(enclosures.is_uploaded(n) for n in EnclosuresPage.DOCUMENTS):
        return False
    status = "completed" if enclosures.uploaded_count() == 6 else "in_progress"
    store.mark_form_step_status(username=user.username, step="enclosures", status=status)
    return True


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def enclosures_page(page) -> EnclosuresPage:
    return EnclosuresPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_enclosures_page(page):
    """Yields (page, user) on the Documents step for a user whose Part F is saved and
    who has never uploaded a document, so every row is empty and the counter is 0/6.
    Users with uploads are never used; when none is left, a new agency is built (see
    ``utils.agency_builder``)."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b", "part_c", "part_f"]):
        if user.steps.get("enclosures") in ("in_progress", "completed"):
            continue
        enclosures = _login_and_open_enclosures(page, user)
        if not _already_uploaded(enclosures, store, user):
            yield page, user
            return
    user = AgencyBuilder(page, store).build("part_f")
    _login_and_open_enclosures(page, user)
    yield page, user


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def enclosures_all_mandatory_data() -> DocumentUploads:
    """TC-380 / TC-395: documents 1–6."""
    return EnclosuresFactory.all_mandatory()


@pytest.fixture
def enclosures_first_document_data() -> DocumentUploads:
    """TC-381 / TC-386 / TC-388 / TC-394: document 1."""
    return EnclosuresFactory.first_document()


@pytest.fixture
def enclosures_replacement_data() -> DocumentUploads:
    """TC-387: document 1 and its replacement."""
    return EnclosuresFactory.replacement()


@pytest.fixture
def enclosures_optional_only_data() -> DocumentUploads:
    """TC-383: optional documents 7 and 8."""
    return EnclosuresFactory.optional_only()


@pytest.fixture
def enclosures_first_three_data() -> DocumentUploads:
    """TC-396: documents 1–3."""
    return EnclosuresFactory.first_three()


@pytest.fixture
def enclosures_several_at_once_data() -> DocumentUploads:
    """TC-473: documents 1, 2 and 7."""
    return EnclosuresFactory.several_at_once()


@pytest.fixture
def enclosures_not_pdf_data() -> DocumentUploads:
    """TC-384: JPG, PNG and DOCX files."""
    return EnclosuresFactory.not_pdf()


@pytest.fixture
def enclosures_too_large_data() -> DocumentUploads:
    """TC-385: a 3 MB PDF."""
    return EnclosuresFactory.too_large()


@pytest.fixture
def enclosures_too_small_data() -> DocumentUploads:
    """TC-397: PDFs under 10 KB."""
    return EnclosuresFactory.too_small()
