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

    def test_redisstat_identity_is_semantically_anchored_but_not_guessed(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        semantic = a["semantic_migration_anchor"]
        self.assertEqual(semantic["target_variable_code"], "UBLGBPS")
        self.assertEqual(
            semantic["retained_romania_series_key"],
            "ROM.1.0.319.0.UBLGBPS",
        )
        self.assertEqual(
            semantic["official_current_release_category"],
            "Cyclical Adjustment of Public Finance Variables",
        )
        self.assertFalse(semantic["redisstat_dataset_code_identified"])
        self.assertIsNone(semantic["redisstat_dataset_code"])
        self.assertFalse(
            semantic["chapter_number_may_be_assumed_to_equal_redisstat_dataset_code"]
        )
        self.assertFalse(
            semantic["historical_ameco17_filename_may_be_assumed_to_equal_redisstat_dataset_code"]
        )

    def test_new_official_access_paths_are_registered(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        official = a["official_current_state"]
        self.assertEqual(official["new_interface"], "ECFIN Redisstat")
        self.assertTrue(official["bulk_and_api_documentation"].startswith("https://"))
        self.assertTrue(official["redisstat_catalogue_wadl"].startswith("https://"))
        self.assertTrue(official["redisstat_sdmx_2_1_wadl"].startswith("https://"))
        self.assertEqual(
            official["redisstat_dataflow_catalogue_endpoint"],
            "https://webgate.ec.europa.eu/ecfin/redisstat/api/dissemination/sdmx/2.1/dataflow/ECFIN/all/latest?detail=allstubs",
        )
        self.assertEqual(
            official["redisstat_catalogue_toc_txt_endpoint"],
            "https://webgate.ec.europa.eu/ecfin/redisstat/api/dissemination/catalogue/toc/txt?lang=en",
        )
        self.assertIn("/explore/all/AMECO", official["redisstat_browser_ameco_root"])

    def test_legacy_ameco_workflows_are_not_future_autumn_execution_path(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        boundary = a["legacy_workflow_execution_boundary"]
        self.assertEqual(
            boundary["current_role"],
            "HISTORICAL_SPRING_2026_REPROBE_AND_REMATERIALISATION_ONLY",
        )
        self.assertFalse(boundary["legacy_workflows_may_execute_future_autumn_2026_cycle"])
        self.assertFalse(boundary["legacy_zip_contracts_may_be_relabelled_as_redisstat_contracts"])
        self.assertFalse(boundary["rerun_of_legacy_workflow_counts_as_new_vintage"])
        self.assertFalse(boundary["future_workflow_creation_authorized_now"])
        self.assertEqual(
            boundary["future_autumn_execution_path_status"],
            "NOT_YET_CREATED_BY_DESIGN",
        )

        probe = (ROOT / boundary["source_probe_workflow"]).read_text(encoding="utf-8")
        materialise = (ROOT / boundary["materialisation_workflow"]).read_text(encoding="utf-8")
        self.assertIn("HISTORICAL SPRING-2026 RE-PROBE ONLY", probe)
        self.assertIn("not the execution", probe.lower())
        self.assertIn("HISTORICAL SPRING-2026 RE-MATERIALISATION ONLY", materialise)
        self.assertIn("not evidence", materialise.lower())
        self.assertIn("future Redisstat source cycle", materialise)

        self.assertEqual(
            boundary["additional_historical_archive_workflow_role"],
            "HISTORICAL_FIXED_VINTAGE_ARCHIVE_REPROBE_AND_REMATERIALISATION_ONLY",
        )
        self.assertFalse(
            boundary["historical_archive_workflows_may_execute_future_autumn_2026_cycle"]
        )
        self.assertFalse(
            boundary["historical_archive_workflow_rerun_counts_as_new_vintage"]
        )
        self.assertFalse(
            boundary["historical_archive_workflows_may_extend_release_list_without_new_contract"]
        )

        historical_probe = (
            ROOT / boundary["historical_archive_reprobe_workflow"]
        ).read_text(encoding="utf-8")
        historical_materialise = (
            ROOT / boundary["historical_multivintage_rematerialisation_workflow"]
        ).read_text(encoding="utf-8")
        self.assertIn("HISTORICAL PRE-2022 ARCHIVE RE-PROBE ONLY", historical_probe)
        self.assertIn("not a new AMECO", historical_probe)
        self.assertIn("not a future Redisstat execution path", historical_probe)
        self.assertIn(
            "HISTORICAL 2022-SPRING-2026 ARCHIVE RE-MATERIALISATION ONLY",
            historical_materialise,
        )
        self.assertIn("not a new AMECO", historical_materialise)
        self.assertIn("future Autumn-2026 Redisstat source cycle", historical_materialise)

    def test_redisstat_discovery_endpoints_do_not_resolve_identity_by_inference(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        semantic = a["semantic_migration_anchor"]
        protocol = a["future_release_discovery_protocol"]
        self.assertFalse(semantic["redisstat_dataset_code_identified"])
        self.assertIsNone(semantic["redisstat_dataset_code"])
        self.assertEqual(
            semantic["current_discovery_status"],
            "OFFICIAL_NO_GUESS_DISCOVERY_ENDPOINTS_IDENTIFIED_DATASET_IDENTITY_NOT_YET_RETAINED",
        )
        self.assertFalse(protocol["redisstat_dataset_code_may_be_derived_from_legacy_chapter_number"])
        self.assertFalse(protocol["redisstat_dataset_code_may_be_derived_from_legacy_zip_name"])
        self.assertFalse(protocol["redisstat_dataset_code_may_be_adopted_from_third_party_mirror"])


if __name__ == "__main__":
    unittest.main()
