#!/usr/bin/env python3
"""Read Codex skill/hook discovery via its local app-server; no model turns."""

import json
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path


class RuntimeErrorInfo(Exception):
    pass


class Client:
    def __init__(self, root: Path, overrides=(), timeout=45):
        self.root = root.resolve()
        self.overrides = overrides
        self.timeout = timeout
        self.messages = queue.Queue()
        self.serial = 0

    def __enter__(self):
        binary = shutil.which("codex")
        if not binary:
            raise RuntimeErrorInfo("Codex CLI is not installed")
        argv = [binary, "app-server", "--stdio", "--strict-config"]
        for override in self.overrides:
            argv.extend(["-c", override])
        try:
            self.process = subprocess.Popen(argv, cwd=self.root, stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                            text=True, encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeErrorInfo(f"Could not start Codex app-server: {exc}") from exc
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.call("initialize", {"clientInfo": {"name": "ai_job_search_doctor", "version": "1.0.0"},
                                     "capabilities": {"experimentalApi": True}})
            self.send({"method": "initialized", "params": {}})
        except Exception:
            self.close()
            raise
        return self

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put({"fatal": "Malformed app-server response"})
        finally:
            self.messages.put({"fatal": "Codex app-server exited before replying"})

    def send(self, message):
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise RuntimeErrorInfo("Codex app-server connection closed") from exc

    def call(self, method, params):
        self.serial += 1
        request = self.serial
        self.send({"id": request, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                message = self.messages.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise RuntimeErrorInfo(f"Codex {method} timed out") from exc
            if not isinstance(message, dict) or "fatal" in message:
                raise RuntimeErrorInfo(message.get("fatal", "Invalid app-server event") if isinstance(message, dict) else "Invalid app-server event")
            if message.get("id") == request:
                if "error" in message:
                    raise RuntimeErrorInfo(f"Codex {method} failed: {message['error'].get('message', 'protocol error')}")
                if not isinstance(message.get("result"), dict):
                    raise RuntimeErrorInfo(f"Codex {method} returned an invalid result")
                return message["result"]

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()

    def __exit__(self, *args):
        self.close()


def discover(root: Path, client_factory=Client) -> dict:
    root = root.resolve()
    with client_factory(root) as client:
        skills = client.call("skills/list", {"cwds": [str(root)], "forceReload": True})
        hooks = client.call("hooks/list", {"cwds": [str(root)]})
    names, errors, policy = set(), [], []
    for entry in skills.get("data", []):
        for skill in entry.get("skills", []):
            if Path(skill.get("path", "/")).is_relative_to(root / ".agents/skills") and skill.get("enabled", True):
                names.add(skill["name"])
        errors.extend(e.get("message", "skill error") for e in entry.get("errors", []))
    for entry in hooks.get("data", []):
        errors.extend(e.get("message", "hook error") for e in entry.get("errors", []))
        for hook in entry.get("hooks", []):
            if Path(hook.get("sourcePath", "/")) == root / ".codex/hooks.json":
                policy.append({"event": hook.get("eventName"), "enabled": hook.get("enabled"),
                               "trust": hook.get("trustStatus")})
    return {"skills": sorted(names), "errors": errors, "policy_hooks": policy}
