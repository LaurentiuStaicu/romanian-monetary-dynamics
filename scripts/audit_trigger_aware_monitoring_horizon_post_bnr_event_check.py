from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_10_22_post_bnr_event_check.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"
BNR_SOURCE = "https://www.bnr.ro/25929-2026-10-08-hotarari-ale-ca-al-bnr-pe-probleme-de-politica-monetara"
CURRENT_NEXT = {"date": "2026-11-12", "id": "prospective_monetary_policy_event"}
EXPECTED_STATUS = "REFERENCE_MODES_10_OF_10_NO_GATE_OPEN_BNR_2026_10_08_UNCHANGED_RATE_6_50_NO_MIR_RESPONSE_INSPECTION_COUNTERPART_PROBES_TRIGGER_CONDITIONED_MOF_FULL_2025_RECOVERY_MANUAL_ONLY_ACTIVE_POLLING_FALSE_AMECO_ACCESS_PROTOCOL_BOUND_DATASET_IDENTITY_UNRESOLVED_AMECO_AUTUMN_2026_WINDOW_2026_11_NO_EXACT_DAY_QSA_Q2_2026_CONTEXT_2026_10_02_HOUSEHOLDS_NFC_2026_10_28_FULL_INSTITUTIONAL_SECTOR_ROUTINE_RELEASES_NO_REOPEN_NEXT_DATED_CHECK_2026_11_12_F4_STOCK_EVIDENCE_WINDOW_AFTER_2026_10_31"
EXPECTED_EVENT_CHECK = {
    "trigger_id": "prospective_monetary_policy_event",
    "event_date": "2026-10-08",
    "source_class": "BNR Board monetary-policy decision",
    "official_source": BNR_SOURCE,
    "policy_rate_percent_per_annum": 6.5,
    "observed_policy_rate_change_basis_points": 0,
    "decision": "UNCHANGED",
    "trigger_satisfied": False,
    "response_values_inspected": False,
    "disposition": "RECORD_EVENT_ONLY_RETURN_TO_BASELINE_HOLD",
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_bnr_event_check() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    p = load(PREDECESSOR)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")
    status_text = (ROOT / "STATUS.md").read_text(encoding="utf-8")

    if h.get("registry_version") != "0.11":
        errors.append("BNR-event successor registry version must be 0.11")
    if h.get("frozen_on") != "2026-10-22":
        errors.append("BNR-event successor freeze date changed")
    if h.get("supersedes") != PREDECESSOR:
        errors.append("BNR-event successor predecessor changed")
    if [x["id"] for x in h["horizons"]] != [x["id"] for x in p["horizons"]]:
        errors.append("trigger identity/order changed")

    current = {x["id"]: x for x in h["horizons"]}
    prior = {x["id"]: x for x in p["horizons"]}
    for trigger_id in current:
        if trigger_id != "prospective_monetary_policy_event" and current[trigger_id] != prior[trigger_id]:
            errors.append(f"non-monetary trigger content changed: {trigger_id}")

    expected_monetary = copy.deepcopy(prior["prospective_monetary_policy_event"])
    expected_monetary["next_check_date"] = "2026-11-12"
    expected_monetary["downstream_release_gate"] = {
        "reference_month_if_event_occurs_on_2026_11_12": "2026-11",
        "earliest_official_MIR_release_date": "2027-01-06",
        "source": "ECB MIR release calendar",
        "rule": "The November-reference MIR response may be inspected only on or after 2027-01-06 and only if November contains a non-zero policy-rate event.",
    }
    if current["prospective_monetary_policy_event"] != expected_monetary:
        errors.append("prospective monetary gate changed beyond next event and corresponding release gate")

    if h.get("completed_event_checks") != [EXPECTED_EVENT_CHECK]:
        errors.append("completed 2026-10-08 BNR event record changed or missing")
    if EXPECTED_EVENT_CHECK["official_source"] != BNR_SOURCE:
        errors.append("BNR event source authority changed")
    if h["monitoring_rules"] != p["monitoring_rules"]:
        errors.append("monitoring rules changed")
    if h["governing_state"] != p["governing_state"]:
        errors.append("governing scientific state changed")
    if h.get("counterpart_probe_execution_boundary") != p.get("counterpart_probe_execution_boundary"):
        errors.append("counterpart execution boundary changed")
    if h.get("mof_full_2025_recovery_execution_boundary") != p.get("mof_full_2025_recovery_execution_boundary"):
        errors.append("MoF recovery execution boundary changed")

    disposition = copy.deepcopy(h["current_disposition"])
    prior_disposition = copy.deepcopy(p["current_disposition"])
    observed_next = disposition.pop("next_dated_check", None)
    prior_disposition.pop("next_dated_check", None)
    if disposition != prior_disposition:
        errors.append("current disposition changed beyond advancing the next dated check")
    if observed_next != CURRENT_NEXT:
        errors.append("current disposition next dated check is not 2026-11-12")

    for key in (
        "any_monitoring_gate_open_now",
        "active_calibration_cycle_open",
        "active_source_task_open",
        "response_values_authorized_for_inspection_now",
        "estimation_or_refit_authorized",
        "model_selection_authorized",
        "holdout_opening_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
        "accounting_spine_completion_authorized",
        "accounting_counterpart_topology_trigger_satisfied",
        "accounting_counterpart_probe_rerun_authorized_now",
        "mof_full_2025_recovery_execution_authorized_now",
        "mof_full_2025_recovery_active_polling",
    ):
        if h["current_disposition"].get(key) is not False:
            errors.append(f"monitoring handoff unexpectedly opens or enables {key}")

    if "### Current trigger-aware monitoring handoff — 2026-10-22" not in status_text:
        errors.append("STATUS current monitoring handoff section missing")
    if "The BNR decision of 2026-10-08 kept the policy rate unchanged at 6.50%" not in status_text:
        errors.append("STATUS does not record the completed unchanged-rate event")
    if "next dated check is **2026-11-12**" not in status_text:
        errors.append("STATUS next event date is stale")
    if "2027-01-06" not in status_text:
        errors.append("STATUS conditional November-reference MIR release gate is missing")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    if ms.get("trigger_aware_monitoring_horizon") != HORIZON:
        errors.append("model contract does not point to the BNR-event successor")
    if ms.get("immediate_previous_trigger_aware_monitoring_horizon") != PREDECESSOR:
        errors.append("model contract immediate predecessor is stale")
    expected_model_next = {
        **CURRENT_NEXT,
        "rule": "Check only the BNR policy decision. If unchanged, do not inspect MIR response values. If non-zero, the November-reference MIR response remains closed until its official 2027-01-06 release.",
    }
    if ms.get("next_dated_trigger_check") != expected_model_next:
        errors.append("model contract next dated trigger check is stale")
    if ms.get("trigger_aware_monitoring_horizon_status") != EXPECTED_STATUS:
        errors.append("model contract monitoring status summary is stale")

    if bs.get("trigger_aware_monitoring_horizon") != HORIZON:
        errors.append("baseline current monitoring pointer is stale")
    if bs.get("immediate_previous_trigger_aware_monitoring_horizon") != PREDECESSOR:
        errors.append("baseline immediate predecessor pointer is stale")
    if bs.get("next_dated_trigger_check") != CURRENT_NEXT:
        errors.append("baseline next dated trigger check is stale")
    if bs.get("trigger_aware_monitoring_horizon_status") != EXPECTED_STATUS:
        errors.append("baseline monitoring status summary is stale")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != HORIZON:
        errors.append("baseline generic monitoring authority is stale")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_qsa_release_context_clarification") != PREDECESSOR:
        errors.append("baseline historical v0.10 authority changed")
    if baseline["authority"].get("trigger_aware_monitoring_horizon_post_bnr_event_check") != HORIZON:
        errors.append("baseline BNR-event authority missing")
    if baseline.get("manifest_version") != "1.15":
        errors.append("scientific baseline manifest must advance to 1.15")

    release = baseline["canonical_state"]["release_versioning"]
    if release["current_public_release"] != "0.3.0":
        errors.append("public release identity changed")
    if release["version_bump_required_now"] is not False:
        errors.append("monitoring-only change unexpectedly requires a version bump")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_bnr_event_check()
    if errors:
        raise RuntimeError("Post-BNR event monitoring audit failed:\n- " + "\n- ".join(errors))
    h = load(HORIZON)
    print(json.dumps({
        "status": "PASS",
        "registry_version": h["registry_version"],
        "completed_event_check": h["completed_event_checks"][0],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
        "response_values_authorized": h["current_disposition"]["response_values_authorized_for_inspection_now"],
        "accounting_spine_completion_authorized": h["current_disposition"]["accounting_spine_completion_authorized"],
        "behavioural_closure_authorized": h["current_disposition"]["behavioural_closure_authorized"],
    }, indent=2))


if __name__ == "__main__":
    main()
