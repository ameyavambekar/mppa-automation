"""
Data Factory — Admin Dashboard
==============================
Filter choices for the Admin Dashboard (module/admin/index.php, "MPPA Officer Console") and
what the dashboard header shows for each. Observed on the dev site on 02-Nov-2026 as the
Super Administrator.

Choosing a division reloads the dashboard for that division: the heading becomes
"<division> — Dashboard", the crumb gains "Maharashtra ›" and a District filter
("All districts" + that division's districts) appears.

Usage
-----
    from test_data.admin_dashboard_factory import AdminDashboardData, AdminDashboardFactory

    data = AdminDashboardFactory.pune_division()
    dashboard.select_division(data.division)
    expect(dashboard.dashboard_heading).to_have_text(data.heading)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdminDashboardData:
    division: str = ""                  # Division filter option label
    heading: str = ""                   # dashboard heading once that division is chosen
    districts: list[str] = field(default_factory=list)   # District filter options (after "All districts")
    scenario_label: str = ""


class AdminDashboardFactory:

    STATE = "All divisions (State)"
    # Division filter options after "All divisions (State)", in page order (option values 5, 4, 1, 6, 3, 2)
    DIVISIONS = ("Amravati Division", "Chhatrapati Sambhajinagar Division", "Konkan Division",
                 "Nagpur Division", "Nashik Division", "Pune Division")

    @staticmethod
    def state_wide() -> AdminDashboardData:
        """The default view: every division, no District filter."""
        return AdminDashboardData(division=AdminDashboardFactory.STATE, heading="Maharashtra State — Dashboard",
                                  scenario_label="state_wide")

    @staticmethod
    def pune_division() -> AdminDashboardData:
        """Pune Division and its five districts."""
        return AdminDashboardData(division="Pune Division", heading="Pune Division — Dashboard",
                                  districts=["Kolhapur", "Pune", "Sangli", "Satara", "Solapur"],
                                  scenario_label="pune_division")
