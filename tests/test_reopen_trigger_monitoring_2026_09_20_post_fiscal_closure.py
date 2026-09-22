from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PostFiscalClosureTriggerMonitoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(
            "model/registries/reopen_trigger_monitoring_2026_09_20_post_fiscal_closure.json"
        )
        self.m = load("model/registries/model_contract.json")
        self.b = load("model/registries/scientific_baseline_manifest.json")
        self.p = load(
            "model/calibration_validation/prospective_monetary_confirmation_status.json"
        )

    def test_no_declared_trigger_is_satisfied(self) -> None:
        self.assertEqual(
            self.a["status"],
            "NO_DECLARED_REOPEN_TRIGGER_SATISFIED_POST_FISCAL_CLOSURE_BASELINE_HOLD_CONTINUES",
        )
        decision = self.a["decision"]
        self.assertFalse(decision["any_declared_reopen_trigger_satisfied"])
        self.assertFalse(decision["accounting_instrument_reopened"])
        self.assertFalse(decision["reference_mode_reopened"])
        self.assertFalse(decision["behavioural_mechanism_reopened"])
        self.assertFalse(decision["active_calibration_cycle_open"])
        self.assertFalse(decision["estimation_or_refit_authorized"])
        self.assertFalse(decision["model_selection_authorized"])
        self.assertFalse(decision["target_family_switch_authorized"])
        self.assertFalse(decision["system_dynamics_feedback_activation_authorized"])
        self.assertFalse(decision["behavioural_closure_activation_authorized"])
        self.assertEqual(
            decision["current_scientific_state"],
            "EVIDENCE_TRIGGERED_BASELINE_HOLD",
        )

    def test_monitoring_is_post_fiscal_closure(self) -> None:
        self.assertEqual(
            self.a["governing_registries"]["fiscal_source_closure"],
            "model/calibration_validation/fiscal_capb_raw_source_preservation_assessment_2026_09_20.json",
        )
        fiscal = self.a["findings"]["fiscal_structural_primary_vintage_extension"]
        self.assertEqual(fiscal["status"], "NO_REOPEN_NO_NEW_AMECO_FULL_RELEASE")
        self.assertIn("13-observation", fiscal["conclusion"])

    def test_current_contract_points_to_latest_snapshot(self) -> None:
        stage = self.m["scientific_stage"]
        expected = (
            "model/registries/"
            "reopen_trigger_monitoring_2026_09_20_post_fiscal_closure.json"
        )
        self.assertEqual(stage["latest_reopen_trigger_monitoring"], expected)
        self.assertEqual(
            stage["latest_reopen_trigger_monitoring_status"],
            self.a["status"],
        )
        self.assertEqual(
            stage["previous_reopen_trigger_monitoring"],
            "model/registries/reopen_trigger_monitoring_2026_09_19.json",
        )
        self.assertEqual(
            stage["latest_reopen_trigger_monitoring_superseded_for"],
            ["sectoral_financial_positions"],
        )
        self.assertFalse(stage["selective_reopen_active"])
        self.assertIsNone(stage["active_manual_empirical_gate"])

        baseline = self.b["canonical_state"]["scientific_stage"]
        self.assertEqual(baseline["latest_reopen_trigger_monitoring"], expected)
        self.assertEqual(
            baseline["latest_reopen_trigger_monitoring_status"],
            self.a["status"],
        )
        self.assertEqual(
            baseline["latest_reopen_trigger_monitoring_superseded_for"],
            ["sectoral_financial_positions"],
        )

    def test_prospective_policy_driver_check_advances_without_peeking(self) -> None:
        self.assertEqual(self.p["as_of_date"], "2026-09-20")
        self.assertEqual(
            self.p["prospective_window"]["driver_checked_through"],
            "2026-09-20",
        )
        self.assertFalse(
            self.p["prospective_window"]["response_series_values_inspected"]
        )
        self.assertFalse(
            self.p["identification_gate"]["identifying_driver_variation_available"]
        )
        self.assertEqual(
            self.p["identification_gate"]["status"],
            "WAIT_FOR_NEW_POLICY_RATE_EVENT",
        )

    def test_nonconfirmation_is_not_treated_as_absence(self) -> None:
        bls = self.a["findings"]["aggregate_bank_credit_bls_2025_q2"]
        self.assertIn("non-confirmation", bls["conclusion"])
        accounting = self.a["findings"]["accounting_and_sectoral_financial_positions"]
        self.assertIn("not proof", accounting["caveat"])


if __name__ == "__main__":
    unittest.main()
