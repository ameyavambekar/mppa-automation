"""
Data Factory — Step 1 (Agency Identity / Part A)
=================================================
All test-data construction for the Step 1 form wizard.
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the Notion test cases KAN-TC-57 through KAN-TC-80.

Usage
-----
    from test_data.step1_factory import PartAData, PartAFactory

    data = PartAFactory.valid_mandatory_fields()     # TC-58 happy path
    data = PartAFactory.future_date()                # TC-62
    data = PartAFactory.invalid_tan_format()         # TC-64
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PartAData:
    agency_name: str = ""
    legal_constitution: str = ""
    date_of_incorporation: str = ""
    address_line1: str = ""
    official_email: str = ""
    mobile_number: str = ""
    tan_number: str = ""
    gst_number: str = ""
    address_line2: str = ""
    branch_offices: str = ""
    website_url: str = ""
    expected_error: Optional[str] = None
    scenario_label: str = ""


class PartAFactory:

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def valid_mandatory_fields() -> PartAData:
        """TC-58: All mandatory fields filled; all optional fields left blank."""
        return PartAData(
            agency_name="Alpha Placement Agency",
            legal_constitution="Private Limited Company",
            date_of_incorporation="15-03-2018",
            address_line1="101, Green Tower, MG Road, Pune",
            official_email="admin@alphaplacement.com",
            mobile_number="9876543210",
            scenario_label="valid_mandatory_fields",
        )

    # ── Date of Incorporation (TC-62, TC-63) ──────────────────────────────────

    @staticmethod
    def future_date() -> PartAData:
        """TC-62: Date of incorporation is in the future."""
        data = PartAFactory.valid_mandatory_fields()
        data.date_of_incorporation = "01-01-2030"
        data.expected_error = "Date of incorporation cannot be a future date."
        data.scenario_label = "future_date"
        return data

    @staticmethod
    def invalid_date_format() -> PartAData:
        """TC-63: Date entered in an invalid format (not dd-mm-yyyy)."""
        data = PartAFactory.valid_mandatory_fields()
        data.date_of_incorporation = "11-30-10000"
        data.expected_error = "Please enter a valid date in dd-mm-yyyy format."
        data.scenario_label = "invalid_date_format"
        return data

    # ── TAN (TC-64) ───────────────────────────────────────────────────────────

    @staticmethod
    def invalid_tan_format() -> PartAData:
        """TC-64 step 1: TAN in an incorrect format (not AAAA99999A)."""
        data = PartAFactory.valid_mandatory_fields()
        data.tan_number = "TAN12345"
        data.expected_error = "Invalid TAN format. Expected format: AAAA99999A."
        data.scenario_label = "invalid_tan_format"
        return data

    @staticmethod
    def valid_tan() -> PartAData:
        """TC-64 step 4: Correctly formatted TAN number."""
        data = PartAFactory.valid_mandatory_fields()
        data.tan_number = "PNEC12345A"
        data.scenario_label = "valid_tan"
        return data

    # ── GSTIN (TC-65) ─────────────────────────────────────────────────────────

    @staticmethod
    def invalid_gstin_format() -> PartAData:
        """TC-65 step 1: GSTIN in an incorrect format (not 15-character)."""
        data = PartAFactory.valid_mandatory_fields()
        data.gst_number = "27ABCDE123"
        data.expected_error = "Invalid GSTIN format. Expected 15-character GST Identification Number."
        data.scenario_label = "invalid_gstin_format"
        return data

    @staticmethod
    def valid_gstin() -> PartAData:
        """TC-65 step 3: Valid 15-character GSTIN."""
        data = PartAFactory.valid_mandatory_fields()
        data.gst_number = "27ABCDE1234F1Z5"
        data.scenario_label = "valid_gstin"
        return data

    # ── Email (TC-66) ─────────────────────────────────────────────────────────

    @staticmethod
    def invalid_email_format() -> PartAData:
        """TC-66 step 1: Email address missing @ and domain."""
        data = PartAFactory.valid_mandatory_fields()
        data.official_email = "adminalphaplacementcom"
        data.expected_error = "Please enter a valid email address."
        data.scenario_label = "invalid_email_format"
        return data

    # ── Mobile (TC-67, TC-75) ─────────────────────────────────────────────────

    @staticmethod
    def invalid_mobile_with_letters() -> PartAData:
        """TC-67 step 1: Mobile number containing letters."""
        data = PartAFactory.valid_mandatory_fields()
        data.mobile_number = "9876ABCD10"
        data.expected_error = "Please enter a valid 10-digit mobile number."
        data.scenario_label = "invalid_mobile_with_letters"
        return data

    @staticmethod
    def invalid_mobile_too_short() -> PartAData:
        """TC-67 step 3: Mobile number with fewer than 10 digits."""
        data = PartAFactory.valid_mandatory_fields()
        data.mobile_number = "98765"
        data.expected_error = "Please enter a valid 10-digit mobile number."
        data.scenario_label = "invalid_mobile_too_short"
        return data

    @staticmethod
    def invalid_mobile_starts_with_zero() -> PartAData:
        """TC-75: 10-digit mobile number beginning with 0."""
        data = PartAFactory.valid_mandatory_fields()
        data.mobile_number = "0987654321"
        data.expected_error = "Please enter a valid 10-digit mobile number."
        data.scenario_label = "invalid_mobile_starts_with_zero"
        return data

    # ── Website URL (TC-68) ───────────────────────────────────────────────────

    @staticmethod
    def invalid_website_url() -> PartAData:
        """TC-68 step 1: URL without http:// or https:// prefix."""
        data = PartAFactory.valid_mandatory_fields()
        data.website_url = "www.alphaplacement.com"
        data.expected_error = "Please enter a valid website URL"
        data.scenario_label = "invalid_website_url"
        return data

    @staticmethod
    def valid_website_url() -> PartAData:
        """TC-68 step 4: URL with https:// prefix."""
        data = PartAFactory.valid_mandatory_fields()
        data.website_url = "https://www.alphaplacement.com"
        data.scenario_label = "valid_website_url"
        return data

    # ── Agency Name (TC-74, TC-76) ────────────────────────────────────────────

    @staticmethod
    def agency_name_with_special_chars() -> PartAData:
        """TC-74: Agency name containing @, #, ! characters."""
        data = PartAFactory.valid_mandatory_fields()
        data.agency_name = "Alpha@Placement#2024!"
        data.expected_error = "Agency name contains invalid characters."
        data.scenario_label = "agency_name_with_special_chars"
        return data

    @staticmethod
    def duplicate_agency_name() -> PartAData:
        """TC-76: Agency name that already exists in the system (non-blocking warning)."""
        data = PartAFactory.valid_mandatory_fields()
        data.agency_name = "Alpha Placement Agency"
        data.expected_error = "An agency with this name already exists."
        data.scenario_label = "duplicate_agency_name"
        return data

    # ── Optional / partial fields (TC-71, TC-72, TC-73) ──────────────────────

    @staticmethod
    def without_branch_offices() -> PartAData:
        """TC-71: All mandatory fields filled; Branch Offices left blank."""
        return PartAData(
            agency_name="Test Agency",
            legal_constitution="Partnership",
            date_of_incorporation="14-10-2020",
            address_line1="A-302, Greenfield Acres, Palmont Drive, Mumbai",
            official_email="testmail@gmail.com",
            mobile_number="9359283811",
            scenario_label="without_branch_offices",
        )

    @staticmethod
    def with_branch_offices() -> PartAData:
        """TC-72: All mandatory fields plus two branch office addresses."""
        data = PartAFactory.valid_mandatory_fields()
        data.branch_offices = "22, Park Street, Mumbai\n5, Civil Lines, Nagpur"
        data.scenario_label = "with_branch_offices"
        return data

    @staticmethod
    def partial_fields_only() -> PartAData:
        """TC-73: Only Agency Name and Official Email filled; form not submitted."""
        return PartAData(
            agency_name="Alpha Placement",
            official_email="admin@alpha.com",
            scenario_label="partial_fields_only",
        )
