#!/usr/bin/env python3
"""List real portal skills, never workflow adapters. No network or dependencies."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def discover(root: Path = ROOT) -> list[dict]:
    portals = []
    for skill in sorted(root.glob(".agents/skills/*/SKILL.md")):
        cli = skill.parent / "cli" / "src" / "cli.ts"
        if not cli.is_file():
            continue
        text = skill.read_text(encoding="utf-8")
        header = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.S)
        frontmatter = header[1] if header else ""
        disabled = re.search(r"^enabled:[ \t]*false[ \t]*(?:#.*)?$", frontmatter, re.M | re.I)
        portals.append({
            "name": skill.parent.name,
            "skill": skill.relative_to(root).as_posix(),
            "cli": cli.relative_to(root).as_posix(),
            "enabled": disabled is None,
        })
    return portals


if __name__ == "__main__":
    print(json.dumps(discover(), ensure_ascii=True, indent=2))
