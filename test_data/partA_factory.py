"""
Data Factory — Step 1 (Part A: Agency Basic Details)
====================================================
All test-data construction for Part A of the Form-I wizard (KAN-8).
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the AIO test cases KAN-TC-58 … KAN-TC-80 and
KAN-TC-426 … KAN-TC-436.

Values are random but always valid for the portal: talukas come from the
portal's own district → taluka table (``test_data.maharashtra_locations``),
pincodes fall in the Maharashtra range, TAN / GSTIN / dates match Part A's
formats.

The head office defaults to Maharashtra, whose District is read-only and
comes from registration, so its Taluka must belong to the *registered*
district of whoever is logged in. Factory methods pick a random district;
call ``PartAFactory.for_user(data, user)`` with the state-store user the test
logged in as to re-point the head office (taluka / city / pincode) at that
user's district and build the GSTIN from the user's PAN.

Usage
-----
    from test_data.partA_factory import PartAData, PartAFactory

    data = PartAFactory.valid_mandatory_fields()     # TC-58 happy path
    data = PartAFactory.for_user(data, user)         # match the logged-in user
    data = PartAFactory.future_date()                # TC-62
    data = PartAFactory.head_office_outside_maharashtra()  # TC-427 / TC-428
"""

from __future__ import annotations

import dataclasses
import random
import string
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from faker import Faker

from pages.partA_page import PartAPage
from test_data.maharashtra_locations import (
    DISTRICT_IDS, is_listed_district, random_district, random_mh_pincode, random_taluka,
)
from utils.file_manager import VALID_CERTIFICATE

fake = Faker("en_IN")

MH_STATE_CODE = "27"     # GSTIN state code for Maharashtra


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
    # Meta — registered district the Maharashtra head office taluka belongs to
    registered_district: str = ""


# ── Random value helpers ──────────────────────────────────────────────────────

def _letters(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase, k=n))


def _digits(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))


def _random_pan() -> str:
    return f"{_letters(5)}{_digits(4)}{_letters(1)}"


def _random_gstin(pan: Optional[str] = None) -> str:
    """27 + PAN + entity number (1-9/A-Z) + 'Z' + check character — Part A's GSTIN pattern."""
    entity = random.choice("123456789" + string.ascii_uppercase)
    check = random.choice(string.ascii_uppercase + string.digits)
    return f"{MH_STATE_CODE}{(pan or _random_pan()).upper()}{entity}Z{check}"


def _random_tan() -> str:
    """4 letters + 5 digits + 1 letter, e.g. PNEC12345A."""
    return f"{_letters(4)}{_digits(5)}{_letters(1)}"


def _random_past_date(min_years: int = 1, max_years: int = 25) -> date:
    today = date.today()
    return today - timedelta(days=random.randint(365 * min_years, 365 * max_years))


def _random_cin(year: int) -> str:
    """Corporate Identification Number for a Maharashtra private company, e.g. U74999MH2018PTC123456."""
    return f"U{_digits(5)}MH{year}PTC{_digits(6)}"


def _random_person() -> str:
    return f"{fake.first_name()} {fake.last_name()}"


_STREET_TYPES = ("Road", "Marg", "Nagar", "Chowk", "Lane", "Path")


def _random_address() -> str:
    """Street address using only letters, digits, commas and spaces."""
    return f"{random.randint(1, 450)}, {fake.last_name()} {random.choice(_STREET_TYPES)}"


def _random_locality() -> str:
    return f"Near {fake.last_name()} {random.choice(('Market', 'Hospital', 'School', 'Temple', 'Bus Stand'))}"


def _city_for(district: str, taluka: str) -> str:
    return random.choice((district, taluka))


def _random_mh_office(district: Optional[str] = None, premise_type: str = "") -> OfficeAddress:
    """A Maharashtra office in ``district`` (random when omitted) with a matching taluka."""
    district = district if is_listed_district(district) else random_district()
    taluka = random_taluka(district)
    return OfficeAddress(_random_address(), district, taluka, _city_for(district, taluka),
                         random_mh_pincode(), premise_type)


def _random_pincode_outside_mh() -> str:
    return str(random.choice((random.randint(110000, 399999), random.randint(446000, 855999))))


# Head offices outside Maharashtra: state → (district, taluka, city, pincode prefix)
_OUT_OF_STATE = {
    "Gujarat": ("Ahmedabad", "Ahmedabad City", "Ahmedabad", "380"),
    "Karnataka": ("Bengaluru Urban", "Bengaluru North", "Bengaluru", "560"),
    "Telangana": ("Hyderabad", "Hyderabad", "Hyderabad", "500"),
    "Madhya Pradesh": ("Indore", "Indore", "Indore", "452"),
    "Goa": ("North Goa", "Tiswadi", "Panaji", "403"),
}

_PREMISE_OTHER_DESCRIPTIONS = (
    "Shared office in a residential society",
    "Space provided by a partner organisation",
    "Temporary site office at a client location",
    "Room in a community hall",
)


class PartAFactory:

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def valid_mandatory_fields(district: Optional[str] = None, pan: Optional[str] = None) -> PartAData:
        """TC-58: every mandatory Part A field, Maharashtra head office, no branches.

        The head office taluka belongs to ``district`` (a random listed district
        when omitted); the GSTIN embeds ``pan`` when given. Legal constitution
        stays Private Limited Company — Part B's Director cards depend on it.
        """
        district = district if is_listed_district(district) else random_district()
        taluka = random_taluka(district)
        established = _random_past_date()
        return PartAData(
            legal_constitution="Private Limited Company",
            date_of_establishment=established.strftime("%d-%m-%Y"),
            incorporation_no=_random_cin(established.year),
            incorporation_certificate=VALID_CERTIFICATE,
            tan_number=_random_tan(),
            tan_certificate=VALID_CERTIFICATE,
            gstin=_random_gstin(pan),
            gst_certificate=VALID_CERTIFICATE,
            address_line1=_random_address(),
            taluka=taluka,
            city=_city_for(district, taluka),
            pincode=random_mh_pincode(),
            authorised_signatory=_random_person(),
            designation="Director",
            registered_district=district,
            scenario_label="valid_mandatory_fields",
        )

    @staticmethod
    def for_user(data: PartAData, user) -> PartAData:
        """Returns a copy of ``data`` that fits the state-store ``user`` the test logged in as.

        * Maharashtra head office: taluka / city / pincode re-picked from the
          user's registered district (Part A only offers that district's talukas).
        * GSTIN: rebuilt around the user's registered PAN (only when ``data``
          carries a valid GSTIN — invalid-GSTIN scenarios keep their bad value).
        """
        data = dataclasses.replace(data, branches=list(data.branches))
        if data.state == "Maharashtra" and data.taluka:
            if not is_listed_district(user.district):
                raise ValueError(
                    f"{user.username} is registered in {user.district!r}, which carries no Maharashtra "
                    "district into Part A — use a user registered in one of the listed districts."
                )
            data.taluka = random_taluka(user.district)
            data.city = _city_for(user.district, data.taluka)
            data.pincode = data.pincode or random_mh_pincode()
            data.registered_district = user.district
        if data.gstin and getattr(user, "pan", None):
            data.gstin = _random_gstin(user.pan)
        return data

    @staticmethod
    def state_store_data(data: PartAData) -> dict:
        """The facts later steps branch on, recorded with Part A in the state store:
        agency type (Part B key-person label and fields), head-office state and
        branch count."""
        return {
            "legal_constitution": data.legal_constitution,
            "state": data.state,
            "branches": len(data.branches),
        }

    # ── Date of Establishment (TC-62, TC-63) ─────────────────────────────────

    @staticmethod
    def future_date() -> PartAData:
        """TC-62: a future date forced into the read-only date box."""
        data = PartAFactory.valid_mandatory_fields()
        future = date.today() + timedelta(days=random.randint(30, 5 * 365))
        data.forced_date_text = future.strftime("%d/%m/%Y")
        data.expected_error = PartAPage.DATE_FUTURE_ALERT
        data.scenario_label = "future_date"
        return data

    @staticmethod
    def invalid_date_format() -> PartAData:
        """TC-63: a typed value (ignored — the box is read-only) and a non DD/MM/YYYY value forced in."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = f"{random.randint(13, 99)}-{random.randint(32, 99)}-{random.randint(10000, 99999)}"
        data.forced_date_text = _random_past_date().strftime("%Y-%m-%d")     # ISO, not DD/MM/YYYY
        data.expected_error = PartAPage.DATE_FORMAT_ALERT
        data.scenario_label = "invalid_date_format"
        return data

    # ── TAN (TC-64) ───────────────────────────────────────────────────────────

    @staticmethod
    def invalid_tan_format() -> PartAData:
        """TC-64: a TAN that doesn't match 4 letters + 5 digits + 1 letter (3 letters + 5 digits)."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = f"{_letters(3)}{_digits(5)}"
        data.scenario_label = "invalid_tan_format"
        return data

    # ── GSTIN (TC-65) ─────────────────────────────────────────────────────────

    @staticmethod
    def invalid_gstin_format() -> PartAData:
        """TC-65: 15 characters that don't match the GSTIN pattern (14th char is not Z)."""
        data = PartAFactory.valid_mandatory_fields()
        good = _random_gstin()
        not_z = random.choice(string.ascii_uppercase.replace("Z", ""))
        data.partial_value = good[:10]
        data.invalid_value = f"{good[:13]}{not_z}{good[14]}"
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
        """TC-72: all mandatory fields plus two branch offices in different districts."""
        data = PartAFactory.valid_mandatory_fields()
        first, second = random.sample(sorted(DISTRICT_IDS), 2)
        premises = [p for p in PartAPage.PREMISE_TYPES if p != "Other"]
        data.branches = [
            _random_mh_office(first, random.choice(premises)),
            _random_mh_office(second, random.choice(premises)),
        ]
        data.scenario_label = "with_branch_offices"
        return data

    @staticmethod
    def branch_premise_other() -> PartAData:
        """TC-431: one branch whose premise type is Other, needing 'Please Specify'."""
        data = PartAFactory.valid_mandatory_fields()
        branch = _random_mh_office(premise_type="Other")
        branch.premise_other = random.choice(_PREMISE_OTHER_DESCRIPTIONS)
        data.branches = [branch]
        data.scenario_label = "branch_premise_other"
        return data

    # ── Head office outside Maharashtra (TC-427, TC-428) ─────────────────────

    @staticmethod
    def head_office_outside_maharashtra() -> PartAData:
        """TC-427 / TC-428: head office in another state plus the Primary Maharashtra Office."""
        data = PartAFactory.valid_mandatory_fields()
        state = random.choice(sorted(_OUT_OF_STATE))
        district, taluka, city, pin_prefix = _OUT_OF_STATE[state]
        data.state = state
        data.address_line1 = _random_address()
        data.district = district
        data.taluka = taluka
        data.city = city
        data.pincode = f"{pin_prefix}{_digits(3)}"
        data.registered_district = ""
        data.mh_office = _random_mh_office()
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
            incorporation_no=_random_cin(_random_past_date().year),
            authorised_signatory=_random_person(),
            designation="Director",
            scenario_label="partial_fields_only",
        )

    @staticmethod
    def session_timeout_partial() -> PartAData:
        """TC-80: fields entered before the session times out."""
        return PartAData(
            incorporation_no=_random_cin(_random_past_date().year),
            authorised_signatory=_random_person(),
            scenario_label="session_timeout_partial",
        )

    # ── Browser back (TC-78) ─────────────────────────────────────────────────

    @staticmethod
    def unsaved_signatory() -> PartAData:
        """TC-78: one value entered and not saved before pressing browser back."""
        return PartAData(authorised_signatory=_random_person(), scenario_label="unsaved_signatory")

    # ── Pincode range (TC-434) ───────────────────────────────────────────────

    @staticmethod
    def pincode_outside_maharashtra() -> PartAData:
        """TC-434: an out-of-range pincode, then one inside 400000–445999."""
        data = PartAFactory.valid_mandatory_fields()
        data.invalid_value = _random_pincode_outside_mh()
        data.pincode = random_mh_pincode()
        data.expected_error = PartAPage.PIN_INVALID_HINT
        data.scenario_label = "pincode_outside_maharashtra"
        return data

    # ── As-you-type input rules (TC-436, TC-64 step 1) ───────────────────────
    # Kept fixed on purpose: each pair documents one exact filtering rule.

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
