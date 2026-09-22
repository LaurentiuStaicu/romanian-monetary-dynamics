from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HORIZON="model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_f4_structural.json"
HISTORICAL_PREDECESSOR="model/registries/trigger_aware_monitoring_horizon_2026_09_21.json"
PREDECESSOR="model/registries/trigger_aware_monitoring_horizon_2026_09_21_post_reference_closure.json"
SUCCESSOR="model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_source_diagnostics.json"
AMECO_SUCCESSOR="model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_ameco_access_protocol.json"
CURRENT="model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_counterpart_workflow_boundary.json"
LATEST="model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_mof_recovery_execution_boundary.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_trigger_aware_monitoring_horizon_2026_09_22()->list[str]:
    errors=[]
    h=load(HORIZON)
    model=load("model/registries/model_contract.json")
    baseline=load("model/registries/scientific_baseline_manifest.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")
    f4mon=load("model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json")

    if h["supersedes"]!=PREDECESSOR:
        errors.append("post-F4 monitoring horizon predecessor changed")
    if h["governing_state"]["current_scientific_state"]!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        errors.append("post-F4 monitoring horizon scientific state changed")
    if h["governing_state"]["reference_mode_readiness"]!="10/10":
        errors.append("reference-mode readiness changed")
    if h["governing_state"].get("f4_stock_trigger_monitoring")!="model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json":
        errors.append("post-F4 horizon lacks canonical F4 stock-trigger monitor")
    if h["governing_state"].get("f4_ras_nonreopen_diagnostic")!="model/accounting/f4_ras_reserve_template_nonreopen_diagnostic_2026_09_22.json":
        errors.append("post-F4 horizon lacks RAS non-reopen diagnostic")

    rules=h["monitoring_rules"]
    for key in (
        "no_repeated_probe_without_trigger",
        "no_f4_cnf_2025_polling_before_evidence_window",
        "f4_cnf_2025_stock_trigger_does_not_reopen_flow",
        "f4_cnf_2025_stock_trigger_does_not_reopen_reference_modes",
    ):
        if rules.get(key) is not True:
            errors.append(f"monitoring hard rule disabled: {key}")

    by_id={x["id"]:x for x in h["horizons"]}
    required_predecessor_ids={
        "prospective_monetary_policy_event",
        "ameco_structural_primary_new_full_vintage",
        "bnr_bls_2025_q2_exact_source",
        "government_repricing_ledger",
        "accounting_counterpart_topology",
    }
    if not required_predecessor_ids.issubset(by_id):
        errors.append("post-F4 horizon dropped a predecessor trigger")
    f4=by_id.get("f4_bnr_cnf_2025_stock_counterpart_matrix")
    if f4 is None:
        errors.append("post-F4 horizon lacks F4 BNR CNF 2025 stock trigger")
    else:
        if f4["next_check_type"]!="EVIDENCE_WINDOW_CONDITIONED_OFFICIAL_PUBLICATION_CHECK":
            errors.append("F4 trigger check type changed")
        if f4["earliest_evidence_window"]!="after 2026-10-31":
            errors.append("F4 earliest evidence window changed")
        if f4["current_state"]!="MONITOR_PUBLICATION_NO_REOPEN":
            errors.append("F4 trigger current state changed")
        if f4["current_reopen_gate_open"] is not False:
            errors.append("F4 monitoring horizon may not open the gate")
        if f4["governing_monitoring_assessment"]!="model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json":
            errors.append("F4 trigger governing assessment changed")

    reg=reopen["instruments"]["F4"]
    if reg["priority_stock_reopen_trigger_id"]!="BNR_CNF_2025_F4_CENTRAL_BANK_ASSET_COUNTERPART_STOCK_MATRIX":
        errors.append("F4 reopen registry priority trigger changed")
    if reg["priority_stock_reopen_trigger_state"]!="MONITOR_PUBLICATION_NO_REOPEN":
        errors.append("F4 reopen registry priority trigger state changed")
    if reg["priority_stock_reopen_earliest_evidence_window"]!="after 2026-10-31":
        errors.append("F4 reopen registry evidence window changed")
    if reg["current_reopen_gate_open"] is not False:
        errors.append("F4 reopen registry gate unexpectedly open")

    if f4mon["current_public_review"]["current_reopen_trigger_satisfied"] is not False:
        errors.append("F4 source monitor unexpectedly claims trigger satisfied")
    if f4mon["monitoring_policy"]["no_repeated_polling_before_new_publication_evidence"] is not True:
        errors.append("F4 source monitor polling prohibition changed")

    d=h["current_disposition"]
    if d["any_monitoring_gate_open_now"] is not False:
        errors.append("post-F4 horizon may not claim an open monitoring gate")
    if d["next_dated_check"]!={"date":"2026-10-08","id":"prospective_monetary_policy_event"}:
        errors.append("next dated event check changed")
    if d.get("next_accounting_evidence_window")!={"after":"2026-10-31","id":"f4_bnr_cnf_2025_stock_counterpart_matrix"}:
        errors.append("next accounting evidence window changed")
    for key in ("f4_stock_reopen_gate_open","f4_flow_reopen_authorized","f4_reference_mode_reopen_authorized"):
        if d.get(key) is not False:
            errors.append(f"post-F4 horizon may not authorize {key}")

    ms=model["scientific_stage"]
    bs=baseline["canonical_state"]["scientific_stage"]
    successor=load(SUCCESSOR)
    ameco_successor=load(AMECO_SUCCESSOR)
    current=load(CURRENT)
    latest=load(LATEST)
    if successor["supersedes"]!=HORIZON:
        errors.append("post-F4 horizon is not preserved as post-source-diagnostics predecessor")
    if ameco_successor["supersedes"]!=SUCCESSOR:
        errors.append("post-source-diagnostics horizon is not preserved as post-AMECO predecessor")
    if current["supersedes"]!=AMECO_SUCCESSOR:
        errors.append("post-AMECO horizon is not preserved as counterpart-workflow predecessor")
    if latest["supersedes"]!=CURRENT:
        errors.append("counterpart-workflow horizon is not preserved as MoF-recovery predecessor")
    if ms["trigger_aware_monitoring_horizon"]!=LATEST:
        errors.append("model contract current monitoring horizon does not point to MoF-recovery successor")
    if bs["trigger_aware_monitoring_horizon"]!=LATEST:
        errors.append("baseline current monitoring horizon does not point to MoF-recovery successor")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_f4_structural")!=HORIZON:
        errors.append("baseline no longer preserves post-F4 horizon as dated authority")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_source_diagnostics")!=SUCCESSOR:
        errors.append("baseline no longer preserves post-source-diagnostics horizon as dated authority")
    if ms["previous_trigger_aware_monitoring_horizon"]!=HISTORICAL_PREDECESSOR:
        errors.append("model contract historical monitoring predecessor changed")
    if bs["previous_trigger_aware_monitoring_horizon"]!=HISTORICAL_PREDECESSOR:
        errors.append("baseline historical monitoring predecessor changed")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_ameco_access_protocol")!=AMECO_SUCCESSOR:
        errors.append("baseline no longer preserves post-AMECO horizon as dated authority")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary")!=CURRENT:
        errors.append("baseline no longer preserves counterpart-workflow horizon as dated authority")
    if ms.get("immediate_previous_trigger_aware_monitoring_horizon")!=CURRENT:
        errors.append("model contract does not preserve counterpart-workflow horizon as immediate predecessor")
    if bs.get("immediate_previous_trigger_aware_monitoring_horizon")!=CURRENT:
        errors.append("baseline does not preserve counterpart-workflow horizon as immediate predecessor")
    expected_window={"after":"2026-10-31","id":"f4_bnr_cnf_2025_stock_counterpart_matrix"}
    if {k:ms["next_accounting_evidence_window_check"][k] for k in ("after","id")}!=expected_window:
        errors.append("model contract next accounting evidence window changed")
    if bs.get("next_accounting_evidence_window_check")!=expected_window:
        errors.append("baseline next accounting evidence window changed")

    return errors

def main()->None:
    errors=audit_trigger_aware_monitoring_horizon_2026_09_22()
    if errors:
        raise RuntimeError("Post-F4 trigger-aware monitoring horizon audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD",
        "next_dated_check":"2026-10-08",
        "next_accounting_evidence_window":"after 2026-10-31",
        "f4_stock_trigger":"BNR_CNF_2025_F4_CENTRAL_BANK_ASSET_COUNTERPART_STOCK_MATRIX",
        "f4_gate_open":False,
        "flow_reopen_authorized":False,
        "reference_mode_reopen_authorized":False
    },indent=2))

if __name__=="__main__":
    main()
