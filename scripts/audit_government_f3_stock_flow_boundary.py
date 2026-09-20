from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_f3_stock_flow_boundary(
    review: dict,
    contract: dict,
    feedback: dict,
    boundary: dict,
    links: dict,
    reference_modes: dict,
    issuance_review: dict,
) -> list[str]:
    errors: list[str] = []

    identity = review["stock_flow_identity"]
    if identity["net_issue_identity"] != (
        "net_issues[t] = gross_issues[t] - redemptions[t]"
    ):
        errors.append("CSEC net-issue identity changed")
    if "gross_issues[t] - redemptions[t]" not in identity["exact_csec_form"]:
        errors.append("CSEC stock-flow identity no longer separates gross issues/redemptions")
    if "revaluations[t]" not in identity["exact_csec_form"]:
        errors.append("CSEC stock-flow identity dropped revaluations")
    if "other_changes_in_volume[t]" not in identity["exact_csec_form"]:
        errors.append("CSEC stock-flow identity dropped other changes in volume")

    discovered = review["source_discovery"]
    if discovered["Romania_general_government_available"] is not True:
        errors.append("Romania S13 CSEC discovery must remain positive")
    if discovered["reference_sector"] != "S13 general government":
        errors.append("CSEC reference sector changed")
    if discovered["instrument"] != "F3 debt securities":
        errors.append("CSEC instrument boundary changed")
    if discovered["valuation"] != "market value":
        errors.append("CSEC valuation boundary changed")
    if discovered["consolidation"] != "non-consolidated":
        errors.append("CSEC consolidation boundary changed")

    verified = {item["role"]: item for item in discovered["exact_verified_series"]}
    expected_keys = {
        "net_issues": "CSEC.M.N.RO.W0.S13.S1.N.L.F.F3.T._Z.EUR._T.M.V.N._T",
        "closing_stock": "CSEC.M.N.RO.W0.S13.S1.N.L.LE.F3.T._Z.EUR._T.M.V.N._T",
    }
    if set(verified) != set(expected_keys):
        errors.append("verified CSEC exact-series roles changed")
    else:
        for role, key in expected_keys.items():
            if verified[role]["key"] != key:
                errors.append(f"{role}: verified CSEC key changed")
            if verified[role]["status"] != "PORTAL_METADATA_VERIFIED":
                errors.append(f"{role}: verified source status changed")

    required_components = {
        "gross_issues",
        "redemptions",
        "net_issues",
        "closing_stock",
        "revaluations",
        "other_changes_in_volume",
    }
    if set(contract["required_components"]) != required_components:
        errors.append("CSEC materialisation component set changed")
    if set(discovered["source_family_verified_components"]) != required_components:
        errors.append("CSEC discovered component family changed")

    gate = contract["exact_boundary_gate"]
    for key in (
        "same_maturity_dimension_required",
        "same_currency_denominator_required",
        "same_unit_required",
        "same_market_value_valuation_required",
        "same_nonconsolidated_status_required",
        "same_monthly_frequency_required",
        "same_reference_and_counterpart_sectors_required",
        "no_component_aggregation_from_mismatched_boundaries",
    ):
        if gate.get(key) is not True:
            errors.append(f"CSEC exact-boundary gate {key} must remain true")

    state = contract["current_state"]
    if state["source_family_discovered"] is not True:
        errors.append("CSEC source family discovery must remain registered")
    for key in (
        "exact_common_six_component_boundary_materialised",
        "source_vintage_retained",
        "structural_refinement_authorized",
        "estimation_authorized",
        "feedback_activation_authorized",
    ):
        if state[key] is not False:
            errors.append(f"CSEC source review may not promote {key}")

    comparison = review["boundary_comparison"]
    if comparison["exact_equivalence"] is not False:
        errors.append("CSEC F3 and Maastricht debt may not be marked equivalent")
    if comparison["bridge_required"] is not True:
        errors.append("CSEC-to-Maastricht boundary bridge must remain required")
    if comparison["csec_S13_F3_stock"]["valuation"] != "market value":
        errors.append("CSEC F3 stock valuation changed")
    if comparison["maastricht_government_debt_reference"]["valuation"] != (
        "nominal/face value"
    ):
        errors.append("Maastricht debt valuation changed")
    if comparison["maastricht_government_debt_reference"]["instrument_scope"] != (
        "AF2 + AF3 + AF4 Maastricht debt"
    ):
        errors.append("Maastricht debt instrument scope changed")

    decision = review["scientific_decision"]
    for key in (
        "current_feedback_topology_changed",
        "government_debt_issuance_boundary_resolved",
        "government_debt_stock_boundary_resolved",
        "exact_issuance_to_stock_equation_admitted",
        "reference_mode_promoted",
        "estimation_or_refit_authorized",
        "feedback_activation_authorized",
    ):
        if decision[key] is not False:
            errors.append(f"CSEC boundary review may not promote {key}")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_refinancing_interest_loop"
    )
    exact_edge = next(
        item for item in loop["path"]
        if item["from"] == "government_debt_issuance"
        and item["to"] == "government_debt_stock"
    )
    if exact_edge["sign"] != "+":
        errors.append("qualitative issuance-to-stock sign changed")
    if loop["quantitatively_active"] is not False:
        errors.append("government refinancing-interest loop may not activate")

    link = next(
        item for item in links["links"]
        if item["link_key"]
        == (
            "government_refinancing_interest_loop|"
            "government_debt_issuance|government_debt_stock"
        )
    )
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("issuance-to-stock exact integrated link must remain blocked")
    if link["current_activation_authorized"] is not False:
        errors.append("issuance-to-stock link may not authorize activation")
    if link.get("stock_flow_boundary_review") != (
        "model/dynamics/government_f3_stock_flow_boundary_review.json"
    ):
        errors.append("link readiness does not point to CSEC stock-flow boundary review")

    by_id = {item["id"]: item for item in boundary["variables"]}
    for node_id in ("government_debt_issuance", "government_debt_stock"):
        if by_id[node_id]["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id} must remain UNRESOLVED")
        if by_id[node_id]["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id} may not authorize feedback activation")

    issuance_node = by_id["government_debt_issuance"]
    if "general_government_f3_gross_issuance_market_value" not in set(
        issuance_node.get("candidate_observed_boundaries", [])
    ):
        errors.append("government issuance boundary does not register CSEC F3 candidate")
    if issuance_node.get("csec_stock_flow_boundary_review") != (
        "model/dynamics/government_f3_stock_flow_boundary_review.json"
    ):
        errors.append("government issuance node is not linked to CSEC boundary review")

    stock_node = by_id["government_debt_stock"]
    if stock_node.get("csec_stock_flow_boundary_review") != (
        "model/dynamics/government_f3_stock_flow_boundary_review.json"
    ):
        errors.append("government debt-stock node is not linked to CSEC boundary review")

    mode = next(
        item for item in reference_modes["modes"]
        if item["id"] == "government_debt_stock"
    )
    if mode["status"] != "OBSERVED_SERIES_AVAILABLE":
        errors.append("Maastricht government-debt reference mode changed")
    if "nominal/face value" not in mode["role"]:
        errors.append("government-debt reference role lost nominal/face-value distinction")
    if "holder-by-issuer Accounting Spine stocks" not in mode["role"]:
        errors.append("government-debt reference role lost financial-account distinction")

    split_ids = {
        item["id"]
        for item in issuance_review["structural_finding"]["candidate_future_split"]
    }
    if "general_government_f3_gross_issuance_market_value" not in split_ids:
        errors.append("issuance source review does not register CSEC F3 gross-issue boundary")

    return errors


def main() -> None:
    errors = audit_government_f3_stock_flow_boundary(
        load("model/dynamics/government_f3_stock_flow_boundary_review.json"),
        load("model/dynamics/government_f3_csec_materialisation_contract.json"),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/reference_modes.json"),
        load("model/dynamics/government_debt_issuance_source_boundary_review.json"),
    )
    if errors:
        raise RuntimeError(
            "Government F3 stock-flow boundary audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "csec_source_family_discovered": True,
                "exact_common_six_component_boundary_materialised": False,
                "issuance_to_stock_exact_link_ready": False,
                "maastricht_boundary_bridge_required": True,
                "topology_changed": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
