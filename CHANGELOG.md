# Changelog

Every release of `vibey` on [PyPI](https://pypi.org/project/vibey/), newest first. From 0.2.0 on there
are no `vibey-v*` tags, so headings carry the release commit's date instead of a compare link, and
0.2.0 through 0.6.0 were reconstructed from the release commits on 2026-09-15 (ADR-0028).

The design behind these releases is written up as a research paper —
[PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) ·
[HTML](https://the-vibey-project.github.io/vibey/main/paper/) — and the complete documentation is
published as a book — [PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) ·
[EPUB](https://the-vibey-project.github.io/vibey/main/book.epub).

## [Unreleased]

### BREAKING CHANGES

* **vibey_gh:** the sovereign review never returns a verdict on a prompt the model did not
  read in full, and names a model that ran out of room (#1090). #1090 read its whole
  31,765-token prompt and ran out of generation room in the 1,004 tokens a 32,768 window left
  (`done_reason=length`); that is now reported as such, not as a JSON error. Truncation is
  possible on this host -- left to its defaults Ollama 0.34.2 read a 36,798-token request as
  16,386 tokens, about half the window, with no error -- and is now refused three ways:
  requests are sized from everything sent against the declared `[pr_automation.fallback]
  context_window` (default 65,536) beside `reasoning_reserve_tokens` (8,192); every request is
  sent with `truncate: false` and `shift: false`, so Ollama answers an oversized one with HTTP
  400, reported in its own words; and every request carries a random check code at each end
  that the answer must echo. The diff half refuses a diff past `max_diff_chars` instead of
  cutting it; a whole review sends the whole diff, trims only its documents in declared order,
  and claims the diff half alone when any was cut or left out, so the gate asks a human
* **db:** the ledger is append-only by the database, not by convention
  ([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)).
  - **Triggers.** Migration 0016 replaces the `DO INSTEAD NOTHING` rules with triggers that
    refuse every `UPDATE`, `DELETE` and `TRUNCATE` of `event` and of each of its partitions,
    for every role, the owner included, with `the ledger is append-only`. The rules did not
    fire for a partition or for `TRUNCATE`, and the owner could disable them. A rewrite is
    now an error, not a silent no-op, and `DELETE FROM project` no longer cascades through
    a project's ledger.
  - **Two roles.** The application connects as a role (`VIBEY_PG_URL`) that holds exactly
    the declared grants: `SELECT` and `INSERT` on the ledger, no `DELETE` or `TRUNCATE`
    anywhere, and no ownership. Migrations run as the owner, `VIBEY_PG_MIGRATE_URL`, read by
    the new `vibey migrate` alone (given for that one command, never exported) or the Helm
    chart's new `migrate` init container. The chart gains `postgres.appRole` (default
    `vibey_app`), `dsn.existingSecretMigrateKey` (empty by default, so an existing-Secret
    install is unchanged until it names an owner key), and
    `postgres.additionalDatabasePasswords`: Plane and Infisical each connect as a role of
    their own, which the postgres container creates and hands its database on every start,
    instead of as the owner.
  - **Hardened after review.** Migration 0017 pins the guard functions to
    `search_path = pg_catalog, pg_temp`. `vibey migrate` takes `CREATE` on `public` away
    from every role but its owner and reconciles under the migration lock. `ledger-guard`
    also fails when the application role may create objects, owns any, may call a
    `SECURITY DEFINER` function running as the owner, may set `session_replication_role`,
    or when a guard trigger is replica-only, re-pointed, re-evented or its function
    changed. The triggers refuse the owner's DML, not its DDL (`DROP` or `DETACH` of a
    partition), which is why only `vibey migrate` holds the owner's DSN.
  - **Checks.** `vibey doctor` gains `ledger-guard` and `local-auth` checks. A single-DSN
    install keeps running, but `vibey doctor` fails until its roles are split, `vibey
    worker` says so on stderr at every start, and `vibey migrate` exits 1. `local-auth`
    fails when the server lets a password-less connection in as the owner or a superuser;
    SECURITY.md §7 gives the `pg_hba.conf` lines. Upgrade path:
    [database roles](docs/reference/configuration.md#database-roles)
* **qwenloop:** the `shell` tool runs with an allow-listed environment: the system basics
  only, and never `VIBEY_*`, `PG*` or a name containing `KEY`, `TOKEN`, `SECRET`,
  `PASSWORD`, `PASSWD`, `CREDENTIAL`, `DSN` or `DATABASE_URL`. It used to pass everything
  except `KEY` and `TOKEN` names, so `VIBEY_PG_URL` and `PGPASSWORD` reached commands a
  model chose.
* **vibey_gh:** the sovereign review never reads a prompt the model did not see in full
  (#1090). Local requests are sized from everything sent and must fit the declared
  `[pr_automation.fallback] context_window` (default 65,536) beside `reasoning_reserve_tokens`
  (8,192), or are refused rather than silently truncated by Ollama; a whole review sends the
  whole diff (never cut at `max_diff_chars`) and trims only its optional documents; each reply
  is checked against Ollama's `prompt_eval_count` and `done_reason`, so a model that ran out of
  room says so
* **vibey_gh:** the exact-head review reaches a paid model only where `[pr_automation]
  paid_review = true` declares one (sub-doctrine 8.b: a paid counterparty is declared-only).
  Undeclared, the default, the paid `review` job never runs: the sovereign lane answers the
  whole review — the diff and the documentation-contract judgments, judged against the pages
  in `[pr_automation.fallback] context_paths` — for a trusted author whose head is in the
  repository, and every other pull request fails `PR review / gate` with `needs a human
  review: <why> (no paid review is declared, 8.b)`. This repository declares none, on the
  operator's instruction. `paid_repair` and `paid_conflict_resolution` (both default `false`)
  declare the repair and conflict-resolution jobs the same way: undeclared, neither is
  scheduled, and failing scans or a conflict are reported as `needs a human: automated
  <repair|conflict resolution> needs a paid model, and none is declared (8.b)`; this
  repository declares neither, so no job it runs can use `ANTHROPIC_API_KEY`. A refused paid
  call (review, repair, conflict resolution) is now
  reported as `the paid <job> was refused by the API: <reason>` rather than as the action's
  closing "Result subtype: success". Set `paid_review = true` to keep the two-lane review
* **engines:** this era's default local model is `gpt-oss:20b` (sub-doctrine 8.d). vibey's
  Ollama default, qwenloop's endpoint default and the Helm chart's `ollama.model` all name it.
  An install that never set a model now asks Ollama for `gpt-oss:20b` instead of
  `qwen2.5-coder:14b`: run `ollama pull gpt-oss:20b`, or set `VIBEY_OLLAMA_MODEL`,
  `QWENLOOP_MODEL` or `ollama.model` to keep the old one. vibey reads only a reply's
  `message.content`, never GPT-OSS's separate `thinking` channel ([#387](https://github.com/the-vibey-project/vibey/issues/387))
* **qwenloop:** with nothing configured, qwenloop attaches to a running local Ollama instead of
  starting its own llama.cpp server. Set `backend = "llama.cpp"` to keep the old behaviour ([#388](https://github.com/the-vibey-project/vibey/issues/388))
* **vibey_gh:** the local review fallback and `vibey-gh fit` default to `gpt-oss:20b`; the rendered
  review workflows name it too. `[pr_automation.fallback] model` or `--model` keeps another ([#389](https://github.com/the-vibey-project/vibey/issues/389))
* **cli:** DESIGN and DECOMPOSE default to the sovereign `qwenloop` provider when `--provider` is
  not given (sub-doctrine 8.a) ([#322](https://github.com/the-vibey-project/vibey/issues/322))
* **vibey_gh:** the merge train admits no stranger (ADR-0053, sub-doctrine 12.j). A pull request
  whose author is not the owner or in `[merge_train] trusted_authors`, or that carries
  `vibey-gh:external-repair`, is held "needs a human merge" whatever state its gates are in
  and whatever its approvals say, and the owner's notice names which of the two holds it; `trusted_authors` used to bind only with PR automation off. Dependabot's pull requests
  now wait for a person. The train also stops retrying a refused merge with
  `gh pr merge --admin`: a refusal (for example `REVIEW_REQUIRED`) is reported "needs a human
  merge" with GitHub's reason and the pass continues. `vibey-gh merge-train --admin-fallback`
  restores the retry for one run; no configuration key can (sub-doctrine 12.d). `vibey-gh
  promote --wait` gets the same rule, with `--admin-fallback` (only with `--wait`)
* **engines:** an engine session no longer inherits the worker's environment. Every engine
  process (the BUILD and DEPLOY_EXECUTE run, its `--version`/`doctor`/`--help` probes, and the
  claudeloop and opencode DESIGN/DECOMPOSE sessions) and every gate command used to start from a
  copy of it with only the Python variables removed. So `VIBEY_PG_URL` (the queue and ledger
  DSN), vibey's other `VIBEY_*` tokens and passwords, `GH_TOKEN`/`GITHUB_TOKEN` and any cloud
  credential reached processes that run model-chosen shell commands unattended. Each is now
  built from an allow-list: the system basics (`PATH`, `HOME`, locale, `TERM`, CA bundle,
  proxy, `XDG_*`), plus, for an engine, the variables its descriptor declares
  (`env_passthrough`, for example `CLAUDELOOP_*` and `ANTHROPIC_*`) and its own API credential.
  Anything else is declared in `vibey.toml`: `[engine_environment]` `allow` (every engine) and
  `[engine_environment.engines]` `<engine> = [...]` (one engine), and `[gates]` `env_allow`
  (gate commands). `vibey new` copies both tables into the project record; the `VibeyProject`
  spec declares the same objects as `engineEnvironment` and `gates`. Nobody edits the
  record's JSON by hand. `VIBEY_*` and libpq's `PG*` can never be declared, for gates or
  engines, and an engine can never be given a name containing `DSN`, `DATABASE_URL`,
  `PASSWORD` or `PASSWD`. A declaration that tries is refused by `vibey new` and the operator
  before the project exists, and stops the worker when it is built; a descriptor's own
  `env_passthrough` is checked when its adapter is built. What now needs declaring: agyloop's
  Vertex credentials (`GOOGLE_ACCESS_TOKEN`, `CLOUDSDK_AUTH_ACCESS_TOKEN`,
  `GOOGLE_APPLICATION_CREDENTIALS`, and `CLOUDSDK_CONFIG` when its gcloud configuration is not
  in the default place), a provider key OpenCode reads from the environment, a `GH_TOKEN` for
  claudeloop's GitHub issue import, and any toolchain variable a gate needs (`JAVA_HOME`,
  `GOPATH`, ...). See `docs/reference/configuration.md#engine_environment` and `#gates`
* **git:** vibey's own git calls (the BUILD worktree's `git worktree add`, the integration
  `git merge`) start from the system basics plus `GIT_CONFIG_NOSYSTEM=1`, never the worker's
  environment, and run with `-c core.hooksPath=/dev/null -c core.fsmonitor=false`; the merge
  also passes `--no-verify`. An engine working in a linked worktree could plant a hook in the
  repository's common directory, or set `core.hooksPath`, `core.fsmonitor`, a filter or a merge
  driver in its shared config, and vibey's next git call ran it with `VIBEY_PG_URL` in its
  environment. A repository whose own config (`local` or `worktree` scope, or a file they
  include) declares a filter driver (`filter.<x>.clean|smudge|process`) or a merge driver
  (`merge.<x>.driver`) is now refused before vibey checks out or merges in it, failing the
  job; declare a driver you need, such as Git LFS's, in your global git config. `vibey worker
  --azure az` runs `az` through an executor of its own, with the system basics plus the Azure
  CLI's configuration variables (`AZURE_CONFIG_DIR`, `AZURE_CORE_*`, ...)

### Added

* **cli:** finding a project or an open gate no longer takes SQL. `vibey projects` lists every
  project, newest first, with its id, phase, cycle and open-gate count; `vibey gates
  [PROJECT_ID]` lists every open gate, oldest first, with its project, kind and prompt, and
  `answer with:` -- the exact `vibey answer` command that answers it. Both take `--json`
  (a projects array; `{"gates": [...]}`), the contract the VS Code extension reads, and both
  exit 0 on an empty list. How each gate kind is answered is declared once, in
  `vibey.cli.gate_answers`: a verdict or choice from the gate's own options, `--defaults` for
  the interview, `--raw '{"max_dollars": N}'` and the other grants with the number left to
  the person, `--raw '{}'` where any answer retries, and `--raw '<json>'` for the rest; a
  test fails when a gate kind is raised without an entry there. The repositories gain
  `list_all()` and `open_all()`, and the next-step hints, the README, the CLI reference and
  the greeter runbook point at `vibey gates` instead of a `human_gate` query

* **vibey_gh:** `vibey-gh slots corpus|calibrate|allowed` measure how many runs of one local
  model fit on a device at once, and `[local_models] concurrent_runs` declares it (sub-doctrines
  8.c and 8.j, ADR-0058). `calibrate` replays storm-shaped turns (`truncate: false`, so a prompt
  a slot cannot hold is refused, never silently cut) at N = 1, 2, 3, ... on a runner of its own
  beside an idle production runner. It samples wired memory, swap-ins and swap-outs, and
  residency every second, compares every answer with the one-slot answers, and stops at a
  broken bound or a plateau. Every completed step is checkpointed, so a sweep a reboot
  interrupts resumes. The evidence is keyed to a device fingerprint (hardware, memory,
  accelerator, OS, runner version, model digest, context window). `allowed` prints the number
  a queue may run here: the default `1` probes nothing, `"measured"` takes what this device's
  evidence supports, and a larger number is refused unless the device measured it inside every
  bound. Missing or stale evidence means one, said out loud, with a calibration requested. A
  step taken while another runner held a model is discarded, and a 200 with no `done_reason`
  counts as a failure, not an answer.
* **cli:** a project's budget can be added to, changed and removed after the project exists;
  until now nothing could change the caps `vibey new` set. `vibey budget [PROJECT_ID]` shows
  the caps, this cycle's spend against them and every change to them; `--all` shows every
  project, newest first; `--json` is the object the VS Code extension reads (`project_id`,
  `name`, `cycle`, `caps`, `spend`, `exhausted`, `history`). `vibey budget set
  [--max-cycle-dollars F] [--max-cycle-turns N]` and `vibey budget clear (--dollars | --turns
  | --all)` change `max_cycle_dollars` / `max_cycle_turns` in the project's config, the one
  place the brake reads them, and append one `BudgetCapChanged` event per changed cap
  (`field`, `old`, `new`, `by`, `account`) in the same transaction; a change that changes
  nothing records nothing. `--by NAME` lets a tool name itself, a label for the record with
  the account recorded beside it. A cap at or below the cycle's spend is allowed and the
  command says the next BUILD session will park a `budget_exhausted` gate, and it names any
  job already parked on one with the `vibey answer` that resumes it. The brake now reads the
  caps at every BUILD session instead of once when the worker starts, so a change binds a
  running worker's next session and an uncapped project can be capped without a restart.
  `vibey cost` reads through the same service, its output unchanged. The publication policy
  now names every kind it withholds (`WITHHELD_KINDS`) and a test fails on a kind classified
  nowhere; `BudgetCapChanged` is withheld from the public and the billing shard
* **storm:** `storm-queue.sh` asks `vibey-gh slots allowed` how many lanes may run at once,
  instead of the host-wide `pgrep` it hard-coded. It runs more than one only when this device's
  evidence says so, and calibrates itself when its queue empties and a calibration was
  requested, from its own lane records or, when none survive, its committed specs
  (`storm_turn_pool.py`).
* **vibey_gh:** the Discord announcement after a docs deploy now says what changed: `vibey-gh
  announce` posts one line per merged change, grouped Breaking / Added / Fixed / Other, capped
  at `[announce] max_changes` (default 8) with `…and N more` and a compare link, merge and
  release chores counted rather than listed, and the surface links last. The message is under
  Discord's 2000-character limit by construction and escapes every mention, link and markdown
  character a commit subject carries, and the payload sets `allowed_mentions: {"parse": []}`.
  The range is a position (sub-doctrine 10.g). Each `Release surfaces` run records its branch
  and release commit in its `run-name`, and a `Record the announced position` step records
  that Discord accepted the post and the position was read. The next announcement starts
  from there. A history that could not be read is announced as `unknown` and never recorded,
  so nothing is skipped; the first announcement, a force-push, or an exhausted window
  re-anchors and says so. A release announces its `CHANGELOG.md` section with the tag range. Configured by the new `[announce]` table; the inline heredoc is gone.

* **cli:** `vibey doctor` prints a `db-passwordless` line: `WARN` when the app DSN's database
  accepts a login with no password (trust or peer authentication) as the DSN's role or the OS
  user doctor runs as, on the DSN's host or a local socket. Any process running as that user,
  an engine session included, could then open the queue and the ledger without
  `VIBEY_PG_URL`. It never fails the command; SECURITY.md §5 now states this limit, and that
  the unwired container boundary does not address same-user access
* **storm:** the push-gate reaper no longer depends on the storm, or on everyone having
  moved off the old push recipe. `push_gate.py install-schedule` installs one reaper pass
  every `[push_gate] schedule_seconds` (90) as a launchd agent on macOS or a systemd user
  timer on Linux, rendered from tracked templates. `schedule-status` and
  `uninstall-schedule` go with it, and `--target cron` prints a cron line instead. A
  non-blocking reap lock makes overlapping passes safe. A bare-`mkdir` lock with no owner
  record is traced to its `git push` by process (the only push started within 5 s of the
  lock's mtime, in a declared worktree root, whose group holds only the push recipe) and
  judged by the same idle and ceiling rules, evidence first. Anything less certain is
  `unknown` and is never killed. `lane-publish.py` and `storm-snapshot.py` now push through
  `push_gate.py run` (new `--wait-timeout` and `--push-timeout`), a meta test fails any storm
  tool that pushes around the gate, and CONTRIBUTING.md gains "Pushing in this repository":
  the one recipe, `push_gate.py run -- git push …`

* **storm:** a hung push gate can no longer hold every other push hostage. After one push's
  pytest sat at 0% CPU for 39 minutes holding the storm's shared push lock, three layers stand
  in the way. No single test can hang either suite: `timeout = 300` (pytest-timeout, now in
  both dev extras) fails the test by name and the suite carries on, and `faulthandler_timeout
  = 240` dumps every thread's stack first; `tests/conftest.py` also dumps them on SIGUSR1,
  into `VIBEY_PYTEST_STACKS_DIR` when set. The push lock is code:
  `docs/plans/qwenstorm-3.0.0/tools/push_gate.py` `acquire` / `release` / `run -- git push …`
  / `status`, an atomic `mkdir` holding an owner record (pid, process group, branch, worktree,
  start time, uid), released only by its owner, at a declared path (`[push_gate] lock`). Its
  reaper runs first in every `storm-cycle.py` pass and acts only on a measured condition — the
  holder is gone; the push's own process group used under `idle_cpu_seconds` (2) over
  `idle_window_seconds` (600), sampled with `ps -o time` across passes; or it passed
  `wall_ceiling_seconds` (3600) — writing evidence (process tree, push-log tail, py-spy or
  SIGUSR1 stacks) before it SIGTERMs, then SIGKILLs, that group and nothing else. Each reap is
  one line in an append-only reap log, and the push reports `reaped: hang` (exit 124), never
  a test failure. `--dry-run` reports without acting (sub-doctrines 12.d, 12.e)
* **queue:** everything a queue guards is reaped by measurement (ADR-0056). Five conditions,
  each against a declared `[queue.reap]` threshold (rendered by the chart from
  `worker.queueReap`): (a) a hung handler -- the broker-wide `consumer_timeout` is now
  declared by the chart (`surfaces.rabbitmq.consumerTimeoutMs`, the image default of 30
  minutes) and vibey's own queues get a `consumer-timeout` of six hours by policy; (b) held
  work with nobody holding it, surfaced; (c) a poison job, parked with a `delivery_exhausted`
  gate once its attempts are spent, and a `delivery-limit` of 20 on vibey's quorum queues;
  (d) ready work nobody has taken for `stale_ready_seconds` (900), surfaced; (e) a dead letter
  on a queue vibey owns becomes a parked `bus.dead_letter` job with a `bus_dead_lettered`
  gate -- answer `--choice replay` or `--choice dismiss` -- and is never deleted; a queue
  vibey does not own, such as Plane's, is only surfaced. Every reap is a `QueueReaped` ledger
  event carrying the object, condition, measured value, threshold and action. The worker
  runs the reaper when idle, at most once per `interval_seconds` (60); `vibey queue reap
  [--dry-run] [--json]` runs it on demand and exits 1 when it could not read a source or
  verify the broker policy. In a cluster the bus is now composed from the chart's
  `VIBEY_BUS_*` environment even with no `vibey.toml`, so the reaper sees the broker at all.

* **vibey_gh:** `vibey-gh runner install|check|cleanup|uninstall` stands the sovereign review
  runner up from a new `[runners]` table instead of hand-written LaunchAgents (12.c). Its gh
  credential is a dedicated, file-based login in `~/.config/gh-runner` holding a fine-grained
  token with Administration read/write on this repository only; the supervisor refuses any
  other credential. Operator steps: `docs/runbooks/sovereign-review-runner.md`.

* **queue:** a job can be bumped to run next (ADR-0054). `vibey queue bump JOB` puts it
  after whatever is running — never interrupting it — behind anything bumped before it
  and ahead of all un-bumped waiting work, and pulls its unfinished dependencies forward
  with it; a dependency that can never finish refuses the bump. `vibey queue unbump JOB`
  takes it out of the lane, which is always the jobs bumped by name plus their unfinished
  dependencies, so nothing is left behind; it is refused while another named job needs it.
  A named job that ends cancelled or failed is swept out with what it alone pulled in by
  the project's next admitted bump or un-bump, recorded (a refused request changes
  nothing); a job this vibey cannot write -- an unknown phase or state -- is left in place
  with everything it still needs, and named, rather than refusing the request. The lane is
  derived through a dependency in an unknown state, so a job a live named job needs is
  never swept past it. `tests/meta/test_migration_drops.py` reads SQL as PostgreSQL lexes
  it -- comments, strings (`E''`, `U&''`, and literals joined by `||`), quoted names
  (`U&""` too), `DO` bodies and `EXECUTE` strings -- and catches every step that takes
  something from a running reader: a column dropped, renamed or retyped; a table, view or
  sequence dropped, renamed away or moved by `SET SCHEMA`; a table replaced under its own
  name without a column it had (known by replaying the migrations in order); and a type
  dropped or renamed, or an enum value renamed (`ALTER TYPE ... RENAME VALUE`), which fails
  an older worker's strict `phase` or `state` read. The ADR sentence must name the workers
  to drain against this migration or an `N.N.N` release, and not negate the drain.
  `vibey queue list [PROJECT]` shows the queue in claim order with every bump marked;
  `vibey design resume PROJECT --priority` enqueues the interview bumped. The claim orders
  `bump_seq ASC NULLS LAST` first (`migrations/0014_job_bump.sql`), so the order among
  un-bumped work is unchanged, and it now claims only jobs in a phase this vibey knows.
  Only the operator — the account owning the project's own `vibey.toml` — and the
  sources that file declares in `[queue.priority] sources`, run as that account, may
  reorder; every request, moved something, moved nothing or refused, is recorded on the
  ledger (sub-doctrine 12.j). `EnqueueRequest.priority` is removed, so a bump is the only
  way to reorder work; the KEDA scaler counts only jobs in a phase this release claims.
  The migration's index rebuild stalls claims until it commits, and during a rolling
  upgrade workers still on the previous release ignore bumps until they are replaced.
  **Upgrade note:** `migrations/0015_job_bump_named.sql` drops `job.bump_origin`, so every
  worker from a build before 0015 must be drained or replaced before 0015 runs; a worker
  still on such a build fails every job read once it commits. The orphans 0015 clears are
  not recorded on the ledger (ADR-0054, known gap).
* **vibey_gh:** `vibey-gh approve-check PR [--head SHA] [--approve]` enforces the delegated approver's grant
  by code (sub-doctrines 12.f, 12.j): it exits 0 only when every `[unattended_approval]`
  condition holds — live switch, author allowlist (`@codeowners` expanded), branch globs,
  `forbidden_paths` (whole-PR refusal), green gates, and an approving account that wrote none
  of the change — and prints every refusal otherwise. `switch_variable` and `switch_value` are
  now declared keys. `--approve` submits one approval pinned to the checked head, and only
  after every condition held. The `unattended-approver` agent runs it as `python -m vibey_gh.approval_check`
  (keeping the CLI off its trust path), first and to approve; its `gh api` grant is gone.
* **qwenloop:** an `edit_file` tool that replaces exactly one match; `write_file` refuses to
  shrink an existing file of 40 or more lines by more than half ([#346](https://github.com/the-vibey-project/vibey/issues/346))
* **qwenloop:** every `turn.completed` event records `started_at`, `ended_at`, `duration_ms`,
  `model_ms` and the model server's own timings; the managed server writes to `server.log`
  instead of `/dev/null`, and `meta.json` records the settings a run used, with its API key
  redacted (sub-doctrine 8.g) ([#382](https://github.com/the-vibey-project/vibey/issues/382))
* **vibey_gh:** `vibey-gh`'s PR automation is split into two workflows — `PR evaluate`
  (`pr-evaluate.yml`, publishes `PR evaluate / gate`) and `PR review` (`pr-review.yml`,
  publishes `PR review / gate`) — so a red gate names its failing task instead of hiding
  behind one ambiguous `PR automation / gate` check. The scan gate lists the failing
  checks in its title; the review gate certifies the exact-head review verdict; the merge
  train requires both.

### Fixed

* **ci:** the delivery estimate refreshes once an hour, and by hand, instead of on every push,
  pull request and issue event. Its pull request now runs every CI gate: the `[skip ci]` that
  let #1125 merge a ledger record, and break develop's paper-figure check with no check run,
  is gone.
* **tests:** a killed test run no longer leaves its databases behind for good. Each session
  now holds an advisory lock on its database for as long as it lives, and marks the database.
  Every run drops, in the background, the test databases that no live session holds
  (`tests/db_reaper.py`; `uv run python -m tests.db_reaper --dry-run` shows what would go).
  An unmarked database from an older harness is dropped only when no other test session is
  running, and a database with an open connection is always kept. On the first run, 1,141
  leaked databases, about 15 GB, were dropped from one machine.
* **storm:** the push-gate reaper, now on an unattended schedule, acts only on what it has
  checked (the independent review of #1105 and #1107).
  - **Kill safety.** The lock and the traced push are read again under the lock's mutex before
    any signal, so a push that ends while the evidence is written is never followed by a kill
    of the recipe's next command. `acquire` is judged by the caller's process group
    (`--pid $$`), not by the `$(...)` subshell that exits at once and got the lock released
    mid-push.
  - **Trust.** The owner record is checked field by field. A lock or record that is a
    symlink, another uid's, or malformed is untrusted and never acted on. The state directory
    is 0700, nothing is written or read through a link, and a push log is read only from the
    gate's own logs.
  - **Observed kills.** A kill is recorded only once the group is seen gone. EPERM means
    "not ours". `protected` matches the program, not the command line, and a group whose
    members cannot be read is never killed.
  - **Awake time.** Holds and idle windows are counted in awake time (CLOCK_UPTIME_RAW on
    macOS, CLOCK_MONOTONIC on Linux), with the boot id, so a laptop's sleep is never a hang.
    A reused holder pid is told apart by its start time.
  - **Shared locks.** The mutex and the reap lock sit beside the lock.
  - **Schedule health.** `schedule-status` reports the last exit, from `launchctl print` or
    `systemctl --user show`, and flags a stale `reaper.log`. `install-schedule` refuses a
    temporary directory, a linked worktree, a Python older than 3.11, or a value systemd
    cannot quote.
  - **Pushes around the gate.** `run --push-timeout` records its kill as a reap.
    `scripts/fleet/land.sh` now pushes through the gate, and an AST scan finds any push that
    goes around it.
  - **Ubuntu 26.04 LTS.** Its systemd and /proc paths are first-class (#1116).

* **vibey_gh:** a whole sovereign review's documents are bounded by their own
  `[pr_automation.fallback] max_document_chars` (default 120,000) and the window, no longer by
  the diff's `max_diff_chars`. This repository's two pages already took 59,607 of the diff's
  60,000, so a small README edit cut one, the review claimed the diff half alone, and every
  gate asked a human. Documents trimmed to the window are also no longer refused once the
  request's check codes are added, and a refusal whose body breaks off mid-read is still reported
* **notify:** a desktop notification's title and message reach `osascript` as arguments of a
  fixed `on run argv` script, never as AppleScript source. Only `"` was escaped before, so a
  model- or gate-written message ending `\" & (do shell script ...) --` ran a shell command.
  `notify-send` gets its text after `--`, and the notifier starts from the system basics
* **engines:** the worker's startup preflight and `vibey doctor --record` probe each engine
  with the project's `engine_environment`, so a credential the project declares for opencode
  or agyloop reaches the auth check and the conformance run, not only the session
* **vibey_gh:** the sovereign heartbeat is honest and no longer skips the pre-push gate
  (ADR-0059). `vibey-gh sovereign --beat` publishes only while GitHub lists a runner with the
  lane's label as online (read with the runner's own login) and the model endpoint answers;
  otherwise it pushes nothing, says why, and the heartbeat goes stale so the gate falls back
  honestly. It no longer pushes with `--no-verify` or a bare `--force`: the pre-push hook now
  recognises by its own rule a push that carries no code (`vibey-gh push-scope`: every ref
  outside `refs/heads/` and `refs/tags/`, every commit the empty tree with no parents), and
  the previous heartbeat is replaced by compare-and-swap. The timer is declared:
  `vibey-gh heartbeat install|status|uninstall` (also run by `runner install`/`uninstall`)
  renders a launchd agent on macOS or a systemd user timer on Linux, and refuses an
  interpreter, package or log under a temporary directory or inside a git work tree. The
  hand-written `vibey-local-authority` LaunchAgent that used to publish the heartbeat is
  retired.

* **queue:** the lease reaper is bounded (ADR-0056, closing ADR-0044 §8's latent gap). An
  expired lease whose attempts are spent is parked with a `delivery_exhausted` gate instead of
  re-readied, so a job that kills its worker on every attempt is no longer claimed forever;
  one attempt is refunded, so each answer buys exactly one more delivery. Every reap is now
  recorded on the ledger in the same transaction as the row it moves.

* **qwenloop:** a model request waits `idle_timeout_seconds` (default 900; 0 waits
  indefinitely) instead of a hard-coded 300 s ([#345](https://github.com/the-vibey-project/vibey/issues/345))
* **qwenloop:** an HTTP 500 "error parsing tool call" no longer ends a run: the turn is retried
  up to three times with a correction, each retry recorded as `turn.retried` ([#386](https://github.com/the-vibey-project/vibey/issues/386))
* **qwenloop:** one empty model reply (no tool call, no text) no longer ends a run. It is
  retried with a neutral nudge up to `max_empty_reply_retries` consecutive times (default 2,
  `0` restores the old behaviour); each retry is a new model call that spends a turn of
  `max_turns`. Every empty turn writes a `turn.empty` event with its `finish_reason`, token
  counts, whether the reply carried a reasoning field, the reasoning's length, and an excerpt
  of its start capped at `empty_reply_reasoning_excerpt_chars` (default 400, `0` records none),
  marked when truncated and recorded as data only. Every tool call writes a `tool.call` event
  with its name and arguments before the tool runs; each argument value is capped at
  `max_recorded_argument_chars` (default 200), so file content is never recorded whole. The
  `failed` event now names one reason — `empty_response`, `turn_limit` or
  `invalid_completion_claims` — with the run's `turn` and `max_turns`, and `meta.json` records
  `max_turns` and every recording cap. `ChatChunk` gains a `ChatChunkInterface` seam, which
  the runner and the `InferenceServer` port now depend on (ADR-0016)

## [2.0.0] (2026-09-21)

### Added

* **qwenloop:** local Qwen storm execution now preserves tool context, emits explicit
  completion and verdict markers, and supports audible desktop notifications.
* **governance:** Convergence-Driven Development (CDD), evidence-bounded status, and
  the software-organism model are documented in the research paper, guides, doctrine
  corpus, and architecture decisions.
* **paper:** the tracked Qwen storm record and reproducible evidence extractor now
  keep the paper's operational claims tied to repository data.

### Fixed

* **qwenloop:** unknown verdict-tool failures no longer terminate a run without a
  structured terminal record.
* **conformance:** existing scratch repositories receive the local Git identity
  required for savepoint commits on every run.
* **notifications:** outbound webhooks reject private destinations and redirects, and
  failed configured deliveries are reported to the worker instead of being swallowed.

## [1.5.0] (2026-09-19)

### BREAKING CHANGES

* **packaging:** one distribution, one version — `pip install vibey` now delivers the whole
  family. The `vibey` wheel carries every workspace tenant (`claudeloop`, `codexloop`,
  `cursorloop`, `agyloop`, `qwenloop`, `vibey_runners`, `vibey_gh`, `vibey_skills`,
  `vibey_bootstrap`) and puts every one of their console scripts on `PATH`. The nine
  separate PyPI distributions are gone — `pip install claudeloop`, `pip install vibey-gh`
  and the rest no longer resolve, and nothing in this repository asks an index for a family
  package any more. The tenants remain separate workspace members with their own
  `pyproject.toml`, version, Python floor, tests and gates (ADR-0021, ADR-0022); what ended
  is separate *publication*, not separate projects. Extras move with them:
  `claudeloop[voice]` becomes `vibey[voice]`, `vibey-bootstrap`'s Azure core becomes
  `vibey[azure]`, and its ~40 per-feature extras are reached through one
  `vibey[bootstrap-all]` aggregate; `vibey[skills]` stays as an empty alias. The published
  Python floor is now 3.12 for everything, so the 3.10 and 3.11 floors the tools used to
  publish cease to exist as shipped artifacts even though CI keeps testing them
  ([ADR-0037](docs/architecture/decisions/0037-one-distribution-one-version.md))

### Bug Fixes

* **db:** replicas that start together no longer race to apply the same migration. Every
  `build_app()` — every worker start and every CLI command that opens the queue — applied
  pending migrations with no lock, so pods brought up together by a KEDA scale-out or a Helm
  rollout each read the same applied set and ran the same migration; on a fresh database even
  the `schema_migration` bootstrap collided on the catalog. The new `PostgresMigrator` holds a
  session-level Postgres advisory lock (key `sha256('vibey.migrate')`, derived as ADR-0029
  derives the integrate key) from before it reads the applied set until the last migration has
  committed, and releases it in a `finally`: one process migrates, the rest wait and find
  nothing to do. The wait is bounded by `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` (default `300`,
  `0` waits indefinitely); when it runs out the start fails with `MigrationLockTimeout` naming
  the backend pid that holds the lock, and a value that is not a usable number of seconds fails
  the start before the pool opens rather than falling back. `apply_migrations` remains as a
  façade with the default wait (#114)
* **gh:** `vibey-gh promote` rewrites a reused promotion pull request's title and body from
  the current derivation instead of leaving them as the run that opened it wrote them
  (#235). #231 kept reading `chore(release): 0.8.0` and "5 file(s) differ" while it
  proposed a 178-file 1.0.0. The body now opens with a `vibey-gh-promotion` record of the
  version the pull request was opened at, says when that differs from the version it now
  carries, and says the merge publishes nothing only when the version equals the release
  branch's. An edit refused over Projects (classic) falls back to the REST endpoint; a
  refresh that fails is a note, not a failed promotion.
* **cluster:** `vibey doctor --cluster` passes a default chart install again. Since the one wheel
  put every runner on `PATH` (ADR-0037), `engine-auth` judged all four paid engines in every pod
  and failed the default `--provider scripted` install, which mounts no keys; `cluster-smoke`
  deploys exactly that install but never runs the preflight, so CI did not notice. The check now
  judges the engines the worker is told to use: `doctor --cluster` takes the worker's own
  `--engines` and `--provider` (chart `worker.engines`, `worker.provider`), requires each of those
  to be on `PATH` with an API key, and with neither reports, as a pass, which engines in the
  worker's default pool have a key — so a default install says plainly that no engine-driven job
  can run. Either flag without `--cluster` exits 2. The check and the sweep behind it are classes
  with declared interfaces (ADR-0016)
  ([#121](https://github.com/the-vibey-project/vibey/issues/121))
* **docs:** the Kubernetes guide, runbooks 05 and 16, `values.yaml`'s header and ADR-0025's status
  stop saying engines do not ship in the image; runbook 16's separate engines image is recorded as
  moot and its remainder narrowed to Phase 0 (codexloop needs an external `codex`; `claudeloop
  doctor` looks for `claude` on `PATH` only, not the copy `claude-agent-sdk` bundles). qwenloop's
  orphaned `deploy/docker/Dockerfile` — built by nothing, keeping `pip`, no fixed uid — is deleted;
  `docker run --entrypoint qwenloop <vibey image>` runs it
  ([#121](https://github.com/the-vibey-project/vibey/issues/121))
* **deploy:** the KEDA ScaledObject counted claimable jobs across every project, while a worker claims only its own (`JobRepository.claim`, `j.project_id = $3`), so another project's backlog scaled up workers that could never claim it. The query is now scoped to `worker.project` when set, and otherwise to the newest project, by the same `ORDER BY created_at DESC` the worker binds with. The ScaledObject's name and labels are unchanged. `worker.project` is validated as a UUID at render time, since it now reaches SQL. `tests/infrastructure/db/test_keda_scaler_query.py` runs the rendered SQL from the goldens against the real schema and asserts it counts exactly what `JobRepository.claim` can take (#121)
* **gh:** `vibey-gh forge-snapshot --out DIR [--classes …] [--since MOMENT|resume]`, a
  read-only capture of a GitHub repository's own state into plain files the project owns
  (#136, slice S1). Issues, comments, change requests, reviews, review comments, labels,
  milestones, releases with their asset manifests, and tags each go to `DIR/<class>.jsonl`
  as append-only `vibey.forge-record/1` records: the forge's JSON verbatim in a forge-neutral
  envelope, sealed with a SHA-256 over the vibey ledger's own canonical form and hash-chained
  to the record before it. `DIR/manifest.json` gives every class's status, counts, chain head
  and resume cursor, and names every artifact class it does not capture with the reason. A
  class the forge could not be asked about is recorded as `could-not-look` and never written
  as empty. `--since` resumes and continues every chain; content already recorded is never
  written twice, so a rerun appends nothing. Nothing is written to the vibey ledger yet: that
  writer (S4) needs #114. Schema: `src/vibey_tools/gh/docs/forge-snapshot.md`
* **worker:** a heartbeat that fails no longer throws away finished work or kills the worker. `_heartbeat_forever` caught only `CancelledError`, so a pool timeout or a Postgres failover ended the task with the exception stored; `run_once` re-raised it from its `finally`, `_settle` never ran — a session that had succeeded was never acked, its lease expired and another worker paid to redo it — and the exception took the worker process down with every parallel drive loop in it. A beat that raises is now said as `job.heartbeat_failed` at warning and retried at the next interval; a beat the queue refuses is said once as `job.lease_lost` and the loop stops beating. The per-kind lease extension right after the claim is guarded the same way and carries on at the default lease. The settle writes stop discarding their answers too: an `ack`, `nack`, `grant_attempts` or `park` refused by the lease guard is said at warning as `job.ack_rejected`, `job.nack_rejected`, `job.grant_rejected` or `job.park_rejected`, the way `job.defer_rejected` already was, and a refused grant skips the nack that would otherwise have failed the job outright. `WorkerLoop` gains its declared seam, `application.interfaces.WorkerLoopInterface` (ADR-0016) ([#211](https://github.com/the-vibey-project/vibey/issues/211))
* **gh:** `[install] pin_version` pins adopters again. From 1.0.0 `vibey-gh install` rendered a floating `pip install --quiet vibey` for every repository that was not `vibey` itself, so the ten adopters that set the key lost their exact pins without a word. The pin is now the release `vibey-gh` runs from: the repository's own `[project] version` where it IS `[install] fallback_package` (unchanged, so vibey's own workflows render byte-identically); otherwise the installed `fallback_package` release that provides the running `vibey_gh`, read from its metadata, so `uvx --from vibey==X.Y.Z vibey-gh install` renders `"vibey==X.Y.Z"`. An editable or other source-tree install names no release, so it still floats, and `install` and `check` now print a `notice:` saying why. The resolution sits behind `FallbackPinResolver` and `InstalledDistributions`, each with its interface beside it (#259)
* **gh:** the managed `commit-msg` hook now carries a refusal from the project's own chained `commit-msg.local` out as its exit status. It chained with `[ -x … ] && "…"` and runs without `set -e`, so a project hook that rejected the message was ignored and the commit went ahead. `pre-push` already propagated the status and now says so explicitly with `|| exit $?`
* **gh:** the `Provenance` workflow takes its promotion shortcut, which skips the per-commit trailer audit, only when the pull request's head repository is this repository. It had matched branch names alone, so a fork pull request from a branch named like the integration branch into the release branch skipped the audit of its commits. The head repository reaches the script through `env:` as `HEAD_REPO`/`THIS_REPO`, never inline
* **gh:** every `python3` the managed hooks start runs with `PYTHONSAFEPATH=1`, so the top of the working tree is never on the import path and a checked-out branch's own `vibey_gh/` package is not imported and executed in place of the tool. A declared `[install] self_source` still runs, through `PYTHONPATH`. These three change the rendered hooks and `provenance.yml`: adopters see them "out of date" until they re-render with `vibey-gh install`
* **engines:** the per-cycle turn cap (`max_cycle_turns`) now counts real turns. `chatter.assistant` mapped to `TurnCompleted` next to `turn.completed`, so claudeloop and agyloop, under their default `log_chatter=summary`, parked a cycle as `budget_exhausted` at about half its configured turns. Every qwenloop `text_delta` counted as a turn as well. Chatter and stream deltas now map to a new `TranscriptRecorded` event kind, which stays in the ledger for replay but is never counted. qwenloop now writes one `turn.completed` per model call, its only event that counts as a turn, and `chatter.prompt` no longer duplicates `TurnRequested`. codexloop's `turn.failed` still counts, once, as a turn attempt. Dollars were never double counted (#266)
* **engines:** vibey read claudeloop's capacity only as a `{"state": …}` mapping, but
  claudeloop writes the class name (`"capacity": "CreditsExhausted"`), so every real
  claudeloop capacity payload classified as `Available`. Both shapes are read now, and
  `BackendMisconfigured` is terminal (`AuthenticationFailed`), never credits (#236)
* **gh:** a mention on a pull request can now reach the "act" path at all. `vibey-gh
  conversation` decided pull-request-ness from `isPullRequest`, a field `gh issue view` does
  not serve (it rejects it), so every thread read as an issue and a trusted request was
  never allowed to change a file. It is now read from the thread's `url` (`.../pull/N`), in
  one place, `ConversationThread.is_pull_request` (#145)
* **gh:** a mention in an inline pull-request review comment is the comment evaluated. Review
  comments are not in `gh issue view`'s thread, so the command silently fell back to the
  newest issue-level comment and answered that instead. The ID is now resolved through the
  pull request review API and checked against the pull request; an ID that names nothing
  fails the command with a clear message rather than answering a different comment. A review
  comment's briefing also carries the file, line and diff hunk it was written on (#145)
* **agyloop:** `agyloop run` and `agyloop resume` exit 75 (`EXIT_WIND_DOWN`) with `Wound down:` when the run wound down on purpose, instead of `Run failed:` and exit 1. vibey's BUILD handler starts the no-loss handoff only on exit 75, so an agyloop wind-down could never reach it. The mapping lives once, in `agyloop/cli/run_outcome.py` behind `cli/interfaces/`, and the runner and CLI now share one `WIND_DOWN_REASON_PREFIX`. It is inert until agyloop's bootstrap enables a wind-down policy and wires the marker and stop-summary writers (#208)
* **hooks:** a commit or push made from a linked git worktree now runs the pre-commit framework's gates. Before this fix it ran none of them and said nothing. The tracked shims `.githooks/pre-commit`, `commit-msg.local` and `pre-push.local` looked for the framework's hook at the literal `.git/hooks/<stage>`. In a worktree `.git` is a file, so that path never exists and each shim exited 0 without a word. The push went out with no test suite, mypy, import-linter, coverage gates, bandit or pip-audit. All three shims now hand over to one helper, `.githooks/framework-hook.sh`. It resolves the hook through `git rev-parse --git-common-dir`, which is where `pre-commit install` writes. `--git-path` would not work: it honours `core.hooksPath` and resolves back to `.githooks`. When the repository declares the framework but its hook for a stage is not installed, the helper warns and names that stage, and the commit or push still goes ahead. The declaring config is `VIBEY_FRAMEWORK_HOOK_CONFIG`, which defaults to `.pre-commit-config.yaml`. The helper also stops passing the `GIT_DIR` that git exports to a worktree's hooks (a plain clone's hooks get none) when it names the repository git would find anyway. The first gated push from a worktree showed why. The suite inherited that `GIT_DIR`, and `vibey.application.conformance`'s scratch `git init` rewrote the shared git config to `core.bare = true`, which broke the main checkout, while its `git commit --allow-empty` landed on the pushing branch. `tests/meta/test_githooks_reach_the_framework.py` drives the real hooks through `git commit` and `git push` from a main checkout and from a linked worktree, and reproduces that damage to prove it can no longer land (#282)
* **tests:** the chaos test counts *committed* executions (acks that returned `True`) and asserts 500 committed, none twice and none lost. It used to log every execution before the fenced ack and ignore the result, so on a loaded machine, where claim-to-ack outlives the 150 ms lease, at-least-once redelivery read as double execution. The raw count is still printed, and the lease is unchanged. `tests/infrastructure/db/conftest.py` and `tests/contracts/conftest.py` now read `VIBEY_TEST_DATABASE_URL` inside a fixture rather than at import, so `pytest tests/infrastructure/db -n 4` gives each worker its own database instead of one shared `vibey_test_main_main`. A serial run or an xdist controller now names its database per process (`vibey_test_main_<pid>_<hex>`), so parallel checkouts no longer terminate and drop each other's database (#262)
* **gh:** `vibey-gh install` no longer fails with a traceback, after writing every file, on a machine without the GitHub CLI; the secret check degrades to the notice `gh not found; skipping secret/permission checks` (#264)
* **gh:** `python -m vibey_gh` now runs the CLI; the package had no `__main__` module (#264)
* **gh:** the docs and the config comment for `[issue_automation] fallback_enabled` now give its real default, `true`: #277 turned both local fallbacks on by default under sub-doctrine 8.a and left them saying "off" (#264)
* **gh:** `vibey-gh doctor` no longer fails every repository on the starter config (`[install] workflows = ["provenance.yml"]`). The missing-gate check is an error only where `pr-automation.yml` or `merge-train.yml` is installed; a repository that declines both gets an `info` note (#264)
* **gh:** the sub-doctrine 4.a social-signals section now actually reaches the published site: `release-surfaces.yml` ran the inject step before `properdocs build` created `channel-site/`, so it injected nothing on every deploy (#264)
* **gh:** the vibey-gh docs now name the local lane's runner by its key, `[pr_automation.fallback] runner_label`, and its default `vibey-local`, instead of `vibey-local-gh`, which is only vibey-gh's own setting (#264)
* **repo:** the absorbed tenants no longer carry the standalone automation they arrived
  with (#189). 155 inert files are gone — 117 under the seven non-gh tenants' `.github/`,
  31 tenant `.githooks/` files and 7 tenant `.vibey-gh.toml` — none of which GitHub or git
  ever acted on here, and nothing in CI depended on (ADR-0022). 43 of those workflows asked
  an index for `vibey-gh==X.Y.Z`
  84 times, against ADR-0037 Decision 2; and because vibey-gh stops at the nearest
  `.vibey-gh.toml`, any `vibey-gh` command run from inside a tenant loaded that tenant's
  stale standalone config instead of the repository's. `src/vibey_tools/gh` keeps its own,
  which is drift-gated.
* **design:** a research topic the sovereign provider cannot source now parks a
  `research_evidence` human gate on its first attempt, naming the topic, the evidence
  file it wants and `VIBEY_EVIDENCE_DIR`. It used to fail as a generic error, retry six
  times with backoff, and then park an `attempts_exhausted` gate asking for more attempts
  that could never succeed. `SovereignResearchUnavailable` moved to `vibey.domain.errors`
  so the handler can catch it (#115)
* **domain:** phase timing, the measured history a time-and-cost estimator needs (#88). A
  pure projection, `PhaseTimingProjection` in `domain/phase_timing.py`, reads one project's
  ledger and reports every phase visit: the `PhaseTransitioned` that entered it and the one
  that left it, ordered by `seq`, the wall-clock time between them, and what the visit spent
  by the budget brake's own rule, now published in the domain as `LedgerSpendRule`. Visits
  roll up per `(cycle, phase)`, because a phase can be visited twice in one cycle. The
  projection predicts nothing, and it never passes a guess off as a measurement. An open
  visit has no duration. A visit whose recorded clocks run backwards is clamped to zero and
  flagged `clock_skewed`. A visit whose entry the range never saw is flagged too. Only a
  visit that is none of these counts as `measured`. Spend that no visit can own is reported
  as `unattributed` instead of being dropped. There is no turn count: engine translation
  writes more than one `TurnCompleted` per real turn, so the projection reports
  `turn_completed_events` with a caveat beside it
* **ci:** root CI now runs each workspace tenant's own static gates (#263). Until now the `tools` matrix ran only the runners' suites and coverage floors; their `mypy --strict`, `lint-imports` and `bandit` lived only in nested workflows, which GitHub never reads. A row's new `static` key runs them from the tenant's directory, against its own configuration, on its floor row: agyloop, claudeloop (on 3.10, plus its skill-frontmatter check), cursorloop, qwenloop, vibey-runners-common (a new static-only row) and vibey-bootstrap (its own pre-commit hook's mypy and `bandit -ll`). codexloop gets its own full matrix back: every gate on ubuntu and macOS, 3.12 and 3.13. A `docs` key restores the strict docs builds that agyloop, codexloop (properdocs) and vibey-skills (mkdocs, with its page-count check) ran in their own CI. `tests/meta/test_tools_matrix_covers_every_package.py` derives from each tenant's pyproject which gates it configures, and fails when no CI command runs one
* **runners-common:** `lint-imports` had never evaluated either of vibey-runners-common's contracts. `root_package = "vibey_runners.common"` is not top-level, so grimp raised NotATopLevelModule and lint-imports exited 1 before evaluating anything. It is now rooted at `vibey_runners`, and both contracts catch a planted violation (#263)
* **imports:** the `interfaces-declare-only` contract bound nothing inside `vibey.application`: `application/interfaces` could import `worker`, `job_dispatcher` or any other consumer, and the contract still reported KEPT. It now forbids `vibey.application.*`, with `design` and `dto` allowed as the vocabulary seams name. The new `tests/meta/test_import_contracts_bind.py` fails any import-linter configuration in the tree that has a dotted root, a forbidden module overlapping its source (the parent-package form that skips every pair), or a forbidden module that does not exist (#263)
* **skills:** `tools/check_links.py` checked none of the 179 repository links in vibey-skills' Markdown. It matched only `/blob/main/` and resolved paths against the skills folder, while every self-link is monorepo-relative and points at `develop`. It now matches any ref: a long-lived branch named in the root `.vibey-gh.toml` `[branches]` resolves against the repository root, and any other ref is reported rather than skipped. It is a class with an interface beside it (ADR-0016), and new unit tests cover it (#263)
* **docs:** the image contracts are named rather than counted in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `CONTRIBUTING.md`, the `vibey-quality-gates` skill in all four agent trees, ADR-0019, runbook 05 and `docs/project.mmd`. Every one of them said four; `ci.yml` has had five since #234 (#263)
* **paper:** `docs/paper.md` is now the family's one paper. It absorbs the theses of the runner, `vibey-gh`, `vibey-skills` and `vibey-bootstrap` papers (checked against the code, which had drifted from several of them) and drops the "companion paper" framing. A new section, *Production rate and governance*, states the measured regularity behind #192 — on one machine, successful throughput stayed between 0.99 and 2.00 generations per minute while offered concurrency rose sixteen-fold — as a band, not a constant or a law, with its modulators, the zero-shortfall time-to-completion it predicts, and what would falsify it. The 61-generation, `1.4 ± 0.25`/min figures it replaces matched nothing in the tracked stress record. `scripts/paper_evidence.py` recomputes every number from the record and git history, and `tests/meta/test_paper_renders.py` guards the renderer's line-at-a-time rule, which had printed three of the old paper's formulas as literal TeX ([#192](https://github.com/the-vibey-project/vibey/issues/192), [#155](https://github.com/the-vibey-project/vibey/issues/155))
* **gh:** the automation-bootstrap recovery path could never merge. It waited on six
  literal check names — `Documentation contract`, `Provenance`, `Build`, `Lint`,
  `Analyze Python`, and the parity check — five of which never report here, and `Build`,
  `Lint` and the parity check came only from vibey-gh's own hand-written workflows, so the
  emergency path failed closed for every adopter exactly when it was needed. Its scope check
  assumed the standalone layout too, and `gh pr diff` reports repository-root paths, so
  every `src/vibey_tools/gh/…` file was refused. Both are now rendered from configuration:
  the gates are `[rulesets.integration] required_checks` less
  `[pr_automation] ignored_checks` and the gate the path routes around (`["gates"]` here),
  and the scope is anchored at `[install] self_source`. Still fail-closed — an empty list,
  an absent gate or any red check refuses the merge, and the error names what is absent
  ([#214](https://github.com/the-vibey-project/vibey/issues/214))
* **briefing:** the deterministic floor brief carries every decision the no-loss gate still
  counts open. It chose decisions by the decision log's `superseded_by`, which records whether
  an id was EVER named by a supersede, whatever the order, so a decision recorded after the
  supersede naming it -- or reinstated after being superseded -- was dropped while R3, which
  reads `open_items`, still required it: the floor that is lossless by construction failed its
  own gate, so a handoff through `DeterministicBriefProducer` (the production default) spent
  its three STRICT attempts on the same brief and escalated to full-transcript mode. It now
  takes the ids from `open_items` and only the wording from the log. Found by the widened
  no-loss suite
  ([#213](https://github.com/the-vibey-project/vibey/issues/213))
* **gh:** the PR automation gate can now say "local fallback found a blocking defect". The
  `review-fallback` job counted its findings but never declared the count as a job output,
  so the gate always read an empty string and reported every local decline as "could not
  complete the review", pointing away from a finding that sat in the job log. The paid
  review job's `findings` output, declared but never written, is now written too (#133)
* **ledger:** ledger readers are forward compatible with event kinds a newer vibey wrote. Every reader parsed `event.kind` with `EventKind(...)`, a closed enum, so during a rolling upgrade or after a rollback one row of a new kind (#270's `TranscriptRecorded` is the first) raised `ValueError` in every older worker that read the project, and the fleet died one lease at a time. Now the shared `EventRowMapper` reads an unknown kind as `UnrecognizedEventKind` carrying the stored text: kept in every range, in the full ledger handed to the next engine (byte for byte what a newer vibey writes) and in `digest_range` (R6 unchanged), skipped by every projection, the gate, the budget brake and the dashboard, and never written. `vibey ledger show --kind` and `vibey ledger search --kind` match a kind they do not know exactly as written and say so on stderr; `EventKindResolver(accept_unrecognized=False)` keeps the old refusal. Must land before #270 and any other new `EventKind` member (#275)
* **domain:** forward-compatible readers for closed vocabularies across database columns. Readers of `engine_id`, `phase`, `provenance`, `job.state`, and `circuit` parse rows into enum members or `UnrecognizedValue` instances rather than crashing with `ValueError` on rows written by newer versions. Older workers keep unrecognized values in storage without mutation and skip domain projections that require known semantics, while writers remain strictly validated. Must land before #281 adds `claudeloop-local` (#287)
* **claudeloop:** `claudeloop resume` exits 75 on a deliberate wind-down, as `run` always
  has, instead of printing "Run failed" and exiting 1 — a supervisor could not tell a
  handoff from a failure without parsing text. Both commands now share one exit-status map
* **claudeloop:** `doctor` no longer fails a machine with no `claude` on `PATH`: it falls
  back to the CLI bundled inside claude-agent-sdk, which is the one the SDK launches anyway,
  and uses it for the login and MCP checks too (#121, slice S1b)
* **claudeloop:** a model the backend does not have (`model_not_found`, on any backend) now
  ends the run with exit 78 instead of re-sending the turn until the turn budget ran out
* **build:** `build.decompose` can no longer enqueue part of a plan. The fan-out used to enqueue items one transaction at a time and only noticed a forward dependency, or a cycle, on reaching it, with every earlier item already committed; a retry then asked the producer again and could orphan or duplicate them. The whole plan is now judged before anything is enqueued (`DecompositionPlanner`, which also refuses dependency cycles and names each one), a sound plan is put into dependency order instead of being refused for its listing order, and the fan-out is one transaction through the new `JobRepository.enqueue_batch`, whose requests name in-batch dependencies by idempotency key (`EnqueueRequest.depends_on_keys`). A replay after a crash mid-batch writes exactly one job per item; a replay after the commit returns the committed fan-out without asking the producer for a second plan (#265)
* **build:** a capacity rejection during `build.verify`'s diff review now defers the job as capacity instead of being discarded. `run_and_record` reported `capacity_rejected`, but the verify handler never read it and judged the run on its verdict alone — so a reviewer out of capacity either failed as `WORK` (burning an unrefunded attempt, up to the `attempts_exhausted` park, while `RotationRecordingHandler` left the exhausted engine's circuit closed and kept handing it the same job) or, with a completing verdict in the same run, approved the item outright — the non-negotiable "a capacity rejection always outranks a completion claim" broken both ways. It now returns `Defer(capacity=True)` after `capacity_backoff` (a constructor keyword defaulting to 5 minutes, exactly as on `build.implement`), before any repair finding is resolved or any independence waiver is written, and `BuildVerifyHandler` takes a required `clock` ([#215](https://github.com/the-vibey-project/vibey/issues/215))
* **cli:** `vibey cost` prints the budget caps the brake actually enforces. It read a `budget`
  table that nothing writes and printed $40.00 per cycle and $250.00 total whatever the
  project's `--max-cycle-dollars` was, and took its spend from `engine_health`, which reads
  $0. It now shows the stored `max_cycle_dollars` / `max_cycle_turns` (or `none (uncapped)` /
  `none`) through `LedgerBudgetSource.caps_from_config`, the one parser the worker's brake
  also uses, and the cycle's ledger spend (DESIGN included) from the brake's own sum. The
  lifetime cap line is gone because nothing enforces one, and the per-engine count is labelled
  `selections`, not `turns`. The shared parser also stops reading a stored `true` as a
  one-turn or one-dollar cap ([#210](https://github.com/the-vibey-project/vibey/issues/210))
* **engines:** engine health records what each engine spent and when it failed. The cost
  column that `vibey engines`, `vibey status` and the dashboard show read $0.00 forever,
  because `record_selection` took a `cost_usd` its one caller never passed. Each
  `build.implement` and `build.verify` job now writes through a per-job `SpendMeteringLedger`
  that forwards every event unchanged and sums spend by `LedgerSpendRule`, and
  `RotationRecordingHandler` charges the total to the selected engine with the new
  `EngineHealthService.record_spend` however the job ends, even if its handler raises. The
  column is BUILD-session spend and accumulates across cycles; `vibey cost` keeps the cycle
  total on the ledger and now labels the per-engine rows `BUILD sessions, all cycles`.
  Failures were half-missing too: an incomplete run's non-zero exit is now attributed by the
  adapter (`attribute`), so a runner killed or timed out (137, -9, 124) is an `ENGINE`
  failure where both handlers hard-coded `WORK`, and the new `record_failure` opens the
  circuit after 3 consecutive failures (`EngineFailurePolicy`, configurable) while setting
  `probe_next_at` (5 minutes, doubling to 30), so the engine half-opens for a probe rather
  than leaving rotation for good. `LedgerBudgetSource` now applies `LedgerSpendRule` instead
  of its own copy, and the shared rule no longer counts a `bool` as a dollar or a turn
  ([#209](https://github.com/the-vibey-project/vibey/issues/209))

### Features

* **gh:** the book is a paperback interior, not a printed web page (#162). `book-print.html`
  now mirrors its margins with the gutter on the binding side, prints a page number at the
  foot of every body page and none on the front matter, carries each chapter's title as the
  running head of its recto pages (its nav section's on the verso), opens every nav section
  with a part page, and sets justified, hyphenated text in the book's declared language with
  widows and orphans held to three lines. The contents — printed and EPUB — is grouped under
  the nav's own section headings at any depth, where it used to be one flat column that
  dropped Guides, Reference, Architecture > Decision records and Governance; chapter titles
  lose YAML quotes and markdown backticks. The EPUB gains `dc:date`, a landmarks navigation,
  `xml:lang` on every document, and a `dc:identifier` that is the same for the same book on
  every build instead of a fresh random UUID. Every physical dimension — trim, margins,
  gutter, type size, leading, font stacks — is a `vibey-gh book` flag defaulting to the
  standard KDP 6x9in interior, and the 0.5in default gutter is documented against KDP's
  page-count tiers.
* **gh:** the clean-repo survey asks its forge through a forge-neutral adapter, the second
  slice of the platform abstraction (#138). `vibey_gh.forge` names what vibey-gh talks
  about in any forge's terms (`ForgeKind`, `ForgeRepository`, `ChangeRequest`,
  `ForgeComment`, `CheckResult`, `ForgeRelease`, `ForgeLabel`, `ProtectedRef`), and
  `vibey_gh/interfaces/forge_adapter_interface.py` declares the verbs, each answering
  `(value, problem)` so a forge that could not be asked never reads as one that said
  "nothing". `vibey_gh.forge_github.GitHubForge` implements them on the `gh` transport, and
  `vibey-gh tidy` and `check --ci` now read the open pull request heads and the releases
  through it, with the same `gh` argv and working directory, which before/after tests prove
  through one fake `gh`. A new `[platform]` table chooses the adapter (`kind = "github"`,
  `host = "github.com"`): `gitlab` and `forgejo` are refused at load with "the … adapter is
  not implemented yet" rather than half-honoured, and a host other than github.com reaches
  `gh` as `GH_HOST` for GitHub Enterprise Server. The noun vocabulary is proposed in
  vibey-gh's ADR 0001 and awaits the operator's ratification
* **deploy:** the Helm chart (0.2.0) can run an in-cluster Ollama for the sovereign path. `ollama.enabled` (default `false`) adds a weights PVC, a ClusterIP Service on 11434, a single-replica `ollama/ollama:0.34.2` Deployment pinned by index digest and run as uid 10001 with its own security context, an optional `nvidia.com/gpu` limit (`ollama.gpu`), and a Job that `ollama pull`s `ollama.model` (default `qwen2.5-coder:14b`) and is named after a hash of its own pod template, so it re-pulls only when the model, image or endpoint changes. The worker gets `VIBEY_OLLAMA_URL`/`VIBEY_OLLAMA_MODEL`, `QWENLOOP_BASE_URL`/`QWENLOOP_MODEL` (with `/v1`) and, unless `ollama.qwenloopFeature=false`, `VIBEY_FEATURE_QWENLOOP=1`, all fully qualified like the DSN; `OLLAMA_CONTEXT_LENGTH` defaults to 32768 because qwenloop runs a 32K context. `worker.extraEnv` is new too. Defaults render byte-for-byte as before apart from the chart label, and a new `chart` CI job lints and diffs five profiles against goldens in `deploy/helm/golden/` (#121)
* **deploy:** the container image carries `codex`, the CLI codexloop drives, as upstream's static musl build 0.154.0: fetched in the build stage for `dpkg --print-architecture`, checked against a pinned per-architecture sha256 (plus its `LICENSE` and `NOTICE`), and copied into the runtime stage alone — no Node, no npm. The `image` job now asserts `codex --version` prints the pinned version and that `node`, `npm` and `npx` are absent (#121)
* **domain:** phase timing, the measured history a time-and-cost estimator needs (#88). A
  pure projection, `PhaseTimingProjection` in `domain/phase_timing.py`, reads one project's
  ledger and reports every phase visit: the `PhaseTransitioned` that entered it and the one
  that left it, ordered by `seq`, the wall-clock time between them, and what the visit spent
  by the budget brake's own rule, now published in the domain as `LedgerSpendRule`. Visits
  roll up per `(cycle, phase)`, because a phase can be visited twice in one cycle. The
  projection predicts nothing, and it never passes a guess off as a measurement. An open
  visit has no duration. A visit whose recorded clocks run backwards is clamped to zero and
  flagged `clock_skewed`. A visit whose entry the range never saw is flagged too. Only a
  visit that is none of these counts as `measured`. Spend that no visit can own is reported
  as `unattributed` instead of being dropped. There is no turn count: engine translation
  writes more than one `TurnCompleted` per real turn, so the projection reports
  `turn_completed_events` with a caveat beside it
* **gh:** the fit calculus reads a model the runner holds but has not loaded (via
  `/api/tags` and `/api/show`) instead of calling it the floor, reads the runner that
  `--base-url` or `VIBEY_OLLAMA_URL` names instead of always 127.0.0.1, and journals to
  `~/.local/state/vibey-gh/fit.jsonl` by default (`VIBEY_GH_FIT_JOURNAL`, `--journal`,
  `--no-journal`). Both local-model calls now size their context window through one
  `ContextSizer`, with unchanged windows. These are prerequisites for wiring the fit loop
  into live Ollama calls; swap actuation stays refused by design (#135)
* **build:** a capacity rejection during `build.verify`'s diff review now defers the job as capacity instead of being discarded. `run_and_record` reported `capacity_rejected`, but the verify handler never read it and judged the run on its verdict alone — so a reviewer out of capacity either failed as `WORK` (burning an unrefunded attempt, up to the `attempts_exhausted` park, while `RotationRecordingHandler` left the exhausted engine's circuit closed and kept handing it the same job) or, with a completing verdict in the same run, approved the item outright — the non-negotiable "a capacity rejection always outranks a completion claim" broken both ways. It now returns `Defer(capacity=True)` after `capacity_backoff` (a constructor keyword defaulting to 5 minutes, exactly as on `build.implement`), before any repair finding is resolved or any independence waiver is written, and `BuildVerifyHandler` takes a required `clock` ([#215](https://github.com/the-vibey-project/vibey/issues/215))
* **build:** gate commands now run isolated and bounded. `SubprocessGateRunner` — which runs `build.verify`'s gates and `git diff`, `build.integrate`'s gates and REVIEW's automated checks — handed every command vibey's whole environment minus `GIT_*`, let it inherit the worker's stdin, and waited on `communicate()` with no timeout, so one hung gate held its job's lease for as long as it hung while the heartbeat kept renewing it. Each command now leads a process group of its own and gets `gates.timeout_seconds` (default 1800); one that overruns is killed with its whole group and fails as exit 124, a failing gate for the repair loop rather than an error. A cancelled run (Ctrl-C, event-loop shutdown) kills and reaps its gate before the cancellation propagates, and the reap itself is bounded by `gates.kill_grace_seconds` (default 5), because asyncio's `wait()` never returns while a descendant that escaped the group still holds the pipes. stdin is `/dev/null`, and output that is not UTF-8 is decoded with replacement characters instead of raising. vibey's own Python environment (`VIRTUAL_ENV`, `PYTHONPATH`, `PYTHONHOME`, its venv's `bin` on `PATH`) is stripped with the same `isolate_python_env` engine sessions use, and the running interpreter's prefix counts as a venv only when it is one, so a system-Python install keeps `/usr/bin`. **Behaviour change:** a gate that found a tool only because it was installed beside vibey — the `ruff`, `bandit` or `pytest` of a development checkout's venv, REVIEW's default `ruff check .` included — no longer finds it and fails with exit 127. Install the tool where the project can reach it, or set `gates.isolate_python_env` to `false` in the project's config record. The worker builds one runner from the project's `gates` object, and a malformed one raises when the worker is built ([#212](https://github.com/the-vibey-project/vibey/issues/212))
* **infra:** every subprocess vibey kills is now killed with its whole process group and reaped within a bound, by one implementation, `infrastructure/process/reaper.py`'s `ProcessReaper`, which #212's gate runner, the loop-process adapter and the skills-context compiler all use (ADR-0017). The adapter's preflight probes (`<engine> --version`, `<engine> doctor`) and the `vibey-skills` CLI used to kill only the direct child and then wait on it with no bound. On CPython 3.12 that wait does not return while a descendant that escaped into a session of its own still holds the pipes, so a probe or a skills compile with such a descendant hung preflight or the BUILD job for as long as the descendant lived. Measured on 3.12.13: a 0.2 s timeout returned after 5.5 s and 6.0 s, when the escaped `sleep 6` exited. Both now start their child in a session of its own. On a timeout or a cancellation, `SIGKILL` goes to the whole group (ESRCH and macOS's EPERM for a zombie-only group are tolerated), and the reap gives up after a grace, logging `engine_process_not_reaped` (with the engine) or `skills_context_process_not_reaped`. The grace is `skills_context.kill_grace_seconds` (default 5, also declared in the `VibeyProject` CRD's `skillsContext`) and `LoopProcessAdapter.kill_grace_seconds` (default 5; the adapter is built without project config). The engine spawn also stripped `/usr/bin` and `/usr/local/bin` from every engine session on a system Python, because it always treated `sys.prefix` as a venv. It now asks the same `OrchestratorPythonEnv` the gate runner does, which counts the interpreter's prefix only when `sys.prefix != sys.base_prefix`. Gate behaviour, `gates.kill_grace_seconds` and `gate_process_not_reaped` are unchanged ([#283](https://github.com/the-vibey-project/vibey/issues/283))
* **engines:** local engines are preferred first (sub-doctrine 8.a). A new engine,
  `claudeloop-local` — the claudeloop binary on a local backend profile
  (`--profile NAME --preset …`, never `--effort`; cost 0/0; honest ceiling STANDARD) —
  joins `qwenloop` in a LOCAL tier behind `VIBEY_FEATURE_CLAUDELOOP_LOCAL` /
  `[features] claudeloop_local`, configured by `[engines.claudeloop_local]` (`profile`
  default `local`, overridable by `VIBEY_CLAUDELOOP_LOCAL_PROFILE`; `context_window`;
  `structured_verdict`, off until conformance proves it). BUILD selection runs SWRR within
  the LOCAL tier and falls back to paid engines only when no local engine is eligible,
  replacing qwenloop's standby filter; verify still rotates away from the implementer. With
  a local engine on and no `--provider`, `vibey work` and `vibey worker` run DESIGN and
  DECOMPOSE on the sovereign providers. Selection is confined to the worker's own pool,
  so a local engine's health row left over from before its switch was turned off can
  never be preferred over the engines the worker can actually run. `VIBEY_OLLAMA_URL` is the one local endpoint
  setting: qwenloop's process now gets `QWENLOOP_BASE_URL=<url>/v1` and `QWENLOOP_MODEL`
  from it through a new `LoopProcessAdapter.env_overlay`. One resolver,
  `LocalEngineSettings`, answers "which local engines are on" for bootstrap, `worker`,
  `work` and `doctor`. New guide: [Local models on Ollama](docs/guides/local-models-ollama.md)
  ([ADR-0038](docs/architecture/decisions/0038-local-engines-are-preferred-first.md);
  #236, #115)
* **engines:** a run that exits 78 (claudeloop's `BackendMisconfigured`: an unreachable
  local server, a model not pulled or failing to load, a context too small) parks its
  `build.implement` or `build.verify` job on an `engine_misconfigured` gate naming the
  engine's `doctor` command, instead of burning its retry ladder on a configuration
  fault (#236)
* **helm:** the `VibeyProject` CRD's `engines` enum accepts `qwenloop` and
  `claudeloop-local`
* **qwenloop:** qwenloop can now attach to an OpenAI-compatible server that is already running, with Ollama as the main target, instead of spawning llama-server or vllm, so the BUILD lane can run for free on an operator's existing Ollama. Before this change, `qwenloop doctor` exited 1 whenever llama-server and vllm were both missing, and vibey reads that exit as an auth failure, so qwenloop could never be selected on a machine that had only Ollama. Set `QWENLOOP_BASE_URL=http://127.0.0.1:11434/v1` (or pass `--base-url`, or set `base_url` in qwenloop's new TOML config file) and `auto` selects the new `openai-compat` backend. The model name is set explicitly (`QWENLOOP_MODEL`, `--model`, or `model`; the default is `qwen2.5-coder:14b`), and an optional API key is read only from `QWENLOOP_API_KEY`. `doctor` exits 0 only when the endpoint answers and serves the model, and says which check failed otherwise. `run`, `run --storm`, `server start`, and `server status` all use the same backend. qwenloop never starts or stops an attached server, and prints its API key as `<redacted>`. One more fix: vLLM is now launched with `--served-model-name`, so the model name each request sends is one vLLM actually serves ([qwenloop ADR 0003](src/vibey_runners/qwen/docs/architecture/decisions/0003-attach-openai-compatible-endpoint.md))
* **design:** sovereign DECOMPOSE — `vibey worker --provider qwenloop` now plans BUILD on
  the local model (`QwenloopWorkPlanProducer`) instead of the scripted test fake, whose
  items carried no verification commands. The plan is decoded under a JSON schema whose
  criterion ids are an enum of the spec's own, every item must carry a verification
  command and a checked criterion, dependencies must precede their dependents, and a plan
  that breaks any rule is refused whole rather than partly enqueued. Decoders are shared
  with the claudeloop producer (`design_json.WorkPlanDecoder`) (#115)
* **design:** one configurable Ollama client for both sovereign providers —
  `VIBEY_OLLAMA_URL` (default `http://127.0.0.1:11434`, `http`/`https` only),
  `VIBEY_OLLAMA_MODEL` (default `qwen2.5-coder:14b`, overridden by `--ollama-model` on
  `vibey work` and `vibey worker`) and `VIBEY_OLLAMA_TIMEOUT` (default 900 s) replace
  values that were hard-coded in the DESIGN provider (#115)
* **noloss:** the no-loss property suite runs the 10,000 adversarial examples the definition
  of done asks for, and they are adversarial. It ran Hypothesis' default 100 over a space of
  256 ledgers (four counts from 0..3, sequential ids, every kind contiguous), so a larger
  `max_examples` alone would have stopped at the space's edge; its adversarial check was four
  `parametrize` cases; and its expected brief came from the same `open_items` the gate uses,
  so it graded the gate with the gate's own answer key. The ledgers now have arbitrary ids
  from one shared pool, every kind interleaved, answers, resolutions and supersedes, several
  verdicts, and a presentation order unrelated to seq; the expectation comes from an
  independent reference model (`tests/domain/test_noloss_reference.py`); and the adversarial
  property drops a random subset of what the brief owes and requires every dropped item named
  under its own rule, and nothing else. A `noloss` Hypothesis profile (10,000 examples, no
  deadline) and marker drive the new required CI check `No-loss property suite (10,000
  examples)` on both branches, which prints Hypothesis' statistics on every run
  ([#213](https://github.com/the-vibey-project/vibey/issues/213))
* **governance:** the protected tests are protected by something. The no-loss suite, the
  chaos test, the full-cycle system test and `tests/live/` were guarded only by a refusal in
  the dormant `scripts/fleet/land.sh`, which targets repositories that no longer exist. A
  root `.github/CODEOWNERS` now owns them (and itself), both rulesets set
  `require_code_owner_review = true`, and `[merge_train] protected_paths` makes the merge
  train refuse such a pull request as "needs a human merge" before its `--admin` fallback
  could bypass that review; `tests/meta/test_protected_paths_agree.py` keeps the two lists
  identical. The ruleset keys take effect on the operator's next `vibey-gh reconcile`
  ([#213](https://github.com/the-vibey-project/vibey/issues/213))
* **gh:** the exact-head review's `--json-schema` is rendered from
  `ReviewContract.json_schema()` instead of hand-written in `pr-automation.yml`, so the
  schema the paid reviewer answers and the diff-groundable / wider-context split the local
  lane uses are one table. The rendered schema is byte-identical to the literal it replaces;
  this is groundwork for putting the sovereign lane first on the half it can carry (#133,
  slice 1 of 3)
* **gh:** the sovereign review lane now goes FIRST on the half of the review it can carry
  (sub-doctrine 8.a, #133). With a fresh heartbeat, `review-sovereign` (formerly
  `review-fallback`) reviews the exact-head diff on the operator's own runner before the
  paid review; for a trusted same-repository author its verdict carries `pass`, `summary`
  and `findings`, and the paid reviewer is handed only the sixteen documentation-contract
  judgments plus its own `wider_summary` / `wider_findings`. `vibey-gh pr-automation
  combine` composes the one verdict the gate reads, recording which lane carried each field,
  and replaces the `jq` that listed the sixteen judgments by name; the gate names the lane
  behind each half. A local finding never triggers automated repair. With no heartbeat the
  workflow behaves exactly as before, and with no API credit exactly as the local fallback
  did — both pinned by a golden capture of the previous gate. `local-review` gains
  `--role sovereign|fallback` (#133, slice 2 of 3)
* **claudeloop:** backend profiles — run claudeloop for free against Ollama, or any server
  that speaks the Anthropic Messages API, with `--profile NAME` / `CLAUDELOOP_PROFILE` and a
  `[profiles.NAME]` table carrying `base_url` and three model tiers. Claude Code still runs
  the agent loop; only the model behind it moves. A local profile blanks
  `ANTHROPIC_API_KEY` so a paid key never leaves the machine, refuses `claude-*` model ids
  and web search / deep research (neither exists there), records every turn at $0 — Claude
  Code prices a model it does not recognise at its default model's rate, a live run showed
  $0.0008365 for one free `qwen2.5-coder:1.5b` turn, and that guess used to reach
  `--max-budget-usd`, the 80% budget downgrade and the supervisor's brake — while keeping
  token counts, and applies the same environment to the capacity probe, which otherwise
  still asked Anthropic. Run meta records the backend, and `resume` refuses a session last
  run on another one. A backend that cannot serve the run — unreachable, model not pulled,
  model failed to load, context window too small for Claude Code's prompt — is a new
  terminal `BackendMisconfigured` capacity state that exits
  78 instead of being read as `Available` and re-sent turn after turn; a full local queue
  (HTTP 503) waits as `WindowExhausted(rate_limit_type="local")`. `claudeloop doctor
  --profile NAME` checks the token, that the endpoint answers, that every model the
  profile names is present, and that each tier makes real tool calls — the live smoke run
  found `qwen2.5-coder:14b` on Ollama writing its tool calls as text, typing the done
  marker, and "completing" a task it never did, so a local profile also turns off the
  done-marker fallback (`done_marker_fallback = false`): only a structured verdict ends a
  local run ([local backend guide](src/vibey_runners/claude/docs/guides/local-backend.md), #236)
* **gh:** `vibey-gh estimate --operation STAGE [--from STAGE] [--json]`, the first slice of
  the feasibility engine (#134). It judges the paper's six-materials state vector at every
  stage a run must pass. That vector has eighteen coordinates, each a value on 0..1 where
  1 is peak, or `unknown`, and each carries its source and measurement time. Feasibility
  is three-valued: a measured shortfall anywhere on the path is `no`, and an unmeasured
  coordinate can never produce `yes`. Agency shortfalls are listed first. The nine
  default stages, install through main-validation, and their requirement vectors are
  data that the new `[estimate]` section can replace. The fit calculus measures hardware
  and software availability, and the other sixteen coordinates are reported as `unknown`,
  which lowers the reported confidence. The local model's service time is projected from
  the fit journal. The stages' duration, the cost and the repair gradient are reported as
  `unknown`, each with its reason. The command is offline by default and exits 0, 1 or 3
  for yes, no or unknown. It is a capability on all five surfaces
* **gh:** one graded estimator, `vibey_gh.estimation` (#88, #134). The fit calculus's
  least squares now lives there, behind `GradedEstimatorInterface`: observations go in,
  and a prediction comes out with its basis and `n`, which can then be graded against
  the actual result. `fit.estimate_from` wraps it, and 400 randomized cases confirm its
  constants are identical to before. `vibey_gh` now ships `py.typed`, so `src/vibey` can
  import it under `mypy --strict`. That makes it ready for the vibey-side forecast, which
  is the follow-up that will combine it with `PhaseTiming`
* **ledger:** `vibey ledger export PROJECT --out FILE` publishes a project's ledger as a
  shard the repository commits, and `vibey ledger site --from FILE --out DIR --json-only`
  builds its static JSON surface with no database: `records/<event_id>.json`, an
  `index.json` for client-side search (id, seq, kind, phase, actor, time, digest, tokens)
  and a `manifest.json` (seq range, `digest_range`, the ledger's chain head, `holds`,
  `tier`, and every withheld count). What is published is a read-time projection through
  a default-deny policy (`domain/publication_policy.py`): allowlisted kinds and fields
  only, engine chatter and `untrusted` events withheld whole, absolute paths and email
  addresses stripped, `repo_path` never published, credential redaction last — and every
  event, field, path, address and credential withheld is counted, never silently dropped.
  Site output is deterministic and HTML-inert. See
  [What gets published](docs/guides/ledger-publication.md). Slices S3 and S4 of
  sub-doctrine 7.a, the searchable ledger (#137)
* **ledger:** `vibey ledger search` finds ledger records by record id (`--id`), payload digest
  (`--digest`, which names a payload, so it can match several records), actor (`--actor`: an
  engine id, a provenance, or `vibey` for events vibey wrote itself), time window
  (`--since`/`--until`, half-open, ISO-8601), any of several kinds (repeatable `--kind`), and
  literal case-insensitive text in the payload (`--text`), scoped to one project. Every
  criterion and the `--limit` run in SQL as one parameterised statement — nothing typed reaches
  the SQL text — and the result says when older matches were cut; `--json` prints every field
  of every event. Migration 0012 adds the digest, production-time and per-engine indexes the
  search reads. The first slice of sub-doctrine 7.a, the searchable ledger (#137)
* **ledger:** the ledger has a hash chain, derived from the rows rather than stored beside them
  (`domain/ledger_chain.py`). Each event's link is the SHA-256 of the previous link and every
  stored field of the event, from a per-project genesis; `verify` walks a whole ledger or a
  window from a trusted link, recomputes each payload's digest, and reports every gap,
  duplicate, foreign event, digest mismatch and disagreeing anchor rather than the first one.
  A window verifies alone from the link before it, which is what the storage tiers' chunk
  hashes will fold over (#114, #137)

### Code Refactoring

* **gh:** one transport for every `gh` call vibey-gh makes, beginning with the shared
  marker-comment state. `vibey_gh.gh_transport.GhTransport`, declared by
  `vibey_gh/interfaces/gh_transport_interface.py`, gives the three answers the package's
  seven private `gh` runners already give — raise, report success as a boolean, or return
  a problem string — each byte-identical to the runner it replaces. `github_state` now
  rides on it, and with it every forge call that conversation, PR and issue automation,
  reconcile, rulesets and flatten make through `github_state`; before/after tests driving
  the old code and the new through the same fake `gh` on PATH show the same argv, working
  directory and outcome, so GitHub sees no difference. The first slice of the platform
  abstraction (#138), which the forge snapshot (#136) and capture (#145) build on

## [0.8.0] (2026-09-16)

### Features

* **ci:** `develop` admits changes through a declared merge queue, and CI answers `merge_group` events so the queue can see its own checks. A pull request whose checks passed against an older base proves only that combination was green; nothing between that base and `develop`'s tip was ever built with it, and `strict_required_status_checks_policy` buys that proof by hand, one rebase at a time, with the base moving underneath. The queue is declared in `.vibey-gh.toml` rather than clicked, so it can be reviewed and restored like any other branch rule, and it is off by default for everyone else ([ADR-0036](docs/architecture/decisions/0036-the-merge-queue-is-declared-not-clicked.md))

### Bug Fixes

* **worker:** every composed worker logs through the structured logger, so a sensitive field is still redactable. `application.observability.StandardLibraryLogger` renders fields into the message as `key=value` before any sink sees them, and `configure_logging` redacts by **field name** — so a value sensitive only because of its key survives flattening (`{'event': 'job.deferred password=hunter2'}` passes through untouched, where `{'event': 'job.deferred', 'password': 'hunter2'}` becomes `[REDACTED]`). That logger exists as a last resort because `application/` may not import `infrastructure/`, and its own docstring says a composition root should inject the real one — but all three `WorkerLoop` builders in `bootstrap.py` constructed it without a logger, making the flattening default the production path for every worker, including the defer line that logs `reason=outcome.detail`, free text a handler controls. `bootstrap` now injects `StructlogAppLogger`, a test asserts every construction keeps doing so (verified to fail when one injection is removed), and the limitation is recorded at the default's definition rather than left to be rediscovered
* **cli:** releasing the SIGTERM latch no longer destroys the worker's drain handler. `cli/main.py` installs the drain handler with `asyncio.add_signal_handler(SIGTERM, ...)` and then calls `SIGTERM_LATCH.release()`, which ran an unconditional `signal.signal(SIGTERM, SIG_DFL)` — overwriting the handler installed twelve lines earlier, so a worker pod sent SIGTERM died where it stood instead of draining: exactly the Kubernetes scale-in failure the latch exists to make survivable, caused by the line meant to clean up after it. The docstring carried the premise that hid it — *"the real handler replaces this one"* — when the ordering is the reverse. `release()` now restores the default only while the latch's own handler is still installed, compared against the object `arm()` actually handed to `signal.signal`; an identity check against `self._remember` cannot work, because a bound method is rebuilt on every attribute access. It read as a flake because `arm()` runs once per process at import, so in a full suite whichever worker test ran first spent the latch and `release()` became a no-op for every later one — `test_worker_drains_on_sigterm_rather_than_claiming_more` failed only in isolation or when xdist scheduled it first, and then as `worker 'gw0' crashed` rather than an assertion, because SIG_DFL terminates ([ADR-0026](docs/architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md))
* **worker:** a deferring worker says why -- one `job.deferred` log line per deferral naming the job kind, the work item, the reason and the retry time, so a job that can never make progress no longer looks like an idle worker. The line is written after the queue transition, never before: a worker whose lease expired mid-handler has deferred nothing, and it says `job.defer_rejected` at warning instead of claiming a `retry_at` the job never took
* **ci:** a commit made in the GitHub web UI is checked on push, not at merge. The pre-commit hook enforces the Conventional subject and the `Made-With:` trailer, but a web-UI commit never runs a hook, so those landed unchecked and only `Provenance` caught them — at merge time, when a history rewrite and a force-push were the only remedy. Four commits across #171–#174 arrived that way in a single day. The `Conventional Commits` workflow now runs on every pull request push and normalises a nonconforming subject while the branch is still the author's own; it refuses to rewrite a branch carrying merge commits and fails loudly there instead, because an automatic rewrite of somebody's merge is not a tidy-up. `"Conventional Commits"` joins `[pr_automation] scan_workflows` in the same change: that list renders into `pr-automation.yml`'s `workflow_run` trigger, and a gating workflow missing from it completes without announcing anything, which is how a pull request ends up blocked with every check green and nothing to rerun
* **worker:** a job that burns its last attempt parks on an `attempts_exhausted` human gate carrying the grant to type, instead of dying as a `failed` row nobody was told about; answering `--raw '{"max_attempts": N}'` widens the bound on the job row so the granted retries survive the next nack (ADR-0024)
* **gh:** the exported book opens: chapter markup is rewritten as well-formed XHTML with
  mkdocs' `&para;` permalinks and other named entities resolved, site chrome dropped, and
  SVG's camelCase names preserved — what counts as chrome and which names are
  case-sensitive are constructor arguments, not policy ([#162](https://github.com/the-vibey-project/vibey/issues/162))
* **worker:** `vibey worker --engines <list>` that matches none of the worker's engines — `--engines qwenloop` without `VIBEY_FEATURE_QWENLOOP`, say — is refused at startup with the reason and the switch that fixes it, instead of starting a worker with no engine adapters that deferred every engine-driven job forever, silently. With the feature on, `qwenloop` now joins the startup preflight sweep, so its conformance warning appears like every other engine's.
* **codexloop:** adopt the OpenAI SDK 3.14.1 surface deliberately, and bound the dependency so it cannot drift again. `openai>=1.40` had no upper bound, so CI installed 3.14.1 while `api_baseline.json` was frozen at 3.0.0's 320 methods; the drift gate fired correctly on 374 and turned every open pull request in the repository red over 54 endpoints nobody here had touched. The floor was also already a fiction — an install at 1.40 could never have matched a 3.0.0 baseline. The dependency is now PINNED at `==3.14.1`, not merely bounded: the gate compares the exact method set and OpenAI adds endpoints within a major — 3.11.0 to 3.14.1 added 54 — so a range only moves the next unplanned breakage a few releases out. The pin and the baseline are one fact in two files and advance together. The added surface is purely additive (43 `beta.agents.*`, 10 `live.*`, 1 `safety.alerts.*`; nothing removed, local helpers unchanged), so no `codexloop api` command disappears. `tools/refresh_api_baseline.py` replaces the `pytest --update-baseline` flag the skills documented and which never existed: it prints the delta, refuses a no-op, and is named on all four agent surfaces
* **build:** a one-engine pool (`vibey work --engines qwenloop`) can verify its own work instead of stalling BUILD forever. The `build.verify` independence rule excluded the implementer unconditionally, so a single-engine pool had nothing eligible left, `NoEligibleEngine` became a capacity defer, and the job retried with no park and nothing in the ledger. The exclusion is now waived only when honoring it would leave the configured pool with no reviewer at all, and the waiver is written to the ledger as a decision and to the job result as `independent_review: false` — a non-independent diff review is allowed there, never hidden. With two or more usable engines the rule is unchanged. The waiver decision is written only once the item really passed verification — the ledger is append-only, so a failing gate must not leave behind an entry saying the item was verified — and `verify.require_independent_review = true` in the project config restores the strict rule for projects that would rather stall than accept a self-review ([ADR-0035](docs/architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
* **design:** the ledger names the engine that actually did the DESIGN work. `design.interview` and
  `design.research` events were attributed to claudeloop whatever `--provider` was in force, so a
  sovereign run on qwenloop -- and a scripted run with no engine at all -- wrote a false actor into
  an append-only record. Each `DesignProvider` now declares its own `engine_id` (`None` for the
  scripted one) and the composition root reads it; the `design.synthesize` exclusion follows the
  same derived value ([#115](https://github.com/the-vibey-project/vibey/issues/115))
* **ledger:** every phase move now writes the `PhaseTransitioned` event the ledger always declared,
  in the same transaction as the compare-and-set that moves the phase — so a project's path through
  the six phases is reconstructable from its own history, and no move can commit without its event

### Features

* one correlation id per delivery: every ledger event of a project's DESIGN, BUILD and REVIEW phases now carries the same `correlation_id`, derived from the project alone so a REVIEW loop-back does not mint a second one, instead of a fresh `uuid4()` per write site. Per-run identity moves to the `causation_id` column, which already existed and was always empty, so individual engine runs stay distinguishable. The id is also bindable into the structured log context under a configurable key ([#89](https://github.com/the-vibey-project/vibey/issues/89))
* **cli:** `vibey recover` reports how many jobs it actually put back — the status-string pattern carried a doubled backslash, so the count was always `0`
* **cli:** the next-step hints after `EscalationExhausted`, `HandoffRejected` and `BudgetExceeded` name commands that exist — they pointed at a `vibey gates` command that has never existed, and at a `[budget]` table nothing reads
* **review:** REVIEW no longer runs a hard-coded security scan. `bandit -q -r src` walked the
  absorbed workspace members and failed every cycle, looping REVIEW back into BUILD forever; no
  narrower path is right for anyone else either, because `bandit` exits 0 on a path that does not
  exist, so a baked-in default would report a passing security check that examined zero files.
  Both the security and code-review command lists are now project configuration
  (`review.security_commands`, `review.code_review_commands`), and `security_commands` defaults to
  empty — a project that wants the check configures it
### Documentation
* stop tracking the two built documentation sites (`site/` and `src/vibey_tools/gh/site/`): 5.8 MB of stale rendered HTML — a second, drifting copy of the docs, the ADRs and the runbooks — that `properdocs build` regenerates and that CI never reads ([#155](https://github.com/the-vibey-project/vibey/issues/155))

* **rotation:** an engine that ran out of credits is probed again once its backoff elapses, instead of being excluded for the rest of the project until someone edited `engine_health` by hand; the selector now half-opens on `probe_next_at` as well as `resets_at`. An engine opened by `AuthenticationFailed` still gets no clock-based probe -- waiting cannot fix a credential -- but a preflight whose auth succeeds half-opens it, so re-authenticating is enough to bring it back.

## [0.7.0] (2026-09-15)

### Features

* **gh:** the book and the research paper linked from every page's navigation and footer, the channel chooser and `llms.txt`, and attached to each GitHub Release; this repository adopts `github-release.yml` ([#147](https://github.com/the-vibey-project/vibey/issues/147)) ([c696374a](https://github.com/the-vibey-project/vibey/commit/c696374a51a2c08f82d7c53f1f1fe1ecda55b22b))
* absorb vibey-gh, vibey-skills and vibey-bootstrap into `src/vibey_tools/` with history preserved ([#140](https://github.com/the-vibey-project/vibey/issues/140)) ([ef52670b](https://github.com/the-vibey-project/vibey/commit/ef52670b3da873e471806596dc7e9c5b92f89ef5)) — imports [ce6c2cce](https://github.com/the-vibey-project/vibey/commit/ce6c2cce571c7fc29c90a25d7bff56e52b9bab1c) (vibey-gh), [bc424175](https://github.com/the-vibey-project/vibey/commit/bc42417511a52d0c35af26808656ba25c5649a18) (vibey-skills), [b49108d5](https://github.com/the-vibey-project/vibey/commit/b49108d534946b7fd7c7d81303013514f0ddbdff) (vibey-bootstrap)
* **workspace:** register `src/vibey_tools/*` as uv workspace members and resolve the tools from the tree ([4e55a60e](https://github.com/the-vibey-project/vibey/commit/4e55a60e9007c6b98f6f05777d838d9b0eac2d7c))
* **build:** let the image build vibey-skills from the tree, and stop shipping the subtrees ([8cbdb7b4](https://github.com/the-vibey-project/vibey/commit/8cbdb7b44bbc96e9918dfd8bd8d40f768da8c22e))

* **gh:** governance published on every docs page and in the book; LaTeX rendered on the site from a self-served, checksum-verified MathJax ([#158](https://github.com/the-vibey-project/vibey/issues/158)) ([df68a084](https://github.com/the-vibey-project/vibey/commit/df68a084d1c33a730268f4e947c5d76d7b0dd1d8))
### Bug Fixes

* **gh:** review, repair and conflict jobs load plugins from a configured marketplace (this repository's own `src/vibey_tools/skills`) instead of a deleted repository ([#149](https://github.com/the-vibey-project/vibey/issues/149)) ([7a5b3b9c](https://github.com/the-vibey-project/vibey/commit/7a5b3b9c4c4631023020668b1e62e7bec61e68f4))
* **gh:** a manual GitHub Release must prove its commit is on the release branch with a successful release run, and never executes the target's code ([#147](https://github.com/the-vibey-project/vibey/issues/147)) ([98f1c81b](https://github.com/the-vibey-project/vibey/commit/98f1c81b3d076164c04c1f420bddb8aa7dab81ed))
* **gh:** list the print HTML book in `llms.txt` ([#147](https://github.com/the-vibey-project/vibey/issues/147)) ([683e48d8](https://github.com/the-vibey-project/vibey/commit/683e48d869331993f3c4bc888a5e322df326c85b))
* **worker:** register the SIGTERM handler before any I/O ([2e8e48ad](https://github.com/the-vibey-project/vibey/commit/2e8e48adc39a9c14741e906dd8a6a6e99fc228d2))
* **worker:** a SIGTERM that arrives during startup is no longer thrown away ([44c1c21a](https://github.com/the-vibey-project/vibey/commit/44c1c21a3924ed3275eb0d5fb83f69c442515364))
* **deploy:** tini is PID 1, because a Python process cannot win this race ([5ab84605](https://github.com/the-vibey-project/vibey/commit/5ab84605269a2d621df7e90abf81b7e3727d6ebe))
* **security:** the tooling is a declared path, never a search — and gate the absorbed suites ([7be8227d](https://github.com/the-vibey-project/vibey/commit/7be8227db595375312ab402d4a61e55a728b5a4e))
* **build:** my own .dockerignore excluded a package, and add the guard that catches it ([64ca4562](https://github.com/the-vibey-project/vibey/commit/64ca4562c849108cd0e1d3ad692a086bc45881df))
* ship the `vibey_bootstrap.gh` compatibility shim, and settle on one formatter ([8d468d1d](https://github.com/the-vibey-project/vibey/commit/8d468d1d99b059b850c5c895ea9fe8879ede71e7))
* regenerate uv.lock for the v0.6.0 version bump ([711181ae](https://github.com/the-vibey-project/vibey/commit/711181ae30cfcfd6a9ea634b86607a96cb852625))

* **release:** install uv where the version is stamped, so develop and promotions publish ([#160](https://github.com/the-vibey-project/vibey/issues/160)) ([2f2185a4](https://github.com/the-vibey-project/vibey/commit/2f2185a49290e220ece4135442e47842c6db49be))
### Documentation

* ADR-0016 — code lives in classes, and every class has an interface beside it ([3468bb51](https://github.com/the-vibey-project/vibey/commit/3468bb51944d7840d266a1150846bb587040edc6))
* ADR-0017 — if the family already does it, the family does it here ([15959d87](https://github.com/the-vibey-project/vibey/commit/15959d87dd750c9e2fc4e31d16bc1dc447332bef))
* ADR-0018 — if it can be declared in the repository, it is declared there ([9a819524](https://github.com/the-vibey-project/vibey/commit/9a819524d0bd5f0534038dfb1c82da3c019d1990))
* ADR-0019 — vibey is installable wherever its users already are ([#141](https://github.com/the-vibey-project/vibey/issues/141)) ([16d9adad](https://github.com/the-vibey-project/vibey/commit/16d9adad2ed506d840340820e03c2c6de072d292))
* ADR-0020 — a governing rule belongs in the canon, ratified, or it is not a rule ([#142](https://github.com/the-vibey-project/vibey/issues/142)) ([718e8980](https://github.com/the-vibey-project/vibey/commit/718e8980da52092ce019bd11f59e8bb1da1cf6ab))
* file 12.b, because ADR-0020 was exempting itself from its own rule ([573804b7](https://github.com/the-vibey-project/vibey/commit/573804b790afc646dcd6587421f2bfa275b06498))

* build out every ADR: 0015 rebuilt, 0021–0033 recorded, 0001–0020 brought up to the code ([#159](https://github.com/the-vibey-project/vibey/issues/159)) ([7cf33920](https://github.com/the-vibey-project/vibey/commit/7cf339201597969facd0137fc66f2da30413d2e9))
* the book and the paper everywhere a reader looks; changelog, contributor docs and paper brought up to date ([#156](https://github.com/the-vibey-project/vibey/issues/156)) ([04766b44](https://github.com/the-vibey-project/vibey/commit/04766b4473dc21100a779497c1be3fc400dfc7b1))
* **canon:** sub-doctrines 9.b, 10.e, 12.c, 2.b and 7.b ratified; 12.b cites Article II.3 ([#150](https://github.com/the-vibey-project/vibey/issues/150)) ([b8038420](https://github.com/the-vibey-project/vibey/commit/b80384202adb61b8b92ae455080b7fb7a46c0f00)) ([#151](https://github.com/the-vibey-project/vibey/issues/151)) ([fbc4de65](https://github.com/the-vibey-project/vibey/commit/fbc4de655d9a53204d3940ce9dbcbc83fa697382)) ([#152](https://github.com/the-vibey-project/vibey/issues/152)) ([5a35d9ac](https://github.com/the-vibey-project/vibey/commit/5a35d9aca5a7321951a751b80bedf05a3f1cd348)) ([#153](https://github.com/the-vibey-project/vibey/issues/153)) ([3be10eb6](https://github.com/the-vibey-project/vibey/commit/3be10eb63f2ea77e4a7925624015a2b1a3d2204f)) ([#154](https://github.com/the-vibey-project/vibey/issues/154)) ([2bab0f9f](https://github.com/the-vibey-project/vibey/commit/2bab0f9f37c554c04e7f9d10343e573c760ad1a6)) ([#157](https://github.com/the-vibey-project/vibey/issues/157)) ([061adf5d](https://github.com/the-vibey-project/vibey/commit/061adf5dfb97e7951476be0a9d040a88bbe3224f))
### Miscellaneous Chores

* repoint provenance and every family URL at the-vibey-project ([8ac15815](https://github.com/the-vibey-project/vibey/commit/8ac15815a7a47042cd6872cc6fe3d84a5eb2b043)); repo_name and vibey-skills marketplace instructions updated to match ([1d38ff12](https://github.com/the-vibey-project/vibey/commit/1d38ff1238666e38e56ee75f425aa3469986037e) and siblings)
* **deps:** bump astral-sh/setup-uv from 3 to 7 ([#129](https://github.com/the-vibey-project/vibey/issues/129)) ([0b406f46](https://github.com/the-vibey-project/vibey/commit/0b406f46b44addbb061428c99a400e5fb66ca898))
* **deps:** bump azure/setup-helm from 4 to 5 ([#128](https://github.com/the-vibey-project/vibey/issues/128)) ([1f23cd52](https://github.com/the-vibey-project/vibey/commit/1f23cd52a0cfceb2e2076eb39b52ce19ce255702))
* **deps:** bump docker/build-push-action from 6 to 7 ([#127](https://github.com/the-vibey-project/vibey/issues/127)) ([ad23bce0](https://github.com/the-vibey-project/vibey/commit/ad23bce03a84cb10e578abfa91b5a3dcc1345cce))
* **deps:** bump docker/setup-buildx-action from 3 to 4 ([#126](https://github.com/the-vibey-project/vibey/issues/126)) ([2c532632](https://github.com/the-vibey-project/vibey/commit/2c5326321f3c0b107ef66064f17165ab16162414))
* **deps:** bump docker/setup-qemu-action from 3 to 4 ([#125](https://github.com/the-vibey-project/vibey/issues/125)) ([cff3eed0](https://github.com/the-vibey-project/vibey/commit/cff3eed0d6f5a1bbe6ab64e0669df8914e040f2e))
* develop -> main ([#130](https://github.com/the-vibey-project/vibey/issues/130)) ([23c7c301](https://github.com/the-vibey-project/vibey/commit/23c7c30130358b852f141fe17c231193855dff9b)), reverted by [#131](https://github.com/the-vibey-project/vibey/issues/131) ([b2093525](https://github.com/the-vibey-project/vibey/commit/b20935255aae6792df5905a4b5fed2242ffa57c6))

## [0.6.0] (2026-09-14)

Published to PyPI 2026-09-15 from the promotion PR [#124](https://github.com/the-vibey-project/vibey/issues/124) ([8c3f3a62](https://github.com/the-vibey-project/vibey/commit/8c3f3a62eea76bda175866d7fee20173f6391655)).

### Features

* **runners:** import claudeloop, codexloop, cursorloop, agyloop and qwenloop into `src/vibey_runners/*` with history preserved ([#123](https://github.com/the-vibey-project/vibey/issues/123)) ([cc7e4c02](https://github.com/the-vibey-project/vibey/commit/cc7e4c021735c826d1af7d85f3f7eae822712f23))
* **runners:** add the shared `vibey_runners.common` application package ([1cd11ab8](https://github.com/the-vibey-project/vibey/commit/1cd11ab850f6056c128a98d042ede47661617e18))
* **workspace:** register `src/vibey_runners/*` as a uv workspace at the root ([fa6fd69b](https://github.com/the-vibey-project/vibey/commit/fa6fd69b9b219402e5aa702d77065e9e413f7423))

### Bug Fixes

* **ci:** disable BuildKit for the minikube image build ([233774c0](https://github.com/the-vibey-project/vibey/commit/233774c0ea1e367b1656ff5236a7e84439fba12f))
* **ci:** capture the SIGTERM-test pod's own logs before it's replaced ([14cf1702](https://github.com/the-vibey-project/vibey/commit/14cf1702172df77ccc59fafa2c149356e2b4c269))
* regenerate uv.lock for the v0.5.0 version bump ([829d7b50](https://github.com/the-vibey-project/vibey/commit/829d7b506875977f3947158837ae4c1c642c9265))

### Miscellaneous Chores

* **claude:** move cross-runner interfaces to `vibey_runners.common` ([bae04b7e](https://github.com/the-vibey-project/vibey/commit/bae04b7ec08c3594b331541b51cc105a91b91817))
* **codex:** rewire codexloop onto the shared common interfaces ([f2ebca3f](https://github.com/the-vibey-project/vibey/commit/f2ebca3f9c52dcff05ca9ed307b5355edfa46d8c))
* update vibey-gh workflow templates and fingerprint headers ([0e11464b](https://github.com/the-vibey-project/vibey/commit/0e11464b257c6c3a2ce97224c48401e6a17ba693))
* instrument the worker drain loop to find where SIGTERM stalls ([ac3b2f9d](https://github.com/the-vibey-project/vibey/commit/ac3b2f9d47d411ac361d56392fd4ffaed3f1c4f5))

## [0.5.0] (2026-08-31)

Published to PyPI 2026-09-14 from the promotion PR [#122](https://github.com/the-vibey-project/vibey/issues/122) ([b8cf03ed](https://github.com/the-vibey-project/vibey/commit/b8cf03ed4ce3f4181767b0ce10fa2b44b8a25431)).

### Features

* **design:** a sovereign DESIGN provider — phase one without paid credits ([#120](https://github.com/the-vibey-project/vibey/issues/120)) ([6f86ec1e](https://github.com/the-vibey-project/vibey/commit/6f86ec1e6247bd38f7bcbf02b2761b92dccca51c))

### Bug Fixes

* regenerate uv.lock for the 0.4.0 bump ([#119](https://github.com/the-vibey-project/vibey/issues/119)) ([2eaea251](https://github.com/the-vibey-project/vibey/commit/2eaea2517b6a3878d71dbb6b76612efb423c06f8))

## [0.4.0] (2026-08-31)

### Bug Fixes

* **doctor:** show the sovereign engine ([#117](https://github.com/the-vibey-project/vibey/issues/117)) ([137bba2c](https://github.com/the-vibey-project/vibey/commit/137bba2c1e5b1dc904a73dad0e699dc013627fb8))
* **docs:** repair the five links that abort the channel-site strict build ([#108](https://github.com/the-vibey-project/vibey/issues/108)) ([dd23c762](https://github.com/the-vibey-project/vibey/commit/dd23c762fbe1d7c9253b36a270b0da44ce359241))
* repair PR #96 ([4a4f8c12](https://github.com/the-vibey-project/vibey/commit/4a4f8c12230d82947fee083f97fdb4cc38d44af1), [ec4a9c5b](https://github.com/the-vibey-project/vibey/commit/ec4a9c5bcc00d28e4ba7ec1b7100593fca2ecd13))

### Documentation

* the research paper — ledger-mediated orchestration ([#101](https://github.com/the-vibey-project/vibey/issues/101)) ([352d9cbf](https://github.com/the-vibey-project/vibey/commit/352d9cbf7cd7b7738e8f1a1ad89f557463cecf27))
* BLUF opening and legible phase numbering ([#99](https://github.com/the-vibey-project/vibey/issues/99)) ([59016e52](https://github.com/the-vibey-project/vibey/commit/59016e52189d6ef6ad79334e32e7aadf63513e86))
* embed standing subdoctrine SD-01 — counterparties, trust, and verification ([#110](https://github.com/the-vibey-project/vibey/issues/110)) ([b4614ba3](https://github.com/the-vibey-project/vibey/commit/b4614ba30676442d2ac582e51e050f671832e8da))

### Miscellaneous Chores

* pin vibey-gh 1.50.0 ([#102](https://github.com/the-vibey-project/vibey/issues/102)) ([f1068f85](https://github.com/the-vibey-project/vibey/commit/f1068f85e84391c07bc0f025ffd3f2dae51ae30a))
* pin vibey-gh 1.56.0 ([#103](https://github.com/the-vibey-project/vibey/issues/103)) ([5f3c4eb3](https://github.com/the-vibey-project/vibey/commit/5f3c4eb3f849c8b4d8ca48e7ae4aae2667567daa))
* render the managed workflows with the real 1.56.0 tool ([#105](https://github.com/the-vibey-project/vibey/issues/105)) ([5ee93b7a](https://github.com/the-vibey-project/vibey/commit/5ee93b7a0c0d6615a57a6cebae73abc267d5c6b2))
* pin vibey-gh 1.58.0 ([#112](https://github.com/the-vibey-project/vibey/issues/112)) ([af596f78](https://github.com/the-vibey-project/vibey/commit/af596f78043257660bd1973051b0d9392ff08012))

## [0.3.0] (2026-08-29)

### Bug Fixes

* replace the git source pin so the package can publish at all ([#92](https://github.com/the-vibey-project/vibey/issues/92)) ([643e78e4](https://github.com/the-vibey-project/vibey/commit/643e78e4da62b595f71aaf17f72e30ea5863629f))
* publish the TestPyPI rehearsal as vibey-dev ([#93](https://github.com/the-vibey-project/vibey/issues/93)) ([a9acd42a](https://github.com/the-vibey-project/vibey/commit/a9acd42af81bd33ddd590919dba28db6ff3d6c42))

### Miscellaneous Chores

* adopt vibey-gh 1.39.0 — provenance, gated automation, ProperDocs ([#91](https://github.com/the-vibey-project/vibey/issues/91)) ([80264c2b](https://github.com/the-vibey-project/vibey/commit/80264c2be624e58060fa1f263759df634a194ef8))
* migrate the provenance URL to vibewithadam.matthewsteinberger.com ([#95](https://github.com/the-vibey-project/vibey/issues/95)) ([49c94d06](https://github.com/the-vibey-project/vibey/commit/49c94d06064808f3324dad7abf3b85fe6cfab921))
* pin vibey-gh 1.47.0 ([#100](https://github.com/the-vibey-project/vibey/issues/100)) ([1a96df91](https://github.com/the-vibey-project/vibey/commit/1a96df918388c99379d9d1418c037ecc851f297f))

## [0.2.0] (2026-08-24)

Release commit [2d08a834](https://github.com/the-vibey-project/vibey/commit/2d08a834a28ae0312f31039ac2e12ffea9cb5fc6); published to PyPI 2026-08-28 once #92 and #93 (shipped in 0.3.0) unblocked the publish job.

### Features

* skills-context retrieval: `vibey new --skills-context-mode {off,shadow,inject}` and `--skills-context-budget`, backed by `infrastructure/skills_context.py` (`VibeySkillsContextCompiler`) and wired into the BUILD implement handler. These are CLI-flag-driven, recorded into the project's own config at creation time — there is no static `[skills_context]` `vibey.toml` table (`domain/config.py`'s `VibeyConfig` has no `skills_context` field) ([#82](https://github.com/the-vibey-project/vibey/issues/82)) ([7837d6f1](https://github.com/the-vibey-project/vibey/commit/7837d6f1764ed0f4591b53ff88fafa93f4fa2ff3))
* add opt-in qwenloop fallback engine ([#83](https://github.com/the-vibey-project/vibey/issues/83)) ([eb57670b](https://github.com/the-vibey-project/vibey/commit/eb57670be949b08795edd29196d2ddc0e6102270))
* `vibey recover` command ([#80](https://github.com/the-vibey-project/vibey/issues/80)) ([2438f3b9](https://github.com/the-vibey-project/vibey/commit/2438f3b9a85c66061a9c4fbc7b350be7f85fa724))
* vibey runs on Kubernetes — image, chart, KEDA autoscaling, and graceful scale-in ([#73](https://github.com/the-vibey-project/vibey/issues/73)) ([1918e94a](https://github.com/the-vibey-project/vibey/commit/1918e94a2cb80b23d348b4a35b7554905485a9c6))
* vibey doctor --cluster, plus four new fitness dimensions in runbook 18 ([#74](https://github.com/the-vibey-project/vibey/issues/74)) ([a4731cd6](https://github.com/the-vibey-project/vibey/commit/a4731cd6ffcd726a8800ae9ad931bf859220ba85))
* **operator:** kopf operator and the VibeyProject CRD ([#76](https://github.com/the-vibey-project/vibey/issues/76)) ([e1820c77](https://github.com/the-vibey-project/vibey/commit/e1820c77b9f4ccfb5a00badefbc23dc373c7e7d0))

### Bug Fixes

* **engines:** render valid CodexLoop plans ([f2f30bfa](https://github.com/the-vibey-project/vibey/commit/f2f30bfaca96c5350ab32901e8eaef250afe3f1e))
* **engines:** reap preflight subprocesses ([3dcebeb8](https://github.com/the-vibey-project/vibey/commit/3dcebeb89cc3f612066a19cb6ccdcce38d93962c))
* **budget:** record DESIGN spend so the brake can actually see it ([#78](https://github.com/the-vibey-project/vibey/issues/78)) ([971bf842](https://github.com/the-vibey-project/vibey/commit/971bf84294f6b68414b97ac9f7c6120869cff810))
* read codexloop's flat events, and accept terminal meta status as completion ([#72](https://github.com/the-vibey-project/vibey/issues/72)) ([4b5de059](https://github.com/the-vibey-project/vibey/commit/4b5de059f4c5a43917b6a66cc331252385624448))
* cursorloop takes the plan as --plan, and the flags check stops validating values ([#69](https://github.com/the-vibey-project/vibey/issues/69)) ([119cae99](https://github.com/the-vibey-project/vibey/commit/119cae9917192586c314131793b1a250fff8051e))
* worktree lifecycle reasserts core.bare=false on every mutating path ([#68](https://github.com/the-vibey-project/vibey/issues/68)) ([b530cffb](https://github.com/the-vibey-project/vibey/commit/b530cffbab594022ee9d5720995389ca9b6cfa80))
* **ci:** build TestPyPI under vibey-dev, the name that project holds ([#79](https://github.com/the-vibey-project/vibey/issues/79)) ([45259a24](https://github.com/the-vibey-project/vibey/commit/45259a24ffc439b0d2786eb4f2cb533d4819b7d3))

### Documentation

* runbooks 19-21 and four more fitness dimensions ([#75](https://github.com/the-vibey-project/vibey/issues/75)) ([88e87c86](https://github.com/the-vibey-project/vibey/commit/88e87c8675c54deb8d3825096efb17c0fe8b3ea2))
* runbook 15 — agent-surface sync across every installed IDE and bot ([#67](https://github.com/the-vibey-project/vibey/issues/67)) ([45da3519](https://github.com/the-vibey-project/vibey/commit/45da3519ed23261f3baa7bf2a415509f52d3817c))
* record Front 1 validation and accept the 135s suite deviation ([#71](https://github.com/the-vibey-project/vibey/issues/71)) ([0aaf422d](https://github.com/the-vibey-project/vibey/commit/0aaf422d094e90f27e8673f1914593816470999f))

### Miscellaneous Chores

* adopt vibey-gh guardrails and retire release-please ([#77](https://github.com/the-vibey-project/vibey/issues/77)) ([bd0b8c2b](https://github.com/the-vibey-project/vibey/commit/bd0b8c2b643e398d0a2344078f83eb19fdb26dbb))
* **tests:** template-database, xdist parallelism, unified coverage, hook diet ([#70](https://github.com/the-vibey-project/vibey/issues/70)) ([7067b2a3](https://github.com/the-vibey-project/vibey/commit/7067b2a35cd4e9ff202159ecb1077e6245ea2ca6))

## [0.1.2](https://github.com/the-vibey-project/vibey/compare/vibey-v0.1.1...vibey-v0.1.2) (2026-08-20)


### Documentation

* engagement refresh -- README, community files, license, templates ([#65](https://github.com/the-vibey-project/vibey/issues/65)) ([48ce5ac](https://github.com/the-vibey-project/vibey/commit/48ce5ac706c9b26cc036ab24d63ecd83828fdae6))


### Miscellaneous Chores

* cut 0.1.2 -- ship the engagement refresh to PyPI ([541e820](https://github.com/the-vibey-project/vibey/commit/541e820fe2d68ac3496cec2f4f7eac34f784bcc3))

## [0.1.1](https://github.com/the-vibey-project/vibey/compare/vibey-v0.1.0...vibey-v0.1.1) (2026-08-20)


### Features

* budget brake and escalation grants -- the last dead-end parks ([#56](https://github.com/the-vibey-project/vibey/issues/56)) ([138483c](https://github.com/the-vibey-project/vibey/commit/138483c430e60c7190ab9c1d132ad50352f9fe17))
* **e1:** live engine adapters, rotation wiring, full worker, two-mode harness ([#17](https://github.com/the-vibey-project/vibey/issues/17)) ([3d05a8a](https://github.com/the-vibey-project/vibey/commit/3d05a8ae2204fb0d50ca97010002f6edb3934862))
* make per-job engine rotation live in the worker (Phase 4) ([#41](https://github.com/the-vibey-project/vibey/issues/41)) ([074d279](https://github.com/the-vibey-project/vibey/commit/074d279621081f2b4b5d8545c68ce6b385dc5b0d))
* paid live worker test, and the two real-engine bugs it caught ([#44](https://github.com/the-vibey-project/vibey/issues/44)) ([c3885f7](https://github.com/the-vibey-project/vibey/commit/c3885f7173b8d82bd3399715f808e05f5cc700fb))
* prevent parallel-item merge conflicts and stale-finding loop-backs ([#49](https://github.com/the-vibey-project/vibey/issues/49)) ([812fdd7](https://github.com/the-vibey-project/vibey/commit/812fdd7930d1ad1e82e92c649a3123d22b8ff598))
* real Azure deploy path via the az CLI, behind an explicit flag ([#57](https://github.com/the-vibey-project/vibey/issues/57)) ([a254f23](https://github.com/the-vibey-project/vibey/commit/a254f23dca57f4f5d8fa8ef30e132d169aa98986))
* serialize concurrent integrates with a Postgres advisory lock (Phase 6) ([#43](https://github.com/the-vibey-project/vibey/issues/43)) ([f9e519b](https://github.com/the-vibey-project/vibey/commit/f9e519bfe87661174472e7cce1271d0519581a22))
* turn deterministic verify failures into a bounded repair loop ([#48](https://github.com/the-vibey-project/vibey/issues/48)) ([f793e8b](https://github.com/the-vibey-project/vibey/commit/f793e8bb46ae9c1f43f42109d5f303ff95cec857))
* verification discipline in prompts, and a race-proof conformance verdict check ([#54](https://github.com/the-vibey-project/vibey/issues/54)) ([b98bf81](https://github.com/the-vibey-project/vibey/commit/b98bf815cd737c44c36de4a1a94fd4a7b0014ccf))
* wire wind-down handoff into the worker (Phase 5) ([#42](https://github.com/the-vibey-project/vibey/issues/42)) ([021f6d2](https://github.com/the-vibey-project/vibey/commit/021f6d28c37f5a93b8b978c9f518b78a4caeef4f))
* worker phase 0 -- rotation-blocking bug fix, phase-aware ledger, queue primitives ([#37](https://github.com/the-vibey-project/vibey/issues/37)) ([028cc6f](https://github.com/the-vibey-project/vibey/commit/028cc6f4e45e7ce681e8c9a0be9a3bb5b9109fb0))
* worker phase 1 -- vibey worker dispatches for real through every phase handler ([#38](https://github.com/the-vibey-project/vibey/issues/38)) ([92e4c1c](https://github.com/the-vibey-project/vibey/commit/92e4c1c5a7258592b6b0c28aa0c1d9600a208dfc))
* worker phase 2 -- close the job chain end to end, DONE(local) reachable ([#39](https://github.com/the-vibey-project/vibey/issues/39)) ([20eb081](https://github.com/the-vibey-project/vibey/commit/20eb08139742deddda43ddbdf2fbc4becce06c41))
* worker phase 3 -- deployment spec/consent persistence, DONE(deployed) reachable ([#40](https://github.com/the-vibey-project/vibey/issues/40)) ([f89a46d](https://github.com/the-vibey-project/vibey/commit/f89a46d42360c67161431c1e05771367579f26cf))
* zero-touch answer contracts for interview and exhausted-repair gates ([#53](https://github.com/the-vibey-project/vibey/issues/53)) ([4d40202](https://github.com/the-vibey-project/vibey/commit/4d40202c15d3b43c315f1f440bb0ad974c853785))


### Bug Fixes

* a completed repair session resolves its finding, breaking the repair livelock ([#59](https://github.com/the-vibey-project/vibey/issues/59)) ([c4ef91d](https://github.com/the-vibey-project/vibey/commit/c4ef91dac043ff539958ea3027d95272e4d77b01))
* a gate command that cannot start is a failing gate, not a vibey failure ([#61](https://github.com/the-vibey-project/vibey/issues/61)) ([b708c7d](https://github.com/the-vibey-project/vibey/commit/b708c7d34de727a0015ea21a3634f6d922b96ccd))
* a positive rotation weight must never round down to zero ([#51](https://github.com/the-vibey-project/vibey/issues/51)) ([7e3d463](https://github.com/the-vibey-project/vibey/commit/7e3d463fcc3e07ca7dac5de7fa693ba75511b38f))
* bound the integrate repair loop and give repairs actionable merge instructions ([#52](https://github.com/the-vibey-project/vibey/issues/52)) ([6b186cc](https://github.com/the-vibey-project/vibey/commit/6b186cc08acff70937617764bc25ad9b94b1cab4))
* budget brake now reads the real spend engines write on TurnCompleted ([#58](https://github.com/the-vibey-project/vibey/issues/58)) ([d3248e4](https://github.com/the-vibey-project/vibey/commit/d3248e44e0c2225e226e3a6130abc61b8e548912))
* four autonomy blockers from the live demo's observability class ([#46](https://github.com/the-vibey-project/vibey/issues/46)) ([39c6388](https://github.com/the-vibey-project/vibey/commit/39c6388c642bcb5315146efb1d4dfa5e0c0e2688))
* implement help_text so the flags conformance check can run at all, fix two broken descriptors it found ([#33](https://github.com/the-vibey-project/vibey/issues/33)) ([c923345](https://github.com/the-vibey-project/vibey/commit/c923345d0d805a62b00b7378cfdd25797765d063))
* isolate engine sessions from the orchestrator's Python environment ([#47](https://github.com/the-vibey-project/vibey/issues/47)) ([dc254ee](https://github.com/the-vibey-project/vibey/commit/dc254ee0a77f309a3a5a394a24a7170435b0ad6b))
* map claudeloop's real event_type strings, same fabrication as agyloop's ([#32](https://github.com/the-vibey-project/vibey/issues/32)) ([89ff3fc](https://github.com/the-vibey-project/vibey/commit/89ff3fc132285b9636109f52c1093e01f1e878a6))
* normalize model-produced work item ids to the worktree shape ([#45](https://github.com/the-vibey-project/vibey/issues/45)) ([f688918](https://github.com/the-vibey-project/vibey/commit/f6889185cae4d9d8ce259054f4af5ed14397bdaf))
* only capacity Defers open circuits, and open circuits actually probe ([#50](https://github.com/the-vibey-project/vibey/issues/50)) ([717c797](https://github.com/the-vibey-project/vibey/commit/717c7971bd6569384c434ebfb405567fc8a26f82))
* reassert core.bare=false after land.sh removes the last worktree ([#31](https://github.com/the-vibey-project/vibey/issues/31)) ([f6ae923](https://github.com/the-vibey-project/vibey/commit/f6ae9231a6b7d09f81fa14a544b333f483c6e6db))
* replace codexloop/cursorloop's fabricated LOOP_EVENT_MAP entries with source-verified vocabulary ([#34](https://github.com/the-vibey-project/vibey/issues/34)) ([1bac413](https://github.com/the-vibey-project/vibey/commit/1bac413dfb67529ae4ff9be69a0b590594031b13))
* replace vague conformance prompt with trivially-completable task ([#23](https://github.com/the-vibey-project/vibey/issues/23)) ([b21cd57](https://github.com/the-vibey-project/vibey/commit/b21cd57777ba0bf78da28aefdbd19807b062121d))
* root LoopProcessAdapter run_dir under the run's own worktree, not adapter base_dir ([#21](https://github.com/the-vibey-project/vibey/issues/21)) ([48fd270](https://github.com/the-vibey-project/vibey/commit/48fd27023fff6eb82046ccff4acba38cbdd5841f))
* stop overriding claudeloop's --permission-mode to acceptEdits ([#12](https://github.com/the-vibey-project/vibey/issues/12)) ([b383ae9](https://github.com/the-vibey-project/vibey/commit/b383ae9f0f9de9c4d65070b71ecccd43e31efd9a))
* two production-blocking bugs found by a real subprocess conformance test ([#36](https://github.com/the-vibey-project/vibey/issues/36)) ([9088919](https://github.com/the-vibey-project/vibey/commit/9088919bd2b2970d40ae5aa7a9f738a4fb7cd1f9))


### Documentation

* fifteen expansion runbooks -- the platform buildout, dogfooded through vibey itself ([#60](https://github.com/the-vibey-project/vibey/issues/60)) ([8bc4484](https://github.com/the-vibey-project/vibey/commit/8bc44843e835f74ba9aefcf3344678bba42558a7))
* **provision:** refer to the marketplace by its new name, vibey-skills ([#26](https://github.com/the-vibey-project/vibey/issues/26)) ([3abeeb4](https://github.com/the-vibey-project/vibey/commit/3abeeb4b822a54c585104fa34b8860e491536afb))
* queue agyloop SDK harness handshake investigation (c3) ([#24](https://github.com/the-vibey-project/vibey/issues/24)) ([373bdfe](https://github.com/the-vibey-project/vibey/commit/373bdfe97e2008f124c7494cb7c6af26a63009e3))
* queue dogfooded investigation of the real-engine conformance timeout ([#22](https://github.com/the-vibey-project/vibey/issues/22)) ([1479cc6](https://github.com/the-vibey-project/vibey/commit/1479cc65f23bea7bcc16e0c99a58f66bfe8c6846))
* queue investigation of LoopProcessAdapter still failing against a healthy agyloop ([#25](https://github.com/the-vibey-project/vibey/issues/25)) ([538d9ee](https://github.com/the-vibey-project/vibey/commit/538d9ee596e3b5d481b382b9ab31070c6c0c24b7))
* queue loop_events.py agyloop event-type mapping fix ([#28](https://github.com/the-vibey-project/vibey/issues/28)) ([e6c90f2](https://github.com/the-vibey-project/vibey/commit/e6c90f20ef07de93ed15cfa099bde26484520226))
* rename e1-loop-event-map plan to match run.sh's REPO-suffix convention ([#29](https://github.com/the-vibey-project/vibey/issues/29)) ([c4df145](https://github.com/the-vibey-project/vibey/commit/c4df14583894e44b5cc380c182f398ab107a5ea0))
* strengthen E1 plan against premature Done declarations ([#13](https://github.com/the-vibey-project/vibey/issues/13)) ([95b1e8c](https://github.com/the-vibey-project/vibey/commit/95b1e8c4464005cbc0e03e4fb1fd8d47b87384d8))
* teach the runbook the zero-touch contracts ([#55](https://github.com/the-vibey-project/vibey/issues/55)) ([9df8690](https://github.com/the-vibey-project/vibey/commit/9df8690e793eb15548b28e0bfa67bf4ef3292ac7))
* update loop_events.py verification status now that both sinks are wired ([#35](https://github.com/the-vibey-project/vibey/issues/35)) ([301b3f5](https://github.com/the-vibey-project/vibey/commit/301b3f53d059561240eb3cb5a8fd0b909220fbd0))

## [0.1.0](https://github.com/the-vibey-project/vibey/releases/tag/vibey-v0.1.0) (2026-08-16)


### Features

* add structured logging, a -v ladder, and operator-facing errors ([53ca473](https://github.com/the-vibey-project/vibey/commit/53ca473c29c7d00cb196e6d6abba5c701cf55ff2))
* **azure:** implement AzureClientPort and mutation-guarded adapter (task 10.4) ([34f43c4](https://github.com/the-vibey-project/vibey/commit/34f43c470b491ee844b24ac34e0a152b009cc77d))
* **build:** agent-surface provisioning into BUILD worktrees (task 6.3) ([c3fd680](https://github.com/the-vibey-project/vibey/commit/c3fd680cfe3be1714c589f43f50be43fd88018c7))
* **build:** budget check before effort escalation (task 6.7) ([8d71791](https://github.com/the-vibey-project/vibey/commit/8d71791d49d825b8d876e523bfa1832f4ca13371))
* **build:** build.implement -- engine run, tail, and ledger (task 6.4) ([fa37161](https://github.com/the-vibey-project/vibey/commit/fa371612c29a280a6bb62e8d9a8a7aa7bf8b5355))
* **build:** build.integrate -- merge, gate, isolate-not-rollback (task 6.8) ([c5f9759](https://github.com/the-vibey-project/vibey/commit/c5f97592c27921cc27869bb22631805220c3616a))
* **build:** build.verify -- gates, criterion coverage, diff review (task 6.5) ([a18a123](https://github.com/the-vibey-project/vibey/commit/a18a12311f4414a98c6e18becc6f874e52089ee8))
* **build:** BUILD→REVIEW and BUILD→DESIGN phase guards (task 6.10) ([27c13d1](https://github.com/the-vibey-project/vibey/commit/27c13d171f2619672a8e82c6685599491402e2e2))
* **build:** forced rotation constraint on effort tier crossings (task 6.6) ([be47648](https://github.com/the-vibey-project/vibey/commit/be47648307d5c0a8b4f54ca84976c3813ee49caa))
* **build:** parallelism limiter -- min(config, eligible×2, cpu) (task 6.9) ([b49d0df](https://github.com/the-vibey-project/vibey/commit/b49d0df35d3840ac8b09bd6c10e4e9b4487eff60))
* **build:** real git worktree manager for BUILD work items (task 6.2) ([e363772](https://github.com/the-vibey-project/vibey/commit/e3637723335272fc037170202bd36886d37b9fbc))
* **build:** start M6 -- build.decompose and BUILD-entry wiring (task 6.1) ([b7fa97f](https://github.com/the-vibey-project/vibey/commit/b7fa97f1afa4103d45195377c5482acafe99128e))
* **cli:** implement operational cli commands (task 8.2) ([6e30e8f](https://github.com/the-vibey-project/vibey/commit/6e30e8f807fc0e496d5a40874674b5a76b692fe6))
* **deploy:** add CLI/TUI surfaces for deployment commands (task 10.12) ([c3ec5b4](https://github.com/the-vibey-project/vibey/commit/c3ec5b40db40a57e8a0747aa23e27f07cbb12697))
* **deploy:** add full offline delivery-to-deployment system test (task 10.13) ([4d8f3f5](https://github.com/the-vibey-project/vibey/commit/4d8f3f532a71598cb5a4b3d2631666b40d8e12c8))
* **deploy:** implement deployment retry and escalation ladder (task 10.7) ([3a36710](https://github.com/the-vibey-project/vibey/commit/3a3671069f083bc5d90703ca7833808138f2fed5))
* **deploy:** implement Phase 4 deploy design interview and acceptance (task 10.3) ([ec3a924](https://github.com/the-vibey-project/vibey/commit/ec3a9247021fcbbfb8e88da772460a5174fe14fe))
* **deploy:** implement Phase 5 deploy execution graph handler (task 10.6) ([b6adba0](https://github.com/the-vibey-project/vibey/commit/b6adba0efe0c0055e726fbde53d0563d978bce80))
* **deploy:** implement Phase 6 review demo and failure triage handlers (task 10.10) ([5dc516a](https://github.com/the-vibey-project/vibey/commit/5dc516a6f648458dd4b8556b0754edcfc2162cef))
* **deploy:** implement Phase 6 review loop routing handler (task 10.11) ([3053219](https://github.com/the-vibey-project/vibey/commit/305321919f5559a22d9b7537e430995af2310109))
* **deploy:** implement progressive exposure and recovery evaluation (task 10.8) ([a9d4f71](https://github.com/the-vibey-project/vibey/commit/a9d4f710c8f418af1412ced4f79f8de880dde63b))
* **deploy:** implement runtime verification contract evaluation (task 10.9) ([c4f90eb](https://github.com/the-vibey-project/vibey/commit/c4f90eba393f017e936d302d5161e8d48546ae85))
* **deployment:** implement DeploymentSpec, consent verification, and failure routing (task 10.2) ([032e441](https://github.com/the-vibey-project/vibey/commit/032e44129e098080a8f9414f95606789fc4794ea))
* **design:** wire the DESIGN -&gt; VISUAL_DESIGN/BUILD choice gate into accept ([b1459d1](https://github.com/the-vibey-project/vibey/commit/b1459d11942ee6d8a9ae62af17839aa96ffaf7cd))
* **domain:** add media-provider capability discovery and rotation (5.9/5.10) ([8293d22](https://github.com/the-vibey-project/vibey/commit/8293d22baa179a0c55f4c9c7f575647b72f065c5))
* **domain:** add VISUAL_DESIGN phase and its opt-in guard (M5 task 5.6) ([8f4c1a9](https://github.com/the-vibey-project/vibey/commit/8f4c1a9605da7cbbac3b4b42ff062cbbee2f222c))
* **domain:** add VisualInventory, the screen/state matrix for M5 task 5.7 ([751803f](https://github.com/the-vibey-project/vibey/commit/751803f065278301c4956e3a797c728525573c11))
* **iac:** implement IaC static checks, preflight, and what-if evaluation (task 10.5) ([75fef62](https://github.com/the-vibey-project/vibey/commit/75fef62e00872860e9f3f2debecc38acf975b054))
* implement M1 pure domain (phase machine, rotation, no-loss gate) ([7114e37](https://github.com/the-vibey-project/vibey/commit/7114e37f21b9ee4e0aaa96c66deadc8f9ae9f369))
* implement M2 durable queue and crash-safe workers ([6cbff9b](https://github.com/the-vibey-project/vibey/commit/6cbff9b2f2ef751b25d04ce9f8a92a50bd520693))
* implement M3 engine adapters and conformance suite ([0b6c1cc](https://github.com/the-vibey-project/vibey/commit/0b6c1cc08700fb8bbb70aeb7630bff4991ef9c39))
* implement M4 ledger and handoff -- the no-loss critical path ([df9243f](https://github.com/the-vibey-project/vibey/commit/df9243f17a47847fec2c7c1b9973a5ae95395ac3))
* **notify:** implement desktop notifications and webhook publisher (task 8.4) ([7d2988c](https://github.com/the-vibey-project/vibey/commit/7d2988cb7a1f5f63ab9118bff95c897ac0256ab7))
* **observability:** implement opentelemetry and metrics exports (task 8.3) ([45de50a](https://github.com/the-vibey-project/vibey/commit/45de50abb751084bbcdf21f451ea2d34761ef61b))
* **phase:** expand pure phase machine to deployment stage set (task 10.1) ([cfe7357](https://github.com/the-vibey-project/vibey/commit/cfe7357a9247e68ad4e82c4085b620cbaf843496))
* **review:** implement automated findings pre-triaging (task 7.3) ([8a264ea](https://github.com/the-vibey-project/vibey/commit/8a264ea3c6572651aa2ec2ae10dc2c02032df06a))
* **review:** implement deployment opt-in handoff to deploy design (task 7.8) ([31ff71f](https://github.com/the-vibey-project/vibey/commit/31ff71fc0df982eb5935f8b7f339eb95dfa3a949))
* **review:** implement deployment-choice gate (task 7.7) ([ac9e697](https://github.com/the-vibey-project/vibey/commit/ac9e6977e1c380b040a23ec8b4828d414f20cd9d))
* **review:** implement re-entrant design scoped to findings (task 7.6) ([c916d8c](https://github.com/the-vibey-project/vibey/commit/c916d8cec0d6a2aff4599b79fb5b862a50967128))
* **review:** implement review.collect and ledger-grounded QA (task 7.2) ([b750b81](https://github.com/the-vibey-project/vibey/commit/b750b816fe123035895eaf9d64b8de24121e04be))
* **review:** implement review.demo and deltas projection (task 7.1) ([b88488e](https://github.com/the-vibey-project/vibey/commit/b88488ed8e93c4843fb407a66ddc95e760d05090))
* **review:** implement review.triage classification (task 7.4) ([ecff22f](https://github.com/the-vibey-project/vibey/commit/ecff22fe724dacdbce27db1f7f618062230e481a))
* **review:** wire loopback routing and cycle increment (task 7.5) ([ff2dea9](https://github.com/the-vibey-project/vibey/commit/ff2dea91dbfc3fa53b1666a1240f604d52a95217))
* scaffold M0 repo skeleton, onion contract, CI, and vibey.toml schema ([578421f](https://github.com/the-vibey-project/vibey/commit/578421fa079bb1aa7f6c4889ab53c7a9651639df))
* **security:** implement destructive-command prevention guard (task 9.2) ([dcb8d30](https://github.com/the-vibey-project/vibey/commit/dcb8d30858f02e10faf577e1978aed1068051494))
* **security:** implement hardened container isolation runtime (task 9.1) ([f59f630](https://github.com/the-vibey-project/vibey/commit/f59f630295f61eff4c3b523534bd222d35942308))
* **security:** implement scope-bound mutation guard (task 9.3) ([0fb9eb8](https://github.com/the-vibey-project/vibey/commit/0fb9eb87481ee67405abefe02aeed000d6034fb2))
* **security:** implement untrusted prompt defense and delimiter shielding (task 9.4) ([c7544e4](https://github.com/the-vibey-project/vibey/commit/c7544e44100394596f25c575688c608ce6d76d6c))
* **tui:** implement live dashboard TUI (task 8.1) ([8bec60f](https://github.com/the-vibey-project/vibey/commit/8bec60ff8e39c40f79cf51d314376bdffe52ee8b))
* **tui:** implement replay mode for watch command (task 8.5) ([cdb34dc](https://github.com/the-vibey-project/vibey/commit/cdb34dc01ae3b0cde5ddd7b3ef84f0950fb5c50e))
* **visual:** close the loop -- VISUAL_DESIGN -&gt; BUILD accept/waive (task 5.13) ([508bb71](https://github.com/the-vibey-project/vibey/commit/508bb717830e32c894b981379dbd44678bc5a30a))
* **visual:** wire visual.inventory/visual.plan job handlers and persistence ([6a5231c](https://github.com/the-vibey-project/vibey/commit/6a5231c2d3d33a310aaba6150c160dd94d9d19c8))


### Bug Fixes

* align rotation weights with ADR-0005 ([3f63fcd](https://github.com/the-vibey-project/vibey/commit/3f63fcd9d1c853dcdff16e9796e0c1e2f1e14d46))
* **cli:** repair unreachable `vibey design accept` and cover build_app() paths ([3987618](https://github.com/the-vibey-project/vibey/commit/39876189a11667e915adde0a4e404b4d0604045f))
* **cli:** stabilize CliRunner terminal styling across all CLI test files ([#1](https://github.com/the-vibey-project/vibey/issues/1)) ([ac76131](https://github.com/the-vibey-project/vibey/commit/ac7613169d1308a49dc3325a9460a4f42ad4ba7f))


### Documentation

* add session handoff for continuing after M4 ([78d77b8](https://github.com/the-vibey-project/vibey/commit/78d77b8b804a7653e6a6129bb10d30e80d0533f3))
* add the agyloop invocation, and stop hardcoding one done marker ([068940c](https://github.com/the-vibey-project/vibey/commit/068940ce46bafbb266f6051a0e0b1155b005a73a))
* add the fleet program runbook ([5768382](https://github.com/the-vibey-project/vibey/commit/57683820fc61d13f695ffd4dfc91356dc3c03068))
* make visual and deployment stages opt in ([329dd2b](https://github.com/the-vibey-project/vibey/commit/329dd2bf82140660a367694d47b8cf77bbcf56e7))
* plan six-phase Azure deployment lifecycle ([30047f7](https://github.com/the-vibey-project/vibey/commit/30047f754705e9b7d3dddac03a22c629e59ebf43))
* **security:** document threat model and security policy (task 9.5) ([a254fc1](https://github.com/the-vibey-project/vibey/commit/a254fc1885285ad9cd7b98d5ff9f81ce1963ef3d))
* update README status for M7 completion and format system test ([0cf7bd3](https://github.com/the-vibey-project/vibey/commit/0cf7bd3596e366929dc34e98d543e75329bcbe3c))


### Miscellaneous Chores

* cut the first vibey release ([ee841fa](https://github.com/the-vibey-project/vibey/commit/ee841fa65b92e9911c8bdeb595577ebb1321d82e))
