from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review_2026_09_21.json"
STATUS="FX_DIRECTION_KNOWN_CURRENCY_PAYMENT_AND_HEDGING_EXPOSURE_NOT_IDENTIFIED"
def load(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_fx_depreciation_to_debt_service(review,source_review,boundary,readiness,feedback,model,baseline):
 e=[]
 if review["decision"]!="DO_NOT_APPLY_EXCHANGE_RATE_MOVE_TO_AGGREGATE_EXTERNAL_DEBT_REQUIRE_CURRENCY_SPECIFIC_PAYMENT_SCHEDULE_AND_HEDGING_BOUNDARY":e.append("decision changed")
 for k,v in review["concept_boundary"].items():
  if v is not False:e.append(f"concept boundary may not authorize {k}")
 if source_review["disposition"]["mechanism_classification"]!="DEFERRED":e.append("external-FX mechanism classification changed")
 if source_review["source_boundary_findings"]["joint_currency_x_residual_maturity_by_sector_available"] is not False:e.append("joint currency/residual-maturity boundary unexpectedly available")
 if source_review["source_boundary_findings"]["hedging_positions_available"] is not False:e.append("hedging boundary unexpectedly available")
 b=review["bridge_resolution"]
 if b["status"]!=STATUS:e.append("bridge status changed")
 for k in ("aggregate_external_debt_revaluation_as_service_burden_authorized","reporting_unit_as_denomination_authorized","original_maturity_as_residual_schedule_authorized","zero_hedging_assumption_authorized","EUR_only_mapping_to_all_FX_debt_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
  if b[k] is not False:e.append(f"bridge may not authorize {k}")
 fx=next(x for x in boundary["variables"] if x["id"]=="exchange_rate_depreciation")
 burden=next(x for x in boundary["variables"] if x["id"]=="fx_debt_service_burden")
 for n in (fx,burden):
  if n.get("exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review")!=REVIEW_PATH:e.append(f"{n['id']}: review pointer missing")
  if n.get("exchange_rate_depreciation_to_fx_debt_service_burden_status")!=STATUS:e.append(f"{n['id']}: boundary status changed")
  if n["current_boundary_class"]!="UNRESOLVED":e.append(f"{n['id']}: review may not resolve node")
 if burden.get("currency_payment_hedging_boundary_ready") is not False:e.append("FX burden boundary may not be ready")
 link=next(x for x in readiness["links"] if x["loop_id"]=="external_fx_refinancing_loop" and x["from"]=="exchange_rate_depreciation")
 if link["readiness_status"]!=STATUS:e.append("link readiness changed")
 if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:e.append("link may not be ready/active")
 loop=next(x for x in feedback["loops"] if x["id"]=="external_fx_refinancing_loop")
 if loop["topology_status"]!="OPEN_CHAIN":e.append("external structure may not be closed")
 if loop.get("exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review")!=REVIEW_PATH:e.append("loop pointer missing")
 if loop.get("exchange_rate_depreciation_to_fx_debt_service_burden_status")!=STATUS:e.append("loop status changed")
 d=model["dynamic_core"]
 if d.get("exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review")!=REVIEW_PATH:e.append("model pointer missing")
 if d.get("external_fx_refinancing_next_structural_task")!="fx_debt_service_burden_to_refinancing_need_boundary_review":e.append("next external-FX task changed")
 if baseline["authority"].get("exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review")!=REVIEW_PATH:e.append("baseline authority missing")
 for k,v in review["hard_rules"].items():
  if v is not True:e.append(f"hard rule disabled: {k}")
 return e
def main():
 errors=audit_fx_depreciation_to_debt_service(load(REVIEW_PATH),load("model/calibration_validation/external_fx_refinancing_source_boundary_review.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
 if errors:raise RuntimeError("FX-depreciation to debt-service boundary audit failed:\n- "+"\n- ".join(errors))
 print(json.dumps({"status":"PASS","bridge_status":STATUS,"open_chain":True,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"fx_debt_service_burden_to_refinancing_need_boundary_review"},indent=2))
if __name__=="__main__":main()
