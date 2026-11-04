import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from fixtures.licenses_fixtures import _restore_certificate
from pages.admin.compliance_page import AdminCompliancePage
from pages.admin.licenses_page import AdminLicensesPage
from test_data.compliance_factory import CaseActionData, ComplianceCaseData, ComplianceFactory

OPEN_STATUSES = ("under inquiry", "hearing scheduled", "post hearing window", "suspended")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _close_open_cases(cp: AdminCompliancePage, agency_name: str) -> None:
    """Drops every open case of the agency. A case that only allows a hearing (a Route B suspension) gets a
    hearing first — dropping is offered only after it."""
    cp.open()
    for row in cp.cases_for(agency_name):
        if row["status"] not in OPEN_STATUSES:
            continue
        cp.open_case(row["case_no"])
        if "drop" not in cp.allowed_actions():
            hearing = ComplianceFactory.hearing()
            cp.choose_action("hearing")
            cp.set_hearing(hearing.hearing_at, hearing.hearing_mode)
            cp.fill_remarks(ComplianceFactory.cleanup_remarks())
            cp.submit_action()
            cp.open_case(row["case_no"])
        cp.choose_action("drop")
        cp.fill_remarks(ComplianceFactory.cleanup_remarks())
        cp.submit_action()


# ── Page-object fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def admin_compliance_page(page) -> AdminCompliancePage:
    return AdminCompliancePage(page)


@pytest.fixture
def logged_in_admin_compliance_page(page) -> AdminCompliancePage:
    """Logs in as the Super Admin and opens Compliance cases. Logs out on teardown (the browser context is
    shared across the session)."""
    _admin_login(page)
    cp = AdminCompliancePage(page)
    cp.open()
    yield cp
    _admin_logout(page)


@pytest.fixture
def compliance_agency(logged_in_admin_compliance_page: AdminCompliancePage) -> str:
    """An approved agency with an Active certificate and no open compliance case, that the test may open
    cases for, suspend or cancel. It is the second-last Active agency in name order: the last one is the
    Licences & certificates tests' scratch agency.

    On teardown every open case of the agency is dropped and its certificate is made Active again with its
    original dates (cases and History entries stay)."""
    cp = logged_in_admin_compliance_page
    lp = AdminLicensesPage(cp.page)
    lp.open(status="all")
    active = lp.agencies_with_status("active")
    if len(active) < 2:
        pytest.skip("Needs two agencies with an Active certificate on Licences & certificates.")
    agency = active[-2]
    valid_from, valid_upto = lp.get_row_validity_dates(agency)
    _close_open_cases(cp, agency)
    cp.open()
    yield agency
    try:
        _close_open_cases(cp, agency)
    except Exception as e:  # still restore the certificate
        print(f"[compliance_agency] Could not close the cases of {agency}: {e}")
    _restore_certificate(lp, agency, valid_from, valid_upto)


def _open_case(cp: AdminCompliancePage, agency: str, data: ComplianceCaseData) -> str:
    case_no, toast = cp.open_case_for(agency, data.trigger, data.details, data.high_risk, data.reasons)
    if not case_no:
        pytest.fail(f"Could not open a compliance case for {agency}: {toast}")
    return case_no


@pytest.fixture
def route_a_case(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str):
    """(agency, case number) of a Route A case opened for ``compliance_agency`` (Under inquiry)."""
    return compliance_agency, _open_case(logged_in_admin_compliance_page, compliance_agency, ComplianceFactory.route_a())


@pytest.fixture
def route_b_case(logged_in_admin_compliance_page: AdminCompliancePage, compliance_agency: str):
    """(agency, case number) of a Route B case opened for ``compliance_agency`` (Suspended)."""
    return compliance_agency, _open_case(logged_in_admin_compliance_page, compliance_agency, ComplianceFactory.route_b())


def _schedule_hearing(cp: AdminCompliancePage, case_no: str) -> None:
    hearing = ComplianceFactory.hearing()
    _, toast = cp.take_action(case_no, "hearing", hearing.remarks, hearing.hearing_at, hearing.hearing_mode)
    if toast != hearing.expected_message:
        pytest.fail(f"Could not schedule the hearing of {case_no}: {toast}")
    cp.case_row(case_no).filter(has_text="hearing scheduled").wait_for()


@pytest.fixture
def heard_case(logged_in_admin_compliance_page: AdminCompliancePage, route_a_case):
    """(agency, case number) of a Route A case with a hearing scheduled 7 days ahead (Hearing scheduled)."""
    _schedule_hearing(logged_in_admin_compliance_page, route_a_case[1])
    return route_a_case


@pytest.fixture
def heard_route_b_case(logged_in_admin_compliance_page: AdminCompliancePage, route_b_case):
    """(agency, case number) of a Route B case (agency suspended) with a hearing scheduled."""
    _schedule_hearing(logged_in_admin_compliance_page, route_b_case[1])
    return route_b_case


# ── Data fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def route_a_data() -> ComplianceCaseData:
    return ComplianceFactory.route_a()


@pytest.fixture
def route_b_data() -> ComplianceCaseData:
    return ComplianceFactory.route_b()


@pytest.fixture
def missing_reasons_data() -> dict:
    """TC-655 — Route B with no reasons, and with only spaces."""
    return {"empty": ComplianceFactory.route_b_without_reasons(""),
            "spaces": ComplianceFactory.route_b_without_reasons("   ")}


@pytest.fixture
def short_details_data() -> ComplianceCaseData:
    return ComplianceFactory.short_details()


@pytest.fixture
def long_text_data() -> ComplianceCaseData:
    return ComplianceFactory.long_text()


@pytest.fixture
def hearing_data() -> CaseActionData:
    return ComplianceFactory.hearing("virtual")


@pytest.fixture
def hearing_without_date_data() -> CaseActionData:
    return ComplianceFactory.hearing_without_date()


@pytest.fixture
def hearing_in_past_data() -> CaseActionData:
    return ComplianceFactory.hearing_in_past()


@pytest.fixture
def window_data() -> CaseActionData:
    return ComplianceFactory.window("3")


@pytest.fixture
def drop_data() -> CaseActionData:
    return ComplianceFactory.drop()


@pytest.fixture
def revoke_data() -> CaseActionData:
    return ComplianceFactory.revoke()


@pytest.fixture
def cancellation_order_data() -> CaseActionData:
    return ComplianceFactory.cancellation()


@pytest.fixture
def blank_remarks_data() -> CaseActionData:
    return ComplianceFactory.blank_remarks()
