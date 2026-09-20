from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_delay_evidence import audit_delay_evidence

ROOT = Path(__file__).resolve().parents[1]


class DelayEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feedback = json.loads(
            (ROOT / "model" / "dynamics" / "feedback_registry.json").read_text(encoding="utf-8")
        )
        self.delay = json.loads(
            (ROOT / "model" / "dynamics" / "delay_evidence_registry.json").read_text(encoding="utf-8")
        )

    def audit(self, delay=None):
        return audit_delay_evidence(self.feedback, delay or self.delay)

    def test_current_registry_passes(self):
        self.assertEqual(self.audit(), [])

    def test_all_feedback_delay_candidates_are_covered(self):
        self.assertEqual(
            {x["id"] for x in self.feedback["delay_candidates"]},
            {x["id"] for x in self.delay["delays"]},
        )

    def test_observation_frequency_cannot_become_tau(self):
        mutated = copy.deepcopy(self.delay)
        item = next(x for x in mutated["delays"] if x["id"] == "credit_supply_adjustment_delay")
        item["current_tau"] = 0.25
        errors = self.audit(mutated)
        self.assertTrue(any("blocked scalar tau must remain TBD" in e for e in errors))

    def test_average_maturity_cannot_become_tau_without_validation(self):
        mutated = copy.deepcopy(self.delay)
        item = next(x for x in mutated["delays"] if x["id"] == "debt_service_maturity_delay")
        item["current_tau"] = 7.0
        item["scalar_tau_activation_ready"] = True
        errors = self.audit(mutated)
        self.assertTrue(any("tau ready without validated scalar evidence" in e for e in errors))

    def test_failed_fx_lag_contract_does_not_activate_delay(self):
        item = next(x for x in self.delay["delays"] if x["id"] == "fx_pass_through_delay")
        self.assertEqual(
            item["evidence_status"],
            "DISTRIBUTED_TIMING_EVIDENCE_SCALAR_TAU_NOT_IDENTIFIED",
        )
        self.assertFalse(item["scalar_tau_activation_ready"])
        self.assertEqual(item["current_tau"], "TBD")

    def test_registry_cannot_authorize_activation(self):
        mutated = copy.deepcopy(self.delay)
        mutated["current_summary"]["activation_authorized"] = True
        self.assertTrue(any("may not authorize activation" in e for e in self.audit(mutated)))


if __name__ == "__main__":
    unittest.main()
