## Title
feat(engines): `paidloop` in [engines].enabled or --engines declares paidloop with claudeloop alone

ADR-0046 lane L17b (slug `loops-paidloop-keyword`).

## Why
Draft ADR-0046 §1 (`specs/ADR-two-loops.md:116`): "**claudeloop is paidloop's default adapter.**
Writing `paidloop` in `[engines].enabled` or `--engines` declares paidloop with `claudeloop`
alone. The other paid adapters join only when they are named." Sub-doctrine 8.b
(`src/vibey_tools/gh/docs/doctrines.md:120-135`) keeps paid declared-only and names Claude the
paid default. Design-sheet decision D12: `--engines` keeps #321's meaning (it narrows the pool;
declaration is the project's config), and `paidloop` is accepted as a spelling in both places,
expanding to `claudeloop`; the VibeyProject CR takes engine ids only.

At integration `d3b4a388` neither place knows the word: `_parse_engines` refuses any name
outside `KNOWN_ENGINES` (`src/vibey/domain/config.py:403-412`), and the worker builds its
allow-list with `EngineId(e.strip())` (`src/vibey/cli/main.py:1471-1477`), which raises on
`paidloop`. Lane `loops-config-engine-names` added `EngineNameResolver` in
`src/vibey/domain/engine_names.py`, and made `_parse_engines` and `parse_config` resolve
`[engines].enabled`, `[engines.weights]` keys and every `[phases.*].engines` through it. This
lane teaches that one resolver the keyword (so config gets it for free) and routes `--engines`
through it, which also makes a legacy spelling on the command line say so (ADR-0046 §7,
Migration table: "`--engines qwenloop` … normalized with a deprecation warning").

## Required behaviour
1. `src/vibey/domain/engine_names.py` gains
   ```python
   #: Loop keywords an operator may write where an engine id goes (ADR-0046 §1, decision D12):
   #: `paidloop` declares paidloop with its default adapter alone. Derived from
   #: `domain/loop.py::DEFAULT_ADAPTER`, so the default adapter is stated once. `sovereignloop`
   #: is not a keyword: it is its own native adapter's engine id.
   LOOP_KEYWORDS: Final[Mapping[str, str]] = MappingProxyType(
       {LoopId.PAIDLOOP.value: DEFAULT_ADAPTER[LoopId.PAIDLOOP].value}
   )
   ```
   so `LOOP_KEYWORDS == {"paidloop": "claudeloop"}`, and `"LOOP_KEYWORDS"` joins the module's
   `__all__` (if it has one).
2. `EngineNameResolver.resolve(name, *, where)` returns `(LOOP_KEYWORDS[name], None)` for a
   keyword — an expansion, not a legacy spelling, so no `LegacySpelling` — before it looks at
   legacy aliases; every other name behaves as before. `resolve_all` (built on `resolve`)
   therefore expands the keyword, keeps order and drops duplicates:
   `resolve_all(("paidloop", "claudeloop", "codexloop"), where="--engines") == (("claudeloop", "codexloop"), ())`.
3. Config (no `config.py` edit; the resolver does it): `[engines] enabled = ["paidloop"]` parses
   to exactly `{"claudeloop", "sovereignloop"}` (sovereignloop is appended as always) with no
   legacy record; `[engines.weights] paidloop = 3` becomes `{"claudeloop": 3}`;
   `[phases.build] engines = ["paidloop"]` becomes `("claudeloop",)`.
4. `vibey worker --engines` resolves its comma-separated names through
   `EngineNameResolver().resolve_all(<stripped names>, where="--engines")` before building the
   allow-list: `--engines paidloop` narrows to `claudeloop`; `--engines qwenloop` narrows to
   `sovereignloop` and prints to **stderr**
   `legacy spelling in use: --engines qwenloop -> sovereignloop (works through 3.x; rename it)`
   (the same wording `vibey doctor` uses, lane `loops-doctor-legacy-spellings`); an unknown name
   keeps today's `Invalid engine: …` and exit 2. Nothing else in `worker` changes.

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first.
- `src/vibey/domain/engine_names.py` (created by lane `loops-config-engine-names`; use
  `edit_file`): the constant of behaviour 1 after the imports, with the imports it needs
  (`from types import MappingProxyType`, `from typing import Final`,
  `from collections.abc import Mapping`, `from vibey.domain.loop import DEFAULT_ADAPTER, LoopId`
  — keep the ones already there), and as the first statements of `EngineNameResolver.resolve`
  (after its docstring):
  ```python
          keyword = LOOP_KEYWORDS.get(name)
          if keyword is not None:
              return keyword, None
  ```
  The module stays pure (`tests/domain/test_domain_purity.py`). Its interface
  (`src/vibey/domain/interfaces/engine_names_interface.py`) keeps its signatures; if its
  `resolve` docstring says "alias key → canonical value", extend it to "loop keyword or alias key".
  If `domain/loop.py` imports `domain/engine_names.py` (an import cycle), stop and report.
- `src/vibey/cli/main.py` (1761 lines: `edit_file`): in `worker`, add
  `from vibey.domain.engine_names import EngineNameResolver` to the local imports after
  `from vibey.domain.engine import EngineId` (`:1466`), and replace the block
  ```python
      if engines_opt:
          try:
              allow_list = frozenset(EngineId(e.strip()) for e in engines_opt.split(","))
          except ValueError as exc:
              typer.echo(f"Invalid engine: {exc}")
              raise typer.Exit(2) from exc
  ```
  (`:1472-1477`) with
  ```python
      if engines_opt:
          # `paidloop` names paidloop's default adapter, and a legacy spelling still works but
          # is said out loud (ADR-0046 §1, §7; decision D12). --engines only narrows the pool.
          names, legacy = EngineNameResolver().resolve_all(
              tuple(e.strip() for e in engines_opt.split(",")), where="--engines"
          )
          for spelling in legacy:
              typer.echo(
                  f"legacy spelling in use: {spelling.where} {spelling.legacy} -> "
                  f"{spelling.current} (works through 3.x; rename it)",
                  err=True,
              )
          try:
              allow_list = frozenset(EngineId(name) for name in names)
          except ValueError as exc:
              typer.echo(f"Invalid engine: {exc}")
              raise typer.Exit(2) from exc
  ```
- New `tests/domain/test_paidloop_keyword.py` (the resolver and config) and new
  `tests/cli/test_engines_option_names.py` (the worker flag; the CLI layer's 100% floor needs a
  test that reaches the new loop). Line 1 of each: the provenance comment copied from a sibling
  in its directory.

## Acceptance criteria
- [ ] Every test below passes; `tests/domain/test_engine_names.py` and `tests/domain/test_config.py`
      pass unedited.
- [ ] `grep -n "EngineId(e.strip())" src/vibey/cli/main.py` prints nothing for the worker
      (other commands' `--engines` options are out of scope).
- [ ] `grep -n "paidloop" deploy/helm/vibey/templates/crd-vibeyproject.yaml` prints nothing (the
      CR takes engine ids only, D12).
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/domain/test_paidloop_keyword.py` (pure; no service):
- `test_paidloop_resolves_to_claudeloop_without_a_legacy_record`:
  `EngineNameResolver().resolve("paidloop", where="engines.enabled") == ("claudeloop", None)`.
- `test_the_keyword_is_derived_from_the_default_adapter`:
  `LOOP_KEYWORDS == {"paidloop": DEFAULT_ADAPTER[LoopId.PAIDLOOP].value}` and
  `"sovereignloop" not in LOOP_KEYWORDS`.
- `test_resolve_all_expands_the_keyword_and_drops_duplicates`: the example of behaviour 2.
- `test_a_legacy_spelling_beside_the_keyword_is_still_recorded`:
  `resolve_all(("paidloop", "qwenloop"), where="--engines") == (("claudeloop", "sovereignloop"), (LegacySpelling("--engines", "qwenloop", "sovereignloop"),))`.
- `test_enabled_paidloop_declares_claudeloop_alone`:
  `load_config_from_string('[project]\nname = "x"\n\n[engines]\nenabled = ["paidloop"]\n')` →
  `sorted(engines.enabled) == ["claudeloop", "sovereignloop"]` and `legacy_spellings == ()`.
- `test_weights_and_phase_engines_accept_the_keyword`: `[engines.weights] paidloop = 3` →
  `engines.weights == {"claudeloop": 3}`; `[phases.build] engines = ["paidloop"]` →
  `phases.build.engines == ("claudeloop",)`. (If `loops-config-engine-names` does not store the
  resolved names in `weights` or `PhaseConfig.engines`, stop and report rather than edit `config.py`.)

`tests/cli/test_engines_option_names.py` (no database: `--azure bogus` makes `worker` exit 2
before it connects anywhere; `runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})`
as `tests/cli/test_operational_commands.py:30`):
- `test_a_legacy_engine_spelling_is_named_on_stderr`: `["worker", "--engines", "qwenloop", "--azure", "bogus"]`
  → `exit_code == 2`, `res.stderr` contains
  `legacy spelling in use: --engines qwenloop -> sovereignloop (works through 3.x; rename it)`,
  and the output contains `--azure must be 'memory' or 'az'`.
- `test_paidloop_is_a_keyword_not_a_legacy_spelling`: `["worker", "--engines", "paidloop", "--azure", "bogus"]`
  → exit 2, `"legacy spelling" not in res.stderr`, `"Invalid engine" not in res.output`.
- `test_an_unknown_engine_is_still_refused`: `["worker", "--engines", "nope"]` → exit 2 and
  `"Invalid engine" in res.output`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/domain/engine_names.py src/vibey/cli/main.py tests/domain/test_paidloop_keyword.py tests/cli/test_engines_option_names.py`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_paidloop_keyword.py tests/domain/test_engine_names.py tests/domain/test_config.py tests/domain/test_domain_purity.py tests/cli/test_engines_option_names.py tests/meta/test_crd_engine_enum.py
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    git diff --stat

## Out of scope
- The CRD enum and the operator handler (engine ids only, D12); `vibey doctor --cluster --engines`
  and every other command's engine options.
- `config.py` (the resolver change reaches it), `KNOWN_ENGINES`, and any chart value.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-claudeloop-local-paid`, `loops-domain-loop-id`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
