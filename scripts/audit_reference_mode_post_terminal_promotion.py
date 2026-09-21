from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROM="model/dynamics/reference_mode_post_terminal_promotion_assessment_2026_09_21.json"
SNAP="model/dynamics/sectoral_financial_positions_observed_snapshot_2026_09_21.json"
EXEC="model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_execution_assessment_2026_09_21.json"
HORIZON="model/registries/trigger_aware_monitoring_horizon_2026_09_21_post_reference_closure.json"

def load(path: str) -> dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_reference_mode_post_terminal_promotion() -> list[str]:
    e=[]
    prom=load(PROM); snap=load(SNAP); execution=load(EXEC)
    refs=load("model/dynamics/reference_modes.json")
    model=load("model/registries/model_contract.json")
    base=load("model/registries/scientific_baseline_manifest.json")
    acc=load("model/accounting/accounting_readiness_gate.json")
    historical=load("model/dynamics/reference_mode_recovery_terminal_assessment.json")
    horizon=load(HORIZON)

    if execution["scientific_gate_result"]!="PASS":
        e.append("canonical ECB QFA execution assessment is not PASS")
    if execution["workflow"]["artifact_id"]!=10646454834:
        e.append("canonical ECB QFA execution artifact changed")
    if execution["gates"]["horizontal_test_count"]!=686:
        e.append("executed per-instrument test count changed")
    if execution["gates"]["strict_bound_exceedance_count"]!=0:
        e.append("executed ECB sufficient-bound gate has an exceedance")
    if execution["gates"]["global_max_abs_residual_million_ron"]!="0.2":
        e.append("executed per-instrument residual maximum changed")
    if execution["official_fx_safety"]["pass"] is not True:
        e.append("executed ECB FX safety gate changed")

    if prom["decision"]!="PROMOTE_SECTORAL_FINANCIAL_POSITIONS_REFERENCE_MODE_ONLY_10_OF_10_REFERENCE_MODES_READY":
        e.append("promotion decision changed")
    if prom["official_threshold_execution_assessment"]!=EXEC:
        e.append("promotion does not consume the canonical executed gate")
    if prom["executed_gate_evidence"]["artifact_id"]!=10646454834:
        e.append("promotion evidence artifact changed")
    if prom["reference_modes_ready_before"]!=9 or prom["reference_modes_ready_after"]!=10:
        e.append("promotion transition is not exactly 9 to 10")

    mode=next(x for x in refs["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("sectoral financial positions not promoted")
    if mode.get("retained_snapshot")!=SNAP or mode.get("assessment")!=PROM:
        e.append("promoted mode lacks successor evidence pointers")

    d=model["dynamic_core"]
    if d["reference_mode_ready_count"]!=10 or d["reference_mode_required_count"]!=10:
        e.append("current reference readiness must be 10/10")
    if d["reference_mode_closure_ready"] is not True:
        e.append("observational reference-mode closure must be ready")
    if d["behavioural_closure_active"] is not False:
        e.append("reference-mode promotion may not activate behavioural closure")
    if d["canonical_multi_instrument_stock_initialization_ready"] is not False:
        e.append("aggregate reference mode may not complete bilateral stock initialization")
    if d["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        e.append("aggregate reference mode may not complete full Accounting Spine benchmark")

    b=base["canonical_state"]["reference_modes"]
    if b["ready_count"]!=10 or b["required_count"]!=10 or b["closure_ready"] is not True:
        e.append("baseline manifest reference readiness is not 10/10")
    if b["blockers"]!=[]:
        e.append("baseline manifest retains a current reference-mode blocker")
    if "sectoral_financial_positions" not in b["ready"]:
        e.append("baseline manifest does not list promoted mode as ready")

    current=acc["current_expected_state"]
    if current["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine complete-instrument state changed")
    if current["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        e.append("Accounting Spine benchmark changed")

    if historical["ready_reference_modes"]!=9 or historical["blocker_count"]!=1:
        e.append("historical 9/10 terminal assessment was rewritten")

    ids={x["id"] for x in horizon["horizons"]}
    if "sectoral_financial_positions_public_precision_rule" in ids:
        e.append("resolved aggregate precision trigger remains active")
    if "accounting_counterpart_topology" not in ids:
        e.append("bilateral Accounting Spine topology trigger missing")
    hd=horizon["current_disposition"]
    if hd.get("reference_mode_observability_ready")!="10/10" or hd.get("reference_mode_closure_ready") is not True:
        e.append("successor horizon does not register 10/10 closure")
    if hd.get("accounting_spine_completion_authorized") is not False:
        e.append("reference-mode closure may not authorize Accounting Spine completion")

    scope=snap["scientific_scope"]
    if scope["reference_mode_observability"] is not True:
        e.append("observed snapshot does not authorize observability")
    for key in ("bilateral_holder_by_issuer_observability","accounting_spine_completion","parameter_estimation","feedback_activation","behavioural_closure"):
        if scope[key] is not False:
            e.append(f"observed snapshot may not authorize {key}")

    effect=prom["promotion_effect"]
    for key in ("accounting_spine_is_complete","accounting_readiness_change","canonical_full_2025_stock_flow_benchmark_ready","canonical_multi_instrument_stock_initialization_ready","calibration_cycle_open","parameter_estimation_authorized","feedback_activation_authorized","behavioural_closure_active","complete_endogenous_system_dynamics_model"):
        if effect[key] is not False:
            e.append(f"promotion may not authorize {key}")
    return e

def main():
    errors=audit_reference_mode_post_terminal_promotion()
    if errors:
        raise RuntimeError("Post-terminal reference-mode promotion audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "reference_modes_ready":"10/10",
        "sectoral_financial_positions":"OBSERVED_SERIES_AVAILABLE",
        "executed_ecb_gate_tests":686,
        "strict_bound_exceedances":0,
        "max_instrument_residual_million_ron":0.2,
        "accounting_complete_stock_and_flow_instruments":["F3"],
        "behavioural_closure_active":False,
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
