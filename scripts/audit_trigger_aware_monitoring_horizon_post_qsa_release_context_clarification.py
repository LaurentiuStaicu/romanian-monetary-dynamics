from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
NEXT_HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_10_22_post_bnr_event_check.json"
CALENDAR = "https://www.ecb.europa.eu/press/calendars/statscal/eaa/html/stprfi.en.html"
DATASET_INFO = "https://data.ecb.europa.eu/data/datasets/QSA/data-information"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_qsa_release_context_clarification() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    p = load(PREDECESSOR)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")
    status_text = (ROOT / "STATUS.md").read_text(encoding="utf-8")

    stale_provenance_handoff = (
        "Otherwise continuation is governed by "
        "`model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_ameco_access_protocol.json`"
    )
    if stale_provenance_handoff in status_text:
        errors.append("STATUS presents the historical provenance horizon as the current governing horizon")
    current_handoff_pointer = (
        "current continuation follows the canonical "
        "`scientific_stage.trigger_aware_monitoring_horizon` pointer in "
        "`model/registries/model_contract.json`"
    )
    if current_handoff_pointer not in status_text:
        errors.append("STATUS provenance handoff does not defer current continuation to the canonical model-contract pointer")

    if h["registry_version"] != "0.10":
        errors.append("QSA-context successor version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("QSA-context successor predecessor changed")
    if [x["id"] for x in h["horizons"]] != [x["id"] for x in p["horizons"]]:
        errors.append("trigger identity/order changed")

    current = {x["id"]: x for x in h["horizons"]}
    prior = {x["id"]: x for x in p["horizons"]}
    for trigger_id in current:
        if trigger_id == "accounting_counterpart_topology":
            continue
        if current[trigger_id] != prior[trigger_id]:
            errors.append(f"non-accounting trigger content changed: {trigger_id}")

    q = copy.deepcopy(current["accounting_counterpart_topology"])
    pq = copy.deepcopy(prior["accounting_counterpart_topology"])
    context = q.pop("current_known_release_context", None)
    pq.pop("current_known_release_context", None)
    if q != pq:
        errors.append("accounting counterpart trigger changed beyond release context")
    if not isinstance(context, dict):
        errors.append("QSA release context missing")
    else:
        if context.get("ECB_QSA_households_nfc_release") != "2026-10-02":
            errors.append("QSA households/NFC release date changed")
        if context.get("ECB_QSA_full_institutional_sector_release") != "2026-10-28":
            errors.append("QSA full institutional-sector release date changed")
        if context.get("ECB_QSA_release_calendar") != CALENDAR:
            errors.append("QSA release-calendar authority changed")
        if context.get("ECB_QSA_dataset_information") != DATASET_INFO:
            errors.append("QSA dataset-information authority changed")
        rule = context.get("rule", "")
        if "do not reopen" not in rule or "changed dataset topology" not in rule:
            errors.append("QSA routine-release non-reopen rule weakened")

    if h["monitoring_rules"] != p["monitoring_rules"]:
        errors.append("monitoring rules changed during QSA context clarification")
    if h["current_disposition"] != p["current_disposition"]:
        errors.append("current disposition changed during QSA context clarification")
    if h["governing_state"] != p["governing_state"]:
        errors.append("governing scientific state changed during QSA context clarification")
    if h.get("counterpart_probe_execution_boundary") != p.get("counterpart_probe_execution_boundary"):
        errors.append("counterpart execution boundary changed during QSA context clarification")
    if h.get("mof_full_2025_recovery_execution_boundary") != p.get("mof_full_2025_recovery_execution_boundary"):
        errors.append("MoF recovery execution boundary changed during QSA context clarification")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    current_horizon = ms.get("trigger_aware_monitoring_horizon")
    if current_horizon not in (HORIZON, NEXT_HORIZON):
        errors.append("current monitoring pointer is neither historical v0.10 nor its declared BNR-event successor")
    expected_current_predecessor = PREDECESSOR if current_horizon == HORIZON else HORIZON
    if ms.get("immediate_previous_trigger_aware_monitoring_horizon") != expected_current_predecessor:
        errors.append("model contract immediate monitoring predecessor is stale")
    if bs.get("trigger_aware_monitoring_horizon") != current_horizon:
        errors.append("baseline current monitoring pointer is stale relative to model contract")
    if bs.get("immediate_previous_trigger_aware_monitoring_horizon") != expected_current_predecessor:
        errors.append("baseline immediate monitoring predecessor is stale")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != current_horizon:
        errors.append("baseline generic monitoring authority is stale")
    if baseline["authority"].get(
        "trigger_aware_monitoring_horizon_post_qsa_release_context_clarification"
    ) != HORIZON:
        errors.append("baseline historical v0.10 authority missing or changed")
    expected_manifest_version = "1.14" if current_horizon == HORIZON else "1.15"
    if baseline.get("manifest_version") != expected_manifest_version:
        errors.append("scientific baseline manifest version is inconsistent with the current monitoring successor")

    historical_status = (
        "REFERENCE_MODES_10_OF_10_NO_GATE_OPEN_COUNTERPART_PROBES_TRIGGER_CONDITIONED_"
        "MOF_FULL_2025_RECOVERY_MANUAL_ONLY_ACTIVE_POLLING_FALSE_AMECO_ACCESS_PROTOCOL_"
        "BOUND_DATASET_IDENTITY_UNRESOLVED_AMECO_AUTUMN_2026_WINDOW_2026_11_NO_EXACT_DAY_"
        "QSA_Q2_2026_CONTEXT_2026_10_02_HOUSEHOLDS_NFC_2026_10_28_FULL_INSTITUTIONAL_SECTOR_"
        "ROUTINE_RELEASES_NO_REOPEN_NEXT_DATED_CHECK_2026_10_08_"
        "F4_STOCK_EVIDENCE_WINDOW_AFTER_2026_10_31"
    )
    if current_horizon == HORIZON:
        if ms.get("trigger_aware_monitoring_horizon_status") != historical_status:
            errors.append("model contract historical v0.10 status summary is stale")
    else:
        status = ms.get("trigger_aware_monitoring_horizon_status", "")
        if "NEXT_DATED_CHECK_2026_11_12" not in status or "NEXT_DATED_CHECK_2026_10_08" in status:
            errors.append("current successor status is inconsistent with the historical v0.10 handoff")

    d = h["current_disposition"]
    for key in (
        "any_monitoring_gate_open_now",
        "accounting_counterpart_topology_trigger_satisfied",
        "accounting_counterpart_probe_rerun_authorized_now",
        "estimation_or_refit_authorized",
        "holdout_opening_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
    ):
        if d.get(key) is not False:
            errors.append(f"QSA clarification unexpectedly authorizes {key}")

    release = baseline["canonical_state"]["release_versioning"]
    if release["current_public_release"] != "0.3.0":
        errors.append("public release changed during QSA context clarification")
    if release["version_bump_required_now"] is not False:
        errors.append("QSA context clarification unexpectedly requires version bump")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_qsa_release_context_clarification()
    if errors:
        raise RuntimeError("Post-QSA release-context monitoring audit failed:\n- " + "\n- ".join(errors))
    h = load(HORIZON)
    q = next(x for x in h["horizons"] if x["id"] == "accounting_counterpart_topology")
    print(json.dumps({
        "status": "PASS",
        "registry_version": h["registry_version"],
        "households_nfc_release": q["current_known_release_context"]["ECB_QSA_households_nfc_release"],
        "full_institutional_sector_release": q["current_known_release_context"]["ECB_QSA_full_institutional_sector_release"],
        "accounting_trigger_satisfied": h["current_disposition"]["accounting_counterpart_topology_trigger_satisfied"],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
    }, indent=2))


if __name__ == "__main__":
    main()
