from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_feedback_link_readiness import (
    audit_feedback_link_readiness,
    compute_loop_readiness,
    feedback_link_keys,
)

ROOT = Path(__file__).resolve().parents[1]


class FeedbackLinkReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feedback = json.loads(
            (ROOT / "model" / "dynamics" / "feedback_registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.registry = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "feedback_link_readiness_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.boundary = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "feedback_variable_boundary_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.mechanisms = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )

    def audit(self, registry=None):
        return audit_feedback_link_readiness(
            self.feedback,
            registry or self.registry,
            self.boundary,
            self.mechanisms,
        )

    def test_current_registry_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_registry_covers_every_path_link_exactly_once(self) -> None:
        self.assertEqual(
            {item["link_key"] for item in self.registry["links"]},
            feedback_link_keys(self.feedback),
        )
        self.assertEqual(len(self.registry["links"]), 22)

    def test_missing_link_is_detected(self) -> None:
        mutated = copy.deepcopy(self.registry)
        mutated["links"] = mutated["links"][1:]
        errors = self.audit(mutated)
        self.assertTrue(
            any("feedback-link coverage mismatch" in error for error in errors)
        )

    def test_related_mechanism_does_not_make_link_exact_ready(self) -> None:
        row = next(
            item
            for item in self.registry["links"]
            if item["link_key"]
            == (
                "monetary_credit_transmission_loop|"
                "policy_rate|market_and_lending_rates"
            )
        )
        self.assertTrue(row["related_mechanisms"])
        self.assertFalse(row["exact_integrated_equation_ready"])
        self.assertEqual(
            row["readiness_status"],
            "PARTIAL_TARGET_SPECIFIC_FORM_NOT_INTEGRATED",
        )

    def test_exact_ready_requires_canonical_equation_pointer(self) -> None:
        mutated = copy.deepcopy(self.registry)
        row = mutated["links"][0]
        row["exact_integrated_equation_ready"] = True
        row["readiness_status"] = "EXACT_INTEGRATED_LINK_FORM_READY"
        row["equation_pointer"] = None
        mutated["loop_activation_readiness"] = compute_loop_readiness(
            self.feedback, mutated, self.boundary, self.mechanisms
        )
        mutated["current_summary"]["exact_integrated_link_forms_ready"] = 1
        errors = self.audit(mutated)
        self.assertTrue(
            any("exact-ready link requires equation_pointer" in e for e in errors)
        )

    def test_unknown_related_mechanism_is_detected(self) -> None:
        mutated = copy.deepcopy(self.registry)
        mutated["links"][0]["related_mechanisms"] = ["invented_mechanism"]
        errors = self.audit(mutated)
        self.assertTrue(any("unknown related mechanisms" in e for e in errors))

    def test_all_feedback_structures_remain_blocked(self) -> None:
        readiness = compute_loop_readiness(
            self.feedback, self.registry, self.boundary, self.mechanisms
        )
        self.assertTrue(readiness)
        self.assertTrue(
            all(item["activation_status"] == "BLOCKED" for item in readiness)
        )
        self.assertTrue(
            all(
                item["exact_integrated_link_forms_ready"] == 0
                for item in readiness
            )
        )

    def test_open_chain_has_explicit_closure_blocker(self) -> None:
        readiness = compute_loop_readiness(
            self.feedback, self.registry, self.boundary, self.mechanisms
        )
        external = next(
            item
            for item in readiness
            if item["loop_id"] == "external_fx_refinancing_loop"
        )
        self.assertIn("OPEN_CHAIN_NOT_CLOSED", external["blockers"])
        self.assertFalse(external["quantitative_activation_authorized"])

    def test_readiness_matrix_staleness_is_detected(self) -> None:
        mutated = copy.deepcopy(self.registry)
        mutated["loop_activation_readiness"][0]["blockers"] = []
        errors = self.audit(mutated)
        self.assertTrue(
            any("per-loop activation-readiness matrix is stale" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
