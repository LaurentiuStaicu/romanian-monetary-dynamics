#!/usr/bin/env python3
"""Retain Ministry announced-RON primary-supply prospectus source vintage.

Acquisition and native text extraction only. No OCR, chart digitisation,
manual approximation, event parsing, reference-mode promotion or estimation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
)
SCRIPT_PATH = Path(__file__).resolve()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def validate_pdf(payload: bytes) -> None:
    if not payload.startswith(b"%PDF-"):
        raise RuntimeError("source response is not a PDF")
    if len(payload) < 50000:
        raise RuntimeError(f"source PDF unexpectedly small: {len(payload)} bytes")


def extract_native_text(pdf_path: Path, text_path: Path) -> None:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(text_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed for {pdf_path.name}: {result.stderr.strip()}"
        )
    if not text_path.is_file() or text_path.stat().st_size == 0:
        raise RuntimeError(f"pdftotext produced no text for {pdf_path.name}")


def normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in decomposed
        if not unicodedata.combining(char)
    )
    return " ".join(without_marks.split()).casefold()


def anchor_checks(text: str, source: dict) -> dict[str, bool]:
    order = source["order_number"]
    anchors = [
        f"ORDIN NR. {order}",
        "ANEXA 1",
        "ANEXA 2",
        "PROSPECT DE EMISIUNE",
        "licitaţiei",
        "Valoare nominală",
        "SSON",
    ]
    haystack = normalized(text)
    return {anchor: normalized(anchor) in haystack for anchor in anchors}


def acquire_source(source: dict, raw_dir: Path, text_dir: Path) -> dict:
    source_id = source["source_id"]
    raw_path = raw_dir / f"{source_id}.pdf"
    text_path = text_dir / f"{source_id}.txt"
    request = Request(
        source["url"],
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
        response_meta = {
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }
    if status != 200:
        raise RuntimeError(f"{source_id}: HTTP {status}")
    validate_pdf(payload)
    raw_path.write_bytes(payload)
    extract_native_text(raw_path, text_path)
    text = text_path.read_text(encoding="utf-8", errors="replace")
    checks = anchor_checks(text, source)
    return {
        "source_id": source_id,
        "order_number": source["order_number"],
        "order_issue_date": source["order_issue_date"],
        "coverage_label": source["coverage_label"],
        "url": source["url"],
        "http_status": status,
        "response_metadata": response_meta,
        "raw_path": f"raw/{raw_path.name}",
        "raw_bytes": raw_path.stat().st_size,
        "raw_sha256": sha256_file(raw_path),
        "native_text_path": f"native_text/{text_path.name}",
        "native_text_bytes": text_path.stat().st_size,
        "native_text_sha256": sha256_file(text_path),
        "required_anchor_checks": checks,
        "all_required_anchors_found": all(checks.values()),
        "article_1_base_nominal_RON_million": source[
            "article_1_base_nominal_RON_million"
        ],
        "article_1_SSON_max_RON_million": source[
            "article_1_SSON_max_RON_million"
        ],
        "article_1_document_total_RON_million": source[
            "article_1_document_total_RON_million"
        ],
    }


def run_probe(out_dir: Path) -> dict:
    contract = load_contract()
    raw_dir = out_dir / "raw"
    text_dir = out_dir / "native_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    sources = [
        acquire_source(source, raw_dir, text_dir)
        for source in contract["pilot_source_documents"]
    ]
    all_anchors = all(item["all_required_anchors_found"] for item in sources)
    manifest = {
        "snapshot_id": "mof-announced-ron-primary-supply-pilot-vintage-2026-09-20",
        "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "native_text_extractor": "pdftotext -layout",
        "sources": sources,
        "all_required_anchor_checks_pass": all_anchors,
        "event_rows_materialised": False,
        "reference_mode_promoted": False,
        "yield_effect_estimation_authorized": False,
        "feedback_activation_authorized": False,
        "status": (
            "RAW_SOURCES_RETAINABLE_NATIVE_TEXT_ANCHORS_PASS"
            if all_anchors
            else "RAW_SOURCES_RETAINABLE_NATIVE_TEXT_ANCHORS_PARTIAL"
        ),
    }
    manifest_path = out_dir / "source_vintage_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "sources": [
                    {
                        "source_id": item["source_id"],
                        "bytes": item["raw_bytes"],
                        "sha256": item["raw_sha256"],
                        "native_text_bytes": item["native_text_bytes"],
                        "anchors_pass": item["all_required_anchors_found"],
                    }
                    for item in sources
                ],
                "event_rows_materialised": False,
                "reference_mode_promoted": False,
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
        default="mof_announced_supply_pilot_artifacts",
    )
    parser.add_argument(
        "--allow-live-refetch",
        action="store_true",
        help=(
            "Explicitly authorize a live provider refetch for this retired "
            "historical acquisition path. Unchanged reruns are reproduction "
            "only and do not reopen any scientific gate."
        ),
    )
    args = parser.parse_args()
    if not args.allow_live_refetch:
        parser.error(
            "live refetch is disabled by default for this retired historical "
            "path; rerun with --allow-live-refetch only after an explicit "
            "evidence/change trigger and review"
        )
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
