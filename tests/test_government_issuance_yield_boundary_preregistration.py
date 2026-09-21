from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_issuance_yield_boundary_preregistration import (
    PREREG_PATH,
    audit_government_issuance_yield_boundary_preregistration,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentIssuanceYieldBoundaryPreregistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prereg = load(PREREG_PATH)
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.materialisation = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.source_review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )
        self.sovereign = load(
            "model/calibration_validation/sovereign_yield_source_boundary_review.json"
        )

    def audit(self, **overrides):
        return audit_government_issuance_yield_boundary_preregistration(
            overrides.get("prereg", self.prereg),
            overrides.get("feedback", self.feedback),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("materialisation", self.materialisation),
            overrides.get("source_review", self.source_review),
            overrides.get("sovereign", self.sovereign),
        )

    def test_current_preregistration_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_conceptual_loop_and_empirical_boundary_are_distinguished(self) -> None:
        self.assertEqual(
            self.prereg["conceptual_topology"]["current_status"],
            "CLOSED_CANDIDATE_LOOP",
        )
        self.assertEqual(
            self.prereg["empirical_boundary_status"]["status"],
            "OPEN_CHAIN_PENDING_EXPLICIT_BRIDGES",
        )
        self.assertFalse(
            self.prereg["scientific_effect"]["conceptual_loop_topology_changed"]
        )

    def test_five_bridges_are_required_before_empirical_closure(self) -> None:
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

    def test_generic_node_remains_unresolved(self) -> None:
        generic = next(
            item for item in self.boundary["variables"]
            if item["id"] == "government_debt_issuance"
        )
        self.assertEqual(generic["current_boundary_class"], "UNRESOLVED")
        self.assertFalse(
            generic[
                "bnr_domestic_primary_market_boundary_can_replace_generic_node_in_both_government_loops"
            ]
        )
        self.assertFalse(generic["current_feedback_activation_authorized"])

    def test_manual_closed_loop_narrowing_authorization_is_detected(self) -> None:
        mutated = copy.deepcopy(self.feedback)
        loop = next(
            item for item in mutated["loops"]
            if item["id"] == "government_issuance_yield_loop"
        )
        loop["bnr_domestic_primary_market_narrowing_as_closed_loop_authorized"] = True
        errors = self.audit(feedback=mutated)
        self.assertTrue(
            any("incorrectly authorizes closed-loop BNR narrowing" in e for e in errors)
        )

    def test_manual_generic_node_resolution_is_detected(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        generic = next(
            item for item in mutated["variables"]
            if item["id"] == "government_debt_issuance"
        )
        generic["current_boundary_class"] = "OBSERVED_FORCING"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("generic government_debt_issuance boundary was resolved" in e for e in errors)
        )

    def test_descriptive_yield_pilot_cannot_activate_feedback(self) -> None:
        mutated = copy.deepcopy(self.prereg)
        mutated["next_empirical_task"]["may_activate_feedback"] = True
        errors = self.audit(prereg=mutated)
        self.assertTrue(
            any("descriptive yield pilot may not activate feedback" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
