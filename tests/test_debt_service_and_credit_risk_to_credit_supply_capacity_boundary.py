from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_debt_service_and_credit_risk_to_credit_supply_capacity_boundary import REVIEW_PATH,STATUS,audit_risk_to_credit_supply_capacity_boundary
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class RiskToCreditSupplyCapacityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.review=load(REVIEW_PATH);self.prudential=load("model/calibration_validation/bank_credit_prudential_population_boundary_review.json");self.aggregate=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json");self.boundary=load("model/dynamics/feedback_variable_boundary_registry.json");self.readiness=load("model/dynamics/feedback_link_readiness_registry.json");self.feedback=load("model/dynamics/feedback_registry.json");self.model=load("model/registries/model_contract.json");self.baseline=load("model/registries/scientific_baseline_manifest.json")
    def audit(self,review=None): return audit_risk_to_credit_supply_capacity_boundary(review or self.review,self.prudential,self.aggregate,self.boundary,self.readiness,self.feedback,self.model,self.baseline)
    def test_current_review_passes(self): self.assertEqual(self.audit(),[])
    def test_npl_not_capacity(self): self.assertFalse(self.review["bridge_resolution"]["direct_NPL_to_capacity_mapping_authorized"])
    def test_bls_standards_not_capacity_identity(self): self.assertFalse(self.review["bridge_resolution"]["BLS_standards_equals_capacity_authorized"])
    def test_capacity_has_no_exact_reference_mode(self):
        n=next(x for x in self.boundary["variables"] if x["id"]=="credit_supply_capacity");self.assertIsNone(n["exact_reference_mode_id"]);self.assertFalse(n["scalar_capacity_measure_selected"])
    def test_manual_capacity_index_detected(self):
        m=copy.deepcopy(self.review);m["bridge_resolution"]["synthetic_prudential_capacity_index_authorized"]=True
        self.assertTrue(any("synthetic_prudential_capacity_index_authorized" in e for e in self.audit(m)))
if __name__=="__main__": unittest.main()
