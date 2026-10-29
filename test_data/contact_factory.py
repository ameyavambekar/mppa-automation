"""
Data Factory — Contact Us
===========================
Message-form data for the Contact Us tests, KAN-TC-543 through KAN-TC-556 (KAN-42).
``valid_message()`` fills every field correctly; the other methods hold the one value a
scenario changes (the rest of the form keeps the valid values).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional


@dataclass
class ContactData:
    name: str = ""
    email: str = ""
    mobile: str = ""
    application_id: str = ""
    query_type: str = ""
    message: str = ""
    typed: str = ""               # text typed into one field, for rules applied as you type
    kept: str = ""                # what the field keeps of ``typed``
    scenario_label: str = ""
    expected_error: Optional[str] = None


class ContactFactory:

    NAME_RULE = "Name can only contain letters, spaces, hyphens, apostrophes, and periods."
    MOBILE_RULE = "Enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9."

    # ── TC-545 / TC-546 / TC-547 / TC-548 / TC-551 — a correctly filled form ──

    @staticmethod
    def valid_message() -> ContactData:
        return ContactData(
            name="Test Agency User",
            email="test@example.com",
            mobile="9876543210",
            query_type="Other",
            message=f"Automated test query — please ignore ({datetime.now():%d-%b-%Y %H:%M:%S})",
            scenario_label="valid_message",
        )

    # ── TC-546 — Full Name ────────────────────────────────────────────────────

    @staticmethod
    def name_with_digits() -> ContactData:
        return replace(ContactFactory.valid_message(), name="Ameya 123", scenario_label="name_with_digits",
                       expected_error=ContactFactory.NAME_RULE)

    @staticmethod
    def name_with_html() -> ContactData:
        return replace(ContactFactory.valid_message(), name="<b>x</b>", scenario_label="name_with_html",
                       expected_error=ContactFactory.NAME_RULE)

    @staticmethod
    def name_with_punctuation() -> ContactData:
        return replace(ContactFactory.valid_message(), name="Ameya O'Neil-Ambekar Jr.",
                       scenario_label="name_with_punctuation")

    # ── TC-547 — Email ID ─────────────────────────────────────────────────────

    @staticmethod
    def email_without_at() -> ContactData:
        return replace(ContactFactory.valid_message(), email="abc", scenario_label="email_without_at",
                       expected_error="'@'")

    # ── TC-548 — Mobile Number ────────────────────────────────────────────────

    @staticmethod
    def mobile_typed_with_letters() -> ContactData:
        return ContactData(typed="98ab76", kept="9876", scenario_label="mobile_typed_with_letters")

    @staticmethod
    def mobile_starting_with_5() -> ContactData:
        return replace(ContactFactory.valid_message(), mobile="5876543210", scenario_label="mobile_starting_with_5",
                       expected_error=ContactFactory.MOBILE_RULE)

    @staticmethod
    def mobile_too_short() -> ContactData:
        return replace(ContactFactory.valid_message(), mobile="98765", scenario_label="mobile_too_short",
                       expected_error=ContactFactory.MOBILE_RULE)

    # ── TC-549 — Application ID ───────────────────────────────────────────────

    @staticmethod
    def application_id_typed_with_letters() -> ContactData:
        return ContactData(typed="abc123", kept="123", scenario_label="application_id_typed_with_letters")

    # ── TC-550 — character counter ────────────────────────────────────────────

    @staticmethod
    def short_message() -> ContactData:
        return ContactData(message="Test query", scenario_label="short_message")

    # ── TC-554 — HTML in the message ──────────────────────────────────────────

    @staticmethod
    def message_with_html() -> ContactData:
        return ContactData(typed="hello <script>x</script> there", kept="hello x there",
                           scenario_label="message_with_html")

    # ── TC-555 — over the length limits ───────────────────────────────────────

    @staticmethod
    def over_length_limits() -> ContactData:
        return ContactData(name="a" * 101, mobile="98765432101", message="m" * 501,
                           scenario_label="over_length_limits")
