<!-- split of #331: child 4 of 5; audit: issue-audit/updates/331.md -->

## Title
feat(cli)!: `vibey worker --cloud {memory,cli}` runs the declared target's CLI adapter; `--azure` becomes a hidden alias

## Why
The worker's only cloud switch is `--azure {memory,az}` (`src/vibey/cli/main.py:1451-1459`): it is
hard-wired to Azure, and it preflights `az` with a raw `subprocess.run` (`main.py:1481-1494`) before
the project is resolved, so before its `[deploy].target` is even known. Sub-doctrine 8.b
(`src/vibey_tools/gh/docs/doctrines.md:136-137`) makes self-hosted OpenStack the cloud default, and
ADR-0042 (`docs/architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md:58-64`)
moves "which cloud" into the reviewed `[deploy].target` declaration, so a flag that also named the
cloud would be a second, unreviewed source of truth. The tests of that switch patch
`vibey.cli.main.subprocess.run` and `PostgresJobReadyNotifier`
(`tests/cli/test_operational_commands.py:1991-2025`), which 9.b (`doctrines.md:349`) forbids. This
lane keeps only the safety switch on the command line (`--cloud memory|cli`), picks the adapter from
the project's declaration through a declared `CloudClientSelector` seam reached from
`CliComposition`, and converts those tests to that seam.

## Required behaviour
**Decision (recorded, not to be re-litigated by the lane):** `--cloud` takes `memory` (in-memory,
the default) or `cli` (the `[deploy].target` provider's own CLI). It never names a cloud: adding a
cloud means adding a target and an adapter, not a flag value (12.c, `doctrines.md:455`). `--azure`
stays one major version as a hidden, deprecated alias: `--azure az` means `--cloud cli`, and only
for a project whose target is `"azure"`, so an old invocation can never mutate OpenStack.

1. **`src/vibey/infrastructure/cloud_clients.py`** declares
   `class UnknownCloudTarget(VibeyError)` and `class CloudClientSelector`:
   - `CloudCliAdapterClass = type[AzCliClientAdapter] | type[OpenStackCliAdapter]` (a module-level
     type alias, not a function);
   - `ADAPTERS: ClassVar[Mapping[str, CloudCliAdapterClass]] = {"azure": AzCliClientAdapter, "openstack": OpenStackCliAdapter}`;
   - `__init__(self, *, executor: CommandExecutor | None = None, adapters: Mapping[str, CloudCliAdapterClass] | None = None) -> None`:
     stores `executor` as given (None lets each adapter default to
     `CleanGitEnvSubprocessExecutor()`), and `dict(adapters if adapters is not None else self.ADAPTERS)`;
   - `targets(self) -> tuple[str, ...]`: the adapter map's keys, sorted;
   - `login_hint(self, target: str) -> str`: the target's adapter class's `LOGIN_HINT`;
   - `async select(self, target: str) -> CloudClientPort | None`: builds
     `adapter_cls(executor=self._executor)` and returns it when `await adapter.preflight()` is true,
     otherwise None. It runs nothing but the adapter's own `PREFLIGHT_ARGV`;
   - an unknown target (in `login_hint` or `select`) raises, before any command,
     `UnknownCloudTarget(f"no cloud CLI adapter for [deploy].target {target!r}; known: {', '.join(self.targets())}")`.
     Put the lookup in one method, `_adapter_class(self, target: str) -> CloudCliAdapterClass`,
     using `try: ... except KeyError: raise UnknownCloudTarget(...) from None`.
2. **`src/vibey/infrastructure/interfaces/cloud_clients_interface.py`** declares
   `@runtime_checkable class CloudClientSelectorInterface(Protocol)` with `targets`, `login_hint`
   and `async select`, same signatures, each with a one-line docstring and `...` body. It imports
   only `typing` and `from vibey.application.interfaces import CloudClientPort`.
3. **`CliComposition`** (`src/vibey/cli/composition.py`, created by lane `fakes-job-wakeup`) gains a
   keyword-only constructor parameter `cloud_clients: CloudClientSelectorInterface | None = None`
   (after the parameters it already has), stored as
   `cloud_clients if cloud_clients is not None else CloudClientSelector()`, and a read-only property
   `cloud_clients -> CloudClientSelectorInterface`. `CliCompositionInterface`
   (`src/vibey/cli/interfaces/composition_interface.py`) declares the same property.
4. **`vibey worker` options** (`main.py:1451-1459`): the `azure` parameter becomes these two:
   ```python
   cloud: Annotated[
       str | None,
       typer.Option(
           "--cloud",
           help="Cloud client for the deploy stage set: 'memory' (default; touches no real "
           "infrastructure) or 'cli' (the [deploy].target provider's own CLI, `openstack` or "
           "`az`, which mutates real resources on consented deploys)",
       ),
   ] = None,
   azure: Annotated[
       str | None,
       typer.Option(
           "--azure",
           hidden=True,
           help="Deprecated alias of --cloud: 'az' is --cloud cli for a project whose "
           "[deploy].target is 'azure'",
       ),
   ] = None,
   ```
5. **Flag checks** run synchronously before `run_worker`, in this order, each exiting
   `typer.Exit(2)` after echoing its line. They replace `main.py:1481-1494` entirely (the whole
   `az` login check and the `AzCliClientAdapter()` construction go away):
   ```python
   if azure is not None and azure not in ("memory", "az"):
       typer.echo("--azure must be 'memory' or 'az'")
       raise typer.Exit(2)
   if cloud is not None and azure is not None:
       typer.echo("--azure is a deprecated alias of --cloud; pass only --cloud")
       raise typer.Exit(2)
   if cloud is not None and cloud not in ("memory", "cli"):
       typer.echo("--cloud must be 'memory' or 'cli'")
       raise typer.Exit(2)
   cloud_mode = cloud if cloud is not None else ("cli" if azure == "az" else "memory")
   ```
6. **The declaration.** Directly after `provider = _resolve_provider(provider_opt)` (`main.py:1573`)
   and before `design_provider: DesignProvider`, resolve `[deploy]`, with this comment:
   `# Which cloud is the project's reviewed declaration (ADR-0042), never a flag. Projects`
   `# created before 3.0.0 stored no [deploy] table, so the repository's vibey.toml answers for them.`
   ```python
   stored_deploy = project.config.get("deploy")
   if stored_deploy is None:
       stored_deploy = load_runtime_config_from_path(project.repo_path / "vibey.toml").get(
           "deploy", {}
       )
   deploy = DeployConfig.from_mapping({"deploy": stored_deploy})
   ```
   An invalid declaration raises `ConfigError` (a `VibeyError`), which reaches `guard()`
   (`src/vibey/cli/errors.py:89-95`) and exits 3 with `Error: deploy.target: ...`.
7. **The client.** Right after 6:
   ```python
   cloud_client: CloudClientPort | None = None
   if cloud_mode == "cli":
       if azure == "az" and deploy.target != "azure":
           typer.echo(
               '--azure az requires [deploy].target = "azure"; this project\'s target is '
               f"{deploy.target!r} -- use --cloud cli"
           )
           raise typer.Exit(EXIT_USAGE)
       cloud_clients = CliComposition.current().cloud_clients
       cloud_client = await cloud_clients.select(deploy.target)
       if cloud_client is None:
           typer.echo(
               f"--cloud cli with [deploy].target = {deploy.target!r} requires "
               f"{cloud_clients.login_hint(deploy.target)}"
           )
           raise typer.Exit(1)
   ```
   `memory` leaves `cloud_client` None, which `build_full_worker` turns into the in-memory adapter.
   The preflight uses ambient credentials; a scope-specific failure surfaces later as the adapter's
   CLI error and goes to DEPLOY_REVIEW triage.
8. **The worker.** The `build_full_worker(...)` call (`main.py:1699-1710`) passes
   `azure_client=cloud_client,` (was `azure_client=azure_client,`) and `deploy=deploy,`. The
   "worker started:" echo (`main.py:1716-1719`) appends ` deploy_target={deploy.target} cloud={cloud_mode}`
   after `provider={provider}` on the same line. Existing tests assert substrings of that line, so
   they keep passing.
9. **Nothing in `cli/main.py` calls `subprocess` any more.** Delete line 15
   (`import subprocess  # nosec B404 - fixed argv, never shell=True`) when
   `grep -n "subprocess" src/vibey/cli/main.py` shows no other use.
10. `vibey worker --help` lists `--cloud` and does not list `--azure`.

## Where to change
This lane touches **nine files** (five source, four test), more than one source file plus its
interface, for these reasons: the selector needs its interface (ADR-0016); the worker can only reach
it through `CliComposition`, the CLI's declared seam, which has an interface of its own; the flag
and the resolution live in `cli/main.py`; the default-tier proof is a new test file; the converted
and new worker tests live where the worker's tests are; the fakes registry must list every new
driver seam (the harness-fakes amendment, A2); and the patching ratchet fails on any count that
differs from `tests/meta/patching_baseline.json`, so removed patches must be written down there. The
selector is a flat module with its interface in the existing `src/vibey/infrastructure/interfaces/`
package (which `.importlinter`'s `infrastructure-interfaces-declare-only` contract already holds,
`.importlinter:112`), not a new `infrastructure/cloud/` package, so `.importlinter` and two
`__init__.py` files do not change.

Line numbers are from the storm integration branch at `4317cff6`. Lanes `rmq-r02-wakeup-composition`
and `fakes-job-wakeup` edit `cli/main.py` before this lane, so **find each quoted text** rather than
trusting a number. Use `edit_file` or a checked replacement for every existing file (`main.py` is
over 1,700 lines; EDITING-RULES.md rule 2). Every new file starts with the provenance header copied
byte for byte from line 1 of `src/vibey/infrastructure/azure/az_cli.py`.

1. New `src/vibey/infrastructure/cloud_clients.py`: Required behaviour 1, with a module docstring:
   the declared target picks the adapter (ADR-0042, 8.b), the map is data a target joins with its
   adapter (12.c), and every adapter runs through one injected `CommandExecutor` (9.b). Imports:
   `collections.abc.Mapping`, `typing.ClassVar`, `CloudClientPort` from
   `vibey.application.interfaces`, `VibeyError` from `vibey.domain.errors`, `AzCliClientAdapter`
   from `vibey.infrastructure.azure.az_cli`, `CommandExecutor` from `vibey.infrastructure.interfaces`,
   and `OpenStackCliAdapter` from `vibey.infrastructure.openstack.openstack_cli`.
2. New `src/vibey/infrastructure/interfaces/cloud_clients_interface.py`: Required behaviour 2, with
   the docstring shape of `src/vibey/infrastructure/secrets/interfaces/openbao_interface.py:1-6`
   ("Mirrors `vibey/infrastructure/cloud_clients.py` (ADR-0016). Interfaces declare; they never
   consume."). Do not edit `src/vibey/infrastructure/interfaces/__init__.py`.
3. `src/vibey/cli/composition.py`: Required behaviour 3. Read the file first and follow its style
   (if it declares `__slots__`, add `"_cloud_clients"`). Import `CloudClientSelector` from
   `vibey.infrastructure.cloud_clients` and `CloudClientSelectorInterface` from
   `vibey.infrastructure.interfaces.cloud_clients_interface`. Do not change the existing parameters
   or `current()`.
4. `src/vibey/cli/interfaces/composition_interface.py`: add to `CliCompositionInterface`
   ```python
   @property
   def cloud_clients(self) -> CloudClientSelectorInterface:
       """The selector `vibey worker --cloud cli` asks for the declared target's CLI adapter."""
       ...
   ```
   with its import.
5. `src/vibey/cli/main.py`:
   - imports: add `from vibey.application.interfaces import CloudClientPort` and
     `from vibey.domain.config import DeployConfig` (keep isort order); remove the `subprocess`
     import as in Required behaviour 9. `load_runtime_config_from_path` (`main.py:58`),
     `EXIT_USAGE` (`main.py:36`) and `CliComposition` (added by `fakes-job-wakeup`) are already
     imported.
   - the `azure: Annotated[` parameter (`main.py:1451-1459`, the block that starts `azure: Annotated[`
     and ends `] = "memory",`) → Required behaviour 4.
   - the block from `if azure not in ("memory", "az"):` through `azure_client = AzCliClientAdapter()`
     (`main.py:1481-1494`, whatever runs the login check in between) → Required behaviour 5.
   - after `provider = _resolve_provider(provider_opt)` (`main.py:1573`) → Required behaviour 6 and 7.
   - in the `build_full_worker(` call, `azure_client=azure_client,` → `azure_client=cloud_client,`
     plus a new line `deploy=deploy,` (Required behaviour 8).
   - the line `f"engines={engines_opt or 'all'} parallelism={count} provider={provider}"` →
     `f"engines={engines_opt or 'all'} parallelism={count} provider={provider} "` followed by a new
     line `f"deploy_target={deploy.target} cloud={cloud_mode}"` inside the same `typer.echo(`.
6. New `tests/infrastructure/test_cloud_clients.py` (default tier; below).
7. `tests/cli/test_operational_commands.py`: convert two tests and append ten (below). If a
   `fakes-cli-operational-*` lane has already moved the worker tests, edit the module that now holds
   `test_worker_azure_az_requires_a_logged_in_cli`
   (`grep -rln "def test_worker_azure_az_requires_a_logged_in_cli" tests/cli`) and append there; if
   that module invokes through `ops.invoke(memory_app, ...)`, pass `cloud_clients=...` through it as
   an extra `CliComposition` field instead of building `_CloudWorkerComposition`.
8. `tests/fakes/registry.py` (created by `fakes-registry`, which `fakes-job-wakeup` depends on):
   import `CloudClientSelector` and `CloudClientSelectorInterface`; append
   `CloudClientSelectorInterface` to `DRIVER_SEAMS`; append to `REGISTRY`
   `FakeRegistration(port=CloudClientSelectorInterface, build=CloudClientSelector, note="the real selector is its own fake: it holds a class map, runs nothing until select(), and tests inject a scripted CommandExecutor at its executor= seam (A2: the real class over an in-memory driver)")`,
   in the same form as the entries already there.
9. `tests/meta/patching_baseline.json`: after the test edits, run
   `uv run pytest -q -p no:cacheprovider tests/meta/test_patching_ratchet.py`. It fails for
   `tests/cli/test_operational_commands.py` because patches were removed; replace that file's entry
   with the corrected entry the failure message prints. Only ever lower a number.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/test_cloud_clients.py`
      passes with PostgreSQL stopped (the default-tier proof).
- [ ] `uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py -k "worker"` passes
      (integration: needs PostgreSQL 17).
- [ ] `grep -c "subprocess" src/vibey/cli/main.py` prints `0`.
- [ ] `grep -nE "subprocess.run|PostgresJobReadyNotifier|_fast_engine_preflight" tests/cli/test_operational_commands.py`
      shows none of those names inside the two converted tests or the ten new ones.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/cli/test_composition.py tests/application/test_interfaces_convention.py` passes.
- [ ] `git diff --stat` names only the nine files in "Where to change".
- [ ] `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` and
      `uv run coverage report --include='src/vibey/cli/*' --fail-under=100` pass after the
      whole-suite coverage run.

## Tests to write first (TDD)
**Default tier: new `tests/infrastructure/test_cloud_clients.py`** (no database, no marker, no
patching). Module constants `OPENSTACK_PREFLIGHT = ("openstack", "token", "issue", "-f", "value", "-c", "project_id")`
and `AZ_PREFLIGHT = ("az", "account", "show", "-o", "none")`, and this double at the selector's
`executor=` seam (if `tests/fakes/process.py` defines `ScriptedCommandExecutor` when you start, you
may use it instead; the assertions do not change):
```python
class _ScriptedCli:
    """A CommandExecutor for a cloud CLI preflight: one scripted answer, or an exception."""

    def __init__(self, answer: CommandResult | BaseException) -> None:
        self.answer = answer
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer
```
(`CommandResult` is `vibey.infrastructure.engines.claudeloop_process.CommandResult`.)
- `test_every_deploy_target_has_a_cli_adapter`: `set(CloudClientSelector.ADAPTERS) == set(DEPLOY_IAC_BY_TARGET)`
  (from `vibey.domain.config`); `ADAPTERS["azure"] is AzCliClientAdapter`;
  `ADAPTERS["openstack"] is OpenStackCliAdapter`; `CloudClientSelector().targets() == ("azure", "openstack")`.
- `test_select_returns_the_adapter_when_its_cli_is_ready`, parametrized over
  `("openstack", OpenStackCliAdapter, OPENSTACK_PREFLIGHT)` and `("azure", AzCliClientAdapter, AZ_PREFLIGHT)`:
  with `cli = _ScriptedCli(CommandResult(0, "", ""))`,
  `client = await CloudClientSelector(executor=cli).select(target)` is an instance of the adapter
  class and of `CloudClientPort`, and `cli.calls == [preflight_argv]`.
- `test_select_refuses_a_cli_that_is_not_logged_in`: `CommandResult(1, "", "Missing value auth-url required for auth plugin password")`
  → `select("openstack")` is None and `cli.calls == [OPENSTACK_PREFLIGHT]`.
- `test_select_refuses_a_missing_cli`: `FileNotFoundError(2, "No such file or directory", "az")` →
  `select("azure")` is None.
- `test_login_hint_is_the_adapters_own`: `login_hint("azure") == AzCliClientAdapter.LOGIN_HINT` and
  `login_hint("openstack") == OpenStackCliAdapter.LOGIN_HINT`.
- `test_an_unknown_target_is_refused_before_any_command`: `select("aws")` and `login_hint("aws")`
  each raise `UnknownCloudTarget` matching
  `r"no cloud CLI adapter for \[deploy\]\.target 'aws'; known: azure, openstack"`; `cli.calls == []`.
- `test_the_adapter_map_is_configurable`:
  `CloudClientSelector(executor=cli, adapters={"openstack": OpenStackCliAdapter})` has
  `targets() == ("openstack",)`, and its `select("azure")` raises `UnknownCloudTarget`.
- `test_selector_satisfies_its_interface`: `isinstance(CloudClientSelector(), CloudClientSelectorInterface)`.

**Integration tier: `tests/cli/test_operational_commands.py`** (the module is already
`pytestmark = pytest.mark.integration`; its tests use PostgreSQL through the real `build_app()`).
Add to the module's import block at the top whichever of these it does not already have:
`contextlib`, `dataclasses`, `from collections.abc import AsyncIterator, Mapping`,
`from vibey.application.dto import FeasibilityAssessment, StartupPreflightReport`,
`from vibey.application.interfaces import EngineAdapter`, `from vibey.bootstrap import AppResources`,
`from vibey.cli.composition import CliComposition`,
`from vibey.infrastructure.cloud_clients import CloudClientSelector`,
`from vibey.infrastructure.engines.claudeloop_process import CommandResult`, and the job-wakeup
fakes from `tests.fakes.queue` (`InMemoryJobWakeupOpener`, `InMemoryJobReadyNotifier`). Then append
these helpers (build the opener exactly the way the module's `_ComposedWithFakeWakeup`, added by
`fakes-job-wakeup`, builds it; read `tests/fakes/queue.py` for the constructors). The sweep double
stands in at the `AppResources.conductor_preflight` field, a declared seam, so no test here needs
the `_fast_engine_preflight` patch:
```python
AZ_PREFLIGHT = ("az", "account", "show", "-o", "none")
OPENSTACK_PREFLIGHT = ("openstack", "token", "issue", "-f", "value", "-c", "project_id")


class _ScriptedCli:
    """A CommandExecutor for a cloud CLI preflight: one scripted answer, or an exception."""

    def __init__(self, answer: CommandResult | BaseException) -> None:
        self.answer = answer
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


class _NothingToSweep:
    """ConductorPreflightInterface with nothing to report. The real sweep runs every engine's
    doctor; these tests are about the cloud client, so the sweep is replaced at its seam."""

    def __init__(self) -> None:
        self.projects: list[UUID] = []

    async def run(
        self, *, project_id: UUID, adapters: Mapping[EngineId, EngineAdapter]
    ) -> StartupPreflightReport:
        self.projects.append(project_id)
        return StartupPreflightReport(
            ineligible_engines=(),
            feasibility=FeasibilityAssessment(
                status="feasible",
                blocked_at=None,
                first_repair=None,
                confidence=1.0,
                required=0,
                required_measured=0,
            ),
        )


class _CloudWorkerComposition:
    """The real app over PostgreSQL with the in-memory job wakeup, a sweep with nothing to
    probe, and a cloud selector over the scripted CLI. Nothing here patches an import (9.b)."""

    def __init__(self, cli: _ScriptedCli) -> None:
        self.cli = cli
        self.sweep = _NothingToSweep()

    @contextlib.asynccontextmanager
    async def open_app(self) -> AsyncIterator[AppResources]:
        async with build_app() as resources:
            yield dataclasses.replace(
                resources,
                wakeup=InMemoryJobWakeupOpener(InMemoryJobReadyNotifier()),
                conductor_preflight=self.sweep,
            )

    def composition(self) -> CliComposition:
        return CliComposition(
            open_app=self.open_app, cloud_clients=CloudClientSelector(executor=self.cli)
        )


def _seed_cloud_project(tmp_path: Path, config: dict[str, object]) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("cloud-proj", tmp_path, max_cycles=1, config=config)

    asyncio.run(seed())
```
Every invocation below that reaches the worker body is
`runner.invoke(app, [...], obj=_CloudWorkerComposition(cli).composition())`, keeping the helper in a
variable when the test asserts on `cli.calls`.

Convert (replace each whole function, decorator to last assert, with a checked replacement whose
`old` text is copied from `read_file` output):
- `test_worker_azure_az_requires_a_logged_in_cli(tmp_path)` (`:1991-2001`): seed
  `{"deploy": {"target": "azure"}}`; `cli = _ScriptedCli(CommandResult(1, "", "Please run 'az login' to setup account."))`;
  `["worker", "--azure", "az", "--once"]` → exit 1, `"az login"` in the output, and
  `cli.calls == [AZ_PREFLIGHT]`.
- `test_worker_azure_az_builds_the_real_adapter_when_logged_in(tmp_path)` (`:2004-2025`): no
  `usefixtures` decorator any more; seed `{"deploy": {"target": "azure"}}`;
  `cli = _ScriptedCli(CommandResult(0, "", ""))`; `["worker", "--azure", "az", "--once"]` → exit 0,
  `"deploy_target=azure cloud=cli"` in the output, and `cli.calls == [AZ_PREFLIGHT]`.

Keep `test_worker_rejects_unknown_azure_mode` (`:1985-1988`) unchanged; it still passes. Append:
- `test_worker_rejects_unknown_cloud_mode()`: `["worker", "--cloud", "gcp"]` → exit 2 and
  `"--cloud must be 'memory' or 'cli'"` in the output.
- `test_worker_rejects_cloud_with_the_deprecated_azure_flag()`:
  `["worker", "--cloud", "cli", "--azure", "az"]` → exit 2 and `"pass only --cloud"` in the output.
- `test_worker_help_offers_cloud_and_hides_the_azure_alias()`: `["worker", "--help"]` → exit 0,
  `"--cloud"` in the output and `"--azure"` not in it.
- `test_worker_azure_az_refuses_a_project_targeting_openstack(tmp_path)`: seed `{}` (no vibey.toml
  in `tmp_path`, so the default target `openstack`); `cli = _ScriptedCli(CommandResult(0, "", ""))`;
  `["worker", "--azure", "az", "--once"]` → exit 2, `'target = "azure"'` and `"'openstack'"` in the
  output, and `cli.calls == []`.
- `test_worker_cloud_cli_preflights_openstack_for_the_default_target(tmp_path)`: seed `{}`;
  `cli = _ScriptedCli(CommandResult(0, "proj-1\n", ""))`; `["worker", "--cloud", "cli", "--once"]` →
  exit 0, `cli.calls == [OPENSTACK_PREFLIGHT]`, and `"deploy_target=openstack cloud=cli"` in the output.
- `test_worker_cloud_cli_refuses_without_openstack_credentials(tmp_path)`: seed `{}`;
  `CommandResult(1, "", "Missing value auth-url required for auth plugin password")` → exit 1,
  `"--cloud cli with [deploy].target = 'openstack' requires"` and `"openstack token issue"` in the output.
- `test_worker_cloud_cli_reports_a_missing_cli(tmp_path)`: seed `{}`;
  `_ScriptedCli(FileNotFoundError(2, "No such file or directory", "openstack"))` → exit 1 and
  `"requires OpenStack credentials"` in the output.
- `test_worker_reads_deploy_from_the_repository_for_a_project_that_stored_none(tmp_path)`:
  `(tmp_path / "vibey.toml").write_text('[deploy]\ntarget = "azure"\n', encoding="utf-8")`; seed `{}`;
  `["worker", "--once"]` → exit 0, `"deploy_target=azure cloud=memory"` in the output, `cli.calls == []`.
- `test_worker_prefers_the_stored_deploy_table(tmp_path)`: the same vibey.toml; seed
  `{"deploy": {"target": "openstack"}}`; `["worker", "--once"]` → exit 0 and
  `"deploy_target=openstack cloud=memory"` in the output.
- `test_worker_refuses_an_invalid_deploy_declaration(tmp_path)`: vibey.toml holds
  `'[deploy]\ntarget = "aws"\n'`; seed `{}`; `["worker", "--once"]` → exit 3 and `"deploy.target"`
  in the output (`guard()` prints the `ConfigError` to stderr, which `res.output` includes).

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/infrastructure/test_cloud_clients.py
uv run pytest -q -p no:cacheprovider tests/infrastructure/test_cloud_clients.py tests/infrastructure/openstack tests/infrastructure/azure tests/cli/test_composition.py tests/fakes tests/meta tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider tests/cli/test_operational_commands.py -k "worker"
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100
```
One coverage run at a time. The `-k "worker"` run and the whole-suite coverage run need
PostgreSQL 17 reachable (`VIBEY_TEST_DATABASE_URL`); the `--noconftest` run needs nothing. If
`ruff check` reports only import order (`I001`), run `uv run ruff check --select I --fix` on the
files you changed, then `uv run ruff format` on them.

## Out of scope
- The adapters themselves (lanes `split-331-2-openstack-cli-adapter`, `split-331-3-az-preflight`),
  `[deploy]` parsing and `build_full_worker(deploy=...)` (lanes `split-330-1-deploy-target-config`,
  `split-330-3-spec-follows-target`), and installing any CLI (lane `split-331-5-openstack-installer`).
- The other patches in `test_operational_commands.py` (`fakes-cli-composition`,
  `fakes-cli-operational-*`); the `_fast_engine_preflight` fixture itself stays for the tests that
  still use it. This lane removes the two `vibey.cli.main.subprocess.run` patches, which
  `fakes-cli-composition` lists at `:1488`.
- AWS and GCP targets; the Kubernetes operator's project config; the deploy interview wording.
- Taking the worker tests off PostgreSQL (`fakes-cli-operational-3`).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, README.md or the skill
  trees (for example `docs/reference/cli.md` still documents `--azure`); the docs wave owns them.
  Do not push, open PRs, or change git remotes. Commit locally with the Title as the subject and
  the footer
  `BREAKING CHANGE: vibey worker --azure az now requires the project's [deploy].target to be "azure" and preflights after the project is resolved; --cloud cli is the switch and --azure is a hidden, deprecated alias; a worker whose project stored no [deploy] reads the repository's vibey.toml and exits 3 on an invalid declaration.`
  The hooks add the `Made-With:` trailer.

## Standing constraints
- Substitute only at a declared seam: `CliRunner.invoke(..., obj=CliComposition(...))`, a
  constructor keyword, or an `AppResources` field swapped inside the composition's `open_app`.
  Never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock` in new or converted tests
  (9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
- Every new seam is registered in `tests/fakes/registry.py` in this lane (A2).
- The patching ratchet only goes down: lower `tests/meta/patching_baseline.json`, never raise it.
- Tests that seed a project stay `integration`; the selector's unit tests are the default-tier proof.
- Exception classes carry no behaviour and get no interface (`src/vibey/infrastructure/cache/redis.py:20`).
- Change existing files with `edit_file` or a checked replacement, append tests, and never rewrite an
  existing file (EDITING-RULES.md). Keep line 1 (the provenance header) of every file.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.

**Depends on:** split-331-2-openstack-cli-adapter, split-331-3-az-preflight, split-330-1-deploy-target-config, split-330-3-spec-follows-target, fakes-job-wakeup
- split-331-2-openstack-cli-adapter: `OpenStackCliAdapter` with `PROVIDER`, `PREFLIGHT_ARGV`,
  `LOGIN_HINT` and `preflight()`.
- split-331-3-az-preflight: the same attributes and `preflight()` on `AzCliClientAdapter`.
- split-330-1-deploy-target-config: `DeployConfig.from_mapping`, `DEPLOY_IAC_BY_TARGET`, and the
  `ConfigError` for a target with no adapter.
- split-330-3-spec-follows-target: `build_full_worker(..., deploy=...)`, and `[deploy]` in
  `RUNTIME_CONFIG_KEYS` so `load_runtime_config_from_path` returns and validates it.
- fakes-job-wakeup: `CliComposition` and `CliCompositionInterface`, `CliComposition.current()` in
  the worker, `AppResources.wakeup` (through `rmq-r02-wakeup-composition`), the in-memory job
  wakeup fakes, and (through `fakes-registry`) `tests/fakes/registry.py` and the patching ratchet.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
