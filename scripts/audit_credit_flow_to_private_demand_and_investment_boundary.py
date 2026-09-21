from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/credit_flow_to_private_demand_and_investment_boundary_review_2026_09_21.json"
STATUS="FINANCING_FLOW_PURPOSES_MULTIPLE_PRIVATE_DEMAND_AND_INVESTMENT_MAPPING_UNIDENTIFIED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_credit_flow_to_private_demand(review,private_credit,household,investment,boundary,readiness,feedback,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_MAP_AGGREGATE_CREDIT_FLOW_ONE_TO_ONE_TO_PRIVATE_CONSUMPTION_OR_INVESTMENT_KEEP_FINANCING_PURPOSES_AND_EXPENDITURE_CONCEPTS_DISTINCT":e.append("decision changed")
 for k,v in review["concept_boundary"].items():
  if v is not False:e.append(f"concept boundary may not authorize {k}")
 if private_credit["verdict"]!="PROMOTE_BOTH_TO_OBSERVED_SERIES_AVAILABLE":e.append("private-credit reference changed")
 if household["source_admissibility"]["registered_full_form_admissible"] is not False:e.append("household form unexpectedly admissible")
 if investment["source_admissibility"]["registered_full_form_admissible"] is not False:e.append("investment form unexpectedly admissible")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("bridge status changed")
 for k in ("direct_credit_to_consumption_mapping_authorized","direct_credit_to_investment_mapping_authorized","housing_credit_as_consumption_authorized","NFC_credit_as_GFCF_authorized","refinancing_as_new_demand_authorized","synthetic_purpose_allocation_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 flow=next(x for x in boundary["variables"] if x["id"]=="credit_flow")
 demand=next(x for x in boundary["variables"] if x["id"]=="private_demand_and_investment")
 for n in (flow,demand):
  if n.get("credit_flow_to_private_demand_and_investment_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review pointer missing")
  if n.get("credit_flow_to_private_demand_and_investment_status")!=STATUS:e.append(f"{n['id']}: boundary status changed")
 if flow["current_boundary_class"]!="UNRESOLVED" or demand["current_boundary_class"]!="UNRESOLVED":e.append("review may not resolve nodes")
 if flow.get("exact_reference_mode_id")!="credit_flow":e.append("credit-flow reference changed")
 if demand.get("aggregate_combined_target_selected") is not False:e.append("combined private-demand target may not be selected")
 link=next(x for x in readiness["links"] if x["loop_id"]=="monetary_credit_transmission_loop" and x["from"]=="credit_flow" and x["to"]=="private_demand_and_investment")
 if link["readiness_status"]!=STATUS:e.append("link readiness changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not be ready/active")
 loop=next(x for x in feedback["loops"] if x["id"]=="monetary_credit_transmission_loop")
 if loop.get("credit_flow_to_private_demand_and_investment_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 if loop.get("credit_flow_to_private_demand_and_investment_status")!=STATUS:e.append("loop status changed")
 d=model["dynamic_core"]
 if d.get("credit_flow_to_private_demand_and_investment_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("monetary_credit_transmission_next_structural_task")!="private_demand_and_investment_to_inflationary_pressure_boundary_review":e.append("next monetary task changed")
 if baseline["authority"].get("credit_flow_to_private_demand_and_investment_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_credit_flow_to_private_demand(load(REVIEW_PATH),load("model/dynamics/private_credit_reference_assessment.json"),load("model/calibration_validation/household_consumption_source_boundary_review.json"),load("model/calibration_validation/corporate_investment_source_boundary_review.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("Credit-flow to private-demand boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"private_demand_and_investment_to_inflationary_pressure_boundary_review"},indent=2))
if __name__=="__main__":main()
