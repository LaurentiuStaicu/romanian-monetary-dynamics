from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_market_and_lending_rates_to_credit_flow_boundary import REVIEW_PATH,STATUS,audit_rates_to_credit_flow
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class RatesToCreditFlowTests(unittest.TestCase):
 def setUp(self):
  self.r=load(REVIEW_PATH);self.pc=load("model/dynamics/private_credit_reference_assessment.json");self.a=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json");self.b=load("model/dynamics/feedback_variable_boundary_registry.json");self.l=load("model/dynamics/feedback_link_readiness_registry.json");self.f=load("model/dynamics/feedback_registry.json");self.m=load("model/registries/model_contract.json");self.s=load("model/registries/scientific_baseline_manifest.json")
 def audit(self,r=None):return audit_rates_to_credit_flow(r or self.r,self.pc,self.a,self.b,self.l,self.f,self.m,self.s)
 def test_current(self):self.assertEqual(self.audit(),[])
 def test_rate_not_flow(self):self.assertFalse(self.r["bridge_resolution"]["direct_rate_to_credit_flow_identity_authorized"])
 def test_mir_volume_not_bsi_transaction(self):self.assertFalse(self.r["bridge_resolution"]["MIR_new_business_volume_substitution_authorized"])
 def test_manual_identity_detected(self):
  x=copy.deepcopy(self.r);x["bridge_resolution"]["direct_rate_to_credit_flow_identity_authorized"]=True;self.assertTrue(any("direct_rate_to_credit_flow_identity_authorized" in e for e in self.audit(x)))
if __name__=="__main__":unittest.main()
