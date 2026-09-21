from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "mof_realized_financing_channel_source_vintage_assessment_2026_09_21.json"
)
MANIFEST_PATH = (
    "data/source_vintages/"
    "mof-realized-financing-channels-2025-vintage-2026-09-21/"
    "source_vintage_manifest.json"
)
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "PASS_FULL_2025_EXACT_CUMULATIVE_YTD_MONTHLY_DIFFERENCING_BLOCKED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_mof_realized_financing_channel_source_vintage_assessment(
    assessment: dict,
    manifest: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["decision"] != (
        "PASS_FULL_2025_EXACT_CUMULATIVE_YTD_VECTOR_MONTHLY_DIFFERENCING_"
        "BLOCKED_BY_CONVERSION_AND_OPERATION_BOUNDARY"
    ):
        errors.append("source-vintage assessment decision changed")

    retention = assessment["source_retention"]
    if retention["report_count"] != 12:
        errors.append("full-year report count changed")
    if retention["coverage"] != "2025-01..2025-12":
        errors.append("full-year report coverage changed")
    for key in (
        "all_months_available",
        "official_MoF_PDFs_retained",
        "native_text_retained",
        "provider_published_cumulative_ytd_extraction_pass",
    ):
        if retention[key] is not True:
            errors.append(f"source retention field changed: {key}")
    if retention["monthly_increment_computed"] is not False:
        errors.append("source-vintage assessment may not compute monthly increments")

    if manifest["status"] != "PASS_FULL_2025_EXACT_CUMULATIVE_YTD_SOURCE_VINTAGE":
        errors.append("source-vintage manifest status changed")
    if manifest["available_report_count"] != 12:
        errors.append("manifest available-report count changed")
    if manifest["unavailable_report_count"] != 0:
        errors.append("manifest may not introduce unavailable reports")
    if manifest["available_periods"] != [f"2025-{month:02d}" for month in range(1, 13)]:
        errors.append("manifest full-year period set changed")
    for key in (
        "monthly_increment_computed",
        "channel_residual_computed",
        "allocation_share_estimated",
        "generic_debt_issuance_node_promoted",
        "feedback_activation_authorized",
    ):
        if manifest[key] is not False:
            errors.append(f"manifest may not promote {key}")

    reports = {item["report_period"]: item for item in manifest["reports"]}
    if len(reports) != 12:
        errors.append("manifest report identity set changed")

    base = ROOT / (
        "data/source_vintages/"
        "mof-realized-financing-channels-2025-vintage-2026-09-21"
    )
    for period, report in reports.items():
        if report["source_available"] is not True:
            errors.append(f"{period}: source must remain available")
            continue
        if report["all_identity_checks_pass"] is not True:
            errors.append(f"{period}: identity checks changed")
        raw_path = base / report["raw_path"]
        text_path = base / report["native_text_path"]
        if sha256_file(raw_path) != report["raw_sha256"]:
            errors.append(f"{period}: retained PDF SHA-256 changed")
        if sha256_file(text_path) != report["native_text_sha256"]:
            errors.append(f"{period}: retained native-text SHA-256 changed")
        if report["cumulative_ytd"]["monthly_increment_computed"] is not False:
            errors.append(f"{period}: report may not contain monthly increment")

        values = report["cumulative_ytd"]["values"]
        central_gap = abs(
            values["central_government_total"]
            - values["domestic_market_total"]
            - values["external_market_total"]
        )
        reimbursable_gap = abs(
            values["total_reimbursable_financing"]
            - values["central_government_total"]
            - values["local_government_borrowing"]
            - values["cash_management_instruments"]
        )
        if central_gap > 0.11:
            errors.append(f"{period}: central market subtotal reconciliation changed")
        if reimbursable_gap > 0.11:
            errors.append(f"{period}: reimbursable financing reconciliation changed")

    regimes = assessment["conversion_regimes"]
    expected_regimes = [
        (["2025-01", "2025-02"], "5,01 LEI/EUR", "4.70 LEI/USD"),
        (["2025-03", "2025-04", "2025-05"], "5,01 LEI/EUR", "4.57 LEI/USD"),
        (["2025-06", "2025-07", "2025-08", "2025-09"], "5,04 LEI/EUR", "4.57 LEI/USD"),
        (["2025-10", "2025-11", "2025-12"], "5,04 LEI/EUR", "4.47 LEI/USD"),
    ]
    if len(regimes) != 4:
        errors.append("conversion-regime count changed")
    else:
        for regime, (periods, eur, usd) in zip(regimes, expected_regimes):
            if regime["periods"] != periods:
                errors.append(f"conversion regime period set changed: {periods}")
            if eur not in regime["published_note"] or usd not in regime["published_note"]:
                errors.append(f"conversion regime values changed: {periods}")

    definition = assessment["definition_stability"]
    if definition["channel_labels_extractable_all_12_reports"] is not True:
        errors.append("channel-label stability changed")
    if definition["same_RON_equivalent_conversion_basis_all_year"] is not False:
        errors.append("annual RON-equivalent conversion basis may not be called stable")
    if definition["RON_treasury_bond_line_includes_exchange_operations_all_reviewed_vintages"] is not True:
        errors.append("Treasury-bond exchange-operation guard changed")
    if definition["cash_management_is_outstanding_due_in_year_not_simple_cumulative_borrowing"] is not True:
        errors.append("cash-management semantic guard changed")

    diagnostics = assessment["non_monotone_cumulative_diagnostics"]
    fields = {item["field"] for item in diagnostics}
    if fields != {
        "eurobonds_cumulative_ytd",
        "external_market_total_cumulative_ytd",
        "local_government_borrowing_cumulative_ytd",
        "cash_management_instruments_cumulative_ytd",
    }:
        errors.append("non-monotone diagnostic field set changed")

    euro = [item for item in diagnostics if item["field"] == "eurobonds_cumulative_ytd"]
    if len(euro) != 2:
        errors.append("Eurobond non-monotone diagnostic count changed")
    else:
        observed = {
            (item["transition"], item["change_million_RON_equivalent"])
            for item in euro
        }
        if observed != {
            ("2025-10_to_2025-11", -500.0),
            ("2025-11_to_2025-12", -5040.0),
        }:
            errors.append("Eurobond non-monotone diagnostic values changed")

    reconciliation = assessment["internal_reconciliation"]
    if reconciliation["central_government_total_equals_domestic_plus_external_with_published_rounding"] is not True:
        errors.append("central subtotal reconciliation guard changed")
    if reconciliation["total_reimbursable_financing_equals_central_plus_local_plus_cash_management_with_published_rounding"] is not True:
        errors.append("total reimbursable reconciliation guard changed")
    if reconciliation["rounding_tolerance_million_RON"] != 0.1:
        errors.append("published rounding tolerance changed")

    disposition = assessment["materialisation_disposition"]
    if disposition["cumulative_ytd_vector_status"] != "PASS_EXACT_FULL_2025_PROVIDER_PUBLISHED":
        errors.append("cumulative-YTD vector disposition changed")
    if disposition["monthly_increment_status"] != (
        "BLOCKED_NOT_DEFINITIONALLY_ADMISSIBLE_FROM_PUBLISHED_RON_EQUIVALENT_YTD_VALUES"
    ):
        errors.append("monthly-increment disposition changed")
    for key in (
        "monthly_increment_equation_authorized",
        "cross_currency_reaggregation_authorized",
        "residual_channel_allocation_authorized",
        "synthetic_channel_shares_authorized",
        "BNR_domestic_primary_series_reconciliation_as_equality_test_authorized",
        "generic_government_debt_issuance_node_promoted",
    ):
        if disposition[key] is not False:
            errors.append(f"source-vintage assessment may not authorize {key}")

    effect = assessment["scientific_effect"]
    if effect["financing_channel_source_boundary_strengthened"] is not True:
        errors.append("source-boundary strengthening flag changed")
    for key in (
        "financing_channel_allocation_identified",
        "government_debt_issuance_node_resolved",
        "government_financing_need_node_resolved",
        "monthly_realized_financing_flow_series_created",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"source-vintage assessment may not promote {key}")

    next_gate = assessment["next_independent_gate"]
    if next_gate["id"] != "government_debt_issuance_to_debt_stock_boundary_review":
        errors.append("next independent gate changed")
    if next_gate["authorization"] != "STRUCTURAL_ACCOUNTING_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next independent gate authorization changed")
    for key in (
        "may_map_gross_borrowing_one_to_one_to_debt_stock_change",
        "may_treat_exchange_operations_as_net_new_debt",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
    ):
        if next_gate[key] is not False:
            errors.append(f"next independent gate may not authorize {key}")

    for node_id in ("government_financing_need", "government_debt_issuance"):
        node = next(x for x in boundary["variables"] if x["id"] == node_id)
        if node.get("financing_channel_source_vintage_assessment") != ASSESSMENT_PATH:
            errors.append(f"{node_id}: source-vintage assessment missing")
        if node.get("financing_channel_source_vintage_status") != STATUS:
            errors.append(f"{node_id}: source-vintage status changed")
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node_id}: source-vintage evidence may not resolve node")
        if node["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node_id}: source-vintage evidence may not activate node")

    links = [
        x for x in readiness["links"]
        if x["from"] == "government_financing_need"
        and x["to"] == "government_debt_issuance"
    ]
    for link in links:
        if link.get("financing_channel_source_vintage_assessment") != ASSESSMENT_PATH:
            errors.append(f"{link['loop_id']}: source-vintage assessment missing")
        if link.get("financing_channel_source_vintage_status") != STATUS:
            errors.append(f"{link['loop_id']}: source-vintage status changed")
        if link.get("monthly_differencing_authorized") is not False:
            errors.append(f"{link['loop_id']}: monthly differencing may not be authorized")
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['loop_id']}: source-vintage evidence may not make equation ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['loop_id']}: source-vintage evidence may not activate link")

    for loop_id in ("government_refinancing_interest_loop", "government_issuance_yield_loop"):
        loop = next(x for x in feedback["loops"] if x["id"] == loop_id)
        if loop.get("financing_channel_source_vintage_assessment") != ASSESSMENT_PATH:
            errors.append(f"{loop_id}: source-vintage assessment missing")
        if loop.get("financing_channel_source_vintage_status") != STATUS:
            errors.append(f"{loop_id}: source-vintage status changed")
        if loop.get("financing_channel_monthly_differencing_authorized") is not False:
            errors.append(f"{loop_id}: monthly differencing may not be authorized")
        if loop["quantitatively_active"] is not False:
            errors.append(f"{loop_id}: source-vintage evidence may not activate loop")

    bridge = next(
        x for x in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if x["id"] == "financing_channel_allocation"
    )
    if bridge.get("source_vintage_manifest") != MANIFEST_PATH:
        errors.append("preregistration source-vintage manifest changed")
    if bridge.get("source_vintage_assessment") != ASSESSMENT_PATH:
        errors.append("preregistration source-vintage assessment changed")
    if bridge.get("source_vintage_status") != STATUS:
        errors.append("preregistration source-vintage status changed")
    if bridge.get("full_2025_cumulative_ytd_coverage") is not True:
        errors.append("preregistration full-year cumulative coverage changed")
    if bridge.get("monthly_differencing_authorized") is not False:
        errors.append("preregistration may not authorize monthly differencing")
    if bridge.get("allocation_vector_identified") is not False:
        errors.append("preregistration may not identify allocation vector")
    if prereg["next_independent_bridge_task"]["id"] != (
        "government_refinancing_interest_loop_evidence_triggered_hold"
    ):
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_realized_financing_channel_source_vintage_manifest") != MANIFEST_PATH:
        errors.append("model contract source-vintage manifest changed")
    if dynamic.get("mof_realized_financing_channel_source_vintage_assessment") != ASSESSMENT_PATH:
        errors.append("model contract source-vintage assessment changed")
    if dynamic.get("mof_realized_financing_channel_source_vintage_status") != STATUS:
        errors.append("model contract source-vintage status changed")
    if dynamic.get("mof_realized_financing_channel_full_2025_cumulative_ytd_coverage") is not True:
        errors.append("model contract full-year cumulative coverage changed")
    if dynamic.get("mof_realized_financing_channel_monthly_differencing_authorized") is not False:
        errors.append("model contract may not authorize monthly differencing")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "government_refinancing_interest_loop_evidence_triggered_hold"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("mof_realized_financing_channel_source_vintage_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline lacks source-vintage assessment authority")

    return errors


def main() -> None:
    errors = audit_mof_realized_financing_channel_source_vintage_assessment(
        load(ASSESSMENT_PATH),
        load(MANIFEST_PATH),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "MoF realized-financing source-vintage assessment failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "full_2025_reports_retained": 12,
        "cumulative_ytd_extraction": "PASS",
        "monthly_differencing_authorized": False,
        "allocation_vector_identified": False,
        "generic_debt_issuance_node_resolved": False,
        "feedback_activation_authorized": False,
        "next_gate": "government_debt_issuance_to_debt_stock_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
