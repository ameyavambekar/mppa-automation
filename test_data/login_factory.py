from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from utils.state_store import UserRecord


@dataclass
class LoginData:
    username: str
    password: str
    scenario_label: str = ""
    expected_error: Optional[str] = None


class LoginFactory:

    # ── Happy-path ────────────────────────────────────────────────────────────

    @staticmethod
    def valid_from_store(user: UserRecord) -> LoginData:
        return LoginData(
            username=user.username,
            password=user.password,
            scenario_label="valid_agency_user",
        )

    # ── Invalid-credentials (AC-2) ────────────────────────────────────────────

    @staticmethod
    def nonexistent_user() -> LoginData:
        """Username that has never been registered (TC-02)."""
        return LoginData(
            username="WrongUser99",
            password="Secure@1234",
            scenario_label="nonexistent_user",
            expected_error="Invalid username or password",
        )

    @staticmethod
    def invalid_password(username: str) -> LoginData:
        """Valid username, wrong password (TC-03)."""
        return LoginData(
            username=username,
            password="WrongPass@99",
            scenario_label="invalid_password",
            expected_error="Invalid username or password",
        )

    # ── Wrong CAPTCHA (AC-3) ──────────────────────────────────────────────────

    @staticmethod
    def wrong_captcha_credentials(user: UserRecord) -> LoginData:
        """Valid credentials intended for a wrong-CAPTCHA submission (TC-04)."""
        return LoginData(
            username=user.username,
            password=user.password,
            scenario_label="wrong_captcha",
            expected_error="Incorrect CAPTCHA",
        )

    # ── Blank-field validations (TC-33 / TC-34 / TC-35) ───────────────────────

    @staticmethod
    def blank_username() -> LoginData:
        """Username left blank on login (KAN-TC-33).

        Form should reject the submission before checking credentials, so a
        placeholder password is sufficient — no state-store dependency."""
        return LoginData(
            username="",
            password="Secure@1234",
            scenario_label="blank_username_login",
            expected_error="Username is required.",
        )

    @staticmethod
    def blank_password() -> LoginData:
        """Password left blank on login (KAN-TC-34).

        Form should reject blank password before authenticating, so the
        username does not need to map to a real account."""
        return LoginData(
            username="NewAgency01",
            password="",
            scenario_label="blank_password_login",
            expected_error="Password is required.",
        )

    @staticmethod
    def blank_captcha() -> LoginData:
        """CAPTCHA left blank on login (KAN-TC-35).

        Username/password are valid-looking but irrelevant — CAPTCHA check
        runs first and blocks submission."""
        return LoginData(
            username="NewAgency01",
            password="Secure@1234",
            scenario_label="blank_captcha_login",
            expected_error="Please enter the CAPTCHA.",
        )

    # ── Account-lockout helper (EC-1) ─────────────────────────────────────────

    @staticmethod
    def lockout_attempt(username: str) -> LoginData:
        """Wrong-password attempt used to trigger account lockout (TC-10).
        Use a DEDICATED lockout-test account — this will lock the account."""
        return LoginData(
            username=username,
            password="WrongPass@99",
            scenario_label="lockout_attempt",
            expected_error="Invalid username or password",
        )
