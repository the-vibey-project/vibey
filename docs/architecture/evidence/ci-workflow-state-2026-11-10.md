# CI workflow state and cost baseline, 2026-11-10

**Object:** the GitHub Actions workflows of `the-vibey-project/vibey`. **Source:** read-only `gh api` GET calls, collected by `scripts/ci_cost_baseline.py` and stored in `ci-cost-baseline-2026-11-10.json` beside this file. **Window:** 14 days, 2026-10-27T18:06:05Z to 2026-11-10T18:06:05Z (UTC). **Cutoff:** 2026-11-10T18:06:05Z. 525 API calls, 0 workflows or probes unreadable.

This is the measured state before any CI change lands in the optimization program (SP0), so a later saving is evidenced against it instead of assumed (sub-doctrines 12.e and 10.f). Every figure below names its window and cutoff; a figure the forge could not give is `unknown`, never a number.

## Cost: billed dollars are 0, the real costs are queueing and wall time

- Repository visibility: **public**. Public repository on standard runners: billed dollars are 0; the run timing API reported 0 billable ms across 3 sampled run(s).
- Measured how: `GET repos/<repo>` for visibility, and `GET repos/<repo>/actions/runs/<id>/timing` on 3 completed runs, which reported 0 billable milliseconds. Billed dollars: **0**.
- The costs that remain are queueing and wall time (below), and any runner capacity limit; none is a dollar figure.

## Headline figures

- Workflows: 39 (21 active, 18 `disabled_manually`, 0 disabled otherwise, 0 unreadable).
- Runs created in the window: 4617 (read from the API's `total_count` for the window); 476 of them sampled (newest 20 per workflow) for conclusions, wall time and job minutes.
- Job minutes in the sample, by runner OS: macos 285, other 106, ubuntu 17,334, windows 0.
- Job minutes **estimated** for the whole window (per-workflow sample mean per run times runs in the window; an estimate, not a measurement): workflows active at the cutoff 2529 runs, macos 2,649, other 0, ubuntu 33,588, windows 0; workflows now disabled 2088 runs, macos 127, other 287, ubuntu 18,064, windows 0.
- Conclusions in the sample: cancelled 31, failure 66, in_progress 1, queued 1, skipped 80, success 297.

## One row per workflow

Wall time is a completed run's `run_started_at` to `updated_at`, in minutes, over the sampled runs (cancelled and failed runs included); p50 and p90 are by linear interpolation. "Runs" is runs created in the window. Triggers are the `event` values seen in the sample, with counts. Last run is the newest run ever, by creation date and conclusion (status when unfinished).

| Workflow | State | Triggers seen (sample) | Runs in window | Last run | Wall p50 / p90 min | Why disabled |
|---|---|---|---|---|---|---|
| Autonomy scorecard | `disabled_manually` | schedule 1 | 1 | 2026-10-29, success | 1.6 / 1.6 (n=1) | unknown, operator to say |
| Backlog cleanup | `disabled_manually` | schedule 20 | 34 (sample capped) | 2026-11-05, success | 2.0 / 2.5 (n=20) | unknown, operator to say |
| Backlog killer | `disabled_manually` | schedule 3, workflow_dispatch 17 | 44 (sample capped) | 2026-10-29, cancelled | 60.0 / 60.1 (n=20) | unknown, operator to say. Related record: the lane was paused in `scripts/daily_lanes.toml` by #1809 (2026-10-29), a repository switch, not this GitHub-level disablement |
| Backlog splitter | `disabled_manually` | schedule 20 | 23 (sample capped) | 2026-11-04, success | 0.3 / 0.3 (n=20) | unknown, operator to say |
| Continuation prompts | `disabled_manually` | schedule 1, workflow_dispatch 19 | 54 (sample capped) | 2026-11-05, failure | 38.8 / 66.2 (n=20) | unknown, operator to say |
| Delivery estimate | `disabled_manually` | schedule 20 | 34 (sample capped) | 2026-11-05, success | 15.1 / 18.0 (n=20) | unknown, operator to say |
| Documentation deep scan | `disabled_manually` | schedule 8 | 8 | 2026-11-04, success | 0.4 / 0.5 (n=8) | unknown, operator to say |
| Documentation updater | `disabled_manually` | schedule 9 | 9 | 2026-11-05, success | 0.8 / 0.8 (n=9) | unknown, operator to say |
| First hour | `disabled_manually` | schedule 2 | 2 | 2026-11-04, failure | 276.4 / 280.0 (n=2) | unknown, operator to say |
| Host health | `disabled_manually` | schedule 1 | 1 | 2026-11-03, success | 0.5 / 0.5 (n=1) | unknown, operator to say |
| Merge train | `disabled_manually` | schedule 1, workflow_dispatch 3 | 4 | 2026-11-02, success | 0.6 / 1.1 (n=4) | unknown, operator to say |
| Minimum specs | `disabled_manually` | schedule 1 | 1 | 2026-11-02, success | 173.5 / 173.5 (n=1) | unknown, operator to say |
| PR evaluate | `disabled_manually` | pull_request_target 1, workflow_run 19 | 1838 (sample capped) | 2026-11-05, success | 0.5 / 0.9 (n=20) | unknown, operator to say |
| Promote | `disabled_manually` | schedule 2, workflow_dispatch 1, workflow_run 1 | 4 | 2026-11-02, success | 0.5 / 0.7 (n=4) | unknown, operator to say |
| Release binaries | `disabled_manually` | pull_request 2, schedule 8, workflow_run 1 | 11 | 2026-11-05, success | 19.6 / 24.6 (n=11) | unknown, operator to say |
| Review canary | `disabled_manually` | schedule 2 | 2 | 2026-11-04, success | 441.6 / 442.2 (n=2) | unknown, operator to say |
| Ruleset drift | `disabled_manually` | push 2, schedule 8 | 10 | 2026-11-05, success | 0.3 / 156.5 (n=10) | unknown, operator to say |
| Self-healer | `disabled_manually` | schedule 8 | 8 | 2026-11-04, success | 1.2 / 4.1 (n=8) | unknown, operator to say |
| Automation bootstrap | `active` | none in window | 0 | never run | n/a (no completed run in window) | n/a, active |
| Branch health | `active` | workflow_run 20 | 127 (sample capped) | 2026-11-10, in_progress | 0.4 / 0.7 (n=19) | n/a, active |
| Changelog | `active` | pull_request 20 | 284 (sample capped) | 2026-11-10, success | 0.4 / 0.9 (n=20) | n/a, active |
| Chat | `active` | issue_comment 20 | 45 (sample capped) | 2026-11-08, skipped | 0.0 / 0.2 (n=20) | n/a, active |
| CI | `active` | pull_request 15, push 5 | 337 (sample capped) | 2026-11-10, failure | 11.3 / 17.6 (n=19) | n/a, active |
| Conventional Commits | `active` | pull_request_target 20 | 304 (sample capped) | 2026-11-10, success | 0.4 / 1.4 (n=20) | n/a, active |
| Copilot | `active` | none in window | 0 | 2026-09-24, success | n/a (no completed run in window) | n/a, active |
| Copilot cloud agent | `active` | none in window | 0 | 2026-09-18, success | n/a (no completed run in window) | n/a, active |
| Dependabot Updates | `active` | dynamic 20 | 24 (sample capped) | 2026-11-08, success | 1.3 / 2.6 (n=20) | n/a, active |
| Dependency Graph | `active` | dynamic 14 | 14 | 2026-11-08, success | 1.1 / 2.4 (n=14) | n/a, active |
| GitHub Release | `active` | workflow_run 20 | 72 (sample capped) | 2026-11-10, skipped | 0.0 / 0.2 (n=20) | n/a, active |
| krypton-app | `active` | pull_request 15, push 5 | 60 (sample capped) | 2026-11-06, success | 0.8 / 1.7 (n=20) | n/a, active |
| Open VSX | `active` | workflow_run 1 | 1 | 2026-11-05, success | 0.8 / 0.8 (n=1) | n/a, active |
| PR review | `active` | workflow_dispatch 20 | 180 (sample capped) | 2026-11-05, failure | 57.0 / 162.5 (n=20) | n/a, active |
| Provenance | `active` | pull_request 8, push 12 | 533 (sample capped) | 2026-11-10, success | 0.5 / 1.0 (n=20) | n/a, active |
| Release | `active` | push 20 | 72 (sample capped) | 2026-11-10, failure | 1.4 / 2.5 (n=20) | n/a, active |
| Release surfaces | `active` | workflow_run 20 | 72 (sample capped) | 2026-11-10, skipped | 0.0 / 0.1 (n=20) | n/a, active |
| Repository profile | `active` | workflow_run 20 | 73 (sample capped) | 2026-11-10, skipped | 0.0 / 0.2 (n=20) | n/a, active |
| Skip markers | `active` | pull_request 20 | 331 (sample capped) | 2026-11-10, success | 0.4 / 0.6 (n=20) | n/a, active |
| vibey (remote command) | `active` | none in window | 0 | never run | n/a (no completed run in window) | n/a, active |
| vibey state (write back) | `active` | none in window | 0 | never run | n/a (no completed run in window) | n/a, active |

## Why the disabled workflows are disabled

The repository holds no record of why any of the 18 `disabled_manually` workflows is disabled. For each one, `docs/`, `CHANGELOG.md`, `changelog.d/`, `.vibey-gh.toml` and the scripts' TOML files were searched for its name beside any of disable, pause, switched off, turned off, suspend; `git log --all` was searched for those words in commit messages and for each workflow's name in `docs/`, `CHANGELOG.md` and `.vibey-gh.toml` (`-S`). Every hit was the workflow's creation or a feature change, with two exceptions that are not the answer:

- #1809, #1813 and #1505 pause the backlog killer through `[backlog_killer] enabled` in `scripts/daily_lanes.toml`. That is a different switch from the GitHub-side `disabled_manually` state, and it does not name the splitter or any other workflow.
- ADR-0072 (the Sabbath window) describes held work as paused, which is a code-level guard, not a disablement record.

So the "why disabled" for every row is `unknown, operator to say`. Nothing here infers a reason. One bounded fact the data does give: each disabled workflow's newest run is dated in the Last run column, so it was disabled after that date (the API reports no disable timestamp).

## Caveats

- The window includes runs of workflows that were later disabled; their run counts are before the disablement. The active and disabled estimates are shown apart for that reason.
- Job minutes come from the newest runs per workflow, so they follow whatever those runs happened to be (a cancelled or in-progress run contributes the minutes it had). The window estimate scales the sample mean to the run count; treat it as an order of magnitude.
- `updated_at` is the run's last update and can postdate completion after a re-run, so wall time can read long; it also includes time waiting for a runner. Queueing is therefore inside the wall figure, not separated from it.
- Runs with no jobs in the API are counted as zero minutes and noted per workflow in the JSON (`runs_without_jobs`); jobs with no start or end are counted in `jobs_without_timing`.
- Workflows with `event` `dynamic` (Dependabot, Copilot, dependency graph) are GitHub-run, not defined in `.github/workflows`.

## Reproduce

`uv run python scripts/ci_cost_baseline.py collect` (settings in `scripts/ci_cost_baseline.toml`: repository, window days, sample size, output path). It makes only `gh api` GET calls.
