from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
G=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_official_tolerance_gate_assessment_2026_09_21.json"
P=ROOT/"model/dynamics/sectoral_financial_positions_reference_mode_promotion_assessment_2026_09_21.json"
S=ROOT/"model/dynamics/reference_mode_recovery_successor_assessment_2026_09_21.json"
R=ROOT/"model/dynamics/reference_modes.json"
M=ROOT/"model/registries/model_contract.json"
B=ROOT/"model/registries/scientific_baseline_manifest.json"
A=ROOT/"model/accounting/accounting_readiness_gate.json"
H=ROOT/"model/registries/trigger_aware_monitoring_horizon_2026_09_21.json"
SERIES=ROOT/"data/processed/sectoral_financial_positions_reference_oecd_2014Q1_2026Q1.csv.gz"

def load(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def audit_reference_mode_promotion()->list[str]:
    e=[]
    g=load(G); p=load(P); s=load(S); r=load(R); m=load(M); b=load(B); a=load(A); h=load(H)

    if g["verdict"]!="PASS_OFFICIAL_ECB_QFA_TOLERANCE_GATE_PROMOTION_ASSESSMENT_AUTHORIZED":
        e.append("official ECB QFA tolerance gate PASS changed")
    if g["gates"]["per_instrument_horizontal_consistency"]["tests"]!=686 or g["gates"]["per_instrument_horizontal_consistency"]["violations"]!=0:
        e.append("per-instrument official-tolerance gate changed")
    if g["gates"]["aggregate_six_sector_consistency"]["tests"]!=98 or g["gates"]["aggregate_six_sector_consistency"]["violations"]!=0:
        e.append("aggregate official-tolerance gate changed")
    if g["fx_threshold"]["conservative_threshold_floor_million_RON"]!="43.830":
        e.append("official threshold floor changed")

    if p["decision"]!="PROMOTE_AGGREGATE_SECTORAL_FINANCIAL_POSITIONS_TO_OBSERVED_SERIES_AVAILABLE":
        e.append("promotion decision changed")
    if p["reference_mode_system_effect"]["ready_count_after"]!=10 or p["reference_mode_system_effect"]["required_count"]!=10:
        e.append("promotion system effect changed")
    if p["scope"]["canonical_bilateral_holder_by_issuer_accounting_boundary_promoted"] is not False:
        e.append("aggregate promotion may not promote bilateral Accounting Spine")
    if p["scope"]["calibration_cycle_opened"] is not False or p["scope"]["feedback_activation_authorized"] is not False:
        e.append("aggregate promotion may not open calibration or feedback activation")

    compressed=SERIES.read_bytes()
    if sha256(compressed)!="3e1d45da7d23645eb29387182c8175fde69527ed438f60f32df009d4bb34d5ad":
        e.append("processed reference-series compressed hash changed")
    raw=gzip.decompress(compressed)
    if sha256(raw)!="0279091f83e4fff8e521b66235ca1116be05b0003e2be6d8860e6c1809fc952d":
        e.append("processed reference-series uncompressed hash changed")
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    if len(rows)!=588:
        e.append(f"processed reference-series row count changed: {len(rows)}")
    if {x["measure"] for x in rows}!={"flow","stock"}:
        e.append("processed reference-series measure set changed")
    if {x["rmd_sector"] for x in rows}!={"H","C","F","G","BNR","X"}:
        e.append("processed reference-series sector set changed")
    periods=sorted({x["time_period"] for x in rows})
    if len(periods)!=49 or periods[0]!="2014-Q1" or periods[-1]!="2026-Q1":
        e.append("processed reference-series period coverage changed")

    mode=next(x for x in r["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("sectoral_financial_positions is not promoted")
    if mode.get("retained_series")!="data/processed/sectoral_financial_positions_reference_oecd_2014Q1_2026Q1.csv.gz":
        e.append("reference-mode retained series pointer changed")

    dc=m["dynamic_core"]
    if dc["reference_mode_ready_count"]!=10 or dc["reference_mode_required_count"]!=10 or dc["reference_mode_closure_ready"] is not True:
        e.append("model contract reference-mode readiness is not 10/10 ready")
    if dc["sectoral_financial_positions_reference_mode_status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("model contract sectoral mode status changed")
    if dc["behavioural_closure_active"] is not False or dc["complete_endogenous_system_dynamics_model"] is not False:
        e.append("reference-mode promotion may not activate behavioural/model completion")
    if dc["full_RMD_empirical_state_claim_allowed"] is not False:
        e.append("reference-mode promotion may not claim full RMD empirical state")

    stage=m["scientific_stage"]
    if stage["active_noncalibration_source_task"] is not None or stage["calibration_cycle_open"] is not False:
        e.append("promotion must close source task and leave calibration closed")
    if stage["next_operational_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("promotion must return to baseline hold")

    br=b["canonical_state"]["reference_modes"]
    if br["ready_count"]!=10 or br["required_count"]!=10 or br["closure_ready"] is not True or br["blockers"]!=[]:
        e.append("scientific baseline reference-mode state is not 10/10")
    if "sectoral_financial_positions" not in br["ready"]:
        e.append("scientific baseline ready list lacks sectoral_financial_positions")

    acc=a["current_expected_state"]
    if acc["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine stock+flow completion changed")
    if acc["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        e.append("Accounting Spine full benchmark may not become ready")

    if s["decision"]!="REFERENCE_MODE_RECOVERY_REOPEN_COMPLETE_10_OF_10_READY_BASELINE_HOLD_CONTINUES":
        e.append("reference-mode recovery successor decision changed")
    if s["preserved_limits"]["behavioural_closure_active"] is not False or s["preserved_limits"]["calibration_cycle_open"] is not False:
        e.append("successor assessment may not activate behavioural closure/calibration")

    d=h["current_disposition"]
    if d["any_monitoring_gate_open_now"] is not False or d["active_source_task_open"] is not False:
        e.append("completed tolerance trigger must be closed in monitoring horizon")
    return e

def main()->None:
    errors=audit_reference_mode_promotion()
    if errors:
        raise RuntimeError("Reference-mode promotion audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "reference_modes_ready":"10/10",
        "reference_mode_closure_ready":True,
        "sectoral_financial_positions":"OBSERVED_SERIES_AVAILABLE",
        "processed_series_rows":588,
        "accounting_complete_stock_and_flow_instruments":["F3"],
        "calibration_cycle_open":False,
        "behavioural_closure_active":False,
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
