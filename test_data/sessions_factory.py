"""
Data Factory — Admin Session Management
=======================================
Centralises the (mostly meta) test data for the Session Management dashboard,
KAN-TC-246 through KAN-TC-256.

Unlike the licensing module, almost every session scenario is driven by *live*
table state captured at runtime (which user is logged in, which row is stale,
etc.), so there is little static input data. What this factory does own is the
set of fixed *expectations* each case asserts against — column names, tile
labels, the confirm-dialog text fragments and the reason/status a kill produces
— kept here so the tests stay free of magic strings.

Note on dialog wording: the AIO spec describes an idealised Kill-All dialog
("This will terminate all N active sessions…"). The live build uses a native
``confirm('Kill ALL active sessions now?')``, so the asserted fragment matches
the real implementation ('active'), not the spec's exact sentence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

    # tile type → label fragment shown on the summary tiles
    TILE_LABELS = {
        "all": "Total",
        "live": "Live",
        "stale": "Stale",
        "ended": "Ended",
    }

    # A session inactive beyond this many hours is classified Stale
    STALE_THRESHOLD_HOURS = 48

    # ── TC-246 — five summary tiles ───────────────────────────────────────────

    @classmethod
    def dashboard_tiles(cls) -> SessionData:
        return SessionData(
            scenario_label="dashboard_tiles",
            expected_columns=cls.COLUMNS,
            tile_labels=cls.TILE_LABELS,
        )

    # ── TC-247 — All tab, all columns, reverse-chronological ─────────────────

    @classmethod
    def all_tab_layout(cls) -> SessionData:
        return SessionData(
            scenario_label="all_tab_layout",
            expected_columns=cls.COLUMNS,
        )

    # ── TC-249 — kill a single live session ──────────────────────────────────

    @classmethod
    def kill_single_session(cls) -> SessionData:
        return SessionData(
            scenario_label="kill_single_session",
            expected_dialog_fragment="Terminate",
            expected_reason="killed",
            expected_status="Ended",
        )

    # ── TC-250 — killed user is bounced to login ─────────────────────────────

    @classmethod
    def kill_then_redirect(cls) -> SessionData:
        return SessionData(
            scenario_label="kill_then_redirect",
            expected_dialog_fragment="Terminate",
            expected_reason="killed",
            expected_status="Ended",
        )

    # ── TC-251 / TC-252 — Kill-All confirmation dialog ───────────────────────

    @classmethod
    def kill_all_confirmation(cls) -> SessionData:
        return SessionData(
            scenario_label="kill_all_confirmation",
            # Matches the live build's confirm() text ('Kill ALL active sessions now?')
            expected_dialog_fragment="active",
        )

    # ── TC-253 — real-time search ────────────────────────────────────────────

    @classmethod
    def search_by(cls, query: str) -> SessionData:
        """Search seed — ``query`` is a username/agency/IP read from the table
        at runtime."""
        return SessionData(scenario_label="search_sessions", search_query=query)

    # ── TC-254 — stale session row ───────────────────────────────────────────

    @classmethod
    def stale_session_row(cls) -> SessionData:
        return SessionData(
            scenario_label="stale_session_row",
            expected_status="Stale",
            expected_reason="—",
        )

    # ── TC-255 — 'No ping' edge case ─────────────────────────────────────────

    @classmethod
    def no_ping_session(cls) -> SessionData:
        return SessionData(
            scenario_label="no_ping_session",
            expected_reason="No ping",
        )

    # ── TC-256 — Kill-All unavailable with no active sessions ────────────────

    @classmethod
    def kill_all_disabled(cls) -> SessionData:
        return SessionData(scenario_label="kill_all_disabled")
