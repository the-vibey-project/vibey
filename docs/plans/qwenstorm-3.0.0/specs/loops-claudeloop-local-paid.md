## Title
feat(engines)!: claudeloop-local is a paidloop adapter, declared-only

ADR-0046 lane L17a (slug `loops-claudeloop-local-paid`).

## Why
Draft ADR-0046 §9 (`specs/ADR-two-loops.md:295-296`): "**`claudeloop-local` is a paidloop
adapter, declared-only** — the operator's ruling of 2026-09-22. Claude Code is not FOSS, so by
8.b's rule (an adapter is sovereign only when both its tool and its model are free) it is
paid-side even when its model is local. Its descriptor's tier becomes PAID, it leaves
sovereignloop's pool and its feature switch, and it runs only when `[engines].enabled` or
`--engines` names it." `STORM-CONTEXT.md` ("Operator rulings") repeats the ruling, and
sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120-135`) keeps paid adapters
declared-only.

At integration `d3b4a388` claudeloop-local is sovereign-side and switch-driven:
- `ClaudeloopLocalDescriptors.build` returns `tier=EngineTier.LOCAL`
  (`src/vibey/infrastructure/engines/descriptors.py:397`), and `LOCAL_DESCRIPTORS` holds it
  (`:411-413`), so it shares the local tier's SWRR (`src/vibey/domain/rotation.py:89-110`);
- `LOCAL_ENGINE_FEATURES` gives it a `[features] claudeloop_local` key
  (`src/vibey/domain/config.py:22-24`), `LocalEngineSettings.enabled` turns it on from
  `VIBEY_FEATURE_CLAUDELOOP_LOCAL` or that key (`src/vibey/infrastructure/engines/local_engines.py:99-107`),
  and `parse_config` refuses to let a project name it unless the switch is on
  (`config.py:679-683`, "must be true before claudeloop-local can be requested");
- the worker's "matches none" message tells the operator to set that switch
  (`src/vibey/cli/main.py:1656-1662`).
`updates/321.md` behaviour 1 (lane `engines-pool`) kept the switch; the design sheet records that
this lane supersedes it.

## Required behaviour
1. **Tier PAID.** `ClaudeloopLocalDescriptors.build` returns `tier=EngineTier.PAID`; every
   other field is unchanged (same binary, profile, zero cost, `doctor_args`). Its docstring gains
   the bullet of "Where to change". So `BY_ENGINE_ID[EngineId.CLAUDELOOP_LOCAL].tier is EngineTier.PAID`,
   and `LocalEngineSettings.descriptor(EngineId.CLAUDELOOP_LOCAL).tier is EngineTier.PAID`.
2. **Out of the sovereign descriptor list.** `LOCAL_DESCRIPTORS == (QWENLOOP,)` (the tier-LOCAL
   engines only, so its name stays true and `tests/infrastructure/engines/test_descriptors.py::test_the_local_descriptors_are_exactly_the_local_tier`
   passes unedited); `ALL_DESCRIPTORS == (*DEFAULT_DESCRIPTORS, *LOCAL_DESCRIPTORS, CLAUDELOOP_LOCAL)`,
   which keeps `BY_ENGINE_ID`'s keys and order exactly as today.
3. **No switch.** `LOCAL_ENGINE_FEATURES` no longer has a `"claudeloop-local"` entry, so
   `LOCAL_ENGINE_SWITCHES` has no claudeloop-local switch and the config loader
   (`src/vibey/infrastructure/config_loader.py:88-98`) no longer maps
   `VIBEY_FEATURE_CLAUDELOOP_LOCAL` into `[features]`.
4. **Declared-only.** `LocalEngineSettings.enabled(EngineId.CLAUDELOOP_LOCAL)` is True **iff** the
   project's config declares it: `config["engines"]` is a table whose `enabled` value is a list
   (or tuple) containing `"claudeloop-local"`, or `config["engines"]` is itself such a list (the
   VibeyProject CR allow-list, `src/vibey/infrastructure/operator/handlers.py:61-62`). A bare
   string, a missing key or any other shape declares nothing. `[features] claudeloop_local` and
   `VIBEY_FEATURE_CLAUDELOOP_LOCAL` never turn it on.
5. **One warning.** When `VIBEY_FEATURE_CLAUDELOOP_LOCAL` is present in the environment (any
   value), the first call of `enabled(EngineId.CLAUDELOOP_LOCAL)` on an instance logs exactly
   one WARNING whose message is
   `claudeloop-local is declared-only now (ADR-0046 §9, sub-doctrine 8.b): name it in [engines].enabled; ignoring VIBEY_FEATURE_CLAUDELOOP_LOCAL`;
   later calls on the same instance log nothing more. Without the variable, nothing is logged.
6. `enabled_engines` is the switched engines in `LOCAL_ENGINE_SWITCHES` order, then
   `EngineId.CLAUDELOOP_LOCAL` when it is declared (so `adapters()` still builds its
   profile-built adapter, and the worker still preflights it on every selection, because nothing
   else records its health). The pool of lane `engines-pool` follows automatically, because
   `EnginePool.for_project` asks `LocalEngineSettings.enabled(EngineId.CLAUDELOOP_LOCAL)` for
   it. **If `src/vibey/infrastructure/engines/engine_pool.py` decides claudeloop-local's
   membership any other way, stop and report** (do not edit that file here).
7. **Config.** `parse_config` no longer refuses `claudeloop-local` in `[engines].enabled` or any
   `[phases.*].engines` without a feature switch (the loop `for engine, key in LOCAL_ENGINE_FEATURES.items():`
   that raised `must be true before … can be requested`, `config.py:679-683`, is deleted). A
   `[features]` table that has the key `claudeloop_local` (any value) adds
   `LegacySpelling(where="features.claudeloop_local", legacy="claudeloop_local", current='[engines].enabled = ["claudeloop-local"]')`
   to `VibeyConfig.legacy_spellings` (lane `loops-config-engine-names`), after the records that
   lane adds; the key still parses as a bool in `FeaturesConfig.claudeloop_local`, and no longer
   adds claudeloop-local to an omitted pool.
8. **The worker's message.** The `--engines … matches none of this worker's engines` message
   (`cli/main.py`, the `typer.echo(` inside `if not allowed:`) names no switch:
   ```python
                   typer.echo(
                       f"--engines {engines_opt} matches none of this worker's engines "
                       f"({available}); sovereignloop is always on, and every other engine "
                       "(claudeloop-local included) joins only when the project declares it "
                       "in [engines].enabled or in its VibeyProject engines list."
                   )
   ```
   The exit code stays `EXIT_USAGE`.

Commit with the Title as the subject and this footer:
`BREAKING CHANGE: claudeloop-local is paid-side and declared-only. VIBEY_FEATURE_CLAUDELOOP_LOCAL and [features] claudeloop_local no longer switch it on (the variable logs a warning; the key is reported as a legacy spelling); name it in [engines].enabled or the VibeyProject engines list. Its tier is PAID, so it never shares sovereignloop's rotation.`

## Where to change
Read `STORM/EDITING-RULES.md` first. Every file below is
over 100 lines: `edit_file` only. Lanes `engines-pool`, `loops-config-engine-names` and
possibly `loops-vibey-local-engine-names` edited some of these lines first: anchor on the quoted
text and function names, and re-read each file before editing it.

- `src/vibey/infrastructure/engines/descriptors.py` (415 lines):
  - in `ClaudeloopLocalDescriptors.build`, the unique text
    `        tier=EngineTier.LOCAL,\n        doctor_args=profile,` becomes
    `        tier=EngineTier.PAID,\n        doctor_args=profile,`;
  - in its class docstring, after the `- **No credential, no price.** …` bullet (it ends with
    `claudeloop records every local turn at $0.`), add:
    ```
    - **Paid-side, declared-only (ADR-0046 §9).** Claude Code is not FOSS, so by 8.b's rule
      the adapter is a paidloop adapter even when its model is local: tier PAID, and it runs
      only when `[engines].enabled` (or the CR's engines list) names it.
    ```
  - replace the line `LOCAL_DESCRIPTORS: tuple[EngineDescriptor, ...] = (QWENLOOP, CLAUDELOOP_LOCAL)`,
    the comment line directly above it, and the `ALL_DESCRIPTORS` line below it with:
    ```python
    # The sovereign engines (tier LOCAL): sovereignloop's native adapter, always on (8.b).
    LOCAL_DESCRIPTORS: tuple[EngineDescriptor, ...] = (QWENLOOP,)
    # claudeloop-local is paid-side and declared-only (ADR-0046 §9). Its per-project
    # descriptor is built from its profile (`LocalEngineSettings.descriptor`); this default
    # one keys BY_ENGINE_ID, in the same place it always had.
    ALL_DESCRIPTORS: tuple[EngineDescriptor, ...] = (
        *DEFAULT_DESCRIPTORS,
        *LOCAL_DESCRIPTORS,
        CLAUDELOOP_LOCAL,
    )
    ```
- `src/vibey/domain/config.py`:
  - `LOCAL_ENGINE_FEATURES` keeps only the sovereign entry (`{"sovereignloop": "sovereignloop"}`
    after lane `loops-config-engine-names`); its comment becomes
    `# The sovereign engine's [features] switch key (ADR-0015). claudeloop-local has none: it is`
    and `# a paidloop adapter, declared in [engines].enabled (ADR-0046 §9).`
  - in `parse_config`, delete the whole `for engine, key in LOCAL_ENGINE_FEATURES.items():` loop
    (its `continue` for the sovereign engine and its `raise ConfigError(f"features.{key}", …)`).
    If `phase_engines` is then read nowhere else (ruff reports F841), delete its assignment too.
  - add the `LegacySpelling` of behaviour 7 where `parse_config` collects the records it passes
    as `legacy_spellings=` to `VibeyConfig(...)`, after the existing ones:
    ```python
        features_table = _optional(data, "features", "features", dict, {})
        if "claudeloop_local" in features_table:
            legacy.append(  # the list parse_config passes as legacy_spellings=tuple(...)
                LegacySpelling(
                    where="features.claudeloop_local",
                    legacy="claudeloop_local",
                    current='[engines].enabled = ["claudeloop-local"]',
                )
            )
    ```
    Use the collection name `loops-config-engine-names` chose; if it builds the tuple another
    way, append this record to it without changing how the others are built.
- `src/vibey/infrastructure/engines/local_engines.py` (200 lines at `d3b4a388`):
  - add `import logging` and, unless the module already has a logger that `engines-pool`'s
    "cannot be switched off" warning uses (then use that one), `_LOG = logging.getLogger(__name__)`;
  - add the two constants after `CLAUDELOOP_LOCAL_PROFILE_ENV` and export both in `__all__`:
    ```python
    #: The switch claudeloop-local had before ADR-0046 §9; read only to say it is ignored.
    CLAUDELOOP_LOCAL_SWITCH_ENV = "VIBEY_FEATURE_CLAUDELOOP_LOCAL"
    CLAUDELOOP_LOCAL_SWITCH_IGNORED = (
        "claudeloop-local is declared-only now (ADR-0046 §9, sub-doctrine 8.b): name it in "
        "[engines].enabled; ignoring VIBEY_FEATURE_CLAUDELOOP_LOCAL"
    )
    ```
  - in `LocalEngineSettings.__init__`, add `self._claudeloop_local_warned = False`;
  - in `enabled`, as its first statements (after its docstring, if it has one):
    ```python
            if engine_id is EngineId.CLAUDELOOP_LOCAL:
                self._warn_if_claudeloop_local_switch_is_set()
                return self._declares(EngineId.CLAUDELOOP_LOCAL)
    ```
  - `enabled_engines` returns:
    ```python
            switched = tuple(s.engine_id for s in LOCAL_ENGINE_SWITCHES if self.enabled(s.engine_id))
            # claudeloop-local has no switch: it runs when the project declares it (ADR-0046 §9).
            declared = (EngineId.CLAUDELOOP_LOCAL,) if self.enabled(EngineId.CLAUDELOOP_LOCAL) else ()
            return (*switched, *declared)
    ```
  - two private methods on `LocalEngineSettings`:
    ```python
        def _declares(self, engine_id: EngineId) -> bool:
            """Whether the project's config names `engine_id`: `[engines].enabled` from
            vibey.toml, or the VibeyProject CR's `engines` list. Any other shape, a bare
            string included, declares nothing."""
            engines = self._config.get("engines")
            listed = engines.get("enabled") if isinstance(engines, Mapping) else engines
            return isinstance(listed, list | tuple) and engine_id.value in listed

        def _warn_if_claudeloop_local_switch_is_set(self) -> None:
            """Once per instance: the switch that used to turn claudeloop-local on is ignored."""
            if self._claudeloop_local_warned or CLAUDELOOP_LOCAL_SWITCH_ENV not in self._environ:
                return
            self._claudeloop_local_warned = True
            _LOG.warning(CLAUDELOOP_LOCAL_SWITCH_IGNORED)
    ```
  - the module docstring's first line becomes
    `"""The local engines: which run, how each is configured, and where they run.`
- `src/vibey/cli/main.py` (1761 lines): replace the whole `typer.echo(` call inside
  `if not allowed:` in `worker` (from its `typer.echo(` line to its closing `)`, just before
  `raise typer.Exit(EXIT_USAGE)`) with behaviour 8's call, at the same indentation.

**Existing test expectations that change** (edit only these, with `edit_file`; list each in the
commit body). Names are at `d3b4a388`; earlier lanes may have changed the bodies, so match by
test name and assertion text. **Stop rule:** any other failing test, or one whose fix is not a
change of the kind listed, means stop and report.
- `tests/infrastructure/engines/test_descriptors.py`:
  `test_claudeloop_local_is_the_claudeloop_binary_on_a_profile_at_no_cost` — `assert CLAUDELOOP_LOCAL.tier is EngineTier.LOCAL`
  becomes `assert CLAUDELOOP_LOCAL.tier is EngineTier.PAID`. (`test_the_local_descriptors_are_exactly_the_local_tier`
  is **not** edited; behaviour 2 keeps it true, and both of its assertions still hold.)
- `tests/infrastructure/engines/test_local_engines.py`:
  - `test_there_is_one_switch_per_local_engine_named_after_its_feature_key`: delete the
    `(EngineId.CLAUDELOOP_LOCAL, "claudeloop_local", CLAUDE_LOCAL_SWITCH)` row of the expected list;
  - `test_the_features_table_switches_each_engine_on`: drop `EngineId.CLAUDELOOP_LOCAL` from the
    expected `enabled_engines` (the `claudeloop_local` feature no longer enables it);
  - `test_the_environment_wins_whenever_it_is_set`: delete the test with its `parametrize`
    decorator (it drives `CLAUDE_LOCAL_SWITCH`, which no longer exists; the new file covers the
    ignored switch);
  - `test_doctor_reads_vibey_toml_under_the_environment`: the file written as
    `"[features]\nclaudeloop_local = true\n"` becomes `'[engines]\nenabled = ["claudeloop-local"]\n'`;
    the `off` case (`{CLAUDE_LOCAL_SWITCH: "0"}`) now expects the same tuple as without the variable;
  - `test_descriptors_are_only_the_enabled_local_engines`: `_settings({CLAUDE_LOCAL_SWITCH: "1"})`
    becomes `_settings(engines={"enabled": ["claudeloop-local"]})`; `EngineId.CLAUDELOOP_LOCAL`
    stays the last element of the expected list;
  - `test_every_enabled_engine_gets_an_adapter_carrying_its_overlay`: remove
    `"claudeloop_local": True` from `features` and pass `engines={"enabled": ["claudeloop-local"]}` too.
- `tests/domain/test_config.py`:
  - `test_claudeloop_local_feature_joins_the_default_pool_with_its_profile`: rename to
    `test_the_legacy_claudeloop_local_feature_no_longer_joins_the_pool`; its
    `assert config.engines.enabled[-1] == "claudeloop-local"` becomes
    `assert "claudeloop-local" not in config.engines.enabled`, and add
    `assert LegacySpelling("features.claudeloop_local", "claudeloop_local", '[engines].enabled = ["claudeloop-local"]') in config.legacy_spellings`;
    the profile and `features.enables(...)` assertions stay;
  - `test_both_local_features_join_the_pool_in_order`: delete (one local switch remains);
  - `test_claudeloop_local_request_requires_its_feature`: delete (the rule is gone; the new file
    proves the opposite).
  `test_an_explicit_pool_is_kept_as_written` is not edited.
- `tests/infrastructure/test_config_loader.py`:
  - `test_environment_switches_every_local_engine_the_same_way`: `assert config.features.claudeloop_local is True`
    becomes `is False`, and `assert config.engines.enabled[-1] == "claudeloop-local"` becomes
    `assert "claudeloop-local" not in config.engines.enabled`;
  - `test_a_non_boolean_claudeloop_local_switch_names_itself`: delete (no such switch).
- `tests/application/test_engine_selector.py`:
  `test_local_engines_share_the_work_by_swrr_within_their_tier` — rename to
  `test_claudeloop_local_is_paid_side_and_never_shares_the_sovereign_tier`; its expectation
  becomes `assert set(picked) == {EngineId.SOVEREIGNLOOP}`.
- `tests/application/test_engine_selection.py`:
  `test_verify_rotates_from_one_local_engine_to_the_other` — rename to
  `test_verify_of_a_sovereign_implementation_goes_paid_side_while_one_sovereign_harness_exists`
  (ADR-0046 §9 records this cost); bind the claudeloop adapter to a name
  (`paid = _Adapter(EngineId.CLAUDELOOP)`, used in the adapters mapping) and assert
  `await provider.select_for(job) is paid` (claudeloop and claudeloop-local now tie in the paid
  tier, and claudeloop's cursor order 0 wins, as ADR-0046 §1 makes it paidloop's default).
- `tests/cli/test_operational_commands.py`:
  - `test_the_feature_flag_falls_back_to_project_config`: `assert on(EngineId.CLAUDELOOP_LOCAL) is True`
    (after the `[features] … claudeloop_local = true` write) becomes `is False`;
  - `test_doctor_lists_claudeloop_local_when_it_is_switched_on`: add a `tmp_path: Path`
    parameter; replace `monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "1")` with
    `monkeypatch.chdir(tmp_path)` and
    `(tmp_path / "vibey.toml").write_text('[engines]\nenabled = ["claudeloop", "claudeloop-local"]\n', encoding="utf-8")`;
  - `test_worker_sweeps_claudeloop_local_when_its_feature_is_on`: replace
    `monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "1")` with
    `monkeypatch.delenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", raising=False)`, and create the project
    with `config={"engines": {"enabled": ["claudeloop-local"]}}` instead of `config={}`;
  - `test_worker_refuses_an_allow_list_that_matches_no_engine`: an assertion that the output
    names a `VIBEY_FEATURE_*` variable or a `[features]` key becomes
    `assert "declares it" in res.output` plus `assert "VIBEY_FEATURE" not in res.output`.
  `test_doctor_omits_claudeloop_local_when_it_is_off` and
  `test_doctor_can_be_asked_for_claudeloop_local_by_name` are not edited.

New test file `tests/infrastructure/engines/test_claudeloop_local_paid.py` (line 1: the
provenance comment copied from `tests/infrastructure/engines/test_local_engines.py`).

## Acceptance criteria
- [ ] Every test below passes, and every edited test passes.
- [ ] `grep -n "claudeloop-local\|claudeloop_local" src/vibey/domain/config.py` shows no
      feature-switch entry and no "must be true before" text.
- [ ] `grep -n "VIBEY_FEATURE_CLAUDELOOP_LOCAL" src/vibey/cli/main.py` prints nothing.
- [ ] `tests/infrastructure/engines/test_descriptors.py::test_the_local_descriptors_are_exactly_the_local_tier`
      passes unedited.
- [ ] 100% branch coverage of `src/vibey/domain/*`, `src/vibey/infrastructure/*` and `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_claudeloop_local_paid.py` (no service; `caplog` and
`monkeypatch.setenv` only; build settings as `LocalEngineSettings(environ=..., config=...)`):
- `test_claudeloop_local_is_a_paid_adapter`: `ClaudeloopLocalDescriptors().build().tier is EngineTier.PAID`,
  `BY_ENGINE_ID[EngineId.CLAUDELOOP_LOCAL].tier is EngineTier.PAID`, and the profile-built
  descriptor from `LocalEngineSettings(environ={}, config={"engines": {"claudeloop_local": {"profile": "gpu"}}}).descriptor(EngineId.CLAUDELOOP_LOCAL)`
  is PAID with `doctor_args == ("--profile", "gpu")`.
- `test_the_sovereign_descriptor_list_holds_only_the_local_tier`: `{d.tier for d in LOCAL_DESCRIPTORS} == {EngineTier.LOCAL}`,
  `CLAUDELOOP_LOCAL not in LOCAL_DESCRIPTORS`, `CLAUDELOOP_LOCAL in ALL_DESCRIPTORS`, and
  `list(BY_ENGINE_ID)[-1] is EngineId.CLAUDELOOP_LOCAL`.
- `test_there_is_no_claudeloop_local_switch`: `"claudeloop-local" not in LOCAL_ENGINE_FEATURES`
  and `EngineId.CLAUDELOOP_LOCAL not in {s.engine_id for s in LOCAL_ENGINE_SWITCHES}`.
- `test_the_engines_table_declares_it`: `config={"engines": {"enabled": ["claudeloop-local"]}}` →
  `enabled(EngineId.CLAUDELOOP_LOCAL) is True`; `config={}` → False.
- `test_the_cr_engine_list_declares_it`: `config={"engines": ["claudeloop", "claudeloop-local"]}` → True.
- `test_other_shapes_declare_nothing`: `{"engines": {"enabled": "claudeloop-local"}}`,
  `{"engines": "claudeloop-local"}`, `{"engines": {}}` and `{"engines": {"enabled": ["claudeloop"]}}` → False.
- `test_the_old_switch_and_feature_key_are_ignored_with_one_warning`: environ
  `{"VIBEY_FEATURE_CLAUDELOOP_LOCAL": "1"}`, config `{"features": {"claudeloop_local": True}}`;
  under `caplog.at_level(logging.WARNING)`, `enabled(...)` twice and `enabled_engines` once →
  all False / not containing it, and exactly one record with
  `record.getMessage() == CLAUDELOOP_LOCAL_SWITCH_IGNORED`.
- `test_no_warning_without_the_old_switch`: environ `{}` → no record carries that message.
- `test_a_declared_claudeloop_local_joins_enabled_engines_with_its_profile_adapter`: config
  `{"engines": {"enabled": ["claudeloop-local"], "claudeloop_local": {"profile": "gpu"}}}` →
  `enabled_engines[-1] is EngineId.CLAUDELOOP_LOCAL`, and
  `adapters(LocalEndpointEnvironment({}))[EngineId.CLAUDELOOP_LOCAL].descriptor` is PAID with
  `doctor_args == ("--profile", "gpu")`.
- `test_config_declares_claudeloop_local_without_any_feature`:
  `load_config_from_string('[project]\nname = "x"\n\n[engines]\nenabled = ["claudeloop-local"]\n')`
  keeps `"claudeloop-local"` in `engines.enabled`, and
  `load_config_from_string('[project]\nname = "x"\n\n[phases.build]\nengines = ["claudeloop-local"]\n')`
  parses without error.
- `test_the_legacy_feature_key_is_reported_and_joins_nothing`:
  `load_config_from_string('[project]\nname = "x"\n\n[features]\nclaudeloop_local = true\n')` →
  `"claudeloop-local" not in engines.enabled`, `features.claudeloop_local is True`, and the
  `LegacySpelling` of behaviour 7 is in `legacy_spellings`; with no `[features]` table no such
  record exists.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey tests/infrastructure/engines tests/domain/test_config.py tests/infrastructure/test_config_loader.py tests/application tests/cli/test_operational_commands.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/domain/test_config.py tests/domain/test_domain_purity.py tests/infrastructure/test_config_loader.py tests/application/test_engine_selector.py tests/application/test_engine_selection.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    git diff --stat

`tests/cli` and `tests/system/test_full_worker_faked.py` need PostgreSQL through
`VIBEY_TEST_DATABASE_URL` (the `integration` tier once lane `fakes-harness-decouple` lands).

## Out of scope
- `--engines paidloop` and the `paidloop` keyword (lane `loops-paidloop-keyword`); `vibey doctor`
  listing the legacy switch (lane `loops-doctor-legacy-spellings`); the helm chart, the CRD
  enum and the operator handler.
- `engine_pool.py` (lane `engines-pool`), `engine_selection.py`, `engine_selector.py` and the
  domain comment on `EngineId.CLAUDELOOP_LOCAL`.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject and the
  `BREAKING CHANGE:` footer above.

**Depends on:** `loops-config-engine-names`, `engines-pool`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
