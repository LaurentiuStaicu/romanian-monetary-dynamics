from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "government_securities_supply_load_ecb_denominator_probe_assessment_2026_09_20.json"
)
VINTAGE_ROOT = (
    ROOT / "data/source_vintages/ecb-supply-load-denominator-candidates-2026-09-20"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_ecb_denominator_probe_assessment(
    assessment: dict,
    manifest: dict,
    denominator_review: dict,
    source_review: dict,
    boundary: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["probe_result"]["status"] != (
        "TWO_VALID_SERIES_ONE_PREREGISTERED_DOMESTIC_GFS_KEY_NOT_FOUND_NO_SELECTION"
    ):
        errors.append("ECB denominator probe assessment status changed")
    if assessment["probe_result"]["valid_candidate_count"] != 2:
        errors.append("ECB denominator valid-candidate count changed")
    if assessment["retained_vintage"]["repository_retained"] is not True:
        errors.append("ECB denominator probe vintage must remain retained")
    if assessment["retained_vintage"]["denominator_selected"] is not False:
        errors.append("ECB probe may not select a denominator")

    manifest_by_id = {
        item["candidate_id"]: item for item in manifest["candidates"]
    }
    csec_id = "ecb_csec_central_government_domestic_currency_debt_securities_stock"
    gfs_dom_id = (
        "ecb_gfs_general_government_domestic_currency_debt_securities_face_value_stock"
    )
    gfs_ctx_id = (
        "ecb_gfs_general_government_all_currency_debt_securities_face_value_context"
    )

    csec_manifest = manifest_by_id[csec_id]
    if csec_manifest["valid_nonempty_csv"] is not True:
        errors.append("CSEC domestic-currency candidate must remain valid")
    if csec_manifest["raw_sha256"] != (
        "13b182b9f920e40ec7c390ee8fed6d63972944d4807aeb9c9b91df2a61238b01"
    ):
        errors.append("CSEC retained raw CSV SHA-256 changed")
    csec_path = VINTAGE_ROOT / csec_manifest["raw_path"]
    if not csec_path.is_file():
        errors.append("CSEC retained raw CSV missing")
    else:
        if sha256_file(csec_path) != csec_manifest["raw_sha256"]:
            errors.append("CSEC retained raw CSV hash differs from manifest")
        rows = read_csv(csec_path)
        expected_period_values = {
            "2024-12": 385370.436527296,
            "2025-01": 385945.229057445,
            "2025-02": 389795.0453263939,
        }
        if len(rows) != 3:
            errors.append("CSEC retained row count changed")
        for row in rows:
            expected_dims = {
                "FREQ": "M",
                "REF_AREA": "RO",
                "REF_SECTOR": "S1311",
                "CONSOLIDATION": "N",
                "ACCOUNTING_ENTRY": "L",
                "STO": "LE",
                "INSTR_ASSET": "F3",
                "MATURITY": "T",
                "UNIT_MEASURE": "XDC",
                "CURRENCY_DENOM": "XDC",
                "VALUATION": "M",
                "PRICES": "V",
                "TRANSFORMATION": "N",
            }
            for key, value in expected_dims.items():
                if row.get(key) != value:
                    errors.append(f"CSEC provider dimension changed: {key}")
            period = row.get("TIME_PERIOD")
            if period not in expected_period_values:
                errors.append(f"CSEC unexpected period: {period}")
            elif float(row["OBS_VALUE"]) != expected_period_values[period]:
                errors.append(f"CSEC value changed for {period}")

    gfs_dom_manifest = manifest_by_id[gfs_dom_id]
    if gfs_dom_manifest["http_status"] != 404:
        errors.append("preregistered GFS domestic-currency key status changed")
    if gfs_dom_manifest["valid_nonempty_csv"] is not False:
        errors.append("preregistered GFS domestic-currency key may not be treated as valid")
    if gfs_dom_manifest.get("error_body_sha256") != (
        "21153141f33de7f5d439d7501d38c6c6f95cc912ac81882466e3c1897e183cef"
    ):
        errors.append("GFS domestic-key provider error identity changed")

    gfs_ctx_manifest = manifest_by_id[gfs_ctx_id]
    if gfs_ctx_manifest["valid_nonempty_csv"] is not True:
        errors.append("GFS all-currency context candidate must remain valid")
    if gfs_ctx_manifest["raw_sha256"] != (
        "546fde5e12ca01785273ae8ba53be5584af7fe891d5427acf355ca960fd56a12"
    ):
        errors.append("GFS context retained raw CSV SHA-256 changed")
    gfs_ctx_path = VINTAGE_ROOT / gfs_ctx_manifest["raw_path"]
    if not gfs_ctx_path.is_file():
        errors.append("GFS context retained raw CSV missing")
    else:
        if sha256_file(gfs_ctx_path) != gfs_ctx_manifest["raw_sha256"]:
            errors.append("GFS context retained raw CSV hash differs from manifest")
        rows = read_csv(gfs_ctx_path)
        expected_period_values = {
            "2024-12": 159666.697,
            "2025-01": 160122.577,
            "2025-02": 164820.177,
        }
        if len(rows) != 3:
            errors.append("GFS context retained row count changed")
        for row in rows:
            expected_dims = {
                "FREQ": "M",
                "REF_AREA": "RO",
                "REF_SECTOR": "S13",
                "CONSOLIDATION": "N",
                "ACCOUNTING_ENTRY": "L",
                "STO": "LE",
                "INSTR_ASSET": "F3",
                "MATURITY": "T",
                "UNIT_MEASURE": "EUR",
                "CURRENCY_DENOM": "_T",
                "VALUATION": "F",
                "PRICES": "V",
                "TRANSFORMATION": "N",
            }
            for key, value in expected_dims.items():
                if row.get(key) != value:
                    errors.append(f"GFS context provider dimension changed: {key}")
            period = row.get("TIME_PERIOD")
            if period not in expected_period_values:
                errors.append(f"GFS context unexpected period: {period}")
            elif float(row["OBS_VALUE"]) != expected_period_values[period]:
                errors.append(f"GFS context value changed for {period}")

    candidates = assessment["candidates"]
    if candidates[csec_id]["denominator_selected"] is not False:
        errors.append("assessment may not select CSEC denominator")
    if candidates[csec_id]["candidate_ratio_materialised"] is not False:
        errors.append("assessment may not materialise CSEC candidate ratio")
    if candidates[gfs_dom_id]["post_hoc_substitution_performed"] is not False:
        errors.append("assessment may not substitute another GFS series post hoc")
    if candidates[gfs_ctx_id]["denominator_selected"] is not False:
        errors.append("assessment may not select GFS context denominator")

    cross = assessment["cross_candidate_assessment"]
    if cross["selection_criterion"] != (
        "semantic_boundary_and_valuation_compatibility_before_numerical_behavior"
    ):
        errors.append("ECB comparison selection criterion changed")
    if cross["numerical_closeness_used_for_selection"] is not False:
        errors.append("ECB comparison may not select by numerical closeness")
    if cross["fit_or_correlation_inspected_for_selection"] is not False:
        errors.append("ECB comparison may not inspect fit/correlation for selection")
    if cross["candidate_ratios_computed"] is not False:
        errors.append("ECB comparison may not compute candidate ratios in this assessment")
    if cross["denominator_selected"] is not False:
        errors.append("ECB comparison may not select denominator")

    effect = assessment["scientific_effect"]
    if effect["ecb_candidate_source_retention_complete"] is not True:
        errors.append("ECB candidate source retention must remain complete")
    if effect["csec_candidate_validated"] is not True:
        errors.append("CSEC candidate validation changed")
    if effect["gfs_domestic_currency_candidate_validated"] is not False:
        errors.append("unavailable GFS domestic key may not be validated")
    if effect["gfs_context_candidate_validated"] is not True:
        errors.append("GFS context candidate validation changed")
    for key in (
        "denominator_selected",
        "supply_load_ratio_materialised",
        "government_securities_supply_pressure_node_resolved",
        "scalar_pressure_index_selected",
        "equation_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"ECB denominator assessment may not promote {key}")

    if denominator_review["ecb_denominator_probe_assessment"] != ASSESSMENT_PATH:
        errors.append("denominator boundary review lacks ECB assessment")
    if denominator_review["decision"] != (
        "NO_EXACT_ONE_TO_ONE_AUCTION_UNIVERSE_DENOMINATOR_SELECTED"
    ):
        errors.append("ECB assessment may not change denominator decision")
    if source_review["ecb_denominator_probe_assessment"] != ASSESSMENT_PATH:
        errors.append("supply-pressure source review lacks ECB assessment")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node["ecb_denominator_probe_assessment"] != ASSESSMENT_PATH:
        errors.append("supply-pressure node lacks ECB assessment")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("ECB assessment may not resolve supply-pressure node")
    if node["supply_load_denominator_selected"] is not False:
        errors.append("ECB assessment may not select denominator")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("ECB assessment may not authorize feedback")

    dynamic = model_contract["dynamic_core"]
    if dynamic["government_securities_supply_load_ecb_denominator_probe_assessment"] != ASSESSMENT_PATH:
        errors.append("model contract lacks ECB denominator assessment")
    if dynamic["government_securities_supply_load_denominator_status"] != (
        "NO_EXACT_ONE_TO_ONE_AUCTION_UNIVERSE_DENOMINATOR_SELECTED"
    ):
        errors.append("model contract denominator status changed")
    if dynamic["government_securities_supply_load_ratio_materialisation_authorized"] is not False:
        errors.append("model contract may not authorize supply-load ratio")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_reference_auction_supply_full_2025_source_vintage"
    ):
        errors.append("model contract next task changed")

    next_gate = assessment["next_gate"]
    if next_gate["id"] != "mof_announced_RON_primary_supply_reference_mode_contract":
        errors.append("ECB assessment next gate changed")
    if next_gate["authorization"] != (
        "SOURCE_CONTRACT_AND_EXACT_REFERENCE_MODE_MATERIALISATION_ONLY"
    ):
        errors.append("ECB assessment next-gate authorization changed")
    if next_gate["may_select_denominator_from_numerical_fit"] is not False:
        errors.append("next gate may not select denominator from numerical fit")
    if next_gate["may_promote_proxy_to_supply_pressure"] is not False:
        errors.append("next gate may not promote proxy to supply pressure")
    if next_gate["may_estimate_supply_to_yield_effect"] is not False:
        errors.append("next gate may not estimate supply-to-yield effect")
    if next_gate["may_activate_feedback"] is not False:
        errors.append("next gate may not activate feedback")

    return errors


def main() -> None:
    assessment = load(ASSESSMENT_PATH)
    manifest = load(
        "data/source_vintages/ecb-supply-load-denominator-candidates-2026-09-20/"
        "ecb_denominator_probe_manifest.json"
    )
    denominator_review = load(
        "model/dynamics/government_securities_supply_load_denominator_boundary_review_2026_09_20.json"
    )
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    model_contract = load("model/registries/model_contract.json")

    errors = audit_ecb_denominator_probe_assessment(
        assessment,
        manifest,
        denominator_review,
        source_review,
        boundary,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "ECB supply-load denominator probe assessment failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "valid_provider_series": 2,
                "csec_domestic_currency_market_value": "VALID",
                "gfs_domestic_currency_face_value_preregistered_key": "NOT_FOUND",
                "gfs_all_currency_face_value_context": "VALID_CONTEXT_ONLY",
                "denominator_selected": False,
                "supply_load_ratio_materialised": False,
                "feedback_activation_authorized": False,
                "next_gate": "mof_announced_RON_primary_supply_reference_mode_contract",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
