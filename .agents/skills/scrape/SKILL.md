---
name: scrape
description: Find new jobs through installed portal CLIs with web-search fallback, profile-based queries, deduplication and portal health checks. Invoke with $scrape.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/skills/job-scraper/SKILL.md`
and follow it using those mappings. The user's invocation text is `$ARGUMENTS`.
Resolve `search-queries.md` beside that canonical skill. Discover only portals
containing `cli/src/cli.ts` (or use `python3 tools/portal_skills.py`), respect each
`enabled` toggle, and keep state/output paths relative to the repository root.
