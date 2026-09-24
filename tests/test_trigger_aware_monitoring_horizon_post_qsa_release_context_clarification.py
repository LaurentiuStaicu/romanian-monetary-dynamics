from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_qsa_release_context_clarification import (
    HORIZON,
    PREDECESSOR,
    audit_trigger_aware_monitoring_horizon_post_qsa_release_context_clarification,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizonPostQsaReleaseContextClarificationTests(unittest.TestCase):
    def test_current_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_qsa_release_context_clarification(),
            [],
        )

    def test_only_accounting_release_context_changes(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        p = json.loads((ROOT / PREDECESSOR).read_text(encoding="utf-8"))
        current = {x["id"]: x for x in h["horizons"]}
        prior = {x["id"]: x for x in p["horizons"]}
        for trigger_id in current:
            if trigger_id != "accounting_counterpart_topology":
                self.assertEqual(current[trigger_id], prior[trigger_id])

    def test_two_qsa_milestones_are_context_not_trigger(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        q = next(x for x in h["horizons"] if x["id"] == "accounting_counterpart_topology")
        context = q["current_known_release_context"]
        self.assertEqual(context["ECB_QSA_households_nfc_release"], "2026-10-02")
        self.assertEqual(context["ECB_QSA_full_institutional_sector_release"], "2026-10-28")
        self.assertFalse(h["current_disposition"]["accounting_counterpart_topology_trigger_satisfied"])
        self.assertFalse(h["current_disposition"]["accounting_counterpart_probe_rerun_authorized_now"])


if __name__ == "__main__":
    unittest.main()
