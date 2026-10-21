#!/usr/bin/env python3
"""Codex PreToolUse tripwires. Not a shell parser or a complete sandbox.

No network, writes, transcript reads or credential reads. Unexpected/malformed
hook input produces a documented deny response rather than a fail-open crash.
"""

import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTECTED = (
    ".claude/settings.json", ".claude/settings.local.json", ".claude/commands",
    ".claude/agents", ".codex", ".github", "AGENTS.md", "tools", "salary_lookup.py",
)
CREDENTIAL = re.compile(r"(?:^|[/\\\s\"'])\.env(?:[.\s/\\\"']|$)|(?:~|\$HOME|\$\{HOME\}|/home/[^/\s]+|/Users/[^/\s]+)[/\\]\.(?:ssh|aws|gnupg)(?:[/\\\s\"']|$)")
REMOTE = {"ssh", "scp", "sftp", "nc", "ncat", "netcat", "socat", "rsync"}


def shell_headers(command: str) -> str:
    """Keep shell syntax, omit literal quoted-heredoc data before shlex.

    This is not an interpreter parser. Unquoted heredocs (which can expand
    commands) are deliberately not stripped. Credential tripwires still scan
    the original complete input before this function is called.
    """
    result, delimiter, strip_tabs = [], None, False
    for line in command.split("\n"):
        if delimiter is not None:
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                delimiter = None
            continue
        result.append(line)
        matches = list(re.finditer(r"<<(-?)[ \t]*(['\"])([A-Za-z_][A-Za-z0-9_]*)\2", line))
        if len(matches) == 1:
            delimiter, strip_tabs = matches[0][3], bool(matches[0][1])
    if delimiter is not None:
        raise ValueError("unterminated quoted heredoc")
    return "\n".join(result)


def protected(path: str, cwd: Path) -> bool:
    target = (cwd / path).resolve()
    try:
        name = target.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    return (any(name == p or name.startswith(p + "/") for p in PROTECTED)
            or bool(re.fullmatch(r"\.claude/skills/[^/]+/SKILL\.md", name))
            or bool(re.fullmatch(r"\.agents/skills/[^/]+/SKILL\.md", name)))


def reason(event: dict) -> str | None:
    if not isinstance(event, dict) or event.get("hook_event_name") != "PreToolUse":
        return "Malformed or unsupported policy event"
    name = event.get("tool_name")
    data = event.get("tool_input")
    if not isinstance(name, str) or not isinstance(data, dict):
        return "Malformed policy tool input"
    cwd = event.get("cwd")
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return "Missing absolute tool working directory"
    serialized = json.dumps(data, ensure_ascii=False)
    if CREDENTIAL.search(serialized.replace("\\\\", "/")):
        return "Credential-store access is blocked"
    if name in {"apply_patch", "Edit", "Write"}:
        patch = data.get("command", data.get("patch", data.get("input")))
        paths = []
        if isinstance(patch, str):
            paths = re.findall(r"^\*\*\* (?:Add File|Update File|Delete File|Move to): (.+)$", patch, re.M)
        elif isinstance(data.get("file_path"), str):
            paths = [data["file_path"]]
        if not paths:
            return "Unrecognized edit format; cannot verify permission-surface paths"
        if any(protected(p.strip(), Path(cwd)) for p in paths):
            return "Permission/security files require a separate human-reviewed edit outside this session"
    if name in {"Bash", "exec_command", "shell", "shell_command"}:
        command = data.get("command", data.get("cmd"))
        if isinstance(command, list) and all(isinstance(s, str) for s in command):
            command = " ".join(command)
        if not isinstance(command, str):
            return "Unrecognized shell input"
        try:
            headers = shell_headers(command)
            tokens = shlex.split(headers)
        except ValueError:
            return "Cannot parse shell input"
        bases = {Path(t).name for t in tokens}
        if bases & REMOTE:
            return "Remote-shell and transfer commands are blocked"
        if "git" in bases and "push" in tokens:
            return "Push requires an explicit human action outside the agent session"
        if "curl" in bases:
            # GET-only; catch reordered/combined upload options as well as prefixes.
            for token in tokens:
                if (token.startswith(("--data", "--form", "--upload", "--request"))
                        or re.match(r"^-[^-]*[dFTX]", token)):
                    return "curl upload/custom-method options are blocked; use fetch_page.py for GETs"
        if "wget" in bases and any(t.startswith(("--post", "--method", "--body")) for t in tokens):
            return "wget upload/custom-method options are blocked"
        # Shell can bypass apply_patch. Block explicit writes/operations naming
        # security surfaces, without pretending this catches computed paths/code.
        mutates = bool(bases & {"rm", "mv", "cp", "tee", "touch", "chmod", "apply_patch"})
        if bases & {"sed", "perl"} and any(t == "-i" or t.startswith(("-i", "--in-place")) for t in tokens):
            mutates = True
        if mutates and any(p in command for p in PROTECTED + ("SKILL.md",)):
            return "Shell operation names a protected permission/security surface"
        # Redirect *destinations*, not every filename mentioned by a command.
        # In particular, `codex_worker.py ... > /private/result.json` must work.
        lexer = shlex.shlex(headers, posix=True, punctuation_chars="<>")
        lexer.whitespace_split = True
        try:
            parts = list(lexer)
        except ValueError:
            return "Cannot validate shell redirection"
        for i, part in enumerate(parts[:-1]):
            if part in {">", ">>"} and protected(parts[i + 1], Path(cwd)):
                return "Shell redirection targets a protected permission/security surface"
    return None


def decision(message: str | None) -> dict:
    if message:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                "permissionDecision": "deny", "permissionDecisionReason": message}}
    return {}


def main() -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    try:
        payload = sys.stdin.read(2_000_001)
        message = "Policy input exceeded the limit" if len(payload) > 2_000_000 else reason(json.loads(payload))
    except Exception:
        # A Python exception/unsupported output shape would fail open in Codex.
        # Do not echo event contents (which may contain private draft text).
        message = "Policy could not validate the tool call"
    print(json.dumps(decision(message), ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
