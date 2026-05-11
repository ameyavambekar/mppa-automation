import pytest
from playwright.sync_api import Page
from conftest import BASE_URL

def test_portal_is_reachable(login_page):
    login_page.open()
    """Verify the portal loads and the login page is accessible."""
    assert login_page.login_title.is_visible(), "Page title should not be empty"


def test_login_page_has_captcha(login_page):
    """Verify CAPTCHA element exists on the login page."""
    # Update selector to match the actual CAPTCHA image element on the portal
    login_page.open()
    assert len(login_page.captcha_value.text_content()) == 6
