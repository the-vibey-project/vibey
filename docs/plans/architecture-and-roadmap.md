---
description: "How vibey is built: one PostgreSQL queue, an append-only ledger, a six-phase machine and a rotating pool of local-first engines, with what the original plan got right and where the code went another way."
---

# How vibey is built: the architecture, and the roadmap it started from

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** vibey is a conductor. Workers lease jobs from one
> PostgreSQL queue, every fact is appended to a ledger nobody may rewrite, a pure phase machine
> decides when work moves on, and each job runs on a local engine first (`gptossloop`) and a
> paid one (`claudeloop`, `codexloop`) only when no local engine can take it. Read this page
> to understand why; read the code and `docs/reference/` to act. About 40 minutes end to end.

> **How current this page is.** Checked section by section on 2026-11-24 against `develop`
> at `d91a3791e` (vibey-engine 0.4.0). This page began as the planning-era design (2026-08)
> and is kept as the rationale document. Where the plan was never built, or was built
> differently, the section says so and names the code or decision record that is current.
> Where this page and the code disagree, the code and [`docs/reference/`](../reference/cli.md)
> win. The published site leaves `docs/plans/` out on purpose (`properdocs.yml`
> `exclude_docs`), so this page is read in the repository.
>
> **Built:** the delivery loop ① DESIGN → optional VISUAL_DESIGN → ② BUILD ⇄ ③ REVIEW, the
> opt-in deployment stage set ④–⑥, the PostgreSQL queue, the event ledger and no-loss gate
> (R1–R10), SWRR rotation with circuit breakers and local-first tiers, agent-surface
> provisioning, a Kubernetes chart and operator
> ([ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md)), the hub
> (`vibey serve`, [ADR-0068](../architecture/decisions/0068-the-hub.md)) with device pairing
> ([ADR-0071](../architecture/decisions/0071-hub-pairing-and-trust.md)), the krypton clients,
> `vibey mcp` / `vibey connect` ([ADR-0100](../architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md)),
> `vibey acp` ([ADR-0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md)),
> `vibey supervisor`, `vibey loops` and the loop capability bundle
> ([ADR-0103](../architecture/decisions/0103-the-loop-capability-bundle.md)), run inputs
> ([ADR-0104](../architecture/decisions/0104-run-inputs-hash-addressed.md),
> [ADR-0105](../architecture/decisions/0105-run-input-store-backends.md)), local-first web
> search ([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)),
> ULTRA effort ([ADR-0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md)),
> the Sabbath ([ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md))
> and `vibey state` ([ADR-0086](../architecture/decisions/0086-state-sync.md)). `domain/`,
> `application/`, `infrastructure/` and `cli/` each hold a 100% branch-coverage CI gate
> ([ADR-0023](../architecture/decisions/0023-four-layers-four-floors.md)).
>
> **Not built:** the media-provider port, adapters and generation jobs of §14 (only
> `visual.inventory` / `visual.plan` and `vibey visual accept|waive` exist); the `container`
> and `vm` isolation levels and the egress allow-list of §11; an OpenTelemetry exporter (§13);
> `vibey up` (§4). Live Azure mutation exists but is off unless a worker is started with
> `--azure az` (§15). The engine failover service of
> [ADR-0070](../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md)
> exists in `application/engine_failover.py` but is not constructed by the worker; only the
> driver session's failover (`vibey driver`) is wired.
>
> **Since this was first written:** the runners and the `vibey-gh`, `vibey-skills` and
> `vibey-bootstrap` tools moved into this repository as a uv workspace
> ([ADR-0021](../architecture/decisions/0021-one-tree-history-preserved.md)) and ship as one
> package, `vibey-engine`, beside the `krypton-app` package
> ([ADR-0069](../architecture/decisions/0069-two-packages-vibey-engine-and-krypton-app.md)).
> The local runner joined as an opt-in standby
> ([ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)), became the sovereign
> DESIGN provider ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)),
> was made preferred first ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md)),
> and since [ADR-0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)
> ships as two engines: `gptossloop`, the sovereign default and on without a switch, and
> `qwenloop` on a Qwen model, opt-in. The default local model is the Heretic v2 build of
> GPT-OSS 20B ([ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)).
> `cursorloop` and `agyloop` were retired and deleted
> ([ADR-0078](../architecture/decisions/0078-retire-cursorloop-and-agyloop.md)); where this
> page still names them it says they are retired.
>
> Audience: the engineer (human or agent) who will change vibey. Companion documents:
> [domain model](domain-model.md), [data model](data-model.md),
> [handoff protocol](handoff-protocol.md), [rotation & engines](rotation-and-engines.md),
> [phase protocols](phase-protocols.md), [implementation plan](implementation-plan.md).

## The idea, in one conversation

> The workshop smelled of solder and coffee. Daniel had the architecture page open on his
> phone and a frown he had been wearing since lunch.
>
> **Daniel:** Professor, vibey runs Claude and Codex and a local model. Why not just run one
> of them in a loop and be done?
>
> **Professor Feynman:** Think of a post office. Letters come in, clerks take one each, and
> every clerk stamps what he did in the day book. If a clerk goes home sick, his letter goes
> back on the pile and someone else picks it up.
>
> **Daniel:** So the pile is the queue, the clerks are the workers, and the day book is the
> ledger.
>
> **Professor Feynman:** Yes. Now, one runner in a loop is a single clerk with the day book in
> his pocket. When he runs out of credit, the work and the book stop with him. vibey keeps the
> book on the counter, in PostgreSQL, where any clerk can read it.
>
> **Daniel:** And which clerk gets the next letter?
>
> **Professor Feynman:** The local clerk first, because he costs nothing. A paid clerk only when
> no local one is free or able. And nobody may tear a page out of the day book, not even the
> postmaster: the database itself refuses.
>
> **Daniel:** What about the phases?
>
> **Professor Feynman:** A rule on the wall: a letter is not sent until it is addressed, stamped
> and checked. The rule is a pure function, so you can test it without a post office. The
> picture stops working in one place: real clerks remember things, and ours must not. Everything
> they need is in the book, so any of them can pick up where another stopped.

## See it on your machine

1. List the engines and the two loops vibey would choose between.

   ```bash
   vibey loops
   ```

   You should see two blocks. The first is `sovereignloop (tier local)` with the columns
   `gptossloop`, `qwenloop` and `claudeloop-local`; only `gptossloop` says `switched on  yes`.
   The second is `paidloop (tier paid)` with `claudeloop` and `codexloop`. Each block lists
   the flags each effort level becomes, from `TRIVIAL` to `ULTRA`.

2. List every command, grouped by what it is for.

   ```bash
   vibey --help
   ```

   You should see groups named "Start here", "Decisions that are yours", "Watch and steer",
   "Run the machinery", "Maintain" and "Tools for agents".

## Daniel's teach-back

> **Daniel:** vibey is a conductor, not a runner. Work is jobs in one PostgreSQL queue; workers
> lease a job, do it, and acknowledge it, so a dead worker loses nothing. Every fact goes into an
> append-only ledger that the database guards, which is what lets work move from one engine to
> another without losing the thread. A pure phase machine decides when a project moves on, and
> each job runs on a local engine first and a paid one only when no local engine can take it.
>
> **Professor Feynman:** Right. One correction: "when no local engine can take it" means none is
> *eligible*. A local engine that is switched off, unhealthy or missing a capability the job
> needs does not count.

---

## 1. Problem statement

Three autonomous session runner packages live in this repository under
`src/vibey_runners/` (`claude`, `codex`, `qwen`, plus the shared `common` package),
and they give vibey five engines (`EngineId` in `src/vibey/domain/engine.py`):

- **Paid tier:** `claudeloop` and `codexloop`.
- **Local tier, zero dollars:** the runner in `src/vibey_runners/qwen` ships as two
  engines, `gptossloop` (GPT-OSS 20B, the sovereign default, on unless
  `[features] gptossloop = false` or `VIBEY_FEATURE_GPTOSSLOOP=0`) and `qwenloop`
  (the same runner on `qwen3:14b`, opt-in via `[features] qwenloop = true` or
  `VIBEY_FEATURE_QWENLOOP=1`); and `claudeloop-local` is the claudeloop binary on a local
  backend profile, opt-in via `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1`.

The default local model is the Heretic v2 build of GPT-OSS 20B,
`hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`; stock `gpt-oss:20b` is the
alternative, and `VIBEY_OLLAMA_MODEL` names any other tag
(`src/vibey/domain/sovereign_model.py`,
[ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)).
See also [ADR-0015](../architecture/decisions/0015-qwenloop-standby.md),
[ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md) and
[ADR-0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md).

When this document was written there were four paid runners, `claudeloop`, `codexloop`,
`cursorloop` and `agyloop`, each in its own repository. They were absorbed with history in
September 2026 ([ADR-0021](../architecture/decisions/0021-one-tree-history-preserved.md)), and
`cursorloop` and `agyloop` were later retired and deleted
([ADR-0078](../architecture/decisions/0078-retire-cursorloop-and-agyloop.md)). A configuration
that still names either is refused with a message naming ADR-0078 (`RETIRED_ENGINES`,
`src/vibey/domain/engine.py`). Each runner drives one vendor's coding agent
through an unattended run: it distinguishes a waitable rate-limit window from
exhausted credits, never blocks on a human, writes savepoints, and exposes a
mid-run control plane. They are, individually, excellent at *running one agent
until a task is done*.

None of them answers the question one level up:

> *Given a person with an idea, how do you get from that idea to deployed software,
> autonomously, using whichever AI happens to have capacity right now, without ever
> losing the thread of the conversation?*

That is vibey's job. It is a **conductor**, not another runner.

### The four capability gaps

| Gap | Why the `*loop` runners can't close it | Vibey's answer |
|---|---|---|
| **No phase structure** | A runner runs *one* plan to completion. It has no notion of "we designed the wrong thing and need to re-interview the user." | A phase state machine with explicit loop-back edges (§6). |
| **Single-vendor lock per run** | A `claudeloop` run holds a live Anthropic session. When Anthropic's credits run out, that run waits — it cannot move the work to Codex. | Engine rotation at handoff boundaries, over a vendor-neutral ledger (§8). |
| **Conversation lives inside the vendor** | The real context is a `~/.claude/projects/**/*.jsonl` transcript in Anthropic's format. Codex cannot read it. | An append-only, engine-agnostic event ledger; vendor transcripts become attachments, not the source of truth (§8). |
| **No durable work queue** | A run is one OS process. Kill it and the in-flight decomposition is gone. | PostgreSQL-backed queue with leases, retries, and dependencies (§7). |

### What "never lose any data" means here, precisely

The user requirement is that passing a conversation from one AI to another must
not lose data. That is easy to claim and hard to guarantee, because the natural
implementation — "ask the outgoing model to write a summary" — loses exactly the
things a summary drops, silently, and you find out three hours later.

Vibey makes it falsifiable. The handoff is gated by a **deterministic structural
check** (§8.4) that fails the handoff if any open question, unfinished plan item,
or recorded decision present in the ledger is absent from the brief. The full
ledger is always written to disk inside the receiving worktree, so "compact
context" is a prompt-economy choice, never a data-availability one. See
[ADR-0004](../architecture/decisions/0004-no-loss-gate-on-handoff.md).

---

## 2. Non-negotiables

These are inherited from the `*loop` family's Global Constraints and extended.
They are enforced by CI, not by convention.

1. **Never block a worker on a human.** Human input is a *parked job* plus a
   `human_gate` row, never a thread waiting on stdin. A parked job releases its
   lease and its worker immediately.
2. **Credits ≠ rate limit.** `CreditsExhausted` has no reset time and must never
   acquire a waitable deadline field. Inherited verbatim from the `*loop` family.
3. **A capacity rejection always outranks a completion claim.** If a turn both
   looks done and hit a limit, it is not done.
4. **`domain/` stays pure.** Stdlib, itself, and only family packages that are
   themselves dependency-free (`vibey-gh`, `vibey-skills`, `vibey-runners-common`);
   `vibey_bootstrap` is forbidden by name
   ([ADR-0017](../architecture/decisions/0017-dogfood-the-family-first.md)). No I/O, no async,
   no clock. Imports are enforced by `import-linter`; the rest by
   `tests/domain/test_domain_purity.py`.
5. **A handoff that fails the no-loss gate is not a handoff.** It is a retry, an
   escalation to full-transcript mode, or a human gate — never a silent partial.
6. **Every job is idempotent under replay.** Workers can and will die mid-job;
   the lease will expire and another worker will pick it up. Every job type must
   be safe to run twice.
7. **The ledger is append-only.** No updates, no deletes. Corrections are new
   events that supersede prior ones. The database enforces it: triggers refuse any
   rewrite, even by the owner, and the application connects as a role that holds only
   `SELECT` and `INSERT` on the ledger (ADR-0055).
8. **Every commit follows Conventional Commits.** Enforced by a git hook.
9. **No engine-specific types leak past `infrastructure/engines/`.** The domain
   knows `EngineId` and `Effort`; it never knows what `--preset` means.

---

## 3. System context (C4 level 1)

```mermaid
graph TB
    User["👤 Developer<br/>(the person with the idea)"]
    Vibey["<b>vibey</b><br/>six-phase conductor<br/>+ optional visual stage"]

    subgraph Clients["Ways in"]
        Cli["vibey CLI / TUI"]
        Krypton["krypton clients<br/>web, mobile, desktop, VS Code"]
        Hosts["host agents over MCP / ACP<br/>Claude Code, Codex, Zed, ..."]
    end

    subgraph Engines["Autonomous session runners (local CLIs)"]
        CL["claudeloop<br/>Anthropic (paid)"]
        XL["codexloop<br/>OpenAI (paid)"]
        QL["gptossloop · qwenloop<br/>local GPT-OSS (default) · Qwen (opt-in)"]
        CLL["claudeloop-local<br/>claudeloop on a local model (opt-in)"]
    end

    subgraph Local["Local machine"]
        PG[("PostgreSQL<br/>queue + ledger")]
        Git["Git repo<br/>+ worktrees"]
        FS["<code>.vibey/</code><br/>artifacts, briefs, logs"]
        Ollama["Ollama<br/>local model"]
        Searx["SearXNG<br/>local web search"]
    end

    subgraph External["External"]
        Providers["Model providers<br/>Anthropic / OpenAI"]
        Market["vibey-skills CLI<br/>(src/vibey_tools/skills)"]
        Media["Media providers<br/>image / audio / video<br/>(planned, not built)"]
        Cloud["Cloud target<br/>(Phases ④–⑥; Azure adapter built)"]
    end

    User --> Clients
    Clients -->|"interview answers,<br/>review verdicts, gate answers"| Vibey
    Vibey -->|"questions, demos,<br/>diffs"| Clients
    Vibey -->|"spawn + control"| Engines
    Engines -->|"run dirs, snapshots,<br/>events.jsonl"| Vibey
    CL -->|API| Providers
    XL -->|API| Providers
    QL --> Ollama
    CLL --> Ollama
    Vibey -->|"capability discovery,<br/>generate, preview"| Media
    Vibey --> PG
    Vibey --> Git
    Vibey --> FS
    Vibey -->|"DESIGN research<br/>(ADR-0102)"| Searx
    Vibey -->|"skills-context packet<br/>per implement job (opt-in)"| Market
    Vibey -->|"plan, deploy,<br/>verify, demo"| Cloud
```

**Trust boundary note.** Everything inside *Local* is on the developer's machine.
Vibey never ships source, prompts, reference assets, or ledger content to a media
provider unless the user opted into the visual stage and accepted external-media
egress. See §12. Local does not mean offline: sovereign DESIGN research searches the
web through a local SearXNG first and falls back to Brave Search only where configured
([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md),
`infrastructure/engines/gptossloop_design.py`), and each search and fetch is recorded on the
ledger as `WebSearched` / `WebFetched`.

**Repository layout (checked 2026-11-24).** The diagram shows the runners and
`vibey-skills` as local CLIs, and that is still how the conductor reaches them: as
subprocesses, never as imported code. Their source lives in this repository, a uv
workspace ([ADR-0021](../architecture/decisions/0021-one-tree-history-preserved.md)):
`src/vibey/` (the conductor), `src/vibey_runners/` (`claude`, `codex`, `qwen`, and the
shared `common` package), and `src/vibey_tools/` (`gh`, `skills`, `bootstrap` — the
packages `vibey_gh`, `vibey_skills`, `vibey_bootstrap`). The clients live under
`clients/` (`app` for krypton mobile and web, `desktop` for krypton desktop in C on GTK 4
per [ADR-0073](../architecture/decisions/0073-krypton-desktop-in-c-on-gtk.md), `vscode`,
and `krypton-app`, the Python package that ships them) and share the TypeScript core in
`packages/vibey-core`
([ADR-0067](../architecture/decisions/0067-one-typescript-core-for-every-krypton-client.md)).
Each Python tenant keeps its own test, lint and coverage gates in this repository's CI
([ADR-0022](../architecture/decisions/0022-absorbed-packages-keep-their-own-gates.md)), and
all of them ship inside the one `vibey-engine` distribution rather than publishing under
their own names; the apps ship as `krypton-app`
([ADR-0037](../architecture/decisions/0037-one-distribution-one-version.md),
[ADR-0069](../architecture/decisions/0069-two-packages-vibey-engine-and-krypton-app.md)). The
former sibling GitHub repositories, and the former PyPI projects, no longer exist.

---

## 4. Container view (C4 level 2)

```mermaid
graph TB
    subgraph CLI["vibey CLI / TUI"]
        Cmd["<code>vibey new|projects|status|gates|answer|design|visual|deploy|<br/>watch|engines|loops|models|cost|budget|queue|retry|recover|abandon|<br/>ledger|ultra|inputs|work|worker|operator|supervisor|driver|<br/>migrate|install|doctor|state|sabbath|explain|search|fetch|searxng|llm</code>"]
        Tui["Textual TUI<br/>live phase + engine + cost"]
    end

    subgraph Surfaces["Surfaces for clients and host agents"]
        Hub["<b>Hub</b> <code>vibey serve</code><br/>HTTP for krypton clients,<br/>paired devices (ADR-0068/0071)"]
        Mcp["<code>vibey mcp</code><br/>MCP tools for a host chat<br/>(ADR-0100)"]
        Acp["<code>vibey acp</code><br/>ACP agent for an editor<br/>(ADR-0101)"]
    end

    subgraph Core["vibey core process(es)"]
        Sup["<b>Phase transitions</b><br/>guards in domain/phase.py,<br/>run inside job handlers"]
        W1["<b>Worker</b> ×N<br/>lease → execute → commit"]
        Rot["<b>Rotator</b><br/>SWRR + circuit breakers"]
        Led["<b>Ledger</b><br/>append + project"]
    end

    subgraph Adapters["infrastructure/engines/"]
        Ad["EngineAdapter per descriptor (5)<br/>argv build, run-dir tail,<br/>capacity map, effort map"]
    end

    subgraph MediaAdapters["infrastructure/media/ (planned, not built)"]
        Md["MediaProvider registry<br/>image / audio / video cursors"]
    end

    subgraph Store["PostgreSQL"]
        Q[("job / job_dep")]
        E[("event")]
        H[("handoff")]
        G[("human_gate")]
        HE[("engine_health")]
    end

    subgraph Work["Filesystem"]
        WT["git worktrees<br/><code>.vibey/worktrees/&lt;project8&gt;/&lt;cycle&gt;/&lt;item&gt;</code>"]
        Art["artifacts + briefs<br/><code>.vibey/runs/</code>"]
    end

    Cmd --> Sup
    Hub --> Sup
    Mcp --> Hub
    Acp --> Hub
    Hub -.->|"LISTEN vibey_ledger_appended"| E
    Tui -.->|"tail"| E
    Sup --> Q
    W1 -->|"SKIP LOCKED"| Q
    W1 --> Rot
    Rot --> HE
    W1 --> Ad
    W1 --> Md
    Ad -->|"subprocess"| Ext["claudeloop / codexloop /<br/>gptossloop / qwenloop /<br/>claudeloop-local"]
    Ad --> WT
    W1 --> Led
    Led --> E
    Led --> H
    Sup --> G
    W1 --> Art
```

### Process model

*Corrected 2026-11-24.* The planned `vibey up` command (one command that brings up the
database and every process) was not built. What runs instead:

- **N stateless worker processes** (`vibey worker`), the only processes that execute jobs.
- **The hub**, `vibey serve`, on `http://127.0.0.1:8765/` by default: one HTTP API for every
  krypton client (web, mobile, desktop, VS Code), with paired devices, scoped tokens and a
  live view fed by the `vibey_ledger_appended` notification
  ([ADR-0068](../architecture/decisions/0068-the-hub.md),
  [ADR-0071](../architecture/decisions/0071-hub-pairing-and-trust.md),
  [ADR-0091](../architecture/decisions/0091-devices-may-start-pause-and-unwind-projects.md);
  `docs/reference/hub-api.md`). `vibey hub start|stop|status|pair|devices|revoke` manages it.
- **`vibey mcp`**, a stdio MCP server a host chat client (Claude Code, Codex, Cursor, Gemini
  CLI, Claude Desktop) launches; it is a thin wrapper over the hub API that authenticates as a
  scoped agent principal (`view`, `answer`, `run`; never `spend`). **`vibey acp`**, an Agent
  Client Protocol agent an editor such as Zed launches, which installs and keeps user-level
  services running under its `[acp]` grant. `vibey connect` registers vibey with each host
  ([ADR-0100](../architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md),
  [ADR-0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md)).
- **`vibey supervisor`**, which keeps the worker and the delivery bridge running
  (`src/vibey/cli/supervisor.py`, `src/vibey/infrastructure/supervisor.py`). It restarts
  processes; it does not own phase transitions, which stay inside job handlers (below).
- **An optional Kubernetes operator** (`vibey operator`).

- `vibey worker` runs the lease → execute → ack loop, woken by
  `LISTEN vibey_job_ready`. `--parallelism/-j` (1–16, default 1) sets concurrent
  jobs, bounded to `min(parallelism, engines × 2, cpu_count)`. `vibey work
  <project-id>` processes one ready DESIGN job in the foreground and exits.
- Every process reads its DSN from `VIBEY_PG_URL` and refuses to start without it
  (`DatabaseNotConfigured`); there is no default database. That DSN names the
  application role; migrations and grants run as the owner, `VIBEY_PG_MIGRATE_URL`
  (`vibey migrate`, ADR-0055). `vibey install --postgres`
  can install and start a local PostgreSQL 14+ server through Homebrew, apt, or dnf.
  Postgres may also be brought by the operator as a container or through the Helm
  chart's in-cluster `postgres:17-alpine`.
- Workers are stateless. Killing one loses nothing; its lease expires and the job
  is re-leased. In a container, `tini` is PID 1 and a SIGTERM latch armed before
  the first import turns a stop into a drain
  ([ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md)).
- **Phase transitions** happen inside the handler (or CLI command) that completes
  a phase: it evaluates the pure guard in `domain/phase.py`, then moves the
  project with a compare-and-set `UPDATE project … WHERE phase = <expected>`, so
  two workers cannot both win. `build.integrate` for one `(project_id, cycle)` is
  serialized by a session-level Postgres advisory lock; contention is a short
  defer ([ADR-0029](../architecture/decisions/0029-integrate-serialized-by-advisory-lock.md)).
- In a cluster, the Helm chart runs workers as a Deployment, KEDA scales them on
  claimable work, and `vibey operator` reconciles `VibeyProject` custom resources
  ([ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md),
  `docs/guides/kubernetes.md`).

---

## 5. Layer map

Vibey follows the same onion the `*loop` family uses, because the engineer is the
same and the conformance tooling is already written.

```
domain/  →  application/  →  infrastructure/  →  cli/ + tui/
                                    ▲
                            bootstrap.py
                     (the sole composition root)
```

Dependencies point inward only, enforced by `import-linter` in CI. Each of
`domain/`, `application/`, `infrastructure/` and `cli/` carries a 100% branch
coverage floor as its own CI gate
([ADR-0023](../architecture/decisions/0023-four-layers-four-floors.md)).

| Layer | Contains | May import |
|---|---|---|
| `domain/` | Phase machine, rotation algorithm, effort ladder, handoff ADTs, no-loss gate rules, budget, plan, config parsing, security primitives | stdlib and dependency-free family packages ([ADR-0017](../architecture/decisions/0017-dogfood-the-family-first.md)) |
| `application/` | `interfaces/` (one Protocol per collaborator, [ADR-0016](../architecture/decisions/0016-classes-behind-interfaces.md)), use cases, `*_handler.py` job handlers, DTOs, engine selection | `domain/` |
| `infrastructure/` | Postgres, engine adapters, git, filesystem, notifications, logging | `domain/`, `application/` |
| `cli/`, `tui/` | Typer commands, Textual app | all inner layers |
| `bootstrap.py` | Wiring — the only place concrete types meet Protocols | everything |

### Package tree

*Updated 2026-11-24 to the tree as built. Abridged: `domain/` alone has 82 modules plus the
`acp/` and `interfaces/` packages, and `cli/` about 60. The planned `handlers/` package and
`infrastructure/media/` do not exist; a supervisor does
(`infrastructure/supervisor.py`), though it restarts processes rather than owning
transitions.*

```
src/vibey/
├── domain/          phase, effort, engine, rotation, circuit, capacity, ledger,
│                    handoff, noloss, briefing, projections, job, plan, spec,
│                    review, budget, config, deployment, visual, media, provision,
│                    worktree, verbosity, command_guard, scope_guard,
│                    prompt_shield, errors, and since 2026-09: engine_dispatch
│                    (ADR-0079), failover (ADR-0070), ultra (ADR-0063), sabbath
│                    (ADR-0072), state_sync (ADR-0086), slicing (ADR-0092),
│                    sovereign_model (ADR-0099), searxng + web_tools (ADR-0102),
│                    loop_capabilities (ADR-0103), run_input (ADR-0104),
│                    queue_priority (ADR-0054), queue_reap (ADR-0056), hub_pairing,
│                    hub_scope (ADR-0071), gate_timeout, gate_notice, stored_value
│                    (forward-compatible enum reads), acp/ (ADR-0101), interfaces/
├── application/     interfaces/ (one Protocol per port, ADR-0016), ports, dto,
│                    worker, job_dispatcher, design_*_handler, visual_handler,
│                    build_*_handler, review_*_handler (incl. review_publish_handler),
│                    deploy_*_handler, engine_selector, engine_selection,
│                    engine_dispatch_service, engine_failover (built, not wired),
│                    driver_failover, handoff_orchestration, rotation_handoff,
│                    wind_down, conformance, seed_prompt, gate_timeouts,
│                    gate_notices, gate_auto_answers, queue_priority, queue_reaper,
│                    ultra_control, state_sync, loops, loop_capabilities_service,
│                    run_inputs_service, hub/, acp/
├── infrastructure/  db/ (asyncpg repositories, migrator, advisory_lock, notifier,
│                    migrations/ 0001_project … 0023_acp_session),
│                    engines/ (descriptors, loop_process_adapter, tailer, classify,
│                    scripted*, claudeloop_*, gptossloop_*), git/, ledger/
│                    (full_ledger_writer, redact), provision/, build/, container/,
│                    azure/, aws/ (declared-only stub), deploy/, notify/, operator/,
│                    hub/, mcp/, acp/, web/, searxng/, inputs/, loops/, state/,
│                    supervisor, publish/, tracker/, docs/, secrets/, files/,
│                    email/, sms/, messaging/, config_store/, cache/, bus/, blob/,
│                    siem/, workflows/, interfaces/, skills_context, context_writer,
│                    review_artifact_writer, cluster_preflight, config_loader,
│                    logging, otel
├── cli/             main (every command), one module per command group
│                    (serve, mcp, acp, connect, loops, inputs, searxng, state,
│                    ultra, supervisor, driver, ...), errors, interfaces/
├── tui/             dashboard
└── bootstrap.py
```

The migrations are forward-only SQL shipped as package data under
`src/vibey/infrastructure/db/migrations/` (23 files, `0001_project.sql` …
`0023_acp_session.sql`), found by `bootstrap.migrations_dir()` the same way in a checkout,
the container image and an installed wheel. There is no root `migrations/` directory any
more. See [data-model.md](data-model.md) §7.

---

## 6. The phase machine

### 6.1 States

| Phase | Interactive? | Effort | Purpose |
|---|---|---|---|
| `INTAKE` | — | — | Create project, detect repo, provision agent surfaces |
| `DESIGN` (①) | **yes** | `HIGH` | Interview the user to a testable spec |
| `VISUAL_DESIGN` | **yes, optional** | `HIGH` | Inventory screens and plan visual, audio, and video assets when opted in (generation is not built; §14) |
| `BUILD` (②) | no | `LOW` (auto-escalating) | Decompose, implement, verify, integrate |
| `REVIEW` (③) | **yes** | `HIGH` | Demo what was built, collect change requests |
| `DEPLOY_DESIGN` (④) | **yes** | `HIGH` | Establish and accept the Azure deployment contract |
| `DEPLOY_EXECUTE` (⑤) | no | `LOW` (auto-escalating) | Plan, provision, release, verify, and recover autonomously |
| `DEPLOY_REVIEW` (⑥) | **yes** | `HIGH` | Demo success or resolve a failure that needs user input |
| `DONE` | — | — | Terminal success (local or deployed). A later explicit deployment opt-in may re-enter `DEPLOY_DESIGN` from `DONE`. |
| `ABANDONED` | — | — | Terminal failure / user cancel |

`Phase.DEPLOY` also remains in the enum as a legacy single-phase bridge from the
pre-ADR-0013 lifecycle, with edges from `REVIEW` and `DONE`; new projects use the
④–⑥ stage set.

The lifecycle has six numbered phases plus one optional, unnumbered visual-design
interstitial. Delivery is `① DESIGN → optional VISUAL_DESIGN → ② BUILD → ③ REVIEW`;
deployment remains `④–⑥`. High-effort models conduct human conversations and
visual review; low-effort models handle bulk build, media generation, and
deployment execution. §9.3 covers escalation ladders.

### 6.2 Transitions

```mermaid
stateDiagram-v2
    [*] --> INTAKE
    INTAKE --> DESIGN: project created
    INTAKE --> ABANDONED: user cancels<br/>(stalled before DESIGN)

    DESIGN --> VISUAL_DESIGN: user opts into visual design
    DESIGN --> BUILD: user declines visual design
    DESIGN --> ABANDONED: user cancels

    VISUAL_DESIGN --> BUILD: all screen specs and media accepted
    VISUAL_DESIGN --> BUILD: explicit visual-stage waiver
    VISUAL_DESIGN --> ABANDONED: user cancels

    BUILD --> REVIEW: all work items integrated
    BUILD --> DESIGN: blocked on ambiguity<br/>(spec insufficient)
    BUILD --> ABANDONED: budget exhausted<br/>+ user declines top-up

    REVIEW --> DEPLOY_DESIGN: user accepts + opts into deployment
    REVIEW --> DONE: user accepts + declines deployment
    REVIEW --> DESIGN: changes need clarification
    REVIEW --> BUILD: changes are unambiguous<br/>(fast path)
    REVIEW --> ABANDONED: user cancels

    DEPLOY_DESIGN --> DEPLOY_EXECUTE: deployment spec accepted<br/>+ mutation consent recorded
    DEPLOY_DESIGN --> DEPLOY_DESIGN: revise the contract
    DEPLOY_DESIGN --> ABANDONED: user cancels

    DEPLOY_EXECUTE --> DEPLOY_EXECUTE: retryable / waitable failure
    DEPLOY_EXECUTE --> DEPLOY_REVIEW: verified success<br/>or user input required
    DEPLOY_EXECUTE --> ABANDONED: user cancels

    DEPLOY_REVIEW --> DONE: successful demo accepted
    DEPLOY_REVIEW --> DEPLOY_DESIGN: deployment details must change
    DEPLOY_REVIEW --> DEPLOY_EXECUTE: unambiguous retry
    DEPLOY_REVIEW --> DESIGN: product intent changed
    DEPLOY_REVIEW --> BUILD: application fix is unambiguous
    DEPLOY_REVIEW --> REVIEW: acceptance evidence must be reconsidered
    DEPLOY_REVIEW --> ABANDONED: user cancels

    DONE --> DEPLOY_DESIGN: late deployment opt-in
```

*Corrected 2026-09-15:* the planned `VISUAL_DESIGN → DESIGN` edge is not in
`_EDGES`; a visual stage that finds a missing requirement has no automatic route
back to ①.

**On `REVIEW → BUILD` (the fast path).** The source diagram specifies
`REVIEW → DESIGN` as the loop-back. That is the correct *default*: a change
request usually carries ambiguity, and re-interviewing is cheap relative to
building the wrong thing twice. But when the review triage classifies every
finding as `unambiguous` (a typo, a renamed label, a failing test with an obvious
fix), routing through a full design interview wastes the user's time. Vibey
therefore supports both edges, defaulting to `REVIEW → DESIGN`, with the fast
path taken only when *every* open finding is `unambiguous` and the user has not
set `strict_loopback = true`. See
[ADR-0010](../architecture/decisions/0010-review-loopback-routing.md).

**Opt-in means an explicit ledger decision, not a default.** Acceptance in ①
always asks whether to enter the optional visual-design interstitial. Acceptance
in ③ always asks whether to work on deployment. Declining deployment records a
successful local completion and enqueues no Azure job. If deployment is accepted,
Phase ④ remains read-only until a trusted, accepted deployment specification and
explicit mutation consent name the tenant, subscription, scope, environment, cost
boundary, verification contract, and recovery policy. See
[ADR-0014](../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md).

### 6.3 Cycle and deployment-attempt accounting

Every pass through the machine increments `cycle`. The ledger, worktree branches,
and artifacts are all `cycle`-scoped, so cycle 3's build does not overwrite cycle
2's evidence. `max_cycles` (default 10) is a hard stop that raises a human gate
rather than looping forever.

Phase ⑤ also increments a separately bounded `deployment_attempt` for each
apply/release attempt. Retryable failures remain autonomous only while attempt,
elapsed-time, and cost caps allow. Reaching a cap raises a Phase ⑥ human gate;
it never turns into an unbounded cloud loop.

### 6.4 Transition guards

A transition fires only when its guard holds. Guards are pure functions in
`domain/phase.py`, registered per edge in `_GUARDS`; an edge not in `_EDGES` is
always denied, a project whose stored phase this vibey does not recognise
(`UnrecognizedPhase`, written by a newer vibey during a rolling upgrade) is never moved,
and no edge except `→ ABANDONED` is legal once `cycle > max_cycles`. The table lists what
the registered guards check today:

| Transition | Guard (as implemented) |
|---|---|
| `DESIGN → VISUAL_DESIGN` | ≥1 acceptance criterion, no open blocking question, no DESIGN job of this cycle still unsettled (research, synthesis and spec must have finished), no unmapped criterion, user verdict `ACCEPT`, explicit visual-design opt-in |
| `DESIGN → BUILD` | the same five design checks, plus an explicit visual-design decline |
| `VISUAL_DESIGN → BUILD` | visual plan accepted or explicitly waived, and a complete screen/state inventory |
| `BUILD → REVIEW` | ≥1 work item; every work item `integrated` or `waived`; integration branch green; every acceptance criterion has a passing test; a build savepoint exists at the integration head |
| `BUILD → DESIGN` | ≥1 work item is `blocked_on_ambiguity` |
| `REVIEW → DONE` | no open findings and user verdict `ACCEPT` |
| `REVIEW → DEPLOY_DESIGN` | explicit deployment opt-in |
| `DONE → DEPLOY_DESIGN` (and legacy `DONE → DEPLOY`) | explicit deployment opt-in |
| `DEPLOY_DESIGN → DEPLOY_EXECUTE` | deployment spec accepted and deployment consent recorded |
| `DEPLOY_EXECUTE → DEPLOY_REVIEW` | deployment verified, or classified as needing user input |
| `DEPLOY_REVIEW → DONE` | deployment demo accepted |

The remaining edges (`INTAKE → DESIGN`, `REVIEW → DESIGN|BUILD`, the ④/⑤
self-edges, `DEPLOY_REVIEW → *` other than `→ DONE`, the legacy
`REVIEW → DEPLOY` and `DEPLOY → *`, and `* → ABANDONED`) carry no domain guard; the handler that
requests them decides. Review routing uses `next_phase_after_review` (ADR-0010);
the deployment retry ladder's attempt/time/cost caps live in
`domain/deployment.py::evaluate_retry_ladder`.

---

## 7. The queue

### 7.1 Why PostgreSQL

SQLite is the tempting choice for a local tool — no daemon, one file. It is the
wrong choice here, for one concrete reason: **SQLite has no row-level locking and
therefore no `SELECT … FOR UPDATE SKIP LOCKED`.** WAL mode fixes reader/writer
blocking, not writer/writer contention, and vibey's whole point is N workers
competing for jobs. The known workarounds (mark-then-return) leak leases when a
worker crashes — precisely the failure vibey must survive.

PostgreSQL gives `SKIP LOCKED`, `LISTEN`/`NOTIFY` for wakeups, `jsonb` with GIN
indices for the ledger, and advisory locks for phase transitions. It is also
already the storage substrate in the sibling `apg-*` projects, so the operational
knowledge is not new.

*Corrected 2026-09-20.* The planned `vibey up` supervisor with Compose and
`pg_ctl` fallbacks was not built. The DSN is still read from `VIBEY_PG_URL` and
nothing else; a missing value is a hard error (`DatabaseNotConfigured`), never a
guessed localhost database — an earlier silent fallback once wrote 78 test
projects into a production database. `vibey install --postgres` now installs
and starts a native local PostgreSQL service when Homebrew, apt, or dnf is
available. Bring the database with that command, a container, or the Helm
chart's `postgres:17-alpine`, then set the explicit DSN.

See [ADR-0002](../architecture/decisions/0002-postgres-not-sqlite.md).

### 7.2 Job lifecycle

```mermaid
stateDiagram-v2
    [*] --> ready: enqueue
    ready --> leased: worker claims<br/>(SKIP LOCKED)
    leased --> ready: lease expired<br/>(worker died)
    leased --> succeeded: handler returns ok
    leased --> ready: retryable failure<br/>(backoff)
    leased --> awaiting_human: handler parks
    leased --> awaiting_capacity: all engines circuit-open<br/>(state defined; no query sets it yet)
    awaiting_human --> ready: gate answered
    awaiting_capacity --> ready: a circuit half-opens
    leased --> failed: attempts exhausted
    ready --> cancelled: vibey abandon, or the<br/>abandon answer to a defect gate
    failed --> ready: operator requeue
    succeeded --> [*]
    failed --> [*]
    cancelled --> [*]
```

The claim query is the standard pattern:

```sql
UPDATE job SET
    state          = 'leased',
    lease_owner    = $1,
    lease_expires_at = now() + $2::interval,
    attempts       = attempts + 1
WHERE id = (
    SELECT j.id FROM job j
    WHERE j.state = 'ready'
      AND j.run_after <= now()
      AND j.project_id = $3
      AND NOT EXISTS (
          SELECT 1 FROM job_dependency d
          JOIN job p ON p.id = d.depends_on_job_id
          WHERE d.job_id = j.id AND p.state <> 'succeeded'
      )
    ORDER BY j.bump_seq ASC NULLS LAST, j.priority DESC, j.run_after ASC, j.id ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING *;
```

Full DDL, indices, and the reaper query are in [data-model.md](data-model.md).

### 7.3 Job kinds

*Updated 2026-11-24 to the kinds registered in `bootstrap.py`.* The effort
column is design intent; the engine actually receives the effort the rotator
and escalation ladder resolve (§9.3).

| Kind | Phase | Parallel? | Isolation | Typical effort |
|---|---|---|---|---|
| `design.interview` | ① | no (one conversation) | none | `HIGH` |
| `design.research` | ① | yes | none | `STANDARD` |
| `design.synthesize` | ① | no | none | `HIGH` |
| `design.spec` | ① | no | none | `HIGH` |
| `visual.inventory` / `visual.plan` | optional visual stage | no | none | `HIGH` |
| `build.decompose` (alias `build.plan`, enqueued by the review fast path) | ② | no | none | `STANDARD` |
| `build.implement` | ② | **yes** | worktree | `LOW` ↑ |
| `build.verify` | ② | yes | worktree | `LOW` |
| `build.integrate` | ② | no (advisory lock per cycle, [ADR-0029](../architecture/decisions/0029-integrate-serialized-by-advisory-lock.md)) | integration branch | `STANDARD` |
| `review.demo` | ③ | no | read-only worktree | `HIGH` |
| `review.collect` | ③ | no | none | `HIGH` |
| `review.triage` | ③ | no | none | `HIGH` |
| `review.deployment_choice` | ③ | no | none | — (records the opt-in or decline) |
| `review.publish` | ③ → `DONE` | no | the project's repository | — (pushes the branch and opens a pull request, or creates the repository, when `[publish] mode` is `interview` or `auto`; `off` by default) |
| `deploy.interview` / `deploy.design` / `deploy.synthesize` / `deploy.spec` (alias `deploy.accept`) | ④ | no | none | `HIGH` |
| `deploy.execute` (alias `deploy.graph`) | ⑤ | dependency-ordered | accepted Azure scope | `LOW` ↑ |
| `deploy.demo` / `deploy.triage` / `deploy.route` | ⑥ | no | read-only Azure evidence | `HIGH` |

The planned `visual.prompt`, `visual.review`, `media.generate.*`,
`media.moderate`, `media.preview`, the separate `deploy.discover` … `deploy.recover`
kinds, and `deploy.collect` do not exist. **Handoff is not a job kind:** on a
capacity rejection or wind-down, the worker runs produce → verify → accept
in-process (`application/rotation_handoff.py`, `handoff_orchestration.py`) before
releasing the job (§8.5).

### 7.4 Leases, retries, idempotency

- **Lease duration** is per-kind (`build.implement` and `build.verify` get 2
  hours; `build.decompose`, `build.plan`, `build.integrate` and `review.publish` get
  15 minutes; every other kind gets 2 minutes; `_KIND_LEASES` in `bootstrap.py`) and
  extended by a heartbeat every `lease/3`.
- **Priority and reaping.** An operator, or a source `[queue]` declares, may bump a job to
  run next, after what is running and ahead of all un-bumped work
  ([ADR-0054](../architecture/decisions/0054-a-bumped-job-runs-next.md); `vibey queue`;
  `JobPriorityBumped` events). Everything the queue guards is reaped by measured, declared
  thresholds, and no dead letter is ever deleted
  ([ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md);
  `QueueReaped` events).
- **Retry backoff** is exponential with full jitter, capped at 15 minutes.
- **Idempotency** is enforced by `idempotency_key` — a deterministic hash of
  `(project_id, cycle, kind, subject)`. Re-enqueueing the same logical work is a
  no-op. Handlers additionally guard their own side effects: `build.implement`
  checks whether its worktree branch already contains a completed savepoint
  before spending a turn.
- **Poison jobs** park on an `attempts_exhausted` human gate once `attempts`
  reaches `max_attempts`, rather than moving to `failed` where nothing asks
  anyone. Answering `--raw '{"max_attempts": N}'` widens the bound on the row
  itself, so the granted retries survive the next nack.
- **Bounded repair ladders park.** A failing verify or integrate enters a bounded
  repair ladder (3 rounds); its end is a parked human gate that can grant more
  rounds, never a terminal failure
  ([ADR-0024](../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md)).

---

## 8. The conversation ledger and handoff

This is the mechanism behind "rotate engines without losing data." It is
specified in full in [handoff-protocol.md](handoff-protocol.md); this section is
the summary.

### 8.1 Event sourcing, not transcript copying

The source of truth for "what has been said and decided" is an **append-only
event log** in Postgres, written in a vendor-neutral schema. Vendor transcripts
(`~/.claude/projects/**/*.jsonl`, codex rollouts, the local runner's run directories) are copied
in as *attachments* referenced by events — they are evidence, not state.

This follows the ESAA-Conversational result (cited in
[ADR-0003](../architecture/decisions/0003-event-sourced-ledger.md)): replaying a logical
event log produces consistent state in a receiving agent even when the two agents' internal
representations differ, whereas passing "fragile context strings" does not.

### 8.2 Event types

`EventKind` in `domain/ledger.py` has 56 members (counted 2026-11-24). The original 26:

`SessionSeeded`, `TurnRequested`, `TurnCompleted`, `ToolInvoked`,
`TranscriptRecorded`, `FileEdited`,
`VerdictRendered`, `CapacityRejected`, `DecisionRecorded`, `QuestionAsked`,
`AnswerGiven`, `AssumptionStated`, `ArtifactProduced`, `SavePointCreated`,
`FindingRaised`, `FindingResolved`, `HandoffInitiated`, `HandoffAccepted`,
`PhaseTransitioned`, `BudgetSpent`, `VisualDesignOptedIn`,
`VisualDesignDeclined`, `VisualDesignAccepted`, `VisualDesignWaived`,
`DeploymentOptedIn`, `DeploymentDeclined`.

Added since, grouped by what they record:

| Group | Kinds |
|---|---|
| Stages and publishing | `StageSettled`, `PublishCompleted`, `PublishSkipped`, `DeliveryEstimateRecorded` |
| Queue | `JobPriorityBumped`, `JobPriorityUnbumped`, `JobPriorityRefused`, `QueueReaped`, `JobFailed` |
| Budget and ULTRA | `BudgetCapChanged`, `UltraStarted`, `UltraStopped`, `UltraPassCompleted`, `UltraNoCapChanged` |
| Gates | `GateAnswered`, `GateWithdrawn`, `GateNotified`, `GateNoticeUndeliverable` |
| Hub devices | `HubDevicePaired`, `HubDeviceRevoked` |
| Engines | `EngineFailedOver`, `EngineProbed`, `EngineHandedBack`, `EngineSlotWaitStarted`, `EngineOverflowSelected`, `EngineDispatchMeasured` |
| Research and the web | `ResearchGapRecorded`, `WebSearched`, `WebFetched` |
| Loops | `LoopCapabilitiesSnapshotted` |

A stored kind this vibey does not know reads as an `UnrecognizedEventKind`: kept, shown, and
never acted on, so an older worker survives a newer worker's events during a rolling upgrade.

Every event carries `(event_id, project_id, cycle, phase, seq, kind, engine_id,
job_id, causation_id, correlation_id, provenance, produced_at, payload,
digest)`; `provenance` is `trusted`, `agent` or `untrusted`. `seq` is a
per-project gapless integer minted by the `append_event()` SQL function from the
per-project `event_seq` table (not a `CREATE SEQUENCE`), unique on
`(project_id, seq)`, so "the ledger from seq 1200 to 1478" is an exact,
verifiable range.

### 8.3 Two projections, one truth

| Projection | Where it goes | Size |
|---|---|---|
| **`HandoffBrief`** | Into the receiving engine's *prompt* | bounded, ~2–6k tokens |
| **`FullLedger`** | Written to `<worktree>/.vibey/handoff/ledger.jsonl` | unbounded |

The receiving agent is *told, in its seed prompt*, that the full ledger is on
disk and how to read it. The brief exists to make the first turn cheap, not to be
the only thing available. This is the resolution to the compact-vs-full tradeoff:
the compact view is the *prompt*, the full log is the *filesystem*.

### 8.4 The no-loss gate

Before a handoff is accepted, `domain/noloss.py` runs a **pure, deterministic
predicate** over `(ledger_range, brief)`:

| Check | Rule |
|---|---|
| `R1 remaining-work closure` | Every item in the last `VerdictRendered.remaining_work` appears in `brief.remaining` |
| `R2 open-question closure` | Every `QuestionAsked` without a matching `AnswerGiven` appears in `brief.open_questions` |
| `R3 decision closure` | Every `DecisionRecorded` not marked superseded appears in `brief.decisions` |
| `R4 assumption closure` | Every `AssumptionStated` appears in `brief.assumptions` |
| `R5 finding closure` | Every `FindingRaised` with `state != resolved` appears in `brief.open_findings` |
| `R6 range integrity` | `brief.ledger_ref.digest` equals the recomputed digest of `[from_seq, to_seq]`, `to_seq` equals the highest seq in the range the gate was handed, and `event_count` matches (`domain/noloss.py`) |
| `R7 artifact closure` | Every `ArtifactProduced` whose payload sets `referenced_by_open_item` appears in `brief.artifacts` — the event's writer, not the gate, decides what counts as referenced |
| `R8 budget carry` | `brief.budget` equals the ledger-derived spend |
| `R9 constraint closure` | Every hard constraint in the accepted spec appears in `brief.constraints` |
| `R10 containment` | No free-text field of the brief carries a denylisted phrase (tool grants, permission changes, acceptance-criteria mutation, prompt-injection phrases) — the brief cannot rewrite the contract |

Matching is by stable `item_id`, not by string similarity — every closable thing
gets an id when it is first recorded, so the check is exact rather than fuzzy.

**On failure:** regenerate the brief (up to 3 attempts, each time feeding back the
specific rule that failed) → then escalate to `full_transcript` mode → then raise a human gate. It never proceeds on
a failed gate. In `full_transcript` mode only R6, R8 and R10 are evaluated. The design
inlines the whole ledger range so the closure rules hold by construction; as built,
the range is delivered as `.vibey/handoff/ledger.jsonl` in the receiving worktree and
named in the seed, not inlined, so the waiver rests on the successor reading it.

### 8.5 Handoff sequence

```mermaid
sequenceDiagram
    participant W as Worker
    participant R as Rotator
    participant L as Ledger
    participant G as No-loss gate
    participant A as Engine A (outgoing)
    participant B as Engine B (incoming)

    W->>A: work in progress
    A-->>W: CapacityRejected(CreditsExhausted)
    W->>L: append CapacityRejected
    W->>R: next_engine(exclude=A)
    R-->>W: Engine B
    W->>L: append HandoffInitiated
    W->>A: request brief (or synthesize if A is dead)
    A-->>W: HandoffBrief (draft)
    W->>G: verify(ledger_range, brief)
    alt gate passes
        G-->>W: OK
    else gate fails
        G-->>W: violations[R2, R5]
        W->>A: regenerate with violations
        Note over W,G: ≤3 attempts, then full_transcript, then human gate
    end
    W->>L: append HandoffAccepted (envelope digest)
    W->>B: seed(brief + ledger.jsonl on disk + worktree)
    B-->>W: TurnCompleted
```

The sequence runs in-process inside the worker that hit the rejection
(`RotationHandoffService` plus `handoff_orchestration`); it is not a queued job.

**When Engine A is unreachable** (crashed, credits gone, binary missing), the
brief is synthesized by the *incoming* engine, or by any healthy engine, reading
the ledger directly. The gate is identical either way — that is the point of
making it deterministic rather than trusting the author.

---

## 9. Engine rotation

Full specification in [rotation-and-engines.md](rotation-and-engines.md).

### 9.1 The capability problem

The runners are not interchangeable at the CLI level. Divergence as recorded in
`infrastructure/engines/descriptors.py` (checked against each binary's
`run --help` by the conformance suite; updated 2026-11-24; `vibey loops --json` prints
every engine's full facts):

| | claudeloop | codexloop | gptossloop / qwenloop | claudeloop-local |
|---|---|---|---|---|
| Tier | paid | paid | local | local |
| Effort at invocation | `--preset` + `--effort`; ULTRA is the top tier with no turn limit | **none** — `run` has no effort flag; every level projects to `STANDARD` | `--max-turns` 8 / 16 / 40 / 64 / 96; ULTRA passes no flag | `--profile <name> --preset low/medium/high`; HIGH and above achieve `STANDARD` |
| Top-level `savepoints` / `effort` commands | yes | yes | echo-only stubs (qwenloop `cli/app.py`) | yes (same binary as claudeloop) |
| `sessions`/`threads` | `sessions` | `threads` | `sessions` | `sessions` |
| Isolation flag passed by vibey | none verified | none verified | none | none verified |
| Plan argument | positional | positional (no `--cwd`) | positional | positional |
| Capability snapshot (`run --capabilities PATH`) | yes | no | yes | yes |
| State dir | `.claudeloop/` | `.codexloop/` | `.qwenloop/` (both engines) | `.claudeloop/` |
| Base weight | 3 | 2 | 1 | 1 |

The originally planned sandbox flags (`--permission-mode`, `--sandbox`,
`--hooks-policy`) were found not to exist or not to mean container isolation and
were removed from the descriptors. The plan also had columns for `cursorloop` (a
`--model` ladder and a `--plan <path>` argument) and `agyloop` (a `--safe` flag); both
engines were retired and deleted by
[ADR-0078](../architecture/decisions/0078-retire-cursorloop-and-agyloop.md).

Treating these as one interface by hoping is how an orchestrator breaks the first
time it hands `--effort` to an engine that has no such flag. Instead:

### 9.2 Capability matrix + normalized ladder

Each engine ships an `EngineDescriptor` declaring what it supports. Vibey's domain
speaks its own six-level ladder — `TRIVIAL, LOW, STANDARD, HIGH, MAX, ULTRA` — and each
descriptor provides a **projection** onto native flags, which may *saturate*. `ULTRA`
([ADR-0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md)) is effort
without a ceiling: it is chosen (`vibey ultra`), never escalated into, and an engine runs it
with no turn limit, pass after pass, until a stop or a budget cap.

```
Effort.MAX    →  claudeloop        --preset high --effort max
              →  codexloop         (no flag)                         (saturates at STANDARD)
              →  gptossloop        --max-turns 96                    (turn budget; qwenloop the same)
              →  claudeloop-local  --profile local --preset high     (saturates at STANDARD)

Effort.ULTRA  →  claudeloop        --preset high --effort max        (no --max-turns)
              →  codexloop         (no flag)                         (saturates at STANDARD)
              →  gptossloop        (no flag)                         (no turn limit; re-invoked pass after pass)
              →  claudeloop-local  --profile local --preset high     (saturates at STANDARD)
```

A job declares `requires: {effort: HIGH, capabilities: {savepoints}}`. The
rotator only considers engines whose descriptor satisfies it. An engine that
saturates below the requested effort is *still eligible* but carries a
`fidelity_penalty` that lowers its rotation weight — so vibey prefers an engine
that can genuinely do `MAX` work, without refusing to use one that can't when it's
the only one with capacity.

### 9.3 Effort policy per phase

| Phase | Base | Escalation |
|---|---|---|
| ① DESIGN | `HIGH` | → `MAX` if the user rejects a synthesized spec twice |
| ② BUILD | `LOW` | → `STANDARD` after 2 failed verifies on one item; → `HIGH` after 4; → human gate after 6 (the gate can grant more, [ADR-0024](../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md)) |
| ③ REVIEW | `HIGH` | → `MAX` for `severity=critical` triage |

Escalation is per work item, not global, and resets when the item succeeds. This
is what keeps the user's "Phase 2 uses low effort" requirement from turning into
"Phase 2 never finishes the hard item."

### 9.4 Smooth weighted round robin

Vibey uses **nginx's SWRR** algorithm rather than naive modulo rotation, because
naive rotation over a set whose membership changes (engines dropping in and out as
circuits open) produces starvation and clumping.

```
for each selection:
    for e in eligible:  e.current += e.effective_weight
    winner = argmax(e.current)
    winner.current -= sum(e.effective_weight for e in eligible)
```

`effective_weight = round(base_weight × health_factor × fidelity_factor ×
cost_factor × affinity_factor)`, never rounded below 1 for a positive product.
Health is 1.0 closed (decayed by an EWMA of failures), 0.25 half-open, 0.0 open;
fidelity is 1.0 at the requested tier, 0.7 one tier short, 0.5 two or more short;
cost, when enabled, is the median-to-engine cost ratio clamped to [0.5, 1.5]
(`EngineSelector` passes 1.0 today, so cost does not yet bias selection); affinity is 2.0
for the engine holding the warm session unless rotation is forced — the
stickiness rule of §9.6. All are pure functions in `domain/rotation.py`,
unit-tested for the properties that matter: **no starvation** (every eligible
engine is selected within `sum(weights)` selections), **determinism** (same state
→ same choice), and **smoothness** (selections interleave across the period
rather than bunching; with weights 5:1 the heavy engine still wins several rounds
in a row — SWRR does not promise no consecutive repeats).

`domain/rotation.py::select()` is called from the real dispatch path through
`application/engine_selector.py::EngineSelector`, with per-project cursors
persisted in `rotation_cursor`.

### 9.5 Eligibility and circuit breakers

An engine is eligible when: installed, authenticated (`doctor` passed within TTL),
circuit not `open`, capability requirements met, and per-phase allow-list permits
it.

**Local tier, preferred first** ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md),
amending [ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)'s standby rule). `gptossloop`,
`qwenloop` and `claudeloop-local` are local, zero-dollar engines, each behind its
`[features]` key or `VIBEY_FEATURE_*` switch: `gptossloop` is on unless switched off,
the other two are off unless switched on
([ADR-0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)). When enabled they are
preferred: `EngineSelector` runs SWRR within the LOCAL tier and a paid engine is
selected only when no local engine is eligible. In code: each descriptor carries a
`tier: EngineTier` (`LOCAL` or `PAID`), `TIER_PREFERENCE = (LOCAL, PAID)` in
`domain/engine.py` fixes the order, and `domain/rotation.py::preferred_tier()` picks the
first tier with an eligible candidate. The two tiers are also the family's two loops,
`sovereignloop` and `paidloop` (`Loop`, `LOOP_BY_TIER`, `DEFAULT_LOOP = sovereignloop`;
sub-doctrine 8.c), which `vibey loops` reports. Separately, DESIGN and DECOMPOSE run
on a local model — `--provider gptossloop`, the default on `vibey work` and `vibey
worker` — which talks to the local model directly rather than through rotation
([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)).

**Hybrid dispatch** ([ADR-0079](../architecture/decisions/0079-hybrid-engine-dispatch.md),
`domain/engine_dispatch.py`). Under `[engines] mode` a job may wait for a local slot for a
bounded time and then overflow to a paid engine within a daily cap; each wait, overflow and
measurement is a ledger event (`EngineSlotWaitStarted`, `EngineOverflowSelected`,
`EngineDispatchMeasured`). The full rules are in
[rotation-and-engines.md](rotation-and-engines.md).

**Failover and handback** ([ADR-0070](../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md),
`domain/failover.py`, `application/engine_failover.py`). The design moves work from a paid
engine whose credit is gone to the sovereign engine, through the same no-loss gate, and hands
it back when a recorded probe passes (`EngineFailedOver`, `EngineProbed`, `EngineHandedBack`).
The service is built and tested but no worker constructs it yet; only the driver session's
failover (`vibey driver`) is wired.

```mermaid
stateDiagram-v2
    closed --> open: CreditsExhausted<br/>or 3 consecutive failures
    closed --> open: AuthenticationFailed
    open --> half_open: probe window elapsed<br/>(resets_at for WindowExhausted,<br/>backoff probe for CreditsExhausted)
    half_open --> closed: probe succeeds
    half_open --> open: probe fails
```

The distinction the `*loop` family fought for is preserved exactly:
`WindowExhausted` half-opens at `resets_at` (plus deterministic jitter), or,
when no reset time is known, on a backoff (2 s doubling, capped at 5 minutes);
`CreditsExhausted` has no deadline and half-opens on a backoff floored at 5
minutes and capped at 30, because only a human top-up can fix it.
`AuthenticationFailed` never schedules a probe.

### 9.6 When rotation happens

**At boundaries only** — never mid-turn.

| Trigger | Rotate? |
|---|---|
| New work item starts | yes (advance cursor) |
| Capacity rejection | yes (forced, exclude the rejecting engine) |
| Effort escalation | yes (re-select for the new tier) |
| Phase transition | yes |
| Handoff requested by operator | yes |
| Mid-turn | **never** |
| Item retry after transient failure | no (stickiness — keep the warm session) |

Stickiness matters: rotating on every turn would mean a handoff on every turn,
which is both expensive and lossy-prone. Vibey rotates when there is a *reason*.

---

## 10. Agent-surface provisioning

The source diagram calls for an "automated repository for I.D.E.'s." Concretely:
every engine reads different guidance files, and if they disagree, rotating
engines silently changes the rules mid-project.

*Updated 2026-09-15 to what `infrastructure/provision/agent_surface.py` does.*
Vibey renders one block from a `ProvisionSpec` (non-negotiables and plugin
names) and merges it into a router file per engine at the root of each
`build.implement` worktree. The production wiring passes an empty spec today —
`[provision] plugins` is not read at runtime (§17) — so the rendered block lists
`- None` under "Non-negotiables" and `none` under "Skill plugins", and points at
`.vibey/context/`:

| Engine | Router file written |
|---|---|
| claudeloop, claudeloop-local / Claude Code | `CLAUDE.md` |
| codexloop / Codex | `AGENTS.md` |
| gptossloop / qwenloop | `QWEN.md` |
| (no engine since ADR-0078) | `CURSOR.md` |
| (no engine since ADR-0078) | `GEMINI.md` |

`RouterFile` in `domain/provision.py` still lists all five files and every one is written.
`CURSOR.md` and `GEMINI.md` were the router files of `cursorloop` and `agyloop`; those
engines are retired and no engine vibey runs reads the two files, but `RouterFile` has not
dropped them. Only the router files are written. The block sits between
`<!-- vibey:begin -->` / `<!-- vibey:end -->` markers; hand-written content
outside the markers is preserved. It names the non-negotiables, the declared
plugin names, and the shared `.vibey/context/` directory (spec, acceptance
criteria, NFRs, decisions, open items). The router files, the engines' state
directories (`.claudeloop/` … `.qwenloop/`), `.vibey/`, and common build
artifacts are added to `.git/info/exclude` so engine sessions cannot commit
them. `.claude/skills/`, `.claude/settings.json`, `.cursor/rules/` and similar
directories are not materialized.

Skill guidance comes instead from the independently versioned `vibey-skills`
package (formerly `vibe-engineering-skills`; 18 plugins and 71 skills when this was
written, 153 plugins and 826 `SKILL.md` files on 2026-11-24, counted from
`src/vibey_tools/skills/.claude-plugin/marketplace.json` and `plugins/`). The
conductor never imports it: `infrastructure/skills_context.py` asks the
`vibey-skills` CLI, over a subprocess, for one bounded packet per implement job
and writes it under `.vibey/context/skills/`. It runs in one of three modes —
`off` (default), `shadow`, `inject` — with a token budget (default 6000), set by
`vibey new --skills-context-mode/--skills-context-budget`
([ADR-0031](../architecture/decisions/0031-skills-context-packets-over-a-process-boundary.md)).

Provisioning is idempotent: a sha256 digest comparison (`needs_write`) skips any
file whose merged content is already present.

---

## 11. Isolation

```
repo/                              ← never checked out by a build job
└── .vibey/
    └── worktrees/
        └── 1a2b3c4d/              ← project scope: the first 8 hex digits of the project id
            └── 3/                 ← cycle
                ├── item-014/      ← git worktree, branch vibey/1a2b3c4d/3/item-014
                ├── item-015/
                └── integration/   ← branch vibey/1a2b3c4d/3/integration
```

The project scope was added by the ADR-0008 amendment (2026-09-30) so two projects in one
repository never share a branch (`domain/worktree.py::WorktreeNaming`). The older
cycle-only name (`vibey/3/item-014`) is still recognised when read, as `legacy_branch`, but
is never created.

Each `build.implement` job gets its own git worktree and branch. Parallel items
never share a working tree, which removes the shared mutable resource rather than
trying to lock it.

**A worktree is not a sandbox.** It prevents agents from overwriting each other;
it does not prevent an agent from running `rm -rf ~`. Vibey therefore offers three
isolation levels, selected per project:

| Level | Mechanism (design) | Protects against | Status (2026-09-15) |
|---|---|---|---|
| `worktree` (default) | git worktree + destructive-command denies | concurrent-edit corruption | Implemented: worktree per item and engine state dirs excluded from git. The deny-list exists in `domain/command_guard.py` but nothing calls it yet. |
| `container` | Docker/Podman, repo bind-mounted, network egress allow-listed to provider APIs | filesystem escape, exfiltration | Accepted by config only. `infrastructure/container/` builds a hardened `docker`/`podman run` (read-only root, `--network=none` by default) but the worker never uses it; `isolation.egress` is parsed and unused. |
| `vm` | Firecracker/Lima microVM | kernel-level escape | Accepted by config only; no runtime. |

Until container mode is wired, every level behaves as `worktree`. The planned
`vibey doctor` nudge and an `autonomous` config key were not built. (The vibey
worker image itself runs non-root under `tini`, ADR-0026; that isolates vibey,
not the engine sessions it launches.)

---

## 12. Security

Threat model, in the vocabulary of the `vibey-skills` `threat-modeling-playbook`
and `ai-security-practices` skills:

| Threat | Vector | Control |
|---|---|---|
| **Indirect prompt injection** | A dependency's README, a fetched web page, or a GitHub issue instructs the agent to exfiltrate secrets | Content fetched during a run enters the ledger as `untrusted` provenance; the seed prompt states that ledger content is data, not instruction; egress allow-list in `container` mode (not built, §11) |
| **Cross-engine injection** | A compromised engine writes a poisoned `HandoffBrief` that redirects the next engine | The brief is *structurally verified* against the ledger; gate rule R10 rejects free text carrying tool grants, permission changes, or acceptance-criteria mutation; `brief` cannot alter `spec` or acceptance criteria — those come from the ledger, not the brief |
| **Secret leakage into the ledger** | Agent pastes `.env` contents into a turn | `infrastructure/ledger/redact.py` (ported from the `*loop` family) runs on every event before append; ledger columns are redacted at write, not at read |
| **Runaway cost** | An agent loops, burning tokens | Hard per-phase and per-project budget caps in `domain/budget.py`; the "AI cost snowball" is a documented incident class, so caps are mandatory, not optional |
| **Destructive command** | `rm -rf`, `git push --force`, `DROP DATABASE` | Deny-list defined in `domain/command_guard.py` (hard reset, force push, deleting main/master, `rm -rf /`, `mkfs`, `dd of=/dev/*`, `DROP DATABASE/TABLE`, …); **not yet called** by any adapter, and container mode is not wired (§11). `allow_push` defaults to `false` |
| **Credential handling** | Provider keys | Vibey never reads provider keys. Each engine authenticates itself from its own env/keychain; vibey only observes `doctor` exit codes |
| **Media egress / provider retention** *(planned with §14 generation)* | Visual stage sends source, prompts, or reference assets to a hosted generator | Visual opt-in shows provider, region, retention, cost, and egress; hosted generation requires `media.allow_external = true`; local-first is the default |
| **Generated harmful or infringing media** | A model returns unsafe, deceptive, or unlicensed output | Provider/content-safety scan, provenance and rights metadata, human review, and an explicit reject/regenerate/waive decision before BUILD |
| **AI voice misrepresentation** | Generated narration is presented as a human recording | Store voice/provider metadata and disclose AI-generated audio wherever the selected provider or policy requires it |

Vibey does not run `git push`, open pull requests, or mutate Azure without
explicit, scope-bound authorization. The one path that pushes and opens a pull request is
`review.publish`, and it runs only when the project declares `[publish] mode = "interview"`
(a `publish_interview` gate shows exactly what would be pushed and where, and waits) or
`"auto"`; the default is `off`, a new repository is private and a pull request is a draft
unless declared otherwise, and nothing forces a push or touches the default branch
(`PublishConfig` in `domain/config.py`). Deployment entry is never automatic; it
occurs only after the explicit deployment opt-in gate. The default posture
remains local branches, opted-out media generation, and no Azure discovery or
mutation until a human accepts each corresponding opt-in.

Two surfaces added since this table was written carry their own controls: the hub grants
each paired device and the MCP agent principal a scope ceiling (the agent never holds
`spend`; [ADR-0071](../architecture/decisions/0071-hub-pairing-and-trust.md),
[ADR-0100](../architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md)),
and web search and fetch run through vibey's own policy and record every call on the ledger
([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)).

---

## 13. Observability and cost

- **Structured logs** — `structlog`, dual transport (human console + JSON lines),
  matching the `*loop` convention.
- **Traces** — `infrastructure/otel.py` records spans and counters in-process;
  `bootstrap.py` constructs it and `WorkerLoop`, BUILD, and handoff orchestration
  emit runtime spans. No external exporter is configured yet. The design:
  OpenTelemetry spans,
  one per job, child spans per engine turn, per
  tool invocation, per handoff. `phase`, `cycle`, `engine_id`, `job_kind`, and
  `effort` are span attributes so any of them can slice a latency or cost query.
- **Metrics** *(same module)* — the active recorder covers queue latency, phase
  duration, handoff gate failure rate by rule, per-engine selection counts (to
  prove rotation fairness in production, not just in unit tests), and cost spend;
  job queue depth by state, lease expiry rate, and media-provider selection counts by
  modality, media generation latency/failure/retention, tokens and dollars by
  phase/engine/provider/cycle.
- **Cost** — every `TurnCompleted` carries `cost_usd`; `domain/budget.py` maintains
  the ledger. `vibey cost` reports by phase, cycle, engine, and work item.
  The `azure-bootstrap` AI usage tracker's sliding-window/soft-cap model is the
  reference for the caps implementation.
- **Notifications** — `infrastructure/notify/` implements desktop alerts and
  signed webhooks; `bootstrap.py` wires it to gate raises and project phase
  transitions when `[notifications] enabled = true` is copied by `vibey new`.
- **The TUI** (`vibey watch`, `tui/dashboard.py`) shows: current phase and cycle,
  the visual-design and deployment decisions, per-engine circuit state, queue
  depth by job state, active worktrees, and a tail of the ledger. There is no
  media-provider state to show until §14 generation exists.

---

## 14. Optional pre-build visual design and media stage

> **Implementation status (2026-09-15).** Built: the `visual.inventory` and
> `visual.plan` jobs (inventory from the accepted spec, published as a reviewable
> artifact), the domain types in `domain/visual.py`, a pure per-modality
> provider selector in `domain/media.py`, `vibey visual accept|waive`, the
> `VisualDesign*` ledger events, and the `VISUAL_DESIGN → BUILD` guard (plan
> accepted or waived, inventory complete). Not built: the `MediaProvider` port,
> `infrastructure/media/`, the prompt/generate/moderate/preview/review jobs,
> persisted per-modality cursors (`rotation_cursor` has no modality column), the
> route back to ① of §14.1, and the `[visual]` / `[media.providers]`
> configuration. `domain/media.py` has no consumer outside `domain/`. The rest of
> this section is design intent.

This is an optional, unnumbered interstitial between Phase ① DESIGN and Phase ②
BUILD. The user is asked after the accepted product specification is produced.
Declining it records a `VisualDesignDeclined` event and takes the normal
`DESIGN → BUILD` edge. Opting in creates a durable visual stage; BUILD cannot
start until the visual-ready guard passes or the user records an explicit waiver.

### 14.1 Screen and state inventory

`visual.inventory` reads the accepted spec, repository routes/components, design
tokens, existing screenshots/prototypes, and acceptance criteria. It produces a
matrix with one row per screen or surface and explicit states:

| Field | Required evidence |
|---|---|
| Screen identity | route, platform, viewport, create/update decision, acceptance IDs |
| Structure | hierarchy, primary action, navigation, responsive behavior, content density |
| State coverage | loading, empty, error, success, permission, offline, retry, reduced motion |
| Interaction | focus order, keyboard/touch targets, validation, transitions, recovery |
| Accessibility | semantic roles, labels, alt text, captions/transcripts, contrast target, screen-reader intent |
| Media | image/audio/video/icon/illustration IDs, placement, dimensions, format, rights/source constraints |

If the inventory discovers a product requirement that Phase ① did not settle, the
stage raises a scoped design gate and routes back to ①. It must not silently fill
the gap with a generated screen.

### 14.2 Generation plan and provider ports

`visual.plan` derives a design-system contract and a media manifest from the
inventory. A media manifest entry contains `asset_id`, modality, screen/state,
purpose, prompt, reference digests, output constraints, accessibility metadata,
rights/likeness constraints, provider policy, and an acceptance test.

The application layer defines a provider-neutral port:

```python
class MediaProvider(Protocol):
    provider_id: str
    capabilities: frozenset[MediaModality]

    async def generate(self, request: MediaGenerationRequest) -> MediaJob: ...
    async def poll_or_resume(self, job: MediaJob) -> MediaJob: ...
    async def download(self, job: MediaJob) -> MediaArtifact: ...
    async def estimate_cost(self, request: MediaGenerationRequest) -> CostEstimate: ...
    async def moderate(self, artifact: MediaArtifact) -> ModerationResult: ...
```

The exact interface is an application port; the domain sees only immutable
modality, request, outcome, and routing values. Concrete providers live under
`infrastructure/media/`. A provider may be local/self-hosted or hosted. The
default is `local_first`; hosted fallback requires explicit external-media
consent and records destination, region, retention, estimated cost, and policy.

Provider capability discovery happens at the start of the visual stage and is
repeated when a provider becomes unavailable. Model names are configuration and
runtime metadata, never domain assumptions. A provider is eligible only if it
supports the requested modality, dimensions/format/reference inputs, region and
data policy, safety policy, budget, and current capacity.

### 14.3 Per-modality round robin

Image, audio, and video each have an independent persisted smooth round-robin
cursor. Selection is capability-filtered before rotation:

```text
image candidates → image cursor → next eligible provider
audio candidates → audio cursor → next eligible provider
video candidates → video cursor → next eligible provider
```

This preserves fairness without selecting a provider that cannot satisfy the
asset. Cursors advance transactionally only after selection; circuit-open,
capacity-exhausted, policy-ineligible, and budget-ineligible providers are
skipped. Cost/capability/quality/latency factors may affect eligibility and
weights, but no provider is starved inside the eligible set. A provider may be
used for more than one modality while retaining separate per-modality state.

Generation is a dependency-ordered, asynchronous queue graph:

```text
inventory → plan → prompt → generate(modality) → moderate → preview
                                                     ↓
                                           review / regenerate / waive
```

Large video operations return an operation ID and release their worker lease;
polling or webhook jobs resume them. Every job is idempotent by
`(project, cycle, visual_revision, asset_id, provider, prompt_digest)`.

### 14.4 User confirmation and visual-ready guard

`visual.review` presents a screen gallery or prototype, design tokens, responsive
variants, interaction states, image/contact sheets, audio previews plus
transcripts, and video storyboards/clips. The user may accept an asset, request a
regeneration with feedback, provide a replacement, or waive it explicitly. A
regeneration creates a new immutable revision; it never overwrites a prior
accepted asset or its evidence.

The `VISUAL_DESIGN → BUILD` guard requires:

- every inventory row has an accepted screen spec;
- every required asset is accepted, user-supplied, or explicitly waived;
- no blocking design question or unresolved rights/safety issue remains;
- accessibility checks cover contrast, semantics, focus, labels, alt text,
  transcripts/captions, touch/keyboard targets, and reduced motion;
- prompt, provider/model, output, moderation, cost, and user-decision evidence is
  persisted; and
- the user issued `visual design accept` or an explicit visual-stage waiver.

### 14.5 Artifacts

```text
.vibey/context/visual/
├── screen-inventory.md
├── design-system.md
├── screen-specs/<screen-id>.md
├── media-manifest.json
├── prompts/<asset-id>.md
├── assets/<asset-id>/<revision>/...
├── previews/                         # gallery, audio, storyboard/video links
└── visual-review.md                  # accepted/rejected/waived decisions
```

---

## 15. Optional deployment stage set (Phases ④–⑥)

Deployment is the optional second three-phase stage set in the core lifecycle,
governed by [ADR-0014](../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md)
and the execution design in
[ADR-0013](../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md)
and specified turn-by-turn in [phase-protocols.md](phase-protocols.md). Azure
implementations remain behind application ports and optional infrastructure
dependencies so `domain/` stays provider-agnostic and stdlib-only.

After Phase ③ has no open product findings and the user accepts the build, Vibey
asks whether to work on deployment. A “no” answer records `DeploymentDeclined`,
sets `completion_mode = "local"`, and transitions to `DONE` without enqueueing
any Azure job. A “yes” answer records `DeploymentOptedIn` and enables the
following stage set:

1. **④ DEPLOY DESIGN (interactive)** discovers the target and authority, selects
   service topology from requirements, resolves secret *references*, defines IaC,
   migration, cost, health, rollout, and recovery policies, and records consent.
2. **⑤ DEPLOY EXECUTE (autonomous)** creates an immutable plan, runs static and
   provider preflight checks plus ARM `what-if`, provisions idempotently, releases
   progressively when supported, verifies runtime health and acceptance, and
   executes only pre-authorized recovery actions. Retryable failures loop in ⑤;
   authority, ambiguity, unexpected deletion, destructive data change, policy,
   budget, or recovery decisions enter ⑥.
3. **⑥ DEPLOY REVIEW (interactive)** presents a live demo with redacted evidence
   on success, or asks only for the input needed to unblock a classified failure.
   It may finish, revise the deployment contract in ④, retry in ⑤, or return an
   application/specification defect to the appropriate delivery phase.

Success means declared resources converged *and* the workload passed health,
smoke/acceptance, and bake-window checks. A successful CLI exit or ARM operation
alone is insufficient. Every mutation records redacted command intent, operation
and resource IDs, artifact digests, verification evidence, and recovery actions.
Secrets remain in Key Vault or another approved secret store and enter the ledger
only as references. A successful deployment demo sets `completion_mode =
"deployed"`; a later artifact or acceptance change invalidates the previous
deployment choice and asks again.

**Status (2026-09-15).** The stage set, its guards, the ④–⑥ job kinds, the
`vibey deploy status|inspect|plan|cancel|rollback` commands, IaC and ARM
`what-if` evaluation, and an `az`-backed Azure adapter are implemented. The
worker defaults to an in-memory Azure client (`vibey worker --azure memory`), so
no cloud resource is touched unless an operator starts a worker with
`--azure az`, which also requires a logged-in Azure CLI. `[deploy] enabled`
defaults to `false`.

---

## 16. Testing strategy

Following the `vibey-skills` `test-strategy` and `python-quality-testing` skills.
*Updated 2026-09-15:* every layer's floor is 100% branch coverage, each its own
CI gate ([ADR-0023](../architecture/decisions/0023-four-layers-four-floors.md)).

| Layer | Approach | Coverage floor |
|---|---|---|
| `domain/` | Pure unit tests + **property-based** (Hypothesis) for rotation fairness, no-loss gate soundness, phase-machine reachability; an AST-walking purity test | **100% branch** |
| `application/` | Use-case tests against fake ports (`tests/fakes`, checked for parity with the real ports); the worker loop tested with a fake queue | **100% branch** |
| `infrastructure/` (incl. `db`, `engines`) | Integration tests against a real Postgres named by `VIBEY_TEST_DATABASE_URL` (one database per xdist worker) — never mocked, because `SKIP LOCKED` semantics are the thing under test; **engine conformance suite** (below) + a `ScriptedEngine` for offline determinism | **100% branch** |
| `cli` | Typer runner tests | **100% branch** |
| `tests/live` | Two modes ([ADR-0030](../architecture/decisions/0030-two-mode-live-harness.md)): faked (`-m live`, scripted binaries, every descriptor) by default; paid (`-m paid`, real engines) only when explicitly selected | — |
| `tests/contracts`, `tests/meta`, `tests/tui` | Cross-layer contracts; repository invariants (ADR numbering and count, container context); TUI rendering | — |
| End-to-end | `pytest -m system`: scripted engine and in-memory Azure adapter drive `①→(optional visual)→②→③→(optional deploy ④→⑤→⑥)`, including decline, accept, and loop-back paths, on throwaway local resources with no network | — |

Default `pytest` options are `-m 'not paid' -n auto --maxprocesses=8`. The
absorbed packages under `src/vibey_runners/` and `src/vibey_tools/` keep their
own suites and floors in CI ([ADR-0022](../architecture/decisions/0022-absorbed-packages-keep-their-own-gates.md)).

### The engine conformance suite

The runners are pre-1.0 and will drift. Vibey pins their behavior with an
executable contract:

```bash
vibey doctor --conformance           # run against every installed engine
vibey doctor --conformance --record  # persist the result to engine_health
```

It asserts, per engine: the state directory exists where the descriptor says;
`run --help` exposes the flags the descriptor claims; a trivial scripted plan
produces a run directory with `meta.json`, `events.jsonl`, and a snapshot at the
documented paths; capacity classification maps to vibey's ADT; the done marker
matches. A failing conformance check marks that engine ineligible rather than
letting it fail mid-cycle. See
[ADR-0001](../architecture/decisions/0001-orchestrate-do-not-reimplement.md).

Property tests worth calling out specifically:

- **Rotation**: over any eligible set and any weight vector, every engine is
  selected at least once per `sum(weights)` selections (no starvation).
- **No-loss gate**: for any ledger and any brief that *omits* a closable item, the
  gate returns a violation naming that item. Generated adversarially.
- **Phase machine**: every state is reachable from `INTAKE`, and `DONE`/`ABANDONED`
  are the only terminals.
- **Idempotency**: running any handler twice with the same input produces the same
  ledger state (modulo `produced_at`).

---

## 17. Configuration

`vibey.toml` at the project root. *Updated 2026-11-24 to the keys
`domain/config.py` parses; the authoritative schema is
[`docs/reference/configuration.md`](../reference/configuration.md).* `VibeyConfig` has 29
tables: `project`, `isolation`, `budget`, `engines`, `phases`, `provision`, `deploy`,
`notifications`, `telemetry`, `features`, `qwenloop`, `tracker`, `docs`, `secrets`, `files`,
`email`, `sms`, `messaging`, `config_store`, `cache`, `bus`, `blob`, `siem`, `surfaces`,
`queue`, `design`, `build`, `engine_dispatch` (the dispatch keys of `[engines]`) and
`publish`.

**How `vibey.toml` reaches a running vibey.** It is read in three places, and the
earlier claim on this page that it "is not yet a runtime input" is wrong:

1. **At process start.** `StartupConfigResolver.resolve` in
   `infrastructure/config_loader.py` parses `./vibey.toml` in full with `parse_config`
   (`bootstrap.py`). It configures the operational surfaces (tracker, docs, secrets, files,
   email, SMS, messaging, config store, cache, bus, blob, SIEM), telemetry and the queue. A
   file that does not parse is logged and skipped, and the environment alone is read
   instead, so one bad key (a retired engine, say) switches every surface back to its
   in-memory default with only a logged warning (`ignoring ./vibey.toml, which could not be
   used (...)`). Read the worker's log after editing the file.
2. **At `vibey new`.** `load_runtime_config_from_path` copies the runtime tables
   `notifications`, `telemetry`, `gates`, `engine_environment`, `design`, `build`,
   `human_gates`, `publish` and the dispatch keys of `[engines]` into the project's stored
   `config` record, after validating them. Workers read them from there.
3. **By `vibey doctor` and `vibey loops`,** which read the `[features]` local-engine
   switches (`gptossloop`, `qwenloop`, `claudeloop_local`); the worker reads the same keys
   from the project's `config` record.

Parsed and validated, but not read by anything at runtime as of 2026-11-24:
`[engines] enabled` and `[engines.weights]` (rotation uses each descriptor's
`base_weight`), `[phases]`, `[provision] plugins`, `[budget]` (per-project limits come from
the project record written by `vibey new` or the Kubernetes operator) and `[deploy]`. The
planned `[visual]` and `[media.providers]` tables and the extra `[deploy]` keys
(`opt_in_required`, `finish_if_declined`, `environment`, `max_attempts`, `max_dollars`)
are not parsed. `isolation.egress` is parsed but not enforced, and `level` values other
than `worktree` have no runtime yet (§11).

The sample below parses with `parse_config` as of 2026-11-24. The plan's original sample
enabled `cursorloop` and `agyloop`; that file is now refused with
`ConfigError: engines.enabled: unknown engine 'cursorloop' -- cursorloop was retired by
ADR-0078 ...`.

```toml
[project]
name          = "my-app"
repo          = "."
max_cycles    = 10
strict_loopback = false          # true forces REVIEW → DESIGN always

[isolation]
level         = "worktree"       # worktree | container | vm (only worktree has a runtime)
allow_push    = false
egress        = ["api.anthropic.com", "api.openai.com"]  # parsed, not enforced

[budget]                         # parsed; limits come from the project record
max_dollars_per_cycle = 40.0
max_dollars_total     = 250.0
max_turns_per_item    = 60

[engines]
enabled = ["claudeloop", "codexloop"]   # gptossloop (the sovereign default) is
                                 # always added unless [features] gptossloop = false;
                                 # known ids: claudeloop, codexloop, gptossloop,
                                 # qwenloop, claudeloop-local

[engines.weights]                # parsed; rotation uses each descriptor's base_weight
claudeloop = 3
codexloop  = 2

[phases.design]
effort   = "high"
engines  = ["gptossloop", "claudeloop"]    # optional per-phase allow-list (parsed)

[phases.build]
effort      = "low"
parallelism = 4

[phases.review]
effort = "high"

[provision]
plugins = ["software-architecture", "quality-engineering", "security-first-dev", "engineering-process"]

[deploy]
enabled = false                  # default
target  = "openstack"            # the default (sovereign cloud); "azure" has the built adapter
iac     = "bicep"
# Tenant, subscription, scope, region, identity, health, rollout, recovery, and
# secret references are completed and accepted interactively in Phase ④.

[features]
gptossloop = true                # the default; VIBEY_FEATURE_GPTOSSLOOP overrides
qwenloop = false                 # VIBEY_FEATURE_QWENLOOP overrides

[qwenloop]
backend = "auto"                 # auto | llama.cpp | vllm
portable_profile = "qwen2.5-coder-14b-q5-k-m"
nvidia_profile   = "qwen2.5-coder-14b-bf16"
idle_timeout_seconds    = 900
startup_timeout_seconds = 180
context_window          = 32768
```

The skills-context policy (`mode` off | shadow | inject, `budget`) is not a
`vibey.toml` table; `vibey new --skills-context-mode/--skills-context-budget`
stores it in the project's `config` record.

---

## 18. Milestones

Detail, with test-first task breakdowns, in
[implementation-plan.md](implementation-plan.md).

| Milestone | Deliverable | Done when | Status (2026-09-15) |
|---|---|---|---|
| **M0** | Repo skeleton, CI, onion contract, `vibey.toml` schema | `lint-imports` green, empty domain 100% covered | done |
| **M1** | Pure domain: phase machine, effort ladder, rotation, circuit, no-loss gate | Property tests pass; no I/O anywhere in `domain/` | done |
| **M2** | Postgres schema, migrations, queue repo, worker loop | Integration test: 8 workers, 500 jobs, zero double-execution, zero lost jobs under random kills | done, with one qualification: the chaos test (`tests/infrastructure/db/test_chaos.py`) simulates kills in-process by abandoning claimed jobs; no test kills OS processes |
| **M3** | Engine adapters + conformance suite + `ScriptedEngine` | `vibey doctor --conformance` passes against all four installed engines | built: five descriptors today (claudeloop, codexloop, gptossloop, qwenloop, claudeloop-local), `vibey doctor --conformance --record`; no recorded run against every real engine is in the repository ([implementation-plan.md](implementation-plan.md) Definition of Done) |
| **M4** | Ledger, projections, handoff produce/verify/accept | Adversarial no-loss property suite passes; a forced mid-item rotation completes with zero dropped items | done (R1–R10) |
| **M5** | Phase ① DESIGN + optional visual-design interstitial | A real interview can either enter BUILD directly or produce a confirmed screen/media plan before BUILD | partial: DESIGN, inventory/plan, accept/waive; media generation not built (§14) |
| **M6** | Phase ② BUILD end to end | Parallel worktrees, integration, escalation ladder, budget caps | done |
| **M7** | Phase ③ REVIEW + loop-backs + deployment choice | Full delivery loop plus explicit local-complete versus deployment-opt-in routing | done |
| **M8** | TUI, cost reporting, OTel, notifications | `vibey watch` usable for an overnight run | done for runtime recording; external telemetry export remains open |
| **M9** | Isolation levels (container), security hardening, threat-model review | Container mode passes egress allow-list test | partial: container runtime written but not wired; no egress allow-list or `vm` |
| **M10** | Optional Phases ④–⑥: Azure deployment stage set | An explicit opt-in can deploy durably in ⑤ and reach a verified demo or actionable human gate in ⑥; an opt-out finishes locally without cloud work | done; in-memory Azure client unless `--azure az` |

The table stops at M10, where the original plan stopped. Work beyond it is tracked in the
decision records (§20), in `docs/runbooks/expansion/` and in `docs/continuation/`. As of
2026-11-24 that includes: the Kubernetes chart and operator (ADR-0025), the monorepo
absorption (ADR-0021), the sovereign DESIGN provider (ADR-0027), local-first tiers
(ADR-0038), queue priority and reaping (ADR-0054, ADR-0056), the database-enforced
append-only ledger (ADR-0055), ULTRA (ADR-0063), the hub, pairing and device control
(ADR-0068, ADR-0071, ADR-0091), the krypton clients (ADR-0065, ADR-0067, ADR-0073), the
Sabbath (ADR-0072), the retirement of cursorloop and agyloop (ADR-0078), hybrid dispatch
(ADR-0079), `vibey state` (ADR-0086), slicing (ADR-0092), the Heretic v2 default model
(ADR-0099), MCP, ACP and `vibey connect` (ADR-0100, ADR-0101), local-first search
(ADR-0102), the loop capability bundle (ADR-0103) and run inputs (ADR-0104, ADR-0105).

---

## 19. Risks and the honest unknowns

| Risk | Severity | Mitigation |
|---|---|---|
| **The runners drift** — they are pre-1.0 and actively changing | high | Conformance suite (§16) run in CI and at `doctor`; descriptors are versioned and pinned; a failing engine is marked ineligible, not fatal. Since ADR-0021 the runners change in the same repository and CI as their descriptors |
| **The no-loss gate is only as good as the ids** — if an agent records a decision without an id, the gate can't check it | high | Ids are assigned by *vibey* at append time, not by the agent; the agent's free text is the payload, the id is infrastructure |
| **Interactive phases fight the runners' "never block" design** | medium | Vibey owns conversations and parks jobs; runners perform bounded research, visual generation, execution, and demo generation without holding a worker lease while awaiting a human |
| **Round-robin across vendors produces inconsistent code style** | medium | Agent-surface provisioning (§10) gives every engine identical guidance; `build.verify` enforces the project's own lint/format gates regardless of author |
| **Media providers drift, disappear, or differ by modality** | high | Capability discovery, per-modality cursors, circuit breakers, provider-neutral artifacts, and explicit configure/upload/waive gates; never pin one video model |
| **Generated visuals look plausible but fail UX/accessibility or rights review** | high | Screen/state inventory, token contract, independent accessibility checks, moderation/provenance evidence, and user confirmation before BUILD |
| **Media generation cost or retention surprises** | medium | Estimate before opt-in, hard media budgets, local-first mode, per-provider cost/retention records, and asynchronous cancellation/cleanup |
| **Cost is unpredictable across providers** | medium | Hard caps per cycle and per project; `cost_factor` in rotation weights is designed to bias toward cheaper engines at equal capability (defined in `domain/rotation.py`; `EngineSelector` passes 1.0 today) |
| **Postgres is a dependency a "local tool" shouldn't need** | low | `VIBEY_PG_URL` is the single explicit dependency (the planned `vibey up` was not built); the Helm chart ships an in-cluster Postgres; the alternative (SQLite) is disqualified on `SKIP LOCKED` grounds |
| **Effort saturation makes "MAX" meaningless on some engines** | low | `fidelity_penalty` lowers weight rather than hiding the fact; `vibey status` reports the effort actually achieved, not the one requested |

### Explicitly out of scope for v1

- ~~Multi-machine / distributed workers~~ — shipped after this was written: a
  Helm chart, KEDA autoscaling on claimable work, and a `VibeyProject` operator
  (ADR-0025, `docs/guides/kubernetes.md`). Engines are not bundled in the image.
- ~~Non-Azure deployment targets~~ — partly reversed: the `[deploy] target` default is now
  `openstack` (the sovereign cloud, sub-doctrine 8.b), and an AWS `CloudClientPort` adapter
  exists as a declared-only stub (`infrastructure/aws/`). The Azure adapter is still the only
  one that mutates a cloud.
- ~~A web UI~~ — shipped: the hub (`vibey serve`, ADR-0068) serves the krypton clients for
  web, mobile, desktop and VS Code, and `vibey status --json` shares its shape with the hub's
  status route.
- Fine-tuning, model hosting, or any direct provider API use outside the engines. (The local
  engines reach a model the operator runs in Ollama; vibey does not host it.)

---

## 20. Decision record index

| ADR | Decision |
|---|---|
| [0001](../architecture/decisions/0001-orchestrate-do-not-reimplement.md) | Orchestrate the `*loop` runners; do not reimplement them |
| [0002](../architecture/decisions/0002-postgres-not-sqlite.md) | PostgreSQL, not SQLite, for the queue |
| [0003](../architecture/decisions/0003-event-sourced-ledger.md) | An event-sourced ledger is the conversation's source of truth |
| [0004](../architecture/decisions/0004-no-loss-gate-on-handoff.md) | Handoffs are gated by a deterministic no-loss predicate |
| [0005](../architecture/decisions/0005-smooth-weighted-round-robin.md) | Smooth weighted round robin, not modulo rotation |
| [0006](../architecture/decisions/0006-normalized-effort-ladder.md) | A normalized effort ladder with saturating per-engine projection |
| [0007](../architecture/decisions/0007-rotate-at-boundaries.md) | Rotate at boundaries, never mid-turn |
| [0008](../architecture/decisions/0008-worktree-isolation.md) | Git worktree per work item; containers for real isolation |
| [0009](../architecture/decisions/0009-human-gates-are-parked-jobs.md) | Human gates park jobs; they never block workers |
| [0010](../architecture/decisions/0010-review-loopback-routing.md) | Review loops back to design by default, to build on the fast path |
| [0011](../architecture/decisions/0011-agent-surface-provisioning.md) | One source of truth materialized into every engine's guidance files |
| [0012](../architecture/decisions/0012-deploy-is-a-separate-cli.md) | Superseded: deployment as a separate CLI |
| [0013](../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md) | Deployment execution and safety contract (entry rule superseded) |
| [0014](../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md) | Optional visual-design interstitial and explicit deployment opt-in |
| [0015](../architecture/decisions/0015-qwenloop-standby.md) | qwenloop is an opt-in local engine: a standby tier for BUILD, the sovereign provider for DESIGN (amended by 0038, superseded in part by 0037 and 0078; the gpt-oss engine is `gptossloop` since 0064) |
| [0016](../architecture/decisions/0016-classes-behind-interfaces.md) | Code lives in classes, and every class has an interface beside it |
| [0017](../architecture/decisions/0017-dogfood-the-family-first.md) | If the family already does it, the family does it here |
| [0018](../architecture/decisions/0018-everything-as-code.md) | If it can be declared in the repository, it is declared in the repository |
| [0019](../architecture/decisions/0019-installable-wherever-its-users-are.md) | Vibey is installable wherever its users already are |
| [0020](../architecture/decisions/0020-governing-rules-are-ratified-subdoctrines.md) | A governing rule belongs in the canon, ratified, or it is not a rule |
| [0021](../architecture/decisions/0021-one-tree-history-preserved.md) | One tree, history preserved: the family is absorbed as subtrees in a uv workspace |
| [0022](../architecture/decisions/0022-absorbed-packages-keep-their-own-gates.md) | An absorbed package keeps every gate it was already held to |
| [0023](../architecture/decisions/0023-four-layers-four-floors.md) | Four layers, four floors: 100% branch coverage per layer, each its own gate |
| [0024](../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md) | Every bounded ladder ends in a park that can grant more |
| [0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md) | Kubernetes: a chart, KEDA on claimable work, and an operator that never grows its own logic |
| [0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md) | tini is PID 1, and the SIGTERM latch is armed before the first import |
| [0027](../architecture/decisions/0027-sovereign-design-provider.md) | A sovereign DESIGN provider: phase one runs without paid credit |
| [0028](../architecture/decisions/0028-vibey-gh-owns-release-and-provenance.md) | vibey-gh owns provenance and release; release-please is retired |
| [0029](../architecture/decisions/0029-integrate-serialized-by-advisory-lock.md) | Integrates are serialized by a Postgres advisory lock, and contention is a Defer |
| [0030](../architecture/decisions/0030-two-mode-live-harness.md) | The live harness has two modes: faked by default, paid by explicit choice |
| [0031](../architecture/decisions/0031-skills-context-packets-over-a-process-boundary.md) | Skills context is a packet compiled over a process boundary, shadow before inject |
| [0032](../architecture/decisions/0032-the-docs-ship-as-a-paper-and-a-book.md) | The documentation ships as a research paper and a book, findable everywhere and built to outlive the site |
| [0033](../architecture/decisions/0033-governance-in-plain-sight.md) | Governance in plain sight: the law is as easy to find and as visible as possible, on every human-readable surface |
| [0034](../architecture/decisions/0034-one-marketplace-at-the-root.md) | One Claude Code marketplace at the repository root, rendered from the workspace members |
| [0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md) | Verify independence is the default, not an absolute |
| [0036](../architecture/decisions/0036-the-merge-queue-is-declared-not-clicked.md) | The merge queue is declared, not clicked |
| [0037](../architecture/decisions/0037-one-distribution-one-version.md) | One distribution, one version: the whole family ships inside `vibey` (the distribution is `vibey-engine` since 0069) |
| [0038](../architecture/decisions/0038-local-engines-are-preferred-first.md) | Local engines are preferred first (8.a): claudeloop-local, tiered selection, and sovereign DESIGN/DECOMPOSE by default when enabled |
| [0039](../architecture/decisions/0039-convergence-driven-development.md) | Convergence-Driven Development (CDD) encloses specification and test-driven development |
| [0040](../architecture/decisions/0040-evidence-bounded-status.md) | Evidence-bounded status for runs, features and research claims |
| [0041](../architecture/decisions/0041-software-organisms-alive-in-the-digital-realm.md) | Biodigitology and software organisms alive in the digital realm |
| [0042](../architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md) | Sovereign self-hosted defaults, paid declared-only relays |
| [0043](../architecture/decisions/0043-sovereign-surfaces-install.md) | Sovereign operational surfaces deploy into the Kubernetes cluster with reconciled health |
| [0044](../architecture/decisions/0044-job-queue-port-and-loop-services.md) | The job queue is a port: RabbitMQ dispatches by default, PostgreSQL stays selectable and stays the record, and every loop engine runs as a long-lived service |
| [0045](../architecture/decisions/0045-fitted-to-the-iron.md) | Every deployment measures the machine it runs on and fits itself to it, and never trades correctness for the fit |
| [0046](../architecture/decisions/0046-unattended-authority-is-bounded-by-a-gate.md) | Standing authority to act unattended is bounded by a gate a human defined, never by the agent's own judgement |
| [0047](../architecture/decisions/0047-the-toil-is-automated.md) | Anything that can be fully automated to make a developer's life better is, and the judgement never is |
| [0048](../architecture/decisions/0048-the-unbroken-read.md) | A job that consumes an accumulating record reads every datum in the gap, and proves its span |
| [0049](../architecture/decisions/0049-the-delegated-approver.md) | A named agent may give the approval an unattended change needs, and is never the author of what it approves |
| [0050](../architecture/decisions/0050-the-machinery-does-not-waste-a-persons-time.md) | The test harness and every automation are kept fast continuously, and speed is never bought with what a check measures |
| [0051](../architecture/decisions/0051-nothing-is-compiled-in-that-could-be-declared.md) | Configuration is declared in TOML, never written into a source file, and a derived value beats both |
| [0052](../architecture/decisions/0052-the-tracker-tells-the-truth.md) | A tracker is kept true by the machinery that changes what it describes, and failure is recorded as failure |
| [0053](../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md) | An unattended run takes direction only from the operator's account, and outside text is contained at the seam it enters |
| [0054](../architecture/decisions/0054-a-bumped-job-runs-next.md) | A bumped job runs next: after what is running, ahead of all un-bumped work, first in first out, and only the operator or a declared source may bump |
| [0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md) | The ledger is append-only by the database, not by convention: triggers refuse every rewrite, and the application connects as a role that could not rewrite it anyway |
| [0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md) | Everything a queue guards is reaped by measurement: five conditions, each a declared threshold, both backends judged alike, and no dead letter ever deleted |
| [0057](../architecture/decisions/0057-the-work-outlives-the-machine.md) | Storm work lives on durable storage, is committed and pushed often, and a tool refuses volatile paths |
| [0058](../architecture/decisions/0058-concurrent-local-runs-are-measured-per-device.md) | Concurrent runs of a local model are measured on each device, and unmeasured or stale means one |
| [0059](../architecture/decisions/0059-the-editor-drives-the-familys-own-loops.md) | The editor drives the family's own loops, on a copy, and adds no loop of its own |
| [0060](../architecture/decisions/0060-the-heartbeat-tells-the-truth-and-passes-the-gate-by-its-rule.md) | The heartbeat tells the truth, and passes the gate by the gate's own rule |
| [0061](../architecture/decisions/0061-every-postgresql-connection-authenticates-with-scram-sha-256.md) | Every PostgreSQL connection authenticates with scram-sha-256 |
| [0062](../architecture/decisions/0062-the-beauty-law-and-its-bar.md) | The Beauty Law and its bar |
| [0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md) | ULTRA: effort without a ceiling |
| [0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md) | `gptossloop` is the sovereign engine, and `qwenloop` is its opt-in Qwen twin |
| [0065](../architecture/decisions/0065-vibey-and-krypton.md) | vibey and krypton |
| [0066](../architecture/decisions/0066-one-design-system-for-every-surface.md) | One design system for every surface |
| [0067](../architecture/decisions/0067-one-typescript-core-for-every-krypton-client.md) | One TypeScript core for every krypton client |
| [0068](../architecture/decisions/0068-the-hub.md) | The hub: `vibey serve`, one HTTP surface for every krypton client |
| [0069](../architecture/decisions/0069-two-packages-vibey-engine-and-krypton-app.md) | Two packages, vibey-engine and krypton-app |
| [0070](../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md) | Failover to the sovereign engine, and handback on a recorded probe |
| [0071](../architecture/decisions/0071-hub-pairing-and-trust.md) | Hub pairing and trust: signed requests, a pinned certificate, `_vibey._tcp` |
| [0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md) | The Sabbath, kept where the machine stands |
| [0073](../architecture/decisions/0073-krypton-desktop-in-c-on-gtk.md) | krypton desktop in C, on GTK 4 and libadwaita |
| [0074](../architecture/decisions/0074-measured-service-bus-dispatch.md) | Measured dispatch for every service-bus surface |
| [0075](../architecture/decisions/0075-context-microslices-and-linked-surfaces.md) | Context-bearing surfaces are linked microslice graphs |
| [0076](../architecture/decisions/0076-discoverability-and-the-first-hour-are-deliverables.md) | Discoverability and the first hour are deliverables |
| [0077](../architecture/decisions/0077-outcome-guides-answer-the-questions-users-search-for.md) | Outcome guides: the project answers the questions its users search for |
| [0078](../architecture/decisions/0078-retire-cursorloop-and-agyloop.md) | Retire cursorloop and agyloop |
| [0079](../architecture/decisions/0079-hybrid-engine-dispatch.md) | Hybrid engine dispatch: paid engines in tandem with sovereign ones, measured and capped |
| [0080](../architecture/decisions/0080-continuation-prompts.md) | Continuation prompts, kept current and run on GitHub every week |
| [0081](../architecture/decisions/0081-vibey-chat-on-github.md) | vibey's chat, inside GitHub, resilient to the parts around it failing |
| [0082](../architecture/decisions/0082-install-copy-reinstall-and-a-core-that-stays.md) | Install, copy and reinstall in one command; the krypton interfaces uninstall cleanly; the core stays |
| [0083](../architecture/decisions/0083-daily-self-healer-and-backlog-killer.md) | A daily self-healer, backlog killer and documentation updater, scripted first, on GitHub's CPU runners only |
| [0084](../architecture/decisions/0084-krypton-nightly.md) | A rolling nightly of every krypton interface, from the release builders |
| [0085](../architecture/decisions/0085-vibey-on-the-workflows.md) | `vibey -w`: any vibey command, run on the repository's GitHub-hosted runners |
| [0086](../architecture/decisions/0086-state-sync.md) | `vibey state`: the whole database, sealed on a branch, kept in sync both ways |
| [0087](../architecture/decisions/0087-the-six-audiences-in-order.md) | The six audiences, in order: FOSS developers, freelancers, universities, governments, non-profits, industry |
| [0088](../architecture/decisions/0088-typescript-never-javascript.md) | TypeScript, never JavaScript: the only authored form is typed, and the JavaScript that must exist is generated |
| [0089](../architecture/decisions/0089-ai-self-reference-is-i-inclusive-we-is-direct.md) | AI self-reference is I; inclusive we is only direct address |
| [0090](../architecture/decisions/0090-pr-af-as-the-declared-default-reviewer.md) | pr-af is the declared default exact-head reviewer |
| [0091](../architecture/decisions/0091-devices-may-start-pause-and-unwind-projects.md) | A paired device may start, pause, resume and unwind a project |
| [0092](../architecture/decisions/0092-large-tasks-are-sliced-into-the-cdd-layers-before-they-run.md) | Large tasks are sliced into the CDD layers before any of them runs, and every lane is given everything its runner can take |
| [0093](../architecture/decisions/0093-local-model-families-are-named-and-measured-not-assumed.md) | Local model families are named and measured, never assumed |
| [0094](../architecture/decisions/0094-the-cost-of-routing-the-cache-through-its-lane-is-accepted.md) | The cost of routing the cache through its lane is accepted |
| [0095](../architecture/decisions/0095-opentofu-is-the-infrastructure-as-code-tool-for-aws.md) | OpenTofu is the infrastructure-as-code tool for AWS deployments |
| [0096](../architecture/decisions/0096-on-forgejo-branch-rules-are-mapped-where-they-can-be-and-waived-loudly-where-they-cannot.md) | On Forgejo, branch rules are mapped where Forgejo can express them and waived loudly where it cannot |
| [0097](../architecture/decisions/0097-this-project-runs-its-own-sovereign-forgejo-host.md) | This project runs its own sovereign Forgejo host, on the operator's home server |
| [0098](../architecture/decisions/0098-the-vs-code-verification-is-done-by-a-large-model-and-reviewed-by-the-operator.md) | The VS Code verification is done by a large model and reviewed by the operator |
| [0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md) | Heretic v2 of GPT-OSS 20B is the sovereign default model |
| [0100](../architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md) | Host-driven MCP interface and chat-first krypton surfaces |
| [0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md) | The ACP agent, and the user-level services it installs and keeps running |
| [0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md) | Local-first search, and the SearXNG vibey installs and runs itself |
| [0103](../architecture/decisions/0103-the-loop-capability-bundle.md) | The loop capability bundle: declared by the person, locked by content, fetched only on their word |
| [0104](../architecture/decisions/0104-run-inputs-hash-addressed.md) | Run inputs: hash-addressed in the person's state, given to every BUILD run the same way |
| [0105](../architecture/decisions/0105-run-input-store-backends.md) | Where run inputs are stored: your state folder by default, or a SeaweedFS bucket you name |

The index lists all 105 decision records as of 2026-11-24 (0001–0105). The directory
`docs/architecture/decisions/` is the source; a record's own status line says whether a
later record amended or superseded it.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `ConfigError: engines.enabled: unknown engine 'cursorloop' -- cursorloop was retired by ADR-0078 ...` | Your `vibey.toml` names a retired engine, often copied from an old version of this page | Remove `cursorloop` and `agyloop` from `[engines] enabled` and `[engines.weights]`; the paid engines are `claudeloop` and `codexloop` |
| The worker logs `ignoring ./vibey.toml, which could not be used (...)` | The file failed to parse, so the operational surfaces fell back to their in-memory defaults | Fix the key the message names, then restart the worker |
| `AttributeError: type object 'EngineId' has no attribute 'CURSORLOOP'` (or `'AGYLOOP'`) in code you wrote | `EngineId` has no such member since ADR-0078 | Use one of the five members listed in [domain-model.md](domain-model.md) §4 |
| A project stays in DESIGN although you accepted the spec | A DESIGN job of this cycle is still unsettled, so the guard refuses (§6.4) | `vibey status <project-id>` and `vibey queue` show the job; let it finish, or `vibey retry` the project |

## Where next

- [domain-model.md](domain-model.md), to see every type this page names, member by member.
- [rotation-and-engines.md](rotation-and-engines.md), for exactly how an engine is chosen and
  what each one is told.
- [`docs/reference/cli.md`](../reference/cli.md), for every command and flag as the code
  defines them today.

## Say it in one line

vibey is a conductor: workers lease jobs from one PostgreSQL queue, write every fact to a ledger
the database will not let anyone rewrite, and run each job on a local engine first.
