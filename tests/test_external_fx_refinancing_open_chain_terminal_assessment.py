from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_external_fx_refinancing_open_chain_terminal_assessment import (
    ASSESSMENT_PATH, HOLD_ID, P1, P2, P3, P4, STATUS,
    audit_external_fx_refinancing_open_chain_terminal_assessment,
)

ROOT = Path(__file__).resolve().parents[1]

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class ExternalFxRefinancingOpenChainTerminalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(ASSESSMENT_PATH)
        self.reviews = [load(P1), load(P2), load(P3), load(P4)]
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.criteria = load("model/dynamics/feedback_activation_criteria_matrix.json")
        self.delays = load("model/dynamics/delay_evidence_registry.json")
        self.mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
        self.source = load("model/calibration_validation/external_fx_refinancing_source_boundary_review.json")
        self.model = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, assessment=None):
        return audit_external_fx_refinancing_open_chain_terminal_assessment(
            assessment or self.a, self.reviews, self.feedback, self.readiness,
            self.boundary, self.criteria, self.delays, self.mechanisms,
            self.source, self.model, self.baseline,
        )

    def test_current_terminal_assessment_passes(self):
        self.assertEqual(self.audit(), [])

    def test_all_four_links_remain_not_equation_ready(self):
        rows = [x for x in self.readiness["links"] if x["loop_id"] == "external_fx_refinancing_loop"]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(not x["exact_integrated_equation_ready"] for x in rows))

    def test_structure_remains_open_chain(self):
        loop = next(x for x in self.feedback["loops"] if x["id"] == "external_fx_refinancing_loop")
        self.assertEqual(loop["topology_status"], "OPEN_CHAIN")
        self.assertFalse(loop["closing_link_authorized"])
        self.assertTrue(self.a["disposition"]["open_chain_remains_open"])

    def test_joint_exposure_is_not_inferred(self):
        self.assertFalse(self.source["source_boundary_findings"]["joint_currency_x_residual_maturity_by_sector_available"])
        self.assertFalse(self.a["next_state"]["may_infer_joint_exposure"])

    def test_terminal_hold_is_explicit(self):
        self.assertEqual(self.a["decision"], STATUS)
        self.assertEqual(self.a["next_state"]["id"], HOLD_ID)
        self.assertIsNone(self.a["disposition"]["active_empirical_task"])

    def test_manual_closing_link_authorization_is_detected(self):
        mutated = copy.deepcopy(self.a)
        mutated["disposition"]["closing_link_authorized"] = True
        self.assertTrue(any("closing_link_authorized" in e for e in self.audit(mutated)))

if __name__ == "__main__":
    unittest.main()
