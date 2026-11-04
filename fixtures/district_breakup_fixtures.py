import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from fixtures.notifications_fixtures import submit_application
from pages.admin.district_breakup_page import AdminDistrictBreakupPage
from test_data.district_breakup_factory import DistrictBreakupFactory, DistrictCountChange


@pytest.fixture
def admin_district_breakup_page(page) -> AdminDistrictBreakupPage:
    return AdminDistrictBreakupPage(page)


@pytest.fixture
def logged_in_admin_district_breakup_page(page) -> AdminDistrictBreakupPage:
    """Logs in as the Super Admin and opens District breakup. Logs out on teardown (the browser context is
    shared across the session)."""
    _admin_login(page)
    report = AdminDistrictBreakupPage(page)
    report.open()
    yield report
    _admin_logout(page)


@pytest.fixture
def pay_for_new_application(page):
    """A function that submits one more application — an unpaid agency from the state store (or a newly
    built one) pays from Preview — then logs the Super Admin back in. Returns the agency. The application
    stays submitted: this cannot be undone."""
    def pay():
        user = submit_application(page)
        _admin_login(page)
        return user
    return pay


@pytest.fixture
def suspension_change() -> DistrictCountChange:
    return DistrictBreakupFactory.suspension()


@pytest.fixture
def new_submission_change() -> DistrictCountChange:
    return DistrictBreakupFactory.new_submission()
