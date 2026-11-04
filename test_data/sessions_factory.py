"""
Data Factory — Admin Session Management (KAN-32)
================================================
Expectations for the Session Management page, KAN-TC-246…256 and 715…722.

Almost every session scenario is driven by live table state (which agency is
logged in, which row is open, which username to search), so there is little
static input data. This factory owns the fixed expectations — column names,
dialog texts, reasons, the page title — so the tests stay free of magic strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class SessionData:
    scenario_label: str = ""
    search_query: Optional[str] = None          # resolved from the table at runtime
    expected_dialog_fragment: Optional[str] = None
    expected_reason: Optional[str] = None
    expected_status: Optional[str] = None
    expected_columns: tuple = ()
    tile_labels: dict = field(default_factory=dict)
    expected_error: Optional[str] = None


class SessionsFactory:

    # Canonical column order shown in the table
    COLUMNS = (
        "#", "Status", "Agency", "Username", "Login IP", "Login Time",
        "Last Ping", "Logout / End", "Duration", "Reason", "Action",
    )

    # tile type → label shown on the summary tile
    TILE_LABELS = {"all": "Total", "live": "Live Now", "stale": "Stale", "ended": "Ended"}
    TAB_LABELS = {"all": "All", "live": "Live", "stale": "Stale", "ended": "Ended"}
    STATUS_BADGE = {"live": "Live", "stale": "Stale", "ended": "Ended"}

    PAGE_SIZE = 20
    HEADING = "Session Management"
    SEARCH_PLACEHOLDER = "Search agency, username, IP…"
    CONFIRM_KILL = "Terminate this session?"
    CONFIRM_KILL_ALL = "Kill ALL active sessions now?"
    EMPTY_LIST = "No sessions found."
    OPEN_END = ("—", "Online")                   # Logout / End of an open row: Stale shows —, Live shows Online
    KILLED_REASON = "kill"                       # "killed" (or similar) — matched as a fragment
    END_REASONS = ("manual", "timeout", "inactivity", "killed", "logout")
    EXPECTED_TITLE = "Active Sessions — MPPA Officer Console"
    CLOCK_FORMAT = "%d %b %Y · %H:%M"
    CLOCK_TOLERANCE_MINUTES = 2
    DURATION_TOLERANCE_MINUTES = 2
    OPEN_FOR_HOURS = 24                          # TC-254 / TC-255: an open session older than this
    SPECIAL_SEARCHES = ("O'Brien", "<b>x</b>")
    PAGE_BEYOND_LAST = 999
    BAD_PAGES = ("0", "abc")
    UNKNOWN_TYPE = "bogus"

    @staticmethod
    def now_ist() -> datetime:
        return datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)

    @staticmethod
    def parse_duration(text: str) -> timedelta:
        """'24h 31m' / '1m 31s' / '2s' / '1d 2h' → timedelta."""
        import re
        units = {"d": "days", "h": "hours", "m": "minutes", "s": "seconds"}
        parts = re.findall(r"(\d+)\s*([dhms])", text)
        if not parts:
            raise ValueError(f"Not a duration: {text!r}")
        return timedelta(**{units[u]: int(n) for n, u in parts})

    # ── Scenario data ─────────────────────────────────────────────────────────

    @classmethod
    def dashboard_tiles(cls) -> SessionData:
        return SessionData(scenario_label="dashboard_tiles", expected_columns=cls.COLUMNS,
                           tile_labels=cls.TILE_LABELS)

    @classmethod
    def all_tab_layout(cls) -> SessionData:
        return SessionData(scenario_label="all_tab_layout", expected_columns=cls.COLUMNS)

    @classmethod
    def kill_single_session(cls) -> SessionData:
        return SessionData(scenario_label="kill_single_session", expected_dialog_fragment=cls.CONFIRM_KILL,
                           expected_reason=cls.KILLED_REASON, expected_status="Ended")

    @classmethod
    def kill_then_redirect(cls) -> SessionData:
        return SessionData(scenario_label="kill_then_redirect", expected_dialog_fragment=cls.CONFIRM_KILL,
                           expected_reason=cls.KILLED_REASON, expected_status="Ended",
                           expected_error="administrator")

    @classmethod
    def kill_all_confirmation(cls) -> SessionData:
        return SessionData(scenario_label="kill_all_confirmation", expected_dialog_fragment=cls.CONFIRM_KILL_ALL,
                           expected_reason=cls.KILLED_REASON, expected_status="Ended")

    @classmethod
    def search_by(cls, query: str) -> SessionData:
        return SessionData(scenario_label="search_sessions", search_query=query)

    @classmethod
    def stale_session_row(cls) -> SessionData:
        return SessionData(scenario_label="open_and_ended_rows", expected_status="Stale", expected_reason="—")

    @classmethod
    def no_ping_session(cls) -> SessionData:
        return SessionData(scenario_label="no_ping_session", expected_reason="No ping", expected_status="Stale")

    @classmethod
    def kill_all_disabled(cls) -> SessionData:
        return SessionData(scenario_label="kill_all_disabled", expected_error=cls.EMPTY_LIST)
