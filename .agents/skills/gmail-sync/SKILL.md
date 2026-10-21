---
name: gmail-sync
description: Propose application status updates from an explicitly connected Gmail MCP source, requiring approval before local writes. Invoke with $gmail-sync.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/commands/gmail-sync.md`
and follow it in order using those mappings. The user's invocation text is
`$ARGUMENTS`. The canonical Claude connector is not automatically available in
Codex. Inspect actual Gmail tool schemas and stop if equivalent search,
pagination and full-message reads are unavailable. Never guess tool names or
use shell/IMAP. Preserve approval of each proposed update batch; never send mail.
