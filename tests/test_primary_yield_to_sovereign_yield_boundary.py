from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_primary_yield_to_sovereign_yield_boundary import (
    BNR_PATH,
    ECB_PATH,
    PREREG_PATH,
    REVIEW_PATH,
    audit_primary_yield_to_sovereign_yield_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PrimaryYieldToSovereignYieldBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.bnr = load(BNR_PATH)
        self.ecb = load(ECB_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_primary_yield_to_sovereign_yield_boundary(
            overrides.get("review", self.review),
            overrides.get("bnr", self.bnr),
            overrides.get("ecb", self.ecb),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_bnr_primary_rates_cannot_become_generic_sovereign_yield(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["official_source_evidence"]["bnr_primary_market"][
            "generic_sovereign_yield_equivalent"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("BNR primary rates may not become generic sovereign yield" in e for e in errors))

    def test_post_hoc_cross_instrument_average_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["boundary_comparison"]["post_hoc_cross_instrument_average_supported"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("post_hoc_cross_instrument_average_supported" in e for e in errors))

    def test_ecb_target_is_not_canonically_promoted_by_review(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["official_source_evidence"]["ecb_long_term_target"][
            "canonical_reference_mode_promoted_by_this_review"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("may not canonically promote ECB target" in e for e in errors))

    def test_supply_pressure_yield_link_cannot_activate(self) -> None:
        mutated = copy.deepcopy(self.readiness)
        link = next(
            item for item in mutated["links"]
            if item["loop_id"] == "government_issuance_yield_loop"
            and item["from"] == "government_securities_supply_pressure"
            and item["to"] == "sovereign_yield"
        )
        link["current_activation_authorized"] = True
        errors = self.audit(readiness=mutated)
        self.assertTrue(any("may not activate" in e for e in errors))

    def test_next_gate_is_yield_to_interest_cost_boundary_review(self) -> None:
        self.assertEqual(
            self.review["next_gate"]["id"],
            "yield_to_interest_cost_boundary_review",
        )
        self.assertFalse(self.review["next_gate"]["may_estimate_parameters"])
        self.assertFalse(self.review["next_gate"]["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
