"""
Fixtures — Second Appeal (FORM-IV), agency side
================================================
FORM-IV (/module/agency/appeals/second.php) is offered only to an agency whose First Appeal was dismissed and
who has not filed a Second Appeal yet. Such agencies are rare on dev, so:

* ``second_appeal_page`` opens the form WITHOUT filing anything. It prefers an agency the state store records
  as ``first_appeal`` (dismissed); when none is left it borrows the agency parked at the map state
  ``first_appeal_dismissed`` — read-only use only, so the map tests still find it there.
* ``second_appeal_filing_page`` opens the form for an agency that may be used up (never a parked one). Filing
  records the agency as ``second_appeal``. Opt-in with RUN_APPEAL_FILING_TESTS=true (``appeal_filing_allowed``).
* ``filed_second_appeal_page(state)`` opens FORM-IV for an agency whose Second Appeal is ``pending`` or
  ``decided`` (store status ``second_appeal``, else the map states ``second_appeal_pending`` /
  ``second_appeal_decided``) — read-only.

Top up dismissed First Appeals (irreversible) with ``python -m utils.seed_appeals --decided 2``.
"""

import pytest

from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.login_page import LoginPage
from pages.second_appeal_page import SecondAppealPage
from test_data.first_appeal_factory import FirstAppealData, SecondAppealFactory
from utils import failure_pages, file_manager
from utils.state_store import TestStateStore, UserRecord


def _login(page, agency: UserRecord) -> bool:
    login = LoginPage(page)
    login.open()
    login.login(agency.username, agency.password)
    page.wait_for_load_state("networkidle")
    return "login" not in page.url


def _logout(page) -> None:
    try:
        page.goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
    except Exception:
        pass


def _form_candidates(include_parked: bool) -> list[UserRecord]:
    store = TestStateStore()
    agencies = store.get_agency_users_in_status("first_appeal")
    if include_parked:
        agencies += store.get_map_users("first_appeal_dismissed")
    return agencies


def _open_form(page, include_parked: bool) -> tuple[SecondAppealPage, UserRecord]:
    """Logs ``page`` in as the first agency that FORM-IV offers the form to and opens it."""
    for agency in _form_candidates(include_parked):
        if not _login(page, agency):
            continue
        sa = SecondAppealPage(page)
        sa.open()
        if sa.appeal_form.count():
            return sa, agency
        _logout(page)
    pytest.skip("No agency in the state store can file a Second Appeal (First Appeal dismissed, no Second Appeal "
                "yet) — run 'python -m utils.seed_appeals --decided 2' first.")


@pytest.fixture
def second_appeal_page(page, request):
    """FORM-IV open on the primary browser for an agency that may file — nothing is filed. Yields
    (SecondAppealPage, UserRecord); logs out on teardown."""
    sa, agency = _open_form(page, include_parked=True)
    failure_pages.register(request.node, page, f"agency {agency.username}")
    yield sa, agency
    _logout(page)


@pytest.fixture
def second_appeal_filing_page(page, request):
    """FORM-IV open for an agency that the test may use up by filing (never a parked map agency)."""
    sa, agency = _open_form(page, include_parked=False)
    failure_pages.register(request.node, page, f"agency {agency.username}")
    yield sa, agency
    _logout(page)


@pytest.fixture
def filed_second_appeal_page(page, request):
    """Returns ``open(state) -> (SecondAppealPage, UserRecord)`` with ``state`` 'pending' or 'decided': FORM-IV for
    an agency whose Second Appeal is in that state. Read-only. Skips when none is."""
    store = TestStateStore()
    map_state = {"pending": "second_appeal_pending", "decided": "second_appeal_decided"}

    def open_(state: str):
        _logout(page)
        for agency in store.get_agency_users_in_status("second_appeal") + store.get_map_users(map_state[state]):
            if not _login(page, agency):
                continue
            sa = SecondAppealPage(page)
            sa.open()
            if sa.filed_appeal_card.count():
                pending = "Pending decision" in sa.filed_appeal_title.text_content()
                if pending == (state == "pending"):
                    failure_pages.register(request.node, page, f"agency {agency.username}")
                    return sa, agency
            _logout(page)
        pytest.skip(f"No agency in the state store has a Second Appeal {state}.")

    yield open_
    _logout(page)


# ── Data ───────────────────────────────────────────────────────────────────────

@pytest.fixture
def second_appeal_valid_data() -> FirstAppealData:
    return SecondAppealFactory.valid_required_documents(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def second_appeal_full_data() -> FirstAppealData:
    return SecondAppealFactory.valid_with_documents(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def second_appeal_no_ground_data() -> FirstAppealData:
    return SecondAppealFactory.no_ground(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def second_appeal_other_blank_data() -> FirstAppealData:
    return SecondAppealFactory.other_ground_blank(file_manager.VALID_CERTIFICATE)


@pytest.fixture
def second_appeal_empty_document_data() -> FirstAppealData:
    return SecondAppealFactory.invalid_document(file_manager.VALID_CERTIFICATE, file_manager.EMPTY_PDF,
                                                "second_appeal_empty_ra_order")
