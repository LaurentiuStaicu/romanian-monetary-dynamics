from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from scripts.audit_ecb_qfa_materiality_acceptability_gate import (
    evaluate_materiality,
    parse_diagnostics,
    quarter_range,
)

ROOT=Path(__file__).resolve().parents[1]
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"

class EcbQfaMaterialityGateTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(C.read_text(encoding="utf-8"))

    def test_contract_preserves_strict_historical_gate(self):
        self.assertTrue(self.c["hard_rules"]["no_change_to_historical_0_1m_gate"])
        self.assertTrue(self.c["hard_rules"]["no_accounting_spine_promotion"])

    def test_conservative_threshold_is_ten_million_ron(self):
        self.assertEqual(
            self.c["retained_diagnostic_gate"]["conservative_threshold_million_ron"],
            "10",
        )
        self.assertEqual(self.c["official_materiality_rule"]["threshold_eur"],10000000)

    def test_retained_diagnostics_have_98_unique_measure_period_rows(self):
        rows=parse_diagnostics()
        keys={(r["measure"],r["time_period"]) for r in rows}
        self.assertEqual(len(rows),98)
        self.assertEqual(len(keys),98)

    def test_synthetic_fx_above_one_yields_pass_on_retained_diagnostics(self):
        periods=quarter_range("2014-Q1","2026-Q1")
        fx={p:Decimal("4.5") for p in periods}
        out=evaluate_materiality(fx,parse_diagnostics(),self.c)
        self.assertTrue(out["pass"])
        self.assertEqual(out["max_abs_system_residual_million_ron"],"0.6")
        self.assertEqual(out["materiality_violations"],[])

    def test_fx_at_one_blocks_gate(self):
        periods=quarter_range("2014-Q1","2026-Q1")
        fx={p:Decimal("4.5") for p in periods}
        fx["2020-Q1"]=Decimal("1")
        out=evaluate_materiality(fx,parse_diagnostics(),self.c)
        self.assertFalse(out["pass"])
        self.assertEqual(out["fx_periods_at_or_below_one"],["2020-Q1"])

if __name__=="__main__":
    unittest.main()
