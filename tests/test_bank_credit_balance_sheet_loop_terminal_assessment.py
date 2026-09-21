from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from scripts.audit_bank_credit_balance_sheet_loop_terminal_assessment import ASSESSMENT_PATH,HOLD_ID,STATUS,audit_bank_credit_loop_terminal
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
class BankCreditLoopTerminalTests(unittest.TestCase):
    def setUp(self):
        self.a=load(ASSESSMENT_PATH);self.feedback=load("model/dynamics/feedback_registry.json");self.readiness=load("model/dynamics/feedback_link_readiness_registry.json");self.boundary=load("model/dynamics/feedback_variable_boundary_registry.json");self.criteria=load("model/dynamics/feedback_activation_criteria_matrix.json");self.delays=load("model/dynamics/delay_evidence_registry.json");self.mechanisms=load("model/empirical_dynamics/mechanism_registry.json");self.aggregate=load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json");self.risk=load("model/calibration_validation/credit_risk_npl_source_boundary_review.json");self.model=load("model/registries/model_contract.json");self.baseline=load("model/registries/scientific_baseline_manifest.json")
    def audit(self,a=None):return audit_bank_credit_loop_terminal(a or self.a,self.feedback,self.readiness,self.boundary,self.criteria,self.delays,self.mechanisms,self.aggregate,self.risk,self.model,self.baseline)
    def test_current_terminal_passes(self):self.assertEqual(self.audit(),[])
    def test_four_links_not_ready(self):
        rows=[x for x in self.readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop"];self.assertEqual(len(rows),4);self.assertTrue(all(not x["exact_integrated_equation_ready"] for x in rows))
    def test_hold_state(self):self.assertEqual(self.a["decision"],STATUS);self.assertEqual(self.a["next_state"]["id"],HOLD_ID);self.assertIsNone(self.a["disposition"]["active_empirical_task"])
    def test_no_unchanged_source_polling(self):self.assertFalse(self.a["next_state"]["may_poll_unchanged_sources"])
    def test_manual_activation_detected(self):
        m=copy.deepcopy(self.a);m["disposition"]["feedback_activation_authorized"]=True;self.assertTrue(any("feedback_activation_authorized" in e for e in self.audit(m)))
if __name__=="__main__":unittest.main()
