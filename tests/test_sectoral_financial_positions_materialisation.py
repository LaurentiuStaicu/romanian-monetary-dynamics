from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_materialisation_contract_2026_09_21.json"

class SectoralFinancialPositionsMaterialisationTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_output_row_counts_are_frozen(self):
        self.assertEqual(self.c["required_row_counts"]["reference_series"],588)
        self.assertEqual(self.c["required_row_counts"]["instrument_breakdown"],4116)

    def test_mapping_has_exact_s121_cancellation(self):
        m=self.c["sector_mapping"]
        coeff={}
        for terms in m.values():
            for sector,sign in terms:
                coeff[sector]=coeff.get(sector,0)+sign
        self.assertEqual(coeff["S121"],0)
        self.assertEqual({k:v for k,v in coeff.items() if v!=0},{"S1M":1,"S11":1,"S12":1,"S13":1,"S2":1})

    def test_materialisation_has_no_model_activation_effect(self):
        self.assertTrue(all(self.c["hard_rules"].values()))
        self.assertIn("no_accounting_spine_promotion",self.c["hard_rules"])
        self.assertIn("no_behavioural_closure_change",self.c["hard_rules"])

if __name__=="__main__":
    unittest.main()
