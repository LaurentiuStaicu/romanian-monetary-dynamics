from __future__ import annotations

import json
import math
from pathlib import Path

from romania_macro_financial_dynamics.dynamics import (
    DEFAULT_DT_YEARS,
    MAX_EULER_DELAY_DT_FRACTION,
    advance_position_rates,
    first_order_delay_timestep_is_adequate,
    simulate_first_order_delay_euler,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "model" / "dynamics" / "numerical_integration_contract.json"
CORE_PATH = ROOT / "model" / "dynamics" / "core_contract.json"
DELAY_PATH = ROOT / "model" / "dynamics" / "delay_evidence_registry.json"
MODEL_PATH = ROOT / "model" / "registries" / "model_contract.json"


def simulate_constant_rate_partition(
    *,
    opening: float,
    transaction_rate: float,
    revaluation_rate: float,
    other_change_rate: float,
    horizon_years: float,
    dt_years: float,
) -> float:
    steps = round(horizon_years / dt_years)
    if steps <= 0 or abs(steps * dt_years - horizon_years) > 1e-12:
        raise ValueError("horizon must be an integer multiple of dt")
    value = opening
    for _ in range(steps):
        value = advance_position_rates(
            value,
            transaction_rate=transaction_rate,
            revaluation_rate=revaluation_rate,
            other_change_rate=other_change_rate,
            dt_years=dt_years,
        )
    return value


def audit_numerical_integration(
    contract: dict[str, object],
    core: dict[str, object],
    delay: dict[str, object],
    model: dict[str, object],
) -> list[str]:
    errors: list[str] = []

    if contract.get("baseline_method") != "explicit_euler":
        errors.append("numerical integration baseline method must remain explicit_euler")
    if abs(float(contract.get("default_dt_years", -1)) - DEFAULT_DT_YEARS) > 1e-15:
        errors.append("contract default dt disagrees with executable DEFAULT_DT_YEARS")
    if abs(float(core["time"]["default_dt_years"]) - DEFAULT_DT_YEARS) > 1e-15:
        errors.append("core contract default dt disagrees with executable default")
    if core["integration"]["baseline_method"] != "explicit_euler":
        errors.append("core contract baseline method changed unexpectedly")
    if core["integration"]["integration_error_test_required"] is not True:
        errors.append("core contract must require integration error testing")

    rate_contract = contract["structural_primitives"]["constant_rate_financial_stock"]
    partitions = [float(value) for value in rate_contract["test_partitions_years"]]
    if not partitions:
        errors.append("constant-rate partition test lacks dt values")
    else:
        expected = 1085.0
        results = [
            simulate_constant_rate_partition(
                opening=1000.0,
                transaction_rate=100.0,
                revaluation_rate=-20.0,
                other_change_rate=5.0,
                horizon_years=1.0,
                dt_years=dt,
            )
            for dt in partitions
        ]
        if any(abs(result - expected) > 1e-10 for result in results):
            errors.append(
                f"constant-rate stock update is not partition invariant: {results}"
            )
        if rate_contract["status"] != "PASS_STRUCTURAL_PRIMITIVE":
            errors.append("constant-rate structural primitive status is stale")

    delay_contract = contract["structural_primitives"]["first_order_delay"]
    reference = delay_contract["reference_case"]
    dts = [float(value) for value in reference["tested_dt_years"]]
    observed = [
        simulate_first_order_delay_euler(
            initial=float(reference["initial"]),
            input_value=float(reference["input_value"]),
            tau_years=float(reference["tau_years"]),
            horizon_years=float(reference["horizon_years"]),
            dt_years=dt,
        )
        for dt in dts
    ]
    expected_results = [float(value) for value in reference["expected_euler_results"]]
    if len(observed) != len(expected_results):
        errors.append("delay reference result length mismatch")
    else:
        for index, (actual, expected) in enumerate(zip(observed, expected_results)):
            if abs(actual - expected) > 1e-14:
                errors.append(
                    f"delay reference result {index} changed: "
                    f"expected={expected}, observed={actual}"
                )

    exact = float(reference["analytic_solution_at_horizon"])
    expected_exact = 1.0 - math.exp(-1.0)
    if abs(exact - expected_exact) > 1e-15:
        errors.append("stored analytic first-order delay solution is stale")
    observed_errors = [abs(value - exact) for value in observed]
    expected_errors = [float(value) for value in reference["expected_absolute_errors"]]
    if len(observed_errors) != len(expected_errors):
        errors.append("delay reference error length mismatch")
    else:
        for index, (actual, expected) in enumerate(
            zip(observed_errors, expected_errors)
        ):
            if abs(actual - expected) > 1e-14:
                errors.append(
                    f"delay reference absolute error {index} changed: "
                    f"expected={expected}, observed={actual}"
                )
    if not all(
        later < earlier
        for earlier, later in zip(observed_errors, observed_errors[1:])
    ):
        errors.append("Euler first-order delay does not converge under dt halving")
    if reference["status"] != "PASS_REFERENCE_CONVERGENCE":
        errors.append("delay reference convergence status is stale")

    time_rule = delay_contract["explicit_euler_time_step_rule"]
    if time_rule["max_dt_fraction_of_tau"] != "strictly_less_than_1_over_3":
        errors.append("delay dt/tau rule changed unexpectedly")
    if abs(MAX_EULER_DELAY_DT_FRACTION - (1.0 / 3.0)) > 1e-15:
        errors.append("executable max Euler delay fraction changed unexpectedly")
    if first_order_delay_timestep_is_adequate(DEFAULT_DT_YEARS, 0.75):
        errors.append("default quarterly dt must reject tau=0.75 years at equality")
    if not first_order_delay_timestep_is_adequate(
        DEFAULT_DT_YEARS, 0.750001
    ):
        errors.append("default quarterly dt should accept tau strictly above 0.75 years")
    if time_rule["implied_tau_requirement_at_default_dt"] != "tau_years > 0.75":
        errors.append("stored default-dt tau implication is stale")

    delay_summary = delay["current_summary"]
    parameterization = delay_contract["current_parameterization"]
    if parameterization["registered_delay_candidates"] != delay_summary[
        "registered_delay_candidates"
    ]:
        errors.append("integration contract registered-delay count is stale")
    if parameterization["validated_scalar_tau_count"] != delay_summary[
        "scalar_tau_identified_and_validated"
    ]:
        errors.append("integration contract validated-tau count is stale")
    if parameterization["active_delay_count"] != delay_summary[
        "active_delay_candidates"
    ]:
        errors.append("integration contract active-delay count is stale")
    if parameterization["active_delay_count"] != 0:
        errors.append("current numerical integration contract assumes no active delay")

    rules = contract["hard_rules"]
    required_true = (
        "integration_error_test_required",
        "default_dt_is_not_universally_valid_for_delays",
        "active_delay_requires_positive_validated_tau",
        "active_delay_requires_dt_over_tau_strictly_below_one_third",
        "active_delay_requires_time_step_halving_test",
        "observation_frequency_must_not_be_used_as_tau",
        "numerical_primitive_pass_does_not_validate_behavioural_closure",
        "integrated_numerical_robustness_must_not_be_claimed_while_closure_inactive",
    )
    for key in required_true:
        if rules.get(key) is not True:
            errors.append(f"hard rule {key} must remain true")

    summary = contract["current_summary"]
    if summary["stock_rate_partition_invariance"] != "PASS":
        errors.append("stock-rate partition invariance summary is stale")
    if summary["first_order_delay_reference_convergence"] != "PASS":
        errors.append("delay convergence summary is stale")
    if summary["default_dt_delay_adequacy"] != (
        "CONDITIONAL_ON_TAU_GREATER_THAN_0_75_YEARS"
    ):
        errors.append("default-dt delay adequacy summary is stale")
    if summary["integrated_model_numerical_robustness"] != (
        "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE"
    ):
        errors.append("integrated numerical robustness must remain NOT_RUN")
    if summary["behavioural_closure_active"] is not False:
        errors.append("numerical integration contract must preserve inactive closure")
    if model["dynamic_core"]["behavioural_closure_active"] is not False:
        errors.append("model contract unexpectedly activates behavioural closure")
    if summary["model_activation_authorized"] is not False:
        errors.append("numerical integration contract may not authorize activation")

    required_tests = set(core["required_tests"])
    for test_id in (
        "integration_error_convergence",
        "delay_time_step_ratio_gate",
        "coarse_euler_delay_step_rejected",
        "delay_invalid_tau_rejected",
    ):
        if test_id not in required_tests:
            errors.append(f"core contract is missing required test {test_id}")

    return errors


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    core = json.loads(CORE_PATH.read_text(encoding="utf-8"))
    delay = json.loads(DELAY_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    errors = audit_numerical_integration(contract, core, delay, model)
    if errors:
        raise RuntimeError(
            "Numerical integration audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "default_dt_years": DEFAULT_DT_YEARS,
                "default_dt_delay_tau_requirement": "tau_years > 0.75",
                "first_order_delay_reference_convergence": "PASS",
                "active_delay_count": 0,
                "integrated_model_numerical_robustness": (
                    "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE"
                ),
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
