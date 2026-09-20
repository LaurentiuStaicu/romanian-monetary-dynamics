from __future__ import annotations

import unittest

from scripts.probe_mof_announced_RON_primary_supply_source_vintage import (
    anchor_checks,
    load_contract,
    normalized,
    validate_pdf,
)


class MOFAnnouncedRONPrimarySupplySourceVintageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_three_frozen_pilot_sources(self) -> None:
        docs = self.contract["pilot_source_documents"]
        self.assertEqual(len(docs), 3)
        self.assertEqual(
            {item["source_id"] for item in docs},
            {
                "mof_order_6826_january_2025",
                "mof_order_159_february_2025",
                "mof_order_352_march_2025",
            },
        )
        for item in docs:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertIn("mfinante.gov.ro", item["url"])

    def test_document_totals_reconcile(self) -> None:
        for item in self.contract["pilot_source_documents"]:
            self.assertEqual(
                item["article_1_base_nominal_RON_million"]
                + item["article_1_SSON_max_RON_million"],
                item["article_1_document_total_RON_million"],
            )

    def test_pdf_validation(self) -> None:
        validate_pdf(b"%PDF-1.7\n" + b"x" * 50000)
        with self.assertRaisesRegex(RuntimeError, "not a PDF"):
            validate_pdf(b"nope" + b"x" * 50000)
        with self.assertRaisesRegex(RuntimeError, "unexpectedly small"):
            validate_pdf(b"%PDF-1.7\nsmall")

    def test_anchor_matching_is_whitespace_case_tolerant(self) -> None:
        source = self.contract["pilot_source_documents"][0]
        text = """
        ORDIN   NR. 6826
        ANEXA 1
        ANEXA 2
        PROSPECT DE EMISIUNE
        Data Licitaţiei
        Valoare nominală
        SSON
        IANUARIE
        """
        checks = anchor_checks(text, source)
        self.assertTrue(all(checks.values()))

    def test_probe_is_not_reference_mode_promotion(self) -> None:
        gate = self.contract["materialisation_gate"]
        self.assertFalse(gate["reference_mode_promotion_authorized_by_contract_alone"])
        self.assertFalse(self.contract["scientific_guards"]["yield_effect_estimation_authorized"])
        self.assertFalse(self.contract["scientific_guards"]["feedback_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
