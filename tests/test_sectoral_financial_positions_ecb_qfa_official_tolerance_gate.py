from __future__ import annotations
import json
import unittest
from decimal import Decimal
from pathlib import Path

from scripts.audit_sectoral_financial_positions_ecb_qfa_official_tolerance_gate import sector_net

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_official_tolerance_gate_contract_2026_09_21.json"
A=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_tolerance_authority_assessment_2026_09_21.json"

class EcbQfaOfficialToleranceGateTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))
        self.a=json.loads(A.read_text(encoding="utf-8"))

    def test_authority_is_independent_and_does_not_promote(self):
        self.assertEqual(self.a["official_evidence"][0]["normative_threshold_eur_million"],10)
        self.assertTrue(self.a["independence_from_rmd_residuals"]["threshold_predates_rmd_gate"])
        self.assertFalse(self.a["scientific_effect"]["reference_mode_promoted"])

    def test_gate_tests_per_instrument_horizontal_consistency(self):
        self.assertEqual(self.c["source_boundary"]["instruments"],["F2","F3","F4","F5","F6","F7","F8"])
        self.assertIn("every measure",self.c["official_consistency_gate"]["primary_test"])

    def test_threshold_conversion_is_conservative(self):
        fx=self.c["fx_threshold_gate"]
        self.assertEqual(fx["threshold_eur_million"],"10")
        self.assertIn("minimum_positive_daily_RON_per_EUR_rate",fx["conversion"])

    def test_exact_decimal_net(self):
        vals={("2025-Q1","S11","A","F3"):Decimal("10.2"),("2025-Q1","S11","L","F3"):Decimal("3.1")}
        self.assertEqual(sector_net(vals,"2025-Q1","S11","F3"),Decimal("7.1"))

    def test_shortcuts_remain_forbidden(self):
        self.assertTrue(all(self.c["hard_rules"].values()))

if __name__=="__main__": unittest.main()
