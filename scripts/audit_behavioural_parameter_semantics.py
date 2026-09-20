from __future__ import annotations

import inspect
import json
from pathlib import Path

import romania_macro_financial_dynamics.behavioural as behavioural

ROOT = Path(__file__).resolve().parents[1]
MECHANISM_PATH = ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
PARAMETER_PATH = ROOT / "model" / "empirical_dynamics" / "behavioural_parameter_contract.json"


def parameter_ids(mechanism: dict[str, object]) -> set[str]:
    result: set[str] = set()
    for parameter in mechanism.get("parameters", []):
        if isinstance(parameter, str):
            result.add(parameter)
        else:
            result.add(str(parameter["id"]))
    return result


def audit_behavioural_parameter_semantics(
    mechanisms: dict[str, object],
    contract: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    current = {
        str(item["implementation"]): item
        for item in mechanisms["mechanisms"]
        if item.get("implementation") is not None
    }
    equations = {
        str(item["implementation"]): item
        for item in contract.get("equations", [])
    }

    if set(current) != set(equations):
        errors.append(
            "parameter-contract implementation coverage mismatch; "
            f"missing={sorted(set(current)-set(equations))}, "
            f"extra={sorted(set(equations)-set(current))}"
        )

    vocab = set(contract["semantics_vocabulary"])
    for implementation, equation in equations.items():
        mechanism = current.get(implementation)
        if mechanism is None:
            continue
        if equation["mechanism_id"] != mechanism["id"]:
            errors.append(f"{implementation}: mechanism ID mismatch")

        function = getattr(behavioural, implementation, None)
        if function is None or not inspect.isfunction(function):
            errors.append(f"{implementation}: implementation not found in behavioural module")
            continue
        signature = inspect.signature(function)
        runtime_names = set(signature.parameters)

        rows = equation.get("parameters", [])
        registry_ids = [str(row["registry_id"]) for row in rows]
        if len(registry_ids) != len(set(registry_ids)):
            errors.append(f"{implementation}: duplicate registry parameter IDs")
        expected_ids = parameter_ids(mechanism)
        if set(registry_ids) != expected_ids:
            errors.append(
                f"{implementation}: registry parameter coverage mismatch; "
                f"expected={sorted(expected_ids)}, observed={sorted(registry_ids)}"
            )

        runtime_parameter_names = [str(row["runtime_name"]) for row in rows]
        if len(runtime_parameter_names) != len(set(runtime_parameter_names)):
            errors.append(f"{implementation}: duplicate runtime parameter names")

        for row in rows:
            runtime_name = str(row["runtime_name"])
            semantic = str(row["semantic"])
            if runtime_name not in runtime_names:
                errors.append(
                    f"{implementation}: runtime parameter {runtime_name} not in function signature"
                )
            if semantic not in vocab:
                errors.append(
                    f"{implementation}: unsupported parameter semantic {semantic!r}"
                )
                continue

            if semantic == "NONNEGATIVE_MAGNITUDE":
                if row.get("lower_bound") != 0:
                    errors.append(
                        f"{implementation}:{runtime_name}: nonnegative magnitude requires lower_bound=0"
                    )
                if row.get("equation_operator") not in {"+", "-"}:
                    errors.append(
                        f"{implementation}:{runtime_name}: magnitude requires explicit +/- equation operator"
                    )
                if "upper_bound" in row:
                    upper_bound = row["upper_bound"]
                    if not isinstance(upper_bound, (int, float)) or upper_bound <= 0:
                        errors.append(
                            f"{implementation}:{runtime_name}: upper_bound must be positive"
                        )
                    frozen_domain = row.get("frozen_validation_domain")
                    if frozen_domain != [0, upper_bound]:
                        errors.append(
                            f"{implementation}:{runtime_name}: frozen validation domain must match [0, upper_bound]"
                        )
            elif semantic in {"UNIT_INTERVAL_SHARE", "UNIT_INTERVAL_PERSISTENCE"}:
                if row.get("bounds") != [0, 1]:
                    errors.append(
                        f"{implementation}:{runtime_name}: unit-interval semantic requires bounds [0, 1]"
                    )
            elif semantic == "UNRESTRICTED_SIGNED_INTERCEPT":
                if row.get("runtime_name") != "intercept":
                    errors.append(
                        f"{implementation}:{runtime_name}: unrestricted signed semantic reserved for intercept"
                    )

    rules = contract["hard_rules"]
    for key in (
        "equation_operator_owns_causal_sign_when_parameter_is_nonnegative_magnitude",
        "negative_magnitude_parameter_is_invalid_input",
        "negative_estimate_for_magnitude_parameter_requires_candidate_failure_or_new_preregistered_form",
        "no_absolute_value_repair_of_negative_estimates",
        "no_post_fit_sign_flip",
        "frozen_parameter_domain_must_be_enforced_when_present",
        "parameter_semantics_do_not_authorize_estimation_or_activation",
    ):
        if rules.get(key) is not True:
            errors.append(f"hard rule {key} must remain true")

    summary = contract["current_summary"]
    if summary["current_implementations_covered"] != len(current):
        errors.append("parameter-contract summary implementation count is stale")
    if summary["parameter_semantics_frozen"] is not True:
        errors.append("parameter semantics must remain frozen")
    if summary["runtime_negative_magnitude_rejection_required"] is not True:
        errors.append("runtime negative-magnitude rejection must remain required")
    if summary["estimation_authorized"] is not False:
        errors.append("parameter contract may not authorize estimation")
    if summary["model_activation_authorized"] is not False:
        errors.append("parameter contract may not authorize model activation")

    return errors


def main() -> None:
    mechanisms = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    contract = json.loads(PARAMETER_PATH.read_text(encoding="utf-8"))
    errors = audit_behavioural_parameter_semantics(mechanisms, contract)
    if errors:
        raise RuntimeError(
            "Behavioural parameter semantics audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(json.dumps({
        "status": "PASS",
        "current_implementations_covered": contract["current_summary"][
            "current_implementations_covered"
        ],
        "parameter_semantics_frozen": True,
        "negative_magnitude_rejection_required": True,
        "estimation_authorized": False,
        "activation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
