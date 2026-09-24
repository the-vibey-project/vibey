## Title
feat(config): declare the test harness's keys in vibey.toml's [test_harness] table

## Why
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`): "a hard-coded value that could
have been a key is a decision taken away from the next human adopter". Draft ADR-0045 §14 lists
the harness's keys. This lane declares and validates them in the pure configuration model; the
next lane (harness-T05-test-harness-config) resolves them against the environment. Nothing reads
them at run time until harness-T06 onwards.

Two facts of the integration tree shape it:
- `src/vibey/domain/` is pure: `tests/domain/test_domain_purity.py:52-61` refuses any `pathlib`
  import, so "absolute" is checked on the string, never with `PurePosixPath`.
- Validation reuses harness-T01's `EnvNamePatterns` and `TestRouteMode`
  (`src/vibey/domain/test_harness.py`), so this lane depends on harness-T01.

## Required behaviour
1. **`TestHarnessConfig`** in `src/vibey/domain/config.py`, `@dataclass(frozen=True, slots=True)`,
   placed after `TelemetryConfig` (`:165-170`). A `__post_init__` validates every field; each
   violation raises `ConfigError(f"test_harness.{field}", <message>)` (`ConfigError(path, message)`, `:38-42`).
   A `bool` is refused wherever an `int` is expected.

   | field | default | constraint |
   |---|---|---|
   | `backend: str` | `"auto"` | `auto`, `local` or `rabbitmq` |
   | `state_dir: str \| None` | `None` | when set, starts with `/` or `~` |
   | `root: str` | `"/"` | starts with `/` |
   | `instance: str \| None` | `None` | when set, matches `^[a-z0-9][a-z0-9-]{0,62}$` |
   | `command: tuple[str, ...]` | `("uv", "run", "--no-sync", "pytest")` | non-empty, every item a non-empty str |
   | `coverage_command: tuple[str, ...]` | `("uv", "run", "--no-sync", "coverage")` | same |
   | `base_env: tuple[str, ...]` | `("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_*", "TMPDIR", "TZ", "SHELL", "TERM", "XDG_*", "UV_*")` | `EnvNamePatterns(base_env)` constructs |
   | `pass_env: tuple[str, ...]` | `("VIBEY_TEST_*", "VIBEY_QUEUE_BACKEND", "VIBEY_ENGINE_INVOCATION", "PYTEST_ADDOPTS")` | valid patterns; no pattern matches the name `VIBEY_HARNESS_RUN`, and none starts with `VIBEY_HARNESS_` |
   | `database_env: str` | `"VIBEY_TEST_DATABASE_URL"` | `""`, or matches `^[A-Za-z_][A-Za-z0-9_]*$` |
   | `tree_exclude: tuple[str, ...]` | `(".hypothesis/",)` | each item non-empty and not starting with `/` |
   | `pass_ttl_seconds: int` | `86400` | ≥ 0 |
   | `fail_ttl_seconds: int` | `900` | ≥ 0 |
   | `run_bound_seconds: int` | `3600` | ≥ 60 |
   | `queue_wait_seconds: int` | `3600` | ≥ 1 |
   | `wait_seconds: int` | `7200` | ≥ 1 |
   | `output_tail_bytes: int` | `65536` | 1024–10485760 |
   | `retention_days: int` | `14` | ≥ 1 |
   | `delivery_limit: int` | `3` | 1–100 |
   | `reconcile_interval_seconds: int` | `30` | ≥ 1 |
   | `route_engines: str` | `"off"` | `TestRouteMode.parse(value)` succeeds; stored as the parsed `.value` |
   | `engine_wait_seconds: int` | `110` | ≥ 1 |
2. **`_parse_test_harness(data: dict[str, Any]) -> TestHarnessConfig`**, a module function next
   to `_parse_telemetry` (`:484-493`), in its style: `table = _optional(data, "test_harness", "test_harness", dict, {})`,
   then `_optional(table, "<key>", "test_harness.<key>", <type>, <default>)` (`:358-364`) for
   each key. TOML arrays arrive as `list`: check every item is a `str` (else `ConfigError`) and
   convert to `tuple`. Unknown keys are ignored, as every other table does.
3. **`VibeyConfig`** (`:319-342`) gains, as its last field,
   `test_harness: TestHarnessConfig = field(default_factory=TestHarnessConfig)`, and
   `parse_config` (`:652-721`) passes `test_harness=_parse_test_harness(data)` after
   `siem=_parse_siem(data)` (`:720`).
4. **`TestHarnessConfigInterface`** in `src/vibey/domain/interfaces/config_interface.py`: a
   `@runtime_checkable` Protocol with one read-only property per field, copying
   `TelemetryConfigInterface` (`:30-36`). Do not edit `src/vibey/domain/interfaces/__init__.py`.

## Where to change
- `src/vibey/domain/config.py` and `src/vibey/domain/interfaces/config_interface.py` (both with
  `edit_file`; `config.py` is 724 lines, never `write_file` it).
- `tests/domain/test_config.py`: add `from vibey.domain import config as cfg` and
  `from vibey.domain.interfaces import config_interface as config_iface` to the import block at
  the top (after `:4`, with `edit_file`, so ruff's E402 stays clean), then append the tests at
  the end. Refer to `cfg.TestHarnessConfig`, never import a `Test*` name into the test module.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).test_harness == TestHarnessConfig()`.
- [ ] Each constraint in behaviour 1 raises `ConfigError` whose `path` is `test_harness.<key>`, both from `parse_config` and from direct construction.
- [ ] `pass_env = ["VIBEY_*"]` and `pass_env = ["VIBEY_HARNESS_FRESH"]` are refused.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
Appended to `tests/domain/test_config.py`:
- `test_test_harness_defaults`
- `test_test_harness_reads_every_key_from_the_table` (a full `[test_harness]` table through `load_config_from_string`)
- `test_test_harness_rejects_each_bad_value` (parametrized over every row of behaviour 1, plus a `bool` for an int and a non-string list item)
- `test_test_harness_pass_env_may_not_reach_the_run_marker`
- `test_test_harness_config_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/test_config_loader.py tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Resolving the keys against the environment, and the `infrastructure/test_harness/` package (harness-T05-test-harness-config).
- Any `[bus]` or `[queue]` key; lane rmq-r01-queue-config owns them.
- CHANGELOG.md, docs/ (`docs/reference/configuration.md` is the docs wave's), ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T01-test-run-key.
- **Files touched:** `src/vibey/domain/config.py`, `src/vibey/domain/interfaces/config_interface.py`, `tests/domain/test_config.py`.
- **Shares a file with:** `src/vibey/domain/config.py` (rmq-r01-queue-config and rmq-r34-defaults-flip edit other tables; harness-T28-route-flip changes one default here later). If rmq-r01 has landed, keep its fields.
- **Must keep passing unchanged:** every existing test in `tests/domain/test_config.py` and `tests/infrastructure/test_config_loader.py`, `tests/infrastructure/test_sovereign_surfaces.py`, `tests/domain/test_domain_purity.py`, and the protected tests.
- **Registry (amendment A4):** nothing; configuration values are `VALUE_CONTRACT`s.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
