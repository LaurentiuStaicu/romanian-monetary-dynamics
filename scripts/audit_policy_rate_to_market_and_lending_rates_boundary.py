from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/policy_rate_to_market_and_lending_rates_boundary_review_2026_09_21.json"
STATUS="TARGET_SPECIFIC_PASS_THROUGH_CANDIDATE_AVAILABLE_GENERIC_RATE_NODE_UNRESOLVED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_policy_rate_to_rates(review,validation,prospective,boundary,readiness,feedback,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_PROMOTE_HOUSEHOLD_HOUSING_PASS_THROUGH_TO_GENERIC_MARKET_AND_LENDING_RATES_KEEP_TARGET_SPECIFIC_CANDIDATE_ONLY":e.append("decision changed")
 if validation["mechanisms_tested"][0]["final_verdict"]!="CANDIDATE":e.append("household candidate verdict changed")
 if prospective["identification_gate"]["status"]!="WAIT_FOR_NEW_POLICY_RATE_EVENT":e.append("prospective gate changed")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("status changed")
 for k in ("generic_rate_node_mapping_authorized","nfc_form_inference_authorized","market_rate_aggregation_authorized","outstanding_rate_substitution_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 p=next(x for x in boundary["variables"] if x["id"]=="policy_rate")
 r=next(x for x in boundary["variables"] if x["id"]=="market_and_lending_rates")
 if p["current_boundary_class"]!="OBSERVED_FORCING":e.append("policy rate forcing changed")
 if r["current_boundary_class"]!="UNRESOLVED":e.append("generic rate node may not resolve")
 for n in (p,r):
  if n.get("policy_rate_to_market_and_lending_rates_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review missing")
  if n.get("policy_rate_to_market_and_lending_rates_status")!=STATUS:e.append(f"{n['id']}: status changed")
 link=next(x for x in readiness["links"] if x["loop_id"]=="monetary_credit_transmission_loop" and x["from"]=="policy_rate")
 if link["readiness_status"]!="PARTIAL_TARGET_SPECIFIC_FORM_NOT_INTEGRATED":e.append("canonical target-specific readiness status changed")
 if link.get("policy_rate_to_market_and_lending_rates_boundary_status")!=STATUS:e.append("link boundary-review status changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not activate")
 loop=next(x for x in feedback["loops"] if x["id"]=="monetary_credit_transmission_loop")
 if loop.get("policy_rate_to_market_and_lending_rates_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 d=model["dynamic_core"]
 if d.get("policy_rate_to_market_and_lending_rates_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("monetary_credit_transmission_next_structural_task")!="monetary_credit_transmission_loop_terminal_assessment":e.append("next task changed")
 if baseline["authority"].get("policy_rate_to_market_and_lending_rates_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_policy_rate_to_rates(load(REVIEW_PATH),load("model/calibration_validation/validation_recovery_disposition.json"),load("model/calibration_validation/prospective_monetary_confirmation_status.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("Policy-rate to rates boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"generic_rate_node_resolved":False,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"monetary_credit_transmission_loop_terminal_assessment"},indent=2))
if __name__=="__main__":main()
