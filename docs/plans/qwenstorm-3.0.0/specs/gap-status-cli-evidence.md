## Title
feat(cli): `vibey status` and `vibey watch` name the object, source and cutoff of what they show

## Why
10.f (`src/vibey_tools/gh/docs/doctrines.md:419` at integration HEAD `4317cff6`): a claim about
live operation states "evidence whose scope and cutoff are stated". ADR-0040
(`docs/architecture/decisions/0040-evidence-bounded-status.md:25-30`): a status claim names its
object, its source, and its scope and cutoff. `vibey status` (`src/vibey/cli/main.py:709-790`)
prints the project, phase, queue and circuits in text and in `--json`, and says nothing about
where they came from or when. `vibey watch` (`:594-658`) opens the TUI over the same state
(gap N6, `issue-audit/gaps.md:749-755`).

`gap-status-evidence-dashboard` builds the claim in `fetch_dashboard_state` and adds
`DashboardState.status_line`. This lane passes the composed clock as the cutoff, and prints the
claim. The clock is `resources.clock` (`AppResources.clock`, `src/vibey/bootstrap.py:155`), the
one every handler uses. The CLI never reads the wall clock itself.

## Required behaviour
Edit `src/vibey/cli/main.py` with edit_file only (the file is about 1,760 lines). The line
numbers are at `4317cff6`. Find each spot by its text, because the `fakes-cli-*` lanes may have
moved them.
1. `status` (`:729-735`, the `state = await fetch_dashboard_state(` call): add
   `observed_at=resources.clock.now(),` as its last keyword argument.
2. `status --json` (`:737-766`): add the key `"evidence": [claim.to_payload() for claim in state.evidence],`
   immediately after `"active_worktrees": list(state.active_worktrees),` (`:764`).
3. `status` text (`:774`): immediately after `typer.echo(f"Repo: {state.repo_path}")`, add
   `typer.echo(f"Status: {state.status_line}")`. Every other line and its order stay the same.
4. `watch`, live mode: add `observed_at=resources.clock.now(),` to both `fetch_dashboard_state`
   calls: the initial one (`:635-641`) and the one inside `_fetch_state` (`:644-650`). The
   refresher reads the clock on each call, so each refreshed frame carries its own cutoff.
5. `watch --replay` is unchanged: its states carry event-stream claims from
   `build_replay_states` (`gap-status-evidence-dashboard`).
6. No other command, and no other file under `src/`, changes.

## Where to change
- `src/vibey/cli/main.py` (five small edits).
- Tests: append to `tests/cli/test_ops_status_ledger.py` (created by `fakes-cli-operational-1`),
  using that module's own `memory_app` fixture, `ops.invoke(...)` and `seed_status_project`
  helper exactly as its `test_status_command_text_and_json` uses them.

## Acceptance criteria
- [ ] `vibey status <id>` prints a line that starts
      `Status: project <id>: active (ready 1, leased 0) — scope: cycle 1; source: store-snapshot (project, job and engine_health rows; ledger`
      for the seeded status project (one READY `design.interview` job at INTAKE). The line
      also contains `; cutoff: `, followed by an ISO-8601 time with an offset.
- [ ] `vibey status --json <id>` has `evidence` as a one-element list with the keys `subject`,
      `status`, `detail`, `source`, `locator`, `scope` and `cutoff`. `status == "active"`,
      `source == "store-snapshot"`, `scope == "cycle 1"`, and `datetime.fromisoformat(cutoff)`
      lies between two `datetime.now(UTC)` readings taken just before and just after the invoke.
- [ ] Every existing status and watch test passes unchanged: they check substrings, and every
      line they check is still printed.
- [ ] 100% branch coverage of `src/vibey/cli/*` from the full run.

## Tests to write first (TDD)
Append to `tests/cli/test_ops_status_ledger.py`:
- `test_status_names_its_object_source_and_cutoff`: the text line above.
- `test_status_json_carries_the_evidence_claim`: the JSON checks above, with the bracketed cutoff.
- `test_status_line_follows_the_repo_line`: in the text output, the `Status:` line comes right
  after the `Repo:` line.
The watch change is exercised by the existing watch tests, which drive the state fetcher
(`test_watch_state_fetcher_is_invoked`, `tests/cli/test_operational_commands.py:1774-1799` at
`4317cff6`, or wherever `fakes-cli-operational-2` or `-3` moved it). Its `observed_at` argument is checked by
reading the diff: the watch tests replace the dashboard app, so no rendered text is available
to assert on.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_ops_status_ledger.py tests/tui
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Claims in `vibey engines`, `vibey cost`, `vibey deploy status` and the ledger commands.
  Follow-ups apply the same vocabulary there.
- The TUI panels and the claim itself (`gap-status-evidence-dashboard`).
- Docs (`docs/reference/cli.md` gains the `Status:` line and the `evidence` key in the docs
  wave), CHANGELOG.md.

Commit as `feat(cli): vibey status and watch name the object, source and cutoff of what they show`. Do not push.

## Lane card
- **Depends on:** `gap-status-evidence-dashboard`, `fakes-cli-operational-1` (the in-memory status tests).
- **Kind:** one source file, one test file.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
