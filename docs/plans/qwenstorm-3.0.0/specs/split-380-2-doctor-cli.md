<!-- split of #380: child 2 of 2; audit: issue-audit/updates/380.md -->

## Title
feat(cli): vibey doctor reports the broker and both loops when the queue or the engines use the bus

## Why
`vibey doctor` (`src/vibey/cli/main.py:1185-1391` at integration `4317cff6`) checks PostgreSQL (the line printed at `:1341`) and the engines, and lane `installer-doctor` adds one line per local-stack dependency after the PostgreSQL line. Once #381 flips the defaults, a laptop with no broker fails with R17's `QueueBackendNotConfigured` (#364), and a worker whose runs sit on a queue nobody consumes looks healthy. Child 1 (`split-380-1-loop-doctor`) built `LoopDoctor`, which checks the broker, each loop's router and each model's seat (draft ADR-0046 §3-§4, `STORM/specs/ADR-two-loops.md`). This child composes it in `bootstrap.py`, the one composition root, and runs it from `vibey doctor` only when the bus is in use: the resolved queue backend is `rabbitmq`, or the resolved engine invocation is `service` (ADR-0046 §2 keeps both invocation modes, "Subprocess invocation (kept, 12.c)", line 138). With the defaults nothing changes and nothing connects.

The loops follow sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`): sovereignloop always, with its declared models, defaulting to the 8.d model `gpt-oss:20b` (`src/vibey/infrastructure/engines/ollama_chat.py:39`); paidloop only when a paid engine id is in `[engines].enabled`, because 8.b (`doctrines.md:120`) makes paid engines declared-only.

Today's doctor tests reach the engine preflight by patching `LoopProcessAdapter.preflight` (`tests/cli/test_operational_commands.py:939-947`). Sub-doctrine 9.b (`doctrines.md:349`) forbids that for new tests, so substitution happens at declared seams: a CLI-layer `DoctorSeams` dataclass passed as `CliRunner.invoke(..., obj=DoctorSeams(...))`, and ADR-0046's adapter-factory seam (`LocalEngineSettings.adapter(..., factory=...)`, carried over from R28 behaviour 2).

## Required behaviour
1. **`bootstrap.build_loop_doctor(config: VibeyConfig | None, environ: Mapping[str, str]) -> LoopDoctorInterface`**, a module function in `src/vibey/bootstrap.py` whose docstring gives its reason: "A module function, like `build_app` and `build_full_worker`: this file is the one composition root, and its builders are functions by that convention. Nothing here connects; the AMQP client and the loop client connect lazily, on `check()`." It does, in order:
   - `settings = QueueBackendSettings.from_sources(config, environ)`; when `settings.amqp_url is None`, `raise QueueBackendNotConfigured()`.
   - `amqp_settings = AmqpSettings(settings.amqp_url)`, `amqp = AmqpClient(amqp_settings)`, `queues = LoopQueueNames(settings.prefix)`, and `client = LoopServiceClient(client=amqp, names=queues, clock=SystemClock(), caller="vibey doctor")`.
   - `loop_services = config.loop_services if config is not None else LoopServicesConfig()` and `enabled = config.engines.enabled if config is not None else DEFAULT_ENGINES`.
   - The sovereign check: `LoopCheck(loop_id=LoopId.SOVEREIGNLOOP, seats=loop_services.loop(LoopId.SOVEREIGNLOOP).models or (DEFAULT_OLLAMA_MODEL,), residency=True)`.
   - The paid check, only when some seat qualifies: `paid_ids = {d.engine_id.value for d in ALL_DESCRIPTORS if d.tier is EngineTier.PAID}`, `paid_seats = tuple(engine for engine in enabled if engine in paid_ids)`; when `paid_seats` is non-empty, append `LoopCheck(loop_id=LoopId.PAIDLOOP, seats=paid_seats, residency=False)`.
   - It returns `LoopDoctor(amqp=amqp, redacted_url=amqp_settings.redacted_url(), queues=queues, client=client, loops=loops, probe_cwd=loop_services.root)`.
2. **`src/vibey/cli/doctor_loops.py`** holds two classes.
   - `@dataclass(frozen=True, slots=True) class DoctorSeams` with three fields, each defaulting to `None` (meaning "production"): `loop_doctor: LoopDoctorInterface | None`, `adapter_factory: EngineAdapterFactoryInterface | None`, `local_stack: LocalStackFactory | None`. Its docstring says it is what `vibey doctor` reaches outside itself, passed as `CliRunner.invoke(app, [...], obj=DoctorSeams(...))` (sub-doctrine 9.b).
   - `class LoopDoctorSection`, built with keyword arguments `environ: Mapping[str, str]`, `config_path: Path`, `doctor: LoopDoctorInterface | None = None` and `build: Callable[[VibeyConfig | None, Mapping[str, str]], LoopDoctorInterface] = build_loop_doctor`. Construction reads nothing. Its methods:
     - `config(self) -> VibeyConfig | None`: `None` when `config_path` is not a file; otherwise `load_config_from_path(config_path)`, and `None` again if that raises `OSError`, `ValueError` or `ConfigError`. (This is the rule `LocalEngineSettings.from_toml` already applies to doctor, `src/vibey/infrastructure/engines/local_engines.py:89-97`: a broken `vibey.toml` must not crash a health check, and the environment still decides.)
     - `applies(self, config: VibeyConfig | None) -> bool`: `QueueBackendSettings.from_sources(config, environ).backend == "rabbitmq" or InvocationSettings.from_sources(config, environ).mode == "service"`.
     - `async def run(self) -> tuple[tuple[str, ...], bool]`: `config = self.config()`; when `not self.applies(config)`, return `((), True)` without building or calling anything. Otherwise `doctor = self._doctor` when one was injected, else `self._build(config, environ)`; a `QueueBackendNotConfigured` raised by the build returns `(tuple(str(exc).splitlines()), False)`. Otherwise `report = await doctor.check()` and it returns `(report.lines, report.ok)`.
3. **`src/vibey/cli/interfaces/doctor_loops_interface.py`** declares `@runtime_checkable` `DoctorSeamsInterface` (the three read-only properties) and `LoopDoctorSectionInterface` (`config()`, `applies(config)`, `async run()`), and both classes satisfy them.
4. **`vibey doctor`** (local mode only; `--cluster` output is unchanged):
   - `seams = ctx.obj if isinstance(ctx.obj, DoctorSeams) else DoctorSeams()`.
   - The local-stack factory lane `installer-doctor` chose becomes: `seams.local_stack` when it is not `None`; else `ctx.obj` when it is a `LocalStackFactory` (as `installer-doctor`'s tests pass it); else `LocalStackComposition()`.
   - Every engine adapter the doctor probes is built with `local.adapter(eid, endpoint, factory=adapter_factory)`, where `adapter_factory` is `seams.adapter_factory` when it is not `None`, else `SubprocessAdapterFactory()` (today's `LoopProcessAdapter`, so the existing tests that patch `LoopProcessAdapter.preflight` keep passing).
   - The loop section's lines are printed after the PostgreSQL line (`:1341`) and after lane `installer-doctor`'s stack lines, one `typer.echo` per line.
   - After the two existing exits (`if install_postgres and not ...ready` and `if conformance and not all_ok`, `:1342-1346`), `if not loops_ok: raise typer.Exit(1)`.
   - With the defaults (backend `postgres`, invocation `subprocess`), the output and exit code are unchanged, the loop doctor is never built or called, and nothing connects to a broker.
   - In bus mode with no AMQP URL, the output holds R17's `QueueBackendNotConfigured` remedies, `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/` and `export VIBEY_QUEUE_BACKEND=postgres`, and the exit code is 1.

## Where to change
**Step 0, before any edit:** run the preflight block under *Conventions this lane relies on*. If any command prints nothing, or prints something different from the signature stated there, make no edit: stop and report `blocked: <the missing or different interface>: <what grep printed>`.

This lane spans four source files, not one, because the audit's scope is exactly a composition-root builder, a CLI seam with its interface, and the wiring in one command:
- `src/vibey/bootstrap.py` (over 960 lines: `edit_file` only). Append `build_loop_doctor` (behaviour 1) at the end of the file. Add the imports it needs beside the existing ones, without importing any name twice (lane R17 already imports some): `DEFAULT_ENGINES` and `LoopServicesConfig` from `vibey.domain.config` (the line that imports `VibeyConfig`, `:77` at `4317cff6`), `EngineTier` from `vibey.domain.engine` (`:78`), `ALL_DESCRIPTORS` from `vibey.infrastructure.engines.descriptors` (`:104`), `LoopId` from `vibey.domain.loop`, `LoopQueueNames` from `vibey.domain.run_protocol`, `DEFAULT_OLLAMA_MODEL` from `vibey.infrastructure.engines.ollama_chat`, `LoopServiceClient` from `vibey.infrastructure.loop_service.client`, `LoopCheck` and `LoopDoctor` from `vibey.infrastructure.loop_service.doctor`, `LoopDoctorInterface` from `vibey.infrastructure.loop_service.interfaces.doctor_interface`, `QueueBackendSettings` from `vibey.infrastructure.queue.selection`, and `AmqpClient` and `AmqpSettings` from `vibey_bootstrap.amqp`. `SystemClock` and `QueueBackendNotConfigured` are already in this file.
- **New `src/vibey/cli/doctor_loops.py`** (behaviour 2). Copy the module layout of `src/vibey/cli/ledger_search.py` (provenance line, module docstring, imports, classes, `__all__ = ["DoctorSeams", "LoopDoctorSection"]`). It may import `vibey.bootstrap` (`build_loop_doctor`, `QueueBackendNotConfigured`), as `ledger_search.py:25` does. Other imports: `load_config_from_path` from `vibey.infrastructure.config_loader`, `ConfigError` and `VibeyConfig` from `vibey.domain.config`, `QueueBackendSettings` from `vibey.infrastructure.queue.selection`, `InvocationSettings` from `vibey.infrastructure.engines.adapter_factory`, `EngineAdapterFactoryInterface` from `vibey.infrastructure.engines.interfaces.adapter_factory_interface`, `LocalStackFactory` from `vibey.application.interfaces`, `LoopDoctorInterface` from `vibey.infrastructure.loop_service.interfaces.doctor_interface`.
- **New `src/vibey/cli/interfaces/doctor_loops_interface.py`** (behaviour 3). Copy the style of `src/vibey/cli/interfaces/ledger_search_interface.py` (`from __future__ import annotations`, domain and infrastructure types imported under `TYPE_CHECKING`).
- `src/vibey/cli/main.py` (over 1760 lines: `edit_file` only), inside `def doctor(ctx: typer.Context, ...)` as lane `installer-doctor` left it:
  1. Beside the function-local imports at the top of `doctor` (`from vibey.application.conformance import run_conformance` and its neighbours, `:1236-1239` at `4317cff6`), add `from vibey.cli.doctor_loops import DoctorSeams, LoopDoctorSection` and `from vibey.infrastructure.engines.adapter_factory import SubprocessAdapterFactory`.
  2. Directly after the block `if cluster and install_postgres: ... raise typer.Exit(EXIT_USAGE)` (`:1241-1243`), add:
     ```python
         seams = ctx.obj if isinstance(ctx.obj, DoctorSeams) else DoctorSeams()
         loop_section = LoopDoctorSection(
             environ=os.environ, config_path=Path.cwd() / "vibey.toml", doctor=seams.loop_doctor
         )
         adapter_factory = (
             seams.adapter_factory if seams.adapter_factory is not None else SubprocessAdapterFactory()
         )
     ```
  3. Replace `installer-doctor`'s single line `factory = ctx.obj if isinstance(ctx.obj, LocalStackFactory) else LocalStackComposition()` (find it with the preflight grep) with, at the same indentation:
     ```python
             if seams.local_stack is not None:
                 factory = seams.local_stack
             elif isinstance(ctx.obj, LocalStackFactory):
                 factory = ctx.obj
             else:
                 factory = LocalStackComposition()
     ```
  4. In `run_doctor`, change `adapter = local.adapter(eid, endpoint)` (`:1292`) to `adapter = local.adapter(eid, endpoint, factory=adapter_factory)`.
  5. In `run_doctor`, directly after the loop with which `installer-doctor` echoes its stack lines (it follows `typer.echo(_postgres_status_line(local_postgres_status))`), add:
     ```python
             loop_lines, loops_ok = await loop_section.run()
             for line in loop_lines:
                 typer.echo(line)
     ```
  6. Directly after `if conformance and not all_ok:` and its `raise typer.Exit(1)`, add:
     ```python
             if not loops_ok:
                 raise typer.Exit(1)
     ```
- After editing, run `uv run ruff check --fix` and `uv run ruff format` on the four source files and the new test file.
- **New `tests/cli/test_doctor_loops.py`.**
- Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/cli/ledger_search.py`: `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`

## Acceptance criteria
- [ ] With the defaults, `vibey doctor --engine claudeloop` prints exactly what it printed without the loop section, exits 0, and never calls the injected loop doctor's broker (`UnreachableAmqpClient.attempts == 0`).
- [ ] An unreachable broker prints `broker: unreachable (connection refused)` after the PostgreSQL line and exits 1.
- [ ] A silent router prints the `vibey loop-service --loop sovereignloop` remedy and exits 1.
- [ ] Service mode with no URL prints both `QueueBackendNotConfigured` remedies and exits 1.
- [ ] `build_loop_doctor` declares paidloop only when a paid engine id is enabled, and connects nowhere.
- [ ] Every existing test in `tests/cli/test_operational_commands.py` and `tests/cli/test_local_install.py` passes unchanged; `vibey doctor --cluster` output is unchanged.
- [ ] No new test uses `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; if `tests/meta/patching_baseline.json` exists, it does not change.
- [ ] 100% branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/cli/test_doctor_loops.py`. Module setup:
- `runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})`, as `tests/cli/test_operational_commands.py:30` builds it; `from vibey.cli.main import app`.
- A fixture `bus_env(monkeypatch, tmp_path)` that calls `monkeypatch.delenv(name, raising=False)` for `VIBEY_QUEUE_BACKEND`, `VIBEY_ENGINE_INVOCATION`, `VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST` and `VIBEY_BUS_PREFIX`, then `monkeypatch.chdir(tmp_path)` so no `vibey.toml` is read, and returns `tmp_path`.
- A private class `_ScriptedAdapterFactory(base_dir: Path)` with `build(self, descriptor, *, env_overlay)` (the parameter names of `EngineAdapterFactoryInterface.build`) that appends `descriptor.engine_id.value` to `self.built` and returns the production in-memory adapter `ScriptedEngine(descriptor=descriptor, base_dir=base_dir)` (`vibey.infrastructure.engines.scripted`), whose preflight runs no process.
- A helper `_seams(tmp_path, loop_doctor=None)` returning `DoctorSeams(loop_doctor=loop_doctor, adapter_factory=_ScriptedAdapterFactory(tmp_path), local_stack=FakeFactory(...))`, where `FakeFactory` is lane `installer-cli`'s fake imported from `tests.cli.test_local_install`, built with host `None` and label `"test-host"` (read its `__init__` for the exact argument order), so the stack check is one line and runs no command.
- A helper `_loop_doctor(amqp, client)` returning `LoopDoctor(amqp=amqp, redacted_url="amqp://guest:***@localhost:5672/", queues=LoopQueueNames("vibey"), client=client, loops=(LoopCheck(loop_id=LoopId.SOVEREIGNLOOP, seats=("gpt-oss:20b",), residency=True),), probe_cwd="/work")`, with `FakeLoopClient` and `UnreachableAmqpClient` from `tests.fakes.loop_service`.
- Every `CliRunner` test passes `["doctor", "--engine", "claudeloop"]`. The PostgreSQL line still comes from the real `PostgresLocalService().status()`, exactly as the existing doctor tests do; assert only that `"postgresql"` appears, never its state.

The tests:
- `test_default_doctor_output_is_unchanged_and_connects_nowhere(bus_env)`: invoke once with `obj=_seams(tmp_path, _loop_doctor(amqp, FakeLoopClient()))` where `amqp = UnreachableAmqpClient()`, and once with `obj=_seams(tmp_path)`. Both exit 0, the two outputs are equal, neither contains `"broker"`, and `amqp.attempts == 0`.
- `test_doctor_reports_an_unreachable_broker_and_exits_non_zero(bus_env)`: `monkeypatch.setenv("VIBEY_QUEUE_BACKEND", "rabbitmq")`; `obj=_seams(tmp_path, _loop_doctor(UnreachableAmqpClient(), FakeLoopClient()))`. Exit code 1; the output contains `broker: unreachable (connection refused)`, after the `postgresql` line and after the `test-host` stack line.
- `test_doctor_reports_a_silent_router(bus_env)`: `monkeypatch.setenv("VIBEY_ENGINE_INVOCATION", "service")`; `obj=_seams(tmp_path, _loop_doctor(InMemoryAmqpClient(), FakeLoopClient()))`. Exit code 1; the output contains `broker: ok amqp://guest:***@localhost:5672/` and `loop sovereignloop: no router answered within 10s; start one with vibey loop-service --loop sovereignloop`.
- `test_service_mode_without_a_url_names_the_remedies(bus_env)`: `monkeypatch.setenv("VIBEY_ENGINE_INVOCATION", "service")`, no URL, `obj=_seams(tmp_path)`. Exit code 1; the output contains `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/` and `export VIBEY_QUEUE_BACKEND=postgres`.
- `test_section_is_silent_with_the_defaults(bus_env)`: `LoopDoctorSection(environ={}, config_path=tmp_path / "vibey.toml", build=<a recording callable that raises AssertionError>)`; `await section.run() == ((), True)` and `section.config() is None`.
- `test_section_reads_the_backend_from_vibey_toml(bus_env)`: write `tmp_path / "vibey.toml"` holding `[project]\nname = "doctor-test"\n\n[queue]\nbackend = "rabbitmq"\n`, and build `section = LoopDoctorSection(environ={}, config_path=tmp_path / "vibey.toml", doctor=_loop_doctor(UnreachableAmqpClient(), FakeLoopClient()))`. `section.config()` is a `VibeyConfig` and `section.applies(section.config())` is True, and `await section.run() == (("broker: unreachable (connection refused)",), False)`.
- `test_a_malformed_vibey_toml_leaves_the_environment_to_decide(bus_env)`: a `vibey.toml` holding `not = [valid` and another holding only `[queue]\nbackend = "rabbitmq"\n` (no project name) both give `config() is None`; with `environ={"VIBEY_ENGINE_INVOCATION": "service"}`, `applies(None)` is True, and with `environ={}` it is False.
- `test_section_names_the_remedies_when_the_bus_has_no_url(bus_env)`: `LoopDoctorSection(environ={"VIBEY_ENGINE_INVOCATION": "service"}, config_path=tmp_path / "vibey.toml")` (the real `build_loop_doctor`); `lines, ok = await section.run()`; `ok is False` and both remedy lines are in `lines`.
- `test_build_loop_doctor_without_a_url_raises`: `pytest.raises(QueueBackendNotConfigured)` for `build_loop_doctor(None, {})`.
- `test_build_loop_doctor_declares_sovereignloop_from_the_loop_config`: `doctor = build_loop_doctor(None, {"VIBEY_BUS_AMQP_URL": "amqp://u:p@localhost:5672/"})`; `doctor.loops` has one check, `LoopId.SOVEREIGNLOOP`, `residency is True`, seats equal to `LoopServicesConfig().loop(LoopId.SOVEREIGNLOOP).models or (DEFAULT_OLLAMA_MODEL,)`; `doctor.probe_cwd == LoopServicesConfig().root`.
- `test_build_loop_doctor_adds_paidloop_only_for_an_enabled_paid_engine`: with `parse_config({"project": {"name": "doctor-test"}, "engines": {"enabled": ["claudeloop"]}})` the second check is `LoopCheck(loop_id=LoopId.PAIDLOOP, seats=("claudeloop",), residency=False)`; with `parse_config({"project": {"name": "doctor-test"}})` there is only the sovereign check.
- `test_doctor_seams_and_section_satisfy_their_interfaces`: `isinstance(DoctorSeams(), DoctorSeamsInterface)` and `isinstance(LoopDoctorSection(environ={}, config_path=Path("vibey.toml")), LoopDoctorSectionInterface)`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run pytest -q -p no:cacheprovider tests/cli/test_doctor_loops.py tests/cli/test_local_install.py tests/application/test_interfaces_convention.py tests/fakes tests/meta
uv run pytest -q -p no:cacheprovider tests/cli tests/infrastructure/loop_service tests/infrastructure/engines
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
Several existing `tests/cli` tests and the full-suite coverage run need PostgreSQL today (the root `tests/conftest.py` opens it at session start, defaulting to `postgresql://$USER@localhost:5432/vibey_test`); this lane's own tests touch no service.

## Out of scope
- The `LoopDoctor` class and its fakes (child 1, `split-380-1-loop-doctor`).
- Installing RabbitMQ (lanes `installer-broker-cache` and `installer-cli`), and the local-stack lines themselves (lane `installer-doctor`).
- `vibey doctor --cluster` (a follow-up may add the broker to `ClusterPreflight`).
- Folding `DoctorSeams` into `CliComposition` (lanes `fakes-job-wakeup` and `fakes-cli-composition`), and converting the existing doctor tests away from patching (lane `fakes-cli-operational-2`).
- Faking `PostgresLocalService` in doctor (lane `fakes-cli-composition` owns that seam).
- Normalizing a literal `paidloop` in `[engines].enabled`, the `[loop_services]` keys themselves, and the invocation resolver (ADR-0046's config and invocation lanes).
- A config key for the probe timeout.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
None of these exists on the integration branch at `4317cff6`; each comes from a lane this one depends on, directly or through them. The names and signatures below are the ones this lane assumes. **Preflight** (run from the repository root; each command must print at least one line, and what it prints must match the signature given below):
```bash
grep -n "class LoopDoctor\b\|class LoopDoctor(\|class LoopDoctor:\|class LoopCheck\|def loops\|def probe_cwd" src/vibey/infrastructure/loop_service/doctor.py
grep -n "class LoopDoctorInterface" src/vibey/infrastructure/loop_service/interfaces/doctor_interface.py
grep -n "class FakeLoopClient\|class UnreachableAmqpClient\|class ProbeAnswer" tests/fakes/loop_service.py
grep -n "class QueueBackendSettings\|def from_sources\|amqp_url\|prefix\|backend" src/vibey/infrastructure/queue/selection.py
grep -n -A8 "class QueueBackendNotConfigured" src/vibey/bootstrap.py
grep -n "isinstance(ctx.obj, LocalStackFactory)\|def doctor(\|ctx: typer.Context" src/vibey/cli/main.py
grep -n "def doctor_lines" src/vibey/cli/local_install.py
grep -n -A6 "class FakeFactory" tests/cli/test_local_install.py
grep -n "class SubprocessAdapterFactory\|class InvocationSettings\|def from_sources\|mode" src/vibey/infrastructure/engines/adapter_factory.py
grep -n -A4 "class EngineAdapterFactoryInterface\|def build" src/vibey/infrastructure/engines/interfaces/adapter_factory_interface.py
grep -n -A6 "def adapter(" src/vibey/infrastructure/engines/local_engines.py
grep -n "class LoopServicesConfig\|class LoopServiceConfig\|def loop(\|root:\|models:\|loop_services:" src/vibey/domain/config.py
grep -n -A10 "class LoopServiceClient" src/vibey/infrastructure/loop_service/client.py
grep -n "class LoopQueueNames" src/vibey/domain/run_protocol.py
grep -n "AmqpClient\b\|AmqpSettings" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/__init__.py
```

**From `split-380-1-loop-doctor`:** `vibey.infrastructure.loop_service.doctor` holds `LoopCheck(loop_id: LoopId, seats: tuple[str, ...], residency: bool)` and `LoopDoctor(*, amqp, redacted_url, queues, client, loops, probe_cwd, probe_timeout=DEFAULT_PROBE_TIMEOUT)` with the properties `loops` and `probe_cwd` and `async check() -> LoopDoctorReport` (`lines: tuple[str, ...]`, `ok: bool`); its first line is `broker: ok <redacted_url>` or the single line `broker: unreachable (<error>)`, and a silent router gives `loop <loop>: no router answered within <n>s; start one with vibey loop-service --loop <loop>`. `vibey.infrastructure.loop_service.interfaces.doctor_interface.LoopDoctorInterface` declares it. `tests/fakes/loop_service.py` holds `FakeLoopClient(answers=None)`, `ProbeAnswer(stdout, cached_at=None)` and `UnreachableAmqpClient(error="connection refused")` with an `attempts` counter.

**From `rmq-r17-queue-backend-selection` (#364):** `vibey.infrastructure.queue.selection.QueueBackendSettings.from_sources(config: VibeyConfig | None, environ: Mapping[str, str]) -> QueueBackendSettings`, frozen, with `backend` (`"postgres"` or `"rabbitmq"`), `amqp_url: str | None`, `vhost`, `prefix` and `rabbitmq`; precedence `VIBEY_QUEUE_BACKEND`, `VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST`, `VIBEY_BUS_PREFIX` (an empty value is unset), then `config.queue` and `config.bus`, then the defaults (`postgres`, no URL, `/`, `vibey`). `vibey.bootstrap.QueueBackendNotConfigured(VibeyError)` beside `DatabaseNotConfigured`, built with no argument (assumed, as `DatabaseNotConfigured` is, `bootstrap.py:641-648`), whose message contains `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/` and `export VIBEY_QUEUE_BACKEND=postgres`. Through R17 (and #351 child 2): `vibey_bootstrap.amqp.AmqpClient(settings: AmqpSettings)`, which connects lazily, and `AmqpSettings(url)` with `redacted_url()`.

**From `installer-doctor`:** `doctor` in `src/vibey/cli/main.py` takes `ctx: typer.Context` first; when not `--cluster` it chooses `factory = ctx.obj if isinstance(ctx.obj, LocalStackFactory) else LocalStackComposition()` (`LocalStackFactory` from `vibey.application.interfaces`, `LocalStackComposition` from `vibey.bootstrap`), computes `InstallCommand(...).doctor_lines(model=...)`, and echoes those lines immediately after the PostgreSQL line. `tests/cli/test_local_install.py` defines `FakeFactory(host, label, precondition, reports_by_key)`; with host `None`, `doctor_lines` returns the one line `local stack: test-host is not a default OS (Arch Linux, macOS); only PostgreSQL is checked` and runs no command.

**From `loops-invocation` (ADR-0046 §2, §10 `infrastructure/engines/adapter_factory.py`), assumed:**
- `vibey.infrastructure.engines.interfaces.adapter_factory_interface.EngineAdapterFactoryInterface` with `def build(self, descriptor: EngineDescriptor, *, env_overlay: Mapping[str, str]) -> EngineAdapter`.
- `vibey.infrastructure.engines.adapter_factory.SubprocessAdapterFactory()`, whose `build` returns `LoopProcessAdapter(descriptor=descriptor, env_overlay=env_overlay)`.
- `LocalEngineSettings.adapter(self, engine_id: EngineId, endpoint: LocalEndpointEnvironmentInterface, *, factory: EngineAdapterFactoryInterface = <a SubprocessAdapterFactory>) -> EngineAdapter`.
- `vibey.infrastructure.engines.adapter_factory.InvocationSettings.from_sources(config: VibeyConfig | None, environ: Mapping[str, str]) -> InvocationSettings`, whose `mode` is `"subprocess"` or `"service"`: `VIBEY_ENGINE_INVOCATION` first (an empty value is unset), then `config.engines.invocation`, then `"subprocess"`.

**From `loops-config` (ADR-0046 §3-§4 and its *Migration* row `[loop_services.<loop_id>]`), assumed:** in `vibey.domain.config`, a frozen `LoopServicesConfig` constructible with no argument, with `root: str` (the `[loop_services] root`, an absolute path) and `loop(self, loop_id: LoopId) -> LoopServiceConfig`, whose `models: tuple[str, ...]` are the loop's declared models (for sovereignloop, `gpt-oss:20b` unless declared otherwise); and `VibeyConfig.loop_services: LoopServicesConfig`, filled by `parse_config`.

**Through `split-380-1-loop-doctor`'s dependencies, assumed:** `vibey.domain.loop.LoopId` (`SOVEREIGNLOOP`, `PAIDLOOP`); `vibey.domain.run_protocol.LoopQueueNames(prefix: str = "vibey")`; and `vibey.infrastructure.loop_service.client.LoopServiceClient(client: AmqpClientInterface, names: LoopQueueNamesInterface, clock: Clock, caller: str)`, whose construction connects nothing.

**Already on the integration branch:** `SystemClock` (`src/vibey/bootstrap.py:174`), `DEFAULT_ENGINES` (`src/vibey/domain/config.py:21`), `EngineTier` (`src/vibey/domain/engine.py:40`), `ALL_DESCRIPTORS` (`src/vibey/infrastructure/engines/descriptors.py:413`), `DEFAULT_OLLAMA_MODEL = "gpt-oss:20b"` (`src/vibey/infrastructure/engines/ollama_chat.py:39`), `load_config_from_path` (`src/vibey/infrastructure/config_loader.py:83`), `ConfigError` (`src/vibey/domain/config.py:38`), `ScriptedEngine(descriptor, base_dir)` (`src/vibey/infrastructure/engines/scripted.py:59`), and `EXIT_USAGE` (`src/vibey/cli/errors.py:34`).

## Standing constraints
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
- **Line 1 of every new file** is the provenance comment, copied byte for byte from a sibling file.
- **Substitution at a declared seam only:** constructor or keyword injection, `CliRunner.invoke(..., obj=...)`. Never `monkeypatch.setattr` on a module or class attribute, `mock.patch`, `MagicMock` or `AsyncMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` are allowed.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and `engines.invocation = "subprocess"`. This lane changes neither.
- **The default run needs no outside service.** No new test connects to a broker, Ollama or the network.
- **Editing:** change existing files with `edit_file` (an exact, unique `old_string` copied from `read_file`), never `write_file`, for any existing file over 100 lines. Never rewrite an existing test file. After each change, run the focused tests.
- **Arch Linux and macOS (8.h):** the loop check is the same on both; the tests use a fake local-stack factory with no host, so they run the same on both and on CI's Linux.

**Depends on:** split-380-1-loop-doctor, rmq-r17-queue-backend-selection, installer-doctor, loops-invocation, loops-config
- split-380-1-loop-doctor: `LoopDoctor`, `LoopCheck`, `LoopDoctorInterface`, and the fakes `FakeLoopClient`, `ProbeAnswer`, `UnreachableAmqpClient`.
- rmq-r17-queue-backend-selection: `QueueBackendSettings.from_sources` (the AMQP URL, prefix and backend) and `QueueBackendNotConfigured` with its two remedies.
- installer-doctor: the same `doctor` function, its `ctx: typer.Context` parameter, its `LocalStackFactory` choice and its stack lines, and `tests/cli/test_local_install.py`'s `FakeFactory`.
- loops-invocation: `EngineAdapterFactoryInterface`, `SubprocessAdapterFactory`, `LocalEngineSettings.adapter(..., factory=...)` and `InvocationSettings.from_sources`.
- loops-config: `LoopServicesConfig` (`root`, `loop(LoopId).models`) and `VibeyConfig.loop_services`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
