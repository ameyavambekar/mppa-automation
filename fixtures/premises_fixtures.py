import os
from urllib.parse import urlparse

import pytest

from config import FORMS_BASE
from pages.login_page import LoginPage
from pages.premises_page import PremisesPage
from test_data.premises_factory import PremisesData, PremisesFactory
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore

_ORIGIN = "{0.scheme}://{0.netloc}".format(urlparse(FORMS_BASE))
_LOCATION = {"latitude": PremisesFactory.LOCATION[0], "longitude": PremisesFactory.LOCATION[1], "accuracy": 20}


class LocationAccess:
    """Allows or blocks the site's access to the browser location (set to Pune, or
    ``location`` = (lat, lng) when given)."""

    def __init__(self, context):
        self.context = context

    def allow(self, location: tuple[float, float] = None):
        self.context.grant_permissions(["geolocation"], origin=_ORIGIN)
        self.context.set_geolocation(
            {**_LOCATION, "latitude": location[0], "longitude": location[1]} if location else _LOCATION)

    def block(self):
        self.context.clear_permissions()


def _login_and_open_premises(page, user) -> PremisesPage:
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    premises = PremisesPage(page)
    premises.open()
    page.wait_for_load_state("networkidle")
    return premises


def _already_touched(premises: PremisesPage, store: TestStateStore, user) -> bool:
    """True when the state store missed earlier activity (a saved photo, a "Not applicable"
    card or an answered question); records it so the user is skipped from now on."""
    touched = (premises.page.locator(".pp-card.is-done, [data-thumb] img").count() > 0
               or premises.page.locator(".pp-q input:checked").count() > 0)
    if touched:
        store.mark_form_step_status(username=user.username, step="premises", status="in_progress")
    return touched


def _open_untouched_premises(page):
    """Logs in as an agency with all six documents uploaded and Premises Photos never touched,
    building one when none is left. Returns the user."""
    store = TestStateStore()
    for user in store.get_agency_users_with_steps(["part_a", "part_b", "part_c", "part_f", "enclosures"]):
        if user.steps.get("premises") in ("in_progress", "completed"):
            continue
        if not _already_touched(_login_and_open_premises(page, user), store, user):
            return user
    user = AgencyBuilder(page, store).build("enclosures")
    _login_and_open_premises(page, user)
    return user


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def premises_page(page) -> PremisesPage:
    return PremisesPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def location_access(page) -> LocationAccess:
    """Location access for the test's browser context, allowed (Pune) by default and
    removed again after the test."""
    access = LocationAccess(page.context)
    access.allow()
    yield access
    page.context.clear_permissions()
    page.context.set_geolocation(None)


@pytest.fixture
def logged_in_premises_page(page, location_access):
    """Yields (page, user) on Premises Photos for an agency with all six documents uploaded
    and Premises Photos never touched (no photo, no answer). Location access is allowed
    (Pune). Users who have touched the step are never used; when none is left, a new
    agency is built (see ``utils.agency_builder``)."""
    yield page, _open_untouched_premises(page)


@pytest.fixture
def logged_in_premises_camera_page(playwright_instance):
    """Like ``logged_in_premises_page`` but in a separate browser with Chromium's fake camera,
    so "Take photo" opens a working camera view. Camera and location (Pune) are allowed."""
    browser = playwright_instance.chromium.launch(
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        slow_mo=int(os.getenv("SLOW_MO", "100")),
        args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
    )
    context = browser.new_context(viewport={"width": 1280, "height": 800}, geolocation=_LOCATION,
                                  permissions=["geolocation", "camera"])
    context.set_default_timeout(30000)
    page = context.new_page()
    yield page, _open_untouched_premises(page)
    browser.close()


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def premises_required_only_data() -> PremisesData:
    """TC-481: the three required photos, both questions No."""
    return PremisesFactory.required_only()


@pytest.fixture
def premises_jpg_and_png_data() -> PremisesData:
    """TC-478: a JPG and a PNG."""
    return PremisesFactory.jpg_and_png()


@pytest.fixture
def premises_not_images_data() -> PremisesData:
    """TC-486: a PDF and a HEIC file."""
    return PremisesFactory.not_images()
