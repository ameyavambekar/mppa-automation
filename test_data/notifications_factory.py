"""
Data Factory — Admin Notifications
==================================
Expectations for the officer Notifications page (KAN-44): the jurisdiction the
subtitle names, the texts of the notifications the portal raises, the colour of
each type's dot and the filter values.

Which notifications exist is live dev data, so the tests read them from the page;
only the notification a test raises itself (a "New application" one, by paying for
an agency) has its title and body built here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pages.admin.notifications_page import AdminNotificationsPage


@dataclass
class NotificationsData:
    scenario_label: str = ""
    jurisdiction: Optional[str] = None
    expected_title: Optional[str] = None
    expected_body: Optional[str] = None
    expected_meta_label: Optional[str] = None
    expected_colour: Optional[str] = None
    filter_value: Optional[str] = None
    expected_error: Optional[str] = None


class NotificationsFactory:

    NEW_APPLICATION_BODY = "Paid and submitted — Desktop Scrutiny can start. The 45-day period has begun."
    SLA_BODY = "The statutory period is over. Decide immediately."

    @classmethod
    def state_wide(cls) -> NotificationsData:
        """The Super Administrator sees the whole state."""
        return NotificationsData(scenario_label="state_wide", jurisdiction=AdminNotificationsPage.STATE_JURISDICTION)

    @classmethod
    def new_application(cls, agency_name: str, application_id: str) -> NotificationsData:
        """Raised for officers when an agency pays and submits its application."""
        return NotificationsData(
            scenario_label="new_application",
            expected_title=f"New application: {agency_name} ({application_id})",
            expected_body=cls.NEW_APPLICATION_BODY,
            expected_meta_label=f"New application · {agency_name} ({application_id})",
            expected_colour=AdminNotificationsPage.TYPE_COLOURS["new"],
        )

    @classmethod
    def unknown_filter(cls) -> NotificationsData:
        """Any ``f`` other than 'unread' shows the All list."""
        return NotificationsData(scenario_label="unknown_filter", filter_value="bogus")

    @classmethod
    def district_officer(cls, district: str) -> NotificationsData:
        """A District Officer sees only the agencies of their district."""
        return NotificationsData(scenario_label="district_officer", jurisdiction=district)
