"""
Data Factory — First Appeal Management (FORM-III)
=================================================
Two value objects power this module's tests:

* ``FirstAppealData``  — what an *agency* enters when it files a FORM-III appeal
  on ``/module/agency/appeals/first.php``. Used by the seeding fixtures to put a
  filed appeal into a precise state (with documents / without documents /
  late-filed) before the admin-side assertions run.

* ``AppealOutcomeData`` — what an *admin* records when reviewing an appeal in the
  Appeals module (decision + remarks). Feeds the outcome tests.

Each value object carries ``scenario_label`` and ``expected_error`` meta fields,
matching the other factories in this project. Methods map to the AIO test cases
KAN-TC-360 through KAN-TC-368 (Admin Console · First Appeal Management).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


# ── Agency-side: filing a FORM-III appeal ──────────────────────────────────────

@dataclass
class FirstAppealData:
    order_number: str
    order_date: str                       # yyyy-mm-dd (native date input)
    order_authority: str
    grounds: list[str] = field(default_factory=list)   # FirstAppealPage.GROUNDS values
    grounds_other: str = ""
    brief_facts: str = ""
    relief_type: str = ""                 # FirstAppealPage.RELIEFS value
    relief_sought: str = ""
    comm_date: str = ""                   # yyyy-mm-dd
    within_time: str = "yes"              # 'yes' | 'no'
    delay_reason: str = ""
    documents: dict[str, str] = field(default_factory=dict)  # DOC_SLOTS key → path
    place: str = "Pune"
    signatory_name: str = "Ameya Ambekar"
    signatory_designation: str = "Director"
    scenario_label: str = ""
    expected_error: Optional[str] = None


class FirstAppealFactory:
    """Builds FORM-III filing payloads. A short timestamp is baked into the
    order number so each filed appeal is uniquely searchable in the admin list."""

    @staticmethod
    def _unique_order_no(prefix: str) -> str:
        return f"AUTO/FA/{prefix}/{int(time.time())}"

    # ── Valid appeal WITH supporting documents (KAN-TC-362) ───────────────────

    @staticmethod
    def valid_with_documents(file_path: str) -> FirstAppealData:
        """A complete, in-time appeal carrying all five supporting documents.

        ``file_path`` is reused for every enclosure slot so the admin detail
        view renders a full set of labelled download links."""
        return FirstAppealData(
            order_number=FirstAppealFactory._unique_order_no("DOCS"),
            order_date="2026-05-01",
            order_authority="Registering Authority, District Labour Office, Pune",
            grounds=["error_of_law", "procedural_irregularity"],
            brief_facts="Registration was rejected without considering the "
                        "documents already on record; this appeal is filed with "
                        "full supporting enclosures.",
            relief_type="Setting Aside the Order",
            relief_sought="Set aside the impugned order and direct registration.",
            comm_date="2026-05-03",
            within_time="yes",
            documents={
                "original": file_path,
                "ack":      file_path,
                "fees":     file_path,
                "order":    file_path,
                "other":    file_path,
            },
            scenario_label="valid_with_documents",
        )

    # ── Valid appeal WITHOUT any documents (KAN-TC-368) ───────────────────────

    @staticmethod
    def valid_without_documents() -> FirstAppealData:
        """A complete, in-time appeal with no enclosures, so the admin detail
        view should show the 'No documents uploaded' placeholder."""
        return FirstAppealData(
            order_number=FirstAppealFactory._unique_order_no("NODOCS"),
            order_date="2026-05-04",
            order_authority="Registering Authority, District Labour Office, Pune",
            grounds=["jurisdictional_error"],
            brief_facts="Appeal filed against the order; supporting documents "
                        "to be produced at the hearing.",
            relief_type="Remand for Fresh Consideration",
            relief_sought="Remand the matter for fresh consideration on merits.",
            comm_date="2026-05-06",
            within_time="yes",
            documents={},
            scenario_label="valid_without_documents",
        )

    # ── Late-filed appeal beyond the 30-day limitation (KAN-TC-366) ───────────

    @staticmethod
    def late_filed() -> FirstAppealData:
        """An appeal filed beyond the prescribed 30-day window: ``within_time``
        is 'no' and a condonation reason is supplied, so the admin Limitation
        section flags the delay and shows the stated reason."""
        return FirstAppealData(
            order_number=FirstAppealFactory._unique_order_no("LATE"),
            order_date="2026-03-01",
            order_authority="Registering Authority, District Labour Office, Pune",
            grounds=["natural_justice"],
            brief_facts="The order was communicated late and the appellant was "
                        "unable to file within the prescribed period.",
            relief_type="Modification of Order",
            relief_sought="Modify the order and condone the delay in filing.",
            comm_date="2026-03-05",
            within_time="no",
            delay_reason="The impugned order reached the agency only on 2026-04-20 "
                         "owing to a postal delay; condonation of the delay is "
                         "prayed for in the interest of justice.",
            documents={},
            scenario_label="late_filed",
        )

    # ── Plain valid appeal (generic seed) ─────────────────────────────────────

    @staticmethod
    def valid() -> FirstAppealData:
        return FirstAppealData(
            order_number=FirstAppealFactory._unique_order_no("STD"),
            order_date="2026-05-10",
            order_authority="Registering Authority, District Labour Office, Pune",
            grounds=["procedural_irregularity"],
            brief_facts="Appeal filed against the registration order.",
            relief_type="Setting Aside the Order",
            relief_sought="Set aside the impugned order.",
            comm_date="2026-05-12",
            within_time="yes",
            scenario_label="valid",
        )


# ── Admin-side: recording an appeal outcome ────────────────────────────────────

@dataclass
class AppealOutcomeData:
    decision: str                         # AdminAppealsPage.DECISIONS value
    remarks: str = ""
    hearing_date: Optional[str] = None    # yyyy-mm-dd, optional
    scenario_label: str = ""
    expected_error: Optional[str] = None


class AppealOutcomeFactory:

    # ── KAN-TC-363 — Allow with mandatory remarks ─────────────────────────────

    @staticmethod
    def allowed_with_remarks() -> AppealOutcomeData:
        return AppealOutcomeData(
            decision="allow",
            remarks="Appeal accepted on grounds of procedural irregularity.",
            scenario_label="allowed_with_remarks",
        )

    # ── KAN-TC-364 — Save blocked when remarks are blank ──────────────────────

    @staticmethod
    def rejected_blank_remarks() -> AppealOutcomeData:
        return AppealOutcomeData(
            decision="reject",
            remarks="",
            scenario_label="rejected_blank_remarks",
            expected_error="Remarks are required when recording an appeal outcome.",
        )

    # ── KAN-TC-365 — Allow with remarks for the audit-trail check ──────────────

    @staticmethod
    def allowed_for_audit() -> AppealOutcomeData:
        return AppealOutcomeData(
            decision="allow",
            remarks="Approved after document verification.",
            scenario_label="allowed_for_audit",
        )
