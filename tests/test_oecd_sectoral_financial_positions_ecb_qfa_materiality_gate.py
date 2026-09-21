from __future__ import annotations
import json
import unittest
from decimal import Decimal
from pathlib import Path

from scripts.audit_oecd_sectoral_financial_positions_ecb_qfa_materiality_gate import row_gate

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"

class EcbQfaMaterialityGateTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_official_threshold_is_fixed_at_10m_eur(self):
        self.assertEqual(Decimal(self.c["official_materiality_rule"]["threshold_million_eur"]),Decimal("10"))
        self.assertFalse(self.c["official_materiality_rule"]["threshold_selected_from_rmd_residuals"])

    def test_gate_is_instrument_level_and_keeps_three_identities(self):
        ids=[x["id"] for x in self.c["exact_decimal_gate"]["identities_per_measure_period_instrument"]]
        self.assertEqual(ids,["rmd_horizontal_system","s1_sector_aggregation","s1_plus_s2_horizontal"])
        self.assertTrue(all(x["required"] for x in self.c["exact_decimal_gate"]["identities_per_measure_period_instrument"]))

    def test_fx_series_is_official_quarterly_ecb_reference_rate(self):
        x=self.c["source_boundary"]["ecb_exchange_rate"]
        self.assertEqual(x["dataset"],"EXR")
        self.assertEqual(x["series_key"],"Q.RON.EUR.SP00.A")
        self.assertEqual(x["unit"],"RON per EUR")

    def test_semantic_exception_remains_narrow(self):
        x=self.c["semantic_exception"]["exact_key_pattern"]
        self.assertEqual(x,{"source_sector":"S1M","accounting_entry":"L","instrument":"F2"})
        self.assertFalse(self.c["semantic_exception"]["may_override_present_provider_row"])

    def test_hard_rules_all_hold(self):
        self.assertTrue(all(self.c["hard_rules"].values()))

if __name__=="__main__":
    unittest.main()
