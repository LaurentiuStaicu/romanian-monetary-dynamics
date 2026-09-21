from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_financing_channel_allocation_boundary import (
    REVIEW_PATH,
    audit_financing_channel_allocation_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FinancingChannelAllocationBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.bnr = load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json")
        self.source_review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_financing_channel_allocation_boundary(
            overrides.get("review", self.review),
            overrides.get("bnr", self.bnr),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_deficit_45_55_split_may_not_be_used_for_total_gfn(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["boundary_comparison"][
            "deficit_45_55_split_is_full_GFN_allocation"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("deficit_45_55_split_is_full_GFN_allocation" in e for e in errors)
        )

    def test_bnr_channel_may_not_equal_total_financing_need(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["allocation_bridge_resolution"]["one_to_one_mapping_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("one_to_one_mapping_authorized" in e for e in errors))

    def test_residual_channel_inference_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["allocation_bridge_resolution"]["residual_allocation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("residual_allocation_authorized" in e for e in errors))

    def test_synthetic_channel_shares_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["allocation_bridge_resolution"]["synthetic_channel_shares_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("synthetic_channel_shares_authorized" in e for e in errors))

    def test_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.feedback)
        loop = next(
            item for item in mutated["loops"]
            if item["id"] == "government_issuance_yield_loop"
        )
        loop["quantitatively_active"] = True
        errors = self.audit(feedback=mutated)
        self.assertTrue(any("may not activate loop" in e for e in errors))

    def test_next_gate_is_descriptive_source_contract_only(self) -> None:
        gate = self.review["next_gate"]
        self.assertEqual(
            gate["id"],
            "mof_realized_financing_channel_materialisation_contract",
        )
        self.assertEqual(gate["authorization"], "DESCRIPTIVE_SOURCE_CONTRACT_ONLY")
        self.assertFalse(gate["may_difference_cumulative_values_now"])
        self.assertFalse(gate["may_infer_channel_residuals"])
        self.assertFalse(gate["may_estimate_allocation_shares"])
        self.assertFalse(gate["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
