#!/usr/bin/env python3
"""Discover and retain exact official legal acts for full-2025 RON supply.

This probe retains Portal Legislativ search pages and selected act pages.
It materialises no auction events and promotes no reference mode.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / (
    "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_full_2025_source_vintage_contract.json"
)
SCRIPT_PATH = Path(__file__).resolve()
PORTAL_ORIGIN = "https://legislatie.just.ro"

MONTHS_RO = {
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


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def extract_text(payload: bytes) -> str:
    parser = TextParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return "\n".join(parser.parts)


def normalized(text: str) -> str:
    text = html.unescape(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("\xa0", " ")
    return " ".join(text.split())


def romanian_date_anchor(iso_date: str) -> str:
    year, month, day = (int(part) for part in iso_date.split("-"))
    return f"{day} {MONTHS_RO[month]} {year}"


def order_number_variants(order_number: str) -> set[str]:
    plain = str(int(order_number))
    variants = {plain}
    if len(plain) > 3:
        variants.add(plain[:-3] + "." + plain[-3:])
    return variants


def act_identity_checks(text: str, document: dict) -> dict[str, bool]:
    n = normalized(text)
    number_ok = any(
        f"ordin nr. {variant}" in n or f"ordin nr {variant}" in n
        for variant in order_number_variants(document["order_number"])
    )
    return {
        "order_number": number_ok,
        "order_date": normalized(romanian_date_anchor(document["order_date"])) in n,
        "issuer": "ministerul finantelor" in n,
        "title_anchor": normalized(document["title_anchor"]) in n,
        "month_anchor": normalized(document["month_anchor"]) in n,
    }


def _curl_fetch(url: str, accept: str) -> tuple[int, bytes, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        body_path = Path(tmp) / "body.bin"
        header_path = Path(tmp) / "headers.txt"
        result = subprocess.run(
            [
                "curl",
                "--http1.1",
                "--fail-with-body",
                "--location",
                "--retry", "3",
                "--retry-delay", "2",
                "--connect-timeout", "30",
                "--max-time", "90",
                "--silent",
                "--show-error",
                "--dump-header", str(header_path),
                "--output", str(body_path),
                "--write-out", "%{http_code}",
                "--header", f"Accept: {accept}",
                "--header", "Accept-Language: ro-RO,ro;q=0.9,en;q=0.7",
                "--header", "Cache-Control: no-cache",
                "--header", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
                url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"curl transport failed for {url}: "
                f"returncode={result.returncode}; stderr={result.stderr.strip()}"
            )
        status_text = result.stdout.strip()
        if not status_text.isdigit():
            raise RuntimeError(f"curl did not return numeric HTTP status for {url}")
        status = int(status_text)
        payload = body_path.read_bytes()
        raw_headers = header_path.read_text(encoding="iso-8859-1", errors="replace")
        blocks = [block for block in raw_headers.split("\r\n\r\n") if block.strip()]
        final_headers = blocks[-1] if blocks else raw_headers
        metadata = {"transport": "curl_browser_headers"}
        for line in final_headers.splitlines()[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            lk = key.strip().casefold()
            if lk == "content-type":
                metadata["content_type"] = value.strip()
            elif lk == "last-modified":
                metadata["last_modified"] = value.strip()
            elif lk == "etag":
                metadata["etag"] = value.strip()
        return status, payload, metadata


def fetch(url: str, accept: str) -> tuple[int, bytes, dict]:
    request = Request(
        url,
        headers={
            "Accept": accept,
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.7",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 Chrome/140 Safari/537.36"
            ),
        },
    )
    try:
        with urlopen(request, timeout=90) as response:
            status = int(response.getcode())
            payload = response.read()
            metadata = {
                "transport": "urllib_browser_headers",
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }
        return status, payload, metadata
    except Exception:
        return _curl_fetch(url, accept)


def search_url(document: dict) -> str:
    date = document["publication_date"].replace("-", "/")
    query = urlencode(
        {
            "publicatinceputtext": date,
            "publicatnumar": document["publication_number"],
            "publicatsfarsittext": date,
        }
    )
    return f"{PORTAL_ORIGIN}/Public/RezultateCautare?{query}"


def candidate_links(search_payload: bytes) -> list[str]:
    parser = LinkParser()
    parser.feed(search_payload.decode("utf-8", errors="replace"))
    by_document_id: dict[str, str] = {}
    for href in parser.links:
        absolute = urljoin(PORTAL_ORIGIN, href)
        parsed = urlparse(absolute)
        if parsed.netloc.casefold() != "legislatie.just.ro":
            continue
        if "detaliidocument" not in parsed.path.casefold():
            continue
        document_id = parsed.path.rstrip("/").split("/")[-1]
        if not document_id:
            continue
        previous = by_document_id.get(document_id)
        if previous is None:
            by_document_id[document_id] = absolute
        elif "detaliidocumentafis" in previous.casefold() and "detaliidocumentafis" not in absolute.casefold():
            by_document_id[document_id] = absolute
    return list(by_document_id.values())


def discover_document(document: dict, out_dir: Path) -> dict:
    sid = document["source_id"]
    search_dir = out_dir / "search_pages"
    act_dir = out_dir / "acts"
    text_dir = out_dir / "normalized_text"
    pdf_dir = out_dir / "official_pdf_crosschecks"
    for directory in (search_dir, act_dir, text_dir, pdf_dir):
        directory.mkdir(parents=True, exist_ok=True)

    result = {
        "source_id": sid,
        "month": document["month"],
        "version_role": document["version_role"],
        "order_number": document["order_number"],
        "order_date": document["order_date"],
        "publication_number": document["publication_number"],
        "publication_date": document["publication_date"],
        "supersedes": document["supersedes"],
        "legal_registry_status": "UNAVAILABLE_FROM_GITHUB_RUNNER",
        "official_pdf_status": "NOT_CONFIGURED",
        "raw_source_retained": False,
        "event_materialisation_authorized": False,
    }

    # First try the exact official MF/ANAF PDF when the contract already freezes one.
    pdf_url = document.get("known_official_pdf_url")
    if pdf_url:
        result["official_pdf_url"] = pdf_url
        try:
            p_status, p_payload, p_meta = fetch(pdf_url, "application/pdf")
            if p_status == 200 and p_payload.startswith(b"%PDF-"):
                pdf_path = pdf_dir / f"{sid}.pdf"
                pdf_path.write_bytes(p_payload)
                result.update(
                    {
                        "official_pdf_status": "RETAINED_EXACT_OFFICIAL_PDF",
                        "official_pdf_path": f"official_pdf_crosschecks/{pdf_path.name}",
                        "official_pdf_bytes": len(p_payload),
                        "official_pdf_sha256": sha256_bytes(p_payload),
                        "official_pdf_response_metadata": p_meta,
                        "raw_source_retained": True,
                        "event_materialisation_authorized": True,
                    }
                )
            else:
                result["official_pdf_status"] = (
                    f"UNAVAILABLE_OR_NON_PDF_HTTP_{p_status}"
                )
        except Exception as exc:
            result["official_pdf_status"] = "UNAVAILABLE_FROM_GITHUB_RUNNER"
            result["official_pdf_error"] = str(exc)

    # Independently try Portal Legislativ. Failure is transport evidence, not a
    # reason to guess document IDs or substitute third-party text.
    s_url = search_url(document)
    result["search_url"] = s_url
    try:
        status, search_payload, search_meta = fetch(s_url, "text/html")
        if status == 200:
            search_path = search_dir / f"{sid}.html"
            search_path.write_bytes(search_payload)
            candidates = candidate_links(search_payload)
            matches: list[dict] = []
            attempted: list[dict] = []
            for url in candidates:
                try:
                    act_status, act_payload, act_meta = fetch(url, "text/html")
                except Exception as exc:
                    attempted.append({"url": url, "error": str(exc)})
                    continue
                text = extract_text(act_payload)
                checks = act_identity_checks(text, document)
                attempted.append(
                    {
                        "url": url,
                        "http_status": act_status,
                        "identity_checks": checks,
                    }
                )
                if act_status == 200 and all(checks.values()):
                    matches.append(
                        {
                            "url": url,
                            "payload": act_payload,
                            "metadata": act_meta,
                            "text": text,
                            "identity_checks": checks,
                        }
                    )
            result["candidate_detail_links_found"] = len(candidates)
            result["attempted_candidates"] = attempted
            if len(matches) == 1:
                selected = matches[0]
                act_path = act_dir / f"{sid}.html"
                act_path.write_bytes(selected["payload"])
                text_path = text_dir / f"{sid}.txt"
                text_path.write_text(selected["text"], encoding="utf-8")
                result.update(
                    {
                        "legal_registry_status": "RETAINED_EXACT_OFFICIAL_ACT",
                        "selected_act_url": selected["url"],
                        "selected_act_path": f"acts/{act_path.name}",
                        "selected_act_bytes": len(selected["payload"]),
                        "selected_act_sha256": sha256_bytes(selected["payload"]),
                        "selected_act_response_metadata": selected["metadata"],
                        "normalized_text_path": f"normalized_text/{text_path.name}",
                        "normalized_text_bytes": text_path.stat().st_size,
                        "normalized_text_sha256": sha256_file(text_path),
                        "identity_checks": selected["identity_checks"],
                        "all_identity_checks_pass": True,
                        "raw_source_retained": True,
                        "event_materialisation_authorized": True,
                    }
                )
            elif len(matches) == 0:
                result["legal_registry_status"] = "NO_EXACT_MATCH_FROM_SEARCH_ENDPOINT"
            else:
                result["legal_registry_status"] = "AMBIGUOUS_MULTIPLE_EXACT_MATCHES"
        else:
            result["legal_registry_status"] = f"UNAVAILABLE_HTTP_{status}"
    except Exception as exc:
        result["legal_registry_error"] = str(exc)

    if not result["raw_source_retained"]:
        result["event_materialisation_authorized"] = False

    return result


def run_probe(out_dir: Path) -> dict:
    contract = load_contract()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [discover_document(doc, out_dir) for doc in contract["documents"]]

    retained = [item for item in results if item["raw_source_retained"]]
    unavailable = [item for item in results if not item["raw_source_retained"]]
    status = (
        "PASS_ALL_OFFICIAL_SOURCES_RETAINED"
        if not unavailable
        else "PARTIAL_OFFICIAL_SOURCE_RETENTION_EXPLICIT_UNAVAILABLE_REMAINDER"
    )

    manifest = {
        "snapshot_id": "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20",
        "fetched_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "documents": results,
        "document_count": len(results),
        "base_order_count": sum(item["version_role"] == "BASE" for item in results),
        "amendment_order_count": sum(item["version_role"] == "AMENDMENT" for item in results),
        "raw_sources_retained_count": len(retained),
        "raw_sources_unavailable_count": len(unavailable),
        "retained_source_ids": [item["source_id"] for item in retained],
        "unavailable_source_ids": [item["source_id"] for item in unavailable],
        "event_rows_materialised": False,
        "canonical_reference_mode_promoted": False,
        "yield_effect_estimation_authorized": False,
        "feedback_activation_authorized": False,
        "status": status,
    }
    manifest_path = out_dir / "source_vintage_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "documents": manifest["document_count"],
                "raw_sources_retained": manifest["raw_sources_retained_count"],
                "raw_sources_unavailable": manifest["raw_sources_unavailable_count"],
                "retained_source_ids": manifest["retained_source_ids"],
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
        default="mof_announced_reference_auction_full_2025_source_artifacts",
    )
    args = parser.parse_args()
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
