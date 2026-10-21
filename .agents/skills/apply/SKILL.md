---
name: apply
description: Run the full application workflow for a posting URL or pasted text; evaluate fit, draft and review CV and cover letter, compile PDFs and verify them. Invoke with $apply.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/commands/apply.md`
and follow it in order using those mappings. The user's invocation text is
`$ARGUMENTS`; ask for a posting URL or pasted posting if absent. Load the canonical
profile first and run the prerequisite check before drafting. Preserve the
posting integrity gate and the user's approval before drafting.
Step 3 uses `tools/codex_worker.py --role reviewer` per `AGENTS.md`: supply inline
drafts, grounding sources and independently verified research. Do not substitute
a native reviewer with the parent's write permissions.
