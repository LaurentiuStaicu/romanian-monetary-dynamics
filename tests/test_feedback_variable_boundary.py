from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_feedback_variable_boundary import (
    audit_feedback_variable_boundary,
    feedback_nodes,
)

ROOT = Path(__file__).resolve().parents[1]


class FeedbackVariableBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.feedback = json.loads(
            (ROOT / "model" / "dynamics" / "feedback_registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.boundary = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "feedback_variable_boundary_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.references = json.loads(
            (ROOT / "model" / "dynamics" / "reference_modes.json").read_text(
                encoding="utf-8"
            )
        )
        self.mechanisms = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.model = json.loads(
            (ROOT / "model" / "registries" / "model_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def audit(self, boundary=None, feedback=None, references=None, mechanisms=None, model=None):
        return audit_feedback_variable_boundary(
            feedback or self.feedback,
            boundary or self.boundary,
            references or self.references,
            mechanisms or self.mechanisms,
            model or self.model,
        )

    def test_current_boundary_registry_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_registry_covers_exactly_every_feedback_node(self) -> None:
        registered = {item["id"] for item in self.boundary["variables"]}
        self.assertEqual(registered, feedback_nodes(self.feedback))

    def test_missing_feedback_node_is_detected(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        mutated["variables"] = [
            item for item in mutated["variables"] if item["id"] != "risk_premium"
        ]
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("feedback-node coverage mismatch" in error for error in errors)
        )

    def test_topology_alone_cannot_make_node_endogenous(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        item = next(
            entry
            for entry in mutated["variables"]
            if entry["id"] == "credit_supply_capacity"
        )
        item["current_boundary_class"] = "ENDOGENOUS"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any(
                error.startswith("credit_supply_capacity: current ENDOGENOUS")
                for error in errors
            )
        )

    def test_observed_target_cannot_silently_become_forcing(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        item = next(
            entry
            for entry in mutated["variables"]
            if entry["id"] == "credit_flow"
        )
        item["current_boundary_class"] = "OBSERVED_FORCING"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any(
                error.startswith(
                    "credit_flow: OBSERVED_FORCING reference mode has"
                )
                for error in errors
            )
        )

    def test_policy_rate_forcing_requires_deferred_policy_rule(self) -> None:
        mutated = copy.deepcopy(self.mechanisms)
        rule = next(
            item
            for item in mutated["mechanisms"]
            if item["id"] == "monetary_policy_reaction_function"
        )
        rule["classification"] = "CANDIDATE"
        errors = self.audit(mechanisms=mutated)
        self.assertTrue(
            any(
                "policy_rate forcing assumption requires" in error
                for error in errors
            )
        )

    def test_open_chain_cannot_gain_inferred_closing_link(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        item = next(
            entry
            for entry in mutated["variables"]
            if entry["id"] == "exchange_rate_pressure"
        )
        item["closing_link"] = "exchange_rate_depreciation"
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any(
                "may not invent an open-chain closing link" in error
                for error in errors
            )
        )

    def test_boundary_registry_never_authorizes_feedback_activation(self) -> None:
        mutated = copy.deepcopy(self.boundary)
        mutated["variables"][0]["current_feedback_activation_authorized"] = True
        errors = self.audit(boundary=mutated)
        self.assertTrue(
            any("current feedback activation must remain unauthorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
