---
name: add-portal
description: Investigate and add a job-portal CLI skill, or list installed portals. Invoke with $add-portal.
---

Read `AGENTS.md`'s Codex runtime mappings, then read `.claude/commands/add-portal.md`
and follow it in order using those mappings. The user's invocation text is
`$ARGUMENTS`; ask for the portal URL if missing. Include only skills containing
`cli/src/cli.ts` when listing/discovering portals. Permission-file changes need
explicit user review; Claude allowed-tools entries do not grant Codex permissions.
With the policy hook active, present the new `SKILL.md` and permission/security
changes as a patch for the user to apply outside the protected session. Do not
disable or bypass the hook, and do not claim registration completed until the
human-reviewed files exist and validation passes.
