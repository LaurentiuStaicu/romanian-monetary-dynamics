from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_feedback_architecture_structural_review_terminal_assessment import (
    ASSESSMENT_PATH, HOLD_ID, STATUS, audit_feedback_architecture_terminal,
)

ROOT = Path(__file__).resolve().parents[1]

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class FeedbackArchitectureTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(ASSESSMENT_PATH)
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.model = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")
        self.validation = load("model/calibration_validation/validation_recovery_disposition.json")

    def audit(self, assessment=None):
        return audit_feedback_architecture_terminal(
            assessment or self.a, self.feedback, self.readiness, self.boundary,
            self.delays, self.criteria, self.model, self.baseline, self.validation,
        )

    def test_current_terminal_assessment_passes(self):
        self.assertEqual(self.audit(), [])

    def test_all_registered_structures_have_terminal_assessments(self):
        self.assertEqual(len(self.a["structure_terminal_states"]), 5)
        self.assertTrue(all(x["terminal_assessment"] for x in self.a["structure_terminal_states"]))

    def test_no_exact_link_or_activation_ready_structure(self):
        self.assertEqual(self.a["registry_snapshot"]["exact_integrated_link_forms_ready"], 0)
        self.assertEqual(self.a["activation_state"]["structures_activation_ready"], 0)

    def test_open_chain_remains_explicit(self):
        rows = [x for x in self.a["structure_terminal_states"] if x["topology_status"] == "OPEN_CHAIN"]
        self.assertEqual([x["id"] for x in rows], ["external_fx_refinancing_loop"])

    def test_architecture_is_on_evidence_triggered_hold(self):
        self.assertEqual(self.a["decision"], STATUS)
        self.assertEqual(self.a["next_state"]["id"], HOLD_ID)
        self.assertIsNone(self.a["disposition"]["active_structural_review_task"])

    def test_manual_activation_is_detected(self):
        mutated = copy.deepcopy(self.a)
        mutated["disposition"]["quantitative_feedback_activation_authorized"] = True
        self.assertTrue(any("quantitative_feedback_activation_authorized" in e for e in self.audit(mutated)))

if __name__ == "__main__":
    unittest.main()
