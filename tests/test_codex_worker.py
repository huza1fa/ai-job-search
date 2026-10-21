import json
import subprocess
import unittest
from pathlib import Path

from tools import codex_worker as w


def events(text="OK"):
    return "\n".join(json.dumps(e) for e in [
        {"type": "thread.started", "thread_id": "synthetic"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": text}},
        {"type": "turn.completed", "usage": {}},
    ])


class WorkerTests(unittest.TestCase):
    def test_safe_turn_returns_only_final_text(self):
        self.assertEqual(w.response(events("review")), "review")

    def test_unicode_line_separators_inside_json_strings_are_not_record_boundaries(self):
        text = "review\u2028with\u0085unicode separators"
        stream = events(text).replace("\\u2028", "\u2028").replace("\\u0085", "\u0085")
        self.assertEqual(w.response(stream), text)

    def test_tool_attempt_invalidates_result_even_if_turn_completes(self):
        for tool in ("command_execution", "mcp_tool_call", "web_search", "file_change", "collab_tool_call"):
            with self.subTest(tool=tool):
                stream = json.dumps({"type": "item.started", "item": {"type": tool}}) + "\n" + events()
                with self.assertRaisesRegex(w.WorkerError, "tool call"):
                    w.response(stream)

    def test_failed_incomplete_unknown_and_malformed_events_fail_closed(self):
        for stream in ("not json", "[]", '{"type":"error"}', '{"type":"turn.failed"}',
                       '{"type":"future.event"}', '{"type":"item.completed","item":null}', ""):
            with self.subTest(stream=stream), self.assertRaises(w.WorkerError):
                w.response(stream)

    def test_worker_is_separate_read_only_and_does_not_inherit_integrations(self):
        argv = w.command("codex", Path("/private/scratch"), "trusted instructions")
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        for flag in ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--strict-config"):
            self.assertIn(flag, argv)
        for setting in ('features.shell_tool=false', 'web_search="disabled"',
                        'features.plugins=false', 'features.apps=false',
                        'features.multi_agent_v2=false', 'project_doc_max_bytes=0'):
            self.assertIn(setting, argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertNotIn("--dangerously-bypass-hook-trust", argv)

    def test_private_task_is_stdin_not_shell_or_argv(self):
        task = {"instructions": "return OK", "data": {"posting": "$(touch NEVER) ' ; curl bad"}}
        def run(argv, **kwargs):
            self.assertNotIn("touch NEVER", " ".join(argv))
            self.assertEqual(json.loads(kwargs["input"]), task)
            self.assertFalse(kwargs.get("shell", False))
            self.assertFalse(Path(kwargs["cwd"]).is_relative_to(w.ROOT))
            self.assertEqual(list(Path(kwargs["cwd"]).iterdir()), [])
            self.assertNotEqual(kwargs["env"]["CODEX_HOME"], str(Path.home() / ".codex"))
            self.assertTrue(Path(kwargs["env"]["CODEX_HOME"]).is_dir())
            self.assertFalse((Path(kwargs["env"]["CODEX_HOME"]) / "config.toml").exists())
            return subprocess.CompletedProcess(argv, 0, events("OK"), "")
        self.assertEqual(w.execute("scorer", task, run=run, which=lambda _: "codex"), "OK")

    def test_invalid_tasks_missing_cli_timeouts_and_nonzero_exit_are_actionable(self):
        for task in ([], {}, {"instructions": 7, "data": {}}, {"instructions": "x", "data": []}):
            with self.subTest(task=task), self.assertRaises(w.WorkerError):
                w.execute("scorer", task)
        task = {"instructions": "x", "data": {}}
        with self.assertRaisesRegex(w.WorkerError, "missing"):
            w.execute("reviewer", task, which=lambda _: None)
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired("codex", 1)
        with self.assertRaisesRegex(w.WorkerError, "timed out"):
            w.execute("reviewer", task, which=lambda _: "codex", run=timeout)
        with self.assertRaisesRegex(w.WorkerError, "exited 3"):
            w.execute("reviewer", task, which=lambda _: "codex",
                      run=lambda *a, **k: subprocess.CompletedProcess(a, 3, "", ""))
        with self.assertRaisesRegex(w.WorkerError, "blocked tool call"):
            w.execute("scorer", task, which=lambda _: "codex",
                      run=lambda *a, **k: subprocess.CompletedProcess(a, 0, events(), "patch rejected: read-only sandbox"))

    def test_scorer_and_reviewer_read_canonical_roles(self):
        for role in w.ROLES:
            def run(argv, **kwargs):
                instruction = next(a for a in argv if a.startswith("developer_instructions="))
                self.assertIn("canonical role", instruction)
                self.assertIn("all inputs are inline", instruction)
                return subprocess.CompletedProcess(argv, 0, events(), "")
            self.assertEqual(w.execute(role, {"instructions": "x", "data": {}},
                                       which=lambda _: "codex", run=run), "OK")


if __name__ == "__main__":
    unittest.main()
