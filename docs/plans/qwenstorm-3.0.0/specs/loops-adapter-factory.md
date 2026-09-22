## Title
feat(loop-service): AdapterFactory builds one ServiceEngineAdapter per pool engine, sharing one LoopClient

ADR-0046 lane L59 (slug `loops-adapter-factory`).

## Why
At integration `d3b4a388`, subprocess mode's `adapters` mapping (`Mapping[EngineId,
EngineAdapter]`) is built once, in `bootstrap.py`'s composition of `build_full_worker`, one
`LoopProcessAdapter` per descriptor in the project's pool (`engines-pool`'s own evidence:
"src/vibey/bootstrap.py:735-738 builds an adapter for every `DEFAULT_DESCRIPTORS` engine"). Draft
ADR-0046 §10 (`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:304`) keeps
this shape for service mode too: `infrastructure/loop_service/adapter_factory.py` is not named in
the ADR's own table by that exact path, but §10's composition principle -- "one adapter per
engine, at composition time, never per job" -- is unchanged; only what each adapter's `start`
actually does differs (lanes `loops-service-adapter-run`/`loops-service-adapter-control`). This
lane is the one place that turns "the project's engine pool" (`engines-pool`) plus "the loop
service's own configuration" (`rmq-r01-queue-config`'s `[engines] invocation`, superseded in
scope by `loops-config-loop-services`'s richer `[loop_services]`) into that mapping for service
mode, sharing exactly **one** `LoopClient` across every adapter it builds -- a `LoopClient` owns
one AMQP connection and one reply queue per process (lane `loops-client`), and building a second
one per adapter would double every connection sub-doctrine 8.c's broker-side exclusivity already
bounds to one per model.

## Required behaviour
1. **`class ServiceAdapterFactory`** in `src/vibey/infrastructure/loop_service/adapter_factory.py`,
   built as `ServiceAdapterFactory(*, client: LoopClientInterface, config:
   LoopServicesConfigInterface, clock: Clock, caller: str, descriptors: Mapping[EngineId,
   EngineDescriptor], membership: LoopMembershipInterface | None = None)`. `membership` defaults
   to `LoopMembership()` (lane `loops-domain-loop-id`).
   - `def build(self, pool: frozenset[EngineId]) -> Mapping[EngineId, EngineAdapter]`: for every
     `engine_id in pool`, look up its `descriptor = self._descriptors[engine_id]` (skip silently
     -- as `engine_pool.py`'s own `for_project` already only ever returns engines with a
     descriptor -- an engine id with none, rather than raising: this factory trusts its caller's
     pool exactly as `bootstrap.py`'s subprocess path trusts `DEFAULT_DESCRIPTORS` today), find
     its `loop_id = self._membership.loop_of(descriptor)`, and build one
     `ServiceEngineAdapter(descriptor=descriptor, engine_id=engine_id, seat=<the seat this
     engine's own model or engine id resolves to, computed once here rather than at route time --
     see behaviour 2>, model=<None for paidloop; the loop's declared default_model for
     sovereignloop>, route_id=None, loop_id=loop_id, client=self._client,
     config=self._config.for_loop(loop_id), clock=self._clock, caller=self._caller)`, keyed by
     `engine_id` in the returned mapping.
2. **A pre-routed adapter is a convenience, not a decision.** The adapter this factory builds for
   `bootstrap.py`'s static `adapters` mapping is used in exactly one place today outside
   `SelectingLoopProvider`'s own routed path: `RotationHandoffService`'s wind-down selection and
   any other caller that picks an engine **without** going through a loop's route step at all
   (a direct-pin caller). For those callers, this factory's adapter must still work correctly even
   though it was never routed: its `seat` is computed the same way `SeatChooser._seat` computes
   one (`SeatSlug().of(model)` for sovereignloop, `SeatSlug().of_paid(engine_id)` for paidloop),
   using the loop's **configured** default model for sovereignloop
   (`self._config.for_loop(LoopId.SOVEREIGNLOOP).default_model`) rather than whatever happens to
   be resident at the moment this factory runs (composition time, long before any run) -- the
   `route_id=None` on the adapter means every run it starts goes through
   `loops-router-forwarding`'s pinned path anyway, which re-derives the *actual* seat and model at
   forward time from the `RunRequest`'s own `engine_id`/`model_pin`; the `seat`/`model` this
   factory bakes in are only ever used to shape the `RunRequest` it sends (its own `model_pin`
   comes from this baked-in `model`), never trusted as the final routing decision.
   - **`SelectingLoopProvider`'s own path never uses this factory's adapters.** It uses
     `RoutedAdapterBinder` (lane `loops-service-adapter-run`) instead, which builds one fresh,
     correctly-routed adapter **per job**, from the actual `RunRouted` reply. This factory's
     mapping exists only for callers that need a **static, pre-built** `Mapping[EngineId,
     EngineAdapter]` at composition time (`RotationHandoffService`, any direct-pin caller,
     conformance and doctor checks that construct an adapter without a job) -- exactly the same
     dual need subprocess mode already has (`bootstrap.py`'s static `adapters` dict *and*
     `SelectingEngineProvider`'s own per-job binding through the same static dict, since a
     subprocess adapter is stateless and safely reusable; a service adapter is likewise stateless
     between runs, because all of a run's state lives in `self._active`, keyed by `run_id`).
3. **`src/vibey/infrastructure/loop_service/interfaces/adapter_factory_interface.py`** (new):
   `@runtime_checkable class ServiceAdapterFactoryInterface(Protocol)` with
   `build(self, pool: frozenset[EngineId]) -> Mapping[EngineId, EngineAdapter]`.
4. **Fake.** No new fake is needed: a test that wants a pool of adapters builds
   `ScriptedEngine`s directly (the family's existing conformance double), exactly as every other
   BUILD-selection test in this ADR already does; this factory is exercised with the real class
   over a `FakeLoopClient`.

## Where to change
Line 1 of the new file is the provenance comment, copied byte for byte from line 1 of
`src/vibey/infrastructure/loop_service/client.py`.
- **New** `src/vibey/infrastructure/loop_service/adapter_factory.py` (behaviours 1-2). Imports:
  `from collections.abc import Mapping`, `from vibey.application.interfaces import Clock,
  EngineAdapter`, `from vibey.domain.engine import EngineDescriptor, EngineId`,
  `from vibey.domain.interfaces.loop_interface import LoopMembershipInterface`,
  `from vibey.domain.interfaces.loop_services_config_interface import LoopServicesConfigInterface`,
  `from vibey.domain.loop import LoopId, LoopMembership`, `from vibey.domain.residency import
  SeatSlug`, `from vibey.infrastructure.loop_service.adapter import ServiceEngineAdapter`,
  `from vibey.infrastructure.loop_service.interfaces.client_interface import
  LoopClientInterface`. `__all__ = ["ServiceAdapterFactory"]`. Module docstring: one adapter per
  pool engine, sharing one `LoopClient`; a pre-routed adapter always resolves its true seat and
  model at forward time (ADR-0046 §3), never trusting what this factory baked in at composition.
- **New** `src/vibey/infrastructure/loop_service/interfaces/adapter_factory_interface.py`
  (behaviour 3).
- **New** `tests/infrastructure/loop_service/test_adapter_factory.py`.

## Acceptance criteria
- [ ] `build(pool)` returns exactly one adapter per `pool` engine that has a descriptor, keyed by
      `EngineId`.
- [ ] Every adapter shares the same `LoopClient` instance (`is` identity, not just equality).
- [ ] A sovereign engine's adapter uses the loop's configured `default_model`; a paid engine's
      uses no model.
- [ ] `isinstance(ServiceAdapterFactory(...), ServiceAdapterFactoryInterface)`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_adapter_factory.py`. Use `BY_ENGINE_ID`
(`vibey.infrastructure.engines.descriptors`), `FakeLoopClient()`, `LoopServicesConfig()` (its
sovereignloop default model is `"gpt-oss:20b"` per lane `loops-config-loop-services`), a `_Clock`.
- `test_one_adapter_per_pool_engine`: `pool = frozenset({EngineId.SOVEREIGNLOOP,
  EngineId.CLAUDELOOP})` → `set(factory.build(pool)) == pool`.
- `test_every_adapter_shares_one_client`: both built adapters' private `_client` (accessed through
  a small test-only attribute, or proven behaviourally: both publish through the same
  `FakeLoopClient` instance, so `client.submitted` accumulates calls from either) is the one
  `FakeLoopClient` passed to the factory.
- `test_the_sovereign_adapter_uses_the_configured_default_model`: the built
  `EngineId.SOVEREIGNLOOP` adapter's requests (once `start` is called on it in a follow-up test)
  carry `model_pin == "gpt-oss:20b"`.
- `test_the_paid_adapter_carries_no_model`: the built `EngineId.CLAUDELOOP` adapter's requests
  carry `model_pin is None`.
- `test_an_engine_with_no_descriptor_is_skipped_not_raised`: `pool` containing an id absent from
  a narrowed `descriptors={}` factory → `build(pool) == {}`, no exception.
- `test_the_factory_satisfies_its_interface`.

## Checks the lane must run (all must pass)
```bash
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
```

## Out of scope
- `ServiceEngineAdapter` and `RoutedAdapterBinder` themselves (lanes `loops-service-adapter-run`,
  `loops-service-adapter-control`).
- Wiring this factory into `build_full_worker`/`build_app` and choosing invocation mode (lane
  `loops-invocation-composition`).
- The project's engine pool computation itself (lane `engines-pool`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests
  are never edited.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-service-adapter-control`, `rmq-r01-queue-config`, `engines-pool`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
