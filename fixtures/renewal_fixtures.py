"""Fixtures for Licence Renewal: the agency's renewal.php (KAN-37) and the officer's Renewal applications (KAN-51).

Where an agency stands is read live from its renewal page (``LicenseRenewalPage.state``): the state store's
``status_data`` is rewritten by the console sync, so it cannot hold the renewal stage. Candidates are the
state-store agencies with a certificate (approved / licence_expired / suspended).

The renewal chain is irreversible on dev, so it only runs with RUN_RENEWAL_TESTS=true:
- expire a certificate (officer, Licences & certificates → Expire) when no agency has the form open;
- submit a renewal (KAN-TC-405, or to provide a pending one);
- reject it (KAN-TC-829) — the form opens again, so the agency can file another;
- approve it (KAN-TC-414).
A renewed agency can be expired again, so the chain keeps itself going. Only agencies not parked at a
Compliance & Appeals Map state are ever changed; parked ones are read only.
"""

import os
from datetime import datetime, timedelta, timezone

import allure
import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from pages.admin.licenses_page import AdminLicensesPage
from pages.admin.renewals_page import AdminRenewalsPage
from pages.license_renewal_page import LicenseRenewalPage
from pages.login_page import LoginPage
from test_data.admin_users_factory import OfficersFactory
from test_data.renewal_factory import RenewalDecisionData, RenewalData, RenewalFactory, RenewalScope
from utils.renewal_sync import record_rows
from utils.state_store import TestStateStore

RUN_ENV = "RUN_RENEWAL_TESTS"
CERTIFIED = ("approved", "licence_expired", "suspended")
EXPIRE_REASON = "Automation — certificate expired to test the renewal flow (KAN-37)."
NOT_ALLOWED = (f"set {RUN_ENV}=true to let the tests expire a certificate / submit / approve a renewal "
               f"(irreversible on dev)")


IST = timezone(timedelta(hours=5, minutes=30))
# renewal.php state → the status of the agency's newest recorded renewal that suggests it
STORE_HINT = {"pending": "pending", "renewed": "renewed", "form": "rejected"}


def _renewal_allowed() -> bool:
    return os.getenv(RUN_ENV, "false").lower() == "true"


def _login_agency(page, user) -> None:
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_load_state("networkidle")


def _renewal_state(page, user) -> str:
    """Logs in as ``user``, opens renewal.php and returns its state (see ``LicenseRenewalPage.state``)."""
    _login_agency(page, user)
    renewal = LicenseRenewalPage(page)
    renewal.open()
    return renewal.state()


def _certified_agencies(include_parked: bool) -> list:
    return TestStateStore().get_agency_users_in_status(CERTIFIED, include_parked=include_parked)


def _find(page, states, include_parked: bool = True, newest_first: bool = False):
    """The first certified agency whose renewal page is in one of ``states`` — left logged in on renewal.php.
    Agencies whose newest recorded renewal (state store) suggests one of ``states`` are tried first; the
    renewal page always decides."""
    users = _certified_agencies(include_parked)
    users = list(reversed(users)) if newest_first else users
    store = TestStateStore()
    hinted = {u.username for state in states if state in STORE_HINT
              for u in store.get_agency_users_with_renewal(STORE_HINT[state], include_parked)}
    for user in sorted(users, key=lambda u: u.username not in hinted):
        if _renewal_state(page, user) in states:
            return user
    return None


def _expire_certificate(page, user) -> None:
    with allure.step(f"Expire the certificate of {user.agency_name} (Officer Console)"):
        page.context.clear_cookies()
        _admin_login(page)
        try:
            licenses = AdminLicensesPage(page)
            licenses.open(status="all")
            licenses.certificate_action(user.agency_name, "expire", EXPIRE_REASON)
        finally:
            _admin_logout(page)
        TestStateStore().record_agency_status(username=user.username, status="licence_expired")


def _submit_renewal(page, user) -> None:
    with allure.step(f"Submit a renewal (No / No, declared) as {user.username}"):
        renewal = LicenseRenewalPage(page)
        renewal.open()
        renewal.fill_form(RenewalFactory.no_changes())
        renewal.submit()
        if not renewal.success_box.count():
            pytest.fail(f"Renewal for {user.username} was not submitted: {renewal.error_messages()}")
        TestStateStore().record_renewal(
            number=int(renewal.submitted_number()), registration_no=user.application_id, status="pending",
            username=user.username, filed_on=datetime.now(IST).date().isoformat(),
            changes_made="no", cases_pending="no")


def _expired_agency(page):
    """An agency with the renewal form open; expires a non-parked one (newest first) when allowed."""
    user = _find(page, ("form",))
    if user:
        return user
    if not _renewal_allowed():
        pytest.skip(f"No agency has the renewal form open (expired certificate, no renewal pending) — {NOT_ALLOWED}.")
    user = _find(page, ("not_open", "renewed"), include_parked=False, newest_first=True)
    if not user:
        pytest.skip("No non-parked agency with a valid certificate to expire — approve another application first.")
    _expire_certificate(page, user)
    if _renewal_state(page, user) != "form":
        pytest.fail(f"The renewal form did not open for {user.username} after its certificate was expired.")
    return user


def _pending_agency(page, include_parked: bool = True):
    """An agency with a renewal pending; submits one for an expired non-parked agency when allowed."""
    user = _find(page, ("pending",), include_parked=include_parked)
    if user:
        return user
    if not _renewal_allowed():
        pytest.skip(f"No agency has a renewal pending — {NOT_ALLOWED}.")
    user = _expired_agency(page)
    _submit_renewal(page, user)
    return user


# ── Page objects ──────────────────────────────────────────────────────────────

@pytest.fixture
def renewal_page(page) -> LicenseRenewalPage:
    return LicenseRenewalPage(page)


@pytest.fixture
def admin_renewals_page(page) -> AdminRenewalsPage:
    return AdminRenewalsPage(page)


# ── Gate ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def renewal_chain_allowed():
    """Skips unless RUN_RENEWAL_TESTS=true: the test submits or approves a renewal (irreversible on dev)."""
    if not _renewal_allowed():
        pytest.skip(f"Submits or decides a renewal — {NOT_ALLOWED}.")


# ── Agency states ─────────────────────────────────────────────────────────────

@pytest.fixture
def renewal_agency_login(page):
    """Logs in as the given agency (a state-store user); the caller then opens the page it needs."""
    return lambda user: _login_agency(page, user)


@pytest.fixture
def expired_renewal_agency(page):
    """(page, user) on renewal.php with the Renewal application form shown — an expired certificate with no
    renewal pending. With RUN_RENEWAL_TESTS=true a certificate is expired when there is none."""
    return page, _expired_agency(page)


@pytest.fixture
def pending_renewal_agency(page):
    """(page, user) on renewal.php for an agency whose renewal is with the department. With
    RUN_RENEWAL_TESTS=true one is submitted when there is none."""
    return page, _pending_agency(page)


@pytest.fixture
def renewed_renewal_agency(page):
    """(page, user) on renewal.php for an agency whose renewal was approved."""
    user = _find(page, ("renewed",))
    if not user:
        pytest.skip("No agency has an approved renewal — run KAN-TC-414 (RUN_RENEWAL_TESTS=true).")
    return page, user


@pytest.fixture
def not_open_renewal_agency(page):
    """(page, user) on renewal.php for an agency whose certificate is valid for more than 90 more days and that
    has never filed a renewal (else one whose renewal was approved)."""
    user = _find(page, ("not_open",)) or _find(page, ("renewed",))
    if not user:
        pytest.skip("No agency with a certificate valid for more than 90 more days.")
    return page, user


@pytest.fixture
def no_certificate_agencies(page):
    """(page, [agency in Desktop scrutiny, refused agency]) — neither has a certificate. Not logged in yet."""
    store = TestStateStore()
    users = [store.get_agency_user_in_status("desktop_scrutiny"), store.get_agency_user_in_status("rejected")]
    if not all(users):
        pytest.skip("Needs a state-store agency in Desktop scrutiny and a refused one.")
    return page, users


@pytest.fixture
def agency_without_form_i(page):
    """(page, user) logged in as an agency that registered but has not submitted Form-I."""
    user = TestStateStore().get_agency_user_with_no_form()
    if not user:
        pytest.skip("No state-store agency without Form-I — register one (tests/test_pre_registration.py).")
    _login_agency(page, user)
    return page, user


# ── Officer side ──────────────────────────────────────────────────────────────

@pytest.fixture
def officer_pending_renewal(page):
    """(AdminRenewalsPage on Pending decision, agency user) for an agency whose renewal is pending, logged in as
    the Super Admin. A renewal is submitted first only when none is pending and RUN_RENEWAL_TESTS=true.
    Logs the officer out on teardown."""
    user = _pending_agency(page)
    page.context.clear_cookies()
    _admin_login(page)
    renewals = AdminRenewalsPage(page)
    renewals.open(tab="submitted")
    yield renewals, user
    _admin_logout(page)


@pytest.fixture
def officer_pending_renewal_to_decide(page, renewal_chain_allowed):
    """Like ``officer_pending_renewal``, but only for a non-parked agency — the test decides the renewal."""
    user = _pending_agency(page, include_parked=False)
    page.context.clear_cookies()
    _admin_login(page)
    renewals = AdminRenewalsPage(page)
    renewals.open(tab="submitted")
    yield renewals, user
    _admin_logout(page)


@pytest.fixture
def renewal_admin_licenses_page(page) -> AdminLicensesPage:
    return AdminLicensesPage(page)


@pytest.fixture
def officer_renewals_page(page) -> AdminRenewalsPage:
    """Renewal applications (default tab) as the Super Admin. Logs out on teardown."""
    page.context.clear_cookies()
    _admin_login(page)
    renewals = AdminRenewalsPage(page)
    renewals.open()
    yield renewals
    _admin_logout(page)


@pytest.fixture
def decided_renewals(officer_renewals_page: AdminRenewalsPage):
    """(AdminRenewalsPage, every row of the All tab) as the Super Admin; skips unless at least one renewal has
    been approved and one rejected. The rows are recorded in the state store on the way."""
    renewals = officer_renewals_page
    counts = renewals.tab_counts()
    if not counts["approved"] or not counts["rejected"]:
        pytest.skip(f"Needs a renewed and a rejected renewal application (counts: {counts}).")
    renewals.open(tab="all")
    rows = renewals.row_data()
    record_rows(rows)
    return renewals, rows


@pytest.fixture
def renewal_scope_rows(logged_in_officers_page) -> list[dict]:
    """Every renewal application row (All tab), read as the Super Admin in the officer fixtures' session."""
    renewals = AdminRenewalsPage(logged_in_officers_page.page)
    renewals.open(tab="all")
    rows = renewals.row_data()
    logged_in_officers_page.open()          # back to Officers & Access: new_officers creates officers there
    if not rows:
        pytest.skip("No renewal applications on dev yet.")
    return rows


@pytest.fixture
def renewal_scope_areas(renewal_scope_rows) -> RenewalScope:
    areas = RenewalFactory.scope_areas(renewal_scope_rows)
    if not areas.district:
        pytest.skip("No renewal application is in a known district.")
    return areas


@pytest.fixture
def renewal_role_officer(new_officers, officer_login):
    """Factory: creates a NEW test officer of ``role`` for the area (never an existing officer), logs it in in
    a separate browser and opens Renewal applications. Returns the AdminRenewalsPage. The officers are deleted
    on teardown (``new_officers``)."""
    def _make(role: str, division: str = "", district: str = "") -> AdminRenewalsPage:
        data = OfficersFactory.officer(role, division=division, district=district,
                                       label=f"{role} officer {division}/{district}".rstrip("/"))
        new_officers.create(data)
        page, error = officer_login(data)
        if error:
            pytest.fail(f"New {role} officer {data.username} could not log in: {error}")
        renewals = AdminRenewalsPage(page)
        renewals.open()
        return renewals

    return _make


@pytest.fixture
def logged_out_page(page):
    """The browser with no officer session."""
    page.context.clear_cookies()
    return page


@pytest.fixture
def renewal_officer_login(page):
    """A callable that swaps the browser to the Officer Console as the Super Admin (mid-test, after the agency
    steps). Logs the officer out on teardown."""
    def _login():
        page.context.clear_cookies()
        _admin_login(page)

    yield _login
    _admin_logout(page)


# ── Data ──────────────────────────────────────────────────────────────────────

@pytest.fixture
def renewal_no_changes_data() -> RenewalData:
    return RenewalFactory.no_changes()


@pytest.fixture
def renewal_blank_data() -> RenewalData:
    return RenewalFactory.blank()


@pytest.fixture
def renewal_not_declared_data() -> RenewalData:
    return RenewalFactory.not_declared()


@pytest.fixture
def renewal_changes_without_details_data() -> RenewalData:
    return RenewalFactory.changes_without_details()


@pytest.fixture
def renewal_changes_without_document_data() -> RenewalData:
    return RenewalFactory.changes_without_document()


@pytest.fixture
def renewal_cases_without_details_data() -> RenewalData:
    return RenewalFactory.cases_without_details()


@pytest.fixture
def renewal_invalid_documents_data() -> list[RenewalData]:
    return RenewalFactory.invalid_documents()


@pytest.fixture
def renewal_approval_data() -> RenewalDecisionData:
    return RenewalFactory.approval()


@pytest.fixture
def renewal_rejection_data() -> RenewalDecisionData:
    return RenewalFactory.rejection()


@pytest.fixture
def renewal_short_remarks_data() -> list[RenewalDecisionData]:
    """[too-short rejection, too-short approval] — the order KAN-TC-413 tries them."""
    return [RenewalFactory.short_rejection(), RenewalFactory.short_approval()]


@pytest.fixture
def renewal_dialog_remarks_data() -> RenewalDecisionData:
    return RenewalFactory.dialog_remarks()
