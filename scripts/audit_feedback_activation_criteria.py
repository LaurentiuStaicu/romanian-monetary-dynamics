from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def feedback_nodes(loop: dict[str, object]) -> list[str]:
    nodes: list[str] = []
    for link in loop["path"]:
        for node in (str(link["from"]), str(link["to"])):
            if node not in nodes:
                nodes.append(node)
    return nodes


def expected_statuses(
    loop: dict[str, object],
    *,
    link_row: dict[str, object],
    boundary_by: dict[str, dict[str, object]],
    delay_by: dict[str, dict[str, object]],
    mechanism_by: dict[str, dict[str, object]],
    unit_implementations: set[str],
    robustness_by_mechanism: dict[str, dict[str, object]],
    validated_reference_behavioural_mechanisms: int,
    accounting_hard_constraint: bool,
    full_accounting_ready: bool,
) -> dict[str, str]:
    nodes = feedback_nodes(loop)
    mapped = [
        mechanism_by[item["id"]]
        for item in link_row.get("mapped_mechanisms", [])
        if item["id"] in mechanism_by
    ]
    implementations = [
        item for item in mapped if item.get("implementation") is not None
    ]
    robust_forms = [
        item for item in mapped if item["id"] in robustness_by_mechanism
    ]
    exact_reference_nodes = [
        node
        for node in nodes
        if boundary_by[node].get("exact_reference_mode_id") is not None
    ]
    unresolved = [
        node
        for node in nodes
        if boundary_by[node]["current_boundary_class"] == "UNRESOLVED"
    ]
    delay_rows = [
        delay_by[delay_id] for delay_id in loop.get("delay_candidates", [])
    ]

    all_exact = (
        int(link_row["path_link_count"]) > 0
        and int(link_row["exact_integrated_link_forms_ready"])
        == int(link_row["path_link_count"])
    )
    all_implementation_units = (
        bool(implementations)
        and all(
            str(item["implementation"]) in unit_implementations
            for item in implementations
        )
    )
    all_mapped_have_evidence = (
        bool(mapped)
        and all(bool(item.get("evidence")) for item in mapped)
    )
    all_mapped_have_plan = (
        bool(mapped)
        and all(
            isinstance(item.get("estimation_plan"), str)
            and bool(str(item["estimation_plan"]).strip())
            for item in mapped
        )
    )
    all_delays_ready = all(
        item.get("scalar_tau_activation_ready") is True for item in delay_rows
    )
    closed = loop.get("topology_status") == "CLOSED_CANDIDATE_LOOP"
    any_robust = bool(robust_forms)

    return {
        "requires_equation": "PASS" if all_exact else "BLOCKED",
        "requires_units": (
            "PASS" if all_exact and all_implementation_units else "BLOCKED"
        ),
        "requires_evidence_status": (
            "PASS"
            if all_exact and all_mapped_have_evidence
            else ("PARTIAL" if mapped else "BLOCKED")
        ),
        "requires_parameter_source_or_estimation_plan": (
            "PASS"
            if all_exact and all_mapped_have_plan
            else ("PARTIAL" if all_mapped_have_plan else "BLOCKED")
        ),
        "requires_identifiability_assessment": (
            "PASS"
            if (
                all_exact
                and validated_reference_behavioural_mechanisms > 0
                and mapped
                and all(item["classification"] == "ACTIVATED" for item in mapped)
            )
            else "BLOCKED"
        ),
        "requires_endogenous_exogenous_classification": (
            "PASS" if not unresolved else "BLOCKED"
        ),
        "requires_polarity_and_loop_path": "PASS" if closed else "BLOCKED",
        "requires_delay_specification_when_delay_claimed": (
            "PASS" if all_delays_ready else "BLOCKED"
        ),
        "requires_nonlinearity_documentation_when_present": (
            "PARTIAL" if all_exact else "NOT_ASSESSABLE"
        ),
        "requires_extreme_condition_test": (
            "PARTIAL" if any_robust else "BLOCKED"
        ),
        "requires_sensitivity_plan": (
            "PARTIAL" if any_robust else "BLOCKED"
        ),
        "requires_validation_gate": (
            "PASS"
            if all_exact and validated_reference_behavioural_mechanisms > 0
            else "BLOCKED"
        ),
        "requires_reference_mode_link": (
            "PASS"
            if len(exact_reference_nodes) == len(nodes)
            else ("PARTIAL" if exact_reference_nodes else "BLOCKED")
        ),
        "requires_accounting_conservation_preservation": (
            "PASS"
            if accounting_hard_constraint and full_accounting_ready and all_exact
            else ("PARTIAL" if accounting_hard_constraint else "BLOCKED")
        ),
    }


def audit_feedback_activation_matrix(
    matrix: dict[str, object],
    gate: dict[str, object],
    feedback: dict[str, object],
    link_registry: dict[str, object],
    boundary: dict[str, object],
    delay: dict[str, object],
    mechanisms: dict[str, object],
    units: dict[str, object],
    robustness: dict[str, object],
    disposition: dict[str, object],
    accounting: dict[str, object],
    model: dict[str, object],
) -> list[str]:
    errors: list[str] = []

    activation_gate = gate["feedback_activation_gate"]
    required_criteria = {
        key
        for key, value in activation_gate.items()
        if key.startswith("requires_") and value is True
    }
    matrix_order = list(matrix.get("criteria_order", []))
    if set(matrix_order) != required_criteria:
        errors.append(
            "criteria-order coverage mismatch; "
            f"missing={sorted(required_criteria - set(matrix_order))}, "
            f"extra={sorted(set(matrix_order) - required_criteria)}"
        )
    if len(matrix_order) != len(set(matrix_order)):
        errors.append("criteria_order contains duplicates")
    if activation_gate.get("all_must_pass") is not True:
        errors.append("canonical activation gate must remain all_must_pass")
    if matrix.get("passing_status") != "PASS":
        errors.append("PASS must remain the only passing matrix status")

    vocabulary = set(matrix.get("status_vocabulary", []))
    if vocabulary != {"PASS", "PARTIAL", "BLOCKED", "NOT_ASSESSABLE"}:
        errors.append("matrix status vocabulary changed unexpectedly")

    loops = {str(item["id"]): item for item in feedback["loops"]}
    link_rows = {
        str(item["loop_id"]): item
        for item in link_registry["loop_activation_readiness"]
    }
    boundary_by = {
        str(item["id"]): item for item in boundary["variables"]
    }
    delay_by = {str(item["id"]): item for item in delay["delays"]}
    mechanism_by = {
        str(item["id"]): item for item in mechanisms["mechanisms"]
    }
    unit_implementations = {
        str(item["implementation"]) for item in units["equations"]
    }
    robustness_by_mechanism = {
        str(item["mechanism_id"]): item for item in robustness["forms"]
    }

    rows = matrix.get("feedbacks", [])
    row_ids = [str(item["loop_id"]) for item in rows]
    if len(row_ids) != len(set(row_ids)):
        errors.append("matrix contains duplicate feedback rows")
    if set(row_ids) != set(loops):
        errors.append(
            "feedback coverage mismatch; "
            f"missing={sorted(set(loops) - set(row_ids))}, "
            f"extra={sorted(set(row_ids) - set(loops))}"
        )

    validated = int(
        disposition["validated_reference_behavioural_mechanisms"]
    )
    accounting_hard_constraint = (
        model["dynamic_core"]["accounting_spine_is_hard_constraint"] is True
    )
    full_accounting_ready = (
        accounting["current_expected_state"][
            "canonical_full_2025_stock_flow_benchmark_ready"
        ]
        is True
    )

    for row in rows:
        loop_id = str(row["loop_id"])
        loop = loops.get(loop_id)
        link_row = link_rows.get(loop_id)
        if loop is None or link_row is None:
            continue

        expected = expected_statuses(
            loop,
            link_row=link_row,
            boundary_by=boundary_by,
            delay_by=delay_by,
            mechanism_by=mechanism_by,
            unit_implementations=unit_implementations,
            robustness_by_mechanism=robustness_by_mechanism,
            validated_reference_behavioural_mechanisms=validated,
            accounting_hard_constraint=accounting_hard_constraint,
            full_accounting_ready=full_accounting_ready,
        )
        criteria = row.get("criteria", {})
        if set(criteria) != required_criteria:
            errors.append(
                f"{loop_id}: criterion coverage does not match canonical gate"
            )
            continue

        observed_statuses: dict[str, str] = {}
        for criterion_id in matrix_order:
            item = criteria[criterion_id]
            status = str(item.get("status", ""))
            observed_statuses[criterion_id] = status
            if status not in vocabulary:
                errors.append(
                    f"{loop_id}:{criterion_id}: unsupported status {status!r}"
                )
            if not str(item.get("reason", "")).strip():
                errors.append(
                    f"{loop_id}:{criterion_id}: missing substantive reason"
                )
            evidence = item.get("evidence", [])
            if not isinstance(evidence, list) or not evidence:
                errors.append(
                    f"{loop_id}:{criterion_id}: missing evidence pointers"
                )

        if observed_statuses != expected:
            mismatches = {
                key: {
                    "expected": expected[key],
                    "observed": observed_statuses.get(key),
                }
                for key in expected
                if observed_statuses.get(key) != expected[key]
            }
            errors.append(
                f"{loop_id}: criterion statuses are stale: {mismatches}"
            )

        pass_count = sum(value == "PASS" for value in expected.values())
        partial_count = sum(value == "PARTIAL" for value in expected.values())
        blocked_count = sum(value == "BLOCKED" for value in expected.values())
        not_assessable_count = sum(
            value == "NOT_ASSESSABLE" for value in expected.values()
        )
        expected_counts = {
            "passed_criteria_count": pass_count,
            "partial_criteria_count": partial_count,
            "blocked_criteria_count": blocked_count,
            "not_assessable_criteria_count": not_assessable_count,
        }
        for key, value in expected_counts.items():
            if row.get(key) != value:
                errors.append(
                    f"{loop_id}: {key} is stale; expected {value}, "
                    f"observed {row.get(key)!r}"
                )

        all_pass = all(status == "PASS" for status in expected.values())
        if row.get("all_requirements_pass") is not all_pass:
            errors.append(f"{loop_id}: all_requirements_pass is stale")
        expected_activation = "READY" if all_pass else "BLOCKED"
        if row.get("activation_status") != expected_activation:
            errors.append(f"{loop_id}: activation_status is stale")
        if row.get("quantitative_activation_authorized") is not False:
            errors.append(
                f"{loop_id}: matrix may not authorize quantitative activation"
            )

    summary = matrix.get("current_summary", {})
    ready_count = sum(
        item.get("all_requirements_pass") is True for item in rows
    )
    if summary.get("registered_feedback_structures") != len(loops):
        errors.append("matrix summary feedback count is stale")
    if summary.get("activation_ready_structures") != ready_count:
        errors.append("matrix summary ready count is stale")
    if summary.get("quantitatively_authorized_structures") != 0:
        errors.append("matrix summary may not authorize structures")
    if ready_count == 0 and summary.get("current_status") != (
        "ALL_FEEDBACK_STRUCTURES_BLOCKED"
    ):
        errors.append("matrix summary must report all structures blocked")
    if summary.get("behavioural_closure_active") is not False:
        errors.append("matrix summary must preserve inactive behavioural closure")

    return errors


def main() -> None:
    matrix = load("model/dynamics/feedback_activation_criteria_matrix.json")
    gate = load("model/dynamics/system_dynamics_conformity_gate.json")
    feedback = load("model/dynamics/feedback_registry.json")
    link_registry = load("model/dynamics/feedback_link_readiness_registry.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    delay = load("model/dynamics/delay_evidence_registry.json")
    mechanisms = load("model/empirical_dynamics/mechanism_registry.json")
    units = load("model/empirical_dynamics/behavioural_unit_contract.json")
    robustness = load(
        "model/empirical_dynamics/behavioural_robustness_contract.json"
    )
    disposition = load(
        "model/calibration_validation/validation_recovery_disposition.json"
    )
    accounting = load("model/accounting/accounting_readiness_gate.json")
    model = load("model/registries/model_contract.json")

    errors = audit_feedback_activation_matrix(
        matrix,
        gate,
        feedback,
        link_registry,
        boundary,
        delay,
        mechanisms,
        units,
        robustness,
        disposition,
        accounting,
        model,
    )
    if errors:
        raise RuntimeError(
            "Feedback activation criteria audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "feedback_structures": len(matrix["feedbacks"]),
                "criteria_per_structure": len(matrix["criteria_order"]),
                "activation_ready_structures": matrix["current_summary"][
                    "activation_ready_structures"
                ],
                "current_status": matrix["current_summary"]["current_status"],
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
