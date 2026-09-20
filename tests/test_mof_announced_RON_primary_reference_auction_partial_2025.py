from __future__ import annotations

import csv
import json
import unittest
from collections import defaultdict
from pathlib import Path

from scripts.materialise_mof_announced_RON_primary_reference_auction_partial_2025 import (
    parse_romanian_number,
)

ROOT = Path(__file__).resolve().parents[1]


class MOFAnnouncedRONPrimaryReferenceAuctionPartial2025Tests(unittest.TestCase):
    def test_romanian_number_parser_handles_decimal_and_thousands_forms(self) -> None:
        self.assertEqual(parse_romanian_number("6,85"), 6.85)
        self.assertEqual(parse_romanian_number("500.000.000"), 500000000.0)
        self.assertEqual(parse_romanian_number("500,000,000"), 500000000.0)

    def test_q1_competitive_only_monthly_sums_are_exact(self) -> None:
        path = ROOT / "data/processed/mof_announced_RON_primary_supply_Q1_2025_events.csv"
        sums = defaultdict(float)
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["event_type"] == "BENCHMARK_BOND_SSON":
                    continue
                sums[row["event_date"][:7]] += float(
                    row["announced_nominal_RON_million"]
                )
        self.assertEqual(
            dict(sums),
            {
                "2025-01": 5200.0,
                "2025-02": 7200.0,
                "2025-03": 7400.0,
            },
        )

    def test_full_year_candidate_excludes_sson(self) -> None:
        path = (
            ROOT
            / "model/dynamics/"
            "mof_announced_RON_primary_supply_full_2025_definition_review_2026_09_20.json"
        )
        review = json.loads(path.read_text(encoding="utf-8"))
        design = review["full_year_measurement_design"]
        self.assertEqual(
            design["canonical_candidate_id"],
            "announced_RON_primary_reference_auction_supply_level",
        )
        self.assertNotIn(
            "BENCHMARK_BOND_SSON",
            design["included_event_types"],
        )
        self.assertIn(
            "BENCHMARK_BOND_SSON",
            design["excluded_from_canonical_candidate"],
        )

    def test_partial_source_vintage_has_nine_retained_raw_sources(self) -> None:
        path = (
            ROOT
            / "data/source_vintages/"
            "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20/"
            "source_vintage_manifest.json"
        )
        manifest = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["raw_sources_retained_count"], 9)
        self.assertEqual(manifest["raw_sources_unavailable_count"], 3)
        self.assertEqual(
            set(manifest["retained_source_ids"]),
            {
                "mof_order_541_april_2025",
                "mof_order_728_may_2025",
                "mof_order_752_may_2025_amendment",
                "mof_order_871_june_2025",
                "mof_order_1088_july_2025",
                "mof_order_1452_september_2025",
                "mof_order_1626_october_2025",
                "mof_order_1831_november_2025_amendment",
                "mof_order_1928_december_2025",
            },
        )
        self.assertEqual(
            set(manifest["unavailable_source_ids"]),
            {
                "mof_order_1221_august_2025",
                "mof_order_1795_november_2025",
                "mof_order_1998_december_2025_amendment",
            },
        )
        self.assertFalse(manifest["canonical_reference_mode_promoted"])
        self.assertFalse(manifest["feedback_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
