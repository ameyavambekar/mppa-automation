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
    """True unless the step is untouched: document 1 is the PAN card from registration and documents 2–4
    are empty (1/2). Otherwise records the user in the state store so it is skipped from now on — as
    ``completed`` / ``in_progress`` when something was uploaded here, and as ``in_progress`` for an agency
    registered before the PAN card was carried over (18-Nov-2026), which opens at 0/2."""
    others = [n for n in EnclosuresPage.DOCUMENTS if n != 1]
    if enclosures.has_registration_pan() and not any(enclosures.is_uploaded(n) for n in others):
        return False
    status = "completed" if enclosures.uploaded_count() == len(EnclosuresPage.MANDATORY) else "in_progress"
    store.mark_form_step_status(username=user.username, step="enclosures", status=status)
    return True


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def enclosures_page(page) -> EnclosuresPage:
    return EnclosuresPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_enclosures_page(page):
    """Yields (page, user) on the Documents step for a user whose Part F is saved and who
    has never uploaded a document here: document 1 is the PAN card carried over from
    registration, documents 2–4 are empty and the counter reads 1/2 (since 20-Nov-2026).
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
def enclosures_address_proof_only_data() -> DocumentUploads:
    """TC-380 / TC-381 / TC-382 / TC-395: document 2, the mandatory document not carried over."""
    return EnclosuresFactory.address_proof_only()


@pytest.fixture
def enclosures_optional_document_data() -> DocumentUploads:
    """TC-386 / TC-388 / TC-394 / TC-396: document 3."""
    return EnclosuresFactory.optional_document()


@pytest.fixture
def enclosures_replacement_data() -> DocumentUploads:
    """TC-387: a replacement for the PAN card from registration (document 1)."""
    return EnclosuresFactory.replacement()


@pytest.fixture
def enclosures_optional_only_data() -> DocumentUploads:
    """TC-383: optional documents 3 and 4."""
    return EnclosuresFactory.optional_only()


@pytest.fixture
def enclosures_several_at_once_data() -> DocumentUploads:
    """TC-473: documents 2, 3 and 4."""
    return EnclosuresFactory.several_at_once()


@pytest.fixture
def enclosures_address_proof_data() -> DocumentUploads:
    """KAN-TC-851: document 2 with and without its type."""
    return EnclosuresFactory.address_proof()


@pytest.fixture
def enclosures_address_proof_other_data() -> DocumentUploads:
    """KAN-TC-865: document 2 of type "Other" without, then with, the name of the document."""
    return EnclosuresFactory.address_proof_other()


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
