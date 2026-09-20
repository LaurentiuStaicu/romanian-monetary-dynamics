from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TriggerAwareMonitoringHorizonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.h = load(
            "model/registries/trigger_aware_monitoring_horizon_2026_09_20.json"
        )
        self.m = load("model/registries/model_contract.json")
        self.b = load("model/registries/scientific_baseline_manifest.json")
        self.p = load(
            "model/calibration_validation/prospective_monetary_confirmation_status.json"
        )

    def test_horizon_preserves_baseline_hold(self) -> None:
        state = self.h["current_disposition"]
        self.assertFalse(state["any_monitoring_gate_open_now"])
        self.assertFalse(state["active_calibration_cycle_open"])
        self.assertFalse(state["response_values_authorized_for_inspection_now"])
        self.assertFalse(state["estimation_or_refit_authorized"])
        self.assertFalse(state["model_selection_authorized"])
        self.assertFalse(state["target_family_switch_authorized"])
        self.assertFalse(state["holdout_opening_authorized"])
        self.assertFalse(state["system_dynamics_activation_authorized"])
        self.assertFalse(state["behavioural_closure_authorized"])

    def test_next_dated_check_is_bnr_policy_event_only(self) -> None:
        next_check = self.h["current_disposition"]["next_dated_check"]
        self.assertEqual(next_check["date"], "2026-10-08")
        self.assertEqual(next_check["id"], "prospective_monetary_policy_event")
        monetary = next(
            x for x in self.h["horizons"]
            if x["id"] == "prospective_monetary_policy_event"
        )
        self.assertEqual(monetary["next_check_type"], "DATE_SCHEDULED_EVENT_CHECK")
        self.assertIn("non-zero", monetary["trigger"])
        self.assertIn("do not inspect MIR", monetary["action_if_no_trigger"])

    def test_october_response_is_release_gated(self) -> None:
        monetary = next(
            x for x in self.h["horizons"]
            if x["id"] == "prospective_monetary_policy_event"
        )
        gate = monetary["downstream_release_gate"]
        self.assertEqual(gate["reference_month_if_event_occurs_on_2026_10_08"], "2026-10")
        self.assertEqual(gate["earliest_official_MIR_release_date"], "2026-12-02")
        self.assertFalse(self.p["prospective_window"]["response_series_values_inspected"])

    def test_ameco_check_is_release_conditioned_not_polled(self) -> None:
        fiscal = next(
            x for x in self.h["horizons"]
            if x["id"] == "ameco_structural_primary_new_full_vintage"
        )
        self.assertEqual(fiscal["next_check_type"], "RELEASE_CONDITIONED_CHECK")
        self.assertEqual(fiscal["current_latest_full_release"], "2026-06-03")
        self.assertIn("No repeated AMECO probing", fiscal["action_before_release"])

    def test_frozen_source_paths_require_new_evidence_or_topology(self) -> None:
        by_id = {x["id"]: x for x in self.h["horizons"]}
        self.assertEqual(
            by_id["bnr_bls_2025_q2_exact_source"]["next_check_type"],
            "NEW_OFFICIAL_EVIDENCE_ONLY",
        )
        self.assertEqual(
            by_id["government_repricing_ledger"]["next_check_type"],
            "NEW_OFFICIAL_EVIDENCE_ONLY",
        )
        accounting = by_id["accounting_reference_mode_counterpart_topology"]
        self.assertEqual(
            accounting["next_check_type"],
            "CHANGED_DATASET_TOPOLOGY_OR_NEW_SOURCE_ONLY",
        )
        self.assertIn("routine new quarterly data vintage", accounting["current_known_release_context"]["rule"])

    def test_contract_and_baseline_register_same_horizon(self) -> None:
        expected = "model/registries/trigger_aware_monitoring_horizon_2026_09_20.json"
        self.assertEqual(
            self.m["scientific_stage"]["trigger_aware_monitoring_horizon"],
            expected,
        )
        self.assertEqual(
            self.b["canonical_state"]["scientific_stage"][
                "trigger_aware_monitoring_horizon"
            ],
            expected,
        )
        self.assertEqual(
            self.m["scientific_stage"]["next_dated_trigger_check"]["date"],
            "2026-10-08",
        )


if __name__ == "__main__":
    unittest.main()
