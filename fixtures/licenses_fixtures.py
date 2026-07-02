import os

import pytest

from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.login_page import AdminLoginPage
from test_data.licenses_factory import LicenseData, LicensesFactory
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL



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


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_licenses_page(page) -> AdminLicensesPage:
    return AdminLicensesPage(page)


@pytest.fixture
def logged_in_admin_licenses_page(page) -> AdminLicensesPage:
    """Logs in as super admin then navigates directly to License Management.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin session cookie would otherwise persist and the
    next test's ``login.open()`` would redirect straight to the dashboard,
    breaking its login flow.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    licenses = AdminLicensesPage(page)
    licenses.open()
    yield licenses
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def license_restorer(logged_in_admin_licenses_page: AdminLicensesPage):
    """Restores an agency's validity dates after a date-mutating test.

    The test calls ``license_restorer(agency_name)`` BEFORE changing anything:
    the agency's current Valid From / Valid Upto are captured from its table
    row. On teardown each registered agency is re-issued its original window
    via the row's Renew flow, so date-mutating tests (TC-262, TC-264, TC-267)
    leave the dev data as they found it. License numbers entered by a test are
    not reverted — only the validity dates drive status/tiles.
    """
    lp = logged_in_admin_licenses_page
    originals = []

    def _register(agency_name: str):
        valid_from, valid_upto = lp.get_row_validity_dates(agency_name)
        originals.append((agency_name, valid_from, valid_upto))
        return valid_from, valid_upto

    yield _register

    for agency_name, valid_from, valid_upto in originals:
        try:
            lp.open()
            lp.renew_license(
                agency_name,
                valid_from=valid_from,
                valid_upto=valid_upto,
                notes="Automation cleanup — restoring original validity dates.",
            )
        except Exception:
            pass


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def quick_duration_data() -> LicenseData:
    """TC-261 — base Valid From for exercising the +1/+2/+3/+5 year buttons."""
    return LicensesFactory.quick_duration_base()


@pytest.fixture
def valid_renewal_data() -> LicenseData:
    """TC-262 — complete, valid renewal (today → today + 5 years)."""
    return LicensesFactory.valid_renewal()


@pytest.fixture
def days_left_color_data() -> dict:
    """TC-264 — validity windows for the green / amber / red bar bands."""
    return {
        "green": LicensesFactory.green_bar_validity(),
        "amber": LicensesFactory.amber_bar_validity(),
        "expired": LicensesFactory.expired_validity(),
    }


@pytest.fixture
def upto_before_from_data() -> LicenseData:
    """TC-265 — Valid Upto earlier than Valid From, expects validation error."""
    return LicensesFactory.upto_before_from()


@pytest.fixture
def missing_agency_data() -> LicenseData:
    """TC-266 — dates filled but no agency selected, expects validation error."""
    return LicensesFactory.missing_agency()


@pytest.fixture
def expiring_boundary_data() -> dict:
    """TC-267 — windows expiring on exactly the 30th and 31st day."""
    return {
        30: LicensesFactory.expiring_in_30_days(),
        31: LicensesFactory.expiring_in_31_days(),
    }
