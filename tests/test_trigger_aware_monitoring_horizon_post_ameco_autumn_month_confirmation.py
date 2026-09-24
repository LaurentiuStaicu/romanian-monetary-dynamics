from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation import (
    HORIZON,
    PREDECESSOR,
    audit_trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation,
)

ROOT = Path(__file__).resolve().parents[1]


class TriggerAwareMonitoringHorizonPostAmecoAutumnMonthConfirmationTests(unittest.TestCase):
    def test_current_horizon_passes(self) -> None:
        self.assertEqual(
            audit_trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation(),
            [],
        )

    def test_only_ameco_timing_is_refined(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        p = json.loads((ROOT / PREDECESSOR).read_text(encoding="utf-8"))
        current = {x["id"]: x for x in h["horizons"]}
        prior = {x["id"]: x for x in p["horizons"]}
        for trigger_id in current:
            if trigger_id != "ameco_structural_primary_new_full_vintage":
                self.assertEqual(current[trigger_id], prior[trigger_id])

    def test_november_is_window_not_invented_day(self) -> None:
        h = json.loads((ROOT / HORIZON).read_text(encoding="utf-8"))
        a = next(
            x for x in h["horizons"]
            if x["id"] == "ameco_structural_primary_new_full_vintage"
        )
        timing = a["official_timing_confirmation"]
        self.assertEqual(timing["expected_release_month"], "2026-11")
        self.assertFalse(timing["exact_publication_date_identified"])
        self.assertFalse(a["pre_november_2026_release_presence_check_authorized"])
        self.assertFalse(h["current_disposition"]["ameco_release_trigger_satisfied"])
        self.assertFalse(
            h["current_disposition"]["ameco_source_materialisation_reopen_active"]
        )


if __name__ == "__main__":
    unittest.main()
