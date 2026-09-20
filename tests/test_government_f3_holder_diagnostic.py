from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.generate_government_f3_holder_diagnostic import build

ROOT = Path(__file__).resolve().parents[1]


class GovernmentF3HolderDiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replay = json.loads(
            (ROOT / "model/dynamics/f3_empirical_replay_2025.json").read_text(
                encoding="utf-8"
            )
        )
        self.artifact = json.loads(
            (ROOT / "model/dynamics/government_f3_holder_diagnostic_2025.json").read_text(
                encoding="utf-8"
            )
        )

    def test_diagnostic_is_reproducible(self) -> None:
        self.assertEqual(self.artifact, build(self.replay))

    def test_holder_shares_sum_to_one(self) -> None:
        for quarter in self.artifact["quarterly_holder_composition"].values():
            self.assertAlmostEqual(
                sum(item["share"] for item in quarter["holders"].values()),
                1.0,
                places=5,
            )

    def test_transition_decompositions_close(self) -> None:
        for item in self.artifact["transition_net_incurrence_and_other_flows"].values():
            self.assertEqual(item["decomposition_residual_million_RON"], 0.0)

    def test_semantic_non_equivalences_are_explicit(self) -> None:
        summary = self.artifact["current_summary"]
        self.assertFalse(summary["net_incurrence_is_gross_issuance"])
        self.assertFalse(summary["net_incurrence_is_refinancing_need"])
        self.assertFalse(summary["holder_composition_is_supply_pressure"])
        self.assertFalse(summary["feedback_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
