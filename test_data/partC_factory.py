"""
Data Factory — Step 3 (Part C: Operations & Infrastructure)
===========================================================
All test-data construction for Part C of the Form-I wizard (KAN-20).
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the AIO test cases KAN-TC-120 … KAN-TC-142 and
KAN-TC-444 … KAN-TC-460.

Usage
-----
    from test_data.partC_factory import PartCData, PartCFactory

    data = PartCFactory.minimal()                 # TC-120 happy path
    data = PartCFactory.with_training()           # TC-127
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pages.partC_page import PartCPage


@dataclass
class TypedInput:
    """What is typed into a field and what the field shows afterwards."""
    typed: str
    shown: str


@dataclass
class PartCData:
    placement_type: str = ""
    service_mode: str = ""
    sectors: list[str] = field(default_factory=list)
    service_models: list[str] = field(default_factory=list)   # PartCPage.SERVICE_MODELS values
    charges_displayed: bool = True
    sector_other: Optional[str] = None                        # only when "Other" is in sectors
    digital_platform_details: Optional[str] = None            # None → digital platform = No
    training: bool = False
    training_mode: Optional[str] = None
    training_capacity: Optional[str] = None
    training_sectors: Optional[str] = None
    training_address: Optional[str] = None                    # None → "same as registered office"
    mobilization: bool = False
    mobilization_address: Optional[str] = None                # None → "same as registered office"
    other_services: Optional[str] = None
    website: Optional[str] = None
    # Scenario-specific values
    invalid_values: list[str] = field(default_factory=list)   # bad values a negative scenario enters, in order
    valid_values: list[str] = field(default_factory=list)     # values that clear the error, in order
    expected_error: Optional[str] = None
    scenario_label: str = ""


class PartCFactory:

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def minimal() -> PartCData:
        """TC-120 / TC-136: mandatory fields only, every Yes/No question left at No."""
        return PartCData(
            placement_type="Domestic",
            service_mode="Online Only",
            sectors=["IT / Software"],
            service_models=["b2b"],
            charges_displayed=True,
            scenario_label="minimal",
        )

    @staticmethod
    def offline() -> PartCData:
        """Agency builder: mandatory fields with Service Mode "Offline Only", so Part F asks
        for the office premises document."""
        data = PartCFactory.minimal()
        data.service_mode = "Offline Only"
        data.scenario_label = "offline"
        return data

    @staticmethod
    def with_training() -> PartCData:
        """TC-127: training = Yes with its own centre address."""
        data = PartCFactory.minimal()
        data.training = True
        data.training_mode = "Offline"
        data.training_capacity = "100"
        data.training_sectors = "IT, Healthcare"
        data.training_address = "12 MG Road, Pune 411001"
        data.scenario_label = "with_training"
        return data

    @staticmethod
    def full() -> PartCData:
        """TC-142: every section filled — all sectors incl. Other, all three Yes blocks, website."""
        return PartCData(
            placement_type="Both Domestic & International",
            service_mode="Both Online & Offline",
            sectors=list(PartCPage.SECTORS),
            sector_other="Fintech & Payments",
            service_models=list(PartCPage.SERVICE_MODELS),
            charges_displayed=True,
            digital_platform_details="www.youragency.in and the YourAgency Jobs app",
            training=True,
            training_mode="Hybrid",
            training_capacity="500",
            training_sectors="IT, Healthcare",
            training_address="12 MG Road, Pune 411001",
            mobilization=True,
            mobilization_address=None,
            other_services="Interview coaching",
            website="https://www.youragency.in",
            scenario_label="full",
        )

    @staticmethod
    def with_other_services() -> PartCData:
        """TC-137: Other Services filled (52 characters)."""
        data = PartCFactory.minimal()
        data.other_services = "Resume writing, interview coaching, skill assessment"
        data.scenario_label = "with_other_services"
        return data

    @staticmethod
    def service_charges() -> PartCData:
        """TC-460: two agency types, charges not displayed."""
        data = PartCFactory.minimal()
        data.service_models = ["b2b", "b2c"]
        data.charges_displayed = False
        data.scenario_label = "service_charges"
        return data

    @staticmethod
    def with_digital_platform() -> PartCData:
        """TC-449: digital platform = Yes; 9 characters first, then valid details."""
        data = PartCFactory.minimal()
        data.digital_platform_details = "www.youragency.in and the YourAgency Jobs app"
        data.invalid_values = ["Jobs app."]
        data.expected_error = PartCPage.DIGITAL_DETAILS_MIN_ERROR.format(n=9)
        data.scenario_label = "with_digital_platform"
        return data

    @staticmethod
    def training_same_address() -> PartCData:
        """TC-450: training = Yes at the registered office address."""
        data = PartCFactory.with_training()
        data.training_address = None
        data.scenario_label = "training_same_address"
        return data

    @staticmethod
    def mobilization_same_address() -> PartCData:
        """TC-451: mobilization = Yes at the registered office address."""
        data = PartCFactory.minimal()
        data.mobilization = True
        data.scenario_label = "mobilization_same_address"
        return data

    # ── Field rules ───────────────────────────────────────────────────────────

    @staticmethod
    def training_capacity_zero() -> PartCData:
        """TC-130: 0 is rejected, 999999 is accepted."""
        return PartCData(invalid_values=["0"], valid_values=["999999"],
                         expected_error=PartCPage.TRAINING_CAPACITY_RANGE_ERROR,
                         scenario_label="training_capacity_zero")

    @staticmethod
    def sector_other_invalid() -> PartCData:
        """TC-448: one character, then a disallowed character."""
        return PartCData(invalid_values=["A", "Fintech $"], valid_values=["Fintech & Payments"],
                         scenario_label="sector_other_invalid")

    @staticmethod
    def centre_address_invalid() -> PartCData:
        """TC-452: 9 characters, then angle brackets; semicolons are allowed."""
        return PartCData(invalid_values=["MG Road 1", "12 MG Road <Pune>"],
                         valid_values=["Unit 4; 12 MG Road, Pune 411001"],
                         scenario_label="centre_address_invalid")

    @staticmethod
    def training_sectors_invalid() -> PartCData:
        """TC-453: one character, then a disallowed character."""
        return PartCData(invalid_values=["I", "IT $"], valid_values=["IT, Healthcare"],
                         scenario_label="training_sectors_invalid")

    @staticmethod
    def website_cases() -> PartCData:
        """TC-454: no domain ending, then a space; a bare domain and a full URL pass."""
        return PartCData(invalid_values=["youragency", "www.your agency.in"],
                         valid_values=["www.youragency.in", "https://youragency.in/about"],
                         expected_error=PartCPage.WEBSITE_INVALID_ERROR,
                         scenario_label="website_cases")

    @staticmethod
    def other_services_no_letters() -> PartCData:
        """TC-455: digits and symbols only, then text with letters."""
        return PartCData(invalid_values=["12345 !!!"], valid_values=["Interview coaching"],
                         expected_error=PartCPage.OTHER_SERVICES_TEXT_ERROR,
                         scenario_label="other_services_no_letters")

    # ── As-you-type input rules (TC-130) ──────────────────────────────────────

    @staticmethod
    def training_capacity_typed_cases() -> list[TypedInput]:
        """TC-130: non-digits are stripped and at most 6 digits are kept."""
        return [
            TypedInput("12a,3", "123"),
            TypedInput("1234567", "123456"),
            TypedInput("-10", "10"),
            TypedInput("12.5", "125"),
        ]
