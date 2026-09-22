from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCIENTIFIC_JSON_ROOTS = (
    ROOT / "model",
    ROOT / "data",
)


class DuplicateKeyError(ValueError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def reject_non_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def audit_scientific_json_integrity() -> list[str]:
    errors: list[str] = []
    paths: list[Path] = []
    for base in SCIENTIFIC_JSON_ROOTS:
        paths.extend(sorted(base.rglob("*.json")))

    for path in sorted(paths):
        relative = path.relative_to(ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{relative}: invalid UTF-8: {exc}")
            continue

        try:
            json.loads(
                text,
                object_pairs_hook=reject_duplicate_keys,
                parse_constant=reject_non_json_constant,
            )
        except (json.JSONDecodeError, DuplicateKeyError, ValueError) as exc:
            errors.append(f"{relative}: {exc}")

    if not paths:
        errors.append("no scientific JSON files discovered under model/ or data/")
    return errors


def main() -> None:
    errors = audit_scientific_json_integrity()
    if errors:
        raise RuntimeError(
            "Scientific JSON integrity audit failed:\n- " + "\n- ".join(errors)
        )

    counts = {}
    total = 0
    for base in SCIENTIFIC_JSON_ROOTS:
        count = sum(1 for _ in base.rglob("*.json"))
        counts[str(base.relative_to(ROOT))] = count
        total += count

    print(
        json.dumps(
            {
                "status": "PASS",
                "scientific_json_files": total,
                "by_root": counts,
                "duplicate_object_keys": 0,
                "non_json_numeric_constants": 0,
                "invalid_utf8_or_json_syntax": 0,
                "scientific_effect": "NONE",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
