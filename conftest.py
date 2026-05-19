import allure
import pytest
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from datetime import datetime
import time

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage
from pages.registration_page import RegistrationPage
from test_data.agency_registration_factory import AgencyRegistrationFactory


# ── Allure output dir ─────────────────────────────────────────────────────────
load_dotenv()
ALLURE_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "reports", "allure-results")
BASE_URL = os.getenv("MPPA_BASE_URL", "https://devmppa.sppuef.in/module/agency/auth")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "100"))


# ── Data fixture plugins ──────────────────────────────────────────────────────
# Each string is a dotted module path to a fixtures file.
# pytest discovers and registers all @pytest.fixture functions inside them
# automatically — no imports needed in test files.
pytest_plugins = [
    "fixtures.registration_fixtures",
    "fixtures.login_fixtures",
    "fixtures.dashboard_fixtures",
]



# ── Allure environment file ───────────────────────────────────────────────────
def pytest_configure(config):
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
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

# ── Browser lifecycle ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def browser_context():
    """Single browser context shared across the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
        )
        context.set_default_timeout(30000)
        yield context
        context.close()
        browser.close()

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


# ── Allure environment ────────────────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # Only act on the actual test call phase (not setup/teardown)
    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if page:
            path = f"reports/allure-results/{item.name}"
            screenshot_bytes = page.screenshot(path=path)

            # Attach to Allure report
            allure.attach(
                screenshot_bytes,
                name=f"FAILED — {item.name}",
                attachment_type=allure.attachment_type.PNG
            )