from __future__ import annotations

import unittest
from pathlib import Path

from scripts.audit_reference_mode_post_terminal_promotion import (
    audit_reference_mode_post_terminal_promotion,
)

ROOT = Path(__file__).resolve().parents[1]


class PostTerminalReferenceModePromotionTests(unittest.TestCase):
    def test_current_promotion_state(self):
        self.assertEqual(audit_reference_mode_post_terminal_promotion(), [])

    def test_status_qualifies_historical_9_of_10_checkpoints(self):
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn(
            "Canonical reference-mode readiness is now **10/10 observed; 0 blockers**",
            status,
        )
        for marker in (
            "At that source-topology checkpoint",
            "at that semantic-adjusted terminal checkpoint",
            "At that dissemination-precision diagnostic checkpoint",
            "At that window-stability checkpoint",
            "At this preregistered pre-execution checkpoint",
        ):
            self.assertIn(marker, status)
        for stale in (
            "The canonical state remains **9/10 reference modes ready**",
            "The result remains `PARTIAL_SERIES_AVAILABLE` and **9/10 reference modes ready**",
            "The mode remains `PARTIAL_SERIES_AVAILABLE` and 9/10 ready",
            "The canonical state remains 9/10 with `sectoral_financial_positions = PARTIAL_SERIES_AVAILABLE`",
        ):
            self.assertNotIn(stale, status)


if __name__ == "__main__":
    unittest.main()
