from conftest import BASE_URL
from playwright.sync_api import Page
from utils.email_otp import get_test_email, get_otp_from_testmail


def test_testmail_email_address_format():
    """Verify the generated email address matches expected format."""
    email = get_test_email()
    assert "@inbox.testmail.app" in email
    assert "." in email.split("@")[0]  # namespace.tag format


def test_otp_retrieval(page: Page):
    """
    Manual trigger test — use this when you need to verify
    OTP polling works end-to-end.

    Steps:
    1. Manually send an email with a 6-digit code to your testmail inbox
       OR trigger it via the portal UI in the test.
    2. Run this test and confirm the OTP is retrieved.
    """
    # Trigger OTP on the portal
    print(BASE_URL)
    page.goto(f"{BASE_URL}/register.php")
    page.fill("input[id='email']", get_test_email())
    page.click("button[id='otpBtn']")

    # Poll for it
    otp = get_otp_from_testmail(retries=10, delay=6)
    print(otp)
    assert otp.isdigit()
    assert len(otp) == 6