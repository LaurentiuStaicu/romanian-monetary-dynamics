from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_debt_issuance_source_boundary import (
    audit_government_debt_issuance_source_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentDebtIssuanceSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )
        self.contract = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.boundary = load(
            "model/dynamics/feedback_variable_boundary_registry.json"
        )
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.reference_modes = load("model/dynamics/reference_modes.json")
        self.sovereign = load(
            "model/calibration_validation/sovereign_yield_source_boundary_review.json"
        )

    def audit(self, review=None, contract=None, boundary=None):
        return audit_government_debt_issuance_source_boundary(
            review or self.review,
            contract or self.contract,
            boundary or self.boundary,
            self.feedback,
            self.reference_modes,
            self.sovereign,
        )

    def test_current_source_boundary_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_generic_node_remains_unresolved(self) -> None:
        node = next(
            item
            for item in self.boundary["variables"]
            if item["id"] == "government_debt_issuance"
        )
        self.assertEqual(node["current_boundary_class"], "UNRESOLVED")
        self.assertTrue(node["semantic_overload_detected"])
        self.assertFalse(node["current_feedback_activation_authorized"])

    def test_bnr_and_ministry_paths_are_not_collapsed(self) -> None:
        self.assertTrue(
            self.contract["cross_source_rule"]["sources_are_expected_to_differ"]
        )
        self.assertTrue(
            self.contract["cross_source_rule"][
                "equality_is_not_a_validation_requirement"
            ]
        )
        self.assertEqual(len(self.contract["paths"]), 2)

    def test_qsa_net_incurrence_is_not_gross_issuance(self) -> None:
        self.assertFalse(
            self.review["semantic_comparison"]["qsa_f3_net_incurrence"][
                "gross_issuance_equivalent"
            ]
        )

    def test_ministry_cumulative_values_cannot_be_differenced_blindly(self) -> None:
        rules = self.contract["paths"]["mof_actual_borrowing"]
        prohibited = " ".join(rules["prohibited_shortcuts"])
        self.assertIn("changed FX conversion conventions", prohibited)
        self.assertIn("Retain the cumulative year-to-date values exactly", rules["materialisation_rule"])

    def test_bnr_domestic_series_is_not_full_government_borrowing(self) -> None:
        item = self.review["semantic_comparison"][
            "bnr_domestic_primary_market_issue_volume"
        ]
        self.assertTrue(
            item["gross_issuance_equivalent_on_exact_domestic_primary_market_boundary"]
        )
        self.assertFalse(item["full_government_borrowing_equivalent"])

    def test_manual_boundary_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        node = next(
            item
            for item in mutated["variables"]
            if item["id"] == "government_debt_issuance"
        )
        node["current_boundary_class"] = "EXOGENOUS"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("must remain UNRESOLVED" in error for error in errors)
        )

    def test_cross_source_equality_gate_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["cross_source_rule"]["equality_is_not_a_validation_requirement"] = False
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("equality may not become a validation gate" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
