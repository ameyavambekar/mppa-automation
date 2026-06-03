import os

import pytest

from pages.admin.login_page import AdminLoginPage
from pages.admin.notices_page import AdminNoticesPage
from pages.login_page import LoginPage
from pages.home_page import HomePage
from test_data.notices_factory import NoticeData, NoticesFactory
from utils.state_store import TestStateStore, UserRecord

_DOC_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data", "documents")
VALID_PDF     = os.path.join(_DOC_DIR, "valid_doc.pdf")
INVALID_FILE  = os.path.join(_DOC_DIR, "invalid.docx")
OVERSIZED_PDF = os.path.join(_DOC_DIR, "oversized.pdf")


# ── Credential helpers ─────────────────────────────────────────────────────────

def _super_admin_or_skip() -> UserRecord:
    store = TestStateStore()
    username = os.getenv("ADMIN_SUPER_USERNAME")
    password = os.getenv("ADMIN_SUPER_PASSWORD")
    if username and password:
        store.record_user(role="super_admin", username=username, password=password)
        return store.get_user_by_username(username)
    user = store.get_any_super_admin()
    if user is not None:
        return user
    pytest.skip(
        "Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env "
        "(or seed a super_admin in the state store)."
    )


def _agency_user_or_skip() -> UserRecord:
    user = TestStateStore().get_any_agency_user()
    if user is None:
        pytest.skip("No agency user in state store — run pre-registration tests first.")
    return user


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_notices_page(page) -> AdminNoticesPage:
    return AdminNoticesPage(page)


@pytest.fixture
def logged_in_admin_notices_page(page) -> AdminNoticesPage:
    """Logs in as super admin then navigates directly to Notices Management."""
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    notices = AdminNoticesPage(page)
    notices.open()
    return notices


@pytest.fixture
def agency_home_page(page) -> HomePage:
    """Logs in as an agency user and returns the HomePage object."""
    agency = _agency_user_or_skip()
    base = os.getenv("MPPA_BASE_URL", "https://devmppa.sppuef.in/module/agency/auth")
    login = LoginPage(page)
    login.open()
    login.login(agency.username, agency.password)
    home = HomePage(page)
    home.open()
    return home


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def valid_notice_data() -> NoticeData:
    """TC-233 — valid mandatory fields, Alert badge."""
    return NoticesFactory.valid_notice()


@pytest.fixture
def active_notice_data() -> NoticeData:
    """TC-234 — active notice, should appear on public board."""
    return NoticesFactory.active_notice()


@pytest.fixture
def inactive_notice_data() -> NoticeData:
    """TC-235 — inactive notice, must NOT appear on public board."""
    return NoticesFactory.inactive_notice()


@pytest.fixture
def pinned_notice_data() -> NoticeData:
    """TC-236 — pinned + active notice, must appear at top of public board."""
    return NoticesFactory.pinned_notice()


@pytest.fixture
def notice_to_edit_data() -> NoticeData:
    """TC-238 — notice to be edited; paired with NoticesFactory.EDITED_TITLE."""
    return NoticesFactory.notice_to_edit()


@pytest.fixture
def notice_to_delete_data() -> NoticeData:
    """TC-239 — notice to be permanently deleted."""
    return NoticesFactory.notice_to_delete()


@pytest.fixture
def notice_with_attachment_data() -> NoticeData:
    """TC-240 — notice with a valid PDF attachment."""
    return NoticesFactory.notice_with_attachment(VALID_PDF)


@pytest.fixture
def blank_title_data() -> NoticeData:
    """TC-241 — blank title, expects validation error."""
    return NoticesFactory.blank_title()


@pytest.fixture
def invalid_attachment_data() -> NoticeData:
    """TC-242 — .docx attachment, expects format-error message."""
    return NoticesFactory.invalid_attachment(INVALID_FILE)


@pytest.fixture
def oversized_attachment_data() -> NoticeData:
    """TC-243 — >5 MB file attachment, expects size-error message."""
    return NoticesFactory.oversized_attachment(OVERSIZED_PDF)
