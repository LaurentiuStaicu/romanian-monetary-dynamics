from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_credit_supply_capacity_to_credit_flow_boundary import REVIEW_PATH,STATUS,audit_credit_supply_capacity_to_credit_flow_boundary
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class CreditSupplyCapacityToCreditFlowBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.review=load(REVIEW_PATH);self.private=load("model/dynamics/private_credit_reference_assessment.json");self.aggregate=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json");self.boundary=load("model/dynamics/feedback_variable_boundary_registry.json");self.readiness=load("model/dynamics/feedback_link_readiness_registry.json");self.feedback=load("model/dynamics/feedback_registry.json");self.model=load("model/registries/model_contract.json");self.baseline=load("model/registries/scientific_baseline_manifest.json")
    def audit(self,review=None): return audit_credit_supply_capacity_to_credit_flow_boundary(review or self.review,self.private,self.aggregate,self.boundary,self.readiness,self.feedback,self.model,self.baseline)
    def test_current_review_passes(self): self.assertEqual(self.audit(),[])
    def test_realized_flow_not_supply_capacity(self): self.assertFalse(self.review["bridge_resolution"]["capacity_equals_realized_flow_authorized"])
    def test_credit_flow_not_supply_only(self): self.assertFalse(self.review["bridge_resolution"]["supply_only_interpretation_of_credit_flow_authorized"])
    def test_demand_not_inferred_from_flow(self): self.assertFalse(self.review["bridge_resolution"]["infer_demand_from_credit_flow_authorized"])
    def test_manual_supply_only_mapping_detected(self):
        m=copy.deepcopy(self.review);m["bridge_resolution"]["supply_only_interpretation_of_credit_flow_authorized"]=True
        self.assertTrue(any("supply_only_interpretation_of_credit_flow_authorized" in e for e in self.audit(m)))
if __name__=="__main__": unittest.main()
