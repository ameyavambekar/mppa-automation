import allure
import base64
import os
import time
from datetime import datetime
from pathlib import Path

import pytest
import pytest_html
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from pages.dashboard_page import DashboardPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.registration_page import RegistrationPage
from test_data.agency_registration_factory import AgencyRegistrationFactory
from utils import aio_client


# ── Allure output dir ─────────────────────────────────────────────────────────
load_dotenv()
ALLURE_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "reports", "allure-results")
BASE_URL = os.getenv("MPPA_BASE_URL", "https://devmppa.sppuef.in/module/agency/auth")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "100"))
REPORT_DIR  = os.path.join(os.path.dirname(__file__), "reports")
HTML_REPORT = os.path.join(REPORT_DIR, "report.html")

# ── Data fixture plugins ──────────────────────────────────────────────────────
# Each string is a dotted module path to a fixtures file.
# pytest discovers and registers all @pytest.fixture functions inside them
# automatically — no imports needed in test files.
pytest_plugins = [
    "fixtures.registration_fixtures",
    "fixtures.login_fixtures",
    "fixtures.dashboard_fixtures",
    "fixtures.home_fixtures",
    "fixtures.step1_fixtures",
    "fixtures.admin_fixtures",
    "fixtures.notices_fixtures",
    "fixtures.licenses_fixtures",
    "fixtures.agencies_fixtures",
]



# ── Allure environment file ───────────────────────────────────────────────────
def pytest_configure(config):
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    env_file = os.path.join(ALLURE_RESULTS_DIR, "environment.properties")
    with open(env_file, "w") as f:
        f.write(f"Base.URL={BASE_URL}\n")
        f.write(f"Browser=chromium\n")
        f.write(f"Python.Version=3.11\n")
        f.write(f"Framework=Playwright+pytest\n")
    config.addinivalue_line(
        "markers",
        "wait_before(seconds): pause for the given number of seconds before "
        "the test starts. Defaults to 60 seconds when no argument is supplied.",
    )

    # Wire up pytest-html as a self-contained single file
    # (only if the user didn't already pass --html on the CLI)
    if not config.option.__dict__.get("htmlpath"):
        config.option.htmlpath = HTML_REPORT
        config.option.self_contained_html = True


def pytest_collection_modifyitems(items):
    """Surface @aio_case keys on items so they appear in JUnit XML and are
    available to the report hook for REST upload to AIO."""
    for item in items:
        key = getattr(item.obj, "_aio_case_key", None)
        if key:
            item.user_properties.append(("aio_case_key", key))


# ── Browser lifecycle ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def playwright_instance():
    """The single session-wide Playwright object. Reuse this to launch
    additional browsers — never call sync_playwright() again inside a test."""
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser_context(playwright_instance):
    """Single browser context shared across the session."""
    browser = playwright_instance.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        accept_downloads=True,
    )
    context.set_default_timeout(30000)
    yield context
    context.close()
    browser.close()

@pytest.fixture
def second_browser(playwright_instance):
    """Factory for an independent second browser (separate cookies/session).
    Used by TC-26 to simulate the same user logging in from another machine,
    and by the Notices dual-role tests to open an agency session alongside the
    admin one. Honours the project HEADLESS / SLOW_MO settings so the second
    window is visible and its interactions are paced just like the primary
    browser. Cleans up every browser it hands out."""
    browsers = []

    def _launch():
        browser = playwright_instance.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        browsers.append(browser)
        return browser

    yield _launch

    for b in browsers:
        b.close()

@pytest.fixture(scope="function")
def page(browser_context):
    """Fresh page for each test function."""
    page = browser_context.new_page()
    yield page
    page.close()

@pytest.fixture
def logged_in_page(request, page):
    """Logs in as the given role before the test."""
    role = request.param          # passed via indirect=
    page.goto(f"{BASE_URL}/login.php")
    page.fill("#user", role)
    page.fill("#pass", "password")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard")
    yield page


@pytest.fixture(autouse=True)
def pause_before(request):
    """
    Pauses before any test marked with @pytest.mark.wait_before.

    Usage — default 60-second pause:
        @pytest.mark.wait_before
        def test_something(...): ...

    Usage — custom duration:
        @pytest.mark.wait_before(30)
        def test_something(...): ...

    The pause happens during fixture setup (before the test body runs) so it
    shows up as setup time in the Allure timeline, not as test time.
    """
    marker = request.node.get_closest_marker("wait_before")
    if marker:
        # marker.args[0] if a duration was passed, otherwise default to 60
        seconds = marker.args[0] if marker.args else 60
        print(f"\n[wait_before] Pausing {seconds}s before '{request.node.name}' ...")
        time.sleep(seconds)
        print(f"[wait_before] Resuming '{request.node.name}'.")
    yield

# Page object fixtures
@pytest.fixture
def registration_page(page) -> RegistrationPage:
    """Returns a RegistrationPage instance and navigates to the form."""
    rp = RegistrationPage(page)
    rp.open()
    return rp

@pytest.fixture
def login_page(page):
    return LoginPage(page)

@pytest.fixture
def dashboard_page(page):
    return DashboardPage(page)

@pytest.fixture
def home_page(page):
    return HomePage(page)


# ── Test reporting: screenshot on failure + AIO Tests REST upload ───────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when != "call":
        return

    # ── AIO Tests: POST status for every test that carries an @aio_case key ──
    aio_run_id = None
    case_key = next(
        (v for k, v in report.user_properties if k == "aio_case_key"), None
    )
    if case_key:
        status = aio_client.map_status(report.outcome)
        if status:
            aio_run_id = aio_client.post_test_run(
                case_key,
                status,
                comment=report.longreprtext if report.failed else None,
                effort_ms=int(report.duration * 1000),
            )

    # ── On failure: capture screenshot, attach to Allure + HTML + AIO ───────
    if report.failed:
        page = item.funcargs.get("page")
        if page:
            png_bytes = page.screenshot()

            # Allure attachment
            allure.attach(
                png_bytes,
                name=f"FAILED — {item.name}",
                attachment_type=allure.attachment_type.PNG,
            )

            # pytest-html inline attachment (base64, no external file needed)
            encoded = base64.b64encode(png_bytes).decode("utf-8")
            html_img = (
                f'<div><img src="data:image/png;base64,{encoded}" '
                f'style="max-width:900px;border:1px solid #ccc;" '
                f'alt="Screenshot on failure"/></div>'
            )
            report.extra = getattr(report, "extra", [])
            report.extra.append(pytest_html.extras.html(html_img))

            # AIO attachment — only if the status POST above gave us a run ID
            if aio_run_id is not None:
                aio_client.post_attachment(
                    aio_run_id,
                    png_bytes,
                    filename=f"{item.name}.png",
                )


def pytest_html_report_title(report):
    report.title = "MPPA One-Stop Portal — Test Run Report"
