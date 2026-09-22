## Title
feat(bootstrap): build_full_worker composes service-mode engines when [engines] invocation = "service"

ADR-0046 lane L60 (slug `loops-invocation-composition`).

## Why
Draft ADR-0046 §2's closing paragraph
(`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-two-loops.md:138`): "Subprocess
invocation (kept, 12.c). The same two layers run in process: `preferred_tier` then `select`,
unchanged, plus the fallback declaration. There are no queues and no residency. The 'both layers
on queues' rule binds service mode, and service mode becomes the default when R34 flips it."
`[engines] invocation` (`subprocess` | `service`) and its `VIBEY_ENGINE_INVOCATION` override
already exist (`rmq-r01-queue-config` behaviour 4 and 7). `rmq-r17-queue-backend-selection`
already establishes the exact pattern this lane follows for the *other* backend-choosing
decision in the same composition root: a `*Settings.from_sources(config, environ)` value type
with environment-first precedence, a `*NotConfigured(VibeyError)` that fails loudly and names both
remedies before any database or broker use, and one `if backend == ...:` branch inside
`build_app`/`build_full_worker` that builds the alternate stack. This lane is that same shape, for
engine invocation instead of the queue backend, and the two composition points are independent:
`queue.backend` and `engines.invocation` may each be `postgres`/`rabbitmq` and
`subprocess`/`service` in any combination (a `postgres` queue can still route BUILD jobs through a
service-mode loop, since the loop's own bus objects are provisioned through `vibey_bootstrap.amqp`
directly, not through the job queue's AMQP client).

## Required behaviour
1. **`class EngineInvocationSettings`** in `src/vibey/infrastructure/queue/selection.py` (the
   module `rmq-r17-queue-backend-selection` already created for `QueueBackendSettings`; this lane
   adds a sibling class in the same file, matching its style):
   `from_sources(config: VibeyConfig | None, environ: Mapping[str, str]) ->
   EngineInvocationSettings`. Fields: `mode: str` (`"subprocess"` or `"service"`), `amqp_url: str
   | None`, `vhost: str`, `prefix: str`, `loop_services: LoopServicesConfig`. Precedence:
   `VIBEY_ENGINE_INVOCATION` and `VIBEY_BUS_AMQP_URL` first, then `config.engines.invocation` and
   `config.bus`, then `config.loop_services`, then R01's defaults (`"subprocess"`, no URL,
   `LoopServicesConfig()`).
2. **`class EngineInvocationNotConfigured(VibeyError)`**. Its message contains both remedies
   verbatim, mirroring `QueueBackendNotConfigured`'s own two-remedy shape:
   - `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/`
   - `export VIBEY_ENGINE_INVOCATION=subprocess`
3. **`build_full_worker`** (`src/vibey/bootstrap.py`), after it already knows the project's engine
   pool (`engines-pool`'s `EnginePool.for_project`) and before it builds the subprocess `adapters`
   mapping:
   - `invocation = EngineInvocationSettings.from_sources(config, os.environ)`.
   - **`"subprocess"`** (the default): everything as today. `provider =
     SelectingEngineProvider(...)`, with `decisions=PostgresReviewLedger(resources.ledger,
     phase=Phase.BUILD)` and `loop_selector=LoopSelector(descriptors=BY_ENGINE_ID)` already wired
     by lane `loops-subprocess-fallback-declared`.
   - **`"service"`**: with no `amqp_url`, raise `EngineInvocationNotConfigured` before any adapter
     is built. Otherwise:
     - build one shared `AmqpClient(AmqpSettings(invocation.amqp_url, ...))` (connects lazily,
       `vibey_bootstrap.amqp`) and one shared `LoopClient(amqp=..., names=RunQueueNames(prefix=
       invocation.prefix), codec=RunProtocolCodec(), clock=clock)` (lane `loops-client`); `await
       loop_client.start()` inside `build_app`'s own async setup, exactly where it already awaits
       other resources, and close both in `build_app`'s existing `finally` (the same place the
       AMQP client of `rmq-r17-queue-backend-selection` is closed, if that queue backend is also
       `rabbitmq` -- **the two AMQP clients are independent and both may be open at once**; do
       not share one `AmqpClient` between the job queue and the loop service, because their
       lifecycles, connection settings and prefetch needs differ);
     - `adapters = ServiceAdapterFactory(client=loop_client,
       config=invocation.loop_services, clock=clock, caller=worker_owner,
       descriptors=BY_ENGINE_ID).build(pool)` (lane `loops-adapter-factory`) in place of the
       subprocess path's per-descriptor `LoopProcessAdapter` construction;
     - `binder = RoutedAdapterBinder(client=loop_client, config=invocation.loop_services, clock=
       clock, descriptors=BY_ENGINE_ID, caller=worker_owner)` (lane `loops-service-adapter-run`);
     - `provider = SelectingLoopProvider(selector=EngineSelector(descriptors=BY_ENGINE_ID),
       loop_selector=LoopSelector(descriptors=BY_ENGINE_ID), routing=loop_client, binder=binder,
       health=health, adapters=adapters, jobs=jobs, decisions=PostgresReviewLedger(resources.ledger,
       phase=Phase.BUILD), clock=clock, owner=worker_owner, allow_list=pool,
       local_engines=local.enabled_engines, metrics=metrics)` (lane
       `loops-selecting-loop-provider`) in place of `SelectingEngineProvider`.
   - `AppResources` gains `loop_client: LoopClientInterface | None`, `None` in subprocess mode, set
     in service mode, so `vibey worker`'s own shutdown path and `vibey loop submit` (lane
     `loops-cli-loop-submit`) can reach the same client rather than building a second one.
4. **`LoopCommandExecutor` composition.** Wherever `build_full_worker`/`build_app` already builds
   an `AsyncSubprocessExecutor` for DESIGN/DECOMPOSE (found by `loops-invocation-cli`'s own grep,
   out of scope here), this lane's `invocation` value is what that composition reads to decide
   between `AsyncSubprocessExecutor()` and `LoopCommandExecutor(loop_id=LoopId.SOVEREIGNLOOP,
   engine_id=EngineId.SOVEREIGNLOOP.value, client=loop_client, config=
   invocation.loop_services.for_loop(LoopId.SOVEREIGNLOOP), clock=clock, caller=worker_owner)` --
   **this lane exposes `invocation` and `loop_client` on `AppResources` precisely so
   `loops-invocation-cli` can make that choice; it does not itself touch any
   `AsyncSubprocessExecutor()` call site.**
5. With the default (`"subprocess"`), nothing observable changes: every existing test passes
   unedited.

## Where to change
- `src/vibey/infrastructure/queue/selection.py` (`edit_file`; created by
  `rmq-r17-queue-backend-selection`): behaviours 1-2, in the same module, same style as
  `QueueBackendSettings`/`QueueBackendNotConfigured`.
- `src/vibey/bootstrap.py` (`edit_file` only; over 100 lines): behaviour 3, inside
  `build_full_worker`, after the pool is known and before the subprocess adapters are built.
  `grep -n "def build_full_worker" src/vibey/bootstrap.py` first, and read the function in full
  before editing: anchor every insertion on the exact surrounding text `orm-bootstrap-engine` and
  `engines-pool` left, not on line numbers.
- `src/vibey/bootstrap_interface.py` (`edit_file`): `AppResources`'s new
  `loop_client: LoopClientInterface | None` field.
- New test file `tests/test_bootstrap_invocation.py` (mirroring `rmq-r17`'s own
  `tests/test_bootstrap.py` additions, kept in a separate file so this lane never touches that
  one's existing content).

## Acceptance criteria
- [ ] With no `[engines] invocation` set, `build_full_worker` composes exactly what it composes
      today, and the whole existing suite passes unchanged.
- [ ] `VIBEY_ENGINE_INVOCATION=service` with no `VIBEY_BUS_AMQP_URL` fails with
      `EngineInvocationNotConfigured`, naming both remedies, before any adapter or database
      operation.
- [ ] With `service` and a URL set, `build_full_worker` composes `SelectingLoopProvider` bound to
      one shared `LoopClient`, and `AppResources.loop_client` is that same instance.
- [ ] `queue.backend = "rabbitmq"` and `engines.invocation = "service"` together build two
      independent `AmqpClient`s, each closed once in `build_app`'s `finally`.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
`tests/test_bootstrap_invocation.py`:
- `test_default_invocation_is_subprocess`: `EngineInvocationSettings.from_sources(None, {}).mode
  == "subprocess"`.
- `test_service_without_a_url_names_both_remedies`: `build_full_worker(...,
  environ={"VIBEY_ENGINE_INVOCATION": "service"})` (or however the composition entry point takes
  environment, matching what `rmq-r17`'s own equivalent test does) raises
  `EngineInvocationNotConfigured` whose message contains both `export` lines verbatim.
- `test_env_beats_config_for_invocation`: `config.engines.invocation == "service"`,
  `environ={"VIBEY_ENGINE_INVOCATION": "subprocess"}` → the environment wins.
- `test_service_composes_the_loop_backed_provider`: `environ={"VIBEY_ENGINE_INVOCATION": "service",
  "VIBEY_BUS_AMQP_URL": "amqp://u:p@h:5672/"}` → `resources.loop_client is not None`, and the
  worker's provider is a `SelectingLoopProvider` (an `isinstance` check, or the equivalent
  structural check the sibling `rmq-r17` test uses for `RabbitMqJobRepository`).
- `test_subprocess_mode_leaves_loop_client_none`: default invocation → `resources.loop_client is
  None`.
- `test_independent_amqp_clients_for_queue_and_invocation`: both `queue.backend` and
  `engines.invocation` set to their bus-backed values, with distinct AMQP URLs → two separate
  `AmqpClient` objects exist among the composed resources (not the same instance).

## Checks the lane must run (all must pass)
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/test_bootstrap_invocation.py tests/infrastructure/queue tests/application/test_loop_provider.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/test_bootstrap.py

## Out of scope
- `AsyncSubprocessExecutor`'s four call sites and the CLI's own invocation-mode help text (lane
  `loops-invocation-cli`).
- `ServiceAdapterFactory`, `RoutedAdapterBinder`, `SelectingLoopProvider`, `LoopClient`
  themselves (their own lanes).
- Flipping the default to `"service"` (a future R34-equivalent decision).
- The chart. Docs, CHANGELOG.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-adapter-factory`, `loops-selecting-loop-provider`, `loops-command-executor`, `rmq-r17-queue-backend-selection`, `orm-bootstrap-engine`, `loops-config-loop-services`.

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
