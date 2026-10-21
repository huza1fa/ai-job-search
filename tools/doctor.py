#!/usr/bin/env python3
"""Check workspace prerequisites without installing anything or contacting job sites."""

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:  # Support both `python tools/doctor.py` and package imports in tests.
    from . import codex_adapters, codex_runtime, portal_skills
except ImportError:
    import codex_adapters
    import codex_runtime
    import portal_skills

ROOT = Path(__file__).resolve().parent.parent


def inspect(root=ROOT, agent="codex", which=shutil.which, run=subprocess.run,
            find_spec=importlib.util.find_spec, runtime=False, discover=codex_runtime.discover) -> list[dict]:
    checks = []

    def add(status, name, detail):
        checks.append({"status": status, "name": name, "detail": detail})

    add("OK" if sys.version_info >= (3, 10) else "FAIL", "Python",
        f"{sys.version.split()[0]}; Python 3.10+ required")

    def binary(name, required, remediation):
        path = which(name)
        if path:
            add("OK", name, f"found: {path}")
        else:
            add("FAIL" if required else "WARN", name, remediation)
        return path

    binary("git", True, "Install Git: https://git-scm.com/downloads")
    cli = binary(agent, True, f"Install {agent} CLI and sign in; see CODEX.md / README.md")
    if cli:
        try:
            result = run([cli, "--version"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=10)
            version = (result.stdout or result.stderr).strip()
            add("OK" if result.returncode == 0 else "WARN", f"{agent} version", version)
            match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
            if agent == "codex" and match and tuple(map(int, match.groups())) < (0, 163, 0):
                add("WARN", "Codex compatibility", "Adapters target 0.163.0+; update Codex before testing")
        except (OSError, subprocess.TimeoutExpired) as exc:
            add("WARN", f"{agent} version", f"Could not run --version: {exc}")

    binary("bun", False, "Install https://bun.sh for portal CLIs; otherwise use live web-search fallback")
    for compiler in ("lualatex", "xelatex"):
        binary(compiler, False, "Stock $apply PDF compilation unavailable; install TeX (SETUP.md#minimal-tex-install-tinytexbasictex), or register a custom template toolchain")
    pypdf = find_spec("pypdf") is not None
    add("OK" if pypdf else "WARN", "pypdf", "available" if pypdf else
        "Optional ATS/page-count backend: python -m pip install pypdf (or install Poppler)")
    pdftotext = binary("pdftotext", False, "Install Poppler: layout geometry checks need pdftotext -bbox; pypdf alone cannot replace them")
    pdfinfo = binary("pdfinfo", False, "Install Poppler for page counts if pypdf is unavailable")
    if not pypdf and not (pdftotext and pdfinfo):
        add("WARN", "PDF verification", "Install pypdf or both Poppler pdfinfo and pdftotext before completing $apply")
    binary("pdftoppm", False, "Optional: install Poppler to render PDF pages as images for visual inspection")

    settings = root / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
        valid = (isinstance(data, dict) and isinstance(data.get("permissions"), dict)
                 and isinstance(data["permissions"].get("allow"), list))
        if not valid:
            raise ValueError("expected permissions.allow list")
        add("OK", "Claude settings", "valid JSON; these permissions do not apply to Codex")
    except (OSError, ValueError) as exc:
        add("FAIL", "Claude settings", str(exc))

    if agent == "codex":
        errors = codex_adapters.check(root)
        if errors:
            for error in errors:
                add("FAIL", "Codex adapters", error)
        else:
            add("OK", "Codex adapters", f"{len(codex_adapters.canonical_workflows(root))} workflow adapters and matching agents/config checked statically")
        if runtime:
            try:
                observed = discover(root)
                expected = set(codex_adapters.canonical_workflows(root)) | {p["name"] for p in portal_skills.discover(root)}
                missing = expected - set(observed["skills"])
                if missing or observed["errors"]:
                    add("FAIL", "Runtime visibility", f"Missing skills: {sorted(missing)}; load errors: {observed['errors']}")
                else:
                    add("OK", "Runtime visibility", f"Codex app-server discovered all {len(expected)} expected skills (no model turn)")
                hooks = observed["policy_hooks"]
                ready = bool(hooks) and all(h["enabled"] and h["trust"] in {"trusted", "managed"} for h in hooks)
                add("OK" if ready else "WARN", "Policy hook trust", "reviewed hook active" if ready else
                    "Policy hook not trusted/active: review this project and .codex/hooks.json via /hooks; never bypass trust")
            except codex_runtime.RuntimeErrorInfo as exc:
                add("FAIL", "Runtime visibility", str(exc))
        else:
            add("WARN", "Runtime visibility", "Not introspected: use --runtime for local skill discovery/hook trust checks (no model turn)")
        add("WARN", "Worker authentication", "Workers use private temporary Codex state and the existing file-based login (or API-key environment), not account config. Keyring/custom-provider-only setups need a supported default login. No auth was inspected")

    portals = portal_skills.discover(root)
    enabled = sum(p["enabled"] for p in portals)
    add("OK" if portals else "WARN", "Portal discovery",
        f"{len(portals)} portal CLI skills ({enabled} enabled); workflow adapters excluded")
    for portal in portals:
        cli_dir = root / portal["cli"]
        cli_dir = cli_dir.parent.parent
        try:
            manifest = json.loads((cli_dir / "package.json").read_text(encoding="utf-8"))
            if not isinstance(manifest, dict):
                raise ValueError("expected manifest object")
            if manifest.get("dependencies") and not (cli_dir / "node_modules").is_dir():
                add("WARN", portal["name"], "Dependencies not installed: python3 tools/install_portal_clis.py")
        except (OSError, ValueError) as exc:
            add("FAIL", portal["name"], f"Invalid/missing CLI package.json: {exc}")
    add("WARN", "Optional integrations", "Notion/Gmail require opt-in MCP setup; no credentials or connections were inspected")
    return checks


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("codex", "claude"), default="codex")
    parser.add_argument("--json", action="store_true", help="emit machine-readable checks")
    parser.add_argument("--runtime", action="store_true", help="query local Codex skills and hook trust via app-server; no model turn")
    args = parser.parse_args(argv)
    checks = inspect(agent=args.agent, runtime=args.runtime)
    if args.json:
        print(json.dumps({"checks": checks}, ensure_ascii=True, indent=2))
    else:
        for item in checks:
            print(f"{item['status']:4}  {item['name']}: {item['detail']}")
        print("\nOptional-feature warnings do not block other workflows; no installations or live job requests made.")
    return int(any(c["status"] == "FAIL" for c in checks))


if __name__ == "__main__":
    sys.exit(main())
