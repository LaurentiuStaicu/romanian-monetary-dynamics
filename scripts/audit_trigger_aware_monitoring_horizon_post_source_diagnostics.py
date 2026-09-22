from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_source_diagnostics.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_f4_structural.json"
BLS_REVIEW = "model/calibration_validation/bnr_bls_2025q2_post_terminal_indexed_endpoint_review_2026_09_22.json"
GOV_REPRICING_REVIEW = "model/calibration_validation/government_repricing_exchange_topology_post_terminal_assessment_2026_09_22.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_source_diagnostics() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    predecessor = load(PREDECESSOR)
    bls = load(BLS_REVIEW)
    gov = load(GOV_REPRICING_REVIEW)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if h["registry_version"] != "0.5":
        errors.append("post-source-diagnostics monitoring horizon version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("post-source-diagnostics monitoring predecessor changed")
    if h["governing_state"]["current_scientific_state"] != "EVIDENCE_TRIGGERED_BASELINE_HOLD":
        errors.append("post-source-diagnostics scientific state changed")
    if h["governing_state"]["reference_mode_readiness"] != "10/10":
        errors.append("post-source-diagnostics reference-mode readiness changed")

    predecessor_ids = [x["id"] for x in predecessor["horizons"]]
    current_ids = [x["id"] for x in h["horizons"]]
    if current_ids != predecessor_ids:
        errors.append("post-source-diagnostics horizon changed trigger identity/order")

    by_id = {x["id"]: x for x in h["horizons"]}
    policy = by_id["prospective_monetary_policy_event"]
    if policy["next_check_date"] != "2026-10-08":
        errors.append("next BNR policy check changed")
    if policy["downstream_release_gate"]["earliest_official_MIR_release_date"] != "2026-12-02":
        errors.append("October MIR release gate changed")

    accounting = by_id["accounting_counterpart_topology"]
    if accounting["current_known_release_context"]["ECB_QSA_next_data_release"] != "2026-10-02":
        errors.append("known ECB QSA release date changed")
    if "Routine new quarterly vintages do not reopen" not in accounting["current_known_release_context"]["rule"]:
        errors.append("routine QSA release no-reopen rule changed")

    f4 = by_id["f4_bnr_cnf_2025_stock_counterpart_matrix"]
    if f4["earliest_evidence_window"] != "after 2026-10-31":
        errors.append("F4 evidence window changed")
    if f4["current_reopen_gate_open"] is not False:
        errors.append("F4 gate unexpectedly open")

    bls_h = by_id["bnr_bls_2025_q2_exact_source"]
    bls_a = bls_h.get("latest_adjudication", {})
    if bls_a.get("assessment") != BLS_REVIEW:
        errors.append("BLS latest adjudication pointer changed")
    if bls_a.get("status") != bls["disposition"]["status"]:
        errors.append("BLS latest adjudication status is stale")
    if bls_a.get("trigger_satisfied") is not False:
        errors.append("BLS source trigger unexpectedly satisfied")
    if bls["semantic_adjudication"]["trigger_condition_satisfied"] is not False:
        errors.append("BLS successor review unexpectedly satisfies source trigger")
    if bls["disposition"]["canonical_panel_remains_11_of_12"] is not True:
        errors.append("BLS canonical panel unexpectedly changed")
    if bls_a.get("repeated_same_clue_search_authorized") is not False:
        errors.append("BLS repeated same-clue search unexpectedly authorized")

    gov_h = by_id["government_repricing_ledger"]
    gov_a = gov_h.get("latest_adjudication", {})
    if gov_a.get("assessment") != GOV_REPRICING_REVIEW:
        errors.append("government repricing latest adjudication pointer changed")
    if gov_a.get("status") != gov["current_disposition"]["status"]:
        errors.append("government repricing latest adjudication status is stale")
    if gov_a.get("trigger_satisfied") is not False:
        errors.append("government repricing trigger unexpectedly satisfied")
    if gov_a.get("gate_1_ledger_completeness") != "FAIL_UNCHANGED":
        errors.append("government repricing Gate 1 changed")
    if gov["contract_adjudication"]["gate_1_status"] != "FAIL_UNCHANGED":
        errors.append("government repricing successor no longer preserves Gate 1 failure")
    if gov_a.get("canonical_ledger_mutation_authorized") is not False:
        errors.append("government repricing ledger mutation unexpectedly authorized")
    if gov_a.get("repeated_same_prospect_search_authorized") is not False:
        errors.append("government repricing repeated same-prospect search unexpectedly authorized")

    rules = h["monitoring_rules"]
    for key in (
        "no_repeated_probe_without_trigger",
        "official_domain_or_file_extension_alone_is_not_source_identity",
        "event_topology_alone_is_not_matched_repricing_ledger",
        "post_terminal_no_reopen_adjudication_blocks_same_clue_repetition",
        "no_f4_cnf_2025_polling_before_evidence_window",
    ):
        if rules.get(key) is not True:
            errors.append(f"monitoring hard rule disabled: {key}")

    d = h["current_disposition"]
    if d["any_monitoring_gate_open_now"] is not False:
        errors.append("post-source-diagnostics horizon may not claim an open gate")
    if d["next_dated_check"] != {"date": "2026-10-08", "id": "prospective_monetary_policy_event"}:
        errors.append("next dated check changed")
    if d["next_accounting_evidence_window"] != {"after": "2026-10-31", "id": "f4_bnr_cnf_2025_stock_counterpart_matrix"}:
        errors.append("next accounting evidence window changed")
    if d.get("new_official_source_clues_adjudicated_without_reopen") is not True:
        errors.append("successor does not record no-reopen source adjudications")
    if d.get("bnr_bls_2025q2_trigger_satisfied") is not False:
        errors.append("successor disposition unexpectedly opens BLS trigger")
    if d.get("government_repricing_trigger_satisfied") is not False:
        errors.append("successor disposition unexpectedly opens government repricing trigger")
    for key in (
        "active_calibration_cycle_open",
        "active_source_task_open",
        "active_semantic_task_open",
        "active_precision_task_open",
        "response_values_authorized_for_inspection_now",
        "estimation_or_refit_authorized",
        "model_selection_authorized",
        "holdout_opening_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
        "reference_mode_promotion_authorized",
        "accounting_spine_completion_authorized",
        "f4_stock_reopen_gate_open",
        "f4_flow_reopen_authorized",
        "f4_reference_mode_reopen_authorized",
    ):
        if d.get(key) is not False:
            errors.append(f"post-source-diagnostics horizon unexpectedly authorizes {key}")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    if ms["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("model contract does not point to current post-source-diagnostics horizon")
    if bs["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("scientific baseline does not point to current post-source-diagnostics horizon")
    if ms.get("immediate_previous_trigger_aware_monitoring_horizon") != PREDECESSOR:
        errors.append("model contract immediate monitoring predecessor changed")
    if bs.get("immediate_previous_trigger_aware_monitoring_horizon") != PREDECESSOR:
        errors.append("baseline immediate monitoring predecessor changed")

    if model["calibration_validation"]["bnr_bls_2025q2_latest_post_terminal_review"] != BLS_REVIEW:
        errors.append("model contract BLS review pointer changed")
    if model["calibration_validation"]["government_repricing_latest_exchange_topology_review"] != GOV_REPRICING_REVIEW:
        errors.append("model contract government repricing review pointer changed")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_source_diagnostics()
    if errors:
        raise RuntimeError(
            "Post-source-diagnostics trigger-aware monitoring horizon audit failed:\n- "
            + "\n- ".join(errors)
        )
    h = load(HORIZON)
    print(json.dumps({
        "status": "PASS",
        "scientific_state": h["governing_state"]["current_scientific_state"],
        "latest_BLS_status": h["governing_state"]["bnr_bls_2025q2_latest_post_terminal_status"],
        "latest_government_repricing_status": h["governing_state"]["government_repricing_latest_exchange_topology_status"],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
        "next_accounting_evidence_window": h["current_disposition"]["next_accounting_evidence_window"],
        "any_monitoring_gate_open_now": h["current_disposition"]["any_monitoring_gate_open_now"],
    }, indent=2))


if __name__ == "__main__":
    main()
