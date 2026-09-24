## Title
feat(engines): the vscode and vscode-paid engine ids, one per loop

ADR-0046 lane L20b (slug `loops-vscode-engine-ids`).

## Why
Sub-doctrine 8.b (amended by #392) puts "VS Code when its provider is local" in
`sovereignloop` and "VS Code on a paid provider" in `paidloop`. ADR-0046 §1 and §8
(`specs/ADR-two-loops.md:108-116`, `:274-278`) turn that into two engine ids that share one
runner: **`vscode`** (tier LOCAL, so sovereignloop) and **`vscode-paid`** (tier PAID, so
paidloop, declared-only). "Sovereignty follows the model and the tool" (§1): the same harness
on a paid provider is a different adapter.

Every engine id must have a descriptor, a capacity classifier, conformance fixtures, an
event map, a CRD enum entry and argv goldens, or the existing suite fails:
- `tests/infrastructure/engines/test_descriptors.py:39-42` asserts `set(ids) == set(EngineId)`
  over `ALL_DESCRIPTORS`;
- `tests/infrastructure/engines/test_classify.py:24-54` parametrizes over `list(EngineId)`;
- `tests/infrastructure/engines/test_loop_events.py:389-422` parametrizes over `list(EngineId)`;
- `tests/infrastructure/engines/test_argv.py:31-45` needs one golden per descriptor × effort;
- `tests/meta/test_crd_engine_enum.py:21-24` binds the CRD enum to `EngineId`.
(All at integration `d3b4a388`.)

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **`EngineId`** (`src/vibey/domain/engine.py`, the `class EngineId(StrEnum)` block) gains,
   after `CLAUDELOOP_LOCAL`:
   ```python
   # Code - OSS (VSCodium) driven by the vscodeloop runner on a local model: a
   # sovereignloop adapter (ADR-0046 §8, sub-doctrine 8.b).
   VSCODE = "vscode"
   # The same runner on a paid provider: a paidloop adapter, declared-only.
   VSCODE_PAID = "vscode-paid"
   ```
2. **Descriptors** (`src/vibey/infrastructure/engines/descriptors.py`), after the
   `ClaudeloopLocalDescriptors`/`CLAUDELOOP_LOCAL` block:
   ```python
   VSCODE = EngineDescriptor(
       engine_id=EngineId.VSCODE,
       binary="vscodeloop",
       min_version="0.1.0",
       state_dir=".vscodeloop",
       done_marker="VSCODELOOP_TASK_FULLY_COMPLETE",
       auth_env=(),
       capabilities=frozenset({Capability.MID_RUN_PROMPT, Capability.SNAPSHOT}),
       effort_projection={
           Effort.TRIVIAL: EngineInvocation(("--max-turns", "8"), achieved=Effort.TRIVIAL),
           Effort.LOW: EngineInvocation(("--max-turns", "16"), achieved=Effort.LOW),
           Effort.STANDARD: EngineInvocation(("--max-turns", "40"), achieved=Effort.STANDARD),
           Effort.HIGH: EngineInvocation(("--max-turns", "64"), achieved=Effort.HIGH),
           Effort.MAX: EngineInvocation(("--max-turns", "96"), achieved=Effort.MAX),
       },
       session_verb="sessions",
       resume_run_id_flag="--run-id",
       isolation_flags={
           IsolationLevel.WORKTREE: (),
           IsolationLevel.CONTAINER: (),
           IsolationLevel.VM: (),
       },
       cost_per_mtok_in=0.0,
       cost_per_mtok_out=0.0,
       context_window=32_768,
       base_weight=1,
       tier=EngineTier.LOCAL,
   )

   VSCODE_PAID = replace(
       VSCODE,
       engine_id=EngineId.VSCODE_PAID,
       effort_projection={
           effort: EngineInvocation(("--paid", *invocation.argv), achieved=invocation.achieved)
           for effort, invocation in VSCODE.effort_projection.items()
       },
       # A paid provider's price is the provider's; it is metered from the run's own
       # usage events, never invented here (the OpenCode precedent, above).
       tier=EngineTier.PAID,
       doctor_args=("--paid",),
   )

   # The IDE adapters: neither is in DEFAULT_DESCRIPTORS. `vscode` joins the always-on
   # pool in lane loops-vscode-vibey-wiring; `vscode-paid` is declared-only (8.b).
   IDE_DESCRIPTORS: tuple[EngineDescriptor, ...] = (VSCODE, VSCODE_PAID)
   ```
   `ALL_DESCRIPTORS` becomes `(*DEFAULT_DESCRIPTORS, *LOCAL_DESCRIPTORS, *IDE_DESCRIPTORS)`.
   The module does not import `replace` at `d3b4a388` (its imports start at `:31`): add
   `from dataclasses import replace` as the first import line, above `:31`. The copied effort projection keeps the
   sovereign runner's `--max-turns` ladder (the 40-turn default is qwenloop's,
   `specs/opencodeloop-parity-p1.md` behaviour 5).
3. **Classifier and fixtures** (`src/vibey/infrastructure/engines/classify.py`): the
   vscodeloop runner writes the family `capacity` shape (lane `loops-vscodeloop-runner`), so
   both ids read through `_classify_claudeloop`, which already reads the mapping and the
   class-name forms (`_CLAUDELOOP_CAPACITY_NAMES` at `:59-65`, the function at `:70`). Add to `_CLASSIFIERS` (`:216-224`):
   `EngineId.VSCODE: _classify_claudeloop, EngineId.VSCODE_PAID: _classify_claudeloop,`.
   Add fixtures, copying existing shapes exactly:
   - `CREDITS_FIXTURES`: `VSCODE` = the `CLAUDELOOP_LOCAL` entry (`{"capacity": "CreditsExhausted"}`);
     `VSCODE_PAID` = the `CLAUDELOOP` entry (`{"capacity": {"state": "credits_exhausted", "can_purchase": True}}`).
   - `WINDOW_FIXTURES`: `VSCODE` = the `CLAUDELOOP_LOCAL` entry (window, `rate_limit_type` `local`);
     `VSCODE_PAID` = the `CLAUDELOOP` entry.
   - `AUTH_FIXTURES`: `VSCODE` = `{"capacity": "BackendMisconfigured"}`; `VSCODE_PAID` = the `CLAUDELOOP` entry.
   - `AVAILABLE_FIXTURES`: `VSCODE` = `{"capacity": "Available"}`; `VSCODE_PAID` = `{}`.
   Add a comment above the two `_CLASSIFIERS` lines: "vscodeloop writes the family capacity
   shape claudeloop does (lane loops-vscodeloop-runner); a local provider never reports
   credits, and the fixture exists only for the shared conformance check".
4. **Event map** (`src/vibey/infrastructure/engines/loop_events.py`), inside `LOOP_EVENT_MAP`:
   ```python
   EngineId.VSCODE: {
       "run.started": EventKind.SESSION_SEEDED,
       "turn.starting": EventKind.TURN_REQUESTED,
       "text_delta": EventKind.TRANSCRIPT_RECORDED,
       "tool_result": EventKind.TOOL_INVOKED,
       "turn.completed": EventKind.TURN_COMPLETED,
       "capacity.rejected": EventKind.CAPACITY_REJECTED,
       "finished": EventKind.VERDICT_RENDERED,
       "failed": EventKind.VERDICT_RENDERED,
   },
   ```
   and after the dict, beside the claudeloop-local line (`:223`):
   `LOOP_EVENT_MAP[EngineId.VSCODE_PAID] = LOOP_EVENT_MAP[EngineId.VSCODE]` with the comment
   "one runner, one events.jsonl vocabulary, one map".
5. **CRD** (`deploy/helm/vibey/templates/crd-vibeyproject.yaml`, the `spec.engines` `enum`
   line, `:78` at `d3b4a388`): append `vscode, vscode-paid` inside the brackets. The binding
   test is unchanged (it already compares against `EngineId` members plus aliases).
6. **The loop-events test tables** (`tests/infrastructure/engines/test_loop_events.py`) state
   the whole map engine by engine on purpose ("a new entry … should have to change this table
   in the same diff", `:304-307` at `d3b4a388`). Add, in this diff:
   - to `_EXPECTED_MAPS` (`:308-375`): `EngineId.VSCODE` and `EngineId.VSCODE_PAID`, each with
     exactly the eight entries of behaviour 4;
   - to `_TURN_BOUNDARIES` (`:393-401`): `EngineId.VSCODE: frozenset({"turn.completed"})` and
     `EngineId.VSCODE_PAID: frozenset({"turn.completed"})`.
   These are the only edits to existing tests.
7. **Argv goldens**: ten new files in `tests/infrastructure/engines/golden/`, each one line,
   no trailing text beyond the newline. For `vscode_<effort>.txt` with `<effort>` in
   `trivial low standard high max` and turns `8 16 40 64 96` respectively:
   ```
   vscodeloop run /repo/.vibey/worktrees/c1-item-001/.vibey/plans/00000000-0000-0000-0000-000000000001.md --run-id 00000000-0000-0000-0000-000000000001 --max-turns <turns> --cwd /repo/.vibey/worktrees/c1-item-001
   ```
   and `vscode-paid_<effort>.txt`:
   ```
   vscodeloop run /repo/.vibey/worktrees/c1-item-001/.vibey/plans/00000000-0000-0000-0000-000000000001.md --run-id 00000000-0000-0000-0000-000000000001 --paid --max-turns <turns> --cwd /repo/.vibey/worktrees/c1-item-001
   ```
   (the test builds them with `shlex.join(build_argv(descriptor, _spec(effort)))`,
   `test_argv.py:14-38`; generate them with a two-line Python loop over the same call rather
   than typing them, then read one back to confirm.)

## Where to change
- `src/vibey/domain/engine.py` (edit_file).
- `src/vibey/infrastructure/engines/descriptors.py` (edit_file; >100 lines).
- `src/vibey/infrastructure/engines/classify.py` (edit_file).
- `src/vibey/infrastructure/engines/loop_events.py` (edit_file).
- `deploy/helm/vibey/templates/crd-vibeyproject.yaml` (one line).
- New: the ten golden files; `tests/infrastructure/engines/test_vscode_descriptors.py`.
- `tests/infrastructure/engines/test_loop_events.py`: the two table additions only (behaviour 6).
- Line 1 of the new test file is the provenance comment copied from line 1 of
  `tests/infrastructure/engines/test_descriptors.py`.

## Acceptance criteria
- [ ] `EngineId("vscode") is EngineId.VSCODE` and `EngineId("vscode-paid") is EngineId.VSCODE_PAID`.
- [ ] `BY_ENGINE_ID[EngineId.VSCODE].tier is EngineTier.LOCAL`; `BY_ENGINE_ID[EngineId.VSCODE_PAID].tier is EngineTier.PAID`; neither is in `DEFAULT_DESCRIPTORS`.
- [ ] `classify_capacity(EngineId.VSCODE, CREDITS_FIXTURES[EngineId.VSCODE])` is a `CreditsExhausted` with no `resets_at` attribute (the type has none).
- [ ] The existing descriptor, classify, argv and CRD tests pass with no edits; the loop-events test passes with only the table additions of behaviour 6.
- [ ] 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_vscode_descriptors.py` (module-level test functions,
pure objects only):
- `test_vscode_is_a_sovereign_adapter_on_the_vscodeloop_runner`: binary `vscodeloop`,
  state_dir `.vscodeloop`, marker `VSCODELOOP_TASK_FULLY_COMPLETE`, tier LOCAL, cost 0/0,
  `auth_env == ()`.
- `test_vscode_paid_is_the_same_runner_on_the_paid_side`: same binary/state_dir/marker,
  tier PAID, `doctor_args == ("--paid",)`, and every effort's argv starts with `"--paid"`.
- `test_vscode_effort_ladder_is_the_sovereign_turn_ladder`: argv `("--max-turns", n)` for
  n = 8, 16, 40, 64, 96 and `achieved is effort` at every level.
- `test_neither_ide_adapter_is_in_the_default_pool`: not in `DEFAULT_DESCRIPTORS`; both in
  `IDE_DESCRIPTORS` and `ALL_DESCRIPTORS`.
- `test_ide_adapters_share_one_event_map`: `LOOP_EVENT_MAP[EngineId.VSCODE_PAID] is LOOP_EVENT_MAP[EngineId.VSCODE]`
  and it maps `capacity.rejected` to `EventKind.CAPACITY_REJECTED`.
- `test_ide_adapters_classify_the_family_capacity_shape`: each of the four fixture maps
  classifies to `CreditsExhausted`, `WindowExhausted`, `AuthenticationFailed`, `Available`
  for both ids.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/meta/test_crd_engine_enum.py tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The `vscodeloop` runner itself (lanes `loops-vscodeloop-*`) and `[engines.vscode_paid]`
  configuration (`loops-vscode-paid-config`).
- Putting `vscode` in any pool, or the endpoint overlay (`loops-vscode-vibey-wiring`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscode-spike`, `loops-claudeloop-local-paid`, `loops-drop-qwenloop-alias`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
