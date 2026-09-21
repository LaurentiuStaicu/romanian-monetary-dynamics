from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG_PATH = (
    "model/dynamics/"
    "government_issuance_yield_boundary_preregistration_2026_09_20.json"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_issuance_yield_boundary_preregistration(
    prereg: dict,
    feedback: dict,
    boundary: dict,
    readiness: dict,
    materialisation: dict,
    source_review: dict,
    sovereign_review: dict,
) -> list[str]:
    errors: list[str] = []

    if prereg.get("decision") != (
        "DO_NOT_NARROW_GENERIC_CLOSED_LOOP_TO_BNR_DOMESTIC_PRIMARY_AS_ONE_TO_ONE"
    ):
        errors.append("issuance-yield structural decision changed")

    conceptual = prereg["conceptual_topology"]
    if conceptual["current_status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("qualitative candidate topology status changed")
    if conceptual["retain_qualitative_topology"] is not True:
        errors.append("preregistration may not silently replace qualitative topology")
    if conceptual["quantitatively_active"] is not False:
        errors.append("preregistration may not activate the conceptual loop")

    empirical = prereg["empirical_boundary_status"]
    if empirical["status"] != "OPEN_CHAIN_PENDING_EXPLICIT_BRIDGES":
        errors.append("empirical issuance-yield boundary must remain explicitly open")
    if empirical["closure_not_claimed"] is not True:
        errors.append("empirical closure may not be claimed")
    if empirical["generic_government_debt_issuance_node_remains_unresolved"] is not True:
        errors.append("generic issuance node must remain unresolved")

    expected_bridges = {
        "financing_channel_allocation",
        "issuance_to_supply_pressure",
        "primary_yield_to_sovereign_yield",
        "yield_to_interest_cost",
        "interest_cost_to_financing_need",
    }
    bridge_ids = {item["id"] for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]}
    if bridge_ids != expected_bridges:
        errors.append(
            "required empirical bridge set changed: "
            f"expected={sorted(expected_bridges)}, observed={sorted(bridge_ids)}"
        )

    bnr = prereg["retained_bnr_boundary"]
    if bnr["candidate_id"] != (
        "domestic_primary_market_government_securities_gross_issuance"
    ):
        errors.append("retained BNR issuance candidate boundary changed")
    prohibited_equivalences = set(bnr["not_equivalent_to"])
    for required in (
        "total government gross financing need",
        "all-market government borrowing",
        "government securities supply pressure",
        "generic sovereign yield",
        "government interest cost",
    ):
        if required not in prohibited_equivalences:
            errors.append(f"BNR non-equivalence guard missing: {required}")

    effect = prereg["scientific_effect"]
    for key in (
        "bnr_boundary_promoted_to_generic_government_debt_issuance",
        "generic_government_debt_issuance_node_resolved",
        "conceptual_loop_topology_changed",
        "reference_mode_promoted",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"structural preregistration may not promote {key}")

    loop = next(item for item in feedback["loops"] if item["id"] == "government_issuance_yield_loop")
    if loop["topology_status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("feedback registry conceptual topology changed")
    if loop["quantitatively_active"] is not False:
        errors.append("issuance-yield loop became quantitatively active")
    if loop["empirical_boundary_preregistration"] != PREREG_PATH:
        errors.append("feedback registry is not bound to structural preregistration")
    if loop["empirical_boundary_status"] != "OPEN_CHAIN_PENDING_EXPLICIT_BRIDGES":
        errors.append("feedback registry empirical boundary status changed")
    if loop["bnr_domestic_primary_market_narrowing_as_closed_loop_authorized"] is not False:
        errors.append("feedback registry incorrectly authorizes closed-loop BNR narrowing")
    if loop["quantitative_activation_authorized"] is not False:
        errors.append("feedback registry incorrectly authorizes quantitative activation")

    generic = next(
        item for item in boundary["variables"]
        if item["id"] == "government_debt_issuance"
    )
    if generic["current_boundary_class"] != "UNRESOLVED":
        errors.append("generic government_debt_issuance boundary was resolved")
    if generic["current_feedback_activation_authorized"] is not False:
        errors.append("generic government_debt_issuance feedback activation changed")
    if generic["structural_preregistration"] != PREREG_PATH:
        errors.append("generic issuance node lacks structural preregistration")
    if generic[
        "bnr_domestic_primary_market_boundary_can_replace_generic_node_in_both_government_loops"
    ] is not False:
        errors.append("BNR boundary may not replace generic issuance in both loops")

    loop_links = [
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
    ]
    if len(loop_links) != 5:
        errors.append(f"expected 5 issuance-yield links, observed {len(loop_links)}")
    for link in loop_links:
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['link_key']}: exact equation became ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['link_key']}: link activation became authorized")
        if link.get("structural_preregistration") != PREREG_PATH:
            errors.append(f"{link['link_key']}: structural preregistration missing")

    bnr_path = materialisation["paths"]["bnr_domestic_primary_market"]
    if bnr_path["structural_preregistration"] != PREREG_PATH:
        errors.append("BNR materialisation path lacks structural preregistration")
    if bnr_path["structural_narrowing_status"] != (
        "PREREGISTERED_DO_NOT_REPLACE_GENERIC_CLOSED_LOOP_ONE_TO_ONE"
    ):
        errors.append("BNR materialisation structural narrowing status changed")

    decision = source_review["scientific_decision"]
    if decision["issuance_yield_structural_preregistration"] != PREREG_PATH:
        errors.append("source-boundary review lacks issuance-yield preregistration")
    if decision["current_boundary_class"] != "UNRESOLVED":
        errors.append("source-boundary review resolved generic issuance node")
    for key in (
        "reference_mode_promoted",
        "feedback_activation_authorized",
        "estimation_or_refit_authorized",
    ):
        if decision[key] is not False:
            errors.append(f"source-boundary review may not promote {key}")

    fiscal = sovereign_review["fiscal_source_boundary"]
    if fiscal["government_issuance_yield_boundary_preregistration"] != PREREG_PATH:
        errors.append("sovereign-yield boundary lacks issuance-yield preregistration")
    no_proxy = fiscal["no_issuance_proxy"]
    if "may not be inserted" not in no_proxy or "supply pressure" not in no_proxy:
        errors.append("sovereign-yield no-issuance-proxy guard was weakened")

    next_task = prereg["next_empirical_task"]
    if next_task["authorization"] != "DESCRIPTIVE_MATERIALISATION_ONLY":
        errors.append("next yield pilot authorization changed")
    if next_task["may_activate_feedback"] is not False:
        errors.append("descriptive yield pilot may not activate feedback")

    return errors


def main() -> None:
    prereg = load(PREREG_PATH)
    feedback = load("model/dynamics/feedback_registry.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    materialisation = load("model/dynamics/government_debt_issuance_materialisation_contract.json")
    source_review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")
    sovereign_review = load(
        "model/calibration_validation/sovereign_yield_source_boundary_review.json"
    )

    errors = audit_government_issuance_yield_boundary_preregistration(
        prereg,
        feedback,
        boundary,
        readiness,
        materialisation,
        source_review,
        sovereign_review,
    )
    if errors:
        raise RuntimeError(
            "Government issuance-yield boundary preregistration audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "conceptual_topology": "CLOSED_CANDIDATE_LOOP",
                "empirical_boundary": "OPEN_CHAIN_PENDING_EXPLICIT_BRIDGES",
                "required_bridges": 5,
                "generic_issuance_node": "UNRESOLVED",
                "feedback_activation_authorized": False,
                "next_empirical_task": "bnr_instrument_specific_primary_market_yield_pilot_2025",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
