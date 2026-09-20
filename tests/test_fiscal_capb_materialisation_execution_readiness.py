from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FiscalCapbMaterialisationExecutionReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(
            "model/registries/fiscal_capb_materialisation_execution_readiness_2026_09_19.json"
        )
        self.m = load("model/registries/model_contract.json")

    def test_original_live_gate_executed_successfully_and_was_reviewed(self) -> None:
        self.assertEqual(
            self.a["status"],
            "WORKFLOW_EXECUTED_SUCCESS_ARTIFACT_REVIEWED_TIMING_ADJUDICATED_RAW_REPOSITORY_RETENTION_PENDING",
        )
        state = self.a["execution_state"]
        self.assertTrue(state["live_provider_work_manual_only"])
        self.assertTrue(state["execution_performed"])
        self.assertEqual(state["workflow_run_id"], 35481663720)
        self.assertEqual(state["workflow_conclusion"], "success")
        self.assertEqual(state["artifact_id"], 10595244882)
        self.assertEqual(state["release_count"], 9)
        self.assertTrue(state["retained_artifact_reviewed"])
        self.assertTrue(state["timing_adjudication_completed"])
        self.assertFalse(state["repository_raw_bytes_retained"])
        self.assertFalse(state["retained_source_vintage_created"])

    def test_next_probe_is_preregistered_but_not_executed(self) -> None:
        state = self.a["execution_state"]
        self.assertTrue(state["pre2022_source_probe_preregistered"])
        self.assertFalse(state["pre2022_source_probe_executed"])
        self.assertEqual(
            state["pre2022_source_probe_contract"],
            "model/calibration_validation/fiscal_reaction_capb_pre2022_source_probe_contract.json",
        )

    def test_scientific_effect_remains_closed(self) -> None:
        effects = self.a["scientific_effects"]
        self.assertEqual(effects["mechanism_classification"], "DEFERRED")
        self.assertFalse(effects["active_calibration_cycle_open"])
        self.assertFalse(effects["estimation_or_refit_authorized"])
        self.assertFalse(
            effects["prior_final_evaluation_2018_2024_opening_authorized"]
        )
        self.assertFalse(effects["system_dynamics_feedback_activation"])
        self.assertFalse(effects["behavioural_closure_activation"])

    def test_model_contract_points_to_pre2022_manual_gate_not_autonomous_work(self) -> None:
        stage = self.m["scientific_stage"]
        self.assertTrue(stage["selective_reopen_active"])
        self.assertIsNone(stage["active_autonomous_empirical_task"])
        self.assertEqual(
            stage["active_manual_empirical_gate"],
            "FISCAL_PRIMARY_BALANCE_CAPB_PRE2022_SOURCE_STRUCTURE_PROBE",
        )
        self.assertEqual(
            stage["selective_reopen_execution_state"],
            "TIMING_ADJUDICATED_PRE2022_SOURCE_PROBE_AND_RAW_RETENTION_PENDING",
        )
        self.assertFalse(stage["fiscal_capb_repository_raw_bytes_retained"])


if __name__ == "__main__":
    unittest.main()
