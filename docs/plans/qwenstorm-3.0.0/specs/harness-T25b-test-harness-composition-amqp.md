## Title
feat(bootstrap): the harness composition uses the machine's queue when a service consumes it

## Why
Draft ADR-0045 §3 and §12. harness-T15a composed the `local` backend and refused `rabbitmq`.
With the resolver (harness-T25a), the requester (harness-T24) and the service (harness-T23) in place,
the composition root (CLAUDE.md: `bootstrap.py` is the sole one) now:
- resolves the backend: `auto` uses the queue only when a service consumes it, and otherwise
  degrades to the machine lock **with an announcement** (10.f; not a silent fallback);
- builds the service that `vibey test-harness serve` (harness-T25) runs;
- takes the AMQP URL and prefix from rmq-r17's `QueueBackendSettings`
  (`src/vibey/infrastructure/queue/selection.py`: environment, then `[bus]`, then rmq-r01's
  defaults), reused rather than re-implemented (10.e).

The AMQP client is injected through an `amqp_factory` keyword with the family's client as the
production default, so every test uses `InMemoryAmqpClient` (amendment A4's registered bus fake)
and no test needs a broker. The registered fake composition (harness-T15a) gains the same members,
so it keeps matching its interface.

## Required behaviour
1. **`TestHarnessComposition`** in `src/vibey/bootstrap.py` gains the constructor keywords
   `config: VibeyConfig | None = None` and
   `amqp_factory: Callable[[str], AmqpClientInterface] | None = None` (default
   `lambda url: AmqpClient(AmqpSettings(url=url))`, `vibey_bootstrap.amqp`, rmq-r04), and:
   - `self._queue = QueueBackendSettings.from_sources(config, environ)` (rmq-r17), giving `amqp_url` and `prefix`;
   - `names()`: `TestHarnessNames(prefix=self._queue.prefix, instance=settings.instance)`;
   - `topology()`: `TestHarnessTopology(client=<the AMQP client>, names=self.names(), settings=settings)`;
   - the AMQP client is built once, from `amqp_factory(self._queue.amqp_url)`, and only when needed;
   - `async client()`: `backend, self._announcement = await TestHarnessBackendResolver().resolve(backend=settings.backend, amqp_url=self._queue.amqp_url, probe=<the AmqpHarnessClient's unavailable_reason>)`.
     `rabbitmq` returns `AmqpHarnessClient(client=..., names=self.names(), codec=TestHarnessCodec(), builder=self.builder(), fast_path=self.fast_path("rabbitmq"), settings=settings)`;
     `local` returns harness-T15a's `LocalHarnessClient`. The T15a `rabbitmq` refusal is removed;
   - `announcement` returns the resolver's second value (`None` before `client()`);
   - `service() -> TestHarnessService`: without a URL, raise
     `TestHarnessNotConfigured(TestHarnessBackendResolver.NOT_CONFIGURED)`; otherwise
     `TestHarnessService(client=..., names=self.names(), topology=self.topology(), instance=self.instance("rabbitmq"), codec=TestHarnessCodec(), store=self.store(), clock=clock, settings=settings, logger=StructlogAppLogger(owner="test-harness"))`;
   - `async aclose()`: close the `AmqpHarnessClient`'s reply consumer and the AMQP client, if built.

   `build_test_harness` passes `config=config` through.
2. **`TestHarnessCompositionInterface`** (`src/vibey/bootstrap_interface.py`) gains `names`,
   `topology`, `service` and `aclose`.
3. **The fake** (`tests/fakes/harness_composition.py`, harness-T15a) gains, with real in-memory
   behaviour: an `amqp` attribute (one `InMemoryAmqpClient()` per fake); `names()`
   (`TestHarnessNames(prefix="vibey", instance=settings.instance)`); `topology()` (the real
   `TestHarnessTopology` over `amqp`); `service()` (the real `TestHarnessService` over `amqp`,
   `self.instance("rabbitmq")`, `self.store()`, the clock, the settings and a `RecordingLogger` from
   `tests/fakes/observability.py`); and `aclose()`, which sets `self.closed = True`.

## Where to change
- `src/vibey/bootstrap.py` (`TestHarnessComposition` and `build_test_harness` only; `edit_file`)
  and `src/vibey/bootstrap_interface.py`.
- `tests/fakes/harness_composition.py` (the added members).
- `tests/test_bootstrap.py` (tests appended; imports into its import block).

## Acceptance criteria
- [ ] `auto` with no URL composes the local client, and `announcement` says `backend=local (auto: no [bus] amqp_url is configured)`.
- [ ] `auto` with a URL but no consumer (an injected `InMemoryAmqpClient`) composes the local client, and announces `no harness service has declared …` (or `… consumes …` once the topology is declared).
- [ ] `auto` with a consumer attached to the in-memory request queue composes `AmqpHarnessClient`.
- [ ] `rabbitmq` without a URL fails naming both remedies; `service()` without a URL does the same.
- [ ] `service()` with a URL builds a `TestHarnessService` over the injected client; `aclose()` closes it.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes: the fake still matches the interface.

## Tests to write first (TDD)
Appended to `tests/test_bootstrap.py` (environments are dicts with `HOME` and `VIBEY_HARNESS_STATE_DIR` under `tmp_path`):
- `test_auto_without_a_url_is_local_and_says_why`
- `test_auto_without_a_consumer_is_local_and_says_why`
- `test_auto_with_a_consumer_is_rabbitmq`
- `test_rabbitmq_without_a_url_names_both_remedies`
- `test_the_harness_service_needs_a_url_and_uses_the_injected_broker`
- `test_aclose_closes_the_broker_client`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The `serve` command (harness-T25). The chart (harness-T27a). `vibey install --rabbitmq` (rmq-r33).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15-test-run-cli, harness-T23-harness-service, harness-T24-harness-amqp-client, harness-T25a-harness-backend-resolver, rmq-r01-queue-config, rmq-r17-queue-backend-selection.
- **Files touched:** `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`, `tests/fakes/harness_composition.py`, `tests/test_bootstrap.py`.
- **Shares a file with:** `bootstrap.py` (after rmq-r17; rmq-r27, rmq-r28 and harness-T26 edit other parts).
- **Must keep passing unchanged:** every existing `tests/test_bootstrap.py` test (harness-T15a's included), `tests/cli/*`, `tests/fakes/*`, and the protected tests.
- **Registry (amendment A4):** the fake composition's registration (harness-T15a) stays; it gains the new members. `AmqpClientInterface`'s fake is registered by harness-T22.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (`amqp_factory`). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - No lane needs a running RabbitMQ (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out). Every state directory is under `tmp_path`.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
