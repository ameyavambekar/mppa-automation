import allure
import pytest
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from datetime import datetime
import time

from pages.dashboard_page import DashboardPage
from pages.login_page import LoginPage

load_dotenv()
ALLURE_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "reports", "allure-results"+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
BASE_URL = os.getenv("MPPA_BASE_URL", "https://mppa.sppuef.in/module/agency/auth/login.php")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SLOW_MO = int(os.getenv("SLOW_MO", "100"))
print(f"HEADLESS value: '{os.getenv('HEADLESS')}'")
print(f"SLOW_MO value: '{os.getenv('SLOW_MO')}'")

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


def pytest_configure(config):
    os.makedirs(ALLURE_RESULTS_DIR, exist_ok=True)
    env_file = os.path.join(ALLURE_RESULTS_DIR, "environment.properties")
    with open(env_file, "w") as f:
        f.write(f"Base.URL={BASE_URL}\n")
        f.write(f"Browser=chromium\n")
        f.write(f"Python.Version=3.11\n")
        f.write(f"Framework=Playwright+pytest\n")

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
    page.goto("https://example.com/login")
    page.fill("#user", role)
    page.fill("#pass", "password")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard")
    yield page


# Page object fixtures
@pytest.fixture
def login_page(page):
    return LoginPage(page)

# Page object fixtures
@pytest.fixture
def dashboard_page(page):
    return DashboardPage(page)

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

