## Title
feat(config): vibey.toml names the sovereign engine sovereignloop and reads qwenloop as its legacy spelling

ADR-0046 lane L08a (slug `loops-config-engine-names`).

## Why
Sub-doctrine 8.b makes **`sovereignloop`** the always-on engine and 8.c says it is "what
`qwenloop` becomes" (`src/vibey_tools/gh/docs/doctrines.md:128-131`, `:196-199`). Draft
ADR-0046 §7 and its *Migration* table (`specs/ADR-two-loops.md`, the rows for
`[engines] enabled/weights`, `[phases.*].engines` and `--engines qwenloop`) rename the id and
keep the old spelling working through 3.x, "normalized with a deprecation warning". Lane
`loops-engine-id-sovereignloop` (L06) adds `EngineId.SOVEREIGNLOOP` and
`ENGINE_ID_ALIASES = {"qwenloop": EngineId.SOVEREIGNLOOP}` in `src/vibey/domain/engine.py`.

The config schema still speaks the old name. At integration `d3b4a388`:
- `src/vibey/domain/config.py:21` `DEFAULT_ENGINES = ("qwenloop", "opencode")`, and lane
  `engines-pool` (#321, `issue-audit/updates/321.md` behaviour 3) turns it into `("qwenloop",)`;
- `KNOWN_ENGINES` (`config.py:25-33`) lists `"qwenloop"`;
- `_parse_engines` (`config.py:403-422`) force-appends it (`:406-409`) and validates
  `enabled` and `weights` keys against `KNOWN_ENGINES` as written;
- `_parse_phase` (`config.py:425-432`) keeps `[phases.*].engines` verbatim;
- `parse_config` exempts it by its literal name (`config.py:679-681`).

Nothing records that an operator used the old spelling, so nothing can ever tell them to
rename it. Lane L07 (`loops-doctor-legacy-spellings`) prints every such record from
`vibey doctor`; this lane produces them for engine names. The domain stays pure: records are
data on `VibeyConfig`, never log lines (`tests/domain/test_domain_purity.py`).

## Required behaviour
1. **`src/vibey/domain/engine_names.py`** (new) holds two classes.
   - `@dataclass(frozen=True, slots=True) class LegacySpelling` with fields
     `where: str`, `legacy: str`, `current: str`: one legacy name in use, where it was read
     (a dotted key such as `engines.enabled`), what it said, and what it now means.
   - `class EngineNameResolver`, built with `aliases: Mapping[str, str] | None = None`. The
     default is `{legacy: member.value for legacy, member in ENGINE_ID_ALIASES.items()}`
     (L06's table, so `{"qwenloop": "sovereignloop"}`); never a second hand-written table.
     - `resolve(self, name: str, *, where: str) -> tuple[str, LegacySpelling | None]`: an
       alias key returns `(canonical, LegacySpelling(where=where, legacy=name, current=canonical))`;
       any other name returns `(name, None)` unchanged. A value that is not a `str` (a
       malformed TOML entry such as `1`) returns `(name, None)` so the caller's own
       validation names it; it never raises.
     - `resolve_all(self, names: Iterable[str], *, where: str) -> tuple[tuple[str, ...], tuple[LegacySpelling, ...]]`:
       resolves each name in order, drops a name already seen **after** resolution
       (`["qwenloop", "sovereignloop"]` gives `("sovereignloop",)`), and records each distinct
       `LegacySpelling` once, in first-seen order.
2. **`src/vibey/domain/interfaces/engine_names_interface.py`** (new): `@runtime_checkable`
   Protocols `LegacySpellingInterface` (read-only properties `where`, `legacy`, `current`)
   and `EngineNameResolverInterface` (both methods, same signatures, returning
   `LegacySpellingInterface`). Copy the layout of `domain/interfaces/stored_value_interface.py`.
3. **`config.py` constants** (anchor by text; `engines-pool` edited them first):
   - `DEFAULT_ENGINES = ("sovereignloop",)`, keeping the comment `engines-pool` wrote above it
     ("The sovereign default (always on, never needs declaration)");
   - `KNOWN_ENGINES`: the entry `"qwenloop",` becomes `"sovereignloop",` (same position);
   - `LOCAL_ENGINE_FEATURES`: the **engine-id key** `"qwenloop"` becomes `"sovereignloop"`,
     and its **feature key value stays `"qwenloop"`**:
     `{"sovereignloop": "qwenloop", "claudeloop-local": "claudeloop_local"}` (keep any other
     entry exactly as a landed lane left it). Add one comment line above it:
     `# The feature key stays "qwenloop" until lane loops-vibey-local-engine-names renames the switch with its legacy reads.`
     (Why: the feature key becomes `VIBEY_FEATURE_<KEY>` in
     `infrastructure/engines/local_engines.py:48-65` and `config_loader.py:88-98`; renaming it
     here would silently stop reading `VIBEY_FEATURE_QWENLOOP` in the infrastructure layer.)
4. **`_parse_engines(data)`** returns `tuple[EnginesConfig, tuple[LegacySpelling, ...]]`:
   - `enabled` is `EngineNameResolver().resolve_all(<the raw list>, where="engines.enabled")`;
   - the force-append block `engines-pool` left (it appends `"qwenloop"` when absent) appends
     `"sovereignloop"` instead;
   - `weights` keys are resolved one by one with `where="engines.weights"`; a weight whose key
     resolves to a name already present keeps the **last** value read;
   - the existing `KNOWN_ENGINES` validation runs on the resolved names, with its existing
     messages (`unknown engine 'bogus'`);
   - if lane `rmq-r01-queue-config` has landed, keep its `invocation` read unchanged;
   - the returned records are `enabled`'s, then `weights`', in that order.
5. **`_parse_phase(table, path, default_effort)`** stores resolved names:
   `engines = EngineNameResolver().resolve_all(engines_raw, where=f"{path}.engines")[0]` when
   `engines_raw is not None`, else `None`. Its signature and return type do not change.
6. **`parse_config(data)`**:
   - builds `spellings: list[LegacySpelling] = []`;
   - `engines, engine_spellings = _parse_engines(data)`; `spellings.extend(engine_spellings)`;
   - replaces the `phase_engines = (...)` block (`config.py:659-678`, three `_optional(...).get("engines") or []`
     arms) with a loop over `("design", "build", "review")` that reads the same raw lists,
     resolves each with `where=f"phases.{phase}.engines"`, extends `phase_engines` with the
     resolved names and `spellings` with the records (design, build, review order);
   - the exemption `if engine == "qwenloop":` becomes `if engine == "sovereignloop":`;
   - passes `legacy_spellings=tuple(spellings)` to `VibeyConfig`.
7. **`VibeyConfig`** gains a last field `legacy_spellings: tuple[LegacySpelling, ...] = ()`.
8. Behaviour for canonical input is unchanged: `parse_config({"project": {"name": "x"}})`
   gives `engines.enabled == ("sovereignloop",)` and `legacy_spellings == ()`.
9. `domain/` stays pure: `engine_names.py` imports only the standard library and
   `vibey.domain.engine`.

## Where to change
- New `src/vibey/domain/engine_names.py` and `src/vibey/domain/interfaces/engine_names_interface.py`.
  Line 1 of each is the provenance line copied byte for byte from line 1 of
  `src/vibey/domain/config.py`. Do not edit `domain/interfaces/__init__.py`; tests import
  from the module path.
- `src/vibey/domain/config.py` (724 lines at `d3b4a388`): `edit_file` only. Anchors, by text:
  - imports (`:9-13`): add `from vibey.domain.engine_names import EngineNameResolver, LegacySpelling`
    after `from vibey.domain.errors import ...` (or wherever isort puts it; run
    `uv run ruff check --fix --select I src/vibey/domain/config.py` if I001 fires);
  - `DEFAULT_ENGINES`, `LOCAL_ENGINE_FEATURES`, `KNOWN_ENGINES` (`:20-33`);
  - `_parse_engines` (`:403-422`); `_parse_phase` (`:425-432`);
  - `parse_config` (`:652-720`): the `phase_engines` block, the `"qwenloop"` exemption, the
    `_parse_engines` call, and the `VibeyConfig(...)` call;
  - `VibeyConfig` (`:318-342`): the new last field.
- Reference code for the three changed bodies (match the surrounding style; keep any line a
  landed lane added, e.g. R01's `invocation=`):
  ```python
  def _parse_engines(data: dict[str, Any]) -> tuple[EnginesConfig, tuple[LegacySpelling, ...]]:
      table = _optional(data, "engines", "engines", dict, {})
      resolver = EngineNameResolver()
      raw_enabled = _optional(table, "enabled", "engines.enabled", list, list(DEFAULT_ENGINES))
      enabled, spellings = resolver.resolve_all(raw_enabled, where="engines.enabled")
      # The sovereign default is always on (cannot be turned off)
      if "sovereignloop" not in enabled:
          enabled = (*enabled, "sovereignloop")
      for engine in enabled:
          if engine not in KNOWN_ENGINES:
              raise ConfigError("engines.enabled", f"unknown engine {engine!r}")
      raw_weights = _optional(table, "weights", "engines.weights", dict, {})
      weights: dict[str, int] = {}
      weight_spellings: list[LegacySpelling] = []
      for raw_engine, weight in raw_weights.items():
          engine, spelling = resolver.resolve(raw_engine, where="engines.weights")
          if engine not in KNOWN_ENGINES:
              raise ConfigError("engines.weights", f"unknown engine {engine!r}")
          if spelling is not None:
              weight_spellings.append(spelling)
          weights[engine] = weight
      local = _optional(table, "claudeloop_local", "engines.claudeloop_local", dict, {})
      return (
          EnginesConfig(
              enabled=enabled,
              weights=weights,
              claudeloop_local=ClaudeloopLocalConfig.from_table(local, "engines.claudeloop_local"),
          ),
          (*spellings, *weight_spellings),
      )
  ```
  In `_parse_phase`, replace `engines = tuple(engines_raw) if engines_raw is not None else None` with:
  ```python
      engines = (
          EngineNameResolver().resolve_all(engines_raw, where=f"{path}.engines")[0]
          if engines_raw is not None
          else None
      )
  ```
  (This also drops a repeated name inside one phase list; nothing depends on repeats.)
  In `parse_config`, the new head (replacing the two first calls and the `phase_engines = (...)` block):
  ```python
      spellings: list[LegacySpelling] = []
      features = _parse_features(data)
      engines, engine_spellings = _parse_engines(data)
      spellings.extend(engine_spellings)
      resolver = EngineNameResolver()
      phases_table = _optional(data, "phases", "phases", dict, {})
      phase_engines: list[str] = []
      for phase_name in ("design", "build", "review"):
          raw = _optional(phases_table, phase_name, f"phases.{phase_name}", dict, {}).get("engines")
          names, found = resolver.resolve_all(raw or [], where=f"phases.{phase_name}.engines")
          phase_engines.extend(names)
          spellings.extend(found)
  ```
  and `legacy_spellings=tuple(spellings),` as the last keyword of the `VibeyConfig(...)` call.
  The omitted-pool rebuild below it is unchanged (if R01 landed it already uses
  `dataclasses.replace`).
- `tests/domain/test_config.py`: update **only** these expectations, each a pure text
  replacement (list them in the commit body). Use one checked script, not a rewrite: write it with
  `write_file` to `.qwenstorm/fix_test_config.py` (the lane's untracked scratch directory; the
  `shell` tool takes an argv list, so a shell heredoc cannot run), then run it as
  `["python3", ".qwenstorm/fix_test_config.py"]`:
  ```
  from pathlib import Path
  p = Path("tests/domain/test_config.py")
  s = p.read_text(encoding="utf-8")
  pairs = [
      ('assert "qwenloop" in config.engines.enabled', 'assert "sovereignloop" in config.engines.enabled', (2,)),
      ('("claudeloop-local", "qwenloop"', '("claudeloop-local", "sovereignloop"', (1, 2)),
      ('("qwenloop", "claudeloop-local")', '("sovereignloop", "claudeloop-local")', (0, 1)),
      ('enabled == ("qwenloop",)', 'enabled == ("sovereignloop",)', (0, 1)),
      ('enables("qwenloop")', 'enables("sovereignloop")', (1,)),
      ('\n        "qwenloop",\n', '\n        "sovereignloop",\n', (1, 2)),
  ]
  for old, new, allowed in pairs:
      n = s.count(old)
      assert n in allowed, (old, n)
      s = s.replace(old, new)
      print(n, old)
  p.write_text(s, encoding="utf-8")
  ```
  The inputs that *write* `qwenloop` in TOML (`enabled = ["qwenloop"]`, `[features] qwenloop`,
  `[qwenloop]`) stay: they now exercise the legacy spelling. `config.features.qwenloop` and
  `config.qwenloop.backend` stay (lanes L18e and L08b rename those).
- **Stop rule.** If any other test fails and the fix is not a pure replacement of an expected
  `"qwenloop"` in a *parsed engine list* by `"sovereignloop"`, stop and report the test name.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).engines.enabled == ("sovereignloop",)` and `.legacy_spellings == ()`.
- [ ] `[engines] enabled = ["qwenloop", "codexloop"]` gives `("sovereignloop", "codexloop")` and exactly `(LegacySpelling("engines.enabled", "qwenloop", "sovereignloop"),)`.
- [ ] `[engines.weights] qwenloop = 3` gives `weights == {"sovereignloop": 3}` and a record with `where="engines.weights"`.
- [ ] `[phases.build] engines = ["qwenloop"]` gives `phases.build.engines == ("sovereignloop",)` and a record with `where="phases.build.engines"`.
- [ ] `"sovereignloop" in KNOWN_ENGINES` and `"qwenloop" not in KNOWN_ENGINES`.
- [ ] `grep -n '"qwenloop"' src/vibey/domain/config.py` prints only the `LOCAL_ENGINE_FEATURES` feature-key value and the `FeaturesConfig`/`[qwenloop]` code other lanes own.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_engine_names.py` (pure; no I/O):
- `test_resolve_maps_the_alias_and_records_it`: `EngineNameResolver().resolve("qwenloop", where="engines.enabled") == ("sovereignloop", LegacySpelling("engines.enabled", "qwenloop", "sovereignloop"))`.
- `test_resolve_leaves_canonical_and_unknown_names_alone`: `"sovereignloop"`, `"claudeloop"` and `"bogus"` come back unchanged with `None`.
- `test_resolve_passes_a_non_string_through`: `resolve(1, where="x") == (1, None)` (add `# type: ignore[arg-type]`).
- `test_resolve_all_keeps_order_and_drops_duplicates_after_resolution`: `["claudeloop", "qwenloop", "sovereignloop", "claudeloop"]` gives `("claudeloop", "sovereignloop")` and one record.
- `test_resolve_all_records_each_legacy_spelling_once`: `["qwenloop", "qwenloop"]` gives one record.
- `test_injected_aliases_replace_the_default_table`: `EngineNameResolver({"old": "new"}).resolve("qwenloop", where="w") == ("qwenloop", None)`.
- `test_classes_satisfy_their_interfaces`.
- `test_the_default_pool_is_sovereignloop`: behaviour 8.
- `test_legacy_enabled_is_normalized_and_recorded`.
- `test_legacy_weights_key_is_normalized_and_recorded`.
- `test_legacy_phase_engines_are_normalized_and_recorded` (design and review too).
- `test_records_follow_the_order_they_were_read`: a config with a legacy name in `enabled`, `weights`, and `[phases.design]` gives records in that order.
- `test_an_unknown_engine_is_still_refused`: `enabled = ["bogus"]` raises `ConfigError` matching `unknown engine 'bogus'`.
- `test_known_engines_name_sovereignloop_not_qwenloop`: `set(KNOWN_ENGINES) <= {e.value for e in EngineId}`, `"sovereignloop" in KNOWN_ENGINES`, `"qwenloop" not in KNOWN_ENGINES`.
- `test_the_local_feature_table_keys_the_new_id_and_keeps_the_old_switch`: `LOCAL_ENGINE_FEATURES["sovereignloop"] == "qwenloop"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_engine_names.py tests/domain/test_config.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_config_loader.py tests/infrastructure/engines tests/test_bootstrap.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

The full `--cov` run needs PostgreSQL until lane `fakes-harness-decouple` lands (the root
`tests/conftest.py` opens it at session start). The last command must print nothing.

## Out of scope
- `FeaturesConfig.qwenloop`, the `[features]` key and `VIBEY_FEATURE_*` names: lane
  `loops-vibey-local-engine-names` (L18e), which owns the legacy switch reads.
- The `[qwenloop]` table: lane `loops-config-sovereignloop-table` (L08b).
- The `paidloop` keyword: lane `loops-paidloop-keyword` (L17b). The `--engines` CLI flag.
- Printing the records: lane `loops-doctor-legacy-spellings` (L07).
- Any infrastructure or CLI file.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-engine-id-sovereignloop`, `engines-pool`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
