from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/inflationary_pressure_to_policy_rate_boundary_review_2026_09_21.json"
STATUS="POLICY_RATE_OBSERVED_FORCING_REACTION_FUNCTION_MEASUREMENT_AND_IDENTIFICATION_BLOCKED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_inflation_to_policy_rate(review,reaction,reference_modes,boundary,readiness,feedback,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_ENDOGENIZE_POLICY_RATE_FROM_INFLATION_PRESSURE_KEEP_POLICY_RATE_OBSERVED_UNTIL_REAL_TIME_REACTION_FUNCTION_BOUNDARY_IS_IDENTIFIED":e.append("decision changed")
 for k,v in review["concept_boundary"].items():
  if v is not False:e.append(f"concept boundary may not authorize {k}")
 if reaction["disposition"]["observed_policy_rate_remains_exogenous"] is not True:e.append("policy-rate exogeneity changed")
 if reaction["disposition"]["estimation_or_refit_allowed"] is not False or reaction["disposition"]["policy_rule_activation"] is not False:e.append("reaction-function gate unexpectedly opened")
 rm=next(x for x in reference_modes["modes"] if x["id"]=="policy_rate")
 if rm["current_endogeneity"]!="EXOGENOUS_OBSERVED_INPUT":e.append("policy-rate reference endogeneity changed")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("bridge status changed")
 for k in ("direct_inflation_to_policy_rate_identity_authorized","Taylor_rule_estimation_authorized","qualitative_expectations_conversion_authorized","revised_gap_backfill_authorized","chart_digitisation_authorized","policy_rate_endogenization_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 infl=next(x for x in boundary["variables"] if x["id"]=="inflationary_pressure")
 policy=next(x for x in boundary["variables"] if x["id"]=="policy_rate")
 for n in (infl,policy):
  if n.get("inflationary_pressure_to_policy_rate_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review pointer missing")
  if n.get("inflationary_pressure_to_policy_rate_status")!=STATUS:e.append(f"{n['id']}: boundary status changed")
 if infl["current_boundary_class"]!="UNRESOLVED":e.append("inflation node may not resolve")
 if policy["current_boundary_class"]!="OBSERVED_FORCING":e.append("policy rate must remain observed forcing")
 if policy.get("endogenous_reaction_function_ready") is not False:e.append("policy reaction may not be ready")
 link=next(x for x in readiness["links"] if x["loop_id"]=="monetary_credit_transmission_loop" and x["from"]=="inflationary_pressure" and x["to"]=="policy_rate")
 if link["readiness_status"]!=STATUS:e.append("link readiness changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not be ready/active")
 loop=next(x for x in feedback["loops"] if x["id"]=="monetary_credit_transmission_loop")
 if loop.get("inflationary_pressure_to_policy_rate_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 if loop.get("inflationary_pressure_to_policy_rate_status")!=STATUS:e.append("loop status changed")
 d=model["dynamic_core"]
 if d.get("inflationary_pressure_to_policy_rate_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("monetary_credit_transmission_next_structural_task")!="monetary_credit_transmission_loop_terminal_assessment":e.append("next monetary task changed")
 if baseline["authority"].get("inflationary_pressure_to_policy_rate_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_inflation_to_policy_rate(load(REVIEW_PATH),load("model/calibration_validation/monetary_policy_reaction_source_screening.json"),load("model/dynamics/reference_modes.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("Inflation-to-policy-rate boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"policy_rate_endogenous":False,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"monetary_credit_transmission_loop_terminal_assessment"},indent=2))
if __name__=="__main__":main()
