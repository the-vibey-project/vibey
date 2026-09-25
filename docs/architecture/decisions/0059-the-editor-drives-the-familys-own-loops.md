# 0059 — The editor drives the family's own loops, on a copy, and adds no loop of its own

**Status:** accepted · **Date:** 2026-09-24 · **Cites:** sub-doctrines 8.b, 8.c, 8.j, 9.b, 10.f, 10.g, 10.h, 12.c, 12.d, 12.e · **Related:** ADR-0005, ADR-0016, ADR-0017, ADR-0018, ADR-0023, ADR-0045, ADR-0055, ADR-0057, ADR-0058 · **Issue:** #290

**Superseded in part** by the change `feat(engines)!: remove the repealed opencodeloop engine` (2026-09-25): the `opencode` engine and its runner are deleted, so `vibey loops` lists no repealed engine today; the extension keeps the rule for any engine 8.b repeals while its code remains.

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
`docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`, the guide
`docs/guides/vscode-extension.md` at the top of the Guides nav, and the extension's own README.
It leaves three debts open, named under *Consequences*: the golden `vibey loops --json` the
catalogue parser should read in place of its fixture, the Open VSX token only the operator can
create, and the CI job's promotion to a required check.

## Context

The operator wants to drive vibey, and vibey's own development, from VS Code with the local
model and without Claude Code: the sovereign version. The first job the extension has is the
beginner-first rewrite of vibey's documentation, run unattended as a batch of task files.

Everything such an extension needs already exists in the family. qwenloop is the local agent
that turns a plan into tool calls against gpt-oss:20b through Ollama. vibey knows the loops,
the effort ladder, the projects, the gates and the budgets. vibey-skills compiles context from
plugins. storm tooling knows how to keep work on durable storage. The question this record
answers is where the extension's own code stops.

## Decision

1. **No agent loop in TypeScript.** A task is a qwenloop run (or another family runner's, on
   paidloop), started from the command line the runner's descriptor declares. The extension
   reads the run's `events.jsonl` by byte offset (10.g) and shows it. Where a runner lacked
   something the extension needed, the runner was fixed, not bypassed: qwenloop now consumes
   the follow-ups `qwenloop prompt` writes, at the next turn boundary, once and in order.
2. **vibey through its own commands, never its database.** Projects, gates, statuses, answers,
   budgets and the loop catalogue come from `vibey projects`, `vibey gates`, `vibey status`,
   `vibey answer`, `vibey budget` and `vibey loops --json`. When a vibey lacks one, the
   extension names the release that adds it; it never falls back to SQL.
3. **No engine facts of its own.** Loops, efforts, engines, models, capabilities, controls and
   event envelopes are read from `vibey loops --json` (the contract amended after #1131's
   review). Without it, the extension runs a declared degraded catalogue (sovereignloop,
   qwenloop on the configured model, effort auto) and says so. Auto mode selects within a tier
   by vibey's smooth weighted round robin (ADR-0005), prefers a model Ollama already holds,
   climbs vibey's ladder on a failed attempt, and records every choice and its reason.
   A repealed engine (OpenCode, by 8.b) is listed and never run. paidloop runs only once
   declared, with a daily or monthly dollar cap or a no-cap declaration confirmed twice.
4. **Every task works on a copy.** A task gets a git worktree of its own under the storm
   home, on `vibey/<slug>-<id>`, from one recorded base. The storm home must be durable
   (10.h, ADR-0057); the extension refuses a volatile one with exit 78, as storm tooling
   does. Finished work is committed on the task's branch with the repository's own hooks. A
   refusal is recorded and shown, never bypassed (12.d). A task file may name its scope
   (`paths:`): its commit holds only matching changes, and anything else is left uncommitted
   and named. A person applies, reviews or discards a task; nothing lands on their branch
   without them.
5. **Nothing that names a database, a password or vibey's own settings reaches a model.**
   A model-driven process gets an allow-listed environment: the basics, and the names its
   runner declares. `VIBEY_*`, `PG*`, names containing `DSN`, `DATABASE_URL`, `PASSWORD` or
   `PASSWD`, and any `postgres://` value never cross, whoever declares them (PR #1093's rule,
   applied here and tested for every child the extension starts).
6. **One run at a time on a machine's model, by measurement.** The model slot is the family's
   `mkdir` lock, shared through `VIBEY_OLLAMA_LOCK` with vibey-gh and storm tooling. A lock
   whose holder writes no owner file is never broken. `vibey.maxConcurrentRuns` defaults to
   one, the measured ideal for gpt-oss:20b on a 24 GB Mac (8.c, ADR-0058).
7. **Nothing is stopped for being slow.** A local turn can take minutes: a long quiet spell
   produces a hint, never an action. Stop asks the runner to finish its turn. Force stop is a
   separate act, confirmed, open only after a fair wait, and journaled.
8. **One core, two front ends.** The core (`clients/vscode/src/core`) imports nothing of
   VS Code, holds every class beside its interface (9.b, ADR-0016), and carries a 100% floor of
   lines, branches, functions and statements, like the Python layers (ADR-0023). The editor
   and the headless `vibey-vscode` command are both thin over it, so a batch run from a
   terminal behaves exactly like one run from the editor, with the same journals. A batch's
   journal is append-only JSON lines, each fsynced before the next step. Running the same
   command again resumes it, from the same base, and a stop or an infrastructure error halts
   it rather than failing every remaining task the same way.
9. **One command table.** The Command Palette, the views' menus, the status-bar menu, the task
   panel's slash commands and the `@vibey` chat participant all come from one table, and tests
   fail when package.json, the README or the handlers disagree with it.
10. **Node stays out of the runtime image.** The extension has no runtime dependency, is built
    and tested by its own CI job, and never enters the container image.

## Consequences

- The documentation rewrite runs as `vibey-vscode batch` against the repository, one task
  file per page, each scoped with `paths:` so a model that edits the project's dependencies to
  run its checks cannot commit them.
- qwenloop's descriptor can declare its prompt control again once the follow-up fix ships; until
  `vibey loops` says so, the extension offers no prompt box for it, because a released qwenloop
  reads none.
- **Owed:** the catalogue parser's tests should read vibey's golden `vibey loops --json`
  (produced by vibey's own suite) in place of the extension's fixture, once that file lands, so
  the producer and the consumer cannot drift (12.e).
- **Owed:** Open VSX publishing is declared in the release workflow and runs only when an
  `OVSX_PAT` secret exists. Creating that token needs the operator's Open VSX account; using
  the extension needs no account.
- **Owed:** the `vscode-extension` CI job is not a required check yet. It becomes one once it
  has run green on develop.
