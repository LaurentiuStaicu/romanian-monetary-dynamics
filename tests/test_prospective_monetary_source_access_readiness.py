from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_prospective_monetary_source_access_readiness import (
    ASSESSMENT_PATH,
    audit_prospective_monetary_source_access_readiness,
)

ROOT = Path(__file__).resolve().parents[1]


class ProspectiveMonetarySourceAccessReadinessTests(unittest.TestCase):
    def test_current_source_access_readiness_passes(self) -> None:
        self.assertEqual(audit_prospective_monetary_source_access_readiness(), [])

    def test_future_bnr_decision_url_is_not_guessed(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        driver = a["authoritative_driver_access"]
        self.assertFalse(driver["exact_2026_10_08_decision_release_url_known"])
        self.assertFalse(driver["future_decision_url_guessing_authorized"])
        self.assertFalse(driver["media_or_social_result_substitution_authorized"])

    def test_exact_frozen_mir_series_is_pinned_semantically(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        response = a["authoritative_response_access"]
        self.assertEqual(
            response["exact_series_key"],
            "MIR.M.RO.B.A2C.A.R.A.2250.RON.N",
        )
        self.assertEqual(response["semantic_identity"]["reference_area"], "Romania")
        self.assertEqual(response["semantic_identity"]["currency"], "Romanian leu")
        self.assertEqual(response["semantic_identity"]["business_coverage"], "New business")
        self.assertFalse(response["response_value_inspection_authorized_now"])

    def test_unchanged_decision_keeps_response_closed(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertIn("keep all reserved MIR response values closed", a["event_day_protocol"]["step_3_if_zero"])
        self.assertFalse(a["disposition"]["policy_event_trigger_satisfied"])
        self.assertFalse(a["disposition"]["response_release_gate_open"])


if __name__ == "__main__":
    unittest.main()
