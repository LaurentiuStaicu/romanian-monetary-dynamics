from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_debt_issuance_source_boundary(
    review: dict,
    contract: dict,
    boundary: dict,
    feedback: dict,
    reference_modes: dict,
    sovereign_review: dict,
) -> list[str]:
    errors: list[str] = []

    if review.get("verdict") != (
        "SOURCE_FAMILIES_FOUND_GENERIC_NODE_SEMANTICALLY_OVERLOADED_"
        "BOUNDARY_REMAINS_UNRESOLVED"
    ):
        errors.append("government issuance source-boundary verdict changed")

    finding = review["structural_finding"]
    if finding.get("semantic_overload_detected") is not True:
        errors.append("semantic overload must remain explicitly detected")
    if (
        finding.get(
            "current_generic_node_can_serve_both_loops_without_additional_boundary_work"
        )
        is not False
    ):
        errors.append("generic issuance node may not be treated as ready for both loops")
    if finding.get("no_topology_change_in_this_review") is not True:
        errors.append("source screening may not change feedback topology")

    candidate_ids = {
        item["id"] for item in finding.get("candidate_future_split", [])
    }
    expected_candidates = {
        "domestic_primary_market_government_securities_gross_issuance",
        "government_total_realized_borrowing_or_securities_funding",
    }
    if candidate_ids != expected_candidates:
        errors.append(
            "candidate issuance boundary split changed unexpectedly; "
            f"expected={sorted(expected_candidates)}, observed={sorted(candidate_ids)}"
        )

    bnr = next(
        item
        for item in review["sources"]
        if item["id"] == "bnr_monthly_bulletin_government_securities"
    )
    mof = next(
        item
        for item in review["sources"]
        if item["id"] == "mof_monthly_public_debt_report_actual_borrowing"
    )
    if bnr["frequency"] != "monthly":
        errors.append("BNR issuance source must remain monthly")
    if (
        bnr["exact_2025_examples"]["2025-01"][
            "discount_treasury_certificates_million_RON"
        ]
        != 1907.7
    ):
        errors.append("BNR January 2025 source example changed")
    if (
        bnr["exact_2025_examples"]["2025-02"][
            "interest_bearing_government_bonds_allotted_million_RON"
        ]
        != 10620.2
    ):
        errors.append("BNR February 2025 source example changed")
    if (
        mof["exact_2025_examples"]["2025-01_cumulative_million_RON"][
            "central_government_total"
        ]
        != 9402.7
    ):
        errors.append("Ministry January 2025 cumulative borrowing example changed")
    if (
        mof["exact_2025_examples"]["2025-02_cumulative_million_RON"][
            "central_government_total"
        ]
        != 51294.4
    ):
        errors.append("Ministry February 2025 cumulative borrowing example changed")

    comparison = review["semantic_comparison"]
    if comparison["qsa_f3_net_incurrence"]["gross_issuance_equivalent"] is not False:
        errors.append("QSA F3 net incurrence may not equal gross issuance")
    if (
        comparison["bnr_domestic_primary_market_issue_volume"][
            "gross_issuance_equivalent_on_exact_domestic_primary_market_boundary"
        ]
        is not True
    ):
        errors.append("BNR exact domestic-primary-market source meaning changed")
    if (
        comparison["bnr_domestic_primary_market_issue_volume"][
            "full_government_borrowing_equivalent"
        ]
        is not False
    ):
        errors.append("BNR source may not equal full government borrowing")
    if comparison["mof_actual_borrowing"]["securities_only"] is not False:
        errors.append("Ministry all-in actual borrowing may not be treated as securities-only")
    if comparison["mof_actual_borrowing"]["monthly_increment_directly_observed"] is not False:
        errors.append("Ministry monthly increments are not directly observed")
    if comparison["government_refinancing_need"]["issuance_equivalent"] is not False:
        errors.append("refinancing need may not equal issuance")
    if comparison["government_securities_supply_pressure"]["issuance_equivalent"] is not False:
        errors.append("supply pressure may not equal issuance")

    if contract["cross_source_rule"]["sources_are_expected_to_differ"] is not True:
        errors.append("BNR and Ministry source families must remain distinct")
    if contract["cross_source_rule"]["equality_is_not_a_validation_requirement"] is not True:
        errors.append("cross-source equality may not become a validation gate")

    activation = contract["activation_boundary"]
    for key in (
        "exact_feedback_node_mapping_established",
        "generic_government_debt_issuance_node_resolved",
        "reference_mode_promotion_authorized",
        "estimation_authorized",
        "behavioural_closure_authorized",
        "feedback_activation_authorized",
    ):
        if activation.get(key) is not False:
            errors.append(f"issuance materialisation contract may not promote {key}")

    boundary_by_id = {item["id"]: item for item in boundary["variables"]}
    node = boundary_by_id["government_debt_issuance"]
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("government_debt_issuance must remain UNRESOLVED")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("government_debt_issuance may not authorize feedback activation")
    if node.get("semantic_overload_detected") is not True:
        errors.append("boundary registry must retain issuance semantic-overload flag")
    if set(node.get("candidate_observed_boundaries", [])) != expected_candidates:
        errors.append("boundary registry candidate issuance boundaries are stale")
    if node.get("source_boundary_review") != (
        "model/dynamics/government_debt_issuance_source_boundary_review.json"
    ):
        errors.append("boundary registry does not point to issuance source review")
    if node.get("source_materialisation_contract") != (
        "model/dynamics/government_debt_issuance_materialisation_contract.json"
    ):
        errors.append("boundary registry does not point to issuance materialisation contract")

    affected = {
        loop["id"]
        for loop in feedback["loops"]
        if any(
            link["from"] == "government_debt_issuance"
            or link["to"] == "government_debt_issuance"
            for link in loop["path"]
        )
    }
    if affected != {
        "government_refinancing_interest_loop",
        "government_issuance_yield_loop",
    }:
        errors.append(
            "generic government_debt_issuance node is no longer confined to expected loops"
        )

    if any(
        mode["id"] == "government_debt_issuance"
        and mode["status"] == "OBSERVED_SERIES_AVAILABLE"
        for mode in reference_modes["modes"]
    ):
        errors.append("source screening may not promote government_debt_issuance reference mode")

    fiscal_boundary = sovereign_review["fiscal_source_boundary"]
    if fiscal_boundary.get("government_issuance_source_boundary_review") != (
        "model/dynamics/government_debt_issuance_source_boundary_review.json"
    ):
        errors.append("sovereign-yield boundary is not linked to issuance source review")
    if fiscal_boundary.get("government_issuance_materialisation_contract") != (
        "model/dynamics/government_debt_issuance_materialisation_contract.json"
    ):
        errors.append("sovereign-yield boundary is not linked to issuance contract")
    if "separate source and structural contract" not in fiscal_boundary["no_issuance_proxy"]:
        errors.append("sovereign-yield no-issuance-proxy rule was weakened")

    decision = review["scientific_decision"]
    if decision["current_boundary_class"] != "UNRESOLVED":
        errors.append("source review may not resolve generic issuance node")
    for key in (
        "reference_mode_promoted",
        "feedback_activation_authorized",
        "estimation_or_refit_authorized",
    ):
        if decision[key] is not False:
            errors.append(f"source review may not promote {key}")

    return errors


def main() -> None:
    review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")
    contract = load("model/dynamics/government_debt_issuance_materialisation_contract.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    reference_modes = load("model/dynamics/reference_modes.json")
    sovereign_review = load(
        "model/calibration_validation/sovereign_yield_source_boundary_review.json"
    )

    errors = audit_government_debt_issuance_source_boundary(
        review,
        contract,
        boundary,
        feedback,
        reference_modes,
        sovereign_review,
    )
    if errors:
        raise RuntimeError(
            "Government debt issuance source-boundary audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "variable_id": "government_debt_issuance",
                "semantic_overload_detected": True,
                "candidate_observed_boundaries": 2,
                "current_boundary_class": "UNRESOLVED",
                "reference_mode_promoted": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
