from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_credit_flow_to_private_demand_and_investment_boundary import REVIEW_PATH,STATUS,audit_credit_flow_to_private_demand
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class CreditFlowToPrivateDemandTests(unittest.TestCase):
 def setUp(self):
  self.r=load(REVIEW_PATH);self.pc=load("model/dynamics/private_credit_reference_assessment.json");self.h=load("model/calibration_validation/household_consumption_source_boundary_review.json");self.i=load("model/calibration_validation/corporate_investment_source_boundary_review.json");self.b=load("model/dynamics/feedback_variable_boundary_registry.json");self.l=load("model/dynamics/feedback_link_readiness_registry.json");self.f=load("model/dynamics/feedback_registry.json");self.m=load("model/registries/model_contract.json");self.s=load("model/registries/scientific_baseline_manifest.json")
 def audit(self,r=None):return audit_credit_flow_to_private_demand(r or self.r,self.pc,self.h,self.i,self.b,self.l,self.f,self.m,self.s)
 def test_current(self):self.assertEqual(self.audit(),[])
 def test_credit_not_consumption(self):self.assertFalse(self.r["bridge_resolution"]["direct_credit_to_consumption_mapping_authorized"])
 def test_credit_not_investment(self):self.assertFalse(self.r["bridge_resolution"]["direct_credit_to_investment_mapping_authorized"])
 def test_manual_mapping_detected(self):
  x=copy.deepcopy(self.r);x["bridge_resolution"]["NFC_credit_as_GFCF_authorized"]=True;self.assertTrue(any("NFC_credit_as_GFCF_authorized" in e for e in self.audit(x)))
if __name__=="__main__":unittest.main()
