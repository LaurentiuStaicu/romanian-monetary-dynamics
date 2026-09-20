from __future__ import annotations

import csv
import hashlib
import json
import os
import urllib.error
import urllib.request
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(
    os.environ.get(
        "FISCAL_CAPB_PRE2022_PROBE_OUT",
        "fiscal_capb_pre2022_probe_artifacts",
    )
)
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "fiscal_reaction_capb_pre2022_source_probe_contract.json"
)
USER_AGENT = (
    "romanian-monetary-dynamics/0.1.0 "
    "(+GitHub AMECO CAPB pre-2022 source-structure probe)"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, dict[str, str], int | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/zip,*/*"},
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return (
                    response.read(),
                    dict(response.headers.items()),
                    int(response.status),
                    None,
                )
        except urllib.error.HTTPError as exc:
            return exc.read(), dict(exc.headers.items()), int(exc.code), None
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                return b"", {}, None, f"{type(exc).__name__}: {exc}"
    return b"", {}, None, f"network failure: {last_error}"


def decode_line(data: bytes) -> str | None:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def iter_zip_members_recursive(
    archive_bytes: bytes,
    *,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 3,
):
    if depth > max_depth:
        raise ValueError("nested ZIP depth exceeds frozen maximum")
    archive = zipfile.ZipFile(BytesIO(archive_bytes))
    with archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            body = archive.read(info)
            path = f"{prefix}{info.filename}"
            is_zip = info.filename.casefold().endswith(".zip") or body.startswith(b"PK\x03\x04")
            if is_zip:
                if depth >= max_depth:
                    raise ValueError(f"{path}: nested ZIP exceeds frozen maximum depth")
                yield from iter_zip_members_recursive(
                    body,
                    prefix=f"{path}::",
                    depth=depth + 1,
                    max_depth=max_depth,
                )
            else:
                yield path, body


def find_target_rows(
    archive_bytes: bytes,
    target_code: str,
    *,
    max_depth: int = 3,
) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for member_path, body in iter_zip_members_recursive(
        archive_bytes, max_depth=max_depth
    ):
        for raw_line in body.splitlines(keepends=True):
            text = decode_line(raw_line)
            if text is None:
                continue
            stripped = text.rstrip("\r\n")
            try:
                fields = next(csv.reader([stripped], delimiter=";"))
            except (csv.Error, StopIteration):
                continue
            if not fields:
                continue
            if fields[0].lstrip("\ufeff").strip() != target_code:
                continue
            matches.append(
                {
                    "member_path": member_path,
                    "row_bytes": raw_line,
                    "row_sha256": sha256(raw_line),
                }
            )
    return matches


def classify_archive(
    archive_bytes: bytes,
    target_code: str,
    *,
    max_depth: int = 3,
) -> dict[str, object]:
    try:
        matches = find_target_rows(
            archive_bytes,
            target_code,
            max_depth=max_depth,
        )
    except (zipfile.BadZipFile, ValueError) as exc:
        return {
            "status": "INDETERMINATE_PROVIDER_OR_ARCHIVE_FAILURE",
            "error": str(exc),
            "matches": [],
        }

    if not matches:
        return {
            "status": "OBSERVED_TARGET_NOT_FOUND_IN_VALID_ARCHIVE",
            "error": None,
            "matches": [],
        }

    distinct = {str(item["row_sha256"]) for item in matches}
    if len(distinct) > 1:
        return {
            "status": "AMBIGUOUS_DISTINCT_TARGET_ROWS",
            "error": None,
            "matches": matches,
        }

    matches.sort(key=lambda item: str(item["member_path"]))
    return {
        "status": "TARGET_PRESENT",
        "error": None,
        "matches": matches,
        "selected": matches[0],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    target = contract["target_series"]["code"]
    max_depth = int(contract["probe_rules"]["maximum_nested_zip_depth"])
    fetched_at = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    reports: list[dict[str, object]] = []

    for release in contract["releases"]:
        body, headers, http_status, network_error = fetch(release["source_url"])
        raw_path = OUT / "raw" / f'{release["id"]}.zip'
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if body:
            raw_path.write_bytes(body)

        if network_error is not None or http_status != 200:
            report = {
                "release_id": release["id"],
                "release_label": release["label"],
                "release_date": release["release_date"],
                "source_url": release["source_url"],
                "http_status": http_status,
                "network_error": network_error,
                "status": "INDETERMINATE_PROVIDER_OR_ARCHIVE_FAILURE",
                "archive_bytes": len(body),
                "archive_sha256": sha256(body) if body else None,
                "target_code": target,
                "matching_row_count": 0,
                "distinct_matching_row_count": 0,
            }
            reports.append(report)
            continue

        classified = classify_archive(body, target, max_depth=max_depth)
        matches = classified.get("matches", [])
        distinct = {str(item["row_sha256"]) for item in matches}
        report = {
            "release_id": release["id"],
            "release_label": release["label"],
            "release_date": release["release_date"],
            "source_url": release["source_url"],
            "http_status": http_status,
            "network_error": None,
            "content_type": headers.get("Content-Type"),
            "last_modified": headers.get("Last-Modified"),
            "status": classified["status"],
            "archive_path": str(raw_path.relative_to(OUT)),
            "archive_bytes": len(body),
            "archive_sha256": sha256(body),
            "target_code": target,
            "matching_row_count": len(matches),
            "distinct_matching_row_count": len(distinct),
            "matching_member_paths": [
                str(item["member_path"]) for item in matches
            ],
            "error": classified.get("error"),
        }
        if classified["status"] == "TARGET_PRESENT":
            selected = classified["selected"]
            row_bytes = selected["row_bytes"]
            assert isinstance(row_bytes, bytes)
            row_path = OUT / "selected_rows" / f'{release["id"]}.txt'
            row_path.parent.mkdir(parents=True, exist_ok=True)
            row_path.write_bytes(row_bytes)
            report["selected_member_path"] = selected["member_path"]
            report["selected_row_path"] = str(row_path.relative_to(OUT))
            report["selected_row_sha256"] = selected["row_sha256"]
            report["selected_row_bytes"] = len(row_bytes)
        reports.append(report)

    counts: dict[str, int] = {}
    for item in reports:
        status = str(item["status"])
        counts[status] = counts.get(status, 0) + 1

    result = {
        "audit_version": "0.1",
        "phase": contract["phase"],
        "generated_at_utc": fetched_at,
        "target_code": target,
        "release_count": len(reports),
        "status_counts": counts,
        "releases": reports,
        "scientific_effect": {
            "estimation_authorized": False,
            "model_selection_authorized": False,
            "prior_final_evaluation_opening_authorized": False,
            "system_dynamics_activation": False,
            "behavioural_closure_change": False,
        },
        "next_gate": contract["next_gate"],
        "hard_rules": contract["hard_rules"],
    }
    audit_path = OUT / "fiscal_capb_pre2022_source_probe_audit.json"
    audit_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fiscal-capb-pre2022-source-probe",
        "fetched_at_utc": fetched_at,
        "probe_script": "scripts/audit_fiscal_capb_pre2022_source_probe.py",
        "probe_script_sha256": sha256(Path(__file__).resolve().read_bytes()),
        "target_series": contract["target_series"],
        "release_reports": reports,
        "audit_report": {
            "path": str(audit_path.relative_to(OUT)),
            "sha256": sha256(audit_path.read_bytes()),
        },
        "canonical_promotion": "REQUIRES_EXPLICIT_REPOSITORY_REVIEW_AND_COMMIT",
    }
    (OUT / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "CAPB_PRE2022_SOURCE_PROBE_COMPLETE",
        "release_count": len(reports),
        "status_counts": counts,
        "estimation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
