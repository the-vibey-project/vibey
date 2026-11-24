---
description: "Reference for codexloop, the autonomous OpenAI Codex session runner inside vibey-engine: commands, flags, sandbox, exit codes and how vibey drives it."
---

# codexloop: run OpenAI Codex unattended until the task is done

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `codexloop` drives `codex exec` from a plan file to completion
> without waiting on a person, and never treats `insufficient_quota` as a rate limit that will
> reset. It ships inside `vibey-engine`. You need the Codex CLI (`codex` 0.40 or newer on `PATH`)
> signed in with `codex login` or an `OPENAI_API_KEY`. Run `codexloop doctor`, then
> `codexloop run plan.md`. In vibey it is one of the two paid engines; unlike claudeloop it takes
> no capability snapshot.

> [!IMPORTANT]
> **Work in progress — not a final product:** `codexloop` and `vibey` are in active development and not a final product. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

> **Now part of the vibey monorepo.** `codexloop` lives in [the-vibey-project/vibey](https://github.com/the-vibey-project/vibey) at [`src/vibey_runners/codex`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex) (vibey ADR-0021). It is not published on its own any more: it ships inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package, so `pip install vibey-engine` installs it (vibey ADR-0037).

[![Ships in vibey](https://img.shields.io/pypi/v/vibey-engine?label=ships%20in%20vibey)](https://pypi.org/project/vibey-engine/)
[![Python versions](https://img.shields.io/pypi/pyversions/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![CI](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/LICENSE)

**Onion-architected, autonomous OpenAI Codex / GPT session runner and
generated OpenAI SDK CLI** — never blocks on a human, never treats
`insufficient_quota` as a waitable `rate_limit_exceeded` window, and resumes
safely across usage windows.

## How to read this page

Daniel knew claudeloop already, and opened this page expecting to read it all again.

**Daniel:** Professor, is this just claudeloop for OpenAI?

**Professor Feynman:** It is the same machine with a different engine bolted in: the same states,
the same run folder, the same promise never to wait on a person. Read the quickstart and the
table that says how a 429 is classified. The command tables below are for looking things up.

**Daniel:** And what does it not do that claudeloop does?

**Professor Feynman:** It takes no capability snapshot. That is written down below, so you are not
surprised by it later.

## What problem this solves

Codex sessions hit usage limits. A `codex exec` process exiting doesn't
tell you whether the *task* finished or just that *turn* did. And an HTTP
429 from OpenAI is two different failures behind one status code:
`rate_limit_exceeded` / `usage_limit_reached` are windows that reset on
their own; `insufficient_quota` / `credit_balance_exhausted` are billing
walls that never will, no matter how long you wait. OpenAI's own guidance
is not to retry the second kind.

`codexloop` exists to get all three of those distinctions right,
automatically, so you can hand it a plan and walk away — including noticing
a top-up or a plan-window reset on the next probe rather than at some fixed
deadline.

It is a deliberate transplant of the [claudeloop](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude)
design — same state machine, same ports, same run-directory layout —
retargeted at the OpenAI stack. The primary transport is `codex exec --json`
as a subprocess, which is exactly what the official TypeScript Codex SDK does
under the hood ([ADR 0002](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/adr/0002-subprocess-codex-exec.md)).
There is **no Anthropic dependency**.

## Install

Requires **Python 3.12+**, **macOS or Linux**, and the
[Codex CLI](https://github.com/openai/codex) (`codex` ≥ 0.40 on `PATH`)
signed in via `codex login` **or** an `OPENAI_API_KEY`. Windows is not a
supported target.

```bash
pipx install vibey-engine      # or: uv tool install vibey-engine / pip install vibey-engine
                               # the whole family; codexloop is one of its console scripts
codexloop --version            # prints: codexloop 0.4.0 (or the version you installed)
codexloop doctor               # reports which auth mode is active; it never guesses
```

`vibey-engine` does not install the Codex CLI. Install it yourself, from the link above.

See the [getting-started guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/getting-started.md)
for a from-source setup.

## Quickstart

```bash
codexloop doctor                        # codex version, login status, probe strategies, MCP OAuth
codexloop capacity                      # ChatGPT plan windows when known; says so honestly when not
codexloop run plan.md --max-turns 20    # seed a run from a markdown plan and drive it to completion
codexloop run plan.md --network-access  # trusted task that needs PostgreSQL/HTTP access
codexloop resume --last                 # or: codexloop resume <thread-id>
codexloop threads                       # this product's run registry (not vendor Codex sessions)
codexloop api models list               # any OpenAI SDK endpoint (generated; see docs)

# Mid-run control (second terminal, same cwd):
codexloop status
codexloop logs
codexloop prompt --now "Also cover the error path"   # or --next-turn
codexloop model <model>                              # queued for the next control boundary
codexloop effort high                                # low | medium | high
codexloop approval never                             # approval policy
codexloop sandbox workspace-write                    # sandbox mode
codexloop watch --follow                             # or --replay for the Textual stream UI
codexloop stop                                       # graceful stop at the next control boundary
codexloop wind-down --reason "capacity exhausted"    # finish the turn, write a handoff, exit 75
codexloop savepoints
codexloop unwind 1                                   # git save-point restore (refuses while live)
```

Replace `<thread-id>` with an id from `codexloop threads`, and `<model>` with a Codex model name.

`--transport app-server` opts into the experimental Codex app-server protocol
and falls back to `exec` when it is unavailable
([ADR 0009](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/adr/0009-optional-app-server.md)).

Network access remains off by default in the `workspace-write` sandbox. Enable
it per invocation with `--network-access`, per process with
`CODEXLOOP_NETWORK_ACCESS=true`, or in `codexloop.toml` with
`network_access = true`. This permits outbound command networking generally; it
is not a localhost- or PostgreSQL-only allowlist. Use it only for trusted tasks.
Runs record the effective `sandbox_mode` and `network_access` values in
`.codexloop/runs/<run_id>/meta.json`. Because the app-server transport cannot
currently express this setting, codexloop uses the exec transport whenever it
is enabled.

## Why it's different from just retrying on 429

| | Naive retry | `codexloop` |
|---|---|---|
| Sees an HTTP 429 | Sleeps a fixed duration, retries | Classifies **body-first** — `error.code` / `error.type` before the status: `rate_limit_exceeded` and `slow_down` are short throttles, `usage_limit_reached` is a plan window, `insufficient_quota` / `credit_balance_exhausted` / `usage_not_included` are billing walls |
| Credits exhausted | Sleeps forever, no reset time exists | `CreditsExhausted` structurally has no `resets_at` field. Probes on a bounded backoff and tells you it needs you |
| Plan window (5-hour / weekly) | Guesses a sleep | Reads `Retry-After` / plan-window resets when the vendor supplies them; degrades to a bounded probe under `--max-wait`, never a blind sleep |
| Turn ends vs. task ends | A marker string, easily confused with a truncated limit message | Structured verdict via `codex exec --output-schema`, done marker (`CODEXLOOP_TASK_FULLY_COMPLETE`) as fallback, and *no signal is never completion* |
| Approval prompts | Hangs, or you reach for `--full-auto` (deprecated, then removed) | `-c approval_policy=never` **plus** `-c sandbox_mode=workspace-write` — non-blocking *and* confined; `danger-full-access` only behind a loud opt-in |
| Bare `codex` TUI | Waits on a TTY | Never invoked; the argv builder forbids it and the child is spawned with stdin closed |

See the [architecture overview](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/index.md)
and [ADR 0003 — credits exhausted](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/adr/0003-credits-exhausted.md)
for the full reasoning.

## Commands

Every command below is in `codexloop --help` and `src/codexloop/cli/app.py`.

| Command | What it does |
|---|---|
| `run PLAN` | Drive a new autonomous run from a markdown plan. Flags: `--run-id`, `--transport exec\|app-server` (default `exec`), `--model`, `--max-turns`, `--max-wait`, `--network-access` / `--no-network-access`, `--stream-ui`. |
| `resume [THREAD_ID] [--last] [--transport]` | Resume by explicit thread id (the default) or the most recent catalog entry. |
| `threads` | List this product's run registry (not vendor Codex sessions). |
| `status [RUN_ID]`, `logs [RUN_ID]` | Persisted state, and `events.jsonl`, for a run (default: the latest). |
| `runs` | List run directories under `.codexloop/runs/`. |
| `prompt TEXT (--now \| --next-turn) [--run-id]` | Queue an operator prompt. Exactly one of `--now` and `--next-turn` is required. |
| `stop [--run-id]` | Request a graceful stop at the next control boundary. |
| `wind-down [--run-id] [--reason TEXT]` | Request a graceful wind-down at the next control boundary. |
| `capacity` | ChatGPT plan windows when known; says so plainly when not. |
| `doctor [--cwd PATH]` | Auth mode, probe strategies, and other pre-flight gates. |
| `watch [RUN_ID] [--follow] [--interval S] [--replay]` | A snapshot of persisted run state, followed every `--interval` seconds (default 1.0), or the Textual stream UI. |
| `savepoints` | List numbered git save points. |
| `unwind TO [--backup \| --no-backup]` | Hard-reset to a save point (a number, sha prefix or label). Refuses while a run is live; keeps a backup ref by default. |
| `reset [--label LABEL]` | Record a save point (commit if dirty, else a ref tag only). Default label `reset`. |
| `snapshot [NAME] [--restore NAME]` | Create or restore a filesystem snapshot for the active run. |
| `model`, `effort`, `approval`, `sandbox`, `cwd` | Queue a change for the next control boundary. |
| `api …` | The generated 1:1 OpenAI SDK REST surface. |

Global flags: `--version`, `-v`/`--verbose` (more detail: `-v` debug, `-vv` also third-party
libraries, `-vvv` full payloads), `-q`/`--quiet`, `--log-level`, `--log-file`. These are
codexloop's own; vibey's `-v` prints vibey's version.

Exit codes: `0` success, `1` failure, `2` usage error, `75` wound down on purpose (a handoff was
written), `130` operator stop.

## How vibey drives codexloop

- codexloop is one of vibey's two paid engines (tier PAID). vibey prefers local engines and falls
  back to paid ones only when no local engine is eligible (vibey ADR-0038).
- **No capability snapshot.** codexloop has no `--capabilities` flag, and vibey's codexloop
  descriptor declares none (`src/vibey/infrastructure/engines/descriptors.py`). A BUILD run on
  codexloop therefore does not get the locked plugins, skills and MCP servers that vibey's loop
  capability bundle (ADR-0103) gives claudeloop and the local runner.
- vibey passes `OPENAI_API_KEY` and the `CODEXLOOP_*`, `CODEX_*`, `OPENAI_*`,
  `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` variables through to the run.

## Documentation

Full docs (MkDocs Material sources) live in the
[`docs/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/docs) directory of the vibey monorepo, starting at
[`docs/index.md`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/index.md). The standalone `codexloop` Pages site has been retired.

| | |
|---|---|
| [Getting started](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/getting-started.md) | Install, preflight, first run, transports |
| [Generated REST surface](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/guides/rest-api-surface.md) | `codexloop api …` — 1:1 over the `openai` SDK resource tree, `--provider openai\|azure\|custom`, drift gate |
| [Architecture](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/index.md) | The onion layers and the twelve [decision records](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/adr/index.md) |
| [CLI reference](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/reference/cli.md) | Command index |
| [Contributing](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/contributing.md) / [Publishing](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/publishing.md) | Setup, tests, coverage floors, publishing |
| [Plans](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/docs/plans) | Design record, vendor research notes, and the shared transplant outline (GitHub tree; not in the site nav) |
| [Changelog](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/CHANGELOG.md) | Release notes (entries up to 2026-08 were written by release-please, which vibey ADR-0028 retired) |

## Project status

Pre-1.0 (0.4.0, shipped inside `vibey-engine`). What runs today: the onion core, the `codex exec`
gateway, the layered capacity probe (exec floor, optional app-server, rollout tail), the control
plane, the generated OpenAI REST CLI with a drift gate, the optional app-server transport with
exec fallback, the `-v`/`-q` verbosity ladder, `--run-id`, wind-down, and capacity forecasting
(measurement only, off by default). The milestone labels in the plan records are history.

CI holds `domain`, `application`, `infrastructure` and `cli` to 100% coverage each, with branch
coverage on, on Python 3.12, 3.13 and 3.14, on Linux and on macOS (the `tools` job in
`.github/workflows/ci.yml`). `pytest -m system` runs a scripted agent with no OpenAI account;
`pytest -m live` is opt-in.

| Item | Value |
|---|---|
| Env prefix | `CODEXLOOP_*` |
| State dir | `.codexloop/runs/<run_id>/` |
| Auth | `OPENAI_API_KEY` **or** `codex login` (`$CODEX_HOME/auth.json`) — never mixed |
| Done marker | `CODEXLOOP_TASK_FULLY_COMPLETE` |
| Effort levels | `low` / `medium` / `high` (Codex `model_reasoning_effort`) |
| Minimum Codex CLI | 0.40 |

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/CONTRIBUTING.md) for the
gitflow branch model, Conventional Commits requirement, and how to run every
quality gate locally.

The GitHub default branch is **`develop`**. Open feature PRs into `develop`,
not `main`. By contributing you agree that your work is licensed under the
same MIT License as the rest of this repository, and that you will follow
the [Code of Conduct](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/CODE_OF_CONDUCT.md).

Agent guidance is mirrored across:

- [CLAUDE.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/CLAUDE.md) + [`.claude/skills/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/.claude/skills/) (Claude Code)
- [`.cursor/rules/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/.cursor/rules/) (Cursor)
- [AGENTS.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/AGENTS.md) + [`.agents/skills/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/.agents/skills/) (Codex)
- [GEMINI.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/GEMINI.md) + [`.agent/rules/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/.agent/rules/) (Antigravity)

## Getting help

| I want to... | Go here |
|---|---|
| Read the docs | [`docs/`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex/docs) |
| Ask a question | [Discussions](https://github.com/the-vibey-project/vibey/discussions) |
| Report a bug or request a feature | [Issues](https://github.com/the-vibey-project/vibey/issues) (use the templates) |
| Report a vulnerability | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/SECURITY.md) (private) |

See [SUPPORT.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/SUPPORT.md)
for the same map.

## Security

This tool runs Codex with `approval_policy=never` by design (that's what
makes autonomous operation possible), confines it to `sandbox_mode=workspace-write`
by default, and handles OpenAI credentials. See
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/SECURITY.md)
for the threat model and how to report a vulnerability.

## Related projects

Same contract, different vendor. The two paid `*loop` runners share one domain
state machine, one set of application ports, and one `.<name>loop/runs/<id>/`
layout — pick the one that matches the agent you pay for:

| Runner | Drives | Command |
|---|---|---|
| [claudeloop](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude) | Claude Code (Anthropic) | `claudeloop` |
| **codexloop** (this package) | OpenAI Codex / GPT | `codexloop` |

Both ship inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package: one
`pip install vibey-engine` puts every command above on `PATH` (vibey ADR-0037).

Around them:

- [vibey](https://github.com/the-vibey-project/vibey) — the queue-based conductor: INTAKE, DESIGN,
  an optional VISUAL_DESIGN stage, BUILD and REVIEW, then three opt-in deployment stages. It
  drives five engines: `claudeloop` and `codexloop` (paid), and three local ones: `gptossloop`,
  the sovereign default on GPT-OSS, and the opt-in `qwenloop` on Qwen (both from the local runner
  in [`src/vibey_runners/qwen`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/qwen)),
  and `claudeloop-local`, claudeloop on a local profile (vibey ADR-0064). Local engines are
  preferred first. `cursorloop` and `agyloop` were retired by vibey ADR-0078. PostgreSQL-backed.
  Background reading: the [vibey research paper](https://the-vibey-project.github.io/vibey/main/paper/) ([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)) and the vibey book ([PDF](https://the-vibey-project.github.io/vibey/main/book.pdf), [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub), [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html)).
- [vibey-bootstrap](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap) — Azure Functions cross-cutting layer: App Config + Key Vault + App Insights bootstrap, Service Bus plumbing, scaffold CLI.
- [vibey-skills](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/skills) — versioned Agent Skills marketplace and deterministic context-packet engine.

No Homebrew formula is published for codexloop; install it with `vibey-engine`.

## License

MIT — see [LICENSE](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/LICENSE).

## Where next

- [Getting started](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/getting-started.md):
  preflight and a first run, step by step.
- [The claudeloop README](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude):
  the same contract for Claude Code, with capability snapshots and a free local profile.
- [ADR 0003 — credits exhausted](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/codex/docs/architecture/adr/0003-credits-exhausted.md):
  why a billing wall is never waited on.

## Say it in one line

codexloop drives `codex exec` from a plan to Done without a person at the keyboard, and reads a
429's body to tell a rate limit that resets from a billing wall that never will.

---

Built by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com) · [more open source](https://vibewithadam.matthewsteinberger.com/open-source)
