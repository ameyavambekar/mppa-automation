import os

import pytest

from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.login_page import AdminLoginPage
from pages.admin.notices_page import AdminNoticesPage
from pages.login_page import LoginPage
from pages.home_page import HomePage
from pages.notice_board_page import NoticeBoardPage
from test_data.notices_factory import NoticeData, NoticesFactory
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL

_DOC_DIR = os.path.join(os.path.dirname(__file__), "..", "test_data", "documents")
VALID_PDF     = os.path.join(_DOC_DIR, "valid_doc.pdf")
INVALID_FILE  = os.path.join(_DOC_DIR, "invalid.docx")
OVERSIZED_PDF_MB = 6



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
    """Logs in as super admin then navigates directly to Notices Management.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin session cookie would otherwise persist and the
    next test's ``login.open()`` would redirect straight to the dashboard,
    breaking its login flow.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(admin.username, admin.password)
    if error:
        pytest.fail(f"Admin login as {admin.username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)
    notices = AdminNoticesPage(page)
    notices.open()
    yield notices
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def cleanup_notices(logged_in_admin_notices_page: AdminNoticesPage):
    """Teardown: deletes every notice the automation suite may have created (``NoticesFactory.all_test_titles``),
    so each run cleans up after itself. Shares the test's ``logged_in_admin_notices_page``."""
    yield logged_in_admin_notices_page
    logged_in_admin_notices_page.open()
    logged_in_admin_notices_page.delete_notices_matching(NoticesFactory.all_test_titles())


@pytest.fixture
def open_public_board(second_browser):
    """Factory that opens the public Notice Board (/module/notices.php) in a second browser with no session —
    the board needs no login — and returns its NoticeBoardPage. Call it again, or reload, to see later changes."""
    def _open() -> NoticeBoardPage:
        context = second_browser().new_context(viewport={"width": 1280, "height": 800})
        board = NoticeBoardPage(context.new_page())
        board.open()
        return board
    return _open


@pytest.fixture(scope="session")
def oversized_pdf(tmp_path_factory) -> str:
    """A valid-looking PDF of just over 6 MB (padding in a PDF comment), built once per session."""
    path = tmp_path_factory.mktemp("notices") / "oversized_6mb.pdf"
    head = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    pad = b"%" + b"0" * 1023 + b"\n"
    with open(path, "wb") as f:
        f.write(head)
        for _ in range(OVERSIZED_PDF_MB * 1024):
            f.write(pad)
        f.write(b"trailer<</Root 1 0 R>>\n%%EOF\n")
    return str(path)


@pytest.fixture
def agency_home_page(page) -> HomePage:
    """Logs in as an agency user and returns the HomePage object."""
    agency = _agency_user_or_skip()
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
def oversized_attachment_data(oversized_pdf) -> NoticeData:
    """TC-243 — 6 MB PDF, expects the client-side size message."""
    return NoticesFactory.oversized_attachment(oversized_pdf)


@pytest.fixture
def valid_pdf() -> str:
    return VALID_PDF


@pytest.fixture
def toggle_status_data() -> NoticeData:
    return NoticesFactory.toggle_status_notice()


@pytest.fixture
def toggle_pin_data() -> NoticeData:
    return NoticesFactory.toggle_pin_notice()


@pytest.fixture
def cancel_edit_data() -> NoticeData:
    return NoticesFactory.notice_to_cancel_edit()


@pytest.fixture
def blank_body_data() -> NoticeData:
    return NoticesFactory.blank_body()


@pytest.fixture
def over_max_lengths_data() -> NoticeData:
    return NoticesFactory.over_max_lengths()


@pytest.fixture
def badge_outside_list_data() -> NoticeData:
    return NoticesFactory.badge_outside_list()


@pytest.fixture
def special_text_data() -> NoticeData:
    return NoticesFactory.special_text()
