from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOL="model/dynamics/sectoral_financial_positions_ecb_official_tolerance_assessment_2026_09_21.json"
PROM="model/dynamics/reference_mode_post_terminal_promotion_assessment_2026_09_21.json"
SNAP="model/dynamics/sectoral_financial_positions_observed_snapshot_2026_09_21.json"
AUDIT_CSV="data/provenance/sectoral_financial_positions_ecb_tolerance_instrument_audit_2026_09_21.csv"

def load(p: str) -> dict:
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def audit_reference_mode_post_terminal_promotion() -> list[str]:
    e=[]
    tol=load(TOL); prom=load(PROM); snap=load(SNAP)
    refs=load("model/dynamics/reference_modes.json")
    model=load("model/registries/model_contract.json")
    base=load("model/registries/scientific_baseline_manifest.json")
    acc=load("model/accounting/accounting_readiness_gate.json")
    historical=load("model/dynamics/reference_mode_recovery_terminal_assessment.json")

    if tol["decision"]!="PASS_OFFICIAL_ECB_NATIONAL_QFA_INTERNAL_CONSISTENCY_TOLERANCE_REFERENCE_MODE_PROMOTION_AUTHORIZED":
        e.append("official-tolerance decision changed")
    rule=tol["official_rule"]
    if rule["threshold_eur_million"]!="10":
        e.append("ECB national-QFA tolerance changed")
    if "horizontal consistency by financial instrument" not in rule["section"].lower():
        e.append("ECB tolerance is not anchored to instrument-level horizontal consistency")
    if tol["exact_decimal_instrument_audit"]["global_max_abs_residual_million_ron"]!="0.2":
        e.append("instrument-level residual maximum changed")
    if tol["currency_unit_adjudication"]["threshold_breach_would_require_eur_ron_below"]!="0.02":
        e.append("currency robustness boundary changed")
    if tol["adjudication"]["prior_failed_gate_rewritten"] is not False:
        e.append("historical 0.1m gate may not be rewritten")

    with (ROOT/AUDIT_CSV).open(encoding="utf-8",newline="") as h:
        rows=list(csv.DictReader(h))
    if len(rows)!=14:
        e.append(f"instrument tolerance audit must contain 14 stock/flow-instrument rows, got {len(rows)}")
    if {r["instrument"] for r in rows}!={"F2","F3","F4","F5","F6","F7","F8"}:
        e.append("instrument tolerance audit scope changed")
    if {r["measure"] for r in rows}!={"stock","flow"}:
        e.append("stock/flow audit scope changed")
    if any(float(r["max_abs_residual_million_ron"])>0.2 for r in rows):
        e.append("instrument residual exceeds retained 0.2m RON maximum")
    if any(r["result"]!="PASS" for r in rows):
        e.append("an instrument-level official-tolerance row does not pass")

    mode=next(x for x in refs["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("sectoral financial positions not promoted")
    if mode.get("retained_snapshot")!=SNAP or mode.get("assessment")!=PROM:
        e.append("promoted mode lacks successor evidence pointers")

    d=model["dynamic_core"]
    if d["reference_mode_ready_count"]!=10 or d["reference_mode_required_count"]!=10:
        e.append("reference readiness must be 10/10")
    if d["reference_mode_closure_ready"] is not True:
        e.append("reference-mode observational closure must be ready")
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
        e.append("baseline manifest retains a reference-mode blocker")
    if "sectoral_financial_positions" not in b["ready"]:
        e.append("baseline manifest does not list promoted mode as ready")

    current=acc["current_expected_state"]
    if current["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine complete-instrument state changed")
    if current["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        e.append("Accounting Spine benchmark changed")

    # Historical 9/10 terminal assessment remains immutable provenance.
    if historical["ready_reference_modes"]!=9 or historical["blocker_count"]!=1:
        e.append("historical 9/10 terminal assessment was rewritten")

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
        "official_ecb_tolerance_eur_million":10,
        "max_instrument_residual_million_ron":0.2,
        "accounting_complete_stock_and_flow_instruments":["F3"],
        "behavioural_closure_active":False,
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
