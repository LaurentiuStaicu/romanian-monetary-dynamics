from __future__ import annotations

import unittest

from scripts.audit_f4_structural_zero_successor_preregistration import (
    audit_f4_structural_zero_successor_preregistration,
)


class F4StructuralZeroSuccessorPreregistrationTests(unittest.TestCase):
    def test_adjudication_and_materialization_contract_are_frozen(self) -> None:
        self.assertEqual(audit_f4_structural_zero_successor_preregistration(), [])


if __name__ == "__main__":
    unittest.main()
