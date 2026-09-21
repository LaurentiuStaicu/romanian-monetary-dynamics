from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXECUTION="model/accounting/f6_oecd_counterpart_stage2_execution_assessment_2026_09_21.json"
CONTRACT="model/accounting/f6_oecd_counterpart_reopen_contract_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f6_oecd_counterpart_stage2_execution()->list[str]:
    errors=[]
    e=load(EXECUTION); c=load(CONTRACT)
    source=load("model/dynamics/sectoral_financial_positions_oecd_counterpart_discovery_assessment.json")
    rank=load("model/accounting/f6_aggregate_rank_assessment.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")

    if e["decision"]!="STAGE2_FAIL_SOURCE_RECONCILIATION_NO_NEW_EQUATIONS_NO_RANK_CHANGE":
        errors.append("F6 Stage 2 decision changed")
    if c["stage2_gate"]["reconciliation"]["tolerance_million_RON"]!="0.1":
        errors.append("F6 preregistered tolerance changed")
    for key in ("asset_liability_mirror_gate","source_S1_aggregate_consistency_gate","component_identity_gate"):
        if e[key]["tolerance_million_RON"]!="0.1":
            errors.append(f"{key} executed tolerance differs from preregistration")
    src=e["source_identity"]; disc=source["discovery_result"]
    if src["retained_workflow_artifact_id"]!=disc["artifact_id"]: errors.append("OECD artifact identity changed")
    if src["stocks_raw_sha256"]!=disc["stocks_raw_sha256"]: errors.append("OECD stock hash changed")
    if src["flows_raw_sha256"]!=disc["flows_raw_sha256"]: errors.append("OECD flow hash changed")
    if src["canonical_filtered_extraction_sha256"]!="823dbfda36fa36ec60d8be0fa5f6a445d2785445ae35109e94dd77988620621e":
        errors.append("F6 canonical extraction identity changed")
    if src["observed_maturity_code"]!="_Z":
        errors.append("F6 source maturity topology changed")
    g=e["extraction_gate"]
    if (g["stock_rows_2025_q4"],g["flow_rows_2025_q1_q4"],g["total_rows"])!=(420,1680,2100):
        errors.append("F6 source row counts changed")
    if g["required_row_duplicates"]!=0 or g["missing_required_values"]!=0 or g["nonfinite_required_values"]!=0 or g["status"]!="PASS":
        errors.append("F6 extraction gate no longer passes")

    m=e["asset_liability_mirror_gate"]
    if m["status"]!="PASS" or (m["stock_checks"],m["stock_violations"],m["stock_max_abs_residual_million_RON"])!=(112,0,"0.0"):
        errors.append("F6 stock A/L mirror result changed")
    if (m["flow_checks"],m["flow_violations"],m["flow_max_abs_residual_million_RON"])!=(112,0,"0.0"):
        errors.append("F6 flow A/L mirror result changed")

    a=e["source_S1_aggregate_consistency_gate"]
    if a["status"]!="FAIL": errors.append("F6 S1 aggregate gate must retain FAIL")
    if (a["stock_checks"],a["stock_violations"],a["stock_max_abs_residual_million_RON"])!=(154,7,"1.0"):
        errors.append("F6 stock S1 aggregate result changed")
    if (a["flow_checks"],a["flow_violations"],a["flow_max_abs_residual_million_RON"])!=(154,13,"2.0"):
        errors.append("F6 flow S1 aggregate result changed")

    comp=e["component_identity_gate"]
    if comp["status"]!="FAIL": errors.append("F6 component identity must retain FAIL")
    if (comp["stock_checks"],comp["stock_violations"],comp["stock_max_abs_residual_million_RON"])!=(60,4,"1.0"):
        errors.append("F6 stock component identity result changed")
    if (comp["annual_flow_checks"],comp["annual_flow_violations"],comp["annual_flow_max_abs_residual_million_RON"])!=(60,11,"1.0"):
        errors.append("F6 annual-flow component identity result changed")
    if (comp["quarterly_flow_checks"],comp["quarterly_flow_violations"],comp["quarterly_flow_max_abs_residual_million_RON"])!=(240,32,"1.0"):
        errors.append("F6 quarterly-flow component identity result changed")

    if e["gate_order"]["stopped_before_rank"] is not True: errors.append("F6 Stage 2 must stop before rank")
    r=e["rank_effect"]
    if r["rank_recomputation_executed"] is not False or r["rank_change"]!=0: errors.append("failed F6 Stage 2 may not change rank")
    if rank["unconditional_identification"]["stock"]["rank"]!=r["predecessor_stock_rank"] or rank["unconditional_identification"]["stock"]["nullity"]!=r["predecessor_stock_nullity"]:
        errors.append("F6 predecessor stock state changed")
    if rank["unconditional_identification"]["flow_2025"]["rank"]!=r["predecessor_flow_rank"] or rank["unconditional_identification"]["flow_2025"]["nullity"]!=r["predecessor_flow_nullity"]:
        errors.append("F6 predecessor flow state changed")
    for key in ("F6_materialization_change","benchmark_change","accounting_readiness_change","reference_mode_change","calibration_change","feedback_activation_change","behavioural_closure_change","version_change"):
        if e["scientific_effect"][key] is not False: errors.append(f"F6 failure may not authorize {key}")
    if e["provenance_rules"]["no_post_result_tolerance_relaxation"] is not True or e["provenance_rules"]["no_partial_equation_salvage_after_global_source_gate_failure"] is not True:
        errors.append("F6 failure provenance rules changed")
    f6=reopen["instruments"]["F6"]
    if f6.get("selective_reopen_execution_assessment")!=EXECUTION: errors.append("F6 registry lacks execution assessment")
    if f6.get("selective_reopen_state")!="STAGE2_EXECUTED_FAIL_SOURCE_RECONCILIATION_RETURNED_TO_HOLD":
        errors.append("F6 registry terminal state stale")
    if f6.get("current_reopen_gate_open") is not False: errors.append("F6 reopen gate must be closed")
    return errors

def main():
    errors=audit_f6_oecd_counterpart_stage2_execution()
    if errors: raise RuntimeError("F6 OECD Stage 2 execution audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","stage2_decision":"FAIL_SOURCE_RECONCILIATION","stock_S1_violations":7,"flow_S1_violations":13,"stock_component_violations":4,"quarterly_flow_component_violations":32,"rank_recomputed":False,"F6_status":"FROZEN_AGGREGATE_ONLY_PUBLIC_DATA_BOUNDARY"},indent=2))

if __name__=="__main__": main()
