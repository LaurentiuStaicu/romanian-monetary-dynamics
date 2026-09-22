from __future__ import annotations

import json
import re
import unittest

from pathlib import Path

from scripts.audit_source_vintage_inventory import audit_source_vintage_inventory

ROOT = Path(__file__).resolve().parents[1]


class SourceVintageInventoryTests(unittest.TestCase):
    def test_every_retained_source_vintage_has_declared_provenance_anchor(self) -> None:
        self.assertEqual(audit_source_vintage_inventory(), [])

    def test_normative_esa_semantic_source_is_not_classified_as_hash_backed_manifest(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/source_vintage_inventory_registry.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(
            item for item in registry["entries"]
            if item["directory"] == "data/source_vintages/esa2010-financial-instrument-semantics-2026-09-21"
        )
        self.assertEqual(entry["anchor_type"], "NORMATIVE_SEMANTIC_MANIFEST")
        payload = json.loads((ROOT / entry["anchor"]).read_text(encoding="utf-8"))
        self.assertFalse(payload["raw_pdf_retained_in_repository"])
        self.assertFalse(payload["numeric_data_used"])

    def test_every_ordinary_local_manifest_contains_a_sha256_identity(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/source_vintage_inventory_registry.json").read_text(
                encoding="utf-8"
            )
        )
        sha256 = re.compile(r"^[0-9a-f]{64}$")
        def strings(value):
            if isinstance(value, str):
                return [value]
            if isinstance(value, list):
                return [item for part in value for item in strings(part)]
            if isinstance(value, dict):
                return [item for part in value.values() for item in strings(part)]
            return []
        for entry in registry["entries"]:
            if entry["anchor_type"] != "LOCAL_MANIFEST":
                continue
            payload = json.loads((ROOT / entry["anchor"]).read_text(encoding="utf-8"))
            self.assertTrue(any(sha256.fullmatch(value) for value in strings(payload)), entry["directory"])

    def test_inventory_gate_is_exposed_in_local_reproduction_and_ci(self) -> None:
        command = "python scripts/audit_source_vintage_inventory.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
