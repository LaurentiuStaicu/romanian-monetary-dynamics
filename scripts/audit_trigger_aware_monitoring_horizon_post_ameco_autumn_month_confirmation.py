from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
PREDECESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_mof_recovery_execution_boundary.json"
EXPECTED_PRESS = "https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_26_1120/IP_26_1120_EN.pdf"
EXPECTED_AMECO = "https://economy-finance.ec.europa.eu/economic-research-and-databases/economic-databases/ameco-database_en"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    p = load(PREDECESSOR)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if h["registry_version"] != "0.9":
        errors.append("AMECO-month successor version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("AMECO-month successor predecessor changed")
    if [x["id"] for x in h["horizons"]] != [x["id"] for x in p["horizons"]]:
        errors.append("trigger identity/order changed")

    current = {x["id"]: x for x in h["horizons"]}
    prior = {x["id"]: x for x in p["horizons"]}
    for trigger_id in current:
        if trigger_id == "ameco_structural_primary_new_full_vintage":
            continue
        if current[trigger_id] != prior[trigger_id]:
            errors.append(f"non-AMECO trigger content changed: {trigger_id}")

    a = copy.deepcopy(current["ameco_structural_primary_new_full_vintage"])
    pa = prior["ameco_structural_primary_new_full_vintage"]
    timing = a.pop("official_timing_confirmation", None)
    pre_november = a.pop("pre_november_2026_release_presence_check_authorized", None)
    if a != pa:
        errors.append("AMECO trigger changed beyond timing refinement")
    if not isinstance(timing, dict):
        errors.append("AMECO official timing confirmation missing")
    else:
        if timing.get("expected_release_month") != "2026-11":
            errors.append("AMECO expected release month changed")
        if timing.get("exact_publication_date_identified") is not False:
            errors.append("AMECO exact publication date must remain unresolved")
        if timing.get("commission_press_release") != EXPECTED_PRESS:
            errors.append("AMECO timing press-release authority changed")
        if timing.get("ameco_transition_page") != EXPECTED_AMECO:
            errors.append("AMECO transition-page authority changed")
    if pre_november is not False:
        errors.append("pre-November AMECO release check unexpectedly authorized")

    rules = copy.deepcopy(h["monitoring_rules"])
    pre_rules = p["monitoring_rules"]
    if rules.pop("ameco_pre_november_2026_polling_disabled", None) is not True:
        errors.append("pre-November AMECO polling disable rule missing")
    if rules != pre_rules:
        errors.append("monitoring rules changed beyond AMECO timing refinement")

    d = copy.deepcopy(h["current_disposition"])
    pd = p["current_disposition"]
    expected = {
        "ameco_expected_release_month": "2026-11",
        "ameco_exact_release_date_identified": False,
        "ameco_pre_november_2026_check_authorized": False,
    }
    for key, value in expected.items():
        if d.pop(key, None) != value:
            errors.append(f"AMECO disposition timing field changed: {key}")
    if d != pd:
        errors.append("current disposition changed beyond AMECO timing refinement")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    if ms["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("model contract does not point to AMECO-month successor")
    if ms["immediate_previous_trigger_aware_monitoring_horizon"] != PREDECESSOR:
        errors.append("model contract immediate predecessor changed")
    if bs["trigger_aware_monitoring_horizon"] != HORIZON:
        errors.append("baseline does not point to AMECO-month successor")
    if bs["immediate_previous_trigger_aware_monitoring_horizon"] != PREDECESSOR:
        errors.append("baseline immediate predecessor changed")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != HORIZON:
        errors.append("baseline generic monitoring authority is stale")
    if baseline["authority"].get(
        "trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation"
    ) != HORIZON:
        errors.append("baseline AMECO-month authority missing")
    if baseline.get("manifest_version") != "1.13":
        errors.append("scientific baseline manifest version did not advance to 1.13")

    release = baseline["canonical_state"]["release_versioning"]
    if release["current_public_release"] != "0.3.0":
        errors.append("public release changed during AMECO timing refinement")
    if release["version_bump_required_now"] is not False:
        errors.append("AMECO timing refinement unexpectedly requires version bump")
    if h["current_disposition"]["any_monitoring_gate_open_now"] is not False:
        errors.append("AMECO timing refinement unexpectedly opened a monitoring gate")
    if h["current_disposition"]["ameco_release_trigger_satisfied"] is not False:
        errors.append("AMECO release trigger unexpectedly satisfied")
    if h["current_disposition"]["ameco_source_materialisation_reopen_active"] is not False:
        errors.append("AMECO source materialisation unexpectedly reopened")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_ameco_autumn_month_confirmation()
    if errors:
        raise RuntimeError("Post-AMECO autumn-month monitoring audit failed:\n- " + "\n- ".join(errors))
    h = load(HORIZON)
    print(json.dumps({
        "status": "PASS",
        "registry_version": h["registry_version"],
        "scientific_state": h["governing_state"]["current_scientific_state"],
        "ameco_expected_release_month": h["current_disposition"]["ameco_expected_release_month"],
        "ameco_release_trigger_satisfied": h["current_disposition"]["ameco_release_trigger_satisfied"],
        "next_dated_check": h["current_disposition"]["next_dated_check"],
    }, indent=2))


if __name__ == "__main__":
    main()
