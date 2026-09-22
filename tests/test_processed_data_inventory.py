from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_processed_data_inventory import audit_processed_data_inventory

ROOT = Path(__file__).resolve().parents[1]


class ProcessedDataInventoryTests(unittest.TestCase):
    def test_every_processed_csv_has_pinned_provenance_coverage(self) -> None:
        self.assertEqual(audit_processed_data_inventory(), [])

    def test_declared_sidecars_bind_exact_processed_artifact(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/processed_data_inventory_registry.json").read_text(
                encoding="utf-8"
            )
        )
        for entry in registry["entries"]:
            sidecar = entry.get("provenance_sidecar")
            if not sidecar:
                continue
            payload = json.loads((ROOT / sidecar).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("processed_artifact"), entry["path"])

    def test_processed_inventory_gate_is_exposed_in_local_reproduction_and_ci(self) -> None:
        command = "python scripts/audit_processed_data_inventory.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
