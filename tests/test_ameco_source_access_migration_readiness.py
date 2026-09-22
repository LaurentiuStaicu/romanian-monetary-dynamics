from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_ameco_source_access_migration_readiness import (
    ASSESSMENT_PATH,
    audit_ameco_source_access_migration_readiness,
)

ROOT = Path(__file__).resolve().parents[1]


class AmecoSourceAccessMigrationReadinessTests(unittest.TestCase):
    def test_current_assessment_passes(self) -> None:
        self.assertEqual(audit_ameco_source_access_migration_readiness(), [])

    def test_future_autumn_source_is_not_guessed(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertFalse(a["official_current_state"]["future_autumn_2026_exact_download_url_known"])
        self.assertFalse(a["future_release_discovery_protocol"]["source_url_guessing_authorized"])
        self.assertFalse(a["future_release_discovery_protocol"]["legacy_chapter_url_template_reuse_authorized"])
        self.assertFalse(a["trigger_adjudication"]["autumn_2026_release_trigger_satisfied"])

    def test_historical_spring_2026_url_is_provenance_not_future_template(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertEqual(
            a["historical_provenance_boundary"]["spring_2026_source_url_role"],
            "IMMUTABLE_HISTORICAL_PROVENANCE_ONLY",
        )
        self.assertFalse(
            a["historical_provenance_boundary"]["legacy_url_pattern_may_be_used_to_guess_autumn_2026_url"]
        )

    def test_new_official_access_paths_are_registered(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        official = a["official_current_state"]
        self.assertEqual(official["new_interface"], "ECFIN Redisstat")
        self.assertTrue(official["bulk_and_api_documentation"].startswith("https://"))
        self.assertTrue(official["redisstat_catalogue_wadl"].startswith("https://"))
        self.assertTrue(official["redisstat_sdmx_2_1_wadl"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
