from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GATE=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_assessment_2026_09_21.json"
PROMOTION=ROOT/"model/dynamics/reference_mode_recovery_successor_assessment_2026_09_21.json"
SERIES=ROOT/"data/processed/sectoral_financial_positions_oecd_ecb_qfa_2014Q1_2026Q1.csv"
REFS=ROOT/"model/dynamics/reference_modes.json"
MODEL=ROOT/"model/registries/model_contract.json"
BASE=ROOT/"model/registries/scientific_baseline_manifest.json"
HIST=ROOT/"model/dynamics/reference_mode_recovery_terminal_assessment.json"
ACCOUNTING=ROOT/"model/accounting/accounting_readiness_gate.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))

def audit_reference_mode_promotion_10_of_10():
    e=[]
    g=load(GATE); p=load(PROMOTION); refs=load(REFS); model=load(MODEL); base=load(BASE); hist=load(HIST); acc=load(ACCOUNTING)

    if g["decision"]!="PASS_ECB_QFA_MATERIALITY_GATE_REFERENCE_MODE_PROMOTION_AUTHORIZED":
        e.append("ECB-QFA materiality gate decision changed")
    mg=g["materiality_gate"]
    if mg["total_tests"]!=2156 or mg["violation_count"]!=0:
        e.append("materiality gate test count/result changed")
    if mg["official_threshold_million_eur"]!="10":
        e.append("official materiality threshold changed")
    if float(mg["max_abs_residual_million_eur"])>=10.0:
        e.append("maximum residual no longer below official materiality threshold")

    if p["decision"]!="REFERENCE_MODE_SET_COMPLETE_10_OF_10_SECTORAL_FINANCIAL_POSITIONS_PROMOTED_ACCOUNTING_AND_BEHAVIOURAL_STATE_UNCHANGED":
        e.append("successor promotion decision changed")
    cur=p["current_reference_mode_state"]
    if cur["required_reference_modes"]!=10 or cur["ready_reference_modes"]!=10 or cur["reference_mode_set_complete"] is not True:
        e.append("successor reference-mode completion state changed")
    for k,v in p["preserved_non_effects"].items():
        if k=="canonical_complete_stock_and_flow_instruments":
            if v!=["F3"]: e.append("promotion altered canonical Accounting Spine completion")
        elif k=="accounting_spine_is_hard_constraint":
            if v is not True: e.append("promotion weakened accounting hard constraint")
        elif isinstance(v,bool) and v is not False:
            e.append(f"promotion unexpectedly enabled {k}")
        elif isinstance(v,int) and not isinstance(v,bool) and v!=0:
            e.append(f"promotion unexpectedly changed {k}")

    mode=next(x for x in refs["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("sectoral_financial_positions is not observed")
    if mode["retained_series"]!=str(SERIES.relative_to(ROOT)):
        e.append("promoted mode retained-series pointer changed")

    rows=list(csv.DictReader(SERIES.open(encoding="utf-8")))
    if len(rows)!=588:
        e.append(f"retained promoted series row count changed: {len(rows)}")
    measures={x["measure"] for x in rows}; sectors={x["rmd_sector"] for x in rows}; periods={x["time_period"] for x in rows}
    if measures!={"flow","stock"}: e.append("promoted series measure coverage changed")
    if sectors!={"H","C","F","G","BNR","X"}: e.append("promoted series sector coverage changed")
    if len(periods)!=49 or min(periods)!="2014-Q1" or max(periods)!="2026-Q1":
        e.append("promoted series period coverage changed")
    for row in rows:
        a=float(row["assets_million_ron"]); l=float(row["liabilities_million_ron"]); n=float(row["net_million_ron"])
        if abs((a-l)-n)>1e-9:
            e.append("retained promoted series contains an assets-liabilities-net arithmetic mismatch")
            break

    dc=model["dynamic_core"]
    if dc["reference_mode_ready_count"]!=10 or dc["reference_mode_required_count"]!=10:
        e.append("model contract reference-mode readiness is not 10/10")
    if dc["reference_mode_closure_ready"] is not True:
        e.append("reference-mode target layer is not marked ready")
    if dc["behavioural_closure_active"] is not False or dc["complete_endogenous_system_dynamics_model"] is not False:
        e.append("10/10 promotion may not activate behavioural/system completion")
    if model["scientific_stage"]["calibration_cycle_open"] is not False:
        e.append("10/10 promotion may not open calibration")

    b=base["canonical_state"]["reference_modes"]
    if b["ready_count"]!=10 or b["required_count"]!=10 or b["closure_ready"] is not True:
        e.append("baseline manifest reference-mode state is not 10/10")
    if b["blockers"]!=[]:
        e.append("baseline manifest still has a reference-mode blocker")
    if "sectoral_financial_positions" not in b["ready"]:
        e.append("baseline manifest ready list lacks sectoral_financial_positions")

    # Historical 9/10 terminal assessment remains an immutable record.
    if hist["status"]!="STAGE_COMPLETE_FROZEN_9_OF_10_UNDER_CURRENT_PUBLIC_EVIDENCE_BOUNDARY":
        e.append("historical 9/10 terminal assessment was rewritten")
    if hist["ready_reference_modes"]!=9 or hist["blocker_count"]!=1:
        e.append("historical 9/10 counts were rewritten")

    if acc["current_expected_state"]["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine readiness changed during reference-mode promotion")
    return e

def main():
    errors=audit_reference_mode_promotion_10_of_10()
    if errors:
        raise RuntimeError("10/10 reference-mode promotion audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "reference_modes_ready":"10/10",
        "sectoral_financial_positions":"OBSERVED_SERIES_AVAILABLE",
        "materiality_tests":2156,
        "materiality_violations":0,
        "accounting_complete_stock_and_flow_instruments":["F3"],
        "calibration_open":False,
        "behavioural_closure_active":False
    },indent=2))

if __name__=="__main__": main()
