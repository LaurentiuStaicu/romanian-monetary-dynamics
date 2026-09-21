from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_yield_to_interest_cost_boundary import (
    REVIEW_PATH,
    EFFECTIVE_ASSESSMENT_PATH,
    BURDEN_ASSESSMENT_PATH,
    REPRICING_ASSESSMENT_PATH,
    PREREG_PATH,
    audit_yield_to_interest_cost_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class YieldToInterestCostBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.effective = load(EFFECTIVE_ASSESSMENT_PATH)
        self.burden = load(BURDEN_ASSESSMENT_PATH)
        self.repricing = load(REPRICING_ASSESSMENT_PATH)
        self.mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_yield_to_interest_cost_boundary(
            overrides.get("review", self.review),
            overrides.get("effective", self.effective),
            overrides.get("burden", self.burden),
            overrides.get("repricing", self.repricing),
            overrides.get("mechanisms", self.mechanisms),
            overrides.get("delays", self.delays),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_sovereign_yield_cannot_equal_effective_portfolio_cost(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["official_source_evidence"]["sovereign_yield_target"][
            "direct_effective_portfolio_cost_equivalent"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("ECB 10-year yield may not equal portfolio effective cost" in e for e in errors)
        )

    def test_ecb_10y_cannot_substitute_for_matched_repricing_rate(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["propagation_architecture"][
            "ecb_10y_may_substitute_for_matched_new_or_reset_rate"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("ecb_10y_may_substitute_for_matched_new_or_reset_rate" in e for e in errors)
        )

    def test_maturity_share_cannot_be_repricing_share(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["propagation_architecture"][
            "maturity_share_may_substitute_for_refixing_share"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("maturity_share_may_substitute_for_refixing_share" in e for e in errors)
        )

    def test_interest_cost_node_remains_unresolved(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        node = next(
            item for item in mutated["variables"]
            if item["id"] == "government_interest_cost"
        )
        node["current_boundary_class"] = "OBSERVED"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("registry node may not be resolved" in e for e in errors)
        )

    def test_repricing_parameter_remains_unidentified(self) -> None:
        mutated = copy.deepcopy(self.mechanisms)
        mechanism = next(
            item for item in mutated["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )
        mechanism["parameters"][0]["status"] = "ESTIMATED"
        errors = self.audit(mechanisms=mutated)
        self.assertTrue(
            any("repricing-share parameter status changed" in e for e in errors)
        )

    def test_delay_tau_remains_tbd(self) -> None:
        mutated = copy.deepcopy(self.delays)
        delay = next(
            item for item in mutated["delays"]
            if item["id"] == "debt_service_maturity_delay"
        )
        delay["current_tau"] = 4.0
        errors = self.audit(delays=mutated)
        self.assertTrue(
            any("registered debt-service delay activation changed" in e for e in errors)
        )

    def test_next_gate_is_interest_cost_to_financing_need(self) -> None:
        self.assertEqual(
            self.review["next_gate"]["id"],
            "interest_cost_to_financing_need_boundary_review",
        )
        self.assertFalse(self.review["next_gate"]["may_estimate_parameters"])
        self.assertFalse(self.review["next_gate"]["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
