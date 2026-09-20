from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_government_issuance_pilot import audit_bnr_issuance_pilot

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class BNRGovernmentIssuancePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = load(
            "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
        )
        self.review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )
        self.contract = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.boundary = load(
            "model/dynamics/feedback_variable_boundary_registry.json"
        )
        self.reference_modes = load("model/dynamics/reference_modes.json")

    def audit(self, snapshot=None):
        return audit_bnr_issuance_pilot(
            snapshot or self.snapshot,
            self.review,
            self.contract,
            self.boundary,
            self.reference_modes,
        )

    def test_current_pilot_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_q1_and_q2_are_complete_but_q3_is_not(self) -> None:
        checks = self.snapshot["derived_checks"]
        self.assertTrue(checks["2025-Q1"]["complete_three_months"])
        self.assertTrue(checks["2025-Q2"]["complete_three_months"])
        self.assertFalse(checks["2025-Q3"]["complete_three_months"])
        self.assertEqual(checks["2025-Q3"]["observed_months"], ["2025-07"])

    def test_native_currency_separation_is_preserved(self) -> None:
        may = next(
            row for row in self.snapshot["monthly_observations"]
            if row["period"] == "2025-05"
        )
        self.assertEqual(
            may["total_RON_domestic_primary_market_securities_million_RON"],
            3934.6,
        )
        self.assertEqual(
            may["total_EUR_domestic_primary_market_securities_million_EUR"],
            1625.1,
        )
        self.assertFalse(
            self.snapshot["extraction"]["EUR_to_RON_conversion_performed"]
        )

    def test_exact_source_boundary_is_not_broader_government_borrowing(self) -> None:
        semantics = self.snapshot["semantics"]
        self.assertTrue(
            semantics["gross_issuance_equivalent_on_exact_source_boundary"]
        )
        self.assertFalse(semantics["total_government_borrowing_equivalent"])
        self.assertFalse(semantics["refinancing_need_equivalent"])
        self.assertFalse(semantics["supply_pressure_equivalent"])

    def test_promotion_is_blocked_without_raw_retention_and_revision_check(self) -> None:
        extraction = self.snapshot["extraction"]
        self.assertFalse(extraction["raw_pdf_retained_in_repository"])
        self.assertFalse(extraction["source_revision_check_performed"])
        self.assertTrue(
            extraction["promotion_blocked_by_raw_retention_and_revision_gate"]
        )
        self.assertFalse(
            self.snapshot["scientific_disposition"][
                "canonical_reference_mode_promoted"
            ]
        )

    def test_manual_q3_completion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.snapshot)
        mutated["derived_checks"]["2025-Q3"]["complete_three_months"] = True
        errors = self.audit(mutated)
        self.assertTrue(any("may not treat Q3 as complete" in e for e in errors))

    def test_manual_generic_node_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.snapshot)
        mutated["scientific_disposition"][
            "generic_government_debt_issuance_node_resolved"
        ] = True
        errors = self.audit(mutated)
        self.assertTrue(
            any("may not promote generic_government_debt_issuance_node_resolved" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
