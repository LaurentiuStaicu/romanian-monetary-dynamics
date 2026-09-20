from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT / "data" / "source_vintages"
    / "fiscal-reaction-capb-realtime-artifact-review-2026-09-20"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FiscalCapbTimingAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(
            "model/calibration_validation/fiscal_capb_timing_adjudication_2026_09_20.json"
        )

    def test_materialisation_run_and_artifact_are_exactly_identified(self) -> None:
        source = self.a["source_materialisation"]
        self.assertEqual(source["workflow_run_id"], 35481663720)
        self.assertEqual(source["workflow_conclusion"], "success")
        self.assertEqual(source["artifact_id"], 10595244882)
        self.assertEqual(source["release_count"], 9)
        self.assertEqual(
            source["inventory_sha256"],
            "55e494ca4010ed75c602392da0fcedee02cecf1aa27aa901833b6ed8d7775588",
        )
        self.assertEqual(
            source["artifact_zip_sha256"],
            "b6a73296e17b490fef6d785a6eee711d6ebf3ba086ab63b63abb973bdf12037b",
        )

    def test_repository_inventory_and_selected_rows_match_reviewed_hashes(self) -> None:
        inventory_path = BASE / "fiscal_capb_release_inventory.csv"
        self.assertEqual(
            sha256(inventory_path),
            self.a["source_materialisation"]["inventory_sha256"],
        )
        with inventory_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(row["status"] == "EXACT_TARGET_ROW_RETAINED" for row in rows))
        for row in rows:
            selected = BASE / "selected_rows" / f'{row["release_id"]}.txt'
            self.assertTrue(selected.is_file(), row["release_id"])
            self.assertEqual(sha256(selected), row["matched_row_sha256"])

    def test_timing_panel_separates_historical_estimates_from_forecasts(self) -> None:
        path = BASE / "fiscal_capb_realtime_values.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreater(len(rows), 100)
        for row in rows:
            year = int(row["year"])
            cutoff = int(row["historical_cutoff"])
            expected = (
                "HISTORICAL_ESTIMATE_UNDER_GENERIC_AMECO_HORIZON"
                if year <= cutoff
                else "FORECAST_UNDER_GENERIC_AMECO_HORIZON"
            )
            self.assertEqual(row["information_status"], expected)

    def test_first_historical_panel_has_five_unbackfilled_observations(self) -> None:
        path = BASE / "fiscal_capb_first_historical_estimates.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([int(x["year"]) for x in rows], [2021, 2022, 2023, 2024, 2025])
        self.assertEqual(len(rows), 5)
        max_abs_revision = max(abs(float(x["revision_to_spring_2026_pp"])) for x in rows)
        self.assertAlmostEqual(max_abs_revision, 0.31809, places=5)

    def test_timing_adjudication_does_not_open_model_selection(self) -> None:
        decision = self.a["scientific_decision"]
        self.assertTrue(decision["timing_adjudication_passed"])
        self.assertTrue(decision["source_extension_probe_authorized"])
        self.assertFalse(decision["new_structural_selection_contract_authorized"])
        self.assertFalse(decision["estimation_authorized"])
        self.assertFalse(decision["model_selection_authorized"])
        self.assertFalse(decision["prior_2018_2024_final_evaluation_opening_authorized"])
        self.assertFalse(decision["system_dynamics_activation"])
        self.assertFalse(decision["behavioural_closure_change"])

    def test_raw_bytes_are_not_overclaimed_as_repository_retained(self) -> None:
        source = self.a["source_materialisation"]
        self.assertFalse(source["repository_raw_bytes_retained"])
        self.assertFalse(source["exact_source_vintage_reproducibility_claim_allowed"])
        self.assertEqual(
            source["reproducibility_classification"],
            "HASH_AND_SELECTED_ROW_REVIEW_WITH_TEMPORARY_ACTIONS_RAW_BYTES",
        )

    def test_short_realtime_window_cannot_reuse_prior_validation_design(self) -> None:
        sample = self.a["sample_size_adjudication"]
        self.assertEqual(sample["current_first_historical_observations"], 5)
        self.assertEqual(
            sample["maximum_public_archive_first_historical_observations_if_pre_2022_target_presence_passes"],
            16,
        )
        self.assertEqual(
            sample["prior_cycle_total_target_years_across_initial_calibration_selection_and_final_evaluation"],
            29,
        )
        self.assertFalse(sample["prior_cycle_design_reusable"])
        self.assertTrue(
            self.a["hard_rules"]["no_weaker_validation_design_merely_to_fit_short_sample"]
        )


if __name__ == "__main__":
    unittest.main()
