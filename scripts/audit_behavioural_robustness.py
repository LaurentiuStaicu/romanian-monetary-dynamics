from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MECHANISM_PATH = ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
ROBUSTNESS_PATH = ROOT / "model" / "empirical_dynamics" / "behavioural_robustness_contract.json"
MODEL_PATH = ROOT / "model" / "registries" / "model_contract.json"


def audit_behavioural_robustness(
    mechanisms: dict[str, object],
    robustness: dict[str, object],
    model: dict[str, object],
) -> list[str]:
    errors: list[str] = []

    current = {
        str(item["implementation"]): item
        for item in mechanisms["mechanisms"]
        if item.get("implementation") is not None
    }
    forms = robustness.get("forms", [])
    by_impl = {str(item["implementation"]): item for item in forms}

    if len(forms) != len(by_impl):
        errors.append("robustness contract contains duplicate implementations")

    if set(current) != set(by_impl):
        errors.append(
            "current implementation coverage mismatch; "
            f"missing={sorted(set(current) - set(by_impl))}, "
            f"extra={sorted(set(by_impl) - set(current))}"
        )

    allowed_form = set(robustness["allowed_form_level_statuses"])
    allowed_integrated = set(robustness["allowed_integrated_statuses"])

    closure_active = bool(model["dynamic_core"]["behavioural_closure_active"])
    if closure_active:
        errors.append(
            "robustness contract is frozen for inactive behavioural closure"
        )

    for implementation, item in by_impl.items():
        mechanism = current.get(implementation)
        if mechanism is None:
            continue

        if item.get("mechanism_id") != mechanism["id"]:
            errors.append(
                f"{implementation}: mechanism ID does not match registry"
            )
        if item.get("classification") != mechanism["classification"]:
            errors.append(
                f"{implementation}: classification is stale relative to registry"
            )

        form_status = item.get("form_level_extreme_condition_test_status")
        if form_status not in allowed_form:
            errors.append(
                f"{implementation}: unsupported form-level status {form_status!r}"
            )
        if form_status == "EXECUTABLE_FORM_STRESS_TESTED":
            if not item.get("structural_extreme_conditions"):
                errors.append(
                    f"{implementation}: stress-tested form lacks declared extreme conditions"
                )
            if not item.get("structural_sensitivity_checks"):
                errors.append(
                    f"{implementation}: stress-tested form lacks structural sensitivity checks"
                )

        plan = item.get("sensitivity_plan")
        if not isinstance(plan, dict):
            errors.append(f"{implementation}: missing sensitivity plan")
        else:
            if plan.get("status") != "PLAN_DEFINED_EMPIRICAL_EXECUTION_BLOCKED":
                errors.append(
                    f"{implementation}: empirical sensitivity must remain blocked"
                )
            if plan.get("empirical_parameter_ranges_frozen") is not False:
                errors.append(
                    f"{implementation}: no empirical parameter ranges may be "
                    "claimed frozen in the current closed cycle"
                )
            if not plan.get("structurally_admissible_axes"):
                errors.append(
                    f"{implementation}: sensitivity plan lacks declared axes"
                )
            if not str(plan.get("blocker", "")).strip():
                errors.append(
                    f"{implementation}: sensitivity plan lacks a blocker"
                )

        integrated = item.get("integrated_extreme_condition_status")
        if integrated not in allowed_integrated:
            errors.append(
                f"{implementation}: unsupported integrated extreme-condition "
                f"status {integrated!r}"
            )
        if integrated != "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE":
            errors.append(
                f"{implementation}: integrated extreme-condition testing must "
                "remain unclaimed while closure is inactive"
            )
        if item.get("model_activation_authorized") is not False:
            errors.append(
                f"{implementation}: robustness contract may not authorize activation"
            )

    summary = robustness.get("current_summary", {})
    if summary.get("current_implementations_covered") != len(current):
        errors.append("robustness summary implementation count is stale")
    if summary.get("form_level_structural_stress_status") != (
        "PASS_CURRENT_IMPLEMENTATIONS"
    ):
        errors.append("robustness summary form-level status is stale")
    if summary.get("empirical_sensitivity_execution_status") != "BLOCKED":
        errors.append("empirical sensitivity execution must remain BLOCKED")
    if summary.get("integrated_extreme_condition_status") != (
        "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE"
    ):
        errors.append("integrated extreme-condition status must remain NOT_RUN")
    if summary.get("activation_authorized") is not False:
        errors.append("robustness summary may not authorize activation")

    return errors


def main() -> None:
    mechanisms = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    robustness = json.loads(ROBUSTNESS_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    errors = audit_behavioural_robustness(mechanisms, robustness, model)
    if errors:
        raise RuntimeError(
            "Behavioural robustness audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "contract": str(ROBUSTNESS_PATH.relative_to(ROOT)),
                "implementations_checked": len(robustness["forms"]),
                "form_level_structural_stress_status": "PASS_CURRENT_IMPLEMENTATIONS",
                "empirical_sensitivity_execution_status": "BLOCKED",
                "integrated_extreme_condition_status": (
                    "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE"
                ),
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
