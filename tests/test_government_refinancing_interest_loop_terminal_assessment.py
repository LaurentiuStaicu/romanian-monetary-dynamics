from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_refinancing_interest_loop_terminal_assessment import (
    ASSESSMENT_PATH,
    HOLD_ID,
    STATUS,
    audit_government_refinancing_interest_loop_terminal_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentRefinancingInterestLoopTerminalAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
        self.repricing = load("model/calibration_validation/government_repricing_ledger_assessment.json")
        self.prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_government_refinancing_interest_loop_terminal_assessment(
            overrides.get("assessment", self.assessment),
            overrides.get("feedback", self.feedback),
            overrides.get("readiness", self.readiness),
            overrides.get("boundary", self.boundary),
            overrides.get("criteria", self.criteria),
            overrides.get("delays", self.delays),
            overrides.get("mechanisms", self.mechanisms),
            overrides.get("repricing", self.repricing),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_terminal_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_all_four_links_remain_not_equation_ready(self) -> None:
        rows = [
            x for x in self.readiness["links"]
            if x["loop_id"] == "government_refinancing_interest_loop"
        ]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(not x["exact_integrated_equation_ready"] for x in rows))

    def test_loop_is_on_evidence_triggered_hold(self) -> None:
        self.assertEqual(self.assessment["decision"], STATUS)
        self.assertEqual(
            self.assessment["disposition"]["current_operational_state"],
            "EVIDENCE_TRIGGERED_HOLD",
        )
        self.assertIsNone(self.assessment["disposition"]["active_empirical_task"])

    def test_hold_requires_genuinely_new_trigger(self) -> None:
        state = self.assessment["next_state"]
        self.assertEqual(state["id"], HOLD_ID)
        self.assertTrue(state["reopen_trigger_required"])
        self.assertFalse(state["may_poll_unchanged_sources"])

    def test_manual_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["disposition"]["feedback_activation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(any("feedback_activation_authorized" in e for e in errors))

    def test_scalar_delay_cannot_be_inferred(self) -> None:
        delay = next(
            x for x in self.delays["delays"]
            if x["id"] == "debt_service_maturity_delay"
        )
        self.assertEqual(delay["current_tau"], "TBD")
        self.assertFalse(delay["scalar_tau_activation_ready"])


if __name__ == "__main__":
    unittest.main()
