from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_primary_market_yield_pilot import (
    PILOT_PATH,
    audit_bnr_primary_market_yield_pilot,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class BNRPrimaryMarketYieldPilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pilot = load(PILOT_PATH)
        self.issuance = load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.feedback = load("model/dynamics/feedback_registry.json")

    def audit(self, **overrides):
        return audit_bnr_primary_market_yield_pilot(
            overrides.get("pilot", self.pilot),
            overrides.get("issuance", self.issuance),
            overrides.get("prereg", self.prereg),
            overrides.get("feedback", self.feedback),
        )

    def test_current_descriptive_pilot_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_may_and_august_preserve_native_currency_rates(self) -> None:
        may = next(r for r in self.pilot["monthly_observations"] if r["period"] == "2025-05")
        aug = next(r for r in self.pilot["monthly_observations"] if r["period"] == "2025-08")
        self.assertEqual(may["discount_treasury_certificates_RON"]["rate_pct_pa"], 8.11)
        self.assertEqual(may["treasury_certificates_EUR"]["rate_pct_pa"], 3.52)
        self.assertEqual(may["interest_bearing_government_bonds_RON"]["rate_pct_pa"], 7.64)
        self.assertEqual(may["interest_bearing_government_bonds_EUR"]["rate_pct_pa"], 3.82)
        self.assertEqual(aug["interest_bearing_government_bonds_EUR"]["rate_pct_pa"], 2.95)

    def test_not_applicable_rate_symbols_are_preserved(self) -> None:
        june = next(r for r in self.pilot["monthly_observations"] if r["period"] == "2025-06")
        december = next(r for r in self.pilot["monthly_observations"] if r["period"] == "2025-12")
        for row in (june, december):
            item = row["discount_treasury_certificates_RON"]
            self.assertEqual(item["amount"], 0)
            self.assertIsNone(item["rate_pct_pa"])
            self.assertEqual(item["source_amount_symbol"], "–")
            self.assertEqual(item["source_rate_symbol"], "x")

    def test_no_generic_sovereign_yield_is_constructed(self) -> None:
        semantics = self.pilot["semantics"]
        self.assertFalse(semantics["generic_sovereign_yield_equivalent"])
        self.assertFalse(
            self.pilot["scientific_disposition"][
                "generic_sovereign_yield_aggregate_constructed"
            ]
        )
        self.assertFalse(
            self.pilot["scientific_disposition"]["feedback_activation_authorized"]
        )

    def test_manual_rate_change_is_detected(self) -> None:
        mutated = copy.deepcopy(self.pilot)
        mutated["monthly_observations"][0][
            "discount_treasury_certificates_RON"
        ]["rate_pct_pa"] = 6.90
        errors = self.audit(pilot=mutated)
        self.assertTrue(any("reviewed source-rate values changed" in e for e in errors))

    def test_manual_cross_instrument_aggregation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.pilot)
        mutated["extraction"]["cross_instrument_rate_aggregation_performed"] = True
        errors = self.audit(pilot=mutated)
        self.assertTrue(
            any("cross_instrument_rate_aggregation_performed" in e for e in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.pilot)
        mutated["scientific_disposition"]["feedback_activation_authorized"] = True
        errors = self.audit(pilot=mutated)
        self.assertTrue(
            any("descriptive yield pilot may not promote feedback_activation_authorized" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
