import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout, _super_admin_or_skip
from pages.admin.audit_log_page import AdminAuditLogPage
from test_data.admin_login_factory import AdminLoginData, AdminLoginFactory
from test_data.audit_log_factory import AuditLogData, AuditLogFactory
from utils.state_store import TestStateStore, UserRecord

# Action types whose event count the "actions write entries" tests compare before and after
COUNTED_ACTIONS = ("ADMIN_LOGIN", "ADMIN_LOGIN_FAILED", "LOGIN")


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_admin_audit_log_page(page) -> AdminAuditLogPage:
    """Logs in as the Super Admin and opens the Audit Log (no filters). Logs out on teardown
    (the browser context is shared across the session)."""
    _admin_login(page)
    audit = AdminAuditLogPage(page)
    audit.open()
    yield audit
    _admin_logout(page)


@pytest.fixture
def admin_login(page):
    """Callable that logs in to the Officer Console as the Super Admin (retrying a misread Security Code),
    for tests that log out and back in."""
    yield lambda: _admin_login(page)
    _admin_logout(page)


@pytest.fixture
def audit_counts_before(page) -> dict:
    """{action code: number of events} for COUNTED_ACTIONS, read as the Super Admin, who is then logged out
    so the test can perform the logins being audited."""
    _admin_login(page)
    audit = AdminAuditLogPage(page)
    counts = {}
    for action in COUNTED_ACTIONS:
        audit.open(action_f=action)
        counts[action] = audit.total_events()
    _admin_logout(page)
    page.context.clear_cookies()
    return counts


@pytest.fixture
def super_admin() -> UserRecord:
    return _super_admin_or_skip()


@pytest.fixture
def super_admin_wrong_password(super_admin: UserRecord) -> AdminLoginData:
    """One wrong password for the Super Admin — the 5th in a row would lock the account for 15 minutes."""
    return AdminLoginFactory.super_admin_wrong_password(super_admin)


@pytest.fixture
def paid_agency_for_login() -> UserRecord:
    """The most recently paid agency in the state store; logging in as it is audited as LOGIN
    (an unpaid agency's login is DRAFT_LOGIN)."""
    users = TestStateStore().get_agency_users_with_steps(["payment"])
    if not users:
        pytest.skip("No paid agency in the state store — run TC-513 (tests/test_preview.py) first.")
    return users[-1]


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def audit_action_types_data() -> AuditLogData:
    return AuditLogFactory.action_types()


@pytest.fixture
def audit_no_match_data() -> AuditLogData:
    return AuditLogFactory.no_match_search()


@pytest.fixture
def audit_admin_login_today_data() -> AuditLogData:
    return AuditLogFactory.admin_login_today()


@pytest.fixture
def audit_all_filters_data() -> AuditLogData:
    return AuditLogFactory.all_filters()


@pytest.fixture
def audit_unknown_date_data() -> AuditLogData:
    return AuditLogFactory.unknown_date_filter()


@pytest.fixture
def audit_unknown_action_data() -> AuditLogData:
    return AuditLogFactory.unknown_action_filter()


@pytest.fixture
def audit_html_search_data() -> AuditLogData:
    return AuditLogFactory.html_search()


@pytest.fixture
def audit_page_beyond_last_data() -> AuditLogData:
    return AuditLogFactory.page_beyond_last()
