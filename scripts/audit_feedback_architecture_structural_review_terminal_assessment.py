from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/feedback_architecture_structural_review_terminal_assessment_2026_09_21.json"
STATUS = "ALL_REGISTERED_FEEDBACK_STRUCTURES_STRUCTURALLY_REVIEWED_EVIDENCE_TRIGGERED_HOLD"
HOLD_ID = "feedback_architecture_evidence_triggered_hold"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_feedback_architecture_terminal(
    assessment: dict,
    feedback: dict,
    readiness: dict,
    boundary: dict,
    delays: dict,
    criteria: dict,
    model: dict,
    baseline: dict,
    validation: dict,
) -> list[str]:
    errors: list[str] = []
    if assessment["decision"] != STATUS:
        errors.append("architecture terminal decision changed")

    loops = feedback["loops"]
    snapshot = assessment["registry_snapshot"]
    if len(loops) != snapshot["registered_structures"]:
        errors.append("registered structure count changed")
    closed = [x for x in loops if x["topology_status"] == "CLOSED_CANDIDATE_LOOP"]
    opened = [x for x in loops if x["topology_status"] == "OPEN_CHAIN"]
    if len(closed) != snapshot["closed_candidate_loops"]:
        errors.append("closed-loop count changed")
    if len(opened) != snapshot["open_candidate_chains"]:
        errors.append("open-chain count changed")
    if any(x.get("quantitatively_active") is not False for x in loops):
        errors.append("a feedback structure became quantitatively active")

    terminal_by_id = {x["id"]: x for x in assessment["structure_terminal_states"]}
    if set(terminal_by_id) != {x["id"] for x in loops}:
        errors.append("terminal-state coverage differs from feedback registry")
    for loop in loops:
        row = terminal_by_id.get(loop["id"], {})
        if row.get("topology_status") != loop.get("topology_status"):
            errors.append(f"{loop['id']}: topology terminal snapshot changed")
        if row.get("terminal_assessment") != loop.get("structural_terminal_assessment"):
            errors.append(f"{loop['id']}: terminal assessment pointer changed")
        if row.get("structural_review_status") != loop.get("structural_review_status"):
            errors.append(f"{loop['id']}: structural review status changed")
        if row.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
            errors.append(f"{loop['id']}: terminal operational state changed")
        if row.get("active_empirical_task") is not None:
            errors.append(f"{loop['id']}: terminal row exposes active task")
        if loop.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
            errors.append(f"{loop['id']}: feedback registry operational state changed")
        if loop.get("active_empirical_task") is not None:
            errors.append(f"{loop['id']}: feedback registry exposes active task")

    summary = readiness["current_summary"]
    if summary["registered_feedback_links"] != snapshot["registered_feedback_links"]:
        errors.append("registered link count changed")
    if summary["exact_integrated_link_forms_ready"] != 0:
        errors.append("exact integrated links may not become ready")
    if summary["feedback_structures_with_all_links_exact_ready"] != 0:
        errors.append("feedback structures may not become exact-ready")
    if summary["activation_authorized"] is not False:
        errors.append("link readiness may not authorize activation")

    if any(x["current_boundary_class"] == "ENDOGENOUS" for x in boundary["variables"]):
        errors.append("current feedback boundary may not contain ENDOGENOUS nodes")
    if any(x["current_feedback_activation_authorized"] is not False for x in boundary["variables"]):
        errors.append("a feedback node authorizes activation")

    if len(delays["delays"]) != assessment["activation_state"]["registered_delay_candidates"]:
        errors.append("delay candidate count changed")
    if any(x["scalar_tau_activation_ready"] is True for x in delays["delays"]):
        errors.append("a scalar delay became activation-ready")
    if any(x["active"] is True for x in delays["delays"]):
        errors.append("a delay became active")

    if len(criteria["feedbacks"]) != len(loops):
        errors.append("activation criteria structure count changed")
    for item in criteria["feedbacks"]:
        if item["activation_status"] != "BLOCKED":
            errors.append(f"{item['loop_id']}: activation criteria no longer blocked")
        if item["all_requirements_pass"] is not False:
            errors.append(f"{item['loop_id']}: all activation requirements unexpectedly pass")
        if item["quantitative_activation_authorized"] is not False:
            errors.append(f"{item['loop_id']}: quantitative activation unexpectedly authorized")

    if validation["validated_reference_behavioural_mechanisms"] != 0:
        errors.append("validated behavioural mechanism count changed")

    dynamic = model["dynamic_core"]
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("behavioural closure changed")
    if dynamic["reference_mode_ready_count"] != 10 or dynamic["reference_mode_required_count"] != 10:
        errors.append("current reference-mode readiness must be 10/10")
    if dynamic["reference_mode_closure_ready"] is not True:
        errors.append("current reference-target prerequisite must be ready")
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("reference-target readiness may not activate behavioural closure")
    if dynamic["canonical_multi_instrument_stock_initialization_ready"] is not False:
        errors.append("canonical multi-instrument stock initialization unexpectedly ready")
    if dynamic["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        errors.append("canonical full-2025 benchmark unexpectedly ready")
    if dynamic.get("feedback_architecture_structural_review_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks architecture terminal assessment")
    if dynamic.get("feedback_architecture_structural_review_status") != STATUS:
        errors.append("model contract architecture terminal status changed")
    if dynamic.get("feedback_architecture_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("model contract architecture operational state changed")
    if dynamic.get("feedback_architecture_active_structural_review_task") is not None:
        errors.append("model contract exposes active architecture task")

    if baseline["authority"].get("feedback_architecture_structural_review_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks architecture terminal assessment")

    for key, value in assessment["cross_structure_hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    disposition = assessment["disposition"]
    if disposition["all_registered_structures_have_terminal_assessments"] is not True:
        errors.append("terminal coverage must remain complete")
    if disposition["all_registered_structures_on_evidence_triggered_hold"] is not True:
        errors.append("all structures must remain on evidence-triggered hold")
    if disposition["active_structural_review_task"] is not None:
        errors.append("architecture terminal state may not expose active task")
    for key in (
        "quantitative_feedback_activation_authorized",
        "behavioural_closure_authorized",
        "model_complete", "release_ready", "public_version_change_authorized",
    ):
        if disposition[key] is not False:
            errors.append(f"architecture terminal assessment may not promote {key}")

    next_state = assessment["next_state"]
    if next_state["id"] != HOLD_ID:
        errors.append("architecture next-state id changed")
    if next_state["authorization"] != "NO_ACTIVE_FEEDBACK_ARCHITECTURE_TASK_UNTIL_DECLARED_STRUCTURE_SPECIFIC_REOPEN_TRIGGER":
        errors.append("architecture hold authorization changed")
    if next_state["reopen_is_structure_specific"] is not True:
        errors.append("architecture reopen must remain structure-specific")
    for key in (
        "may_poll_unchanged_sources", "may_relax_link_gates",
        "may_infer_missing_equations", "may_estimate_parameters",
        "may_activate_feedback", "may_change_behavioural_closure",
        "may_treat_structural_review_as_model_completion",
    ):
        if next_state[key] is not False:
            errors.append(f"architecture hold may not authorize {key}")

    return errors

def main() -> None:
    errors = audit_feedback_architecture_terminal(
        load(ASSESSMENT_PATH),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
        load("model/calibration_validation/validation_recovery_disposition.json"),
    )
    if errors:
        raise RuntimeError(
            "Feedback-architecture terminal audit failed:\n- " + "\n- ".join(errors)
        )
    print(json.dumps({
        "status": "PASS",
        "terminal_status": STATUS,
        "registered_structures": 5,
        "registered_feedback_links": 22,
        "exact_integrated_link_forms_ready": 0,
        "activation_ready_structures": 0,
        "behavioural_closure_active": False,
        "operational_state": "EVIDENCE_TRIGGERED_HOLD",
    }, indent=2))

if __name__ == "__main__":
    main()
