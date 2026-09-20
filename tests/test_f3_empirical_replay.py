from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.dynamics import (
    advance_empirical_replay_position,
)
from scripts.audit_f3_empirical_replay import audit_f3_empirical_replay
from scripts.generate_f3_empirical_replay import (
    AUDIT,
    BENCHMARK,
    MANIFEST,
    build_artifact,
    load,
)

ROOT = Path(__file__).resolve().parents[1]


class F3EmpiricalReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = json.loads(
            (
                ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
            ).read_text(encoding="utf-8")
        )
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "f3_empirical_replay_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.regenerated = build_artifact(
            load(AUDIT), load(MANIFEST), load(BENCHMARK)
        )

    def audit(self, artifact=None, contract=None):
        return audit_f3_empirical_replay(
            artifact or self.artifact,
            contract or self.contract,
            self.regenerated,
        )

    def test_current_replay_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_committed_replay_is_exactly_reproducible_offline(self) -> None:
        self.assertEqual(self.artifact, self.regenerated)

    def test_replay_covers_q2_to_q4_and_105_numeric_cells(self) -> None:
        self.assertEqual(
            [item["period"] for item in self.artifact["transitions"]],
            ["2025-Q2", "2025-Q3", "2025-Q4"],
        )
        numeric = [
            cell
            for transition in self.artifact["transitions"]
            for cell in transition["cells"]
            if cell["status"] == "REPLAYED"
        ]
        self.assertEqual(len(numeric), 105)

    def test_every_numeric_transition_closes_with_runtime_primitive(self) -> None:
        for transition in self.artifact["transitions"]:
            for cell in transition["cells"]:
                if cell["status"] == "NOT_APPLICABLE":
                    continue
                observed = advance_empirical_replay_position(
                    cell["opening_stock_million_RON"],
                    transaction=cell["transaction_million_RON"],
                    combined_nontransaction_change=cell[
                        "combined_nontransaction_change_million_RON"
                    ],
                )
                self.assertAlmostEqual(
                    observed, cell["closing_stock_million_RON"], places=9
                )

    def test_replay_is_not_transaction_only(self) -> None:
        other = [
            abs(cell["combined_nontransaction_change_million_RON"])
            for transition in self.artifact["transitions"]
            for cell in transition["cells"]
            if cell["status"] == "REPLAYED"
        ]
        self.assertTrue(any(value > 0.0 for value in other))

    def test_q1_is_not_backfilled(self) -> None:
        self.assertFalse(
            self.artifact["summary"]["q1_transition_replayed"]
        )
        self.assertIn(
            "2024-Q4",
            self.artifact["summary"]["q1_nonreplay_reason"],
        )

    def test_partial_replay_never_promotes_full_rmd_readiness(self) -> None:
        self.assertFalse(
            self.artifact["summary"][
                "full_RMD_empirical_state_claim_allowed"
            ]
        )
        self.assertFalse(
            self.artifact["summary"]["behavioural_closure_active"]
        )
        self.assertFalse(
            self.artifact["summary"]["feedback_activation_authorized"]
        )
        self.assertEqual(
            self.contract["scientific_status"],
            "PARTIAL_INSTRUMENT_SPECIFIC_EMPIRICAL_REPLAY",
        )

    def test_manual_identity_corruption_is_detected(self) -> None:
        mutated = copy.deepcopy(self.artifact)
        cell = next(
            cell
            for cell in mutated["transitions"][0]["cells"]
            if cell["status"] == "REPLAYED"
        )
        cell["combined_nontransaction_change_million_RON"] += 1.0
        errors = audit_f3_empirical_replay(
            mutated, self.contract, self.regenerated
        )
        self.assertTrue(
            any(
                "differs from deterministic regeneration" in error
                for error in errors
            )
        )

    def test_runtime_primitive_rejects_nonfinite_values(self) -> None:
        for kwargs in (
            dict(
                opening=math.nan,
                transaction=1.0,
                combined_nontransaction_change=0.0,
            ),
            dict(
                opening=1.0,
                transaction=math.inf,
                combined_nontransaction_change=0.0,
            ),
            dict(
                opening=1.0,
                transaction=1.0,
                combined_nontransaction_change=math.nan,
            ),
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    advance_empirical_replay_position(**kwargs)


if __name__ == "__main__":
    unittest.main()
