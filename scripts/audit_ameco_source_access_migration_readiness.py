from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/calibration_validation/ameco_source_access_migration_readiness_2026_09_22.json"
HISTORICAL_CONTRACT = "model/calibration_validation/fiscal_reaction_capb_realtime_vintage_contract.json"
HORIZON = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_source_diagnostics.json"
EXPECTED_DECISION = "AMECO_ACCESS_MIGRATION_READY_FUTURE_RELEASE_NOT_YET_AVAILABLE_NO_REOPEN"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_ameco_source_access_migration_readiness() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT_PATH)
    contract = load(HISTORICAL_CONTRACT)
    horizon = load(HORIZON)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if a["decision"] != EXPECTED_DECISION:
        errors.append("AMECO source-access migration decision changed")
    if a["governing_trigger_horizon"] != HORIZON:
        errors.append("AMECO source-access assessment horizon pointer changed")
    if a["retained_historical_contract"] != HISTORICAL_CONTRACT:
        errors.append("AMECO historical contract pointer changed")

    official = a["official_current_state"]
    if official["latest_full_release_date"] != "2026-06-03":
        errors.append("AMECO latest full release date changed without a new review")
    if official["latest_full_release_label"] != "Spring 2026 Economic Forecast":
        errors.append("AMECO latest full release label changed without a new review")
    if official["autumn_2026_exact_release_date_published"] is not False:
        errors.append("Autumn 2026 exact release date may not be invented")
    if official["future_autumn_2026_exact_download_url_known"] is not False:
        errors.append("Autumn 2026 exact download URL may not be invented")
    if official["old_ameco_online_retirement_announced"] is not True:
        errors.append("AMECO old-interface retirement evidence lost")
    if official["new_interface"] != "ECFIN Redisstat":
        errors.append("AMECO new interface changed")
    for key in (
        "current_release_download_page",
        "archive_page",
        "bulk_and_api_documentation",
        "redisstat_catalogue_wadl",
        "redisstat_sdmx_2_1_wadl",
        "redisstat_dataflow_catalogue_endpoint",
        "redisstat_catalogue_toc_txt_endpoint",
        "redisstat_browser_ameco_root",
    ):
        value = official.get(key)
        if not isinstance(value, str) or not value.startswith("https://"):
            errors.append(f"AMECO official access endpoint missing: {key}")

    hist = a["historical_provenance_boundary"]
    spring = next((x for x in contract["releases"] if x["id"] == "spring_2026"), None)
    if spring is None:
        errors.append("historical CAPB contract lost Spring 2026 release")
    else:
        if spring["source_url"] != hist["spring_2026_source_url"]:
            errors.append("historical Spring 2026 AMECO URL changed")
        if spring["source_url"] != "https://ec.europa.eu/economy_finance/db_indicators/ameco/documents/ameco17.zip":
            errors.append("historical Spring 2026 AMECO URL no longer matches frozen contract")
    if contract["hard_rules"]["no_source_url_guessing"] is not True:
        errors.append("historical CAPB contract no longer prohibits source URL guessing")
    for key in (
        "historical_release_urls_may_be_rewritten",
        "retained_source_bytes_may_be_refetched_to_replace_repository_bytes",
        "legacy_url_pattern_may_be_used_to_guess_autumn_2026_url",
    ):
        if hist[key] is not False:
            errors.append(f"unsafe AMECO historical-source rule enabled: {key}")

    semantic = a["semantic_migration_anchor"]
    if semantic["target_variable_code"] != "UBLGBPS":
        errors.append("AMECO migration target code changed")
    if semantic["retained_romania_series_key"] != "ROM.1.0.319.0.UBLGBPS":
        errors.append("AMECO retained Romania UBLGBPS series key changed")
    if semantic["official_current_release_category"] != "Cyclical Adjustment of Public Finance Variables":
        errors.append("AMECO current-release semantic category changed")
    if semantic["official_current_release_category_url"] != "https://ec.europa.eu/economy_finance/db_indicators/ameco/documents/ameco17.zip":
        errors.append("AMECO current-release category URL changed")
    if semantic["redisstat_dataset_code_identified"] is not False or semantic["redisstat_dataset_code"] is not None:
        errors.append("Redisstat dataset code may not be fabricated before official identification")
    if semantic["redisstat_series_key_identified"] is not False or semantic["redisstat_series_key"] is not None:
        errors.append("Redisstat series key may not be fabricated before official identification")
    for key in (
        "chapter_number_may_be_assumed_to_equal_redisstat_dataset_code",
        "historical_ameco17_filename_may_be_assumed_to_equal_redisstat_dataset_code",
        "third_party_mirror_code_may_define_official_redisstat_identity",
    ):
        if semantic[key] is not False:
            errors.append(f"unsafe AMECO Redisstat identity inference enabled: {key}")
    if "{DATASET_CODE}" not in semantic["redisstat_api_rule"]:
        errors.append("AMECO Redisstat API dataset-code discovery rule changed")
    expected_discovery = {
        "https://webgate.ec.europa.eu/ecfin/redisstat/api/dissemination/sdmx/2.1/dataflow/ECFIN/all/latest?detail=allstubs",
        "https://webgate.ec.europa.eu/ecfin/redisstat/api/dissemination/catalogue/toc/txt?lang=en",
        "https://webgate.ec.europa.eu/ecfin/redisstat/databrowser/explore/all/AMECO?display=card&lang=en&sort=category",
    }
    if set(semantic.get("official_dataset_discovery_metadata", [])) != expected_discovery:
        errors.append("AMECO official Redisstat dataset-discovery metadata set changed")
    if semantic.get("current_discovery_status") != "OFFICIAL_NO_GUESS_DISCOVERY_ENDPOINTS_IDENTIFIED_DATASET_IDENTITY_NOT_YET_RETAINED":
        errors.append("AMECO Redisstat current discovery status changed")
    method = semantic.get("redisstat_dataset_code_discovery_method", "")
    for token in ("official Redisstat", "UBLGBPS", "Do not derive"):
        if token not in method:
            errors.append(f"AMECO Redisstat discovery method lost safeguard: {token}")

    protocol = a["future_release_discovery_protocol"]
    if len(protocol["allowed_discovery_surfaces"]) < 5:
        errors.append("AMECO future discovery surfaces are incomplete")
    if len(protocol.get("dataset_identity_discovery_order", [])) != 4:
        errors.append("AMECO Redisstat dataset-identity discovery order is incomplete")
    for key in (
        "redisstat_dataset_code_may_be_derived_from_legacy_chapter_number",
        "redisstat_dataset_code_may_be_derived_from_legacy_zip_name",
        "redisstat_dataset_code_may_be_adopted_from_third_party_mirror",
    ):
        if protocol.get(key) is not False:
            errors.append(f"unsafe Redisstat dataset-code discovery rule enabled: {key}")
    required = protocol["required_before_value_extraction"]
    for token in (
        "identify the exact official Autumn 2026 release/vintage",
        "retain exact provider bytes or exact reproducible API response",
        "verify the exact UBLGBPS structural-primary target semantics and release label/date",
        "create a new preregistered source-cycle contract before any modelling decision",
    ):
        if token not in required:
            errors.append(f"AMECO future protocol lost prerequisite: {token}")
    for key in (
        "source_url_guessing_authorized",
        "legacy_chapter_url_template_reuse_authorized",
        "silent_fallback_to_old_interface_authorized",
        "current_latest_release_repolling_before_autumn_release_authorized",
        "future_value_inspection_authorized_now",
    ):
        if protocol[key] is not False:
            errors.append(f"unsafe AMECO future discovery rule enabled: {key}")

    fiscal = next((x for x in horizon["horizons"] if x["id"] == "ameco_structural_primary_new_full_vintage"), None)
    if fiscal is None:
        errors.append("monitoring horizon lost AMECO fiscal trigger")
    else:
        if fiscal["next_check_type"] != "RELEASE_CONDITIONED_CHECK":
            errors.append("AMECO fiscal trigger is no longer release-conditioned")
        if fiscal["current_latest_full_release"] != "2026-06-03":
            errors.append("monitoring horizon AMECO latest release changed")
        if fiscal["action_before_release"] != "No repeated AMECO probing; remain in baseline hold.":
            errors.append("AMECO pre-release no-probing rule changed")

    adjudication = a["trigger_adjudication"]
    for key in (
        "autumn_2026_release_trigger_satisfied",
        "source_materialisation_reopen_active",
        "exact_future_release_url_known",
        "exact_future_release_bytes_known",
        "calibration_cycle_open",
        "parameter_estimation_authorized",
        "model_selection_authorized",
        "holdout_opening_authorized",
        "behavioural_closure_authorized",
        "system_dynamics_activation_authorized",
        "model_effect",
    ):
        if adjudication[key] is not False:
            errors.append(f"AMECO access migration unexpectedly authorizes {key}")
    if adjudication["fiscal_mechanism_classification"] != "DEFERRED":
        errors.append("fiscal mechanism classification changed")

    cv = model["calibration_validation"]
    if cv.get("ameco_source_access_migration_readiness") != ASSESSMENT_PATH:
        errors.append("model contract does not register AMECO access-migration assessment")
    if baseline["authority"].get("ameco_source_access_migration_readiness") != ASSESSMENT_PATH:
        errors.append("scientific baseline does not register AMECO access-migration assessment")

    return errors


def main() -> None:
    errors = audit_ameco_source_access_migration_readiness()
    if errors:
        raise RuntimeError("AMECO source-access migration readiness audit failed:\n- " + "\n- ".join(errors))
    a = load(ASSESSMENT_PATH)
    print(json.dumps({
        "status": "PASS",
        "decision": a["decision"],
        "latest_full_release": a["official_current_state"]["latest_full_release_date"],
        "old_interface_retirement_announced": True,
        "future_autumn_url_known": False,
        "release_trigger_satisfied": False,
        "model_effect": False,
    }, indent=2))


if __name__ == "__main__":
    main()
