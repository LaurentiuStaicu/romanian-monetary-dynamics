from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_yield_to_interest_cost_boundary import (
    EFFECTIVE_RATE_PATH,
    INTEREST_BURDEN_PATH,
    PREREG_PATH,
    REPRICING_PATH,
    REVIEW_PATH,
    audit_yield_to_interest_cost_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class YieldToInterestCostBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.repricing = load(REPRICING_PATH)
        self.effective_rate = load(EFFECTIVE_RATE_PATH)
        self.interest_burden = load(INTEREST_BURDEN_PATH)
        self.reference_modes = load("model/dynamics/reference_modes.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_yield_to_interest_cost_boundary(
            overrides.get("review", self.review),
            overrides.get("repricing", self.repricing),
            overrides.get("effective_rate", self.effective_rate),
            overrides.get("interest_burden", self.interest_burden),
            overrides.get("reference_modes", self.reference_modes),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_three_observed_concepts_remain_distinct(self) -> None:
        comparison = self.review["boundary_comparison"]
        self.assertFalse(
            comparison["sovereign_yield_and_effective_portfolio_rate_same_concept"]
        )
        self.assertFalse(
            comparison["sovereign_yield_and_interest_expenditure_same_concept"]
        )
        self.assertFalse(
            comparison["effective_portfolio_rate_and_interest_expenditure_same_concept"]
        )

    def test_maturity_and_refixing_are_not_collapsed(self) -> None:
        structure = self.review["official_source_evidence"]["repricing_structure"]
        snapshot = structure["mof_risk_snapshot_2024_12_30"]
        self.assertEqual(snapshot["debt_maturing_within_1y_pct"], 10)
        self.assertEqual(snapshot["debt_refixing_within_1y_pct"], 12)
        self.assertEqual(snapshot["average_time_to_maturity_years"], 6.9)
        self.assertEqual(snapshot["average_time_to_refixing_years"], 6.7)
        self.assertTrue(
            self.review["propagation_architecture"][
                "maturity_and_refixing_may_not_be_collapsed"
            ]
        )

    def test_repricing_transition_remains_unidentified(self) -> None:
        self.assertEqual(self.repricing["final_verdict"], "DEFERRED")
        self.assertFalse(self.repricing["estimation"]["run"])
        self.assertFalse(
            self.review["bridge_resolution"]["synthetic_repricing_share_created"]
        )
        self.assertFalse(
            self.review["bridge_resolution"]["synthetic_lag_distribution_created"]
        )

    def test_current_10y_yield_cannot_price_full_debt_stock(self) -> None:
        self.assertTrue(
            self.review["hard_rules"][
                "no_current_10y_yield_times_full_debt_stock_as_interest_cost"
            ]
        )
        self.assertTrue(
            self.review["propagation_architecture"][
                "ten_year_yield_may_not_price_all_repricing_blocks"
            ]
        )

    def test_manual_direct_mapping_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["boundary_comparison"][
            "contemporaneous_one_to_one_mapping_supported"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("contemporaneous_one_to_one_mapping_supported" in e for e in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["issuance_yield_loop_effect"]["current_activation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("current_activation_authorized" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
