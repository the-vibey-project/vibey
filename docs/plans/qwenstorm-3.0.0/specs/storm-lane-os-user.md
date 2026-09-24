## Title
feat(storm): run every lane as a separate low-privilege OS user

## Why
Lanes run as the operator's uid, so a lane's commands can write every file the storm trusts:
`queue.txt`, `integrated.txt`, `abandoned.txt`, `progress.log` and the priority log. The
priority lane (ADR-0054, `tools/storm_queue.py` `Authority`) checks that a caller runs as the
account that owns `queue.txt`, and refuses a caller carrying `VIBEY_STORM_LANE`, which
`tools/lane_environment.py` `LaneEnvironment.build` exports into every lane command. A process
running as the same uid can unset that variable or append to the ledgers directly, so today
that check is defence in depth, not containment, and the tools say so. Sub-doctrine 12.j
(outside text is contained at the seam it enters) and 12.d (unattended authority is bounded by
a gate) both want the boundary to be one the lane cannot remove: an OS permission.

## Required behaviour
1. A dedicated OS account (declared in `storm.toml` as `[lane] user`, never a literal; 12.h)
   runs every lane attempt. `qwenlane.py` starts the attempt child as that user; nothing else
   in the lane's process tree runs as the operator.
2. The lane user can write its own lane worktree and nothing else the storm owns. The storm
   root, `queue.txt`, the ledgers, `progress.log`, the priority log and `tools/` are owned by
   the operator and are not writable by the lane user.
3. `storm_queue.Authority` keeps its uid check. With (1) and (2) in place, a lane process fails
   that check because its uid is not the owner's, whatever its environment says, and the
   marker becomes a second line rather than the only one.
4. If `[lane] user` is not declared, or the account cannot be switched to, the lane is refused
   with a result.json saying why. It never falls back to running as the operator.
5. The watchdog (`lane_watchdog.py`) can still signal the attempt's whole process tree across
   the uid boundary, and a test shows it.

## Where to change
- `tools/qwenlane.py` (`attempt_argv`, the child start) and `tools/lane_watchdog.py`
  (`AttemptWatchdog`): start and stop the child as `[lane] user`.
- `tools/lane-setup.sh`: create the worktree owned by the lane user; leave the storm root
  owned by the operator.
- `tools/storm_paths.py`: read `[lane] user` through `declared`.
- `tools/storm_queue.py` `Authority`: update the docstring's "what this does not do" once
  the boundary exists. The check itself does not change.
- Each new class gets an interface in `tools/interfaces/` (ADR-0016).

## Acceptance criteria
- [ ] A lane attempt's processes run as `[lane] user` (test: the child reports `os.getuid()`).
- [ ] A lane process cannot append to `queue.txt`, the ledgers or the priority log
      (test: the write fails with PermissionError).
- [ ] `storm-priority.py push` run as the lane user exits 1 and is recorded as refused.
- [ ] With no `[lane] user` declared the lane is refused, never run as the operator.
- [ ] `tests/meta/test_storm_priority.py` and `tests/meta/test_storm_lane_watchdog.py` pass.

## Tests to write first (TDD)
- `tests/meta/test_storm_lane_user.py`: the uid of the attempt child; a denied write to each
  storm ledger; the refusal when `[lane] user` is absent; the priority CLI refusing the lane
  user. Tests that need a second OS account are skipped, with the reason given, where the
  test host has none, and CI provides one.

## Checks the lane must run (all must pass)
```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q -p no:cacheprovider tests/meta/test_storm_lane_user.py
uv run pytest -q -p no:cacheprovider tests/meta/test_storm_priority.py
uv run pytest -q -p no:cacheprovider tests/meta/test_storm_lane_watchdog.py
```

## Out of scope
The queue and priority rules (ADR-0054), admission (`storm_trust.py`), and `src/vibey`. Do
not edit CHANGELOG.md, docs/ outside this folder, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md or
skill trees. Do not push, open PRs, or change git remotes. Commit locally with a Conventional
Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.
