"""
Data Factory — Step 1 (Part A: Agency Basic Details)
====================================================
All test-data construction for Part A of the Form-I wizard (KAN-8).
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the AIO test cases KAN-TC-58 … KAN-TC-80 and
KAN-TC-426 … KAN-TC-436.

The head office defaults to Maharashtra, whose District is read-only and
comes from registration (``AgencyRegistrationFactory`` registers agencies in
Pune), so the head office Taluka must be a Pune taluka.

Usage
-----
    from test_data.step1_factory import PartAData, PartAFactory

    data = PartAFactory.valid_mandatory_fields()     # TC-58 happy path
    data = PartAFactory.future_date()                # TC-62
    data = PartAFactory.head_office_outside_maharashtra()  # TC-427 / TC-428
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pages.partA_page import PartAPage
from utils.file_manager import VALID_CERTIFICATE


@dataclass
class OfficeAddress:
    """A Maharashtra office: the Primary Maharashtra Office block or a branch card."""
    address: str
    district: str          # district name as shown in the drop-down
    taluka: str            # must belong to ``district``
    city: str
    pincode: str
    premise_type: str = "" # branches only (PartAPage.PREMISE_TYPES)
    premise_other: Optional[str] = None


@dataclass
class TypedInput:
    """What is typed into a field and what the field shows afterwards."""
    field: str             # PartAPage locator property name
    typed: str
    shown: str


@dataclass
class PartAData:
    # Agency Constitution
    legal_constitution: str = ""
    date_of_establishment: str = ""           # dd-mm-yyyy, set via the calendar
    incorporation_no: str = ""
    incorporation_certificate: Optional[str] = None
    # Tax Registration
    tan_number: str = ""
    tan_certificate: Optional[str] = None
    gstin: str = ""
    gst_certificate: Optional[str] = None
    # Registered Office Address
    state: str = "Maharashtra"
    address_line1: str = ""
    address_line2: str = ""
    district: str = ""                        # only typed for a head office outside Maharashtra
    taluka: str = ""
    city: str = ""
    pincode: str = ""
    mh_office: Optional[OfficeAddress] = None # required when state != Maharashtra
    branches: list[OfficeAddress] = field(default_factory=list)
    # Authorised Signatory
    authorised_signatory: str = ""
    designation: str = ""
    aadhaar: str = ""
    # Scenario-specific values
    invalid_value: str = ""                   # the bad value a negative scenario enters
    partial_value: str = ""                   # an incomplete value typed before the full one
    forced_date_text: str = ""                # text forced into the read-only date box
    expected_error: Optional[str] = None
    scenario_label: str = ""


class PartAFactory:

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def valid_mandatory_fields() -> PartAData:
        """TC-58: every mandatory Part A field, Maharashtra head office, no branches."""
        return PartAData(
            legal_constitution="Private Limited Company",
            date_of_establishment="15-03-2018",
            incorporation_no="U74999MH2018PTC123456",
            incorporation_certificate=VALID_CERTIFICATE,
            tan_number="PNEC12345A",
            tan_certificate=VALID_CERTIFICATE,
            gstin="27ABCDE1234F1Z5",
            gst_certificate=VALID_CERTIFICATE,
            address_line1="101, Green Tower, MG Road",
            taluka="Pune City",
            city="Pune",
            pincode="411001",
            authorised_signatory="Ravi Kulkarni",
            designation="Director",
            scenario_label="valid_mandatory_fields",
        )

    # ── Date of Establishment (TC-62, TC-63) ─────────────────────────────────

    @staticmethod
    def future_date() -> PartAData:
        """TC-62: a future date forced into the read-only date box."""
        data = PartAFactory.valid_mandatory_fields()
        data.forced_date_text = "01/01/2030"
        data.expected_error = PartAPage.DATE_FUTURE_ALERT
        data.scenario_label = "future_date"
        return data

    @staticmethod
    def invalid_date_format() -> PartAData:
        """TC-63: a typed value (ignored — the box is read-only) and a non DD/MM/YYYY value forced in."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = "11-30-10000"
        data.forced_date_text = "2018-03-15"
        data.expected_error = PartAPage.DATE_FORMAT_ALERT
        data.scenario_label = "invalid_date_format"
        return data

    # ── TAN (TC-64) ───────────────────────────────────────────────────────────

    @staticmethod
    def invalid_tan_format() -> PartAData:
        """TC-64: a TAN that doesn't match 4 letters + 5 digits + 1 letter."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = "TAN12345"
        data.scenario_label = "invalid_tan_format"
        return data

    # ── GSTIN (TC-65) ─────────────────────────────────────────────────────────

    @staticmethod
    def invalid_gstin_format() -> PartAData:
        """TC-65: 15 characters that don't match the GSTIN pattern (14th char is not Z)."""
        data = PartAFactory.valid_mandatory_fields()
        data.partial_value = "27ABCDE123"
        data.invalid_value = "27ABCDE1234F1X5"
        data.expected_error = PartAPage.GSTIN_INVALID_HINT
        data.scenario_label = "invalid_gstin_format"
        return data

    # ── Branch offices (TC-71, TC-72, TC-431, TC-435) ────────────────────────

    @staticmethod
    def without_branch_offices() -> PartAData:
        """TC-71: all mandatory fields, no branch office added."""
        data = PartAFactory.valid_mandatory_fields()
        data.scenario_label = "without_branch_offices"
        return data

    @staticmethod
    def with_branch_offices() -> PartAData:
        """TC-72: all mandatory fields plus two branch offices."""
        data = PartAFactory.valid_mandatory_fields()
        data.branches = [
            OfficeAddress("22, Park Street", "Pune", "Haveli", "Pune", "411028", "Rented Office Space"),
            OfficeAddress("5, Civil Lines", "Nagpur", "Nagpur", "Nagpur", "440001", "Owned Office Space"),
        ]
        data.scenario_label = "with_branch_offices"
        return data

    @staticmethod
    def branch_premise_other() -> PartAData:
        """TC-431: one branch whose premise type is Other, needing 'Please Specify'."""
        data = PartAFactory.valid_mandatory_fields()
        data.branches = [OfficeAddress("22, Park Street", "Pune", "Haveli", "Pune", "411028", "Other",
                                       premise_other="Shared office in a residential society")]
        data.scenario_label = "branch_premise_other"
        return data

    # ── Head office outside Maharashtra (TC-427, TC-428) ─────────────────────

    @staticmethod
    def head_office_outside_maharashtra() -> PartAData:
        """TC-427 / TC-428: head office in Gujarat plus the Primary Maharashtra Office."""
        data = PartAFactory.valid_mandatory_fields()
        data.state = "Gujarat"
        data.address_line1 = "12, Ashram Road"
        data.district = "Ahmedabad"
        data.taluka = "Ahmedabad City"
        data.city = "Ahmedabad"
        data.pincode = "380009"
        data.mh_office = OfficeAddress("22, Park Street", "Pune", "Haveli", "Pune", "411028")
        data.scenario_label = "head_office_outside_maharashtra"
        return data

    # ── Proprietorship (TC-430) ──────────────────────────────────────────────

    @staticmethod
    def proprietorship_without_incorporation() -> PartAData:
        """TC-430: a Proprietorship saved without incorporation number or certificate."""
        data = PartAFactory.valid_mandatory_fields()
        data.legal_constitution = "Proprietorship"
        data.incorporation_no = ""
        data.incorporation_certificate = None
        data.designation = "Proprietor"
        data.scenario_label = "proprietorship_without_incorporation"
        return data

    # ── Partial data (TC-429, TC-80) ──────────────────────────────────────────

    @staticmethod
    def partial_fields_only() -> PartAData:
        """TC-429: a few fields entered without saving; Designation added after reopening."""
        return PartAData(
            incorporation_no="U74999MH2018PTC123456",
            authorised_signatory="Ravi Kulkarni",
            designation="Director",
            scenario_label="partial_fields_only",
        )

    @staticmethod
    def session_timeout_partial() -> PartAData:
        """TC-80: fields entered before the session times out."""
        return PartAData(
            incorporation_no="U74999MH2018PTC123456",
            authorised_signatory="Delta Kumar",
            scenario_label="session_timeout_partial",
        )

    # ── Browser back (TC-78) ─────────────────────────────────────────────────

    @staticmethod
    def unsaved_signatory() -> PartAData:
        """TC-78: one value entered and not saved before pressing browser back."""
        return PartAData(authorised_signatory="Beta Kumar", scenario_label="unsaved_signatory")

    # ── Pincode range (TC-434) ───────────────────────────────────────────────

    @staticmethod
    def pincode_outside_maharashtra() -> PartAData:
        """TC-434: an out-of-range pincode, then one inside 400000–445999."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = "380009"
        data.pincode = "411001"
        data.expected_error = PartAPage.PIN_INVALID_HINT
        data.scenario_label = "pincode_outside_maharashtra"
        return data

    # ── As-you-type input rules (TC-436, TC-64 step 1) ───────────────────────

    @staticmethod
    def as_you_type_cases() -> list[TypedInput]:
        """TC-436: what each Part A text field shows after typing raw input."""
        return [
            TypedInput("incorporation_no_input", "u74999-mh/2018 ptc#123", "U74999-MH/2018 PTC123"),
            TypedInput("tan_number_input", "pnec-12345a", "PNEC12345A"),
            TypedInput("gst_number_input", "27abcde1234f1z5", "27ABCDE1234F1Z5"),
            TypedInput("aadhaar_input", "1234-5678-9012-34", "123456789012"),
            TypedInput("pincode_input", "41100A12", "411001"),
        ]

    @staticmethod
    def tan_typed_lowercase() -> TypedInput:
        """TC-64 step 1: a lower-case TAN with separators is upper-cased and stripped."""
        return TypedInput("tan_number_input", "pnec-12345a!", "PNEC12345A")
