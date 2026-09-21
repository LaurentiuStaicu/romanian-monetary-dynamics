from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"model/dynamics/sectoral_financial_positions_oecd_window_stability_diagnostic_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"

def audit_window_stability():
    e=[]; a=json.loads(A.read_text()); m=json.loads(M.read_text())
    if a["decision"]!="NO_WINDOW_BASED_REOPEN_FAILURE_PERSISTS_ACROSS_ALL_40Q_WINDOWS_AND_POST_BENCHMARK_PERIOD":
        e.append("window diagnostic decision changed")
    r=a["rolling_window_adjudication"]
    if r["possible_contiguous_40_quarter_windows"]!=10 or r["passing_windows"]!=0:
        e.append("rolling-window pass count changed")
    if r["minimum_measure_period_violations"]!=39 or r["maximum_measure_period_violations"]!=41:
        e.append("rolling-window violation range changed")
    p=a["post_benchmark_public_boundary_check"]
    if p["measure_period_violations"]!=5 or p["quarters_with_any_violation"]!=4:
        e.append("post-benchmark failure count changed")
    if not all(v is False for v in a["safeguards"].values()):
        e.append("window diagnostic safeguard relaxed")
    if m["dynamic_core"]["reference_mode_ready_count"]!=10:
        e.append("current successor reference readiness must be 10")
    if m["scientific_stage"]["next_operational_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("baseline hold changed")
    return e

def main():
    errs=audit_window_stability()
    if errs: raise RuntimeError("Window stability diagnostic failed:\n- "+"\n- ".join(errs))
    print(json.dumps({"status":"PASS","40q_windows_passing":0,"post_benchmark_measure_period_violations":5,"reference_modes_ready":"10/10"},indent=2))
if __name__=="__main__": main()
