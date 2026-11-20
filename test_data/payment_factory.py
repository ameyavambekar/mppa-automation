"""
Data Factory — Payment
======================
All test-data construction for the Payment step (KAN-11).
Each factory method maps to one Acceptance Criterion, Edge Case, or scenario
referenced in the AIO test cases KAN-TC-873 … KAN-TC-887.

Payment takes no input on dev (no gateway); the factory holds the fee charged for
each Part C area of placement operations (Rule 3(3)(d)), as the receipt and the
submitted application show it.

Usage
-----
    from test_data.payment_factory import PaymentData, PaymentFactory

    data = PaymentFactory.for_area("Within Maharashtra")    # TC-874
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaymentData:
    area: str = ""                # Part C "Area of Placement Operations"
    fee_amount: int = 0           # rupees
    # Scenario-specific values
    scenario_label: str = ""
    expected_error: str = ""

    @property
    def amount_text(self) -> str:
        """'₹ 2,000.00' — as the receipt and View my application print it."""
        return f"₹ {self.fee_amount:,.2f}"


class PaymentFactory:

    @staticmethod
    def within_maharashtra() -> PaymentData:
        """TC-874: an agency operating only within Maharashtra."""
        return PaymentData(area="Within Maharashtra", fee_amount=2000, scenario_label="within_maharashtra")

    @staticmethod
    def across_india() -> PaymentData:
        """TC-874: an agency with its office or operations outside Maharashtra."""
        return PaymentData(area="Across India", fee_amount=4000, scenario_label="across_india")

    @staticmethod
    def india_and_overseas() -> PaymentData:
        """TC-874: an agency placing job seekers overseas."""
        return PaymentData(area="India and Overseas", fee_amount=10000, scenario_label="india_and_overseas")

    @classmethod
    def for_area(cls, area: str) -> PaymentData:
        """The fee for the Part C area ``area`` as the submitted application shows it."""
        for data in (cls.within_maharashtra(), cls.across_india(), cls.india_and_overseas()):
            if data.area == area:
                return data
        raise ValueError(f"no fee known for the Part C area {area!r}")
