from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.acquire_bnr_government_issuance_raw_source import (
    build_manifest,
    load_contract,
    sha256_bytes,
    validate_source_bytes,
)


class BNRGovernmentIssuanceRawSourceAcquisitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()
        minimum = int(self.contract["acquisition"]["minimum_bytes"])
        self.payload = b"%PDF-1.7\n" + (b"x" * minimum)

    def test_frozen_contract_keeps_scientific_boundary_closed(self) -> None:
        guards = self.contract["scientific_guards"]
        self.assertTrue(guards["raw_acquisition_only"])
        self.assertFalse(guards["canonical_reference_mode_promotion_authorized"])
        self.assertFalse(
            guards["generic_government_debt_issuance_node_resolution_authorized"]
        )
        self.assertFalse(guards["estimation_authorized"])
        self.assertFalse(guards["feedback_activation_authorized"])
        self.assertFalse(guards["behavioural_closure_authorized"])
        self.assertFalse(guards["public_version_change_authorized"])

    def test_expected_pdf_payload_passes_validation(self) -> None:
        validate_source_bytes(self.payload, "application/pdf", self.contract)

    def test_wrong_magic_is_rejected(self) -> None:
        bad = b"NOT-A-PDF" + (b"x" * len(self.payload))
        with self.assertRaisesRegex(RuntimeError, "did not return a PDF"):
            validate_source_bytes(bad, "application/pdf", self.contract)

    def test_too_small_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unexpectedly small"):
            validate_source_bytes(b"%PDF-1.7\nshort", "application/pdf", self.contract)

    def test_unexpected_content_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unexpected BNR response content type"):
            validate_source_bytes(self.payload, "text/html", self.contract)

    def test_manifest_binds_raw_hash_url_and_nonpromotion_state(self) -> None:
        manifest = build_manifest(
            payload=self.payload,
            content_type="application/pdf",
            last_modified="Sun, 20 Sep 2026 00:00:00 GMT",
            etag='"test-etag"',
            fetched_at_utc="2026-09-20T15:00:00+00:00",
            contract=self.contract,
            raw_relative_path="raw/bnr_monthly_bulletin_12_2025.pdf",
            fetcher_script_sha256="a" * 64,
        )
        raw = manifest["raw_source"]
        self.assertEqual(raw["sha256"], sha256_bytes(self.payload))
        self.assertEqual(raw["url"], self.contract["source"]["url"])
        self.assertEqual(raw["accept"], "application/pdf")
        self.assertFalse(manifest["promotion_authorized"])
        self.assertFalse(manifest["generic_government_debt_issuance_node_resolved"])
        self.assertFalse(manifest["feedback_activation_authorized"])

    def test_manual_contract_weakening_is_detectable(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["scientific_guards"]["feedback_activation_authorized"] = True
        self.assertTrue(mutated["scientific_guards"]["feedback_activation_authorized"])
        self.assertFalse(
            self.contract["scientific_guards"]["feedback_activation_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
