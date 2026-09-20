from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path

import romania_macro_financial_dynamics as rmd

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "model" / "registries" / "release_versioning_contract.json"


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def parse_citation_field(name: str) -> str:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing CITATION.cff field: {name}")
    return match.group(1).strip()


class ReleaseVersioningContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = load_contract()
        with (ROOT / "pyproject.toml").open("rb") as handle:
            self.project = tomllib.load(handle)["project"]

    def test_current_repository_version_is_atomic_across_metadata(self) -> None:
        current = self.c["versioning_basis"]["current_repository_version"]
        self.assertEqual(current, self.project["version"])
        self.assertEqual(current, rmd.__version__)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        badge = re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)", readme)
        self.assertIsNotNone(badge)
        self.assertEqual(current, badge.group(1))
        self.assertEqual(current, parse_citation_field("version"))

    def test_current_public_release_identity_matches_citation_and_changelog(self) -> None:
        release = self.c["versioning_basis"]["current_public_release"]
        self.assertEqual(release["version"], "0.1.0")
        self.assertEqual(release["tag"], "v0.1.0")
        self.assertTrue(release["immutable_historical_identity"])
        self.assertEqual(release["release_date"], parse_citation_field("date-released"))

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(
            f"## {release['version']} - {release['release_date']}",
            changelog,
        )

    def test_unreleased_work_does_not_rewrite_v010(self) -> None:
        basis = self.c["versioning_basis"]
        self.assertTrue(basis["unreleased_changes_present"])
        self.assertFalse(basis["version_bump_required_now"])
        self.assertEqual(basis["current_public_release"]["version"], "0.1.0")
        self.assertEqual(basis["current_repository_version"], "0.1.0")
        self.assertEqual(basis["next_public_release_candidate"], "0.2.0")

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## Unreleased", changelog)

    def test_atomic_repository_surface_set_is_complete(self) -> None:
        surfaces = {
            (entry["path"], entry["field"])
            for entry in self.c["atomic_repository_surfaces"]
        }
        required = {
            ("pyproject.toml", "project.version"),
            ("src/romania_macro_financial_dynamics/__init__.py", "__version__"),
            ("README.md", "version badge"),
            ("CITATION.cff", "version"),
            ("CITATION.cff", "date-released"),
            ("CHANGELOG.md", "release heading and release date"),
            (
                "model/registries/release_versioning_contract.json",
                "current_public_release/current_repository_version/next_public_release_candidate",
            ),
            ("releases/v<version>.md", "versioned release notes"),
        }
        self.assertEqual(surfaces, required)


    def test_current_release_has_versioned_release_notes(self) -> None:
        release = self.c["versioning_basis"]["current_public_release"]
        notes = ROOT / "releases" / f"v{release['version']}.md"
        self.assertTrue(notes.is_file())
        text = notes.read_text(encoding="utf-8")
        self.assertIn(f"v{release['version']}", text)
        self.assertIn("historical v0.1.0 release snapshot", text)

    def test_external_release_surfaces_require_tag_and_github_release(self) -> None:
        surfaces = {entry["surface"] for entry in self.c["external_release_surfaces"]}
        self.assertEqual(surfaces, {"Git tag", "GitHub Release"})

    def test_version_bump_has_no_scientific_activation_effect(self) -> None:
        boundary = self.c["scientific_boundary"]
        for key, value in boundary.items():
            self.assertTrue(value, key)

    def test_model_contract_registers_versioning_contract_without_authorizing_release(self) -> None:
        model = json.loads(
            (ROOT / "model" / "registries" / "model_contract.json").read_text(
                encoding="utf-8"
            )
        )
        governance = model["repository_governance"]
        self.assertEqual(
            governance["release_versioning_contract"],
            "model/registries/release_versioning_contract.json",
        )
        self.assertEqual(governance["current_public_release"], "0.1.0")
        self.assertEqual(governance["next_public_release_candidate"], "0.2.0")
        self.assertFalse(governance["version_bump_required_now"])
        self.assertFalse(governance["release_or_version_change_authorized"])

    def test_release_checklist_is_user_visible(self) -> None:
        release_doc = (ROOT / "RELEASE.md").read_text(encoding="utf-8")
        for token in (
            "pyproject.toml",
            "CITATION.cff",
            "CHANGELOG.md",
            "releases/v<version>.md",
            "GitHub Release",
            "v<version>",
        ):
            self.assertIn(token, release_doc)


if __name__ == "__main__":
    unittest.main()
