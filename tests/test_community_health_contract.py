from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".github" / "community_health_contract.json"
CONTRIBUTING = ROOT / ".github" / "CONTRIBUTING.md"
SUPPORT = ROOT / ".github" / "SUPPORT.md"
PR_TEMPLATE = ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
BUG_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug.yml"
SCIENCE_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "scientific_issue.yml"
ISSUE_CONFIG = ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class CommunityHealthContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = load_json(CONTRACT)
        self.contributing = CONTRIBUTING.read_text(encoding="utf-8")
        self.support = SUPPORT.read_text(encoding="utf-8")
        self.pr = PR_TEMPLATE.read_text(encoding="utf-8")
        self.bug = BUG_FORM.read_text(encoding="utf-8")
        self.science = SCIENCE_FORM.read_text(encoding="utf-8")
        self.config = ISSUE_CONFIG.read_text(encoding="utf-8")
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_contract_declares_reference_implementation_and_deferred_boundaries(self) -> None:
        self.assertEqual(self.c["contract_version"], "1.0")
        self.assertEqual(
            self.c["suite_strategy"]["interim_strategy"],
            "Use RMD as the reference implementation. Keep project-specific scientific issue form local. Later centralize genuinely shared files once an account-level .github repository exists.",
        )
        self.assertEqual(
            self.c["deferred"]["code_of_conduct"]["status"],
            "PENDING_GOVERNANCE_DECISION",
        )
        self.assertEqual(
            self.c["deferred"]["security_policy"]["status"],
            "PENDING_PRIVATE_REPORTING_ROUTE",
        )
        self.assertFalse(
            self.c["suite_strategy"]["account_level_dot_github_repository_currently_observed"]
        )

    def test_all_implemented_community_files_exist(self) -> None:
        for rel in self.c["implemented_now"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_contributing_preserves_scientific_invariants(self) -> None:
        required = (
            "missing / TBD is not zero",
            "partial evidence is not canonical completion",
            "aggregate evidence is not a bilateral allocation",
            "provider/access failure is not negative scientific evidence",
            "missing bilateral positions must not be invented",
            "reserved holdout/prospective outcomes remain closed",
            "releases/README.md",
        )
        for token in required:
            self.assertIn(token, self.contributing)

    def test_pr_template_requires_scientific_effect_and_integrity_classification(self) -> None:
        required = (
            "## Scientific effect",
            "No canonical scientific-state change",
            "Canonical scientific-state change proposed",
            "Missing/TBD values were not converted to zero.",
            "No bilateral allocation was invented",
            "Provider/access failure was not treated as negative scientific evidence.",
            "No reserved holdout/prospective outcome was inspected",
            "Version metadata was not changed unless this is an authorized release change.",
        )
        for token in required:
            self.assertIn(token, self.pr)

    def test_issue_forms_have_required_github_form_keys(self) -> None:
        for name, text in (("bug", self.bug), ("scientific", self.science)):
            for key in ("name:", "description:", "body:"):
                self.assertRegex(text, rf"(?m)^{re.escape(key)}", name)
            self.assertIn("validations:", text, name)
            self.assertIn("required: true", text, name)

    def test_scientific_issue_form_separates_facts_sources_and_interpretation(self) -> None:
        required = (
            "Affected area",
            "Observed facts",
            "Sources / evidence",
            "Boundary and units",
            "Interpretation",
            "I am not treating missing/TBD values as zero.",
            "I am not inventing bilateral allocations",
            "provider/access failure as negative scientific evidence",
            "candidate behavioural relation is quantitatively active",
        )
        for token in required:
            self.assertIn(token, self.science)

    def test_bug_form_asks_for_reproducible_context(self) -> None:
        required = (
            "RMD version or commit",
            "Python version",
            "Environment",
            "Command or action",
            "Expected behaviour",
            "Actual behaviour",
            "Relevant output or traceback",
            "does not contain sensitive security-vulnerability details",
        )
        for token in required:
            self.assertIn(token, self.bug)

    def test_issue_chooser_routes_to_support(self) -> None:
        self.assertIn("blank_issues_enabled: true", self.config)
        self.assertIn(".github/SUPPORT.md", self.config)

    def test_support_does_not_request_public_security_details(self) -> None:
        self.assertIn("Do **not** include vulnerability details in a public issue.", self.support)
        self.assertIn("private reporting route", self.support)

    def test_readme_links_to_contributing_and_support(self) -> None:
        self.assertIn("[Contributing](.github/CONTRIBUTING.md)", self.readme)
        self.assertIn("[Support](.github/SUPPORT.md)", self.readme)

    def test_security_and_code_of_conduct_are_not_prematurely_claimed(self) -> None:
        self.assertFalse((ROOT / ".github" / "SECURITY.md").exists())
        self.assertFalse((ROOT / ".github" / "CODE_OF_CONDUCT.md").exists())
        self.assertFalse((ROOT / "SECURITY.md").exists())
        self.assertFalse((ROOT / "CODE_OF_CONDUCT.md").exists())

    def test_community_health_change_does_not_bump_release(self) -> None:
        release = load_json(
            ROOT / "model" / "registries" / "release_versioning_contract.json"
        )
        basis = release["versioning_basis"]
        self.assertEqual(basis["current_repository_version"], "0.1.0")
        self.assertEqual(basis["current_public_release"]["version"], "0.1.0")
        self.assertFalse(basis["version_bump_required_now"])


if __name__ == "__main__":
    unittest.main()
