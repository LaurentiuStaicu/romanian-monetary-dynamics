from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"model/dynamics/sectoral_financial_positions_oecd_precision_diagnostic_2026_09_21.json"
T=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_terminal_assessment_2026_09_21.json"
R=ROOT/"model/dynamics/reference_modes.json"
M=ROOT/"model/registries/model_contract.json"

def audit_oecd_precision_diagnostic():
    e=[]
    p=json.loads(P.read_text(encoding="utf-8"))
    t=json.loads(T.read_text(encoding="utf-8"))
    r=json.loads(R.read_text(encoding="utf-8"))
    m=json.loads(M.read_text(encoding="utf-8"))

    if p["decision"]!="NO_PRECISION_BASED_REOPEN_DECIMALS_ONLY_EXPLANATION_INSUFFICIENT_BASELINE_HOLD_CONTINUES":
        e.append("precision diagnostic decision changed")
    q=p["conservative_declared_precision_test"]
    if q["quantum_million_ron"]!=0.01:
        e.append("declared DECIMALS quantum changed")
    if q["system_identity"]["disseminated_observation_terms"]!=69 or q["system_identity"]["conservative_bound_million_ron"]!=0.69:
        e.append("system one-ULP envelope changed")
    if q["resident_additivity_diagnostic"]["disseminated_observation_terms"]!=69 or q["resident_additivity_diagnostic"]["conservative_bound_million_ron"]!=0.69:
        e.append("resident-additivity envelope changed")
    if q["external_balance_diagnostic"]["disseminated_observation_terms"]!=28 or q["external_balance_diagnostic"]["conservative_bound_million_ron"]!=0.28:
        e.append("external-balance envelope changed")
    if not (q["external_balance_diagnostic"]["observed_max_abs_residual_million_ron"] > q["external_balance_diagnostic"]["conservative_bound_million_ron"]):
        e.append("external-balance residual must continue to exceed DECIMALS-only envelope")
    a=p["adjudication"]
    for key in ("declared_decimals_metadata_sufficient_to_explain_all_public_residuals","actual_csv_lexical_one_decimal_can_be_promoted_to_official_precision_rule","post_result_tolerance_change_authorized","new_value_gate_authorized","reference_mode_promotion_authorized"):
        if a[key] is not False:
            e.append(f"precision diagnostic may not authorize {key}")
    if t["verdict"]!="FAIL_FROZEN_RECONCILIATION_TOLERANCE_NO_PROMOTION_SEMANTIC_PATH_CLOSED":
        e.append("terminal semantic-adjusted verdict changed")
    mode=next(x for x in r["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("current successor promotion is missing")
    if m["dynamic_core"]["reference_mode_ready_count"]!=10 or m["dynamic_core"]["reference_mode_required_count"]!=10:
        e.append("global reference readiness must remain 9/10")
    if m["scientific_stage"]["next_operational_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("baseline hold changed")
    return e

def main():
    errors=audit_oecd_precision_diagnostic()
    if errors:
        raise RuntimeError("OECD dissemination-precision diagnostic audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "declared_decimals":2,
        "system_bound_million_ron":0.69,
        "s1_plus_s2_bound_million_ron":0.28,
        "s1_plus_s2_observed_max_million_ron":0.5000000002328306,
        "precision_reopen_authorized":False,
        "historical_gate_effect":"NO_PROMOTION_AT_THIS_GATE","current_reference_modes_ready":"10/10",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
