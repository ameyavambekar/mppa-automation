import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from pages.admin.licenses_page import AdminLicensesPage
from test_data.licenses_factory import CertificateActionData, LicenseData, LicensesFactory


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_licenses_page(page) -> AdminLicensesPage:
    return AdminLicensesPage(page)


@pytest.fixture
def logged_in_admin_licenses_page(page) -> AdminLicensesPage:
    """Logs in as the Super Admin and opens Licences & certificates on the Approved chip.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin session cookie would otherwise persist and the
    next test's ``login.open()`` would redirect straight to the dashboard,
    breaking its login flow.
    """
    _admin_login(page)
    licenses = AdminLicensesPage(page)
    licenses.open(status="all")
    yield licenses
    _admin_logout(page)


def _restore_certificate(lp: AdminLicensesPage, agency_name: str, valid_from: str, valid_upto: str) -> None:
    """Lifts a suspension or reinstates an expired / cancelled certificate (whenever the row offers Lift
    suspension or Reinstate — a renewed certificate that an officer had expired still offers Reinstate),
    then re-issues the original validity dates if they changed."""
    lp.open(status="all")
    actions = lp.row_action_labels(agency_name)
    if "Lift suspension" in actions:
        lp.certificate_action(agency_name, "lift", "Automation cleanup — lifting the test suspension.")
    elif "Reinstate" in actions:
        lp.certificate_action(agency_name, "reinstate", "Automation cleanup — reinstating the test certificate.")
    if lp.get_row_validity_dates(agency_name) != (valid_from, valid_upto):
        lp.renew_license(agency_name, valid_from=valid_from, valid_upto=valid_upto,
                         notes="Automation cleanup — restoring original validity dates.")


@pytest.fixture
def certificate_restorer(logged_in_admin_licenses_page: AdminLicensesPage):
    """Restores an agency's certificate after a test that changes it.

    The test calls ``certificate_restorer(agency_name)`` BEFORE changing anything: the agency's Valid From /
    Valid Upto are read from its row. On teardown the certificate is made active again (lift / reinstate)
    and the original window re-issued, so the dev data is left as found (History keeps the test's entries).
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
            _restore_certificate(lp, agency_name, valid_from, valid_upto)
        except Exception as e:  # leave the next agency's restore a chance
            print(f"[certificate_restorer] Could not restore {agency_name}: {e}")


@pytest.fixture
def scratch_agency(logged_in_admin_licenses_page: AdminLicensesPage, certificate_restorer) -> str:
    """An agency with an Active certificate that the test may suspend, expire, cancel or renew — the last
    Active one in name order, so the first rows (which other modules' tests look at) are left alone.
    Restored on teardown by ``certificate_restorer``."""
    active = logged_in_admin_licenses_page.agencies_with_status("active")
    if not active:
        pytest.skip("No agency with an Active certificate on Licences & certificates.")
    agency = active[-1]
    certificate_restorer(agency)
    return agency


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def quick_duration_data() -> LicenseData:
    """TC-261 — base Valid From for exercising the +1/+2/+3/+5 year buttons."""
    return LicensesFactory.quick_duration_base()


@pytest.fixture
def valid_renewal_data() -> LicenseData:
    """TC-262 / TC-639 — renewal from today for 5 years."""
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
    """TC-265 — Valid Upto earlier than Valid From."""
    return LicensesFactory.upto_before_from()


@pytest.fixture
def missing_agency_data() -> LicenseData:
    """TC-266 — dates filled but no agency selected."""
    return LicensesFactory.missing_agency()


@pytest.fixture
def expiring_boundary_data() -> dict:
    """TC-267 — windows expiring on exactly the 30th and 31st day."""
    return {
        30: LicensesFactory.expiring_in_30_days(),
        31: LicensesFactory.expiring_in_31_days(),
    }


@pytest.fixture
def no_match_search() -> str:
    """TC-640 — search text no agency has."""
    return LicensesFactory.no_match_search()


@pytest.fixture
def suspension_data() -> CertificateActionData:
    return LicensesFactory.suspension()


@pytest.fixture
def short_suspension_data() -> CertificateActionData:
    return LicensesFactory.short_suspension()


@pytest.fixture
def lift_data() -> CertificateActionData:
    return LicensesFactory.lift()


@pytest.fixture
def expiry_data() -> CertificateActionData:
    return LicensesFactory.expiry()


@pytest.fixture
def cancellation_data() -> CertificateActionData:
    return LicensesFactory.cancellation()


@pytest.fixture
def reinstatement_data() -> CertificateActionData:
    return LicensesFactory.reinstatement()


@pytest.fixture
def reason_rules_data() -> dict:
    """TC-635 — a reason one character short, and one exactly at the minimum."""
    return {"short": LicensesFactory.reason_one_short(), "minimum": LicensesFactory.reason_minimum()}
