# vibey — open-source orchestration for AI coding agents

AI coding agents can write the code. Getting it delivered still takes a person:
re-prompting an agent that lost the thread, re-explaining everything after a crash,
restarting the run when one vendor's credits give out at 2 a.m.

**vibey is a free, open-source orchestrator for AI coding agents** — a program that runs
a team of them for you. It interviews you until the specification is precise, builds
unattended on local or paid agents, stops only for the decisions that are yours, and
writes every step to a record that can only be added to — an append-only ledger in a
PostgreSQL database — so a crashed or out-of-credit agent's work is picked up again
rather than lost.

**Never written code?** You can still read this. *Code* is text files of
instructions computers run; an *AI coding agent* is a program that writes and
edits that code from plain-English requests; *deploying* means putting the
finished software somewhere people can use it. vibey's job is to manage a
team of those agents from your first description to deployed software, the
way a project manager runs a team — asking you questions up front, checking
the work, and only interrupting you when a decision is truly yours.

**Who it is for:** developers who already use Claude Code, Codex or a local model
and want finished, reviewed work rather than one session at a time; people who run it for
a team on their own hardware or on Kubernetes; and anyone who wants to study or extend a
working design for durable, auditable agent orchestration.

**What makes it different** — each claim links to what proves it:

- **A crash loses no job.** Jobs are held under expiring leases and reclaimed when a worker dies. A [chaos test](tests/infrastructure/db/test_chaos.py) runs 8 workers through 500 jobs, abandoning each claim with probability 0.2, and passes only if no job is lost or committed twice — [the case study](docs/case-studies/how-vibey-survives-a-crashed-agent.md) tells how.
- **The record cannot be quietly rewritten.** The database refuses every update and delete to the ledger ([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)), and a SHA-256 hash chain over its events makes any edit visible ([`ledger_chain.py`](src/vibey/domain/ledger_chain.py)).
- **Local first, paid by choice.** The default engine runs GPT-OSS 20B on your own machine through Ollama ([ADR-0064](docs/architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)); a paid engine runs only when no local one can ([ADR-0038](docs/architecture/decisions/0038-local-engines-are-preferred-first.md)).
- **You decide what matters.** Design, review and deployment wait for your recorded answer, and a waiting question parks its job instead of blocking a worker ([ADR-0009](docs/architecture/decisions/0009-human-gates-are-parked-jobs.md)).
- **Held to gates it cannot talk its way past.** vibey's four code layers each need 100% branch coverage to merge ([ADR-0023](docs/architecture/decisions/0023-four-layers-four-floors.md)), every hard call is argued in a [decision record](docs/architecture/decisions/) (80 ADRs), and releases publish through PyPI trusted publishing with no stored token ([`vibey-engine.yml`](.github/workflows/vibey-engine.yml)).

**Try it** — Python 3.12+ and PostgreSQL 14+, on macOS or Linux:

```bash
uv tool install vibey-engine   # or: pipx install vibey-engine
vibey doctor                   # checks engines, local PostgreSQL, and the ledger guard
```

The full setup is under [Install](#install), then [Quickstart](#quickstart). Came with a
specific problem? [What do you want to do?](docs/guides/outcomes/index.md) answers six,
from running agents on your own hardware to capping what they spend.

**Contribute in your first hour.** Clone, `uv sync --extra dev`, run one test, make one
small change: [the first-hour guide](CONTRIBUTING.md#your-first-hour) walks it command
by command, from a [good first issue](https://github.com/the-vibey-project/vibey/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
to your pull request. The project governs itself by written law — start with
[the Constitution](src/vibey_tools/gh/docs/constitution.md).

---

[![PyPI](https://img.shields.io/pypi/v/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![PyPI downloads](https://img.shields.io/pypi/dm/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![Python versions](https://img.shields.io/pypi/pyversions/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![CI](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/the-vibey-project/vibey/blob/develop/LICENSE)
[![Docs](https://img.shields.io/badge/docs-read-blue.svg)](https://the-vibey-project.github.io/vibey/main/)
[![Research paper](https://img.shields.io/badge/paper-PDF%20%7C%20HTML-6f42c1.svg)](https://the-vibey-project.github.io/vibey/main/paper.pdf)
[![Book](https://img.shields.io/badge/book-PDF%20%7C%20EPUB-0a7ea4.svg)](https://the-vibey-project.github.io/vibey/main/book.pdf)

**Prefer to read first?** The design is a research paper — [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) · [HTML](https://the-vibey-project.github.io/vibey/main/paper/) —
and the whole documentation is a book — [PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print](https://the-vibey-project.github.io/vibey/main/book-print.html).

The project and its engine are **vibey**; every app and interface a person uses is
**krypton** (sub-doctrine 9.e), whose emblem is the krypton atom: krypton-84, four shells.

For the precise version: a queue-based, six-phase conductor for autonomous
software delivery — with an optional visual-design interstitial and opt-in
Azure deployment — built on top of the [`*loop` autonomous session
runners](src/vibey_runners/), which live in this repository as uv
workspace members (ADR-0021).

## What problem this solves

An autonomous coding session is not autonomous software delivery. A single
`claudeloop` run can finish a task, but it cannot interview you until the spec
is sharp, split the work into parallel items, verify each one against gates it
cannot game, survive its own credit exhaustion by handing off to a different
vendor's engine *without losing a single open question*, or know that a review
finding should reopen design rather than vanish into a transcript.

vibey conducts all of that. You describe what you want; it interviews you until
the spec is sharp, builds unattended across a pool of engines with real budget
caps, reviews the result with you, and (only if you opt in) deploys. Every
choice, finding, and handoff lives in an append-only PostgreSQL ledger — never
in one vendor's chat session.

| | |
|---|---|
| Runs on | macOS / Linux, local. No cloud control plane required. |
| Language | Python 3.12+ |
| Queue | PostgreSQL (`FOR UPDATE SKIP LOCKED`) |
| Engines | [`claudeloop`](src/vibey_runners/claude), [`codexloop`](src/vibey_runners/codex) — plus the local runner [`src/vibey_runners/qwen`](src/vibey_runners/qwen) as two engines — `gptossloop`, the sovereign default on GPT-OSS 20B (on by default, and the sovereign DESIGN provider), and the opt-in `qwenloop` on Qwen — and `claudeloop-local`, the claudeloop binary on a local backend profile. Local engines are preferred first when switched on (ADR-0015, ADR-0027, ADR-0038, ADR-0064). All three runners ship inside the `vibey-engine` package (ADR-0037). |
| State dir | `.vibey/` |
| Env prefix | `VIBEY_` |
| Done marker | Each loop's own marker (`CLAUDELOOP_TASK_FULLY_COMPLETE`, `QWENLOOP_TASK_FULLY_COMPLETE`, etc.) |

## Install

Requires **Python 3.12+** and **PostgreSQL 14+**. Windows is not a supported
target. vibey supports every currently supported PostgreSQL major (14–18),
and CI runs the database suite against each one. Every database-backed command
reads the connection string from `VIBEY_PG_URL`; vibey never guesses a
database and exits with `VIBEY_PG_URL is not set` when it is missing.

Memory, disk, GPU, network and each krypton client's needs are on the
[system requirements](docs/reference/system-requirements.md) page. Those figures are
re-measured every week, and any figure that could not be re-measured is marked stale.
For the sovereign default (a local model), memory is the binding constraint.

Prefer a ready-built file? Every release on GitHub also carries the user interfaces built
for each supported platform: krypton desktop for Linux (a Flatpak bundle and an Ubuntu
build, x86_64 and arm64) and, from 3.4.0, for macOS on Apple silicon (a self-contained
`.dmg`), the krypton app for Android, the web and, from 3.4.0, iOS (signed for TestFlight
and the App Store), krypton for VS Code (also on Open VSX), and the Python wheels below,
with checksums and build provenance. The
[downloads page](docs/guides/downloads.md) lists each file, what it runs on and whether it is signed.

One install is the whole family: `vibey`, all six `*loop` engine commands, and the
tools (`vibey-gh`, `vibey-skills`, `vibey-bootstrap`) ship in the one `vibey-engine`
distribution and land on `PATH` together (ADR-0037). What each engine still
needs separately is its own vendor CLI and credentials — which is what
`vibey doctor` checks.

```bash
uv tool install vibey-engine          # or: pipx install vibey-engine / pip install vibey-engine
vibey install --postgres       # install/start local PostgreSQL 18 when needed, then set
                               # the scram-sha-256 pg_hba.conf lines in SECURITY.md §7
export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey # the application
# The owner's DSN is given to `vibey migrate` alone, for that one command -- never exported,
# so no worker, engine session or gate command ever holds it:
VIBEY_PG_MIGRATE_URL=postgresql://user@localhost:5432/vibey vibey migrate
vibey doctor                   # pre-flight: engines, and whether the ledger is guarded
```

Two DSNs, because the ledger is append-only by the database
([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)):
the application connects as a role that can read and append to the ledger and nothing
more. One DSN still works, but `vibey doctor` fails its `ledger-guard` check until the
roles are split ([database roles](docs/reference/configuration.md#database-roles)).

`vibey install --postgres` uses Homebrew, apt, or dnf to install and start the
current stable PostgreSQL major. `vibey doctor` reports local PostgreSQL
readiness as well as engine health; `vibey doctor --install-postgres` performs
the same explicit installation before checking. `--record` also writes engine
results to the database for a project, and `--cluster` runs the in-cluster
preflight (DSN, workspace, secrets, database, migrations) instead.

`gptossloop` and `qwenloop` install with everything else; what is opt-in is the
*feature*, not the install. Each local engine has a switch: `gptossloop` — the
sovereign default on GPT-OSS 20B — is on unless `VIBEY_FEATURE_GPTOSSLOOP=0`;
`qwenloop` — the same runner on `qwen3:14b` — needs `VIBEY_FEATURE_QWENLOOP=1`;
and `claudeloop-local` (claudeloop on a local backend profile) needs
`VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` (ADR-0064). A switched-on local engine is
**preferred first** for BUILD — a paid engine runs only when no local one is
eligible — and `vibey doctor` lists it; `vibey doctor` also honours
`[features] gptossloop = false` / `qwenloop = true` / `claudeloop_local = true`
in a `./vibey.toml`. With no `--provider`, `vibey work` and `vibey worker` run
DESIGN and DECOMPOSE on the sovereign gptossloop providers too (ADR-0038).
`VIBEY_OLLAMA_URL` is the one endpoint setting; the
[local models guide](docs/guides/local-models-ollama.md) has the Ollama recipe.

To add deterministic, budgeted context packets from the `vibey-skills`
marketplace, enable it per project — `vibey-skills` ships in the same
distribution, so there is nothing extra to install:

```bash
vibey new my-app --repo ~/src/my-app \
  --skills-context-mode shadow --skills-context-budget 6000
```

`shadow` builds and records packet provenance without changing agent prompts.
After observing results, switch the project config to `inject` to append successful
packets to BUILD prompts. Missing tools, timeouts, low-confidence retrieval, and
insufficient budgets all fall back to the original prompt. The feature is off by
default, and wind-down prompts are never modified (ADR-0031).

The same tree is a Claude Code plugin marketplace — every plugin in the family, the 138
skills plugins and vibey-gh's four, from one address and nothing else:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install security-principles@vibey
/plugin                                    # browse all 142
```

The root manifest is rendered from the workspace members by `vibey-gh marketplace` and
held to them by `vibey-gh check` (ADR-0034); it is never edited by hand. Since the family
ships as one distribution (ADR-0037) this root manifest is the only marketplace there is.

## Quickstart

```bash
export VIBEY_PG_URL=postgresql://user@localhost:5432/vibey
vibey new my-app --repo ~/src/my-app \
  --max-cycle-dollars 15                     # real budget brake, enforced from the ledger
vibey doctor --conformance --record          # verify each engine's contract, persist health for the latest project
vibey worker --provider claudeloop \
  --engines claudeloop,codexloop -j 2        # live DESIGN provider; unattended build across the pool

# When vibey parks for your input (design gates, review, budget grants):
vibey gates                                  # each open gate, its prompt, and the command that answers it
vibey answer <gate-id> --defaults            # accept the interview defaults, or:
vibey answer <gate-id> --raw '{"max_dollars": 25}'   # raise a tripped budget cap
vibey design accept <project-id> --no-visual
vibey answer <gate-id> --verdict accept      # review demo
vibey answer <gate-id> --choice local_only   # decline deployment → DONE (local)
```

`vibey doctor --record` needs a project to record against, so run it after
`vibey new`. `vibey worker` defaults to `--provider gptossloop`, the sovereign
DESIGN interview and BUILD decomposition on a local model; pass
`--provider claudeloop` for the same on a paid engine, or `--provider scripted`
for the test double. `--provider qwenloop` is still accepted and read as
gptossloop (ADR-0064).
`vibey gates` lists every open gate with its id, its prompt, and the exact
`vibey answer` command that answers it (`vibey gates <project-id>` for one
project); `vibey projects` lists your projects, their ids, and how many gates
each is waiting on. Both take `--json`.

The [greeter live-demo runbook](docs/guides/greeter-live-demo.md) walks a full
paid run end to end, including the zero-touch contracts.

## Command reference

Every command's flags and defaults are in the
[CLI reference](docs/reference/cli.md). The most common ones:

| Command | What it does |
|---|---|
| `vibey doctor` | Pre-flight: engine install state, versions, auth; `--conformance` runs the 9-check suite, `--record` persists health, `--cluster` runs the in-cluster preflight. |
| `vibey new` | Create a project and enqueue its first DESIGN interview. |
| `vibey worker` | Long-running worker: dispatches jobs across every phase (`--provider scripted\|claudeloop\|gptossloop`, `--engines`, `-j`, `--azure memory\|az`). |
| `vibey work` | Process one ready DESIGN or VISUAL_DESIGN job for a project (foreground, capped). |
| `vibey answer` | Answer a parked human gate. |
| `vibey design resume/accept` / `vibey visual accept/waive` | Resume or accept DESIGN; accept or waive VISUAL_DESIGN. |
| `vibey watch` / `vibey status` | Live dashboard, or one-shot status (`--json` for scripting). |
| `vibey engines` / `vibey cost` / `vibey ledger show` | Engine health, budget spend, and event-ledger inspection. |
| `vibey budget` / `budget set` / `budget clear` | A project's per-cycle caps and spend, and changing the caps after creation (`--json` for scripting). |
| `vibey deploy status/inspect/plan/cancel/rollback` | Inspect and control Phases ④–⑥. |
| `vibey recover` | Recover jobs stuck under a dead worker's lease. |
| `vibey operator` | Run the Kubernetes operator (`pip install 'vibey-engine[operator]'`; ADR-0025). |

## Configuration

`vibey.toml`'s schema — `[project]`, `[isolation]`, `[budget]`, `[engines]` (with
`[engines.claudeloop_local]`), `[phases.design/build/review]`, `[provision]`,
`[deploy]`, `[notifications]`, `[telemetry]`, `[features]`, `[qwenloop]`,
`[queue.priority]`, `[queue.reap]`, and the operational surfaces `[tracker]`,
`[docs]`, `[secrets]`, `[files]`, `[email]`, `[sms]`, `[messaging]`,
`[config_store]`, `[cache]`, `[bus]`, `[blob]` and `[siem]` — is implemented and
unit-tested in `domain/config.py` (`parse_config`) and
`infrastructure/config_loader.py`. `[verify]`, `[gates]`, `[engine_environment]`,
`[failover]`, `[hub]` and `[sabbath]` are read by their own loaders. Defaults and an
example file are in the [configuration reference](docs/reference/configuration.md).
The local-engine keys are read at runtime today: `[features] gptossloop`,
`[features] qwenloop`, `[features] claudeloop_local` and
`[engines.claudeloop_local]`. `vibey doctor` and `vibey loops`
read them from `./vibey.toml` in the current directory, and the worker reads the
same keys from the project's stored config (which no CLI flag sets yet);
`VIBEY_FEATURE_GPTOSSLOOP`, `VIBEY_FEATURE_QWENLOOP`,
`VIBEY_FEATURE_CLAUDELOOP_LOCAL` and
`VIBEY_CLAUDELOOP_LOCAL_PROFILE` override them. `[notifications]`,
`[telemetry]`, `[gates]` and `[engine_environment]` are copied from the
repository's `vibey.toml` into the stored project config by `vibey new`; the
worker and lifecycle repository then use those settings. Telemetry is an in-process recorder for now, so it is available
to the running app but has no external exporter yet.

What does configure a project today is a handful of `vibey new` CLI flags
(`--max-cycles`, `--max-cycle-dollars`, `--max-cycle-turns`,
`--skills-context-mode`, `--skills-context-budget`) recorded directly into
that project's stored config at creation time — see the
[CLI reference](docs/reference/cli.md). The two caps can be changed after that:
`vibey budget set` and `vibey budget clear` rewrite them in the stored config,
record each change on the ledger, and bind the next BUILD session of a worker
already running.

## Notifications

`infrastructure/notify/` implements a `NotificationService` that dispatches
desktop alerts and HMAC-SHA256-signed webhooks (`X-Vibey-Signature`, see
[SECURITY.md](SECURITY.md#6-webhook-payload-integrity--implemented-unit-tested-and-active-when-configured)), and it is covered
by tests. `build_app()` constructs it; workers notify on newly raised gates,
and project transitions notify on phase changes and completion. Enable it in
the repository TOML with `[notifications] enabled = true`; `vibey new` stores
that table with the project.

## Telemetry

`infrastructure/otel.py` implements `TelemetryTracer` (span tracing for
jobs, turns, and handoffs) and `TelemetryMetrics` (engine-selection,
queue-latency, phase-duration, handoff-failure, and cost-spend counters),
plus `calculate_rotation_fairness()` for measuring rotation fairness against
declared engine weights. It is covered by unit tests and constructed by
`build_app()`. The worker records queue latency, phase duration, and job spans;
BUILD records engine turns, selections, handoffs, and cost spend. Set
`[telemetry] enabled = false` to disable those runtime calls for a project.

## The shape of it

```
  DELIVERY STAGE SET
  INTAKE → ① DESIGN ──┬─ no ───────────────→ ② BUILD ⇄ ③ REVIEW
             ▲        │                       autonomous / interactive
             │        └─ yes → [VISUAL DESIGN]
             │                  interactive, media generation + confirmation
             │                            │ visual-ready
             │                            └──────────────→ ② BUILD
             │
             └─ loop-back from ② BUILD or ③ REVIEW: a finding needs clarification

  ③ REVIEW ── no deployment ─────────────────────────────→ DONE (local)
       │ opt in
       ▼
  DEPLOYMENT STAGE SET
  ④ DEPLOY DESIGN → ⑤ DEPLOY EXECUTE → ⑥ DEPLOY REVIEW → DONE (deployed)
       interactive       autonomous          interactive
             ▲                 ▲                    │
             └─────────────────┴────────────────────┘
                  ⑥ can also route a defect back to ①, ②, or ③
```

**The six phases** — ① Design · ② Build · ③ Review · ④ Deploy Design ·
⑤ Deploy Execute · ⑥ Deploy Review. The circled numbers above are these;
**bold** below means the phase talks to you.

**① Design** → ② Build → **③ Review** → **④ Deploy Design** → ⑤ Deploy Execute → **⑥ Deploy Review**

Phases 1, 3, 4, and 6 talk to you. The optional Visual Design stage also talks to
you and cannot hand work to BUILD until every planned visual is accepted or you
explicitly waive the stage. Phases 2 and 5 run unattended, survive rate-limit
windows and credit exhaustion, and rotate eligible engines/providers when one
runs dry. Phase 3 asks whether to deploy; "no" is a successful local completion.
Phase 6 accepts a successful deployment, requests changed deployment details in
Phase 4, retries an unambiguous deployment in Phase 5, or routes an application
defect back to the appropriate delivery phase.

## How it fits together

```
  you ──► vibey CLI · krypton apps and the VS Code extension (through the hub)
            │ answers to gates               ▲ questions, reviews, budget parks
            ▼                                │
  ┌─────────────────────── vibey conductor ───────────────────────┐
  │  six-phase machine  ·  human gates  ·  budget brake  ·  handoff │
  └──────────┬────────────────────────────────────┬────────────────┘
             │ claims jobs under leases            │ appends every event first
             ▼                                     ▼
   PostgreSQL job queue                 append-only ledger in PostgreSQL
   (FOR UPDATE SKIP LOCKED)             (no update, no delete; hash-chained)
             │
             ▼ one engine per job, local engines first
   gptossloop · qwenloop · claudeloop-local        on your machine
   claudeloop · codexloop                          paid, when you allow them
             │
             ▼
   one git worktree per work item ──► your repository
```

The same picture in words: you talk to vibey through its command line or the krypton
apps. The conductor runs the six phases, parks a job whenever it needs your answer, and
enforces your budget. Workers claim jobs from a PostgreSQL queue under leases that expire
if a worker dies. Every decision, question, answer and handoff is appended to a ledger
in the same database before it takes effect, and the database refuses to change or
delete what is written there. Each job runs on one engine — a local model first, a paid
engine only when no local one can — inside its own git worktree, and finished work lands
in your repository. The [architecture map](docs/project.mmd) shows every layer.

## Why it isn't just another agent framework

The hard part is not calling an LLM in a loop — `claudeloop` and its siblings
already solve that, including the distinction between a waitable rate-limit
window and exhausted credits that no amount of waiting will fix. vibey adds the
things those runners deliberately do not do:

1. **A phase machine with loop-backs**, so a review finding becomes a new design
   conversation rather than a lost note.
2. **Round-robin engine rotation with lossless handoff** — the conversation is an
   append-only event ledger, not a chat transcript locked inside one vendor's
   session, so any engine can pick up where any other left off. A handoff that
   would lose an open question, decision, assumption, or finding is rejected by
   a pure, deterministic no-loss gate — never silently accepted.
3. **A durable queue**, so work survives a laptop lid closing, a crash, or a
   provider outage, and so multiple work items build in parallel in isolated
   git worktrees.
4. **Real money brakes** — per-cycle dollar and turn caps summed from the
   ledger's own cost events, with parks that tell you the exact command to
   grant more.

## Questions people ask

### What is vibey?

vibey is a free, open-source orchestrator for AI coding agents: it interviews you until
the specification is precise, builds unattended on local or paid agents, stops only for
the decisions that are yours, and records every step in an append-only PostgreSQL ledger.
It is written in Python, MIT-licensed, and runs on macOS and Linux.

### What happens if an AI agent crashes mid-task?

Its job is not lost. A worker holds each job under a lease it must keep renewing; when
the worker dies the lease runs out, a reaper returns the job to the queue, and another
worker picks it up. A late commit from the dead worker is refused, so the job is not
committed twice. Because every question and decision is in the ledger rather than in the
dead session, the next engine starts from the same place. The
[crash case study](docs/case-studies/how-vibey-survives-a-crashed-agent.md) walks
through the design, the chaos test behind it, and what it costs.

### Can vibey run without sending code to a cloud model?

Yes. The default engine, `gptossloop`, runs GPT-OSS 20B on your own machine through
[Ollama](docs/guides/local-models-ollama.md), and with no `--provider`, the design
interview and the work plan run on local models too. To keep every job on your machine,
allow only the local engine:

```bash
vibey worker --provider gptossloop --engines gptossloop
```

With that allow-list the only models vibey calls are the ones running on your machine
([ADR-0038](docs/architecture/decisions/0038-local-engines-are-preferred-first.md),
[ADR-0064](docs/architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)).

### How does vibey keep an audit trail?

Every decision, question, answer, handoff, cost and phase change is appended to a ledger
in PostgreSQL before it takes effect. The database refuses to update or delete a ledger
row, and the application connects as a role that could not rewrite one anyway
([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md));
a SHA-256 hash chain over the events makes any edit detectable. `vibey ledger show`
reads it, and `vibey ledger export` publishes a redacted projection
([what gets published](docs/guides/ledger-publication.md)).

### What happens when an engine runs out of credits?

The work moves to another engine; it does not wait. vibey writes a handoff brief and
checks it with a deterministic no-loss gate — no model involved — that rejects any brief
missing an open question, decision, assumption or finding. A failing brief is retried,
then replaced by the full transcript, then brought to you; it is never passed on with
gaps ([ADR-0004](docs/architecture/decisions/0004-no-loss-gate-on-handoff.md)).

### Does vibey replace Claude Code or Codex?

No — it drives them. Each engine is a `*loop` runner around a vendor's own tool or a
local model ([ADR-0001](docs/architecture/decisions/0001-orchestrate-do-not-reimplement.md)).
vibey adds what a single session cannot do: a durable queue, a shared ledger, human
gates, budget caps, and rotation between engines.

### Where does a person stay in control?

At four gates: the design interview, the review, and the design and review of a
deployment. Each one waits for your recorded answer, and `vibey gates` lists every gate
that is open. Budgets cap the dollars and turns each cycle may spend, and a tripped cap
parks with the exact command that grants more. Nothing is deployed unless you opt in.

### How do I start contributing?

Follow [your first hour](CONTRIBUTING.md#your-first-hour): clone, install with uv, run a
first test, make one small change, and open a pull request into `develop`. Questions are
welcome on [Discord](https://discord.gg/Qvu8aYnVS) and in
[Discussions](https://github.com/the-vibey-project/vibey/discussions).

## Documentation

| Document | What's in it |
|---|---|
| [Architecture map](docs/project.mmd) | Comprehensive Mermaid diagram: every layer, the six phases, the ledger/handoff data flow, the security boundary, and the release channels |
| [Research paper](https://the-vibey-project.github.io/vibey/main/paper/) · [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) | *Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents* — the ledger invariant, queue semantics and gate soundness, the engine family, the exact-head release calculus, and a measured production-rate regularity with its falsification conditions: the family's one paper |
| [The book](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html) | Every page of the documentation site, in reading order, as one downloadable book |
| [What do you want to do?](docs/guides/outcomes/index.md) | Six outcome guides — local-only agents, spending caps, a tamper-evident record, review before merge, deployment without stored cloud secrets, regulated environments — each with commands, evidence and limits |
| [CLI reference](docs/reference/cli.md) | Every command, subcommand, flag, and default |
| [Configuration reference](docs/reference/configuration.md) | The full `vibey.toml` schema, with defaults and an example file |
| [System requirements](docs/reference/system-requirements.md) | Hardware, software, network and per-client requirements, re-measured weekly, with what is measured, derived or stale |
| [How far vibey is from full autonomy](docs/reference/autonomy.md) | The delivery loop's stages, each measured weekly from the forge, the review canary, the code and the local queue, with what would close each gap |
| [Host health](docs/reference/host-health.md) | The machine vibey runs on, measured weekly on the host itself (SSD, battery, memory and swap, thermals, generation rate), with a forecast of when it needs replacing |
| [Host optimization](docs/runbooks/host-optimization.md) | The host's measured memory and SSD-write budget, and its declared, gated and reversible tuning plan in three classes |
| [How vibey survives a crashed agent](docs/case-studies/how-vibey-survives-a-crashed-agent.md) | A case study: the problem, the fixes that fail, the lease-and-ledger design, the chaos test that checks it, and what it costs |
| [Convergence-Driven Development](docs/guides/convergence-driven-development.md) | The CDD loop above SDD and TDD, convergence/divergence checks at four scopes, the atom model, and delivery evidence |
| [Kubernetes guide](docs/guides/kubernetes.md) | Container, Helm chart, KEDA autoscaling, and its own troubleshooting section |
| [Greeter live-demo runbook](docs/guides/greeter-live-demo.md) | A full paid run, end to end, with the zero-touch contracts |
| [What gets published](docs/guides/ledger-publication.md) | What `vibey ledger export` publishes of a ledger, what it withholds, and how it counts both |
| [Expansion runbooks](docs/runbooks/expansion/) | 21 workstreams: JIRA, more clouds, Kubernetes server mode, clients, store submissions, … |
| [Architecture & roadmap](docs/plans/architecture-and-roadmap.md) | The master design: context, containers, layers, phases, risks, milestones |
| [Domain model](docs/plans/domain-model.md) | Every value object, ADT, and invariant in `domain/` |
| [Data model](docs/plans/data-model.md) | Full PostgreSQL DDL, queue semantics, indices |
| [Handoff protocol](docs/plans/handoff-protocol.md) | The event ledger, the envelope, and the no-loss gate |
| [Rotation & engines](docs/plans/rotation-and-engines.md) | Capability matrix, effort normalization, smooth weighted round robin |
| [Phase protocols](docs/plans/phase-protocols.md) | What all six phases do, turn by turn |
| [Implementation plan](docs/plans/implementation-plan.md) | Milestone-by-milestone, test-first task breakdown |
| [CLAUDE.md](CLAUDE.md) | The short facts file every coding agent working on vibey loads first: non-negotiables, layer map, gate commands |
| [Decision records](docs/architecture/decisions/) | Why each hard call was made (80 ADRs) |

## Status

<!-- BEGIN GENERATED autonomy:summary — regenerated by scripts/autonomy_scorecard.py -->
**Distance from full autonomy: 1 of 11 stages autonomous (3 partial, 6 manual, 1 unknown)**, measured at 2026-10-02 11:39Z from the forge, the review canary, the code and the local queue. Not yet autonomous: DESIGN resolves without a person (partial), BUILD runs unattended (unknown), Paid engines stay available (manual), REVIEW resolves without a person (partial), The pull-request review reaches a verdict (manual), Approval comes from the delegated approver (manual), Merges land without the operator (manual), Promotion and release run without hand steps (manual), CI stays green without human re-runs (partial), The queue delivers projects to DONE (manual). Each stage's metric, threshold, evidence and what would close it are on [How far vibey is from full autonomy](docs/reference/autonomy.md); the record is [`docs/architecture/evidence/autonomy-scorecard.jsonl`](https://github.com/the-vibey-project/vibey/blob/develop/docs/architecture/evidence/autonomy-scorecard.jsonl). *Regenerated by `scripts/autonomy_scorecard.py`; do not edit inside these markers.*
<!-- END GENERATED autonomy:summary -->

**Live-validated.** The full pipeline has conducted real paid deliveries end to
end: multi-worker builds (`-j 2`) with cross-engine rotation (claudeloop
implements, agyloop — since retired by ADR-0078 — verifies), the bounded verify-repair ladder, budget caps
tripping and being granted live, and fully zero-touch DESIGN phases answered
with nothing but `--defaults`. The validation campaign's findings — a blind
budget brake, a repair-loop livelock, terminal gate-command failures — were
each fixed and re-validated live.

Every architectural layer (`domain`, `application`, `infrastructure`, `cli`)
holds a **100% branch-coverage floor**, enforced as four separate CI gates
(ADR-0023); the absorbed runner and tool packages keep their own gates (ADR-0022).
`domain/` is pure stdlib, enforced by import-linter and an AST-walking purity
test — the no-loss handoff gate is deterministic code, not a model's opinion.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `vibey doctor` reports an engine `NOT INSTALLED` | The `*loop` binaries ship with `vibey`, so this is a `PATH` problem, not a missing package: `vibey` is being run from one environment while `PATH` points at another (a venv whose `bin/` is not exported, a shadowing `uv tool` shim, a system `python` install). | `python -c 'import shutil; print(shutil.which("claudeloop"))'` in the same environment that runs `vibey`; if it prints nothing, put that environment's `bin/` on `PATH` (or reinstall with `uv tool install vibey-engine`), then re-run `vibey doctor`. |
| `VIBEY_PG_URL is not set` | No database connection string in the environment. | `export VIBEY_PG_URL=postgresql://user@localhost:5432/vibey`, pointing at a database you own. |
| `vibey doctor` reports `auth FAIL` | The engine's own vendor credentials aren't configured. | Run that engine's own login/auth flow, then re-run `vibey doctor --conformance`. |
| `vibey worker` logs `no recorded conformance for ...` | `vibey doctor --conformance --record` has never passed for that engine on this project. | Run it before starting the worker; engine-driven jobs won't select an unrecorded engine. |
| A project is parked and nothing progresses | A human gate (interview, review verdict, budget cap) is waiting. | `vibey gates` (or `vibey gates <project-id>`) prints each open gate's id, its prompt, and the exact `vibey answer` command that answers it. Run that command, putting your value where it shows `N` or `<json>`. |
| Jobs sit `leased` after a worker crash | The lease hasn't expired yet, or nothing has reclaimed it. | `vibey recover --project <id>` (or `--all`) sets them back to `ready`. |
| Budget cap trips mid-cycle | The project's `max_cycle_dollars` / `max_cycle_turns` cap (set by `vibey new --max-cycle-dollars` / `--max-cycle-turns`) was exceeded — by design. | `vibey answer <gate-id> --raw '{"max_dollars": 25}'` (or `{"max_turns": N}`) to grant more, or accept the park. |
| Kubernetes-specific issues | — | See the [Kubernetes guide's Troubleshooting section](docs/guides/kubernetes.md#troubleshooting). |

## Upgrading

From 1.0.0 vibey follows semantic versioning: a change that breaks
`vibey.toml` fields, ledger event shapes, or CLI flags takes a major version.
Before upgrading:

1. Read [CHANGELOG.md](CHANGELOG.md) for the versions between your current
   version and the target.
2. Re-run `vibey doctor --conformance --record` afterward — engine
   contracts and conformance checks can gain new checks between releases.
3. The database schema migrates automatically
   (`infrastructure/db/migrator.py`); no manual migration step is needed.

Every push to `develop` publishes a uniquely versioned dev build (`X.Y.Z.devN`)
to TestPyPI; every push to `main` publishes to PyPI. Two packages publish, each by its own
workflow (ADR-0069): `vibey-engine`, the engine family (`vibey-engine.yml`), and
`krypton-app`, the apps and the `krypton` command (`krypton-app.yml`).
After a successful `main` release, `github-release.yml` tags that exact commit
and creates the matching GitHub Release. Versioning and release are owned by
the in-tree `vibey-gh`; release-please is retired (ADR-0028). `uv tool install
vibey-engine` (or `pipx install vibey-engine` / `pip install vibey-engine`) tracks stable
releases of the engine family (ADR-0037, ADR-0069); `pip install krypton-app` adds the apps.

## Formal notes

For the reader who wants the theory under the phases. Work items form a queue
$Q$ in PostgreSQL; workers claim with `SELECT ... FOR UPDATE SKIP LOCKED`, so
claims serialize per item without global locks: for any item $w$, at most one
worker holds $w$ at any instant, while throughput scales with
$\min(|Q|, \text{workers})$. The conductor is a six-phase state machine
$\Sigma = \langle D, B, R, D_d, D_e, D_r \rangle$ (design, build, review,
deploy-design, deploy-execute, deploy-review) with human gates exactly at
$\{D, R, D_d, D_r\}$ — interactive phases are the fixed points where the
ledger's open questions must drain to zero before the transition fires.
Crash recovery follows from two invariants: every decision, finding, and
handoff is a row in an append-only ledger *before* it takes effect
(write-ahead intent), and engine handoff re-derives session context from the
ledger alone — so vendor credit exhaustion is a scheduling event, not a loss
of state: $\text{state}(t) = f(\text{ledger}_{\leq t})$, independent of any
vendor session. The full treatment — with the queue-fairness argument and the gate-soundness
proof sketch — is the research paper, *Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents*:
[read it online](https://the-vibey-project.github.io/vibey/main/paper/) or [download the PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)
(source: [`docs/paper.md`](docs/paper.md)). The complete documentation is also a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html).

## Project links

| | |
|---|---|
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security policy | [SECURITY.md](SECURITY.md) |
| Getting help | [SUPPORT.md](SUPPORT.md) |
| Code of Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Community | [Discord](https://discord.gg/Qvu8aYnVS) · [Join me](https://vibewithadam.matthewsteinberger.com/join-me) |

## Join the community

vibey is free and open-source software, and it is built in the open. If you write
software and want to build the autonomous-delivery stack with us, come and say hello
on [Discord](https://discord.gg/Qvu8aYnVS), and read
[how to join me](https://vibewithadam.matthewsteinberger.com/join-me). Questions,
critiques, pull requests and wild ideas are all welcome.

## Related projects

These packages live in this repository as uv workspace members
(`src/vibey_runners/*`, `src/vibey_tools/*`; ADR-0021). Each keeps its own
`pyproject.toml`, version, Python floor, tests and gates — but none is
published separately any more: all nine ship inside the one `vibey-engine`
distribution (ADR-0037), and their former standalone GitHub repositories and
PyPI projects no longer exist.

| Project | Source | What it is |
|---|---|---|
| claudeloop | [`src/vibey_runners/claude`](src/vibey_runners/claude) | Autonomous Claude Code session runner — the design the family transplants |
| codexloop | [`src/vibey_runners/codex`](src/vibey_runners/codex) | The same design retargeted onto OpenAI Codex |
| gptossloop, qwenloop | [`src/vibey_runners/qwen`](src/vibey_runners/qwen) | The same design on a local model, as two engines over Ollama, llama.cpp or vLLM: `gptossloop` on GPT-OSS 20B — the sovereign default, on by default, and the sovereign DESIGN provider — and the opt-in `qwenloop` on Qwen (`qwen3:14b`); both preferred first when switched on (ADR-0064) |
| vibey-skills | [`src/vibey_tools/skills`](src/vibey_tools/skills) | The Agent Skills marketplace (a Claude Code plugin marketplace) and its context packets |
| vibey-gh | [`src/vibey_tools/gh`](src/vibey_tools/gh) | Provenance fingerprints, derived version bumps, a merge train, and branch realignment; it owns vibey's own release (ADR-0028) |
| vibey-bootstrap | [`src/vibey_tools/bootstrap`](src/vibey_tools/bootstrap) | Azure bootstrap library for App Configuration, Key Vault, and App Insights integration |

## License

[MIT](LICENSE) © [Adam Matthew Steinberger](https://github.com/adammatthewsteinberger)

---

**The short version, again**: agents can code, but delivery still meant
babysitting them — vibey is the layer that does the babysitting, from sharp
spec to deployed software, without losing a single open question.

**Your next step**: install it and let it interview you —

```bash
uv tool install vibey-engine && vibey doctor
```

**Prefer to read first?** The design is a [research paper](https://the-vibey-project.github.io/vibey/main/paper/)
([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)), and the whole documentation is a [book](https://the-vibey-project.github.io/vibey/main/book.pdf)
([EPUB](https://the-vibey-project.github.io/vibey/main/book.epub)).

**Want to build it with us?** [Your first hour](CONTRIBUTING.md#your-first-hour) takes you
from a clone to a pull request.
