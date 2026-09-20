from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_securities_supply_measurement_design import (
    REVIEW_PATH,
    audit_supply_measurement_design,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentSecuritiesSupplyMeasurementDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.denominator_review = load(
            "model/dynamics/government_securities_supply_load_denominator_boundary_review_2026_09_20.json"
        )
        self.ecb_assessment = load(
            "model/dynamics/government_securities_supply_load_ecb_denominator_probe_assessment_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_supply_measurement_design(
            overrides.get("review", self.review),
            overrides.get("source_review", self.source_review),
            overrides.get("denominator_review", self.denominator_review),
            overrides.get("ecb_assessment", self.ecb_assessment),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_measurement_design_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_ex_ante_and_post_auction_measures_are_separate(self) -> None:
        topology = self.review["structural_topology"]
        self.assertEqual(
            set(topology["ex_ante_supply_inputs"]),
            {
                "announced_RON_primary_supply_level",
                "announced_RON_supply_surprise",
                "announced_RON_duration_supply",
            },
        )
        self.assertEqual(
            set(topology["post_auction_outcome_diagnostics"]),
            {
                "primary_auction_absorption",
                "primary_auction_bid_to_cover",
            },
        )

    def test_announced_supply_requires_no_stock_denominator(self) -> None:
        item = next(
            x for x in self.review["measurement_vector"]
            if x["measure_id"] == "announced_RON_primary_supply_level"
        )
        self.assertFalse(item["normalisation_required"])
        self.assertFalse(item["stock_denominator_required"])

    def test_market_expectation_surprise_is_blocked(self) -> None:
        item = next(
            x for x in self.review["measurement_vector"]
            if x["measure_id"] == "announced_RON_supply_surprise"
        )
        self.assertEqual(
            item["current_source_status"],
            "BLOCKED_PREANNOUNCEMENT_EXPECTATION_SOURCE_NOT_FROZEN",
        )
        self.assertFalse(item["official_plan_revision_substitute_allowed"])

    def test_duration_supply_cannot_use_auction_yield(self) -> None:
        item = next(
            x for x in self.review["measurement_vector"]
            if x["measure_id"] == "announced_RON_duration_supply"
        )
        self.assertTrue(
            any(
                "auction clearing yield" in guard
                for guard in item["guards"]
            )
        )

    def test_no_scalar_composite_is_authorized(self) -> None:
        topology = self.review["structural_topology"]
        self.assertFalse(topology["scalar_composite_authorized"])
        self.assertFalse(topology["arbitrary_weighted_index_authorized"])
        self.assertFalse(
            self.review["scientific_effect"]["single_supply_pressure_scalar_selected"]
        )

    def test_manual_scalar_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["structural_topology"]["scalar_composite_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("scalar composite may not be authorized" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
