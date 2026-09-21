from __future__ import annotations

import csv
import io
import json
import unittest
from pathlib import Path

from scripts.audit_oecd_sectoral_financial_positions_nonconsolidated_probe import (
    build_country_key, household_coverage, inspect_dimension_rows,
)

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_probe_contract_2026_09_21.json"

class OecdNonconsolidatedTopologyProbeTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_discovery_only(self):
        self.assertFalse(self.c["formal_reference_mode_gate"])
        self.assertFalse(self.c["topology_gate"]["numeric_observation_values_may_be_reviewed"])
        self.assertTrue(self.c["hard_rules"]["no_reference_mode_promotion"])
        self.assertTrue(self.c["hard_rules"]["no_accounting_reopen"])

    def test_frozen_dataflows_are_nonconsolidated_quarterly_pairs(self):
        refs={x["flow_ref"] for x in self.c["provider"]["dataflows"]}
        self.assertEqual(refs,{
            "OECD.SDD.NAD,DSD_NASEC20@DF_T620R_Q",
            "OECD.SDD.NAD,DSD_NASEC20@DF_T720R_Q",
        })

    def test_s121_and_f2_f8_are_required(self):
        gate=self.c["topology_gate"]
        self.assertIn("S121",gate["required_reporting_sector_codes"])
        self.assertEqual(gate["required_instrument_codes"],["F2","F3","F4","F5","F6","F7","F8"])

    def test_country_key_is_dimension_order_derived(self):
        order=["FREQ","ADJUSTMENT","REF_AREA","SECTOR","ACCOUNTING_ENTRY"]
        self.assertEqual(build_country_key(order,reference_area="ROU",frequency="Q"),"Q..ROU..")

    def test_household_coverage_accepts_s1m_or_exact_components(self):
        self.assertEqual(household_coverage({"S1M"}),"PASS_S1M")
        self.assertEqual(household_coverage({"S14","S15"}),"PASS_EXACT_S14_PLUS_S15_COMPONENTS")
        self.assertEqual(household_coverage({"S14"}),"FAIL")

    def test_dimension_inspection_never_reads_obs_value(self):
        text="REF_AREA,SECTOR,INSTR_ASSET,ACCOUNTING_ENTRY,TIME_PERIOD,OBS_VALUE\nROU,S121,F2,A,2025-Q1,12345\n"
        out=inspect_dimension_rows(text.encode(),["REF_AREA","SECTOR","INSTR_ASSET","ACCOUNTING_ENTRY"])
        self.assertFalse(out["numeric_observation_value_review_performed"])
        self.assertNotIn("OBS_VALUE",out["dimension_code_sets"])
        self.assertEqual(out["dimension_code_sets"]["SECTOR"],["S121"])

if __name__=="__main__":
    unittest.main()
