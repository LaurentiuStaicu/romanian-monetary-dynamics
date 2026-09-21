from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_validation_contract_2026_09_21.json"

class EcbQfa10mGateTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_threshold_is_official_and_not_result_selected(self):
        self.assertEqual(self.c["official_validation_rule"]["threshold_eur_million"],"10")
        self.assertEqual(self.c["official_validation_rule"]["comparison"],"ABS(DISCREPANCY_EUR_MILLION) < 10")

    def test_gate_is_per_instrument(self):
        self.assertTrue(self.c["official_validation_rule"]["per_instrument_required"])
        self.assertEqual(self.c["validation_gate"]["required_tests"],686)
        self.assertIn("per-instrument",self.c["validation_gate"]["pass_rule"])

    def test_fx_conversion_is_measure_specific(self):
        self.assertEqual(self.c["exchange_rate_conversion"]["flow_series"],"EXR.Q.RON.EUR.SP00.A")
        self.assertEqual(self.c["exchange_rate_conversion"]["stock_series"],"EXR.Q.RON.EUR.SP00.E")
        self.assertTrue(self.c["exchange_rate_conversion"]["no_interpolation"])

    def test_semantic_exception_is_only_s1m_l_f2(self):
        self.assertEqual(
            self.c["semantic_exception"]["exact_key_pattern"],
            {"source_sector":"S1M","accounting_entry":"L","instrument":"F2"},
        )
        self.assertEqual(Decimal(self.c["semantic_exception"]["value_million_ron"]),Decimal("0"))

    def test_sector_mapping_cancels_s121_between_f_and_bnr(self):
        m=self.c["sector_mapping"]
        self.assertEqual(m["F"]["terms"],[["S12",1],["S121",-1]])
        self.assertEqual(m["BNR"]["terms"],[["S121",1]])
        coeff={}
        for spec in m.values():
            for sector,sign in spec["terms"]:
                coeff[sector]=coeff.get(sector,0)+sign
        self.assertEqual(coeff["S121"],0)
        self.assertEqual(
            {k:v for k,v in coeff.items() if v!=0},
            {"S1M":1,"S11":1,"S12":1,"S13":1,"S2":1},
        )

    def test_historical_gate_is_not_rewritten(self):
        self.assertTrue(self.c["hard_rules"]["no_rewrite_of_historical_0_1_million_ron_gate"])
        self.assertTrue(self.c["hard_rules"]["no_threshold_selected_from_observed_residuals"])
        self.assertTrue(all(self.c["hard_rules"].values()))

if __name__=="__main__":
    unittest.main()
