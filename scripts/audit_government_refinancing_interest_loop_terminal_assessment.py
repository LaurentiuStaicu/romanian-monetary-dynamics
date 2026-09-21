from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/government_refinancing_interest_loop_terminal_assessment_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "STRUCTURAL_REVIEW_COMPLETE_CURRENT_EVIDENCE_INSUFFICIENT_EVIDENCE_TRIGGERED_HOLD"
HOLD_ID = "government_refinancing_interest_loop_evidence_triggered_hold"

EXPECTED_LINK_STATUSES = {
    ("government_financing_need", "government_debt_issuance"):
        "MULTI_CHANNEL_STRUCTURE_CONFIRMED_ALLOCATION_VECTOR_NOT_IDENTIFIED",
    ("government_debt_issuance", "government_debt_stock"):
        "STOCK_ACCUMULATION_FORM_KNOWN_NET_DEBT_TRANSACTION_BOUNDARY_NOT_IDENTIFIED",
    ("government_debt_stock", "government_interest_cost"):
        "ACCOUNTING_SCALE_FORM_KNOWN_RATE_BOUNDARY_NOT_CANONICAL",
    ("government_interest_cost", "government_financing_need"):
        "ACCOUNTING_COMPOSITION_FORM_KNOWN_BOUNDARY_NOT_CANONICAL",
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_refinancing_interest_loop_terminal_assessment(
    assessment: dict,
    feedback: dict,
    readiness: dict,
    boundary: dict,
    criteria: dict,
    delays: dict,
    mechanisms: dict,
    repricing: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != STATUS:
        errors.append("terminal decision changed")
    if assessment["loop_id"] != "government_refinancing_interest_loop":
        errors.append("terminal assessment loop id changed")

    topology = assessment["topology"]
    if topology["status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("qualitative topology status changed")
    if topology["quantitatively_active"] is not False:
        errors.append("terminal assessment may not activate loop")
    if topology["behavioural_closure_active"] is not False:
        errors.append("terminal assessment may not activate behavioural closure")

    loop = next(x for x in feedback["loops"] if x["id"] == "government_refinancing_interest_loop")
    if loop["quantitatively_active"] is not False:
        errors.append("feedback registry loop became quantitatively active")
    if loop.get("structural_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("feedback registry lacks terminal assessment")
    if loop.get("structural_review_status") != STATUS:
        errors.append("feedback registry terminal status changed")
    if loop.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("feedback registry operational state changed")

    rows = [x for x in readiness["links"] if x["loop_id"] == "government_refinancing_interest_loop"]
    if len(rows) != 4:
        errors.append(f"expected 4 loop links, observed {len(rows)}")
    for row in rows:
        key = (row["from"], row["to"])
        expected = EXPECTED_LINK_STATUSES.get(key)
        if expected is None:
            errors.append(f"unexpected refinancing-loop link {key}")
            continue
        if row["readiness_status"] != expected:
            errors.append(f"{key}: readiness status changed")
        if row["exact_integrated_equation_ready"] is not False:
            errors.append(f"{key}: exact equation may not be ready")
        if row["current_activation_authorized"] is not False:
            errors.append(f"{key}: link activation may not be authorized")

    integrated = next(
        x for x in readiness["loop_activation_readiness"]
        if x["loop_id"] == "government_refinancing_interest_loop"
    )
    if integrated["path_link_count"] != 4:
        errors.append("integrated path-link count changed")
    if integrated["exact_integrated_link_forms_ready"] != 0:
        errors.append("terminal state may not have exact-ready links")
    if set(integrated["unresolved_boundary_nodes"]) != {
        "government_financing_need",
        "government_debt_issuance",
        "government_debt_stock",
        "government_interest_cost",
    }:
        errors.append("unresolved refinancing-loop node set changed")
    if integrated["activation_status"] != "BLOCKED":
        errors.append("integrated readiness must remain blocked")
    if integrated["quantitative_activation_authorized"] is not False:
        errors.append("integrated readiness may not authorize activation")
    for blocker in assessment["integrated_readiness"]["blockers"]:
        if blocker not in integrated["blockers"]:
            errors.append(f"required integrated blocker missing: {blocker}")

    by_id = {x["id"]: x for x in boundary["variables"]}
    for node_id in (
        "government_financing_need",
        "government_debt_issuance",
        "government_debt_stock",
        "government_interest_cost",
    ):
        if by_id[node_id]["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: terminal assessment may not resolve node")
        if by_id[node_id]["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: terminal assessment may not activate node")

    criterion = next(
        x for x in criteria["feedbacks"]
        if x["loop_id"] == "government_refinancing_interest_loop"
    )
    snap = assessment["activation_gate_snapshot"]
    for key in (
        "passed_criteria_count",
        "partial_criteria_count",
        "blocked_criteria_count",
        "not_assessable_criteria_count",
    ):
        if criterion[key] != snap[key]:
            errors.append(f"activation-gate count changed: {key}")
    if criterion["all_requirements_pass"] is not False:
        errors.append("activation criteria may not all pass")
    if criterion["quantitative_activation_authorized"] is not False:
        errors.append("activation criteria may not authorize loop")

    delay = next(x for x in delays["delays"] if x["id"] == "debt_service_maturity_delay")
    if delay["current_tau"] != "TBD":
        errors.append("debt-service delay tau may not be inferred")
    if delay["scalar_tau_activation_ready"] is not False:
        errors.append("debt-service scalar delay may not be activation-ready")

    mechanism_by_id = {x["id"]: x for x in mechanisms["mechanisms"]}
    for mechanism_id in ("government_refinancing_effective_rate", "fiscal_primary_balance_reaction"):
        if mechanism_by_id[mechanism_id]["classification"] != "DEFERRED":
            errors.append(f"{mechanism_id}: mechanism classification changed")

    if repricing["final_verdict"] != "DEFERRED":
        errors.append("government repricing verdict changed")
    if repricing["gate_results"]["gate_1_ledger_completeness"]["status"] != "FAIL":
        errors.append("repricing completeness gate changed")
    if repricing["gate_results"]["gate_4_parameter_identification"]["status"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("repricing identification gate changed")
    if repricing["estimation"]["run"] is not False:
        errors.append("repricing estimation may not run")

    findings = assessment["no_further_current_evidence_task_findings"]
    for key in (
        "repeat_same_source_searches_scientifically_useful",
        "apparent_cost_materialisation_would_resolve_rate_endogeneity",
        "aggregate_proxy_refit_would_resolve_repricing_identification",
        "current_maturity_statistics_can_supply_scalar_tau",
        "residual_or_synthetic_allocations_authorized",
    ):
        if findings[key] is not False:
            errors.append(f"terminal finding may not authorize {key}")

    disposition = assessment["disposition"]
    if disposition["structural_review_complete"] is not True:
        errors.append("structural review must be complete")
    if disposition["current_operational_state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("terminal operational state changed")
    if disposition["active_empirical_task"] is not None:
        errors.append("terminal hold may not expose an active empirical task")
    for key in (
        "exact_integrated_equation_ready",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
        "qualitative_topology_changed",
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
        "may_poll_unchanged_sources",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
        "may_relax_existing_gates",
    ):
        if next_state[key] is not False:
            errors.append(f"terminal hold may not authorize {key}")

    next_task = prereg["next_independent_bridge_task"]
    if next_task["id"] != HOLD_ID:
        errors.append("preregistration next state changed")
    if next_task["authorization"] != "NO_ACTIVE_TASK_UNTIL_DECLARED_REOPEN_TRIGGER":
        errors.append("preregistration hold authorization changed")
    if next_task["reopen_trigger_required"] is not True:
        errors.append("preregistration hold must require a reopen trigger")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("government_refinancing_interest_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks terminal assessment")
    if dynamic.get("government_refinancing_interest_loop_structural_review_status") != STATUS:
        errors.append("model contract terminal status changed")
    if dynamic.get("government_refinancing_interest_loop_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("model contract loop operational state changed")
    if dynamic.get("government_refinancing_interest_loop_active_empirical_task") is not None:
        errors.append("model contract may not expose active refinancing task")
    if dynamic.get("government_issuance_yield_next_independent_task") != HOLD_ID:
        errors.append("model contract next-state pointer changed")
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("model contract behavioural closure changed")

    if baseline["authority"].get("government_refinancing_interest_loop_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks terminal-assessment authority")

    return errors


def main() -> None:
    errors = audit_government_refinancing_interest_loop_terminal_assessment(
        load(ASSESSMENT_PATH),
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/empirical_dynamics/mechanism_registry.json"),
        load("model/calibration_validation/government_repricing_ledger_assessment.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Government refinancing-interest terminal assessment failed:\n- "
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
