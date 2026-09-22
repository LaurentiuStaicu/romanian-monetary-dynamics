from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_ameco_access_protocol import (
    AMECO,
    HORIZON,
    PREDECESSOR,
    audit_trigger_aware_monitoring_horizon_post_ameco_access_protocol,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizonPostAmecoAccessProtocolTests(unittest.TestCase):
    def test_current_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_ameco_access_protocol(),
            [],
        )

    def test_ameco_trigger_is_protocol_bound_but_closed(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        a = json.loads((ROOT / AMECO).read_text(encoding="utf-8"))
        self.assertEqual(h["supersedes"], PREDECESSOR)
        by_id = {x["id"]: x for x in h["horizons"]}
        ameco = by_id["ameco_structural_primary_new_full_vintage"]
        self.assertEqual(ameco["source_access_protocol"]["assessment"], AMECO)
        self.assertEqual(ameco["source_access_protocol"]["target_variable_code"], "UBLGBPS")
        self.assertFalse(ameco["source_access_protocol"]["redisstat_dataset_code_identified"])
        self.assertIsNone(ameco["source_access_protocol"]["redisstat_dataset_code"])
        self.assertFalse(ameco["source_access_protocol"]["trigger_satisfied"])
        self.assertEqual(
            set(ameco["source_access_protocol"]["official_dataset_discovery_routes"]),
            {
                a["official_current_state"]["redisstat_dataflow_catalogue_endpoint"],
                a["official_current_state"]["redisstat_catalogue_toc_txt_endpoint"],
                a["official_current_state"]["redisstat_browser_ameco_root"],
            },
        )

    def test_all_existing_trigger_dates_and_windows_are_preserved(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        by_id = {x["id"]: x for x in h["horizons"]}
        self.assertEqual(by_id["prospective_monetary_policy_event"]["next_check_date"], "2026-10-08")
        self.assertEqual(
            by_id["prospective_monetary_policy_event"]["downstream_release_gate"]["earliest_official_MIR_release_date"],
            "2026-12-02",
        )
        self.assertEqual(
            by_id["accounting_counterpart_topology"]["current_known_release_context"]["ECB_QSA_next_data_release"],
            "2026-10-02",
        )
        self.assertEqual(
            by_id["f4_bnr_cnf_2025_stock_counterpart_matrix"]["earliest_evidence_window"],
            "after 2026-10-31",
        )
        self.assertFalse(h["current_disposition"]["any_monitoring_gate_open_now"])


if __name__ == "__main__":
    unittest.main()
