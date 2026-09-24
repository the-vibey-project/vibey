## Title
feat(engines): vibey switches and points the sovereign engine by its sovereignloop names, and still reads every qwenloop spelling

ADR-0046 lane L18e (slug `loops-vibey-local-engine-names`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`) renames, with legacy reads
through 3.x:
- `[features] qwenloop`, `VIBEY_FEATURE_QWENLOOP` → `[features] sovereignloop`,
  `VIBEY_FEATURE_SOVEREIGNLOOP`, the old ones "read when the new one is unset";
- `QWENLOOP_BASE_URL`, `QWENLOOP_MODEL` → `SOVEREIGNLOOP_*` (the runner reads both since lane
  `loops-tenant-legacy-env`, L18c).

At integration `d3b4a388`:
- `src/vibey/domain/config.py:24` `LOCAL_ENGINE_FEATURES` (lane L08a made its key
  `"sovereignloop"` and kept the feature key `"qwenloop"` for this lane), `:173-181`
  `FeaturesConfig.qwenloop`, `:495-502` `_parse_features`;
- `src/vibey/domain/interfaces/value_objects_interface.py:60-67` `FeaturesConfigInterface.qwenloop`;
- `src/vibey/infrastructure/engines/local_engines.py:48-65` builds each switch's
  `VIBEY_FEATURE_<KEY>` from that feature key, `:99-107` `LocalEngineSettings.enabled` reads it
  (lane `engines-pool`, #321 behaviour 4, made sovereignloop always on there, with one warning
  per instance naming its source), `:43-45` and `:180-188` write `QWENLOOP_BASE_URL` /
  `QWENLOOP_MODEL` into the runner's environment;
- `src/vibey/infrastructure/config_loader.py:88-98` overlays each switch's variable onto
  `[features]`;
- `src/vibey/infrastructure/provision/agent_surface.py:60` excludes `.qwenloop/` from engine
  commits, but not the `.sovereignloop/` lane L18d now writes.

The feature key, the environment switch and the loader are one mechanism
(`VIBEY_FEATURE_<KEY>` is derived from the key), so they are renamed together here, with the
legacy spelling read in every place that reads the current one (12.c: never less configurable;
`doctrines.md:455`). The records land in `VibeyConfig.legacy_spellings` for lane L07's doctor.

## Required behaviour
1. **Domain** (`config.py`):
   - `LOCAL_ENGINE_FEATURES = {"sovereignloop": "sovereignloop", "claudeloop-local": "claudeloop_local"}`
     (drop L08a's one-line comment above it; keep any entry a landed lane removed, e.g. lane
     `loops-claudeloop-local-paid` drops `claudeloop-local`);
   - new `LEGACY_FEATURE_KEYS = {"sovereignloop": "qwenloop"}` (feature key → its legacy
     spelling), with the comment
     `# A feature key's legacy spelling, read while the current key is absent (ADR-0046 Migration table, through 3.x).`;
   - `FeaturesConfig.sovereignloop: bool = False` replaces `qwenloop` (same position);
   - `_parse_features(data) -> tuple[FeaturesConfig, tuple[LegacySpelling, ...]]`: reads
     `[features] sovereignloop`; when `qwenloop` is in the table it records
     `LegacySpelling("features.qwenloop", "qwenloop", "sovereignloop")`, and reads `qwenloop`'s
     value when `sovereignloop` is absent (when both are present the current key wins and the
     record still says the legacy key is written); errors name the key read
     (`features.qwenloop` or `features.sovereignloop`); if lane `loops-claudeloop-local-paid`
     landed its `features.claudeloop_local` record here, keep it, after this one;
   - `parse_config`: `features, feature_spellings = _parse_features(data)` followed by
     `spellings.extend(feature_spellings)` (so feature records come first).
   - `value_objects_interface.py`: `FeaturesConfigInterface`'s `qwenloop` property becomes `sovereignloop`.
2. **The switch** (`local_engines.py`, `LocalEngineSwitch`):
   - new field `legacy_feature_key: str | None = None` (last);
   - `env_var` unchanged (`VIBEY_FEATURE_{feature_key.upper()}`); new property
     `legacy_env_var -> str | None` (`VIBEY_FEATURE_{legacy_feature_key.upper()}`, or `None`);
   - `from_environment(self, environ: Mapping[str, str]) -> tuple[str, str] | None`: the
     `(variable, raw value)` of the current variable whenever it is set at all (empty counts,
     as today), else of the legacy variable when set, else `None`;
   - `from_features(self, features: Mapping[str, object]) -> tuple[str, object] | None`:
     `("[features] <key>", value)` for the current key when present, else the legacy key when
     present, else `None`;
   - `LOCAL_ENGINE_SWITCHES` is built with `LEGACY_FEATURE_KEYS.get(key)` as each switch's legacy key;
   - declared by a new `LocalEngineSwitchInterface` in
     `infrastructure/engines/interfaces/local_engines_interface.py` (the two properties plus
     `feature_key`, `legacy_feature_key`, `engine_id`, and both methods).
3. **`LocalEngineSettings.enabled`** reads a switch only through `from_environment` then
   `from_features` (a private method `_switch_setting(self, switch) -> tuple[str | None, bool]`
   returning the deciding source and whether it says on). Everything `engines-pool` built
   stays: sovereignloop is always on, and when the deciding source explicitly says off, the
   once-per-instance warning is
   `sovereignloop cannot be switched off (sub-doctrine 8.b); ignoring <source>`, where
   `<source>` is exactly what decided: `VIBEY_FEATURE_SOVEREIGNLOOP`, `VIBEY_FEATURE_QWENLOOP`,
   `[features] sovereignloop` or `[features] qwenloop`. Any other engine is on only when its
   deciding source says on (for an environment value, `strip().lower()` in `TRUTHY`; for a
   feature value, `is True`), as today; keep any branch another landed lane added (for example
   lane `loops-claudeloop-local-paid`'s declaration rule).
4. **The loader** (`config_loader.load_config_from_path`) takes each switch's variable from
   `switch.from_environment(os.environ)`; its error names the variable actually read
   (`VIBEY_FEATURE_QWENLOOP must be a boolean value` for the legacy one); the value is written to
   `features[switch.feature_key]` (the current key), so an environment switch still beats the file.
5. **The endpoint overlay** (`LocalEndpointEnvironment.overlay_for`):
   - new constants `SOVEREIGNLOOP_BASE_URL_ENV = "SOVEREIGNLOOP_BASE_URL"` and
     `SOVEREIGNLOOP_MODEL_ENV = "SOVEREIGNLOOP_MODEL"`; `QWENLOOP_BASE_URL_ENV` and
     `QWENLOOP_MODEL_ENV` keep their values and stay in `__all__` (the legacy names);
   - for `EngineId.SOVEREIGNLOOP` with `VIBEY_OLLAMA_URL` set, it derives
     `SOVEREIGNLOOP_BASE_URL = <url>/v1` and `SOVEREIGNLOOP_MODEL = <model>`, and derives
     **nothing** for a key when either its new or its legacy name is already set (an operator who
     set `QWENLOOP_BASE_URL` keeps it; the runner reads it as the legacy spelling).
6. **Worktree exclusions**: `_ARTIFACT_PATTERNS` (`agent_surface.py:48-61`) gains
   `".sovereignloop/",` right after `".qwenloop/",` (both stay).

## Where to change
All files are over 100 lines except `value_objects_interface.py`'s neighbours; use
`edit_file` (or the checked-replacement form of `EDITING-RULES.md`) for every existing file.
- `src/vibey/domain/config.py`: reference body for `_parse_features`
  ```python
  def _parse_features(data: dict[str, Any]) -> tuple[FeaturesConfig, tuple[LegacySpelling, ...]]:
      table = _optional(data, "features", "features", dict, {})
      spellings: tuple[LegacySpelling, ...] = ()
      sovereign_key = "sovereignloop"
      if "qwenloop" in table:
          spellings = (LegacySpelling("features.qwenloop", "qwenloop", "sovereignloop"),)
          if "sovereignloop" not in table:
              sovereign_key = "qwenloop"
      return (
          FeaturesConfig(
              sovereignloop=_optional(table, sovereign_key, f"features.{sovereign_key}", bool, False),
              claudeloop_local=_optional(
                  table, "claudeloop_local", "features.claudeloop_local", bool, False
              ),
          ),
          spellings,
      )
  ```
- `src/vibey/domain/interfaces/value_objects_interface.py`: the one property rename.
- `src/vibey/infrastructure/engines/local_engines.py`:
  - import `LEGACY_FEATURE_KEYS` from `vibey.domain.config` (sorted into the existing import);
  - replace the constants block `#: What qwenloop's openai-compat backend reads ...` (`:43-45`) with
    ```python
    #: What sovereignloop's openai-compat backend reads (its own settings; ADR-0046 renamed them).
    SOVEREIGNLOOP_BASE_URL_ENV = "SOVEREIGNLOOP_BASE_URL"
    SOVEREIGNLOOP_MODEL_ENV = "SOVEREIGNLOOP_MODEL"
    #: Their legacy spellings, which the runner still reads through 3.x. The overlay never
    #: derives a value either spelling already holds.
    QWENLOOP_BASE_URL_ENV = "QWENLOOP_BASE_URL"
    QWENLOOP_MODEL_ENV = "QWENLOOP_MODEL"
    ```
  - `LocalEngineSwitch` (`:48-57`) becomes
    ```python
    @dataclass(frozen=True, slots=True)
    class LocalEngineSwitch:
        """One local engine's feature switch: a `[features]` key and its environment name, and
        the legacy spelling of both, still read while the current one is unset (ADR-0046).

        Declared by `interfaces/local_engines_interface.py`."""

        engine_id: EngineId
        feature_key: str
        legacy_feature_key: str | None = None

        @property
        def env_var(self) -> str:
            return f"VIBEY_FEATURE_{self.feature_key.upper()}"

        @property
        def legacy_env_var(self) -> str | None:
            if self.legacy_feature_key is None:
                return None
            return f"VIBEY_FEATURE_{self.legacy_feature_key.upper()}"

        def from_environment(self, environ: Mapping[str, str]) -> tuple[str, str] | None:
            """The variable that decides this switch and its raw value: the current name whenever
            it is set at all, else the legacy name when set, else None."""
            for variable in (self.env_var, self.legacy_env_var):
                if variable is not None and variable in environ:
                    return variable, environ[variable]
            return None

        def from_features(self, features: Mapping[str, object]) -> tuple[str, object] | None:
            """`[features] <key>` and its value: the current key when present, else the legacy
            key when present, else None."""
            for key in (self.feature_key, self.legacy_feature_key):
                if key is not None and key in features:
                    return f"[features] {key}", features[key]
            return None
    ```
  - `LOCAL_ENGINE_SWITCHES` (`:63-65`):
    `LocalEngineSwitch(EngineId(engine), key, LEGACY_FEATURE_KEYS.get(key)) for engine, key in LOCAL_ENGINE_FEATURES.items()`;
  - `LocalEngineSettings`: add
    ```python
        def _switch_setting(self, switch: LocalEngineSwitch) -> tuple[str | None, bool]:
            """What decides `switch`, and whether it says on; (None, False) when nothing does."""
            decided = switch.from_environment(self._environ)
            if decided is not None:
                return decided[0], decided[1].strip().lower() in TRUTHY
            features = self._config.get("features")
            if not isinstance(features, Mapping):
                return None, False
            configured = switch.from_features(features)
            if configured is None:
                return None, False
            return configured[0], configured[1] is True
    ```
    and make `enabled` use it. Target shape (keep engines-pool's warning mechanism and its
    once-per-instance guard exactly; only its source and its first word change):
    ```python
        def enabled(self, engine_id: EngineId) -> bool:
            switch = self._switches.get(engine_id)
            if switch is None:
                return False
            source, on = self._switch_setting(switch)
            if engine_id is EngineId.SOVEREIGNLOOP:
                if source is not None and not on:
                    ...  # engines-pool's once-per-instance warning, with this message:
                    # f"sovereignloop cannot be switched off (sub-doctrine 8.b); ignoring {source}"
                return True
            return on
    ```
  - `LocalEndpointEnvironment`: update its docstring's two bullet names to
    `SOVEREIGNLOOP_BASE_URL` / `SOVEREIGNLOOP_MODEL` (and say the legacy spellings count as
    set); `overlay_for` becomes
    ```python
        def overlay_for(self, engine_id: EngineId) -> dict[str, str]:
            if engine_id is not EngineId.SOVEREIGNLOOP or not self._environ.get(OLLAMA_URL_ENV):
                return {}
            client = OllamaChatClient.from_environment(self._environ, model=self._model)
            derived = {
                SOVEREIGNLOOP_BASE_URL_ENV: (QWENLOOP_BASE_URL_ENV, f"{client.base_url}/v1"),
                SOVEREIGNLOOP_MODEL_ENV: (QWENLOOP_MODEL_ENV, client.model),
            }
            return {
                name: value
                for name, (legacy, value) in derived.items()
                if not self._environ.get(name) and not self._environ.get(legacy)
            }
    ```
  - `__all__`: add `"SOVEREIGNLOOP_BASE_URL_ENV"` and `"SOVEREIGNLOOP_MODEL_ENV"` after `"QWENLOOP_MODEL_ENV"`.
- `src/vibey/infrastructure/engines/interfaces/local_engines_interface.py`: add
  `LocalEngineSwitchInterface` (`@runtime_checkable`; properties `engine_id: EngineId`,
  `feature_key: str`, `legacy_feature_key: str | None`, `env_var: str`,
  `legacy_env_var: str | None`; methods `from_environment` and `from_features` with the
  signatures above; import `Mapping` from `collections.abc`), and export it from
  `infrastructure/engines/interfaces/__init__.py` beside `LocalEngineSettingsInterface`.
- `src/vibey/infrastructure/config_loader.py`: the switch loop (`:88-98`) becomes
  ```python
      for switch in LOCAL_ENGINE_SWITCHES:
          decided = switch.from_environment(os.environ)
          if decided is None:
              continue
          variable, override = decided
          normalized = override.strip().lower()
          if normalized not in {"0", "1", "false", "true", "no", "yes", "off", "on"}:
              raise ValueError(f"{variable} must be a boolean value")
          features = data.setdefault("features", {})
          if not isinstance(features, dict):
              raise ValueError("features must be a table")
          features[switch.feature_key] = normalized in {"1", "true", "yes", "on"}
  ```
- `src/vibey/infrastructure/provision/agent_surface.py`: `    ".qwenloop/",\n` becomes
  `    ".qwenloop/",\n    ".sovereignloop/",\n`.
- Existing expectations that change (pure text; one checked script, then run the tests).
  This body carries both quote styles, so it does not fit one shell argument: write it with
  `write_file` to `STORM/scratch/rename_expectations.py` — outside the repository, so it can never
  reach `git diff --stat` — run `python3 STORM/scratch/rename_expectations.py` as one `shell`
  command, then delete it.
  ```python
  from pathlib import Path
  edits = {
      "tests/domain/test_config.py": [("config.features.qwenloop", "config.features.sovereignloop", (1,))],
      "tests/infrastructure/test_config_loader.py": [(".features.qwenloop", ".features.sovereignloop", (2,))],
      "tests/infrastructure/engines/test_local_engines.py": [
          ('(EngineId.QWENLOOP, "qwenloop", QWEN_SWITCH)', '(EngineId.QWENLOOP, "sovereignloop", "VIBEY_FEATURE_SOVEREIGNLOOP")', (0, 1)),
          ('"QWENLOOP_BASE_URL": "http://10.0.0.5:11434/v1"', '"SOVEREIGNLOOP_BASE_URL": "http://10.0.0.5:11434/v1"', (1,)),
          ('"QWENLOOP_MODEL": "gpt-oss:20b"', '"SOVEREIGNLOOP_MODEL": "gpt-oss:20b"', (2,)),
          ('["QWENLOOP_MODEL"]', '["SOVEREIGNLOOP_MODEL"]', (2,)),
          ("qwenloop cannot be switched off", "sovereignloop cannot be switched off", (0, 1, 2, 3, 4)),
      ],
  }
  for name, pairs in edits.items():
      p = Path(name)
      s = p.read_text(encoding="utf-8")
      for old, new, allowed in pairs:
          n = s.count(old)
          assert n in allowed, (name, old, n)
          s = s.replace(old, new)
          print(name, n, old)
      p.write_text(s, encoding="utf-8")
  ```
  Inputs that *set* `VIBEY_FEATURE_QWENLOOP`, `[features] qwenloop` or `QWENLOOP_BASE_URL` stay
  unedited everywhere: they now prove the legacy reads (for example
  `test_what_the_operator_set_for_qwenloop_directly_is_kept`, whose expected dict becomes
  `{"SOVEREIGNLOOP_MODEL": "gpt-oss:20b"}` through the replacement above).
- **Stop rule.** Any other failing test that is not the replacement of a current-name
  expectation by its sovereignloop spelling: stop and report it (for example an exact-output
  doctor or worker message).

## Acceptance criteria
- [ ] `LOCAL_ENGINE_SWITCHES`' sovereign switch is `(SOVEREIGNLOOP, "sovereignloop", "qwenloop")` with `env_var == "VIBEY_FEATURE_SOVEREIGNLOOP"` and `legacy_env_var == "VIBEY_FEATURE_QWENLOOP"`.
- [ ] `[features] qwenloop = true` parses to `features.sovereignloop is True` and records `LegacySpelling("features.qwenloop", "qwenloop", "sovereignloop")`.
- [ ] `VIBEY_FEATURE_QWENLOOP=maybe` with no new variable raises `ValueError` naming `VIBEY_FEATURE_QWENLOOP`; `VIBEY_FEATURE_SOVEREIGNLOOP=1` wins over `VIBEY_FEATURE_QWENLOOP=0`.
- [ ] The warning names each of the four sources exactly, and sovereignloop stays enabled.
- [ ] `overlay_for(SOVEREIGNLOOP)` writes `SOVEREIGNLOOP_BASE_URL`/`_MODEL` and skips a key whose new or legacy name is set.
- [ ] `".sovereignloop/"` is in `_ARTIFACT_PATTERNS`.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_local_engine_names.py` (environment passed as a plain dict,
or `monkeypatch.setenv`/`delenv` for the loader, which reads `os.environ`; never `setattr`):
- `test_the_sovereign_switch_has_its_legacy_spelling`.
- `test_a_switch_without_a_legacy_spelling_has_no_legacy_variable`.
- `test_the_current_variable_decides_whenever_it_is_set` (both set, the current one empty: the current one still decides).
- `test_the_legacy_variable_decides_while_the_current_is_unset`.
- `test_nothing_set_decides_nothing` (`from_environment({}) is None`, `from_features({}) is None`).
- `test_from_features_prefers_the_current_key_then_the_legacy_key`.
- `test_sovereignloop_stays_on_and_the_warning_names_what_decided` (parametrized over the four sources; assert the message the way `engines-pool`'s own tests in `test_local_engines.py` assert its warning).
- `test_a_local_engine_other_than_sovereignloop_follows_its_switch` (`claudeloop-local`, if lane `loops-claudeloop-local-paid` has not removed its switch; else a `LocalEngineSwitch` built in the test and read through `_switch_setting`).
- `test_the_overlay_writes_the_sovereignloop_names`.
- `test_the_overlay_derives_nothing_either_spelling_already_holds` (parametrized: `QWENLOOP_BASE_URL`, `SOVEREIGNLOOP_BASE_URL`, `QWENLOOP_MODEL`, `SOVEREIGNLOOP_MODEL`).
- `test_the_legacy_constants_stay_exported`.
- `test_the_loader_reads_the_legacy_switch_variable` and `test_the_loader_error_names_the_variable_read`.
- `test_the_features_table_reads_its_legacy_key_and_records_it` and `test_the_current_features_key_wins_and_the_legacy_one_is_still_recorded`.
- `test_both_state_dirs_stay_out_of_engine_commits` (`_ARTIFACT_PATTERNS`).
- `test_the_switch_satisfies_its_interface`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines/test_local_engine_names.py tests/infrastructure/engines tests/infrastructure/test_config_loader.py tests/domain/test_config.py tests/domain/test_engine_names.py tests/domain/test_sovereignloop_table.py
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/test_cluster_preflight.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

The full `--cov` run needs PostgreSQL until lane `fakes-harness-decouple` lands.

## Out of scope
- The chart's `VIBEY_FEATURE_*` and `QWENLOOP_*` (lane `loops-chart-sovereignloop-names`, L18g).
- `vibey doctor`'s legacy-spelling report (lane L07); the `--provider` name (lane L18f).
- `claudeloop-local`'s switch semantics (lane `loops-claudeloop-local-paid`).
- The `bootstrap.qwenloop_enabled` and `QwenloopDesignProvider` Python names, and
  `EngineId.QWENLOOP` references (lane `loops-drop-qwenloop-alias`, L09).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-tenant-legacy-paths`, `loops-config-engine-names`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
