from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scripts.probe_mof_announced_RON_primary_reference_auction_missing_official_pdfs import (
    fetch,
    identity_checks,
    pdftotext,
    required_identity_checks,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_full_2025_source_vintage_contract.json"
)
VINTAGE_ROOT = (
    ROOT
    / "data/source_vintages/"
    "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20"
)
MANIFEST_PATH = VINTAGE_ROOT / "source_vintage_manifest.json"

BASELINE_RETAINED = {
    "mof_order_541_april_2025",
    "mof_order_728_may_2025",
    "mof_order_871_june_2025",
    "mof_order_1626_october_2025",
}
RECOVERED = {
    "mof_order_752_may_2025_amendment",
    "mof_order_1088_july_2025",
    "mof_order_1452_september_2025",
    "mof_order_1831_november_2025_amendment",
    "mof_order_1928_december_2025",
}
UNRESOLVED = {
    "mof_order_1221_august_2025",
    "mof_order_1795_november_2025",
    "mof_order_1998_december_2025_amendment",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_retained_file_hashes(manifest: dict, source_ids: set[str]) -> None:
    by_id = {item["source_id"]: item for item in manifest["documents"]}
    for source_id in source_ids:
        item = by_id[source_id]
        pdf_path = VINTAGE_ROOT / item["official_pdf_path"]
        if not pdf_path.is_file():
            raise RuntimeError(f"{source_id}: retained PDF missing")
        if sha256_file(pdf_path) != item["official_pdf_sha256"]:
            raise RuntimeError(f"{source_id}: retained PDF hash changed")


def verify_manifest_state(manifest: dict, contract: dict | None = None) -> str:
    if manifest["canonical_reference_mode_promoted"] is not False:
        raise RuntimeError("source vintage unexpectedly promotes reference mode")
    if manifest["feedback_activation_authorized"] is not False:
        raise RuntimeError("source vintage unexpectedly authorizes feedback")
    if manifest["yield_effect_estimation_authorized"] is not False:
        raise RuntimeError("source vintage unexpectedly authorizes yield-effect estimation")

    retained = set(manifest["retained_source_ids"])
    unavailable = set(manifest["unavailable_source_ids"])

    if (
        manifest["raw_sources_retained_count"] == 4
        and manifest["raw_sources_unavailable_count"] == 8
        and retained == BASELINE_RETAINED
        and unavailable == RECOVERED | UNRESOLVED
    ):
        _verify_retained_file_hashes(manifest, BASELINE_RETAINED)
        return "PRE_RECOVERY_4"

    expected_retained = BASELINE_RETAINED | RECOVERED
    if (
        manifest["raw_sources_retained_count"] == 9
        and manifest["raw_sources_unavailable_count"] == 3
        and retained == expected_retained
        and unavailable == UNRESOLVED
        and manifest["status"]
        == "PARTIAL_OFFICIAL_SOURCE_RETENTION_9_OF_12_THREE_UNAVAILABLE"
    ):
        if contract is None:
            contract = load_json(CONTRACT_PATH)
        docs = {item["source_id"]: item for item in contract["documents"]}
        manifest_docs = {item["source_id"]: item for item in manifest["documents"]}
        _verify_retained_file_hashes(manifest, expected_retained)

        for source_id in RECOVERED:
            document = docs[source_id]
            item = manifest_docs[source_id]
            expected_sha = document["recovery_probe_expected_pdf_sha256"]
            if item.get("official_pdf_sha256") != expected_sha:
                raise RuntimeError(f"{source_id}: promoted PDF hash differs from recovery probe")
            if item.get("official_pdf_url") != document["known_official_pdf_url"]:
                raise RuntimeError(f"{source_id}: promoted PDF URL differs from recovery contract")
            if item.get("recovery_identity_profile") != document["official_pdf_identity_profile"]:
                raise RuntimeError(f"{source_id}: promoted identity profile changed")
            if item.get("raw_source_retained") is not True:
                raise RuntimeError(f"{source_id}: promoted raw source not marked retained")
            if item.get("event_materialisation_authorized") is not True:
                raise RuntimeError(f"{source_id}: promoted source not parser-authorized")
            text_rel = item.get("native_text_path")
            if not text_rel:
                raise RuntimeError(f"{source_id}: promoted native-text path missing")
            text_path = VINTAGE_ROOT / text_rel
            if not text_path.is_file():
                raise RuntimeError(f"{source_id}: promoted native text missing")
            if sha256_file(text_path) != item.get("native_text_sha256"):
                raise RuntimeError(f"{source_id}: promoted native-text hash changed")

        transition = manifest.get("recovery_transition", {})
        if transition.get("retained_before") != 4:
            raise RuntimeError("post-recovery manifest lost retained-before count")
        if transition.get("recovered_now") != 5:
            raise RuntimeError("post-recovery manifest lost recovered-now count")
        if transition.get("retained_after") != 9:
            raise RuntimeError("post-recovery manifest lost retained-after count")
        if transition.get("remaining_unavailable") != 3:
            raise RuntimeError("post-recovery manifest lost remaining-unavailable count")
        return "POST_RECOVERY_9"

    raise RuntimeError(
        "source-vintage manifest is neither the exact pre-recovery 4/12 state "
        "nor the exact post-recovery 9/12 state"
    )


def verify_baseline_manifest(manifest: dict) -> None:
    state = verify_manifest_state(manifest)
    if state != "PRE_RECOVERY_4":
        raise RuntimeError(f"expected pre-recovery state, found {state}")


def _emit_existing_post_recovery_state(
    output: Path,
    manifest: dict,
    contract: dict,
) -> dict:
    pdf_out = output / "official_pdf_crosschecks"
    text_out = output / "native_text"
    pdf_out.mkdir(parents=True, exist_ok=True)
    text_out.mkdir(parents=True, exist_ok=True)

    by_id = {item["source_id"]: item for item in manifest["documents"]}
    for source_id in RECOVERED:
        item = by_id[source_id]
        shutil.copy2(
            VINTAGE_ROOT / item["official_pdf_path"],
            pdf_out / Path(item["official_pdf_path"]).name,
        )
        shutil.copy2(
            VINTAGE_ROOT / item["native_text_path"],
            text_out / Path(item["native_text_path"]).name,
        )

    (output / "source_vintage_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "manifest_state": "POST_RECOVERY_9",
                "raw_sources_retained": 9,
                "raw_sources_unavailable": 3,
                "unavailable_source_ids": manifest["unavailable_source_ids"],
                "idempotent_reverification": True,
                "event_rows_materialised": False,
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )
    return manifest


def promote(output: Path) -> dict:
    contract = load_json(CONTRACT_PATH)
    manifest = load_json(MANIFEST_PATH)
    state = verify_manifest_state(manifest, contract)

    output.mkdir(parents=True, exist_ok=True)
    if state == "POST_RECOVERY_9":
        return _emit_existing_post_recovery_state(output, manifest, contract)

    docs = {item["source_id"]: item for item in contract["documents"]}
    manifest_docs = {item["source_id"]: item for item in manifest["documents"]}

    if set(docs) != set(manifest_docs):
        raise RuntimeError("contract/manifest document sets diverge")

    pdf_out = output / "official_pdf_crosschecks"
    text_out = output / "native_text"
    pdf_out.mkdir(exist_ok=True)
    text_out.mkdir(exist_ok=True)

    recovery_records = []
    for source_id in sorted(RECOVERED):
        document = docs[source_id]
        target = manifest_docs[source_id]

        if target["raw_source_retained"]:
            raise RuntimeError(f"{source_id}: recovery target already retained")
        url = document.get("known_official_pdf_url")
        expected_sha = document.get("recovery_probe_expected_pdf_sha256")
        profile = document.get("official_pdf_identity_profile")
        if not url or not expected_sha or not profile:
            raise RuntimeError(f"{source_id}: recovery contract is incomplete")

        status, payload, metadata = fetch(url)
        if status != 200 or not payload.startswith(b"%PDF-"):
            raise RuntimeError(f"{source_id}: official PDF unavailable or invalid")
        observed_sha = sha256_bytes(payload)
        if observed_sha != expected_sha:
            raise RuntimeError(
                f"{source_id}: official PDF hash changed: {observed_sha} != {expected_sha}"
            )

        text = pdftotext(payload)
        if not text.strip():
            raise RuntimeError(f"{source_id}: native PDF text extraction returned empty text")
        checks = identity_checks(text, document)
        required = required_identity_checks(url, document)
        if not all(checks.get(key) is True for key in required):
            raise RuntimeError(
                f"{source_id}: required identity checks failed: "
                f"{ {key: checks.get(key) for key in required} }"
            )

        pdf_path = pdf_out / f"{source_id}.pdf"
        text_path = text_out / f"{source_id}.txt"
        pdf_path.write_bytes(payload)
        text_path.write_text(text, encoding="utf-8")

        target.update(
            {
                "official_pdf_status": "RETAINED_EXACT_OFFICIAL_PDF_RECOVERED",
                "raw_source_retained": True,
                "event_materialisation_authorized": True,
                "official_pdf_url": url,
                "official_pdf_path": f"official_pdf_crosschecks/{pdf_path.name}",
                "official_pdf_bytes": len(payload),
                "official_pdf_sha256": observed_sha,
                "official_pdf_response_metadata": metadata,
                "recovery_identity_profile": profile,
                "recovery_identity_checks": checks,
                "recovery_required_identity_checks": required,
                "recovery_frozen_legal_metadata": {
                    "order_date": document["order_date"],
                    "publication_number": document["publication_number"],
                    "publication_date": document["publication_date"],
                },
                "native_text_path": f"native_text/{text_path.name}",
                "native_text_bytes": text_path.stat().st_size,
                "native_text_sha256": sha256_file(text_path),
            }
        )
        recovery_records.append(
            {
                "source_id": source_id,
                "official_pdf_url": url,
                "official_pdf_sha256": observed_sha,
                "identity_profile": profile,
                "required_identity_checks": required,
                "all_required_identity_checks_pass": True,
            }
        )

    ordered_ids = [item["source_id"] for item in contract["documents"]]
    retained = [
        source_id for source_id in ordered_ids
        if manifest_docs[source_id]["raw_source_retained"]
    ]
    unavailable = [
        source_id for source_id in ordered_ids
        if not manifest_docs[source_id]["raw_source_retained"]
    ]

    if set(retained) != BASELINE_RETAINED | RECOVERED:
        raise RuntimeError("post-recovery retained source set is not exactly 9/12")
    if set(unavailable) != UNRESOLVED:
        raise RuntimeError("post-recovery unavailable source set is not exactly three")

    manifest.update(
        {
            "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "raw_sources_retained_count": len(retained),
            "raw_sources_unavailable_count": len(unavailable),
            "retained_source_ids": retained,
            "unavailable_source_ids": unavailable,
            "event_rows_materialised": False,
            "canonical_reference_mode_promoted": False,
            "yield_effect_estimation_authorized": False,
            "feedback_activation_authorized": False,
            "status": "PARTIAL_OFFICIAL_SOURCE_RETENTION_9_OF_12_THREE_UNAVAILABLE",
            "recovery_transition": {
                "transition_id": "official_pdf_recovery_2026_09_20",
                "retained_before": 4,
                "recovered_now": 5,
                "retained_after": 9,
                "remaining_unavailable": 3,
                "recovery_records": recovery_records,
                "no_event_materialisation_in_this_transition": True,
                "no_canonical_reference_mode_promotion": True,
                "no_feedback_activation": True,
            },
        }
    )

    (output / "source_vintage_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "raw_sources_retained": len(retained),
                "recovered_source_ids": sorted(RECOVERED),
                "raw_sources_unavailable": len(unavailable),
                "unavailable_source_ids": unavailable,
                "event_rows_materialised": False,
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_recovered_official_pdf_source_vintage_artifact",
    )
    args = parser.parse_args()
    promote(Path(args.output))


if __name__ == "__main__":
    main()
