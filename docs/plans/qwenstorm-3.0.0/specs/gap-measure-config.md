## Title
feat(config): a [measure] table declares where measurements go and how often samplers run

## Why
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`): "everything that can be made
generic and configurable is made so … A default is configurability with an opinion; a constant
is not." The measurement lanes (8.g, `:316-324`) need five decisions an adopter must be able to
change: which ledger holds measurements that belong to no one project, how often the samplers
run, whether the family telemetry sink and its spans are on, which measurement logs are
ingested, and which RabbitMQ queues are sampled. This lane declares them as `[measure]` keys
with environment overrides, beside the surface tables (`src/vibey/domain/config.py:194-342`)
and their environment overlay (`src/vibey/infrastructure/config_loader.py:12-80`).

## Required behaviour
1. `src/vibey/domain/config.py` gains, after `SiemConfig` (`:308-315`):
   ```python
   @dataclass(frozen=True, slots=True)
   class MeasureConfig:
       """`[measure]`: where measurements go and how often samplers run (8.g)."""
       fleet_project_id: UUID = FLEET_PROJECT_ID
       sample_seconds: int = 60
       family_telemetry: bool = True
       family_spans: bool = False
       logs: tuple[str, ...] = (".vibey/measurements.jsonl",)
       amqp_queues: tuple[str, ...] = ()
   ```
   `FLEET_PROJECT_ID` is imported from `vibey.domain.measurement` (lane `gap-measure-domain`).
2. `MeasureConfig.from_data(cls, data: dict[str, Any]) -> MeasureConfig` (a classmethod) reads
   `table = _optional(data, "measure", "measure", dict, {})`, then:
   - `fleet_project_id`: `_optional(table, "fleet_project_id", "measure.fleet_project_id", str,
     str(FLEET_PROJECT_ID))`, then `UUID(raw)`; a `ValueError` becomes
     `ConfigError("measure.fleet_project_id", f"must be a UUID, got {raw!r}")`.
   - `sample_seconds`: an `int` that is not a `bool` and is `>= 1`, else
     `ConfigError("measure.sample_seconds", "must be a whole number of seconds, at least 1")`.
   - `family_telemetry`, `family_spans`: `bool` through `_optional`.
   - `logs`, `amqp_queues`: a list of strings, or one string split on `","` (what the environment
     overlay produces). Each entry is stripped and must be non-empty, else
     `ConfigError("measure.<key>", "must be a list of non-empty strings")`. Stored as a tuple.
3. `VibeyConfig` (`:318-342`) gains `measure: MeasureConfig = field(default_factory=MeasureConfig)`
   as its last field, and `parse_config` (`:696-720`) passes `measure=MeasureConfig.from_data(data)`.
4. `src/vibey/infrastructure/config_loader.py`:
   - A new `_MEASURE_ENV_VARS: tuple[tuple[str, str, str, type], ...]` after `_SURFACE_ENV_VARS`
     (`:17-59`):
     `("measure", "fleet_project_id", "VIBEY_MEASURE_FLEET_PROJECT_ID", str)`,
     `("measure", "sample_seconds", "VIBEY_MEASURE_SAMPLE_SECONDS", int)`,
     `("measure", "family_telemetry", "VIBEY_MEASURE_FAMILY_TELEMETRY", bool)`,
     `("measure", "family_spans", "VIBEY_MEASURE_FAMILY_SPANS", bool)`,
     `("measure", "logs", "VIBEY_MEASURE_LOGS", list)`,
     `("measure", "amqp_queues", "VIBEY_MEASURE_AMQP_QUEUES", list)`.
   - `apply_env_overrides` (`:62-80`) iterates `(*_SURFACE_ENV_VARS, *_MEASURE_ENV_VARS)` and
     learns two casts: `bool` accepts `1/true/yes/on` and `0/false/no/off` (stripped, any case),
     else `ValueError(f"{variable} must be a boolean value")`; `list` stores the raw text
     unchanged (the domain parser splits it). The docstring says "surface and measure".
   - A new module function, with the reason comment "the same module-function form as its
     neighbours `load_config_from_path` and `load_runtime_config_from_path`; this module
     converges as a unit (ADR-0016)":
     ```python
     def load_measure_config(path: Path, environ: Mapping[str, str] = os.environ) -> MeasureConfig:
         data = parse_toml_string(path.read_text()) if path.is_file() else {}
         apply_env_overrides(data, environ)
         return MeasureConfig.from_data(data)
     ```
     So an environment variable works with no `vibey.toml` at all (a cluster renders none).

## Where to change
- `src/vibey/domain/config.py`, `src/vibey/infrastructure/config_loader.py` (both with `edit_file`;
  `config.py` is 724 lines).
- Append tests to `tests/domain/test_config.py` and `tests/infrastructure/test_config_loader.py`.

## Acceptance criteria
- [ ] A minimal `[project]` config has `config.measure == MeasureConfig()` and
      `config.measure.fleet_project_id == FLEET_PROJECT_ID`.
- [ ] `VIBEY_MEASURE_SAMPLE_SECONDS=5` and `VIBEY_MEASURE_LOGS="a.jsonl, b.jsonl"` reach
      `load_measure_config(tmp_path / "missing.toml")` as `5` and `("a.jsonl", "b.jsonl")`.
- [ ] `VIBEY_MEASURE_FAMILY_SPANS=maybe` raises `ValueError` naming the variable.
- [ ] Every existing test in both test files passes unchanged; 100% branch coverage of
      `src/vibey/domain/` and `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/domain/test_config.py`:
- `test_measure_defaults`
- `test_measure_keys_parse_from_toml` (every key set in a `[measure]` table)
- `test_invalid_measure_config_is_rejected` (parametrized: `fleet_project_id = "nope"`,
  `sample_seconds = 0`, `sample_seconds = true`, `logs = [""]`, `logs = 3`,
  `amqp_queues = [1]`, `family_spans = "yes"`), each matching its `ConfigError` path
- `test_measure_lists_accept_comma_separated_text`

Append to `tests/infrastructure/test_config_loader.py` (environment through
`monkeypatch.setenv`, which stays allowed):
- `test_measure_environment_overrides_the_file`
- `test_load_measure_config_without_a_file_reads_the_environment`
- `test_measure_boolean_environment_rejects_garbage`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/infrastructure/test_config_loader.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Using the keys (each later `gap-measure-*` lane reads the one it needs).
- `docs/reference/configuration.md` (the docs wave), CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees.

Commit as `feat(config): a [measure] table declares where measurements go and how often samplers run`. Do not push.

## Lane card
- **Depends on:** `gap-measure-domain`.
- **Shares a file with:** `src/vibey/domain/config.py` is edited by R01, T05, R34 and T28; rebase
  on whichever has landed and keep their code.
- **Must keep passing unchanged:** every existing test in the two test files.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
