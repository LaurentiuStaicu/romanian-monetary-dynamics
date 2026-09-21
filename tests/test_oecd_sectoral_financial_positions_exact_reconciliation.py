from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_oecd_sectoral_financial_positions_exact_reconciliation import (
    build_selection_key, quarter_range, selection_for_measure,
)

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_oecd_exact_extraction_reconciliation_contract_2026_09_21.json"

class OecdExactSectoralFinancialPositionsTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_quarter_range_is_frozen_49_quarters(self):
        q=quarter_range("2014-Q1","2026-Q1")
        self.assertEqual(len(q),49)
        self.assertEqual(q[0],"2014-Q1")
        self.assertEqual(q[-1],"2026-Q1")

    def test_query_requires_s121_and_rest_of_world(self):
        self.assertIn("S121",self.c["source"]["required_mapping_source_sectors"])
        self.assertIn("S2",self.c["source"]["required_mapping_source_sectors"])

    def test_exact_instrument_maturity_rule_is_frozen(self):
        m={k:v["MATURITY"] for k,v in self.c["instrument_mapping"].items()}
        self.assertEqual(m,{"F2":"T","F3":"T","F4":"T","F5":"_Z","F6":"_Z","F7":"T","F8":"T"})

    def test_selection_is_total_currency_nonconsolidated(self):
        s=selection_for_measure(self.c,"stock")
        self.assertEqual(s["CONSOLIDATION"],"N")
        self.assertEqual(s["CURRENCY_DENOM"],"_T")
        self.assertEqual(s["TRANSACTION"],"LE")
        self.assertEqual(s["ACCOUNTING_ENTRY"],["A","L"])

    def test_key_builder_preserves_multiselection(self):
        order=["FREQ","ADJUSTMENT","REF_AREA","SECTOR","ACCOUNTING_ENTRY"]
        sel={"FREQ":"Q","ADJUSTMENT":"N","REF_AREA":"ROU","SECTOR":["S11","S121"],"ACCOUNTING_ENTRY":["A","L"]}
        self.assertEqual(build_selection_key(order,sel),"Q.N.ROU.S11+S121.A+L")

    def test_missing_rows_fail_before_value_review(self):
        self.assertTrue(self.c["validation_gates"]["row_completeness_precedes_numeric_value_review"])
        self.assertIn("Any missing/duplicate exact row",self.c["failure_rule"])

    def test_scientific_shortcuts_remain_forbidden(self):
        for k,v in self.c["hard_rules"].items():
            self.assertTrue(v,k)

if __name__=="__main__":
    unittest.main()
