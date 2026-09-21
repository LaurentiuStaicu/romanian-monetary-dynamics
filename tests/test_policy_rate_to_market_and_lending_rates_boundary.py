from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_policy_rate_to_market_and_lending_rates_boundary import REVIEW_PATH,STATUS,audit_policy_rate_to_rates
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class PolicyRateToRatesTests(unittest.TestCase):
 def setUp(self):
  self.r=load(REVIEW_PATH);self.v=load("model/calibration_validation/validation_recovery_disposition.json");self.p=load("model/calibration_validation/prospective_monetary_confirmation_status.json");self.b=load("model/dynamics/feedback_variable_boundary_registry.json");self.l=load("model/dynamics/feedback_link_readiness_registry.json");self.f=load("model/dynamics/feedback_registry.json");self.m=load("model/registries/model_contract.json");self.s=load("model/registries/scientific_baseline_manifest.json")
 def audit(self,r=None):return audit_policy_rate_to_rates(r or self.r,self.v,self.p,self.b,self.l,self.f,self.m,self.s)
 def test_current(self):self.assertEqual(self.audit(),[])
 def test_target_specific_only(self):self.assertFalse(self.r["bridge_resolution"]["generic_rate_node_mapping_authorized"])
 def test_nfc_not_inferred(self):self.assertFalse(self.r["bridge_resolution"]["nfc_form_inference_authorized"])
 def test_manual_generic_promotion_detected(self):
  x=copy.deepcopy(self.r);x["bridge_resolution"]["generic_rate_node_mapping_authorized"]=True;self.assertTrue(any("generic_rate_node_mapping_authorized" in e for e in self.audit(x)))
if __name__=="__main__":unittest.main()
