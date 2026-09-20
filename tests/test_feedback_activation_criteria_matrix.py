from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_feedback_activation_criteria import (
    audit_feedback_activation_matrix,
)

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class FeedbackActivationCriteriaMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = read(
            "model/dynamics/feedback_activation_criteria_matrix.json"
        )
        self.gate = read(
            "model/dynamics/system_dynamics_conformity_gate.json"
        )
        self.feedback = read("model/dynamics/feedback_registry.json")
        self.link_registry = read(
            "model/dynamics/feedback_link_readiness_registry.json"
        )
        self.boundary = read(
            "model/dynamics/feedback_variable_boundary_registry.json"
        )
        self.delay = read("model/dynamics/delay_evidence_registry.json")
        self.mechanisms = read(
            "model/empirical_dynamics/mechanism_registry.json"
        )
        self.units = read(
            "model/empirical_dynamics/behavioural_unit_contract.json"
        )
        self.robustness = read(
            "model/empirical_dynamics/behavioural_robustness_contract.json"
        )
        self.disposition = read(
            "model/calibration_validation/validation_recovery_disposition.json"
        )
        self.accounting = read(
            "model/accounting/accounting_readiness_gate.json"
        )
        self.model = read("model/registries/model_contract.json")

    def audit(self, matrix=None):
        return audit_feedback_activation_matrix(
            matrix or self.matrix,
            self.gate,
            self.feedback,
            self.link_registry,
            self.boundary,
            self.delay,
            self.mechanisms,
            self.units,
            self.robustness,
            self.disposition,
            self.accounting,
            self.model,
        )

    def test_current_matrix_passes_audit(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_all_fourteen_gate_criteria_are_present(self) -> None:
        required = {
            key
            for key, value in self.gate["feedback_activation_gate"].items()
            if key.startswith("requires_") and value is True
        }
        self.assertEqual(len(required), 14)
        self.assertEqual(set(self.matrix["criteria_order"]), required)
        for row in self.matrix["feedbacks"]:
            self.assertEqual(set(row["criteria"]), required)

    def test_only_topology_passes_for_current_closed_candidate_loops(self) -> None:
        closed = [
            row
            for row in self.matrix["feedbacks"]
            if row["topology_status"] == "CLOSED_CANDIDATE_LOOP"
        ]
        self.assertEqual(len(closed), 4)
        for row in closed:
            with self.subTest(loop=row["loop_id"]):
                passing = {
                    key
                    for key, item in row["criteria"].items()
                    if item["status"] == "PASS"
                }
                self.assertEqual(
                    passing, {"requires_polarity_and_loop_path"}
                )
                self.assertEqual(row["passed_criteria_count"], 1)
                self.assertFalse(row["all_requirements_pass"])
                self.assertEqual(row["activation_status"], "BLOCKED")

    def test_external_fx_chain_has_no_passing_activation_criteria(self) -> None:
        row = next(
            item
            for item in self.matrix["feedbacks"]
            if item["loop_id"] == "external_fx_refinancing_loop"
        )
        self.assertEqual(row["topology_status"], "OPEN_CHAIN")
        self.assertEqual(row["passed_criteria_count"], 0)
        self.assertEqual(
            row["criteria"]["requires_polarity_and_loop_path"]["status"],
            "BLOCKED",
        )
        self.assertFalse(row["all_requirements_pass"])

    def test_partial_or_not_assessable_never_counts_as_pass(self) -> None:
        self.assertEqual(self.matrix["passing_status"], "PASS")
        self.assertTrue(self.matrix["hard_rules"]["partial_is_not_pass"])
        self.assertTrue(self.matrix["hard_rules"]["not_assessable_is_not_pass"])
        for row in self.matrix["feedbacks"]:
            non_pass = [
                item["status"]
                for item in row["criteria"].values()
                if item["status"] != "PASS"
            ]
            self.assertTrue(non_pass)
            self.assertTrue(
                all(
                    status in {"PARTIAL", "BLOCKED", "NOT_ASSESSABLE"}
                    for status in non_pass
                )
            )

    def test_target_specific_monetary_form_does_not_pass_equation_gate(self) -> None:
        row = next(
            item
            for item in self.matrix["feedbacks"]
            if item["loop_id"] == "monetary_credit_transmission_loop"
        )
        self.assertEqual(
            row["criteria"]["requires_equation"]["status"],
            "BLOCKED",
        )
        self.assertEqual(
            row["criteria"]["requires_units"]["status"],
            "BLOCKED",
        )
        self.assertEqual(
            row["criteria"]["requires_extreme_condition_test"]["status"],
            "PARTIAL",
        )

    def test_accounting_hard_constraint_is_only_partial_at_integrated_loop_level(self) -> None:
        self.assertTrue(
            self.model["dynamic_core"]["accounting_spine_is_hard_constraint"]
        )
        self.assertFalse(
            self.accounting["current_expected_state"][
                "canonical_full_2025_stock_flow_benchmark_ready"
            ]
        )
        for row in self.matrix["feedbacks"]:
            self.assertEqual(
                row["criteria"][
                    "requires_accounting_conservation_preservation"
                ]["status"],
                "PARTIAL",
            )

    def test_manual_promotion_without_source_state_change_is_detected(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        row = next(
            item
            for item in mutated["feedbacks"]
            if item["loop_id"] == "monetary_credit_transmission_loop"
        )
        row["criteria"]["requires_equation"]["status"] = "PASS"
        row["passed_criteria_count"] += 1
        errors = self.audit(mutated)
        self.assertTrue(
            any("criterion statuses are stale" in error for error in errors)
        )

    def test_missing_criterion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        del mutated["feedbacks"][0]["criteria"]["requires_validation_gate"]
        errors = self.audit(mutated)
        self.assertTrue(
            any("criterion coverage" in error for error in errors)
        )

    def test_matrix_never_authorizes_quantitative_feedback(self) -> None:
        self.assertEqual(
            self.matrix["current_summary"]["activation_ready_structures"],
            0,
        )
        self.assertEqual(
            self.matrix["current_summary"][
                "quantitatively_authorized_structures"
            ],
            0,
        )
        self.assertFalse(
            self.matrix["current_summary"]["behavioural_closure_active"]
        )
        self.assertTrue(
            all(
                row["quantitative_activation_authorized"] is False
                for row in self.matrix["feedbacks"]
            )
        )


if __name__ == "__main__":
    unittest.main()
