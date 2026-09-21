from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    "model/dynamics/"
    "mof_realized_financing_channel_materialisation_contract_2026_09_21.json"
)
FINANCING_REVIEW_PATH = "model/dynamics/financing_channel_allocation_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "FROZEN_CUMULATIVE_YTD_ONLY_MONTHLY_DIFFERENCING_NOT_AUTHORIZED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_mof_realized_financing_channel_materialisation_contract(
    contract: dict,
    generic_contract: dict,
    financing_review: dict,
    boundary: dict,
    readiness: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if contract["contract_id"] != "mof_realized_financing_channel_materialisation_contract":
        errors.append("realized-financing contract id changed")
    if contract["governing_boundary_review"] != FINANCING_REVIEW_PATH:
        errors.append("realized-financing governing review changed")

    target = contract["target"]
    if target["target_id"] != "mof_realized_financing_channels_cumulative_ytd":
        errors.append("realized-financing target id changed")
    if target["scientific_role"] != "DESCRIPTIVE_MULTI_CHANNEL_FINANCING_VECTOR":
        errors.append("realized-financing scientific role changed")
    if target["canonical_government_debt_issuance_node"] is not False:
        errors.append("contract may not promote generic debt-issuance node")
    if target["government_financing_need_equivalent"] is not False:
        errors.append("realized borrowing may not equal government financing need")
    if target["securities_only"] is not False:
        errors.append("realized-financing vector may not be relabelled securities-only")

    source = contract["source_family"]
    if source["institution"] != "Romanian Ministry of Finance":
        errors.append("Ministry source institution changed")
    if source["section"] != "Actual borrowings in 2025 / by instrument, currency and market":
        errors.append("Ministry source section changed")
    if source["raw_retention_required"] is not True:
        errors.append("raw source retention must remain required")
    if source["ocr_authorized"] is not False:
        errors.append("OCR may not be authorized")
    if source["manual_chart_digitisation_authorized"] is not False:
        errors.append("manual chart digitisation may not be authorized")

    known = {item["source_id"]: item for item in source["known_exact_sources"]}
    if set(known) != {
        "mof_public_debt_report_january_2025",
        "mof_public_debt_report_february_2025",
    }:
        errors.append("pilot exact-source set changed")
    if known["mof_public_debt_report_january_2025"]["url"] != (
        "https://mfinante.gov.ro/static/10/Mfp/buletin/executii/Publicdebtreport012025.pdf"
    ):
        errors.append("January Ministry report URL changed")
    if known["mof_public_debt_report_february_2025"]["url"] != (
        "https://mfinante.gov.ro/static/10/Mfp/buletin/executii/Publicdebtreport022025.pdf"
    ):
        errors.append("February Ministry report URL changed")

    required_ids = {item["field_id"] for item in contract["required_observables"]}
    expected_required = {
        "report_cutoff_date",
        "mof_t_bills_cumulative_ytd",
        "retail_bonds_cumulative_ytd",
        "ron_treasury_bonds_cumulative_ytd",
        "eur_treasury_bonds_cumulative_ytd",
        "eurobonds_cumulative_ytd",
        "rrf_pnrr_loan_drawings_cumulative_ytd",
        "loans_cumulative_ytd",
        "domestic_market_total_cumulative_ytd",
        "external_market_total_cumulative_ytd",
        "central_government_total_cumulative_ytd",
        "local_government_borrowing_cumulative_ytd",
        "cash_management_instruments_cumulative_ytd",
    }
    if required_ids != expected_required:
        errors.append("required financing-channel observable set changed")

    by_id = {item["field_id"]: item for item in contract["required_observables"]}
    if by_id["rrf_pnrr_loan_drawings_cumulative_ytd"]["securities_instrument"] is not False:
        errors.append("RRF drawings may not be relabelled securities")
    if by_id["loans_cumulative_ytd"]["securities_instrument"] is not False:
        errors.append("loans may not be relabelled securities")
    if by_id["local_government_borrowing_cumulative_ytd"]["may_enter_central_government_total"] is not False:
        errors.append("local-government borrowing may not enter central-government total")
    if by_id["cash_management_instruments_cumulative_ytd"][
        "may_be_silently_merged_into_structural_financing_channels"
    ] is not False:
        errors.append("cash-management instruments may not be silently merged")

    pilot = contract["pilot_exact_values"]
    jan = pilot["2025-01"]
    feb = pilot["2025-02"]
    expected_jan = {
        "mof_t_bills": 1307.7,
        "retail_bonds": 2125.2,
        "ron_treasury_bonds": 5926.4,
        "eur_treasury_bonds": 0.0,
        "eurobonds": 0.0,
        "loans": 43.4,
        "central_government_total": 9402.7,
    }
    expected_feb = {
        "mof_t_bills": 2427.7,
        "retail_bonds": 11358.6,
        "ron_treasury_bonds": 14870.5,
        "eur_treasury_bonds": 0.0,
        "eurobonds": 19903.0,
        "loans": 2734.6,
        "central_government_total": 51294.4,
    }
    for key, value in expected_jan.items():
        if jan[key] != value:
            errors.append(f"January pilot value changed: {key}")
    for key, value in expected_feb.items():
        if feb[key] != value:
            errors.append(f"February pilot value changed: {key}")
    if pilot["role"] != "SOURCE_DEFINITION_ANCHORS_ONLY_NOT_MONTHLY_FLOW_SERIES":
        errors.append("pilot values may not become monthly flow series")

    currency = contract["currency_and_conversion_contract"]
    for key in (
        "provider_published_RON_equivalent_values_may_be_retained_exactly",
        "provider_conversion_metadata_must_be_retained_per_vintage",
        "same_conversion_convention_may_not_be_assumed_across_vintages",
        "native_currency_fields_must_remain_separate_when_explicitly_published",
    ):
        if currency[key] is not True:
            errors.append(f"currency/conversion guard changed: {key}")
    for key in (
        "cross_currency_reaggregation_by_RMD_authorized_now",
        "exchange_rate_series_selected_by_this_contract",
    ):
        if currency[key] is not False:
            errors.append(f"currency contract may not authorize {key}")

    revision = contract["revision_and_vintage_contract"]
    for key in (
        "each_monthly_report_is_a_distinct_source_vintage",
        "later_report_may_revise_prior_cumulative_values",
        "later_vintage_may_not_silently_overwrite_earlier_vintage",
        "revision_check_required_before_monthly_differencing",
        "definition_check_required_before_monthly_differencing",
        "reporting_cutoff_alignment_required_before_monthly_differencing",
        "negative_difference_may_not_be_interpreted_as_negative_borrowing_without_revision_or_operation_review",
    ):
        if revision[key] is not True:
            errors.append(f"revision/vintage guard changed: {key}")

    gate = contract["monthly_increment_gate"]
    if gate["monthly_differencing_authorized_now"] is not False:
        errors.append("monthly differencing may not be authorized")
    if gate["equation_status_now"] != "NOT_AUTHORIZED":
        errors.append("monthly-increment equation status changed")
    if len(gate["requirements_before_any_difference"]) < 7:
        errors.append("monthly-differencing prerequisites weakened")

    rules = contract["channel_boundary_rules"]
    if rules["BNR_domestic_primary_market_series_is_separate"] is not True:
        errors.append("BNR boundary separation changed")
    if rules["equality_with_BNR_is_not_a_validation_requirement"] is not True:
        errors.append("BNR equality guard changed")
    if rules["BNR_series_may_not_be_inferred_by_subtraction"] is not True:
        errors.append("BNR series may not be inferred by subtraction")
    if rules["securities_only_subset_must_exclude_loans_and_RRF_drawings"] is not True:
        errors.append("securities-only boundary guard changed")
    if rules["total_realized_borrowing_may_not_be_relabelled_government_financing_need"] is not True:
        errors.append("realized borrowing may not be relabelled GFN")

    for key, value in contract["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    effect = contract["scientific_effect"]
    if effect["source_contract_frozen"] is not True:
        errors.append("source contract must remain frozen")
    if effect["cumulative_ytd_materialisation_authorized_after_raw_source_retention"] is not True:
        errors.append("cumulative-YTD materialisation gate changed")
    for key in (
        "monthly_increment_materialisation_authorized",
        "financing_channel_allocation_identified",
        "government_debt_issuance_node_resolved",
        "government_financing_need_node_resolved",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"contract may not promote {key}")

    next_gate = contract["next_gate"]
    if next_gate["id"] != "mof_realized_financing_channel_source_vintage_probe":
        errors.append("realized-financing next gate changed")
    if next_gate["authorization"] != (
        "OFFICIAL_SOURCE_RETENTION_AND_CUMULATIVE_YTD_EXTRACTION_ONLY"
    ):
        errors.append("realized-financing next gate authorization changed")
    if next_gate["may_retain_raw_sources"] is not True:
        errors.append("source-vintage probe must allow raw retention")
    if next_gate["may_extract_published_cumulative_ytd_values"] is not True:
        errors.append("source-vintage probe must allow exact cumulative extraction")
    for key in (
        "may_difference_cumulative_values",
        "may_infer_channel_residuals",
        "may_estimate_allocation_shares",
        "may_promote_generic_debt_issuance_node",
        "may_activate_feedback",
    ):
        if next_gate[key] is not False:
            errors.append(f"source-vintage probe may not authorize {key}")

    generic = generic_contract["paths"]["mof_actual_borrowing"]
    if generic["target_id"] != "government_total_realized_borrowing_or_securities_funding":
        errors.append("generic Ministry borrowing target changed")
    if generic["preferred_frequency"] != "monthly_report_cumulative_ytd":
        errors.append("generic Ministry borrowing frequency changed")
    if "month-to-month differencing may be executed only after all above gates pass" not in generic[
        "monthly_increment_gate"
    ]:
        errors.append("generic Ministry differencing guard changed")

    if financing_review["next_gate"]["id"] != "mof_realized_financing_channel_materialisation_contract":
        errors.append("governing review historical next gate changed")

    for node_id in ("government_financing_need", "government_debt_issuance"):
        node = next(x for x in boundary["variables"] if x["id"] == node_id)
        if node.get("financing_channel_materialisation_contract") != CONTRACT_PATH:
            errors.append(f"{node_id}: source contract missing")
        if node.get("financing_channel_materialisation_contract_status") != STATUS:
            errors.append(f"{node_id}: source contract status changed")
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: source contract may not resolve node")
        if node["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: source contract may not activate node")

    links = [
        x for x in readiness["links"]
        if x["from"] == "government_financing_need"
        and x["to"] == "government_debt_issuance"
    ]
    if len(links) != 2:
        errors.append("expected two financing-channel links")
    for link in links:
        if link.get("financing_channel_materialisation_contract") != CONTRACT_PATH:
            errors.append(f"{link['loop_id']}: source contract missing")
        if link.get("monthly_differencing_authorized") is not False:
            errors.append(f"{link['loop_id']}: monthly differencing may not be authorized")
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['loop_id']}: source contract may not make link equation-ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['loop_id']}: source contract may not activate link")

    bridge = next(
        x for x in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if x["id"] == "financing_channel_allocation"
    )
    if bridge.get("materialisation_contract") != CONTRACT_PATH:
        errors.append("preregistration financing-channel source contract missing")
    if bridge.get("materialisation_contract_status") != STATUS:
        errors.append("preregistration financing-channel contract status changed")
    if bridge.get("monthly_differencing_authorized") is not False:
        errors.append("preregistration may not authorize monthly differencing")
    if bridge.get("cumulative_ytd_materialisation_authorized_after_raw_retention") is not True:
        errors.append("preregistration cumulative-YTD gate changed")
    if prereg["next_independent_bridge_task"]["id"] != (
        "government_refinancing_interest_loop_terminal_assessment"
    ):
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_realized_financing_channel_materialisation_contract") != CONTRACT_PATH:
        errors.append("model contract lacks realized-financing source contract")
    if dynamic.get("mof_realized_financing_channel_materialisation_contract_status") != STATUS:
        errors.append("model contract realized-financing contract status changed")
    if dynamic.get("mof_realized_financing_channel_monthly_differencing_authorized") is not False:
        errors.append("model contract may not authorize monthly differencing")
    if dynamic.get(
        "mof_realized_financing_channel_cumulative_ytd_materialisation_authorized_after_raw_retention"
    ) is not True:
        errors.append("model contract cumulative-YTD gate changed")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "government_refinancing_interest_loop_terminal_assessment"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("source contract may not activate issuance-yield feedback")

    if baseline["authority"].get("mof_realized_financing_channel_materialisation_contract") != CONTRACT_PATH:
        errors.append("scientific baseline lacks realized-financing source-contract authority")

    return errors


def main() -> None:
    errors = audit_mof_realized_financing_channel_materialisation_contract(
        load(CONTRACT_PATH),
        load("model/dynamics/government_debt_issuance_materialisation_contract.json"),
        load(FINANCING_REVIEW_PATH),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "MoF realized-financing channel materialisation-contract audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "target": "mof_realized_financing_channels_cumulative_ytd",
        "monthly_differencing_authorized": False,
        "cumulative_ytd_materialisation_authorized_after_raw_retention": True,
        "generic_debt_issuance_node_resolved": False,
        "feedback_activation_authorized": False,
        "next_gate": "mof_realized_financing_channel_source_vintage_probe",
    }, indent=2))


if __name__ == "__main__":
    main()
