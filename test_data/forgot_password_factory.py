"""
Data Factory — Forgot Password
================================
Values for the Forgot password and Set a new password tests, KAN-TC-557 through KAN-TC-573 (KAN-43).
Field-rule methods hold the one value a scenario enters into one field; ``kept`` is what the field
keeps of a typed value and ``expected_error`` the message shown under it (``""`` for none). The
account details themselves (username, e-mail, PAN, password) come from the state store.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pages.forgot_password_page import ForgotPasswordPage as FP


@dataclass
class ForgotPasswordData:
    value: str = ""
    kept: str = ""                # what the field keeps of ``value`` typed key by key
    scenario_label: str = ""
    expected_error: Optional[str] = None


class ForgotPasswordFactory:

    # ── TC-559 — Username ─────────────────────────────────────────────────────

    @staticmethod
    def invalid_usernames() -> list[ForgotPasswordData]:
        return [
            ForgotPasswordData("abcde", scenario_label="username_5_characters", expected_error=FP.USERNAME_LENGTH),
            ForgotPasswordData("a" * 31, scenario_label="username_31_characters", expected_error=FP.USERNAME_LENGTH),
            ForgotPasswordData("abc-def1", scenario_label="username_with_hyphen", expected_error=FP.USERNAME_CHARACTERS),
        ]

    @staticmethod
    def username_typed_with_space() -> ForgotPasswordData:
        return ForgotPasswordData("abc def", kept="abcdef", scenario_label="username_typed_with_space")

    @staticmethod
    def username_as_email() -> ForgotPasswordData:
        return ForgotPasswordData("user@mail.com", scenario_label="username_as_email",
                                  expected_error=FP.USERNAME_NOT_EMAIL)

    @staticmethod
    def valid_username() -> ForgotPasswordData:
        return ForgotPasswordData("Valid_User1", scenario_label="valid_username", expected_error="")

    # ── TC-560 — Registered e-mail ────────────────────────────────────────────

    @staticmethod
    def invalid_emails() -> list[ForgotPasswordData]:
        return [
            ForgotPasswordData("abc", scenario_label="email_without_at", expected_error=FP.EMAIL_INVALID),
            ForgotPasswordData("a@b", scenario_label="email_without_domain_ending", expected_error=FP.EMAIL_DOMAIN),
            ForgotPasswordData("a..b@gmail.com", scenario_label="email_with_two_dots", expected_error=FP.EMAIL_DOUBLE_DOT),
            ForgotPasswordData(".ab@gmail.com", scenario_label="email_starting_with_dot", expected_error=FP.EMAIL_EDGE_DOT),
        ]

    @staticmethod
    def email_typed_with_space_and_capitals() -> ForgotPasswordData:
        return ForgotPasswordData("A b@Gmail.com", kept="ab@gmail.com", scenario_label="email_typed_with_space_and_capitals",
                                  expected_error="")

    # ── TC-561 — PAN ──────────────────────────────────────────────────────────

    @staticmethod
    def pan_typed_in_small_letters() -> ForgotPasswordData:
        return ForgotPasswordData("abcde1234f", kept="ABCDE1234F", scenario_label="pan_typed_in_small_letters",
                                  expected_error="")

    @staticmethod
    def invalid_pans() -> list[ForgotPasswordData]:
        return [
            ForgotPasswordData("ABCD1234F", scenario_label="pan_9_characters", expected_error=FP.PAN_FORMAT),
            ForgotPasswordData("12345ABCDE", scenario_label="pan_numbers_first", expected_error=FP.PAN_FORMAT),
        ]

    @staticmethod
    def pan_pasted_too_long() -> ForgotPasswordData:
        """One character too many — the field cuts it to 10, so the user must be told the PAN is too long."""
        return ForgotPasswordData("ABCDE1234F9", scenario_label="pan_pasted_too_long")

    # ── TC-562 — Captcha ──────────────────────────────────────────────────────

    @staticmethod
    def captcha_typed_with_symbols() -> ForgotPasswordData:
        return ForgotPasswordData("abc$%2xy", kept="ABC2XY", scenario_label="captcha_typed_with_symbols")

    @staticmethod
    def captcha_with_0_and_1() -> ForgotPasswordData:
        """0 and 1 are never drawn — the message must say so rather than ask for 6 letters and numbers."""
        return ForgotPasswordData("AB01CD", scenario_label="captcha_with_0_and_1")

    @staticmethod
    def captcha_too_short() -> ForgotPasswordData:
        return ForgotPasswordData("ABC", scenario_label="captcha_3_characters", expected_error=FP.CAPTCHA_FORMAT)

    # ── TC-565 / TC-570 — wrong details ───────────────────────────────────────

    @staticmethod
    def wrong_pan(real_pan: str) -> ForgotPasswordData:
        """A PAN in the right format that is not the agency's (its last letter changed)."""
        last = "Z" if real_pan[-1] != "Z" else "Y"
        return ForgotPasswordData(real_pan[:-1] + last, scenario_label="wrong_pan")

    @staticmethod
    def unknown_username() -> ForgotPasswordData:
        return ForgotPasswordData(f"nouser_{datetime.now():%d%H%M%S}", scenario_label="unknown_username")

    @staticmethod
    def wrong_captcha() -> ForgotPasswordData:
        return ForgotPasswordData("AAAAAA", scenario_label="wrong_captcha", expected_error=FP.CAPTCHA_MISMATCH)

    # ── TC-566 / TC-572 — new password rules ──────────────────────────────────

    @staticmethod
    def new_password() -> ForgotPasswordData:
        """A new password meeting every rule, different on every run."""
        return ForgotPasswordData(f"Kan43@{datetime.now():%m%d%H%M%S}x", scenario_label="new_password")

    @staticmethod
    def password_checklist_steps() -> dict[str, ForgotPasswordData]:
        return {
            "small_letters": ForgotPasswordData("abcdefgh", scenario_label="small_letters_only"),
            "all_rules": ForgotPasswordData("Abcdefg1@", scenario_label="all_rules"),
            "mismatch": ForgotPasswordData("Abcdefg1#", scenario_label="confirmation_mismatch"),
            "with_space": ForgotPasswordData("Abcdefg 1@", scenario_label="with_space"),
        }

    @staticmethod
    def password_lengths() -> dict[int, ForgotPasswordData]:
        """Passwords meeting every rule but length, at 7, 8 and 64 characters."""
        return {n: ForgotPasswordData("Aa1@" + "x" * (n - 4), scenario_label=f"password_{n}_characters")
                for n in (7, 8, 64)}
