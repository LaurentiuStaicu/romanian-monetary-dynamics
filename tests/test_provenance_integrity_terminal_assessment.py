from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_provenance_integrity_terminal_assessment import (
    audit_provenance_integrity_terminal,
)

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceIntegrityTerminalAssessmentTests(unittest.TestCase):
    def test_terminal_provenance_state_is_internally_consistent(self) -> None:
        self.assertEqual(audit_provenance_integrity_terminal(), [])

    def test_terminal_audit_is_exposed_in_readme_and_scientific_ci(self) -> None:
        command = "python scripts/audit_provenance_integrity_terminal_assessment.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
