"""
Fixtures — First Appeal Management (FORM-III)
=============================================
Two halves:

* Admin-side — ``logged_in_admin_appeals_page`` logs in as super admin and opens
  the Appeals module; the ``*_outcome_data`` fixtures supply decision payloads.

* Agency-side — ``first_appeal_page`` opens FORM-III for a refused agency without
  filing anything; the ``filed_first_appeal_*`` fixtures FILE a FORM-III appeal in
  a separate agency browser and yield what the officer side searches for.

Filing uses up a refused agency: each can file only one first appeal. Only agencies
the state store records as ``rejected`` are used; a filed agency is recorded as
``first_appeal``. Fixtures skip when none is left — prepare refused agencies, pending
and decided appeals with ``python -m utils.seed_appeals`` (see ``utils.appeal_seeder``).
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
from utils import failure_pages, file_manager
from utils.state_store import TestStateStore, UserRecord
from config import ADMIN_LOGOUT_URL
from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL



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


def _refused_agencies() -> list[UserRecord]:
    """Agencies whose application is refused and not yet appealed, oldest first."""
    return TestStateStore().get_agency_users_in_status("rejected")


# ── Admin page-object fixtures ─────────────────────────────────────────────────

@pytest.fixture
def admin_appeals_page(page) -> AdminAppealsPage:
    return AdminAppealsPage(page)


@pytest.fixture
def logged_in_admin_appeals_page(page) -> AdminAppealsPage:
    """Logs in as the Super Administrator and opens Appeals › First Appeals — Division; logs out on teardown."""
    admin = _super_admin_or_skip()
    login = AdminLoginPage(page)
    login.open()
    error = login.login_past_captcha(admin.username, admin.password)
    if error:
        pytest.fail(f"Admin login as {admin.username} failed: {error}")
    page.wait_for_url(ADMIN_DASHBOARD_URL)
    appeals = AdminAppealsPage(page)
    appeals.open_view("first")
    yield appeals
    try:
        page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


def _pending_first_appeal(ap: AdminAppealsPage, documents: int = None) -> dict | None:
    """The oldest first appeal still awaiting a decision (optionally with exactly ``documents`` documents),
    as the page's APPEALS data, or None."""
    ap.open_view("first")
    pending = [a for a in ap.appeals_data().values()
               if a["type"] == "first" and a["can_decide"] and not a["decided"]
               and (documents is None or len(a["docs"]) == documents)]
    return min(pending, key=lambda a: a["id"]) if pending else None


@pytest.fixture
def pending_first_appeal(logged_in_admin_appeals_page, second_browser) -> dict:
    """A first appeal awaiting decision that carries all five documents (APPEALS data, plus the
    ``seeded`` dict when it had to be filed). Reuses one already on the portal; files one — using up a
    refused agency — only when none is pending. Leaves the First Appeals view open."""
    ap = logged_in_admin_appeals_page
    appeal = _pending_first_appeal(ap, documents=5)
    if appeal is None:
        seeded = _seed_first_appeal(second_browser, FirstAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE))
        appeal = next((a for a in [_pending_first_appeal(ap, documents=5)] if a and a["reg_id"] == seeded["reg_id"]), None)
        if appeal is None:
            pytest.skip(f"The appeal filed for {seeded['reg_id']} is not listed under First Appeals.")
        appeal["seeded"] = seeded
    ap.open_view("first")
    return appeal


@pytest.fixture
def decided_first_appeal(logged_in_admin_appeals_page) -> dict:
    """The newest first appeal with an appellate order (APPEALS data), or skip — the decision tests
    (RUN_APPEAL_DECISION_TESTS) create one."""
    ap = logged_in_admin_appeals_page
    ap.open_view("first")
    decided = [a for a in ap.appeals_data().values() if a["type"] == "first" and a["decided"]]
    if not decided:
        pytest.skip("No decided first appeal on the portal — run 'python -m utils.seed_appeals' (or TC-363 with "
                    "RUN_APPEAL_DECISION_TESTS=true) first.")
    return max(decided, key=lambda a: a["decided"])


@pytest.fixture
def appeal_decisions_allowed():
    """Skips unless RUN_APPEAL_DECISION_TESTS=true. Passing an appellate order cannot be undone and uses up a
    pending appeal (and the refused agency that filed it), so these tests run only on purpose."""
    if os.getenv("RUN_APPEAL_DECISION_TESTS", "false").lower() != "true":
        pytest.skip("Passes an appellate order (irreversible) — set RUN_APPEAL_DECISION_TESTS=true to run.")


# ── Agency-side First Appeal page object + seeding ─────────────────────────────

def _open_form_for_refused_agency(page) -> tuple[FirstAppealPage, UserRecord]:
    """Logs ``page`` in as the first refused agency that can still file a first appeal and opens FORM-III."""
    agencies = _refused_agencies()
    if not agencies:
        pytest.skip("No refused agency in the state store — run 'python -m utils.seed_appeals' first.")
    store = TestStateStore()
    for agency in agencies:
        login = LoginPage(page)
        login.open()
        login.login(agency.username, agency.password)
        page.wait_for_load_state("networkidle")
        if "login" in page.url:
            continue
        fa = FirstAppealPage(page)
        fa.open()
        if not fa.has_existing_appeal():
            return fa, agency
        store.record_agency_status(username=agency.username, status="first_appeal")   # filed elsewhere
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
    pytest.skip("Every refused agency in the state store has already filed its first appeal — run "
                "'python -m utils.seed_appeals' first.")


@pytest.fixture
def first_appeal_page(page):
    """FORM-III open for a refused agency on the primary browser — nothing is filed. Yields
    (FirstAppealPage, the agency's UserRecord); logs the agency out on teardown."""
    fa, agency = _open_form_for_refused_agency(page)
    yield fa, agency
    try:
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


def _seed_first_appeal(second_browser, data: FirstAppealData) -> dict:
    """FILES ``data`` as a FORM-III appeal for a refused agency in a separate browser, records the agency
    as ``first_appeal`` and returns what the officer side looks for. Skips when no refused agency is left
    or the page does not confirm the filing."""
    browser = second_browser()
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    try:
        fa, agency = _open_form_for_refused_agency(page)
        seeded = {"username": agency.username, "reg_id": fa.get_registration_no(),
                  "agency_name": fa.get_agency_name(), "order_number": fa.get_order_number(),
                  "scenario_label": data.scenario_label, "documents": dict(data.documents)}
        fa.file_appeal(data)
        fa.open()
        if not fa.has_existing_appeal():
            pytest.skip(f"Filing the '{data.scenario_label}' appeal for '{agency.username}' was not confirmed — "
                        f"FORM-III still offers the form.")
        TestStateStore().record_agency_status(username=agency.username, status="first_appeal",
                                              data={"appeal_status": "filed"})
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        return seeded
    finally:
        context.close()


@pytest.fixture
def filed_first_appeal_with_documents(second_browser) -> dict:
    """A FORM-III appeal filed with all five documents (uses up one refused agency)."""
    return _seed_first_appeal(second_browser, FirstAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE))


@pytest.fixture
def filed_first_appeal_order_only(second_browser) -> dict:
    """A FORM-III appeal filed with only the required Order document (uses up one refused agency)."""
    return _seed_first_appeal(second_browser, FirstAppealFactory.valid_order_only(file_manager.VALID_CERTIFICATE))


def _filed_agency_page(second_browser, node, want_pending: bool):
    """Generator behind the filed-appeal fixtures: logs a separate browser in as each ``first_appeal`` agency
    in turn and yields (FirstAppealPage, UserRecord) for the first whose appeal card is pending
    (``want_pending``) or decided. Skips when none matches. ``node`` is the test, for the failure screenshot."""
    browser = second_browser()
    context = browser.new_context()
    page = context.new_page()
    try:
        for agency in TestStateStore().get_agency_users_in_status("first_appeal"):
            lp = LoginPage(page)
            lp.open()
            lp.login(agency.username, agency.password)
            page.wait_for_load_state("networkidle")
            if "login" in page.url:
                continue
            fa = FirstAppealPage(page)
            fa.open()
            if fa.filed_appeal_card.count():
                pending = "Pending decision" in fa.filed_appeal_title.text_content()
                if pending == want_pending:
                    failure_pages.register(node, page, f"agency {agency.username}")
                    yield fa, agency
                    page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
                    return
            page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        state = "awaiting a decision" if want_pending else "decided"
        pytest.skip(f"No agency in the state store has a First Appeal {state} — run 'python -m utils.seed_appeals' first.")
    finally:
        context.close()


@pytest.fixture
def appealed_agency_page(second_browser, request):
    """FORM-III in a separate browser for an agency whose First Appeal awaits a decision (recorded as
    ``first_appeal`` in the state store). Yields (FirstAppealPage, the agency's UserRecord); nothing is filed."""
    yield from _filed_agency_page(second_browser, request.node, want_pending=True)


@pytest.fixture
def agency_login(page):
    """Returns ``login(status) -> UserRecord``: logs the primary page in as the oldest agency the state store
    records in ``status`` (e.g. 'rejected', 'desktop_scrutiny', 'approved') and lands on Home. Skips when none
    can log in. Call it again to switch agency (it logs out first); logs out on teardown."""
    store = TestStateStore()

    def login(status: str) -> UserRecord:
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        for agency in store.get_agency_users_in_status(status):
            lp = LoginPage(page)
            lp.open()
            lp.login(agency.username, agency.password)
            page.wait_for_load_state("networkidle")
            if "login" not in page.url:
                return agency
        pytest.skip(f"No agency recorded as '{status}' in the state store could log in.")

    yield login
    try:
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


@pytest.fixture
def appeal_filing_allowed():
    """Skips unless RUN_APPEAL_FILING_TESTS=true. Each filing uses up a refused agency for good (one First
    Appeal per agency; refusing more takes the long officer + agency loop), so these tests run only on purpose."""
    if os.getenv("RUN_APPEAL_FILING_TESTS", "false").lower() != "true":
        pytest.skip("Files an appeal and uses up the agency — set RUN_APPEAL_FILING_TESTS=true to run.")


@pytest.fixture
def decided_appeal_agency_page(second_browser, request):
    """FORM-III in a separate browser for an agency whose First Appeal has been decided (its card no longer
    says 'Pending decision'). Yields (FirstAppealPage, UserRecord); skips when no appeal has been decided."""
    yield from _filed_agency_page(second_browser, request.node, want_pending=False)


# ── Agency-side data fixtures ──────────────────────────────────────────────────

@pytest.fixture
def first_appeal_full_data() -> FirstAppealData:
    return FirstAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def other_ground_blank_data() -> FirstAppealData:
    return FirstAppealFactory.other_ground_blank(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def oversized_order_data() -> FirstAppealData:
    return FirstAppealFactory.oversized_order(file_manager.OVERSIZED_FILE)


@pytest.fixture
def docx_order_data() -> FirstAppealData:
    return FirstAppealFactory.invalid_order_document(file_manager.UNSUPPORTED_CERTIFICATE, "docx_order")


@pytest.fixture
def empty_order_data() -> FirstAppealData:
    return FirstAppealFactory.invalid_order_document(file_manager.EMPTY_PDF, "empty_order")


@pytest.fixture
def first_appeal_valid_data() -> FirstAppealData:
    return FirstAppealFactory.valid_order_only(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def first_appeal_other_ground_data() -> FirstAppealData:
    return FirstAppealFactory.other_ground(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def first_appeal_no_ground_data() -> FirstAppealData:
    return FirstAppealFactory.no_ground(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def first_appeal_oversized_data() -> FirstAppealData:
    return FirstAppealFactory.oversized_document(file_manager.VALID_CERTIFICATE, file_manager.OVERSIZED_FILE)


# ── Officer outcome data fixtures ──────────────────────────────────────────────

@pytest.fixture
def dismissed_upheld_data() -> AppealOutcomeData:
    return AppealOutcomeFactory.dismissed_upheld()


@pytest.fixture
def invalid_outcome_cases() -> list[AppealOutcomeData]:
    """No disposal, blank reasons, 49-character reasons — each refused before the confirmation."""
    return [AppealOutcomeFactory.no_disposal(), AppealOutcomeFactory.blank_reasons(), AppealOutcomeFactory.short_reasons()]
