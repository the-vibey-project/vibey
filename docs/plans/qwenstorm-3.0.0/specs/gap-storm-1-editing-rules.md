## Title
feat(qwenloop): every storm plan carries the lane editing rules, shipped with the runner

## Why
A small local model given only whole-file writes tends to "add a test" by writing the test and
deleting the rest of the file. The QwenStorm learned the countermeasure the hard way and keeps
it outside the family: `STORM/EDITING-RULES.md` (seven rules) is appended to every lane's item
body by a script (`STORM/qwenlane.py:79-80`). The in-tree storm, `qwenloop run --storm`, sends
its plans without them (`src/vibey_runners/qwen/src/qwenloop/application/storm.py:97-139`,
`build_plan`), although qwenloop already has the tools the rules name: `edit_file` and the
`write_file` shrink refusal (`src/qwenloop/infrastructure/tools.py:21-33`, `:104-117`).

10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) says the family runs the delivery tooling it
ships; this lane moves the generic rules into the runner, as a prompt asset every storm plan
carries. Rule 4 of the storm copy (vibey's provenance header) is repository-specific and stays
out: the repository's own grounding already travels in the plan. This is a child of
`gap-spike-storm-command` that is exact without the spike's decisions.

## Required behaviour
1. `src/vibey_runners/qwen/src/qwenloop/application/storm.py` gains, after `_CDD_PROTOCOL`
   (`:14-67`), the public constant `LANE_EDITING_RULES: str`, exactly this text (a
   triple-quoted string, ending with a newline):
   ```
   ## Lane editing rules (read before changing any file)
   1. `write_file` REPLACES the whole file. Never use it on a file that already exists unless
      you write back its complete content with your change applied. Every line you do not mean
      to change must still be there. For any existing file longer than 100 lines, do not use
      `write_file` at all.
   2. Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly
      from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one
      occurrence and tells you if the text is missing or not unique. `write_file` refuses to
      shrink a long existing file. Only if `edit_file` cannot express a change, use a checked
      replacement through the `shell` tool (an argv list, not a shell string) that asserts the
      old text occurs exactly once before replacing it. If the assertion fails, read the file
      again and fix the old text; never fall back to rewriting the file.
   3. Add tests by APPENDING to the existing test file, or by creating a new test file. Never
      rewrite an existing test file.
   4. Only edit the files the item names. If you believe another file must change, say so in
      your verdict instead.
   5. After each change, run the focused tests. If a test you did not mean to affect fails,
      undo your change with a targeted replacement and try again.
   6. Before your final verdict, run `git diff --stat` and confirm no file lost lines you did
      not mean to remove.
   ```
2. `build_plan` gains the keyword parameter `editing_rules: str = LANE_EDITING_RULES`, and its
   returned text places `f"{editing_rules}\n"` immediately after `f"{_CDD_PROTOCOL}\n"` (`:128`)
   and before `"### Repository grounding"`. An empty `editing_rules` omits the section
   entirely (no blank heading).
3. `build_item_plans` gains the same keyword parameter and passes it to every `build_plan` call
   (`:161`, `:175`, `:188`), so a caller can replace the asset in one place.
4. `build_plan` and `build_item_plans` stay module functions. Each gets the written reason 9.b
   (`doctrines.md:349`) asks for, as a comment at the definition: "a module function because
   `qwenloop.cli.app` and the storm driver import it by name; it converges into a class with the
   storm command (gap-spike-storm-command)".
5. Nothing else changes: `qwenloop.cli.app._run_storm` (`app.py:373-474`) calls
   `build_item_plans` without the new keyword and so gets the rules.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/application/storm.py` (edit_file; 197 lines).
- `src/vibey_runners/qwen/tests/test_storm.py` (append the tests below; never rewrite it).
- If `src/vibey_runners/qwen` does not exist because lane `loops-rename` has already renamed the
  tenant, stop and report it instead of guessing the new paths.

## Acceptance criteria
- [ ] Every storm plan contains `## Lane editing rules (read before changing any file)` exactly
      once, after the CDD section and before `### Repository grounding`.
- [ ] Every existing test in `tests/test_storm.py` and `tests/test_cli.py` passes unchanged.
- [ ] The tenant's floor holds: `python -m pytest -q` reports 100% branch coverage of `qwenloop`.

## Tests to write first (TDD)
Append to `src/vibey_runners/qwen/tests/test_storm.py`:
- `test_build_plan_carries_the_lane_editing_rules_once` -- `plan.count("## Lane editing rules") == 1`.
- `test_the_rules_sit_between_cdd_and_grounding` -- the index of the rules heading is greater than that of `## Convergence-Driven Development (CDD)` and less than that of `### Repository grounding`.
- `test_the_rules_name_the_runner_tools` -- `"edit_file" in LANE_EDITING_RULES` and `"write_file" in LANE_EDITING_RULES`.
- `test_the_rules_are_not_repository_specific` -- `"Made with" not in LANE_EDITING_RULES` and `"src/vibey" not in LANE_EDITING_RULES`.
- `test_a_caller_can_replace_or_drop_the_rules` -- `editing_rules="## Custom\n"` puts `## Custom` in the plan and no default heading; `editing_rules=""` leaves no `## Lane editing rules`.
- `test_every_item_plan_carries_the_rules` -- over `build_item_plans` with two issues and one PR.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen && pip install -e ".[dev]"
    cd src/vibey_runners/qwen && mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
    cd src/vibey_runners/qwen && python -m pytest -q
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- A configuration key or file for custom rules (the spike's ADR decides where storm settings
  live); the gutted-file guard (`gap-storm-2-gutted-file-guard`); `STORM/*` scripts.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(qwenloop): every storm plan carries the lane editing rules`. Do not push.

## Lane card
- **Depends on:** none (the tools it names, `qwenloop-edit-tool`, are integrated).
- **Standing constraints:** the tenant's own gates on its floor (ADR-0022); tenants never
  import `vibey`; provenance line 1 on every file touched.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
