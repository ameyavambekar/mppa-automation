"""
Data Factory — Step 5 (Documents / Enclosures)
==============================================
All test-data construction for the Documents step of the Form-I wizard (KAN-9).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-379 … KAN-TC-398 and
KAN-TC-471 … KAN-TC-474.

Documents are keyed by the number shown on the page (1–4 since portal 2.1.0); see
``EnclosuresPage.DOCUMENTS``.

Usage
-----
    from test_data.enclosures_factory import DocumentUploads, EnclosuresFactory

    data = EnclosuresFactory.all_mandatory()     # TC-380
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pages.enclosures_page import EnclosuresPage
from utils.file_manager import (CERTIFICATE_JPG, CERTIFICATE_PNG, EMPTY_PDF, OVERSIZED_FILE, REPLACEMENT_PDF,
                                UNDERSIZED_FILE, UNSUPPORTED_CERTIFICATE, VALID_CERTIFICATE)


@dataclass
class DocumentUploads:
    documents: dict[int, str] = field(default_factory=dict)          # number → file path to upload
    # Scenario-specific values
    invalid_files: list[tuple[int, str]] = field(default_factory=list)  # (number, path) a negative scenario chooses
    replacement: Optional[str] = None
    address_proof_type: Optional[str] = None                          # type chosen for document 2 (doctype3)
    expected_error: Optional[str] = None
    scenario_label: str = ""


class EnclosuresFactory:

    VALID_PDF = VALID_CERTIFICATE

    @staticmethod
    def all_mandatory() -> DocumentUploads:
        """TC-380 / TC-395: the mandatory documents (1 and 2 since portal 2.1.0)."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in EnclosuresPage.MANDATORY},
                               scenario_label="all_mandatory")

    @staticmethod
    def first_document() -> DocumentUploads:
        """TC-381 / TC-386 / TC-388 / TC-394: document 1 (PAN Card of the Agency)."""
        return DocumentUploads(documents={1: VALID_CERTIFICATE}, scenario_label="first_document")

    @staticmethod
    def replacement() -> DocumentUploads:
        """TC-387: document 1, then a PDF with a different name."""
        return DocumentUploads(documents={1: VALID_CERTIFICATE}, replacement=REPLACEMENT_PDF,
                               scenario_label="replacement")

    @staticmethod
    def optional_only() -> DocumentUploads:
        """TC-383: the optional documents (3 and 4 since portal 2.1.0)."""
        return DocumentUploads(documents={3: VALID_CERTIFICATE, 4: VALID_CERTIFICATE}, scenario_label="optional_only")

    @staticmethod
    def partial() -> DocumentUploads:
        """TC-396: one mandatory (1) and one optional (3) document, leaving 2 and 4 empty."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in (1, 3)}, scenario_label="partial")

    @staticmethod
    def several_at_once() -> DocumentUploads:
        """TC-473: documents 1, 2 and 4 in one upload."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in (1, 2, 4)}, scenario_label="several_at_once")

    @staticmethod
    def address_proof() -> DocumentUploads:
        """KAN-TC-851: document 2 alone — first with no type chosen (refused), then as a rent / leave and
        licence agreement."""
        return DocumentUploads(documents={2: VALID_CERTIFICATE},
                               address_proof_type=EnclosuresPage.ADDRESS_PROOF_TYPES[1],
                               expected_error=EnclosuresPage.ADDRESS_PROOF_TYPE_REQUIRED,
                               scenario_label="address_proof")

    # ── Rejected files ────────────────────────────────────────────────────────

    @staticmethod
    def not_pdf() -> DocumentUploads:
        """TC-384: a JPG, a PNG and a DOCX."""
        return DocumentUploads(invalid_files=[(3, CERTIFICATE_JPG), (1, CERTIFICATE_PNG), (4, UNSUPPORTED_CERTIFICATE)],
                               scenario_label="not_pdf")

    @staticmethod
    def too_large() -> DocumentUploads:
        """TC-385: a 3 MB PDF."""
        return DocumentUploads(invalid_files=[(2, OVERSIZED_FILE)], scenario_label="too_large")

    @staticmethod
    def too_small() -> DocumentUploads:
        """TC-397: a 298-byte PDF, then a 0-byte one."""
        return DocumentUploads(invalid_files=[(4, UNDERSIZED_FILE), (4, EMPTY_PDF)], scenario_label="too_small")
