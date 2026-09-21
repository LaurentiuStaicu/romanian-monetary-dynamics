from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_interest_cost_to_financing_need_boundary import (
    REVIEW_PATH,
    BURDEN_PATH,
    REFINANCING_PATH,
    FISCAL_BOUNDARY_PATH,
    PREREG_PATH,
    audit_interest_cost_to_financing_need_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class InterestCostToFinancingNeedBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.burden = load(BURDEN_PATH)
        self.refinancing = load(REFINANCING_PATH)
        self.fiscal_boundary = load(FISCAL_BOUNDARY_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_interest_cost_to_financing_need_boundary(
            overrides.get("review", self.review),
            overrides.get("burden", self.burden),
            overrides.get("refinancing", self.refinancing),
            overrides.get("fiscal_boundary", self.fiscal_boundary),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_d41_cannot_be_relabelled_cash_financing_requirement(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["official_source_evidence"]["eurostat_accrual_interest"][
            "direct_cash_financing_requirement_equivalent"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("D41 may not be treated as direct cash financing requirement" in e for e in errors)
        )

    def test_refinancing_need_cannot_be_relabelled_gfn(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["official_source_evidence"]["mof_refinancing_component"][
            "gross_financing_need_equivalent"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("MoF refinancing need may not equal GFN" in e for e in errors))

    def test_cross_boundary_sum_remains_blocked(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["accounting_boundary"]["cross_boundary_sum_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("cross_boundary_sum_authorized" in e for e in errors))

    def test_financing_need_node_remains_unresolved(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        node = next(
            item for item in mutated["variables"]
            if item["id"] == "government_financing_need"
        )
        node["current_boundary_class"] = "ENDOGENOUS"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("registry node may not be resolved" in e for e in errors)
        )

    def test_fifth_empirical_bridge_is_required(self) -> None:
        ids = {
            item["id"]
            for item in self.prereg[
                "required_bridges_before_any_closed_empirical_loop_claim"
            ]
        }
        self.assertEqual(
            ids,
            {
                "financing_channel_allocation",
                "issuance_to_supply_pressure",
                "primary_yield_to_sovereign_yield",
                "yield_to_interest_cost",
                "interest_cost_to_financing_need",
            },
        )

    def test_link_cannot_activate_in_either_loop(self) -> None:
        mutated = copy.deepcopy(self.readiness)
        links = [
            item for item in mutated["links"]
            if item["from"] == "government_interest_cost"
            and item["to"] == "government_financing_need"
        ]
        links[0]["current_activation_authorized"] = True
        errors = self.audit(readiness=mutated)
        self.assertTrue(any("link may not activate" in e for e in errors))

    def test_next_gate_is_financing_channel_allocation(self) -> None:
        self.assertEqual(
            self.review["next_gate"]["id"],
            "financing_channel_allocation_boundary_review",
        )
        self.assertFalse(
            self.review["next_gate"][
                "may_construct_one_to_one_financing_need_to_bnr_issuance_mapping"
            ]
        )
        self.assertFalse(self.review["next_gate"]["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
