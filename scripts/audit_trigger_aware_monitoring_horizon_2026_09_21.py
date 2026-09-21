from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
H=ROOT/"model/registries/trigger_aware_monitoring_horizon_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"

def audit_trigger_horizon_2026_09_21():
    e=[]
    h=json.loads(H.read_text(encoding="utf-8"))
    m=json.loads(M.read_text(encoding="utf-8"))
    if h["supersedes"]!="model/registries/trigger_aware_monitoring_horizon_2026_09_20.json":
        e.append("monitoring-horizon lineage changed")
    if h["governing_state"]["current_scientific_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("governing scientific state changed")
    if not all(h["monitoring_rules"].values()):
        e.append("a monitoring hard rule was disabled")
    ids={x["id"] for x in h["horizons"]}
    required={
        "prospective_monetary_policy_event",
        "ameco_structural_primary_new_full_vintage",
        "bnr_bls_2025_q2_exact_source",
        "government_repricing_ledger",
        "accounting_reference_mode_counterpart_topology",
        "sectoral_financial_positions_public_precision_rule",
    }
    if ids!=required:
        e.append(f"monitoring horizon ids changed: {sorted(ids)}")
    precision=next(x for x in h["horizons"] if x["id"]=="sectoral_financial_positions_public_precision_rule")
    if precision["current_negative_evidence"]["observed_residuals_may_define_future_tolerance"] is not False:
        e.append("observed residuals may not define a future tolerance")
    d=h["current_disposition"]
    for key in (
        "any_monitoring_gate_open_now","active_calibration_cycle_open","active_source_task_open",
        "active_semantic_task_open","active_precision_task_open","response_values_authorized_for_inspection_now",
        "estimation_or_refit_authorized","model_selection_authorized","target_family_switch_authorized",
        "holdout_opening_authorized","system_dynamics_activation_authorized","behavioural_closure_authorized",
        "reference_mode_promotion_authorized",
    ):
        if d[key] is not False:
            e.append(f"monitoring disposition may not open {key}")
    if d["next_dated_check"]!={"date":"2026-10-08","id":"prospective_monetary_policy_event"}:
        e.append("next dated check changed")
    s=m["scientific_stage"]
    if s.get("trigger_aware_monitoring_horizon")!="model/registries/trigger_aware_monitoring_horizon_2026_09_21.json":
        e.append("model contract does not point to successor monitoring horizon")
    if s["next_operational_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("model operational state changed")
    return e

def main():
    errors=audit_trigger_horizon_2026_09_21()
    if errors:
        raise RuntimeError("Trigger-aware monitoring horizon audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "monitoring_gate_open":False,
        "next_dated_check":"2026-10-08",
        "next_dated_check_id":"prospective_monetary_policy_event",
        "precision_reopen_requires":"NEW_OFFICIAL_DOMAIN_SPECIFIC_PRECISION_EVIDENCE",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__":
    main()
