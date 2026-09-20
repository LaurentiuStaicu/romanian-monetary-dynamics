from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = "model/dynamics/government_issuance_bnr_primary_market_yield_pilot_2025.json"
EXPECTED_SHA256 = "171569f159b47ceedc9d8ba6d5628a39de49a8fb18d11e13a20ac55edb39c628"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


EXPECTED_RATES = {
    "discount_treasury_certificates_RON": [
        6.91, 6.57, 6.53, 6.53, 8.11, None, 6.85, 6.98, 6.81, 6.72, 6.14, None
    ],
    "treasury_certificates_EUR": [
        None, None, None, None, 3.52, None, None, None, None, None, None, None
    ],
    "interest_bearing_government_bonds_RON": [
        7.56, 7.24, 7.24, 7.25, 7.64, 7.47, 7.28, 7.35, 7.45, 7.22, 6.87, 6.68
    ],
    "inflation_linked_interest_bearing_government_bonds_RON": [
        None, None, None, None, None, None, None, None, None, None, None, None
    ],
    "interest_bearing_government_bonds_EUR": [
        None, None, None, None, 3.82, None, None, 2.95, None, None, None, None
    ],
}

AMOUNT_KEYS = {
    "discount_treasury_certificates_RON": "discount_treasury_certificates_million_RON",
    "treasury_certificates_EUR": "treasury_certificates_million_EUR",
    "interest_bearing_government_bonds_RON": "interest_bearing_government_bonds_million_RON",
    "interest_bearing_government_bonds_EUR": "interest_bearing_government_bonds_million_EUR",
}


def audit_bnr_primary_market_yield_pilot(
    pilot: dict,
    issuance: dict,
    prereg: dict,
    feedback: dict,
) -> list[str]:
    errors: list[str] = []

    if pilot.get("status") != (
        "DESCRIPTIVE_FULL_2025_INSTRUMENT_SPECIFIC_PRIMARY_MARKET_RATES_"
        "NOT_GENERIC_SOVEREIGN_YIELD"
    ):
        errors.append("primary-market yield pilot status changed")

    source = pilot["source"]
    if source["table"] != "12.2 Government securities (new and roll-over issues)":
        errors.append("BNR table boundary changed")
    if source["pdf_page"] != 65:
        errors.append("BNR source page changed")
    if source["statistical_data_available_as_of"] != "2026-02-24":
        errors.append("BNR source vintage changed")

    retained = pilot["retained_source"]
    if retained["raw_sha256"] != EXPECTED_SHA256:
        errors.append("retained BNR raw-source SHA-256 changed")
    if retained["raw_bytes"] != 2305604:
        errors.append("retained BNR raw-source byte size changed")

    extraction = pilot["extraction"]
    for key in (
        "ocr_used",
        "interpolation_performed",
        "imputation_performed",
        "currency_conversion_performed",
        "cross_instrument_rate_aggregation_performed",
    ):
        if extraction[key] is not False:
            errors.append(f"descriptive pilot may not perform {key}")
    for key in (
        "native_currency_and_instrument_columns_preserved",
        "zero_amount_source_symbol_preserved",
        "not_applicable_rate_symbol_preserved",
    ):
        if extraction[key] is not True:
            errors.append(f"descriptive pilot must preserve {key}")

    rows = pilot["monthly_observations"]
    expected_periods = [f"2025-{month:02d}" for month in range(1, 13)]
    periods = [row["period"] for row in rows]
    if periods != expected_periods:
        errors.append(f"yield pilot monthly coverage changed: {periods}")

    issuance_rows = {row["period"]: row for row in issuance["monthly_observations"]}

    for instrument, expected_rates in EXPECTED_RATES.items():
        observed_rates = [row[instrument]["rate_pct_pa"] for row in rows]
        if observed_rates != expected_rates:
            errors.append(f"{instrument}: reviewed source-rate values changed")

    for row in rows:
        period = row["period"]
        issuance_row = issuance_rows[period]
        for instrument, issuance_key in AMOUNT_KEYS.items():
            item = row[instrument]
            if item["amount"] != issuance_row[issuance_key]:
                errors.append(f"{period} {instrument}: amount differs from issuance pilot")
            amount_positive = float(item["amount"]) > 0
            if amount_positive and item["rate_pct_pa"] is None:
                errors.append(f"{period} {instrument}: positive issue amount lacks source rate")
            if not amount_positive and item["rate_pct_pa"] is not None:
                errors.append(f"{period} {instrument}: zero issue amount has a source rate")
            if amount_positive:
                if item["source_amount_symbol"] is not None:
                    errors.append(f"{period} {instrument}: positive amount has source symbol")
                if item["source_rate_symbol"] is not None:
                    errors.append(f"{period} {instrument}: reported rate has source symbol")
            else:
                if item["source_amount_symbol"] != "–":
                    errors.append(f"{period} {instrument}: nil amount symbol not preserved")
                if item["source_rate_symbol"] != "x":
                    errors.append(f"{period} {instrument}: not-applicable rate symbol not preserved")

        inflation = row["inflation_linked_interest_bearing_government_bonds_RON"]
        if inflation["amount"] != 0 or inflation["rate_pct_pa"] is not None:
            errors.append(f"{period}: inflation-linked RON column must remain nil/not-applicable")
        if inflation["source_amount_symbol"] != "–" or inflation["source_rate_symbol"] != "x":
            errors.append(f"{period}: inflation-linked source symbols changed")

    checks = pilot["coverage_checks"]
    expected_counts = {
        "discount_treasury_certificates_RON_rate_observations": 10,
        "treasury_certificates_EUR_rate_observations": 1,
        "interest_bearing_government_bonds_RON_rate_observations": 12,
        "inflation_linked_interest_bearing_government_bonds_RON_rate_observations": 0,
        "interest_bearing_government_bonds_EUR_rate_observations": 2,
        "months_with_any_reported_rate": 12,
    }
    for key, expected in expected_counts.items():
        if checks[key] != expected:
            errors.append(f"{key}: expected {expected}, observed {checks[key]}")

    semantics = pilot["semantics"]
    for key in (
        "generic_sovereign_yield_equivalent",
        "secondary_market_yield_equivalent",
        "debt_stock_effective_interest_rate_equivalent",
        "government_interest_cost_equivalent",
        "securities_supply_pressure_equivalent",
        "causal_issuance_to_yield_effect_identified",
    ):
        if semantics[key] is not False:
            errors.append(f"primary-market yield pilot may not imply {key}")

    structural = pilot["structural_boundary"]
    if structural["preregistration"] != (
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    ):
        errors.append("yield pilot is not bound to structural preregistration")
    if structural["conceptual_loop_status"] != "CLOSED_CANDIDATE_LOOP":
        errors.append("yield pilot changed conceptual loop status")
    if structural["empirical_boundary_status"] != "OPEN_CHAIN_PENDING_EXPLICIT_BRIDGES":
        errors.append("yield pilot changed empirical boundary status")
    if structural["generic_government_debt_issuance_node_resolved"] is not False:
        errors.append("yield pilot may not resolve generic issuance node")
    if structural["generic_sovereign_yield_node_resolved"] is not False:
        errors.append("yield pilot may not resolve generic sovereign-yield node")

    if prereg["next_empirical_task"]["id"] != "bnr_instrument_specific_primary_market_yield_pilot_2025":
        errors.append("structural preregistration no longer authorizes this descriptive task")

    loop = next(item for item in feedback["loops"] if item["id"] == "government_issuance_yield_loop")
    if loop["quantitatively_active"] is not False:
        errors.append("yield pilot may not activate issuance-yield loop")

    disposition = pilot["scientific_disposition"]
    if disposition["descriptive_materialisation_complete"] is not True:
        errors.append("yield pilot materialisation must remain complete")
    for key in (
        "canonical_reference_mode_promoted",
        "generic_sovereign_yield_aggregate_constructed",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if disposition[key] is not False:
            errors.append(f"descriptive yield pilot may not promote {key}")

    return errors


def main() -> None:
    pilot = load(PILOT_PATH)
    issuance = load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    feedback = load("model/dynamics/feedback_registry.json")
    errors = audit_bnr_primary_market_yield_pilot(pilot, issuance, prereg, feedback)
    if errors:
        raise RuntimeError(
            "BNR primary-market yield pilot audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "coverage": "2025-01..2025-12",
                "rate_observations": {
                    "RON_discount_treasury_certificates": 10,
                    "EUR_treasury_certificates": 1,
                    "RON_interest_bearing_bonds": 12,
                    "RON_inflation_linked_bonds": 0,
                    "EUR_interest_bearing_bonds": 2,
                },
                "generic_sovereign_yield_aggregate_constructed": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
