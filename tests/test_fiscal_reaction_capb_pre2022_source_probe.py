from __future__ import annotations

import importlib.util
import io
import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "fiscal_reaction_capb_pre2022_source_probe_contract.json"
)
SCRIPT = ROOT / "scripts" / "audit_fiscal_capb_pre2022_source_probe.py"

spec = importlib.util.spec_from_file_location("capb_pre2022_probe", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


class FiscalReactionCapbPre2022SourceProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.c = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.target = self.c["target_series"]["code"]

    def test_contract_has_exact_spring_autumn_2011_2021_boundary(self) -> None:
        releases = self.c["releases"]
        self.assertEqual(len(releases), 22)
        self.assertEqual(releases[0]["id"], "spring_2011")
        self.assertEqual(releases[-1]["id"], "autumn_2021")
        self.assertTrue(all(item["source_url"].startswith("https://") for item in releases))
        years = {int(item["release_date"][:4]) for item in releases}
        self.assertEqual(years, set(range(2011, 2022)))

    def test_probe_is_source_only_and_manual(self) -> None:
        h = self.c["hard_rules"]
        self.assertTrue(h["no_parameter_estimation"])
        self.assertTrue(h["no_model_selection"])
        self.assertTrue(h["no_value_transform"])
        self.assertTrue(h["no_old_holdout_reuse"])
        self.assertTrue(h["live_provider_work_manual_only"])
        self.assertTrue(
            self.c["sample_size_guard"][
                "no_weaker_validation_design_merely_to_fit_short_sample"
            ]
        )

    def test_exact_target_is_present_when_one_distinct_row_exists(self) -> None:
        row = f"{self.target};Romania;x;y;z;1\n".encode()
        archive = make_zip({"AMECO17.TXT": row})
        result = module.classify_archive(archive, self.target)
        self.assertEqual(result["status"], "TARGET_PRESENT")

    def test_byte_identical_duplicates_are_not_ambiguous(self) -> None:
        row = f"{self.target};Romania;x;y;z;1\n".encode()
        archive = make_zip({"a.txt": row, "b.txt": row})
        result = module.classify_archive(archive, self.target)
        self.assertEqual(result["status"], "TARGET_PRESENT")
        self.assertEqual(len(result["matches"]), 2)

    def test_distinct_duplicates_are_ambiguous(self) -> None:
        archive = make_zip({
            "a.txt": f"{self.target};Romania;x;y;z;1\n".encode(),
            "b.txt": f"{self.target};Romania;x;y;z;2\n".encode(),
        })
        result = module.classify_archive(archive, self.target)
        self.assertEqual(result["status"], "AMBIGUOUS_DISTINCT_TARGET_ROWS")

    def test_valid_archive_without_target_is_observed_negative(self) -> None:
        archive = make_zip({"a.txt": b"OTHER;Romania;x;y;z;1\n"})
        result = module.classify_archive(archive, self.target)
        self.assertEqual(
            result["status"],
            "OBSERVED_TARGET_NOT_FOUND_IN_VALID_ARCHIVE",
        )

    def test_bad_zip_is_indeterminate_not_negative(self) -> None:
        result = module.classify_archive(b"not-a-zip", self.target)
        self.assertEqual(
            result["status"],
            "INDETERMINATE_PROVIDER_OR_ARCHIVE_FAILURE",
        )


if __name__ == "__main__":
    unittest.main()
