from __future__ import annotations
import json
import unittest
from decimal import Decimal
from pathlib import Path
from scripts.audit_ecb_qfa_10m_horizontal_consistency_gate import per_instrument_residuals
from scripts.audit_ecb_qfa_10m_horizontal_gate_preregistration import audit_ecb_qfa_10m_preregistration

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_contract_2026_09_21.json"

class EcbQfa10mGateTests(unittest.TestCase):
    def setUp(self): self.c=json.loads(C.read_text())

    def test_preregistration_state(self):
        self.assertEqual(audit_ecb_qfa_10m_preregistration(),[])

    def test_threshold_is_per_instrument_and_not_aggregate(self):
        self.assertTrue(self.c["horizontal_identity"]["per_measure_per_period_per_instrument"])
        self.assertTrue(self.c["hard_rules"]["no_instrument_aggregation_before_threshold_test"])

    def test_strict_ron_bound_is_ten(self):
        self.assertEqual(Decimal(self.c["official_threshold_gate"]["first_stage_strict_sufficient_bound_million_ron"]),Decimal("10"))

    def test_semantic_exception_remains_only_s1m_l_f2(self):
        self.assertEqual(self.c["semantic_exception"]["exact_key_pattern"],{"source_sector":"S1M","accounting_entry":"L","instrument":"F2"})

    def test_no_binary_float_threshold(self):
        self.assertTrue(self.c["hard_rules"]["exact_decimal_arithmetic_required"])
        self.assertTrue(self.c["hard_rules"]["no_binary_float_threshold_comparison"])

if __name__=="__main__": unittest.main()
