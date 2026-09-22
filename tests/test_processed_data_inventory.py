from __future__ import annotations

import unittest

from scripts.audit_processed_data_inventory import audit_processed_data_inventory


class ProcessedDataInventoryTests(unittest.TestCase):
    def test_every_processed_csv_has_pinned_provenance_coverage(self) -> None:
        self.assertEqual(audit_processed_data_inventory(), [])


if __name__ == "__main__":
    unittest.main()
