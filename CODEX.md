# Codex support in this fork

**Target: Codex CLI 0.163.0+ on Linux/macOS (WSL on Windows).** The canonical
Claude workflows are retained so upstream updates remain manageable. All 12
command files and three core skills have discoverable Codex wrappers; three
custom agent definitions adapt the fetcher, scorer, and reviewer roles.

## Start here

Install Codex CLI **0.163.0+ on PATH**, including when using the IDE extension:
the isolated worker invokes the CLI. An IDE extension must also support project
skills and standalone `.codex/agents/*.toml` agents. Configuration was checked against the
0.163.0 schema. The runtime smoke suite is exercised on Linux CLI; native IDE,
macOS, newer CLI and PowerShell sessions still need their own smoke testing.
Use **WSL on Windows** for the Bash-heavy workflows.

Before personalizing, read the public-fork privacy warning in `README.md`.
Profile files are tracked: do not commit personal information to a public fork.

```bash
python3 tools/doctor.py --agent codex --runtime
# Optional, only if using portal CLIs and Bun is installed:
python3 tools/install_portal_clis.py
codex --search
```

Review and trust this project in Codex before expecting `.codex/config.toml` to
load. Start a new session after adding skills or agents. Check `/skills`, then
review and trust the exact repository policy hook using **`/hooks`** (separate
from project trust). Changed hooks need review again. Enter these **inside
Codex**, not your shell:

```text
$setup
$scrape
$rank
$apply https://example.com/careers/a-real-posting
$outcome
$interview
```

Other wrappers: `$expand`, `$upskill`, `$html-report`, `$add-portal`,
`$add-template`, `$reset`, `$notion-sync`, `$gmail-sync`, and
`$job-application-assistant`. They read the existing specifications; they do not
duplicate the workflow or candidate profile. Claude's `/command` names in
canonical files refer to the corresponding `$command` skill in Codex.

`CLAUDE.md` remains the canonical profile. `AGENTS.md` supplies Codex's runtime
translations, including relative paths, temporary files, web fetching, and PDF
verification. Do not run a blind `/import`: user-level imports can create stale,
duplicate skills/agents outside this repository's drift checks.

## Prerequisites and diagnostics

| Tier | Requirement | Missing behavior |
|---|---|---|
| Core | Codex CLI on PATH (also for IDE use), Git, Python 3.10+ | Install before using the workspace |
| Validation on Python 3.10 | `python -m pip install tomli` | TOML checks fail with remediation; Python 3.11+ includes `tomllib` |
| Portal CLIs | Bun and CLI dependencies | Live web-search fallback; results may be stale |
| Stock application PDFs | `lualatex` and `xelatex` | Draft-only with consent, or install TeX; custom templates use their own toolchains |
| ATS/page counts | `pypdf`, or Poppler `pdftotext` + `pdfinfo` | PDF verification incomplete |
| Layout geometry | Poppler `pdftotext` with `-bbox` | Layout check skipped, never passed; pypdf cannot substitute |
| Visual review | PDF image rendering/viewing (`pdftoppm` is useful) | Ask the user to inspect PDFs; automated geometry is not visual approval |
| Integrations | Explicitly configured Notion/Gmail MCP tools | Stop with setup guidance; never silently substitute a connector |

For a small TeX installation see
[TinyTeX/BasicTeX setup](SETUP.md#minimal-tex-install-tinytexbasictex).
The doctor checks executable presence, selected agent version, settings JSON,
adapter coverage/configuration, and portal discovery/dependency directories.
With `--runtime`, it also asks the local Codex app-server to list repository
skills and policy-hook trust. This uses no model turn and changes no trust.
It **does not** install anything, read credentials, compile templates, test TeX
packages/fonts, or contact job sites. Runtime discovery is not a workflow test.
Run `--json` for machine-readable output. Exit 1 means a required tool or static
configuration check failed; warnings are optional features or manual checks.

## Permissions and integrations

The project defaults to `workspace-write`, `on-request`, live search, and **no
unrestricted sandbox shell networking**. Portal and `fetch_page.py` shell calls
may require individual network approval. Do not enable full access to make them
work. Hosted search/web tools and configured MCP servers have their own policies.
No model/provider or account configuration is imposed.

Native Codex agents inherit parent permissions; their instructions alone are
**not a read-only sandbox**. Therefore `$rank` and `$apply` use
`tools/codex_worker.py` for scoring and review in **separate read-only Codex
processes**. The parent fetches/gates postings and independently obtains company
research first, then supplies cleaned postings, required profile/rubric sources,
drafts and research inline. Only the parent persists state or applies edits.

The worker disables shell/web/browser tools, apps/plugins, skills and delegation,
ignores user config/rules, and runs outside the repository with private temporary
runtime state. It does not parse/copy login tokens: the Codex client accesses an
existing file-based login through an auth-file link, or uses the configured
API-key environment. Account configuration, custom provider/model routing and
MCP servers are not imported. Workers use the default Codex provider/model;
if the parent uses a local/private/custom provider, obtain consent to this
difference or stop rather than silently switching providers. Keyring-only or
custom-provider-only setups require a supported default Codex login. Private
temporary state avoids giving the parent write access to your real `CODEX_HOME`.
Normal model processing sends the inline task to the default Codex service;
this is not an offline/local model promise.

Launching this trusted helper may need **per-call network approval** for the
model endpoint. Never retry with full access or enable networking globally.
Observed tool calls, blocked patch attempts, failed and incomplete worker turns
invalidate the result. Worker text remains an untrusted proposal, not permission
to execute commands or use links it returns.

The reviewed synchronous `.codex/hooks.json` PreToolUse policy adds tripwires
for direct credential reads, obvious uploads/remote shells, pushes and edits to
permission/security files. It denies instead of emitting Codex's unsupported
`ask` decision. Hooks run only after you explicitly trust their current hash in
`/hooks`; untrusted/changed hooks are skipped. No trust-bypass flag is shipped.
The static guard requires the exact reviewed hook configuration and restrictive
defaults; it is not runtime enforcement. See
[SECURITY.md](SECURITY.md#codex-adapter-security) for bypasses and coverage limits.

Notion setup, **only if you choose to enable it**:

```bash
codex mcp add notion --url https://mcp.notion.com/mcp
codex mcp login notion
```

Restart Codex, check the actual tools, then invoke `$notion-sync`. This command
intentionally publishes a selected pipeline view; review the scope first.

There is no built-in assumption that Claude's Gmail connector exists in Codex.
`$gmail-sync` needs a trusted, user-configured server with equivalent search,
pagination and full-message tools. If absent or incompatible, it stops. Server
selection and OAuth are user decisions; `codex mcp --help` describes management.

## Verification status and remaining work

Implementation and reproducible checks:

- Thin wrappers for every canonical command/core skill, with drift tests.
- Profile, argument, path, scratchpad, tool, PDF and integration mappings.
- Fetcher/scorer/reviewer role adapters plus separate read-only scoring/review.
- Portal discovery excludes workflows and preserves `enabled: false`.
- Prerequisite doctor, opt-in runtime discovery, reviewed PreToolUse hook, and
  CI lint/security checks for config, agents, hooks and adapter drift.
- `python3 tools/codex_smoke.py --pdf-only`: real synthetic CV/letter compiles,
  page counts, ATS text, layout checks and optional PNG rendering, **no model or
  job-site requests**. This runs in both existing LaTeX CI legs.
- `python3 tools/codex_smoke.py --live --pdf`: explicitly opt-in, token-consuming
  Codex fixture suite: portal listing, profile identity update, CLI search and
  deduplication, isolated scoring/state persistence, missing MCP stop paths,
  flagged pasted postings, approval-gated application drafting, isolated review,
  PDFs, tracker/archive updates, interview prep, HTML report and reset confirmation.
  Omit `--pdf` for routing/scoring/approval tests without a TeX installation.

The live suite copies framework code into a marked disposable directory, builds
only synthetic candidate data, disables the real portals, and uses a local Bun
fixture portal. It deliberately trusts only that inspected test hook through
per-process overrides, without changing your real account/project trust. Its
synthetic-only parent networking simulates approval for the worker's model
endpoint; the shipped production config remains restricted. Logs/artifacts stay
outside the repo. To retry a failed scenario, use `--resume <artifact-directory>
--start-at <case>` with the same `--live`/`--pdf` options. Do not pass a real job
workspace to the test runner.

Also checked locally with the installed **Codex CLI 0.163.0**: its app-server
`skills/list` discovered all **21 repository skills** (15 workflow adapters and
six portals) with no loading errors. No model turn or live job request was used
for that discovery check. The project config validates against that release's
published schema; agent instruction/feature fields and identity structure were
checked separately. Local Codex diagnostics accepted the restricted sandbox
configuration.

### Recorded local validation — 2026-10-21

- **882 Python tests:** no failures/errors; seven intentional upstream-template
  placeholder checks skipped on this fork.
- **495 Bun fixture/mock tests** across all six portal CLIs, plus all six CLI
  TypeScript typechecks: passed. No real job-board searches were used.
- **13 real Codex fixture scenarios:** profile update, search/dedup, isolated
  ranking, missing integrations, flagged pasted input, approval-gated application,
  independent review, PDFs, outcome/archive, interview prep, offline dashboard,
  and destructive-reset confirmation. Scenario logs are retained under
  `/tmp/opencode/codex-live-*/results.json` on the test machine.
- All **21 repository skills** were discovered. All **three native custom roles**
  were dispatched on harmless capability tasks. The required full-workflow
  scorer/reviewer route was separately exercised as read-only subprocesses.
- A real read-only patch attempt was rejected; an adversarial posting left its
  canary unchanged. A trusted native PreToolUse hook rejected a protected-file
  patch without changing the file.
- Real LuaLaTeX/XeLaTeX compiles, exact **2-page CV / 1-page letter** counts,
  ATS text, layout checks and rendered visual inspection passed. TeX Live 2026
  was installed only in temporary validation storage, not the system PATH.
- Skill lint, security guards and `git diff --check`: passed. The PDF-only
  regression is wired into both LaTeX CI legs; remote CI has not been run here.

Authenticated Notion/Gmail operations and real third-party portal availability
remain **user-specific manual checks**. The fixture suite never submits an
application, sends mail, connects an integration or searches for real jobs.
Passing it cannot certify external services, native UI clients or arbitrary
custom templates. Do not use a passing doctor as a blanket parity badge.

For a new client/platform or live-service certification, recheck on a disposable
**private** workspace:

1. Check `/skills` in your target client and run `$setup` with synthetic candidate data; confirm only
   canonical profile/reference files are personalized.
2. Run `$scrape health` and a bounded search. Confirm workflow adapters are not
   queried and disabled portals remain disabled.
3. Run `$rank`; confirm separate read-only workers and parent-only state writes.
4. With all toolchains installed, run `$apply` on a harmless posting (URL and
   pasted-text cases). Confirm integrity gating, approval before drafting,
   independent review, both compiles, page counts, layout/ATS checks, and actual
   visual review. Also test missing-tool and flagged-posting paths.
5. Exercise `$outcome` and `$interview` against the resulting synthetic archive;
   test missing integrations stop without side effects.
6. Separately validate any opt-in MCP setup and review data sent to it.

The read-only worker's disabled network-facing tools narrow the attack surface,
but no guarantee covers the parent's web tools, arbitrary shell code, managed
machine policy, a compromised CLI/provider, or malicious local framework code.
Review fetched content, profile changes, company claims and final documents.

## Plan review

The supplied October 19 porting plan is sound as an incremental adapter design,
but is not sufficient evidence of completion. Corrections applied here:

- The checkout has 12 command files and three core skills, not 13 command files.
- Portal discovery must be filtered everywhere, including `$add-portal --list`.
- Private unique scratch directories avoid collisions and preserve canonical
  shell snippets without rewriting upstream files.
- Real candidate tool use, not the runtime, determines application claims.
- Notion's Codex syntax is `--url`, not Claude's `--transport http`.
- Default networking stays restricted; no regex hook is presented as robust
  upload protection or an exact replacement for Claude permission rules.
- PDF geometry cannot replace all visual checks; missing tools remain visible.
- Doctor output distinguishes static coverage from active runtime discovery.

Reference sources: [Codex skills](https://developers.openai.com/codex/skills/),
[subagents](https://developers.openai.com/codex/subagents/),
[configuration](https://developers.openai.com/codex/config-reference/), and the
[0.163.0 config schema](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/core/config.schema.json).
