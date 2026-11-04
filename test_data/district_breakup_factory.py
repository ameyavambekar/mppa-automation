"""
Data Factory — Admin District breakup report
============================================
Expected values for the District breakup report tests (KAN-47, AIO KAN-TC-678…694).

The report is read-only: its counts come from the live applications, so the tests compare the page with
itself and with Applications / Licences & certificates instead of with fixed numbers. This factory holds
the fixed expectations: the revenue division of every district, the page title and the IST clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class DistrictCountChange:
    """How a district's row should move after an action (deltas per column)."""
    total: int = 0
    approved: int = 0
    submitted: int = 0
    rejected: int = 0
    suspended: int = 0
    scenario_label: str = ""

    def as_dict(self) -> dict[str, int]:
        return {"total": self.total, "approved": self.approved, "submitted": self.submitted,
                "rejected": self.rejected, "suspended": self.suspended}


class DistrictBreakupFactory:

    # Page title in the Officer Console's "<Page> — MPPA Officer Console" form (EC-8)
    EXPECTED_TITLE = "District Breakup — MPPA Officer Console"
    OTHER_DISTRICT = "Other"
    # Allowed difference between the page clock and IST (the clock has no seconds)
    CLOCK_TOLERANCE = timedelta(minutes=2)

    # Maharashtra's six revenue divisions and their districts, as the report names them
    DIVISIONS = {
        "Konkan": ("Mumbai City", "Mumbai Suburban", "Thane", "Palghar", "Raigad", "Ratnagiri", "Sindhudurg"),
        "Pune": ("Pune", "Satara", "Sangli", "Solapur", "Kolhapur"),
        "Nashik": ("Nashik", "Ahilyanagar", "Dhule", "Jalgaon", "Nandurbar"),
        "Chhatrapati Sambhajinagar": ("Chhatrapati Sambhajinagar", "Jalna", "Beed", "Dharashiv", "Latur",
                                      "Nanded", "Parbhani", "Hingoli"),
        "Amravati": ("Amravati", "Akola", "Washim", "Buldhana", "Yavatmal"),
        "Nagpur": ("Nagpur", "Wardha", "Bhandara", "Gondia", "Chandrapur", "Gadchiroli"),
    }

    @classmethod
    def division_of(cls, district: str) -> str | None:
        for division, districts in cls.DIVISIONS.items():
            if district in districts:
                return division
        return None

    @staticmethod
    def now_ist() -> datetime:
        return datetime.now(IST).replace(tzinfo=None)

    @staticmethod
    def bar_width(count: int, highest: int) -> int:
        """The expected bar width in %: count relative to the highest, rounded (half up) to a whole %."""
        return int(count * 100 / highest + 0.5)

    # ── Expected changes ──────────────────────────────────────────────────────

    @staticmethod
    def suspension() -> DistrictCountChange:
        """A Route B case suspends an approved agency: it moves from Approved to Suspended."""
        return DistrictCountChange(approved=-1, suspended=1, scenario_label="route_b_suspension")

    @staticmethod
    def new_submission() -> DistrictCountChange:
        """An agency pays: one more Submitted application in its district."""
        return DistrictCountChange(total=1, submitted=1, scenario_label="new_submission")
