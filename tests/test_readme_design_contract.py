from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".github" / "readme_design_contract.json"
PREVIEW = ROOT / ".github" / "RMD_README_PREVIEW.md"
PUBLIC = ROOT / "README.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RMDReadmeDesignContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(CONTRACT)
        self.preview = PREVIEW.read_text(encoding="utf-8")
        self.public = PUBLIC.read_text(encoding="utf-8")
        self.model = load(ROOT / "model" / "registries" / "model_contract.json")
        self.baseline = load(
            ROOT / "model" / "registries" / "scientific_baseline_manifest.json"
        )
        self.accounting = load(
            ROOT / "model" / "accounting" / "accounting_readiness_gate.json"
        )
        self.sd = load(
            ROOT / "model" / "dynamics" / "system_dynamics_conformity_gate.json"
        )
        self.release = load(
            ROOT / "model" / "registries" / "release_versioning_contract.json"
        )

    def test_contract_marks_public_implementation_as_proposed_not_merged(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.0")
        self.assertEqual(
            self.contract["implementation_status"],
            "PUBLIC_README_IMPLEMENTATION_PROPOSED_NOT_MERGED",
        )
        boundary = self.contract["approval_boundary"]
        self.assertTrue(boundary["public_readme_replacement_proposed"])
        self.assertFalse(boundary["public_readme_replacement_authorized_by_this_contract"])
        self.assertTrue(PREVIEW.is_file())

    def test_suite_visual_shell_is_compact_and_consistent(self) -> None:
        visual = self.contract["suite_consistency"]["shared_visual_tokens"]
        self.assertEqual(visual["icon_width_px"], 112)
        self.assertEqual(visual["badge_style"], "flat-square")
        self.assertLessEqual(visual["header_primary_badge_limit"], 3)
        self.assertEqual(
            visual["header_primary_badges_order"],
            ["release", "Scientific CI or project build health", "license"],
        )
        self.assertEqual(
            visual["palette"],
            ["#333333", "#707070", "#a0a0a0", "white", "black"],
        )

    def test_public_header_uses_three_primary_badges_and_compact_icon(self) -> None:
        header = self.public.split("---", 1)[0]
        badges = re.findall(r"<img alt=", header)
        self.assertEqual(len(badges), 3)
        self.assertIn('width="112"', header)
        self.assertIn("Scientific CI", header)
        self.assertIn("MIT License", header)
        self.assertNotIn("blue?style=", header)

    def test_public_status_matches_canonical_registries(self) -> None:
        complete = self.accounting["current_expected_state"][
            "canonical_complete_stock_and_flow_instruments"
        ]
        self.assertEqual(complete, ["F3"])
        self.assertIn("**F3 only**", self.public)

        refs = self.baseline["canonical_state"]["reference_modes"]
        self.assertEqual(refs["ready_count"], 9)
        self.assertEqual(refs["required_count"], 10)
        self.assertIn("**9 / 10 ready**", self.public)

        validated = self.baseline["canonical_state"]["empirical_validation"][
            "validated_reference_behavioural_mechanisms"
        ]
        activated = self.baseline["canonical_state"]["empirical_validation"][
            "activated_mechanisms_count"
        ]
        self.assertEqual(validated, 0)
        self.assertEqual(activated, 0)
        self.assertIn(
            "Validated reference behavioural mechanisms | **0**",
            self.public,
        )
        self.assertIn(
            "Quantitatively active feedback loops | **0**",
            self.public,
        )

        self.assertFalse(self.model["dynamic_core"]["behavioural_closure_active"])
        self.assertIn("Behavioural closure | **Inactive**", self.public)

        self.assertFalse(
            self.baseline["canonical_state"]["mechanism_readiness"][
                "calibration_cycle_open"
            ]
        )
        self.assertIn("Calibration / refit cycle | **Closed**", self.public)

        state = self.model["scientific_stage"]["next_operational_state"]
        self.assertEqual(state, "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertIn("**Evidence-Triggered Baseline Hold**", self.public)

    def test_public_accounting_maturity_matches_sd_gate(self) -> None:
        maturity = self.sd["maturity_dimensions"]["Accounting / Stock-Flow Core"]
        self.assertEqual(maturity, "PARTIAL_PASS")
        self.assertIn("Accounting / stock-flow core | **Partial pass**", self.public)

    def test_public_readme_does_not_duplicate_internal_audit_chronology(self) -> None:
        forbidden = (
            "PR #47",
            "PR #48",
            "PR #59",
            "workflow run",
            "35483550266",
            "CONSOLIDATION_COMPLETE_HUMAN_REVIEW_DECISION_PENDING",
        )
        for token in forbidden:
            self.assertNotIn(token, self.public)

    def test_public_readme_exposes_required_reader_routes(self) -> None:
        required = (
            "### What is RMD?",
            "### Model at a glance",
            "### How RMD is structured",
            "### Scientific status at a glance",
            "### Reproduce the scientific baseline",
            "### Data and provenance",
            "### Repository map",
            "### Where should I start?",
            "### Documentation",
            "### Support, citation and license",
        )
        for heading in required:
            self.assertIn(heading, self.public)

    def test_public_readme_preserves_paradigm_boundary(self) -> None:
        self.assertIn(
            "not yet a complete endogenous System Dynamics model",
            self.public,
        )
        self.assertIn("behavioural closure is inactive", self.public)
        self.assertIn("None is quantitatively active", self.public)
        self.assertIn("missing / TBD is not zero", self.public)

    def test_public_readme_exposes_release_state_without_bumping_version(self) -> None:
        basis = self.release["versioning_basis"]
        self.assertEqual(basis["current_public_release"]["version"], "0.1.0")
        self.assertEqual(basis["next_public_release_candidate"], "0.2.0")
        self.assertFalse(basis["version_bump_required_now"])
        self.assertIn("**v0.1.0**", self.public)
        self.assertIn("**v0.2.0**", self.public)

    def test_public_readme_uses_promoted_concept_assets(self) -> None:
        self.assertIn("assets/readme/rmd-concept-overview-light.svg", self.public)
        self.assertIn("assets/readme/rmd-concept-overview-dark.svg", self.public)
        self.assertTrue(
            (ROOT / "assets" / "readme" / "rmd-concept-overview-light.svg").is_file()
        )
        self.assertTrue(
            (ROOT / "assets" / "readme" / "rmd-concept-overview-dark.svg").is_file()
        )

    def test_public_local_links_resolve(self) -> None:
        targets = set(re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.public))
        targets.update(re.findall(r'(?:href|src|srcset)="([^"]+)"', self.public))

        unresolved: list[str] = []
        for target in targets:
            if (
                target.startswith(("http://", "https://", "#", "mailto:"))
                or "img.shields.io" in target
            ):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            candidate = ROOT / clean
            if not candidate.exists():
                unresolved.append(target)

        self.assertEqual(unresolved, [])

    def test_preview_remains_as_review_history_but_public_readme_is_root_adapted(self) -> None:
        self.assertNotEqual(self.public, self.preview)
        self.assertIn('src="assets/icon.png"', self.public)
        self.assertIn('src="../assets/icon.png"', self.preview)


if __name__ == "__main__":
    unittest.main()
