---
description: "Reference for claudeloop, the autonomous Claude Code session runner inside vibey-engine: commands, flags, exit codes, files and how vibey drives it."
---

# claudeloop: run Claude Code unattended until the task is done

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `claudeloop` drives a Claude Code session from a plan file to
> completion without waiting on a person, and tells an exhausted rate-limit window (which resets)
> apart from exhausted credits (which never do). It ships inside `vibey-engine`. You need an
> authenticated Claude account; the Claude CLI comes bundled with `claude-agent-sdk`. Run
> `claudeloop doctor`, then `claudeloop run plan.md`. In vibey it is the default paid engine; a
> local backend profile runs the same binary as the `claudeloop-local` engine at no cost.

> [!IMPORTANT]
> **Work in progress — not a final product:** `claudeloop` and `vibey` are in active development and not a final product. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

> **Now part of the vibey monorepo.** `claudeloop` lives in [the-vibey-project/vibey](https://github.com/the-vibey-project/vibey) at [`src/vibey_runners/claude`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude) (vibey ADR-0021). It is not published on its own any more: it ships inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package, so `pip install vibey-engine` installs it (vibey ADR-0037).

[![Ships in vibey](https://img.shields.io/pypi/v/vibey-engine?label=ships%20in%20vibey)](https://pypi.org/project/vibey-engine/)
[![Python versions](https://img.shields.io/pypi/pyversions/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![CI](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/LICENSE)

**Onion-architected, autonomous Claude Code session runner and full Anthropic
SDK CLI** — never blocks on a human, distinguishes an exhausted rate-limit
window from exhausted credits, and resumes safely across usage windows.

## How to read this page

Daniel had been told to "just use claudeloop" and wanted to know what he was signing up for.

**Daniel:** Professor, why not simply run `claude -p` in a loop?

**Professor Feynman:** Because a closed shop door can mean "back at two" or "gone out of
business". Waiting helps with the first and never with the second. claudeloop reads the sign.
The top of this page tells you how to start it; the tables further down are for looking things
up: every command, every exit code, every file it writes.

**Daniel:** So I read the quickstart and keep the rest for later.

**Professor Feynman:** Exactly. The man page, `claudeloop --help`, carries the same tables.

## What problem this solves

Claude Code sessions hit usage limits. A `claude -p` invocation ending
doesn't tell you whether the *task* finished or just that *turn* did. And
when a rate limit rejects you, you can't tell from the outside whether
waiting will ever help — a five-hour window resets on its own; an exhausted
credits balance never will, no matter how long you wait.

`claudeloop` exists to get all three of those distinctions right,
automatically, so you can hand it a plan and walk away — including handling
the case where you top up your account's credits while it's mid-wait, which
it notices on the next probe rather than at some fixed deadline.

This project began as [`legacy/claude_autoresume.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/legacy/claude_autoresume.py),
a single-file script that did this by shelling out to `claude -p` and
regex-scraping its output. `claudeloop` replaces that with a tested,
typed, onion-architected package built on the official `claude-agent-sdk`.
See the [architecture decision records](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/architecture/decisions/0001-onion-architecture-with-import-linter.md) for why
each specific change was made.

## Install

Requires **Python 3.12+** and **macOS or Linux**. Windows is not a supported target.

```bash
pipx install vibey-engine      # or: uv tool install vibey-engine / pip install vibey-engine
                               # the whole family; claudeloop is one of its console scripts
claudeloop --version
```

You should see `claudeloop 0.4.0` (or the version you installed).

Authentication is yours to set up: sign in to Claude Code, or set `ANTHROPIC_API_KEY` or
`ANTHROPIC_AUTH_TOKEN`. You do not need a separate Claude Code install: `claudeloop doctor` looks
first for the Claude CLI bundled with `claude-agent-sdk`, then for `claude` on `PATH`, the order
the SDK launches them in. A local backend profile needs no Anthropic account at all (see
[Run it for free on a local model](#run-it-for-free-on-a-local-model)).

See the [installation guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/getting-started/installation.md)
for requirements and a from-source setup.

## Quickstart

```bash
claudeloop doctor                # pre-flight checks before a long unattended run
claudeloop run handoff.md        # seed a session from a plan file and run to completion
claudeloop resume                # resume whatever you were last working on
claudeloop resume --session-id <id>
claudeloop api models list       # any Anthropic SDK endpoint (generated; see docs)

# Mid-run control (second terminal, same cwd):
claudeloop status
claudeloop snapshot              # handoff JSON under .claudeloop/runs/<id>/snapshots/
claudeloop logs -f --chatter
claudeloop prompt --now "Also cover the error path"
claudeloop preset high           # or: model / effort (low|medium|high|xhigh|max)
claudeloop permission-mode plan  # mid-run; default at start is always bypass
claudeloop attach ./notes.md
claudeloop response retry
claudeloop watch --stream        # Textual live stream; --replay for history
claudeloop wind-down             # finish the turn, write handoff.json, exit 75
claudeloop stop                  # soft-stop → stop-summary.md (exit 130)
claudeloop savepoints
claudeloop unwind --to 1         # after stop; git save-point restore
```

Replace `<id>` with a session id from `claudeloop sessions`. `claudeloop run` prints the run id
on stderr when it starts.

Ops surface (attachments, skills/MCP, memories, chat metadata, slash commands):
[run resources and chat ops](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/run-resources-and-chat-ops.md).

## Why it's different from just retrying on 429

| | Naive retry | `claudeloop` |
|---|---|---|
| Sees an HTTP 429 | Sleeps a fixed duration, retries | Classifies *why* — a waitable rate-limit window, or exhausted credits that only a human can fix |
| Credits exhausted | Sleeps forever, no reset time exists | Probes on a bounded backoff and tells you it needs you |
| A credit top-up arrives mid-wait | Not noticed until the fixed sleep ends | Noticed on the next scheduled probe |
| Turn ends vs. task ends | No structured signal — a marker string, easily confused with a truncated limit message | Structured per-turn JSON verdict, with the legacy marker kept only as a fallback |
| Asked a clarifying question | Hangs waiting for stdin, or fabricates an answer | Denies the tool call with guidance, so the model proceeds on a stated, auditable assumption |

See [rate limits vs. credits](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/rate-limits-and-credits.md)
and [never blocking on a human](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/never-blocking.md) for the
full reasoning.

## Commands

Every command below is in `claudeloop --help` (the man page) and `src/claudeloop/cli/app.py`.

| Command | What it does |
|---|---|
| `run PLAN_FILE` | Start a new session from a markdown plan and drive it until Done, Blocked, budget exhaustion, max-wait, auth failure, or operator stop. Prints the run id on stderr. |
| `resume [--session-id ID]` | Continue a session. Without `--session-id`, picks the most recently modified session for the current directory and says which. |
| `stop [--run-id ID]` | Soft-stop: finish the turn or abort a wait, write `stop-summary.md`, exit 130. |
| `wind-down [--run-id ID] [--reason TEXT]` | Finish the turn, write `handoff.json` naming every artifact, exit 75. `--reason` defaults to `operator`. |
| `prompt (--now \| --at-break) TEXT` | Inject operator text: next turn (`--now`), or queued until a natural break (`--at-break`). Exactly one is required. |
| `model NAME` / `effort LEVEL` / `preset NAME` | Mid-run changes, applied at a turn boundary. |
| `permission-mode MODE` | `bypass`, `manual`, `accept-edits`, `plan` or `auto`. Sessions always start in bypass. |
| `cwd DIR` | Change the working directory mid-run (reconnects the session). |
| `slash /COMMAND` | Inject an allow-listed slash command; never raw shell. |
| `tool approve\|deny REQUEST_ID` | Resolve a pending Manual-mode tool approval. |
| `attach`, `unattach`, `folder`, `skill`, `plugin`, `connector`, `github`, `research`, `web-search` | Run-scoped resources. |
| `memory`, `artifact` | Native memories (`*.md`) and artifacts under the run directory. |
| `chat` | Local session metadata (pin, rename, share, project). `share` writes a local export bundle, not a Claude.ai share. |
| `response copy\|good\|bad\|retry` | The last turn: copy it, record feedback, or re-queue the prompt. |
| `voice`, `speak` | Optional text-to-speech and speech-to-text extras (`vibey-engine[voice]`, or system `say`/`espeak`). |
| `logs [--run-id ID] [-f] [--chatter]` | Print or follow the run's redacted `events.jsonl`; `--chatter` keeps only `chatter.*` events. |
| `status [--run-id ID]` | The latest `status.json`: phase, attempt, session id, model/effort, capacity subtype, `waiting_until`. |
| `snapshot [--out PATH] [--bundle \| --no-bundle]` | Write a handoff snapshot under `snapshots/`. A bundle copies attachments, memories, artifacts and a Claude Code transcript when one is found; a missing transcript is recorded, never invented. |
| `runs` | List run directories under `.claudeloop/runs/`. |
| `savepoints` | List git save points (`refs/claudeloop/<run_id>/<n>`). |
| `unwind --to N [--backup \| --no-backup]` | Reset the worktree to a save point. Refuses while the run is live; makes a backup ref by default. |
| `reset --yes` | Delete the project's `.claudeloop/` control plane. Refuses while a run is live; never touches the worktree or `~/.claude/`. |
| `watch [--follow \| --no-follow] [--stream] [--replay] [--speed N]` | Follow `bus.jsonl` state changes, or a full-screen token stream. |
| `sessions [--cwd PATH]` | List known Claude Code sessions (read-only). |
| `doctor [--profile NAME]` | Pre-flight: Claude CLI present, authentication, MCP servers, SDK import, API surface, cwd safety. With a local profile: its token, its `base_url`, every model it names, and real tool calls on each tier. |
| `api …` | The generated 1:1 Anthropic SDK REST surface, with a CI drift gate. |

### `run` and `resume` flags

| Flag | Default | Meaning |
|---|---|---|
| `--run-id` | generated | Name the run (lets a supervisor attach while it runs). `run` only. |
| `--cwd DIR` | current directory | Working directory for the run. |
| `--attach PATH`, `--add-folder PATH`, `--skill NAME`, `--plugin NAME` | none | Declare run resources up front (repeatable). |
| `--from-github OWNER/REPO`, `--import-issue OWNER/REPO#N` | none | A GitHub repo or issue as run resources. |
| `--connector NAME=JSON\|url` | none | An MCP connector (repeatable). |
| `--append-system-prompt TEXT` | none | Append to the system prompt (repeatable). |
| `--web-search`, `--deep-research` | off | Enable the web-search tool flag, or local research-job recording. |
| `--permission-mode MODE` | `bypass` | `bypass`, `manual`, `accept-edits`, `plan`, `auto`. |
| `--slash /COMMAND` | none | An initial validated slash command. |
| `--max-turns`, `--max-dollars`, `--max-wait SECONDS` | none | Caps on turns, reported USD cost, and capacity waiting. |
| `--profile NAME` | Anthropic | A backend profile (`[profiles.NAME]`); `resume` refuses a session last run on another backend. |
| `--model NAME` | alias `low` (`claude-sonnet-4-5`) | An alias (`low`, `medium`, `high`) or a raw model id. |
| `--effort LEVEL` | `medium` | `low`, `medium`, `high`, `xhigh`, `max`. |
| `--preset NAME` | none | `low`, `medium` or `high` sets model and effort; `high` is `claude-fable-5` at `max`. |
| `--auto-model` / `--no-auto-model` | on | Automatic escalation and cost-aware downgrade. |
| `--continue-prompt TEXT`, `--done-marker TEXT` | built in | The prompt for later turns; the fallback completion marker. |
| `--max-buffer-size BYTES` | 52428800 (50 MiB) | The SDK's JSON message buffer. `run` only. |
| `--log-level`, `--log-file`, `--log-chatter full\|summary\|off`, `--stream-ui` | `INFO` | Logging and the full-screen stream view. |
| `--wind-down-at WHEN` | none | Wind down at an ISO 8601 time or after `+2h`, `+90m`. |
| `--capabilities PATH` | none | The run's locked capability document, written by vibey (ADR-0103): its plugins, skills and folders, with no user, project or local settings. A refused document exits 78 before the session starts. `run` only. |

Global flags: `--version`, `--help`/`-h`/`--man`, `-v` (repeatable: `-v` debug, `-vv` also
third-party libraries, `-vvv` full payloads), `-q`/`--quiet`, `--log-level`, `--log-file`.
These are claudeloop's own; vibey's `-v` prints vibey's version.

### Exit codes

| Exit | Meaning |
|---|---|
| `0` | Success: a Done verdict, every doctor check passed, or an inspection command succeeded. |
| `1` | Blocked, budget or max-wait exhausted, auth failed, a doctor check failed, or another error. |
| `2` | Usage error: `prompt` without exactly one of `--now`/`--at-break`, an unknown `--profile`, or resuming on another backend. |
| `75` | Wound down on purpose (`wind-down`); `runs/<id>/handoff.json` names every artifact, and a supervisor can resume elsewhere. |
| `78` | Backend misconfigured (unreachable, model missing, model failed to load), or a refused `--capabilities` document. Waiting will not fix it. |
| `130` | Soft-stopped by `claudeloop stop` or an equivalent interrupt. |

### Files

| Path | What it holds |
|---|---|
| `claudeloop.toml` | Optional per-project configuration in the working directory. |
| `~/.config/claudeloop/config.toml` | Optional user configuration. Precedence: user file, then the cwd file, then environment, then flags. |
| `.claudeloop/runs/<run_id>/` | The per-run control plane: `meta.json`, `inbox/`, `events.jsonl`, `audit.jsonl`, `savepoints.jsonl`, `status.json`, `bus.jsonl`, `stop-summary.md`, `resources/`, `memories/`, `artifacts/`, `snapshots/`, `run.lock`. |
| `.claudeloop/chats/<session_id>.json` | Native chat metadata. |

Environment overrides use the `CLAUDELOOP_` prefix (for example `CLAUDELOOP_MAX_TURNS`,
`CLAUDELOOP_PROFILE`, `CLAUDELOOP_MAX_BUFFER_SIZE`); the man page lists them all.

## Run it for free on a local model

A `[profiles.NAME]` table in `claudeloop.toml` or `~/.config/claudeloop/config.toml` with a
`base_url` runs claudeloop against a local Anthropic-compatible server such as Ollama. The paid
`ANTHROPIC_API_KEY` is blanked and cost is recorded as $0. Check the profile first:

```bash
claudeloop doctor --profile local
claudeloop run handoff.md --profile local
```

See the [local backend guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/local-backend.md)
for the profile's keys.

## How vibey drives claudeloop

- **Two engines, one binary.** vibey's `claudeloop` engine is the default paid engine (tier
  PAID). The `claudeloop-local` engine (tier LOCAL) is the same binary run with
  `--profile local`, off by default: switch it on with `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` or
  `[features] claudeloop_local = true`, and name another profile with
  `[engines.claudeloop_local] profile` or `VIBEY_CLAUDELOOP_LOCAL_PROFILE` (ADR-0064;
  `src/vibey/infrastructure/engines/descriptors.py`).
- **Effort.** vibey maps its effort ladder onto `--preset` and `--effort`; at `max` and `ultra`
  it passes `--preset high --effort max`, and at ULTRA it passes no `--max-turns` (ADR-0063).
- **Capability snapshot.** BUILD writes the run's locked capability document and starts every
  claudeloop run with `--capabilities PATH` (ADR-0103). vibey passes no `--web-search` or
  `--deep-research`: the snapshot's `[loops] builtin_web` decides the built-in web tools, and
  claudeloop refuses `--web-search` beside a snapshot that switches them off.

## Documentation

Full docs (MkDocs Material sources) live in the
[`docs/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/docs) directory of the vibey monorepo, starting at
[`docs/index.md`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/index.md). The standalone `claudeloop` Pages site has been retired.

| | |
|---|---|
| [Getting started](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/getting-started/installation.md) | Install, quickstart, configuration |
| [Guides](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/autonomous-runs.md) | How autonomous runs work, rate limits vs. credits, never blocking, completion detection, [logging](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/logging-and-observability.md), [run resources and chat ops](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/run-resources-and-chat-ops.md) |
| [Architecture](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/architecture/overview.md) | The onion layers, the domain model, the run-loop state machine |
| [Decision records](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/architecture/decisions/0001-onion-architecture-with-import-linter.md) | Why each hard call was made |
| [Contributing](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/contributing/development.md) | Development setup, testing philosophy, release process |
| [Plans](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/plans/architecture-and-roadmap.md) | The original approved plans this project was built from |
| [Changelog](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/CHANGELOG.md) | Release notes (entries up to 2026-08 were written by release-please, which vibey ADR-0028 retired) |

## Project status

Pre-1.0 (0.4.0, shipped inside `vibey-engine`). The commands on this page run today: `run` and
`resume` drive Claude Code through `claude-agent-sdk`, `sessions` and `doctor` run against your
environment, and **`claudeloop api`** exposes a generated 1:1 Anthropic SDK REST surface with a CI
drift gate. The milestone labels (M1 to M5) in the original plan record are history: that file is
preserved verbatim and its status line predates the commands above.

CI holds all four layers, `domain`, `application`, `infrastructure` and `cli`, to 100% line and
branch coverage, each as its own gate, on Python 3.12, 3.13 and 3.14 (the `tools` job in
`.github/workflows/ci.yml`). A live suite (`tests/live/`) exercises the installed console script.
`run` / `resume` log to stderr twice — a human-readable stream and a JSON line stream —
controlled by `--log-level`; see
[logging and observability](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/logging-and-observability.md).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/CONTRIBUTING.md) for the
gitflow branch model, Conventional Commits requirement, and how to run every
quality gate locally.

The GitHub default branch is **`develop`**. Open feature PRs into `develop`,
not `main`. By contributing you agree that your work is licensed under the
same MIT License as the rest of this repository, and that you will follow
the [Code of Conduct](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/CODE_OF_CONDUCT.md).

Agent guidance is mirrored across:

- [CLAUDE.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/CLAUDE.md) + [`.claude/skills/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/.claude/skills/) (Claude Code)
- [`.cursor/rules/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/.cursor/rules/) (Cursor)
- [AGENTS.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/AGENTS.md) + [`.agents/skills/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/.agents/skills/) (Codex)
- [GEMINI.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/GEMINI.md) + [`.agent/rules/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/.agent/rules/) (Antigravity)

## Getting help

| I want to... | Go here |
|---|---|
| Read the docs | [`docs/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude/docs) |
| Ask a question | [Discussions](https://github.com/the-vibey-project/vibey/discussions) |
| Report a bug or request a feature | [Issues](https://github.com/the-vibey-project/vibey/issues) (use the templates) |
| Report a vulnerability | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/SECURITY.md) (private) |

See [SUPPORT.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/SUPPORT.md)
for the same map.

## Security

This tool bypasses Claude Code's interactive permission prompts by design
(that's what makes autonomous operation possible) and handles API
credentials. See [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/SECURITY.md) for the threat model and how
to report a vulnerability.

## Related projects

Same contract, different vendor. The two paid `*loop` runners share one domain
state machine, one set of application ports, and one `.<name>loop/runs/<id>/`
layout — pick the one that matches the agent you pay for:

| Runner | Drives | Command |
|---|---|---|
| **claudeloop** (this package) | Claude Code (Anthropic) | `claudeloop` |
| [codexloop](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex) | OpenAI Codex / GPT | `codexloop` |

Both ship inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package: one
`pip install vibey-engine` puts every command above on `PATH` (vibey ADR-0037).

Around them:

- [vibey](https://github.com/the-vibey-project/vibey) — the queue-based conductor: INTAKE, DESIGN,
  an optional VISUAL_DESIGN stage, BUILD and REVIEW, then three opt-in deployment stages. It
  drives five engines: `claudeloop` and `codexloop` (paid), and three local ones: `gptossloop`,
  the sovereign default on GPT-OSS, and the opt-in `qwenloop` on Qwen (both from the local runner
  in [`src/vibey_runners/qwen`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/qwen)),
  and `claudeloop-local`, this binary on a local profile (vibey ADR-0064). Local engines are
  preferred first. `cursorloop` and `agyloop` were retired by vibey ADR-0078. PostgreSQL-backed.
  Background reading: the [vibey research paper](https://the-vibey-project.github.io/vibey/main/paper/) ([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)) and the vibey book ([PDF](https://the-vibey-project.github.io/vibey/main/book.pdf), [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub), [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html)).
- [vibey-bootstrap](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap) — Azure Functions cross-cutting layer: App Config + Key Vault + App Insights bootstrap, Service Bus plumbing, scaffold CLI.
- [vibey-skills](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/skills) — versioned Agent Skills marketplace and deterministic context-packet engine.

No Homebrew formula is published for claudeloop; install it with `vibey-engine`.

## License

MIT — see [LICENSE](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/LICENSE).

## Where next

- [The local backend guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/local-backend.md):
  run claudeloop on your own model for free.
- [The codexloop README](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex):
  the same contract for OpenAI Codex.
- [Rate limits vs. credits](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/rate-limits-and-credits.md):
  the distinction the whole tool rests on.

## Say it in one line

claudeloop drives Claude Code from a plan to Done without a person at the keyboard, and never
mistakes exhausted credits for a rate limit that will reset.

---

Built by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com) · [more open source](https://vibewithadam.matthewsteinberger.com/open-source)
