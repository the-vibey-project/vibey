## Title
feat(build): every build.verify attempt records its CDD distance and trajectory in the ledger

## Why
CDD (CLAUDE.md non-negotiable; ADR-0039 `:98-116`; sub-doctrine 9.c) requires every iteration
to classify its trajectory. It also requires the "trajectory classification" in the minimum
completion record. The BUILD loop's iteration is a `build.verify` attempt: gates, then an
independent diff review, then either integrate or a bounded repair round
(`src/vibey/application/build_verify_handler.py:193-332`, repair at `:401-472`). It records
findings, but no distance and no trajectory (`issue-audit/gaps.md` N7, lines 757-763).
`gap-cdd-distance` added `CddDistance`, `TrajectoryClassifier` and
`EventKind.TRAJECTORY_RECORDED`.

## Required behaviour
1. `BuildVerifyHandler.__init__` (`build_verify_handler.py:163-191`) gains the keyword
   `trajectories: TrajectoryClassifierInterface = TRAJECTORIES`, stored as `self._trajectories`.
   It is a declared seam, never patched.
2. A new private method
   `async def _record_trajectory(self, job: JobRecord, item_id: str, current: CddDistance) -> None`:
   - `previous`: when `self._repair` is not None, the payload of the **last**
     `EventKind.TRAJECTORY_RECORDED` event whose `cycle == job.cycle` and
     `payload["work_item_id"] == item_id`, read through
     `self._repair.ledger_reader.all_for_project(job.project_id)` exactly as
     `_verify_findings` does (`:382-399`), decoded with
     `CddDistance.from_payload(payload["distance"])`. Otherwise it is `None`.
   - `trajectory = self._trajectories.classify(previous, current)`.
   - It writes one event through `self._ledger.record(...)`, shaped like the `FINDING_RAISED`
     write at `:437-450`: `engine_id=None`, `EngineEvent(kind=EventKind.TRAJECTORY_RECORDED.value, at=<clock now>, payload=...)`.
     The payload is:
     `{"work_item_id": item_id, "scope": "item", "distance": current.to_payload(), "known_total": current.known_total, "unknowns": current.unknowns, "previous": previous.to_payload() if previous else None, "trajectory": trajectory.value}`.
     The clock is `self._clock`.
3. Where the distance is measured. Here `n_criteria = len(criteria_checked)`, read the same
   way as `:219-221`, and `commands` is today's list.
   - **A gate fails** at index `i` (`:212-217`), before the repair or failure return. The
     distance is
     `CddDistance(unverified_criteria=n_criteria, failing_checks=1, unresolved_blockers=<open>, unrelated_changes=None)`.
     Checks after index `i` did not run, so they add nothing. The distance stays honest
     because `unverified_criteria` still counts every criterion.
   - **The review completes without approving** (`:264-278`, the two `Failure` returns after
     `misconfiguration_gate`). The distance is `CddDistance(n_criteria, 0, <open>, None)`.
   - **The review approves** (just before the `build.integrate` enqueue at `:292`). The
     distance is `CddDistance(0, 0, 0, None)`, recorded after `_resolve_open_findings`.
   - `<open>` is `len(open_findings)` from `self._verify_findings(job, item_id, self._repair)`
     when `self._repair` is not None, and `None` when it is None.
   - `unrelated_changes` is always `None`. vibey does not yet measure it, and ADR-0039 says
     unknown stays unknown.
4. **Nothing is recorded** on these paths:
   - a wrong kind or missing item;
   - "verifier must differ";
   - "no acceptance criteria checked" (`:222-227`), because the item has no criteria to measure;
   - a capacity rejection (`:244-262`): a capacity rejection outranks a completion claim, and
     no iteration took place;
   - a misconfiguration park (`:266-271`).
5. The ledger write is best-effort toward the outcome: the handler's `Outcome` for each path
   is exactly today's. The recording happens before the return on the same path, so a replay
   of the job writes one more trajectory event. That is correct append-only history (7.c),
   and it is idempotent in effect because the classifier then reads the replayed distance as
   the previous one and gives `NEUTRAL`.

## Where to change
- `src/vibey/application/build_verify_handler.py` (505 lines): edit_file only.
- Tests: append to `tests/application/test_build_verify_handler.py`, using the in-memory
  fakes that `fakes-build` puts in that file (`InMemoryWorktrees`, `build_ledger(InMemoryLedger())`
  from `tests/fakes/`). Read the file's fixture helpers first. Use no `monkeypatch.setattr`
  and no `mock`.
- No new interface. The seam is `TrajectoryClassifierInterface` from `gap-cdd-distance`.

## Acceptance criteria
- [ ] A failing gate with two criteria, repair wired and no open findings writes one
      `TrajectoryRecorded` with `distance == {"unverified_criteria": 2, "failing_checks": 1, "unresolved_blockers": 0, "unrelated_changes": None}`,
      `previous is None` and `trajectory == "neutral"`. The outcome is today's `Defer`.
- [ ] A second verify of the same item after the repair, now approved, writes
      `distance == {0, 0, 0, None}` with `previous` equal to the first distance and
      `trajectory == "converging"`, then enqueues `build.integrate` as today.
- [ ] A review that completes without approval, after an approved attempt in the same cycle,
      writes `trajectory == "diverging"`.
- [ ] Without a repair policy, `unresolved_blockers` is `None` and `previous` is `None`.
- [ ] A capacity-rejected review writes no `TrajectoryRecorded`, and the outcome is today's
      `Defer(capacity=True)`.
- [ ] An injected classifier (a test class implementing `TrajectoryClassifierInterface` that
      always returns `DIVERGING`) is the one used.
- [ ] Every existing test in `tests/application/test_build_verify_handler.py` passes
      unchanged. 100% branch coverage of `src/vibey/application/*`.

## Tests to write first (TDD)
Append to `tests/application/test_build_verify_handler.py`:
- `test_a_failing_gate_records_a_neutral_first_trajectory`
- `test_an_approved_repair_records_a_converging_trajectory`
- `test_a_rejected_review_after_approval_records_diverging`
- `test_without_a_repair_policy_blockers_and_previous_are_unknown`
- `test_a_capacity_rejection_records_no_trajectory`
- `test_the_classifier_is_an_injected_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_build_verify_handler.py tests/domain/test_cdd.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Other scopes (project, phase, epic) and other phases' iterations.
- Parking on repeated divergence (a follow-up; the repair bound at `:414-433` still bounds the loop).
- Measuring `unrelated_changes` from the worktree diff (a follow-up).
- Publication rules for the new kind; it stays withheld by default.
- Docs.

Commit as `feat(build): every verify attempt records its CDD trajectory`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
