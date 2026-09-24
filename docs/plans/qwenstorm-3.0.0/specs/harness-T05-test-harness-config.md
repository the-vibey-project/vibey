## Title
feat(test-harness): resolve the harness's keys without a vibey.toml, environment first

## Why
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) makes every tunable a key, and
draft ADR-0045 §14 lists the harness's. harness-T05a declared them in `[test_harness]`
(`TestHarnessConfig`, `src/vibey/domain/config.py`). The harness must also run where no
`vibey.toml` exists, which includes this repository's own root: a push hook has no project
file. So resolution is its own step, in infrastructure:
- the environment beats the file, and the file beats the default;
- the default `state_dir` follows `$XDG_STATE_HOME`, else `~/.local/state/vibey/test-harness`;
- the default instance name is the sanitized host name.

This lane also creates the `src/vibey/infrastructure/test_harness/` package and its
`interfaces` package, which every later infrastructure harness lane adds a module to, and it
declares `TestHarnessNotConfigured`, which harness-T15a and harness-T25a raise. The error lives
here, beside the settings that decide the backend, following `ConfigError` in
`src/vibey/domain/config.py:38`; that keeps `domain/errors.py` out of the harness lanes.

## Required behaviour
1. **Packages.** `src/vibey/infrastructure/test_harness/__init__.py` holds the provenance line
   and the docstring `"""The test harness: one test run at a time per machine, fed by a queue (sub-doctrine 8.e; ADR-0045)."""`.
   `src/vibey/infrastructure/test_harness/interfaces/__init__.py` holds the provenance line and
   `"""Seams the test harness declares. Interfaces declare; they never consume."""`. Neither
   re-exports anything; later lanes import from module paths.
2. **`src/vibey/infrastructure/test_harness/settings.py`**:
   - `class TestHarnessNotConfigured(VibeyError)` (`vibey.domain.errors.VibeyError`), docstring
     "The test harness cannot run with the backend it was asked for; the message names the remedy."
   - `class InstanceName` with the static method `sanitize(raw: str) -> str`: lower-case the
     input; replace every character outside `[a-z0-9-]` with `-`; strip leading and trailing `-`;
     truncate to 63 characters (then strip a trailing `-` again); return `"localhost"` if empty.
   - `@dataclass(frozen=True, slots=True) class TestHarnessSettings` of resolved values:
     `backend: str`, `state_dir: Path`, `root: Path`, `instance: str`, `command: tuple[str, ...]`,
     `coverage_command: tuple[str, ...]`, `base_env: EnvNamePatterns`, `pass_env: EnvNamePatterns`,
     `database_env: str`, `tree_exclude: tuple[str, ...]`, `pass_ttl: timedelta`,
     `fail_ttl: timedelta`, `run_bound_seconds: int`, `queue_wait_seconds: int`,
     `wait_seconds: int`, `output_tail_bytes: int`, `retention: timedelta`,
     `delivery_limit: int`, `reconcile_interval_seconds: int`, `route_engines: TestRouteMode`,
     `engine_wait_seconds: int` (`EnvNamePatterns` and `TestRouteMode` from
     `vibey.domain.test_harness`).
     - property `lock_path -> Path`: `self.state_dir / "machine.lock"`.
     - classmethod
       `from_sources(cls, config: VibeyConfig | None, environ: Mapping[str, str], *, hostname: str | None = None) -> TestHarnessSettings`.
       The base is `config.test_harness`, or `TestHarnessConfig()` when `config is None`. These
       variables override the base; an empty or whitespace-only value counts as unset:

       | variable | overrides |
       |---|---|
       | `VIBEY_HARNESS_BACKEND` | `backend` |
       | `VIBEY_HARNESS_STATE_DIR` | `state_dir` |
       | `VIBEY_HARNESS_ROOT` | `root` |
       | `VIBEY_HARNESS_INSTANCE` | `instance` |
       | `VIBEY_HARNESS_WAIT_SECONDS` | `wait_seconds` (parsed with `int`) |

       Apply each with `dataclasses.replace(base, <field>=<value>)`, so harness-T05a's
       `__post_init__` validates it. A `ConfigError` or a failed `int()` becomes
       `ValueError(f"{variable}: <reason>")` naming the variable.
     - Resolution, with no filesystem access:
       - `state_dir`: a configured value starting with `~` has the `~` replaced by the home
         (`environ["HOME"]` when set, else `Path.home()`); any other configured value is
         `Path(value)`. Unconfigured: `Path(environ["XDG_STATE_HOME"]) / "vibey" / "test-harness"`
         when that variable is set and starts with `/`, else `<home> / ".local" / "state" / "vibey" / "test-harness"`.
       - `root`: `Path(value)`.
       - `instance`: the configured value, else `InstanceName.sanitize(hostname or socket.gethostname())`.
       - `pass_ttl`, `fail_ttl` and `retention` are `timedelta(seconds=...)` and `timedelta(days=retention_days)`;
         `route_engines` is `TestRouteMode(value)`; the pattern tuples become `EnvNamePatterns`.
3. **`src/vibey/infrastructure/test_harness/interfaces/settings_interface.py`** declares
   `@runtime_checkable` `TestHarnessSettingsInterface` (one read-only property per field, plus
   `lock_path`) and `InstanceNameInterface` (`sanitize`). It imports nothing from `settings.py`.
4. **`.importlinter`**: append the line `    vibey.infrastructure.test_harness.interfaces` as the
   last entry of `source_modules` in `[importlinter:contract:infrastructure-interfaces-declare-only]`
   (today the list ends with `vibey.infrastructure.tracker.interfaces` at `:129`; if a lane
   appended after it, append after the last entry).
5. **No rows in `_SURFACE_ENV_VARS`** (`src/vibey/infrastructure/config_loader.py:17`): the harness
   resolves its own environment because it must work with no file at all.

## Where to change
- New `src/vibey/infrastructure/test_harness/__init__.py`, `.../settings.py`,
  `.../interfaces/__init__.py`, `.../interfaces/settings_interface.py`. Copy the package-docstring
  style of `src/vibey/infrastructure/bus/__init__.py:1-2`.
- `.importlinter` (one appended line, with `edit_file`).
- New `tests/infrastructure/test_harness/__init__.py` (the provenance line only) and
  `tests/infrastructure/test_harness/test_settings.py`.

## Acceptance criteria
- [ ] `from_sources(None, {"HOME": "/h"}, hostname="Box.local")` gives `state_dir == Path("/h/.local/state/vibey/test-harness")`, `instance == "box-local"` and every other default of `TestHarnessConfig()`.
- [ ] Precedence (environment > file > default) holds for each of the five variables; a blank variable is unset; a bad value raises `ValueError` naming its variable.
- [ ] `state_dir` follows `XDG_STATE_HOME`, else `HOME`; `~/x` expands against `environ["HOME"]`.
- [ ] `uv run lint-imports` and `uv run pytest -q -p no:cacheprovider tests/meta/test_import_contracts_bind.py` pass.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_settings.py` imports
`from vibey.infrastructure.test_harness import settings as hs` and
`from vibey.infrastructure.test_harness.interfaces import settings_interface as hsi`:
- `test_defaults_without_a_config`
- `test_config_values_are_resolved` (a `VibeyConfig` from `load_config_from_string` with a `[test_harness]` table)
- `test_env_beats_config_beats_default` (parametrized over the five variables)
- `test_blank_env_values_are_unset`
- `test_bad_env_values_name_the_variable` (parametrized: `VIBEY_HARNESS_BACKEND=nope`, `VIBEY_HARNESS_WAIT_SECONDS=soon`, `VIBEY_HARNESS_WAIT_SECONDS=0`, `VIBEY_HARNESS_ROOT=relative`)
- `test_state_dir_follows_xdg_then_home`
- `test_tilde_state_dir_expands_against_the_given_home`
- `test_instance_sanitize_table` (parametrized: `"Adams-MacBook.local"` → `"adams-macbook-local"`, `"___"` → `"localhost"`, a 70-character name → 63 characters, no trailing `-`)
- `test_lock_path_is_under_the_state_dir`
- `test_not_configured_is_a_vibey_error`
- `test_settings_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/infrastructure/test_config_loader.py tests/meta/test_import_contracts_bind.py tests/domain/test_config.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading the settings at run time (harness-T06 onwards).
- Any `[bus]` key (rmq-r01-queue-config).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05a-test-harness-config-keys.
- **Files touched:** the four new package files, `.importlinter`, and the two new test files.
- **Shares a file with:** `.importlinter` (rmq-r03, rmq-r12, rmq-r21 append to other contracts; append your line at the end of this contract's list).
- **Must keep passing unchanged:** `tests/infrastructure/test_config_loader.py`, `tests/infrastructure/test_sovereign_surfaces.py`, `tests/meta/test_import_contracts_bind.py`, harness-T05a's tests, and the protected tests.
- **Registry (amendment A4):** nothing. `TestHarnessSettings` is a value (`VALUE_CONTRACT`) and `InstanceName` a pure policy.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names (`hs.TestHarnessSettings`, never `from ... import TestHarnessSettings`).
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; pass `environ` dicts and `hostname=` explicitly. Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never touch the real machine lock: every settings object a test builds gets `HOME` and `VIBEY_HARNESS_STATE_DIR` under `tmp_path` (or explicit fake paths it never opens).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
