from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".github" / "readme_design_contract.json"
PREVIEW = ROOT / ".github" / "RMD_README_PREVIEW.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RMDReadmeDesignContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(CONTRACT)
        self.preview = PREVIEW.read_text(encoding="utf-8")
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

    def test_contract_is_preview_only_until_public_review(self) -> None:
        self.assertEqual(self.contract["contract_version"], "1.0")
        self.assertEqual(
            self.contract["implementation_status"],
            "DESIGN_AND_PREVIEW_ONLY_PUBLIC_README_NOT_YET_REPLACED",
        )
        self.assertFalse(
            self.contract["approval_boundary"]["public_readme_replacement_authorized_by_this_contract"]
        )
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

    def test_preview_uses_only_three_primary_header_badges(self) -> None:
        header = self.preview.split("---", 1)[0]
        badges = re.findall(r"<img alt=", header)
        self.assertEqual(len(badges), 3)
        self.assertIn("width=\"112\"", header)
        self.assertIn("Scientific CI", header)
        self.assertIn("MIT License", header)

    def test_preview_status_matches_canonical_registries(self) -> None:
        complete = self.accounting["current_expected_state"][
            "canonical_complete_stock_and_flow_instruments"
        ]
        self.assertEqual(complete, ["F3"])
        self.assertIn("**F3 only**", self.preview)

        refs = self.baseline["canonical_state"]["reference_modes"]
        self.assertEqual(refs["ready_count"], 9)
        self.assertEqual(refs["required_count"], 10)
        self.assertIn("**9 / 10 ready**", self.preview)

        validated = self.baseline["canonical_state"]["empirical_validation"][
            "validated_reference_behavioural_mechanisms"
        ]
        activated = self.baseline["canonical_state"]["empirical_validation"][
            "activated_mechanisms_count"
        ]
        self.assertEqual(validated, 0)
        self.assertEqual(activated, 0)
        self.assertIn("Validated reference behavioural mechanisms | **0**", self.preview)
        self.assertIn("Quantitatively active feedback loops | **0**", self.preview)

        self.assertFalse(self.model["dynamic_core"]["behavioural_closure_active"])
        self.assertIn("Behavioural closure | **Inactive**", self.preview)

        self.assertFalse(
            self.baseline["canonical_state"]["mechanism_readiness"][
                "calibration_cycle_open"
            ]
        )
        self.assertIn("Calibration / refit cycle | **Closed**", self.preview)

        state = self.model["scientific_stage"]["next_operational_state"]
        self.assertEqual(state, "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertIn("**Evidence-Triggered Baseline Hold**", self.preview)

    def test_preview_accounting_maturity_matches_sd_gate(self) -> None:
        maturity = self.sd["maturity_dimensions"]["Accounting / Stock-Flow Core"]
        self.assertEqual(maturity, "PARTIAL_PASS")
        self.assertIn("Accounting / stock-flow core | **Partial pass**", self.preview)

    def test_preview_does_not_duplicate_internal_audit_chronology(self) -> None:
        forbidden = (
            "PR #47",
            "PR #48",
            "PR #59",
            "workflow run",
            "35483550266",
            "CONSOLIDATION_COMPLETE_HUMAN_REVIEW_DECISION_PENDING",
        )
        for token in forbidden:
            self.assertNotIn(token, self.preview)

    def test_preview_exposes_required_reader_routes(self) -> None:
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
            self.assertIn(heading, self.preview)

    def test_preview_preserves_paradigm_boundary(self) -> None:
        self.assertIn(
            "not yet a complete endogenous System Dynamics model",
            self.preview,
        )
        self.assertIn("behavioural closure is inactive", self.preview)
        self.assertIn("None is quantitatively active", self.preview)
        self.assertIn("missing / TBD is not zero", self.preview)

    def test_current_public_readme_is_not_silently_replaced_on_design_branch(self) -> None:
        public = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotEqual(public, self.preview)
        self.assertIn("width=\"180\"", public)


if __name__ == "__main__":
    unittest.main()
