# Amendment to draft ADR-0045 — every seam has an in-memory fake, and the default run needs nothing outside the process

*Append this below the draft's "Verification owed at implementation" section in
`specs/ADR-test-harness-queue.md`.*

**Status:** proposed, with the draft · **Date:** 2026-09-22 · **Cites:** sub-doctrines 9.b
("substitution happens at the declared seam, never by patching an import … the test double is
the second, and it exists from the first day"), 8.e (ratified: see
`src/vibey_tools/gh/docs/doctrines.md:271-293` on the integration branch, which carries the
validity clause this record asked for), 10.e, 10.f, 12.c · **Related:** ADR-0002 (PostgreSQL,
never SQLite), ADR-0016, ADR-0022, ADR-0023 (four layers, four 100% floors), ADR-0042 (the
sovereign surfaces), ADR-0044 §16 (one suite binds both implementations) · **Evidence:** the
storm integration clone at `c91561f4`, read 2026-09-22 · **Lanes:** `specs/fakes-*.md`, and
the queue in `specs/fakes-queue.txt`.

**The rule this implements, stated by the operator:** "the test harness always needs to create
comprehensive fakes for all interfaces at all times", and "these fakes run in memory so that no
outside thing is ever needed in order to run tests". It is met **in code**. Where it is already
law, the law is 9.b's double-from-day-one and no-import-patching. This amendment does not
change any canon text. The in-memory, no-outside-service half is not yet written in the canon.
Whether to write it, for example as one sentence added to 9.b, is the operator's decision
(CLAUDE.md: "a governing rule is a ratified sub-doctrine").

## A1. Two tiers, and the default one needs nothing outside the process

- **The default tier** is what a bare `pytest` runs in any package. It needs nothing that is not
  in the process or on its local disk:
  - no PostgreSQL, RabbitMQ, Redis, Ollama, llama-server or vLLM;
  - no Docker or Podman;
  - no network beyond loopback to a peer the test itself started;
  - no engine CLI (`claude`, `codex`, `cursor-agent`, `gemini`, `agy`), no `az`, no `kubectl`.

  The following are *inside*:
  - `tmp_path`;
  - a child of the test's own interpreter (`sys.executable`);
  - `git`;
  - the in-tree loop binaries, which are this repository's code.
- **The opt-in tier** is marked `integration` in the root suite and in vibey-bootstrap, and
  `network` in vibey-gh (the precedent: `src/vibey_tools/gh/pyproject.toml:77-80`, "every branch
  a `network` test touches must also be reached offline").
  - Its services are named by `VIBEY_TEST_*` variables, which are already in the harness's
    `pass_env` (§14).
  - A test whose variable is unset is skipped with a message naming the variable.
  - `addopts` deselects the tier (`fakes-ci-no-services`), so opting in is always explicit:
    `-m integration`.
- **Enforced, not remembered.** A `sys.addaudithook` guard (`fakes-isolation-guard`) fails a
  default-tier test at the moment it tries to connect to a non-loopback address or to
  PostgreSQL's Unix socket, or to spawn a listed service or engine binary. The list is
  `[tool.vibey.test_isolation]` in `pyproject.toml` (12.c). No module is patched: audit hooks
  are the interpreter's declared observation seam (PEP 578).
- **Before the flip, the database is lazy.** The root conftest builds its per-worker database
  only when the session selected an `integration` item (`fakes-harness-decouple`). It also fixes
  a live bug: `pytest_collection_modifyitems` in `tests/infrastructure/db/conftest.py:17-19` and
  `tests/contracts/conftest.py:19-21` receives **every** collected item, so in a whole-suite run
  it marked the whole suite `integration`.

## A2. The fakes standard, and the registry that holds it

- **What counts as a substitution seam:**
  - every Protocol in `vibey.application.interfaces` (the ports);
  - every infrastructure-level seam listed in `DRIVER_SEAMS` in `tests/fakes/registry.py`:
    `CommandExecutor`, `UrlOpener`, the SMTP connector, the socket and resolver seams,
    `ProcessSpawnerInterface`, `LedgerRepositoryInterface`, the unit-of-work factory,
    `PostgresConnectorInterface`, `ResourcesFactoryInterface`, `JobWakeupOpenerInterface`,
    the CLI and operator compositions' collaborators, and the harness's seams (A4).
- **What counts as a comprehensive fake.** A plain class with real in-memory behaviour for
  **every** method of its port:
  - no `unittest.mock`;
  - no method body that is only `...`, `pass`, `return None` or `raise NotImplementedError`;
  - its signatures equal the port's, down to parameter names and kinds, defaults, and
    async-ness;
  - it passes **the port's contract suite**, the same suite that binds the real adapter in the
    opt-in tier (A5). Passing that suite is the definition of comprehensive. A fake that is
    kinder than the real adapter fails it.
  - Faults are first-class: a fake can be told to fail on cue (`fail_next_append`,
    `FaultyCloudClient(fail_at=…)`, `unreachable(...)`), so a test never needs a mock to
    simulate an error.
  - Where production already ships an honest in-memory implementation, that implementation
    *is* the registered fake. Examples are the twelve ADR-0042 `InMemory*` surfaces,
    `ScriptedEngine`, `ScriptedDesignProvider` and `InMemoryAzureClientAdapter` (10.e).
  - Where the real class only composes over a store, the fake is **the real class over an
    in-memory store**. For example, `PostgresBuildLedger(InMemoryLedger())`: those views never
    touch a pool.
- **The registry** is `tests/fakes/registry.py`: `REGISTRY`, `EXEMPT` and `PENDING`.
  - `EXEMPT` reasons are closed: a value contract, a class contract, or a pure policy.
  - A `PENDING` entry must name the lane that owes the fake.
  - `tests/fakes/test_port_parity.py` fails when a port is none of the three. From
    `fakes-ci-no-services` on, `PENDING` may only name in-flight harness lanes.
  - Each tenant keeps the same registry in its own test directory (ADR-0022).
- **The ratchet.** `tests/meta/test_patching_ratchet.py` counts, per test file, three things:
  `monkeypatch.setattr`; `patch`, `patch.object` and `patch.dict`; and the mock classes.
  `setenv`, `delenv` and `chdir` are not counted: the environment is a declared seam. It fails
  when any count **differs** from `tests/meta/patching_baseline.json`. So a lane that removes
  patches must write the decrease down, and nothing can add one. The root reaches zero, except
  files named as retiring (opencodeloop). Each tenant carries its own ratchet.
- **The declared seams used** (9.b), none of them an import patch:
  - constructor and keyword injection with production defaults;
  - `click`'s context object (`CliRunner.invoke(..., obj=…)`, found with `find_object`), for
    vibey's `CliComposition` and each runner's CLI;
  - kopf's `memo`, for the operator handlers;
  - httpx's `MockTransport`, for cursorloop;
  - `socket.socketpair()`, for the RESP fake;
  - `build_app(resources_factory=…)`, for the composition root.

## A3. What a fake cannot evaluate, stated plainly

SQLite is forbidden (ADR-0002), and it would answer a different dialect anyway. Two mechanisms
cover `infrastructure/db` in the default tier:
- **An interpreter at the unit-of-work seam** (`fakes-db-unit-of-work`, after `orm-unit-of-work`).
  - It evaluates exactly the SQLAlchemy statement shapes the repositories issue: select,
    insert with on-conflict, update, and delete with returning.
  - It enforces primary keys, uniques, NOT NULL, defaults, and every CHECK constraint of the
    migrations that has a registered predicate. That includes `credits_never_have_a_deadline`
    (`migrations/0007_engine_health_rotation.sql:21`), the database leg of CLAUDE.md's
    "Credits ≠ rate limit".
  - It raises on any construct it does not interpret, naming it.
- **Transcripts, for SQL only PostgreSQL can answer** (`fakes-db-sql-transcripts`): the
  migrator, advisory locks, `append_event()`, `ILIKE … ESCAPE`, and `LISTEN`/`NOTIFY`.
  - The integration tier records each exchange against real PostgreSQL.
  - The default tier replays it and fails on any statement not in the transcript.
  - Each transcript carries a digest of `migrations/*.sql`, so a transcript fails the moment
    the schema moves under it.
  - This is the only fake whose behaviour comes from a recording. Its fidelity is exactly what
    PostgreSQL answered, and no more.
- **What stays PostgreSQL-only**, by design and in the opt-in tier: `test_chaos.py` (protected;
  real concurrency) and the chart's KEDA scaler query.

## A4. The harness is held to the same standard

- The harness's seams join `DRIVER_SEAMS` with in-memory fakes (`fakes-test-harness`):
  `MachineLockInterface`, `TestRunStoreInterface`, `WorkingTreeDigestInterface`,
  `EnvironmentProbeInterface`, the executor, the coverage gates and keeper, and the supervisor
  spawner.
- `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (R04) is the registered in-memory bus fake
  for T21–T24.
- **The standing constraints for T-lanes gain one line:** "A lane that declares a seam
  interface either registers its in-memory fake in `tests/fakes/registry.py` in the same
  lane, or adds a `PENDING` entry naming `fakes-test-harness`."
- The pure policies (`TestReusePolicy`, `TestOutcomePolicy`, the codecs) are `PURE_POLICY`,
  not seams.

## A5. One suite binds the fake and the real adapter

- `tests/contracts/` becomes the definition of each repository port. The `memory` backend runs
  in the default tier, and `postgres` runs under `integration` (`fakes-contracts-repositories`).
  The twelve surface ports have one contract each: `InMemory*` always, and the real adapter when
  `VIBEY_TEST_<SURFACE>_*` is set (`fakes-contracts-surfaces`).
- **R18 conflict.** R18 calls its `rabbitmq-memory` backend "always runs", but that backend
  stores its records in PostgreSQL. Under A1 it is `integration`. `fakes-contracts-queue` adds
  a `memory` backend (`FakeJobRepository` over `InMemoryQueueStore`) as the queue contract's
  default-tier backend. R18's contracts and its chaos twin are otherwise untouched.
- **T19 amendment.** After `fakes-ci-no-services`:
  - `gates` and `noloss` start **no service**. Their `vibey test run --backend local --fresh …`
    wrapping (T19) keeps the default selection;
  - `postgres-compatibility` runs `-m "integration and not paid" tests`. It no longer passes a
    path list without `-m`: `addopts` would deselect the integration tests in those paths and
    the job would pass vacuously;
  - T19's step 4 path list is replaced accordingly;
  - the PostgreSQL 17 row joins `required_checks`.

## A6. How the queue-fed harness runs with nothing outside

8.e's queue is how test runs are dispatched **when the bus exists**. `pytest` in a fresh clone
with nothing running must still pass. Each prerequisite degrades like this:

| missing | what happens | where |
|---|---|---|
| broker | `auto` selects `local`, and the answer's first line names why | §3 (T25), unchanged |
| PostgreSQL | nothing: the default tier does not select it. The key's `database` component is `unset`. T09's `test_database_version_against_the_test_database` becomes `integration`, because it relied on `tests/conftest.py` exporting `VIBEY_TEST_DATABASE_URL` for every session, which no longer happens | A1; `fakes-harness-degrade` |
| a writable `state_dir` (sandboxed or read-only `$HOME`, containers) | `locked` and `queue` print `vibey test-harness: no writable state_dir … ; running directly (not serialised, not recorded)`, and pytest runs in-process | `fakes-harness-degrade` |
| the configured command's executable (no `uv` on `PATH`) | the same announced direct run, instead of an `unexecutable` dead letter and exit 3 | `fakes-harness-degrade` |
| anything else that raises in the harness | T17's exit 3 and bypass message, unchanged: a **broken** harness still never passes silently | T17 |

A **missing prerequisite** is not a broken harness. Its degrade is announced (10.f), so it is
not silent. It is the same posture §3 already takes for the broker. The requester never touches
the database in any mode: T17's `tryfirst` short-circuit runs before any conftest, and the
child builds the database only when it selected `integration` items (A1).

**Ordering.** `harness-T28-route-flip` also depends on `fakes-ci-no-services` and
`fakes-harness-degrade`. Its acceptance line "run twice, `executed` then `reused`" must hold in
a clone with nothing running.

## A7. Edits to the T-lane texts before they are filed

- **Standing constraints:** add A4's registry line. Add: "default-tier tests pass the isolation
  guard (`fakes-isolation-guard`); a test that needs a broker or PostgreSQL is `integration`."
- **T07 and T17:** add the prerequisite check of A6. Or leave it to `fakes-harness-degrade`,
  which verifies that it is present and adds it if not.
- **T09:** mark `test_database_version_against_the_test_database` `integration`, and reword the
  acceptance line that relies on `tests/conftest.py:146-156`.
- **T19:** as A5.
- **T28:** the dependencies and acceptance of A6.

## A8. pgserver, evaluated

`pgserver` (PyPI) ships PostgreSQL server binaries in a platform wheel. It `initdb`s a private
data directory and serves it on a Unix socket. No system install, no Docker and no network are
needed.

- **Does it satisfy "no outside thing"?** Only in the narrow sense that nothing must be
  installed or already running. It is still a PostgreSQL *server process* with on-disk state,
  which is precisely what the operator listed as not allowed in the default run, and it is not
  in memory. So it **cannot** carry the default tier or its 100% floors.
- **Its risks:**
  - native binaries from a single-maintainer third-party wheel, which pip-audit cannot inspect
    beyond its version;
  - one bundled major, 16 at the last release known to this record, where ADR-0002 names 17
    and CI's compatibility matrix spans 14–18;
  - one more dependency, where 10.e asks first whether the family provides it. It does not.
- **Recommendation.** Adopt it only as an **optional convenience for the opt-in tier**:
  - a `pg-embedded` extra, used when `VIBEY_TEST_EMBEDDED_PG=1` and no `VIBEY_TEST_DATABASE_URL`
    is set, printing the major it started (`fakes-embedded-postgres`, **operator-gated**);
  - never a default dependency, never in the default tier, and never in CI, where real 14–18
    service containers remain the conformance evidence.
  It is worth having for storm lanes and laptops that must record SQL transcripts (A3) or run
  `-m integration` without a server. If the operator prefers no native third-party binaries, do
  not file that lane. Nothing else depends on it.
