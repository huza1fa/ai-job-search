---
name: rank
description: Batch-score scraped jobs against the candidate profile and present a ranked shortlist with honest strengths and gaps. Invoke with $rank.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/commands/rank.md`
and follow it in order using those mappings. The user's invocation text is
`$ARGUMENTS`. Use the required isolated `tools/codex_worker.py --role scorer`
route from `AGENTS.md` for the specified batches: fetch/gate first without the
profile, then score inline in separate read-only processes. Only the orchestrator
writes tracker/state changes; never substitute an inherited-permission scorer.
