"""
Data Factory — Application Preview
==================================
All test-data construction for the Preview step (KAN-39).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-504 … KAN-TC-516.

Preview itself takes no input; the factory holds what the page is expected to
show for a given kind of agency.

Usage
-----
    from test_data.preview_factory import PreviewData, PreviewFactory

    data = PreviewFactory.within_maharashtra()      # TC-512
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreviewData:
    fee_amount: int = 0           # rupees, as posted in #payForm's fee_amount
    fee_category: str = ""        # the line under the amount in the fee box
    # Scenario-specific values
    scenario_label: str = ""
    expected_error: str = ""


class PreviewFactory:

    @staticmethod
    def within_maharashtra() -> PreviewData:
        """TC-512: an agency that operates only within Maharashtra (every agency the builder makes)."""
        return PreviewData(
            fee_amount=2000,
            fee_category=("Within Maharashtra — Operates only within the State of Maharashtra · Rule 3(3)(d) · "
                          "one-time, non-refundable"),
            scenario_label="within_maharashtra",
        )
