from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from scripts.audit_credit_flow_to_loan_stock_boundary import REVIEW_PATH, STATUS, audit_credit_flow_to_loan_stock_boundary
ROOT=Path(__file__).resolve().parents[1]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
class CreditFlowToLoanStockBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.review=load(REVIEW_PATH)
        self.private=load("model/dynamics/private_credit_reference_assessment.json")
        self.snapshot=load("model/dynamics/private_credit_reference_snapshot.json")
        self.boundary=load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness=load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback=load("model/dynamics/feedback_registry.json")
        self.model=load("model/registries/model_contract.json")
        self.baseline=load("model/registries/scientific_baseline_manifest.json")
    def audit(self,**o):
        return audit_credit_flow_to_loan_stock_boundary(o.get("review",self.review),self.private,self.snapshot,self.boundary,self.readiness,self.feedback,self.model,self.baseline)
    def test_current_review_passes(self): self.assertEqual(self.audit(),[])
    def test_stock_change_is_not_transaction(self):
        self.assertFalse(self.review["bridge_resolution"]["stock_change_equals_credit_flow_authorized"])
    def test_reference_mapping_is_exact(self):
        stock=next(x for x in self.boundary["variables"] if x["id"]=="loan_stock")
        self.assertEqual(stock["exact_reference_mode_id"],"credit_stock")
    def test_manual_one_to_one_is_detected(self):
        m=copy.deepcopy(self.review);m["bridge_resolution"]["stock_change_equals_credit_flow_authorized"]=True
        self.assertTrue(any("stock_change_equals_credit_flow_authorized" in e for e in self.audit(review=m)))
    def test_link_status(self):
        row=next(x for x in self.readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop" and x["from"]=="credit_flow" and x["to"]=="loan_stock")
        self.assertEqual(row["readiness_status"],STATUS);self.assertFalse(row["exact_integrated_equation_ready"])
if __name__=="__main__": unittest.main()
