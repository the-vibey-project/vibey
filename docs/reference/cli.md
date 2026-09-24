# CLI reference

Every `vibey` command and subcommand, written by hand against
[`src/vibey/cli/main.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/cli/main.py)
and checked against it as of 2026-09-20. Nothing generates this page. If it
and the code disagree, the code wins. `vibey <command> --help` prints the
code's own help text, which is shorter than this page and in places less
complete (for example, `vibey work --help` does not list `qwenloop`).

Top-level commands, in `vibey --help` order: `new`, `projects`, `gates`,
`answer`, `work`, `watch`, `recover`, `status`, `engines`, `cost`, `install`,
`doctor`, `migrate`, `operator`, `worker`, and the command groups `design`,
`visual`, `deploy`, `ledger`, `queue`.
Bare `vibey`, and each bare command group, prints help.

Commands that read or write project state need `VIBEY_PG_URL` (see
[Environment variables](#environment-variables)). `doctor` needs it only
with `--record` or `--cluster`.

## Global options

These apply to every command; they must come before the subcommand name.

| Option | Default | What it does |
|---|---|---|
| `--version` | — | Print `vibey <version>` and exit. |
| `--verbose` / `-v` (repeatable) | `0` | `-v` debug, `-vv` also third-party libraries, `-vvv` full payloads. |
| `--quiet` / `-q` | off | Warnings and errors only. |
| `--log-level LEVEL` | unset | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` (case-insensitive). Overrides the level `-v` or `-q` would pick. |
| `--log-file PATH` | unset | Also write redacted JSON lines to this file. |
| `--install-completion` | — | Install shell completion for the current shell. |
| `--show-completion` | — | Print the completion script for the current shell. |
| `--help` | — | Show help and exit. |

`-v` and `-q` are mutually exclusive: together they print
`Error: --quiet and --verbose are mutually exclusive` and exit 2. An unknown
`--log-level` exits 2 with `Error: invalid log level ...`. `--log-level`
fixes the level, but the `-v` count still widens scope, so
`--log-level WARNING -vvv` means warnings from third-party libraries too,
with payloads.

## Exit codes and errors

| Code | Meaning |
|---|---|
| `0` | Success. Also a guarded command whose reader closed the pipe early. |
| `1` | Nothing to act on, or a check failed: no project exists (``no projects found; create one with `vibey new` first``); an explicit `PROJECT_ID` is unknown in `watch`, `cost`, `gates` (said on stderr), or `deploy *`; `recover` without `--project` or `--all`; `doctor --engine` with an unknown name; `doctor --conformance` with a failing engine; `doctor --install-postgres` or `install --postgres` could not install/start a supported server; `doctor --cluster` with a failing check; `operator` without the `operator` extra; `worker --azure az` without a logged-in Azure CLI. |
| `2` | Usage error: a bad global flag (see above); typer's own validation (missing argument, malformed UUID, a value outside an option's minimum or maximum, unknown option); `install` without `--postgres`; `doctor --install-postgres` with `--cluster`; `new --skills-context-mode` outside `off`/`shadow`/`inject`; `answer` mode conflicts or a `--raw` value that is not a JSON object; `worker` with an unknown `--engines` id, an `--engines` list matching none of the worker's engines, an unknown `--provider`, or an unknown `--azure` value; `doctor --cluster` with an unknown `--engines` id or `--provider`; `doctor --engines` or `--provider` without `--cluster`; `doctor --record` whose target project declares a forbidden `engine_environment` entry; `new` whose `vibey.toml` declares a malformed or forbidden `[gates]` or `[engine_environment]` entry. |
| `3` | Blocked by a domain rule, in a guarded command. Prints `Error: <message>` on stderr, plus a next-step hint for some error types. |
| `130` | Interrupted with Ctrl-C, in a guarded command (prints `Interrupted.`). |

### Guarded and unguarded commands

Thirteen commands run inside `vibey.cli.errors.guard()`: `new`, `projects`,
`gates`, `design resume`, `design accept`, `work`, `visual accept`,
`visual waive`, `queue bump`, `queue unbump`, `queue list`, `queue reap`, and
`worker`. For these, any `VibeyError` — an unknown project or provider,
a wrong phase, an invalid spec, no eligible engine, a rejected handoff, an
unset `VIBEY_PG_URL` — becomes the one-line `Error:` message and exit 3.
Ctrl-C exits 130 and a closed pipe exits 0. Exceptions that are not
`VibeyError` keep their Python traceback.

The other commands (`answer`, `watch`, `recover`, `status`, `engines`,
`cost`, `ledger show`, every `deploy` subcommand, `doctor`, `operator`) are
not guarded. Their own checks exit 1 or 2 as listed above; any other error,
including an unset `VIBEY_PG_URL`, surfaces as a Python traceback.

Known gaps in unknown-project handling:

- `status <unknown-id>` raises `ValueError: unknown project ...` as a traceback.
- `engines <unknown-id>` prints `no engines recorded for project` and exits 0.
- `ledger show <unknown-id>` prints nothing and exits 0.

## `vibey install`

Install local dependencies that vibey can manage explicitly.

| Option | Default | What it does |
|---|---|---|
| `--postgres` | off | Install and start the current stable PostgreSQL major using Homebrew, apt, or dnf. |

The installer targets PostgreSQL 18 today. The application floor is
PostgreSQL 14, and the same SQL/runtime contract is tested against 14, 15, 16,
17, and 18 in CI. Installation does not invent or persist a database DSN:
set `VIBEY_PG_URL` to a database you own after the server is ready.

### Next-step hints

`guard()` appends a hint for these error types. Every command a hint names
exists, and a test asserts it (`tests/cli/test_errors_and_logging.py`).

| Error | Hint printed | Notes |
|---|---|---|
| `NoEligibleEngine` | Every engine is excluded, circuit-open, or missing a capability; run `vibey engines` or `vibey doctor`. | |
| `BudgetExceeded` | A tripped cap parks a `budget_exhausted` gate; raise it with `vibey answer GATE_ID --raw '{"max_dollars": 25}'` (or `"max_turns"`), and `vibey cost` shows where the spend went. Ends by naming [`vibey gates`](#vibey-gates-project_id), which lists the gate. | Nothing in `src/vibey` raises this error today, and no runtime code reads `[budget]` from `vibey.toml` — which is why the hint names neither. |
| `EscalationExhausted` | The work item failed at every rung of the effort ladder and parked a human gate; `vibey answer GATE_ID` it. Ends by naming [`vibey gates`](#vibey-gates-project_id). | |
| `HandoffRejected` | The no-loss gate refused the handoff and parked a human gate whose `prompt` says what could not be carried over; `vibey answer GATE_ID` it. Ends by naming [`vibey gates`](#vibey-gates-project_id). | |
| `IllegalTransitionError` | The project is not in a phase this command applies to; `vibey status` shows the phase. | |
| `InvalidSpecError` | Run `vibey design` to finish the spec before building. | |
| `InvalidPhaseError` | Likely a bug in vibey rather than the project. | |

## `vibey new NAME`

Create a project and enqueue its first DESIGN interview.

| Option | Default | What it does |
|---|---|---|
| `--repo PATH` | `.` | Repository the project builds against. |
| `--max-cycles N` | `10` | Cap on delivery cycles before the project stops (min 1). |
| `--max-cycle-dollars F` | unset | Per-cycle dollar cap (min 0.01), stored as `max_cycle_dollars` in project config. Tripping it parks a `budget_exhausted` gate instead of starting more sessions (ADR-0024). Unset means no dollar cap. |
| `--max-cycle-turns N` | unset | Per-cycle engine-turn cap (min 1), stored as `max_cycle_turns`. |
| `--skills-context-mode {off,shadow,inject}` | `off` | `vibey-skills` retrieval mode (ADR-0031) — see [Configuration reference](configuration.md#skills_context). Any other value exits 2. |
| `--skills-context-budget N` | `6000` | Token budget for skills retrieval (1,000–32,000). Stored only when the mode is not `off`. |

Prints `project <id>` and `design job <id>`. The project id is the
`PROJECT_ID` the other commands take; [`vibey projects`](#vibey-projects)
prints it again later.

## `vibey projects`

List every project, newest first (by creation time, then id), with its phase,
its cycle, and how many gates are waiting for your answer.

| Option | Default | What it does |
|---|---|---|
| `--json` | off | Print a JSON array instead of the table. |

The table has one row per project — `NAME`, `PHASE`, `CYCLE`
(`cycle/max_cycles`), `OPEN GATES`, `CREATED (UTC)`, `PROJECT ID` — then a
line counting them that, when any gate is open, points at `vibey gates`.
`PHASE` is the phase's name, such as `BUILD`. A phase a newer vibey wrote,
which this one has no name for (vibey#287), is shown as its stored text; it
never fails the listing.

`--json` prints an array, newest first, of one object per project with exactly
these keys:

```json
[
  {
    "project_id": "0b5c9a4e-1d4c-4c47-9a2a-3c1d2b8f9e10",
    "name": "greeter",
    "phase": "BUILD",
    "cycle": 1,
    "max_cycles": 3,
    "repo_path": "/Users/me/src/greeter",
    "created_at": "2026-09-24T09:00:00.123456+00:00",
    "open_gates": 2
  }
]
```

`phase` follows the table's rule, `created_at` is ISO-8601 with its offset,
and `open_gates` counts the project's unanswered gates. With no projects both
forms exit 0: the table form prints
``no projects yet; create one with `vibey new <name> --repo <path>` `` and
`--json` prints `[]`. An empty list is an answer, not an error — unlike
`vibey status`, which needs a project to report on and exits 1 without one.

## `vibey gates [PROJECT_ID]`

List every open gate — a job parked until a person answers it (ADR-0009) —
oldest first (by raise time, then gate id), across every project or only
`PROJECT_ID`'s. Each gate shows its project's name, its kind, its prompt as
one wrapped paragraph, and the exact command that answers it:

```text
1 open gate, oldest first -- each is a job waiting for your answer:

1. greeter: approval gate, raised 2026-09-24 12:03 UTC
   Review artifacts ready for cycle 1. Accept, request changes, or ask
   questions.
   answer with: vibey answer 5e1f0c7a-8b2d-4e5f-9a61-2c3d4e5f6a7b --verdict accept
```

| Argument / option | Default | What it does |
|---|---|---|
| `PROJECT_ID` | every project | Only this project's open gates. An unknown id exits 1 with `unknown project <id>` on stderr and nothing on stdout. |
| `--json` | off | Print `{"gates": [...]}` instead. |

`--json` prints one object whose `gates` array holds, oldest first, one object
per gate with exactly these keys:

```json
{
  "gates": [
    {
      "gate_id": "5e1f0c7a-8b2d-4e5f-9a61-2c3d4e5f6a7b",
      "project_id": "0b5c9a4e-1d4c-4c47-9a2a-3c1d2b8f9e10",
      "project_name": "greeter",
      "job_id": "9d2a7b1c-3e4f-4a5b-8c6d-7e8f9a0b1c2d",
      "kind": "approval",
      "prompt": "Review artifacts ready for cycle 1. Accept, request changes, or ask questions.",
      "options": ["accept", "changes", "cancel"],
      "default_answer": null,
      "raised_at": "2026-09-24T12:03:04.567890+00:00",
      "timeout_at": null,
      "answer_with": "vibey answer 5e1f0c7a-8b2d-4e5f-9a61-2c3d4e5f6a7b --verdict accept"
    }
  ]
}
```

`job_id`, `default_answer` and `timeout_at` are `null` when the gate has none;
`prompt` is the gate's own text, line breaks included. With nothing waiting,
both forms exit 0: the text form prints
`no open gates: nothing is waiting for your answer` and `--json` prints
`{"gates": []}`.

### How each kind of gate is answered

`answer_with` is one line a shell runs as printed: every word is quoted as the
shell needs it. Its form depends on the gate's kind, declared once in
`src/vibey/cli/gate_answers.py`; a test fails when a gate kind is raised
anywhere in `src/vibey` without an entry there.

| Kind | `answer_with` (`ID` is the gate id) | Raised by |
|---|---|---|
| `question` | `vibey answer ID --defaults` | The DESIGN interview. Accepts every question's default. |
| `approval` | `vibey answer ID --verdict accept` | REVIEW. Its other options are `changes` and `cancel`. |
| `deploy_demo_review` | `vibey answer ID --verdict approve` | The Phase ⑥ demo. Or `request_changes`. |
| `choice` | `vibey answer ID --choice local_only` | The deployment opt-in after REVIEW. `deploy` opts in. |
| `deploy_interview` | `vibey answer ID --choice accept_defaults` | The Phase ④ interview. |
| `deploy_acceptance` | `vibey answer ID --choice reject` | Phase ④ spec consent; see below. |
| `deploy_failure_triage` | `vibey answer ID --choice LOOP_DEPLOY_DESIGN` | The Phase ⑥ triage. Or `RETRY_DEPLOY_EXECUTE`, `ABORT_DEPLOYMENT`. |
| `bus_dead_lettered` | `vibey answer ID --choice replay`, or `dismiss` when the message cannot be replayed | A dead-lettered bus message. |
| `budget_exhausted` | `vibey answer ID --raw '{"max_dollars": N}'` | The budget brake. |
| `escalation_exhausted`, `attempts_exhausted` | `vibey answer ID --raw '{"max_attempts": N}'` | A spent effort ladder; a job out of attempts. |
| `verify_repair_exhausted`, `integrate_repair_exhausted` | `vibey answer ID --raw '{"max_rounds": N}'` | BUILD's verify and integrate repair loops. |
| `delivery_exhausted`, `research_evidence`, `engine_misconfigured` | `vibey answer ID --raw '{}'` | Any answer retries, once the cause outside vibey is fixed. |
| `handoff_gate_failed`, `too_many_wind_downs`, and any kind not listed | `vibey answer ID --raw '<json>'` | Nothing reads a particular answer; you write it. |

A verdict or choice uses the gate's declared default, else its first option;
`options` in `--json` lists the rest. `N` and `<json>` are placeholders, and
the text form says what to put there. Neither is valid JSON, so a command
pasted without filling it in is refused by `vibey answer` (exit 2), never
sent. How much more money or how many more tries to grant is a person's
decision, so no number is suggested; the gate's prompt usually proposes one.

`deploy_acceptance` prints its declared default, `reject`. Accepting the
deployment spec also takes explicit consent to change real infrastructure,
which no flag sends and `answer_with` never suggests:
`vibey answer ID --raw '{"verdict": "accept", "explicit_mutation_authorized": true}'`.

## `vibey answer GATE_ID [QUESTION_ID=ANSWER ...]`

Answer a parked human gate. Exactly one of the following modes is required
(or `--defaults` alone for interview gates):

| Form | Used for |
|---|---|
| `QUESTION_ID=ANSWER [QUESTION_ID=ANSWER ...]` | Interview gates, answered per question. Combine with `--defaults` to fill in every other question's default; the explicit pairs win. |
| `--defaults` | Interview gates: accept every question's default. Question keys are model-minted per run, so this needs none. |
| `--choice VALUE` | Deployment and triage gates: sends `{"choice": VALUE}`. |
| `--verdict VALUE` | Review gates: sends `{"verdict": VALUE}` — `accept`, `changes`, `cancel`, `approve`, or `request_changes`. |
| `--raw JSON` | Any other gate shape, e.g. raising a tripped budget cap: `--raw '{"max_dollars": 25}'` or `--raw '{"max_turns": 50}'`. |

[`vibey gates`](#vibey-gates-project_id) prints, beside each open gate, the
form that answers it.

Prints `answered <gate_id>`. These exit 2 with a one-line message:
combining `--defaults` with `--choice`, `--verdict`, or `--raw`; giving no
mode or more than one; `--raw` that is not valid JSON or not a JSON object.
A positional item without `=` (`InvalidAnswer`) and an unknown gate id
(`LookupError`) currently surface as tracebacks, because `answer` is not
guarded.

### Finding a gate id

[`vibey gates`](#vibey-gates-project_id) lists every open gate with its id,
its prompt, and the `vibey answer` command that answers it;
`vibey gates PROJECT_ID` lists one project's. The worker also sends
`NOTIFY vibey_gate_raised` with the gate id when one is raised, for a program
that would rather listen than poll.

## `vibey work PROJECT_ID`

Process one ready DESIGN job, or, when the project is in VISUAL_DESIGN, one
visual-inventory job. Live engine use is explicit and capped. Prints
`processed one job` or `no ready job`.

| Option | Default | What it does |
|---|---|---|
| `--provider {scripted,claudeloop,qwenloop}` | `scripted` | `scripted` needs no live engine. `claudeloop` runs a real, paid session capped by `--max-turns` and `--max-dollars`; its spend is recorded as `budget_spent` ledger events so the budget brake counts it. `qwenloop` runs the sovereign local DESIGN provider (ADR-0015, ADR-0027) and reads research material from `$VIBEY_EVIDENCE_DIR`; with that unset, research refuses rather than inventing a source, and DESIGN stops there. Any other value exits 3 with `Error: provider must be 'scripted', 'claudeloop', or 'qwenloop'`. |
| `--max-turns N` | `1` | Turn cap for this one job (min 1). |
| `--max-dollars F` | `0.25` | Dollar cap for this one job (0.01–10). |

In VISUAL_DESIGN only `--provider scripted` works; any other provider exits
3 with `Error: no live VisualInventoryProducer is implemented yet; use --provider scripted`.
An unknown `PROJECT_ID` exits 3.

## `vibey design`

Bare `vibey design` prints help. Subcommands:

| Subcommand | What it does |
|---|---|
| `design resume PROJECT_ID [--priority]` | Enqueue or resume the project's DESIGN interview. Prints `design job <id>`. `--priority` enqueues it bumped, so it runs next after whatever is running — the same grant and ledger record as [`vibey queue bump`](#vibey-queue). On an interview that has already finished, `--priority` is a recorded no-op, as plain `resume` is a no-op. |
| `design accept PROJECT_ID [--spec-json PATH] [--visual/--no-visual]` | Accept the synthesized spec (optionally importing JSON first) and choose whether to enter the VISUAL_DESIGN interstitial. Defaults to `--no-visual`; the choice is never implicit. Prints `accepted design for <id>; entered <phase>; context under <repo_path>`. |

`--spec-json` expects a JSON object with:

- `objective` and `walking_skeleton` — required strings;
- `criteria` — required list of objects with `criterion_id`, `given`, `when`, `then`, `fit`;
- `constraints` — optional list of `{"text": ..., "kind": "hard" | "soft"}`;
- `non_goals` — optional list of strings;
- `nfrs` — optional list of objects with `nfr_id`, `attribute`, `scale`, `meter`, `must`, `wish` (string or `null`), `fit_criterion`.

The shapes are the dataclasses in `src/vibey/domain/spec.py`. A missing
required key or an unreadable file currently surfaces as a traceback,
because `guard()` renders only `VibeyError`.

## `vibey visual`

Bare `vibey visual` prints help. Subcommands:

| Subcommand | What it does |
|---|---|
| `visual accept PROJECT_ID` | Accept the reviewed visual plan and enter BUILD. Prints `accepted visual design for <id>; entered <phase>`. |
| `visual waive PROJECT_ID` | Explicitly waive the visual plan (the inventory must still be complete) and enter BUILD. Prints `waived visual design for <id>; entered <phase>`. |

## `vibey watch [PROJECT_ID]`

Live TUI dashboard: current phase, queue, engine circuits, active worktrees,
and a ledger tail. Defaults to the most recently created project; an unknown
id prints `unknown project <id>` and exits 1.

| Option | Default | What it does |
|---|---|---|
| `--replay` | off | Replay the project's historical ledger events instead of following live state. |
| `--speed F` | `1.0` | Replay rate in ledger states per second while playing (`--speed 4` advances four states per second). `0` or a negative value disables auto-advance. The option's `--help` text calls it a "multiplier"; it is a rate. |

Replay starts paused. Keys: Space play/pause, Right or `n` next step, Left or
`p` previous step, `q` quit.

## `vibey recover`

Recover stuck leased jobs (e.g. after a worker crash): every job in state
`leased` is set back to `ready`, and its lease owner, lease expiry, and
assigned engine are cleared.

| Option | Default | What it does |
|---|---|---|
| `--project ID` | unset | Recover jobs for one project. |
| `--all` | off | Recover jobs for every project. Wins if `--project` is also given. |

One of `--project` or `--all` is required; with neither, it prints
`Must specify either --project <id> or --all` and exits 1.

Prints `Recovered N stuck job(s).`, where N is the number of rows actually
reset, read from PostgreSQL's `UPDATE n` status tag.

## `vibey status [PROJECT_ID]`

Show the project's name, phase, cycle, visual and deployment decisions,
repository path, queue depth per job state, and engine circuits (circuit
state, consecutive failures, cycle cost). Defaults to the most recently
created project.

| Option | Default | What it does |
|---|---|---|
| `--json` | off | Emit JSON instead: `project_id`, `name`, `phase`, `cycle`, `max_cycles`, `repo_path`, `visual_decision`, `deployment_decision`, `queue_depth`, `circuits` (each with `engine_id`, `installed`, `version`, `conformance_ok`, `circuit`, `capacity_state`, `consecutive_fail`, `cost_usd_cycle`, `selected_count`), and `active_worktrees`. |

## `vibey engines [PROJECT_ID]`

Show recorded engine health for a project as a table: engine, version,
circuit-breaker state, consecutive failures, selection count, and cycle
cost. Rows exist only for engines that `vibey doctor --record` or a worker's
startup preflight has recorded; with none it prints
`no engines recorded for project`. Defaults to the most recently created
project.

## `vibey cost [PROJECT_ID]`

Show per-engine spend for the current cycle, read from `engine_health`, with
a total and two budget caps. The `(N turns)` figure after each engine is its
selection count, not a turn count. Defaults to the most recently created
project.

The caps come from a `budget` table in the project's stored config
(`max_dollars_per_cycle`, `max_dollars_total`), with fallbacks of $40.00 and
$250.00. No code path writes that table today — not `vibey new`, not the
Kubernetes operator, and no runtime code reads `[budget]` from `vibey.toml` — so the command
prints the $40.00 / $250.00 placeholders. The cap that is enforced is
`--max-cycle-dollars` / `--max-cycle-turns` from `vibey new`, applied by the
worker's budget brake; `vibey cost` does not print it.

## `vibey ledger`

Bare `vibey ledger` prints help. Subcommand:

| Subcommand | Option | Default | What it does |
|---|---|---|---|
| `ledger show [PROJECT_ID]` | `--limit N` / `-n` | `50` | Show the most recent N events (min 1). |
| | `--phase PHASE` | unset | Filter to one phase, by name or value, case-insensitive (`BUILD`, `deploy_design`). |
| | `--kind KIND` | unset | Filter to one event kind, by name or value, case-insensitive. |
| `ledger export PROJECT_ID` | `--out FILE` | required | Write the public, redacted ledger projection. |
| | `--billing` | off | Write the operator-scoped billing projection consumed by `vibey-gh forecast`; it keeps metered spend fields and operational event kinds only. |

Prints one line per event, oldest first:
`#<seq> <YYYY-MM-DD HH:MM:SS> [<PHASE>] <kind> [<engine>]`. Filters apply
before `--limit`. Defaults to the most recently created project.

## `vibey queue`

See the job queue in claim order, move a job to the front of it
([ADR-0054](../architecture/decisions/0054-a-bumped-job-runs-next.md)), and reap what is
stuck ([ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md)).
Bare `vibey queue` prints help.

| Subcommand | Option | Default | What it does |
|---|---|---|---|
| `queue list [PROJECT_ID]` | `--json` | off | Every unfinished job: running work first (`running`), then waiting work numbered in the order the claim will take it. A bumped job is marked `bumped #N`, one pulled forward for another job says which, and a job still waiting on unfinished dependencies says how many. A job in a phase or state this vibey does not know is listed with `-` in place of a number, marked as not claimable by this vibey (`claimable_here: false` in JSON). Defaults to the latest project; an unknown id prints `unknown project <id>` and exits 1. |
| `queue bump JOB_ID` | `--project PROJECT_ID` | latest project | Run the job next: after whatever is running, ahead of every un-bumped waiting job, behind anything bumped before it. Its unfinished dependencies move forward with it, dependencies first. Prints every job moved with its new place and any already ahead. |
| | `--source NAME` | unset | An automation naming itself (see below). |
| | `--json` | off | Print the change as JSON. |
| `queue reap` | `--project PROJECT_ID` | latest project | One pass of the queue reaper: every expired lease (requeued while attempts remain, parked with a `delivery_exhausted` gate once they are spent), ready work nobody has taken for `[queue.reap] stale_ready_seconds`, and -- with a broker configured -- vibey's policy reconciled onto the queues it owns and read back, every queue measured, and each dead letter on an owned queue parked as a `bus.dead_letter` job. Ready work and broker verdicts are recorded under this project; a lease under its own job's project. |
| | `--dry-run` | off | Judge everything and change nothing: no requeue, no park, no ledger event, no policy write. Prints what it would do. |
| | `--json` | off | Print the report as JSON: `ok`, `acted`, `surfaced` (each with `object`, `queue`, `condition`, `measured`, `threshold`, `unit`, `action`), `policy`, `notes`, `unreadable`. |
| `queue unbump JOB_ID` | `--project`, `--source`, `--json` | as `bump` | Take the job out of the lane. The lane is always the jobs bumped by name plus their unfinished dependencies, so every pulled-in job no remaining named job needs leaves with it; the output and the ledger list exactly what was removed. Refused while another named job depends on this one. |

A bump changes order only. It never interrupts the running job or touches its lease,
never makes a job claimable before its dependencies succeed, and never shortens a
`run_after` a capacity deferral set; phases and human gates apply as before. A job that
is running can be bumped: it keeps its place if the attempt returns it to the queue.

**Who may reorder** is decided by the project's own `vibey.toml` — at the root of the
repository the project record names, never the current directory — and nothing on the
command line can widen it. With no `--source`, the caller must be the operator: the
account that owns that file (or the repository root, when there is none), checked by uid.
With `--source NAME`, `NAME` must be declared in that file's `[queue.priority] sources`
(see the [configuration reference](configuration.md#queuepriority)) **and** the caller must
still be that account. Anything else is refused: nothing moves and the command exits 3
with the reason.

**Every request is recorded** on the project ledger — `JobPriorityBumped`,
`JobPriorityUnbumped` or `JobPriorityRefused` — whether it moved something, moved
nothing (bumping a job already bumped or already finished, un-bumping one that is not:
exit 0 with `nothing moved` or `nothing to move`), or was refused. The grant is checked before the job is looked up, so a refused
request is recorded whether or not the job exists. `vibey ledger search --kind
JobPriorityRefused` lists the refusals. Refused with exit 3, and recorded:

- a caller that is not the operator, or a source not declared or not run as the operator;
- a `vibey.toml` or repository this process may not read, or one that is not valid TOML;
- a job that does not exist in the project, or is in a state or phase this
  vibey does not know; an un-bump of a finished job;
- a bump whose dependency can never finish (failed or cancelled), or a dependency ring —
  the message names it;
- an un-bump of a job that another named job still depends on — the message names them;
- a request the database aborted to break a lock cycle (retry it).

**`queue reap`** prints what it reaped (`reaped:`), what is stuck and was only surfaced
(`stuck, surfaced, nothing moved:`), the broker policy's read-back (`verified` or
`NOT VERIFIED`), notes, and every source it could not read (`UNREAD:`). Each verdict line
names the action, the condition, the object, the queue, the measured value and the
threshold. It exits 0 when every source was read and the broker policy, where one was
reconciled, read back as written; otherwise 1 -- a reaper never reports success it did not
observe. It never deletes a dead letter: answer the parked job's gate with `vibey answer
GATE_ID --choice replay` (publish it back to the queue it died on, at least once) or
`--choice dismiss`; the broker's copy stays on the dead-letter queue either way. Its
thresholds are [`[queue.reap]`](configuration.md#queuereap).

## `vibey-gh slots`

How many runs of one local model may run at once on this device, measured per device
([ADR-0058](../architecture/decisions/0058-concurrent-local-runs-are-measured-per-device.md)).
This is a `vibey-gh` command, part of the same distribution:

| Subcommand | What it does |
|---|---|
| `vibey-gh slots corpus --pool FILE --out FILE` | Draw a stratified corpus of turn segments from a turn pool (the storm builds one with `storm_turn_pool.py`). |
| `vibey-gh slots calibrate --corpus FILE` | Sweep N = 1, 2, 3, ... on this device beside an idle production runner. Stops at a broken bound or a plateau, checkpoints every step, and records the evidence keyed to the device's fingerprint. |
| `vibey-gh slots allowed` | Print the number a queue may run at once here, with the reason on stderr. Missing or stale evidence prints `1` and requests a calibration. |

Every option is in the vibey-gh [CLI reference](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/cli.md).

## `vibey deploy`

Phases ④–⑥. Bare `vibey deploy` prints help. Each subcommand takes an
optional `PROJECT_ID`, defaulting to the latest project; an unknown id
prints `unknown project <id>` and exits 1.

| Subcommand | What it does |
|---|---|
| `deploy status` | Prints the project name, its current phase, cycle, and the endpoint recorded by the most recent `deployment_verification` artifact (`(none)` if there is none). |
| `deploy inspect` | Prints spec id, scope digest, and monthly budget from the most recent `deployment_spec_accepted` decision. When no spec has been accepted it prints the placeholders `default` / `none` / `$100.00`. |
| `deploy plan` | Placeholder, not yet implemented: prints `Status: NOT EVALUATED` with every check marked "not checked". Reads no IaC changeset and evaluates no budget. |
| `deploy cancel` | Placeholder, not yet implemented: prints a notice and cancels nothing. No cloud resource, ledger event, or job or phase state is touched. |
| `deploy rollback` | Placeholder, not yet implemented: prints a notice and performs no rollback. |

Only `deploy status` and `deploy inspect` read real state today; the other
three reserve the command surface. Deployments themselves run through
`vibey worker` (see `--azure`) after an explicit opt-in at REVIEW.

## `vibey doctor`

Check local PostgreSQL readiness, engine installs and auth; optionally install
PostgreSQL, run the conformance suite, or run the in-cluster preflight instead.

| Option | Default | What it does |
|---|---|---|
| `--conformance` | off | Run the 9-check conformance suite against each checked engine that is installed. |
| `--engine ENGINE` | unset | Check one engine: `claudeloop`, `codexloop`, `cursorloop`, `agyloop`, `opencode`, or `qwenloop`. An unknown name prints `Unknown engine: <name>` and exits 1. |
| `--record` | off | Persist preflight (and conformance, with `--conformance`) results to `engine_health`. Exits 1 if no project exists. |
| `--project ID` | latest | Project to record health for, with `--record`. |
| `--cluster` | off | Run the in-cluster preflight instead of the engine checks — see [Kubernetes guide](../guides/kubernetes.md). |
| `--engines LIST` | unset | With `--cluster`: the worker's own `--engines` allow-list (chart value `worker.engines`). `engine-auth` requires exactly these. Parsed as the worker parses it; empty means unset. |
| `--provider NAME` | `scripted` | With `--cluster`: the worker's own `--provider` (`scripted`, `claudeloop`, or `qwenloop`; chart value `worker.provider`). `claudeloop` adds claudeloop to what `engine-auth` requires. |
| `--install-postgres` | off | Install and start local PostgreSQL when it is missing or stopped. This is explicit; the default doctor never changes the host. It cannot be combined with `--cluster`. |

With `--engine` unset, doctor checks the five paid engines (`claudeloop`,
`codexloop`, `cursorloop`, `agyloop`, `opencode`) whether or not they are installed —
missing ones print `NOT INSTALLED` — and adds `qwenloop` when
`VIBEY_FEATURE_QWENLOOP` is truthy or, if that variable is unset,
`./vibey.toml` in the current directory has `[features] qwenloop = true`.
`--engine qwenloop` works regardless of the flag.

Each engine line shows install state, version, and auth. Auth is the exit
status of `<binary> doctor`; if that command cannot run, doctor falls back
to the engine's API-key variable (see
[Environment variables](#environment-variables)). Each probe starts from the
engine's allow-listed environment, never doctor's own: the defaults, or with
`--record` the target project's `engine_environment`, so a credential that project
declares reaches the auth check and the conformance run as it reaches a session. A
forbidden declaration in that project exits 2.

The final `postgresql` line shows `READY`, `NOT READY`, `UNSUPPORTED`, or
`NOT INSTALLED`. `READY` means a local PostgreSQL server at port 5432 accepts
connections and is at least version 14. `--install-postgres` exits 1 if the
package manager or service start fails, or if verification still does not reach
that state.

The `db-passwordless` line after it asks whether the app DSN's database admits a
login with no password at all: as the DSN's role and as the OS user doctor runs as,
on the DSN's host and, when that host is local, on each local socket directory. It
prints `WARN` when one is let in (trust or peer authentication: any process running
as that user, an engine session included, can open the database without
`VIBEY_PG_URL`; see [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/main/SECURITY.md) §5),
`PASS` when every attempt was refused, and `UNKNOWN` when none reached the server or
`VIBEY_PG_URL` is unset. It never changes the exit code.

With `--conformance`, the command exits 1 if any engine fails a check. The
worker does not select an engine for engine-driven jobs until a
`doctor --conformance --record` run has passed for it.

When `VIBEY_PG_URL` is set, doctor ends with two database checks
([ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)).
Each prints `PASS`, `FAIL` or `UNKNOWN`, and doctor exits 1 if either fails:

- `ledger-guard` fails when the role `VIBEY_PG_URL` connects as could rewrite the ledger:
  it is a superuser, owns `event`, holds `UPDATE`, `DELETE` or `TRUNCATE` on it or a
  partition, or finds a guard trigger missing or disabled. A single-DSN install fails here
  until its roles are split
  ([database roles](configuration.md#database-roles)).
- `local-auth` fails when the server lets a password-less connection in as the owner or a
  superuser. It attempts one on the DSN's host and, for a local host, on the local socket
  directories. It also fails when `pg_hba.conf` has a `trust`, `peer` or `ident` rule that
  can match them. It is `UNKNOWN` (not a failure, never a pass) when it could neither get
  in nor read `pg_hba_file_rules`.

With `VIBEY_PG_URL` unset, `ledger-guard` prints `UNKNOWN` and nothing is checked.

`--cluster` ignores `--conformance`, `--engine`, `--record` and `--project`,
runs up to eight checks, and exits 1 if any fails: the DSN host resolves beyond
its own namespace, the process is not root, the workspace (current directory)
is writable, the engines the worker uses have API keys, the database accepts a
connection, no migrations are pending, and the two database checks above
(`ledger-guard`, `local-auth`). The last three are skipped when the database
connection fails.

The engine check (`engine-auth`) judges what the worker was told to run, not
what is on `PATH` — every runner ships in the image since ADR-0037, so a
binary's presence says nothing. It requires each engine in `--engines`, plus
claudeloop under `--provider claudeloop`, to be on `PATH` with one of its
API-key variables set (qwenloop takes none). With neither, nothing is
required: the check passes and reports which engines in the worker's default
pool have a key, so a default install says plainly when no engine-driven job
can run. `--engines` and `--provider` without `--cluster` exit 2.

## `vibey migrate`

Apply migrations as the schema's owner, then make the application role's privileges
exactly the declared ones
([ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)).
It reads the owner's DSN from `VIBEY_PG_MIGRATE_URL` and the application's from
`VIBEY_PG_URL`. It takes no options.

1. Applies pending migrations under the migration lock, as the owner.
2. Creates the role `VIBEY_PG_URL` names if it is missing and the DSN carries a password.
   A role that is a superuser, the owner, or a member of the owner is refused.
3. Revokes everything that role holds and grants exactly `APP_ROLE_GRANTS`.
4. Attaches the `TRUNCATE` guard to any partition of `event` that lacks it.
5. Connects as the application role and prints the ledger guard.

It exits 2 when `VIBEY_PG_MIGRATE_URL` is unset. It exits 1 when `VIBEY_PG_URL` is unset
(nothing reconciled, guard unchecked), or when the guard is not in force: for instance
while `VIBEY_PG_URL` still names the owner. The Helm chart runs it as the `migrate` init
container of the worker and the operator, the only place the owner's DSN is mounted.

## `vibey operator`

Run the Kubernetes operator, reconciling `VibeyProject` custom resources
(ADR-0025). Requires the optional extra, `pip install 'vibey[operator]'`;
without it the command prints
`operator support is not installed: pip install 'vibey[operator]'` and exits 1.

| Option | Default | What it does |
|---|---|---|
| `--namespace NS` | unset (cluster-wide) | Watch a single namespace instead of the whole cluster. |

## `vibey worker`

Long-running worker: listens on `vibey_job_ready` and dispatches jobs across
every phase for one project.

| Option | Default | What it does |
|---|---|---|
| `--engines LIST` | the five paid engines | Comma-separated allowlist of engine ids (`claudeloop`, `codexloop`, `cursorloop`, `agyloop`, `opencode`, `qwenloop`) for engine-driven jobs. An unknown id prints `Invalid engine: ...` and exits 2. `qwenloop` joins the pool only when `VIBEY_FEATURE_QWENLOOP` is on (see below). A list that matches none of the worker's engines — `--engines qwenloop` with the feature off, say — is refused at startup with `--engines <list> matches none of this worker's engines (...)` and exits 2, rather than starting a worker with no engine that would defer every engine-driven job forever. |
| `--parallelism N` / `-j N` | `1` | Concurrent job loops, 1–16. The effective count is clamped to twice the number of allowed engines and to the CPU count, and is never below 1. |
| `--once` | off | Process one job and exit (`processed one job` or `no ready job`), instead of running forever. |
| `--provider {scripted,claudeloop,qwenloop}` | `scripted` | DESIGN and decomposition providers. `scripted` is fully offline. `claudeloop` uses a live session for both DESIGN and decomposition, capped by `--max-turns` / `--max-dollars`. `qwenloop` uses the sovereign local DESIGN provider (reads `$VIBEY_EVIDENCE_DIR`) with scripted decomposition. Any other value exits 2. |
| `--max-turns N` | `25` | Turn cap per claudeloop DESIGN or decomposition session (min 1). |
| `--max-dollars F` | `2.0` | Dollar cap per claudeloop DESIGN or decomposition session (0.01–10). |
| `--project ID` | latest | Project to work on. |
| `--wait-for-project SECONDS` | unset (min 1.0) | Poll every N seconds for a project instead of exiting 1 when none exists yet — for long-lived deployments, where exiting means a restart loop. |
| `--azure {memory,az}` | `memory` | Azure client for the deploy stage set. `memory` is an in-memory adapter that touches no real infrastructure. `az` uses the real Azure CLI and mutates real resources on consented deploys; the worker runs `az account show` first and exits 1 if you are not logged in. Any other value exits 2. |

The VISUAL_DESIGN stage always uses the scripted visual provider.

On start the worker preflights every allowed engine — including `qwenloop`
when the feature is on, so the standby engine is visible in `vibey engines`
like every other. Engines with no passing recorded conformance produce
``warning: no recorded conformance for <names> -- engine-driven jobs will not select them until `vibey doctor --conformance --record` passes``.
It then prints
`worker started: project=<name> engines=<list or all> parallelism=<n> provider=<p>`.

qwenloop as a standby engine (ADR-0015): the worker enables it only when
`VIBEY_FEATURE_QWENLOOP` is truthy. Unlike `doctor`, the worker does not
read `[features] qwenloop` from `vibey.toml`; it falls back to a `features`
table in the project's stored config, which no creation path writes today.
In practice the environment variable is the only switch for the worker.

The queue reaper (ADR-0056) runs in the same idle iterations: after the lease reap, at
most once per `[queue.reap] interval_seconds` across all of the worker's loops, the
worker surfaces stale ready work and -- with a broker configured -- reaps the broker, as
`vibey queue reap` does. Its findings go to the ledger (`QueueReaped`) and to stderr
(`queue.reaped`, `queue.stuck`, `queue.reap_unreadable`).

Shutdown (ADR-0026): SIGTERM drains the worker — it finishes the job in
hand, claims no more, and exits. A SIGTERM that arrives during startup,
before the handler is installed, is latched at import time and honoured as
soon as the event loop starts. Ctrl-C aborts immediately with exit 130. The
worker writes diagnostic lines to stderr (`sigterm handler registered`,
`drive[<i>] iter=...`); they are temporary instrumentation, not errors.

## Environment variables

Variables read by code under `src/vibey`:

| Variable | Read by | Effect |
|---|---|---|
| `VIBEY_PG_URL` | every command that opens the database; `recover`; `doctor`; `migrate` | The application role's PostgreSQL 14+ DSN ([database roles](configuration.md#database-roles)). There is no default: when unset, vibey refuses with `VIBEY_PG_URL is not set. vibey will not guess a database.` (exit 3 from guarded commands, a traceback from the others). `vibey install --postgres` installs the server but does not set this variable for the parent shell. |
| `VIBEY_PG_MIGRATE_URL` | `migrate` only | The owner's DSN. Migrations run on it and the application role's grants are reconciled from it. Give it to that one command (`VIBEY_PG_MIGRATE_URL=… vibey migrate`); never export it. |
| `VIBEY_EVIDENCE_DIR` | `work --provider qwenloop`, `worker --provider qwenloop` | Directory of reading material for the qwenloop DESIGN provider's research stage. Unset means research refuses and DESIGN stops there. |
| `VIBEY_FEATURE_QWENLOOP` | `doctor`, `worker` | `1`, `true`, `yes`, or `on` (case-insensitive) enables qwenloop; any other set value disables it. When set it overrides config. When unset, `doctor` falls back to `[features] qwenloop` in `./vibey.toml` and `worker` falls back to the project's stored config. |
| `ANTHROPIC_API_KEY` | `doctor` auth fallback; `doctor --cluster` (which also accepts `ANTHROPIC_AUTH_TOKEN`) | claudeloop credentials. |
| `OPENAI_API_KEY` | `doctor` auth fallback; `doctor --cluster` (which also accepts `AZURE_OPENAI_API_KEY`, `CODEX_API_KEY`) | codexloop credentials. |
| `CURSOR_API_KEY` | `doctor` auth fallback; `doctor --cluster` | cursorloop credentials. |
| `GOOGLE_API_KEY` | `doctor` auth fallback; `doctor --cluster` (which also accepts `GEMINI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`) | agyloop credentials. |
| `VIRTUAL_ENV` | engine session launch | Removed, together with `VIRTUAL_ENV_PROMPT`, `PYTHONHOME`, `PYTHONPATH`, and the matching `PATH` entries, from the environment passed to engine sessions, so an engine does not install into or run vibey's own interpreter. |

Engine sessions otherwise inherit the caller's environment. Build-gate and
git subprocesses inherit it minus every `GIT_*` variable. The engine CLIs
read further variables of their own; see each runner under
`src/vibey_runners/`.
