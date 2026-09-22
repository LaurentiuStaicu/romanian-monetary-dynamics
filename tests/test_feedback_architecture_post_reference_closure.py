from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_feedback_architecture_post_reference_closure import (
    ASSESSMENT_PATH,
    audit_feedback_architecture_post_reference_closure,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FeedbackArchitecturePostReferenceClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.predecessor = load(
            "model/dynamics/feedback_architecture_structural_review_terminal_assessment_2026_09_21.json"
        )
        self.reference_successor = load(
            "model/dynamics/reference_mode_post_terminal_promotion_assessment_2026_09_21.json"
        )
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.model = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")
        self.validation = load("model/calibration_validation/validation_recovery_disposition.json")

    def audit(self, assessment=None):
        return audit_feedback_architecture_post_reference_closure(
            assessment or self.assessment,
            self.predecessor,
            self.reference_successor,
            self.feedback,
            self.readiness,
            self.delays,
            self.criteria,
            self.model,
            self.baseline,
            self.validation,
        )

    def test_current_successor_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_historical_9_of_10_snapshot_is_preserved(self) -> None:
        self.assertEqual(
            self.predecessor["remaining_integrated_blockers"]["reference_modes_ready"],
            9,
        )
        self.assertEqual(
            self.predecessor["remaining_integrated_blockers"]["reference_mode_blocker"],
            "sectoral_financial_positions",
        )

    def test_current_state_is_10_of_10_without_feedback_activation(self) -> None:
        current = self.assessment["current_reference_mode_state"]
        architecture = self.assessment["current_feedback_architecture_state"]
        self.assertEqual((current["reference_modes_ready"], current["reference_modes_required"]), (10, 10))
        self.assertIsNone(current["reference_mode_blocker"])
        self.assertEqual(architecture["exact_integrated_link_forms_ready"], 0)
        self.assertEqual(architecture["feedback_structures_activation_ready"], 0)
        self.assertFalse(architecture["behavioural_closure_active"])

    def test_false_activation_after_reference_closure_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["structure_disposition"]["quantitative_feedback_activation_authorized"] = True
        self.assertTrue(
            any("quantitative_feedback_activation_authorized" in error for error in self.audit(mutated))
        )


if __name__ == "__main__":
    unittest.main()
