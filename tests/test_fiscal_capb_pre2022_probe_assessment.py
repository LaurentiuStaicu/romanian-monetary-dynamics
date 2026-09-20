from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FiscalCapbPre2022ProbeAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = load(
            "model/calibration_validation/fiscal_capb_pre2022_source_probe_assessment_2026_09_20.json"
        )
        self.s = load(
            "model/calibration_validation/fiscal_capb_measurement_semantic_refinement_2026_09_20.json"
        )

    def test_probe_result_is_complete_without_provider_failures(self) -> None:
        counts = self.a["result_counts"]
        self.assertEqual(counts["release_count"], 22)
        self.assertEqual(counts["target_present"], 15)
        self.assertEqual(counts["observed_target_not_found_in_valid_archive"], 6)
        self.assertEqual(counts["ambiguous_distinct_target_rows"], 1)
        self.assertEqual(counts["indeterminate_provider_or_archive_failure"], 0)
        self.assertEqual(
            self.a["first_exact_target_release"]["release_id"],
            "spring_2014",
        )

    def test_early_negatives_are_exact_code_negatives_not_generic_capb_absence(self) -> None:
        self.assertEqual(
            self.a["observed_negative_releases"],
            [
                "spring_2011", "autumn_2011",
                "spring_2012", "autumn_2012",
                "spring_2013", "autumn_2013",
            ],
        )
        predecessor = self.a["predecessor_family_observation"]
        self.assertEqual(
            predecessor["code"],
            "ROM.1.0.319.0.UBLGBP",
        )
        self.assertTrue(predecessor["present_in_all_six_2011_2013_archives"])
        self.assertFalse(predecessor["same_target_as_ublgbps"])
        self.assertFalse(predecessor["substitution_authorized"])

    def test_autumn_2018_remains_unresolved_and_is_not_needed_for_spring_chain(self) -> None:
        ambiguous = self.a["ambiguous_release"]
        self.assertEqual(ambiguous["release_id"], "autumn_2018")
        self.assertEqual(ambiguous["distinct_matching_rows"], 2)
        self.assertEqual(
            ambiguous["adjudication"],
            "UNRESOLVED_EXCLUDE_FROM_CANONICAL_FIRST_HISTORICAL_CHAIN",
        )
        self.assertFalse(
            self.a["spring_first_historical_chain"][
                "autumn_2018_ambiguity_affects_chain"
            ]
        )

    def test_spring_first_historical_chain_is_2013_to_2025(self) -> None:
        path = ROOT / self.a["spring_first_historical_chain"]["processed_path"]
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 13)
        self.assertEqual(int(rows[0]["year"]), 2013)
        self.assertEqual(int(rows[-1]["year"]), 2025)
        self.assertEqual(
            [int(row["year"]) for row in rows],
            list(range(2013, 2026)),
        )

    def test_historical_support_change_is_explicit(self) -> None:
        coverage = self.a["historical_coverage_structure"]
        self.assertEqual(coverage["spring_2014_historical_span"], "2003..2013")
        self.assertEqual(coverage["spring_2015_historical_span"], "2010..2014")
        self.assertEqual(
            coverage["stable_common_start_for_spring_2015_onward"],
            2010,
        )

    def test_semantic_refinement_keeps_structural_and_cyclically_adjusted_distinct(self) -> None:
        clarification = self.s["clarification"]
        self.assertEqual(clarification["exact_target_code"], "UBLGBPS")
        self.assertEqual(clarification["distinct_related_code"], "UBLGBP")
        self.assertEqual(
            clarification["corrected_exact_target"],
            "structural primary balance",
        )
        self.assertFalse(self.s["governance"]["automatic_switch_to_ublgbp"])
        self.assertTrue(self.s["governance"]["switch_requires_separate_preregistration"])
        self.assertTrue(
            self.s["modeling_implication"][
                "prior_output_gap_control_cannot_be_carried_over_automatically"
            ]
        )

    def test_probe_does_not_open_model_selection(self) -> None:
        effect = self.a["scientific_effect"]
        self.assertEqual(effect["mechanism_classification"], "DEFERRED")
        self.assertFalse(effect["active_calibration_cycle_open"])
        self.assertFalse(effect["estimation_authorized"])
        self.assertFalse(effect["model_selection_authorized"])
        self.assertFalse(effect["prior_2018_2024_final_evaluation_opening_authorized"])
        self.assertFalse(effect["system_dynamics_activation"])
        self.assertFalse(effect["behavioural_closure_change"])


if __name__ == "__main__":
    unittest.main()
