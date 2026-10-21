import unittest
from pathlib import Path

from tools import codex_runtime, doctor

ROOT = Path(__file__).resolve().parent.parent


class RuntimeTests(unittest.TestCase):
    def test_runtime_discovery_filters_user_skills_and_reports_hook_trust(self):
        class Client:
            def __init__(self, root):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def call(self, method, params):
                if method == "skills/list":
                    return {"data": [{"skills": [
                        {"name": "apply", "path": str(ROOT / ".agents/skills/apply/SKILL.md")},
                        {"name": "private-user-skill", "path": "/elsewhere/SKILL.md"}], "errors": []}]}
                return {"data": [{"hooks": [{"sourcePath": str(ROOT / ".codex/hooks.json"),
                        "eventName": "preToolUse", "enabled": True, "trustStatus": "untrusted"}], "errors": []}]}
        result = codex_runtime.discover(ROOT, client_factory=Client)
        self.assertEqual(result["skills"], ["apply"])
        self.assertEqual(result["policy_hooks"][0]["trust"], "untrusted")

    def test_doctor_fails_missing_runtime_skills_and_does_not_auto_trust_hooks(self):
        checks = doctor.inspect(agent="codex", runtime=True, which=lambda _: None,
                                find_spec=lambda _: None,
                                discover=lambda _: {"skills": [], "errors": [], "policy_hooks": []})
        self.assertEqual(next(c["status"] for c in checks if c["name"] == "Runtime visibility"), "FAIL")
        self.assertEqual(next(c["status"] for c in checks if c["name"] == "Policy hook trust"), "WARN")

    def test_runtime_protocol_error_is_actionable(self):
        def fail(_):
            raise codex_runtime.RuntimeErrorInfo("unsupported skills/list")
        checks = doctor.inspect(agent="codex", runtime=True, which=lambda _: None,
                                find_spec=lambda _: None, discover=fail)
        self.assertIn("unsupported skills/list", next(c["detail"] for c in checks if c["name"] == "Runtime visibility"))


if __name__ == "__main__":
    unittest.main()
