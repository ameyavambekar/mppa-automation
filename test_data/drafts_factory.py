"""
Data Factory — Registrations in Progress (admin drafts)
======================================================
Inputs and expectations for the Registrations in Progress page (KAN-45). The
drafts themselves are live dev data; the tests use agencies the state store knows
(so their username, e-mail, mobile, PAN and district can be checked) or register a
throwaway agency to delete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pages.admin.drafts_page import AdminDraftsPage


@dataclass
class DraftsData:
    scenario_label: str = ""
    filter_value: Optional[str] = None
    query: Optional[str] = None
    extend_days: Optional[str] = None
    expected_message: Optional[str] = None
    deadline_days: Optional[int] = None
    expected_error: Optional[str] = None


class DraftsFactory:

    # Days from registration to the deadline, before any extension
    DEADLINE_DAYS = 7

    @classmethod
    def extend(cls, days: str = "3") -> DraftsData:
        """days: one of AdminDraftsPage.EXTEND_DAYS."""
        return DraftsData(scenario_label=f"extend_{days}_days", extend_days=days,
                          expected_message=AdminDraftsPage.extended_message(days))

    @classmethod
    def unknown_filter(cls) -> DraftsData:
        """Any ``f`` outside AdminDraftsPage.FILTERS shows All drafts."""
        return DraftsData(scenario_label="unknown_filter", filter_value="bogus")

    @classmethod
    def no_match_search(cls) -> DraftsData:
        return DraftsData(scenario_label="no_match_search", query="zz-no-such-draft-zz",
                          expected_message=AdminDraftsPage.EMPTY_SEARCH)

    @classmethod
    def deadline_rule(cls) -> DraftsData:
        return DraftsData(scenario_label="deadline_rule", deadline_days=cls.DEADLINE_DAYS)

    @classmethod
    def delete_confirmation(cls) -> DraftsData:
        return DraftsData(scenario_label="delete_confirmation", expected_message=AdminDraftsPage.DELETE_CONFIRM)
