#!/usr/bin/env python3
"""Acquire the exact reviewed BNR government-securities source PDF.

This is a source-vintage acquisition utility only. It does not transform,
promote, estimate, or activate any RMD model variable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

CONTRACT_PATH = Path(
    "model/dynamics/government_debt_issuance_bnr_raw_source_acquisition_contract.json"
)
SCRIPT_PATH = Path(__file__)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source_bytes(payload: bytes, content_type: str | None, contract: dict) -> None:
    acquisition = contract["acquisition"]
    prefix = acquisition["required_magic_prefix"].encode("ascii")
    if not payload.startswith(prefix):
        raise RuntimeError("BNR source acquisition did not return a PDF payload")
    if len(payload) < int(acquisition["minimum_bytes"]):
        raise RuntimeError(
            f"BNR source payload is unexpectedly small: {len(payload)} bytes"
        )
    if content_type:
        media_type = content_type.split(";", 1)[0].strip().lower()
        allowed = {value.lower() for value in acquisition["allowed_content_types"]}
        if media_type not in allowed:
            raise RuntimeError(
                f"Unexpected BNR response content type: {content_type!r}"
            )


def build_manifest(
    *,
    payload: bytes,
    content_type: str | None,
    last_modified: str | None,
    etag: str | None,
    fetched_at_utc: str,
    contract: dict,
    raw_relative_path: str,
    fetcher_script_sha256: str,
) -> dict:
    source = contract["source"]
    return {
        "snapshot_id": "bnr-government-issuance-2025-vintage-2026-09-20",
        "fetched_at_utc": fetched_at_utc,
        "status": "RAW_ACQUISITION_READY_FOR_REPOSITORY_REVIEW_NOT_PROMOTED",
        "fetcher_script": str(SCRIPT_PATH),
        "fetcher_script_sha256": fetcher_script_sha256,
        "target_candidate_id": contract["target_candidate_id"],
        "raw_source": {
            "name": contract["acquisition"]["raw_filename"],
            "institution": source["institution"],
            "publication": source["publication"],
            "url": source["url"],
            "accept": source["accept"],
            "status": 200,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "path": raw_relative_path,
            "response_metadata": {
                "content_type": content_type,
                "last_modified": last_modified,
                "etag": etag,
            },
        },
        "source_semantics": {
            "table": source["table"],
            "pdf_page": source["pdf_page"],
            "statistical_data_available_as_of": source[
                "statistical_data_available_as_of"
            ],
        },
        "normalized_outputs": [],
        "scientific_guards": contract["scientific_guards"],
        "promotion_authorized": False,
        "generic_government_debt_issuance_node_resolved": False,
        "feedback_activation_authorized": False,
    }


def acquire(out_dir: Path, contract_path: Path = CONTRACT_PATH) -> dict:
    contract = load_contract(contract_path)
    source = contract["source"]
    request = Request(
        source["url"],
        headers={
            "Accept": source["accept"],
            "User-Agent": (
                "Romanian-Monetary-Dynamics-source-vintage/0.1 "
                "(https://github.com/LaurentiuStaicu/romanian-monetary-dynamics)"
            ),
        },
    )
    with urlopen(request, timeout=90) as response:
        status = int(response.getcode())
        if status != 200:
            raise RuntimeError(f"Unexpected BNR HTTP status: {status}")
        payload = response.read()
        content_type = response.headers.get("Content-Type")
        last_modified = response.headers.get("Last-Modified")
        etag = response.headers.get("ETag")

    validate_source_bytes(payload, content_type, contract)

    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / contract["acquisition"]["raw_filename"]
    raw_path.write_bytes(payload)

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    relative_raw = f"raw/{raw_path.name}"
    manifest = build_manifest(
        payload=payload,
        content_type=content_type,
        last_modified=last_modified,
        etag=etag,
        fetched_at_utc=fetched_at,
        contract=contract,
        raw_relative_path=relative_raw,
        fetcher_script_sha256=sha256_file(SCRIPT_PATH),
    )
    manifest_path = out_dir / "source_vintage_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": "PASS",
                "raw_path": str(raw_path),
                "bytes": manifest["raw_source"]["bytes"],
                "sha256": manifest["raw_source"]["sha256"],
                "manifest": str(manifest_path),
                "promotion_authorized": False,
            },
            indent=2,
        )
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="bnr_government_issuance_raw_artifacts",
        help="Directory for the exact raw PDF and source-vintage manifest.",
    )
    args = parser.parse_args()
    acquire(Path(args.output))


if __name__ == "__main__":
    main()
