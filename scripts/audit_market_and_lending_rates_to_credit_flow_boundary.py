from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/market_and_lending_rates_to_credit_flow_boundary_review_2026_09_21.json"
STATUS="RATE_PRICE_AND_CREDIT_TRANSACTION_BOUNDARIES_DISTINCT_JOINT_DETERMINATION_UNRESOLVED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_rates_to_credit_flow(review,private_credit,aggregate_review,boundary,readiness,feedback,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_MAP_LENDING_RATE_ONE_TO_ONE_TO_CREDIT_FLOW_KEEP_PRICE_NEW_BUSINESS_VOLUME_AND_BSI_TRANSACTION_CONCEPTS_DISTINCT":e.append("decision changed")
 for k,v in review["concept_boundary"].items():
  if v is not False:e.append(f"concept boundary may not authorize {k}")
 if private_credit["verdict"]!="PROMOTE_BOTH_TO_OBSERVED_SERIES_AVAILABLE":e.append("credit-flow observed reference changed")
 if aggregate_review["scientific_boundary_decisions"]["aggregate_single_equation_not_yet_eligible_for_calibration"] is not True:e.append("aggregate bank-credit gate unexpectedly opened")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("bridge status changed")
 for k in ("direct_rate_to_credit_flow_identity_authorized","MIR_new_business_volume_substitution_authorized","demand_elasticity_inference_authorized","supply_response_inference_authorized","cross_sector_rate_mapping_authorized","outstanding_rate_substitution_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 rates=next(x for x in boundary["variables"] if x["id"]=="market_and_lending_rates")
 flow=next(x for x in boundary["variables"] if x["id"]=="credit_flow")
 for n in (rates,flow):
  if n.get("market_and_lending_rates_to_credit_flow_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review pointer missing")
  if n.get("market_and_lending_rates_to_credit_flow_status")!=STATUS:e.append(f"{n['id']}: boundary status changed")
 if rates["current_boundary_class"]!="UNRESOLVED" or flow["current_boundary_class"]!="UNRESOLVED":e.append("review may not resolve rate/flow nodes")
 if flow.get("exact_reference_mode_id")!="credit_flow":e.append("credit-flow reference mapping changed")
 if flow.get("rate_to_flow_mapping_ready") is not False:e.append("rate-to-flow mapping may not be ready")
 link=next(x for x in readiness["links"] if x["loop_id"]=="monetary_credit_transmission_loop" and x["from"]=="market_and_lending_rates" and x["to"]=="credit_flow")
 if link["readiness_status"]!=STATUS:e.append("link readiness status changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not be exact-ready or active")
 loop=next(x for x in feedback["loops"] if x["id"]=="monetary_credit_transmission_loop")
 if loop.get("market_and_lending_rates_to_credit_flow_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 if loop.get("market_and_lending_rates_to_credit_flow_status")!=STATUS:e.append("loop status changed")
 if loop["quantitatively_active"] is not False:e.append("loop may not activate")
 d=model["dynamic_core"]
 if d.get("market_and_lending_rates_to_credit_flow_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("monetary_credit_transmission_next_structural_task")!="monetary_credit_transmission_loop_evidence_triggered_hold":e.append("next monetary task changed")
 if baseline["authority"].get("market_and_lending_rates_to_credit_flow_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_rates_to_credit_flow(load(REVIEW_PATH),load("model/dynamics/private_credit_reference_assessment.json"),load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("Rates-to-credit-flow boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"monetary_credit_transmission_loop_evidence_triggered_hold"},indent=2))
if __name__=="__main__":main()
