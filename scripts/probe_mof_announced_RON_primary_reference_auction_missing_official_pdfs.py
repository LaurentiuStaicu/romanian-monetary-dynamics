from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_full_2025_source_vintage_contract.json"
)

MISSING_SOURCE_IDS = {
    "mof_order_752_may_2025_amendment",
    "mof_order_1088_july_2025",
    "mof_order_1221_august_2025",
    "mof_order_1452_september_2025",
    "mof_order_1795_november_2025",
    "mof_order_1831_november_2025_amendment",
    "mof_order_1928_december_2025",
    "mof_order_1998_december_2025_amendment",
}

# Discovery candidates only. No candidate becomes a source unless the downloaded
# PDF itself passes frozen identity checks.
EXACT_WEB_VERIFIED = {
    "mof_order_1928_december_2025": [
        "https://static.anaf.ro/static/10/Anaf/legislatie/OMF_1928_2025.pdf"
    ],
}

ANAF_FILENAME_CANDIDATES = {
    "mof_order_752_may_2025_amendment": "OMF_752_2025.pdf",
    "mof_order_1088_july_2025": "OMF_1088_2025.pdf",
    "mof_order_1221_august_2025": "OMF_1221_2025.pdf",
    "mof_order_1452_september_2025": "OMF_1452_2025.pdf",
    "mof_order_1795_november_2025": "OMF_1795_2025.pdf",
    "mof_order_1831_november_2025_amendment": "OMF_1831_2025.pdf",
    "mof_order_1998_december_2025_amendment": "OMF_1998_2025.pdf",
}

MF_FILENAME_CANDIDATES = {
    "mof_order_752_may_2025_amendment": [
        "OMF752_07052025.pdf",
        "OMF752mai2025.pdf",
    ],
    "mof_order_1088_july_2025": [
        "OMF1088iulie2025.pdf",
        "OMF1088_30062025.pdf",
    ],
    "mof_order_1221_august_2025": [
        "OMF1221august2025.pdf",
        "OMF1221_31072025.pdf",
    ],
    "mof_order_1452_september_2025": [
        "OMF1452septembrie2025.pdf",
        "OMF1452_29082025.pdf",
    ],
    "mof_order_1795_november_2025": [
        "OMF1795noiembrie2025.pdf",
        "OMF1795_31102025.pdf",
    ],
    "mof_order_1831_november_2025_amendment": [
        "OMF1831_10112025.pdf",
        "OMF1831noiembrie2025.pdf",
    ],
    "mof_order_1998_december_2025_amendment": [
        "OMF1998_19122025.pdf",
        "OMF1998decembrie2025.pdf",
    ],
}


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fold(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def order_number_pattern(number: str) -> re.Pattern[str]:
    digits = re.escape(number)
    if len(number) > 3:
        digits = re.escape(number[:-3]) + r"[\.\s]?" + re.escape(number[-3:])
    return re.compile(rf"\b(?:nr\.?\s*)?{digits}\b", re.IGNORECASE)


ROMANIAN_MONTHS = {
    1: "ianuarie",
    2: "februarie",
    3: "martie",
    4: "aprilie",
    5: "mai",
    6: "iunie",
    7: "iulie",
    8: "august",
    9: "septembrie",
    10: "octombrie",
    11: "noiembrie",
    12: "decembrie",
}


def romanian_date_anchor(iso_date: str) -> str:
    year, month, day = map(int, iso_date.split("-"))
    return f"{day} {ROMANIAN_MONTHS[month]} {year}"


def candidate_urls(source_id: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for url in EXACT_WEB_VERIFIED.get(source_id, []):
        out.append({"url": url, "discovery_basis": "EXACT_WEB_VERIFIED_OFFICIAL_PDF"})
    filename = ANAF_FILENAME_CANDIDATES.get(source_id)
    if filename:
        out.append(
            {
                "url": f"https://static.anaf.ro/static/10/Anaf/legislatie/{filename}",
                "discovery_basis": "ANAF_FILENAME_PATTERN_PROBE_REQUIRES_DOCUMENT_IDENTITY_PASS",
            }
        )
    for filename in MF_FILENAME_CANDIDATES.get(source_id, []):
        out.append(
            {
                "url": f"https://mfinante.gov.ro/static/10/Mfp/trezorerie/{filename}",
                "discovery_basis": "MF_FILENAME_PATTERN_PROBE_REQUIRES_DOCUMENT_IDENTITY_PASS",
            }
        )
    # Stable de-duplication.
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in out:
        if item["url"] not in seen:
            seen.add(item["url"])
            deduped.append(item)
    return deduped


def fetch(url: str) -> tuple[int, bytes, dict]:
    request = Request(
        url,
        headers={
            "Accept": "application/pdf,*/*;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/140 Safari/537.36"
            ),
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            return (
                int(response.getcode()),
                response.read(),
                {
                    "transport": "urllib",
                    "content_type": response.headers.get("Content-Type"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"),
                },
            )
    except Exception:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.bin"
            result = subprocess.run(
                [
                    "curl",
                    "--http1.1",
                    "--location",
                    "--retry", "2",
                    "--connect-timeout", "20",
                    "--max-time", "60",
                    "--silent",
                    "--show-error",
                    "--output", str(body),
                    "--write-out", "%{http_code}",
                    "--header", "Accept: application/pdf,*/*;q=0.8",
                    "--header",
                    "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            status = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            payload = body.read_bytes() if body.exists() else b""
            return (
                status,
                payload,
                {
                    "transport": "curl_http1_1",
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip(),
                },
            )


def pdftotext(payload: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "source.pdf"
        txt_path = Path(tmp) / "source.txt"
        pdf_path.write_bytes(payload)
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0 or not txt_path.exists():
            return ""
        return txt_path.read_text(encoding="utf-8", errors="replace")


def identity_checks(text: str, document: dict) -> dict[str, bool]:
    folded = fold(text)
    publication_number = document["publication_number"]
    publication_digits = re.escape(publication_number)
    if len(publication_number) > 3:
        publication_digits = (
            re.escape(publication_number[:-3])
            + r"[\.\s]?"
            + re.escape(publication_number[-3:])
        )
    checks = {
        "order_number": bool(order_number_pattern(document["order_number"]).search(text)),
        "order_date": fold(romanian_date_anchor(document["order_date"])) in folded,
        "ministry": "ministerul finantelor" in folded,
        "title_anchor": fold(document["title_anchor"]) in folded,
        "month_anchor": fold(document["month_anchor"]) in folded,
        "publication_number": bool(
            re.search(
                rf"monitorul oficial[^\n]{{0,100}}(?:nr\.?\s*)?{publication_digits}\b",
                folded,
                re.IGNORECASE,
            )
        ),
    }
    if document.get("supersedes"):
        base_number = document["supersedes"].split("/", 1)[0]
        checks["superseded_order_number"] = bool(
            order_number_pattern(base_number).search(text)
        )
    return checks


def run_probe(output: Path) -> dict:
    contract = load_contract()
    docs = {
        item["source_id"]: item
        for item in contract["documents"]
        if item["source_id"] in MISSING_SOURCE_IDS
    }
    if set(docs) != MISSING_SOURCE_IDS:
        raise RuntimeError("missing-source probe set no longer matches frozen contract")

    output.mkdir(parents=True, exist_ok=True)
    pdf_dir = output / "accepted_pdfs"
    text_dir = output / "accepted_native_text"
    pdf_dir.mkdir(exist_ok=True)
    text_dir.mkdir(exist_ok=True)

    records = []
    accepted = []
    for source_id in sorted(MISSING_SOURCE_IDS):
        document = docs[source_id]
        attempts = []
        accepted_item = None
        for candidate in candidate_urls(source_id):
            status, payload, metadata = fetch(candidate["url"])
            attempt = {
                **candidate,
                "http_status": status,
                "bytes": len(payload),
                "pdf_magic": payload.startswith(b"%PDF-"),
                "response_metadata": metadata,
            }
            if status == 200 and payload.startswith(b"%PDF-"):
                text = pdftotext(payload)
                checks = identity_checks(text, document)
                attempt["identity_checks"] = checks
                attempt["all_identity_checks_pass"] = bool(checks) and all(checks.values())
                if attempt["all_identity_checks_pass"]:
                    pdf_path = pdf_dir / f"{source_id}.pdf"
                    text_path = text_dir / f"{source_id}.txt"
                    pdf_path.write_bytes(payload)
                    text_path.write_text(text, encoding="utf-8")
                    accepted_item = {
                        "source_id": source_id,
                        "official_pdf_url": candidate["url"],
                        "discovery_basis": candidate["discovery_basis"],
                        "pdf_path": str(pdf_path.relative_to(output)),
                        "pdf_sha256": sha256_bytes(payload),
                        "pdf_bytes": len(payload),
                        "native_text_path": str(text_path.relative_to(output)),
                        "native_text_sha256": sha256_bytes(text.encode("utf-8")),
                        "identity_checks": checks,
                    }
                    accepted.append(source_id)
                    attempts.append(attempt)
                    break
            attempts.append(attempt)

        records.append(
            {
                "source_id": source_id,
                "order_number": document["order_number"],
                "month": document["month"],
                "version_role": document["version_role"],
                "accepted": accepted_item,
                "attempts": attempts,
            }
        )

    manifest = {
        "probe_id": "mof-announced-ron-primary-reference-auction-missing-source-official-pdf-probe-2026-09-20",
        "scope": sorted(MISSING_SOURCE_IDS),
        "accepted_source_ids": accepted,
        "accepted_count": len(accepted),
        "unresolved_source_ids": sorted(MISSING_SOURCE_IDS - set(accepted)),
        "unresolved_count": len(MISSING_SOURCE_IDS - set(accepted)),
        "no_model_state_changed": True,
        "no_event_materialisation": True,
        "no_canonical_promotion": True,
        "no_feedback_activation": True,
        "records": records,
    }
    (output / "probe_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    diagnostic_records = []
    for record in records:
        diagnostic_records.append(
            {
                "source_id": record["source_id"],
                "attempts": [
                    {
                        "url": attempt["url"],
                        "discovery_basis": attempt["discovery_basis"],
                        "http_status": attempt["http_status"],
                        "bytes": attempt["bytes"],
                        "pdf_magic": attempt["pdf_magic"],
                        "identity_checks": attempt.get("identity_checks"),
                        "all_identity_checks_pass": attempt.get(
                            "all_identity_checks_pass"
                        ),
                        "transport": attempt["response_metadata"].get("transport"),
                        "returncode": attempt["response_metadata"].get("returncode"),
                        "stderr": attempt["response_metadata"].get("stderr"),
                    }
                    for attempt in record["attempts"]
                ],
            }
        )
    print(
        json.dumps(
            {
                "accepted_count": manifest["accepted_count"],
                "accepted_source_ids": manifest["accepted_source_ids"],
                "unresolved_source_ids": manifest["unresolved_source_ids"],
                "no_model_state_changed": True,
                "diagnostics": diagnostic_records,
            },
            indent=2,
        )
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_missing_source_official_pdf_probe_artifact",
    )
    args = parser.parse_args()
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
