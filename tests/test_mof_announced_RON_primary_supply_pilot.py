from __future__ import annotations

import copy
import unittest

from scripts.audit_mof_announced_RON_primary_supply_pilot import (
    ASSESSMENT_PATH,
    EVENTS_PATH,
    MONTHLY_PATH,
    audit_announced_supply_q1_pilot,
    load,
    read_csv,
)


class AnnouncedRONPrimarySupplyQ1PilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.manifest = load(
            "data/source_vintages/"
            "mof-announced-ron-primary-supply-pilot-2026-09-20/"
            "source_vintage_manifest.json"
        )
        self.events = read_csv(EVENTS_PATH)
        self.monthly = read_csv(MONTHLY_PATH)
        self.measurement_design = load(
            "model/dynamics/"
            "government_securities_supply_measurement_design_review_2026_09_20.json"
        )
        self.source_review = load(
            "model/dynamics/"
            "government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/"
            "government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")
        self.reference_modes = load("model/dynamics/reference_modes.json")

    def audit(self, **overrides):
        return audit_announced_supply_q1_pilot(
            overrides.get("assessment", self.assessment),
            overrides.get("manifest", self.manifest),
            overrides.get("events", self.events),
            overrides.get("monthly", self.monthly),
            overrides.get("measurement_design", self.measurement_design),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("reference_modes", self.reference_modes),
        )

    def test_current_q1_pilot_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_exact_monthly_values_are_frozen(self) -> None:
        values = self.assessment["monthly_pilot"]["values_RON_million"]
        self.assertEqual(
            values,
            {
                "2025-01": 5770.0,
                "2025-02": 8040.0,
                "2025-03": 8165.0,
            },
        )

    def test_march_boundary_moves_one_sson_to_april(self) -> None:
        forward = self.assessment["event_level_pilot"]["post_cutoff_forward_events"]
        self.assertEqual(
            forward,
            [
                {
                    "event_date": "2025-04-01",
                    "event_type": "BENCHMARK_BOND_SSON",
                    "isin": "RO45DLJ4EE76",
                    "announced_nominal_RON_million": 75.0,
                    "source_id": "mof_order_352_march_2025",
                }
            ],
        )
        self.assertEqual(
            self.assessment["monthly_pilot"]["march_difference_RON_million"],
            75.0,
        )

    def test_legacy_anchor_false_negative_is_explicitly_superseded(self) -> None:
        diagnostic = self.assessment["raw_probe_diagnostic"]
        self.assertFalse(diagnostic["manifest_all_anchor_checks_pass"])
        self.assertFalse(
            diagnostic["source_retention_is_blocked_by_legacy_anchor_diagnostic"]
        )
        self.assertTrue(
            self.assessment["pilot_result"]["all_document_reconciliations_pass"]
        )

    def test_q1_pilot_is_not_canonical_full_reference_mode(self) -> None:
        self.assertFalse(
            self.assessment["pilot_result"]["full_reference_mode_promoted"]
        )
        self.assertFalse(
            any(
                mode["id"] == "announced_RON_primary_supply_level"
                for mode in self.reference_modes["modes"]
            )
        )

    def test_manual_full_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["pilot_result"]["full_reference_mode_promoted"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("may not promote full reference mode" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
