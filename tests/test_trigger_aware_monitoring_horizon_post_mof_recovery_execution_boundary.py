from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary import (
    HORIZON,
    PREDECESSOR,
    RECOVERY,
    WORKFLOWS,
    TARGET_BRANCHES,
    audit_trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizonPostMofRecoveryExecutionBoundaryTests(
    unittest.TestCase
):
    def test_current_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary(),
            [],
        )

    def test_existing_trigger_set_and_content_are_identical_to_predecessor(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        p = json.loads((ROOT / PREDECESSOR).read_text(encoding="utf-8"))
        self.assertEqual(h["supersedes"], PREDECESSOR)
        self.assertEqual(h["horizons"], p["horizons"])

    def test_mof_recovery_stays_closed_until_new_evidence(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        r = json.loads((ROOT / RECOVERY).read_text(encoding="utf-8"))
        b = h["mof_full_2025_recovery_execution_boundary"]
        self.assertEqual(r["path_disposition"]["state"], "EVIDENCE_TRIGGERED_HOLD")
        self.assertFalse(r["path_disposition"]["active_polling"])
        self.assertFalse(b["current_execution_authorized"])
        self.assertFalse(b["active_polling"])
        self.assertEqual(b["remaining_required_source_count"], 3)
        self.assertFalse(
            h["current_disposition"]["mof_full_2025_recovery_trigger_satisfied"]
        )

    def test_recovery_workflows_are_manual_evidence_declared_and_branch_explicit(self) -> None:
        for name, relative in WORKFLOWS.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("workflow_dispatch:", text, name)
            self.assertNotIn("\n  push:", text, name)
            self.assertIn("trigger_condition:", text, name)
            self.assertIn("evidence_reference:", text, name)
            self.assertIn("evidence_verified:", text, name)
            self.assertIn("inputs.evidence_verified == true", text, name)
            self.assertIn(TARGET_BRANCHES[name], text, name)


if __name__ == "__main__":
    unittest.main()
