#!/usr/bin/env python3
"""Probe 2025 Ministry monthly public-debt reports for realized financing.

Retains exact official PDFs/native text and extracts provider-published
cumulative-YTD values only. No month-to-month differencing is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PROBE_CONTRACT = ROOT / (
    "model/dynamics/"
    "mof_realized_financing_channel_source_vintage_probe_contract_2026_09_21.json"
)
GOVERNING_CONTRACT = ROOT / (
    "model/dynamics/"
    "mof_realized_financing_channel_materialisation_contract_2026_09_21.json"
)
SCRIPT_PATH = Path(__file__).resolve()

MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def parse_ro_number(raw: str) -> float:
    value = raw.strip().replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def extract_native_text(pdf_path: Path, text_path: Path) -> None:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(text_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed for {pdf_path.name}: {result.stderr.strip()}"
        )
    if not text_path.exists() or text_path.stat().st_size == 0:
        raise RuntimeError(f"empty native text for {pdf_path.name}")


def fetch_pdf(url: str) -> tuple[int, bytes, dict]:
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
        with urlopen(request, timeout=90) as response:
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
    except Exception as first_exc:
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.bin"
            result = subprocess.run(
                [
                    "curl", "--http1.1", "--location", "--retry", "2",
                    "--connect-timeout", "20", "--max-time", "90",
                    "--silent", "--show-error",
                    "--output", str(body), "--write-out", "%{http_code}",
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
                    "transport": "curl_http1_1_after_urllib_failure",
                    "urllib_error": str(first_exc),
                    "curl_returncode": result.returncode,
                    "curl_stderr": result.stderr.strip(),
                },
            )


def actual_borrowing_section(text: str) -> str:
    match = re.search(r"-\s*Actual borrowing as of", text, re.IGNORECASE)
    if not match:
        raise ValueError("Actual borrowing section start not found")
    start = match.start()
    end_match = re.search(r"\n\s*II\.\s*Public debt stock", text[start:], re.IGNORECASE)
    end = start + end_match.start() if end_match else min(len(text), start + 9000)
    return text[start:end]


def first_number_after(section: str, pattern: str, field: str) -> float:
    match = re.search(pattern + r"\s+([0-9][0-9\.]*,[0-9]+)", section, re.IGNORECASE)
    if not match:
        raise ValueError(f"required field not extractable: {field}")
    return parse_ro_number(match.group(1))


def extract_cumulative_ytd(text: str) -> dict:
    section = actual_borrowing_section(text)

    values = {
        "total_reimbursable_financing": first_number_after(
            section, r"Total reimbursable financing", "total_reimbursable_financing"
        ),
        "mof_t_bills": first_number_after(
            section, r"T-Bills\s*\(LEI and EUR\)", "mof_t_bills"
        ),
        "retail_bonds": first_number_after(
            section, r"Retail bonds in LEI and EUR", "retail_bonds"
        ),
        "ron_treasury_bonds": first_number_after(
            section, r"T-Bonds denominated in LEI\*?\*?\)?", "ron_treasury_bonds"
        ),
        "eur_treasury_bonds": first_number_after(
            section, r"T-Bonds denominated in EUR\*?", "eur_treasury_bonds"
        ),
        "eurobonds": first_number_after(
            section, r"Eurobonds\*?", "eurobonds"
        ),
        "rrf_pnrr_loan_drawings": first_number_after(
            section,
            r"Drawings from\s+(?:RRNP|RRF|PNRR).*?loan component",
            "rrf_pnrr_loan_drawings",
        ),
        "loans": first_number_after(section, r"Loans\*", "loans"),
        "central_government_total": first_number_after(
            section, r"\n\s*total", "central_government_total"
        ),
        "local_government_borrowing": first_number_after(
            section, r"b\)\s*Local governments", "local_government_borrowing"
        ),
    }

    cash_match = re.search(
        r"Treasury certificates issued for cash management\s*\n"
        r"purpose, due in the year of issuances and not repaid\s+"
        r"([0-9][0-9\.]*,[0-9]+)",
        section,
        re.IGNORECASE,
    )
    if not cash_match:
        raise ValueError("required field not extractable: cash_management_instruments")
    values["cash_management_instruments"] = parse_ro_number(cash_match.group(1))

    domestic = re.search(
        r"Domestic\s+([0-9][0-9\.]*,[0-9]+)", section, re.IGNORECASE
    )
    external = re.search(
        r"External\s+([0-9][0-9\.]*,[0-9]+)", section, re.IGNORECASE
    )
    if not domestic or not external:
        raise ValueError("domestic/external market totals not extractable")
    values["domestic_market_total"] = parse_ro_number(domestic.group(1))
    values["external_market_total"] = parse_ro_number(external.group(1))

    fx_note = re.search(
        r"\*Average exchange rates.*?(?=\n\*\*|\n\s*\f|\n\s*II\.)",
        section,
        re.IGNORECASE | re.DOTALL,
    )
    exchange_note = re.search(
        r"\*\*\)\s*includes exchange operations",
        section,
        re.IGNORECASE,
    )

    return {
        "unit": "million_RON_equivalent_as_published",
        "values": values,
        "provider_fx_conversion_note": (
            " ".join(fx_note.group(0).split()) if fx_note else None
        ),
        "exchange_operations_note_present": bool(exchange_note),
        "monthly_increment_computed": False,
    }


def identity_checks(text: str, period: str) -> dict[str, bool]:
    month = MONTH_NAMES[period[-2:]]
    f = fold(text)
    return {
        "monthly_report": "monthly report" in f,
        "period_month_year": fold(f"{month} 2025") in f,
        "institution": (
            "ministry of finance" in f
            or "ministerul finantelor" in f
            or (
                "public debt according to national legislation" in f
                and "a)mof" in f
            )
        ),
        "actual_borrowing_section": "actual borrowing as of" in f,
        "total_reimbursable_financing": "total reimbursable financing" in f,
        "mof_t_bills": "t-bills" in f and "mof" in f,
        "retail_bonds": "retail bonds" in f,
        "by_instrument": "by instrument" in f,
    }


def retain_existing(item: dict, out_dir: Path) -> dict:
    raw_src = ROOT / item["raw_path"]
    text_src = ROOT / item["native_text_path"]
    if not raw_src.exists() or not text_src.exists():
        raise RuntimeError(f"missing existing retained source for {item['report_period']}")

    raw_dir = out_dir / "raw"
    text_dir = out_dir / "native_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    raw_dst = raw_dir / f"{item['source_id']}.pdf"
    text_dst = text_dir / f"{item['source_id']}.txt"
    shutil.copyfile(raw_src, raw_dst)
    shutil.copyfile(text_src, text_dst)

    text = text_dst.read_text(encoding="utf-8", errors="replace")
    checks = identity_checks(text, item["report_period"])
    extracted = extract_cumulative_ytd(text)

    return {
        "report_period": item["report_period"],
        "source_id": item["source_id"],
        "discovery_basis": item["role"],
        "source_available": True,
        "raw_path": f"raw/{raw_dst.name}",
        "raw_bytes": raw_dst.stat().st_size,
        "raw_sha256": sha256_file(raw_dst),
        "native_text_path": f"native_text/{text_dst.name}",
        "native_text_bytes": text_dst.stat().st_size,
        "native_text_sha256": sha256_file(text_dst),
        "identity_checks": checks,
        "all_identity_checks_pass": all(checks.values()),
        "cumulative_ytd": extracted,
    }


def probe_candidate(item: dict, out_dir: Path) -> dict:
    status, payload, metadata = fetch_pdf(item["url"])
    result = {
        "report_period": item["report_period"],
        "source_id": item["source_id"],
        "url": item["url"],
        "discovery_basis": item["discovery_basis"],
        "http_status": status,
        "response_metadata": metadata,
        "response_bytes": len(payload),
        "pdf_magic": payload.startswith(b"%PDF-"),
        "source_available": False,
    }
    if status != 200 or not payload.startswith(b"%PDF-"):
        result["disposition"] = "UNAVAILABLE_OR_NON_PDF"
        return result

    raw_dir = out_dir / "raw"
    text_dir = out_dir / "native_text"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    temp_pdf = raw_dir / f".{item['source_id']}.candidate.pdf"
    temp_txt = text_dir / f".{item['source_id']}.candidate.txt"
    temp_pdf.write_bytes(payload)
    try:
        extract_native_text(temp_pdf, temp_txt)
        text = temp_txt.read_text(encoding="utf-8", errors="replace")
        checks = identity_checks(text, item["report_period"])
        result["identity_checks"] = checks
        result["all_identity_checks_pass"] = all(checks.values())
        if not result["all_identity_checks_pass"]:
            result["disposition"] = "PDF_IDENTITY_CHECK_FAILED"
            return result
        try:
            extracted = extract_cumulative_ytd(text)
        except ValueError as exc:
            result["disposition"] = "IDENTITY_PASS_CUMULATIVE_EXTRACTION_BLOCKED"
            result["extraction_error"] = str(exc)
            return result

        raw_dst = raw_dir / f"{item['source_id']}.pdf"
        text_dst = text_dir / f"{item['source_id']}.txt"
        temp_pdf.replace(raw_dst)
        temp_txt.replace(text_dst)
        result.update(
            {
                "source_available": True,
                "disposition": "PASS_EXACT_OFFICIAL_PDF_NATIVE_TEXT_AND_CUMULATIVE_YTD",
                "raw_path": f"raw/{raw_dst.name}",
                "raw_bytes": raw_dst.stat().st_size,
                "raw_sha256": sha256_file(raw_dst),
                "native_text_path": f"native_text/{text_dst.name}",
                "native_text_bytes": text_dst.stat().st_size,
                "native_text_sha256": sha256_file(text_dst),
                "cumulative_ytd": extracted,
            }
        )
        return result
    finally:
        temp_pdf.unlink(missing_ok=True)
        temp_txt.unlink(missing_ok=True)


def run_probe(out_dir: Path) -> dict:
    probe = load_json(PROBE_CONTRACT)
    governing = load_json(GOVERNING_CONTRACT)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for item in probe["source_strategy"]["existing_retained_sources"]:
        results.append(retain_existing(item, out_dir))
    for item in probe["source_strategy"]["official_url_candidates"]:
        results.append(probe_candidate(item, out_dir))

    available = [x for x in results if x["source_available"]]
    unavailable = [x for x in results if not x["source_available"]]

    manifest = {
        "snapshot_id": "mof-realized-financing-channels-2025-vintage-2026-09-21",
        "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "probe_contract": str(PROBE_CONTRACT.relative_to(ROOT)),
        "governing_contract": str(GOVERNING_CONTRACT.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "reports": results,
        "available_report_count": len(available),
        "unavailable_report_count": len(unavailable),
        "available_periods": [x["report_period"] for x in available],
        "unavailable_periods": [x["report_period"] for x in unavailable],
        "monthly_increment_computed": False,
        "channel_residual_computed": False,
        "allocation_share_estimated": False,
        "generic_debt_issuance_node_promoted": False,
        "feedback_activation_authorized": False,
        "status": (
            "PASS_FULL_2025_EXACT_CUMULATIVE_YTD_SOURCE_VINTAGE"
            if len(available) == 12
            else "PARTIAL_EXACT_CUMULATIVE_YTD_SOURCE_VINTAGE"
        ),
    }
    (out_dir / "source_vintage_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": manifest["status"],
        "available_report_count": manifest["available_report_count"],
        "available_periods": manifest["available_periods"],
        "unavailable_periods": manifest["unavailable_periods"],
        "monthly_increment_computed": False,
        "feedback_activation_authorized": False,
    }, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_realized_financing_channel_source_probe_artifacts",
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
