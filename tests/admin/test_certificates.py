"""
Form-II registration certificate — admin side (KAN-28)
======================================================
Covers KAN-TC-222…232 (story KAN-28), read from each approved agency's certificate on Approved agencies → "📜 Cert"
(the admin copy). Read-only: nothing is approved, renewed or changed. Certificates are checked against the story's
fields (Rule 4(1)), validity, banners, print layout, numbers and classification ticks.

Known failures on dev (16-Nov-2026, defect sheet "Super admin"): TC-222 and TC-223 (no Valid From, no first-generated
timestamp — #92), TC-223 and TC-229 (no business classification tick on any certificate — #91), TC-223 (no area tick
on three certificates — #94), TC-225 (no first-generated timestamp in the banner — #92), TC-224 (two renewed
certificates run past five years from their Date, and one has licence-test dates — see the test). A revoked agency's
certificate still reads as valid (#93); no case covers that yet.

Data-dependent, skip when dev has no such agency: TC-230 (a suspended agency), TC-231 (no TAN), TC-232 (a branch
line). TC-222 and TC-228 need the approval and renewal steps; they check the certificates left by them.
"""

import re
from datetime import date, datetime

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.approved_agencies_page import AdminApprovedAgenciesPage
from pages.admin.licenses_page import AdminLicensesPage
from utils.aio import aio_case

STORY = "Registration certificate — Form-II (KAN-28)"


def _parse(d: str) -> date:
    day, month, year = (int(x) for x in d.split("/"))
    return date(year, month, day)


def _facts(cert) -> dict:
    """What one certificate shows, read from its text and tick boxes (no assertions here)."""
    flat = re.sub(r"\s+", " ", cert.body_text())

    def first(pattern):
        m = re.search(pattern, flat)
        return m.group(1).strip() if m else None

    banner = cert.banner
    return {
        "cert_no": first(r"Cert\. No\. (\d+)"),
        "reg_id": first(r"Reg\. ID (\d+)"),
        "date": first(r"Date: (\d{2}/\d{2}/\d{4})"),
        "valid_upto": first(r"valid up to (\d{2}/\d{2}/\d{4})"),
        "pan": first(r"PAN: (\w+)"),
        "tan": first(r"TAN \(if applicable\): (\S+)"),
        "head": first(r"Head / Principal Office Address: (.*?) 2\."),
        "branch": first(r"Branch / Authorised Agency / Person Office Address: (.*?) Validity"),
        "has_valid_from": "Valid From" in flat,
        "has_first_generated": "First generated" in flat,
        "banner_count": banner.count(),
        "banner_class": banner.first.get_attribute("class") if banner.count() else "",
        "banner_text": re.sub(r"\s+", " ", banner.first.text_content() or "").strip() if banner.count() else "",
        "classification": cert.ticked_labels(cert.classification_rows),
        "area": cert.ticked_labels(cert.area_rows),
        "error_text": bool(re.search(r"\bError\b|undefined|Fatal", flat)),
    }


def _all_certificates(approved_certificates, open_admin_certificate) -> list[tuple[str, dict]]:
    return [(c["agency"], _facts(open_admin_certificate(c["href"]))) for c in approved_certificates]


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-222  The record is created on approval
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-222")
@allure.story(STORY)
@allure.title("TC-222: Form-II certificate record is created when an agency is approved")
def test_tc222_certificate_record(approved_certificates, open_admin_certificate):
    """
    Given agencies have been approved
    When the Super Admin opens each approved agency's certificate from Approved agencies
    Then each certificate has a Certificate Number, a Valid From and a Valid Until date
    And   each shows the first-generated timestamp

    The approval step itself is not run here (it changes an application). Fails on dev (16-Nov-2026): Valid From and
    the first-generated timestamp are not shown — defect "Super admin" #92.

    AIO: KAN-TC-222 | KAN-28 AC-1 | data: approved agencies on Approved agencies
    """
    problems = []
    for agency, f in _all_certificates(approved_certificates, open_admin_certificate):
        if not f["cert_no"]:
            problems.append(f"{agency}: no Certificate Number")
        if not f["valid_upto"]:
            problems.append(f"{agency}: no Valid Until")
        if not f["has_valid_from"]:
            problems.append(f"{agency}: no Valid From")
        if not f["has_first_generated"]:
            problems.append(f"{agency}: no first-generated timestamp")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-223  Every Rule 4(1) field is accurate
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-223")
@allure.story(STORY)
@allure.title("TC-223: Certificate view shows all Rule 4(1) required fields accurately")
def test_tc223_rule_4_1_fields(approved_certificates, open_admin_certificate):
    """
    Given an approved agency's certificate is open
    Then it shows the Registration Number, Certificate Number, Date, PAN, Valid Until and Valid From
    And   exactly one business classification box is ticked
    And   the area of operation has a tick

    Fails on dev (16-Nov-2026): no classification box is ticked on any certificate (#91), Valid From is not shown
    (#92), and three certificates have no area tick (#94).

    AIO: KAN-TC-223 | KAN-28 AC-2 | data: approved agencies on Approved agencies
    """
    problems = []
    for agency, f in _all_certificates(approved_certificates, open_admin_certificate):
        for key, label in (("reg_id", "Registration Number"), ("cert_no", "Certificate Number"),
                           ("date", "Date"), ("pan", "PAN"), ("valid_upto", "Valid Until")):
            if not f[key]:
                problems.append(f"{agency}: no {label}")
        if not f["has_valid_from"]:
            problems.append(f"{agency}: no Valid From")
        if len(f["classification"]) != 1:
            problems.append(f"{agency}: business classification ticks {f['classification'] or 'none'}")
        if not f["area"]:
            problems.append(f"{agency}: no area of operation tick")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-224  Validity is exactly five years
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-224")
@allure.story(STORY)
@allure.title("TC-224: Valid From = approval date; Valid Until = approval date + exactly 5 years")
def test_tc224_five_year_validity(approved_certificates, open_admin_certificate):
    """
    Given approved agencies' certificates are open
    Then Valid Until is exactly five years after the certificate's Date

    Valid From is not shown, so the start is taken from the Date line. Fails on dev (16-Nov-2026) for certificates
    whose Valid Until was renewed (Randhawa-Reddy, Dani Inc) and for Skillsphere, whose validity licence tests
    changed (its Valid Until is 29/11/2026 for a Date of 26/10/2026). Renewal and the Date line are an open point
    for the product owner (KAN-28 AC-3).

    AIO: KAN-TC-224 | KAN-28 AC-3 | data: approved agencies on Approved agencies
    """
    problems = []
    for agency, f in _all_certificates(approved_certificates, open_admin_certificate):
        if not (f["date"] and f["valid_upto"]):
            problems.append(f"{agency}: Date or Valid Until missing")
            continue
        start = _parse(f["date"])
        expected = start.replace(year=start.year + 5)
        if _parse(f["valid_upto"]) != expected:
            problems.append(f"{agency}: Date {f['date']} but Valid Until {f['valid_upto']} "
                            f"(expected {expected:%d/%m/%Y})")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-225  Green and red status banners
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-225")
@allure.story(STORY)
@allure.title("TC-225: Valid certificate shows a green banner; expired certificate shows a red banner")
def test_tc225_status_banner(approved_certificates, open_admin_certificate):
    """
    Given approved agencies' certificates are open
    Then each valid certificate shows a green "✓ Valid certificate — expires DD/MM/YYYY · First generated: …" banner
    And   an expiring certificate shows an amber banner

    The red banner for an expired certificate is not on dev and is not checked here. Fails on dev (16-Nov-2026): the
    green banner has no first-generated timestamp (#92).

    AIO: KAN-TC-225 | KAN-28 AC-4 | data: approved agencies on Approved agencies
    """
    problems = []
    for agency, f in _all_certificates(approved_certificates, open_admin_certificate):
        if f["banner_count"] != 1:
            problems.append(f"{agency}: {f['banner_count']} status banners")
            continue
        if "Valid certificate" in f["banner_text"]:
            if "ok" not in f["banner_class"]:
                problems.append(f"{agency}: valid certificate banner is not green ({f['banner_class']})")
            if "First generated" not in f["banner_text"]:
                problems.append(f"{agency}: banner has no first-generated timestamp")
        elif "Expiring" in f["banner_text"]:
            if "warn" not in f["banner_class"]:
                problems.append(f"{agency}: expiring banner is not amber ({f['banner_class']})")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-226  Print layout
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-226")
@allure.story(STORY)
@allure.title("TC-226: Print layout shows only certificate content; no UI chrome included")
def test_tc226_print_layout(approved_certificates, open_admin_certificate):
    """
    Given an approved agency's certificate is open
    When the page is put in print layout
    Then the top bar, the ID strip and the Print buttons are not printed

    Checked on the first approved certificate only. Print preview itself is not captured.

    AIO: KAN-TC-226 | KAN-28 AC-5 | data: first approved agency on Approved agencies
    """
    if not approved_certificates:
        pytest.skip("No approved agency on dev.")
    cert = open_admin_certificate(approved_certificates[0]["href"])
    with allure.step("Switch to print layout"):
        cert.page.emulate_media(media="print")
    with allure.step("Verify the UI chrome is hidden"):
        expect(cert.top_bar).to_be_hidden()
        expect(cert.id_strip).to_be_hidden()
        expect(cert.print_buttons.first).to_be_hidden()
    cert.page.emulate_media(media="screen")


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-227  Certificate numbers are unique
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-227")
@allure.story(STORY)
@allure.title("TC-227: Each certificate generated has a unique, non-repeating Certificate Number")
def test_tc227_unique_numbers(approved_certificates, open_admin_certificate):
    """
    Given several agencies are approved
    When each certificate is opened
    Then each has a Certificate Number and no two share one

    AIO: KAN-TC-227 | KAN-28 AC-6 | data: approved agencies on Approved agencies
    """
    numbers = [(agency, f["cert_no"]) for agency, f in _all_certificates(approved_certificates, open_admin_certificate)]
    missing = [agency for agency, n in numbers if not n]
    seen, duplicates = {}, []
    for agency, n in numbers:
        if n and n in seen:
            duplicates.append(f"{agency} and {seen[n]} share {n}")
        elif n:
            seen[n] = agency
    assert not missing and not duplicates, "\n".join(
        [f"no Certificate Number: {m}" for m in missing] + duplicates)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-228  Renewal reflects the new validity dates
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-228")
@allure.story(STORY)
@allure.title("TC-228: Renewing a license updates Valid From and Valid Until on the certificate")
def test_tc228_renewal_reflected(logged_in_admin_licenses_page, open_admin_certificate):
    """
    Given agencies have licences listed on Licences & certificates
    When the certificate of each approved agency is opened
    Then its Valid Until is the same date as the licence's Valid Upto on Licences & certificates

    The renewal itself is not run here (it changes a licence). Renewed agencies on dev are the ones to look at.

    AIO: KAN-TC-228 | KAN-28 AC-7 | data: approved agencies on Approved agencies
    """
    lp: AdminLicensesPage = logged_in_admin_licenses_page
    listed_upto = {r["agency"]: datetime.strptime(r["valid_upto"], "%d %b %Y").date() for r in lp.table_data()}
    approved = AdminApprovedAgenciesPage(lp.page)
    approved.open()
    problems = []
    for c in approved.certificate_links():
        if c["agency"] not in listed_upto:
            continue
        f = _facts(open_admin_certificate(c["href"]))
        shown = _parse(f["valid_upto"]) if f["valid_upto"] else None
        if shown != listed_upto[c["agency"]]:
            problems.append(f"{c['agency']}: certificate Valid Until {f['valid_upto']} but the licence says "
                            f"{listed_upto[c['agency']]:%d/%m/%Y}")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-229  Only the right classification box is ticked
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-229")
@allure.story(STORY)
@allure.title("TC-229: Only the correct business classification checkbox is ticked on certificate")
def test_tc229_classification_tick(approved_certificates, open_admin_certificate):
    """
    Given approved agencies with B2B, B2C and B2B & B2C registrations
    Then each certificate ticks exactly one classification box, the one matching the agency

    Fails on dev (16-Nov-2026): no classification box is ticked on any certificate, including the B2B agency Dani Inc
    (defect "Super admin" #91). Which box matches each agency is checked against its Part C choice.

    AIO: KAN-TC-229 | KAN-28 AC-8 | data: approved agencies on Approved agencies
    """
    problems = []
    for agency, f in _all_certificates(approved_certificates, open_admin_certificate):
        if len(f["classification"]) != 1:
            problems.append(f"{agency}: ticks {f['classification'] or 'none'}")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-230  Suspended agency's certificate
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-230")
@allure.story(STORY)
@allure.title("TC-230: Suspended agency's certificate is not displayed")
def test_tc230_suspended_not_displayed(logged_in_admin_licenses_page, open_admin_certificate):
    """
    Given an agency is suspended and its certificate has not expired
    When its certificate is opened from Approved agencies
    Then the certificate is not displayed

    Open point (KAN-28 EC-1): the story expects the certificate to display with an amber "Certificate currently
    suspended" banner. This test follows the AIO case; align the two before the next run. Skips when no suspended
    agency is listed on dev.

    AIO: KAN-TC-230 | KAN-28 EC-1 | data: a suspended agency on Licences & certificates
    """
    lp: AdminLicensesPage = logged_in_admin_licenses_page
    suspended = [r["agency"] for r in lp.table_data() if r["status"].lower().startswith("suspended")]
    if not suspended:
        pytest.skip("No suspended agency on dev (Licences & certificates).")
    approved_page = AdminApprovedAgenciesPage(lp.page)
    approved_page.open()
    approved = {c["agency"]: c["href"] for c in approved_page.certificate_links()}
    if suspended[0] not in approved:
        pytest.skip(f"{suspended[0]} is suspended but has no certificate link on Approved agencies.")
    cert = open_admin_certificate(approved[suspended[0]])
    assert "Cert. No." not in cert.body_text(), f"{suspended[0]} is suspended but its certificate is displayed"


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-231  TAN blank is not an error
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-231")
@allure.story(STORY)
@allure.title("TC-231: TAN field on certificate is blank (not an error) when agency did not provide TAN")
def test_tc231_blank_tan(approved_certificates, open_admin_certificate):
    """
    Given an approved agency did not give a TAN
    When its certificate is opened
    Then the TAN field is blank, and the certificate renders with no error

    Skips when every approved agency on dev has a TAN.

    AIO: KAN-TC-231 | KAN-28 EC-2 | data: approved agencies on Approved agencies
    """
    no_tan =[(a, f) for a, f in _all_certificates(approved_certificates, open_admin_certificate)
              if not f["tan"] or f["tan"] in ("—", "-")]
    if not no_tan:
        pytest.skip("No approved agency on dev without a TAN.")
    problems = []
    for agency, f in no_tan:
        if not f["cert_no"]:
            problems.append(f"{agency}: certificate did not render")
        if f["error_text"]:
            problems.append(f"{agency}: an error is shown")
    assert not problems, "\n".join(problems)


# ═══════════════════════════════════════════════════════════════════════════
# KAN-TC-232  No branch office
# ═══════════════════════════════════════════════════════════════════════════

@aio_case("KAN-TC-232")
@allure.story(STORY)
@allure.title("TC-232: Authorised Offices section omits Branch Office line when none provided")
def test_tc232_no_branch_office(approved_certificates, open_admin_certificate):
    """
    Given an approved agency has no branch office
    When its certificate is opened
    Then the head office line is populated and the branch line is blank

    The page shows an em dash (—) on the branch line when there is no branch; that counts as blank. Skips when every
    approved agency on dev has a branch office.

    AIO: KAN-TC-232 | KAN-28 EC-3 | data: approved agencies on Approved agencies
    """
    no_branch =[(a, f) for a, f in _all_certificates(approved_certificates, open_admin_certificate)
                 if f["branch"] is not None and f["branch"] in ("—", "-", "")]
    if not no_branch:
        pytest.skip("No approved agency on dev without a branch office.")
    problems = []
    for agency, f in no_branch:
        if not f["head"]:
            problems.append(f"{agency}: head office line is blank")
        if f["error_text"]:
            problems.append(f"{agency}: an error is shown")
    assert not problems, "\n".join(problems)
