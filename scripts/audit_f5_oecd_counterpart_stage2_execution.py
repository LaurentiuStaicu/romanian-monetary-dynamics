from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = "model/accounting/f5_oecd_counterpart_stage2_execution_assessment_2026_09_21.json"
CONTRACT = "model/accounting/f5_oecd_counterpart_reopen_contract_2026_09_21.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_f5_oecd_counterpart_stage2_execution() -> list[str]:
    errors: list[str] = []
    e = load(EXECUTION)
    c = load(CONTRACT)
    source = load("model/dynamics/sectoral_financial_positions_oecd_counterpart_discovery_assessment.json")
    rank = load("model/accounting/f5_component_aware_rank_assessment.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")

    if e["decision"] != "STAGE2_FAIL_SOURCE_AGGREGATE_RECONCILIATION_NO_NEW_EQUATIONS_NO_RANK_CHANGE":
        errors.append("F5 Stage 2 execution decision changed")
    if c["stage2_gate"]["reconciliation"]["tolerance_million_RON"] != "0.1":
        errors.append("preregistered F5 Stage 2 tolerance changed")
    if e["source_aggregate_consistency_gate"]["tolerance_million_RON"] != "0.1":
        errors.append("executed tolerance differs from preregistration")

    src=e["source_identity"]
    disc=source["discovery_result"]
    if src["retained_workflow_artifact_id"] != disc["artifact_id"]:
        errors.append("OECD counterpart artifact identity changed")
    if src["stocks_raw_sha256"] != disc["stocks_raw_sha256"]:
        errors.append("OECD stock raw hash changed")
    if src["flows_raw_sha256"] != disc["flows_raw_sha256"]:
        errors.append("OECD flow raw hash changed")
    if src["canonical_filtered_extraction_sha256"] != "8ccd1b695395d3a88e4809b768a7cba1199cda2029070c6598edb8dd2389f9dc":
        errors.append("canonical filtered extraction identity changed")

    g=e["extraction_gate"]
    if (g["stock_rows_2025_q4"],g["flow_rows_2025_q1_q4"],g["total_rows"]) != (120,480,600):
        errors.append("Stage 2 source row counts changed")
    if g["required_row_duplicates"] != 0 or g["missing_required_values"] != 0 or g["nonfinite_required_values"] != 0:
        errors.append("Stage 2 extraction gate no longer passes")

    m=e["asset_liability_mirror_gate"]
    if m["status"] != "PASS":
        errors.append("A/L mirror gate no longer passes")
    if (m["stock_violations"],m["flow_violations"]) != (0,0):
        errors.append("A/L mirror violations changed")
    if (m["stock_max_abs_residual_million_RON"],m["flow_max_abs_residual_million_RON"]) != ("0.0","0.0"):
        errors.append("A/L mirror residual changed")

    a=e["source_aggregate_consistency_gate"]
    if a["status"] != "FAIL":
        errors.append("aggregate-consistency gate must retain FAIL")
    if (a["stock_checks"],a["stock_violations"],a["stock_max_abs_residual_million_RON"]) != (44,16,"1.0"):
        errors.append("stock aggregate-consistency result changed")
    if (a["flow_checks"],a["flow_violations"],a["flow_max_abs_residual_million_RON"]) != (44,24,"3.0"):
        errors.append("flow aggregate-consistency result changed")

    if e["gate_order"]["stopped_before_rank"] is not True:
        errors.append("Stage 2 must stop before rank after source-gate failure")
    r=e["rank_effect"]
    if r["rank_recomputation_executed"] is not False or r["rank_change"] != 0:
        errors.append("failed Stage 2 may not alter rank")
    if rank["exact_rank"]["stock"]["rank"] != r["predecessor_stock_rank"]:
        errors.append("predecessor stock rank changed")
    if rank["exact_rank"]["flow_2025"]["rank"] != r["predecessor_flow_rank"]:
        errors.append("predecessor flow rank changed")
    if rank["exact_rank"]["stock"]["nullity"] != r["predecessor_stock_nullity"]:
        errors.append("predecessor stock nullity changed")
    if rank["exact_rank"]["flow_2025"]["nullity"] != r["predecessor_flow_nullity"]:
        errors.append("predecessor flow nullity changed")

    for key in ("F5_materialization_change","benchmark_change","accounting_readiness_change","reference_mode_change","calibration_change","feedback_activation_change","behavioural_closure_change","version_change"):
        if e["scientific_effect"][key] is not False:
            errors.append(f"Stage 2 failure may not authorize {key}")

    if e["provenance_rules"]["failed_0_1_million_RON_gate_is_immutable"] is not True:
        errors.append("failed source gate must remain immutable")
    if e["provenance_rules"]["no_post_result_tolerance_relaxation"] is not True:
        errors.append("post-result tolerance relaxation must remain prohibited")
    if e["provenance_rules"]["no_partial_equation_salvage_after_global_gate_failure"] is not True:
        errors.append("failed global source gate may not be partially salvaged")

    f5=reopen["instruments"]["F5"]
    if f5.get("selective_reopen_execution_assessment") != EXECUTION:
        errors.append("F5 registry does not register Stage 2 execution")
    if f5.get("selective_reopen_state") != "STAGE2_EXECUTED_FAIL_SOURCE_AGGREGATE_RECONCILIATION_RETURNED_TO_HOLD":
        errors.append("F5 registry Stage 2 terminal state is stale")
    if f5.get("current_reopen_gate_open") is not False:
        errors.append("F5 reopen gate must be closed after Stage 2 terminal failure")
    return errors


def main() -> None:
    errors=audit_f5_oecd_counterpart_stage2_execution()
    if errors:
        raise RuntimeError("F5 OECD Stage 2 execution audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "stage2_decision":"FAIL_SOURCE_AGGREGATE_RECONCILIATION",
        "stock_aggregate_violations":16,
        "flow_aggregate_violations":24,
        "max_stock_residual_million_RON":1.0,
        "max_flow_residual_million_RON":3.0,
        "rank_recomputed":False,
        "F5_status":"FROZEN_AT_PUBLIC_DATA_BOUNDARY"
    },indent=2))


if __name__=="__main__":
    main()
