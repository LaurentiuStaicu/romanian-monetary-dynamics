from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/interest_cost_to_financing_need_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "ACCOUNTING_COMPOSITION_FORM_KNOWN_BOUNDARY_NOT_CANONICAL"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_interest_cost_to_financing_need_boundary(
    review: dict,
    refinancing: dict,
    fiscal_contract: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "ACCOUNTING_COMPOSITION_FORM_KNOWN_CANONICAL_FINANCING_NEED_"
        "BOUNDARY_UNRESOLVED_DO_NOT_ADD_INTEREST_TWICE"
    ):
        errors.append("accounting-boundary decision changed")

    forms = review["accounting_forms"]
    if forms["headline_deficit_form"]["interest_cost_explicit_separate_addend"] is not False:
        errors.append("interest may not be added separately to headline deficit")
    if forms["headline_deficit_form"]["double_counting_if_interest_added_again"] is not True:
        errors.append("headline-deficit double-counting guard changed")
    if forms["primary_deficit_form"]["interest_cost_explicit_separate_addend"] is not True:
        errors.append("primary-deficit form must include interest exactly once")
    if forms["primary_deficit_form"]["requires_matched_component_boundaries"] is not True:
        errors.append("primary-deficit form must require matched boundaries")
    if forms["ministry_operational_form"]["canonical_for_dynamic_core_now"] is not False:
        errors.append("Ministry operational GFN may not become canonical automatically")

    identity = fiscal_contract["measurement_identity"]
    if identity["equation"] != "primary_balance_pct_gdp = B9_pct_gdp + D41PAY_pct_gdp":
        errors.append("matched Eurostat primary-balance identity changed")
    if identity["same_boundary_required"] is not True or identity["no_sign_flip"] is not True:
        errors.append("matched Eurostat boundary/sign guards changed")

    if refinancing["current_observed_series"]["observation_count"] != 12:
        errors.append("refinancing reference coverage changed")
    if "not gross financing need" not in " ".join(refinancing["semantic_limits"]).casefold():
        errors.append("refinancing reference lost GFN distinction")

    examples = review["official_definition_evidence"]["ministry_operational_examples"]["examples_bn_RON"]
    for period, row in examples.items():
        if abs(row["budget_deficit"] + row["government_debt_refinancing"] - row["reported_gross_financing_need"]) > 1e-9:
            errors.append(f"{period}: Ministry GFN example no longer reconciles")

    resolution = review["link_resolution"]
    if resolution["status"] != STATUS:
        errors.append("link status changed")
    if resolution["causal_role_after_review"] != "ACCOUNTING_COMPOSITION_CONDITIONAL_ON_FINANCING_NEED_DEFINITION":
        errors.append("accounting causal role changed")
    if resolution["behavioural_equation_required"] is not False:
        errors.append("accounting composition may not require behavioural equation")
    if resolution["parameter_estimation_required"] is not False:
        errors.append("accounting composition may not require parameter estimation")
    if resolution["exact_integrated_identity_ready"] is not False:
        errors.append("accounting identity may not be exact-ready before boundary match")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    effect = review["scientific_effect"]
    for key, value in effect.items():
        if value is not False:
            errors.append(f"review may not promote {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "financing_channel_allocation_boundary_review":
        errors.append("next gate changed")
    if next_gate["authorization"] != "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next gate authorization changed")
    for key in (
        "may_construct_one_to_one_GFN_to_BNR_issuance",
        "may_invent_channel_allocations",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
    ):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    node = next(x for x in boundary["variables"] if x["id"] == "government_financing_need")
    if node.get("source_boundary_review") != REVIEW_PATH:
        errors.append("financing-need node lacks review")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("financing-need node may not be resolved")
    if node.get("interest_cost_to_financing_need_status") != STATUS:
        errors.append("financing-need node accounting status changed")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("financing-need node activation changed")

    links = [x for x in readiness["links"] if x["from"] == "government_interest_cost" and x["to"] == "government_financing_need"]
    if len(links) != 2:
        errors.append("expected two interest-cost/financing-need feedback links")
    for link in links:
        if link.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
            errors.append(f"{link['loop_id']}: link lacks review")
        if link["causal_role"] != "ACCOUNTING_COMPOSITION_CONDITIONAL_ON_BOUNDARY":
            errors.append(f"{link['loop_id']}: accounting role changed")
        if link["readiness_status"] != STATUS:
            errors.append(f"{link['loop_id']}: readiness status changed")
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['loop_id']}: link may not become exact-ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['loop_id']}: link may not activate")

    for loop_id in ("government_issuance_yield_loop", "government_refinancing_interest_loop"):
        loop = next(x for x in feedback["loops"] if x["id"] == loop_id)
        if loop.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
            errors.append(f"{loop_id}: feedback registry lacks review")
        if loop.get("interest_cost_to_financing_need_status") != STATUS:
            errors.append(f"{loop_id}: accounting status changed")
        if loop["quantitatively_active"] is not False:
            errors.append(f"{loop_id}: accounting review may not activate loop")

    bridges = {x["id"]: x for x in prereg["required_bridges_before_any_closed_empirical_loop_claim"]}
    bridge = bridges.get("interest_cost_to_financing_need")
    if bridge is None:
        errors.append("preregistration lacks accounting bridge")
    else:
        if bridge["status"] != STATUS or bridge.get("boundary_review") != REVIEW_PATH:
            errors.append("preregistration accounting bridge changed")
        for key in (
            "behavioural_equation_required",
            "parameter_estimation_required",
            "exact_integrated_identity_ready",
            "direct_addition_to_headline_deficit_authorized",
            "cross_boundary_identity_authorized",
            "feedback_activation_authorized",
        ):
            if bridge[key] is not False:
                errors.append(f"preregistration may not authorize {key}")

    if prereg["next_independent_bridge_task"]["id"] != "mof_realized_financing_channel_materialisation_contract":
        errors.append("preregistration next bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks review")
    if dynamic.get("interest_cost_to_financing_need_boundary_status") != STATUS:
        errors.append("model contract accounting status changed")
    if dynamic.get("government_financing_need_canonical_boundary_selected") is not False:
        errors.append("model contract may not select canonical GFN")
    if dynamic.get("government_issuance_yield_next_independent_task") != "mof_realized_financing_channel_materialisation_contract":
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate feedback")

    if baseline["authority"].get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks review authority")

    return errors


def main() -> None:
    errors = audit_interest_cost_to_financing_need_boundary(
        load(REVIEW_PATH),
        load("model/dynamics/government_refinancing_need_reference_assessment.json"),
        load("model/calibration_validation/fiscal_primary_balance_materialisation_contract.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError("Interest-cost to financing-need boundary audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "link_status": STATUS,
        "double_counting_guard": True,
        "canonical_financing_need_boundary_selected": False,
        "exact_integrated_identity_ready": False,
        "feedback_activation_authorized": False,
        "next_gate": "financing_channel_allocation_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
