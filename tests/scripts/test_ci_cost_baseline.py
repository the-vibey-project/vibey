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
from pathlib import Path
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
        billable: Mapping[str, Any] | None = None,
    ) -> None:
        self.workflows, self.runs, self.jobs = workflows, runs, jobs
        self.private, self.billable = private, dict(billable or {})
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
            return Result(0, json.dumps({"billable": self.billable, "run_duration_ms": 1000}))
        return Result(1, "", f"gh: unrouted {path}")


def settings(**over: Any) -> cb.CiBaselineSettings:
    base: dict[str, Any] = {
        "repo": REPO,
        "window_days": 14,
        "sample_size": 10,
        "per_page": 100,
        "timeout_seconds": 5.0,
        "timing_probe_runs": 1,
        "output": "out-{stamp}.json",
        "baseline": "baseline.json",
        "document": "state.md",
        "orientation_disabled": 14,
        "related_records": {"old": "a related note"},
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


UBUNTU_JOB = [job("ubuntu-latest", 5)]
ZERO = {"UBUNTU": {"total_ms": 0, "jobs": 1}}


def cost_of(gh: FakeGh, **over: Any) -> dict[str, Any]:
    return collector(gh, **over).collect(14)["cost"]  # type: ignore[return-value]


def test_billed_dollars_zero_only_when_the_api_returned_entries_that_are_zero() -> None:
    cost = cost_of(FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB}, billable=ZERO))
    assert cost["billed_usd"] == 0
    assert cost["repository_visibility"] == "public"
    assert cost["billable_ms_observed"] == 0
    assert cost["billable_keys_seen"] == ["UBUNTU"]
    assert "standard runners" not in cost["basis"]


def test_an_empty_billable_object_is_no_data_not_a_zero() -> None:
    cost = cost_of(FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB}, billable={}))
    assert cost["billed_usd"] is None
    assert cost["billable_ms_observed"] is None
    assert cost["basis"].startswith("unknown")
    assert cost["billable_keys_seen"] == []


def test_billable_milliseconds_above_zero_on_a_public_repository_are_not_called_free() -> None:
    paid = {"UBUNTU": {"total_ms": 5000, "jobs": 1}}
    cost = cost_of(FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB}, billable=paid))
    assert cost["billed_usd"] is None
    assert cost["billable_ms_observed"] == 5000
    assert cost["basis"].startswith("unknown")


def test_private_repository_does_not_claim_zero_dollars() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB}, private=True, billable=ZERO)
    cost = cost_of(gh)
    assert cost["billed_usd"] is None
    assert "unknown" in cost["basis"]


def test_one_completed_run_is_probed_per_runner_os() -> None:
    jobs = {11: [job("ubuntu-latest", 5)], 12: [job("macos-14", 5)], 13: [job("ubuntu-latest", 5)]}
    gh = FakeGh([wf(1, "ci")], {1: [run(11), run(12), run(13)]}, jobs, billable=ZERO)
    probes = cost_of(gh)["probes"]
    assert [(p["os"], p["run_id"]) for p in probes] == [("ubuntu", 11), ("macos", 12)]
    assert sum(1 for path in gh.paths if path.endswith("/timing")) == 2


def test_labels_in_the_other_bucket_are_recorded() -> None:
    jobs = {11: [job("self-hosted", 5), job("ubuntu-latest", 5)]}
    record = collector(FakeGh([wf(1, "ci")], {1: [run(11)]}, jobs)).collect(14)
    assert record["other_runner_labels"] == {"self-hosted": 1}


def test_record_names_window_cutoff_and_api_call_count() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: []})
    record = collector(gh).collect(14)
    assert record["window"] == {"days": 14, "start": "2026-10-27T12:00:00Z", "cutoff": NOW}
    assert record["repo"] == REPO
    assert record["api_calls"] == len(gh.paths)
    assert all(p.startswith("repos/") for p in gh.paths)


def test_only_get_calls_are_made() -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB})
    seen: list[Sequence[str]] = []
    original = gh.run

    def spy(argv: Sequence[str], **kw: Any) -> Result:
        seen.append(list(argv))
        return original(argv, **kw)

    gh.run = spy  # type: ignore[method-assign]
    collector(gh).collect(14)
    assert seen
    for argv in seen:
        assert argv == ["gh", "api", argv[-1]]
        assert argv[-1].startswith("repos/")


def test_the_guard_rejects_anything_that_is_not_a_plain_get() -> None:
    guard = cb.GhActionsReader.is_read_only
    assert guard(["gh", "api", "repos/a/b/actions/workflows"])
    assert not guard(["gh", "api", "-X", "POST", "repos/a/b/actions/runs/1/rerun"])
    assert not guard(["gh", "api", "--method", "DELETE", "repos/a/b"])
    assert not guard(["gh", "api", "-f", "x=1", "repos/a/b"])
    assert not guard(["gh", "api", "orgs/a"])
    assert not guard(["gh", "workflow", "disable", "repos/a/b"])


def test_the_reader_refuses_a_write_shaped_path_before_calling_gh() -> None:
    gh = FakeGh([], {}, {})
    reader = cb.GhActionsReader(gh, REPO, 5.0)
    try:
        reader._get("orgs/elsewhere")
    except ValueError:
        assert gh.paths == []
        return
    raise AssertionError("a non-repos path must be refused")


def test_collector_satisfies_its_interface() -> None:
    assert isinstance(collector(FakeGh([], {}, {})), contracts.CiCostBaselineInterface)


def test_settings_load_from_toml_with_no_defaults(tmp_path: Any) -> None:
    path = tmp_path / "s.toml"
    path.write_text(
        '[ci_cost_baseline]\nrepo = "a/b"\nwindow_days = 3\nsample_size = 4\nper_page = 5\n'
        'timeout_seconds = 6.0\ntiming_probe_runs = 1\noutput = "o.json"\nbaseline = "b.json"\n'
        'document = "d.md"\norientation_disabled = 14\n[ci_cost_baseline.related_records]\nx = "y"\n'
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


# ------------------------------------------------------------------ the command line

DOC = "intro\n" + "".join(
    f"<!-- BEGIN GENERATED ci-baseline:{n} — regenerated by scripts/ci_cost_baseline.py -->\n"
    f"old\n<!-- END GENERATED ci-baseline:{n} -->\nstatic prose\n"
    for n in ("provenance", "cost", "headline", "workflows")
)


def cli(tmp_path: Any, gh: FakeGh) -> cb.CiCostBaselineCli:
    config = tmp_path / "scripts"
    config.mkdir(exist_ok=True)
    (config / "ci_cost_baseline.toml").write_text(
        '[ci_cost_baseline]\nrepo = "example-org/example-repo"\nwindow_days = 14\nsample_size = 10\n'
        'per_page = 100\ntimeout_seconds = 5.0\ntiming_probe_runs = 1\noutput = "out-{stamp}.json"\n'
        'baseline = "baseline.json"\ndocument = "state.md"\norientation_disabled = 14\n'
        '[ci_cost_baseline.related_records]\nold = "a related note"\n'
    )
    return cb.CiCostBaselineCli(tmp_path, runner=gh, clock=FixedClock())


def healthy() -> FakeGh:
    return FakeGh(
        [wf(1, "ci"), wf(2, "old", "disabled_manually")],
        {1: [run(11)], 2: [run(12)]},
        {11: UBUNTU_JOB, 12: UBUNTU_JOB},
        billable=ZERO,
    )


def test_collect_writes_a_stamped_file_and_exits_zero(tmp_path: Any) -> None:
    assert cli(tmp_path, healthy()).run(["collect"]) == 0
    assert (tmp_path / "out-20261110T120000Z.json").exists()


def test_collect_refuses_to_overwrite_and_force_overwrites(tmp_path: Any) -> None:
    target = tmp_path / "out-20261110T120000Z.json"
    target.write_text("good evidence")
    assert cli(tmp_path, healthy()).run(["collect"]) == 1
    assert target.read_text() == "good evidence"
    assert cli(tmp_path, healthy()).run(["collect", "--force"]) == 0
    assert json.loads(target.read_text())["repo"] == REPO


def test_collect_exits_one_and_writes_nothing_when_the_listing_is_unreadable(tmp_path: Any) -> None:
    class Dead(FakeGh):
        def run(self, argv: Sequence[str], **kw: Any) -> Result:
            return Result(1, "", "gh: HTTP 500")

    assert cli(tmp_path, Dead([], {}, {})).run(["collect"]) == 1
    assert list(tmp_path.glob("out-*.json")) == []


def test_collect_exits_two_when_the_record_is_written_with_unknowns(tmp_path: Any) -> None:
    class Partial(FakeGh):
        def run(self, argv: Sequence[str], **kw: Any) -> Result:
            if "/workflows/1/runs" in argv[-1]:
                return Result(1, "", "gh: HTTP 502")
            return super().run(argv, **kw)

    flaky = Partial([wf(1, "ci"), wf(2, "other")], {2: [run(9)]}, {9: []})
    assert cli(tmp_path, flaky).run(["collect"]) == 2
    assert (tmp_path / "out-20261110T120000Z.json").exists()


def test_render_rewrites_only_the_generated_blocks_and_check_follows(tmp_path: Any) -> None:
    tool = cli(tmp_path, healthy())
    assert tool.run(["collect", "--out", "baseline.json"]) == 0
    (tmp_path / "state.md").write_text(DOC)
    assert tool.run(["check"]) == 1  # the blocks still say "old"
    assert tool.run(["render"]) == 0
    text = (tmp_path / "state.md").read_text()
    assert text.startswith("intro\n") and text.count("static prose") == 4
    assert "| old | `disabled_manually` |" in text and "a related note" in text
    assert "about 14 disabled workflows; the measurement found 1" in text
    assert tool.run(["check"]) == 0
    (tmp_path / "state.md").write_text(text.replace("| ci |", "| edited |"))
    assert tool.run(["check"]) == 1


def test_render_fails_loudly_when_a_block_is_missing(tmp_path: Any) -> None:
    tool = cli(tmp_path, healthy())
    assert tool.run(["collect", "--out", "baseline.json"]) == 0
    (tmp_path / "state.md").write_text("no markers here\n")
    try:
        tool.run(["render"])
    except ValueError as exc:
        assert "ci-baseline:provenance" in str(exc)
        return
    raise AssertionError("a missing block must be an error")


def test_committed_document_matches_the_committed_record() -> None:
    """The state document's generated blocks must be what `render` makes of the committed record
    (the same check as `python scripts/ci_cost_baseline.py check`)."""
    root = Path(__file__).resolve().parents[2]
    assert cb.CiCostBaselineCli(root).run(["check"]) == 0


def test_cost_wording_names_probed_os_and_what_falls_outside_the_measurement(tmp_path: Any) -> None:
    jobs = {11: [job("ubuntu-latest", 5), job("self-hosted", 5), job("", 5), job("", 5)]}
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, jobs, billable=ZERO)
    tool = cli(tmp_path, gh)
    assert tool.run(["collect", "--out", "baseline.json"]) == 0
    record = json.loads((tmp_path / "baseline.json").read_text())
    basis = record["cost"]["basis"]
    assert "covering runner OS ubuntu" in basis
    assert "not for jobs on any other runner kind" in basis
    assert "are listed in `probes`" not in basis
    (tmp_path / "state.md").write_text(DOC)
    assert tool.run(["render"]) == 0
    text = (tmp_path / "state.md").read_text()
    assert "Runner OS with no probe recorded: macos, windows." in text
    assert "(2 jobs)" in text and "`self-hosted` (1 jobs)" in text
    assert "jobs (3 in the sampled runs) are on runner kinds no probe covered" in text
    assert "A self-hosted runner label appears on 1 jobs" in text
    assert "scripts/minimum_specs.toml" in text and "the operator is to say which is right" in text


def test_no_self_hosted_note_when_no_job_used_a_self_hosted_label(tmp_path: Any) -> None:
    gh = FakeGh([wf(1, "ci")], {1: [run(11)]}, {11: UBUNTU_JOB}, billable=ZERO)
    tool = cli(tmp_path, gh)
    assert tool.run(["collect", "--out", "baseline.json"]) == 0
    (tmp_path / "state.md").write_text(DOC)
    assert tool.run(["render"]) == 0
    assert "self-hosted runner label appears" not in (tmp_path / "state.md").read_text()
