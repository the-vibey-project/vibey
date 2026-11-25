---
description: Drive one small project, a command-line greeter, through DESIGN, BUILD, REVIEW and a local finish on real engines, and force one engine to hand its work to another without losing anything.
---

# Run the greeter demo: a real project, real engines, one forced rotation

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This runbook takes a tiny "CLI greeter" from an idea to
> DONE(local) on two paid engines, `claudeloop` and `codexloop`, and makes one of them hand its
> work to the other mid-task. It costs real money, capped by `--max-cycle-dollars`. You need
> PostgreSQL and both engines logged in. This exact engine pair has not yet been run live end to
> end or timed; the last live run used claudeloop with the since-retired agyloop (ADR-0078).

## The lesson

The kettle had boiled twice before Daniel got to the question he had come with.

**Daniel:** Professor, the whole design is supposed to rest on two behaviours: rotation and the
no-loss handoff. What do they look like in practice?

**Professor Feynman:** Picture a relay race. Each leg of the race is one job: implement this
item, verify that one. Before each leg, vibey picks a runner from the pool, a little like a coach
taking turns fairly, so no runner runs every leg. That is rotation.

**Daniel:** And the handoff?

**Professor Feynman:** Sometimes a runner tires in the middle of a leg: an engine's session ends
before the work is done. In a relay you pass the baton. Here the baton is a written brief: every
open question, decision and finding, word for word. vibey checks the brief against the ledger
before it lets the next runner take it. If anything is missing, it tries again with the full
transcript, and only if that fails does it stop and ask you.

**Daniel:** So the second engine starts where the first one stopped, with nothing forgotten.

**Professor Feynman:** That is the claim, and this demo is how you test it. You will make
claudeloop tire on purpose with `claudeloop wind-down`, and watch codexloop pick up the brief.
The picture stops working in one place: a relay baton is the same object in every hand. This
brief is rebuilt from the ledger each time, which is why it can be checked.

## Do it

The commands were checked against the code (`vibey <command> --help` and the sources named in
[The details](#the-details)), not run live for this page, so each "You should see" describes
what the code prints. Use an installed
`vibey` ([install guide](install.md)); from a source checkout, prefix each `vibey` with
`uv run --project <your vibey checkout>`.

1. Create the project, with a dollar cap per cycle.

   ```bash
   mkdir -p ~/demos/greeter && cd ~/demos/greeter && git init
   vibey new greeter --repo . --max-cycles 3 --max-cycle-dollars 15
   ```

   You should see the new project's id. Keep it; `vibey projects` lists it again at any time.
   Nothing runs yet: jobs run only inside a worker.

2. Record engine health, so the two engines are eligible.

   ```bash
   vibey doctor --conformance --record
   ```

   You should see the 9-check conformance suite run against every installed engine, recorded for
   the latest project.

3. Start the worker in its own terminal.

   ```bash
   vibey worker --provider claudeloop --engines claudeloop,codexloop
   ```

   You should see the worker start, name its engines and provider, and say which web search it
   will use.

4. In a second terminal, answer the DESIGN interview.

   ```bash
   vibey gates
   vibey answer GATE_ID system_description="a CLI that greets the user by name" --defaults
   ```

   `GATE_ID` is the id `vibey gates` printed. You should see the gate answered; repeat with
   `vibey answer GATE_ID --defaults` for each later stage until no gate is open.

5. Accept the design once research, synthesis and the spec have run.

   ```bash
   vibey design accept PROJECT_ID --no-visual
   ```

   `PROJECT_ID` is the id from step 1. BUILD starts.

6. While a `build.implement` session runs on claudeloop, force a rotation.

   ```bash
   claudeloop wind-down --cwd ~/demos/greeter/.vibey/worktrees/PROJECT8/CYCLE/ITEM_ID --reason demo
   ```

   `PROJECT8` is the first eight hex digits of the project id; `CYCLE` and `ITEM_ID` are the
   folders you find under that path. You should see the session exit 75 and a follow-up
   `build.implement` start on codexloop.

7. Finish: accept the review and decline deployment.

   ```bash
   vibey answer GATE_ID --verdict accept
   vibey answer GATE_ID --choice local_only
   ```

   You should see the project reach DONE(local), and `vibey status` show an empty queue with no
   failed jobs.

## Daniel's teach-back

**Daniel:** I make a project with a dollar cap, record which engines are healthy, and start a
worker that may use only claudeloop and codexloop. I answer the DESIGN questions and accept the
spec. In BUILD, vibey picks an engine per job and never lets an item's implementer verify its
own work. When I wind claudeloop down, vibey writes the ledger to disk, builds a brief, checks
it, and hands it to codexloop. Then I accept the review and finish locally.

**Professor Feynman:** Right. One correction: the per-cycle cap is the brake on BUILD spend. The
worker's own `--max-dollars` limits only the claudeloop process that runs the DESIGN interview
and the decomposition.

## The details

### Cost and caps

The demo runs live claudeloop and codexloop sessions, which bill your accounts. The BUILD-phase
brake is the per-cycle cap you set at `vibey new` (`--max-cycle-dollars`, enforced from the
ledger's recorded `cost_usd`); without it BUILD spend is uncapped. The worker's `--max-turns`
(default 25) and `--max-dollars` (default 2.0) cap only the claudeloop process that runs the
DESIGN interview and the BUILD decomposition, not the BUILD engine sessions. No cost has been
recorded for this engine pair, so treat your cap as the bound.

### Prerequisites

- PostgreSQL 14 or newer running, and `VIBEY_PG_URL` pointing at a database you own (never
  SQLite; [ADR-0002](../architecture/decisions/0002-postgres-not-sqlite.md)).
- `claudeloop` and `codexloop` installed (both ship in `vibey-engine`) and authenticated.
  `vibey doctor` says which are ready.
- A clean folder for the project's repository.
- **Not on the Sabbath.** From sundown Friday to sundown Saturday `vibey new` exits 75 and the
  worker claims nothing, so a demo started then looks hung
  ([ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md)).
  `--ignore-sabbath` runs one command through the window and says so; `[sabbath] enabled` and
  `VIBEY_SABBATH_ENABLED` are the declared switches ([`[sabbath]`](../reference/configuration.md#sabbath)).

### Engine health (step 2)

Selection is driven by the `engine_health` table. An engine with no recorded conformance is
**ineligible**: the worker warns and never selects it. `vibey doctor --conformance --record`
runs the 9-check conformance suite against every installed engine and persists preflight and
conformance for the latest project, so it needs `vibey new` to have run first; without a project
it exits with "no projects found" (use `--project` to target another project). Re-run it
whenever an engine is updated.

### The worker's flags (step 3)

- `--provider claudeloop` makes the DESIGN interview and the BUILD decomposition use live
  claudeloop calls (`scripted` is for tests). This demo uses it because it exercises the paid
  pool.
- `--provider gptossloop`, the default when no `--provider` is given, is the sovereign
  alternative (ADR-0027, ADR-0064). It runs the interview and the decomposition on a local model
  (`GptossloopDesignProvider` and `GptossloopWorkPlanProducer`, sharing one Ollama client). The
  server is `VIBEY_OLLAMA_URL` (default `http://127.0.0.1:11434`). The model is
  `--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else the variant `VIBEY_SOVEREIGN_MODEL` names,
  else `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`
  ([ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)).
  `--provider qwenloop` is still accepted and read as gptossloop.
- `--engines claudeloop,codexloop` is the allow-list: BUILD jobs select between exactly these
  two by smooth-weighted round-robin, per job.
- `gptossloop`, the sovereign local engine, is on by default but is not in this allow-list, so it
  runs no BUILD job here; drop `--engines` to let it run first (ADR-0038, ADR-0064). To add
  `qwenloop`, the same runner on a Qwen model, export `VIBEY_FEATURE_QWENLOOP=1` before both
  `vibey doctor` and `vibey worker`, and name it in `--engines`. `[features] qwenloop = true` in
  `vibey.toml` is honoured by `vibey doctor` but not by the worker, which reads the project's
  stored config.
- **Fewer questions.** `--auto-answer` answers the interview with each question's own default,
  and `--auto-accept-design` accepts the spec once DESIGN finishes; both are for one worker and
  one project and are recorded on the ledger. See
  [Running unattended](local-models-ollama.md#running-unattended).
- **Gate commands do not see vibey's Python.** Gate commands (verify, integrate, REVIEW's checks)
  have vibey's venv stripped: its `bin`, `VIRTUAL_ENV`, `PYTHONPATH` and `PYTHONHOME`, so a
  gate's `python` is whichever one the rest of `PATH` provides. A project whose gates need tools
  installed beside vibey sets `isolate_python_env = false` under `[gates]` in its `vibey.toml`
  before `vibey new` ([`[gates]`](../reference/configuration.md#gates)).

The worker LISTENs on `vibey_job_ready`, so answers you give in another terminal wake it at once.

### Research, and where it finds its sources

DESIGN runs `design.research` (three topics) before synthesis. With `--provider claudeloop` the
paid provider researches. With the sovereign provider:

1. **Your own reading wins.** If `VIBEY_EVIDENCE_DIR` holds `<topic>.md` for the topic
   (`prior-art.md`, `libraries.md`, `api-docs.md`), with `source: <where it came from>` on its
   first line, the model summarises that file.
2. **Otherwise vibey searches the web** through a local SearXNG (`VIBEY_SEARXNG_URL`, else
   `http://127.0.0.1:28180`), with Brave as a backup only when SearXNG fails and a key is set
   (`VIBEY_BRAVE_API_KEY` or `BRAVE_SEARCH_API_KEY`). It quotes what it finds with its URLs
   ([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)).
   `vibey searxng install` sets up the local SearXNG.
3. **When both give nothing,** the research job parks a `research_evidence` gate naming the file
   to add, rather than inventing a source; add the file and answer the gate to retry. Set
   `[design.research] on_unavailable = "record_gap"` (or run the worker with
   `--auto-record-research-gaps`) to record the topic as not researched and go on instead
   ([`[design.research]`](../reference/configuration.md#designresearch)).

Synthesis waits on every research job.

### The DESIGN gates (step 4)

`vibey status` shows only queue depth per job state (`AWAITING_HUMAN: 1` means a gate is
parked), never a gate id or its questions. `vibey gates` lists every open gate, oldest first,
with its id, its prompt, and `answer with:`, the exact `vibey answer` command for it
([`vibey gates`](../reference/cli.md#vibey-gates-project_id)).

Question keys are minted by the model and vary per run; read them from the gate prompt when you
want to answer one explicitly. `--defaults` accepts every default (blocking questions included)
and combines with explicit pairs, which win; it is the zero-touch path.

When `vibey status` shows no `AWAITING_HUMAN` jobs and research, synthesis and spec have
succeeded, accept the design. Acceptance is an explicit command, not a gate.
`--no-visual` (the default) declines the VISUAL_DESIGN interstitial and enters BUILD directly;
the greeter has no UI. `vibey watch` gives a live dashboard of the queue, circuits and ledger
tail.

### Watching BUILD rotate (after step 5)

BUILD decomposes the spec into work items and runs `build.implement` and `build.verify` jobs on
engine-selected sessions:

- every job's selected engine is durable (`job.assigned_engine`);
- each item's **verifier is never its implementer**;
- `vibey engines` prints a snapshot of selection counts and circuit states; `vibey watch` keeps
  them live.

### The forced rotation (step 6, the E1 milestone)

Each project's worktrees live under their own root, `.vibey/worktrees/<first 8 hex digits of the
project id>/`. claudeloop honours the wind-down at its next natural break, after the turn in
flight finishes, so a short greeter session may complete before the request lands: trigger it
early in a session, or wait for a real window exhaustion. The engine exits with code 75; vibey
then:

1. writes this cycle's full BUILD ledger to `<worktree>/.vibey/handoff/ledger.jsonl`;
2. produces a handoff brief and verifies it against the no-loss gate (STRICT, escalating to
   FULL_TRANSCRIPT, parking for you only if even that fails);
3. persists the verified `HandoffEnvelope` (query the `handoff` table: `accepted` must be true);
4. enqueues a follow-up `build.implement` whose prompt is the rendered brief (every open
   question, decision, assumption and finding id, verbatim) with claudeloop durably excluded,
   so codexloop picks it up.

The wind-down job settles **Success**: rotation is not a failure and never burns the escalation
ladder. An item may rotate three times; a fourth wind-down on the same item parks it for you as a
`too_many_wind_downs` gate.

### REVIEW and completion (step 7)

REVIEW produces the demo artifacts under `.vibey/runs/<cycle>/review/`, runs the automated
review (`ruff check .`, `bandit -q -r src`) against the integrated result, then parks two gates
in turn: the review approval (`--verdict accept`) and the deployment choice
(`--choice local_only`). The project records DONE(local).

`vibey cost PROJECT_ID` then prints the cycle's spend and caps, as the budget brake reads them:

```text
Project: greeter (Cycle 1)
Cycle spend:      $<spent> (<turns> turns)
Cycle dollar cap: $15.00
Cycle turn cap:   none
```

followed by `Per-engine (BUILD sessions, all cycles):` with one line per engine,
`<engine>: $<spent> (<n> selections)`. The count is how often rotation selected the engine, not a
turn count ([`vibey cost`](../reference/cli.md#vibey-cost-project_id)). The lines are the format `src/vibey/cli/cost.py`
prints; the figures depend on your run.

## When it goes wrong

- **"no projects found" from `vibey doctor --record`.** The project does not exist yet; run
  step 1 first.
- **`vibey new` says `resting for the Sabbath` and exits 75.** See Prerequisites; nothing was
  changed.
- **"no recorded conformance" warning at worker startup.** Step 2 was skipped or failed;
  engine-driven jobs will sit ready but unselected. A timing-flaky conformance FAIL is possible on
  a loaded machine: re-run `vibey doctor --conformance --record --engine <name>` once.
- **A `research_evidence` gate.** No evidence file and no search result for a topic. Add the file
  it names to `VIBEY_EVIDENCE_DIR`, install SearXNG (`vibey searxng install`), or record a gap
  (`--auto-record-research-gaps`), then answer the gate.
- **A job keeps deferring.** Three causes, none of which `vibey status` names: an open circuit
  (`vibey engines`), a capacity backoff, or a verify/integrate repair round in flight (a
  `build.implement` repair job for the same item is queued or running; the verify job re-checks
  every 10 minutes). The worker logs one `job.deferred` line per deferral, naming the kind, the
  work item, the reason and the `retry_at` it will come back at: a capacity deferral at WARNING,
  a routine repair wait at INFO. For a job that deferred before you were watching, the reason is
  on the job row:
  `psql "$VIBEY_PG_URL" -c "SELECT kind, work_item_id, run_after, last_error->>'detail' FROM job WHERE state='ready' AND run_after > now();"`.
  Watch `vibey ledger show --kind FindingRaised` and `--kind FindingResolved` for the repair
  round to close. Circuits and backoffs clear on their own; an open circuit past its reset
  deadline half-opens at the next selection and closes on the first success.
- **A `job.heartbeat_failed` warning.** A lease heartbeat could not reach PostgreSQL (a pool
  timeout, a failover). The worker keeps running and retries at the next beat; one line is a
  blip, a run of them means the database is unreachable and the lease will lapse.
- **A `job.lease_lost` or `job.<ack|nack|grant|park|defer>_rejected` warning.** This worker's
  lease on the job expired (the handler outlived it, or heartbeats kept failing) and the row was
  reaped or claimed by another worker. The worker stays up, but the outcome it just produced was
  not recorded; the job runs again under whoever holds it now.
- **A `verify_repair_exhausted` or `integrate_repair_exhausted` gate.** The item burned its
  bounded repair rounds. Grant more with `vibey answer GATE_ID --raw '{"max_rounds": 6}'` (the
  prompt suggests a value), or fix the branch by hand and answer anything to retry. Bounded
  ladders park with grants rather than failing
  ([ADR-0024](../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md)).
- **A `budget_exhausted` gate.** The cycle's ledger-recorded spend crossed `--max-cycle-dollars`
  (or `--max-cycle-turns`), or the next attempt's projected cost would. No further engine session
  starts until you raise the cap: `vibey answer GATE_ID --raw '{"max_dollars": 25}'` (add
  `"max_turns": N` to raise the turn cap too), or leave it parked to stop here.
- **An `escalation_exhausted` gate.** The item burned the six-rung effort ladder (the seventh
  attempt parks). Grant more with `vibey answer GATE_ID --raw '{"max_attempts": 10}'` (they run at
  the ladder's top effort), or fix the item by hand and answer anything to let the next verify
  pass.
- **A verify gate fails with `gate command could not start` (exit 127).** The engine wrote a gate
  command (often `python`) whose binary is not on the worker's `PATH` once vibey's venv is
  stripped from it. That is a failing gate the repair loop fixes, not a vibey failure; put the
  binary on the worker's `PATH` outside vibey's venv, or opt the project out with
  `gates.isolate_python_env`. If `vibey doctor` starts failing after a run anyway, `uv sync`
  restores a source checkout's environment.
- **A verify gate fails with exit 124, `gate command timed out`.** The command ran past
  `gates.timeout_seconds` (30 minutes by default) and was killed with everything it started.
  Raise the timeout in the project's config record if the suite is simply slow.
- **A gate you do not recognise.** `vibey answer GATE_ID --raw '{"...": ...}'` covers any shape
  the typed flags do not.
- **Anything else.** Workers are disposable: kill the worker any time; leases expire and the next
  worker replays idempotently.

## Where next

- [Local models on Ollama](local-models-ollama.md): run the same demo on the sovereign path, at
  no cost per token.
- [Drive a project](drive-a-project.md): answer the same gates from krypton or a chat client
  instead of the terminal.
- [How vibey survives a crashed agent](../case-studies/how-vibey-survives-a-crashed-agent.md):
  the handoff, told as a case study.

## Say it in one line

The greeter demo runs a tiny project on two paid engines and forces one to hand off mid-task, so you can watch vibey rotate engines and lose nothing.
