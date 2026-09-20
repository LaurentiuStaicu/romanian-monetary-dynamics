from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "171569f159b47ceedc9d8ba6d5628a39de49a8fb18d11e13a20ac55edb39c628"
EXPECTED_BYTES = 2305604
VINTAGE_ROOT = ROOT / "data/source_vintages/bnr-government-issuance-2025-vintage-2026-09-20"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_bnr_raw_source_retention(
    manifest: dict,
    acquisition_contract: dict,
    retention: dict,
    snapshot: dict,
    materialisation: dict,
    review: dict,
) -> list[str]:
    errors: list[str] = []
    raw = manifest["raw_source"]
    raw_path = VINTAGE_ROOT / raw["path"]

    if not raw_path.is_file():
        errors.append("retained BNR raw PDF is missing")
        return errors

    if raw_path.stat().st_size != EXPECTED_BYTES:
        errors.append("retained BNR raw PDF byte size changed")
    if file_sha256(raw_path) != EXPECTED_SHA256:
        errors.append("retained BNR raw PDF SHA-256 changed")

    if raw["bytes"] != EXPECTED_BYTES:
        errors.append("BNR source-vintage manifest byte size changed")
    if raw["sha256"] != EXPECTED_SHA256:
        errors.append("BNR source-vintage manifest SHA-256 changed")

    source = acquisition_contract["source"]
    if raw["url"] != source["url"]:
        errors.append("retained BNR raw URL differs from frozen acquisition contract")
    if raw["accept"] != source["accept"]:
        errors.append("retained BNR Accept header differs from frozen acquisition contract")
    if manifest["source_semantics"]["table"] != source["table"]:
        errors.append("retained BNR table semantics changed")
    if manifest["source_semantics"]["pdf_page"] != source["pdf_page"]:
        errors.append("retained BNR PDF page changed")
    if manifest["source_semantics"]["statistical_data_available_as_of"] != (
        source["statistical_data_available_as_of"]
    ):
        errors.append("retained BNR statistical vintage changed")

    retained = retention["retained_vintage"]
    if retained["repository_retained"] is not True:
        errors.append("retention assessment does not claim repository retention")
    if retained["bytes"] != EXPECTED_BYTES or retained["sha256"] != EXPECTED_SHA256:
        errors.append("retention assessment raw identity changed")

    extraction = snapshot["extraction"]
    if extraction["raw_pdf_retained_in_repository"] is not True:
        errors.append("BNR pilot does not register retained raw PDF")
    if extraction["raw_source_sha256"] != EXPECTED_SHA256:
        errors.append("BNR pilot raw-source hash differs from retained vintage")
    if extraction["raw_source_bytes"] != EXPECTED_BYTES:
        errors.append("BNR pilot raw-source byte size differs from retained vintage")
    if extraction["promotion_blocked_by_raw_retention_gate"] is not False:
        errors.append("closed raw-retention blocker is still reported as open")
    if snapshot["scientific_disposition"]["raw_source_retention_completed"] is not True:
        errors.append("BNR pilot scientific disposition does not close raw retention")

    bnr_path = materialisation["paths"]["bnr_domestic_primary_market"]
    if bnr_path["raw_source_retention_status"] != "PASS_RETAINED_SHA256_VERIFIED":
        errors.append("materialisation contract raw-retention status changed")
    if bnr_path["raw_source_sha256"] != EXPECTED_SHA256:
        errors.append("materialisation contract raw-source hash changed")

    decision = review["scientific_decision"]
    if decision["bnr_raw_source_retention_status"] != "PASS_RETAINED_SHA256_VERIFIED":
        errors.append("source-boundary review raw-retention status changed")
    if decision["bnr_raw_source_sha256"] != EXPECTED_SHA256:
        errors.append("source-boundary review raw-source hash changed")

    effect = retention["scientific_effect"]
    if effect["raw_source_retention_blocker_closed"] is not True:
        errors.append("retention assessment must close raw-source blocker")
    for key in (
        "canonical_reference_mode_promoted",
        "generic_government_debt_issuance_node_resolved",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"raw-source retention may not promote {key}")

    return errors


def main() -> None:
    manifest = load(
        "data/source_vintages/bnr-government-issuance-2025-vintage-2026-09-20/"
        "source_vintage_manifest.json"
    )
    acquisition_contract = load(
        "model/dynamics/government_debt_issuance_bnr_raw_source_acquisition_contract.json"
    )
    retention = load(
        "model/dynamics/government_debt_issuance_bnr_raw_source_retention_assessment_2025.json"
    )
    snapshot = load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json")
    materialisation = load(
        "model/dynamics/government_debt_issuance_materialisation_contract.json"
    )
    review = load("model/dynamics/government_debt_issuance_source_boundary_review.json")

    errors = audit_bnr_raw_source_retention(
        manifest,
        acquisition_contract,
        retention,
        snapshot,
        materialisation,
        review,
    )
    if errors:
        raise RuntimeError(
            "BNR government issuance raw-source retention audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "raw_pdf_retained": True,
                "bytes": EXPECTED_BYTES,
                "sha256": EXPECTED_SHA256,
                "raw_source_retention_blocker_closed": True,
                "reference_mode_promoted": False,
                "generic_node_resolved": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
