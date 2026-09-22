## Title
feat(queue)!: RabbitMQ dispatch and loop services are the defaults

## Why
ADR-0044 §1 and §13. By the time this lane runs, the evidence the ADR owes before the
flip has landed and is green:

- the contract suite on both backends (R18);
- the chaos twin (R18);
- the supersede and dedupe tests (R22);
- the cluster contracts (R32);
- a one-command local broker (R33).

This lane changes only defaults, so reverting it restores today's behaviour
completely. That is CDD's bounded divergence (sub-doctrine 9.c).

## Required behaviour
1. `QueueConfig.backend` defaults to `"rabbitmq"`, and `EnginesConfig.invocation` to
   `"service"`. R01's `test_queue_defaults_to_postgres_and_subprocess` is renamed to
   `test_queue_defaults_to_rabbitmq_and_service` and asserts the new defaults. This is
   the only edit to an existing assertion.
2. `tests/conftest.py` `pytest_configure` (`:146-156`) adds, with a comment:
   ```python
   os.environ.setdefault("VIBEY_QUEUE_BACKEND", "postgres")
   os.environ.setdefault("VIBEY_ENGINE_INVOCATION", "subprocess")
   ```
   The comment says the historical suite was written for these, the contract suite
   (R18) proves both backends, and `setdefault` lets CI or a developer run the suite on
   another backend.
3. `QueueBackendNotConfigured`'s message adds a third remedy: `vibey install --rabbitmq`.
4. `values.yaml`: `queue.backend: rabbitmq` and `engines.invocation: service`.
5. `ci.yml`'s existing step "the ScaledObject reconciles against real Postgres"
   (`:973-991`) adds `--set queue.backend=postgres` to its `helm upgrade`, so that step
   keeps testing the PostgreSQL trigger.
6. Regenerate the goldens. `keda-latest` and `keda-project` stay byte-identical,
   because R31 pinned them.
7. The commit carries a `BREAKING CHANGE:` footer. Its text: vibey now needs a
   RabbitMQ broker by default (`VIBEY_BUS_AMQP_URL`); `vibey install --rabbitmq`
   installs one; `VIBEY_QUEUE_BACKEND=postgres` with
   `VIBEY_ENGINE_INVOCATION=subprocess` restores the one-daemon behaviour; and in the
   chart, `keda.enabled` now needs `worker.project` unless `queue.backend=postgres`.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] The whole suite passes with the conftest pin.
- [ ] `VIBEY_QUEUE_BACKEND=rabbitmq VIBEY_TEST_AMQP_URL=… uv run pytest tests/contracts tests/infrastructure/queue` passes against a local broker.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.
- [ ] `git diff --stat` shows no protected file.

## Tests to write first (TDD)
- Rename and update the default test (behaviour 1).
- `tests/test_bootstrap.py`: `test_defaults_without_a_broker_name_all_three_remedies`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    deploy/helm/golden/render.sh
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Docs, ADRs and CHANGELOG (R35).

Do not push. Commit locally as `feat(queue)!: …` with the `BREAKING CHANGE:` footer.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

# Lane R35 — docs-wave (owned by the docs wave, not a 14B lane)

**Lane card.**

- **Depends on:** R34.
- **Wave:** 12.
- **Files touched:** documentation, ADRs and governance only.
- **Must keep passing unchanged:** the doc meta-tests:
  - `tests/meta/test_adr_counts.py` (counts and nav)
  - `tests/meta/test_paper_renders.py`
  - `tests/meta/test_paper_evidence.py`
  - `tests/meta/test_phase_diagram.py`

## Title
docs: ADR-0044, the queue port, RabbitMQ dispatch and loop services

## Why
CLAUDE.md, the ADRs, the data-model and architecture plans, and the paper all state
"PostgreSQL `SKIP LOCKED` is the queue" as a present fact. The docs wave owns those
surfaces (`SPEC-TEMPLATE.md`, *Out of scope*). An ADR that is not in the nav, with
counts that disagree, fails `tests/meta/test_adr_counts.py`.

## Required behaviour
1. Land `specs/ADR-rabbitmq-queue.md` as
   `docs/architecture/decisions/0044-the-job-queue-is-a-port.md`, keeping the status
   *proposed* until the operator merges it. Add it to the `properdocs.yml` nav, and
   update "(N ADRs" to 44 in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
   `docs/index.md`.
2. Status notes:
   - ADR-0002: "superseded in part by ADR-0044 (dispatch); its record-store and ledger
     decisions stand".
   - ADR-0025: the autoscaling trigger is amended by ADR-0044 §12.
   - ADR-0009: an answer also re-dispatches (ADR-0044 §6).
3. `docs/plans/data-model.md`:
   - §1: the requirement table gains a RabbitMQ column.
   - §3.3: `dispatch_seq` and `dispatched_at`.
   - §3.4: add the lease-mapping table (ADR-0044 §5).
   - A new §3.11 for `job_outbox`.
   - §4: notifications in both backends.
   - The relation count in the status note.
4. `docs/plans/architecture-and-roadmap.md`:
   - §4 container view: the broker, the loop services, and replacing "Adapters →
     subprocess" with "→ loop service".
   - The process model.
   - §7.1–§7.4.
5. `docs/paper.md`:
   - *Queue semantics*: two backends. The strict-priority claim holds for PostgreSQL;
     the RabbitMQ ordering is FIFO with best-effort priority.
   - *Validation*: the chaos twin.
   - Keep `test_paper_evidence.py` green.
6. CLAUDE.md, AGENTS.md and GEMINI.md: the "Queue backend" fact, the engines and
   invocation fact, and the commands block. Update the four agent-surface trees
   (`.claude/skills/`, `.cursor/rules/`, `.agents/skills/`, `.agent/rules/`) in the
   same PR: architecture, engine-adapters, testing, quality-gates.
7. `docs/reference/cli.md`: `loop-service`, `loop submit`, `install --rabbitmq`.
8. `docs/reference/configuration.md`: `[queue]`, `[bus]` AMQP keys, `[engines] invocation`,
   `[loop_services]`.
9. `docs/guides/kubernetes.md`: the core broker, the loop services, worktree access
   modes, and the KEDA requirement.
10. `CHANGELOG.md`, through the release tooling's usual path.
11. **Owed to the operator, not writable by this lane:** an amendment to sub-doctrine
    8.b (`src/vibey_tools/gh/docs/doctrines.md:109-142`, plus `corpus-index.json`) that
    names the Bus surface and its RabbitMQ default. ADR-0044 flags that the operator's
    decision cites a ratification the canon does not record.

## Where to change
- The files listed above.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.
- [ ] The book and paper build as in the docs job.

## Tests to write first (TDD)
- None. The doc meta-tests are the tests.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Code.
- The canon amendment (the operator's).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

## Lane card
- **Depends on:** R01–R33, all merged.
- **Wave:** 11.
- **Files touched:**
  - `src/vibey/domain/config.py` (two defaults)
  - `src/vibey/bootstrap.py` or `infrastructure/queue/selection.py` (the `QueueBackendNotConfigured` message)
  - `tests/domain/test_config.py` (R01's default test)
  - `tests/conftest.py`
  - `deploy/helm/vibey/values.yaml`
  - `deploy/helm/golden/*` (regenerated)
  - `.github/workflows/ci.yml` (one step pins `postgres`)
- **Parallel-safe with:** nothing.
- **Must keep passing unchanged:** the entire suite, including all protected tests, the
  `keda-*` goldens and `test_keda_scaler_query.py`.
- **Standing constraints:** see the header list.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
