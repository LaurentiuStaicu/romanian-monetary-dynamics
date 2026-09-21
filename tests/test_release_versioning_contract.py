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
    text=(ROOT/"CITATION.cff").read_text(encoding="utf-8")
    m=re.search(rf"^{re.escape(name)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$",text,re.MULTILINE)
    if m is None:
        raise AssertionError(f"missing CITATION.cff field: {name}")
    return m.group(1).strip()

class ReleaseVersioningContractTests(unittest.TestCase):
    def setUp(self):
        self.c=load_contract()
        with (ROOT/"pyproject.toml").open("rb") as h:
            self.project=tomllib.load(h)["project"]

    def test_repository_candidate_version_is_atomic_across_metadata(self):
        current=self.c["versioning_basis"]["current_repository_version"]
        self.assertEqual(current,"0.2.0")
        self.assertEqual(current,self.project["version"])
        self.assertEqual(current,rmd.__version__)
        readme=(ROOT/"README.md").read_text(encoding="utf-8")
        badge=re.search(r"Version:\s*([0-9]+\.[0-9]+\.[0-9]+)",readme)
        self.assertIsNotNone(badge)
        self.assertEqual(current,badge.group(1))
        self.assertEqual(current,parse_citation_field("version"))

    def test_last_published_release_remains_v010_during_prepublication_gate(self):
        release=self.c["versioning_basis"]["current_public_release"]
        self.assertEqual(release["version"],"0.1.0")
        self.assertEqual(release["tag"],"v0.1.0")
        self.assertTrue(release["immutable_historical_identity"])
        changelog=(ROOT/"CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## {release['version']} - {release['release_date']}",changelog)
        notes=ROOT/"releases"/"v0.1.0.md"
        self.assertTrue(notes.is_file())
        self.assertIn("historical v0.1.0 release snapshot",notes.read_text(encoding="utf-8"))

    def test_v020_release_preparation_is_complete(self):
        basis=self.c["versioning_basis"]
        prep=basis["release_preparation"]
        self.assertEqual(prep["state"],"READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI")
        self.assertEqual(prep["candidate_version"],"0.2.0")
        self.assertEqual(prep["candidate_tag"],"v0.2.0")
        self.assertEqual(prep["intended_release_date"],"2026-09-21")
        self.assertEqual(prep["release_notes"],"releases/v0.2.0.md")
        self.assertEqual(parse_citation_field("date-released"),"2026-09-21")
        self.assertTrue((ROOT/prep["release_notes"]).is_file())
        changelog=(ROOT/"CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.2.0 - 2026-09-21",changelog)
        self.assertEqual(basis["next_public_release_candidate"],"0.2.0")
        self.assertFalse(basis["version_bump_required_now"])

    def test_atomic_repository_surface_set_is_complete(self):
        surfaces={(e["path"],e["field"]) for e in self.c["atomic_repository_surfaces"]}
        required={
            ("pyproject.toml","project.version"),
            ("src/romania_macro_financial_dynamics/__init__.py","__version__"),
            ("README.md","version badge"),
            ("CITATION.cff","version"),
            ("CITATION.cff","date-released"),
            ("CHANGELOG.md","release heading and release date"),
            ("model/registries/release_versioning_contract.json","current_public_release/current_repository_version/next_public_release_candidate"),
            ("releases/v<version>.md","versioned release notes"),
        }
        self.assertEqual(surfaces,required)

    def test_external_release_surfaces_require_tag_and_github_release(self):
        self.assertEqual({e["surface"] for e in self.c["external_release_surfaces"]},{"Git tag","GitHub Release"})

    def test_version_bump_has_no_scientific_activation_effect(self):
        self.assertTrue(all(self.c["scientific_boundary"].values()))

    def test_model_contract_registers_gated_release_preparation(self):
        model=json.loads((ROOT/"model/registries/model_contract.json").read_text(encoding="utf-8"))
        g=model["repository_governance"]
        self.assertEqual(g["current_public_release"],"0.1.0")
        self.assertEqual(g["current_repository_version"],"0.2.0")
        self.assertEqual(g["next_public_release_candidate"],"0.2.0")
        self.assertEqual(g["release_preparation_state"],"READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI")
        self.assertFalse(g["release_or_version_change_authorized"])\n        self.assertTrue(g["release_publication_authorized_by_release_readiness"])

    def test_release_checklist_is_user_visible(self):
        release_doc=(ROOT/"releases/README.md").read_text(encoding="utf-8")
        for token in ("pyproject.toml","CITATION.cff","CHANGELOG.md","releases/v<version>.md","GitHub Release","v<version>"):
            self.assertIn(token,release_doc)

if __name__=="__main__":
    unittest.main()
