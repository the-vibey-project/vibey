## Title
feat(measure): RabbitMQ queue depth is sampled from the broker for the dead-letter queue and every declared queue

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every queue, and 8.c
puts both rotation layers on RabbitMQ (ADR-0046 §3). The job rows stay in PostgreSQL under either
backend and are measured by `gap-measure-queue-sampler`; what the broker holds is not: its
dead-letter queue, loop seats (ADR-0046 §4), surface lanes (ADR-0047) and the test harness queue
(ADR-0045). ADR-0046 §4 and §10 add the one family primitive for this, `queue_depth()` in
`vibey_bootstrap.amqp` (lane L21, placeholder `loops-queue-depth`): a passive `queue.declare`
returning the queue's `message_count` (V-AMQP2, `specs/ADR-two-loops.md:461`). Family first
(10.e, `:417`): this lane uses it and adds no second AMQP path.

Waiting time and oldest-message age are **not** in a passive declare. ADR-0046 §4 gives them to
the loop router's in-memory first-seen times (`specs/ADR-two-loops.md:214`, lane
`loops-residency`); this lane records broker depth only and says so in its docstring.

## Required behaviour
1. New `src/vibey/infrastructure/measure/rabbitmq_queue_sampler.py`,
   `class RabbitMqQueueSampler`:
   `__init__(self, client: AmqpClientInterface, queues: Sequence[str], *, clock: Clock,
   ids: Callable[[], UUID] = uuid4)` — `AmqpClientInterface` from
   `vibey_bootstrap.amqp.interfaces.client_interface` (lane `rmq-r04-bootstrap-amqp`); duplicate
   and empty names are dropped, order kept; `name` property returns `"rabbitmq"`.
   `async def collect(self) -> tuple[Measurement, ...]`: for each queue,
   `depth = await self._client.queue_depth(queue)` (the coroutine L21 adds to
   `AmqpClientInterface`; if L21 named it differently, use its name and say so in the verdict).
   - Success: subject `MeasurementSubject(SubjectKind.QUEUE, f"rabbitmq.{queue}")`, outcome
     `SAMPLED`, `started_at = ended_at = clock.now()`, reading `DEPTH = depth`.
   - An `Exception` for one queue (comment: "one unreachable queue is recorded, and never hides
     the others"): the same subject, outcome `FAILED`, no readings, detail
     `f"{type(exc).__name__}: {exc}"[:500]`.
2. New `src/vibey/infrastructure/measure/interfaces/rabbitmq_queue_sampler_interface.py`:
   `RabbitMqQueueSamplerInterface` (`name`, `collect`).
3. `src/vibey/bootstrap.py` `build_app`:
   - before the backend choice lane `rmq-r17-queue-backend-selection` adds, bind
     `amqp_client: AmqpClientInterface | None = None` and
     `queue_names: QueueNamesInterface | None = None`;
   - in its `rabbitmq` branch, once it has built `AmqpClient(AmqpSettings(url))` and
     `QueueNames(prefix)`, assign them to those two names (the `postgres` branch leaves them
     `None` and is otherwise unchanged);
   - where `measurement_sources` is built before the yield (after `measure` and `clock` exist,
     lanes `gap-measure-ledger-sink` and `gap-measure-queue-sampler`), when both are set, add
     `RabbitMqQueueSampler(amqp_client, (queue_names.dead_queue(), *measure.amqp_queues),
     clock=clock)` after the `JobQueueSampler`.
   `[measure] amqp_queues` is lane `gap-measure-config`'s key (env `VIBEY_MEASURE_AMQP_QUEUES`).

## Where to change
- New `src/vibey/infrastructure/measure/rabbitmq_queue_sampler.py` and its interface file.
- `src/vibey/bootstrap.py` (`edit_file`, the rabbitmq branch only).
- New `tests/infrastructure/measure/test_rabbitmq_queue_sampler.py`, using the family's
  in-memory AMQP double (`vibey_bootstrap.amqp.memory`, lane R04) with L21's depth support, or
  a small plain class implementing `queue_depth` — never a mock.

## Acceptance criteria
- [ ] Queues `("vibey.jobs.dead", "seat.a", "seat.a", "")` sample two queues, in that order.
- [ ] Depths 3 and 0 give two `SAMPLED` measurements with `depth` 3 and 0.
- [ ] A `queue_depth` that raises `ConnectionError("gone")` for `seat.a` gives a `FAILED`
      measurement for it with detail `"ConnectionError: gone"` and still samples the others.
- [ ] Under `VIBEY_QUEUE_BACKEND=rabbitmq`, `resources.measurement_sources` holds a
      `RabbitMqQueueSampler` (in `tests/test_bootstrap.py`'s rabbitmq composition tests, R17's).
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_rabbitmq_queue_sampler.py`:
- `test_each_declared_queue_is_sampled_once_in_order`
- `test_depth_is_recorded_per_queue`
- `test_an_unreachable_queue_is_recorded_failed_and_the_rest_are_sampled`
- `test_the_sampler_satisfies_its_interfaces`
- `test_build_app_samples_the_broker_under_the_rabbitmq_backend` (append beside R17's
  composition tests if they live in `tests/test_bootstrap.py`; mark as they are marked)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Per-seat waiting time and oldest age (`loops-residency`); per-project job queues (their rows
  are measured by `gap-measure-queue-sampler`); declaring or consuming any queue.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): RabbitMQ queue depth is sampled from the broker for the dead-letter queue and every declared queue`. Do not push.

## Lane card
- **Depends on:** `gap-measure-queue-sampler`, `loops-queue-depth`, `rmq-r12-queue-topology`,
  `rmq-r17-queue-backend-selection`.
- **Must keep passing unchanged:** R17's composition tests and the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
