"""
Data Factory — Step 4 (Part F: Certificates, Licences & Signature)
==================================================================
All test-data construction for Part F of the Form-I wizard (KAN-21).
Each factory method maps to one Acceptance Criterion, Edge Case, or
scenario referenced in the AIO test cases KAN-TC-143 … KAN-TC-168,
KAN-TC-462 … KAN-TC-470, KAN-TC-574 … KAN-TC-579, KAN-TC-849 and KAN-TC-859 … KAN-TC-863.

Dates are given as the digits a user types (the field adds the slashes);
``shown`` is what the field then displays.

Usage
-----
    from test_data.partF_factory import PartFData, PartFFactory

    data = PartFFactory.all_no()          # TC-143 happy path
    data = PartFFactory.all_six()         # TC-144
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.file_manager import (CERTIFICATE_JPG, CERTIFICATE_PNG, SIGNATURE_JPG, SIGNATURE_OVERSIZED_PNG,
                                SIGNATURE_PNG, SIGNATURE_SMALL_DIMENSIONS_PNG, SIGNATURE_TRANSPARENT_PNG,
                                UNDERSIZED_FILE, UNDERSIZED_SIGNATURE, VALID_CERTIFICATE, VALID_SIGNATURE)


@dataclass
class TypedInput:
    """What is typed into a field and what the field shows afterwards."""
    typed: str
    shown: str


@dataclass
class CertificateData:
    number: Optional[str] = None
    date: Optional[TypedInput] = None
    document: Optional[str] = None              # file path


@dataclass
class PartFData:
    place: str = ""
    certificates: dict[str, CertificateData] = field(default_factory=dict)   # PartFPage.CERTIFICATES ids answered Yes
    # Since portal 2.1.0 the signature is required, so every scenario carries a valid one unless it sets another.
    signature: Optional[str] = SIGNATURE_TRANSPARENT_PNG    # file path
    premises: Optional[str] = None              # file path — office premises document (gone from Part F 20-Nov-2026)
    # Scenario-specific values
    invalid_values: list[str] = field(default_factory=list)   # bad values a negative scenario enters, in order
    valid_values: list[str] = field(default_factory=list)     # values that clear the error, in order
    expected_error: Optional[str] = None
    scenario_label: str = ""


def _date(shown: str) -> TypedInput:
    return TypedInput(shown.replace("/", ""), shown)


class PartFFactory:

    PLACE = "Pune"
    VALID_DATE = _date("15/06/2020")

    # ── Happy path ────────────────────────────────────────────────────────────

    @staticmethod
    def all_no() -> PartFData:
        """TC-143 / TC-148: every certificate No, Place chosen."""
        return PartFData(place=PartFFactory.PLACE, scenario_label="all_no")

    @staticmethod
    def all_six() -> PartFData:
        """TC-144: all six certificates Yes and fully filled, plus a signature."""
        return PartFData(
            place=PartFFactory.PLACE,
            certificates={
                "cl": CertificateData("CL/MH/2024/001", _date("15/06/2020"), VALID_CERTIFICATE),
                "sec": CertificateData("PSARA-MH-12345", _date("01/04/2021"), VALID_CERTIFICATE),
                "em": CertificateData("B-0123/MUM/PER/1000/5/9999/2022", _date("10/01/2022"), CERTIFICATE_JPG),
                "lin": CertificateData("1-2345-6789-0", _date("05/05/2019"), CERTIFICATE_PNG),
                "epf": CertificateData("MHBAN0012345000", _date("20/08/2018"), VALID_CERTIFICATE),
                "esic": CertificateData("31000123450001001", _date("20/08/2018"), VALID_CERTIFICATE),
            },
            signature=SIGNATURE_TRANSPARENT_PNG,
            scenario_label="all_six",
        )

    @staticmethod
    def contractor_licence() -> PartFData:
        """TC-154 / TC-155 / TC-160: a complete Contractor Licence; tests drop the part they check."""
        return PartFData(
            place=PartFFactory.PLACE,
            certificates={"cl": CertificateData("CL/MH/2024/001", PartFFactory.VALID_DATE, VALID_CERTIFICATE)},
            scenario_label="contractor_licence",
        )

    @staticmethod
    def lin_only() -> PartFData:
        """TC-163: only the LIN answered Yes."""
        return PartFData(
            place=PartFFactory.PLACE,
            certificates={"lin": CertificateData("1-2345-6789-0", _date("05/05/2019"), CERTIFICATE_PNG)},
            scenario_label="lin_only",
        )

    # ── Field rules ───────────────────────────────────────────────────────────

    @staticmethod
    def future_date() -> PartFData:
        """TC-160: a Date of Issue after today, then a past one."""
        data = PartFFactory.contractor_licence()
        data.invalid_values = ["01012099"]
        data.valid_values = [PartFFactory.VALID_DATE.typed]
        data.scenario_label = "future_date"
        return data

    @staticmethod
    def invalid_dates() -> PartFData:
        """TC-161: an impossible date, a year before 1900, an incomplete date."""
        data = PartFFactory.contractor_licence()
        data.invalid_values = ["31022024", "01011899", "010120"]
        data.scenario_label = "invalid_dates"
        return data

    @staticmethod
    def psara_number_rules() -> PartFData:
        """TC-466: too short, starting with a symbol, a disallowed character; then a valid number."""
        return PartFData(
            place=PartFFactory.PLACE,
            certificates={"sec": CertificateData(None, _date("01/04/2021"), VALID_CERTIFICATE)},
            invalid_values=["AB", "-ABC123", "PSARA#123"],
            valid_values=["PSARA-MH/12345 (2021)"],
            scenario_label="psara_number_rules",
        )

    @staticmethod
    def with_premises_document() -> PartFData:
        """TC-579 (offline service mode): every certificate No, a valid office premises document."""
        data = PartFFactory.all_no()
        data.premises = VALID_CERTIFICATE
        data.scenario_label = "with_premises_document"
        return data

    # ── Files under 10 KB (checked by the server on save) ─────────────────────

    @staticmethod
    def undersized_certificate() -> PartFData:
        """TC-574: a complete Contractor Licence whose document is a 298-byte PDF."""
        return PartFData(
            place=PartFFactory.PLACE,
            certificates={"cl": CertificateData("CL/MH/2024/001", PartFFactory.VALID_DATE, UNDERSIZED_FILE)},
            scenario_label="undersized_certificate",
        )

    # ── Signatures the page checks while cleaning them (since 20-Nov-2026) ────

    @staticmethod
    def undersized_signature() -> PartFData:
        """TC-575: signatures below 150 × 40 pixels — an 8 × 8 PNG (72 bytes) and a 140 × 38 PNG —
        both rejected in the browser."""
        return PartFData(
            place=PartFFactory.PLACE,
            signature=UNDERSIZED_SIGNATURE,
            invalid_values=[UNDERSIZED_SIGNATURE, SIGNATURE_SMALL_DIMENSIONS_PNG],
            expected_error="The image is too small — upload a clear signature (at least 150 × 40 pixels).",
            scenario_label="undersized_signature",
        )

    @staticmethod
    def opaque_signature() -> PartFData:
        """KAN-TC-849: every certificate No, a 320 × 120 PNG with a white background (RGB, no alpha channel);
        the page removes the background before saving."""
        return PartFData(
            place=PartFFactory.PLACE,
            signature=SIGNATURE_PNG,
            scenario_label="opaque_signature",
        )

    @staticmethod
    def unreadable_signature() -> PartFData:
        """KAN-TC-862: a 170-byte "signature.png" that is not a valid image."""
        return PartFData(
            place=PartFFactory.PLACE,
            signature=VALID_SIGNATURE,
            expected_error="The image could not be read — choose a JPG, JPEG or PNG file.",
            scenario_label="unreadable_signature",
        )

    @staticmethod
    def uncleanable_signature() -> PartFData:
        """KAN-TC-863: a ~1.5 MB PNG of random coloured pixels — no plain background to remove."""
        return PartFData(
            place=PartFFactory.PLACE,
            signature=SIGNATURE_OVERSIZED_PNG,
            expected_error=("The background could not be removed — photograph the signature on plain white "
                            "paper in good light."),
            scenario_label="uncleanable_signature",
        )

    @staticmethod
    def without_signature() -> PartFData:
        """KAN-TC-861: every certificate No, Place chosen, no signature."""
        return PartFData(
            place=PartFFactory.PLACE,
            signature=None,
            expected_error="Upload the signature (JPG, JPEG or PNG).",
            scenario_label="without_signature",
        )

    @staticmethod
    def jpg_signature() -> PartFData:
        """KAN-TC-152: every certificate No, a JPG signature on white paper — saved as signature_valid.png."""
        return PartFData(place=PartFFactory.PLACE, signature=SIGNATURE_JPG, scenario_label="jpg_signature")

    @staticmethod
    def replacement_signature(current: str) -> str:
        """KAN-TC-153: a signature file whose cleaned name differs from ``current`` (the one on file)."""
        return SIGNATURE_JPG if current == "signature_transparent.png" else SIGNATURE_TRANSPARENT_PNG

    @staticmethod
    def ra_compulsory_blank() -> PartFData:
        """KAN-TC-860: RA compulsory but left blank; a signature and a Place chosen."""
        return PartFData(place=PartFFactory.PLACE, scenario_label="ra_compulsory_blank")

    # ── As-you-type input rules (TC-467) ──────────────────────────────────────

    @staticmethod
    def date_typed_cases() -> list[TypedInput]:
        """TC-467: slashes are added, letters dropped, 10 characters at most. The last case
        types the slashes too — it shows 01//01/202 on dev (defect, 28-Oct-2026)."""
        return [
            TypedInput("01012024", "01/01/2024"),
            TypedInput("1a5b0620c20", "15/06/2020"),
            TypedInput("15062020999", "15/06/2020"),
            TypedInput("01/01/2024", "01/01/2024"),
        ]
