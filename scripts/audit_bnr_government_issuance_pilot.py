from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_bnr_issuance_pilot(
    snapshot: dict,
    review: dict,
    contract: dict,
    boundary: dict,
    reference_modes: dict,
) -> list[str]:
    errors: list[str] = []

    if snapshot.get("status") != "REVIEWED_SOURCE_PILOT_NOT_CANONICAL_REFERENCE_SERIES":
        errors.append("BNR issuance pilot status changed unexpectedly")
    if snapshot.get("target_candidate_id") != (
        "domestic_primary_market_government_securities_gross_issuance"
    ):
        errors.append("BNR issuance pilot target boundary changed")
    if snapshot["source"]["table"] != (
        "12.2 Government securities (new and roll-over issues)"
    ):
        errors.append("BNR source table changed")
    if snapshot["source"]["pdf_page"] != 65:
        errors.append("BNR source page changed")
    if snapshot["source"]["statistical_data_available_as_of"] != "2025-08-26":
        errors.append("BNR source vintage date changed")

    extraction = snapshot["extraction"]
    if extraction["ocr_used"] is not False:
        errors.append("BNR pilot unexpectedly claims OCR extraction")
    if extraction["raw_pdf_retained_in_repository"] is not False:
        errors.append("raw BNR PDF may not be claimed retained")
    if extraction["raw_source_sha256"] is not None:
        errors.append("raw BNR source hash may not exist before raw retention")
    if extraction["exact_raw_source_retention_required_before_promotion"] is not True:
        errors.append("raw-source retention gate must remain required")
    if extraction["native_currency_columns_preserved"] is not True:
        errors.append("native-currency columns must remain preserved")
    if extraction["EUR_to_RON_conversion_performed"] is not False:
        errors.append("EUR issue volumes may not be converted to RON in pilot")
    if extraction["source_revision_check_performed"] is not False:
        errors.append("pilot may not claim a completed revision check")
    if extraction["promotion_blocked_by_raw_retention_and_revision_gate"] is not True:
        errors.append("pilot promotion blocker was weakened")

    rows = snapshot.get("monthly_observations", [])
    periods = [row["period"] for row in rows]
    expected_periods = [
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-05",
        "2025-06",
        "2025-07",
    ]
    if periods != expected_periods:
        errors.append(f"BNR pilot monthly coverage changed: {periods}")

    for row in rows:
        expected_ron = round(
            float(row["discount_treasury_certificates_million_RON"])
            + float(row["interest_bearing_government_bonds_million_RON"]),
            1,
        )
        expected_eur = round(
            float(row["treasury_certificates_million_EUR"])
            + float(row["interest_bearing_government_bonds_million_EUR"]),
            1,
        )
        if row["total_RON_domestic_primary_market_securities_million_RON"] != expected_ron:
            errors.append(f"{row['period']}: RON total is stale")
        if row["total_EUR_domestic_primary_market_securities_million_EUR"] != expected_eur:
            errors.append(f"{row['period']}: EUR total is stale")

    by_period = {row["period"]: row for row in rows}
    def sum_field(periods_: list[str], key: str) -> float:
        return round(sum(float(by_period[p][key]) for p in periods_), 1)

    checks = snapshot["derived_checks"]
    q1 = checks["2025-Q1"]
    q2 = checks["2025-Q2"]
    q3 = checks["2025-Q3"]
    if q1["complete_three_months"] is not True or q1["RON_total_million"] != 29070.2:
        errors.append("BNR pilot Q1 RON total/completeness changed")
    if q1["EUR_total_million"] != 0:
        errors.append("BNR pilot Q1 EUR total changed")
    if q2["complete_three_months"] is not True or q2["RON_total_million"] != 21282.2:
        errors.append("BNR pilot Q2 RON total/completeness changed")
    if q2["EUR_total_million"] != 1625.1:
        errors.append("BNR pilot Q2 EUR total changed")
    if q3["complete_three_months"] is not False:
        errors.append("BNR pilot may not treat Q3 as complete")
    if q3["observed_months"] != ["2025-07"]:
        errors.append("BNR pilot Q3 observed-month state changed")
    if q3["RON_partial_total_million"] != 11080.9:
        errors.append("BNR pilot July RON total changed")

    if checks["jan_to_jul_RON_total_million"] != sum_field(
        expected_periods, "total_RON_domestic_primary_market_securities_million_RON"
    ):
        errors.append("Jan-Jul RON total is stale")
    if checks["jan_to_jul_EUR_total_million"] != sum_field(
        expected_periods, "total_EUR_domestic_primary_market_securities_million_EUR"
    ):
        errors.append("Jan-Jul EUR total is stale")

    semantics = snapshot["semantics"]
    if semantics["gross_issuance_equivalent_on_exact_source_boundary"] is not True:
        errors.append("exact BNR source-boundary gross-issuance meaning changed")
    for key in (
        "total_government_borrowing_equivalent",
        "refinancing_need_equivalent",
        "qsa_net_incurrence_equivalent",
        "supply_pressure_equivalent",
        "Maastricht_debt_stock_equivalent",
    ):
        if semantics[key] is not False:
            errors.append(f"BNR pilot may not imply {key}")

    decision = snapshot["scientific_disposition"]
    if decision["candidate_source_path_materialised_for_screening"] is not True:
        errors.append("BNR pilot must remain a materialised screening path")
    for key in (
        "canonical_reference_mode_promoted",
        "generic_government_debt_issuance_node_resolved",
        "estimation_authorized",
        "feedback_activation_authorized",
    ):
        if decision[key] is not False:
            errors.append(f"BNR pilot may not promote {key}")

    if review["scientific_decision"].get("bnr_pilot_snapshot") != (
        "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
    ):
        errors.append("issuance source review does not register BNR pilot")
    if contract["paths"]["bnr_domestic_primary_market"].get("pilot_snapshot") != (
        "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
    ):
        errors.append("issuance materialisation contract does not register BNR pilot")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_debt_issuance"
    )
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("BNR pilot may not resolve government_debt_issuance")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("BNR pilot may not authorize feedback activation")

    if any(
        mode["id"] == "government_debt_issuance"
        and mode["status"] == "OBSERVED_SERIES_AVAILABLE"
        for mode in reference_modes["modes"]
    ):
        errors.append("BNR pilot may not create an observed issuance reference mode")

    return errors


def main() -> None:
    snapshot = load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json")
    review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")
    contract = load("model/dynamics/government_debt_issuance_materialisation_contract.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    reference_modes = load("model/dynamics/reference_modes.json")

    errors = audit_bnr_issuance_pilot(
        snapshot, review, contract, boundary, reference_modes
    )
    if errors:
        raise RuntimeError(
            "BNR government issuance pilot audit failed:\n- "
            + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "coverage": "2025-01..2025-07",
                "complete_quarters": ["2025-Q1", "2025-Q2"],
                "q3_complete": False,
                "raw_pdf_retained": False,
                "reference_mode_promoted": False,
                "generic_node_resolved": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
