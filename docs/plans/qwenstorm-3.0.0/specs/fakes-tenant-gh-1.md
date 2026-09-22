## Title
test(vibey-gh): gh and git run through declared transports with scripted fakes, and reconcile's tests patch nothing

## Why
vibey-gh (`src/vibey_tools/gh`) makes 338 `monkeypatch.setattr` calls in its suite, which is
the most of any package. Two kinds dominate:
- **The `subprocess` module itself**, set on a vibey-gh module (47 calls: 25 in
  `test/test_reconcile.py`, 11 in `test_pr_automation.py`, 5 in `test_rulesets.py`, and more).
  The source runs `gh` and `git` with `subprocess.run` in 26 modules (53 call sites): for
  example `vibey_gh/reconcile.py:143-151`, `:245` and `:349`.
- **The package's own module functions**, replaced on the module:
  - `merge_train.open_pull_requests` ×17, `merge_train.judge` ×13;
  - `pr_automation.fetch_pr` ×10;
  - `reconcile.unique_commits` and `reconcile.is_behind` ×26;
  - `fit.sample_model` and `fit.sample_machine` ×15.

The seam already half-exists. `vibey_gh/gh_transport.py` (`GhTransport`, implementing
`GhTransportInterface` and `ForgeTransportInterface`) is "one way to run `gh`". Its docstring
says the rest of the package "still runs its own and moves over one module at a time". There
is no equivalent for `git`, and no fake for either.

vibey-gh declares `dependencies = []`, and `domain/` may import it (CLAUDE.md). Fakes live in
its `test/` directory only.

## Required behaviour
1. **`vibey_gh/interfaces/git_runner_interface.py`** declares `GitRunnerInterface`, with
   `run(self, args: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]`.
   `vibey_gh/git_runner.py` holds `class SubprocessGitRunner` (with an empty environment
   overlay, and `check=False`, `capture_output`, `text`, exactly as `reconcile._git_at` does
   today), and the module constant `GIT = SubprocessGitRunner()`. Add the new interfaces
   package entry to `.importlinter`'s `vibey-gh-interfaces-declare-only` if it lists modules.
2. **`test/fakes.py`** (new):
   - `ScriptedGhTransport` implements `GhTransportInterface` and `ForgeTransportInterface`.
     It is scripted by argv prefix, where the longest prefix wins, with a
     `CompletedProcess`-shaped answer or JSON. It records `calls`. `json`, `probe` and
     `survey` follow `GhTransport`'s documented result shapes (`gh_transport.py:1-15`),
     including the exact error text on a non-zero exit;
   - `ScriptedGitRunner` implements `GitRunnerInterface`, scripted by
     `(cwd or None, args prefix)`. An unscripted command returns returncode 128 with
     `fatal: not scripted: git <args>`;
   - `InMemoryUrlOpener` is the urllib opener contract, for `local_review` and `yank`, as in
     vibey's `tests/fakes/http.py`, and local to this package.
   Each fake has behaviour tests in `test/test_fakes.py`.
3. **The tenant registry.** `test/test_port_parity.py` registers `ScriptedGhTransport` for
   both transport interfaces and `ScriptedGitRunner` for `GitRunnerInterface`. It fails on
   any Protocol in `vibey_gh/interfaces/*_interface.py` whose name ends in `Transport`,
   `Runner`, `Opener` or `Sampler` and has no registered fake. The other interfaces there
   are class contracts; list them in `EXEMPT` with that reason.
4. **The ratchet.** Add `test/test_patching_ratchet.py` and `test/patching_baseline.json`.
5. **Reconcile moves over.** `vibey_gh/reconcile.py`'s `_git_at`, `_git`, `unique_commits` and
   `is_behind`, plus the two `subprocess.run` sites at `:245` and `:349`, go through a
   `GitRunnerInterface` and a `GhTransportInterface`. Both are passed as keyword parameters
   whose defaults are `GIT` and `GhTransport()`, all the way from the public entry points the
   CLI calls. If `reconcile.py` holds module functions, convert the ones you touch into
   methods of `class Reconciler(git=GIT, gh=GhTransport())` with an interface beside it
   (ADR-0016). Keep module-level names bound to a default instance for the CLI, with a comment
   saying why. Then:
   - `test/test_reconcile.py` uses `Reconciler(git=ScriptedGitRunner(...), gh=ScriptedGhTransport(...))`;
   - the 25 `subprocess` and 26 `rc.` patches go;
   - the baseline is lowered.

## Where to change
- New `vibey_gh/interfaces/git_runner_interface.py`, `vibey_gh/git_runner.py`; `vibey_gh/reconcile.py`, its interface file if one exists (or a new one).
- New `test/fakes.py`, `test/test_fakes.py`, `test/test_port_parity.py`, `test/test_patching_ratchet.py`, `test/patching_baseline.json`; `test/test_reconcile.py`.
- `.importlinter` (one line, if needed).

## Acceptance criteria
- [ ] `grep -c "monkeypatch.setattr" src/vibey_tools/gh/test/test_reconcile.py` prints `0`.
- [ ] `(cd src/vibey_tools/gh && python -m pytest -q)` passes at its 100% floor.
- [ ] `(cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh)` passes. The `tools-lint` job runs both black and ruff format; memory trap: black vs ruff-format.
- [ ] The managed automation has no drift (`tools-lint`'s drift check).

## Tests to write first (TDD)
`test/test_fakes.py`:
- `test_gh_transport_fake_matches_the_json_error_text`
- `test_gh_transport_fake_longest_prefix_wins`
- `test_git_runner_fake_scripts_by_cwd_and_refuses_the_unscripted`
- `test_url_opener_fake_routes_and_errors`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- `merge_train`, `pr_automation` and `issue_automation` (`fakes-tenant-gh-2`).
- `fit`, `fitloop`, `tidy`, `surfaces`, `local_review`, `yank`, `rulesets` and the rest (`fakes-tenant-gh-3`).
- The byte-compared hook templates (`install.py:639`), which are never edited here.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-registry` (the pattern).
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every other vibey-gh test, the governance meta tests, and the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).
  - vibey-gh stays dependency-free.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
