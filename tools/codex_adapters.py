#!/usr/bin/env python3
"""Static Codex adapter/drift checks. Not a runtime permission boundary."""

import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

ROOT = Path(__file__).resolve().parent.parent
HOOK_COMMAND = 'python3 "$(git rev-parse --show-toplevel)/tools/codex_policy.py"'
HOOKS = {"PreToolUse": [{"matcher": "*", "hooks": [{
    "type": "command", "command": HOOK_COMMAND, "timeout": 10,
    "statusMessage": "Checking job-search security tripwires",
}]}]}


def _same(actual, expected) -> bool:
    """Compare reviewed values without Python treating 0/1 as False/True."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same(a, e) for a, e in zip(actual, expected))
    return actual == expected


def canonical_workflows(root: Path) -> dict[str, Path]:
    workflows = {p.stem: p for p in root.glob(".claude/commands/*.md")}
    for path in root.glob(".claude/skills/*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", text, re.M)
        if match:
            workflows[match[1]] = path
    return workflows


def check(root: Path = ROOT) -> list[str]:
    errors = []
    for name in ("codex_policy.py", "codex_worker.py", "codex_runtime.py", "portal_skills.py"):
        if not (root / "tools" / name).is_file():
            errors.append(f"tools/{name}: required Codex runtime helper is missing")
    for name, canonical in canonical_workflows(root).items():
        wrapper = root / ".agents" / "skills" / name / "SKILL.md"
        label = wrapper.relative_to(root).as_posix()
        if not wrapper.is_file():
            errors.append(f"{label}: missing adapter for {canonical.relative_to(root).as_posix()}")
            continue
        text = wrapper.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{label}: missing/unterminated frontmatter")
            continue
        header, body = text[4:].split("\n---\n", 1)
        if not re.search(rf"^name: {re.escape(name)}$", header, re.M):
            errors.append(f"{label}: name must match {name}")
        if not re.search(r"^description:\s*\S", header, re.M):
            errors.append(f"{label}: missing description")
        if f"read `{canonical.relative_to(root).as_posix()}`".lower() not in body.lower():
            errors.append(f"{label}: must read the canonical workflow")
        if "`AGENTS.md`" not in body or "runtime mappings" not in body:
            errors.append(f"{label}: missing runtime mapping pointer")
        if (wrapper.parent / "cli" / "src" / "cli.ts").exists():
            errors.append(f"{label}: workflow adapter must not be a portal CLI")

    for wrapper in root.glob(".agents/skills/*/SKILL.md"):
        if (wrapper.parent / "cli/src/cli.ts").is_file():
            continue
        text = wrapper.read_text(encoding="utf-8")
        for target in re.findall(r"read `([.]claude/[^`]+[.]md)`", text, re.I):
            if not (root / target).is_file():
                errors.append(f"{wrapper.relative_to(root).as_posix()}: stale canonical pointer: {target}")

    if tomllib is None:
        return errors + ["Codex TOML checks require Python 3.11+ or `python -m pip install tomli` on Python 3.10"]

    def load(path):
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: invalid/missing TOML: {exc}")
            return {}

    config = load(root / ".codex" / "config.toml")
    # New configuration/capability keys require explicit review here as well.
    expected = {
        "approval_policy": "on-request", "sandbox_mode": "workspace-write",
        "web_search": "live", "project_doc_max_bytes": 65536,
        "sandbox_workspace_write": {"network_access": False},
        "skills": {"max_context_tokens": 10000},
        "agents": {"enabled": True, "max_concurrent_threads_per_session": 4},
        "features": {"hooks": True},
    }
    for key, value in expected.items():
        if not _same(config.get(key), value):
            errors.append(f".codex/config.toml: {key} differs from the reviewed default {value!r}")
    instruction = config.get("developer_instructions", "")
    if not isinstance(instruction, str) or not all(s in instruction for s in ("AGENTS.md", "CLAUDE.md")):
        errors.append(".codex/config.toml: developer_instructions must point to AGENTS.md and CLAUDE.md")
    extra = config.keys() - expected.keys() - {"developer_instructions"}
    if extra:
        errors.append(f".codex/config.toml: unreviewed configuration keys: {sorted(extra)}")

    hooks = root / ".codex" / "hooks.json"
    try:
        data = json.loads(hooks.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not _same(data.get("hooks"), HOOKS) or data.keys() - {"description", "hooks"}:
            errors.append(".codex/hooks.json: hooks differ from the reviewed PreToolUse policy")
    except (OSError, ValueError) as exc:
        errors.append(f".codex/hooks.json: invalid/missing hooks: {exc}")
    allowed_files = {root / ".codex" / "config.toml", hooks}
    for canonical in sorted(root.glob(".claude/agents/*.md")):
        name = canonical.stem.replace("-", "_")
        path = root / ".codex" / "agents" / f"{name}.toml"
        allowed_files.add(path)
        data = load(path)
        label = path.relative_to(root).as_posix()
        for key in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                errors.append(f"{label}: missing/non-string {key}")
        if data.get("name") != name:
            errors.append(f"{label}: agent name must be {name}")
        instructions = data.get("developer_instructions", "")
        if not isinstance(instructions, str) or canonical.relative_to(root).as_posix() not in instructions:
            errors.append(f"{label}: missing canonical agent pointer")
        features = {"apps": False, "plugins": False, "memories": False}
        if name in {"posting_scorer", "application_reviewer"}:
            features["shell_tool"] = False
        if not _same(data.get("features"), features):
            errors.append(f"{label}: capability flags differ from the reviewed defaults")
        extra = data.keys() - {"name", "description", "developer_instructions", "features"}
        if extra:
            errors.append(f"{label}: unreviewed agent keys (permissions are inherited): {sorted(extra)}")
    for path in root.glob(".codex/**/*"):
        if path.is_file() and path not in allowed_files:
            errors.append(f"{path.relative_to(root).as_posix()}: unreviewed Codex file")
    return errors


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    errors = check()
    if errors:
        print("codex_adapters: FAILED\n" + "\n".join(f"  - {e}" for e in errors))
        return 1
    print("codex_adapters: OK (workflow coverage, canonical pointers, reviewed config/agents)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
