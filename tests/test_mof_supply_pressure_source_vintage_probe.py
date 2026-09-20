from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.probe_mof_supply_pressure_source_vintage import (
    CONTRACT_PATH,
    anchor_assessment,
    load_contract,
    normalized,
    validate_pdf,
)

ROOT = Path(__file__).resolve().parents[1]


class MOFSupplyPressureSourceVintageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_contract_has_three_exact_official_sources(self) -> None:
        sources = self.contract["sources"]
        self.assertEqual(len(sources), 3)
        self.assertEqual(
            {item["source_id"] for item in sources},
            {
                "mof_flash_report_january_2025",
                "mof_public_debt_report_january_2025",
                "mof_public_debt_report_february_2025",
            },
        )
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIn("mfinante.gov.ro", source["url"])

    def test_probe_guard_forbids_ocr_and_approximation(self) -> None:
        rules = self.contract["extractability_rules"]
        self.assertTrue(rules["native_pdf_text_only"])
        self.assertFalse(rules["ocr_authorized"])
        self.assertFalse(rules["visual_chart_digitisation_authorized"])
        self.assertFalse(rules["manual_graph_value_approximation_authorized"])
        self.assertTrue(rules["absence_of_exact_values_must_remain_a_blocker"])

    def test_scientific_guard_keeps_feedback_closed(self) -> None:
        guards = self.contract["scientific_guards"]
        self.assertTrue(guards["raw_source_probe_only"])
        for key in (
            "government_securities_supply_pressure_node_resolved",
            "scalar_pressure_index_selected",
            "reference_mode_promotion_authorized",
            "estimation_authorized",
            "feedback_activation_authorized",
            "behavioural_closure_authorized",
            "public_version_change_authorized",
        ):
            self.assertFalse(guards[key])

    def test_pdf_magic_and_minimum_size_validation(self) -> None:
        validate_pdf(b"%PDF-1.7\n" + b"x" * 100, 100)
        with self.assertRaisesRegex(RuntimeError, "not a PDF"):
            validate_pdf(b"not-pdf" + b"x" * 100, 100)
        with self.assertRaisesRegex(RuntimeError, "unexpectedly small"):
            validate_pdf(b"%PDF-1.7\nsmall", 100)

    def test_anchor_assessment_is_whitespace_and_case_tolerant(self) -> None:
        text = "Domestic   Auctions - January 2025\nSIZE ANNOUNCED\nTotal RON"
        checks = anchor_assessment(
            text,
            [
                "Domestic auctions - January 2025",
                "Size Announced",
                "Total RON",
            ],
        )
        self.assertTrue(all(checks.values()))

    def test_manual_feedback_authorization_change_is_detectable_in_contract(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["scientific_guards"]["feedback_activation_authorized"] = True
        self.assertTrue(
            mutated["scientific_guards"]["feedback_activation_authorized"]
        )
        self.assertFalse(
            self.contract["scientific_guards"]["feedback_activation_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
