from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_securities_supply_pressure_source_boundary import (
    REVIEW_PATH,
    audit_supply_pressure_source_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentSecuritiesSupplyPressureSourceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_supply_pressure_source_boundary(
            overrides.get("review", self.review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_source_boundary_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_candidate_boundary_is_multidimensional(self) -> None:
        ids = {
            item["candidate_id"]
            for item in self.review["candidate_observable_vector"]
        }
        self.assertEqual(
            ids,
            {
                "domestic_RON_primary_market_supply_load",
                "domestic_RON_primary_market_auction_absorption",
                "domestic_RON_primary_market_bid_to_cover",
                "domestic_government_securities_secondary_market_liquidity",
            },
        )
        self.assertFalse(
            self.review["scientific_effect"]["scalar_pressure_index_selected"]
        )

    def test_announced_amount_is_preserved_as_ex_ante_supply_candidate(self) -> None:
        item = next(
            x for x in self.review["candidate_observable_vector"]
            if x["candidate_id"] == "domestic_RON_primary_market_supply_load"
        )
        self.assertEqual(item["role"], "EX_ANTE_SUPPLY_LOAD_CANDIDATE")
        self.assertIn("monthly_announced_RON_amount", item["provisional_formula"])
        self.assertIn("lagged_month_end_outstanding", item["provisional_formula"])

    def test_accepted_amount_is_not_pure_ex_ante_supply(self) -> None:
        self.assertEqual(
            self.review["auction_rule_evidence"]["structural_implication"],
            "accepted_amount_is_an_auction_outcome_and_may_not_be_treated_as_pure_ex_ante_supply",
        )

    def test_no_chart_digitisation_or_ocr_is_authorized(self) -> None:
        gate = self.review["materialisation_gate"]
        self.assertFalse(gate["visual_chart_digitisation_authorized"])
        self.assertFalse(gate["ocr_authorized"])
        self.assertFalse(gate["manual_approximation_authorized"])

    def test_manual_scalar_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["scientific_effect"]["scalar_pressure_index_selected"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("scalar_pressure_index_selected" in error for error in errors)
        )

    def test_manual_node_resolution_is_detected(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        node = next(
            item for item in mutated["variables"]
            if item["id"] == "government_securities_supply_pressure"
        )
        node["current_boundary_class"] = "OBSERVED_FORCING"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("boundary registry supply-pressure node resolved" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.feedback)
        loop = next(
            item for item in mutated["loops"]
            if item["id"] == "government_issuance_yield_loop"
        )
        loop["quantitatively_active"] = True
        errors = self.audit(feedback=mutated)
        self.assertTrue(
            any("may not activate loop" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
