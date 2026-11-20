"""
Data Factory — Declaration & Authorisation
==========================================
All test-data construction for the Declaration step (KAN-10).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-490 … KAN-TC-503 and KAN-TC-868 … KAN-TC-870.

Files are keyed by the form card (see ``DeclarationPage.FORMS``): "ia" is
FORM-I(A) — Self-Declaration, "ib" is FORM-I(B) — Letter of Authorization.

Usage
-----
    from test_data.declaration_factory import DeclarationData, DeclarationFactory

    data = DeclarationFactory.signed_forms()      # TC-495
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pages.declaration_page import DeclarationPage
from utils.file_manager import (CERTIFICATE_JPG, CERTIFICATE_PNG, EMPTY_PDF, JPG_AS_PDF, OVERSIZED_FILE,
                                REPLACEMENT_PDF, UNDERSIZED_FILE, VALID_CERTIFICATE)


@dataclass
class DeclarationData:
    files: dict[str, str] = field(default_factory=dict)        # form key → signed PDF path
    # Scenario-specific values
    invalid_files: dict[str, str] = field(default_factory=dict)  # form key → path a negative scenario chooses
    replacements: dict[str, str] = field(default_factory=dict)   # form key → PDF that replaces the uploaded one
    scenario_label: str = ""
    expected_error: str = ""


class DeclarationFactory:

    @staticmethod
    def signed_forms() -> DeclarationData:
        """TC-495: a signed scan for each form, both under 2 MB."""
        return DeclarationData(files={"ia": VALID_CERTIFICATE, "ib": REPLACEMENT_PDF}, scenario_label="signed_forms")

    @staticmethod
    def single_form() -> DeclarationData:
        """TC-503: a signed scan for FORM-I(A) only."""
        return DeclarationData(files={"ia": VALID_CERTIFICATE}, scenario_label="single_form")

    @staticmethod
    def not_pdf() -> DeclarationData:
        """TC-501: a JPG for FORM-I(A) (chosen) and a PNG for FORM-I(B) (dropped)."""
        return DeclarationData(invalid_files={"ia": CERTIFICATE_JPG, "ib": CERTIFICATE_PNG},
                               scenario_label="not_pdf", expected_error=DeclarationPage.NOT_PDF_ERROR)

    @staticmethod
    def too_large() -> DeclarationData:
        """TC-502: a 3 MB PDF for FORM-I(A), then a valid one."""
        return DeclarationData(files={"ia": VALID_CERTIFICATE}, invalid_files={"ia": OVERSIZED_FILE},
                               scenario_label="too_large", expected_error=DeclarationPage.too_large_error(OVERSIZED_FILE))

    @staticmethod
    def replacement() -> DeclarationData:
        """KAN-TC-868: FORM-I(A), then a different PDF in its 'Replace' zone (a small PDF with other content, so
        'View ↗' can tell the two apart — certificate.pdf and certificate_v2.pdf are byte-identical)."""
        return DeclarationData(files={"ia": VALID_CERTIFICATE}, replacements={"ia": UNDERSIZED_FILE},
                               scenario_label="replacement")

    @staticmethod
    def jpg_as_pdf() -> DeclarationData:
        """KAN-TC-869: a JPG renamed to .pdf for FORM-I(A) — the browser accepts it, the server refuses it."""
        return DeclarationData(invalid_files={"ia": JPG_AS_PDF}, scenario_label="jpg_as_pdf",
                               expected_error=DeclarationPage.server_not_pdf_error("ia", JPG_AS_PDF))

    @staticmethod
    def empty_pdf() -> DeclarationData:
        """KAN-TC-870: a 0-byte PDF for FORM-I(B) — the browser accepts it, the server refuses it."""
        return DeclarationData(invalid_files={"ib": EMPTY_PDF}, scenario_label="empty_pdf")
