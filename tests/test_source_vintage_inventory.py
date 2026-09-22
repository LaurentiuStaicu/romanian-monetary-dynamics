from __future__ import annotations

import unittest

from pathlib import Path

from scripts.audit_source_vintage_inventory import audit_source_vintage_inventory

ROOT = Path(__file__).resolve().parents[1]


class SourceVintageInventoryTests(unittest.TestCase):
    def test_every_retained_source_vintage_has_declared_provenance_anchor(self) -> None:
        self.assertEqual(audit_source_vintage_inventory(), [])

    def test_inventory_gate_is_exposed_in_local_reproduction_and_ci(self) -> None:
        command = "python scripts/audit_source_vintage_inventory.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
