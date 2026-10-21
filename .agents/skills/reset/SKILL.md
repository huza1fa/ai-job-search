---
name: reset
description: Reset candidate profile data or selected document folders only after explicit scope confirmation. Invoke with $reset.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/commands/reset.md`
and follow it in order using those mappings. The user's invocation text is
`$ARGUMENTS`. Never interpret invocation alone as confirmation: show the exact
destructive scope and wait for the canonical confirmation before deleting data.
Preserve framework files, Codex adapters, and unrelated user changes.
