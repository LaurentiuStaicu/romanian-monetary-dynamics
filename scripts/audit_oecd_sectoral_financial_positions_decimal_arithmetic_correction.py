from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"model/dynamics/sectoral_financial_positions_oecd_decimal_arithmetic_correction_assessment_2026_09_21.json"
F=ROOT/"data/source_vintages/oecd-decimal-arithmetic-correction-2026-09-21/legacy_float_boundary_false_positives.csv"
T=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_terminal_assessment_2026_09_21.json"
R=ROOT/"model/dynamics/reference_modes.json"
M=ROOT/"model/registries/model_contract.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))

def audit_decimal_correction():
    e=[]
    a=load(A); t=load(T); r=load(R); m=load(M)
    if a["decision"]!="CORRECT_NUMERICAL_VIOLATION_COUNT_63_TO_47_VERDICT_UNCHANGED_BASELINE_HOLD_CONTINUES":
        e.append("decimal correction decision changed")
    h=a["historical_execution"]
    if h["recorded_violation_count"]!=63 or h["historical_execution_rewritten"] is not False:
        e.append("historical execution provenance changed")
    d=a["exact_decimal_reaudit"]
    if d["exact_violation_count"]!=47 or d["exact_flow_violation_count"]!=21 or d["exact_stock_violation_count"]!=26:
        e.append("exact-decimal violation counts changed")
    if d["exact_boundary_abs_residual_equal_0_1_count"]!=28:
        e.append("exact boundary-row count changed")
    if d["legacy_float_boundary_rows_misclassified_as_violations"]!=16:
        e.append("legacy float false-positive count changed")
    if d["legacy_float_boundary_rows_not_misclassified"]!=12:
        e.append("legacy float correctly nonviolating boundary count changed")
    if d["max_abs_flow_residual_million_ron"]!="0.5" or d["max_abs_stock_residual_million_ron"]!="0.6":
        e.append("exact-decimal residual maxima changed")

    rows=list(csv.DictReader(F.open(encoding="utf-8")))
    if len(rows)!=16:
        e.append(f"compact false-positive evidence count changed: {len(rows)}")
    if any(abs(float(x["exact_decimal_system_residual_million_ron"]))!=0.1 for x in rows):
        e.append("compact evidence contains a non-boundary exact residual")
    if any(abs(float(x["legacy_float_system_residual_million_ron"]))<=0.1 for x in rows):
        e.append("compact evidence contains a legacy value that was not above the binary-float threshold")

    c=a["corrected_scientific_interpretation"]
    if c["mathematically_correct_violation_count"]!=47 or c["terminal_verdict"]!="FAIL_FROZEN_RECONCILIATION_TOLERANCE_NO_PROMOTION":
        e.append("corrected terminal interpretation changed")
    for k in ("new_tolerance_authorized","new_live_execution_authorized","reference_mode_promotion_authorized","accounting_readiness_change","parameter_estimation_authorized","feedback_activation_authorized","behavioural_closure_authorized"):
        if c[k] is not False:
            e.append(f"decimal correction may not authorize {k}")

    if t["reconciliation_gate"]["violation_count"]!=63:
        e.append("historical terminal assessment must remain immutable")
    mode=next(x for x in r["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("current promoted reference mode must remain observed")
    if m["dynamic_core"]["reference_mode_ready_count"]!=10 or m["dynamic_core"]["reference_mode_required_count"]!=10:
        e.append("global current reference-mode readiness must remain 10/10")
    if m["scientific_stage"]["next_operational_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("baseline hold changed")
    return e

def main():
    errors=audit_decimal_correction()
    if errors:
        raise RuntimeError("OECD exact-decimal correction audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "historical_machine_float_violation_count":63,
        "correct_exact_decimal_violation_count":47,
        "flow_violations":21,
        "stock_violations":26,
        "boundary_false_positives_corrected":16,
        "verdict":"FAIL_UNCHANGED",
        "reference_modes_ready":"10/10",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
