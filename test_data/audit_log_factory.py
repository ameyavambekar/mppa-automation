"""
Data Factory — Audit Log
========================
Inputs and expectations for the Audit Log page (KAN-36). The events themselves are
live dev data, so the tests read them from the page; this factory holds what each
action type is expected to record (table, Record ID, detail keys), the searches and
the invalid filter values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pages.admin.audit_log_page import AdminAuditLogPage


@dataclass(frozen=True)
class AuditActionSpec:
    """What one action type writes: its pill label, table, whether it carries a Record ID, its detail keys
    (in display order) and its dropdown group."""
    action: str
    label: str
    table: str
    has_record_id: bool
    detail_keys: tuple
    group: str = "── Other ──"


@dataclass
class AuditLogData:
    scenario_label: str = ""
    query: Optional[str] = None
    date_f: Optional[str] = None
    action_f: Optional[str] = None
    page: Optional[int] = None
    expected_message: Optional[str] = None
    expected_error: Optional[str] = None
    actions: dict = field(default_factory=dict)


class AuditLogFactory:

    # KAN-36 "Action Types" table (02-Nov-2026)
    ACTIONS = {spec.action: spec for spec in (
        AuditActionSpec("AGENCY_APPROVE", "Agency Approved", "agency_registrations", True,
                        ("reg_id", "mppa_number", "new_status", "admin", "remarks"), "── Agency ──"),
        AuditActionSpec("LOGIN", "Agency Login", "agency_registrations", True, ("username", "ip", "status"),
                        "── Sessions ──"),
        AuditActionSpec("ADMIN_LOGIN", "Admin Login", "admin_users", True, ("username", "ip", "role"), "── Admin ──"),
        AuditActionSpec("ADMIN_LOGIN_FAILED", "ADMIN_LOGIN_FAILED", "admin_users", False, ("username", "ip")),
        AuditActionSpec("CERTIFICATE_EXPIRE", "CERTIFICATE_EXPIRE", "agency_approvals", True, ("details", "until")),
        AuditActionSpec("DRAFT_DELETE", "DRAFT_DELETE", "temp_draft_registration", False, ("token", "by")),
        AuditActionSpec("DRAFT_EXTEND", "DRAFT_EXTEND", "temp_draft_registration", False, ("token", "days", "by")),
        AuditActionSpec("DRAFT_LOGIN", "DRAFT_LOGIN", "temp_draft_registration", False,
                        ("username", "ip", "continue_at")),
        AuditActionSpec("JOB_SEEKER_APPROVED", "JOB_SEEKER_APPROVED", "agency_job_seekers", True, ("by", "agency_id")),
        AuditActionSpec("PASSWORD_RESET_DONE", "PASSWORD_RESET_DONE", "temp_draft_registration", False,
                        ("username", "ip")),
        AuditActionSpec("PASSWORD_RESET_VERIFIED", "PASSWORD_RESET_VERIFIED", "temp_draft_registration", False,
                        ("username", "ip")),
        AuditActionSpec("PAYMENT_COMMIT", "PAYMENT_COMMIT", "agency_registrations", True,
                        ("action", "reg_id", "district", "ip")),
        AuditActionSpec("SECTION_REVIEW_SAVE", "SECTION_REVIEW_SAVE", "agency_registrations", True, ("admin", "items")),
    )}

    NO_MATCH_QUERY = "zz-no-such-event-zz"

    @classmethod
    def action_types(cls) -> AuditLogData:
        return AuditLogData(scenario_label="action_types", actions=cls.ACTIONS)

    @classmethod
    def no_match_search(cls) -> AuditLogData:
        return AuditLogData(scenario_label="no_match_search", query=cls.NO_MATCH_QUERY,
                            expected_message=AdminAuditLogPage.EMPTY)

    @classmethod
    def admin_login_today(cls) -> AuditLogData:
        """Today's Admin Login events — the Super Admin's own login guarantees at least one."""
        return AuditLogData(scenario_label="admin_login_today", date_f="today", action_f="ADMIN_LOGIN")

    @classmethod
    def all_filters(cls) -> AuditLogData:
        return AuditLogData(scenario_label="all_filters", query="super", date_f="week", action_f="ADMIN_LOGIN")

    @classmethod
    def unknown_date_filter(cls) -> AuditLogData:
        """Any date_f other than today/week/month is All Time."""
        return AuditLogData(scenario_label="unknown_date_filter", date_f="bogus")

    @classmethod
    def unknown_action_filter(cls) -> AuditLogData:
        """An action_f the log does not hold lists nothing."""
        return AuditLogData(scenario_label="unknown_action_filter", action_f="BOGUS")

    @classmethod
    def html_search(cls) -> AuditLogData:
        """Echoed back into the search box escaped, never run."""
        return AuditLogData(scenario_label="html_search", query="<script>alert(1)</script>")

    @classmethod
    def page_beyond_last(cls) -> AuditLogData:
        return AuditLogData(scenario_label="page_beyond_last", page=999)
