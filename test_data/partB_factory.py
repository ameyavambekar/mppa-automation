"""
Data Factory — Step 2 (Part B: Key Persons)
===========================================
All test-data construction for Part B of the Form-I wizard (KAN-19).
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the AIO test cases KAN-TC-81 … KAN-TC-119 and
KAN-TC-437 … KAN-TC-443.

The happy-path data is for a Private Limited Company agency, so every person
carries a DIN / DPIN and PAN.

Usage
-----
    from test_data.partB_factory import KeyPersonData, PartBFactory

    data = PartBFactory.valid_director()         # TC-113 happy path
    data = PartBFactory.aadhaar_too_short()      # TC-90
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pages.partB_page import PartBPage


@dataclass
class TypedInput:
    """What is typed into a field and what the field shows afterwards."""
    field: str             # PartBPage per-person locator method name
    typed: str
    shown: str


@dataclass
class KeyPersonData:
    full_name: str = ""
    aadhaar: str = ""
    mobile: str = ""
    address: str = ""
    email: Optional[str] = None
    din: Optional[str] = None                  # company types only
    pan: Optional[str] = None                  # company types only
    nationality: str = "Indian"
    passport: Optional[str] = None             # Foreign nationals only
    country_code: str = "+91"
    # Scenario-specific values
    invalid_values: list[str] = field(default_factory=list)  # bad values a negative scenario enters, in order
    expected_error: Optional[str] = None       # server error message (without the "Person N: " prefix)
    scenario_label: str = ""


class PartBFactory:

    # Agency type saved in Part A → key-person label it gives Part B.
    AGENCY_TYPE = "Private Limited Company"
    PERSON_LABEL = "Director"
    PROPRIETORSHIP_AGENCY_TYPE = "Proprietorship"
    PROPRIETORSHIP_LABEL = "Proprietor"

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def valid_director() -> KeyPersonData:
        """TC-113: every mandatory field for one Director, Indian national."""
        return KeyPersonData(
            full_name="Rajesh Kumar Sharma",
            aadhaar="234567890123",
            mobile="9876543210",
            address="12, MG Road, Andheri East, Mumbai, Maharashtra 400069",
            din="23456789",
            pan="ABCDE1234F",
            scenario_label="valid_director",
        )

    @staticmethod
    def second_valid_director() -> KeyPersonData:
        """TC-114: a second, different Director."""
        return KeyPersonData(
            full_name="Meena Patil",
            aadhaar="345678901234",
            mobile="9876500000",
            address="45, FC Road, Shivajinagar, Pune, Maharashtra 411005",
            din="34567890",
            pan="BCDEF2345G",
            scenario_label="second_valid_director",
        )

    @staticmethod
    def blank() -> KeyPersonData:
        """TC-84: every field empty."""
        return KeyPersonData(din="", pan="", scenario_label="blank")

    # ── Full Name (TC-85, TC-87) ──────────────────────────────────────────────

    @staticmethod
    def full_name_too_long() -> KeyPersonData:
        """TC-85: 151 characters typed into the 150-character Full Name."""
        data = PartBFactory.valid_director()
        data.invalid_values = ["A" * 151]
        data.scenario_label = "full_name_too_long"
        return data

    @staticmethod
    def full_name_invalid_characters() -> KeyPersonData:
        """TC-87: a name with digits, then one with a symbol."""
        data = PartBFactory.valid_director()
        data.invalid_values = ["Rajesh123", "Rajesh@Kumar"]
        data.expected_error = PartBPage.NAME_FORMAT_ERROR
        data.scenario_label = "full_name_invalid_characters"
        return data

    # ── Aadhaar (TC-89, TC-90, TC-91) ─────────────────────────────────────────

    @staticmethod
    def aadhaar_blank() -> KeyPersonData:
        """TC-89: every other mandatory field filled, Aadhaar empty."""
        data = PartBFactory.valid_director()
        data.aadhaar = ""
        data.expected_error = PartBPage.AADHAAR_REQUIRED_ERROR
        data.scenario_label = "aadhaar_blank"
        return data

    @staticmethod
    def aadhaar_too_short() -> KeyPersonData:
        """TC-90: 8 digits."""
        data = PartBFactory.valid_director()
        data.aadhaar = "23456789"
        data.expected_error = PartBPage.AADHAAR_LENGTH_ERROR
        data.scenario_label = "aadhaar_too_short"
        return data

    @staticmethod
    def aadhaar_starts_with_0_or_1() -> KeyPersonData:
        """TC-91: 12 digits starting with 0, then with 1."""
        data = PartBFactory.valid_director()
        data.invalid_values = ["023456789012", "123456789012"]
        data.expected_error = PartBPage.AADHAAR_PREFIX_ERROR
        data.scenario_label = "aadhaar_starts_with_0_or_1"
        return data

    # ── Passport (TC-94, TC-95) ───────────────────────────────────────────────

    @staticmethod
    def foreign_national() -> KeyPersonData:
        """TC-94: a foreign national; the passport is typed in lower case."""
        data = PartBFactory.valid_director()
        data.nationality = "Foreign"
        data.passport = "a1234567"
        data.invalid_values = ["A12345678901234567890"]   # 21 characters
        data.expected_error = PartBPage.PASSPORT_REQUIRED_ERROR
        data.scenario_label = "foreign_national"
        return data

    @staticmethod
    def passport_cleared_for_indian() -> KeyPersonData:
        """TC-95: a passport entered, then nationality set back to Indian."""
        data = PartBFactory.valid_director()
        data.nationality = "Foreign"
        data.passport = "B9876543"
        data.scenario_label = "passport_cleared_for_indian"
        return data

    # ── Residential Address (TC-96, TC-97) ────────────────────────────────────

    @staticmethod
    def address_blank_then_short() -> KeyPersonData:
        """TC-97: Address empty, then shorter than 10 characters."""
        data = PartBFactory.valid_director()
        data.address = ""
        data.invalid_values = ["12 MG Rd"]
        data.expected_error = PartBPage.ADDRESS_REQUIRED_ERROR
        data.scenario_label = "address_blank_then_short"
        return data

    # ── Personal Email (TC-102, TC-103, TC-442) ───────────────────────────────

    @staticmethod
    def with_personal_email() -> KeyPersonData:
        """TC-102 / TC-442: a valid personal email different from the agency's."""
        data = PartBFactory.valid_director()
        data.email = "rajesh.sharma@example.com"
        data.scenario_label = "with_personal_email"
        return data

    @staticmethod
    def malformed_emails() -> KeyPersonData:
        """TC-103: an email without @, then one without a domain."""
        data = PartBFactory.valid_director()
        data.invalid_values = ["rajeshexample.com", "rajesh@"]
        data.scenario_label = "malformed_emails"
        return data

    # ── Mobile (TC-104 … TC-108, TC-441) ──────────────────────────────────────

    @staticmethod
    def mobile_blank() -> KeyPersonData:
        """TC-105: every other mandatory field filled, Mobile empty."""
        data = PartBFactory.valid_director()
        data.mobile = ""
        data.expected_error = PartBPage.MOBILE_REQUIRED_ERROR
        data.scenario_label = "mobile_blank"
        return data

    @staticmethod
    def mobile_wrong_format() -> KeyPersonData:
        """TC-106: starting with 0, starting with 5, and too short."""
        data = PartBFactory.valid_director()
        data.invalid_values = ["0987654321", "5876543210", "98765"]
        data.scenario_label = "mobile_wrong_format"
        return data

    # ── DIN / DPIN and PAN (TC-439) ───────────────────────────────────────────

    @staticmethod
    def din_and_pan_blank() -> KeyPersonData:
        """TC-439: DIN / DPIN and PAN empty, then a 5-digit DIN."""
        data = PartBFactory.valid_director()
        data.din = ""
        data.pan = ""
        data.invalid_values = ["23456"]
        data.expected_error = PartBPage.DIN_LENGTH_ERROR
        data.scenario_label = "din_and_pan_blank"
        return data

    # ── Duplicate Aadhaar (TC-112) ────────────────────────────────────────────

    @staticmethod
    def duplicate_aadhaar_director() -> KeyPersonData:
        """TC-112: a second Director reusing valid_director's Aadhaar."""
        data = PartBFactory.second_valid_director()
        data.aadhaar = PartBFactory.valid_director().aadhaar
        data.expected_error = PartBPage.DUPLICATE_AADHAAR_ERROR
        data.scenario_label = "duplicate_aadhaar_director"
        return data

    # ── Exit links (TC-443) ───────────────────────────────────────────────────

    @staticmethod
    def unsaved_name() -> KeyPersonData:
        """TC-443: a name typed and never saved."""
        return KeyPersonData(full_name="Meena Patil", scenario_label="unsaved_name")

    # ── As-you-type input rules (TC-88, TC-92, TC-104, TC-107, TC-438, TC-440) ─

    @staticmethod
    def aadhaar_typed_cases() -> list[TypedInput]:
        """TC-92: letters and symbols are removed; a pasted mixed value keeps its digits."""
        return [
            TypedInput("aadhaar_input", "A", ""),
            TypedInput("aadhaar_input", "!", ""),
            TypedInput("aadhaar_input", "23-45 67ab89", "23456789"),
        ]

    @staticmethod
    def aadhaar_max_length_case() -> TypedInput:
        """TC-88: a 13th digit is dropped."""
        return TypedInput("aadhaar_input", "2345678901234", "234567890123")

    @staticmethod
    def mobile_typed_cases() -> list[TypedInput]:
        """TC-107: letters and symbols are removed; digits are kept."""
        return [
            TypedInput("mobile_input", "A", ""),
            TypedInput("mobile_input", "#", ""),
            TypedInput("mobile_input", "9876543210", "9876543210"),
        ]

    @staticmethod
    def mobile_max_length_case() -> TypedInput:
        """TC-104: an 11th digit is dropped."""
        return TypedInput("mobile_input", "98765432101", "9876543210")

    @staticmethod
    def din_typed_cases() -> list[TypedInput]:
        """TC-438: DIN / DPIN keeps digits only, up to 8."""
        return [
            TypedInput("din_input", "AB-#", ""),
            TypedInput("din_input", "23456789", "23456789"),
            TypedInput("din_input", "234567890", "23456789"),
        ]

    @staticmethod
    def pan_typed_cases() -> list[TypedInput]:
        """TC-440: PAN is upper-cased, stripped to letters and digits, and cut at 10."""
        return [
            TypedInput("pan_input", "abcde1234f", "ABCDE1234F"),
            TypedInput("pan_input", "AB CD-E1234F", "ABCDE1234F"),
            TypedInput("pan_input", "ABCDE1234FG", "ABCDE1234F"),
        ]
