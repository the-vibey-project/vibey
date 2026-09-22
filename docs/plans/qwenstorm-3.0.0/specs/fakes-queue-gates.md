## Title
test(fakes): the in-memory queue and gates behave like PostgreSQL's: dependencies, run_after, priority, reap, fencing, idempotency

## Why
`FakeJobRepository` (`tests/fakes/queue.py`, moved there by `fakes-registry` from
`tests/application/fakes.py:16-222`) is the queue that the worker, handler and system tests
run on. ADR-0044 says so: "The system tests run on `FakeJobRepository`". It differs from
`PostgresJobRepository` (`src/vibey/infrastructure/db/job_repository.py`) wherever a test
does not happen to look:

| operation | PostgreSQL | the fake today |
|---|---|---|
| `enqueue` | idempotent on `(project_id, idempotency_key)`, records `depends_on` and `depends_on_keys` (`:49-160`) | creates a new job on every call and records no dependencies |
| `claim` | only `ready` jobs with `run_after <= now()` whose dependencies have all `succeeded`, ordered `priority DESC, run_after ASC, id ASC` (`:178-208`) | the first `ready` job in dict order, ignoring all three |
| `reap` | re-readies every `leased` job whose lease expired, and returns the count (`:311-320`) | returns `0` |
| `heartbeat`, `defer` | refused unless `state='leased'` (`:210-221`, `:287-309`) | accepted in any state |
| `nack` | backs `run_after` off by `min(2**attempts * 2 s, 15 min) * random()` (`:237-256`) | leaves `run_after` alone |
| `queue_depth` | zero-fills every `JobState` (`:353-362`) | only the states present |

`FakeHumanGateRepository` is short one method: it has no `get`, which Postgres has at
`human_gate_repository.py:88`. Its `answer` does not re-ready the parked job
(`:61-86`: `UPDATE job SET state='ready' WHERE id=$1 AND state='awaiting_human'`), and
an unknown gate raises `StopIteration` instead of `LookupError`.

A fake that is kinder than the real queue lets bugs pass. This lane makes both fakes behave
like PostgreSQL, over one shared in-memory store, the way the two Postgres repositories
share one database.

## Required behaviour
1. **`class InMemoryQueueStore`** in `tests/fakes/queue.py` is the shared state:
   - `jobs: dict[UUID, JobRecord]`;
   - `dependencies: dict[UUID, tuple[UUID, ...]]`;
   - `gates: dict[UUID, HumanGateRecord]`;
   - `notified: list[UUID]`, the project ids announced, standing in for `NOTIFY vibey_job_ready`.
   Its `__init__` takes these keyword arguments:
   - `clock: Clock | None = None`: `vibey.application.interfaces.system.Clock`. The default
     is a private `_UtcClock` class with `now()`;
   - `jitter: Callable[[], float] | None = None`: the stand-in for `random()`, whose default
     returns `0.5`;
   - `on_ready: Callable[[UUID], None] | None = None`: called with a project id whenever a
     job becomes claimable (enqueue, answer, reap). `fakes-job-wakeup` wires the notifier
     through it.
2. **`FakeJobRepository(jobs: list[JobRecord] | None = None, *, store: InMemoryQueueStore | None = None)`**
   keeps its existing call signature, `self.calls` and `self.dependencies` (a view of
   `store.dependencies`). Every method uses `store.clock.now()` wherever SQL says `now()`.
   - `enqueue` follows the same rules as `enqueue_batch`, for one request. An existing
     `(project_id, idempotency_key)` returns the existing record unchanged. It resolves
     `depends_on_keys` against committed jobs; a key naming nothing raises `LookupError`,
     and nothing is written. It stores the dependencies, and it appends `project_id` to
     `notified` and calls `on_ready`.
   - `claim` returns `None` unless there is a job with:
     - `project_id` equal to the argument;
     - `state is JobState.READY`;
     - `run_after <= now`;
     - every dependency's state `is JobState.SUCCEEDED`.
     Among those it takes the minimum of
     `(-priority, run_after, str(id))`, sets `state=LEASED`, `lease_owner`,
     `lease_expires_at=now+lease` and `attempts+1`, and returns it.
   - `heartbeat` and `defer` also require `state is JobState.LEASED`, and so does
     `assign_engine` (it already does).
   - `nack`:
     `run_after = now + min(timedelta(seconds=2) * 2**attempts, timedelta(minutes=15)) * jitter()`.
   - `reap` re-readies each `LEASED` job with `lease_expires_at < now`: `state=READY`,
     `lease_owner=None`, `lease_expires_at=None`. It calls `on_ready` for each project and
     returns the count.
   - `queue_depth` returns `{state: 0 for state in JobState}` updated with the counts.
   - `list_for_cycle` sorts by `(created_at, str(id))`.
   - Every write sets `updated_at=now`.
3. **`FakeHumanGateRepository(*, store: InMemoryQueueStore | None = None)`**.
   - Existing callers construct it with no arguments. Each such fake gets its own store.
     Pass one store to both fakes to link them.
   - It keeps `raised` (a list property ordered by `raised_at`) and `calls`.
   - It adds `get(gate_id)`.
   - `answer` on an unknown gate raises `LookupError(f"answer: no gate {gate_id}")`. When the
     gate has a `job_id` whose job is `AWAITING_HUMAN`, the job becomes `READY` and `on_ready`
     fires.
   - `open_for_project` sorts by `(raised_at, str(gate_id))`.
   - `latest_for_job` takes the maximum by `(raised_at, str(gate_id))`.
4. **`make_job`** gains an optional `run_after: datetime | None = None` and
   `priority: int = 0`, so that tests can build ordering cases.
5. **Behaviour that existing tests rely on stays.** If an existing test fails because it
   relied on a kindness listed in the table (for example, it claims a job it enqueued with a
   future `run_after`), fix the test's inputs and never the fake. List every such test in the
   commit body.

## Where to change
- `tests/fakes/queue.py`.
- `tests/fakes/registry.py`: the `REGISTRY` entries stay. Add `build=lambda: FakeJobRepository()`
  if the lambda form differs.
- New `tests/fakes/test_fake_queue.py`.

## Acceptance criteria
- [ ] Every test named below passes, and each asserts the same outcome as its PostgreSQL
      twin in `tests/infrastructure/db/test_job_repository.py` or
      `tests/infrastructure/db/test_human_gate_repository.py`.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application tests/system tests/fakes` passes.
- [ ] `tests/fakes/test_port_parity.py` passes, including the signature parity.

## Tests to write first (TDD)
`tests/fakes/test_fake_queue.py` mirrors the names of the PostgreSQL tests it shadows, using a
`_FrozenClock` it can advance (a small class in the test file):
- `test_enqueue_is_idempotent`
- `test_claim_leases_the_highest_priority_ready_job`
- `test_claim_skips_a_job_whose_run_after_is_in_the_future`
- `test_dependency_gating_blocks_claim_until_dependency_succeeds`
- `test_heartbeat_fails_for_wrong_owner_or_unleased_job`
- `test_nack_reschedules_with_bounded_backoff`
- `test_nack_marks_failed_once_max_attempts_reached`
- `test_grant_attempts_never_narrows_the_bound`
- `test_defer_capacity_releases_lease_without_consuming_attempt`
- `test_reap_reclaims_expired_leases_and_counts_them`
- `test_queue_depth_returns_all_zeros_for_empty_project`
- `test_enqueue_batch_rolls_back_when_a_key_names_no_job`
- `test_list_for_cycle_scopes_by_project_cycle_and_kind_oldest_first`
- `test_answer_re_readies_the_parked_job_and_announces_it`
- `test_answer_unknown_gate_raises_lookup_error`
- `test_gate_get_open_and_latest_ordering`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" tests/application tests/system tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- `JobReadyNotifier` and `JobHandlerFactory` (`fakes-job-wakeup`).
- The shared contract suite that runs the fake against PostgreSQL (`fakes-contracts-repositories`).
- Changes the RabbitMQ lanes make to the `JobRepository` port. If an R-lane has already changed
  `vibey.application.interfaces.queue.JobRepository`, the fake follows the port as it is on
  the integration branch.
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry`.
- **Files touched:** `tests/fakes/queue.py`, `tests/fakes/test_fake_queue.py` (new),
  `tests/fakes/registry.py`, and any test whose inputs relied on a kindness (behaviour 5).
- **Must keep passing unchanged:** the protected tests, `tests/system/test_delivery_stage_set.py`
  (which uses its own in-memory classes), and `tests/fakes/test_port_parity.py`.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
