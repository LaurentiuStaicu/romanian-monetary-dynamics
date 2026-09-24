from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_counterpart_workflow_boundary.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_ameco_access_protocol.json"
SUCCESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_mof_recovery_execution_boundary.json"
PREVIOUS_LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    p = load(PREDECESSOR)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if h["registry_version"] != "0.7":
        errors.append("counterpart-workflow horizon version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("counterpart-workflow predecessor changed")

    if [x["id"] for x in h["horizons"]] != [x["id"] for x in p["horizons"]]:
        errors.append("trigger identity/order changed")
    by_id = {x["id"]: x for x in h["horizons"]}
    prior = {x["id"]: x for x in p["horizons"]}

    for trigger_id in by_id:
        if by_id[trigger_id] != prior[trigger_id]:
            errors.append(f"existing trigger content changed: {trigger_id}")

    rules = h["monitoring_rules"]
    for key in (
        "no_repeated_probe_without_trigger",
        "no_provider_polling_counts_as_scientific_progress",
        "accounting_counterpart_probe_requires_changed_topology_or_new_source",
        "accounting_counterpart_manual_rerun_without_trigger_is_not_scientific_progress",
    ):
        if rules.get(key) is not True:
            errors.append(f"monitoring hard rule disabled: {key}")

    accounting = by_id["accounting_counterpart_topology"]
    if accounting["next_check_type"] != "CHANGED_DATASET_TOPOLOGY_OR_NEW_SOURCE_ONLY":
        errors.append("accounting counterpart trigger type changed")
    if accounting["action_without_topology_change"] != "Do not rerun exhausted historical source probes.":
        errors.append("accounting counterpart no-rerun rule changed")
    if accounting["current_known_release_context"]["ECB_QSA_next_data_release"] != "2026-10-02":
        errors.append("ECB QSA known release date changed")
    if "Routine new quarterly vintages do not reopen" not in accounting["current_known_release_context"]["rule"]:
        errors.append("routine-vintage non-reopen rule changed")

    boundary = h.get("counterpart_probe_execution_boundary", {})
    expected = {
        "governing_trigger_id": "accounting_counterpart_topology",
        "oecd_workflow": ".github/workflows/sectoral-financial-positions-oecd-counterpart-probe.yml",
        "eurostat_workflow": ".github/workflows/sectoral-financial-positions-eurostat-counterpart-probe.yml",
        "historical_oecd_contract": "model/dynamics/sectoral_financial_positions_oecd_counterpart_probe_contract.json",
        "historical_eurostat_contract": "model/dynamics/sectoral_financial_positions_eurostat_counterpart_probe_contract.json",
        "current_role": "TRIGGER_CONDITIONED_HISTORICAL_DISCOVERY_REPLAY_ONLY",
    }
    for key, value in expected.items():
        if boundary.get(key) != value:
            errors.append(f"counterpart workflow boundary changed: {key}")
    if boundary.get("historical_contracts_rewritten") is not False:
        errors.append("historical counterpart contracts may not be rewritten")
    for key in (
        "rerun_authorized_now",
        "unchanged_dataset_vintage_is_trigger",
        "routine_quarterly_release_is_trigger",
        "manual_rerun_without_trigger_counts_as_scientific_progress",
    ):
        if boundary.get(key) is not False:
            errors.append(f"unsafe counterpart workflow rule enabled: {key}")
    if len(boundary.get("reopen_prerequisites", [])) != 3:
        errors.append("counterpart workflow reopen prerequisites changed")

    for key in ("oecd_workflow", "eurostat_workflow"):
        workflow = (ROOT / boundary[key]).read_text(encoding="utf-8")
        for token in (
            "TRIGGER-CONDITIONED HISTORICAL DISCOVERY REPLAY",
            "unchanged topology",
            "not new scientific progress",
            "accounting_counterpart_topology",
            "source-topology pass is preregistered",
        ):
            if token not in workflow:
                errors.append(f"{key} lost trigger-conditioned safeguard: {token}")

    d = h["current_disposition"]
    if d.get("accounting_counterpart_probe_rerun_authorized_now") is not False:
        errors.append("counterpart probe rerun unexpectedly authorized")
    if d.get("accounting_counterpart_topology_trigger_satisfied") is not False:
        errors.append("accounting counterpart topology trigger unexpectedly satisfied")
    for key in (
        "any_monitoring_gate_open_now",
        "active_source_task_open",
        "estimation_or_refit_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
    ):
        if d.get(key) is not False:
            errors.append(f"successor unexpectedly authorizes {key}")

    successor = load(SUCCESSOR)
    previous_latest = load(PREVIOUS_LATEST)
    latest = load(LATEST)
    if successor["supersedes"] != HORIZON:
        errors.append("counterpart-workflow horizon is not preserved as successor predecessor")
    if previous_latest["supersedes"] != SUCCESSOR:
        errors.append("MoF-recovery horizon is not preserved as AMECO-month predecessor")
    if latest["supersedes"] != PREVIOUS_LATEST:
        errors.append("latest AMECO-month monitoring predecessor changed")
    if model["scientific_stage"]["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("model contract current horizon does not point to MoF-recovery successor")
    if model["scientific_stage"]["immediate_previous_trigger_aware_monitoring_horizon"] != PREVIOUS_LATEST:
        errors.append("model contract does not preserve counterpart-workflow horizon as immediate predecessor")
    state = baseline["canonical_state"]["scientific_stage"]
    if state["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("baseline canonical state does not point to MoF-recovery successor")
    if state["immediate_previous_trigger_aware_monitoring_horizon"] != PREVIOUS_LATEST:
        errors.append("baseline does not preserve AMECO-month horizon as immediate predecessor")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != LATEST:
        errors.append("baseline generic monitoring authority is stale")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary") != HORIZON:
        errors.append("baseline no longer retains counterpart-workflow horizon as dated authority")
    if baseline.get("manifest_version") != "1.14":
        errors.append("scientific baseline manifest version did not advance to 1.14")

    return errors

def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary()
    if errors:
        raise RuntimeError(
            "Post-counterpart-workflow monitoring horizon audit failed:\n- "
            + "\n- ".join(errors)
        )
    h = load(HORIZON)
    print(json.dumps({
        "status": "PASS",
        "registry_version": h["registry_version"],
        "scientific_state": h["governing_state"]["current_scientific_state"],
        "counterpart_probe_rerun_authorized_now": h["current_disposition"]["accounting_counterpart_probe_rerun_authorized_now"],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
        "next_accounting_evidence_window": h["current_disposition"]["next_accounting_evidence_window"],
    }, indent=2))

if __name__ == "__main__":
    main()
