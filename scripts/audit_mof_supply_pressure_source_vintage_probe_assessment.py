from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "government_securities_supply_pressure_source_vintage_probe_assessment_2026_09_20.json"
)
VINTAGE_ROOT = ROOT / "data/source_vintages/mof-supply-pressure-probe-vintage-2026-09-20"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_mof_supply_pressure_probe_assessment(
    assessment: dict,
    manifest: dict,
    source_review: dict,
    boundary: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    retained = assessment["retained_vintage"]
    if retained["repository_retained"] is not True:
        errors.append("probe assessment must retain source vintage")
    if retained["native_text_extraction_method"] != "pdftotext -layout":
        errors.append("native text extraction method changed")
    for key in (
        "ocr_used",
        "visual_chart_digitisation_used",
        "manual_graph_value_approximation_used",
    ):
        if retained[key] is not False:
            errors.append(f"probe assessment may not use {key}")

    identities = assessment["source_identity"]
    for source_id, expected in identities.items():
        manifest_source = next(
            item for item in manifest["sources"] if item["source_id"] == source_id
        )
        raw_path = VINTAGE_ROOT / manifest_source["raw_path"]
        text_path = VINTAGE_ROOT / manifest_source["native_text_path"]
        if not raw_path.is_file():
            errors.append(f"{source_id}: retained raw PDF missing")
            continue
        if not text_path.is_file():
            errors.append(f"{source_id}: retained native text missing")
            continue
        if raw_path.stat().st_size != expected["raw_bytes"]:
            errors.append(f"{source_id}: retained raw byte size changed")
        if sha256_file(raw_path) != expected["raw_sha256"]:
            errors.append(f"{source_id}: retained raw SHA-256 changed")
        if sha256_file(text_path) != expected["native_text_sha256"]:
            errors.append(f"{source_id}: retained native-text SHA-256 changed")
        if manifest_source["raw_sha256"] != expected["raw_sha256"]:
            errors.append(f"{source_id}: manifest raw SHA-256 changed")
        if manifest_source["all_required_anchors_found"] is not True:
            errors.append(f"{source_id}: required native-text anchors no longer pass")

    flash = assessment["extractability_results"]["flash_auction_table_native_text"]
    if flash["status"] != "PASS_EXACT_TABLE_TEXT_AVAILABLE":
        errors.append("Flash auction table extractability status changed")
    january = flash["january_2025"]
    if january["coverage_status"] != "COMPLETED_MONTH_IN_REVIEWED_FLASH_TABLE":
        errors.append("January auction coverage status changed")
    if january["total_announced_RON_million"] != 5770.0:
        errors.append("January exact announced total changed")
    if january["total_borrowed_RON_million"] != 7556.97:
        errors.append("January exact borrowed total changed")
    if january["safe_as_exact_descriptive_values"] is not True:
        errors.append("January exact values must remain descriptive-safe")

    february = flash["february_2025"]
    if february["total_announced_RON_million"] != 8040.0:
        errors.append("February scheduled announced total changed")
    if february["borrowed_total_shown_RON_million"] != 4207.01:
        errors.append("February as-of-report borrowed total changed")
    if february["safe_as_final_full_month_borrowed_total"] is not False:
        errors.append("February borrowed total may not be treated as final full month")

    flash_text = (
        VINTAGE_ROOT / "native_text/mof_flash_report_january_2025.txt"
    ).read_text(encoding="utf-8")
    for token in ("5,770.00", "7,556.97", "8,040.00", "4,207.01"):
        if token not in flash_text:
            errors.append(f"Flash exact token missing: {token}")

    chart = assessment["extractability_results"]["monthly_report_bid_to_cover_chart"]
    if chart["month_to_series_numeric_mapping_reproducible_from_native_text_only"] is not False:
        errors.append("bid-to-cover chart may not claim exact month/series mapping")
    if chart["submitted_bids_series_materialisation_authorized"] is not False:
        errors.append("submitted-bids series materialisation may not be authorized")
    if chart["bid_to_cover_series_materialisation_authorized"] is not False:
        errors.append("bid-to-cover series materialisation may not be authorized")

    stock = assessment["extractability_results"]["january_stock_denominator_candidates"]
    if stock["monthly_report_all_domestic_market_securities_available_at_nominal_value_LEI_million"] != 395936.0:
        errors.append("January all-currency domestic holdings total changed")
    if stock["monthly_report_RON_denom_domestic_market_securities_available_at_nominal_value_LEI_million"] != 381933.8:
        errors.append("January RON-denominated domestic holdings total changed")
    if stock["monthly_report_EUR_denom_domestic_market_securities_available_at_nominal_value_EUR_million"] != 2813.5:
        errors.append("January EUR-denominated domestic holdings total changed")
    if stock["flash_components_arithmetically_reconcile_to_flash_total"] is not False:
        errors.append("Flash current-outstanding components may not be claimed reconciled")
    if stock["denominator_selected"] is not False:
        errors.append("supply-load denominator may not be selected")

    readiness = assessment["candidate_readiness"]
    if readiness["domestic_RON_primary_market_supply_load"]["ratio_materialisation_authorized"] is not False:
        errors.append("supply-load ratio may not be materialised")
    if readiness["domestic_RON_primary_market_auction_absorption"]["ratio_materialisation_authorized"] is not False:
        errors.append("auction-absorption ratio may not be materialised")
    if readiness["domestic_RON_primary_market_bid_to_cover"]["series_materialisation_authorized"] is not False:
        errors.append("bid-to-cover series may not be materialised")

    effect = assessment["scientific_effect"]
    if effect["raw_source_retention_blocker_closed_for_probe_sources"] is not True:
        errors.append("raw-source retention probe must remain closed")
    if effect["native_text_extractability_probe_completed"] is not True:
        errors.append("native-text probe must remain completed")
    for key in (
        "full_month_multimonth_supply_pressure_series_created",
        "government_securities_supply_pressure_node_resolved",
        "scalar_pressure_index_selected",
        "exact_reference_mode_promoted",
        "equation_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"probe assessment may not promote {key}")

    gate = source_review["materialisation_gate"]
    if gate["raw_ministry_pdf_retained_now"] is not True:
        errors.append("source review does not register retained Ministry PDFs")
    if gate["supply_load_denominator_boundary_frozen"] is not False:
        errors.append("source review denominator boundary unexpectedly frozen")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("probe assessment may not resolve supply-pressure node")
    if node["scalar_pressure_index_selected"] is not False:
        errors.append("probe assessment may not select scalar pressure index")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("probe assessment may not authorize feedback")

    dynamic = model_contract["dynamic_core"]
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "government_securities_supply_measurement_design_review"
    ):
        errors.append("model contract next task changed")

    next_gate = assessment["next_gate"]
    if next_gate["id"] != "supply_load_denominator_candidate_materialisation_comparison":
        errors.append("assessment next gate changed")
    if next_gate["may_compute_pressure_ratio_now"] is not False:
        errors.append("assessment may not compute pressure ratio now")
    if next_gate["may_activate_feedback"] is not False:
        errors.append("assessment may not activate feedback")

    return errors


def main() -> None:
    assessment = load(ASSESSMENT_PATH)
    manifest = load(
        "data/source_vintages/mof-supply-pressure-probe-vintage-2026-09-20/"
        "source_vintage_probe_manifest.json"
    )
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    model_contract = load("model/registries/model_contract.json")

    errors = audit_mof_supply_pressure_probe_assessment(
        assessment, manifest, source_review, boundary, model_contract
    )
    if errors:
        raise RuntimeError(
            "Ministry supply-pressure source-vintage probe assessment failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "raw_sources_retained": 3,
                "native_text_extractability": "PASS",
                "january_announced_RON_million": 5770.0,
                "january_borrowed_RON_million": 7556.97,
                "february_borrowed_final_month_claim_allowed": False,
                "submitted_bids_series_materialisable": False,
                "supply_load_denominator_frozen": False,
                "pressure_ratio_materialisation_authorized": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
