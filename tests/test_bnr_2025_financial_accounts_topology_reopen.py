from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_2025_financial_accounts_topology_reopen import (
    A,C,M,audit_bnr_2025_financial_accounts_topology_reopen,
)

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class Bnr2025FinancialAccountsTopologyReopenTests(unittest.TestCase):
    def setUp(self):
        self.a=load(A); self.c=load(C); self.m=load(M)
        self.ra=load("model/dynamics/sectoral_financial_positions_reference_assessment.json")
        self.es=load("model/dynamics/sectoral_financial_positions_external_source_screening.json")
        self.rm=load("model/dynamics/reference_modes.json")
        self.model=load("model/registries/model_contract.json")
        self.base=load("model/registries/scientific_baseline_manifest.json")
        self.acc=load("model/accounting/accounting_readiness_gate.json")

    def audit(self,a=None,c=None):
        return audit_bnr_2025_financial_accounts_topology_reopen(
            a or self.a,c or self.c,self.m,self.ra,self.es,self.rm,self.model,self.base,self.acc
        )

    def test_current_reopen_state_passes(self):
        self.assertEqual(self.audit(),[])

    def test_reference_mode_stays_partial_and_9_of_10(self):
        mode=next(x for x in self.rm["modes"] if x["id"]=="sectoral_financial_positions")
        self.assertEqual(mode["status"],"PARTIAL_SERIES_AVAILABLE")
        self.assertEqual(self.model["dynamic_core"]["reference_mode_ready_count"],9)
        self.assertEqual(self.model["dynamic_core"]["reference_mode_required_count"],10)

    def test_metadata_only_cannot_promote_reference_mode(self):
        x=copy.deepcopy(self.a)
        x["scientific_effect"]["reference_mode_readiness_count_change"]=1
        self.assertTrue(any("readiness" in e for e in self.audit(a=x)))

    def test_public_access_topology_passed_but_exact_row_gate_failed_terminally(self):
        s=self.c["current_state"]
        self.assertTrue(s["execution_completed"])
        self.assertTrue(s["topology_pass"])
        self.assertFalse(s["aggregate_reference_mode_gate_pass"])
        self.assertFalse(s["bilateral_accounting_reopen_gate_pass"])
        self.assertFalse(s["reference_mode_promotion_authorized"])
        self.assertFalse(s["accounting_reopen_authorized"])
        self.assertEqual(
            s["terminal_assessment"],
            "model/dynamics/sectoral_financial_positions_oecd_exact_row_gate_assessment_2026_09_21.json",
        )

    def test_s121_and_f2_f8_boundaries_are_frozen(self):
        t=self.c["frozen_target"]
        self.assertEqual(t["required_source_sector_semantics"]["BNR"],"S121 separately observable")
        self.assertEqual(t["required_instruments"],["F2","F3","F4","F5","F6","F7","F8"])

    def test_no_scientific_activation_from_source_trigger(self):
        self.assertFalse(self.a["scientific_effect"]["accounting_readiness_change"])
        self.assertFalse(self.a["scientific_effect"]["parameter_estimation_authorized"])
        self.assertFalse(self.a["scientific_effect"]["feedback_activation_authorized"])
        self.assertFalse(self.a["scientific_effect"]["behavioural_closure_authorized"])

if __name__=="__main__": unittest.main()
