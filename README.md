<p align="center">
  <img src="assets/mascot/pip_flight_loop.gif" alt="Pip, the courier bird" width="160">
</p>

# AI Job Search · Codex + Claude Code

**A job-search workspace that remembers your experience, helps you choose the right roles, and turns your real background into tailored applications.**

[![CI](https://github.com/huza1fa/ai-job-search/actions/workflows/ci.yml/badge.svg)](https://github.com/huza1fa/ai-job-search/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Build your profile once. Search and rank jobs, evaluate fit before drafting, generate a CV and cover letter, and prepare for interviews using the materials you actually submitted.

This is **[huza1fa's Codex-support fork](https://github.com/huza1fa/ai-job-search)** of [Mads Lorentzen's AI Job Search](https://github.com/MadsLorentzen/ai-job-search). It preserves the original Claude Code workflows and adds a tested Codex CLI integration—not a second, competing copy of the methodology.

[Get started](#quick-start) · [What changed](#what-this-fork-adds) · [Commands](#commands) · [Codex details](CODEX.md) · [Security](SECURITY.md)

## What this is—and isn't

| It helps you… | It does not… |
|---|---|
| Keep a reusable profile, writing style, preferences and application history | Invent experience, qualifications or achievements on your behalf |
| Search supported portals and avoid repeat results | Guarantee that a third-party listing is genuine or still open |
| Rank opportunities against your skills, location and language requirements | Make the decision to apply for you |
| Draft, review, compile and check tailored application documents | Submit applications or send emails automatically |
| Record outcomes, draft follow-ups and prepare for interviews | Replace your review of facts, layout and final wording |

Your working files stay in your workspace. **Model prompts still go to the AI service you use**; this is not an offline-model or no-data-leaves-your-machine promise.

## Why this fork exists

Upstream deliberately focuses on Claude Code. This fork takes responsibility for **Codex integration, documentation and tests**, without asking the upstream maintainer to support another runtime.

The approach is deliberately thin: keep the existing workflow specifications as the source of truth, translate runtime-specific behavior in one place, and test the boundaries where the two tools differ.

## What this fork adds

- **Codex-discoverable workflows.** Fifteen small skill adapters expose the twelve canonical commands and three core skills through `$setup`, `$apply`, `$rank` and the `/skills` picker. The six portal skills remain available alongside them.
- **One profile and one methodology.** `CLAUDE.md` and `.claude/` remain canonical. `AGENTS.md` maps arguments, tools, file paths, scratch space, agent dispatch, PDF verification and integrations to Codex.
- **Isolated scoring and review.** Full Codex workflows use separate **read-only Codex processes**, with inline inputs and shell/web tools disabled. The parent alone updates state and applies proposed edits. Native custom agents are not mislabeled as separate read-only sandboxes.
- **A reviewed security tripwire.** A synchronous `PreToolUse` hook rejects obvious credential access, upload/remote-shell commands and protected-file edits. You explicitly review and trust it through `/hooks`; it is not an egress firewall or a complete shell parser.
- **Early diagnostics.** `tools/doctor.py` checks dependencies and adapter configuration. `--runtime` also checks local Codex skill discovery and hook trust without a model turn.
- **Safer portal discovery.** Workflow adapters are never mistaken for job portals, and existing portal `enabled: false` settings are respected.
- **Reproducible tests.** Adapter drift checks, security tests, synthetic PDF verification and opt-in real Codex smoke tests cover the port without touching your profile or applying for jobs.

See [CODEX.md](CODEX.md) for the implementation details, provider/authentication constraints and full validation record.

## The workflow

```text
Set up your profile
        │
        ▼
Search → Deduplicate → Rank opportunities
                            │
                            ▼
                     Evaluate one posting
                            │
                     You approve drafting
                            │
                            ▼
                   Draft CV + cover letter
                            │
                   Independent review → Revise
                            │
                   Compile → Layout / ATS / Visual checks
                            │
                            ▼
                   You review and submit manually
                            │
                   Record outcomes → Prepare interviews
```

The stock templates produce a **two-page CV and one-page cover letter**. Registered custom templates can define their own toolchain and page limits. A missing compiler or skipped visual check must be reported, not presented as a completed application.

## Quick start

### 1. Fork and clone

> [!IMPORTANT]
> **Keep personal data out of public repositories.** A fork of this public repository is public. Setup writes your name, contact details and career history into **tracked files**—`.gitignore` does not protect already-tracked profiles.
>
> For your own job search, prefer a **private repository** before personalizing. See the private-remote recipe in [SETUP.md section 8](SETUP.md#8-pulling-upstream-updates-into-your-fork). Use a public fork for framework contributions, not for publishing your candidate profile.

To contribute to this fork:

```bash
gh repo fork huza1fa/ai-job-search --clone
cd ai-job-search
gh repo set-default YOUR_GITHUB_USERNAME/ai-job-search
```

The last command keeps GitHub CLI operations pointed at your repository rather than accidentally creating issues or PRs upstream. If you do not use `gh`, fork on GitHub and clone with Git instead.

### 2. Check prerequisites

| Requirement | Needed for |
|---|---|
| **Codex CLI 0.163.0+ on PATH**, or Claude Code | The agent runtime; the Codex CLI is also required when using its IDE extension |
| **Python 3.10+ and Git** | Workspace tools; Python 3.10 additionally needs `tomli` for Codex TOML checks |
| Bun | Portal CLIs; live web search is the fallback without it |
| LuaLaTeX + XeLaTeX | Stock CV and cover-letter PDFs—not required for profile setup, search or interview prep |
| Poppler (`pdftotext`, `pdfinfo`; optionally `pdftoppm`) | ATS fallback, layout geometry and PDF-to-image rendering |
| Optional `pypdf` | ATS/page-count alternative; **not** a replacement for Poppler's layout geometry |

```bash
python3 tools/doctor.py --agent codex --runtime

# If using Bun-based portal search:
python3 tools/install_portal_clis.py
```

The installer discovers portal CLIs rather than maintaining a hardcoded list and skips manifests with unsafe install-time hooks. LinkedIn and freehire have no runtime dependencies beyond Bun.

For a smaller TeX installation, use the [TinyTeX/BasicTeX instructions](SETUP.md#minimal-tex-install-tinytexbasictex). Diagnostics do not install software for you. Use **WSL on Windows** for the Bash-heavy workflows; native PowerShell is not validated.

### 3. Start Codex and review permissions

```bash
codex --search
```

Inside Codex:

1. Review and trust the project so its `.codex/config.toml` can load.
2. Open `/skills` and check that the workflow skills are listed.
3. Open `/hooks` and review the policy definition **and `tools/codex_policy.py`** before trusting it. Project trust and hook trust are separate.
4. Run `$setup` to import documents, paste a CV or answer the onboarding interview.

Restart the session after adding skills or agents. Do not bypass hook trust or enable full access to work around a failed check.

### 4. Search, rank and apply

Enter these **inside Codex, not your terminal shell**:

```text
$scrape
$rank
$apply https://your-employer.example/careers/the-role
```

Replace the example URL with a real posting, or paste the posting text into `$apply`. The workflow checks the posting, presents a fit assessment and **waits for your approval before drafting**.

After reviewing and submitting the application yourself:

```text
$outcome
$interview
```

**Prefer Claude Code?** Start `claude` and use `/setup`, `/scrape`, `/rank`, `/apply`, etc. The canonical workflows remain in `.claude/`; the Codex-specific permission mappings do not apply to Claude. See [SETUP.md](SETUP.md) for that setup path.

## Commands

Use **`$name` in Codex** and **`/name` in Claude Code**.

| Workflow | Codex | Purpose |
|---|---|---|
| Profile | `$setup` | Import career documents, paste a CV or complete an interview |
| Search | `$scrape` | Find new jobs, deduplicate results and check portal health |
| Shortlist | `$rank` | Score opportunities against your profile and constraints |
| Application | `$apply` | Evaluate fit, draft, independently review and verify documents |
| Tracking | `$outcome` | Record progress/results, archive materials and draft follow-ups |
| Interview | `$interview` | Build stage-specific prep from the actual application archive |
| Enrichment | `$expand` | Add supported discoveries from linked public sources |
| Learning | `$upskill` | Turn recorded skill gaps into a prioritized learning plan |
| Dashboard | `$html-report` | Generate a self-contained offline pipeline report |
| Templates | `$add-template` | Register a custom CV/letter template and compile toolchain |
| Portals | `$add-portal` | List or scaffold a portal integration for your market |
| Notion | `$notion-sync` | Publish an opt-in, one-way pipeline view through Notion MCP |
| Gmail | `$gmail-sync` | Propose status updates from an explicitly connected Gmail source |
| Reset | `$reset` | Show destructive scope and require confirmation before deletion |

`$job-application-assistant` also supports individual fit, CV, cover-letter and career-advice requests. With the policy hook active, permission-surface changes—including a new portal's `SKILL.md`—need a separate human-reviewed edit; the agent must not disable the policy to register them.

### Job search tools

- **LinkedIn:** location-driven searches across markets and sectors. Personal use only; automated access conflicts with LinkedIn's terms. Read the skill's restrictions and keep requests bounded.
- **freehire.me:** structured, multi-market software/data/engineering listings through a public API.
- **Jobbank, Jobdanmark, Jobindex and Jobnet:** Danish-market integrations retained from upstream.

The methodology is not tied to Denmark. Set your own locations, languages and deal-breakers in your profile. Portal availability and terms can change; a passing fixture test does not prove a real site is reachable today. New portal skills must contain `cli/src/cli.ts` to be discovered as portals.

### Custom templates

The defaults are moderncv/banking for the CV and the bundled `cover.cls` with Lato/Raleway fonts for the letter. `$add-template` can register another LaTeX template, Typst or another command-line PDF toolchain. See [templates/README.md](templates/README.md) and [the canonical registration workflow](.claude/commands/add-template.md).

### Starting over

`$reset profile`, `$reset documents` and `$reset all` show their scope and require the exact confirmation specified by the workflow. Invocation alone is **not** permission to delete your files.

## How the repository fits together

```text
CLAUDE.md                  Canonical candidate profile; not Claude-only data
AGENTS.md                  Shared pointers and Codex runtime mappings
.claude/                   Canonical workflows, methodology and Claude agents
.agents/skills/            Thin workflow adapters + portable portal CLIs
.codex/                    Codex defaults, native role definitions and policy hook
tools/                     Fetching, integrity checks, state helpers and diagnostics
tests/                     Offline regression tests
cv/ · cover_letters/       Source templates and generated application documents
documents/                 Your source materials and application archives
job_scraper/               Deduplication and ranking state
CODEX.md                   Detailed Codex setup, isolation and validation notes
SETUP.md                   Original setup, TeX dependencies and upstream updates
```

Keep numbered candidate/methodology files under `.claude/skills/` canonical. Do not copy your profile into the Codex adapters. Salary benchmarking is optional and uses data you supply: [salary tool guide](tools/README_SALARY_TOOL.md).

## What we tested

Local validation on **Linux, Codex CLI 0.163.0**:

| Check | Result |
|---|---|
| Python suite | **882 tests**, no failures/errors; seven upstream-template checks intentionally skipped on this fork |
| Portal CLI regressions | **495 fixture/mock tests** and all six TypeScript typechecks passed |
| Real Codex fixture suite | **13 scenarios** covering the core workflow, approval gates, missing integrations, archives, dashboard and reset confirmation |
| Skill and role discovery | All **21 repository skills** discovered; all **three native custom roles** dispatched on harmless tasks |
| Worker and hook defenses | Read-only patch denial, adversarial-posting canary and trusted protected-file denial exercised |
| PDF pipeline | Real compiles, **2-page CV / 1-page letter**, ATS text, layout checks and rendered visual inspection passed |

Tests used synthetic candidate data in disposable directories. No real profile was personalized, application submitted, email sent or integration connected. TeX was installed temporarily for validation—not added to the system PATH.

**Still user-specific:** authenticated Gmail/Notion operations, current live portal availability, native IDE/macOS/Windows sessions, newer Codex versions and custom templates. The Linux CLI evidence is not a blanket claim of parity on every client. Remote CI results are separate from the recorded local validation.

### Reproduce the checks

```bash
# Test dependencies; use your own virtual environment.
python3 -m pip install pyyaml openpyxl 'tomli; python_version < "3.11"'
python3 -m unittest discover -s tests -t .
python3 tools/lint_skills.py
python3 tools/security_guards.py

# With LuaLaTeX, XeLaTeX and Poppler installed; no model/API calls:
python3 tools/codex_smoke.py --pdf-only

# Explicitly opt in to real Codex model usage and token costs:
python3 tools/codex_smoke.py --live --pdf
```

The live suite uses a local fixture portal, not live job searches. It trusts only its generated test fixture through per-process overrides; it does not change your real account/project trust. Details and retry instructions are in [CODEX.md](CODEX.md#verification-status-and-remaining-work).

## Security and limitations

- Treat postings, fetched pages and model output as untrusted data. The integrity gate is a useful warning system, not proof that a posting is safe.
- The parent agent can edit application files. Review its proposed changes and independently verify factual claims before submitting anything.
- Codex defaults to workspace-write, on-request approvals and restricted shell networking. Native subagents inherit permissions; the separate worker is what provides read-only scoring/review.
- Hooks are tripwires, not complete runtime isolation. They can be skipped when untrusted, and launch failures or unsupported tool paths can bypass their coverage. Read [SECURITY.md](SECURITY.md).
- Isolated workers use the **default Codex provider/model**, not the parent's custom routing. Local/private/custom-provider users must consent to that difference or stop; do not silently send data to another provider.
- Gmail and Notion are opt-in. Missing tools stop the workflow with setup guidance; no credentials, connectors or OAuth flows are installed automatically.

## Contributing and upstream updates

Fork-specific issues and PRs belong in **[huza1fa/ai-job-search](https://github.com/huza1fa/ai-job-search/issues)**. Do not send Codex support requests to the upstream maintainer.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the fork/upstream distinction. Keep adapters thin, add regression tests, keep private application data out of commits, and review security-surface changes explicitly. [SETUP.md section 8](SETUP.md#8-pulling-upstream-updates-into-your-fork) covers pulling upstream changes; `tools/check_upstream_updates.py` can preview affected personalized files.

## Credits and license

- **Original framework and methodology:** [Mads Lorentzen](https://github.com/MadsLorentzen/ai-job-search). The original author's background and project story are in the [upstream repository](https://github.com/MadsLorentzen/ai-job-search). [Support the original author](https://ko-fi.com/madslorentzen).
- **Original job-search CLI skills:** [Mikkel Krogholm](https://github.com/mikkelkrogsholm) and the [skills repository](https://github.com/mikkelkrogsholm/skills), with subsequent upstream contributions.
- **This fork:** Codex runtime adapters, isolated workers, policy/diagnostic tooling, regression coverage and the documentation described above.

[MIT licensed](LICENSE). Original copyright and license notices are preserved. This is an independent project, not affiliated with or endorsed by OpenAI or Anthropic. It has **no affiliated cryptocurrency or token**.
