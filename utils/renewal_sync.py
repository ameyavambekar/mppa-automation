# utils/renewal_sync.py
"""
Renewal sync
============
Reads every licence renewal application from the officer's Renewal applications page
(``admin/licenses/renewals.php?tab=all``) and records it in the state store
(``TestStateStore.record_renewal``): number, agency (by Registration No.), status, date filed,
payment reference, the two declarations and, once decided, the decision date, officer and — for a
renewed one — the new expiry. Remarks are not on the list; tests record them when they decide.

``utils.agency_status_sync`` runs it as part of the agency sync. On its own, from the repo root
(logs in as the Super Admin from ``.env``)::

    python -m utils.renewal_sync

or call ``sync_renewals(page)`` with a page logged in as the Super Admin.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Optional

from pages.admin.renewals_page import AdminRenewalsPage
from utils.state_store import TestStateStore

# Status badge on the officer's page → RENEWAL_STATUSES
STATUSES = {AdminRenewalsPage.PENDING: "pending", AdminRenewalsPage.RENEWED: "renewed",
            AdminRenewalsPage.REJECTED: "rejected"}
_DATE = r"\d{2} [A-Z][a-z]{2} \d{4}"


def iso(date_text: Optional[str]) -> Optional[str]:
    """'13 Nov 2026' (anywhere in the text) → '2026-11-13'; None when there is no such date."""
    match = re.search(_DATE, date_text or "")
    return datetime.strptime(match.group(), "%d %b %Y").date().isoformat() if match else None


def renewal_facts(row: dict) -> dict:
    """The state-store facts of one ``AdminRenewalsPage.row_data()`` row (plus ``number``, ``registration_no``
    and ``status``)."""
    declarations = re.search(r"Changes since registration: (No|Yes) Cases / suspension: (No|Yes)",
                              row["declarations"])
    decided = row["decided"].split(" · ", 1) if row["decided"] else [None, None]
    renewed_to = re.search(rf"Renewed to ({_DATE})", row["validity"])
    return {
        "number": int(row["number"]),
        "registration_no": row["reg"],
        "status": STATUSES[row["status"]],
        "filed_on": iso(row["applied"]),
        "payment_ref": row["reference"] or None,
        "changes_made": declarations.group(1).lower() if declarations else None,
        "cases_pending": declarations.group(2).lower() if declarations else None,
        "decided_on": iso(decided[0]),
        "decided_by": decided[1] if len(decided) > 1 else None,
        "valid_upto": iso(renewed_to.group(1)) if renewed_to else None,
    }


def record_rows(rows: list[dict], store: TestStateStore = None) -> Counter:
    """Records ``AdminRenewalsPage.row_data()`` rows. Returns how many went to each status, plus "unknown
    agency" for renewals of agencies the store does not know (recorded without a user)."""
    store = store or TestStateStore()
    known = {u.application_id for u in store.get_agency_users(include_deleted=True) if u.application_id}
    summary = Counter()
    for row in rows:
        facts = renewal_facts(row)
        store.record_renewal(**facts)
        summary[facts["status"]] += 1
        if facts["registration_no"] not in known:
            summary["unknown agency"] += 1
    return summary


def sync_renewals(page, store: TestStateStore = None) -> Counter:
    """Reads the All tab of Renewal applications (the page must be logged in as the Super Admin, who sees every
    district) and records every renewal application."""
    renewals = AdminRenewalsPage(page)
    renewals.open(tab="all")
    return record_rows(renewals.row_data(), store)


def main() -> None:
    from dotenv import load_dotenv
    from playwright.sync_api import sync_playwright

    from utils.agency_status_sync import super_admin_page

    load_dotenv()
    store = TestStateStore()
    with sync_playwright() as p:
        with super_admin_page(p, store) as page:
            summary = sync_renewals(page, store)
    for status, count in sorted(summary.items()):
        print(f"{status:24} {count}")


if __name__ == "__main__":
    main()
