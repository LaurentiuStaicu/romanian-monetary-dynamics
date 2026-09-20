from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "fiscal_capb_raw_source_preservation_contract.json"
)
SCRIPT = ROOT / "scripts" / "promote_fiscal_capb_raw_source_vintage.py"

spec = importlib.util.spec_from_file_location("capb_preserve", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FiscalCapbRawSourcePreservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_uses_reviewed_artifacts_only_and_no_refetch(self) -> None:
        self.assertTrue(
            self.c["verification_rules"]["no_live_ameco_refetch"]
        )
        self.assertTrue(
            self.c["verification_rules"]["download_exact_cross_run_artifacts_only"]
        )
        self.assertEqual(
            self.c["source_artifacts"]["pre2022"]["run_id"],
            35482485118,
        )
        self.assertEqual(
            self.c["source_artifacts"]["from2022"]["run_id"],
            35481663720,
        )

    def test_promotion_has_no_model_effect(self) -> None:
        effect = self.c["scientific_effect"]
        self.assertFalse(effect["estimation_authorized"])
        self.assertFalse(effect["model_selection_authorized"])
        self.assertFalse(effect["target_family_switch_authorized"])
        self.assertFalse(effect["prior_final_evaluation_opening_authorized"])
        self.assertFalse(effect["system_dynamics_activation"])
        self.assertFalse(effect["behavioural_closure_change"])

    def test_pre2022_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = root / "raw"
            raw.mkdir()
            payload = b"example"
            (raw / "spring_2011.zip").write_bytes(payload)
            audit = {
                "release_count": 22,
                "status_counts": self.c["source_artifacts"]["pre2022"][
                    "required_status_counts"
                ],
                "target_code": self.c["target_series"]["code"],
                "releases": [
                    {
                        "release_id": "spring_2011",
                        "release_label": "Spring 2011",
                        "release_date": "2011-05-05",
                        "source_url": "https://example.invalid/x.zip",
                        "archive_path": "raw/spring_2011.zip",
                        "archive_sha256": "0" * 64,
                        "status": "OBSERVED_TARGET_NOT_FOUND_IN_VALID_ARCHIVE",
                    }
                ],
            }
            (root / "fiscal_capb_pre2022_source_probe_audit.json").write_text(
                json.dumps(audit), encoding="utf-8"
            )
            with self.assertRaises(RuntimeError):
                module.pre2022_records(root, self.c)

    def test_post2022_inventory_hash_is_frozen(self) -> None:
        expected = self.c["source_artifacts"]["from2022"][
            "required_inventory_sha256"
        ]
        self.assertEqual(
            expected,
            "55e494ca4010ed75c602392da0fcedee02cecf1aa27aa901833b6ed8d7775588",
        )


if __name__ == "__main__":
    unittest.main()
