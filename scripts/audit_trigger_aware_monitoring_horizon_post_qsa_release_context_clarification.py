from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
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
    if ms["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("model contract does not point to QSA-context successor")
    if ms["immediate_previous_trigger_aware_monitoring_horizon"] != PREDECESSOR:
        errors.append("model contract immediate predecessor changed")
    if bs["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("baseline does not point to QSA-context successor")
    if bs["immediate_previous_trigger_aware_monitoring_horizon"] != PREDECESSOR:
        errors.append("baseline immediate predecessor changed")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != HORIZON:
        errors.append("baseline generic monitoring authority is stale")
    if baseline["authority"].get(
        "trigger_aware_monitoring_horizon_post_qsa_release_context_clarification"
    ) != HORIZON:
        errors.append("baseline QSA-context authority missing")
    if baseline.get("manifest_version") != "1.14":
        errors.append("scientific baseline manifest version did not advance to 1.14")

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
