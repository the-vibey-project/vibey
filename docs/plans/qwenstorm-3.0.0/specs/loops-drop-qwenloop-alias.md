## Title
refactor(engines): remove the QWENLOOP Python enum alias now that every internal reference is sovereignloop

ADR-0046 lane L09 (slug `loops-drop-qwenloop-alias`).

## Why
- **The law.** ADR-0046 §7 (`specs/ADR-two-loops.md:257`): "`QWENLOOP` stays a Python enum alias
  of the same member, and L09 removes it." The *Migration* table's row for `EngineId.QWENLOOP`
  (`:400`) says the same: "enum alias, removed by L09, in the same release wave" as the rename.
  `loops-engine-id-sovereignloop` (L06) explicitly defers this: "Removing the `QWENLOOP` alias
  (lane `loops-drop-qwenloop-alias`, L09)." `ENGINE_ID_ALIASES = {"qwenloop":
  EngineId.SOVEREIGNLOOP}` and `EngineId._missing_` are **not** touched by this lane -- they stay
  forever (`specs/ADR-two-loops.md:398`: the stored spelling "read verbatim; `known()` resolves it
  … **forever** (append-only history)"). This lane removes only the **Python-level convenience**
  alias (`EngineId.QWENLOOP is EngineId.SOVEREIGNLOOP`), which exists solely so that code written
  before the rename kept compiling during the rename wave; by the time this lane runs, every such
  reference has been renamed by its own lane.
- **The gap, at the point this lane runs.** `src/vibey/domain/engine.py` still has the two-line
  alias block `loops-engine-id-sovereignloop` added:
  ```python
      SOVEREIGNLOOP = "sovereignloop"
      # The rename wave's alias (ADR-0046 §7); lane L09 removes it.
      QWENLOOP = "sovereignloop"
  ```
  By this point every lane that named `EngineId.QWENLOOP` in *source* (not in a *stored string
  literal*, which is a different, permanent thing) has landed and renamed its reference to
  `EngineId.SOVEREIGNLOOP`: `loops-tenant-legacy-paths` renamed the descriptor constant's
  comment reference, `loops-vibey-local-engine-names` renamed `LOCAL_ENGINE_FEATURES`'s key,
  `loops-claudeloop-local-paid` renamed `LOCAL_DESCRIPTORS`, `loops-cli-provider-name` renamed
  every `--provider` branch. The only reason to keep the alias any longer is defensive; removing
  it now is what makes a *future* reintroduction of `EngineId.QWENLOOP` in source fail loudly at
  `mypy --strict` instead of silently compiling.

## Required behaviour
1. **`grep -rn "EngineId\.QWENLOOP" src/vibey src/vibey_runners src/vibey_tools tests` first.**
   Every hit must be one of:
   - the two-line alias definition itself in `domain/engine.py` (removed by this lane);
   - a **stored string literal** such as `"qwenloop"` compared against `record.engine_id ==
     "qwenloop"` or similar (never touched: that is preserved history, not a Python-attribute
     reference, and is out of this lane's grep scope entirely -- this rule is about the
     `EngineId.QWENLOOP` attribute access, not the text `"qwenloop"`);
   - a test that explicitly exercises the alias itself, named for it (for example
     `test_the_legacy_spelling_constructs_the_current_member` in
     `tests/domain/test_engine_aliases.py`, lane `loops-engine-id-sovereignloop`) -- **that test
     file is a protected fixture of this lane's own history and is edited here**, in the one way
     behaviour 3 describes, and nowhere else.
   Any other hit -- a live, non-test source reference to `EngineId.QWENLOOP` outside
   `domain/engine.py` and outside `test_engine_aliases.py` -- means a rename lane this lane depends
   on has not actually finished renaming its own reference. **Stop and report every such hit by
   file and line; do not rename it here.** (This lane's job is to delete the alias once nothing
   needs it, never to hunt down and fix a straggler reference itself -- that would silently
   absorb another lane's unfinished work.)
2. **`src/vibey/domain/engine.py`**: delete exactly the comment line
   `    # The rename wave's alias (ADR-0046 §7); lane L09 removes it.` and the member line
   `    QWENLOOP = "sovereignloop"` that follows it. `SOVEREIGNLOOP = "sovereignloop"` and every
   other member, `_missing_` and `ENGINE_ID_ALIASES` are **untouched**: `EngineId("qwenloop")`
   must keep resolving to `EngineId.SOVEREIGNLOOP` through `_missing_`, exactly as before this
   lane, and `ENGINE_ID_PARSER.known("qwenloop")` must keep answering `EngineId.SOVEREIGNLOOP`.
3. **`tests/domain/test_engine_aliases.py`**: the one test whose assertion is the alias itself,
   `test_sovereignloop_is_the_member_and_qwenloop_its_python_alias`
   (`EngineId.QWENLOOP is EngineId.SOVEREIGNLOOP`, `"QWENLOOP" in EngineId.__members__`), is
   **replaced** by a test proving the alias is gone while `_missing_` still resolves the text:
   ```python
   def test_qwenloop_is_no_longer_a_python_alias_but_the_text_still_resolves():
       assert "QWENLOOP" not in EngineId.__members__
       assert not hasattr(EngineId, "QWENLOOP")
       assert EngineId("qwenloop") is EngineId.SOVEREIGNLOOP
       assert list(EngineId).count(EngineId.SOVEREIGNLOOP) == 1
   ```
   Every other test in that file (the alias-table tests, the ledger-record test, the
   `ActorResolver` test) is unedited: they all assert behaviour of `ENGINE_ID_ALIASES` and
   `_missing_`, which this lane does not touch.
4. Nothing else changes. Behaviour for every stored spelling, every `known()`/`parse()` call and
   the ledger chain is byte-identical to before this lane: only the Python attribute
   `EngineId.QWENLOOP` stops existing.

## Where to change
- `src/vibey/domain/engine.py` (`edit_file` only; well over 100 lines): the two-line deletion of
  behaviour 2. `old_string` is the comment line and the member line together (copied exactly from
  `read_file`); `new_string` is empty (delete both lines, including their trailing newline, so
  `SOVEREIGNLOOP = "sovereignloop"` is immediately followed by whatever member came after
  `QWENLOOP` before this lane, with no blank line left behind).
- `tests/domain/test_engine_aliases.py` (`edit_file` only): replace exactly the one test named in
  behaviour 3, by its function name and body, with the new one. Every other test in the file is
  untouched.
- Before touching anything, run the grep of behaviour 1 and follow its stop rule.
- No new file. No fake changes: `EngineId` needs no fake (it is a value, not a driven seam).

## Acceptance criteria
- [ ] `grep -n "QWENLOOP" src/vibey/domain/engine.py` prints nothing (the member and its comment
      are both gone; `ENGINE_ID_ALIASES`'s key `"qwenloop"` is a string, not the token `QWENLOOP`,
      so this grep is exact).
- [ ] `python3 -c "from vibey.domain.engine import EngineId; assert not hasattr(EngineId,
      'QWENLOOP'); assert EngineId('qwenloop') is EngineId.SOVEREIGNLOOP"` (run through `uv run`)
      exits 0.
- [ ] Every other test in `tests/domain/test_engine_aliases.py` passes unedited
      (`git diff --stat HEAD -- tests/domain/test_engine_aliases.py` shows only the one function's
      body changed, never a line count larger than that one replacement).
- [ ] `grep -rn "EngineId\.QWENLOOP" src/vibey src/vibey_runners src/vibey_tools tests` prints
      nothing anywhere in `src/vibey` outside the (now-removed) two lines, and nothing anywhere in
      `tests` outside the one replaced test.
- [ ] The whole default tier passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
This lane replaces one existing test rather than adding new ones (behaviour 3); write the
replacement test first, watch it fail against the pre-removal source (`EngineId.QWENLOOP` still
resolves, so `not hasattr(EngineId, "QWENLOOP")` fails), then make it pass by deleting the alias.
- `test_qwenloop_is_no_longer_a_python_alias_but_the_text_still_resolves`: the exact body of
  behaviour 3.
- Confirm, without editing them, that these existing tests in the same file still pass unchanged
  after the removal: `test_the_legacy_spelling_constructs_the_current_member`,
  `test_an_unknown_value_is_still_refused`, `test_known_resolves_the_alias_and_parse_keeps_the_text`,
  `test_the_legacy_text_is_not_a_member_value`,
  `test_every_alias_names_a_member_and_is_not_itself_a_member_value`,
  `test_the_alias_table_is_read_only`, `test_a_parser_without_aliases_resolves_nothing_extra`,
  `test_the_ledger_actor_resolver_finds_legacy_engine_text`,
  `test_a_ledger_record_keeps_a_legacy_engine_spelling_verbatim`,
  `test_a_ledger_record_still_refuses_an_unknown_engine`.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/engine.py tests/domain/test_engine_aliases.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_engine_aliases.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    grep -n "QWENLOOP" src/vibey/domain/engine.py
    grep -rn "EngineId\.QWENLOOP" src/vibey src/vibey_runners src/vibey_tools tests
    git diff --stat HEAD -- tests/domain/test_engine_aliases.py

The two `grep` lines above must print nothing outside what the acceptance criteria describe.

## Out of scope
- `ENGINE_ID_ALIASES`, `_missing_`, `ENGINE_ID_PARSER` and every stored `"qwenloop"` string: all
  kept forever (ADR-0046 §7, Migration table).
- Fixing any straggler live reference the grep of behaviour 1 finds: report it, do not fix it here.
- `EngineId.CLAUDELOOP_LOCAL`'s tier or pool membership, the CRD enum, the chart, the tenant
  console script `qwenloop`, and every other spelling in the Migration table that this lane's grep
  does not name (they each have their own kept-forever alias and their own lane).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-doctor-legacy-spellings`, `loops-chart-sovereignloop-names`, `loops-cli-provider-name`.

## Hard repository rules (always)
- `domain/` stays pure: no I/O, no async, no clock, no network. Enforced by `tests/domain/test_domain_purity.py`, which walks the AST.
- Dependencies point inward only: `domain -> application -> infrastructure -> cli`, enforced by `import-linter` (`uv run lint-imports`).
- `CreditsExhausted` never has a `resets_at` field. A capacity rejection always outranks a completion claim.
- Code lives in classes, and every class gets an interface declared beside it (ADR-0016, sub-doctrine 9.b): `pkg/x.py` implies `pkg/interfaces/x_interface.py` (or an entry in an existing `interfaces/` module in the same package). A module-level function is the method of last resort, and needs a written reason at its definition. Interfaces declare; they never consume, and no Protocol is declared outside a package named `interfaces`.
- Every job is idempotent under replay; the ledger is append-only (no updates, no deletes; a correction is a new event that supersedes the prior one).
- `write_file` REPLACES the whole file. Never use it on a file that already exists unless the complete content with the change applied is written back. Every line not meant to change must still be there. For any existing file longer than 100 lines, do not use `write_file` at all.
- Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one occurrence and reports when the text is missing or not unique. Only if `edit_file` cannot express a change, use a checked replacement through the `shell` tool, and the `shell` tool takes an **argv list**, never a shell string: a shell here-document that redirects a block of text into a command never works this way and must never be written. For any one-off script, write it with `write_file` to `.qwenstorm/<name>.py`, then run it as `["python3", ".qwenstorm/<name>.py"]`. To append to an existing file, use `edit_file` with `old_string` equal to the file's exact last few lines. Copy `old_string` exactly, including indentation; if a checked assert fails, read the file again and fix the string; never fall back to rewriting the whole file.
- Add tests by appending to an existing test file (read it, append, write the whole file back with everything before the addition unchanged) or by creating a new test file. Never rewrite an existing test file's prior content beyond the one change this spec names.
- Every source file begins with the provenance header line `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`. Keep it on every file touched, and put it on every file created (copy it from a neighbour file in the same package, byte for byte).
- Only edit the files named under "Where to change" and the tests named under "Tests to write first". If another file seems like it must change, say so in the verdict instead of editing it.
- After each change, run the focused tests named in this spec. If a test not meant to be affected fails, undo the change with a targeted replacement and try again rather than pushing forward.
- Before the final verdict, run `git diff --stat` and confirm no file lost lines that were not meant to be removed.
- Tests substitute only at declared seams: constructor injection, keyword injection, or a named fixture. Never `monkeypatch.setattr` on an import, a module attribute or a class attribute; never `mock.patch`; never a bare `MagicMock` or `AsyncMock` standing in for a port. A fake is a plain class with real in-memory behaviour for every method it implements; no method body is only `...`, only `pass`, only `return None`, or only `raise NotImplementedError`.
- Persistence goes only through the ORM seams declared in the `orm-*.md` specs in this same directory. No raw `asyncpg` SQL, no `text()`, no `exec_driver_sql()` and no SQL string literal in a loops lane.
- No failure-text string a lane writes may trail off with an ellipsis character: write every failure message out in full, to its last word.
- Do not edit `CHANGELOG.md`, anything under `docs/`, any ADR, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` or a skill tree (the docs wave owns those). Do not push, open a pull request, or change a git remote. Commit locally, with the Title as the Conventional Commit subject.
- Protected tests are never edited, under any circumstance: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`. They must keep passing.
