import re

import pytest

from config import FORMS_BASE
from pages.declaration_page import PREVIEW_URL
from pages.login_page import LoginPage
from pages.preview_page import PreviewPage
from test_data.preview_factory import PreviewData, PreviewFactory
from utils.agency_builder import AgencyBuilder
from utils.state_store import TestStateStore

ON_PREVIEW = re.compile(rf"{re.escape(PREVIEW_URL)}")
# Where the Form-I pages send an agency whose application is already submitted (paid).
SUBMITTED = re.compile(r"/auth/user_manual\.php")


def _login_and_open_preview(page, user) -> bool:
    """Logs in as ``user`` and opens Preview; False when preview.php sends the user elsewhere."""
    page.context.clear_cookies()
    login = LoginPage(page)
    login.open()
    login.login(user.username, user.password)
    page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)
    PreviewPage(page).open()
    page.wait_for_load_state("networkidle")
    return bool(ON_PREVIEW.match(page.url))


# ── Page object fixture ───────────────────────────────────────────────────────

@pytest.fixture
def preview_page(page) -> PreviewPage:
    return PreviewPage(page)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def logged_in_preview_page(page):
    """Yields (page, user) on the Preview step for an agency whose Declaration step is complete
    and who has not paid. Looking at Preview does not use the agency up — only paying does
    (TC-513), and that test records it. An agency paid outside the tests no longer gets the
    Form-I pages (they redirect to the user manual); it is recorded as paid and skipped. When
    none is left, a new agency is built up to "declaration" (see ``utils.agency_builder``)."""
    store = TestStateStore()
    steps = ["part_a", "part_b", "part_c", "part_f", "enclosures", "premises", "declaration"]
    for user in store.get_agency_users_with_steps(steps):
        if user.steps.get("payment") in ("in_progress", "completed"):
            continue
        if _login_and_open_preview(page, user):
            yield page, user
            return
        if SUBMITTED.search(page.url):
            store.mark_form_step_status(username=user.username, step="payment", status="completed")
    user = AgencyBuilder(page, store).build("declaration")
    _login_and_open_preview(page, user)
    yield page, user


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def preview_fee_data() -> PreviewData:
    """TC-512: the fee for an agency operating only within Maharashtra."""
    return PreviewFactory.within_maharashtra()
