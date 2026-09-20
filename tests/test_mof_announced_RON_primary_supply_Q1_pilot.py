from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_announced_RON_primary_supply_Q1_pilot import (
    PILOT_PATH,
    audit_announced_supply_q1_pilot,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFAnnouncedRONPrimarySupplyQ1PilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pilot = load(PILOT_PATH)
        self.contract = load(
            "model/dynamics/mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
        )
        self.manifest = load(
            "data/source_vintages/mof-announced-ron-primary-supply-pilot-2026-09-20/"
            "source_vintage_manifest.json"
        )
        self.measurement_design = load(
            "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_announced_supply_q1_pilot(
            overrides.get("pilot", self.pilot),
            overrides.get("contract", self.contract),
            overrides.get("manifest", self.manifest),
            overrides.get("measurement_design", self.measurement_design),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_q1_pilot_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_completed_monthly_reference_mode_uses_event_dates(self) -> None:
        self.assertEqual(
            self.pilot["completed_monthly_reference_mode"],
            {
                "2025-01": 5770.0,
                "2025-02": 8040.0,
                "2025-03": 8165.0,
            },
        )

    def test_march_document_total_excludes_april_sson_from_march_reference_mode(self) -> None:
        checks = self.pilot["crosschecks"]
        self.assertEqual(checks["march_document_total_RON_million"], 8240.0)
        self.assertEqual(checks["march_completed_period_RON_million"], 8165.0)
        self.assertEqual(
            checks["march_difference_due_to_2025_04_01_SSON_RON_million"],
            75.0,
        )
        forward = self.pilot["forward_schedule_not_in_completed_reference_mode"]
        self.assertEqual(len(forward), 1)
        self.assertEqual(forward[0]["event_date"], "2025-04-01")
        self.assertEqual(forward[0]["event_type"], "BENCHMARK_BOND_SSON")
        self.assertEqual(forward[0]["announced_nominal_RON_million"], 75.0)

    def test_canonical_reference_mode_is_not_yet_promoted(self) -> None:
        disposition = self.pilot["scientific_disposition"]
        self.assertFalse(disposition["canonical_reference_modes_registry_promoted"])
        self.assertFalse(disposition["feedback_activation_authorized"])
        self.assertEqual(
            self.pilot["next_gate"]["id"],
            "mof_announced_RON_primary_supply_full_2025_extension",
        )

    def test_manual_canonical_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.pilot)
        mutated["scientific_disposition"][
            "canonical_reference_modes_registry_promoted"
        ] = True
        errors = self.audit(pilot=mutated)
        self.assertTrue(
            any("canonical_reference_modes_registry_promoted" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.pilot)
        mutated["scientific_disposition"]["feedback_activation_authorized"] = True
        errors = self.audit(pilot=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
