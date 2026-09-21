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
CONTRACT_PATH = "model/dynamics/numerical_integration_contract.json"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def simulate_constant_rate_partition(*, opening: float, transaction_rate: float,
                                     revaluation_rate: float, other_change_rate: float,
                                     horizon_years: float, dt_years: float) -> float:
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

def audit_numerical_integration(contract: dict, core: dict, delays: dict,
                                model: dict, feedback_readiness: dict) -> list[str]:
    e: list[str] = []

    if contract["baseline_method"] != "explicit_euler":
        e.append("baseline method changed")
    if abs(contract["default_dt_years"] - DEFAULT_DT_YEARS) > 1e-15:
        e.append("contract default dt disagrees with executable default")
    if abs(core["time"]["default_dt_years"] - DEFAULT_DT_YEARS) > 1e-15:
        e.append("core default dt disagrees with executable default")
    if core["integration"]["baseline_method"] != "explicit_euler":
        e.append("core integration method changed")
    if core["integration"]["integration_error_test_required"] is not True:
        e.append("core must require integration error testing")

    rate = contract["structural_primitives"]["constant_rate_financial_stock"]
    rc = rate["reference_case"]
    observed = [
        simulate_constant_rate_partition(
            opening=rc["opening"],
            transaction_rate=rc["transaction_rate_per_year"],
            revaluation_rate=rc["revaluation_rate_per_year"],
            other_change_rate=rc["other_change_rate_per_year"],
            horizon_years=rc["horizon_years"],
            dt_years=dt,
        )
        for dt in rate["tested_dt_years"]
    ]
    if any(abs(x - rc["expected_closing"]) > 1e-10 for x in observed):
        e.append(f"constant-rate partition invariance failed: {observed}")
    if rate["status"] != "PASS_STRUCTURAL_PRIMITIVE":
        e.append("constant-rate primitive status changed")

    d = contract["structural_primitives"]["first_order_delay"]
    ref = d["reference_case"]
    calc = [
        simulate_first_order_delay_euler(
            initial=ref["initial"],
            input_value=ref["input_value"],
            tau_years=ref["tau_years"],
            horizon_years=ref["horizon_years"],
            dt_years=dt,
        )
        for dt in ref["tested_dt_years"]
    ]
    for i, (actual, expected) in enumerate(zip(calc, ref["expected_euler_results"])):
        if abs(actual - expected) > 1e-14:
            e.append(f"delay reference result {i} changed")
    exact = 1.0 - math.exp(-1.0)
    if abs(ref["analytic_solution_at_horizon"] - exact) > 1e-15:
        e.append("analytic delay reference changed")
    errs = [abs(x - exact) for x in calc]
    for i, (actual, expected) in enumerate(zip(errs, ref["expected_absolute_errors"])):
        if abs(actual - expected) > 1e-14:
            e.append(f"delay reference error {i} changed")
    if not all(b < a for a, b in zip(errs, errs[1:])):
        e.append("Euler delay does not converge under dt halving")
    if ref["status"] != "PASS_REFERENCE_CONVERGENCE":
        e.append("delay convergence status changed")

    rule = d["explicit_euler_time_step_rule"]
    if rule["max_dt_fraction_of_tau"] != "strictly_less_than_1_over_3":
        e.append("dt/tau adequacy rule changed")
    if rule["rule_type"] != "CONSERVATIVE_SYSTEM_DYNAMICS_ADEQUACY_RULE_NOT_STABILITY_LIMIT":
        e.append("one-third rule semantics changed")
    if abs(MAX_EULER_DELAY_DT_FRACTION - 1.0 / 3.0) > 1e-15:
        e.append("executable Euler delay fraction changed")
    if first_order_delay_timestep_is_adequate(DEFAULT_DT_YEARS, 0.75):
        e.append("strict tau=0.75 boundary must fail")
    if not first_order_delay_timestep_is_adequate(DEFAULT_DT_YEARS, 0.750001):
        e.append("tau strictly above 0.75 should pass")
    if rule["implied_tau_requirement_at_default_dt"] != "tau_years > 0.75":
        e.append("default-dt tau implication changed")

    ds = delays["current_summary"]
    cp = d["current_parameterization"]
    for key in ("registered_delay_candidates", "scalar_tau_identified_and_validated",
                "scalar_tau_activation_ready"):
        if cp[key] != ds[key]:
            e.append(f"delay summary mismatch: {key}")
    if cp["active_delay_count"] != ds["active_delay_candidates"]:
        e.append("active delay count mismatch")
    if cp["active_delay_count"] != 0:
        e.append("current gate assumes no active delay")

    fr = feedback_readiness["current_summary"]
    ib = contract["integrated_validation_boundary"]
    if fr["exact_integrated_link_forms_ready"] != ib["exact_integrated_feedback_link_forms_ready"]:
        e.append("integrated exact-link readiness mismatch")
    active_structures = sum(
        x.get("quantitatively_active") is True
        for x in load("model/dynamics/feedback_registry.json")["loops"]
    )
    if active_structures != ib["active_quantitative_feedback_structures"]:
        e.append("active feedback-structure count mismatch")

    for key, value in contract["hard_rules"].items():
        if value is not True:
            e.append(f"hard rule disabled: {key}")
    summary = contract["current_summary"]
    if summary["integrated_model_numerical_robustness"] != "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE":
        e.append("integrated numerical robustness improperly promoted")
    if summary["behavioural_closure_active"] is not False:
        e.append("numerical gate may not activate behavioural closure")
    if summary["model_activation_authorized"] is not False:
        e.append("numerical gate may not authorize model activation")
    if summary["public_version_change_authorized"] is not False:
        e.append("numerical gate may not authorize version change")
    if model["dynamic_core"]["behavioural_closure_active"] is not False:
        e.append("model contract behavioural closure changed")

    required = set(core["required_tests"])
    for test_id in ("integration_error_convergence", "delay_time_step_ratio_gate",
                    "coarse_euler_delay_step_rejected", "delay_invalid_tau_rejected"):
        if test_id not in required:
            e.append(f"core required test missing: {test_id}")
    return e

def main() -> None:
    errors = audit_numerical_integration(
        load(CONTRACT_PATH),
        load("model/dynamics/core_contract.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/registries/model_contract.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
    )
    if errors:
        raise RuntimeError("Numerical integration audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "default_dt_years":DEFAULT_DT_YEARS,
        "default_dt_delay_tau_requirement":"tau_years > 0.75",
        "first_order_delay_reference_convergence":"PASS",
        "active_delay_count":0,
        "integrated_model_numerical_robustness":"NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE",
        "activation_authorized":False,
    }, indent=2))

if __name__ == "__main__":
    main()
