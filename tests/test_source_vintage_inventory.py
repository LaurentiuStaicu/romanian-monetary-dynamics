from __future__ import annotations

import unittest

from scripts.audit_source_vintage_inventory import audit_source_vintage_inventory


class SourceVintageInventoryTests(unittest.TestCase):
    def test_every_retained_source_vintage_has_declared_provenance_anchor(self) -> None:
        self.assertEqual(audit_source_vintage_inventory(), [])


if __name__ == "__main__":
    unittest.main()
