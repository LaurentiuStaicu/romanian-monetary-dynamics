from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/private_demand_and_investment_to_inflationary_pressure_boundary_review_2026_09_21.json"
STATUS="MULTI_DRIVER_INFLATION_HICP_OBSERVABLE_DEMAND_CONTRIBUTION_NOT_IDENTIFIED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_private_demand_to_inflation(review,fx_boundary,fx_selection,boundary,readiness,feedback,reference_modes,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_EQUATE_PRIVATE_DEMAND_OR_INVESTMENT_WITH_INFLATIONARY_PRESSURE_KEEP_HICP_OBSERVATION_AND_MULTI_DRIVER_INFLATION_IDENTIFICATION_DISTINCT":e.append("decision changed")
 for k,v in review["concept_boundary"].items():
  if v is not False:e.append(f"concept boundary may not authorize {k}")
 if fx_boundary["primary_sources"]["inflation"]["concept"]!="Romania all-items HICP under ECOICOP version 2":e.append("HICP evidence boundary changed")
 if fx_selection["selection_verdict"]!="FAIL_BEFORE_HOLDOUT" or fx_selection["final_evaluation_opened"] is not False:e.append("FX inflation selection state changed")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("bridge status changed")
 for k in ("direct_demand_to_inflation_identity_authorized","HICP_as_demand_pressure_state_authorized","output_gap_proxy_inference_authorized","omit_supply_controls_authorized","reuse_failed_FX_form_authorized","add_core_inflation_reference_mode_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 demand=next(x for x in boundary["variables"] if x["id"]=="private_demand_and_investment")
 infl=next(x for x in boundary["variables"] if x["id"]=="inflationary_pressure")
 for n in (demand,infl):
  if n.get("private_demand_and_investment_to_inflationary_pressure_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review pointer missing")
  if n.get("private_demand_and_investment_to_inflationary_pressure_status")!=STATUS:e.append(f"{n['id']}: boundary status changed")
  if n["current_boundary_class"]!="UNRESOLVED":e.append(f"{n['id']}: review may not resolve node")
 if infl.get("exact_reference_mode_id") is not None:e.append("inflationary-pressure node may not gain exact reference mode")
 if infl.get("core_reference_mode_promotion_authorized") is not False:e.append("core inflation reference-mode promotion may not be authorized")
 if any(x["id"]=="inflationary_pressure" for x in reference_modes["modes"]):e.append("inflationary_pressure may not be added as reference mode")
 link=next(x for x in readiness["links"] if x["loop_id"]=="monetary_credit_transmission_loop" and x["from"]=="private_demand_and_investment" and x["to"]=="inflationary_pressure")
 if link["readiness_status"]!=STATUS:e.append("link readiness changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not be ready/active")
 loop=next(x for x in feedback["loops"] if x["id"]=="monetary_credit_transmission_loop")
 if loop.get("private_demand_and_investment_to_inflationary_pressure_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 if loop.get("private_demand_and_investment_to_inflationary_pressure_status")!=STATUS:e.append("loop status changed")
 d=model["dynamic_core"]
 if d.get("private_demand_and_investment_to_inflationary_pressure_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("monetary_credit_transmission_next_structural_task")!="monetary_credit_transmission_loop_terminal_assessment":e.append("next monetary task changed")
 if baseline["authority"].get("private_demand_and_investment_to_inflationary_pressure_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_private_demand_to_inflation(load(REVIEW_PATH),load("model/calibration_validation/fx_inflation_pass_through_source_boundary_review.json"),load("model/calibration_validation/fx_inflation_structural_selection_result.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/dynamics/reference_modes.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("Private-demand to inflation boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"core_inflation_reference_mode_added":False,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"monetary_credit_transmission_loop_terminal_assessment"},indent=2))
if __name__=="__main__":main()
