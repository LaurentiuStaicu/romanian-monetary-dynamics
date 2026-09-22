from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_issuance_yield_loop_terminal_assessment import (
    ASSESSMENT_PATH,
    STATUS,
    audit_government_issuance_yield_loop_terminal_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentIssuanceYieldLoopTerminalAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
        self.selection = load("model/calibration_validation/sovereign_yield_structural_selection_result.json")
        self.missing_sources = load("model/dynamics/mof_announced_RON_primary_reference_auction_missing_source_recovery_assessment_2026_09_20.json")
        self.prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_government_issuance_yield_loop_terminal_assessment(
            overrides.get("assessment", self.assessment),
            overrides.get("feedback", self.feedback),
            overrides.get("readiness", self.readiness),
            overrides.get("boundary", self.boundary),
            overrides.get("criteria", self.criteria),
            overrides.get("delays", self.delays),
            overrides.get("mechanisms", self.mechanisms),
            overrides.get("selection", self.selection),
            overrides.get("missing_sources", self.missing_sources),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_terminal_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_all_five_links_remain_not_equation_ready(self) -> None:
        rows = [
            x for x in self.readiness["links"]
            if x["loop_id"] == "government_issuance_yield_loop"
        ]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(not x["exact_integrated_equation_ready"] for x in rows))

    def test_loop_is_on_evidence_triggered_hold(self) -> None:
        self.assertEqual(self.assessment["decision"], STATUS)
        self.assertEqual(
            self.assessment["disposition"]["current_operational_state"],
            "EVIDENCE_TRIGGERED_HOLD",
        )
        self.assertIsNone(self.assessment["disposition"]["active_empirical_task"])

    def test_model_contract_next_task_pointer_is_terminal_hold(self) -> None:
        dynamic = self.model_contract["dynamic_core"]
        self.assertEqual(
            dynamic["next_government_issuance_yield_empirical_task"],
            "government_issuance_yield_loop_evidence_triggered_hold",
        )
        self.assertIsNone(dynamic["government_issuance_yield_loop_active_empirical_task"])

    def test_failed_yield_form_remains_frozen_before_holdout(self) -> None:
        state = self.assessment["behavioural_link_state"]
        self.assertEqual(state["selection_verdict"], "FAIL_BEFORE_HOLDOUT")
        self.assertFalse(state["final_evaluation_opened"])
        self.assertFalse(state["system_dynamics_activation"])

    def test_missing_supply_sources_remain_trigger_gated(self) -> None:
        state = self.assessment["supply_source_state"]
        self.assertEqual(state["required_missing_source_count"], 3)
        self.assertFalse(state["active_polling"])
        self.assertFalse(state["canonical_reference_mode_promoted"])

    def test_both_delays_remain_unidentified(self) -> None:
        self.assertTrue(
            all(x["current_tau"] == "TBD" for x in self.assessment["delay_state"])
        )
        self.assertTrue(
            all(not x["scalar_tau_activation_ready"] for x in self.assessment["delay_state"])
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["disposition"]["feedback_activation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(any("feedback_activation_authorized" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
