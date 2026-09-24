# vibey

**You've used an AI coding agent. Then you babysat it** — re-prompting when it
lost the thread, re-explaining everything after a crash, copying results
between tools, watching a run die at 2am because one vendor's credits ran out.
The agent was autonomous; the *delivery* was you.

**Vibey is the layer that does the babysitting.** It's an orchestrator that
wraps AI coding agents so you're not managing sessions or threads by hand: you
describe what you want, it interviews you until the spec is sharp, builds
unattended across a pool of engines, brings you back only for the decisions
that are genuinely yours, and survives crashes and credit exhaustion without
losing a single open question.

**Never written code?** You can still read this. *Code* is text files of
instructions computers run; an *AI coding agent* is a program that writes and
edits that code from plain-English requests; *deploying* means putting the
finished software somewhere people can use it. Vibey's job is to manage a
team of those agents from your first description to deployed software, the
way a project manager runs a team — asking you questions up front, checking
the work, and only interrupting you when a decision is truly yours.

**Read it first:** the design is a research paper — [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) · [HTML](paper.md) —
and the whole documentation is a book — [PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print](https://the-vibey-project.github.io/vibey/main/book-print.html).

For the precise version: a queue-based, six-phase conductor for autonomous
software delivery — with an optional visual-design interstitial and opt-in
Azure deployment — built on top of the [`*loop` autonomous session
runners](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/), which live in this repository as uv
workspace members (ADR-0021).

## What problem this solves

An autonomous coding session is not autonomous software delivery. A single
`claudeloop` run can finish a task, but it cannot interview you until the spec
is sharp, split the work into parallel items, verify each one against gates it
cannot game, survive its own credit exhaustion by handing off to a different
vendor's engine *without losing a single open question*, or know that a review
finding should reopen design rather than vanish into a transcript.

Vibey conducts all of that. You describe what you want; it interviews you until
the spec is sharp, builds unattended across a pool of engines with real budget
caps, reviews the result with you, and (only if you opt in) deploys. Every
choice, finding, and handoff lives in an append-only PostgreSQL ledger — never
in one vendor's chat session.

| | |
|---|---|
| Runs on | macOS / Linux, local. No cloud control plane required. |
| Language | Python 3.12+ |
| Queue | PostgreSQL (`FOR UPDATE SKIP LOCKED`) |
| Engines | [`claudeloop`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude), [`codexloop`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex), [`cursorloop`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/cursor), [`agyloop`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/agy), [`opencode`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/opencode) — the `opencodeloop` adapter for the official OpenCode CLI — plus the opt-in [`qwenloop`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/qwen) — a local engine and the sovereign DESIGN provider — and `claudeloop-local`, the claudeloop binary on a local backend profile. Local engines are preferred first when switched on (ADR-0015, ADR-0027, ADR-0038). All six runners ship inside the `vibey` distribution ([ADR-0037](architecture/decisions/0037-one-distribution-one-version.md)). |
| State dir | `.vibey/` |
| Env prefix | `VIBEY_` |
| Done marker | Each loop's own marker (`CLAUDELOOP_TASK_FULLY_COMPLETE`, `QWENLOOP_TASK_FULLY_COMPLETE`, etc.) |

## Install

Requires **Python 3.12+** and **PostgreSQL**. Windows is not a supported
target. Every database-backed command reads the connection string from
`VIBEY_PG_URL`; vibey never guesses a database and exits with
`VIBEY_PG_URL is not set` when it is missing.

One install is the whole family: `vibey`, all six `*loop` engines, and the
tools (`vibey-gh`, `vibey-skills`, `vibey-bootstrap`) ship in the one `vibey`
distribution and land on `PATH` together
([ADR-0037](architecture/decisions/0037-one-distribution-one-version.md)). What
each engine still needs separately is its own vendor CLI and credentials —
which is what `vibey doctor` checks.

```bash
uv tool install vibey          # or: pipx install vibey / pip install vibey
export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey # the application
# The owner's DSN is given to `vibey migrate` alone, for that one command -- never exported,
# so no worker, engine session or gate command ever holds it:
VIBEY_PG_MIGRATE_URL=postgresql://user@localhost:5432/vibey vibey migrate
vibey doctor                   # pre-flight: engines, and whether the ledger is guarded
```

Two DSNs, because the ledger is append-only by the database
([ADR-0055](architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)):
the application connects as a role that can read and append to the ledger and nothing
more. One DSN still works, but `vibey doctor` fails its `ledger-guard` check until the
roles are split ([database roles](reference/configuration.md#database-roles)).

`vibey doctor` alone checks only the engines. `--record` also writes the result
to the database for a project, and `--cluster` runs the in-cluster preflight
(DSN, workspace, secrets, database, migrations) instead.

`qwenloop` installs with everything else; what is opt-in is the *feature*, not
the install. Two local engines have a switch each: `VIBEY_FEATURE_QWENLOOP=1`
and `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` (claudeloop on a local backend profile).
A switched-on local engine is **preferred first** for BUILD — a paid engine runs
only when no local one is eligible — and `vibey doctor` lists it; `vibey doctor`
also honours `[features] qwenloop = true` / `claudeloop_local = true` in a
`./vibey.toml`. With a local engine on and no `--provider`, `vibey work` and
`vibey worker` run DESIGN and DECOMPOSE on the sovereign providers too (ADR-0038).
`VIBEY_OLLAMA_URL` is the one endpoint setting; the
[local models guide](guides/local-models-ollama.md) has the Ollama recipe.

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

The same tree is a Claude Code plugin marketplace — every plugin in the family, the 135
skills plugins and vibey-gh's four, from one address and nothing else:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install security-principles@vibey
/plugin                                    # browse all 139
```

The root manifest is rendered from the workspace members by `vibey-gh marketplace` and
held to them by `vibey-gh check` ([ADR-0034](architecture/decisions/0034-one-marketplace-at-the-root.md)); it is never edited by hand. Since the family
ships as one distribution ([ADR-0037](architecture/decisions/0037-one-distribution-one-version.md)) this root manifest is the only marketplace there is.

## Quickstart

```bash
export VIBEY_PG_URL=postgresql://user@localhost:5432/vibey
vibey new my-app --repo ~/src/my-app \
  --max-cycle-dollars 15                     # real budget brake, enforced from the ledger
vibey doctor --conformance --record          # verify each engine's contract, persist health for the latest project
vibey worker --provider claudeloop \
  --engines claudeloop,agyloop -j 2          # live DESIGN provider; unattended build across the pool

# When vibey parks for your input (design gates, review, budget grants):
vibey gates                                  # each open gate, its prompt, and the command that answers it
vibey answer <gate-id> --defaults            # accept the interview defaults, or:
vibey answer <gate-id> --raw '{"max_dollars": 25}'   # raise a tripped budget cap
vibey design accept <project-id> --no-visual
vibey answer <gate-id> --verdict accept      # review demo
vibey answer <gate-id> --choice local_only   # decline deployment → DONE (local)
```

`vibey doctor --record` needs a project to record against, so run it after
`vibey new`. `vibey worker` defaults to `--provider scripted`, a test double —
or to `--provider qwenloop` when a local engine is switched on; pass
`--provider claudeloop` for a live, paid DESIGN interview and BUILD
decomposition, or `--provider qwenloop` for the same on a local model.
`vibey gates` lists every open gate with its id, its prompt, and the exact
`vibey answer` command that answers it (`vibey gates <project-id>` for one
project); `vibey projects` lists your projects, their ids, and how many gates
each is waiting on. Both take `--json`.

The [greeter live-demo runbook](guides/greeter-live-demo.md) walks a full
paid run end to end, including the zero-touch contracts.

## Command reference

Every command's flags and defaults are in the
[CLI reference](reference/cli.md). The most common ones:

| Command | What it does |
|---|---|
| `vibey doctor` | Pre-flight: engine install state, versions, auth; `--conformance` runs the 9-check suite, `--record` persists health, `--cluster` runs the in-cluster preflight. |
| `vibey new` | Create a project and enqueue its first DESIGN interview. |
| `vibey worker` | Long-running worker: dispatches jobs across every phase (`--provider scripted\|claudeloop\|qwenloop`, `--engines`, `-j`, `--azure memory\|az`). |
| `vibey work` | Process one ready DESIGN or VISUAL_DESIGN job for a project (foreground, capped). |
| `vibey answer` | Answer a parked human gate. |
| `vibey design resume/accept` / `vibey visual accept/waive` | Resume or accept DESIGN; accept or waive VISUAL_DESIGN. |
| `vibey watch` / `vibey status` | Live dashboard, or one-shot status (`--json` for scripting). |
| `vibey engines` / `vibey cost` / `vibey ledger show` | Engine health, budget spend, and event-ledger inspection. |
| `vibey deploy status/inspect/plan/cancel/rollback` | Inspect and control Phases ④–⑥. |
| `vibey recover` | Recover jobs stuck under a dead worker's lease. |
| `vibey operator` | Run the Kubernetes operator (`pip install 'vibey[operator]'`; ADR-0025). |

## Configuration

`vibey.toml`'s schema — `[project]`, `[isolation]`, `[budget]`, `[engines]`,
`[phases.design/build/review]`, `[provision]`, `[deploy]`, `[features]`,
`[qwenloop]`, `[notifications]`, and `[telemetry]` — is fully implemented and unit-tested in
`domain/config.py`/`infrastructure/config_loader.py`, with defaults and an
example file in the [configuration reference](reference/configuration.md).
The local-engine keys are read at runtime today: `[features] qwenloop`,
`[features] claudeloop_local` and `[engines.claudeloop_local]`. `vibey doctor`
reads them from `./vibey.toml` in the current directory, and the worker reads the
same keys from the project's stored config (which no CLI flag sets yet);
`VIBEY_FEATURE_QWENLOOP`, `VIBEY_FEATURE_CLAUDELOOP_LOCAL` and
`VIBEY_CLAUDELOOP_LOCAL_PROFILE` override them. `[notifications]` and
`[telemetry]` are copied from the repository's `vibey.toml` into the stored
project config by `vibey new`; the worker and lifecycle repository then use
those settings. Telemetry is an in-process recorder for now, so it is available
to the running app but has no external exporter yet.

What does configure a project today is a handful of `vibey new` CLI flags
(`--max-cycles`, `--max-cycle-dollars`, `--max-cycle-turns`,
`--skills-context-mode`, `--skills-context-budget`) recorded directly into
that project's stored config at creation time — see the
[CLI reference](reference/cli.md).

## Notifications

`infrastructure/notify/` implements a `NotificationService` that dispatches
desktop alerts and HMAC-SHA256-signed webhooks (`X-Vibey-Signature`, see
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/main/SECURITY.md#6-webhook-payload-integrity--implemented-unit-tested-and-active-when-configured)),
and it is covered by tests. `build_app()` constructs it; workers notify on
newly raised gates, and project transitions notify on phase changes and
completion. Enable it in the repository TOML with
`[notifications] enabled = true`; `vibey new` stores that table with the project.

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

## Why it isn't just another agent framework

The hard part is not calling an LLM in a loop — `claudeloop` and its siblings
already solve that, including the distinction between a waitable rate-limit
window and exhausted credits that no amount of waiting will fix. Vibey adds the
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

## Documentation

| Document | What's in it |
|---|---|
| [Architecture map](https://github.com/the-vibey-project/vibey/blob/main/docs/project.mmd) | Comprehensive Mermaid diagram: every layer, the six phases, the ledger/handoff data flow, the security boundary, and the release channels |
| [Research paper](https://the-vibey-project.github.io/vibey/main/paper/) · [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) | *Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents* — the ledger invariant, queue semantics and gate soundness, the engine family, the exact-head release calculus, and a measured production-rate regularity with its falsification conditions: the family's one paper |
| [The book](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html) | Every page of the documentation site, in reading order, as one downloadable book |
| [CLI reference](reference/cli.md) | Every command, subcommand, flag, and default |
| [Configuration reference](reference/configuration.md) | The full `vibey.toml` schema, with defaults and an example file |
| [Convergence-Driven Development](guides/convergence-driven-development.md) | The CDD loop above SDD and TDD, convergence/divergence checks at four scopes, the atom model, and delivery evidence |
| [Kubernetes guide](guides/kubernetes.md) | Container, Helm chart, KEDA autoscaling, and its own troubleshooting section |
| [Greeter live-demo runbook](guides/greeter-live-demo.md) | A full paid run, end to end, with the zero-touch contracts |
| [What gets published](guides/ledger-publication.md) | What `vibey ledger export` publishes of a ledger, what it withholds, and how it counts both |
| [Expansion runbooks](https://github.com/the-vibey-project/vibey/blob/main/docs/runbooks/expansion/) | 21 workstreams: JIRA, more clouds, Kubernetes server mode, clients, store submissions, … |
| [Architecture & roadmap](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/architecture-and-roadmap.md) | The master design: context, containers, layers, phases, risks, milestones |
| [Domain model](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/domain-model.md) | Every value object, ADT, and invariant in `domain/` |
| [Data model](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/data-model.md) | Full PostgreSQL DDL, queue semantics, indices |
| [Handoff protocol](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/handoff-protocol.md) | The event ledger, the envelope, and the no-loss gate |
| [Rotation & engines](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/rotation-and-engines.md) | Capability matrix, effort normalization, smooth weighted round robin |
| [Phase protocols](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/phase-protocols.md) | What all six phases do, turn by turn |
| [Implementation plan](https://github.com/the-vibey-project/vibey/blob/main/docs/plans/implementation-plan.md) | Milestone-by-milestone, test-first task breakdown |
| [CLAUDE.md](https://github.com/the-vibey-project/vibey/blob/main/CLAUDE.md) | The short facts file every coding agent working on vibey loads first: non-negotiables, layer map, gate commands |
| [Decision records](https://github.com/the-vibey-project/vibey/blob/main/docs/architecture/decisions/) | Why each hard call was made (57 ADRs) |

## Status

**Live-validated.** The full pipeline has conducted real paid deliveries end to
end: multi-worker builds (`-j 2`) with cross-engine rotation (claudeloop
implements, agyloop verifies), the bounded verify-repair ladder, budget caps
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
| `vibey doctor` reports an engine `NOT INSTALLED` | The `*loop` binaries ship with `vibey`, so this is a `PATH` problem, not a missing package: `vibey` is being run from one environment while `PATH` points at another (a venv whose `bin/` is not exported, a shadowing `uv tool` shim, a system `python` install). | `python -c 'import shutil; print(shutil.which("claudeloop"))'` in the same environment that runs `vibey`; if it prints nothing, put that environment's `bin/` on `PATH` (or reinstall with `uv tool install vibey`), then re-run `vibey doctor`. |
| `VIBEY_PG_URL is not set` | No database connection string in the environment. | `export VIBEY_PG_URL=postgresql://user@localhost:5432/vibey`, pointing at a database you own. |
| `vibey doctor` reports `auth FAIL` | The engine's own vendor credentials aren't configured. | Run that engine's own login/auth flow, then re-run `vibey doctor --conformance`. |
| `vibey worker` logs `no recorded conformance for ...` | `vibey doctor --conformance --record` has never passed for that engine on this project. | Run it before starting the worker; engine-driven jobs won't select an unrecorded engine. |
| A project is parked and nothing progresses | A human gate (interview, review verdict, budget cap) is waiting. | `vibey gates` (or `vibey gates <project-id>`) prints each open gate's id, its prompt, and the exact `vibey answer` command that answers it. Run that command, putting your value where it shows `N` or `<json>`. |
| Jobs sit `leased` after a worker crash | The lease hasn't expired yet, or nothing has reclaimed it. | `vibey recover --project <id>` (or `--all`) sets them back to `ready`. |
| Budget cap trips mid-cycle | The project's `max_cycle_dollars` / `max_cycle_turns` cap (set by `vibey new --max-cycle-dollars` / `--max-cycle-turns`) was exceeded — by design. | `vibey answer <gate-id> --raw '{"max_dollars": 25}'` (or `{"max_turns": N}`) to grant more, or accept the park. |
| Kubernetes-specific issues | — | See the [Kubernetes guide's Troubleshooting section](guides/kubernetes.md#troubleshooting). |

## Upgrading

From 1.0.0 vibey follows semantic versioning: a change that breaks
`vibey.toml` fields, ledger event shapes, or CLI flags takes a major version.
Before upgrading:

1. Read the [changelog](https://github.com/the-vibey-project/vibey/blob/main/CHANGELOG.md)
   for the versions between your current version and the target.
2. Re-run `vibey doctor --conformance --record` afterward — engine
   contracts and conformance checks can gain new checks between releases.
3. The database schema migrates automatically
   (`infrastructure/db/migrator.py`); no manual migration step is needed.

Every push to `develop` publishes a uniquely versioned dev build (`X.Y.Z.devN`)
to TestPyPI as `vibey-dev`; every push to `main` publishes `vibey` to PyPI.
After a successful `main` release, `github-release.yml` tags that exact commit
and creates the matching GitHub Release. Versioning and release are owned by
the in-tree `vibey-gh`; release-please is retired (ADR-0028). `uv tool install
vibey` (or `pipx install vibey` / `pip install vibey`) tracks stable releases —
and it is the family's only install instruction
([ADR-0037](architecture/decisions/0037-one-distribution-one-version.md)).

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
(source: [`paper.md`](paper.md)). The complete documentation is also a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html).

## Project links

| | |
|---|---|
| Contributing | [CONTRIBUTING.md](https://github.com/the-vibey-project/vibey/blob/main/CONTRIBUTING.md) |
| Security policy | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/main/SECURITY.md) |
| Getting help | [SUPPORT.md](https://github.com/the-vibey-project/vibey/blob/main/SUPPORT.md) |
| Code of Conduct | [CODE_OF_CONDUCT.md](https://github.com/the-vibey-project/vibey/blob/main/CODE_OF_CONDUCT.md) |
| Changelog | [CHANGELOG.md](https://github.com/the-vibey-project/vibey/blob/main/CHANGELOG.md) |
| Community | [Discord](https://discord.gg/Qvu8aYnVS) · [Join me](https://vibewithadam.matthewsteinberger.com/join-me) |

## Join the community

vibey is free and open-source software, and it is built in the open. If you write
software and want to build the autonomous-delivery stack with us, come and say hello
on [Discord](https://discord.gg/Qvu8aYnVS), and read
[how to join me](https://vibewithadam.matthewsteinberger.com/join-me). Questions,
critiques, pull requests and wild ideas are all welcome.

<iframe src="https://discord.com/widget?id=1552349678215893002&theme=dark" width="350" height="500" allowtransparency="true" frameborder="0" sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts" title="The vibey Discord server"></iframe>

## Related projects

These packages live in this repository as uv workspace members
(`src/vibey_runners/*`, `src/vibey_tools/*`; ADR-0021). Each keeps its own
`pyproject.toml`, version, Python floor, tests and gates — but none is
published separately any more: all nine ship inside the one `vibey`
distribution ([ADR-0037](architecture/decisions/0037-one-distribution-one-version.md)),
and their former standalone GitHub repositories and PyPI projects no longer
exist.

| Project | Source | What it is |
|---|---|---|
| claudeloop | [`src/vibey_runners/claude`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/claude) | Autonomous Claude Code session runner — the design the family transplants |
| codexloop | [`src/vibey_runners/codex`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/codex) | The same design retargeted onto OpenAI Codex |
| cursorloop | [`src/vibey_runners/cursor`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/cursor) | The same design retargeted onto Cursor |
| agyloop | [`src/vibey_runners/agy`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/agy) | The same design retargeted onto Google Antigravity / Gemini |
| opencodeloop | [`src/vibey_runners/opencode`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/opencode) | Contract-preserving adapter for the official OpenCode CLI; provider selection and billing remain OpenCode-owned |
| qwenloop | [`src/vibey_runners/qwen`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/qwen) | The same design on a local Qwen 2.5 Coder model (llama.cpp or vLLM) — an opt-in local engine, preferred first when switched on, and the sovereign DESIGN provider |
| vibey-skills | [`src/vibey_tools/skills`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/skills) | The Agent Skills marketplace (a Claude Code plugin marketplace) and its context packets |
| vibey-gh | [`src/vibey_tools/gh`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/gh) | Provenance fingerprints, derived version bumps, a merge train, and branch realignment; it owns vibey's own release (ADR-0028) |
| vibey-bootstrap | [`src/vibey_tools/bootstrap`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_tools/bootstrap) | Azure bootstrap library for App Configuration, Key Vault, and App Insights integration |

## License

[MIT](https://github.com/the-vibey-project/vibey/blob/main/LICENSE) © [Adam Matthew Steinberger](https://github.com/adammatthewsteinberger)

---

**The short version, again**: agents can code, but delivery still meant
babysitting them — Vibey is the layer that does the babysitting, from sharp
spec to deployed software, without losing a single open question.

**Your next step**: install it and let it interview you —

```bash
uv tool install vibey && vibey doctor
```

**Prefer to read first?** The design is a [research paper](https://the-vibey-project.github.io/vibey/main/paper/)
([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)), and the whole documentation is a [book](https://the-vibey-project.github.io/vibey/main/book.pdf)
([EPUB](https://the-vibey-project.github.io/vibey/main/book.epub)).
