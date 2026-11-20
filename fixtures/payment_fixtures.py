import pytest

from pages.my_application_page import MyApplicationPage
from pages.receipt_page import ReceiptPage
from test_data.payment_factory import PaymentData, PaymentFactory

# Navigation: a paid agency comes from ``logged_in_agency_home_page`` (agency_home_fixtures), an unpaid
# one from ``logged_in_preview_page`` (preview_fixtures); ``dashboard_page`` is in conftest.


# ── Page object fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def payment_receipt_page(page) -> ReceiptPage:
    return ReceiptPage(page)


@pytest.fixture
def submitted_application_page(page) -> MyApplicationPage:
    return MyApplicationPage(page)


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def payment_fee_for_area():
    """TC-874: the fee for a Part C area — call it with the area the submitted application shows."""
    def fee(area: str) -> PaymentData:
        return PaymentFactory.for_area(area)
    return fee
