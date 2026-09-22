from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_2026_09_22 import (
    audit_trigger_aware_monitoring_horizon_2026_09_22,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizon20260922Tests(unittest.TestCase):
    def test_post_f4_monitoring_horizon_is_consistent(self) -> None:
        self.assertEqual(audit_trigger_aware_monitoring_horizon_2026_09_22(), [])

    def test_generic_baseline_authority_tracks_current_monitoring_horizon(self) -> None:
        baseline = json.loads(
            (ROOT / "model/registries/scientific_baseline_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        model = json.loads(
            (ROOT / "model/registries/model_contract.json").read_text(encoding="utf-8")
        )
        authority = baseline["authority"]["trigger_aware_monitoring_horizon"]
        self.assertEqual(
            authority,
            baseline["canonical_state"]["scientific_stage"]["trigger_aware_monitoring_horizon"],
        )
        self.assertEqual(
            authority,
            model["scientific_stage"]["trigger_aware_monitoring_horizon"],
        )
        self.assertEqual(
            baseline["authority"]["trigger_aware_monitoring_horizon_post_f4_structural"],
            "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_f4_structural.json",
        )


if __name__ == "__main__":
    unittest.main()
