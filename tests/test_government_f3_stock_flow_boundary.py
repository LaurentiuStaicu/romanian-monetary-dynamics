from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_f3_stock_flow_boundary import (
    audit_government_f3_stock_flow_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentF3StockFlowBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(
            "model/dynamics/government_f3_stock_flow_boundary_review.json"
        )
        self.contract = load(
            "model/dynamics/government_f3_csec_materialisation_contract.json"
        )
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.boundary = load(
            "model/dynamics/feedback_variable_boundary_registry.json"
        )
        self.links = load(
            "model/dynamics/feedback_link_readiness_registry.json"
        )
        self.reference_modes = load("model/dynamics/reference_modes.json")
        self.issuance_review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )

    def audit(self, review=None, contract=None, boundary=None, links=None):
        return audit_government_f3_stock_flow_boundary(
            review or self.review,
            contract or self.contract,
            self.feedback,
            boundary or self.boundary,
            links or self.links,
            self.reference_modes,
            self.issuance_review,
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_gross_issuance_is_not_a_complete_stock_update(self) -> None:
        identity = self.review["stock_flow_identity"]
        self.assertIn("gross_issues[t] - redemptions[t]", identity["exact_csec_form"])
        self.assertIn("revaluations[t]", identity["exact_csec_form"])
        self.assertIn("other_changes_in_volume[t]", identity["exact_csec_form"])

    def test_csec_f3_is_not_maastricht_debt(self) -> None:
        comparison = self.review["boundary_comparison"]
        self.assertFalse(comparison["exact_equivalence"])
        self.assertTrue(comparison["bridge_required"])
        self.assertEqual(
            comparison["csec_S13_F3_stock"]["instrument_scope"],
            "F3 debt securities only",
        )
        self.assertEqual(
            comparison["maastricht_government_debt_reference"]["instrument_scope"],
            "AF2 + AF3 + AF4 Maastricht debt",
        )

    def test_common_six_component_boundary_is_not_claimed_materialised(self) -> None:
        state = self.contract["current_state"]
        self.assertTrue(state["source_family_discovered"])
        self.assertFalse(state["exact_common_six_component_boundary_materialised"])
        self.assertFalse(state["source_vintage_retained"])
        self.assertFalse(state["structural_refinement_authorized"])

    def test_current_topology_remains_unchanged_and_inactive(self) -> None:
        decision = self.review["scientific_decision"]
        self.assertFalse(decision["current_feedback_topology_changed"])
        self.assertFalse(decision["exact_issuance_to_stock_equation_admitted"])
        self.assertFalse(decision["feedback_activation_authorized"])

    def test_manual_exact_link_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.links)
        link = next(
            item for item in mutated["links"]
            if item["link_key"]
            == (
                "government_refinancing_interest_loop|"
                "government_debt_issuance|government_debt_stock"
            )
        )
        link["exact_integrated_equation_ready"] = True
        errors = self.audit(links=mutated)
        self.assertTrue(
            any("exact integrated link must remain blocked" in error for error in errors)
        )

    def test_removing_redemptions_from_materialisation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["required_components"].remove("redemptions")
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("component set changed" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
