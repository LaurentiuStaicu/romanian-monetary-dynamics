from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_f3_behavior_diagnostics import audit_f3_behavior_diagnostics
from scripts.generate_f3_behavior_diagnostics import build_diagnostics

ROOT = Path(__file__).resolve().parents[1]


class F3BehaviorDiagnosticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay = json.loads(
            (
                ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
            ).read_text(encoding="utf-8")
        )
        self.artifact = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "f3_behavior_over_time_diagnostics_2025.json"
            ).read_text(encoding="utf-8")
        )
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "f3_behavior_over_time_diagnostics_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.reference_modes = json.loads(
            (ROOT / "model" / "dynamics" / "reference_modes.json").read_text(
                encoding="utf-8"
            )
        )
        self.model_contract = json.loads(
            (ROOT / "model" / "registries" / "model_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.regenerated = build_diagnostics(self.replay)

    def audit(self, artifact=None, contract=None, reference_modes=None, model=None):
        return audit_f3_behavior_diagnostics(
            artifact or self.artifact,
            contract or self.contract,
            self.regenerated,
            reference_modes or self.reference_modes,
            model or self.model_contract,
        )

    def test_current_diagnostics_pass(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_committed_diagnostics_are_exactly_reproducible(self) -> None:
        self.assertEqual(self.artifact, self.regenerated)

    def test_every_sector_and_bilateral_decomposition_closes(self) -> None:
        self.assertTrue(
            self.artifact["current_summary"][
                "all_sector_decomposition_residuals_zero"
            ]
        )
        self.assertTrue(
            self.artifact["current_summary"][
                "all_bilateral_decomposition_residuals_zero"
            ]
        )
        self.assertTrue(
            all(
                item["decomposition_residual_million_RON"] == 0.0
                for item in self.artifact["sector_summary"].values()
            )
        )
        self.assertTrue(
            all(
                item["decomposition_residual_million_RON"] == 0.0
                for item in self.artifact["bilateral_q1_to_q4_summary"]
            )
        )

    def test_reference_mode_remains_partial(self) -> None:
        mode = next(
            item
            for item in self.reference_modes["modes"]
            if item["id"] == "sectoral_financial_positions"
        )
        self.assertEqual(mode["status"], "PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(
            self.model_contract["dynamic_core"]["reference_mode_ready_count"],
            9,
        )
        self.assertFalse(
            self.model_contract["dynamic_core"]["reference_mode_closure_ready"]
        )

    def test_pattern_labels_use_exact_rules_only(self) -> None:
        allowed = {
            "FLAT",
            "MONOTONIC_INCREASE",
            "MONOTONIC_DECREASE",
            "MIXED",
        }
        for item in self.artifact["sector_summary"].values():
            self.assertIn(item["observed_asset_pattern"], allowed)
            self.assertIn(item["observed_liability_pattern"], allowed)
            self.assertIn(item["observed_net_position_pattern"], allowed)

    def test_transaction_activity_share_is_bounded(self) -> None:
        for item in self.artifact["bilateral_q1_to_q4_summary"]:
            share = item["transaction_share_of_absolute_change_activity"]
            if share is not None:
                self.assertGreaterEqual(share, 0.0)
                self.assertLessEqual(share, 1.0)

    def test_diagnostic_does_not_authorize_causal_or_feedback_claims(self) -> None:
        summary = self.artifact["current_summary"]
        self.assertFalse(summary["canonical_reference_mode_promoted"])
        self.assertFalse(summary["full_RMD_empirical_state_claim_allowed"])
        self.assertFalse(summary["causal_interpretation_authorized"])
        self.assertFalse(summary["behavioural_closure_active"])
        self.assertFalse(summary["feedback_activation_authorized"])

    def test_manual_reference_mode_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.reference_modes)
        mode = next(
            item
            for item in mutated["modes"]
            if item["id"] == "sectoral_financial_positions"
        )
        mode["status"] = "OBSERVED_SERIES_AVAILABLE"
        errors = self.audit(reference_modes=mutated)
        self.assertTrue(any("must remain PARTIAL" in error for error in errors))

    def test_manual_diagnostic_corruption_is_detected(self) -> None:
        mutated = copy.deepcopy(self.artifact)
        mutated["sector_summary"]["F"][
            "q1_to_q4_net_position_change_million_RON"
        ] += 1.0
        errors = self.audit(artifact=mutated)
        self.assertTrue(
            any(
                "differs from deterministic regeneration" in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
