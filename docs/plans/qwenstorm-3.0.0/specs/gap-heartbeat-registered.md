## Title
fix(gh): the sovereign heartbeat is published only while a runner with the lane's label is registered and online

## Why
Sub-doctrine 10.f (`src/vibey_tools/gh/docs/doctrines.md:419`) says "silence is not success",
and a false readiness is worse. `vibey_gh/sovereign.py:60-88` (`beat`) pushes
`refs/vibey-gh/sovereign-heartbeat` unconditionally. The operator's out-of-tree loop decides
when to call it, using a launchd job with a live PID (`runner_up`,
`~/.local/share/vibey-runner/vibey-local-authority.sh:33-44`). While registration was 404ing,
that PID was live for about 30 s of every failing restart cycle, so a heartbeat went out at
2026-09-22T01:38Z with no runner able to take a job (`issue-audit/gaps.md` L3, lines 544-554).
A fresh heartbeat with no runner makes the sovereign review job **queue forever**, and the
required gate `needs` it.

GitHub's runners API is authoritative, but it needs `administration: read`, which
`GITHUB_TOKEN` cannot hold (`sovereign.py:16-22`). The operator's `gh`, which already mints
registration tokens (`vibey-runner.sh:79-81`), can read it. So `beat()` checks before it
publishes. The gap asked for "registered and idle". This lane requires **registered and online**
and reports `busy`: a busy runner takes the next job when it finishes, and withholding its
heartbeat would stale the lane out during every long review.

## Required behaviour
1. New module `src/vibey_tools/gh/vibey_gh/runner_status.py`:
   - `@dataclass(frozen=True) class RunnerStatus` with fields `name: str`, `online: bool`,
     `busy: bool` and `labels: tuple[str, ...]`.
   - `class GhRunnerStatusReader` with
     `__init__(self, *, run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run)`,
     the declared seam, and
     `list(self, repo: str) -> tuple[tuple[RunnerStatus, ...], str]`. It runs
     `gh api --paginate repos/{repo}/actions/runners --jq '.runners[] | {name, status, busy, labels: [.labels[].name]}'`
     with `capture_output=True, text=True, check=False`. It parses one JSON object per line,
     setting `online` to `status == "online"`. A non-zero exit returns
     `((), f"could not list runners for {repo}: {stderr.strip()}")`.
2. New interface `src/vibey_tools/gh/vibey_gh/interfaces/runner_status_interface.py`:
   `RunnerStatusReaderInterface(Protocol)` with `list`.
3. `sovereign.beat` (`sovereign.py:60`) gains keyword-only parameters
   `reader: RunnerStatusReaderInterface | None = None`, `repo: str = ""` and `label: str = ""`.
   - When `reader` is not None, before creating anything it calls `reader.list(repo)`.
     - On a problem it returns `Readiness(False, f"heartbeat withheld: {problem}")`.
     - If no runner has `label` in its labels and `online` true, it returns
       `Readiness(False, f"heartbeat withheld: no online runner labelled {label} is registered for {repo}")`.
     - Otherwise it proceeds as today. On success the reason ends with
       `f" ({n} online, {b} busy)"`.
   - With `reader=None` the behaviour is exactly today's; every existing test passes unchanged.
4. `_sovereign` in `cli.py` (`:678-706`) passes, for `--beat`:
   - `reader=GhRunnerStatusReader()`;
   - `label=fallback.runner_label`;
   - `repo`, taken from a new `--repo` option; else `$GH_REPO`; else parsed from
     `git remote get-url <remote>`, where `https://github.com/o/r(.git)` or
     `git@github.com:o/r(.git)` gives `o/r`.
   - An unparseable remote leaves `repo=""`. `beat` then reports
     `heartbeat withheld: could not list runners for : ...`. Make it clearer: when `repo` is
     empty, return `Readiness(False, "heartbeat withheld: cannot tell which repository the runner serves; pass --repo")`
     before calling the reader.
5. `probe()` is unchanged. Workflows still decide scheduling from the heartbeat's age.

## Where to change
- New: `vibey_gh/runner_status.py`, `vibey_gh/interfaces/runner_status_interface.py` (under `src/vibey_tools/gh/`).
- `vibey_gh/sovereign.py` (edit_file), and `vibey_gh/cli.py` (edit_file; the `sovereign` subparser at `:1603-1609` gains `--repo`).
- Tests: append to the existing sovereign test file (find it with `grep -ln "sovereign" src/vibey_tools/gh/test/*.py`).
  Add `src/vibey_tools/gh/test/test_runner_status.py`.
- Fakes: a test class implementing `RunnerStatusReaderInterface`, and a `run` callable that
  returns canned `CompletedProcess` objects. No `mock`, no `monkeypatch.setattr`.

## Acceptance criteria
- [ ] With a reader that answers no runners, `beat(..., reader=r, repo="o/r", label="vibey-local-vibey")`
      returns `ready=False` with the exact "no online runner labelled" text, and runs **no** `git` command.
      Assert this with a recording `git` runner if `beat`'s `_run` can be injected; otherwise
      assert that no ref changed in a temporary repo.
- [ ] A runner that is online but busy lets the beat proceed, and the reason says `(1 online, 1 busy)`.
- [ ] A runner that is offline, or has another label, withholds the beat.
- [ ] `GhRunnerStatusReader` parses the `--jq` lines, and turns a non-zero exit into the problem text.
- [ ] The remote URL parsing covers the https and ssh forms, and the empty-repo message is exact.
- [ ] Every existing sovereign test passes unchanged. vibey-gh's gates pass.

## Tests to write first (TDD)
- `test/test_runner_status.py`: `test_reader_parses_runners`, `test_reader_reports_a_failed_listing`.
- Appended to the sovereign test file: `test_beat_is_withheld_without_an_online_runner`,
  `test_beat_proceeds_for_a_busy_online_runner`, `test_beat_is_withheld_for_the_wrong_label`,
  `test_beat_without_a_repo_is_withheld`, `test_cli_beat_derives_the_repo_from_the_remote`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q -p no:cacheprovider
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The out-of-tree loop's own `runner_up`. Once `deploy/runners/vibey-local-authority.sh` is in
  the tree (`gap-ops-runner-assets-import`), a follow-up drops its PID check in favour of this one.
- Probe or workflow changes, and docs.

Commit as `fix(gh): publish the sovereign heartbeat only for a registered, online runner`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
