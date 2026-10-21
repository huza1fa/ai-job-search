import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import codex_smoke as s
from tools.codex_adapters import tomllib


class SmokeFixtureTests(unittest.TestCase):
    def test_fixture_is_synthetic_and_real_portals_disabled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = s.workspace(Path(temp), initialize_git=False)
            self.assertIn("Initial Example", (root / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertIn("alex@example.invalid", (root / "cv/main_example.tex").read_text(encoding="utf-8"))
            self.assertFalse((root / "job_search_tracker.csv").exists())
            self.assertEqual(list((root / "documents/cv").iterdir()), [])
            self.assertFalse((root / ".git").exists())
            from tools.portal_skills import discover
            portals = discover(root)
            self.assertEqual([p["name"] for p in portals if p["enabled"]], ["fixture-search"])
            self.assertTrue((root / ".claude/commands/apply.md").is_file())
            self.assertTrue((root / ".agents/skills/apply/SKILL.md").is_file())

    def test_live_model_usage_requires_explicit_opt_in(self):
        result = subprocess.run([sys.executable, str(Path(s.__file__))], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicitly pass --live", result.stderr)

    def test_fixture_generates_json_parseable_cli_data(self):
        self.assertIn("FICTIONAL", s.POSTING)
        self.assertIn("example.invalid", s.PROFILE)
        self.assertEqual(json.loads(json.dumps({"posting": s.POSTING}))["posting"], s.POSTING)

    @unittest.skipIf(tomllib is None, "Python 3.10 needs tomli (installed in CI)")
    def test_test_only_trust_maps_preserve_dots_in_literal_paths(self):
        root = Path("/private/test.with.dots/workspace")
        hook = {"key": str(root / ".codex/hooks.json") + ":pre_tool_use:0:0",
                "sourcePath": str(root / ".codex/hooks.json"), "currentHash": "fixture-hash"}
        flags = s.fixture_overrides(root, [hook])
        self.assertTrue(flags[0].startswith("projects="))
        self.assertTrue(flags[1].startswith("hooks.state="))
        self.assertEqual(tomllib.loads(flags[0])["projects"][str(root)]["trust_level"], "trusted")
        self.assertEqual(tomllib.loads(flags[1])["hooks"]["state"][hook["key"]]["trusted_hash"], "fixture-hash")


if __name__ == "__main__":
    unittest.main()
