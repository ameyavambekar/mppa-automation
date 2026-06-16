"""
Data Factory — Admin User Management
=====================================
Centralises all Create-Admin / admin-user test data. Each method maps to one of
the AIO test cases KAN-TC-268 through KAN-TC-279.

Usernames and emails are generated unique per call (timestamp + counter) so the
create tests can run repeatedly without colliding with accounts left behind by a
previous run. The AIO sheet's fixed values (``officer01`` / ``priya@mppa.gov``)
describe the spec dataset, not the dev environment — duplicate-conflict tests
read a real existing username/email from the live table instead.

The default password ``Officer@1234`` satisfies the portal's complexity rules
(uppercase + digit + symbol, min 8); the weak-password scenario deliberately
breaks them.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AdminUserData:
    username: str
    full_name: str
    email: str
    password: str
    role: str = "officer"                       # 'officer' | 'admin' | 'viewer'
    permissions: List[str] = field(default_factory=list)
    scenario_label: str = ""
    expected_error: Optional[str] = None


class AdminUsersFactory:

    # Compliant password reused across the happy-path scenarios
    VALID_PASSWORD = "Officer@1234"

    _counter = itertools.count(1)

    @classmethod
    def _unique(cls) -> str:
        """A short token unique within and across runs."""
        return f"{int(time.time())}{next(cls._counter)}"

    # ── TC-270 / TC-279 — a brand-new, valid admin ───────────────────────────

    @classmethod
    def new_admin(cls, role: str = "officer", scenario_label: str = "new_admin") -> AdminUserData:
        token = cls._unique()
        return AdminUserData(
            username=f"qa{token}",
            full_name="QA Automation Admin",
            email=f"qa.{token}@example.test",
            password=cls.VALID_PASSWORD,
            role=role,
            permissions=["view_agencies"],
            scenario_label=scenario_label,
        )

    # ── TC-271 — username already taken ──────────────────────────────────────

    @classmethod
    def duplicate_username(cls, existing_username: str) -> AdminUserData:
        """Valid everything except the username, which collides with an existing
        account read from the live table."""
        data = cls.new_admin(scenario_label="duplicate_username")
        data.username = existing_username
        data.expected_error = "username"
        return data

    # ── TC-272 — email already taken ─────────────────────────────────────────

    @classmethod
    def duplicate_email(cls, existing_email: str) -> AdminUserData:
        """Unique username but an email that collides with an existing account."""
        data = cls.new_admin(scenario_label="duplicate_email")
        data.email = existing_email
        data.expected_error = "email"
        return data

    # ── TC-277 — username shorter than 4 characters ──────────────────────────

    @classmethod
    def short_username(cls) -> AdminUserData:
        data = cls.new_admin(scenario_label="short_username")
        data.username = "adm"  # 3 chars — below the 4-char minimum
        data.expected_error = "4 characters"
        return data

    # ── TC-278 — password without the required complexity ────────────────────

    @classmethod
    def weak_password(cls) -> AdminUserData:
        """Password is 9 chars (passes the client minlength=8) but has no
        uppercase letter and no symbol, so the server must reject it."""
        data = cls.new_admin(scenario_label="weak_password")
        data.password = "simple123"
        data.expected_error = "password"
        return data
