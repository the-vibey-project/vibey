## Title
test(vibey-gh): fit, fitloop, tidy, surfaces, rulesets, local review and yank take injected samplers, transports and openers, and the vibey-gh ratchet reaches zero

## Why
After `fakes-tenant-gh-1` and `-2`, the rest of vibey-gh's patching sits in a handful of modules:
- `test/test_fit.py` and `test_fitloop.py`:
  - `fit.sample_model` ×8 and `fit.sample_machine` ×7;
  - `fit._run` ×5, `fit.shutil.which` ×4 and `fit.subprocess.run` ×2.
  `vibey_gh/fit.py:239-241` runs `subprocess.run` itself.
- `test/test_rulesets.py`: `rs.fetch_ruleset` ×5, `create_ruleset` ×3, `update_ruleset` ×2,
  `_api` ×2 and `reconcile_one`.
- `test/test_surfaces.py`: `surfaces.invoke` ×4, and `mcp_dispatch` and `api_dispatch`.
- `test/test_tidy.py`: `tidy.subprocess` ×6.
- `test/test_local_review.py`: `local_review.urllib.request` ×9.
- `test/test_yank.py`: `yank.urllib.request` ×4.
- `test_debugging.py`, `test_conversation.py`, `test_forge_github.py` and
  `test_gh_internals.py`: a few `subprocess` sets each.

`vibey_gh/interfaces/` already declares `memory_sampler_interface.py` and
`model_sampler_interface.py`, so fit has declared sampler seams. The tests patch the
module functions anyway.

## Required behaviour
1. **fit and fitloop** take `model_sampler`, `machine_sampler` and a `CommandRunner` (`run`
   and `which`; declare it beside `GitRunnerInterface` if gh-1 did not) as constructor or
   keyword parameters, with the production defaults. Wrap the module functions in classes
   where they are touched (ADR-0016). `test/fakes.py` gains `ScriptedModelSampler`,
   `ScriptedMachineSampler` (with the sampler interfaces' shapes) and `ScriptedCommandRunner`.
2. **rulesets** routes `_api`, `fetch_ruleset`, `create_ruleset` and `update_ruleset` through a
   `ForgeTransportInterface` it is given (`ScriptedGhTransport` in tests).
3. **surfaces** takes its dispatch table (`invoke`, `mcp_dispatch`, `api_dispatch`) as an
   injected mapping, with the production default.
4. **tidy, debugging, conversation, forge_github and gh_internals**: every `subprocess` set
   becomes an injected `GitRunnerInterface`, `GhTransportInterface` or `CommandRunner`.
5. **local_review and yank** take `opener: UrlOpener = urllib.request.urlopen`, declared in
   `vibey_gh/interfaces/url_opener_interface.py`, and tests use `InMemoryUrlOpener`
   (`test/fakes.py`). The `network`-marked tests (`VIBEY_GH_NETWORK_TESTS=1`,
   `test/conftest.py:24-41`) stay as they are: they are the opt-in real-service tier. Every
   branch they touch must also be reached offline, as `pyproject.toml:77-80` requires.
6. **The ratchet reaches zero.** `test/patching_baseline.json` is `{}`, apart from any entry
   carrying a written reason. `monkeypatch.setenv` and `delenv`, including `conftest.py`'s
   autouse `_no_ambient_actions_env`, are the environment seam and are not counted.

## Where to change
- `vibey_gh/fit.py`, `fitloop.py`, `rulesets.py`, `surfaces.py`, `tidy.py`, `debugging.py`, `conversation.py`, `forge_github.py`, `local_review.py`, `yank.py` (injection only), and any interface files added.
- `test/fakes.py`, `test/test_fakes.py`, `test/test_port_parity.py`, `test/patching_baseline.json`, and the listed test modules.

## Acceptance criteria
- [ ] `python -c "import json; print(json.load(open('src/vibey_tools/gh/test/patching_baseline.json')))"` prints `{}`, or only entries with a `reason`.
- [ ] `(cd src/vibey_tools/gh && python -m pytest -q)` passes at 100%, offline.
- [ ] black, isort and mypy pass. The drift check passes.

## Tests to write first (TDD)
`test/test_fakes.py` (appended):
- `test_model_and_machine_samplers_script_readings`
- `test_command_runner_scripts_which_and_run`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The hook templates. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-gh-2`.
- **Files touched:** see *Where to change*. If this lane proves too large in practice, split
  it at the numbered behaviours (1–2, then 3–5) and keep the ratchet honest in each half.
- **Must keep passing unchanged:** the `network` tier (opt-in), and the protected root tests.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
