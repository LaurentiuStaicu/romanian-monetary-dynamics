#!/usr/bin/env python3
"""Acquire exact Ministry monthly issuance orders for the announced-RON supply pilot.

This stage retains provider bytes and native PDF text only. It does not perform
OCR, visual digitisation, event extraction, reference-mode promotion or yield
estimation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "model/dynamics/mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
)
SCRIPT_PATH = Path(__file__).resolve()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def extract_native_text(raw_path: Path, text_path: Path) -> None:
    result = subprocess.run(
        ["pdftotext", "-layout", str(raw_path), str(text_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed for {raw_path.name}: {result.stderr.strip()}"
        )
    if not text_path.is_file() or text_path.stat().st_size == 0:
        raise RuntimeError(f"pdftotext produced no text for {raw_path.name}")


def anchor_checks(text: str, doc: dict) -> dict[str, bool]:
    haystack = normalized(text)
    expected_total = doc["article_1_document_total_RON_million"]
    base = doc["article_1_base_nominal_RON_million"]
    sson = doc["article_1_SSON_max_RON_million"]
    anchors = [
        f"ORDIN NR. {doc['order_number']}",
        "Anexa 1",
        "Anexa 2",
        "Data licita",
        "Cod ISIN",
        "Valoare",
        str(int(base)),
        str(int(sson)),
        str(int(expected_total)),
    ]
    return {anchor: normalized(anchor) in haystack for anchor in anchors}


def run_probe(out_dir: Path) -> dict:
    contract = load_contract()
    raw_dir = out_dir / "raw"
    text_dir = out_dir / "native_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for doc in contract["pilot_source_documents"]:
        request = Request(
            doc["url"],
            headers={
                "Accept": "application/pdf",
                "User-Agent": (
                    "Romanian-Monetary-Dynamics-source-vintage/0.1 "
                    "(https://github.com/LaurentiuStaicu/romanian-monetary-dynamics)"
                ),
            },
        )
        with urlopen(request, timeout=90) as response:
            status = int(response.getcode())
            payload = response.read()
            meta = {
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }

        if status != 200:
            raise RuntimeError(f"{doc['source_id']}: HTTP {status}")
        if not payload.startswith(b"%PDF-"):
            raise RuntimeError(f"{doc['source_id']}: non-PDF payload")
        if len(payload) < 20000:
            raise RuntimeError(
                f"{doc['source_id']}: unexpectedly small PDF ({len(payload)} bytes)"
            )

        filename = doc["source_id"] + ".pdf"
        raw_path = raw_dir / filename
        raw_path.write_bytes(payload)

        text_path = text_dir / (doc["source_id"] + ".txt")
        extract_native_text(raw_path, text_path)
        text = text_path.read_text(encoding="utf-8", errors="replace")
        checks = anchor_checks(text, doc)

        results.append(
            {
                "source_id": doc["source_id"],
                "order_number": doc["order_number"],
                "order_issue_date": doc["order_issue_date"],
                "coverage_label": doc["coverage_label"],
                "url": doc["url"],
                "http_status": status,
                "raw_path": f"raw/{filename}",
                "raw_bytes": len(payload),
                "raw_sha256": sha256_bytes(payload),
                "response_metadata": meta,
                "native_text_path": f"native_text/{text_path.name}",
                "native_text_bytes": text_path.stat().st_size,
                "native_text_sha256": sha256_file(text_path),
                "anchor_checks": checks,
                "all_anchor_checks_pass": all(checks.values()),
                "article_1_expected": {
                    "base_RON_million": doc[
                        "article_1_base_nominal_RON_million"
                    ],
                    "SSON_RON_million": doc["article_1_SSON_max_RON_million"],
                    "combined_RON_million": doc[
                        "article_1_document_total_RON_million"
                    ],
                },
            }
        )

    manifest = {
        "snapshot_id": "mof-announced-ron-primary-supply-pilot-vintage-2026-09-20",
        "fetched_at_utc": (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        ),
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "native_text_extractor": "pdftotext -layout",
        "sources": results,
        "all_sources_retained": len(results) == len(contract["pilot_source_documents"]),
        "all_anchor_checks_pass": all(
            item["all_anchor_checks_pass"] for item in results
        ),
        "event_rows_extracted": False,
        "reference_mode_materialised": False,
        "ocr_used": False,
        "visual_digitisation_used": False,
        "feedback_activation_authorized": False,
    }
    (out_dir / "source_vintage_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": (
                    "PASS_RAW_AND_NATIVE_TEXT_RETAINABLE"
                    if manifest["all_anchor_checks_pass"]
                    else "PARTIAL_ANCHOR_CHECK"
                ),
                "sources": [
                    {
                        "source_id": x["source_id"],
                        "raw_bytes": x["raw_bytes"],
                        "raw_sha256": x["raw_sha256"],
                        "native_text_bytes": x["native_text_bytes"],
                        "anchors_pass": x["all_anchor_checks_pass"],
                    }
                    for x in results
                ],
                "event_rows_extracted": False,
                "reference_mode_materialised": False,
            },
            indent=2,
        )
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_announced_supply_pilot_artifacts",
    )
    args = parser.parse_args()
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
