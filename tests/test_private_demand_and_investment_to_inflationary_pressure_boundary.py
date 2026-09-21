from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_private_demand_and_investment_to_inflationary_pressure_boundary import REVIEW_PATH,STATUS,audit_private_demand_to_inflation
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class PrivateDemandToInflationTests(unittest.TestCase):
 def setUp(self):
  self.r=load(REVIEW_PATH);self.fx=load("model/calibration_validation/fx_inflation_pass_through_source_boundary_review.json");self.sel=load("model/calibration_validation/fx_inflation_structural_selection_result.json");self.b=load("model/dynamics/feedback_variable_boundary_registry.json");self.l=load("model/dynamics/feedback_link_readiness_registry.json");self.f=load("model/dynamics/feedback_registry.json");self.rm=load("model/dynamics/reference_modes.json");self.m=load("model/registries/model_contract.json");self.s=load("model/registries/scientific_baseline_manifest.json")
 def audit(self,r=None):return audit_private_demand_to_inflation(r or self.r,self.fx,self.sel,self.b,self.l,self.f,self.rm,self.m,self.s)
 def test_current(self):self.assertEqual(self.audit(),[])
 def test_no_core_inflation_reference_mode(self):self.assertFalse(self.r["bridge_resolution"]["add_core_inflation_reference_mode_authorized"]);self.assertFalse(any(x["id"]=="inflationary_pressure" for x in self.rm["modes"]))
 def test_no_demand_identity(self):self.assertFalse(self.r["bridge_resolution"]["direct_demand_to_inflation_identity_authorized"])
 def test_manual_reference_promotion_detected(self):
  x=copy.deepcopy(self.r);x["bridge_resolution"]["add_core_inflation_reference_mode_authorized"]=True;self.assertTrue(any("add_core_inflation_reference_mode_authorized" in e for e in self.audit(x)))
if __name__=="__main__":unittest.main()
