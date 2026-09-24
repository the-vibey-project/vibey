## Title
feat(domain): declare the local stack that `vibey install` installs on Arch Linux and macOS

## Why
The operator's standard (2026-09-22): the installer must always install everything a human
developer needs to run vibey on the default OSes. Those are Arch Linux (the sovereign default)
and macOS (the paid default). Today `vibey install` knows one thing, PostgreSQL
(src/vibey/cli/main.py:1155-1182). Its package names are buried in the methods of
`PostgresLocalService` (src/vibey/infrastructure/postgres.py:310-365). Sub-doctrine 12.c
(src/vibey_tools/gh/docs/doctrines.md:364) and ADR-0018 say the dependency list must be
declared data, reviewed in a pull request, not scattered calls. Sub-doctrine 8.d (doctrines.md:200)
makes `gpt-oss:20b` this era's default model. This lane adds only the pure vocabulary and the
first three entries (postgres, ollama, model). Later lanes add more entries and the code that
carries them out.

## Required behaviour
1. A new pure module `src/vibey/domain/local_stack.py` declares the names below exactly. Use
   frozen, slotted dataclasses. Follow the `StrEnum` style of `src/vibey/domain/phase.py:8-17`.
   ```python
   DEFAULT_LOCAL_MODEL: Final = "gpt-oss:20b"          # sub-doctrine 8.d
   DEFAULT_LOCAL_MODEL_DOWNLOAD: Final = "14 GB"       # ollama.com/library/gpt-oss:20b, read 2026-09-22

   class HostOs(StrEnum):         ARCH = "arch"; MACOS = "macos"
   class PackageSource(StrEnum):  PACMAN = "pacman"; AUR = "aur"; BREW_FORMULA = "brew-formula"; BREW_CASK = "brew-cask"; NONE = "none"
   class ServiceManager(StrEnum): SYSTEMD = "systemd"; BREW_SERVICES = "brew-services"; MACOS_APP = "macos-app"
   class InstallerKind(StrEnum):  PACKAGE = "package"; POSTGRES = "postgres"; MODEL = "model"
   class DependencyState(StrEnum): READY = "ready"; MISSING = "missing"; STOPPED = "stopped"; FAILED = "failed"; SKIPPED = "skipped"; UNSUPPORTED = "unsupported"

   PackageSpec(source: PackageSource, names: tuple[str, ...] = (), binaries: tuple[str, ...] = ())
   ServiceSpec(manager: ServiceManager, name: str)
   ProbeSpec(argv: tuple[str, ...], privileged: bool = False, timeout_seconds: float = 120.0, timeout_hint: str = "")
   HostRecipe(package: PackageSpec, service: ServiceSpec | None = None, probe: ProbeSpec | None = None,
              post_install: tuple[tuple[str, ...], ...] = (), hint: str = "")
   DependencySpec(key: str, title: str, group: str, default: bool, installer: InstallerKind,
                  arch: HostRecipe | None = None, macos: HostRecipe | None = None,
                  requires: tuple[str, ...] = (), note: str = "")
       def recipe(self, host: HostOs | None) -> HostRecipe | None   # arch for ARCH, macos for MACOS, None otherwise
   DependencyReport(key: str, state: DependencyState, detail: str, changed: bool = False, fix: str = "")
       @property ok -> bool   # state is READY
   LocalStackReport(host_label: str, reports: tuple[DependencyReport, ...])
       @property ok -> bool       # every report ok (an empty stack is ok)
       @property changed -> bool  # any report changed
   class UnknownDependency(ValueError)
   CATALOGUE_ENTRIES: Final[tuple[DependencySpec, ...]]
   class LocalStackCatalogue
   ```
   Field meanings:
   - `binaries`: if any one of them is on `PATH`, the package counts as installed.
   - `post_install`: argv steps that run with privilege after the package is installed. The
     token `{user}` is replaced by the login user.
   - `hint`: one line printed under a ready dependency after install, for example an
     `export` line.
   - `note`: the recorded reason for a choice (sub-doctrine 10.f). It is never printed as a
     fix.
2. `CATALOGUE_ENTRIES` holds exactly these three entries, in this order. Declaration order
   is install order.
   - **postgres**:
     - title "PostgreSQL", group "services", default True, installer `POSTGRES`.
     - arch: `HostRecipe(PackageSpec(PACMAN, ("postgresql",), ("pg_isready",)), hint=H)`.
     - macos: `HostRecipe(PackageSpec(BREW_FORMULA, ("postgresql@17",), ()), hint=H)`.
     - `H` is `"export VIBEY_PG_URL=postgresql://$USER@localhost:5432/vibey"`.
     - note: "Homebrew is pinned to 17, the major the chart (deploy/helm/vibey/values.yaml:53)
       and CI run. Arch's repositories carry only the current major (18.6 on 2026-09-22), which
       vibey supports (14+)."
   - **ollama**:
     - title "Ollama", group "services", default True, installer `PACKAGE`.
     - arch: `HostRecipe(PackageSpec(PACMAN, ("ollama",), ("ollama",)), ServiceSpec(SYSTEMD, "ollama"), ProbeSpec(("ollama", "list"), timeout_seconds=60.0))`.
     - macos: `HostRecipe(PackageSpec(BREW_FORMULA, ("ollama",), ("ollama",)), ServiceSpec(BREW_SERVICES, "ollama"), ProbeSpec(("ollama", "list"), timeout_seconds=60.0))`.
   - **model**:
     - title f"local model {DEFAULT_LOCAL_MODEL}", group "services", default True, installer
       `MODEL`.
     - arch and macos: `HostRecipe(PackageSpec(PackageSource.NONE))`.
     - requires ("ollama",).
3. `LocalStackCatalogue(entries: tuple[DependencySpec, ...] = CATALOGUE_ENTRIES)`:
   - `__init__` raises `ValueError` if a key repeats, or if a `requires` key is not declared
     earlier in the tuple.
   - `entries()` returns the tuple.
   - `keys()` returns the keys in declaration order.
   - `groups()` returns the distinct groups in declaration order.
   - `get(key)` returns the entry, or raises `UnknownDependency`. The message is
     `unknown dependency or group 'x'; known: <keys and groups, comma-separated>`.
   - `resolve(host, *, only=(), extra=(), exclude=())` returns a tuple of entries in
     declaration order. The steps run in this order:
     1. Each name in `only`, `extra` and `exclude` is either a key or a group name. A group
        name means every key in that group. An unknown name raises `UnknownDependency`.
     2. The starting set is:
        - if `only` is given: exactly those keys;
        - otherwise: every entry with `default=True` whose `recipe(host)` is not None.
     3. Add `extra`.
     4. Add every `requires`, transitively.
     5. Remove `exclude`.
     With `host=None` and no `only`, the result is empty.
4. The module stays pure. It may use `dataclasses`, `enum` and `typing` only, and
   `tests/domain/test_domain_purity.py` must still pass.
5. `src/vibey/domain/interfaces/local_stack_interface.py` declares these `@runtime_checkable`
   Protocols (ADR-0016):
   - `LocalStackCatalogueInterface`, with the six methods above;
   - `DependencySpecInterface`, with the properties plus `recipe`;
   - `DependencyReportInterface`;
   - `LocalStackReportInterface`.

   Import the implementation types under `TYPE_CHECKING` only, as
   `src/vibey/domain/interfaces/phase_timing_interface.py:14-21` does.

## Where to change
- Create `src/vibey/domain/local_stack.py`. Its first line is the provenance comment, copied
  byte for byte from line 1 of `src/vibey/domain/phase.py`.
- Create `src/vibey/domain/interfaces/local_stack_interface.py`. Do not edit
  `domain/interfaces/__init__.py`.
- Create `tests/domain/test_local_stack.py`.

## Acceptance criteria
- [ ] `resolve(HostOs.ARCH)` and `resolve(HostOs.MACOS)` contain postgres, ollama and model, in
      that relative order.
- [ ] `resolve(HostOs.MACOS, only=("model",))` returns ollama then model.
- [ ] `resolve(HostOs.ARCH, exclude=("model",))` has no model.
- [ ] `resolve(None)` is empty, and `resolve(None, only=("postgres",))` is (postgres,).
- [ ] A group name expands, an unknown name raises `UnknownDependency` naming the known keys,
      and duplicate or forward `requires` keys raise `ValueError`.
- [ ] No recipe runs a downloaded script. For every probe and post-install argv, `argv[0]` is
      not one of `curl`, `wget`, `sh`, `bash` or `zsh`.
- [ ] `uv run coverage report --include='src/vibey/domain/*' --fail-under=100` passes.

## Tests to write first (TDD)
`tests/domain/test_local_stack.py`. Later lanes append entries, so never assert the complete
list of keys. Assert membership and relative order.
- `test_default_local_model_is_gpt_oss_20b`: the constant, and the model entry's title
  contains it.
- `test_core_entries_have_a_recipe_for_both_default_oses`.
- `test_every_entry_has_package_names_unless_its_source_is_none`: a guard over every entry.
- `test_resolve_defaults_keep_declaration_order`.
- `test_resolve_only_pulls_in_requirements`.
- `test_resolve_exclude_drops_the_model`.
- `test_resolve_expands_a_group_name`.
- `test_resolve_rejects_an_unknown_name_and_lists_the_known_ones`.
- `test_unsupported_host_resolves_to_nothing_unless_named`.
- `test_catalogue_rejects_duplicate_keys_and_forward_requirements`.
- `test_no_recipe_pipes_a_remote_script_into_a_shell`: a guard over every entry.
- `test_reports_are_ok_only_when_ready_and_a_stack_is_ok_when_all_are`: the `ok` and
  `changed` properties.
- `test_implementations_satisfy_their_interfaces`: `isinstance` against each Protocol.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Running any command: that is lanes installer-host-runner and installer-service-runner.
- The other entries: docker, toolchain, rabbitmq/valkey, vscode and the paid CLIs have their
  own lanes.
- `PostgresLocalService` and the CLI.
- Docs, CHANGELOG, ADRs and skill trees.

Commit as `feat(domain): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
