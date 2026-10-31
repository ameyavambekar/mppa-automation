"""
Data Factory — Premises Photos
==============================
All test-data construction for the Premises Photos step (KAN-38).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-475 … KAN-TC-489 (488: OUTSIDE_LOCATION).

Photos are keyed by the card's ``data-key`` (see ``PremisesPage.PHOTOS``).
The browser's location is set to ``PremisesFactory.LOCATION`` (Pune), or to
``OUTSIDE_LOCATION`` for the outside-Maharashtra check.

Usage
-----
    from test_data.premises_factory import PremisesData, PremisesFactory

    data = PremisesFactory.required_only()      # TC-481
"""

from __future__ import annotations

from dataclasses import dataclass, field

from utils.file_manager import CERTIFICATE_JPG, CERTIFICATE_PNG, UNSUPPORTED_PHOTO, VALID_CERTIFICATE


@dataclass
class PremisesData:
    photos: dict[str, str] = field(default_factory=dict)       # card key → photo path
    answers: dict[str, bool] = field(default_factory=dict)     # conditional card key → Yes / No
    # Scenario-specific values
    invalid_files: list[str] = field(default_factory=list)     # paths a negative scenario chooses
    scenario_label: str = ""


class PremisesFactory:

    LOCATION = (18.5204, 73.8567)     # Pune, Maharashtra
    OUTSIDE_LOCATION = (-31.9502, 115.8609)   # Perth, Australia — TC-488
    PHOTO_JPG = CERTIFICATE_JPG
    PHOTO_PNG = CERTIFICATE_PNG

    @staticmethod
    def required_only() -> PremisesData:
        """TC-481: the three required photos, both conditional questions answered No."""
        return PremisesData(
            photos={"signboard": CERTIFICATE_JPG, "exterior": CERTIFICATE_JPG, "interior": CERTIFICATE_PNG},
            answers={"classroom": False, "working_area": False},
            scenario_label="required_only",
        )

    @staticmethod
    def jpg_and_png() -> PremisesData:
        """TC-478: a JPG for the outside view, a PNG for the inside view."""
        return PremisesData(photos={"exterior": CERTIFICATE_JPG, "interior": CERTIFICATE_PNG}, scenario_label="jpg_and_png")

    @staticmethod
    def not_images() -> PremisesData:
        """TC-486: a PDF, then a HEIC photo."""
        return PremisesData(invalid_files=[VALID_CERTIFICATE, UNSUPPORTED_PHOTO], scenario_label="not_images")
