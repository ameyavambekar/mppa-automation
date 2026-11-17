import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from pages.admin.agencies_page import AdminAgenciesPage
from pages.admin.agency_view_page import AdminAgencyViewPage
from test_data.agencies_factory import (AgenciesFactory, AgencySearchData, CompletionData,
                                        RegistrationInfoData)


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_agencies_page(page) -> AdminAgenciesPage:
    return AdminAgenciesPage(page)


@pytest.fixture
def admin_agency_view_page(page) -> AdminAgencyViewPage:
    return AdminAgencyViewPage(page)


@pytest.fixture
def logged_in_admin_agencies_page(page) -> AdminAgenciesPage:
    """Logs in as the Super Admin and opens Applications → All applications. Logs out on teardown (the
    browser context is shared across the session)."""
    _admin_login(page)
    agencies = AdminAgenciesPage(page)
    agencies.open("all")
    yield agencies
    _admin_logout(page)


# ── Application pickers (read-only) ────────────────────────────────────────────

def _first_application(agencies: AdminAgenciesPage, view: str) -> dict:
    """The first listed application of a tab, as a ``table_data`` row plus its review ``view_id``, or a skip."""
    agencies.open(view)
    rows = agencies.table_data()
    ids = agencies.review_view_ids()
    for row in rows:
        if row["application_id"] in ids:
            return {**row, "view_id": ids[row["application_id"]], "view": view}
    pytest.skip(f"No application with a Review / View link under Applications '{view}' on dev.")


@pytest.fixture
def listed_application(logged_in_admin_agencies_page) -> dict:
    """The first application under All applications (every listed application is submitted and paid)."""
    app = _first_application(logged_in_admin_agencies_page, "all")
    logged_in_admin_agencies_page.open("all")
    return app


@pytest.fixture
def approved_application(logged_in_admin_agencies_page) -> dict:
    """The first application under the Approved tab (certificate issued)."""
    app = _first_application(logged_in_admin_agencies_page, "approved")
    logged_in_admin_agencies_page.open("all")
    return app


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def agency_search_data() -> AgencySearchData:
    """TC-207 — search by name, Application ID, e-mail and PAN; a query that matches nothing."""
    return AgenciesFactory.search_by_each_field()


@pytest.fixture
def registration_info_data() -> RegistrationInfoData:
    """TC-196 — expected format of each Registration Info value."""
    return AgenciesFactory.registration_info_formats()


@pytest.fixture
def completion_data() -> CompletionData:
    """TC-197 — the Completion Status panel of a submitted application."""
    return AgenciesFactory.completion_of_submitted()
