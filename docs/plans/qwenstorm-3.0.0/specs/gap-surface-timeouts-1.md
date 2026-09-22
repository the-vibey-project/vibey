## Title
feat(config): `[surfaces] adapter_timeout_seconds` declares the bound on every sovereign adapter call (default 10)

## Why
Doctrine 10 (`src/vibey_tools/gh/docs/doctrines.md:366-369`): every dependency is "never
assumed, always confirmed, always self-healed around". Yet no sovereign surface adapter passes a
timeout to `urlopen` (gap K3: `tracker/plane.py:61`, `:77`; `docs/bookstack.py:53`, `:73`;
`secrets/openbao.py:47`, `:70`; `config_store/infisical.py:54`, `:81`; `blob/garage.py:112`;
`messaging/matrix.py:44`; `siem/wazuh.py:51`; `sms/kannel.py:55`; also `files/nextcloud.py:47`,
`:61`, `bus/rabbitmq.py:50`, and `email/forward_email.py:45`, `:50` opens SMTP with none), so a
hung server hangs its thread forever. ADR-0047 (`specs/ADR-surface-lanes.md:562`) names
"giving the adapters socket timeouts" as a follow-up defect fix. The Redis adapter has a bound,
but it is a hard-coded `timeout: int = 5` (`cache/redis.py:54`).

Sub-doctrine 12.c (`doctrines.md:455`): the bound is a declared key with an environment
override and a stated default, never a constant. This lane declares the key and its default.
Lanes `gap-surface-timeouts-2` to `-5` make every adapter use the default, and `-6` wires the key.

## Required behaviour
1. `src/vibey/domain/config.py`, directly after `DEFAULT_LOCAL_CONTEXT_WINDOW = 32_768` (`:35`):
   ```python
   # The bound, in seconds, on each blocking network operation of a sovereign surface
   # adapter (doctrine 10). `[surfaces] adapter_timeout_seconds` or
   # VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS overrides it.
   DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS = 10
   SURFACE_ADAPTER_TIMEOUT_BOUNDS = (1, 600)
   ```
2. **If `grep -n "class SurfacesConfig" src/vibey/domain/config.py` prints nothing** (ADR-0047
   lane S01 has not landed), add after `SiemConfig` (`:308-315`), before `VibeyConfig`:
   ```python
   @dataclass(frozen=True, slots=True)
   class SurfacesConfig:
       """`[surfaces]`: settings every sovereign surface adapter shares."""

       adapter_timeout_seconds: int = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS

       @classmethod
       def from_table(cls, table: dict[str, Any], path: str) -> "SurfacesConfig":
           """Validate one already-parsed table; `path` names it in any error."""
           low, high = SURFACE_ADAPTER_TIMEOUT_BOUNDS
           timeout = table.get("adapter_timeout_seconds", DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS)
           if isinstance(timeout, bool) or not isinstance(timeout, int) or not low <= timeout <= high:
               raise ConfigError(
                   f"{path}.adapter_timeout_seconds", f"must be an integer from {low} to {high}"
               )
           return cls(adapter_timeout_seconds=timeout)
   ```
   Add `surfaces: SurfacesConfig = field(default_factory=SurfacesConfig)` as the last field of
   `VibeyConfig` (after `siem`, `:342`), and
   `surfaces=SurfacesConfig.from_table(_optional(data, "surfaces", "surfaces", dict, {}), "surfaces"),`
   as the last argument of the `VibeyConfig(...)` call in `parse_config` (after
   `siem=_parse_siem(data),`, `:719`). The pattern copied is `ClaudeloopLocalConfig.from_table`
   (`:88-107`), so no new module-level function is added.
   **If `SurfacesConfig` already exists** (S01 landed first): add the same field to it and the
   same validation to whatever builds it (its `from_table` or its parse function), keeping S01's
   fields and their order; do not add a second class or a second `VibeyConfig` field.
3. `src/vibey/domain/interfaces/config_interface.py`: add
   `@runtime_checkable class SurfacesConfigInterface(Protocol)` with the read-only property
   `adapter_timeout_seconds -> int`, in the style of `TelemetryConfigInterface` (`:31-36`).
   If S01 already declared an interface for `SurfacesConfig`, add the property to it instead.
4. `src/vibey/infrastructure/config_loader.py`: append to `_SURFACE_ENV_VARS` (`:17-59`), as its
   last entry, `("surfaces", "adapter_timeout_seconds", "VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS", int),`.
   `apply_env_overrides` already casts it and refuses a non-integer with
   "VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS must be an integer".
5. Nothing reads the key yet (`gap-surface-timeouts-6` wires it). A `vibey.toml` without
   `[surfaces]` parses exactly as before, plus `config.surfaces.adapter_timeout_seconds == 10`.

## Where to change
- `src/vibey/domain/config.py` (edit_file only; the file is 724 lines).
- `src/vibey/domain/interfaces/config_interface.py`.
- `src/vibey/infrastructure/config_loader.py` (one tuple line).
- New `tests/infrastructure/test_surface_timeout_config.py`.
- Run `uv run ruff format` on every file you touched before the checks (the formatter wraps
  the long `if` in behaviour 2).

## Acceptance criteria
- [ ] `load_config_from_string('[project]\nname = "x"\n').surfaces.adapter_timeout_seconds == 10`.
- [ ] `[surfaces] adapter_timeout_seconds = 7` parses to 7; `0`, `601`, `true`, `"7"` and `7.5`
      each raise `ConfigError` whose message starts `surfaces.adapter_timeout_seconds: must be an integer from 1 to 600`.
- [ ] `VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS=30` beats the file's value; `abc` raises
      `ValueError("VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS must be an integer")`; an empty value is ignored.
- [ ] `isinstance(config.surfaces, SurfacesConfigInterface)`.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `domain/` and `infrastructure/`.

## Tests to write first (TDD)
New `tests/infrastructure/test_surface_timeout_config.py` (provenance line first, copied from
`tests/infrastructure/test_config_loader.py:1`):
- `test_the_adapter_timeout_defaults_to_ten_seconds`
- `test_the_adapter_timeout_is_read_from_the_surfaces_table`
- `test_the_adapter_timeout_rejects_out_of_range_and_non_integer_values` (parametrized over
  `0`, `601`, `true`, `"7"`, `7.5`; asserts the message)
- `test_the_surfaces_table_must_be_a_table` (`surfaces = 3` raises `ConfigError` naming `surfaces`)
- `test_the_environment_overrides_the_adapter_timeout` (`apply_env_overrides(data, environ={...})`
  then `parse_config(data)`; pass `environ` as an argument, never patch `os.environ`)
- `test_a_non_integer_environment_timeout_is_refused`
- `test_the_surfaces_config_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_surface_timeout_config.py tests/infrastructure/test_config_loader.py tests/domain/test_config.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Passing the timeout in any adapter (`gap-surface-timeouts-2` to `-5`) or wiring it in
  `build_app` (`gap-surface-timeouts-6`).
- ADR-0047's other `[surfaces]` keys (lane S01) and any cross-check against its
  `operation_timeout_seconds`; S01 owns that check.
- Docs and `docs/reference/configuration.md` (the docs wave), CHANGELOG.md, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md, skill trees.

Commit as `feat(config): declare [surfaces] adapter_timeout_seconds`. Do not push.

## Lane card
- **Depends on:** none.
- **Shares a file with:** ADR-0047 lane S01 (`domain/config.py`, `config_loader.py`); behaviour 2
  says what to do when S01 landed first. `surfaces-env` refactors `load_config_from_path`
  (`config_loader.py:83-100`), not `_SURFACE_ENV_VARS`.
- **Must keep passing unchanged:** `tests/domain/test_config.py`, `tests/infrastructure/test_config_loader.py`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
