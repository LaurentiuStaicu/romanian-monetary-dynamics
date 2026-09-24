from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"

APPROVED_EXTERNAL_ACTIONS = {
    "actions/checkout",
    "actions/setup-python",
    "actions/upload-artifact",
}
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)(?:\s+#\s*(\S+))?\s*$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_COMMENT_RE = re.compile(r"^v\d+\.\d+\.\d+$")


class ActionsDependencyPinningTests(unittest.TestCase):
    def test_external_actions_are_approved_and_pinned_to_full_sha(self) -> None:
        seen: set[str] = set()
        errors: list[str] = []

        for path in sorted(WORKFLOW_DIR.glob("*.y*ml")):
            for number, raw_line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                match = USES_RE.match(raw_line)
                if match is None:
                    continue
                reference, version_comment = match.groups()
                if reference.startswith("./"):
                    continue
                if "@" not in reference:
                    errors.append(
                        f"{path.name}:{number}: external action reference has no @ref"
                    )
                    continue
                action, ref = reference.rsplit("@", 1)
                seen.add(action)
                if action not in APPROVED_EXTERNAL_ACTIONS:
                    errors.append(
                        f"{path.name}:{number}: unapproved external action {action}"
                    )
                if not FULL_SHA_RE.fullmatch(ref):
                    errors.append(
                        f"{path.name}:{number}: action {action} is not pinned to a full SHA"
                    )
                if version_comment is None or not SEMVER_COMMENT_RE.fullmatch(
                    version_comment
                ):
                    errors.append(
                        f"{path.name}:{number}: pinned action {action} must retain a "
                        "same-line semantic-version comment for Dependabot"
                    )

        self.assertEqual(errors, [])
        self.assertEqual(seen, APPROVED_EXTERNAL_ACTIONS)

    def test_dependabot_updates_github_actions_weekly(self) -> None:
        text = DEPENDABOT.read_text(encoding="utf-8")
        for token in (
            'version: 2',
            'package-ecosystem: "github-actions"',
            'directory: "/"',
            'interval: "weekly"',
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
