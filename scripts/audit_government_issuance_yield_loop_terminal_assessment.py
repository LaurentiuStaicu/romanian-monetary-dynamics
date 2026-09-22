from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/government_issuance_yield_loop_terminal_assessment_2026_09_21.json"
STATUS = "STRUCTURAL_REVIEW_COMPLETE_SOURCE_AND_IDENTIFICATION_BLOCKED_EVIDENCE_TRIGGERED_HOLD"

EXPECTED_LINK_STATUSES = {
    ("government_debt_issuance", "government_securities_supply_pressure"):
        "STRUCTURAL_RELATION_NOT_CONTRACTED_AS_INTEGRATED_EQUATION",
    ("government_securities_supply_pressure", "sovereign_yield"):
        "TARGET_BOUNDARY_AVAILABLE_LINK_FORM_UNRESOLVED",
    ("sovereign_yield", "government_interest_cost"):
        "TARGETS_AVAILABLE_REPRICING_TRANSITION_UNIDENTIFIED",
    ("government_interest_cost", "government_financing_need"):
        "ACCOUNTING_COMPOSITION_FORM_KNOWN_BOUNDARY_NOT_CANONICAL",
    ("government_financing_need", "government_debt_issuance"):
        "MULTI_CHANNEL_STRUCTURE_CONFIRMED_ALLOCATION_VECTOR_NOT_IDENTIFIED",
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_issuance_yield_loop_terminal_assessment(
    assessment: dict,
    feedback: dict,
    readiness: dict,
    boundary: dict,
    criteria: dict,
    delays: dict,
    mechanisms: dict,
    selection: dict,
    missing_sources: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != STATUS:
        errors.append("issuance-yield terminal decision changed")
    if assessment["loop_id"] != "government_issuance_yield_loop":
        errors.append("issuance-yield terminal loop id changed")

    topology = assessment["topology"]
    if topology["status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("issuance-yield qualitative topology changed")
    if topology["qualitative_topology_retained"] is not True:
        errors.append("issuance-yield qualitative topology must remain retained")
    if topology["quantitatively_active"] is not False:
        errors.append("issuance-yield terminal assessment may not activate loop")
    if topology["behavioural_closure_active"] is not False:
        errors.append("issuance-yield terminal assessment may not activate behavioural closure")

    loop = next(x for x in feedback["loops"] if x["id"] == "government_issuance_yield_loop")
    if loop["quantitatively_active"] is not False:
        errors.append("feedback registry issuance-yield loop became quantitatively active")
    if loop.get("structural_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("feedback registry lacks issuance-yield terminal assessment")
    if loop.get("structural_review_status") != STATUS:
        errors.append("feedback registry issuance-yield terminal status changed")
    if loop.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("feedback registry issuance-yield operational state changed")
    if loop.get("active_empirical_task") is not None:
        errors.append("feedback registry issuance-yield loop may not expose an active empirical task")

    rows = [x for x in readiness["links"] if x["loop_id"] == "government_issuance_yield_loop"]
    if len(rows) != 5:
        errors.append(f"expected 5 issuance-yield links, observed {len(rows)}")
    for row in rows:
        key = (row["from"], row["to"])
        expected = EXPECTED_LINK_STATUSES.get(key)
        if expected is None:
            errors.append(f"unexpected issuance-yield link {key}")
            continue
        if row["readiness_status"] != expected:
            errors.append(f"{key}: issuance-yield readiness status changed")
        if row["exact_integrated_equation_ready"] is not False:
            errors.append(f"{key}: exact integrated equation may not be ready")
        if row["current_activation_authorized"] is not False:
            errors.append(f"{key}: link activation may not be authorized")

    integrated = next(
        x for x in readiness["loop_activation_readiness"]
        if x["loop_id"] == "government_issuance_yield_loop"
    )
    if integrated["path_link_count"] != 5:
        errors.append("issuance-yield integrated path-link count changed")
    if integrated["exact_integrated_link_forms_ready"] != 0:
        errors.append("issuance-yield terminal state may not have exact-ready links")
    if set(integrated["unresolved_boundary_nodes"]) != {
        "government_debt_issuance",
        "government_securities_supply_pressure",
        "sovereign_yield",
        "government_interest_cost",
        "government_financing_need",
    }:
        errors.append("issuance-yield unresolved node set changed")
    if integrated["activation_status"] != "BLOCKED":
        errors.append("issuance-yield integrated readiness must remain blocked")
    if integrated["quantitative_activation_authorized"] is not False:
        errors.append("issuance-yield integrated readiness may not authorize activation")
    for blocker in assessment["integrated_readiness"]["blockers"]:
        if blocker not in integrated["blockers"]:
            errors.append(f"issuance-yield required blocker missing: {blocker}")

    by_id = {x["id"]: x for x in boundary["variables"]}
    for node_id in (
        "government_debt_issuance",
        "government_securities_supply_pressure",
        "sovereign_yield",
        "government_interest_cost",
        "government_financing_need",
    ):
        if by_id[node_id]["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: terminal assessment may not resolve node")
        if by_id[node_id]["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: terminal assessment may not activate node")

    criterion = next(
        x for x in criteria["feedbacks"]
        if x["loop_id"] == "government_issuance_yield_loop"
    )
    snap = assessment["activation_gate_snapshot"]
    for key in (
        "passed_criteria_count",
        "partial_criteria_count",
        "blocked_criteria_count",
        "not_assessable_criteria_count",
    ):
        if criterion[key] != snap[key]:
            errors.append(f"issuance-yield activation-gate count changed: {key}")
    if criterion["all_requirements_pass"] is not False:
        errors.append("issuance-yield activation criteria may not all pass")
    if criterion["quantitative_activation_authorized"] is not False:
        errors.append("issuance-yield activation criteria may not authorize loop")

    delay_by_id = {x["id"]: x for x in delays["delays"]}
    for delay_id in ("portfolio_reallocation_delay", "debt_service_maturity_delay"):
        delay = delay_by_id[delay_id]
        if delay["current_tau"] != "TBD":
            errors.append(f"{delay_id}: scalar tau may not be inferred")
        if delay["scalar_tau_activation_ready"] is not False:
            errors.append(f"{delay_id}: scalar delay may not be activation-ready")

    mechanism = next(
        x for x in mechanisms["mechanisms"]
        if x["id"] == "sovereign_yield_spread_response"
    )
    if mechanism["classification"] != "CANDIDATE":
        errors.append("sovereign-yield mechanism classification changed")
    if mechanism["implementation"] is not None:
        errors.append("failed sovereign-yield form may not gain an implementation")
    disposition = mechanism["structural_selection_disposition"]
    if disposition["status"] != "TESTED_FORM_FAILED_BEFORE_HOLDOUT":
        errors.append("sovereign-yield structural-selection disposition changed")
    if selection["selection_verdict"] != "FAIL_BEFORE_HOLDOUT":
        errors.append("sovereign-yield selection verdict changed")
    if selection["final_evaluation_opened"] is not False:
        errors.append("sovereign-yield final evaluation may not be opened")
    if selection["causal_claim_allowed"] is not False:
        errors.append("sovereign-yield causal claim may not be allowed")
    if selection["system_dynamics_activation"] is not False:
        errors.append("sovereign-yield form may not activate System Dynamics feedback")

    source_state = assessment["supply_source_state"]
    current = missing_sources["current_materialisation"]
    if source_state["required_missing_source_count"] != current["required_missing_source_count"]:
        errors.append("remaining announced-supply source count changed")
    if source_state["retained_required_source_count"] != current["retained_required_source_count"]:
        errors.append("retained announced-supply source count changed")
    if source_state["exact_final_month_count"] != current["exact_final_month_count"]:
        errors.append("exact final announced-supply month count changed")
    if source_state["event_level_complete_final_month_count"] != current["event_level_complete_final_month_count"]:
        errors.append("event-level complete announced-supply month count changed")
    if missing_sources["path_disposition"]["state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("announced-supply source path must remain on evidence-triggered hold")
    if missing_sources["path_disposition"]["active_polling"] is not False:
        errors.append("announced-supply source path may not resume unchanged-source polling")
    if current["canonical_reference_mode_promoted"] is not False:
        errors.append("partial announced-supply source may not be canonically promoted")

    findings = assessment["no_further_current_evidence_task_findings"]
    for key in (
        "repeat_missing_source_polling_scientifically_useful",
        "synthetic_supply_pressure_scalar_authorized",
        "post_hoc_primary_yield_aggregation_authorized",
        "failed_sovereign_yield_form_refit_authorized",
        "final_holdout_opening_authorized",
        "aggregate_proxy_repricing_fit_authorized",
        "residual_financing_channel_allocation_authorized",
    ):
        if findings[key] is not False:
            errors.append(f"issuance-yield terminal finding may not authorize {key}")

    terminal = assessment["disposition"]
    if terminal["structural_review_complete"] is not True:
        errors.append("issuance-yield structural review must be complete")
    if terminal["current_operational_state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("issuance-yield terminal operational state changed")
    if terminal["active_empirical_task"] is not None:
        errors.append("issuance-yield terminal hold may not expose an active empirical task")
    for key in (
        "exact_integrated_equation_ready",
        "parameter_estimation_authorized",
        "final_holdout_opening_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
        "qualitative_topology_changed",
    ):
        if terminal[key] is not False:
            errors.append(f"issuance-yield terminal assessment may not promote {key}")

    next_state = assessment["next_state"]
    if next_state["id"] != "government_issuance_yield_loop_evidence_triggered_hold":
        errors.append("issuance-yield next-state id changed")
    if next_state["authorization"] != "NO_ACTIVE_TASK_UNTIL_DECLARED_REOPEN_TRIGGER":
        errors.append("issuance-yield hold authorization changed")
    if next_state["reopen_trigger_required"] is not True:
        errors.append("issuance-yield hold must require a reopen trigger")
    for key in (
        "may_poll_unchanged_sources",
        "may_refit_failed_behavioural_form",
        "may_open_final_holdout",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
        "may_relax_existing_gates",
    ):
        if next_state[key] is not False:
            errors.append(f"issuance-yield hold may not authorize {key}")

    if prereg.get("government_issuance_yield_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("issuance-yield preregistration lacks terminal assessment")
    if prereg.get("government_issuance_yield_loop_structural_review_status") != STATUS:
        errors.append("issuance-yield preregistration terminal status changed")
    if prereg.get("government_issuance_yield_loop_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("issuance-yield preregistration operational state changed")
    if prereg.get("government_issuance_yield_loop_active_empirical_task") is not None:
        errors.append("issuance-yield preregistration may not expose an active task")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("government_issuance_yield_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks issuance-yield terminal assessment")
    if dynamic.get("government_issuance_yield_loop_structural_review_status") != STATUS:
        errors.append("model contract issuance-yield terminal status changed")
    if dynamic.get("government_issuance_yield_loop_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("model contract issuance-yield operational state changed")
    if dynamic.get("government_issuance_yield_loop_active_empirical_task") is not None:
        errors.append("model contract may not expose an active issuance-yield task")
    if dynamic.get("next_government_issuance_yield_empirical_task") != "government_issuance_yield_loop_evidence_triggered_hold":
        errors.append("model contract government issuance-yield next-task pointer is stale")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("model contract behavioural closure changed")

    if baseline["authority"].get("government_issuance_yield_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks issuance-yield terminal-assessment authority")

    return errors


def main() -> None:
    errors = audit_government_issuance_yield_loop_terminal_assessment(
        load(ASSESSMENT_PATH),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/empirical_dynamics/mechanism_registry.json"),
        load("model/calibration_validation/sovereign_yield_structural_selection_result.json"),
        load("model/dynamics/mof_announced_RON_primary_reference_auction_missing_source_recovery_assessment_2026_09_20.json"),
        load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Government issuance-yield terminal assessment failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status":"PASS",
        "terminal_status":STATUS,
        "exact_integrated_link_forms_ready":0,
        "activation_status":"BLOCKED",
        "operational_state":"EVIDENCE_TRIGGERED_HOLD",
        "active_empirical_task":None,
        "feedback_activation_authorized":False,
    }, indent=2))


if __name__ == "__main__":
    main()
