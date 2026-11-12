"""
Fixtures — MPPA Compliance & Appeals Map states
===============================================
Used by the compliance-state tests in tests/admin/test_application_review.py (agency side KAN-48, officer side
KAN-12) and the appeal-state tests in tests/test_appeals_map.py (KAN-49) and tests/admin/test_appeals_map.py
(KAN-50).

``map_user(state)`` hands a test the agency parked at a map state (``test_data.compliance_map_factory.
MAP_STATES``), after checking the Officer Console still shows it there. With RUN_MAP_STATE_TESTS=true a missing one
is generated first (``utils.map_states.MapStateDriver``): an untouched submission is taken along the state's path
and parked there — irreversible on dev, and slow for the appeal states (a whole refusal loop first, and a new
agency built and paid when no untouched submission is left). Without the flag a state with no parked agency skips
before anything is opened.

``agency_at(state)`` logs that agency in on a second browser (``AgencyView``); ``officer_at(state)`` gives the
officer's view of it (``OfficerView``). Both types live in ``utils.map_states``, so tests can annotate with
them without importing from a fixtures module. The officer side runs on the primary page as the Super Admin
(``admin_review``).
"""

import os

import allure
import pytest

from fixtures.sessions_fixtures import AGENCY_LOGOUT_URL
from pages.login_page import LoginPage
from test_data.compliance_map_factory import MAP_STATES
from utils import failure_pages
from utils.map_states import AgencyView, MapStateDriver, MapStateError, OfficerView
from utils.state_store import TestStateStore, UserRecord

FLAG = "RUN_MAP_STATE_TESTS"


def map_generation_allowed() -> bool:
    return os.getenv(FLAG, "false").lower() == "true"


@pytest.fixture
def map_driver(admin_review, second_browser, request) -> MapStateDriver:
    """The map driver on the Super Admin's page (``admin_review``); agencies get their own contexts. Map tests reach
    this page through ``request.getfixturevalue``, so it is registered for the failure screenshot."""
    failure_pages.register(request.node, admin_review.page, "Super Admin")

    def log(message: str):
        allure.attach(message, name="Map state", attachment_type=allure.attachment_type.TEXT)
    return MapStateDriver(admin_review.page, second_browser(), log=log)


@pytest.fixture
def map_user(request):
    """``get(state_key) -> UserRecord``: the agency parked at that map state (generated first when
    RUN_MAP_STATE_TESTS=true and none is parked there; skips otherwise). The Super Admin logs in (``map_driver``)
    only once there is an agency to check or one is to be generated."""

    def get(key: str) -> UserRecord:
        state = MAP_STATES[key]
        generate = map_generation_allowed()
        skip = (f"No agency is parked at '{key}' ({state.step}: {state.title}). Set {FLAG}=true to generate one — "
                f"irreversible on dev.")
        if not generate and not TestStateStore().get_map_users(key):
            pytest.skip(skip)
        driver: MapStateDriver = request.getfixturevalue("map_driver")
        try:
            agency = driver.ensure(state, generate=generate)
        except MapStateError as e:
            pytest.fail(str(e))
        if agency is None:
            pytest.skip(skip.replace("No agency is parked", "The agency parked has moved on from"))
        allure.attach(f"{agency.username} ({agency.application_id}) — {agency.map_state}",
                      name=f"Agency at '{key}'", attachment_type=allure.attachment_type.TEXT)
        return agency

    return get


@pytest.fixture
def agency_at(second_browser, map_user, request):
    """``open(state_key) -> AgencyView``: the agency parked at that state, logged in on a second browser (Home).
    Logs out and closes on teardown. Depends on ``second_browser`` up front (the factory launches nothing until
    called) so that browser is still open when this teardown logs the agency out."""
    contexts = []

    def open_(key: str) -> AgencyView:
        agency = map_user(key)
        driver: MapStateDriver = request.getfixturevalue("map_driver")
        context = driver.browser.new_context(viewport={"width": 1366, "height": 900})
        context.set_default_timeout(30000)
        contexts.append(context)
        page = context.new_page()
        failure_pages.register(request.node, page, f"agency {agency.username}")
        with allure.step(f"Log in as the agency {agency.username}"):
            login = LoginPage(page)
            login.open()
            login.login(agency.username, agency.password)
            page.wait_for_load_state("networkidle")
            if "login" in page.url:
                pytest.fail(f"Agency {agency.username} could not log in.")
        return AgencyView(page=page, agency=agency, driver=driver)

    yield open_
    for context in contexts:
        try:
            if context.pages:
                context.pages[0].goto(AGENCY_LOGOUT_URL, wait_until="domcontentloaded")
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass


@pytest.fixture
def officer_at(map_user, request):
    """``open(state_key) -> OfficerView``: the agency parked at that state, seen as the Super Admin."""

    def open_(key: str) -> OfficerView:
        agency = map_user(key)
        return OfficerView(agency=agency, driver=request.getfixturevalue("map_driver"))

    return open_
