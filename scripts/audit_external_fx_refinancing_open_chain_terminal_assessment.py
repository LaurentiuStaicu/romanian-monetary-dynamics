from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/dynamics/external_fx_refinancing_open_chain_terminal_assessment_2026_09_21.json"
P1 = "model/dynamics/exchange_rate_depreciation_to_fx_debt_service_burden_boundary_review_2026_09_21.json"
P2 = "model/dynamics/fx_debt_service_burden_to_refinancing_need_boundary_review_2026_09_21.json"
P3 = "model/dynamics/refinancing_need_to_risk_premium_boundary_review_2026_09_21.json"
P4 = "model/dynamics/risk_premium_to_exchange_rate_pressure_boundary_review_2026_09_21.json"
STATUS = "STRUCTURAL_REVIEW_COMPLETE_OPEN_CHAIN_MEASUREMENT_AND_IDENTIFICATION_BLOCKED_EVIDENCE_TRIGGERED_HOLD"
HOLD_ID = "external_fx_refinancing_open_chain_evidence_triggered_hold"

EXPECTED_LINKS = {
    ("exchange_rate_depreciation", "fx_debt_service_burden"): (
        "FX_DEBT_SERVICE_TRANSLATION_CONDITIONAL_JOINT_CURRENCY_RESIDUAL_MATURITY_HEDGING_UNRESOLVED", P1
    ),
    ("fx_debt_service_burden", "refinancing_need"): (
        "DEBT_SERVICE_DUE_NOT_EQUAL_REFINANCING_NEED_SECTOR_LIQUIDITY_AND_BUFFER_BOUNDARY_UNRESOLVED", P2
    ),
    ("refinancing_need", "risk_premium"): (
        "MULTI_DRIVER_RISK_PREMIUM_REFINANCING_CONTRIBUTION_NOT_IDENTIFIED", P3
    ),
    ("risk_premium", "exchange_rate_pressure"): (
        "RISK_PREMIUM_AND_EXCHANGE_RATE_PRESSURE_SIMULTANEOUS_MANAGED_FLOAT_BOUNDARY_UNRESOLVED", P4
    ),
}

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_external_fx_refinancing_open_chain_terminal_assessment(
    assessment: dict,
    reviews: list[dict],
    feedback: dict,
    readiness: dict,
    boundary: dict,
    criteria: dict,
    delays: dict,
    mechanisms: dict,
    source_boundary: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != STATUS:
        errors.append("terminal decision changed")
    if assessment["loop_id"] != "external_fx_refinancing_loop":
        errors.append("terminal structure id changed")

    topology = assessment["topology"]
    if topology["status"] != "OPEN_CHAIN":
        errors.append("external FX structure may not be relabelled as a closed loop")
    if topology["closing_link_inferred"] is not False:
        errors.append("terminal assessment may not infer a closing link")
    if topology["quantitatively_active"] is not False:
        errors.append("external FX chain may not activate")
    if topology["behavioural_closure_active"] is not False:
        errors.append("behavioural closure may not activate")

    for review in reviews:
        for key, value in review["hard_rules"].items():
            if value is not True:
                errors.append(f"{review.get('gate_id')}: hard rule disabled: {key}")
        bridge = review["bridge_resolution"]
        if bridge["exact_integrated_equation_ready"] is not False:
            errors.append(f"{review.get('gate_id')}: exact equation may not be ready")
        if bridge["parameter_estimation_authorized"] is not False:
            errors.append(f"{review.get('gate_id')}: parameter estimation may not open")
        if bridge["feedback_activation_authorized"] is not False:
            errors.append(f"{review.get('gate_id')}: feedback activation may not open")

    loop = next(x for x in feedback["loops"] if x["id"] == "external_fx_refinancing_loop")
    if loop["topology_status"] != "OPEN_CHAIN":
        errors.append("feedback registry topology changed")
    if loop["quantitatively_active"] is not False:
        errors.append("feedback registry chain became active")
    if loop.get("closing_link_authorized") is not False:
        errors.append("feedback registry may not authorize a closing link")
    if loop.get("structural_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("feedback registry lacks terminal assessment")
    if loop.get("structural_review_status") != STATUS:
        errors.append("feedback registry terminal status changed")
    if loop.get("operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("feedback registry operational state changed")
    if loop.get("active_empirical_task") is not None:
        errors.append("feedback registry may not expose an active FX task")

    rows = [x for x in readiness["links"] if x["loop_id"] == "external_fx_refinancing_loop"]
    if len(rows) != 4:
        errors.append(f"expected 4 external FX links, observed {len(rows)}")
    for row in rows:
        key = (row["from"], row["to"])
        expected = EXPECTED_LINKS.get(key)
        if expected is None:
            errors.append(f"unexpected external FX link {key}")
            continue
        status, review_path = expected
        if row["readiness_status"] != status:
            errors.append(f"{key}: readiness status changed")
        if row.get("boundary_review") != review_path:
            errors.append(f"{key}: boundary review pointer changed")
        if row["exact_integrated_equation_ready"] is not False:
            errors.append(f"{key}: exact integrated equation may not be ready")
        if row["current_activation_authorized"] is not False:
            errors.append(f"{key}: link activation may not be authorized")

    integrated = next(
        x for x in readiness["loop_activation_readiness"]
        if x["loop_id"] == "external_fx_refinancing_loop"
    )
    if integrated["topology_status"] != "OPEN_CHAIN":
        errors.append("integrated topology changed")
    if integrated["path_link_count"] != 4:
        errors.append("integrated path-link count changed")
    if integrated["exact_integrated_link_forms_ready"] != 0:
        errors.append("external FX chain may not have exact-ready links")
    expected_nodes = {
        "exchange_rate_depreciation", "fx_debt_service_burden",
        "refinancing_need", "risk_premium", "exchange_rate_pressure",
    }
    if set(integrated["unresolved_boundary_nodes"]) != expected_nodes:
        errors.append("unresolved external FX node set changed")
    if "OPEN_CHAIN_NOT_CLOSED" not in integrated["blockers"]:
        errors.append("open-chain blocker missing")
    if integrated["activation_status"] != "BLOCKED":
        errors.append("integrated activation must remain blocked")
    if integrated["quantitative_activation_authorized"] is not False:
        errors.append("integrated activation may not be authorized")

    by_id = {x["id"]: x for x in boundary["variables"]}
    for node_id in expected_nodes:
        node = by_id[node_id]
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: may not resolve without new evidence")
        if node["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: may not activate")
    if by_id["exchange_rate_pressure"].get("open_chain_closing_link_authorized") is not False:
        errors.append("exchange-rate-pressure terminus may not authorize closing link")

    criterion = next(x for x in criteria["feedbacks"] if x["loop_id"] == "external_fx_refinancing_loop")
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
        errors.append("activation criteria may not authorize chain")
    if criterion["criteria"]["requires_polarity_and_loop_path"]["status"] != "BLOCKED":
        errors.append("open-chain topology criterion may not pass")

    for delay_id in ("refinancing_maturity_delay", "fx_pass_through_delay"):
        delay = next(x for x in delays["delays"] if x["id"] == delay_id)
        if delay["current_tau"] != "TBD":
            errors.append(f"{delay_id}: tau may not be inferred")
        if delay["scalar_tau_activation_ready"] is not False:
            errors.append(f"{delay_id}: scalar tau may not become activation-ready")

    mechanism = next(x for x in mechanisms["mechanisms"] if x["id"] == "external_fx_refinancing_feedback")
    if mechanism["classification"] != "DEFERRED":
        errors.append("external FX mechanism classification changed")
    if mechanism["implementation"] is not None:
        errors.append("external FX mechanism may not gain an implementation")

    if source_boundary["verdict"] != (
        "SECTOR_ORIGINAL_MATURITY_AND_PARTIAL_AGGREGATE_CURRENCY_RISK_MARGINS_OBSERVED_"
        "JOINT_CURRENCY_RESIDUAL_MATURITY_HEDGING_UNRESOLVED"
    ):
        errors.append("external FX source-boundary verdict changed")
    findings = source_boundary["source_boundary_findings"]
    for key in (
        "residual_maturity_schedule_available",
        "debt_currency_denomination_available_from_confirmed_series",
        "hedging_positions_available",
        "matched_interest_or_coupon_schedule_available",
        "joint_currency_by_sector_available",
        "joint_currency_x_residual_maturity_by_sector_available",
    ):
        if findings[key] is not False:
            errors.append(f"source boundary unexpectedly resolves {key}")

    no_task = assessment["no_further_current_evidence_task_findings"]
    for key, value in no_task.items():
        if key != "interpretation" and value is not False:
            errors.append(f"terminal finding may not authorize {key}")

    disposition = assessment["disposition"]
    if disposition["structural_review_complete"] is not True:
        errors.append("structural review must be complete")
    if disposition["current_operational_state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("terminal operational state changed")
    if disposition["active_empirical_task"] is not None:
        errors.append("terminal hold may not expose active task")
    if disposition["open_chain_remains_open"] is not True:
        errors.append("external FX chain must remain open")
    for key in (
        "closing_link_authorized", "exact_integrated_equation_ready",
        "parameter_estimation_authorized", "feedback_activation_authorized",
        "behavioural_closure_authorized", "public_version_change_authorized",
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
        "may_poll_unchanged_sources", "may_infer_joint_exposure",
        "may_infer_closing_link", "may_estimate_parameters",
        "may_activate_feedback", "may_change_behavioural_closure",
        "may_relax_existing_gates",
    ):
        if next_state[key] is not False:
            errors.append(f"terminal hold may not authorize {key}")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("external_fx_refinancing_open_chain_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks external FX terminal assessment")
    if dynamic.get("external_fx_refinancing_structural_review_status") != STATUS:
        errors.append("model contract terminal status changed")
    if dynamic.get("external_fx_refinancing_operational_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("model contract operational state changed")
    if dynamic.get("external_fx_refinancing_active_empirical_task") is not None:
        errors.append("model contract may not expose active FX task")
    if dynamic.get("external_fx_refinancing_next_structural_task") != HOLD_ID:
        errors.append("model contract next-state pointer changed")
    if dynamic.get("external_fx_refinancing_closing_link_authorized") is not False:
        errors.append("model contract may not authorize closing link")
    if dynamic["behavioural_closure_active"] is not False:
        errors.append("model contract behavioural closure changed")

    authority = baseline["authority"]
    for path in (P1, P2, P3, P4, ASSESSMENT_PATH):
        if path not in authority.values():
            errors.append(f"scientific baseline authority missing {path}")

    return errors

def main() -> None:
    errors = audit_external_fx_refinancing_open_chain_terminal_assessment(
        load(ASSESSMENT_PATH),
        [load(P1), load(P2), load(P3), load(P4)],
        load("model/dynamics/feedback_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_activation_criteria_matrix.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/empirical_dynamics/mechanism_registry.json"),
        load("model/calibration_validation/external_fx_refinancing_source_boundary_review.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "External FX-refinancing open-chain terminal assessment failed:\n- "
            + "\n- ".join(errors)
        )
    print(json.dumps({
        "status": "PASS",
        "terminal_status": STATUS,
        "topology": "OPEN_CHAIN",
        "exact_integrated_link_forms_ready": 0,
        "activation_status": "BLOCKED",
        "operational_state": "EVIDENCE_TRIGGERED_HOLD",
        "active_empirical_task": None,
        "closing_link_authorized": False,
        "feedback_activation_authorized": False,
    }, indent=2))

if __name__ == "__main__":
    main()
