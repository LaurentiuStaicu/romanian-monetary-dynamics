from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETIRED = (
    ".github/workflows/bnr-government-issuance-raw-source-acquisition.yml",
    ".github/workflows/ecb-supply-load-denominator-probe.yml",
    ".github/workflows/mof-announced-ron-primary-supply-probe.yml",
    ".github/workflows/mof-announced-ron-primary-supply-materialise.yml",
    ".github/workflows/mof-realized-financing-channel-source-vintage.yml",
    ".github/workflows/mof-supply-pressure-source-vintage-probe.yml",
)
VERIFIER = ROOT / ".github/workflows/verify-retained-completed-source-vintages.yml"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class RetiredCompletedSourceVintageWriteWorkflowsTests(unittest.TestCase):
    def test_completed_write_workflows_are_retired(self) -> None:
        for relative in RETIRED:
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_current_verifier_is_manual_and_read_only(self) -> None:
        self.assertTrue(VERIFIER.is_file())
        text = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertNotIn("contents: write", text)
        self.assertNotIn("push:", text)
        self.assertNotIn("git push", text)

    def test_governing_assessments_show_completed_retention_stages(self) -> None:
        bnr = load(
            "model/dynamics/"
            "government_debt_issuance_bnr_raw_source_retention_assessment_2025.json"
        )
        self.assertTrue(bnr["retained_vintage"]["repository_retained"])
        self.assertTrue(bnr["retained_vintage"]["raw_bytes_immutable"])
        self.assertTrue(bnr["scientific_effect"]["raw_source_retention_blocker_closed"])

        ecb = load(
            "model/dynamics/"
            "government_securities_supply_load_ecb_denominator_probe_assessment_2026_09_20.json"
        )
        self.assertTrue(ecb["retained_vintage"]["repository_retained"])
        self.assertTrue(ecb["scientific_effect"]["ecb_candidate_source_retention_complete"])
        self.assertFalse(ecb["scientific_effect"]["denominator_selected"])

        supply = load(
            "model/dynamics/"
            "government_securities_supply_pressure_source_vintage_probe_assessment_2026_09_20.json"
        )
        self.assertTrue(supply["retained_vintage"]["repository_retained"])
        self.assertTrue(
            supply["scientific_effect"]["raw_source_retention_blocker_closed_for_probe_sources"]
        )

        financing = load(
            "model/dynamics/"
            "mof_realized_financing_channel_source_vintage_assessment_2026_09_21.json"
        )
        self.assertEqual(financing["source_retention"]["report_count"], 12)
        self.assertTrue(financing["source_retention"]["all_months_available"])
        self.assertTrue(financing["source_retention"]["official_MoF_PDFs_retained"])
        self.assertFalse(
            financing["materialisation_disposition"]["monthly_increment_equation_authorized"]
        )

        q1 = load(
            "model/dynamics/"
            "mof_announced_RON_primary_supply_reference_mode_pilot_Q1_2025.json"
        )
        self.assertTrue(
            q1["scientific_disposition"]["exact_event_level_pilot_materialised"]
        )
        self.assertTrue(
            q1["scientific_disposition"]["exact_completed_monthly_pilot_materialised"]
        )
        self.assertFalse(
            q1["scientific_disposition"]["canonical_reference_modes_registry_promoted"]
        )


if __name__ == "__main__":
    unittest.main()
