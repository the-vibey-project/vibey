# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/ci_cost_baseline.py`: percentiles, the runner-OS split, the window cutoff, pagination
and the disabled-workflow record, driven through a fake `gh` that answers from fixture JSON.

Module-level test functions (ADR-0016: the rule is about production code; pytest collects them).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from scripts import ci_cost_baseline as cb
from scripts.interfaces import ci_cost_baseline_interface as contracts

REPO = "example-org/example-repo"
NOW = "2026-11-10T12:00:00Z"
FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str
    stderr: str = ""
    seconds: float = 0.0


class FixedClock:
    def now(self) -> str:
        return NOW


class FakeGh:
    """Answers `gh api <path>` GETs from fixtures and records every path it was asked for."""

    def __init__(
        self,
        workflows: Sequence[Mapping[str, Any]],
        runs: Mapping[int, Sequence[Mapping[str, Any]]],
        jobs: Mapping[int, Sequence[Mapping[str, Any]]],
        private: bool = False,
        timing_ms: int = 0,
    ) -> None:
        self.workflows, self.runs, self.jobs = workflows, runs, jobs
        self.private, self.timing_ms = private, timing_ms
        self.paths: list[str] = []

    def run(
        self, argv: Sequence[str], *, timeout: float, env: Any = None, cwd: Any = None
    ) -> Result:
        assert argv[:2] == ["gh", "api"], argv
        path = argv[-1]
        self.paths.append(path)
        route, _, query = path.partition("?")
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        per_page, page = int(params.get("per_page", "30")), int(params.get("page", "1"))
        if route == f"repos/{REPO}":
            visibility = "private" if self.private else "public"
            return Result(0, json.dumps({"private": self.private, "visibility": visibility}))
        if route == f"repos/{REPO}/actions/workflows":
            body = {"total_count": len(self.workflows), "workflows": list(self.workflows)}
            return Result(0, json.dumps(body))
        if route.endswith("/runs") and "/workflows/" in route:
            wid = int(route.split("/workflows/")[1].split("/")[0])
            rows = list(self.runs.get(wid, []))
            chunk = rows[(page - 1) * per_page : page * per_page]
            return Result(0, json.dumps({"total_count": len(rows), "workflow_runs": chunk}))
        if route.endswith("/jobs"):
            rid = int(route.split("/runs/")[1].split("/")[0])
            if rid not in self.jobs:
                return Result(1, "", "gh: Not Found (HTTP 404)")
            rows = list(self.jobs[rid])
            chunk = rows[(page - 1) * per_page : page * per_page]
            return Result(0, json.dumps({"total_count": len(rows), "jobs": chunk}))
        if route.endswith("/timing"):
            billable = {"UBUNTU": {"total_ms": self.timing_ms}} if self.timing_ms else {}
            return Result(0, json.dumps({"billable": billable, "run_duration_ms": 1000}))
        return Result(1, "", f"gh: unrouted {path}")


def settings(**over: Any) -> cb.CiBaselineSettings:
    base: dict[str, Any] = {
        "repo": REPO,
        "window_days": 14,
        "sample_size": 10,
        "per_page": 100,
        "timeout_seconds": 5.0,
        "timing_probe_runs": 1,
        "output": "unused.json",
    }
    base.update(over)
    return cb.CiBaselineSettings(**base)


def wf(wid: int, name: str, state: str = "active") -> dict[str, Any]:
    return {"id": wid, "name": name, "path": f".github/workflows/{name}.yml", "state": state}


def run(
    rid: int,
    created: str = "2026-11-09T10:00:00Z",
    minutes: float = 10.0,
    event: str = "push",
    conclusion: str | None = "success",
) -> dict[str, Any]:
    end = (datetime.strptime(created, FORMAT) + timedelta(minutes=minutes)).strftime(FORMAT)
    return {
        "id": rid,
        "created_at": created,
        "run_started_at": created,
        "updated_at": end,
        "event": event,
        "status": "completed" if conclusion else "in_progress",
        "conclusion": conclusion,
    }


def job(label: str, minutes: float, started: str | None = "2026-11-09T10:00:00Z") -> dict[str, Any]:
    done = None
    if started is not None:
        done = (datetime.strptime(started, FORMAT) + timedelta(minutes=minutes)).strftime(FORMAT)
    return {
        "labels": [label] if label else [],
        "started_at": started,
        "completed_at": done,
        "conclusion": "success",
    }


def collector(gh: FakeGh, **over: Any) -> cb.CiCostBaseline:
    return cb.CiCostBaseline(settings(**over), cb.GhActionsReader(gh, REPO, 5.0), FixedClock())


def test_percentile_odd_count() -> None:
    assert cb.Statistics().percentile([3.0, 1.0, 2.0], 50) == 2.0


def test_percentile_even_count_interpolates() -> None:
    stats = cb.Statistics()
    assert stats.percentile([4.0, 1.0, 3.0, 2.0], 50) == 2.5
    assert stats.percentile([float(i) for i in range(1, 11)], 90) == 9.1


def test_percentile_of_nothing_is_none_not_zero() -> None:
    assert cb.Statistics().percentile([], 50) is None


def test_percentile_of_one_value() -> None:
    assert cb.Statistics().percentile([7.0], 90) == 7.0


def test_os_split_ubuntu_macos_windows_and_other() -> None:
    split = cb.RunnerOs()
    assert split.of(["ubuntu-latest"]) == "ubuntu"
    assert split.of(["ubuntu-24.04-arm"]) == "ubuntu"
    assert split.of(["macos-14"]) == "macos"
    assert split.of(["windows-2022"]) == "windows"
    assert split.of(["self-hosted", "gpu"]) == "other"
    assert split.of([]) == "other"


def test_job_minutes_split_by_runner_os() -> None:
    jobs = [
        job("ubuntu-latest", 10),
        job("ubuntu-latest", 5),
        job("macos-14", 20),
        job("windows-2022", 4),
    ]
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: jobs})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["job_minutes_sampled"] == {
        "ubuntu": 15.0,
        "macos": 20.0,
        "windows": 4.0,
        "other": 0.0,
    }
    assert only["job_minutes_per_run_mean"]["ubuntu"] == 15.0


def test_run_with_no_jobs_counts_zero_and_is_noted() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11), run(12)]}, {11: [], 12: [job("ubuntu-latest", 6)]})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["runs_without_jobs"] == 1
    assert only["job_minutes_sampled"]["ubuntu"] == 6.0
    assert only["jobs_sampled_runs"] == 2


def test_unfinished_job_has_no_duration_and_is_counted() -> None:
    jobs = [job("ubuntu-latest", 0, started=None), job("ubuntu-latest", 3)]
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: jobs})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["jobs_without_timing"] == 1
    assert only["job_minutes_sampled"]["ubuntu"] == 3.0


def test_window_cutoff_excludes_older_runs() -> None:
    runs = [run(1, "2026-11-09T10:00:00Z"), run(2, "2026-10-20T10:00:00Z")]
    gh = FakeGh([wf(1, "ci")], {1: runs}, {1: [], 2: []})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["runs_sampled"] == 1
    assert only["conclusions"] == {"success": 1}


def test_pagination_stops_at_the_cutoff() -> None:
    newer = [run(i, "2026-11-09T10:00:00Z") for i in range(1, 3)]
    older = [run(i, "2026-10-01T10:00:00Z") for i in range(3, 9)]
    gh = FakeGh([wf(1, "ci")], {1: newer + older}, {i: [] for i in range(1, 9)})
    collector(gh, per_page=2, sample_size=50).collect(14)
    pages = [p for p in gh.paths if "/workflows/1/runs" in p]
    assert len(pages) == 2  # page 2 crosses the cutoff, so page 3 is never asked for


def test_sample_size_caps_the_runs_read_and_is_flagged() -> None:
    runs = [run(i) for i in range(1, 8)]
    gh = FakeGh([wf(1, "ci")], {1: runs}, {i: [] for i in range(1, 8)})
    only = collector(gh, sample_size=3).collect(14)["workflows"][0]
    assert only["runs_sampled"] == 3
    assert only["runs_in_window"] == 7
    assert only["sample_capped"] is True


def test_wall_time_p50_p90_in_minutes_and_trigger_events() -> None:
    shape = [(1, "push"), (2, "pull_request"), (3, "pull_request"), (4, "schedule")]
    runs = [run(i, minutes=m, event=e) for i, (m, e) in enumerate(shape, start=1)]
    gh = FakeGh([wf(1, "ci")], {1: runs}, {i: [] for i in range(1, 5)})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["wall_minutes"]["p50"] == 2.5
    assert only["wall_minutes"]["p90"] == 3.7
    assert only["events"] == {"pull_request": 2, "push": 1, "schedule": 1}


def test_in_progress_runs_are_counted_but_not_timed() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(1), run(2, conclusion=None)]}, {1: [], 2: []})
    only = collector(gh).collect(14)["workflows"][0]
    assert only["runs_sampled"] == 2
    assert only["conclusions"] == {"success": 1, "in_progress": 1}
    assert only["wall_minutes"]["n"] == 1


def test_disabled_manually_workflows_are_recorded() -> None:
    flows = [wf(1, "ci"), wf(2, "old", "disabled_manually"), wf(3, "idle", "disabled_inactivity")]
    gh = FakeGh(flows, {1: [run(1)]}, {1: []})
    record = collector(gh).collect(14)
    assert [w["name"] for w in record["disabled_workflows"]] == ["idle", "old"]
    states = {w["name"]: w["state"] for w in record["disabled_workflows"]}
    assert states["old"] == "disabled_manually"
    assert record["totals"]["workflows_disabled_manually"] == 1
    assert record["totals"]["workflows_active"] == 1


def test_totals_are_split_by_whether_the_workflow_is_still_active() -> None:
    flows = [wf(1, "ci"), wf(2, "old", "disabled_manually")]
    runs = {1: [run(1), run(2)], 2: [run(3)]}
    jobs = {1: [job("ubuntu-latest", 10)], 2: [job("ubuntu-latest", 10)], 3: [job("macos-14", 30)]}
    split = collector(FakeGh(flows, runs, jobs)).collect(14)["totals_by_state"]
    assert split["active"]["runs_in_window"] == 2
    assert split["active"]["job_minutes_estimated_for_window"]["ubuntu"] == 20.0
    assert split["disabled"]["runs_in_window"] == 1
    assert split["disabled"]["job_minutes_estimated_for_window"]["macos"] == 30.0


def test_a_workflow_that_cannot_be_read_is_unknown_with_its_reason() -> None:
    class Broken(FakeGh):
        def run(self, argv: Sequence[str], **kw: Any) -> Result:
            if "/workflows/1/runs" in argv[-1]:
                return Result(1, "", "gh: HTTP 502")
            return super().run(argv, **kw)

    gh = Broken([wf(1, "ci"), wf(2, "other")], {2: [run(9)]}, {9: []})
    record = collector(gh).collect(14)
    broken = next(w for w in record["workflows"] if w["name"] == "ci")
    assert broken["status"] == "unknown"
    assert "502" in broken["reason"]
    assert record["unknowns"] and "ci" in record["unknowns"][0]


def test_billed_dollars_zero_for_public_repository_with_measured_basis() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: []}, private=False, timing_ms=0)
    cost = collector(gh).collect(14)["cost"]
    assert cost["billed_usd"] == 0
    assert cost["repository_visibility"] == "public"
    assert cost["billable_ms_observed"] == 0
    assert "public" in cost["basis"]


def test_private_repository_does_not_claim_zero_dollars() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: []}, private=True)
    cost = collector(gh).collect(14)["cost"]
    assert cost["billed_usd"] is None
    assert "unknown" in cost["basis"]


def test_record_names_window_cutoff_and_api_call_count() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: []})
    record = collector(gh).collect(14)
    assert record["window"] == {"days": 14, "start": "2026-10-27T12:00:00Z", "cutoff": NOW}
    assert record["repo"] == REPO
    assert record["api_calls"] == len(gh.paths)
    assert all(p.startswith("repos/") for p in gh.paths)


def test_only_get_calls_are_made() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: []})
    seen: list[Sequence[str]] = []
    original = gh.run

    def spy(argv: Sequence[str], **kw: Any) -> Result:
        seen.append(argv)
        return original(argv, **kw)

    gh.run = spy  # type: ignore[method-assign]
    collector(gh).collect(14)
    flags = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"}
    assert seen and all(not flags & set(a) for a in seen)


def test_collector_satisfies_its_interface() -> None:
    assert isinstance(collector(FakeGh([], {}, {})), contracts.CiCostBaselineInterface)


def test_settings_load_from_toml_with_no_defaults(tmp_path: Any) -> None:
    path = tmp_path / "s.toml"
    path.write_text(
        '[ci_cost_baseline]\nrepo = "a/b"\nwindow_days = 3\nsample_size = 4\nper_page = 5\n'
        'timeout_seconds = 6.0\ntiming_probe_runs = 1\noutput = "o.json"\n'
    )
    loaded = cb.CiBaselineSettings.load(path)
    assert (loaded.repo, loaded.window_days, loaded.sample_size, loaded.output) == (
        "a/b",
        3,
        4,
        "o.json",
    )
    path.write_text('[ci_cost_baseline]\nrepo = "a/b"\n')
    try:
        cb.CiBaselineSettings.load(path)
    except KeyError:
        return
    raise AssertionError("a missing key must be an error, not a default")
