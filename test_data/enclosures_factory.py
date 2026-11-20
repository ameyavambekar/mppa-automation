"""
Data Factory — Step 5 (Documents / Enclosures)
==============================================
All test-data construction for the Documents step of the Form-I wizard (KAN-9).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-379 … KAN-TC-398, KAN-TC-471 … KAN-TC-474,
KAN-TC-851 and KAN-TC-864 … KAN-TC-865.

Documents are keyed by the number shown on the page (1–4 since portal 2.1.0); see
``EnclosuresPage.DOCUMENTS``. Since 20-Nov-2026 document 1 (PAN card) is already on file
from registration, so the scenarios upload document 2 to complete the step and use
document 3 when any one document will do.

Usage
-----
    from test_data.enclosures_factory import DocumentUploads, EnclosuresFactory

    data = EnclosuresFactory.address_proof_only()     # TC-380
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
    address_proof_other: Optional[str] = None                         # name typed for type "Other" (doctype_other3)
    invalid_other_names: list[str] = field(default_factory=list)      # "Other" names the page refuses
    expected_error: Optional[str] = None
    scenario_label: str = ""


class EnclosuresFactory:

    VALID_PDF = VALID_CERTIFICATE

    @staticmethod
    def all_mandatory() -> DocumentUploads:
        """Both mandatory documents (1 and 2) — used by the agency builder, which also works for agencies
        registered before the PAN card was carried over."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in EnclosuresPage.MANDATORY},
                               scenario_label="all_mandatory")

    @staticmethod
    def address_proof_only() -> DocumentUploads:
        """TC-380 / TC-381 / TC-382 / TC-395: document 2 (office address proof), the one mandatory document
        not carried over from registration."""
        return DocumentUploads(documents={2: VALID_CERTIFICATE},
                               address_proof_type=EnclosuresPage.ADDRESS_PROOF_TYPES[0],
                               scenario_label="address_proof_only")

    @staticmethod
    def optional_document() -> DocumentUploads:
        """TC-386 / TC-388 / TC-394 / TC-396: document 3 (Training Programme / Affiliation Certificate)."""
        return DocumentUploads(documents={3: VALID_CERTIFICATE}, scenario_label="optional_document")

    @staticmethod
    def replacement() -> DocumentUploads:
        """TC-387: a PDF with a different name replacing document 1, the PAN card from registration."""
        return DocumentUploads(replacement=REPLACEMENT_PDF, scenario_label="replacement")

    @staticmethod
    def optional_only() -> DocumentUploads:
        """TC-383: the optional documents (3 and 4 since portal 2.1.0)."""
        return DocumentUploads(documents={3: VALID_CERTIFICATE, 4: VALID_CERTIFICATE}, scenario_label="optional_only")

    @staticmethod
    def several_at_once() -> DocumentUploads:
        """TC-473: documents 2, 3 and 4 in one upload."""
        return DocumentUploads(documents={n: VALID_CERTIFICATE for n in (2, 3, 4)},
                               address_proof_type=EnclosuresPage.ADDRESS_PROOF_TYPES[0],
                               scenario_label="several_at_once")

    @staticmethod
    def address_proof() -> DocumentUploads:
        """KAN-TC-851: document 2 alone — first with no type chosen (refused), then as a rent / leave and
        licence agreement."""
        return DocumentUploads(documents={2: VALID_CERTIFICATE},
                               address_proof_type=EnclosuresPage.ADDRESS_PROOF_TYPES[1],
                               expected_error=EnclosuresPage.ADDRESS_PROOF_TYPE_REQUIRED,
                               scenario_label="address_proof")

    @staticmethod
    def address_proof_other() -> DocumentUploads:
        """KAN-TC-865: document 2 of type "Other" — refused with a blank and a two-letter name, then saved
        as "Water bill"."""
        return DocumentUploads(documents={2: VALID_CERTIFICATE},
                               address_proof_type=EnclosuresPage.ADDRESS_PROOF_OTHER,
                               address_proof_other="Water bill",
                               invalid_other_names=["", "WB"],
                               expected_error=EnclosuresPage.ADDRESS_PROOF_OTHER_NAME_REQUIRED,
                               scenario_label="address_proof_other")

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
