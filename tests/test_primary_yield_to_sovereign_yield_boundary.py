from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_primary_yield_to_sovereign_yield_boundary import (
    REVIEW_PATH,
    audit_primary_yield_to_sovereign_yield_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PrimaryYieldToSovereignYieldBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")
        self.selection_result = load(
            "model/calibration_validation/sovereign_yield_structural_selection_result.json"
        )

    def audit(self, **overrides):
        return audit_primary_yield_to_sovereign_yield_boundary(
            overrides.get("review", self.review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("selection_result", self.selection_result),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_primary_rate_vector_is_not_generic_scalar(self) -> None:
        primary = self.review["primary_market_boundary"]
        self.assertFalse(primary["generic_scalar_aggregation_authorized"])
        self.assertEqual(
            primary["status"],
            "EXACT_RETAINED_2025_INSTRUMENT_AND_CURRENCY_SPECIFIC_PRIMARY_MARKET_RATES",
        )

    def test_exact_long_term_candidate_is_ten_year_ron(self) -> None:
        candidate = self.review["long_term_RON_boundary"]
        self.assertEqual(candidate["candidate_id"], "RON_10Y_long_term_sovereign_yield")
        self.assertEqual(candidate["series_key"], "IRS.M.RO.L.L40.CI.0000.RON.N.Z")
        self.assertEqual(candidate["maturity"], "10 years")
        self.assertEqual(candidate["currency"], "RON")
        self.assertFalse(candidate["generic_sovereign_yield_node_resolution_authorized"])

    def test_generic_node_remains_unresolved(self) -> None:
        disposition = self.review["umbrella_node_disposition"]
        self.assertEqual(disposition["current_boundary_class"], "UNRESOLVED")
        self.assertTrue(disposition["keep_generic_umbrella_node"])
        self.assertFalse(disposition["narrow_generic_node_to_10Y_now"])
        self.assertFalse(disposition["current_feedback_activation_authorized"])

    def test_failed_structural_selection_remains_failed_before_holdout(self) -> None:
        evidence = self.review["existing_structural_selection_evidence"]
        self.assertEqual(evidence["selection_verdict"], "FAIL_BEFORE_HOLDOUT")
        self.assertFalse(evidence["final_evaluation_opened"])
        self.assertFalse(evidence["causal_claim_allowed"])
        self.assertFalse(evidence["system_dynamics_activation"])

    def test_manual_generic_aggregation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["primary_market_boundary"]["generic_scalar_aggregation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("may not be aggregated generically" in e for e in errors))

    def test_manual_node_resolution_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["scientific_effect"]["generic_sovereign_yield_node_resolved"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("generic_sovereign_yield_node_resolved" in e for e in errors)
        )

    def test_next_bridge_is_yield_to_interest_cost_review_only(self) -> None:
        task = self.review["next_independent_bridge_task"]
        self.assertEqual(task["id"], "yield_to_interest_cost_boundary_review")
        self.assertEqual(task["authorization"], "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY")
        self.assertFalse(task["may_select_interest_cost_equation"])
        self.assertFalse(task["may_estimate_yield_to_cost_effect"])
        self.assertFalse(task["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
