from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
CONTRACT_PATH = ROOT / "model" / "empirical_dynamics" / "behavioural_unit_contract.json"


def parameter_ids(mechanism: dict[str, object]) -> set[str]:
    result: set[str] = set()
    for parameter in mechanism.get("parameters", []):
        if isinstance(parameter, str):
            result.add(parameter)
        else:
            result.add(parameter["id"])
    return result


def audit_behavioural_units(
    registry: dict[str, object],
    contract: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    mechanisms = {
        item["id"]: item
        for item in registry["mechanisms"]
    }
    implementations = {
        item["implementation"]: item
        for item in registry["mechanisms"]
        if item.get("implementation") is not None
    }
    equations = {
        item["implementation"]: item
        for item in contract["equations"]
    }
    unit_classes = set(contract["unit_classes"])

    if set(implementations) != set(equations):
        missing = sorted(set(implementations) - set(equations))
        extra = sorted(set(equations) - set(implementations))
        errors.append(
            f"implementation coverage mismatch; missing={missing}, extra={extra}"
        )

    for implementation, equation in equations.items():
        mechanism_id = equation["mechanism_id"]
        mechanism = mechanisms.get(mechanism_id)
        if mechanism is None:
            errors.append(f"{implementation}: unknown mechanism {mechanism_id}")
            continue
        if mechanism.get("implementation") != implementation:
            errors.append(
                f"{implementation}: mechanism implementation pointer does not match"
            )

        output_unit = equation.get("output_unit_class")
        if output_unit not in unit_classes:
            errors.append(f"{implementation}: unknown output unit class {output_unit!r}")

        for input_name, unit_class in equation.get("input_unit_classes", {}).items():
            if unit_class not in unit_classes:
                errors.append(
                    f"{implementation}: input {input_name} has unknown unit class {unit_class!r}"
                )

        declared_parameter_units = equation.get("parameter_unit_classes", {})
        expected_parameters = parameter_ids(mechanism)
        if set(declared_parameter_units) != expected_parameters:
            errors.append(
                f"{implementation}: parameter unit coverage mismatch; "
                f"expected={sorted(expected_parameters)}, "
                f"observed={sorted(declared_parameter_units)}"
            )
        for parameter_name, unit_class in declared_parameter_units.items():
            if unit_class not in unit_classes:
                errors.append(
                    f"{implementation}: parameter {parameter_name} has unknown unit class {unit_class!r}"
                )

        for term in equation.get("additive_terms", []):
            if term.get("unit_class") != output_unit:
                errors.append(
                    f"{implementation}: additive term {term.get('id')} unit "
                    f"{term.get('unit_class')!r} does not match output {output_unit!r}"
                )

        scale_status = equation.get("measurement_scale_status")
        unit_gate = equation.get("unit_activation_readiness")
        if scale_status == "NOT_FROZEN" and unit_gate != "BLOCKED_MEASUREMENT_SCALE":
            errors.append(
                f"{implementation}: unfrozen measurement scale must block unit activation readiness"
            )
        if scale_status == "NOT_FROZEN" and not equation.get("measurement_scale_blockers"):
            errors.append(
                f"{implementation}: unfrozen measurement scale lacks explicit blockers"
            )
        if equation.get("model_activation_authorized") is not False:
            errors.append(
                f"{implementation}: unit contract must not authorize model activation"
            )

    government = mechanisms.get("government_refinancing_effective_rate")
    if government is not None:
        m_params = {
            p["id"]: p
            for p in government.get("parameters", [])
            if isinstance(p, dict)
        }
        m = m_params.get("m[t]")
        if m is None:
            errors.append("government_refinancing_effective_rate: missing m[t]")
        elif m.get("unit") != "dimensionless_period_share":
            errors.append(
                "government_refinancing_effective_rate: m[t] must be a "
                "dimensionless period share when used as a convex weight"
            )

    return errors


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    errors = audit_behavioural_units(registry, contract)
    if errors:
        raise RuntimeError(
            "Behavioural dimensional consistency audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "contract": str(CONTRACT_PATH.relative_to(ROOT)),
                "implementations_checked": [
                    item["implementation"] for item in contract["equations"]
                ],
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
