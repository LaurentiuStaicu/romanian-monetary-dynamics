from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/monetary_credit_transmission_loop_terminal_assessment_2026_09_21.json"
STATUS = "STRUCTURAL_REVIEW_COMPLETE_MEASUREMENT_AND_IDENTIFICATION_BLOCKED_EVIDENCE_TRIGGERED_HOLD"
HOLD_ID = "monetary_credit_transmission_loop_evidence_triggered_hold"

EXPECTED_LINK_STATUSES = {
    ("policy_rate", "market_and_lending_rates"): "PARTIAL_TARGET_SPECIFIC_FORM_NOT_INTEGRATED",
    ("market_and_lending_rates", "credit_flow"): "RATE_PRICE_AND_CREDIT_TRANSACTION_BOUNDARIES_DISTINCT_JOINT_DETERMINATION_UNRESOLVED",
    ("credit_flow", "private_demand_and_investment"): "FINANCING_FLOW_PURPOSES_MULTIPLE_PRIVATE_DEMAND_AND_INVESTMENT_MAPPING_UNIDENTIFIED",
    ("private_demand_and_investment", "inflationary_pressure"): "MULTI_DRIVER_INFLATION_HICP_OBSERVABLE_DEMAND_CONTRIBUTION_NOT_IDENTIFIED",
    ("inflationary_pressure", "policy_rate"): "POLICY_RATE_OBSERVED_FORCING_REACTION_FUNCTION_MEASUREMENT_AND_IDENTIFICATION_BLOCKED",
}

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_monetary_credit_transmission_loop_terminal_assessment(
    assessment: dict,
    feedback: dict,
    readiness: dict,
    boundary: dict,
    criteria: dict,
    delays: dict,
    mechanisms: dict,
    prospective: dict,
    reaction_terminal: dict,
    reference_modes: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != STATUS:
        errors.append("terminal decision changed")
    if assessment["loop_id"] != "monetary_credit_transmission_loop":
        errors.append("terminal loop id changed")

    topology = assessment["topology"]
    if topology["status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("qualitative topology changed")
    if topology["qualitative_topology_retained"] is not True:
        errors.append("qualitative topology must remain retained")
    if topology["quantitatively_active"] is not False:
        errors.append("terminal assessment may not activate loop")
    if topology["behavioural_closure_active"] is not False:
        errors.append("terminal assessment may not activate behavioural closure")

    loop = next(x for x in feedback["loops"] if x["id"] == "monetary_credit_transmission_loop")
    if loop["quantitatively_active"] is not False:
        errors.append("feedback registry loop became quantitatively active")
    if loop.get("structural_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("feedback registry lacks terminal assessment")
    if loop.get("structural_review_status") != STATUS:
        errors.append("feedback registry terminal status changed")
    if loop.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("feedback registry operational state changed")
    if loop.get("active_empirical_task") is not None:
        errors.append("feedback registry may not expose an active monetary task")

    rows = [x for x in readiness["links"] if x["loop_id"] == "monetary_credit_transmission_loop"]
    if len(rows) != 5:
        errors.append(f"expected 5 monetary links, observed {len(rows)}")
    for row in rows:
        key = (row["from"], row["to"])
        expected = EXPECTED_LINK_STATUSES.get(key)
        if expected is None:
            errors.append(f"unexpected monetary link {key}")
            continue
        if row["readiness_status"] != expected:
            errors.append(f"{key}: readiness status changed")
        if row["exact_integrated_equation_ready"] is not False:
            errors.append(f"{key}: exact integrated equation may not be ready")
        if row["current_activation_authorized"] is not False:
            errors.append(f"{key}: link activation may not be authorized")

    first = next(x for x in rows if x["from"] == "policy_rate")
    if first.get("policy_rate_to_market_and_lending_rates_boundary_status") != "TARGET_SPECIFIC_PASS_THROUGH_CANDIDATE_AVAILABLE_GENERIC_RATE_NODE_UNRESOLVED":
        errors.append("target-specific pass-through boundary status changed")

    integrated = next(
        x for x in readiness["loop_activation_readiness"]
        if x["loop_id"] == "monetary_credit_transmission_loop"
    )
    if integrated["path_link_count"] != 5:
        errors.append("integrated path-link count changed")
    if integrated["exact_integrated_link_forms_ready"] != 0:
        errors.append("terminal state may not have exact-ready links")
    if set(integrated["unresolved_boundary_nodes"]) != {
        "market_and_lending_rates", "credit_flow",
        "private_demand_and_investment", "inflationary_pressure",
    }:
        errors.append("unresolved monetary-loop node set changed")
    if integrated["activation_status"] != "BLOCKED":
        errors.append("integrated readiness must remain blocked")
    if integrated["quantitative_activation_authorized"] is not False:
        errors.append("integrated readiness may not authorize activation")
    for blocker in assessment["integrated_readiness"]["blockers"]:
        if blocker not in integrated["blockers"]:
            errors.append(f"required integrated blocker missing: {blocker}")

    by_id = {x["id"]: x for x in boundary["variables"]}
    for node_id in (
        "market_and_lending_rates", "credit_flow",
        "private_demand_and_investment", "inflationary_pressure",
    ):
        if by_id[node_id]["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: terminal assessment may not resolve node")
        if by_id[node_id]["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: terminal assessment may not activate node")
    policy = by_id["policy_rate"]
    if policy["current_boundary_class"] != "OBSERVED_FORCING":
        errors.append("policy rate must remain observed forcing")
    if policy["current_feedback_activation_authorized"] is not False:
        errors.append("policy-rate node may not activate")

    policy_mode = next(x for x in reference_modes["modes"] if x["id"] == "policy_rate")
    if policy_mode["current_endogeneity"] != "EXOGENOUS_OBSERVED_INPUT":
        errors.append("policy-rate reference mode endogeneity changed")
    if any(x["id"] == "inflationary_pressure" for x in reference_modes["modes"]):
        errors.append("inflationary_pressure may not become a core reference mode")

    criterion = next(
        x for x in criteria["feedbacks"]
        if x["loop_id"] == "monetary_credit_transmission_loop"
    )
    snap = assessment["activation_gate_snapshot"]
    for key in (
        "passed_criteria_count", "partial_criteria_count",
        "blocked_criteria_count", "not_assessable_criteria_count",
    ):
        if criterion[key] != snap[key]:
            errors.append(f"activation-gate count changed: {key}")
    if criterion["all_requirements_pass"] is not False:
        errors.append("activation criteria may not all pass")
    if criterion["quantitative_activation_authorized"] is not False:
        errors.append("activation criteria may not authorize loop")

    delay = next(x for x in delays["delays"] if x["id"] == "monetary_transmission_delay")
    if delay["current_tau"] != "TBD":
        errors.append("monetary transmission tau may not be inferred")
    if delay["scalar_tau_activation_ready"] is not False:
        errors.append("monetary transmission scalar delay may not be activation-ready")

    mechanism_by = {x["id"]: x for x in mechanisms["mechanisms"]}
    pass_through = mechanism_by["monetary_policy_lending_rate_pass_through"]
    reaction = mechanism_by["monetary_policy_reaction_function"]
    if pass_through["classification"] != "CANDIDATE":
        errors.append("pass-through classification changed")
    if pass_through.get("implementation_scope") != "HOUSEHOLD_HOUSING_TARGET_SPECIFIC_ONLY":
        errors.append("pass-through implementation scope changed")
    if pass_through.get("implementation_not_generic_feedback_link") is not True:
        errors.append("target-specific pass-through may not become generic feedback")
    if reaction["classification"] != "DEFERRED":
        errors.append("policy-reaction classification changed")

    if prospective["identification_gate"]["status"] != "WAIT_FOR_NEW_POLICY_RATE_EVENT":
        errors.append("prospective monetary gate changed")
    if prospective["identification_gate"]["identifying_driver_variation_available"] is not False:
        errors.append("prospective identifying variation may not be inferred")
    if prospective["disposition"]["validated_reference_behavioural_mechanisms"] != 0:
        errors.append("prospective confirmation may not validate a mechanism")

    reaction_effect = reaction_terminal["model_effect"]
    if reaction_effect["mechanism_classification"] != "DEFERRED":
        errors.append("reaction source-discovery terminal classification changed")
    if reaction_effect["estimation_or_refit_allowed"] is not False:
        errors.append("reaction source-discovery may not authorize estimation")
    if reaction_effect["policy_rule_activation"] is not False:
        errors.append("reaction source-discovery may not activate policy rule")

    findings = assessment["no_further_current_evidence_task_findings"]
    for key, value in findings.items():
        if key != "interpretation" and value is not False:
            errors.append(f"terminal finding may not authorize {key}")

    disposition = assessment["disposition"]
    if disposition["structural_review_complete"] is not True:
        errors.append("structural review must be complete")
    if disposition["current_operational_state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("terminal operational state changed")
    if disposition["active_empirical_task"] is not None:
        errors.append("terminal hold may not expose active task")
    for key in (
        "exact_integrated_equation_ready", "parameter_estimation_authorized",
        "final_holdout_opening_authorized", "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "core_inflation_reference_mode_extension_authorized",
        "public_version_change_authorized", "qualitative_topology_changed",
    ):
        if disposition[key] is not False:
            errors.append(f"terminal assessment may not promote {key}")

    next_state = assessment["next_state"]
    if next_state["id"] != HOLD_ID:
        errors.append("terminal next-state id changed")
    if next_state["authorization"] != "NO_ACTIVE_TASK_UNTIL_DECLARED_REOPEN_TRIGGER":
        errors.append("terminal hold authorization changed")
    if next_state["reopen_trigger_required"] is not True:
        errors.append("terminal hold must require a reopen trigger")
    for key in (
        "may_poll_unchanged_sources", "may_respecify_frozen_candidates",
        "may_open_unopened_holdouts", "may_estimate_parameters",
        "may_endogenize_policy_rate", "may_add_core_inflation_reference_mode",
        "may_activate_feedback", "may_change_behavioural_closure",
        "may_relax_existing_gates",
    ):
        if next_state[key] is not False:
            errors.append(f"terminal hold may not authorize {key}")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("monetary_credit_transmission_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks monetary terminal assessment")
    if dynamic.get("monetary_credit_transmission_loop_structural_review_status") != STATUS:
        errors.append("model contract terminal status changed")
    if dynamic.get("monetary_credit_transmission_loop_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("model contract operational state changed")
    if dynamic.get("monetary_credit_transmission_loop_active_empirical_task") is not None:
        errors.append("model contract may not expose active monetary task")
    if dynamic.get("monetary_credit_transmission_next_structural_task") != HOLD_ID:
        errors.append("model contract next-state pointer changed")
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("model contract behavioural closure changed")

    if baseline["authority"].get("monetary_credit_transmission_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks monetary terminal assessment")

    return errors

def main() -> None:
    errors = audit_monetary_credit_transmission_loop_terminal_assessment(
        load(ASSESSMENT_PATH),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/empirical_dynamics/mechanism_registry.json"),
        load("model/calibration_validation/prospective_monetary_confirmation_status.json"),
        load("model/calibration_validation/monetary_policy_reaction_source_discovery_terminal_assessment.json"),
        load("model/dynamics/reference_modes.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Monetary-credit transmission terminal assessment failed:\n- "
            + "\n- ".join(errors)
        )
    print(json.dumps({
        "status":"PASS",
        "terminal_status":STATUS,
        "exact_integrated_link_forms_ready":0,
        "activation_status":"BLOCKED",
        "policy_rate_endogeneity":"EXOGENOUS_OBSERVED_INPUT",
        "operational_state":"EVIDENCE_TRIGGERED_HOLD",
        "active_empirical_task":None,
        "feedback_activation_authorized":False,
    }, indent=2))

if __name__ == "__main__":
    main()
