from __future__ import annotations

import copy
import unittest

from scripts.probe_ecb_supply_load_denominator_candidates import load_contract


class ECBSupplyLoadDenominatorProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_three_preregistered_candidates_are_frozen(self) -> None:
        candidates = self.contract["candidates"]
        self.assertEqual(len(candidates), 3)
        self.assertEqual(
            {item["candidate_id"] for item in candidates},
            {
                "ecb_csec_central_government_domestic_currency_debt_securities_stock",
                "ecb_gfs_general_government_domestic_currency_debt_securities_face_value_stock",
                "ecb_gfs_general_government_all_currency_debt_securities_face_value_context",
            },
        )

    def test_csec_and_gfs_semantic_tradeoffs_are_explicit(self) -> None:
        items = {x["candidate_id"]: x for x in self.contract["candidates"]}
        csec = items[
            "ecb_csec_central_government_domestic_currency_debt_securities_stock"
        ]
        gfs = items[
            "ecb_gfs_general_government_domestic_currency_debt_securities_face_value_stock"
        ]
        self.assertEqual(
            csec["expected_semantics"]["reference_sector"],
            "central government excluding social security",
        )
        self.assertEqual(csec["expected_semantics"]["valuation"], "market value")
        self.assertEqual(
            gfs["expected_semantics"]["reference_sector"],
            "general government",
        )
        self.assertEqual(gfs["expected_semantics"]["valuation"], "face value")

    def test_selection_is_forbidden_in_probe(self) -> None:
        guards = self.contract["selection_guards"]
        self.assertFalse(guards["denominator_selected_in_this_probe"])
        self.assertTrue(guards["no_selection_from_fit_or_correlation"])
        self.assertTrue(guards["no_selection_from_closeness_to_ministry_value"])
        self.assertTrue(guards["semantic_boundary_before_numeric_behaviour"])
        self.assertTrue(guards["valuation_compatibility_before_numeric_behaviour"])
        self.assertFalse(
            guards["candidate_ratio_promotion_to_supply_pressure_authorized"]
        )

    def test_scientific_activation_guards_are_closed(self) -> None:
        for key, value in self.contract["scientific_guards"].items():
            self.assertFalse(value, key)

    def test_candidate_key_change_is_visible(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["candidates"][0]["series_key"] = "CHANGED"
        self.assertNotEqual(
            mutated["candidates"][0]["series_key"],
            self.contract["candidates"][0]["series_key"],
        )


if __name__ == "__main__":
    unittest.main()
