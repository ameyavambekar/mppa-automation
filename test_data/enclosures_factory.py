"""
Data Factory — Step 5 (Documents / Enclosures)
==============================================
All test-data construction for the Documents step of the Form-I wizard (KAN-9).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-379 … KAN-TC-398 and
KAN-TC-471 … KAN-TC-474.

Documents are keyed by the number shown on the page (1–8); see
``EnclosuresPage.DOCUMENTS``.

Usage
-----
    from test_data.enclosures_factory import DocumentUploads, EnclosuresFactory

    data = EnclosuresFactory.all_mandatory()     # TC-380
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.file_manager import (CERTIFICATE_JPG, CERTIFICATE_PNG, EMPTY_PDF, OVERSIZED_FILE, REPLACEMENT_PDF,
                                UNDERSIZED_FILE, UNSUPPORTED_CERTIFICATE, VALID_CERTIFICATE)


@dataclass
class DocumentUploads:
    documents: dict[int, str] = field(default_factory=dict)          # number → file path to upload
    # Scenario-specific values
    invalid_files: list[tuple[int, str]] = field(default_factory=list)  # (number, path) a negative scenario chooses
    replacement: Optional[str] = None
    expected_error: Optional[str] = None
    scenario_label: str = ""


class EnclosuresFactory:

    VALID_PDF = VALID_CERTIFICATE

    @staticmethod
    def all_mandatory() -> DocumentUploads:
        """TC-380 / TC-395: documents 1–6."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in range(1, 7)}, scenario_label="all_mandatory")

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
        """TC-383: optional documents 7 and 8."""
        return DocumentUploads(documents={7: VALID_CERTIFICATE, 8: VALID_CERTIFICATE}, scenario_label="optional_only")

    @staticmethod
    def first_three() -> DocumentUploads:
        """TC-396: documents 1–3."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in (1, 2, 3)}, scenario_label="first_three")

    @staticmethod
    def several_at_once() -> DocumentUploads:
        """TC-473: documents 1, 2 and 7 in one upload."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in (1, 2, 7)}, scenario_label="several_at_once")

    # ── Rejected files ────────────────────────────────────────────────────────

    @staticmethod
    def not_pdf() -> DocumentUploads:
        """TC-384: a JPG, a PNG and a DOCX."""
        return DocumentUploads(invalid_files=[(3, CERTIFICATE_JPG), (1, CERTIFICATE_PNG), (8, UNSUPPORTED_CERTIFICATE)],
                               scenario_label="not_pdf")

    @staticmethod
    def too_large() -> DocumentUploads:
        """TC-385: a 3 MB PDF."""
        return DocumentUploads(invalid_files=[(2, OVERSIZED_FILE)], scenario_label="too_large")

    @staticmethod
    def too_small() -> DocumentUploads:
        """TC-397: a 298-byte PDF, then a 0-byte one."""
        return DocumentUploads(invalid_files=[(5, UNDERSIZED_FILE), (5, EMPTY_PDF)], scenario_label="too_small")
