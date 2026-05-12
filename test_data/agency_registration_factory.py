"""
Data Factory — MPPA Pre-Registration Form
==========================================
Centralises ALL test-data construction so that test functions
never hard-code values.  Each factory method maps 1-to-1 with
an Acceptance Criterion (AC) or Edge Case (EC) from the spec.

Usage
-----
    from data.agency_registration_factory import AgencyRegistrationFactory

    data = AgencyRegistrationFactory.valid()          # AC-5 happy path
    data = AgencyRegistrationFactory.invalid_pan()    # AC-4
    data = AgencyRegistrationFactory.short_username() # field-level validation
"""

from __future__ import annotations

import os
import random
import re
import string
from dataclasses import dataclass, field
from typing import Optional

from faker import Faker

# ── Faker with Indian locale for realistic, locale-correct data ──────────────
fake = Faker("en_IN")
Faker.seed(0)   # Deterministic seeds make CI reproducible; remove for true random

# ── Testmail.app namespace — set TESTMAIL_NAMESPACE=kmi3t in your .env ───────
TESTMAIL_NAMESPACE = os.getenv("TESTMAIL_NAMESPACE", "kmi3t")


def _testmail_email(username: str) -> str:
    """
    Builds a Testmail.app inbox address tied to the given username.

    Format : {namespace}.{username}@inbox.testmail.app
    Example: kmi3t.ameyavambekar@inbox.testmail.app

    The 'tag' (username part) is what Testmail uses to route mail to the
    correct inbox, and is the same value passed to get_otp_from_testmail().
    """
    return f"{TESTMAIL_NAMESPACE}.{username}@inbox.testmail.app"
# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class AgencyRegistrationData:
    """
    Immutable-ish value object representing one set of form inputs.
    Fields map directly to the four form sections in the spec.
    """
    # Section 1 — Login Credentials
    username: str = ""
    password: str = ""
    confirm_password: str = ""          # defaults to same as password

    # Section 2 — Contact & Identity Verification
    email: str = ""
    pan_number: str = ""
    district: str = "Pune"

    # Meta — used by tests to assert expected outcomes
    expected_error: Optional[str] = field(default=None, repr=False)
    scenario_label: str = field(default="", repr=False)

    def __post_init__(self):
        # If confirm_password was not explicitly set, mirror the password
        if not self.confirm_password and self.password:
            self.confirm_password = self.password
        # If email was not explicitly set but username is known, derive it
        if not self.email and self.username:
            self.email = _testmail_email(self.username)
            self.email_tag = self.username

# ── Helpers ───────────────────────────────────────────────────────────────────

class _PanGenerator:
    """Generates syntactically valid Indian PAN numbers."""

    PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

    @staticmethod
    def valid() -> str:
        """Returns a random, correctly-formatted PAN: ABCDE1234F"""
        letters_prefix = "".join(random.choices(string.ascii_uppercase, k=5))
        digits = "".join(random.choices(string.digits, k=4))
        letter_suffix = random.choice(string.ascii_uppercase)
        return f"{letters_prefix}{digits}{letter_suffix}"

    @staticmethod
    def too_short() -> str:
        return "ABCDE123"          # only 8 chars — fails format check

    @staticmethod
    def all_digits() -> str:
        return "12345678901"       # no letters at all

    @staticmethod
    def lowercase() -> str:
        """EC-4 — user types in lowercase; site should auto-uppercase."""
        return _PanGenerator.valid().lower()

    @staticmethod
    def duplicate() -> str:
        """
        AC-7 / EC-9 — a PAN known to already exist in the test environment.
        Replace with the actual seeded duplicate PAN for your test DB.
        """
        return "AZPPA6529G"        # ← replace with your test-env seeded value


class _PasswordGenerator:
    """Builds passwords that satisfy (or intentionally violate) the rules:
    min 8 chars | ≥1 uppercase | ≥1 digit | ≥1 symbol."""

    @staticmethod
    def valid() -> str:
        num = fake.numerify("####")
        return f"Test@{num}"       # e.g. Test@4729  — always valid

    @staticmethod
    def too_short() -> str:
        return "Ab1!"              # 4 chars — fails min-8 rule

    @staticmethod
    def no_uppercase() -> str:
        return "test@1234"         # all lowercase

    @staticmethod
    def no_number() -> str:
        return "Test@abcd"         # no digit

    @staticmethod
    def no_symbol() -> str:
        return "TestPass1"         # no special char

    @staticmethod
    def blank() -> str:
        return ""


class _UsernameGenerator:
    """Builds usernames that satisfy (or intentionally violate) the rules:
    min 6 chars | no spaces."""

    @staticmethod
    def valid() -> str:
        base = fake.user_name().replace("-", "").replace(".", "").replace("_", "")
        # Ensure min 6, no spaces, max 20 for usability
        base = base[:20] if len(base) > 20 else base
        return base if len(base) >= 6 else base + "123456"

    @staticmethod
    def too_short() -> str:
        return "ab"                # 2 chars — fails min-6 rule

    @staticmethod
    def with_space() -> str:
        return "ameya ambekar"      # contains a space

    @staticmethod
    def blank() -> str:
        return ""

    @staticmethod
    def already_taken() -> str:
        """EC-9 — username that already exists in the test environment."""
        return "testuser01"        # ← replace with your test-env seeded value


# ── Factory ───────────────────────────────────────────────────────────────────

class AgencyRegistrationFactory:
    """
    Factory class — each class method corresponds to one test scenario.

    Naming convention
    -----------------
    valid()             → AC-5  happy-path, all fields correct
    <invalid_field>()   → negative / field-validation scenarios
    ec_<n>_<name>()     → edge-cases directly from the spec
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    @classmethod
    def valid(cls) -> AgencyRegistrationData:
        """
        AC-5 — Full valid registration.
        All fields satisfy every constraint; form should submit successfully.
        """
        pwd = _PasswordGenerator.valid()
        username = _UsernameGenerator().valid()
        return AgencyRegistrationData(
            username=username,
            password=pwd,
            confirm_password=pwd,
            email= _testmail_email(username),
            pan_number=_PanGenerator.valid(),
            district="Pune",
            scenario_label="AC-5: valid full registration",
        )

    # ── Section 1: Login Credential Validations ───────────────────────────────

    @classmethod
    def blank_username(cls) -> AgencyRegistrationData:
        """Field-level: Username is required."""
        data = cls.valid()
        data.username = _UsernameGenerator.blank()
        data.expected_error = "Username is required."
        data.scenario_label = "FV: blank username"
        return data

    @classmethod
    def short_username(cls) -> AgencyRegistrationData:
        """Field-level: Username must be at least 6 characters."""
        data = cls.valid()
        data.username = _UsernameGenerator.too_short()
        data.expected_error = "6–30 chars, letters/numbers/underscore only"
        data.scenario_label = "FV: username too short"
        return data

    @classmethod
    def username_with_space(cls) -> AgencyRegistrationData:
        """Field-level: Username must not contain spaces."""
        data = cls.valid()
        data.username = _UsernameGenerator.with_space()
        data.expected_error = "Username must not contain spaces."
        data.scenario_label = "FV: username contains space"
        return data

    @classmethod
    def username_already_taken(cls) -> AgencyRegistrationData:
        """EC-9: Username already exists — inline error on blur."""
        data = cls.valid()
        data.username = "ameyavambekar"
        data.expected_error = "❌ Username taken"
        data.scenario_label = "EC-9: username already taken"
        return data

    @classmethod
    def blank_password(cls) -> AgencyRegistrationData:
        """Field-level: Password is required."""
        data = cls.valid()
        data.password = _PasswordGenerator.blank()
        data.confirm_password = _PasswordGenerator.blank()
        data.expected_error = "Password is required."
        data.scenario_label = "FV: blank password"
        return data

    @classmethod
    def password_too_short(cls) -> AgencyRegistrationData:
        """Field-level: Password must be at least 8 characters."""
        data = cls.valid()
        pw = _PasswordGenerator.too_short()
        data.password = pw
        data.confirm_password = pw
        data.expected_error = "Password must be at least 8 characters."
        data.scenario_label = "FV: password too short"
        return data

    @classmethod
    def password_no_uppercase(cls) -> AgencyRegistrationData:
        """Field-level: Password must contain at least one uppercase letter."""
        data = cls.valid()
        pw = _PasswordGenerator.no_uppercase()
        data.password = pw
        data.confirm_password = pw
        data.expected_error = "Password must contain at least one uppercase letter."
        data.scenario_label = "FV: password missing uppercase"
        return data

    @classmethod
    def password_no_number(cls) -> AgencyRegistrationData:
        """Field-level: Password must contain at least one number."""
        data = cls.valid()
        pw = _PasswordGenerator.no_number()
        data.password = pw
        data.confirm_password = pw
        data.expected_error = "Password must contain at least one number."
        data.scenario_label = "FV: password missing number"
        return data

    @classmethod
    def password_no_symbol(cls) -> AgencyRegistrationData:
        """Field-level: Password must contain at least one special character."""
        data = cls.valid()
        pw = _PasswordGenerator.no_symbol()
        data.password = pw
        data.confirm_password = pw
        data.expected_error = "Password must contain at least one special character."
        data.scenario_label = "FV: password missing symbol"
        return data

    @classmethod
    def password_mismatch(cls) -> AgencyRegistrationData:
        """Field-level: Passwords do not match."""
        data = cls.valid()
        data.confirm_password = data.password + "DIFF"
        data.expected_error = "Passwords do not match."
        data.scenario_label = "FV: confirm password mismatch"
        return data

    # ── AC-1: Login Credentials + Password Strength ───────────────────────────

    @classmethod
    def ac1_valid_credentials(cls) -> AgencyRegistrationData:
        """
        AC-1 — Valid credentials entered.
        Asserts that all three fields are accepted and strength feedback is shown.
        """
        return cls.valid()

    # ── Section 2: Contact & Identity Validations ─────────────────────────────

    # ── Section 2: Contact & Identity Validations ─────────────────────────────

    @classmethod
    def invalid_email_domain(cls) -> AgencyRegistrationData:
        """
        TC-14 / EC-3 — Syntactically valid email address but with a
        non-existent domain so OTP delivery will fail at the SMTP layer.
        Expected error: 'OTP could not be delivered. Please check the email
        address and try again.'
        """
        data = cls.valid()
        data.email = "user@nonexistentdomain12345"
        data.expected_error = (
            "OTP could not be delivered. "
            "Please check the email address and try again."
        )
        data.scenario_label = "TC-14: undeliverable email domain"
        return data

    @classmethod
    def invalid_pan(cls) -> AgencyRegistrationData:
        """
        AC-4 — PAN format validation.
        Expected inline error: 'Invalid PAN format. Expected format: ABCDE1234F'
        """
        data = cls.valid()
        data.pan_number = _PanGenerator.too_short()
        data.expected_error = "Invalid PAN format. Expected format: ABCDE1234F"
        data.scenario_label = "AC-4: invalid PAN format"
        return data

    @classmethod
    def duplicate_pan(cls) -> AgencyRegistrationData:
        """
        AC-7 — Duplicate PAN blocked.
        Expected: 'This PAN is already registered. Please use a different PAN or login...'
        """
        data = cls.valid()
        data.pan_number = _PanGenerator.duplicate()
        data.expected_error = (
            "This PAN is already registered. "
            "Please use a different PAN or login if you are an existing user."
        )
        data.scenario_label = "AC-7: duplicate PAN"
        return data

    @classmethod
    def blank_pan(cls) -> AgencyRegistrationData:
        """Field-level: PAN number is required."""
        data = cls.valid()
        data.pan_number = ""
        data.expected_error = "PAN number is required."
        data.scenario_label = "FV: blank PAN"
        return data

    @classmethod
    def no_district_selected(cls) -> AgencyRegistrationData:
        """Field-level: District dropdown left at default '--Select District--'."""
        data = cls.valid()
        data.district = ""
        data.expected_error = "Please select the district where your agency is located."
        data.scenario_label = "FV: district not selected"
        return data

    # ── Edge Cases ────────────────────────────────────────────────────────────

    @classmethod
    def ec4_pan_lowercase(cls) -> AgencyRegistrationData:
        """
        EC-4 — PAN typed in lowercase; site auto-uppercases to ABCDE1234F.
        The test verifies the displayed value is uppercase after typing.
        """
        data = cls.valid()
        data.pan_number = _PanGenerator.lowercase()
        data.scenario_label = "EC-4: PAN lowercase auto-uppercase"
        return data

    @classmethod
    def ec5_password_show_hide(cls) -> AgencyRegistrationData:
        """
        EC-5 — Password show/hide toggle.
        Uses a recognisable password so the test can assert visible plain text.
        """
        data = cls.valid()
        data.password = "Visible@1234"
        data.confirm_password = "Visible@1234"
        data.scenario_label = "EC-5: password show/hide toggle"
        return data

    # ── Parametrize helpers ───────────────────────────────────────────────────

    # ── Parametrize helpers ───────────────────────────────────────────────────

    @classmethod
    def password_complexity_scenarios(cls) -> list[AgencyRegistrationData]:
        """
        TC-07 — Returns all four password-complexity-violation scenarios as a
        list ready for @pytest.mark.parametrize.

        Usage in test:
            @pytest.mark.parametrize(
                "data",
                AgencyRegistrationFactory.tc07_password_complexity_scenarios(),
                ids=lambda d: d.scenario_label,
            )
        """
        return [
            cls.password_no_uppercase(),
            cls.password_no_number(),
            cls.password_no_symbol(),
            cls.password_too_short(),
        ]

    @classmethod
    def all_field_validation_scenarios(cls) -> list[AgencyRegistrationData]:
        """
        Returns every negative scenario as a list — ready for
        @pytest.mark.parametrize.

        Usage in test:
            @pytest.mark.parametrize(
                "data",
                AgencyRegistrationFactory.all_field_validation_scenarios(),
                ids=lambda d: d.scenario_label,
            )
        """
        return [
            cls.blank_username(),
            cls.short_username(),
            cls.username_with_space(),
            cls.blank_password(),
            cls.password_too_short(),
            cls.password_no_uppercase(),
            cls.password_no_number(),
            cls.password_no_symbol(),
            cls.password_mismatch(),
            cls.blank_pan(),
            cls.invalid_pan(),
            cls.no_district_selected(),
        ]

    @classmethod
    def all_district_options(cls) -> list[AgencyRegistrationData]:
        """
        Parametrize helper: one valid data object per major Maharashtra district.
        Verifies that district selection is reflected in the Registration ID prefix.
        """
        districts = [
            "Pune", "Mumbai", "Nagpur", "Nashik",
            "Aurangabad", "Solapur", "Kolhapur",
        ]
        username = _UsernameGenerator.valid()

        return [
            AgencyRegistrationData(
                username = username,
                password=_PasswordGenerator.valid(),
                email=_testmail_email(username),
                pan_number=_PanGenerator.valid(),
                district=d,
                scenario_label=f"district: {d}",
            )
            for d in districts
        ]
