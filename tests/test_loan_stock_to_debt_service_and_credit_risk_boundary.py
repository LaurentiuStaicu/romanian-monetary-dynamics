from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_loan_stock_to_debt_service_and_credit_risk_boundary import REVIEW_PATH,STATUS,audit_loan_stock_to_debt_service_and_credit_risk_boundary
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class LoanStockToRiskBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.review=load(REVIEW_PATH);self.risk_review=load("model/calibration_validation/credit_risk_npl_source_boundary_review.json");self.boundary=load("model/dynamics/feedback_variable_boundary_registry.json");self.readiness=load("model/dynamics/feedback_link_readiness_registry.json");self.feedback=load("model/dynamics/feedback_registry.json");self.model=load("model/registries/model_contract.json");self.baseline=load("model/registries/scientific_baseline_manifest.json")
    def audit(self,review=None): return audit_loan_stock_to_debt_service_and_credit_risk_boundary(review or self.review,self.risk_review,self.boundary,self.readiness,self.feedback,self.model,self.baseline)
    def test_current_review_passes(self): self.assertEqual(self.audit(),[])
    def test_stock_is_not_debt_service(self): self.assertFalse(self.review["bridge_resolution"]["direct_loan_stock_to_debt_service_mapping_authorized"])
    def test_stock_times_rate_shortcut_blocked(self): self.assertFalse(self.review["bridge_resolution"]["stock_times_lending_rate_as_debt_service_authorized"])
    def test_combined_node_has_no_exact_reference_mode(self):
        node=next(x for x in self.boundary["variables"] if x["id"]=="debt_service_and_credit_risk");self.assertIsNone(node["exact_reference_mode_id"])
    def test_manual_proxy_authorization_detected(self):
        m=copy.deepcopy(self.review);m["bridge_resolution"]["direct_loan_stock_to_credit_risk_mapping_authorized"]=True
        self.assertTrue(any("direct_loan_stock_to_credit_risk_mapping_authorized" in e for e in self.audit(m)))
if __name__=="__main__": unittest.main()
