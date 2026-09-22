## Title
feat(config): the [sovereignloop] table replaces [qwenloop], which is read as its legacy spelling

ADR-0046 lane L08b (slug `loops-config-sovereignloop-table`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`, row "`[qwenloop]` table") says:
`[qwenloop]` becomes `[sovereignloop]`; the old table is "read when `[sovereignloop]` is
absent; both present is an error", through 3.x. Sub-doctrine 8.c names the loop
`sovereignloop`, "what `qwenloop` becomes" (`src/vibey_tools/gh/docs/doctrines.md:196-199`),
and 12.c forbids making the key less configurable (`doctrines.md:455`): the same six keys keep
working under the new name.

At integration `d3b4a388` the table is `QwenloopConfig` (`src/vibey/domain/config.py:184-191`),
the field `VibeyConfig.qwenloop` (`:330`), and `_parse_qwenloop` (`:505-530`), called from
`parse_config` (`:707`). Lane `loops-config-engine-names` (L08a) added
`VibeyConfig.legacy_spellings` and the `LegacySpelling` record
(`src/vibey/domain/engine_names.py`); this lane adds the table's record to it. No module in
`src/vibey` reads `VibeyConfig.qwenloop` (`git grep -n "\.qwenloop\b" -- src/vibey` shows only
`config.py`), so the rename touches config and its tests only.

## Required behaviour
1. `QwenloopConfig` is renamed `SovereignloopConfig`, with the same six fields and defaults
   (`backend="auto"`, `portable_profile="qwen2.5-coder-14b-q5-k-m"`,
   `nvidia_profile="qwen2.5-coder-14b-bf16"`, `idle_timeout_seconds=900`,
   `startup_timeout_seconds=180`, `context_window=32_768`). No alias name `QwenloopConfig`
   is kept (nothing imports it outside `config.py`).
2. `VibeyConfig.qwenloop` is renamed `VibeyConfig.sovereignloop:
   SovereignloopConfig = field(default_factory=SovereignloopConfig)` (same position).
3. `_parse_qwenloop` is renamed `_parse_sovereignloop(data: dict[str, Any]) ->
   tuple[SovereignloopConfig, tuple[LegacySpelling, ...]]`:
   - `[sovereignloop]` present and `[qwenloop]` absent: parse `[sovereignloop]`; records `()`.
   - `[qwenloop]` present and `[sovereignloop]` absent: parse `[qwenloop]`; records
     `(LegacySpelling(where="[qwenloop]", legacy="qwenloop", current="sovereignloop"),)`.
   - both present: `raise ConfigError("sovereignloop", "both [sovereignloop] and its legacy spelling [qwenloop] are set; keep [sovereignloop]")`.
   - neither: defaults; records `()`.
   - Every error path names the table actually read: with `table_name` = `"sovereignloop"`
     or `"qwenloop"`, the paths are `f"{table_name}.backend"`,
     `f"{table_name}.portable_profile"`, `f"{table_name}.nvidia_profile"`,
     `f"{table_name}.idle_timeout_seconds"`, `f"{table_name}.startup_timeout_seconds"`,
     `f"{table_name}.context_window"`, and `table_name` itself for the
     "startup_timeout_seconds and context_window must be positive" check. The messages are
     unchanged ("must be one of ('auto', 'llama.cpp', 'vllm')", "must be non-negative",
     "startup_timeout_seconds and context_window must be positive"). A non-table value is
     refused by `_optional` with the path `table_name`, as today.
4. `parse_config` calls `sovereignloop, sovereign_spellings = _parse_sovereignloop(data)`
   right after L08a's phase loop, extends `spellings` with `sovereign_spellings` (so the
   record order is engines, weights, phases, then `[qwenloop]`), and passes
   `sovereignloop=sovereignloop` to `VibeyConfig` in place of `qwenloop=_parse_qwenloop(data)`.
5. `SovereignloopConfigInterface` is declared: append to
   `src/vibey/domain/interfaces/value_objects_interface.py` a `@runtime_checkable` Protocol
   with read-only properties `backend: str`, `portable_profile: str`, `nvidia_profile: str`,
   `idle_timeout_seconds: int`, `startup_timeout_seconds: int`, `context_window: int`
   (copy the `ClaudeloopLocalConfigInterface` style above it).

## Where to change
- `src/vibey/domain/config.py` (`edit_file` only; over 100 lines). Anchors by text:
  - the class `class QwenloopConfig:` (`:184-191`);
  - the field `    qwenloop: QwenloopConfig = field(default_factory=QwenloopConfig)` (`:330`);
  - `def _parse_qwenloop(data: dict[str, Any]) -> QwenloopConfig:` and its body (`:505-530`);
  - in `parse_config`, the keyword `        qwenloop=_parse_qwenloop(data),` (`:707`) and
    L08a's `spellings` list.
- Reference body for the renamed parser (replace the whole old function):
  ```python
  def _parse_sovereignloop(
      data: dict[str, Any],
  ) -> tuple[SovereignloopConfig, tuple[LegacySpelling, ...]]:
      """`[sovereignloop]`, else its legacy spelling `[qwenloop]` (ADR-0046 Migration table)."""
      if "sovereignloop" in data and "qwenloop" in data:
          raise ConfigError(
              "sovereignloop",
              "both [sovereignloop] and its legacy spelling [qwenloop] are set; "
              "keep [sovereignloop]",
          )
      name = "qwenloop" if "qwenloop" in data else "sovereignloop"
      spellings: tuple[LegacySpelling, ...] = ()
      if name == "qwenloop":
          spellings = (LegacySpelling(where="[qwenloop]", legacy="qwenloop", current="sovereignloop"),)
      table = _optional(data, name, name, dict, {})
      backend = _optional(table, "backend", f"{name}.backend", str, "auto")
      if backend not in {"auto", "llama.cpp", "vllm"}:
          raise ConfigError(f"{name}.backend", "must be one of ('auto', 'llama.cpp', 'vllm')")
      result = SovereignloopConfig(
          backend=backend,
          portable_profile=_optional(
              table, "portable_profile", f"{name}.portable_profile", str, "qwen2.5-coder-14b-q5-k-m"
          ),
          nvidia_profile=_optional(
              table, "nvidia_profile", f"{name}.nvidia_profile", str, "qwen2.5-coder-14b-bf16"
          ),
          idle_timeout_seconds=_optional(
              table, "idle_timeout_seconds", f"{name}.idle_timeout_seconds", int, 900
          ),
          startup_timeout_seconds=_optional(
              table, "startup_timeout_seconds", f"{name}.startup_timeout_seconds", int, 180
          ),
          context_window=_optional(table, "context_window", f"{name}.context_window", int, 32_768),
      )
      if result.idle_timeout_seconds < 0:
          raise ConfigError(f"{name}.idle_timeout_seconds", "must be non-negative")
      if result.startup_timeout_seconds <= 0 or result.context_window <= 0:
          raise ConfigError(name, "startup_timeout_seconds and context_window must be positive")
      return result, spellings
  ```
  Run `uv run ruff format src/vibey/domain/config.py` if `ruff format --check` wants to rewrap it.
- `src/vibey/domain/interfaces/value_objects_interface.py` (over 100 lines): append the
  Protocol with `edit_file` after `FeaturesConfigInterface`.
- `tests/domain/test_config.py`: the only expectations that change are
  `config.qwenloop.backend` (two occurrences, `:126` and `:173` at `d3b4a388`), which become
  `config.sovereignloop.backend`. Use a checked replacement
  (`assert s.count("config.qwenloop.backend") == 2`). The TOML inputs that write `[qwenloop]`
  stay: they now exercise the legacy table.
- **Stop rule.** Any other failing test that is not that replacement: stop and report it.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).sovereignloop == SovereignloopConfig()`, and `legacy_spellings == ()`.
- [ ] `[sovereignloop] backend = "vllm"` parses, with no record.
- [ ] `[qwenloop] backend = "vllm"` parses to `sovereignloop.backend == "vllm"` and records `LegacySpelling("[qwenloop]", "qwenloop", "sovereignloop")`.
- [ ] Both tables raise `ConfigError` whose `path == "sovereignloop"` and whose message is exactly the one in behaviour 3.
- [ ] `[qwenloop] backend = "ollama"` raises with `path == "qwenloop.backend"`; `[sovereignloop] backend = "ollama"` with `path == "sovereignloop.backend"`.
- [ ] `git grep -n "QwenloopConfig\|_parse_qwenloop\|config\.qwenloop\b" -- src tests` prints nothing.
- [ ] 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_sovereignloop_table.py` (pure):
- `test_defaults_without_either_table`.
- `test_the_sovereignloop_table_is_read`: every one of the six keys set under `[sovereignloop]` reaches `config.sovereignloop`.
- `test_the_legacy_qwenloop_table_is_read_and_recorded`.
- `test_both_tables_is_an_error_naming_the_new_one`.
- `test_errors_name_the_table_that_was_read` (parametrized over `("sovereignloop", "qwenloop")` × the three invalid inputs `backend = "ollama"`, `idle_timeout_seconds = -1`, `context_window = 0`, asserting `exc.path`).
- `test_the_table_record_follows_the_engine_records`: `[engines] enabled = ["qwenloop"]` plus `[qwenloop] backend = "vllm"` gives records in the order `engines.enabled`, `[qwenloop]`.
- `test_the_config_value_satisfies_its_interface`: `isinstance(SovereignloopConfig(), SovereignloopConfigInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_sovereignloop_table.py tests/domain/test_config.py tests/domain/test_engine_names.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_config_loader.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    git grep -n "QwenloopConfig\|_parse_qwenloop\|config\.qwenloop\b" -- src tests

The last command must print nothing. The full `--cov` run needs PostgreSQL until lane
`fakes-harness-decouple` lands.

## Out of scope
- The `[features]` switch and `VIBEY_FEATURE_*` (lane `loops-vibey-local-engine-names`).
- The runner's own config file and environment (`loops-tenant-legacy-env`).
- The model profile names inside the table (they name models, not the tool).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-config-engine-names`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
