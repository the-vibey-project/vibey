## Title
feat(cli): vibey doctor lists every qwenloop-era legacy spelling still in use

ADR-0046 lane L07 (slug `loops-doctor-legacy-spellings`).

## Why
- **The law.** 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) forbids silently dropping a
  spelling: "Removing a spelling is not 'less configurable' … because the same key exists under
  its new name. Removing one *silently* would break adopters, and that is why every removal waits
  for `vibey doctor` evidence (lane L07 makes it list each legacy spelling in use)" (ADR-0046
  *Migration*, `specs/ADR-two-loops.md:417`).
- **The decision.** Every rename lane in the ADR-0046 rename wave defers its own reporting to this
  lane, by name:
  - `loops-config-engine-names` (L08a): `VibeyConfig.legacy_spellings: tuple[LegacySpelling, ...]`
    records `engines.enabled`, `engines.weights` and `phases.*.engines` legacy names.
  - `loops-config-sovereignloop-table` (L08b): the `[qwenloop]` table's own record, appended to
    the same tuple.
  - `loops-vibey-local-engine-names` (L18e): `[features] qwenloop` and every `VIBEY_FEATURE_QWENLOOP`
    /`VIBEY_FEATURE_SOVEREIGNLOOP` decision, recorded the same way; also "Printing the records:
    lane `loops-doctor-legacy-spellings` (L07)" verbatim.
  - `loops-claudeloop-local-paid` (L17a): `features.claudeloop_local` records itself into the
    same tuple with `current='[engines].enabled = ["claudeloop-local"]'`.
  - `loops-tenant-legacy-paths` (L18d) and `loops-tenant-legacy-env` (L18c): the runner's own
    `.qwenloop/` run directories, `<cache>/qwenloop` model cache and `QWENLOOP_*` environment
    names, none of which flow through `VibeyConfig.legacy_spellings` (they are read inside the
    `sovereignloop` tenant, not vibey's own config parser), so this lane must ask the runner
    directly, not just read config.
  - `loops-cli-provider-name` (L18f): `--provider qwenloop` prints its own one-line warning on
    stderr at the moment it is used, but records nothing durable for `doctor` to read later --
    this lane does not re-detect a past `--provider` invocation; that spelling's exposure is its
    own stderr line, unchanged by this lane.
- **The gap, at integration `d3b4a388`.** `vibey doctor` has no legacy-spelling section at all
  (there is nothing to have one of, before the rename wave). Every source this lane reads already
  exists as a **named** field or method by the time this lane lands, because every lane above
  landed first (`loops-config-sovereignloop-table`, `loops-tenant-legacy-paths`,
  `loops-vibey-local-engine-names`, `loops-claudeloop-local-paid`) plus `installer-doctor`, which
  gives `vibey doctor` its current output structure (its own sections, printed before or after
  this one; this lane does not know their exact text and must not assume it).

## Required behaviour
1. **`class LegacySpellingReport`** in `src/vibey/infrastructure/doctor/legacy_spellings.py` (new
   package `infrastructure/doctor/` if `installer-doctor` did not already create one; if it did,
   add this module beside whatever `installer-doctor` put there), built as
   `LegacySpellingReport(*, config: VibeyConfig, cwd: Path, environ: Mapping[str, str],
   cache_base: Callable[[str], Path] = user_cache_path)`:
   - `lines(self) -> tuple[str, ...]`: every distinct legacy spelling currently in use, each as
     one line of the exact shape
     `f"legacy spelling in use: {where} {legacy} -> {current} (works through 3.x; rename it)"`
     (the wording `loops-paidloop-keyword` already uses for `--engines`, kept identical here so
     an operator sees one phrasing everywhere), in this order:
     1. every `LegacySpelling` in `config.legacy_spellings`, in the order stored (`config.py`'s
        `parse_config` already orders them: engines, weights, phases, `[qwenloop]`, `[features]
        qwenloop`, `features.claudeloop_local`);
     2. `"legacy spelling in use: <cache> holds the pre-rename model cache -> <cache>/sovereignloop (rename it by moving the directory yourself; nothing here moves it)"`
        when `cache_base("qwenloop").exists()` and `not cache_base("sovereignloop").exists()`
        (`StatePaths`'s exact rule, lane `loops-tenant-legacy-paths`; call
        `StatePaths(cache_base=cache_base).cache_root() == cache_base("qwenloop")` rather than
        reimplementing the "only while the current one is absent" check a second time);
     3. `"legacy spelling in use: .qwenloop/ holds N run director{y|ies} -> .sovereignloop/ (works through 3.x; rename it)"`
        when `cwd / ".qwenloop" / "runs"` exists and holds at least one entry, with `N` the count
        and the noun singular for 1 and plural otherwise;
     4. one line per legacy environment variable from `{"QWENLOOP_CONFIG", "QWENLOOP_BASE_URL",
        "QWENLOOP_MODEL", "QWENLOOP_API_KEY", "QWENLOOP_NETWORK"}` (lane `loops-tenant-legacy-env`'s
        `LEGACY_ENV` values) that is **set and non-blank** in `environ` while its current
        counterpart (`SOVEREIGNLOOP_CONFIG`, etc.) is **unset or blank** -- the same precedence
        `SettingsLoader._read` uses -- each worded
        `f"legacy spelling in use: {legacy} is set -> {current} (works through 3.x; rename it)"`,
        in the fixed order `CONFIG, BASE_URL, MODEL, API_KEY, NETWORK`;
     5. one line for `VIBEY_FEATURE_CLAUDELOOP_LOCAL` when it is present in `environ` at all (any
        value, matching `LocalEngineSettings._warn_if_claudeloop_local_switch_is_set`'s own
        trigger), worded exactly
        `"legacy spelling in use: VIBEY_FEATURE_CLAUDELOOP_LOCAL is set -> [engines].enabled = [\"claudeloop-local\"] (works through 3.x; rename it)"`.
   - `lines()` returns `()` when nothing legacy is in use; it never raises for a missing cache
     directory, a missing `.qwenloop/runs`, or an empty `environ`.
2. **`vibey doctor`** prints every line `LegacySpellingReport(...).lines()` returns, each on its
   own line, **after** every section that already exists at the point this lane lands (find the
   end of `doctor`'s current output with `grep -n "def doctor" src/vibey/cli/main.py` and read the
   function to its end; append the new block as the last thing it prints, before the function's
   final `return`/`raise typer.Exit(...)`). Nothing legacy in use prints nothing extra: `doctor`'s
   output for a project that uses no legacy spelling is byte-identical to today's.
3. **`src/vibey/infrastructure/doctor/interfaces/legacy_spellings_interface.py`** (new, or added to
   whatever `installer-doctor` already created under `infrastructure/doctor/interfaces/`):
   `@runtime_checkable class LegacySpellingReportInterface(Protocol)` with
   `lines(self) -> tuple[str, ...]`.

## Where to change
- First run `grep -n "class LegacySpelling\b" src/vibey/domain/engine_names.py` and
  `grep -n "StatePaths" src/vibey_runners/sovereign/src/sovereignloop/infrastructure/state_paths.py`
  to confirm both lanes have landed with the shapes this spec assumes; **stop and report** the
  exact mismatch if either constructor or field differs (do not silently adapt the report's
  wording to a different shape).
- New: `src/vibey/infrastructure/doctor/legacy_spellings.py` (or alongside `installer-doctor`'s
  package if it already exists under that path -- `grep -n "class.*Doctor" -r
  src/vibey/infrastructure/doctor 2>/dev/null` first; if the directory does not exist, create it
  with an `__init__.py` holding only the provenance line and a one-sentence module docstring).
  Imports: `from collections.abc import Callable, Mapping`, `from pathlib import Path`,
  `from platformdirs import user_cache_path`, `from vibey.domain.config import VibeyConfig`,
  `from sovereignloop.infrastructure.state_paths import StatePaths` (the tenant is on the
  interpreter's path the same way `vibey doctor` already imports other sovereign-tenant pieces;
  if it is not, stop and report rather than vendoring a second copy of `StatePaths`'s rule).
- New: `src/vibey/infrastructure/doctor/interfaces/legacy_spellings_interface.py`.
- `src/vibey/cli/main.py` (`edit_file` only): the `doctor` command, appended block (behaviour 2).
- Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- New test file `tests/infrastructure/doctor/test_legacy_spellings.py` (create
  `tests/infrastructure/doctor/__init__.py` with the provenance line only, if the directory does
  not already exist).
- **Stop rule.** If `vibey doctor`'s current output already tests an exact byte-for-byte golden
  string in `tests/cli/test_operational_commands.py` that this lane's appended block would now
  make fail, that test's expectation is not one this lane may edit unless the failure is purely
  "the new block now appears after it" (i.e. it asserts equality of the *whole* output): if so,
  change that one assertion to check the previously-asserted prefix plus `no legacy spelling
  content` for a project that uses none, and say so in the commit body; any other failure, stop
  and report.

## Acceptance criteria
- [ ] A project with no legacy config, no legacy environment variable and no legacy cache/run
      directory sees no new output from `doctor` at all.
- [ ] Every one of the five line kinds in behaviour 1 has its own test, in the fixed order given.
- [ ] The wording matches `loops-paidloop-keyword`'s stderr line character for character for the
      config-derived lines: `"legacy spelling in use: {where} {legacy} -> {current} (works
      through 3.x; rename it)"`.
- [ ] `lines()` never raises for any combination of a missing cache directory or run directory.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*` and `src/vibey/cli/*`.

## Tests to write first (TDD)
`tests/infrastructure/doctor/test_legacy_spellings.py` (`tmp_path` for `cwd`, a dict for
`environ`, `cache_base=lambda name: tmp_path / "cache" / name`; build `config` with
`parse_config(...)` on a minimal `{"project": {"name": "x"}}` unless a test overrides it):
- `test_nothing_legacy_gives_no_lines`: defaults everywhere → `lines() == ()`.
- `test_config_legacy_spellings_are_printed_in_their_recorded_order`: `config.legacy_spellings =
  (LegacySpelling("engines.enabled", "qwenloop", "sovereignloop"),
  LegacySpelling("features.qwenloop", "qwenloop", "sovereignloop"))` (built via
  `dataclasses.replace` on a parsed config) → the first two lines are exactly
  `"legacy spelling in use: engines.enabled qwenloop -> sovereignloop (works through 3.x; rename it)"`
  and the same for the second, in that order.
- `test_the_legacy_cache_is_reported_once`: `(tmp_path / "cache" / "qwenloop").mkdir(parents=True)`,
  no `sovereignloop` cache dir → one line naming the cache; creating the `sovereignloop` cache dir
  too removes that line.
- `test_legacy_runs_are_counted_and_pluralized`: one run directory under
  `cwd/.qwenloop/runs/r1` → `"...holds 1 run directory -> ..."`; a second one → `"...holds 2 run
  directories -> ..."`; no `.qwenloop/runs` at all → no such line.
- `test_legacy_environment_variables_are_reported_in_fixed_order`: `environ = {"QWENLOOP_MODEL":
  "gpt-oss:20b", "QWENLOOP_API_KEY": "k"}` (no current-name counterparts) → two lines, `MODEL`
  before `API_KEY`, each worded `"legacy spelling in use: QWENLOOP_MODEL is set -> SOVEREIGNLOOP_MODEL (works through 3.x; rename it)"`.
- `test_a_blank_legacy_variable_is_not_reported`: `environ = {"QWENLOOP_MODEL": "  "}` → no line
  for it.
- `test_a_set_current_variable_suppresses_its_legacy_line`: `environ = {"QWENLOOP_MODEL": "old",
  "SOVEREIGNLOOP_MODEL": "new"}` → no `MODEL` line.
- `test_the_claudeloop_local_switch_is_reported_whatever_its_value`: `environ =
  {"VIBEY_FEATURE_CLAUDELOOP_LOCAL": "0"}` → the one fixed line naming
  `[engines].enabled = ["claudeloop-local"]`.
- `test_doctor_prints_the_report_after_its_existing_output`: `CliRunner().invoke(app, ["doctor"])`
  in a `tmp_path` with `monkeypatch.setenv("QWENLOOP_MODEL", "gpt-oss:20b")` and
  `monkeypatch.chdir(tmp_path)` → the legacy line appears in `res.output`, after every line
  `doctor` would have printed with the variable unset.
- `test_classes_satisfy_their_interfaces`: `isinstance(LegacySpellingReport(config=..., cwd=...,
  environ={}), LegacySpellingReportInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/doctor tests/cli/test_operational_commands.py tests/domain/test_config.py tests/domain/test_engine_names.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

`tests/cli/test_operational_commands.py` needs PostgreSQL (`VIBEY_TEST_DATABASE_URL`) until lane
`fakes-harness-decouple` lands; `tests/infrastructure/doctor/test_legacy_spellings.py` itself
needs none.

## Out of scope
- Removing any legacy spelling (a 4.0.0 decision made only after this report shows none in use).
- `--provider qwenloop`'s own stderr line (lane `loops-cli-provider-name`, already printed at the
  point of use) and `vibey worker --engines`'s stderr line (lane `loops-paidloop-keyword`,
  likewise).
- `installer-doctor`'s own checks and output.
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-config-sovereignloop-table`, `loops-tenant-legacy-paths`, `loops-vibey-local-engine-names`, `loops-claudeloop-local-paid`, `installer-doctor`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
