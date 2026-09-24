from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_ameco_access_protocol.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_source_diagnostics.json"
AMECO = "model/calibration_validation/ameco_source_access_migration_readiness_2026_09_22.json"
SUCCESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_counterpart_workflow_boundary.json"
MOF_LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_mof_recovery_execution_boundary.json"
PREVIOUS_LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_ameco_access_protocol() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    predecessor = load(PREDECESSOR)
    ameco = load(AMECO)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if h["registry_version"] != "0.6":
        errors.append("post-AMECO-access monitoring horizon version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("post-AMECO-access predecessor changed")
    if h["governing_state"]["current_scientific_state"] != "EVIDENCE_TRIGGERED_BASELINE_HOLD":
        errors.append("scientific state changed")
    if h["governing_state"]["reference_mode_readiness"] != "10/10":
        errors.append("reference-mode readiness changed")
    if h["governing_state"]["ameco_source_access_migration_readiness"] != AMECO:
        errors.append("AMECO migration-readiness pointer changed")
    if h["governing_state"]["ameco_source_access_migration_status"] != ameco["decision"]:
        errors.append("AMECO migration-readiness status is stale")
    if h["governing_state"]["ameco_target_variable_code"] != "UBLGBPS":
        errors.append("AMECO target code changed")
    if h["governing_state"]["ameco_redisstat_dataset_code_identified"] is not False:
        errors.append("AMECO Redisstat dataset identity was fabricated")

    predecessor_ids = [x["id"] for x in predecessor["horizons"]]
    current_ids = [x["id"] for x in h["horizons"]]
    if current_ids != predecessor_ids:
        errors.append("trigger identity/order changed")

    by_id = {x["id"]: x for x in h["horizons"]}
    policy = by_id["prospective_monetary_policy_event"]
    if policy["next_check_date"] != "2026-10-08":
        errors.append("BNR policy date changed")
    if policy["downstream_release_gate"]["earliest_official_MIR_release_date"] != "2026-12-02":
        errors.append("MIR release gate changed")
    accounting = by_id["accounting_counterpart_topology"]
    if accounting["current_known_release_context"]["ECB_QSA_next_data_release"] != "2026-10-02":
        errors.append("ECB QSA known release date changed")
    f4 = by_id["f4_bnr_cnf_2025_stock_counterpart_matrix"]
    if f4["earliest_evidence_window"] != "after 2026-10-31":
        errors.append("F4 evidence window changed")
    if f4["current_reopen_gate_open"] is not False:
        errors.append("F4 gate unexpectedly open")

    ameco_h = by_id["ameco_structural_primary_new_full_vintage"]
    if ameco_h["next_check_type"] != "RELEASE_CONDITIONED_CHECK":
        errors.append("AMECO trigger no longer release-conditioned")
    if ameco_h["current_latest_full_release"] != "2026-06-03":
        errors.append("AMECO latest full release changed")
    protocol = ameco_h.get("source_access_protocol", {})
    if protocol.get("assessment") != AMECO:
        errors.append("AMECO horizon access-protocol assessment pointer changed")
    if protocol.get("status") != ameco["decision"]:
        errors.append("AMECO horizon access-protocol status is stale")
    if protocol.get("target_variable_code") != "UBLGBPS":
        errors.append("AMECO horizon target code changed")
    if protocol.get("redisstat_dataset_code_identified") is not False:
        errors.append("AMECO horizon fabricates Redisstat dataset code")
    if protocol.get("redisstat_dataset_code") is not None:
        errors.append("AMECO horizon stores unverified Redisstat dataset code")
    expected_routes = {
        ameco["official_current_state"]["redisstat_dataflow_catalogue_endpoint"],
        ameco["official_current_state"]["redisstat_catalogue_toc_txt_endpoint"],
        ameco["official_current_state"]["redisstat_browser_ameco_root"],
    }
    if set(protocol.get("official_dataset_discovery_routes", [])) != expected_routes:
        errors.append("AMECO horizon official discovery routes drifted")
    if protocol.get("discovery_order") != ameco["future_release_discovery_protocol"]["dataset_identity_discovery_order"]:
        errors.append("AMECO horizon dataset-discovery order drifted")
    if protocol.get("trigger_satisfied") is not False:
        errors.append("AMECO release trigger unexpectedly satisfied")
    if protocol.get("current_value_inspection_authorized") is not False:
        errors.append("AMECO current value inspection unexpectedly authorized")

    rules = h["monitoring_rules"]
    for key in (
        "no_repeated_probe_without_trigger",
        "post_terminal_no_reopen_adjudication_blocks_same_clue_repetition",
        "no_f4_cnf_2025_polling_before_evidence_window",
        "ameco_future_dataset_identity_must_come_from_official_provider_metadata",
        "ameco_legacy_chapter_or_zip_name_cannot_define_redisstat_dataset_code",
        "ameco_no_data_query_before_release_and_dataset_identity",
        "ameco_current_release_must_not_be_repolled_before_release_trigger",
    ):
        if rules.get(key) is not True:
            errors.append(f"monitoring hard rule disabled: {key}")

    d = h["current_disposition"]
    if d["any_monitoring_gate_open_now"] is not False:
        errors.append("monitoring horizon may not claim an open gate")
    if d["next_dated_check"] != {"date": "2026-10-08", "id": "prospective_monetary_policy_event"}:
        errors.append("next dated check changed")
    if d["next_accounting_evidence_window"] != {"after": "2026-10-31", "id": "f4_bnr_cnf_2025_stock_counterpart_matrix"}:
        errors.append("next accounting evidence window changed")
    if d.get("ameco_release_trigger_satisfied") is not False:
        errors.append("AMECO release trigger unexpectedly open")
    if d.get("ameco_source_materialisation_reopen_active") is not False:
        errors.append("AMECO source materialisation unexpectedly open")
    if d.get("ameco_redisstat_dataset_identity_resolved") is not False:
        errors.append("AMECO Redisstat dataset identity unexpectedly resolved")
    for key in (
        "active_calibration_cycle_open",
        "active_source_task_open",
        "response_values_authorized_for_inspection_now",
        "estimation_or_refit_authorized",
        "model_selection_authorized",
        "holdout_opening_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
        "accounting_spine_completion_authorized",
    ):
        if d.get(key) is not False:
            errors.append(f"horizon unexpectedly authorizes {key}")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    successor = load(SUCCESSOR)
    mof_latest = load(MOF_LATEST)
    previous_latest = load(PREVIOUS_LATEST)
    latest = load(LATEST)
    if successor["supersedes"] != HORIZON:
        errors.append("post-AMECO-access horizon is not preserved as counterpart-workflow predecessor")
    if mof_latest["supersedes"] != SUCCESSOR:
        errors.append("counterpart-workflow horizon is not preserved as MoF-recovery predecessor")
    if previous_latest["supersedes"] != MOF_LATEST:
        errors.append("MoF-recovery horizon is not preserved as AMECO-month predecessor")
    if latest["supersedes"] != PREVIOUS_LATEST:
        errors.append("MoF-recovery horizon is not preserved as AMECO-month predecessor")
    if ms["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("model contract current horizon does not point to MoF-recovery successor")
    if bs["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("baseline current horizon does not point to MoF-recovery successor")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_ameco_access_protocol") != HORIZON:
        errors.append("baseline no longer preserves post-AMECO-access horizon as dated authority")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary") != SUCCESSOR:
        errors.append("baseline no longer preserves counterpart-workflow horizon as dated authority")
    if ms.get("immediate_previous_trigger_aware_monitoring_horizon") != PREVIOUS_LATEST:
        errors.append("model contract does not preserve counterpart-workflow horizon as immediate predecessor")
    if bs.get("immediate_previous_trigger_aware_monitoring_horizon") != PREVIOUS_LATEST:
        errors.append("baseline does not preserve counterpart-workflow horizon as immediate predecessor")
    if model["calibration_validation"].get("ameco_source_access_migration_readiness") != AMECO:
        errors.append("model contract lost AMECO access readiness")
    if baseline["authority"].get("ameco_source_access_migration_readiness") != AMECO:
        errors.append("baseline lost AMECO access readiness")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_ameco_access_protocol()
    if errors:
        raise RuntimeError(
            "Post-AMECO-access trigger-aware monitoring horizon audit failed:\n- "
            + "\n- ".join(errors)
        )
    h = load(HORIZON)
    print(json.dumps({
        "status": "PASS",
        "registry_version": h["registry_version"],
        "scientific_state": h["governing_state"]["current_scientific_state"],
        "ameco_trigger_satisfied": h["current_disposition"]["ameco_release_trigger_satisfied"],
        "ameco_dataset_identity_resolved": h["current_disposition"]["ameco_redisstat_dataset_identity_resolved"],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
        "next_accounting_evidence_window": h["current_disposition"]["next_accounting_evidence_window"],
    }, indent=2))


if __name__ == "__main__":
    main()
