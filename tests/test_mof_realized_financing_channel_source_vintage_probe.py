from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.probe_mof_realized_financing_channel_source_vintage import (
    GOVERNING_CONTRACT,
    PROBE_CONTRACT,
    extract_cumulative_ytd,
    identity_checks,
    load_json,
    parse_ro_number,
)

ROOT = Path(__file__).resolve().parents[1]


class MOFRealizedFinancingChannelSourceVintageProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.probe = load_json(PROBE_CONTRACT)
        self.governing = load_json(GOVERNING_CONTRACT)
        base = (
            ROOT
            / "data/source_vintages/mof-supply-pressure-probe-vintage-2026-09-20/"
            "native_text"
        )
        self.jan_text = (base / "mof_public_debt_report_january_2025.txt").read_text(
            encoding="utf-8"
        )
        self.feb_text = (base / "mof_public_debt_report_february_2025.txt").read_text(
            encoding="utf-8"
        )

    def test_romanian_number_parser(self) -> None:
        self.assertEqual(parse_ro_number("1.307,7"), 1307.7)
        self.assertEqual(parse_ro_number("19.903,0"), 19903.0)
        self.assertEqual(parse_ro_number("0,0"), 0.0)

    def test_existing_january_identity_passes(self) -> None:
        checks = identity_checks(self.jan_text, "2025-01")
        self.assertTrue(all(checks.values()), checks)

    def test_existing_february_identity_passes(self) -> None:
        checks = identity_checks(self.feb_text, "2025-02")
        self.assertTrue(all(checks.values()), checks)

    def test_january_exact_cumulative_values_match_contract(self) -> None:
        extracted = extract_cumulative_ytd(self.jan_text)
        values = extracted["values"]
        frozen = self.governing["pilot_exact_values"]["2025-01"]
        for key in (
            "mof_t_bills",
            "retail_bonds",
            "ron_treasury_bonds",
            "eur_treasury_bonds",
            "eurobonds",
            "loans",
            "central_government_total",
        ):
            self.assertEqual(values[key], frozen[key])
        self.assertEqual(values["domestic_market_total"], 9359.3)
        self.assertEqual(values["external_market_total"], 43.4)
        self.assertEqual(values["local_government_borrowing"], 158.4)
        self.assertEqual(values["cash_management_instruments"], 600.0)
        self.assertFalse(extracted["monthly_increment_computed"])
        self.assertTrue(extracted["exchange_operations_note_present"])

    def test_february_exact_cumulative_values_match_contract(self) -> None:
        extracted = extract_cumulative_ytd(self.feb_text)
        values = extracted["values"]
        frozen = self.governing["pilot_exact_values"]["2025-02"]
        for key in (
            "mof_t_bills",
            "retail_bonds",
            "ron_treasury_bonds",
            "eur_treasury_bonds",
            "eurobonds",
            "loans",
            "central_government_total",
        ):
            self.assertEqual(values[key], frozen[key])
        self.assertEqual(values["domestic_market_total"], 28656.9)
        self.assertEqual(values["external_market_total"], 22637.6)
        self.assertEqual(values["local_government_borrowing"], 217.4)
        self.assertEqual(values["cash_management_instruments"], 1400.0)
        self.assertFalse(extracted["monthly_increment_computed"])
        self.assertTrue(extracted["exchange_operations_note_present"])

    def test_probe_has_two_reused_and_ten_identity_gated_candidates(self) -> None:
        strategy = self.probe["source_strategy"]
        self.assertEqual(len(strategy["existing_retained_sources"]), 2)
        self.assertEqual(len(strategy["official_url_candidates"]), 10)
        self.assertTrue(strategy["pattern_candidate_is_not_source_until_identity_passes"])
        self.assertFalse(strategy["non_official_domain_authorized"])

    def test_probe_cannot_compute_monthly_increments_or_activate_feedback(self) -> None:
        scope = self.probe["extraction_scope"]
        self.assertFalse(scope["monthly_increment_computation"])
        self.assertFalse(scope["channel_residual_computation"])
        self.assertFalse(scope["allocation_share_estimation"])
        guards = self.probe["scientific_guards"]
        self.assertFalse(guards["monthly_differencing_authorized"])
        self.assertFalse(guards["cross_currency_reaggregation_by_RMD_authorized"])
        self.assertFalse(guards["synthetic_channel_shares_authorized"])
        self.assertFalse(guards["generic_debt_issuance_node_promotion_authorized"])
        self.assertFalse(guards["feedback_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
