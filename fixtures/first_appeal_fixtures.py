"""
Fixtures — First Appeal Management (FORM-III)
=============================================
Covers KAN-TC-360 through KAN-TC-368 (Admin Console · Appeals module).

Two halves:

* Admin-side — ``logged_in_admin_appeals_page`` logs in as super admin and opens
  the Appeals module; the ``*_outcome_data`` fixtures supply decision payloads.

* Agency-side seeding — ``filed_first_appeal_*`` fixtures file a FORM-III appeal
  in a *separate* agency browser (so the shared admin session is untouched) to
  guarantee a precondition the admin assertions need: an appeal WITH documents,
  WITHOUT documents, or filed LATE. They yield the order number / reg id the
  admin test searches for. Each skips gracefully when it cannot seed (no agency
  in the state store, or the agency already has an appeal on file).
"""

import os

import pytest

from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.login_page import AdminLoginPage
from pages.first_appeal_page import FirstAppealPage
from pages.login_page import LoginPage
from test_data.first_appeal_factory import (
    AppealOutcomeData,
    AppealOutcomeFactory,
    FirstAppealData,
    FirstAppealFactory,
)
from utils import file_manager
from utils.state_store import TestStateStore, UserRecord

ADMIN_LOGOUT_URL = "https://devmppa.sppuef.in/module/admin/auth/logout.php"


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


# ── Admin page-object fixtures ─────────────────────────────────────────────────

@pytest.fixture
def admin_appeals_page(page) -> AdminAppealsPage:
    return AdminAppealsPage(page)


@pytest.fixture
def logged_in_admin_appeals_page(page) -> AdminAppealsPage:
    """Logs in as super admin then opens the Appeals module.

    Logs the admin out on teardown: the browser context is shared across the
    whole session, so the admin session cookie would otherwise persist and the
    next test's ``login.open()`` would redirect straight to the dashboard,
    breaking its login flow.
    """
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    login.login(admin.username, admin.password)
    appeals = AdminAppealsPage(page)
    appeals.open()
    yield appeals
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


# ── Agency-side First Appeal page object + seeding ─────────────────────────────

@pytest.fixture
def first_appeal_page(page) -> FirstAppealPage:
    """A FirstAppealPage on the primary browser, logged in as an agency user and
    parked on the FORM-III form. Use this to drive the agency filing flow
    directly (it shares the primary ``page``, so don't combine it with an admin
    fixture in the same test)."""
    agency = _agency_user_or_skip()
    login = LoginPage(page)
    login.open()
    login.login(agency.username, agency.password)
    fa = FirstAppealPage(page)
    fa.open()
    return fa


def _seed_first_appeal(second_browser, data: FirstAppealData) -> dict:
    """Files ``data`` as a FORM-III appeal in an independent agency browser and
    returns a locator dict for the admin side. Skips the requesting test if the
    appeal cannot be filed (no agency, already-filed banner, or no success
    confirmation)."""
    agency = _agency_user_or_skip()
    browser = second_browser()
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    try:
        login = LoginPage(page)
        login.open()
        login.login(agency.username, agency.password)

        fa = FirstAppealPage(page)
        fa.open()
        if fa.has_existing_appeal():
            pytest.skip(
                f"Agency '{agency.username}' already has a first appeal on file — "
                f"cannot seed the '{data.scenario_label}' precondition."
            )
        reg_id = fa.get_registration_no()
        fa.file_appeal(data)

        if fa.success_alert.count() == 0:
            pytest.skip(
                f"Filing the '{data.scenario_label}' appeal did not confirm "
                f"(no success banner) — the dev environment may block this agency "
                f"from filing right now."
            )
        return {
            "order_number": data.order_number,
            "reg_id": reg_id,
            "delay_reason": data.delay_reason,
            "scenario_label": data.scenario_label,
        }
    finally:
        context.close()


@pytest.fixture
def filed_first_appeal_with_documents(second_browser) -> dict:
    """KAN-TC-362 — a filed FORM-III appeal carrying all five enclosures."""
    data = FirstAppealFactory.valid_with_documents(file_manager.VALID_PDF)
    return _seed_first_appeal(second_browser, data)


@pytest.fixture
def filed_first_appeal_without_documents(second_browser) -> dict:
    """KAN-TC-368 — a filed FORM-III appeal with no enclosures."""
    data = FirstAppealFactory.valid_without_documents()
    return _seed_first_appeal(second_browser, data)


@pytest.fixture
def filed_late_first_appeal(second_browser) -> dict:
    """KAN-TC-366 — a FORM-III appeal filed beyond the 30-day limitation."""
    data = FirstAppealFactory.late_filed()
    return _seed_first_appeal(second_browser, data)


# ── Admin outcome data fixtures ────────────────────────────────────────────────

@pytest.fixture
def allowed_outcome_data() -> AppealOutcomeData:
    """KAN-TC-363 — allow the appeal with mandatory remarks."""
    return AppealOutcomeFactory.allowed_with_remarks()


@pytest.fixture
def rejected_blank_remarks_data() -> AppealOutcomeData:
    """KAN-TC-364 — attempt to save an outcome with blank remarks (blocked)."""
    return AppealOutcomeFactory.rejected_blank_remarks()


@pytest.fixture
def allowed_for_audit_data() -> AppealOutcomeData:
    """KAN-TC-365 — allow the appeal with remarks for the audit-trail check."""
    return AppealOutcomeFactory.allowed_for_audit()
