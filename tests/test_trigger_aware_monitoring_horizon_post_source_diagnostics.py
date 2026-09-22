from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_source_diagnostics import (
    HORIZON,
    PREDECESSOR,
    audit_trigger_aware_monitoring_horizon_post_source_diagnostics,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizonPostSourceDiagnosticsTests(unittest.TestCase):
    def test_current_successor_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_source_diagnostics(),
            [],
        )

    def test_successor_preserves_dates_and_closes_both_new_source_clues(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        self.assertEqual(h["supersedes"], PREDECESSOR)
        by_id = {x["id"]: x for x in h["horizons"]}
        self.assertEqual(
            by_id["prospective_monetary_policy_event"]["next_check_date"],
            "2026-10-08",
        )
        self.assertEqual(
            by_id["prospective_monetary_policy_event"]["downstream_release_gate"]["earliest_official_MIR_release_date"],
            "2026-12-02",
        )
        self.assertFalse(
            by_id["bnr_bls_2025_q2_exact_source"]["latest_adjudication"]["trigger_satisfied"]
        )
        self.assertFalse(
            by_id["government_repricing_ledger"]["latest_adjudication"]["trigger_satisfied"]
        )
        self.assertFalse(h["current_disposition"]["any_monitoring_gate_open_now"])

    def test_post_f4_horizon_remains_immutable_predecessor(self) -> None:
        predecessor = json.loads((ROOT / PREDECESSOR).read_text(encoding="utf-8"))
        self.assertEqual(predecessor["registry_version"], "0.4")
        self.assertNotIn(
            "bnr_bls_2025q2_latest_post_terminal_review",
            predecessor["governing_state"],
        )
        self.assertNotIn(
            "government_repricing_latest_exchange_topology_review",
            predecessor["governing_state"],
        )


if __name__ == "__main__":
    unittest.main()
