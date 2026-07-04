"""
Data Factory — Admin / Super Admin Login
========================================
Centralises all admin-login test data. Each method maps to one of the
Notion test cases KAN-TC-169 through KAN-TC-182.

Real credentials come from the state store (preferred) or environment
variables; this factory only shapes the data objects and scenario metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from utils.state_store import UserRecord


@dataclass
class AdminLoginData:
    username: str
    password: str
    captcha: Optional[str] = None          # explicit CAPTCHA for wrong-CAPTCHA tests
    scenario_label: str = ""
    expected_error: Optional[str] = None


class AdminLoginFactory:

    # ── Happy path (TC-169, TC-172, TC-180 success) ───────────────────────────

    @staticmethod
    def valid_super_admin(user: UserRecord) -> AdminLoginData:
        return AdminLoginData(
            username=user.username,
            password=user.password,
            scenario_label="valid_super_admin",
        )

    # ── Wrong credentials (TC-170) ────────────────────────────────────────────

    @staticmethod
    def wrong_credentials() -> AdminLoginData:
        """Non-existent admin username / bad password (TC-170)."""
        return AdminLoginData(
            username="wrongadmin",
            password="BadPass@1",
            scenario_label="wrong_credentials",
            expected_error="Invalid username or password.",
        )

    # ── Wrong CAPTCHA (TC-171) ────────────────────────────────────────────────

    @staticmethod
    def valid_creds_wrong_captcha(user: UserRecord) -> AdminLoginData:
        """Valid admin credentials submitted with an incorrect CAPTCHA (TC-171)."""
        return AdminLoginData(
            username=user.username,
            password=user.password,
            captcha="XXXXXX",
            scenario_label="valid_creds_wrong_captcha",
            expected_error="Captcha Incorrect. Please try again.",
        )

    # ── Cross-portal rejection (TC-173, TC-174) ───────────────────────────────

    @staticmethod
    def agency_creds_on_admin(agency_user: UserRecord) -> AdminLoginData:
        """Agency credentials entered on the Admin Login form (TC-173)."""
        return AdminLoginData(
            username=agency_user.username,
            password=agency_user.password,
            scenario_label="agency_creds_on_admin",
            expected_error="Invalid username or password.",
        )

    @staticmethod
    def admin_creds_for_agency_page(admin_user: UserRecord) -> AdminLoginData:
        """Admin credentials to be tried on the agency login page (TC-174)."""
        return AdminLoginData(
            username=admin_user.username,
            password=admin_user.password,
            scenario_label="admin_creds_on_agency",
            expected_error="Invalid username or password.",
        )

    # ── Blank-field validations (TC-177, TC-178) ──────────────────────────────

    @staticmethod
    def blank_username() -> AdminLoginData:
        """Username left blank (TC-177)."""
        return AdminLoginData(
            username="",
            password="password",
            scenario_label="blank_username",
            expected_error="Username is required.",
        )

    @staticmethod
    def blank_password(user: UserRecord) -> AdminLoginData:
        """Password left blank (TC-178)."""
        return AdminLoginData(
            username=user.username,
            password="",
            scenario_label="blank_password",
            expected_error="Password is required.",
        )

    # ── Stale CAPTCHA after refresh (TC-176) ──────────────────────────────────

    @staticmethod
    def stale_captcha(user: UserRecord) -> AdminLoginData:
        """Valid credentials with a stale (pre-refresh) CAPTCHA value (TC-176).

        The CAPTCHA value is captured at runtime before clicking Refresh, so it
        is filled in by the test rather than the factory."""
        return AdminLoginData(
            username=user.username,
            password=user.password,
            scenario_label="stale_captcha",
            expected_error="Captcha Incorrect. Please try again.",
        )

    # ── Sub-admin lockout (TC-179) ────────────────────────────────────────────

    @staticmethod
    def subadmin_wrong_password(subadmin: UserRecord) -> AdminLoginData:
        """Wrong-password attempt for a sub-admin, used to trigger lockout (TC-179).
        WILL lock the account — use a dedicated sub-admin test account."""
        return AdminLoginData(
            username=subadmin.username,
            password="WrongPass@1",
            scenario_label="subadmin_wrong_password",
            expected_error="Invalid username or password.",
        )

    @staticmethod
    def subadmin_correct(subadmin: UserRecord) -> AdminLoginData:
        """Correct sub-admin credentials, expected to remain blocked while locked (TC-179)."""
        return AdminLoginData(
            username=subadmin.username,
            password=subadmin.password,
            scenario_label="subadmin_correct",
        )

    # ── Super admin never locks (TC-180) ──────────────────────────────────────

    @staticmethod
    def super_admin_wrong_password(user: UserRecord) -> AdminLoginData:
        """Wrong-password attempt for the super admin (TC-180) — should never lock."""
        return AdminLoginData(
            username=user.username,
            password="WrongPass@1",
            scenario_label="super_admin_wrong_password",
            expected_error="Invalid username or password.",
        )
