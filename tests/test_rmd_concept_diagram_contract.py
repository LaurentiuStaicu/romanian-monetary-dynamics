from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / ".github" / "rmd_concept_diagram_contract.json"
PREVIEW = ROOT / ".github" / "RMD_README_PREVIEW.md"
LIGHT = ROOT / ".github" / "readme-assets" / "rmd-concept-overview-light.svg"
DARK = ROOT / ".github" / "readme-assets" / "rmd-concept-overview-dark.svg"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def svg_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class RMDConceptDiagramContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = load(CONTRACT)
        self.preview = PREVIEW.read_text(encoding="utf-8")
        self.baseline = load(
            ROOT / "model" / "registries" / "scientific_baseline_manifest.json"
        )
        self.model = load(ROOT / "model" / "registries" / "model_contract.json")

    def test_assets_are_preview_only_and_have_light_dark_variants(self) -> None:
        self.assertEqual(self.c["contract_version"], "1.0")
        self.assertEqual(self.c["status"], "PREVIEW_ONLY_NOT_PUBLIC_README_ASSET")
        self.assertFalse(
            self.c["public_readme_boundary"]["diagram_publication_authorized"]
        )
        self.assertTrue(LIGHT.is_file())
        self.assertTrue(DARK.is_file())

    def test_svg_has_accessible_title_and_description(self) -> None:
        for path in (LIGHT, DARK):
            root = ET.fromstring(svg_text(path))
            ns = {"svg": "http://www.w3.org/2000/svg"}
            title = root.find("svg:title", ns)
            desc = root.find("svg:desc", ns)
            self.assertIsNotNone(title)
            self.assertIsNotNone(desc)
            self.assertIn("Romanian Monetary Dynamics", title.text or "")
            self.assertIn("Evidence-Triggered Baseline Hold", desc.text or "")

    def test_svg_uses_only_suite_palette_and_no_decorative_effects(self) -> None:
        allowed = set(self.c["visual_identity"]["suite_palette"])
        for path in (LIGHT, DARK):
            text = svg_text(path)
            colours = set(re.findall(r"#[0-9a-fA-F]{6}", text))
            self.assertTrue(colours.issubset(allowed), (path, colours - allowed))
            for forbidden in ("linearGradient", "radialGradient", "filter=", "drop-shadow"):
                self.assertNotIn(forbidden, text)

    def test_svg_uses_standard_font_and_legible_sizes(self) -> None:
        minimum = self.c["accessibility"]["minimum_effective_body_font_px"]
        for path in (LIGHT, DARK):
            text = svg_text(path)
            self.assertIn('font-family="Arial, Helvetica, sans-serif"', text)
            sizes = [int(x) for x in re.findall(r'font-size="(\d+)"', text)]
            self.assertTrue(sizes)
            self.assertGreaterEqual(min(sizes), minimum)

    def test_diagram_contains_boundary_and_layer_structure(self) -> None:
        text = svg_text(LIGHT)
        required = (
            "H",
            "Households + NPISH",
            "C",
            "Non-financial corps.",
            "F",
            "Financial corps.",
            "G",
            "General government",
            "BNR",
            "Central bank",
            "X",
            "Rest of world",
            "Accounting Spine",
            "Observed evidence &amp; reference modes",
            "Candidate dynamics",
            "Activation gates",
        )
        for token in required:
            self.assertIn(token, text)

    def test_diagram_status_matches_canonical_state(self) -> None:
        refs = self.baseline["canonical_state"]["reference_modes"]
        self.assertEqual((refs["ready_count"], refs["required_count"]), (9, 10))
        self.assertIn("9 / 10 required reference modes ready", svg_text(LIGHT))

        active = self.baseline["canonical_state"]["empirical_validation"][
            "activated_mechanisms_count"
        ]
        self.assertEqual(active, 0)
        self.assertIn("0 quantitatively active feedback loops", svg_text(LIGHT))

        self.assertFalse(self.model["dynamic_core"]["behavioural_closure_active"])
        self.assertIn("behavioural closure inactive", svg_text(LIGHT))

        state = self.model["scientific_stage"]["next_operational_state"]
        self.assertEqual(state, "EVIDENCE_TRIGGERED_BASELINE_HOLD")
        self.assertIn("Evidence-Triggered Baseline Hold", svg_text(LIGHT))

    def test_diagram_does_not_use_cld_polarity_or_loop_labels(self) -> None:
        for path in (LIGHT, DARK):
            text = svg_text(path)
            self.assertNotRegex(text, r">\s*[RB]\s*<")
            self.assertNotIn("polarity", text)
            self.assertNotIn("reinforcing", text)
            self.assertNotIn("balancing", text)
            self.assertNotIn("causal link", text)

    def test_preview_uses_responsive_picture_and_descriptive_alt_text(self) -> None:
        self.assertIn("<picture>", self.preview)
        self.assertIn('prefers-color-scheme: dark', self.preview)
        self.assertIn('prefers-color-scheme: light', self.preview)
        self.assertIn("rmd-concept-overview-dark.svg", self.preview)
        self.assertIn("rmd-concept-overview-light.svg", self.preview)
        self.assertIn("six institutional sectors", self.preview)
        self.assertIn("not** a causal-loop diagram", self.preview)

    def test_public_readme_still_does_not_reference_preview_diagram(self) -> None:
        public = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("rmd-concept-overview", public)


if __name__ == "__main__":
    unittest.main()
