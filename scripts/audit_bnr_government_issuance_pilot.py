from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_bnr_issuance_pilot(
    snapshot: dict,
    revision: dict,
    review: dict,
    contract: dict,
    boundary: dict,
    reference_modes: dict,
) -> list[str]:
    errors: list[str] = []

    if snapshot.get("status") != (
        "REVIEWED_FULL_2025_SOURCE_PILOT_NOT_CANONICAL_REFERENCE_SERIES"
    ):
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
    if snapshot["source"]["statistical_data_available_as_of"] != "2026-02-24":
        errors.append("BNR full-year source vintage date changed")

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
    if extraction["source_revision_check_performed"] is not True:
        errors.append("completed BNR revision check must remain recorded")
    if extraction["source_revision_check_result"] != (
        "PASS_NO_CHANGES_JAN_JUL_2025_AT_PUBLISHED_PRECISION"
    ):
        errors.append("BNR revision-check result changed")
    if extraction["promotion_blocked_by_raw_retention_and_revision_gate"] is not False:
        errors.append("closed revision blocker is still reported as open")
    if extraction["promotion_blocked_by_raw_retention_gate"] is not True:
        errors.append("raw-source retention must remain the promotion blocker")

    rows = snapshot.get("monthly_observations", [])
    periods = [row["period"] for row in rows]
    expected_periods = [f"2025-{month:02d}" for month in range(1, 13)]
    if periods != expected_periods:
        errors.append(f"BNR pilot full-year monthly coverage changed: {periods}")

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

    quarter_months = {
        "2025-Q1": ["2025-01", "2025-02", "2025-03"],
        "2025-Q2": ["2025-04", "2025-05", "2025-06"],
        "2025-Q3": ["2025-07", "2025-08", "2025-09"],
        "2025-Q4": ["2025-10", "2025-11", "2025-12"],
    }
    expected_quarter_totals = {
        "2025-Q1": (29070.2, 0.0),
        "2025-Q2": (21282.2, 1625.1),
        "2025-Q3": (26260.5, 231.0),
        "2025-Q4": (22292.9, 0.0),
    }
    checks = snapshot["derived_checks"]
    for quarter, months in quarter_months.items():
        item = checks[quarter]
        if item["complete_three_months"] is not True:
            errors.append(f"{quarter}: full-year pilot quarter must be complete")
        ron_expected, eur_expected = expected_quarter_totals[quarter]
        if item["RON_total_million"] != ron_expected:
            errors.append(f"{quarter}: reviewed RON total changed")
        if item["EUR_total_million"] != eur_expected:
            errors.append(f"{quarter}: reviewed EUR total changed")
        if item["RON_total_million"] != sum_field(
            months, "total_RON_domestic_primary_market_securities_million_RON"
        ):
            errors.append(f"{quarter}: RON aggregation is stale")
        if item["EUR_total_million"] != sum_field(
            months, "total_EUR_domestic_primary_market_securities_million_EUR"
        ):
            errors.append(f"{quarter}: EUR aggregation is stale")

    if checks["full_year_RON_total_million"] != 98905.8:
        errors.append("full-year reviewed RON issuance total changed")
    if checks["full_year_EUR_total_million"] != 1856.1:
        errors.append("full-year reviewed EUR issuance total changed")
    if checks["all_four_quarters_complete"] is not True:
        errors.append("full-year BNR pilot must retain all four complete quarters")

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

    result = revision["result"]
    if result["revision_check_completed"] is not True:
        errors.append("BNR revision assessment must remain completed")
    if result["exact_matches"] != 28 or result["changed_cells"] != 0:
        errors.append("BNR Jan-Jul revision comparison changed")
    if result["jan_jul_revision_status"] != "PASS_NO_CHANGES_AT_PUBLISHED_PRECISION":
        errors.append("BNR Jan-Jul revision status changed")
    if result["source_still_provisional"] is not True:
        errors.append("later BNR source must remain marked provisional")
    effect = revision["scientific_effect"]
    if effect["revision_check_blocker_closed"] is not True:
        errors.append("revision-check blocker should remain closed")
    if effect["raw_source_retention_blocker_closed"] is not False:
        errors.append("revision check may not close raw-source retention")
    for key in (
        "canonical_reference_mode_promoted",
        "generic_government_debt_issuance_node_resolved",
        "estimation_authorized",
        "feedback_activation_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"revision assessment may not promote {key}")

    decision = snapshot["scientific_disposition"]
    if decision["candidate_source_path_materialised_for_screening"] is not True:
        errors.append("BNR pilot must remain a materialised screening path")
    if decision["revision_check_completed"] is not True:
        errors.append("pilot scientific disposition must record completed revision check")
    if decision["full_2025_monthly_coverage"] is not True:
        errors.append("pilot scientific disposition must record full-2025 coverage")
    if decision["raw_source_retention_completed"] is not False:
        errors.append("pilot may not claim raw-source retention")
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
    if review["scientific_decision"].get("bnr_revision_assessment") != (
        "model/dynamics/government_debt_issuance_bnr_revision_assessment_2025.json"
    ):
        errors.append("issuance source review does not register revision assessment")
    bnr_path = contract["paths"]["bnr_domestic_primary_market"]
    if bnr_path.get("pilot_snapshot") != (
        "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
    ):
        errors.append("issuance materialisation contract does not register BNR pilot")
    if bnr_path.get("revision_assessment") != (
        "model/dynamics/government_debt_issuance_bnr_revision_assessment_2025.json"
    ):
        errors.append("issuance materialisation contract does not register revision assessment")
    if bnr_path.get("revision_check_status") != (
        "PASS_NO_CHANGES_JAN_JUL_2025_FULL_YEAR_EXTENSION_COMPLETE"
    ):
        errors.append("materialisation contract revision-check status is stale")
    if bnr_path.get("raw_source_retention_status") != "NOT_RETAINED_BLOCKS_PROMOTION":
        errors.append("raw-source retention blocker was weakened")

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
    revision = load(
        "model/dynamics/government_debt_issuance_bnr_revision_assessment_2025.json"
    )
    review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")
    contract = load("model/dynamics/government_debt_issuance_materialisation_contract.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    reference_modes = load("model/dynamics/reference_modes.json")

    errors = audit_bnr_issuance_pilot(
        snapshot, revision, review, contract, boundary, reference_modes
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
                "coverage": "2025-01..2025-12",
                "complete_quarters": [
                    "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"
                ],
                "revision_check": "PASS_NO_CHANGES_JAN_JUL_2025",
                "full_year_RON_total_million": 98905.8,
                "full_year_EUR_total_million": 1856.1,
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
