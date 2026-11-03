# utils/agency_status_sync.py
"""
Agency status sync
==================
Reads where every agency stands on the Officer Console and records it in the
state store (``TestStateStore.record_agency_status``):

* Registrations in Progress — Filling form / Ready to pay / Expired drafts, by username
* Applications — Desktop scrutiny / Physical verification / Branch office
  verification (with the review state: Under review / Compliance — with agency /
  Show cause / hearing), Rejected and Suspended / cancelled, by Application ID
* Licences & certificates — Active / Expiring / Expired / Suspended / Revoked, by
  Registration No. (the Application ID)
* Appeals — First Appeals (Division) and Second Appeals (Commissionerate)

Later sources win (an appealed application is still listed as Rejected; an
approved one under Licences). A known agency that has not paid and is no longer
a draft was deleted on the portal and is recorded as ``deleted``. An agency
with an Application ID that no list shows keeps its status.

Run it from the repo root before a test run that needs agencies in a given
state (it logs in as the Super Admin from ``.env``)::

    python -m utils.agency_status_sync

or call ``sync_agency_statuses(page)`` with a page logged in as the Super Admin.
"""

from __future__ import annotations

import os
from collections import Counter

from pages.admin.appeals_page import AdminAppealsPage
from pages.admin.applications_page import AdminApplicationsPage
from pages.admin.drafts_page import AdminDraftsPage
from pages.admin.licenses_page import AdminLicensesPage
from utils.state_store import TestStateStore

# Registrations in Progress filter → status
DRAFT_FILTERS = {"progress": "filling_form", "ready": "ready_to_pay", "expired": "draft_expired"}
# Applications stage view → status, and review step → status_data["review"]
STAGE_VIEWS = {"desktop": "desktop_scrutiny", "physical": "physical_verification", "branches": "branch_verification"}
REVIEW_STEPS = {"review": "under_review", "agency": "with_agency", "hearing": "show_cause"}
DECIDED_VIEWS = {"rejected": "rejected", "suspended": "suspended"}
APPEAL_VIEWS = {"first": "first_appeal", "second": "second_appeal"}


def _licence_status(label: str) -> str:
    """Licences & certificates status label ("Active", "Expiring", "Expired", "Suspended", "Revoked",
    "Cancelled") → agency status."""
    label = label.lower()
    if "suspend" in label:
        return "suspended"
    if "revok" in label or "cancel" in label:
        return "revoked"
    if "expired" in label:
        return "licence_expired"
    return "approved"


def read_console_statuses(page) -> tuple[dict, dict]:
    """Reads the console with ``page`` (logged in as the Super Admin). Returns ``(drafts, applications)``:
    username → (status, data) for drafts, and Application ID → (status, data, e-mail) for paid ones."""
    drafts = {}
    dp = AdminDraftsPage(page)
    for filter_, status in DRAFT_FILTERS.items():
        dp.open(filter_=filter_)
        for r in dp.table_data():
            username = r["sub"].split(" · ")[0].lstrip("@")
            drafts[username] = (status, {"deadline": r["deadline"], "progress": r["progress"]})

    applications = {}
    ap = AdminApplicationsPage(page)
    for view, status in STAGE_VIEWS.items():
        for step, review in REVIEW_STEPS.items():
            ap.open(view, step)
            for r in ap.table_data():
                applications.setdefault(r["application_id"], (status, {"review": review}, r["email"]))
    for view, status in DECIDED_VIEWS.items():
        ap.open(view)
        for r in ap.table_data():
            applications[r["application_id"]] = (status, {"decided": r["period"].removeprefix("Decided ")}, r["email"])

    lp = AdminLicensesPage(page)
    lp.open(status="all")
    for r in lp.table_data():
        email = r["email"] or applications.get(r["registration_no"], (None, None, ""))[2]
        applications[r["registration_no"]] = (_licence_status(r["status"]),
                                              {"licence": r["status"], "valid_till": r["valid_upto"]}, email)

    appeals = AdminAppealsPage(page)
    for view, status in APPEAL_VIEWS.items():
        appeals.open_view(view)
        for r in appeals.view_table_data():
            email = applications.get(r["application_id"], (None, None, ""))[2]
            applications[r["application_id"]] = (status, {"appeal_status": r["badges"][-1] if r["badges"] else ""},
                                                 email)
    return drafts, applications


def sync_agency_statuses(page, store: TestStateStore = None) -> Counter:
    """Records the console status of every agency the state store knows. Returns how many agencies
    went to each status, plus "unlisted" for submitted ones no list shows."""
    store = store or TestStateStore()
    drafts, applications = read_console_statuses(page)
    by_email = Counter(email for _, _, email in applications.values() if email)
    email_to_id = {email: app_id for app_id, (_, _, email) in applications.items() if by_email[email] == 1}
    agencies = store.get_agency_users(include_deleted=True)
    store_emails = Counter(u.email for u in agencies if u.email)

    summary = Counter()
    for user in agencies:
        application_id = user.application_id
        if not application_id and user.email in email_to_id and store_emails[user.email] == 1 \
                and user.username not in drafts:
            # Paid outside the automation — the console's e-mail ties it to one Application ID
            application_id = email_to_id[user.email]
            store.record_application_id(username=user.username, application_id=application_id)
        if user.username in drafts:
            status, data = drafts[user.username]
        elif application_id in applications:
            status, data, _ = applications[application_id]
        elif not application_id and drafts and user.steps.get("payment") != "completed":
            status, data = "deleted", None
        else:
            summary["unlisted"] += 1
            continue
        store.record_agency_status(username=user.username, status=status, data=data)
        summary[status] += 1
    return summary


def main() -> None:
    from dotenv import load_dotenv
    from playwright.sync_api import sync_playwright

    from config import ADMIN_LOGOUT_URL
    from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
    from pages.admin.login_page import AdminLoginPage

    load_dotenv()
    store = TestStateStore()
    username, password = os.getenv("ADMIN_SUPER_USERNAME"), os.getenv("ADMIN_SUPER_PASSWORD")
    if not (username and password):
        admin = store.get_any_super_admin()
        if admin is None:
            raise SystemExit("Set ADMIN_SUPER_USERNAME / ADMIN_SUPER_PASSWORD in .env (or seed a super_admin).")
        username, password = admin.username, admin.password
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        login = AdminLoginPage(page)
        login.open()
        error = login.login_past_captcha(username, password)
        if error:
            raise SystemExit(f"Admin login as {username} failed: {error}")
        page.wait_for_url(ADMIN_DASHBOARD_URL)
        try:
            summary = sync_agency_statuses(page, store)
        finally:
            page.goto(ADMIN_LOGOUT_URL, wait_until="domcontentloaded")
            browser.close()
    for status, count in sorted(summary.items()):
        print(f"{status:24} {count}")


if __name__ == "__main__":
    main()
