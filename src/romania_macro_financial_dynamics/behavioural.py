"""Behavioural research forms for the scientific core.

This module contains executable equations used by current candidate/deferred
mechanisms and a small number of explicitly retained noncanonical research
forms. Code availability is never evidence of scientific admission. The
canonical mapping from mechanism to executable implementation is governed by
model/empirical_dynamics/mechanism_registry.json; functions listed there as
retained noncanonical forms may not enter the reference model, calibration,
System Dynamics feedback activation or behavioural closure merely because they
remain executable.

No coefficient has a convenience default: every numerical parameter must be
supplied explicitly by an authorized calibration/validation or source contract.
Accounting Spine and Dynamic Core identities remain hard constraints.
"""

from __future__ import annotations

from math import isfinite


class InvalidBehaviouralInput(ValueError):
    """Raised when a behavioural equation receives an invalid input/parameter."""


def _finite(*values: float) -> None:
    if not all(isfinite(value) for value in values):
        raise InvalidBehaviouralInput("Behavioural inputs and parameters must be finite")


def _unit_interval(value: float, name: str) -> None:
    _finite(value)
    if not 0.0 <= value <= 1.0:
        raise InvalidBehaviouralInput(f"{name} must lie in [0, 1]")


def _nonnegative(value: float, name: str) -> None:
    _finite(value)
    if value < 0.0:
        raise InvalidBehaviouralInput(f"{name} must be non-negative")


def partial_adjustment_rate(
    previous_rate: float,
    policy_rate: float,
    *,
    intercept: float,
    long_run_pass_through: float,
    adjustment_speed: float,
) -> float:
    """Retained noncanonical generic partial-adjustment pass-through form.

    r_t = r_(t-1) + lambda * (alpha + beta * policy_t - r_(t-1))

    This historical research form is not the current RMD monetary-pass-through
    implementation. The canonical candidate is the frozen household-housing
    delta-policy equation recorded in the mechanism registry.

    Rates are percentage points per annum. ``adjustment_speed`` is a fraction of
    the remaining gap closed per observation period.
    """

    _finite(previous_rate, policy_rate, intercept, long_run_pass_through)
    _unit_interval(adjustment_speed, "adjustment_speed")
    target = intercept + long_run_pass_through * policy_rate
    return previous_rate + adjustment_speed * (target - previous_rate)



def household_housing_delta_policy_rate(
    previous_lending_rate: float,
    current_policy_rate: float,
    previous_policy_rate: float,
    *,
    beta: float,
) -> float:
    """Frozen household-housing delta-policy candidate from validation recovery.

    lend[t] = lend[t-1] + beta * (policy[t] - policy[t-1])

    This is the exact target-specific candidate selected for household housing
    new-business lending rates. It is not a generic market/lending-rate equation,
    is not validated, and does not activate the monetary-credit feedback loop.
    The preregistered validation domain for beta is [0, 2].
    """

    _finite(
        previous_lending_rate,
        current_policy_rate,
        previous_policy_rate,
        beta,
    )
    if not 0.0 <= beta <= 2.0:
        raise InvalidBehaviouralInput(
            "beta must lie in the frozen household-housing validation domain [0, 2]"
        )
    return previous_lending_rate + beta * (
        current_policy_rate - previous_policy_rate
    )

def refinancing_effective_rate(
    previous_effective_rate: float,
    marginal_market_yield: float,
    *,
    refinancing_share: float,
) -> float:
    """Weighted repricing of the effective debt rate as debt is refinanced.

    This is a stock-composition mechanism, not a fiscal reaction function.
    ``refinancing_share`` is a dimensionless fraction of the opening debt stock
    repriced/refinanced during the declared observation period. It is used as a
    convex weight, not as a continuous-time rate, and must be supported by
    matched maturity/refinancing evidence.
    """

    _finite(previous_effective_rate, marginal_market_yield)
    _unit_interval(refinancing_share, "refinancing_share")
    return (1.0 - refinancing_share) * previous_effective_rate + refinancing_share * marginal_market_yield


def household_consumption_growth(
    *,
    disposable_income_growth: float,
    real_borrowing_rate: float,
    debt_service_ratio: float,
    intercept: float,
    income_sensitivity: float,
    rate_sensitivity: float,
    debt_service_sensitivity: float,
) -> float:
    """Candidate reduced-form household consumption-growth equation.\n\n    Sensitivity parameters are non-negative magnitudes; the equation operators\n    own the causal signs. A negative magnitude is invalid for this frozen form.\n    """

    _finite(
        disposable_income_growth,
        real_borrowing_rate,
        debt_service_ratio,
        intercept,
        income_sensitivity,
        rate_sensitivity,
        debt_service_sensitivity,
    )
    _nonnegative(income_sensitivity, "income_sensitivity")
    _nonnegative(rate_sensitivity, "rate_sensitivity")
    _nonnegative(debt_service_sensitivity, "debt_service_sensitivity")
    return (
        intercept
        + income_sensitivity * disposable_income_growth
        - rate_sensitivity * real_borrowing_rate
        - debt_service_sensitivity * debt_service_ratio
    )


def corporate_investment_growth(
    *,
    demand_growth: float,
    real_corporate_lending_rate: float,
    eu_fund_impulse: float,
    intercept: float,
    demand_sensitivity: float,
    rate_sensitivity: float,
    eu_fund_sensitivity: float,
) -> float:
    """Retained noncanonical exploratory corporate-investment equation.

    No corporate-investment behavioural form is currently admitted after the
    preregistered structural-selection cycle failed before holdout.
    """

    _finite(
        demand_growth,
        real_corporate_lending_rate,
        eu_fund_impulse,
        intercept,
        demand_sensitivity,
        rate_sensitivity,
        eu_fund_sensitivity,
    )
    return (
        intercept
        + demand_sensitivity * demand_growth
        - rate_sensitivity * real_corporate_lending_rate
        + eu_fund_sensitivity * eu_fund_impulse
    )


def aggregate_credit_growth(
    *,
    activity_growth: float,
    real_lending_rate: float,
    npl_ratio: float,
    capital_buffer: float,
    intercept: float,
    activity_sensitivity: float,
    rate_sensitivity: float,
    npl_sensitivity: float,
    capital_sensitivity: float,
) -> float:
    """Candidate aggregate bank-credit growth equation.

    Sensitivity parameters are non-negative magnitudes; the equation operators
    own the causal signs. Bank-level evidence does not by itself identify this
    aggregate relation; it remains a candidate until the declared data and
    identifiability gates pass.
    """

    _finite(
        activity_growth,
        real_lending_rate,
        npl_ratio,
        capital_buffer,
        intercept,
        activity_sensitivity,
        rate_sensitivity,
        npl_sensitivity,
        capital_sensitivity,
    )
    _nonnegative(activity_sensitivity, "activity_sensitivity")
    _nonnegative(rate_sensitivity, "rate_sensitivity")
    _nonnegative(npl_sensitivity, "npl_sensitivity")
    _nonnegative(capital_sensitivity, "capital_sensitivity")
    return (
        intercept
        + activity_sensitivity * activity_growth
        - rate_sensitivity * real_lending_rate
        - npl_sensitivity * npl_ratio
        + capital_sensitivity * capital_buffer
    )


def sovereign_spread(
    *,
    debt_to_gdp: float,
    deficit_to_gdp: float,
    external_risk_proxy: float,
    intercept: float,
    debt_sensitivity: float,
    deficit_sensitivity: float,
    external_risk_sensitivity: float,
) -> float:
    """Retained noncanonical exploratory sovereign-spread equation.

    No sovereign-yield behavioural form is currently admitted after the
    preregistered structural-selection cycle failed before holdout.
    """

    _finite(
        debt_to_gdp,
        deficit_to_gdp,
        external_risk_proxy,
        intercept,
        debt_sensitivity,
        deficit_sensitivity,
        external_risk_sensitivity,
    )
    return (
        intercept
        + debt_sensitivity * debt_to_gdp
        + deficit_sensitivity * deficit_to_gdp
        + external_risk_sensitivity * external_risk_proxy
    )


def fx_pass_through_inflation(
    *,
    baseline_inflation: float,
    depreciation_lags: tuple[float, ...],
    lag_weights: tuple[float, ...],
) -> float:
    """Retained noncanonical exploratory distributed-lag FX pass-through form.

    No FX-inflation behavioural form is currently admitted after the
    preregistered structural-selection cycle failed before holdout. No
    historical pass-through coefficient is hard-coded because published
    Romanian evidence indicates regime dependence over time.
    """

    _finite(baseline_inflation, *depreciation_lags, *lag_weights)
    if len(depreciation_lags) != len(lag_weights) or not lag_weights:
        raise InvalidBehaviouralInput("depreciation_lags and lag_weights must be non-empty and equal length")
    return baseline_inflation + sum(change * weight for change, weight in zip(depreciation_lags, lag_weights))


def npl_ratio_change(
    *,
    output_growth: float,
    debt_service_burden: float,
    previous_npl_ratio: float,
    intercept: float,
    output_sensitivity: float,
    debt_service_sensitivity: float,
    persistence: float,
) -> float:
    """Candidate credit-risk/NPL change equation; not admitted to the core yet.\n\n    Output and debt-service sensitivities are non-negative magnitudes; the\n    equation operators own their causal signs.\n    """

    _finite(
        output_growth,
        debt_service_burden,
        previous_npl_ratio,
        intercept,
        output_sensitivity,
        debt_service_sensitivity,
    )
    _nonnegative(output_sensitivity, "output_sensitivity")
    _nonnegative(debt_service_sensitivity, "debt_service_sensitivity")
    _unit_interval(persistence, "persistence")
    return (
        intercept
        - output_sensitivity * output_growth
        + debt_service_sensitivity * debt_service_burden
        + persistence * previous_npl_ratio
    )
