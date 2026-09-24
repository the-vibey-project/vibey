# 0045 — The test harness runs once per machine and takes its runs from a queue: a run is keyed by what it tests, answered once, and parked when it dies

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 8.c, 8.e (drafted for ratification), 12.c, 10.e, 10.f · **Related:** ADR-0044 (the queue port, loop services, dead letters as parks), ADR-0028 (hooks chain, they do not replace), ADR-0024 (every bounded ladder parks with a grant), ADR-0023 (four layers, four floors), ADR-0036 (the merge queue is declared), ADR-0018, ADR-0017, ADR-0016, ADR-0022, ADR-0002, ADR-0030, ADR-0037, ADR-0040 · **Evidence:** `develop` at `702b1490`, read 2026-09-22. Every `file:line` below is at that commit unless it names a storm file (`STORM/…`), which is read at the same time. ADR-0044's lanes R01–R34 are specifications, not code; where this record builds on one, it names the lane.

**Owes:** the ratification of 8.e, with the one amendment this record asks for (a recorded result is reused *while it is valid*, see *Where the drafted rule conflicts*). The docs wave: CLAUDE.md's commands block, `docs/reference/cli.md` (`vibey test …`, `vibey test-harness …`), `docs/reference/configuration.md` (`[test_harness]`), CONTRIBUTING.md's hook section, the four agent-surface trees' testing skill, and the ADR count (`tests/meta/test_adr_counts.py`).

**Naming.** ADR-0030's "live harness" is a test *mode* (faked or paid engines). The "test harness" here is the single instance that *executes* test runs. They are unrelated.

## Context

### The rule

Sub-doctrine 8.e, as drafted for ratification:

> The test harness is held to 8.c. It runs as a single instance per deployment — one test run at a time on one machine — and takes its work from a queue on the bus surface. Nothing starts a second test run beside a running one: a commit hook, a storm lane, a reviewer and the command line all put their run on the queue and wait for its result. Parallelism inside the one run is the instance's capacity; a second run beside it is contention. Idempotency: a run is identified by what it tests — the tree, the selection of tests and the environment — so the same run asked for twice is answered once, and a repeat request receives the recorded result instead of a second execution. Dead letters: a run that crashes the harness, exceeds its bound or cannot be executed is moved to a dead-letter queue with its evidence, where a human or a repair lane can see it — it is never retried forever and never silently dropped.

8.c (`src/vibey_tools/gh/docs/doctrines.md:173-198`) is ratified: every loop runs as a single instance per deployment, fed by a queue on the bus surface, and "a restart, never a second copy, is how a loop survives a death" (`:196-198`). 8.b names RabbitMQ as the bus default (`:148-151`).

The operator's evidence:

1. A pre-push full suite failed a timing test while a local model server was running.
2. Two coverage runs in one directory consumed each other's `.coverage.*` shards. `[tool.coverage.run] parallel = true` (`pyproject.toml:304-307`) makes every process write `.coverage.<host>.<pid>.<random>` in the working directory, and the `coverage combine` that pytest-cov performs at the end of a run merges every shard it finds there, including another run's.

### Who runs tests today

| caller | path | evidence |
|---|---|---|
| `git push` | vibey-gh's managed `pre-push` hook chains to `pre-push.local` (`.githooks/pre-push:116-118`), which execs `framework-hook.sh pre-push` (`.githooks/pre-push.local:5`), which execs the pre-commit framework's own generated hook from `$(git rev-parse --git-common-dir)/hooks/pre-push` (`.githooks/framework-hook.sh:32-33`, `:56-58`) | ADR-0028 "hooks chain, they do not replace" |
| the framework's pre-push stage | `test-suite` = `uv run pytest -q -p no:cacheprovider` (`.pre-commit-config.yaml:11-24`); `coverage-gates` = the same suite with `--cov=vibey --cov-branch` plus four `coverage report --fail-under=100` (`:40-45`); `mypy`, `lint-imports`, `bandit`, `pip-audit` (`:26-38`, `:47-59`) | the file's own comment: `coverage-gates` is "a strict superset" of `test-suite`, and "one push ran the whole suite three times" (`:20-23`); the full suite "measured at 259s" (`:18`) |
| `git commit` | `.githooks/pre-commit:5` runs the framework's pre-commit stage: ruff only; no tests | `.pre-commit-config.yaml:1-7` |
| CI `gates` | one `uv run pytest … --cov` (`.github/workflows/ci.yml:72-73`), then four per-layer `coverage report` steps reading `.coverage` in the checkout (`:75-85`) | ADR-0023 |
| CI `noloss` | `uv run pytest -m noloss --hypothesis-profile=noloss` (`:139`); a required check (`:98-103`) | |
| CI `postgres-compatibility` | a 14–18 matrix running `uv run pytest` on three paths (`:188-193`), bound by `tests/meta/test_postgres_support_matrix.py:13-18` (which pins the matrix and image, not the command) | |
| CI `tools` rows | each tenant's own `pytest`, in a fresh venv built with plain `pip install -e` (`:195-548`); qwenloop's floor rides in its addopts (`src/vibey_runners/qwen/pyproject.toml:68`) | ADR-0022 |
| storm lanes | a local model runs `uv run pytest …` through qwenloop's `shell` tool: `SandboxTools.execute` spawns the argv in the lane's worktree with `os.environ` minus names containing `KEY` or `TOKEN` (`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py:30-51`) and **kills it after a hard-coded 120 s** (`:55-59`). Lanes are full clones with their own `.venv` (`lane-setup.sh:22-29`). `storm-queue.sh:19` runs one lane at a time, which serializes lanes against each other, but not against the operator's own pushes on the same machine | the ADR-0044 lane specs' *Checks* sections all say `uv run pytest` |
| `build.verify` | `infrastructure/build/gate_runner.py` runs a project's gate commands in the item's worktree, bounded by `gates.timeout_seconds` (`:52`, 30 min) | "a project's whole test suite is one gate command" (`:53-54`) |
| the command line, a reviewer | `uv run pytest …` by hand | |

Inside one run, pytest-xdist already parallelizes: `addopts = "-m 'not paid' -n auto --maxprocesses=8 --dist=loadgroup"` (`pyproject.toml:262`). Each run clones its own database from a per-server template, serialized by an advisory lock around the clone (`tests/conftest.py:63-78`, `:81-127`). Nothing serializes whole runs.

### What exists to build on

- ADR-0044: `vibey_bootstrap.amqp` (lane R04: robust connection, confirming publisher, prefetching consumer, `AmqpDelivery.complete/abandon/dead_letter`, and `InMemoryAmqpClient`), quorum queues with a delivery limit and a dead-letter exchange (§2), "dead letters are parks" (§8), the idempotency-key table (§9), and "persist the result, then publish, then acknowledge" (§13).
- `ProcessReaper` (`src/vibey/infrastructure/process/reaper.py:45-100`): SIGKILL a process group and reap it within a bound.
- `CleanGitEnvSubprocessExecutor` (`src/vibey/infrastructure/git/clean_env.py:22-37`): runs git with every `GIT_*` variable stripped, which matters inside a hook, where git exports `GIT_DIR` (`.githooks/framework-hook.sh:35-53`).
- The `Clock` port (`src/vibey/application/interfaces/system.py:11-12`).

### What does not fit

- `human_gate.project_id` is `NOT NULL` (`migrations/0008_human_gate_artifact_budget.sql:3`). A test run belongs to a checkout, not to a vibey project, so a dead-lettered test run cannot be a gate row.
- vibey-gh manages exactly two hooks, `commit-msg` and `pre-push` (`src/vibey_tools/gh/vibey_gh/install.py:34`), and `installed()` compares each byte for byte with its template (`:639`) in every adopting repository. The pre-push *template* is the wrong place for anything repository-specific. The framework config the chain reaches is the right one.
- vibey-gh declares `dependencies = []` (`src/vibey_tools/gh/pyproject.toml:30`), and `domain/` may import it (CLAUDE.md). An AMQP client cannot live there.
- `.hypothesis/` is not in the root `.gitignore` (`.gitignore:1-20`). The four runner tenants ignore it (for example `src/vibey_runners/claude/.gitignore:22`). A Hypothesis run writes its example database there, so a working-tree digest would see a test run change the tree it tested.

## Decision

### 1. The run, the instance, the deployment

- A **test run** is one execution of the configured test command (`[test_harness] command`, default `uv run --no-sync pytest`) with one argv, in one working directory, followed by the run's coverage gates, if it has any (§8).
- The **instance** is the one process executing runs on a machine. It has two shapes, one per backend (§3). With `rabbitmq`, it is `vibey test-harness serve`, a long-lived service that consumes the machine's queue with prefetch 1. With `local`, it is `vibey test-harness execute`, a supervisor the requester spawns detached for each request.
- The **deployment** is the machine:
  - On a laptop, it is the user's `[test_harness] state_dir`, which defaults to `$XDG_STATE_HOME/vibey/test-harness`, or `~/.local/state/vibey/test-harness`. Every checkout, worktree and storm lane of that user shares it.
  - A shared machine, such as a self-hosted CI runner, sets `state_dir` to one shared path.
  - In a cluster, the harness is one Deployment with `replicas: 1` and `strategy: Recreate`, with its queue named `cluster` (lane T27).
  - A GitHub-hosted job is a machine of its own.
- **Concurrency is not a key.** 8.e fixes it at one run. A key that could only be set to a value the law forbids is not configurability (12.c). Capacity *inside* a run stays a key: it is pytest's own `-n` / `--maxprocesses` (`pyproject.toml:262`).

### 2. The machine lock is the floor

Every instance takes `flock(LOCK_EX)` on `<state_dir>/machine.lock` for the whole of each run. This holds in both backends, and so does the pytest plugin's `locked` mode (§10). The descriptor is passed to the run's child through `pass_fds`, so the lock is held until the **last** process of the run exits, even if the instance itself is SIGKILLed.

That gives one invariant the rest of the design leans on:

> An instance that holds the lock and finds an attempt recorded `running` knows that the process which recorded it is dead, and so is every process that attempt started.

A crash is detected by that fact alone, with no pid probing and no clock (§9). The lock also serializes the two backends against each other: a `local` supervisor and the `rabbitmq` service on one machine cannot run at the same time.

A `<state_dir>/machine.lock.holder.json` file names the holder (pid, run id, request id, since). `vibey test status` prints it.

### 3. Two backends, one store, no silent fallback

`[test_harness] backend` (`VIBEY_HARNESS_BACKEND`) selects the backend.

| backend | instance | queue | used when |
|---|---|---|---|
| `auto` (the default) | as below | as below | `rabbitmq` when `[bus] amqp_url` resolves (lane R17's precedence), the broker answers, **and** a harness service consumes the machine's queue; otherwise `local` |
| `rabbitmq` | `vibey test-harness serve` | `<prefix>.tests.<instance>` (§12) | always; with no URL, the run fails with `TestHarnessNotConfigured`, which names the remedies |
| `local` | a detached `vibey test-harness execute` per request | the set of processes waiting on the machine lock | always; it never touches the broker |

**Why `auto` is not the silent fallback that ADR-0002 and ADR-0044 §1 forbid.**

1. It is not silent. The first line of every answer names the backend, and when `auto` degrades, the next line says why: `backend=local (auto: no harness service consumes vibey.tests.<instance>)`.
2. It cannot split anything. Both backends take the same machine lock and write the same store (§9), so choosing either path can neither run two tests at once nor fork the record. ADR-0044 §1 guards against two consumers of one job table reading two different queues. Here, that cannot happen.
3. The rule's own operator requires that a machine without RabbitMQ can still commit and push.

**The store** is one directory tree under `state_dir` (lane T10), shared by both backends on the machine. It holds requests, per-request answers, per-key attempt records, full logs, kept coverage data and dead letters. Every write is atomic (a temporary file plus `os.replace`). An attempt number is claimed with `O_CREAT|O_EXCL`. Only the lock holder writes attempts. PostgreSQL is **not** the harness's store, for three reasons:

- the records are per machine, by the rule's own scope;
- the push path must work with nothing running but the tests' own database;
- one store per machine keeps both backends coherent.

This is a deliberate departure from ADR-0044's record-store rule, which is about job truth shared by many workers and enforced by CHECK constraints. The store is a port (`TestRunStoreInterface`), so a PostgreSQL adapter can be added without touching the key or the protocol.

### 4. What a request carries, and what a run executes

A `TestRunRequest` (`vibey.test.request/1`, lane T03) carries:

- `request_id` and `cwd`;
- the selection: the command, the argv and the gates;
- the requester's `TestEnvironment` (§5);
- the raw values of the pass-through variables;
- `fresh`, `grant`, `requested_at`, `start_by` and `requester`.

The instance validates it before running anything:

- `cwd` is absolute and exists, and after `resolve()` it lies under `[test_harness] root`;
- no argv item contains NUL;
- every variable name matches `[test_harness] pass_env`;
- the selection's command equals the instance's own `[test_harness] command`. The command is in the request only so that it is part of the key: a message never chooses what runs.

A request that fails any of these is **unexecutable** and is dead-lettered without a run (§9).

It then executes `command + argv` in `cwd`:

- with `start_new_session=True`;
- with stdout and stderr going to `<state_dir>/logs/<run_id>.log`;
- bounded by `run_bound_seconds`, after which `ProcessReaper` kills the process group.

The environment is **exactly** the following, the same in both backends:

- `base_env` from the instance's own environment (default `PATH HOME USER LOGNAME LANG LC_* TMPDIR TZ SHELL TERM XDG_* UV_*`);
- the request's `pass_env` values (default `VIBEY_TEST_* VIBEY_QUEUE_BACKEND VIBEY_ENGINE_INVOCATION PYTEST_ADDOPTS`);
- `VIBEY_HARNESS_RUN=<run_id>`, the re-entrancy marker (§10);
- `COVERAGE_FILE=<state_dir>/data/<run_id>/.coverage` (§8).

Nothing else is inherited. That includes `GIT_*` (the hook's `GIT_DIR` would re-point git inside tests, `.githooks/framework-hook.sh:35-43`), `VIRTUAL_ENV`, and any credential the configuration does not name.

### 5. The idempotency key

```
key = sha256( canonical_json({
  "schema": "vibey.test.key/1",
  "tree": <working-tree digest>,
  "selection": {"command": [...], "argv": [...], "gates": [[include, fail_under], ...]},
  "environment": {"python": ..., "distributions": ..., "database": ..., "env": {NAME: sha256(value), ...}}
}) )
```

`canonical_json` is `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`. It is pure, and lives in `domain/test_harness.py` (lane T01).

| component | defined as | why |
|---|---|---|
| tree | `wt1:` + sha256 over sorted lines `"<mode> <blob>\t<path>"` for every file git would add with `git add -A`. The lines are the index entries (`git ls-files -s -z`), with each modified, deleted and untracked-but-not-ignored path (`git ls-files -z -m -d -o --exclude-standard`) replaced by its worktree blob (`git hash-object`), minus `[test_harness] tree_exclude` (default `.hypothesis/`). Outside a git work tree, it is `untracked:<uuid4>`, which is never reused | It covers what the run reads. That is the committed tree plus uncommitted edits plus new test files a lane has not added, which a HEAD tree id would miss. It writes nothing to `.git` and never touches the real index, and it runs through `CleanGitEnvSubprocessExecutor`, so it is correct inside a hook |
| selection | the configured command, the argv exactly as given (after `pytest`), and the gates | a different flag is a different run; normalizing flags is where a cache lies |
| python | `<implementation>-<version>-<sys.platform>-<machine>` of the requester's interpreter | |
| distributions | sha256 over sorted `name==version` of `importlib.metadata.distributions()` in the requester's interpreter | This, rather than the lockfile hash, is what the run imports. `uv.lock` is tracked, so it is already in the tree, and a stale venv is caught here |
| database | the server version of the DSN named by `[test_harness] database_env` (default `VIBEY_TEST_DATABASE_URL`), or `unset`, or `unreachable` | a PostgreSQL upgrade re-runs everything. A failure against an unreachable database is recorded under a key that stops matching once the database is back |
| env | the names and **digests** of the pass-through values | a changed DSN or `PYTEST_ADDOPTS` is a different run. Raw values are never stored |

The requester computes the environment in its own process, which is the interpreter the tests run in (`uv run vibey …` or the plugin inside `pytest`). The instance recomputes the tree **under the lock, immediately before it spawns**, and again after the run.

- If the tree changed while the request was queued, the result is recorded under the tree actually tested, and the answer names it (`tested_tree`).
- If the tree changed *during* the run, the attempt is recorded as not reusable, because what was tested is then unknown (10.f).

A selection that reads pytest's cache (`--lf`, `--last-failed`, `--ff`, `--failed-first`, `--nf`, `--new-first`, `--sw`, `--stepwise`, `--sw-skip`, `--stepwise-skip`) depends on state outside the key, so it is never reusable.

### 6. Outcomes

`TestOutcomePolicy.classify(exit_code, timed_out, gate_failures)` is pure (lane T01). It classifies by pytest's documented exit codes:

| observed | outcome | reusable | dead letter |
|---|---|---|---|
| exit 0, every gate passes | `passed` | yes | no |
| exit 0, a gate fails; exit 1 (tests failed), 2 (interrupted, which includes collection errors), 4 (usage error) or 5 (no tests collected) | `failed` | yes | no |
| exit 3 (pytest internal error), killed by a signal, or no exit code | `crashed` | no | **yes** |
| the bound was reached | `timed_out` | no | **yes** |
| rejected by validation, or the command could not be spawned | `unexecutable` | no | **yes** |
| stopped by a drain, SIGTERM or SIGINT of the instance | `abandoned` | no | no |

Any other positive exit code, such as one from `uv` itself, is `failed`. A wrong classification there is still bounded by the failure window (§7).

### 7. Answered once: when a recorded result is reused

`TestReusePolicy.decide(attempts, now, fresh, grant)` is pure (lane T02). It is applied to the key's attempts, in this order:

1. **Parked.** The latest terminal attempt is a dead letter that no one has answered, and the request carries no grant. The answer is `parked`, naming the run and `vibey test requeue <run_id>`. Nothing runs. This is "never retried forever" (§9).
2. **Fresh or granted.** The request says `--fresh` (`VIBEY_HARNESS_FRESH=1`), or it is a requeue: execute.
3. **Flaky.** Among the key's retained, reusable, terminal attempts, one `passed` and one `failed`. The evidence is contradictory, so the state is unknown (10.f). Execute, and mark the answer `flaky`, listing both run ids.
4. **Latest.** Take the latest terminal attempt. If it is reusable and still inside its window, the answer is `reused`, carrying the recorded exit code, output tail, gate reports, run id and `recorded_at`. Otherwise execute.

The windows are keys: `pass_ttl_seconds` (default 86 400) and `fail_ttl_seconds` (default 900).

- **A cached FAIL is never replayed forever.** It answers the duplicate that arrives while it runs, a push repeated straight away, and a model re-running an unchanged command. Fifteen minutes later it runs again. A human who suspects a flake says `--fresh` at once. When the reruns disagree, rule 3 stops all reuse of that key.
- **A cached PASS** is evidence that *a* run passed on this exact input at `recorded_at`, and the answer says exactly that. It expires so that drift the key cannot see (the kernel, the machine, a clock-sensitive test) is re-examined daily.
- **Coalescing.** Identical requests queued behind a running one are answered from its record when they reach the lock. That holds in both backends, because the check runs under the lock.
- **CI always sends `--fresh`.** A verifier must produce its own evidence (§10).

### 8. Coverage runs inside the run

- **Gates are part of the request** (`--gate 'src/vibey/domain/*=100'`, which is `CoverageGate(include, fail_under)`). The instance runs each one as `coverage_command report --data-file=<private> --include=<glob> --fail-under=<n>` (default `uv run --no-sync coverage`) after pytest, under the same lock. Each result is a `GateReport` in the record. A cached answer therefore replays the gates as well.
- **The data file is private.** `COVERAGE_FILE` points into the run's own data directory, so every `.coverage.*` shard and the combine stay inside it. That removes the second piece of evidence structurally, not only by serialization.
- **The data is kept and restored.** When the argv collects coverage (`--cov`, `--cov=…`), the combined file is kept with the record. It is copied to `<cwd>/.coverage` after execution **and** on reuse, so a later `coverage report` (CI's four gate steps, `ci.yml:75-85`, or a lane's *Checks*) reads the data of the run that answered. The requester's fast path skips any request that collects coverage, so that restore happens only under the lock.

### 9. Dead letters are parks

This is ADR-0044 §8's pattern and ADR-0024's grant, applied to test runs.

| ADR-0044 (jobs) | this record (test runs) |
|---|---|
| a delivery past `x-delivery-limit` dead-letters to `vibey.jobs.dead` | a run that crashed, timed out or was unexecutable is recorded with its evidence in `<state_dir>/dead/<run_id>.json`. With `rabbitmq`, its request message also goes to `<prefix>.tests.<instance>.dead` through `delivery.dead_letter()`: literally, a dead-letter queue |
| `reap()` drains the dead queue into `delivery_exhausted` gates | the service's reconcile tick (`reconcile_interval_seconds`, default 30) drains its dead queue. A message whose request already has a dead-letter record is acknowledged. One without a record is a crash that happened before anything could be written, and becomes a record with the reason `exceeded the delivery limit (<n> deliveries)` |
| the job moves to `awaiting_human`; it holds no worker | the key is **parked**: every new request for it is answered `parked` at once and runs nothing (§7). No requester waits for a human |
| "answer anything to retry with a fresh delivery budget" | `vibey test requeue <run_id>` is the grant. It writes an answer marker beside the dead letter (`dead/<run_id>.answer.json`; the dead letter itself is never rewritten), and it submits the same `cwd`, argv and gates with `grant=true` |
| a gate row | a store record. `human_gate.project_id` is `NOT NULL` (`0008:3`), and a test run has no project |

**Crash detection.** It follows from §2. Before each run, the lock holder marks every attempt recorded `running` as `crashed`, then dead-letters it, with the log file that the orphaned child kept writing as evidence. Any requester still waiting on it receives that answer. With `rabbitmq`, the redelivered request of a crashed service finds that dead letter and is answered from it. **It is not run again.** `x-delivery-limit` (default 3) is only the backstop for a service that dies before it can write a record.

**Evidence kept with every dead letter.**

- the request (cwd, argv, gates, requester, and pass-through variable names, never their values);
- the key and all its components;
- the exit code or signal, and `timed_out`;
- `started_at`, `finished_at` and the duration;
- the last `output_tail_bytes` (default 64 KiB) of output, and the path of the full log;
- `os.getloadavg()` at the start and at the end, and `os.cpu_count()`;
- the tree before and after;
- the instance id, pid and delivery count;
- a one-line reason.

**Seeing them.** `vibey test dead-letters [--json] [--all]` (lane T16) is where a human, or a repair lane reading the JSON, finds them. Retention (`retention_days`, default 14) prunes attempts, logs, data and answered dead letters. An unanswered dead letter is never pruned.

### 10. Who puts runs on the queue

| caller | route | lane |
|---|---|---|
| `git push` | `.pre-commit-config.yaml` `coverage-gates` becomes one request: `uv run vibey test run --gate …×4 -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=`. The separate `test-suite` hook is removed: its one reason, reporting a plain test failure as itself (`:20-23`), is met by the answer, which reports test and gate failures separately | T18 |
| the command line, a reviewer | `vibey test run …`, or a plain `uv run pytest …` routed by the pytest plugin | T15, T07, T17 |
| a storm lane (a model running `uv run pytest …`) | the plugin, switched on by `vibey_harness_route` in the root `[tool.pytest.ini_options]`. The lane's clone carries that setting, so **the model needs to know nothing**. A tenant-directory run reads its tenant's ini, and is routed by `VIBEY_HARNESS_ROUTE` in the engine's environment | T07, T28, T26 |
| engines that vibey launches (BUILD sessions, loop services) | `EngineProcessLauncher`'s environment overlay exports `VIBEY_HARNESS_ROUTE` and `VIBEY_HARNESS_WAIT_SECONDS` when `[test_harness] route_engines` is not `off` | T26 |
| `build.verify` in a vibey worktree | the plugin, through that worktree's ini | T07 |
| CI root jobs (`gates`, `noloss`, `postgres-compatibility`) | `uv run vibey test run --backend local --fresh --full-output -- …`. `--full-output` prints the whole log, so `noloss`'s Hypothesis statistics are never cut to the output tail. The four `coverage report` steps are unchanged, because §8 restores `.coverage` | T19 |
| CI tenant rows | unchanged. Their venvs are built with plain pip and hold no vibey, and each row is a separate machine | — |

**The pytest plugin** is `vibey.cli.pytest_route:PLUGIN`. It is a class instance registered through a `pytest11` entry point in the root `pyproject.toml`, so no module-level hook functions are needed (9.b). It implements two hooks:

- `pytest_addoption` registers the ini key `vibey_harness_route`, which takes `off`, `locked` or `queue` and defaults to `off`.
- `pytest_cmdline_main` is `tryfirst`, so it runs before any `pytest_configure`: no conftest has built a database yet.

The mode is resolved as follows:

- `VIBEY_HARNESS_ROUTE` beats the ini.
- `VIBEY_HARNESS_RUN` in the environment means "I am inside a run", and the plugin passes through. The harness sets it in every child, and `locked` mode sets it in its own process, so xdist workers and nested pytest invocations never re-enter.
- `--help`, `-h`, `--version`, `-V`, `--fixtures`, `--fixtures-per-test`, `--markers`, `--collect-only` and `--co` always pass through.

The three modes:

- `off`: nothing happens.
- `locked`: take the machine lock (§2), bounded by the wait, then let pytest run in this process. This is *serialize only*: no store and no reuse.
- `queue`: build a request from `config.invocation_params.args` and `.dir`, put it on the queue, print the answer (§11), and return its exit code, so pytest itself runs nothing.

The plugin loads wherever vibey is installed. It is inert unless an ini or the environment switches it on, and `-p no:vibey_harness_route` removes it.

**The escape hatch.** `VIBEY_HARNESS_ROUTE=off` bypasses routing, the way `git push --no-verify` bypasses a hook (ADR-0028). It exists because a lane that breaks the harness itself must still be able to run its own tests. When the ini says otherwise, the plugin prints one line naming the bypass.

### 11. Waiting, and the 120-second shell

A request has three bounds, all of them keys:

| bound | default | exceeded means |
|---|---|---|
| `queue_wait_seconds` | 3600 | the run could not start: the lock wait (`local`) or `start_by` (`rabbitmq`). The answer is `saturated`, with exit 75. It is not a dead letter |
| `run_bound_seconds` | 3600 | the run is killed, and it is `timed_out`, a dead letter |
| `wait_seconds` (`VIBEY_HARNESS_WAIT_SECONDS`) | 7200 | the **requester** stops waiting. The answer is `still running`, with exit 75: "run the same command again to receive its result". **The run continues**, because the instance is detached or is the service, and a requester's death never cancels a run |

qwenloop kills a shell command after 120 s (`tools.py:55`), and a full suite does not fit in that. Two changes answer this:

- The engine overlay sets `VIBEY_HARNESS_WAIT_SECONDS` below the shell's limit (`engine_wait_seconds`, default 110). The model then reads a clear "still running" line instead of a killed command, and its natural retry is answered by coalescing or from the record.
- qwenloop's shell timeout becomes a key (`shell_timeout_seconds`, `QWENLOOP_SHELL_TIMEOUT_SECONDS`, lane T20). A hard-coded 120 is a 12.c defect in its own right.

A human who stops a run that is no longer wanted sends the holder `SIGTERM` (`vibey test status` prints the pid). The instance kills the run's process group and records the run `abandoned`.

`vibey test run` exits with:

- the recorded pytest exit code for `passed` and `failed`;
- 1 when only a gate failed;
- 75 for `saturated` and `still running`;
- 3 (`EXIT_BLOCKED`, `src/vibey/cli/errors.py:35`) for `parked` and for any dead-letter outcome.

The first line always reads: `vibey test-harness: backend=<b> run=<run_id> key=<first 12> <executed|reused|flaky|parked|saturated|still running>`.

### 12. Topology (the `rabbitmq` backend)

Names use `[bus] prefix` and vhost (lane R01), resolved by lane R17's `QueueBackendSettings`. `<instance>` is `[test_harness] instance`: the host name, lower-cased with every other character turned into `-`, or `cluster` in the chart.

| object | type | arguments / bindings | purpose |
|---|---|---|---|
| `<prefix>.tests` | direct exchange, durable | — | requests |
| `<prefix>.tests.<instance>` | quorum queue | routing key `<instance>`; `x-single-active-consumer: true`, `x-delivery-limit` (`delivery_limit`), `x-dead-letter-exchange=<prefix>.tests.dlx`, `x-dead-letter-strategy=at-least-once`, `x-overflow=reject-publish`, `x-consumer-timeout=(run_bound_seconds + 600) × 1000` | one queue per machine. Its single active consumer is the instance; a second service on the machine is a hot standby that executes nothing |
| `<prefix>.tests.dlx` | direct exchange | — | poison |
| `<prefix>.tests.<instance>.dead` | quorum queue | routing key `<instance>` on the DLX | dead letters in transit to the store (§9) |
| requester reply queue | exclusive, auto-delete, server-named | named in `reply_to` | the answer |

A request is published with `message_id = correlation_id = request_id`, persistent, mandatory, with publisher confirms, and **no expiration**. `start_by` travels in the body, as in ADR-0044 §13. The service writes the answer to the store, **then** publishes it, **then** settles the delivery: `complete()`, or `dead_letter()` for the three dead-letter outcomes. A redelivered request whose answer already exists is re-answered from the store and completed. `auto` asks `consumer_count()` of the queue before it publishes (§13, lane T21).

### 13. Where the code lives, and why

| layer | modules (new unless noted) | lanes |
|---|---|---|
| `domain/` (pure) | `test_harness.py`: `CoverageGate`, `TestSelection`, `EnvNamePatterns`, `TestEnvironment`, `TestRunKey`, `TestOutcome`, `TestOutcomePolicy`, `TestRouteMode`. `test_reuse.py`: `RecordedAttempt`, `ReuseDecision`, `TestReusePolicy`. `test_harness_protocol.py`: `TestRunRequest`, `TestRunResult`, `GateReport`, `AnswerStatus`, `TestHarnessCodec`. `test_run_record.py`: `TestRunRecord`, `MachineLoad`, `DeadLetter`, `TestRunRecordCodec`. `config.py` (edited): `TestHarnessConfig`. Each has an interface under `domain/interfaces/` | T01–T05 |
| `infrastructure/test_harness/` | `settings.py`, `machine_lock.py`, `tree_digest.py`, `environment_probe.py`, `file_store.py`, `executor.py`, `coverage.py`, `instance.py`, `local_client.py`, `amqp_topology.py`, `amqp_service.py`, `amqp_client.py`, `backend.py`, `routing_env.py`, each with its interface in `infrastructure/test_harness/interfaces/`, which joins `.importlinter`'s `infrastructure-interfaces-declare-only` contract | T05–T14, T22–T26 |
| `cli/` | `test_harness.py` (`vibey test run\|status\|dead-letters\|requeue`, `vibey test-harness execute\|serve`), `pytest_route.py` (the plugin) | T07, T15–T17, T25 |
| `bootstrap.py` | `build_test_harness(config, environ)`, the composition | T15, T25, T26 |
| `vibey/__main__.py` | `python -m vibey`, the supervisor's argv | T15 |
| `vibey_bootstrap.amqp` (edited) | `consumer_count(queue)`, on the real client and the in-memory double | T21 |

**Why here.**

- **Not vibey-gh.** It is dependency-free and importable from `domain/`, so no AMQP client and no asyncpg probe can live in it. Its hooks are byte-compared templates shared by every adopter (`install.py:639`). The chain those templates already make (ADR-0028) reaches the repository's own framework config, and that is where the routing goes (T18). No vibey-gh template changes.
- **Not a new tenant.** A tenant brings its own pyproject, gates and matrix row (ADR-0022) for code that needs vibey's config, its composition root and ADR-0044's AMQP lanes. ADR-0044 §14 rejected "six serve subcommands" for the same reason, and put its loop services inside vibey.
- **Family first (10.e).** Each capability below comes from the family, not a re-implementation:
  - AMQP transport, settle vocabulary and in-memory double: `vibey_bootstrap.amqp` (R04);
  - the consumer watchdog: `vibey_bootstrap.heartbeat`, through that client;
  - group kill and reap: `ProcessReaper`;
  - git without `GIT_*`: `CleanGitEnvSubprocessExecutor`;
  - AMQP URL, vhost and prefix precedence: R17's `QueueBackendSettings`;
  - the SIGTERM latch and drain: `cli/early_signals.py` and `cli/main.py`'s worker pattern;
  - the clock: `Clock`.
- **The one gap is taught to the family, not worked around.** "Does anyone consume this queue?" is a passive `queue.declare`, and it is added to `vibey_bootstrap.amqp` (T21).
- **No new third-party dependency.** `fcntl`, `hashlib`, `importlib.metadata` and `json` are stdlib. `asyncpg` and `aio-pika` (R03) are already runtime dependencies.

### 14. Configuration (12.c)

`[test_harness]` in `vibey.toml`. Where no file exists, as at this repository's root, the environment and the defaults apply (`TestHarnessSettings.from_sources`, T05). Environment beats file, and file beats default.

| key | default | env | constraint |
|---|---|---|---|
| `backend` | `auto` | `VIBEY_HARNESS_BACKEND` | `auto`, `local` or `rabbitmq` |
| `state_dir` | `$XDG_STATE_HOME/vibey/test-harness`, else `~/.local/state/vibey/test-harness` | `VIBEY_HARNESS_STATE_DIR` | absolute after `~` expansion |
| `root` | `/` | `VIBEY_HARNESS_ROOT` | absolute |
| `instance` | host name, sanitized | `VIBEY_HARNESS_INSTANCE` | `^[a-z0-9][a-z0-9-]{0,62}$` |
| `command` | `["uv","run","--no-sync","pytest"]` | — | non-empty |
| `coverage_command` | `["uv","run","--no-sync","coverage"]` | — | non-empty |
| `base_env` | `PATH HOME USER LOGNAME LANG LC_* TMPDIR TZ SHELL TERM XDG_* UV_*` | — | names or `PREFIX*` |
| `pass_env` | `VIBEY_TEST_* VIBEY_QUEUE_BACKEND VIBEY_ENGINE_INVOCATION PYTEST_ADDOPTS` | — | names or `PREFIX*`; never a `VIBEY_HARNESS_*` name |
| `database_env` | `VIBEY_TEST_DATABASE_URL` | — | a name, or `""` to disable the probe |
| `tree_exclude` | `[".hypothesis/"]` | — | relative paths |
| `pass_ttl_seconds` | 86400 | — | ≥ 0 |
| `fail_ttl_seconds` | 900 | — | ≥ 0 |
| `run_bound_seconds` | 3600 | — | ≥ 60 |
| `queue_wait_seconds` | 3600 | — | ≥ 1 |
| `wait_seconds` | 7200 | `VIBEY_HARNESS_WAIT_SECONDS` | ≥ 1 |
| `output_tail_bytes` | 65536 | — | 1024–10485760 |
| `retention_days` | 14 | — | ≥ 1 |
| `delivery_limit` | 3 | — | 1–100 |
| `reconcile_interval_seconds` | 30 | — | ≥ 1 |
| `route_engines` | `off` (the last lane, T28, makes it `queue`) | — | `off`, `locked` or `queue` |
| `engine_wait_seconds` | 110 | — | ≥ 1 |

Per invocation: `VIBEY_HARNESS_ROUTE` (the plugin's mode), `VIBEY_HARNESS_FRESH=1`, and `VIBEY_HARNESS_RUN`, the internal marker. The `VIBEY_HARNESS_*` prefix is deliberately outside the default `pass_env` pattern `VIBEY_TEST_*`, so harness settings never change a key.

### 15. Order: serialize first, then queue

The machine lock and the plugin's `locked` mode land early (lanes T06–T07), and the root ini is set to `locked` in the same lane. Every root pytest run on a machine, from hooks, lanes, humans and CI, is serialized from that merge on. That is 8.e's "one at a time", delivered before any queue exists. The queue, the store, reuse and dead letters follow. The last lane (T28) moves the ini to `queue` and `route_engines` to `queue`. Every step is reversible by one key (CDD, 9.c).

## How each non-negotiable still holds

1. **Never block a worker on a human.**
   - Nothing waits on a person. The waits are all on machines, and all three are bounded (§11).
   - A parked key is *answered* `parked` at once. A BUILD session whose tests crash the harness receives a failing command and a reason, and its own ladder (ADR-0024) decides what happens next.
   - The requeue is a grant a human *may* give. Nothing is held until they do.
2. **Credits ≠ rate limit.** Untouched. The harness has no capacity model, reads no engine events, and carries no `resets_at` anywhere. Its codecs reject unknown keys, so none can be smuggled in.
3. **A capacity rejection outranks a completion claim.** Untouched. An answer reports an exit code and an outcome of a *test run*, never an engine's completion. A routed `pytest` inside an engine session returns the same exit code a direct run would, and the session's verdict logic is unchanged.
4. **`domain/` stays pure.** The domain modules use dataclasses, `hashlib` and `json` only, and `now` is always an argument. `tests/domain/test_domain_purity.py` walks them.
5. **Dogfood the family.** See §13. The one gap, `consumer_count`, is taught to `vibey_bootstrap.amqp`. CI's root jobs run the harness they ship (10.e: "in CI"), and hooks run it on every push.
6. **Everything-as-code, never less configurable (12.c).**
   - Every tunable is a key (§14).
   - The routing of hooks, lanes and humans is declared in tracked files: `.pre-commit-config.yaml` and the root `[tool.pytest.ini_options]`.
   - The topology is declared by code at start.
   - Harness concurrency is the one number that is not a key, because 8.e fixes it (§1).
   - Nothing that was configurable becomes less so.
7. **A governing rule is a ratified sub-doctrine.** This record implements 8.e and does not replace it. 8.e must be ratified, with the amendment asked for below, before the last lane (T28) makes queue routing the default. Until then, the lanes land behind `off` and `locked`, and `locked` is already required by 8.c's reading of "one instance".
8. **CDD.** Serialize first, then queue, with one key flipped at a time (§15). The instance's tests (T13) and the service's tests (T23) drive the same `HarnessInstance`, so the two backends cannot drift apart in what a run means.
9. **Status is evidence-bounded (10.f).**
   - A reused answer says `reused`, with `recorded_at` and the run id. It never passes for a fresh run.
   - `flaky` is contradictory evidence, and it forces a run.
   - A tree that changed during a run is not reusable.
   - `still running` and `saturated` are not failures and not passes: exit 75.
   - This record names its cutoff (`702b1490`).
10. **Code lives in classes with interfaces (9.b, ADR-0016).**
    - Every new class has its mirrored interface.
    - The plugin is a class instance, not module-level hook functions.
    - The unavoidable module-level code is `vibey/__main__.py`'s entry call, the plugin's `PLUGIN = PytestHarnessRoute()` binding, and the thin typer command functions, which hold no logic, as `cli/ledger_search.py:275-276` already does. Each carries its reason at the definition.
11. **The handoff no-loss gate.** Untouched.
12. **Every job is idempotent under replay.**
    - A redelivered request is answered from the stored answer, or from the dead letter its crash left. It is never run twice for one request id.
    - Two requests with one key are answered once while the record is valid (§7).
13. **The ledger is append-only.**
    - Harness records are not the ledger. Like `job` rows, an attempt is mutable while it is `running`.
    - After it is terminal it is never rewritten.
    - An answer to a dead letter is a new file.
14. **Conventional Commits; never implement on `main`.** Every lane commits locally on its storm branch.

## Where the drafted rule conflicts or falls short (stated plainly)

1. **Evidence 1 is not removed by 8.e.**
   - A timing test failing beside a local model server is contention between *two different loops*: the qwenloop instance under 8.c and the test harness under 8.e. Neither rule serializes one against the other.
   - The harness records the machine load at the start and end of every run, so such a failure is visible in the record.
   - A rerun that disagrees marks the key `flaky` and stops reuse.
   - But the contention itself remains. Removing it needs a new rule: for example, "a test run and a local model run never share a machine at once", with the loop service and the harness taking one machine lock. That trades storm throughput for test stability, so it is the operator's decision. This record does not make it.
2. **"A repeat request receives the recorded result" has no expiry in the draft.**
   - Replaying a recorded FAIL forever would make one flake permanent.
   - Replaying a recorded PASS forever would hide a flake that passed by luck.
   - This record adds validity windows, flaky re-execution, `--fresh` and CI's always-fresh (§7).
   - The ratified text should say "…receives the recorded result **while that result is valid** instead of a second execution".
3. **CI is two different things.**
   - On GitHub-hosted runners, every job is its own machine and runs its steps in sequence, so 8.e already holds there by construction. Routing the root jobs through the harness is for 10.e ("in CI") and for 8.b's sovereign default, self-hosted Forgejo runners, where jobs *do* share a machine.
   - A verifier must never be answered from a cache, so CI sends `--fresh` on every request. That is an explicit exception to the repeat-request clause, and it should be ratified as one.
   - The tenant rows cannot reach the harness at all (plain pip, no vibey). They comply only because each row is its own machine.
4. **The lock is advisory.** "Nothing starts a second test run" holds for every path vibey controls: hooks, `vibey test run`, the plugin wherever vibey is installed, engines vibey launches, and CI's root jobs. It cannot hold for a process that never asks:
   - `python -m pytest -p no:vibey_harness_route`;
   - `VIBEY_HARNESS_ROUTE=off`;
   - `git push --no-verify`;
   - a tenant-directory run without the environment variable;
   - a test command that is not pytest.

   This is the same posture as ADR-0028's hooks. It is a gate that can be bypassed in an emergency, because a gate that cannot be gets uninstalled.
5. **Adopter projects are outside this design.** Engines that build an adopter's repository run that project's tests in a venv without vibey, and often with a command other than pytest. The core is command-generic: the key takes any command, and classification is a policy. But the only transparent route built here is pytest's. The general case needs an out-of-tree shim, a standalone plugin module on `PYTHONPATH` plus `PYTEST_PLUGINS`, and per-ecosystem outcome policies. That is a follow-up, and until it lands, 8.e binds vibey's own tests and Python projects with vibey installed.
6. **The storm driver is not in the tree.** `storm-queue.sh` and `qwenlane.py` live in the operator's scratch directory, so their environment cannot be declared in the repository (12.c). Root-directory runs in a lane are routed by the ini the clone carries. Tenant-directory runs in a QwenStorm lane need `VIBEY_HARNESS_ROUTE=queue` exported by the driver, which is an operator step, not a lane.
7. **8.e's "queue on the bus surface" and a machine without a broker.** `auto` degrades to the lock with an announcement (§3). The operator required that this be possible. The ratified text may want to name it: "…from a queue on the bus surface, or, where the machine has no bus, from the machine's lock".

## Security impact

- **The broker is an execution capability.** Anyone who can publish to `<prefix>.tests.<instance>` can make that machine run the configured test command in any `cwd` under `[test_harness] root`, which executes that tree's code. That is the same class of capability as ADR-0044's run queues, with the same mitigations:
  - broker credentials are secrets;
  - the objects live under vibey's prefix and vhost;
  - `root` bounds `cwd`;
  - the command comes from the instance's configuration, never from a message;
  - only `pass_env` names are accepted from a message.
- **Values of pass-through variables are sensitive.** A test DSN carries a password, for example.
  - They travel in the request (the local request file sits under `state_dir`, which is created `0700`), and they reach the child.
  - They are **never** written to a record, an answer or a dead letter. Those keep the names and sha256 digests only.
- **Logs are written `0600`.** They hold whatever the tests print, as the terminal would.

## Migration

- Until lane T07, nothing changes.
- From T07 on, every root pytest run takes the machine lock. A second run on the same machine waits, which is the rule. `VIBEY_HARNESS_ROUTE=off` bypasses it in an emergency.
- From T18 on, a push runs one gated request instead of the suite twice. `SKIP=coverage-gates git push` remains the framework's own bypass.
- From T28 on, root pytest runs are queued requests. The `.coverage` a later `coverage report` reads is the answering run's (§8).
- No data migration is needed. The store is created on first use and pruned by retention.

## Consequences

**Good.**

- One test run at a time per machine, across hooks, lanes, humans, reviewers and CI, with the machine lock as a floor that works with no broker at all.
- A push runs the suite once, where the framework config's own comment records it running two or three times.
- Coverage shards cannot collide, even in principle.
- An unchanged input is answered from its record, which matters most in storms, where a model re-runs the same command.
- Flakes become visible as contradictory evidence instead of being flattened into pass or fail.
- Crashes and timeouts become records a human or a repair lane can act on, and are never retried in a loop.
- A requester that times out, like qwenloop's shell, no longer wastes the run it started.

**Bad.**

- Every routed run pays for a working-tree digest, an environment probe (one database round trip) and a supervisor spawn. That is on the order of a second, which matters for a one-test run.
- A cached PASS is only as good as the key. Anything the key cannot see (the kernel, `PATH` tools, the clock, network services other than the test database) can drift for up to `pass_ttl_seconds`.
- Detached supervisors outlive a Ctrl-C. A human must `kill` the holder to stop an unwanted run.
- The lock serializes *everything* on the machine, so a quick targeted run waits behind a full suite. Ordering among lock waiters is not FIFO (`flock` gives no order). The `rabbitmq` backend is FIFO among queued requests, but not relative to `local` waiters.
- There is more state on disk. Retention bounds it.
- The pytest plugin is loaded in every environment where vibey is installed, including adopters'. It is inert there, but it is an import at every pytest start.

## Alternatives rejected

- **A `pytest` shim on `PATH`.** `uv run` puts the project venv's `bin` first, so the shim never runs for `uv run pytest`, the command lanes actually use. `python -m pytest` bypasses it too.
- **A `uv` shim.** It catches `uv run pytest`, but not `.venv/bin/pytest` or `python -m pytest`, and it shadows the operator's real `uv`.
- **Routing inside qwenloop's shell tool.** That is one runner of six. It would put vibey's harness protocol into a runner tenant (ADR-0022; ADR-0044 §13 keeps tenants untouched), and every other engine's shell would still run pytest directly. The plugin routes all of them without their knowing.
- **The harness inside vibey-gh.** It is dependency-free and importable from `domain/`, and its hooks are byte-compared templates for every adopter (§13).
- **A new tenant.** It would add a pyproject, gates and a matrix row for code that needs vibey's config, composition root and AMQP lanes.
- **Only a file lock.** That meets "one at a time", but not "takes its work from a queue on the bus surface". It has no order, no visibility beyond one holder, no cluster story, no idempotency and no dead letters. It is the floor and the fallback here, not the design.
- **A queue without a machine lock.** It would let a `local` requester and the service run at once, and it could not detect a crash without pid probing. The lock is what makes `auto` safe.
- **Keying by request id, or by HEAD's tree id.** A request-id key re-executes every repeat. A HEAD tree id misses uncommitted edits and new test files, which is exactly what a lane tests.
- **The lockfile hash as the environment.** `uv.lock` is already in the tree. What the run imports is the installed distributions.
- **Caching FAILs forever, or never.** Forever makes a flake permanent. Never re-runs an unchanged failing command that a model repeats. A short window plus flaky detection is the bounded middle.
- **PostgreSQL as the store.** See §3: records are per machine, the push path must not need the operator database, and one store keeps both backends coherent. The port admits a PostgreSQL adapter later.
- **`human_gate` rows for dead letters.** `project_id` is `NOT NULL` (`0008:3`).
- **A delivery budget that retries crashes.** The rule sends a crash to the dead-letter queue. Retrying a run that OOMs the machine is the unbounded ladder ADR-0024 rules out. `x-delivery-limit` is only the backstop for a crash before any record exists.
- **Harness concurrency as a key.** 8.e fixes it at one (§1).
- **Keeping both `test-suite` and `coverage-gates` hooks.** Under the harness they would be two different selections, and so two runs. One gated request reports both failure kinds.

## Verification owed at implementation

Each item is recalled from upstream behaviour at design time, and is asserted by a test in the lane that relies on it, so a disagreement fails a lane rather than a push:

- an `flock` held through a descriptor passed to a child survives the parent's SIGKILL, and is released when the last holder exits, on macOS and Linux (T06);
- `pytest_cmdline_main` with `tryfirst=True` on an entry-point *object* plugin runs before any conftest's `pytest_configure`, and its return value becomes the exit code (T07 `locked`, T17 `queue`);
- output printed from `pytest_cmdline_main` reaches the terminal, because global capture is suspended after the initial conftests (T17, end to end);
- pytest-cov honours `COVERAGE_FILE` under xdist with `parallel = true`: the shards and the combined file land beside it and nowhere in `cwd` (T11);
- the locked coverage version accepts `coverage report --data-file=…`, and exits 2 below `--fail-under` (T12);
- `uv run --no-sync pytest` from a workspace member's directory runs against the workspace venv (T11; skipped when `uv` is absent);
- `git ls-files -m -d -o --exclude-standard` together with `git hash-object` reproduce `git add -A`'s view, including deletions and untracked files (T08, against a scratch repository);
- quorum queues accept `x-single-active-consumer`, and a second consumer stays idle (T22, integration);
- a passive `queue.declare` returns the consumer count on the pinned `rabbitmq:4-management-alpine` image (T21, integration).
