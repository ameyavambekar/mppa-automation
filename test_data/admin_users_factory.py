"""
Data Factory — Officers & Access (KAN-34)
=========================================
Test officers for KAN-TC-268…279 and 725…740.

Every officer a test creates is NEW and run-unique (username ``qatest<time><n>``,
email ``<username>@example.com``, a random valid mobile and a random password
generated per run — no password is stored in the repo). Tests never edit,
deactivate or delete an officer that already exists on the portal.

The fixed expectations (messages, labels, prompts) live here so the tests stay
free of magic strings.
"""

from __future__ import annotations

import itertools
import random
import secrets
import time
from dataclasses import dataclass, replace
from typing import Optional

_counter = itertools.count(1)


@dataclass
class OfficerData:
    role: str                       # commissioner | division | district | superadmin
    full_name: str
    username: str
    email: str
    mobile: str
    password: str
    designation: str = ""
    division: str = ""              # division name, e.g. "Pune"
    district: str = ""              # district name, e.g. "Pune"
    scenario_label: str = ""
    expected_error: Optional[str] = None
    id: Optional[int] = None        # set once created

    @property
    def role_label(self) -> str:
        return OfficersFactory.ROLE_LABELS[self.role]


class OfficersFactory:

    ROLE_LABELS = {"commissioner": "Commissioner (State)", "division": "Divisional Officer",
                   "district": "District Officer", "superadmin": "Super Administrator"}
    ROLE_ORDER = ("superadmin", "commissioner", "division", "district")
    PREFIX = "qatest"

    TITLE = "Officers & Access — MPPA Officer Console"
    HEADING = "Officers & Access"
    SUB_HEADING = "All divisional and district officers"
    SEARCH_PLACEHOLDER = "Search name, username, district…"
    COLUMNS = ["Officer", "Role", "Area", "Contact", "Last login", "Status", ""]
    SIDEBAR_LINK = "Officers & access"
    NEVER = "Never"
    LAST_LOGIN_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOGIN_TOLERANCE_MINUTES = 3
    EMPTY_LIST = "No officers found."
    ACCESS_DENIED = "Access denied — this page is for Divisional Officer and above."

    ADD_TITLE = "Add officer"
    EDIT_TITLE = "Edit officer"
    DEFAULT_ROLE = "Commissioner (State)"
    DIVISIONS = ["Select division", "Konkan", "Pune", "Nashik", "Chhatrapati Sambhajinagar", "Amravati", "Nagpur"]
    DISTRICT_PLACEHOLDER = "Select division first"
    PUNE_DISTRICTS = ["Select district", "Kolhapur", "Pune", "Sangli", "Satara", "Solapur"]
    NASHIK_DISTRICTS = ["Ahilyanagar", "Dhule", "Jalgaon", "Nandurbar", "Nashik"]
    KEEP_PASSWORD_HELP = "Leave both password fields blank to keep the current password."
    PASSWORD_RULES = ["8–64 characters", "1 uppercase letter", "1 lowercase letter", "1 number",
                      "1 special character", "No spaces"]
    BAR_GREEN, BAR_ORANGE = "rgb(21, 115, 71)", "rgb(181, 71, 8)"

    FORM_ERROR = "Please correct the highlighted fields."
    CREATED = "{role} account '{username}' created."
    UPDATED = "Account updated."
    DEACTIVATED = "Account deactivated."
    ACTIVATED = "Account activated."
    DELETED = "Account deleted."
    CONFIRM_DEACTIVATE = "Deactivate this officer? They will not be able to log in."
    CONFIRM_DELETE = "Delete this officer account permanently? This cannot be undone."
    LOGIN_REFUSED = "Invalid username or password."
    ROLE_REFUSED = "Your role cannot perform this action."
    SERVER_DUPLICATE = "Another account already uses this username or email."

    AUDIT_CREATED, AUDIT_UPDATED = "Admin Created", "ADMIN_UPDATE"
    AUDIT_DEACTIVATED, AUDIT_ACTIVATED = "ADMIN_DEACTIVATE", "ADMIN_ACTIVATE"
    AUDIT_DELETED, AUDIT_LOGIN_FAILED = "Admin Deleted", "ADMIN_LOGIN_FAILED"

    MSG = {
        "division": "Select the division.",
        "district": "Select the district.",
        "name_required": "Full name is required.",
        "name_short": "Full name must be at least 3 characters.",
        "name_chars": "Use letters, spaces, dot, apostrophe or hyphen only.",
        "desig_short": "Designation is too short.",
        "desig_chars": "Use letters, numbers, spaces and . , & ( ) / - only.",
        "user_required": "Username is required.",
        "user_short": "Username must be at least 5 characters.",
        "user_letter": "Username must start with a letter.",
        "user_chars": "Use letters, numbers, dot and underscore only.",
        "user_dots": "Dot / underscore cannot repeat or come at the end.",
        "user_taken": "This username is already in use.",
        "email_required": "Email is required.",
        "email_invalid": "Enter a valid email address (e.g. name@department.gov.in).",
        "email_taken": "This email is already used by another officer.",
        "mobile_required": "Mobile number is required.",
        "mobile_len": "Mobile number must be exactly 10 digits ({n} entered).",
        "mobile_start": "Mobile number must start with 6, 7, 8 or 9.",
        "mobile_real": "Enter a real mobile number.",
        "pw_required": "Password is required.",
        "pw_space": "Password cannot contain spaces.",
        "pw_len": "Password must be 8–64 characters.",
        "pw_mix": "Password must include uppercase, lowercase, a number and a special character.",
        "pw_user": "Password must not contain the username.",
        "pw_mobile": "Password must not contain the mobile number.",
        "confirm_required": "Please confirm the password.",
        "confirm_mismatch": "Passwords do not match.",
    }

    # TC-277: (typed, expected message)
    USERNAME_CASES = [("qa12", "user_short"), ("9qatest", "user_letter"), ("qa-test", "user_chars"),
                      ("qa..test", "user_dots"), ("qa_test_", "user_dots")]
    VALID_USERNAME = "qa.test_01"
    # TC-278: form context and (password, expected message)
    PW_CONTEXT_USERNAME, PW_CONTEXT_MOBILE = "qatest01", "9876543210"
    PASSWORD_CASES = [("Ab1!xyz", "pw_len"), ("Ab1! xyzw", "pw_space"), ("Qatest01!x", "pw_user"),
                      ("Ab!9876543210", "pw_mobile")]
    PASSWORD_NO_UPPER_SPECIAL = "abcdefg1"
    # TC-731
    NAME_TYPED, NAME_KEPT = "Qa 123 #", "Qa  "
    NAME_CASES = [("Qa", "name_short"), ("Qa Test-", "name_chars")]
    NAME_SPACED, NAME_TIDY = "  Qa    Test  ", "Qa Test"
    DESIG_CASES = [("Q", "desig_short"), ("QA @ Lead", "desig_chars")]
    # TC-732
    EMAIL_CASES = ["qa@test", "qa..test@example.com"]
    MOBILE_TYPED, MOBILE_KEPT = "98abc", "98"
    MOBILE_CASES = [("98765", "mobile_len"), ("5876543210", "mobile_start"), ("9999999999", "mobile_real")]
    # TC-734: a username with a space must get a username message only, not this email one
    SERVER_SPACE_USERNAME_MESSAGE_BAD = "A valid email is required."
    # TC-736 / TC-737
    WILDCARDS = ["%", "_"]
    SPECIAL_SEARCHES = ["O'Brien", "<b>x</b>"]
    # TC-730
    SEARCH_TERM, EMAIL_PART, NO_MATCH = "pune", "nashikrojgar", "zzzz"
    # TC-739
    SPACED_NAME, SPACED_DESIG = "  QA   Test  ", " QA   Lead "

    # ── Officers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _mobile() -> str:
        while True:
            m = random.choice("6789") + "".join(random.choice("0123456789") for _ in range(9))
            if len(set(m)) > 1:
                return m

    @classmethod
    def _username(cls) -> str:
        return f"{cls.PREFIX}{int(time.time() * 1000) % 10**9}{next(_counter)}"

    @staticmethod
    def _password() -> str:
        return "Qa" + secrets.token_hex(5) + "!7Zz"

    @classmethod
    def officer(cls, role: str = "district", label: str = "", **overrides) -> OfficerData:
        username = cls._username()
        area = {"district": ("Pune", "Pune"), "division": ("Pune", "")}.get(role, ("", ""))
        data = OfficerData(role=role, full_name="QA Test Officer", username=username, email=f"{username}@example.com",
                           mobile=cls._mobile(), password=cls._password(), designation="QA Tester",
                           division=area[0], district=area[1], scenario_label=label or f"new_{role}_officer")
        return replace(data, **overrides)

    @classmethod
    def district_officer(cls, **kw) -> OfficerData:
        return cls.officer("district", **kw)

    @classmethod
    def divisional_officer(cls, **kw) -> OfficerData:
        return cls.officer("division", **kw)

    @classmethod
    def commissioner(cls, **kw) -> OfficerData:
        return cls.officer("commissioner", **kw)

    @classmethod
    def created_toast(cls, data: OfficerData) -> str:
        return cls.CREATED.format(role=data.role_label, username=data.username)

    @classmethod
    def server_bypass_cases(cls, base: OfficerData) -> dict:
        """TC-734: label → OfficerData the form would refuse."""
        u = cls._username()
        return {
            "4-character username": replace(base, username="qa12", email=f"qa12{u}@example.com"),
            "username starting with a digit": replace(base, username=f"9{u}", email=f"9{u}@example.com"),
            "digits in the full name": replace(base, username=f"{u}n", email=f"{u}n@example.com", full_name="Qa Test 123"),
            "weak password": replace(base, username=f"{u}w", email=f"{u}w@example.com", password="password"),
            "password containing the username": replace(base, username=f"{u}p", email=f"{u}p@example.com",
                                                        password=f"X!{u}p9"),
        }
