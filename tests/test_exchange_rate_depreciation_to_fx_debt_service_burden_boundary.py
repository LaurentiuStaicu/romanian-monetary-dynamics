from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_exchange_rate_depreciation_to_fx_debt_service_burden_boundary import REVIEW_PATH,STATUS,audit_fx_depreciation_to_debt_service
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class FXDepreciationToDebtServiceTests(unittest.TestCase):
 def setUp(self):
  self.r=load(REVIEW_PATH);self.sr=load("model/calibration_validation/external_fx_refinancing_source_boundary_review.json");self.b=load("model/dynamics/feedback_variable_boundary_registry.json");self.l=load("model/dynamics/feedback_link_readiness_registry.json");self.f=load("model/dynamics/feedback_registry.json");self.m=load("model/registries/model_contract.json");self.s=load("model/registries/scientific_baseline_manifest.json")
 def audit(self,r=None):return audit_fx_depreciation_to_debt_service(r or self.r,self.sr,self.b,self.l,self.f,self.m,self.s)
 def test_current(self):self.assertEqual(self.audit(),[])
 def test_no_zero_hedge_assumption(self):self.assertFalse(self.r["bridge_resolution"]["zero_hedging_assumption_authorized"])
 def test_no_reporting_currency_shortcut(self):self.assertFalse(self.r["bridge_resolution"]["reporting_unit_as_denomination_authorized"])
 def test_chain_remains_open(self):self.assertEqual(next(x for x in self.f["loops"] if x["id"]=="external_fx_refinancing_loop")["topology_status"],"OPEN_CHAIN")
 def test_manual_shortcut_detected(self):
  x=copy.deepcopy(self.r);x["bridge_resolution"]["zero_hedging_assumption_authorized"]=True;self.assertTrue(any("zero_hedging_assumption_authorized" in e for e in self.audit(x)))
if __name__=="__main__":unittest.main()
