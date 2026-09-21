from __future__ import annotations

import unittest

from scripts.audit_f4_bnr_zero_liability_structural_adjudication import (
    audit_f4_bnr_zero_liability_structural_adjudication,
)


class F4BNRZeroLiabilityStructuralAdjudicationTests(unittest.TestCase):
    def test_stock_only_structural_zero_successor(self) -> None:
        self.assertEqual(audit_f4_bnr_zero_liability_structural_adjudication(), [])


if __name__ == "__main__":
    unittest.main()
