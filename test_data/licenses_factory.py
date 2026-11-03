"""
Data Factory — Admin Licences & Certificates
=============================================
Centralises the Issue / Renew License and certificate action test data for
KAN-33 (AIO KAN-TC-257…267 and KAN-TC-625…643).

All dates are generated relative to today so the scenarios stay valid on any
run date (the AIO cases' fixed dates like 11/05/2026 only made sense on the
day the cases were written). Dates are ISO ``yyyy-mm-dd`` strings — the format
the modal's native date inputs accept.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class LicenseData:
    agency_name: Optional[str] = None      # resolved from the table at runtime
    valid_from: Optional[str] = None       # ISO yyyy-mm-dd
    valid_upto: Optional[str] = None       # ISO yyyy-mm-dd
    duration_years: Optional[int] = None   # use a quick-duration button instead
    notes: Optional[str] = None
    scenario_label: str = ""
    expected_error: Optional[str] = None


@dataclass
class CertificateActionData:
    action: str                            # suspend / lift / expire / cancel / reinstate
    reason: str                            # shown to the agency
    period: Optional[tuple] = None         # (number, unit) — suspend only
    scenario_label: str = ""
    expected_error: Optional[str] = None


class LicensesFactory:

    # ── Date helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    @staticmethod
    def today_plus(days: int) -> str:
        return (date.today() + timedelta(days=days)).isoformat()

    @staticmethod
    def plus_years(valid_from: str, years: int) -> str:
        """Adds N years the way the modal's setDur() JS does (setFullYear):
        same month/day with the year bumped, Feb 29 rolling over to Mar 1."""
        d = date.fromisoformat(valid_from)
        try:
            return d.replace(year=d.year + years).isoformat()
        except ValueError:  # Feb 29 in a non-leap target year
            return d.replace(year=d.year + years, month=3, day=1).isoformat()

    # ── TC-261 — Quick-duration buttons calculate Valid Upto ─────────────────

    @classmethod
    def quick_duration_base(cls) -> LicenseData:
        return LicenseData(
            valid_from=cls.today(),
            scenario_label="quick_duration_base",
        )

    # ── TC-262 / TC-639 — Valid renewal (today → today + 5 years) ────────────

    @classmethod
    def valid_renewal(cls) -> LicenseData:
        valid_from = cls.today()
        return LicenseData(
            valid_from=valid_from,
            valid_upto=cls.plus_years(valid_from, 5),
            duration_years=5,
            notes="Renewed by automation",
            scenario_label="valid_renewal",
        )

    # ── TC-264 — Days Left bar colour bands ──────────────────────────────────

    @classmethod
    def with_days_left(cls, days_left: int, scenario_label: str) -> LicenseData:
        """A validity window ending exactly ``days_left`` days from today
        (negative = already expired). Valid From is kept well in the past so
        it always precedes Valid Upto."""
        return LicenseData(
            valid_from=cls.today_plus(min(0, days_left) - 365),
            valid_upto=cls.today_plus(days_left),
            notes=f"Automated validity window — {scenario_label}.",
            scenario_label=scenario_label,
        )

    @classmethod
    def green_bar_validity(cls) -> LicenseData:
        """More than 30 days remaining — bar must be green."""
        return cls.with_days_left(180, "green_bar_validity")

    @classmethod
    def amber_bar_validity(cls) -> LicenseData:
        """30 days or fewer remaining — bar must be amber."""
        return cls.with_days_left(26, "amber_bar_validity")

    @classmethod
    def expired_validity(cls) -> LicenseData:
        """Already expired — bar must be red / row shows overdue."""
        return cls.with_days_left(-44, "expired_validity")

    # ── TC-265 — Valid Upto earlier than Valid From ───────────────────────────

    @classmethod
    def upto_before_from(cls) -> LicenseData:
        return LicenseData(
            valid_from=cls.today_plus(200),
            valid_upto=cls.today_plus(20),
            scenario_label="upto_before_from",
            expected_error="Valid Upto must be after Valid From",
        )

    # ── TC-266 — No agency selected ───────────────────────────────────────────

    @classmethod
    def missing_agency(cls) -> LicenseData:
        valid_from = cls.today()
        return LicenseData(
            valid_from=valid_from,
            valid_upto=cls.plus_years(valid_from, 1),
            scenario_label="missing_agency",
            expected_error="select an item",  # Chromium: "Please select an item in the list."
        )

    # ── TC-267 — Expiring (30d) inclusive boundary ───────────────────────────

    @classmethod
    def expiring_in_30_days(cls) -> LicenseData:
        """Expires on exactly the 30th day — must count as Expiring."""
        return cls.with_days_left(30, "expiring_in_30_days")

    @classmethod
    def expiring_in_31_days(cls) -> LicenseData:
        """Expires on the 31st day — must NOT count as Expiring."""
        return cls.with_days_left(31, "expiring_in_31_days")

    # ── TC-626 / TC-640 — Search ──────────────────────────────────────────────

    @staticmethod
    def no_match_search() -> str:
        return "zz-no-such-agency-zz"

    # ── TC-630…635 — Certificate actions ──────────────────────────────────────

    @staticmethod
    def suspension() -> CertificateActionData:
        return CertificateActionData("suspend", "Suspended by automation for testing", period=(7, "days"),
                                     scenario_label="suspension_7_days")

    @staticmethod
    def short_suspension() -> CertificateActionData:
        """Used as the Given of lift / history / state tests — lifted again by the test."""
        return CertificateActionData("suspend", "Suspended by automation for testing", period=(1, "days"),
                                     scenario_label="suspension_1_day")

    @staticmethod
    def lift() -> CertificateActionData:
        return CertificateActionData("lift", "Lifted by automation", scenario_label="lift")

    @staticmethod
    def expiry() -> CertificateActionData:
        return CertificateActionData("expire", "Expired by automation for testing", scenario_label="expiry")

    @staticmethod
    def cancellation() -> CertificateActionData:
        return CertificateActionData("cancel", "Cancelled by automation for testing", scenario_label="cancellation")

    @staticmethod
    def reinstatement() -> CertificateActionData:
        return CertificateActionData("reinstate", "Reinstated by automation for testing",
                                     scenario_label="reinstatement")

    @staticmethod
    def reason_one_short() -> CertificateActionData:
        """19 characters — one short of the 20 a suspension needs."""
        return CertificateActionData("suspend", "1234567890123456789", scenario_label="reason_19_chars",
                                     expected_error="Write at least 20 characters.")

    @staticmethod
    def reason_minimum() -> CertificateActionData:
        """Exactly 20 characters — accepted (the test then dismisses the confirmation)."""
        return CertificateActionData("suspend", "12345678901234567890", scenario_label="reason_20_chars")
