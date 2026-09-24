## Title
feat(test-harness): the RabbitMQ topology of one machine's test queue

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-277`): the harness "takes its
work from a queue on the bus surface", which 8.b makes RabbitMQ. Draft ADR-0045 §12 names each object:
- one quorum queue per machine, so each machine's runs execute where their worktrees are;
- `x-single-active-consumer`, so a second service on a machine is a standby that executes nothing
  (8.c: "a restart, never a second copy");
- a delivery limit and a dead-letter exchange, the backstop for a service that dies before it can
  record anything ("never retried forever and never silently dropped", 8.e);
- a consumer timeout longer than the longest run.

The topology is declared in code at start (12.c: declared, not clicked), in the style of ADR-0044's
lane rmq-r12. Amendment A4 (`specs/ADR-test-harness-fakes-amendment.md:128-138`) makes
`vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (rmq-r04) the registered in-memory bus fake, so no
default-tier test needs a broker; this is the first root lane that injects the AMQP client, so it
registers that fake.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/amqp_topology.py`:
1. **`TestHarnessNames(*, prefix: str, instance: str)`**:
   `exchange()` → `f"{prefix}.tests"`; `request_queue()` → `f"{prefix}.tests.{instance}"`;
   `routing_key()` → `instance`; `dead_exchange()` → `f"{prefix}.tests.dlx"`;
   `dead_queue()` → `f"{prefix}.tests.{instance}.dead"`.
2. **`TestHarnessTopology(*, client: AmqpClientInterface, names: TestHarnessNamesInterface, settings: TestHarnessSettingsInterface)`**
   (`AmqpClientInterface` from `vibey_bootstrap.amqp.interfaces.client_interface`):
   - `request_queue_arguments(self) -> dict[str, object]` returns **exactly**
     ```python
     {"x-queue-type": "quorum", "x-single-active-consumer": True,
      "x-delivery-limit": settings.delivery_limit,
      "x-dead-letter-exchange": names.dead_exchange(),
      "x-dead-letter-strategy": "at-least-once", "x-overflow": "reject-publish",
      "x-consumer-timeout": (settings.run_bound_seconds + 600) * 1000}
     ```
   - `async def declare(self) -> None`, idempotent per topology object (a second call declares
     nothing): `client.declare_exchange(names.exchange(), "direct")`;
     `client.declare_exchange(names.dead_exchange(), "direct")`;
     `client.declare_queue(names.request_queue(), arguments=self.request_queue_arguments())` bound
     with `client.bind(names.request_queue(), names.exchange(), names.routing_key())`;
     `client.declare_queue(names.dead_queue(), arguments={"x-queue-type": "quorum"})` bound with
     `client.bind(names.dead_queue(), names.dead_exchange(), names.routing_key())`.
3. **Interfaces**, `src/vibey/infrastructure/test_harness/interfaces/amqp_topology_interface.py`:
   `@runtime_checkable` `TestHarnessNamesInterface` and `TestHarnessTopologyInterface`.
4. **`tests/infrastructure/test_harness/conftest.py`** (new) provides two fixtures, used by this
   lane and harness-T23/T24: `memory_amqp` returns a fresh `InMemoryAmqpClient()`; `amqp_url`
   returns `os.environ["VIBEY_TEST_AMQP_URL"]`, or calls `pytest.skip("VIBEY_TEST_AMQP_URL is not set")`.
5. **The fake**, new `tests/fakes/harness_amqp.py`: `class InMemoryHarnessTopology(TestHarnessTopology)`
   whose zero-argument `__init__` calls `super().__init__(client=InMemoryAmqpClient(), names=TestHarnessNames(prefix="vibey", instance="memory"), settings=TestHarnessSettings.from_sources(None, {"HOME": "/memory"}, hostname="memory"))`:
   the real topology over the in-memory broker, which amendment A2 names the fake for a class that
   only composes over a store.
6. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface modules and `tests.fakes.harness_amqp`, then:
   - append `FakeRegistration(port=amqp_topology_interface.TestHarnessTopologyInterface, build=harness_amqp.InMemoryHarnessTopology, note="the real topology over InMemoryAmqpClient (A2)")`;
   - unless `REGISTRY` already registers `AmqpClientInterface` (fakes-test-harness may have), append
     `FakeRegistration(port=client_interface.AmqpClientInterface, build=InMemoryAmqpClient, note="the family's in-memory broker (rmq-r04; amendment A4)")`;
   - append `TestHarnessTopologyInterface` and `AmqpClientInterface` (if absent) to `DRIVER_SEAMS`.
   `TestHarnessNames` is a pure policy, not a seam.

## Where to change
- New `src/vibey/infrastructure/test_harness/amqp_topology.py` and its interface module. Copy rmq-r12's
  shape (`src/vibey/infrastructure/queue/rabbitmq_topology.py`) if it has landed; it is not a dependency.
- New `tests/infrastructure/test_harness/conftest.py`, `tests/fakes/harness_amqp.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/test_harness/test_amqp_topology.py` and
  `tests/infrastructure/test_harness/test_amqp_topology_integration.py` (the opt-in twin).

## Acceptance criteria
- [ ] Against the in-memory client, each exchange, queue, argument and binding is declared once, however often `declare` runs.
- [ ] A message published to the exchange on the routing key lands in the request queue, and a `dead_letter()` of it lands in the dead queue with its routing key kept.
- [ ] Integration (`@pytest.mark.integration`, skipped without `VIBEY_TEST_AMQP_URL`): a real broker accepts every argument, including `x-single-active-consumer` on a quorum queue, and a second consumer stays idle while the first holds the queue (ADR-0045 *Verification owed*). Queue names in this test carry a random suffix and are deleted afterwards.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes with the registrations.
- [ ] 100% coverage of `src/vibey/infrastructure/` in the default tier.

## Tests to write first (TDD)
- `test_amqp_topology.py` (`from vibey.infrastructure.test_harness import amqp_topology as topo`; the `memory_amqp` fixture):
  `test_names`, `test_request_queue_arguments_are_exact`, `test_declare_is_idempotent`,
  `test_routing_and_dead_lettering`, `test_classes_satisfy_their_interfaces`
- `test_amqp_topology_integration.py` (`pytestmark = pytest.mark.integration`; the `amqp_url` fixture):
  `test_real_broker_accepts_every_argument`, `test_single_active_consumer_idles_the_second`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/meta/test_import_contracts_bind.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Consuming (harness-T23) and publishing (harness-T24). The chart (harness-T27a).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r04-bootstrap-amqp, harness-T05-test-harness-config, fakes-registry.
- **Files touched:** the two new source files; new `tests/infrastructure/test_harness/conftest.py`, `tests/fakes/harness_amqp.py` and the two test files; `tests/fakes/registry.py`.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** harness-T05's tests, `tests/meta/test_import_contracts_bind.py`, `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names (`topo.TestHarnessTopology`).
  - Substitute only at a declared seam (the `client` keyword). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - No lane needs a running RabbitMQ: the default tier uses `InMemoryAmqpClient`; a real-broker test is `integration` and skips without `VIBEY_TEST_AMQP_URL` (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
