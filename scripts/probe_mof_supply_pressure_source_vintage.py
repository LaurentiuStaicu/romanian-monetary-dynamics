#!/usr/bin/env python3
"""Acquire exact Ministry source PDFs and test native text extractability.

This probe is provenance/extractability only. It performs no OCR, no chart
digitisation, no numerical interpolation, no pressure-index construction and
no feedback activation.
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
CONTRACT_PATH = ROOT / "model/dynamics/government_securities_supply_pressure_source_vintage_probe_contract.json"
SCRIPT_PATH = Path(__file__).resolve()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def validate_pdf(payload: bytes, minimum_bytes: int) -> None:
    if not payload.startswith(b"%PDF-"):
        raise RuntimeError("source response is not a PDF payload")
    if len(payload) < minimum_bytes:
        raise RuntimeError(
            f"source PDF is unexpectedly small: {len(payload)} bytes"
        )


def acquire_pdf(source: dict, raw_dir: Path, minimum_bytes: int, accept: str) -> tuple[Path, dict]:
    request = Request(
        source["url"],
        headers={
            "Accept": accept,
            "User-Agent": (
                "Romanian-Monetary-Dynamics-source-vintage/0.1 "
                "(https://github.com/LaurentiuStaicu/romanian-monetary-dynamics)"
            ),
        },
    )
    with urlopen(request, timeout=90) as response:
        status = int(response.getcode())
        if status != 200:
            raise RuntimeError(
                f"{source['source_id']}: unexpected HTTP status {status}"
            )
        payload = response.read()
        headers = {
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }

    validate_pdf(payload, minimum_bytes)
    raw_path = raw_dir / source["raw_filename"]
    raw_path.write_bytes(payload)
    return raw_path, {
        "status": status,
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "response_metadata": headers,
    }


def extract_native_text(raw_path: Path, text_path: Path) -> None:
    result = subprocess.run(
        ["pdftotext", "-layout", str(raw_path), str(text_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed for {raw_path.name}: {result.stderr.strip()}"
        )
    if not text_path.is_file() or text_path.stat().st_size == 0:
        raise RuntimeError(f"pdftotext produced no text for {raw_path.name}")


def anchor_assessment(text: str, anchors: list[str]) -> dict:
    haystack = normalized(text)
    return {
        anchor: normalized(anchor) in haystack
        for anchor in anchors
    }


def excerpt_for_anchor(text: str, anchor: str, radius: int = 900) -> str:
    haystack = normalized(text)
    needle = normalized(anchor)
    idx = haystack.find(needle)
    if idx < 0:
        return f"[ANCHOR NOT FOUND] {anchor}\n"
    start = max(0, idx - radius)
    end = min(len(haystack), idx + len(needle) + radius)
    return haystack[start:end] + "\n"


def run_probe(out_dir: Path) -> dict:
    contract = load_contract()
    acquisition = contract["acquisition"]
    raw_dir = out_dir / "raw"
    text_dir = out_dir / "native_text"
    excerpt_dir = out_dir / "anchor_excerpts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    excerpt_dir.mkdir(parents=True, exist_ok=True)

    source_results = []
    all_anchor_checks_pass = True

    for source in contract["sources"]:
        raw_path, raw_meta = acquire_pdf(
            source,
            raw_dir,
            int(acquisition["minimum_bytes_per_pdf"]),
            acquisition["accept"],
        )
        text_path = text_dir / (raw_path.stem + ".txt")
        extract_native_text(raw_path, text_path)
        text = text_path.read_text(encoding="utf-8", errors="replace")
        checks = anchor_assessment(text, source["required_text_anchors"])
        all_anchor_checks_pass = all_anchor_checks_pass and all(checks.values())

        excerpt_path = excerpt_dir / (raw_path.stem + "_anchors.txt")
        excerpt_chunks = []
        for anchor in source["required_text_anchors"]:
            excerpt_chunks.append(f"=== {anchor} ===\n")
            excerpt_chunks.append(excerpt_for_anchor(text, anchor))
        excerpt_path.write_text("".join(excerpt_chunks), encoding="utf-8")

        source_results.append(
            {
                "source_id": source["source_id"],
                "institution": source["institution"],
                "publication": source["publication"],
                "role": source["role"],
                "url": source["url"],
                "raw_path": f"raw/{raw_path.name}",
                "raw_bytes": raw_meta["bytes"],
                "raw_sha256": raw_meta["sha256"],
                "response_metadata": raw_meta["response_metadata"],
                "native_text_path": f"native_text/{text_path.name}",
                "native_text_bytes": text_path.stat().st_size,
                "native_text_sha256": sha256_file(text_path),
                "anchor_excerpt_path": f"anchor_excerpts/{excerpt_path.name}",
                "required_anchor_checks": checks,
                "all_required_anchors_found": all(checks.values()),
            }
        )

    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    manifest = {
        "snapshot_id": "mof-supply-pressure-probe-vintage-2026-09-20",
        "fetched_at_utc": fetched_at,
        "status": (
            "RAW_SOURCES_RETAINABLE_NATIVE_TEXT_ANCHORS_PASS"
            if all_anchor_checks_pass
            else "RAW_SOURCES_RETAINABLE_NATIVE_TEXT_ANCHORS_PARTIAL"
        ),
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "native_text_extractor": acquisition["native_text_extractor"],
        "sources": source_results,
        "all_required_anchor_checks_pass": all_anchor_checks_pass,
        "scientific_guards": contract["scientific_guards"],
        "extractability_rules": contract["extractability_rules"],
        "numeric_series_materialised": False,
        "scalar_pressure_index_selected": False,
        "feedback_activation_authorized": False,
    }
    manifest_path = out_dir / "source_vintage_probe_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "status": manifest["status"],
        "sources": [
            {
                "source_id": item["source_id"],
                "bytes": item["raw_bytes"],
                "sha256": item["raw_sha256"],
                "native_text_bytes": item["native_text_bytes"],
                "anchors_pass": item["all_required_anchors_found"],
            }
            for item in source_results
        ],
        "numeric_series_materialised": False,
        "feedback_activation_authorized": False,
    }, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_supply_pressure_probe_artifacts",
    )
    args = parser.parse_args()
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
