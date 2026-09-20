from __future__ import annotations

import unittest

from scripts.probe_mof_announced_RON_primary_supply_source_vintage import (
    load_contract,
)


class MOFAnnouncedRONPrimarySupplySourceVintageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_three_official_pilot_orders_are_frozen(self) -> None:
        docs = self.contract["pilot_source_documents"]
        self.assertEqual(len(docs), 3)
        self.assertEqual(
            {item["order_number"] for item in docs},
            {"6826", "159", "352"},
        )
        for item in docs:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertIn("mfinante.gov.ro", item["url"])

    def test_article_1_totals_reconcile_before_download(self) -> None:
        for item in self.contract["pilot_source_documents"]:
            self.assertEqual(
                item["article_1_base_nominal_RON_million"]
                + item["article_1_SSON_max_RON_million"],
                item["article_1_document_total_RON_million"],
            )

    def test_probe_does_not_authorize_ocr_or_activation(self) -> None:
        gate = self.contract["materialisation_gate"]
        self.assertFalse(gate["ocr_authorized"])
        self.assertFalse(gate["visual_chart_digitisation_authorized"])
        self.assertFalse(gate["manual_value_approximation_authorized"])
        self.assertFalse(
            self.contract["scientific_guards"]["feedback_activation_authorized"]
        )

    def test_event_extraction_is_not_assumed_before_raw_probe(self) -> None:
        self.assertTrue(
            self.contract["materialisation_gate"]["raw_pdf_retention_required"]
        )
        self.assertTrue(
            self.contract["materialisation_gate"]["native_text_extraction_required"]
        )
        self.assertFalse(
            self.contract["materialisation_gate"][
                "reference_mode_promotion_authorized_by_contract_alone"
            ]
        )


if __name__ == "__main__":
    unittest.main()
