from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_oecd_sectoral_financial_positions_semantic_adjusted_gate import row_gate

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_exact_gate_contract_2026_09_21.json"

class OecdSemanticAdjustedGateTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_only_one_semantic_exception_is_authorized(self):
        x=self.c["semantic_exception"]["exact_key_pattern"]
        self.assertEqual(x,{"source_sector":"S1M","accounting_entry":"L","instrument":"F2"})
        self.assertEqual(self.c["semantic_exception"]["value_million_ron"],0.0)
        self.assertFalse(self.c["semantic_exception"]["may_override_present_nonzero_row"])

    def test_all_hard_rules_hold(self):
        self.assertTrue(all(self.c["hard_rules"].values()))

    def test_exception_presence_is_conflict(self):
        row={"TIME_PERIOD":"2014-Q1","SECTOR":"S1M","ACCOUNTING_ENTRY":"L","INSTR_ASSET":"F2"}
        gate=row_gate([row],self.c)
        self.assertTrue(gate["semantic_exception_rows_present"])
        self.assertFalse(gate["row_gate_pass"])

    def test_contract_does_not_promote_reference_mode(self):
        self.assertIn("separate explicit reference-mode promotion assessment",self.c["promotion_rule"])

if __name__=="__main__":
    unittest.main()
