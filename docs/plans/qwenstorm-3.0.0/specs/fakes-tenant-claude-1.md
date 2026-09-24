## Title
test(claudeloop): `claudeloop run` takes its logging, config, plan parser and bootstrap from a typer-context composition, and test_run_cmd.py patches nothing

## Why
claudeloop (`src/vibey_runners/claude`) has 219 `patch` calls and 212 mocks. One file carries
the most: `tests/cli/test_run_cmd.py` (109). It patches the names that
`claudeloop/cli/commands/run.py` imports:
- `configure_logging` ×13;
- `parse_plan_file` ×12;
- `load_config` ×12;
- `bootstrap` ×12;
- `run_from_plan_file`.
Each test re-patches the whole set to reach one branch.

`tests/application/fakes.py` already has 15 fakes. `vibey-runners-common` now ships fakes for
the shared ports (`fakes-tenant-common`). This is the first of three claudeloop lanes. It
establishes the composition seam for the CLI, and converts the `run` command.

## Required behaviour
1. **`claudeloop/cli/composition.py` — `class ClaudeloopComposition`**, with an interface,
   found through `click.get_current_context(silent=True).find_object(...)`. Its fields
   default to production:
   - `configure_logging`, `load_config`, `parse_plan_file`;
   - `bootstrap`: the factory that returns the runner graph;
   - `run_from_plan_file`.
   Later lanes add more fields.
2. **`cli/commands/run.py`** reads each of those from `ClaudeloopComposition.current()`, and
   nowhere else.
3. **`tests/application/fakes.py`**:
   - delete every fake of a `vibey_runners.common` port, and import it from
     `vibey_runners.common.testing.fakes`;
   - add `ScriptedBootstrap`, which returns a runner graph assembled from the existing
     in-memory fakes, and records how it was called;
   - add `RecordingLoggingConfigurator`;
   - add an in-memory `load_config` that returns a supplied config.
   The plan parser is pure, so tests use the real `parse_plan_file` over files under
   `tmp_path`, except where a test needs a parse error. Then write the malformed file; do not
   stub the parser.
4. **Switch `tests/cli/test_run_cmd.py`** to `CliRunner().invoke(app, [...], obj=ClaudeloopComposition(...))`.
   Every `patch("claudeloop.cli.commands.run...` goes. Keep every output and exit-code
   assertion.
5. **The tenant registry and ratchet:** `tests/application/test_port_parity.py`,
   `tests/test_patching_ratchet.py`, `tests/patching_baseline.json`. `test_run_cmd.py`
   counts zero.

## Where to change
- New `src/claudeloop/cli/composition.py` and its interface under `cli/interfaces/`; `src/claudeloop/cli/commands/run.py`.
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/test_patching_ratchet.py`,
  `tests/patching_baseline.json`, `tests/cli/test_run_cmd.py`.

## Acceptance criteria
- [ ] `grep -cE "patch\(|MagicMock|monkeypatch.setattr" src/vibey_runners/claude/tests/cli/test_run_cmd.py` prints `0`.
- [ ] claudeloop's CI row passes on 3.12 (its floor): `mypy --strict`, `lint-imports`, `bandit`, the suite, and the frontmatter check.

## Tests to write first (TDD)
`tests/cli/test_composition.py`:
- `test_defaults_are_production`
- `test_context_object_is_found`
- `test_run_reads_every_collaborator_from_the_composition`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/claude && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/claude && mypy --strict src/claudeloop && lint-imports && bandit -q -r src/claudeloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `resume`, the other commands and the backend profiles (`fakes-tenant-claude-2`).
- The infrastructure gateways (`fakes-tenant-claude-3`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-common`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** claudeloop's `live` and `system` tiers (deselected by its
  `addopts`), and the protected root tests.
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

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
