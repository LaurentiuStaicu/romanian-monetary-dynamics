from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    "model/dynamics/"
    "government_securities_supply_load_denominator_boundary_review_2026_09_20.json"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_supply_load_denominator_boundary(
    review: dict,
    source_review: dict,
    probe_assessment: dict,
    boundary: dict,
    readiness: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "NO_EXACT_ONE_TO_ONE_AUCTION_UNIVERSE_DENOMINATOR_SELECTED"
    ):
        errors.append("supply-load denominator decision changed")

    numerator = review["numerator_boundary"]
    if numerator["concept"] != "announced RON amount in Ministry domestic primary-market auctions":
        errors.append("supply-load numerator concept changed")
    if numerator["january_2025_exact_announced_RON_million"] != 5770.0:
        errors.append("January exact announced numerator changed")
    if numerator["status"] != "EXACT_NATIVE_TABLE_VALUE_AVAILABLE":
        errors.append("numerator extractability status changed")

    candidates = {
        item["candidate_id"]: item
        for item in review["denominator_candidates"]
    }
    expected = {
        "mof_RON_domestic_market_holdings_nominal",
        "ecb_csec_central_government_domestic_currency_debt_securities_stock",
        "ecb_gfs_general_government_debt_securities_face_value_stock",
    }
    if set(candidates) != expected:
        errors.append(
            "denominator candidate set changed: "
            f"expected={sorted(expected)}, observed={sorted(candidates)}"
        )

    mof = candidates["mof_RON_domestic_market_holdings_nominal"]
    if mof["january_2025_exact_value_RON_million"] != 381933.8:
        errors.append("Ministry nominal RON holdings candidate changed")
    if mof["valuation"] != "available at nominal value":
        errors.append("Ministry holdings valuation changed")
    if mof["exact_auction_universe_equivalence_established"] is not False:
        errors.append("Ministry holdings may not claim exact auction-universe equivalence")
    if mof["selected"] is not False:
        errors.append("Ministry holdings denominator may not be selected")

    csec = candidates[
        "ecb_csec_central_government_domestic_currency_debt_securities_stock"
    ]
    if csec["valuation"] != "market value":
        errors.append("CSEC valuation changed")
    if csec["sector_boundary"] != "central government excluding social security (S1311)":
        errors.append("CSEC sector boundary changed")
    if csec["selected"] is not False:
        errors.append("CSEC denominator may not be selected")

    gfs = candidates[
        "ecb_gfs_general_government_debt_securities_face_value_stock"
    ]
    if gfs["valuation"] != "face value":
        errors.append("GFS valuation changed")
    if gfs["sector_boundary"] != "general government (S13)":
        errors.append("GFS sector boundary changed")
    if gfs["selected"] is not False:
        errors.append("GFS denominator may not be selected")

    flash = review["flash_report_consistency_check"]
    if flash["components_reconcile_to_headline"] is not False:
        errors.append("Flash headline/components may not be claimed reconciled")
    if flash["eligible_as_denominator"] is not False:
        errors.append("Flash headline may not be used as denominator")

    dimensional = review["dimensional_rule"]
    if dimensional["ratio_unit"] != "dimensionless":
        errors.append("supply-load ratio unit changed")
    if dimensional["valuation_mismatch_requires_explicit_bridge"] is not True:
        errors.append("valuation mismatch must require explicit bridge")
    if dimensional["sector_or_market_scope_mismatch_requires_explicit_bridge"] is not True:
        errors.append("scope mismatch must require explicit bridge")

    effect = review["decision_effect"]
    for key in (
        "supply_load_ratio_materialisation_authorized",
        "mof_holdings_denominator_selected",
        "ecb_csec_denominator_selected",
        "ecb_gfs_denominator_selected",
        "government_securities_supply_pressure_node_resolved",
        "scalar_pressure_index_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"denominator review may not promote {key}")

    next_task = review["next_task"]
    if next_task["id"] != "mof_announced_RON_primary_supply_reference_mode_contract":
        errors.append("denominator review next task changed")
    if next_task["authorization"] != (
        "SOURCE_CONTRACT_AND_EXACT_REFERENCE_MODE_MATERIALISATION_ONLY"
    ):
        errors.append("denominator next-task authorization changed")
    if next_task["selection_criterion"] != (
        "announced_supply_reference_mode_does_not_require_stock_denominator"
    ):
        errors.append("denominator selection criterion changed")
    if next_task["may_promote_any_ratio_to_supply_pressure"] is not False:
        errors.append("candidate comparison may not promote ratio to supply pressure")
    if next_task["may_activate_feedback"] is not False:
        errors.append("candidate comparison may not activate feedback")

    if source_review["supply_load_denominator_boundary_review"] != REVIEW_PATH:
        errors.append("supply-pressure source review lacks denominator boundary review")
    source_candidate = next(
        item for item in source_review["candidate_observable_vector"]
        if item["candidate_id"] == "domestic_RON_primary_market_supply_load"
    )
    if source_candidate["denominator_boundary_review"] != REVIEW_PATH:
        errors.append("supply-load candidate lacks denominator boundary review")
    if source_candidate["denominator_selected"] is not False:
        errors.append("source review selected a denominator")

    if probe_assessment["denominator_boundary_review"] != REVIEW_PATH:
        errors.append("probe assessment lacks denominator boundary review")
    if probe_assessment["candidate_readiness"][
        "domestic_RON_primary_market_supply_load"
    ]["ratio_materialisation_authorized"] is not False:
        errors.append("probe assessment may not authorize supply-load ratio")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node["supply_load_denominator_boundary_review"] != REVIEW_PATH:
        errors.append("supply-pressure node lacks denominator boundary review")
    if node["supply_load_denominator_selected"] is not False:
        errors.append("supply-pressure node selected denominator")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("denominator review may not resolve supply-pressure node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("denominator review may not authorize feedback")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link["supply_load_denominator_boundary_review"] != REVIEW_PATH:
        errors.append("issuance-pressure link lacks denominator review")
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
    ):
        errors.append("issuance-pressure link denominator status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("denominator review may not make link equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("denominator review may not activate link")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge["denominator_boundary_review"] != REVIEW_PATH:
        errors.append("issuance-pressure bridge lacks denominator review")
    if bridge["status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
    ):
        errors.append("issuance-pressure bridge status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic["government_securities_supply_load_denominator_boundary_review"] != REVIEW_PATH:
        errors.append("model contract lacks denominator boundary review")
    if dynamic["government_securities_supply_load_denominator_status"] != (
        "NO_EXACT_ONE_TO_ONE_AUCTION_UNIVERSE_DENOMINATOR_SELECTED"
    ):
        errors.append("model contract denominator status changed")
    if dynamic["government_securities_supply_load_ratio_materialisation_authorized"] is not False:
        errors.append("model contract may not authorize supply-load ratio")
    if dynamic.get("government_securities_supply_stock_normalisation_required") is not False:
        errors.append("model contract may not require stock normalization for first reference mode")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery"
    ):
        errors.append("model contract next task changed")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    probe_assessment = load(
        "model/dynamics/government_securities_supply_pressure_source_vintage_probe_assessment_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_supply_load_denominator_boundary(
        review,
        source_review,
        probe_assessment,
        boundary,
        readiness,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Government securities supply-load denominator boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "candidate_id": "domestic_RON_primary_market_supply_load",
                "denominator_candidates": 3,
                "denominator_selected": False,
                "ratio_materialisation_authorized": False,
                "pressure_node_resolved": False,
                "feedback_activation_authorized": False,
                "next_task": "mof_announced_RON_primary_supply_reference_mode_contract",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
