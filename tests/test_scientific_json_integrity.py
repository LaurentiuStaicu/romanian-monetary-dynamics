from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_scientific_json_integrity import (
    ROOT,
    audit_scientific_json_integrity,
    reject_duplicate_keys,
    reject_non_json_constant,
)


class ScientificJsonIntegrityTests(unittest.TestCase):
    def test_scientific_json_corpus_is_strict_and_unambiguous(self) -> None:
        self.assertEqual(audit_scientific_json_integrity(), [])

    def test_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reject_duplicate_keys([("a", 1), ("a", 2)])

    def test_non_json_constants_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reject_non_json_constant("NaN")

    def test_gate_is_exposed_in_readme_and_scientific_ci(self) -> None:
        command = "python scripts/audit_scientific_json_integrity.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
