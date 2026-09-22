from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary import (
    HORIZON,
    PREDECESSOR,
    audit_trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary,
)

ROOT = Path(__file__).resolve().parents[1]

class TriggerAwareMonitoringHorizonPostCounterpartWorkflowBoundaryTests(unittest.TestCase):
    def test_current_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary(),
            [],
        )

    def test_trigger_set_is_identical_to_predecessor(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        p = json.loads((ROOT / PREDECESSOR).read_text(encoding="utf-8"))
        self.assertEqual(h["supersedes"], PREDECESSOR)
        self.assertEqual(h["horizons"], p["horizons"])

    def test_counterpart_workflows_are_trigger_conditioned(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        b = h["counterpart_probe_execution_boundary"]
        self.assertFalse(b["rerun_authorized_now"])
        self.assertFalse(b["unchanged_dataset_vintage_is_trigger"])
        self.assertFalse(b["routine_quarterly_release_is_trigger"])
        self.assertFalse(b["manual_rerun_without_trigger_counts_as_scientific_progress"])
        self.assertFalse(h["current_disposition"]["accounting_counterpart_topology_trigger_satisfied"])
        self.assertFalse(h["current_disposition"]["accounting_counterpart_probe_rerun_authorized_now"])

if __name__ == "__main__":
    unittest.main()
