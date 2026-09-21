from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_monetary_credit_transmission_loop_terminal_assessment import (
    ASSESSMENT_PATH, HOLD_ID, STATUS,
    audit_monetary_credit_transmission_loop_terminal_assessment,
)

ROOT = Path(__file__).resolve().parents[1]

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class MonetaryCreditTransmissionLoopTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(ASSESSMENT_PATH)
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
        self.prospective = load("model/calibration_validation/prospective_monetary_confirmation_status.json")
        self.reaction_terminal = load("model/calibration_validation/monetary_policy_reaction_source_discovery_terminal_assessment.json")
        self.reference_modes = load("model/dynamics/reference_modes.json")
        self.model = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, assessment=None):
        return audit_monetary_credit_transmission_loop_terminal_assessment(
            assessment or self.a, self.feedback, self.readiness, self.boundary,
            self.criteria, self.delays, self.mechanisms, self.prospective,
            self.reaction_terminal, self.reference_modes, self.model, self.baseline,
        )

    def test_current_terminal_assessment_passes(self):
        self.assertEqual(self.audit(), [])

    def test_all_five_links_remain_not_equation_ready(self):
        rows = [x for x in self.readiness["links"] if x["loop_id"] == "monetary_credit_transmission_loop"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(not x["exact_integrated_equation_ready"] for x in rows))

    def test_policy_rate_remains_observed_forcing(self):
        node = next(x for x in self.boundary["variables"] if x["id"] == "policy_rate")
        mode = next(x for x in self.reference_modes["modes"] if x["id"] == "policy_rate")
        self.assertEqual(node["current_boundary_class"], "OBSERVED_FORCING")
        self.assertEqual(mode["current_endogeneity"], "EXOGENOUS_OBSERVED_INPUT")

    def test_no_core_inflation_reference_mode(self):
        self.assertFalse(any(x["id"] == "inflationary_pressure" for x in self.reference_modes["modes"]))

    def test_loop_is_on_evidence_triggered_hold(self):
        self.assertEqual(self.a["decision"], STATUS)
        self.assertEqual(self.a["next_state"]["id"], HOLD_ID)
        self.assertIsNone(self.a["disposition"]["active_empirical_task"])

    def test_manual_activation_is_detected(self):
        mutated = copy.deepcopy(self.a)
        mutated["disposition"]["feedback_activation_authorized"] = True
        self.assertTrue(any("feedback_activation_authorized" in e for e in self.audit(mutated)))

if __name__ == "__main__":
    unittest.main()
