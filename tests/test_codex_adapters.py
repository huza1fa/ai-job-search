"""Offline drift, discovery and prerequisite tests; no model/API calls."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import codex_adapters, doctor, portal_skills

ROOT = Path(__file__).resolve().parent.parent


class PortalDiscoveryTests(unittest.TestCase):
    def test_real_portals_only_and_enabled_flags_preserved(self):
        portals = portal_skills.discover()
        # cli.ts -> src -> cli -> skill
        expected = {p.parents[2].name for p in ROOT.glob(".agents/skills/*/cli/src/cli.ts")}
        self.assertEqual({p["name"] for p in portals}, expected)
        self.assertTrue(portals)
        self.assertFalse({"apply", "scrape", "rank", "setup"} & expected)
        for portal in portals:
            self.assertTrue((ROOT / portal["skill"]).is_file())
            self.assertTrue((ROOT / portal["cli"]).is_file())

    def test_workflow_exclusion_and_false_toggle_without_hardcoded_portal_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, toggle, cli in (("workflow", "", False), ("new-search", "enabled: false # opted out\n", True),
                                      ("default-search", "", True)):
                skill = root / ".agents" / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(f"---\nname: {name}\n{toggle}---\n", encoding="utf-8")
                if cli:
                    path = skill / "cli" / "src" / "cli.ts"
                    path.parent.mkdir(parents=True)
                    path.write_text("", encoding="utf-8")
            self.assertEqual({p["name"]: p["enabled"] for p in portal_skills.discover(root)},
                             {"new-search": False, "default-search": True})

    def test_canonical_scrape_filters_cli_directories(self):
        text = (ROOT / ".claude/skills/job-scraper/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("only directories containing `cli/src/cli.ts`", text)

    def test_disabled_detection_is_scoped_to_complete_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / ".agents/skills/example/SKILL.md"
            cli = skill.parent / "cli/src/cli.ts"
            cli.parent.mkdir(parents=True)
            cli.write_text("", encoding="utf-8")
            for header in ('description: "contains --- in text"\nenabled: false',
                           'enabled: False # opted out'):
                skill.write_text(f"---\nname: example\n{header}\n---\n", encoding="utf-8")
                self.assertFalse(portal_skills.discover(root)[0]["enabled"])
            skill.write_text("---\nname: example\n---\nenabled: false\n", encoding="utf-8")
            self.assertTrue(portal_skills.discover(root)[0]["enabled"])


@unittest.skipIf(codex_adapters.tomllib is None, "Python 3.10 needs optional tomli (installed in CI)")
class AdapterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in (".codex", ".claude/commands", ".claude/skills", ".claude/agents"):
            shutil.copytree(ROOT / name, self.root / name)
        for name in codex_adapters.canonical_workflows(ROOT):
            shutil.copytree(ROOT / ".agents/skills" / name, self.root / ".agents/skills" / name)
        (self.root / "tools").mkdir()
        for name in ("codex_policy.py", "codex_worker.py", "codex_runtime.py", "portal_skills.py"):
            shutil.copy(ROOT / "tools" / name, self.root / "tools" / name)

    def test_repository_adapters_pass(self):
        self.assertEqual(codex_adapters.check(ROOT), [])

    def test_added_upstream_command_requires_an_adapter(self):
        (self.root / ".claude/commands/new-command.md").write_text("# /new-command\n", encoding="utf-8")
        self.assertIn("missing adapter", "\n".join(codex_adapters.check(self.root)))

    def test_missing_core_skill_adapter_fails(self):
        (self.root / ".agents/skills/scrape/SKILL.md").unlink()
        self.assertIn("missing adapter", "\n".join(codex_adapters.check(self.root)))

    def test_wrong_pointer_fails(self):
        path = self.root / ".agents/skills/apply/SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace(".claude/commands/apply.md", "missing.md"), encoding="utf-8")
        self.assertIn("canonical workflow", "\n".join(codex_adapters.check(self.root)))

    def test_removed_upstream_command_cannot_leave_a_stale_wrapper(self):
        (self.root / ".claude/commands/expand.md").unlink()
        self.assertIn("stale canonical pointer", "\n".join(codex_adapters.check(self.root)))

    def test_missing_hook_script_is_a_static_failure_not_a_silent_fail_open(self):
        (self.root / "tools/codex_policy.py").unlink()
        self.assertIn("runtime helper is missing", "\n".join(codex_adapters.check(self.root)))

    def test_unsafe_config_changes_fail(self):
        path = self.root / ".codex/config.toml"
        original = path.read_text(encoding="utf-8")
        for old, new in (("workspace-write", "danger-full-access"), ('"on-request"', '"never"'),
                         ("network_access = false", "network_access = true"),
                         ("network_access = false", "network_access = 0")):
            with self.subTest(new=new):
                path.write_text(original.replace(old, new), encoding="utf-8")
                self.assertTrue(codex_adapters.check(self.root))

    def test_missing_malformed_and_wrong_shape_toml_fail_cleanly(self):
        path = self.root / ".codex/config.toml"
        path.unlink()
        self.assertIn("invalid/missing TOML", "\n".join(codex_adapters.check(self.root)))
        for content in ("not TOML !", "agents = []\n", "developer_instructions = 12\n"):
            path.write_text(content, encoding="utf-8")
            self.assertTrue(codex_adapters.check(self.root))

    def test_missing_agent_and_inherited_permission_override_rejected(self):
        path = self.root / ".codex/agents/posting_scorer.toml"
        path.unlink()
        self.assertTrue(codex_adapters.check(self.root))
        shutil.copy(ROOT / ".codex/agents/posting_scorer.toml", path)
        path.write_text('sandbox_mode = "read-only"\n' + path.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertIn("permissions are inherited", "\n".join(codex_adapters.check(self.root)))

    def test_new_hooks_need_explicit_review(self):
        (self.root / ".codex/hooks.json").write_text("{}", encoding="utf-8")
        self.assertIn("hooks differ", "\n".join(codex_adapters.check(self.root)))

    def test_upstream_agent_requires_matching_codex_role(self):
        (self.root / ".claude/agents/new-role.md").write_text("---\nname: new-role\n---\n", encoding="utf-8")
        self.assertIn("new_role.toml", "\n".join(codex_adapters.check(self.root)))

    def test_security_guard_calls_adapter_checks(self):
        # The fixture has all canonical adapter sources, but no Claude settings
        # or manifests. Isolate those unrelated checks, not the adapter check.
        from tools import security_guards
        with patch.object(security_guards, "ROOT", self.root), \
             patch.object(security_guards, "errors", []), \
             patch.object(security_guards, "check_permissions"), \
             patch.object(security_guards, "check_gitignore"), \
             patch.object(security_guards, "check_package_manifests"), \
             patch.object(security_guards, "check_tracked_node_modules"), \
             patch.object(security_guards, "check_skill_tool_grants"), \
             patch.object(security_guards, "check_agent_tool_grants"), \
             patch("builtins.print"):
            self.assertEqual(security_guards.main(), 0)
            (self.root / ".codex/hooks.json").write_text("{}", encoding="utf-8")
            self.assertEqual(security_guards.main(), 1)


class DoctorTests(unittest.TestCase):
    def inspect(self, available=(), agent="claude", runner=None):
        return doctor.inspect(agent=agent, which=lambda n: f"/bin/{n}" if n in available else None,
                              run=runner or (lambda *a, **k: subprocess.CompletedProcess(a, 0, "0.163.0", "")),
                              find_spec=lambda _: None)

    def test_missing_required_tools_fail_but_optional_tools_warn(self):
        checks = {c["name"]: c for c in self.inspect()}
        for name in ("git", "claude"):
            self.assertEqual(checks[name]["status"], "FAIL")
        for name in ("bun", "lualatex", "xelatex", "pdftotext", "pypdf"):
            self.assertEqual(checks[name]["status"], "WARN")

    def test_version_timeout_is_actionable_not_a_crash(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("claude", 10)
        checks = self.inspect(("git", "claude"), runner=timeout)
        self.assertTrue(any(c["name"] == "claude version" and c["status"] == "WARN" for c in checks))

    def test_no_network_or_install_commands_are_executed(self):
        runner = unittest.mock.Mock(return_value=subprocess.CompletedProcess([], 0, "0.163.0", ""))
        self.inspect(("git", "claude", "bun", "lualatex", "xelatex", "pdfinfo", "pdftotext"), runner=runner)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(runner.call_args.args[0], ["/bin/claude", "--version"])

    def test_missing_toml_parser_has_remediation(self):
        with patch.object(codex_adapters, "tomllib", None):
            errors = codex_adapters.check()
        self.assertIn("pip install tomli", "\n".join(errors))

    def test_cannot_claim_runtime_skill_visibility(self):
        checks = self.inspect(("git", "codex"), agent="codex")
        visibility = next(c for c in checks if c["name"] == "Runtime visibility")
        self.assertEqual(visibility["status"], "WARN")
        self.assertIn("Not introspected", visibility["detail"])

    def test_cli_json_is_parseable_from_another_directory(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/doctor.py"), "--agent", "claude", "--json"],
                                cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")
        self.assertIn(result.returncode, (0, 1))
        self.assertTrue(json.loads(result.stdout)["checks"])


if __name__ == "__main__":
    unittest.main()
