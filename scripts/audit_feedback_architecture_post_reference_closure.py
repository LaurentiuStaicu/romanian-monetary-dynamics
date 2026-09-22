from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/feedback_architecture_post_reference_closure_assessment_2026_09_22.json"
PREDECESSOR_PATH = "model/dynamics/feedback_architecture_structural_review_terminal_assessment_2026_09_21.json"
REFERENCE_SUCCESSOR_PATH = "model/dynamics/reference_mode_post_terminal_promotion_assessment_2026_09_21.json"
DECISION = "POST_REFERENCE_MODE_CLOSURE_RECONCILED_FEEDBACK_ARCHITECTURE_HOLD_UNCHANGED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_feedback_architecture_post_reference_closure(
    assessment: dict,
    predecessor: dict,
    reference_successor: dict,
    feedback: dict,
    readiness: dict,
    delays: dict,
    criteria: dict,
    model: dict,
    baseline: dict,
    validation: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != DECISION:
        errors.append("post-reference feedback-architecture decision changed")
    if assessment["predecessor_terminal_assessment"] != PREDECESSOR_PATH:
        errors.append("predecessor terminal assessment pointer changed")
    if assessment["reference_mode_successor"] != REFERENCE_SUCCESSOR_PATH:
        errors.append("reference-mode successor pointer changed")

    historical = assessment["historical_snapshot_preserved"]
    predecessor_blockers = predecessor["remaining_integrated_blockers"]
    if predecessor_blockers["reference_modes_ready"] != 9:
        errors.append("historical predecessor no longer preserves 9/10 reference readiness")
    if predecessor_blockers["reference_modes_required"] != 10:
        errors.append("historical predecessor required reference-mode count changed")
    if predecessor_blockers["reference_mode_blocker"] != "sectoral_financial_positions":
        errors.append("historical predecessor blocker changed")
    if historical != {
        "reference_modes_ready": 9,
        "reference_modes_required": 10,
        "reference_mode_blocker": "sectoral_financial_positions",
        "immutable_predecessor": True,
    }:
        errors.append("successor no longer preserves historical 9/10 snapshot explicitly")

    if reference_successor["reference_modes_ready_before"] != 9:
        errors.append("reference-mode successor pre-promotion count changed")
    if reference_successor["reference_modes_ready_after"] != 10:
        errors.append("reference-mode successor post-promotion count changed")
    if reference_successor["promoted_mode"]["id"] != "sectoral_financial_positions":
        errors.append("reference-mode successor promoted mode changed")
    if reference_successor["promotion_effect"]["feedback_activation_authorized"] is not False:
        errors.append("reference-mode promotion may not authorize feedback")
    if reference_successor["promotion_effect"]["behavioural_closure_active"] is not False:
        errors.append("reference-mode promotion may not activate behavioural closure")

    current = assessment["current_reference_mode_state"]
    dynamic = model["dynamic_core"]
    if current["reference_modes_ready"] != dynamic["reference_mode_ready_count"]:
        errors.append("successor current reference-mode ready count is stale")
    if current["reference_modes_required"] != dynamic["reference_mode_required_count"]:
        errors.append("successor current reference-mode required count is stale")
    if current["reference_modes_ready"] != 10 or current["reference_modes_required"] != 10:
        errors.append("current reference-mode state must remain 10/10")
    if current["reference_mode_blocker"] is not None:
        errors.append("current successor may not retain a reference-mode blocker")
    if current["reference_mode_closure_ready"] is not True:
        errors.append("current successor must record reference-mode closure ready")

    architecture = assessment["current_feedback_architecture_state"]
    loops = feedback["loops"]
    closed = [x for x in loops if x["topology_status"] == "CLOSED_CANDIDATE_LOOP"]
    opened = [x for x in loops if x["topology_status"] == "OPEN_CHAIN"]
    if architecture["registered_structures"] != len(loops):
        errors.append("registered feedback structure count is stale")
    if architecture["closed_candidate_loops"] != len(closed):
        errors.append("closed-loop count is stale")
    if architecture["open_candidate_chains"] != len(opened):
        errors.append("open-chain count is stale")
    if architecture["registered_feedback_links"] != readiness["current_summary"]["registered_feedback_links"]:
        errors.append("registered feedback-link count is stale")
    if architecture["exact_integrated_link_forms_ready"] != readiness["current_summary"]["exact_integrated_link_forms_ready"]:
        errors.append("exact integrated link count is stale")
    if architecture["feedback_structures_activation_ready"] != readiness["current_summary"]["feedback_structures_with_all_links_exact_ready"]:
        errors.append("activation-ready structure count is stale")
    if architecture["registered_delay_candidates"] != delays["current_summary"]["registered_delay_candidates"]:
        errors.append("registered delay count is stale")
    if architecture["scalar_tau_activation_ready"] != delays["current_summary"]["scalar_tau_activation_ready"]:
        errors.append("scalar-tau ready count is stale")
    if architecture["active_delay_candidates"] != delays["current_summary"]["active_delay_candidates"]:
        errors.append("active delay count is stale")
    if architecture["validated_reference_behavioural_mechanisms"] != validation["validated_reference_behavioural_mechanisms"]:
        errors.append("validated behavioural mechanism count is stale")

    if architecture["exact_integrated_link_forms_ready"] != 0:
        errors.append("reference-mode closure may not create exact integrated feedback links")
    if architecture["feedback_structures_activation_ready"] != 0:
        errors.append("reference-mode closure may not make a feedback structure activation-ready")
    if architecture["scalar_tau_activation_ready"] != 0 or architecture["active_delay_candidates"] != 0:
        errors.append("reference-mode closure may not identify or activate delays")
    if architecture["validated_reference_behavioural_mechanisms"] != 0:
        errors.append("reference-mode closure may not validate behavioural mechanisms")
    if architecture["behavioural_closure_active"] is not False:
        errors.append("successor may not activate behavioural closure")
    if any(item["activation_status"] != "BLOCKED" for item in criteria["feedbacks"]):
        errors.append("a feedback activation-criteria row is no longer blocked")
    if any(loop.get("active_empirical_task") is not None for loop in loops):
        errors.append("a feedback structure exposes an active empirical task")

    blockers = assessment["remaining_integrated_blockers"]
    if blockers["reference_mode_observability_blocker_removed"] is not True:
        errors.append("successor does not acknowledge reference-mode blocker removal")
    if blockers["canonical_multi_instrument_stock_initialization_ready"] is not dynamic["canonical_multi_instrument_stock_initialization_ready"]:
        errors.append("stock-initialization blocker state is stale")
    if blockers["canonical_full_2025_stock_flow_benchmark_ready"] is not dynamic["canonical_full_2025_stock_flow_benchmark_ready"]:
        errors.append("full benchmark blocker state is stale")
    if blockers["exact_integrated_link_forms_ready"] != 0:
        errors.append("integrated-link blocker unexpectedly removed")
    if blockers["scalar_delay_parameters_ready"] != 0:
        errors.append("delay blocker unexpectedly removed")
    if blockers["validated_reference_behavioural_mechanisms"] != 0:
        errors.append("validation blocker unexpectedly removed")
    for key in (
        "unresolved_link_equation_identification_remains",
        "unresolved_endogenous_exogenous_boundaries_remain",
    ):
        if blockers[key] is not True:
            errors.append(f"successor unexpectedly clears {key}")

    if dynamic["behavioural_closure_active"] is not False:
        errors.append("model contract behavioural closure changed")
    if dynamic.get("feedback_architecture_current_assessment") != ASSESSMENT_PATH:
        errors.append("model contract does not register current feedback-architecture assessment")
    if dynamic.get("feedback_architecture_structural_review_terminal_assessment") != PREDECESSOR_PATH:
        errors.append("model contract historical feedback-architecture terminal pointer changed")

    if baseline["authority"].get("feedback_architecture_post_reference_closure_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks current feedback-architecture successor")
    if baseline["authority"].get("feedback_architecture_structural_review_terminal_assessment") != PREDECESSOR_PATH:
        errors.append("scientific baseline historical terminal pointer changed")

    disposition = assessment["structure_disposition"]
    if disposition["all_registered_structures_remain_on_evidence_triggered_hold"] is not True:
        errors.append("all feedback structures must remain on evidence-triggered hold")
    if disposition["active_feedback_architecture_task"] is not None:
        errors.append("successor exposes active feedback-architecture task")
    for key in (
        "quantitative_feedback_activation_authorized",
        "behavioural_closure_authorized",
        "calibration_or_refit_authorized",
        "parameter_estimation_authorized",
        "model_complete",
        "release_or_version_change_authorized",
    ):
        if disposition[key] is not False:
            errors.append(f"successor unexpectedly authorizes {key}")

    for key, value in assessment["hard_rules"].items():
        if value is not True:
            errors.append(f"successor hard rule disabled: {key}")

    next_state = assessment["next_state"]
    if next_state["id"] != "feedback_architecture_evidence_triggered_hold":
        errors.append("successor feedback-architecture next state changed")
    if next_state["active_task"] is not None:
        errors.append("successor next state exposes active task")

    return errors


def main() -> None:
    errors = audit_feedback_architecture_post_reference_closure(
        load(ASSESSMENT_PATH),
        load(PREDECESSOR_PATH),
        load(REFERENCE_SUCCESSOR_PATH),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
        load("model/calibration_validation/validation_recovery_disposition.json"),
    )
    if errors:
        raise RuntimeError(
            "Feedback architecture post-reference-closure audit failed:\n- "
            + "\n- ".join(errors)
        )
    assessment = load(ASSESSMENT_PATH)
    print(json.dumps({
        "status": "PASS",
        "decision": assessment["decision"],
        "reference_modes_ready": assessment["current_reference_mode_state"]["reference_modes_ready"],
        "reference_modes_required": assessment["current_reference_mode_state"]["reference_modes_required"],
        "exact_integrated_link_forms_ready": assessment["current_feedback_architecture_state"]["exact_integrated_link_forms_ready"],
        "activation_ready_structures": assessment["current_feedback_architecture_state"]["feedback_structures_activation_ready"],
        "behavioural_closure_active": assessment["current_feedback_architecture_state"]["behavioural_closure_active"],
        "operational_state": assessment["next_state"]["id"],
    }, indent=2))


if __name__ == "__main__":
    main()
