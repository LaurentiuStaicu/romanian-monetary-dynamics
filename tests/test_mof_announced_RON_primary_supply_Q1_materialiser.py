from __future__ import annotations

import unittest

from scripts.materialise_mof_announced_RON_primary_supply_Q1_2025 import (
    BOND_ROW,
    T_BILL_ROW,
    iso_date,
    parse_article_1_totals,
    parse_ron_integer,
)


class MOFAnnouncedRONPrimarySupplyQ1MaterialiserTests(unittest.TestCase):
    def test_t_bill_row_parser(self) -> None:
        line = (
            " ROCNYYYXL9V2             13/01/2025      15/01/2025      "
            "30/06/2025         166          600,000,000"
        )
        match = T_BILL_ROW.match(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "ROCNYYYXL9V2")
        self.assertEqual(parse_ron_integer(match.group(6)), 600_000_000)

    def test_bond_row_parser(self) -> None:
        line = (
            "ROJVM8ELBDU4    09/01/2025     10/01/2025   13/01/2025   "
            "25/04/2029     5        4.28    6.30    226.97   "
            "500,000,000     75,000,000"
        )
        match = BOND_ROW.match(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "ROJVM8ELBDU4")
        self.assertEqual(parse_ron_integer(match.group(10)), 500_000_000)
        self.assertEqual(parse_ron_integer(match.group(11)), 75_000_000)

    def test_article_1_totals_parser_handles_romanian_diacritics(self) -> None:
        text = (
            "în valoare nominală totală de 7.400 milioane lei, la care se poate "
            "adăuga suma de 840 milioane lei din alocările sesiunilor"
        )
        self.assertEqual(parse_article_1_totals(text), (7400.0, 840.0))

    def test_date_and_amount_helpers(self) -> None:
        self.assertEqual(iso_date("31/03/2025"), "2025-03-31")
        self.assertEqual(parse_ron_integer("1,000,000,000"), 1_000_000_000)


if __name__ == "__main__":
    unittest.main()
