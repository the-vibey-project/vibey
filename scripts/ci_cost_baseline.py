# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What vibey's CI costs, measured from the forge and recorded with its window and cutoff.

    python scripts/ci_cost_baseline.py collect [--since-days N] [--out PATH] [--force]
    python scripts/ci_cost_baseline.py render     # rewrite the state document's GENERATED blocks
    python scripts/ci_cost_baseline.py check      # exit 1 if the document disagrees with the record

The record names the repository, the window (days, start and cutoff, UTC) and, per workflow,
the trigger events seen, the run count in the window, the conclusion counts, the wall time
p50 and p90 in minutes and the job minutes split by runner OS. Wall time is the run's
`run_started_at` to its `updated_at`, so it includes time a run spent waiting on a runner
approval; job minutes are each job's `started_at` to `completed_at`. Job minutes are measured
on a sample (the newest `sample_size` runs per workflow) and the sample is named beside them.

Billed dollars are 0 for a public repository on standard runners; the record observes the
billable milliseconds the run timing API reports for a few runs and says so. Anything the
forge could not answer is recorded `unknown` with the reason, never a number (sub-doctrine
10.f). Settings come only from `scripts/ci_cost_baseline.toml`. Every call is a `gh api` GET.
Promoting this to a `vibey-gh` command is a later step (SP1, CI-L).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.ci_cost_baseline_interface import (
        CiCostBaselineInterface,
        ClockInterface,
        GhActionsReaderInterface,
        RunnerOsInterface,
        StatisticsInterface,
    )
    from scripts.minimum_specs import SubprocessRunner, SystemClock
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.ci_cost_baseline_interface import (  # type: ignore[import-not-found,no-redef]
        CiCostBaselineInterface,
        ClockInterface,
        GhActionsReaderInterface,
        RunnerOsInterface,
        StatisticsInterface,
    )
    from minimum_specs import (  # type: ignore[import-not-found,no-redef]
        SubprocessRunner,
        SystemClock,
    )

SCRIPT = "scripts/ci_cost_baseline.py"
SCHEMA = "vibey-ci-cost-baseline/1"
DEFAULT_CONFIG = "scripts/ci_cost_baseline.toml"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
OS_KEYS = ("ubuntu", "macos", "windows", "other")


class ForgeUnavailable(Exception):
    """The forge could not answer; the message is the reason that is recorded."""


@dataclass(frozen=True)
class CiBaselineSettings:
    """Everything `scripts/ci_cost_baseline.toml` declares. Nothing here has a default in code:
    a key missing from the file is an error, not a silent value."""

    repo: str
    window_days: int
    sample_size: int
    per_page: int
    timeout_seconds: float
    timing_probe_runs: int
    output: str
    baseline: str
    document: str
    orientation_disabled: int
    related_records: Mapping[str, str]

    @classmethod
    def load(cls, path: Path) -> CiBaselineSettings:
        table = tomllib.loads(path.read_text(encoding="utf-8"))["ci_cost_baseline"]
        return cls(
            repo=table["repo"],
            window_days=table["window_days"],
            sample_size=table["sample_size"],
            per_page=table["per_page"],
            timeout_seconds=table["timeout_seconds"],
            timing_probe_runs=table["timing_probe_runs"],
            output=table["output"],
            baseline=table["baseline"],
            document=table["document"],
            orientation_disabled=table["orientation_disabled"],
            related_records=table["related_records"],
        )


class Statistics(StatisticsInterface):
    """Percentiles by linear interpolation between closest ranks (the numpy default)."""

    def percentile(self, values: Sequence[float], q: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        rank = (len(ordered) - 1) * q / 100
        low = int(rank)
        high = min(low + 1, len(ordered) - 1)
        return round(ordered[low] + (ordered[high] - ordered[low]) * (rank - low), 4)


class RunnerOs(RunnerOsInterface):
    """Maps runner labels to an operating system. A label that names none is `other`."""

    def of(self, labels: Sequence[str]) -> str:
        for label in labels:
            lowered = label.lower()
            for key in ("ubuntu", "macos", "windows"):
                if lowered.startswith(key):
                    return key
        return "other"


class GhActionsReader(GhActionsReaderInterface):
    """Reads the Actions API through `gh api` (a GET: no method flag, no field flag, ever)."""

    def __init__(self, runner: Any, repo: str, timeout: float) -> None:
        self._runner, self._repo, self._timeout = runner, repo, timeout
        self._calls = 0

    @property
    def calls(self) -> int:
        return self._calls

    @staticmethod
    def is_read_only(argv: Sequence[str]) -> bool:
        """True only for exactly `gh api repos/...`: no method, field, input or header flag."""
        return len(argv) == 3 and list(argv[:2]) == ["gh", "api"] and argv[2].startswith("repos/")

    def _get(self, path: str) -> dict[str, Any]:
        argv = ["gh", "api", path]
        if not self.is_read_only(argv):
            raise ValueError(f"refusing a call that is not a repos/ GET: {argv}")
        self._calls += 1
        done = self._runner.run(argv, timeout=self._timeout)
        if done.returncode != 0:
            detail = (done.stderr or done.stdout).strip().splitlines()
            raise ForgeUnavailable(
                f"gh api {path.partition('?')[0]} failed: {detail[-1] if detail else done.returncode}"[
                    :300
                ]
            )
        try:
            body = json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise ForgeUnavailable(
                f"gh api {path.partition('?')[0]} returned unreadable JSON: {exc}"
            ) from exc
        if not isinstance(body, dict):
            raise ForgeUnavailable(f"gh api {path.partition('?')[0]} returned a non-object")
        return body

    def repository(self) -> Mapping[str, Any]:
        return self._get(f"repos/{self._repo}")

    def workflows(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        page = 1
        while True:
            body = self._get(f"repos/{self._repo}/actions/workflows?per_page=100&page={page}")
            chunk = list(body.get("workflows", []))
            found.extend(chunk)
            if len(chunk) < 100:
                return found
            page += 1

    def runs_page(
        self, workflow_id: int, *, page: int, per_page: int, since: str | None
    ) -> tuple[int, list[dict[str, Any]]]:
        query = f"per_page={per_page}&page={page}"
        if since is not None:
            query += f"&created=>={since}"
        body = self._get(f"repos/{self._repo}/actions/workflows/{workflow_id}/runs?{query}")
        return int(body.get("total_count", 0)), list(body.get("workflow_runs", []))

    def jobs(self, run_id: int) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        page = 1
        while True:
            body = self._get(
                f"repos/{self._repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}"
            )
            chunk = list(body.get("jobs", []))
            found.extend(chunk)
            if len(chunk) < 100:
                return found
            page += 1

    def timing(self, run_id: int) -> Mapping[str, Any]:
        return self._get(f"repos/{self._repo}/actions/runs/{run_id}/timing")


class CiCostBaseline(CiCostBaselineInterface):
    """Collects the record. A workflow or probe the forge cannot answer is `unknown`, with why."""

    def __init__(
        self,
        settings: CiBaselineSettings,
        reader: GhActionsReaderInterface,
        clock: ClockInterface,
        statistics: StatisticsInterface | None = None,
        runner_os: RunnerOsInterface | None = None,
    ) -> None:
        self._settings, self._reader, self._clock = settings, reader, clock
        self._stats = statistics or Statistics()
        self._os = runner_os or RunnerOs()
        self._candidates: dict[str, list[int]] = {key: [] for key in OS_KEYS[:3]}
        self._other_labels: Counter[str] = Counter()

    @staticmethod
    def _parse(stamp: str | None) -> datetime | None:
        if not stamp:
            return None
        return datetime.strptime(stamp, TIME_FORMAT).replace(tzinfo=UTC)

    @staticmethod
    def _minutes(start: str | None, end: str | None) -> float | None:
        a, b = CiCostBaseline._parse(start), CiCostBaseline._parse(end)
        if a is None or b is None:
            return None
        return max((b - a).total_seconds(), 0.0) / 60

    def collect(self, since_days: int) -> dict[str, object]:
        cutoff = self._clock.now()
        start = (self._parse(cutoff) - timedelta(days=since_days)).strftime(TIME_FORMAT)  # type: ignore[operator]
        unknowns: list[str] = []
        try:
            flows = self._reader.workflows()
        except ForgeUnavailable as exc:
            return self._record(
                since_days, start, cutoff, [], {"status": "unknown", "reason": str(exc)}, [str(exc)]
            )
        rows: list[dict[str, Any]] = []
        self._candidates = {key: [] for key in OS_KEYS[:3]}
        self._other_labels = Counter()
        for flow in sorted(flows, key=lambda f: f["name"]):
            try:
                row = self._workflow(flow, start)
            except ForgeUnavailable as exc:
                row = self._identity(flow) | {"status": "unknown", "reason": str(exc)}
                unknowns.append(f"workflow {flow['name']}: {exc}")
            rows.append(row)
        cost = self._cost(unknowns)
        return self._record(since_days, start, cutoff, rows, cost, unknowns)

    @staticmethod
    def _identity(flow: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "id": flow["id"],
            "name": flow["name"],
            "path": flow["path"],
            "state": flow["state"],
        }

    def _workflow(self, flow: Mapping[str, Any], start: str) -> dict[str, Any]:
        cfg = self._settings
        per_page = min(cfg.per_page, cfg.sample_size)
        sampled: list[dict[str, Any]] = []
        total_in_window = 0
        crossed = False
        page = 1
        while len(sampled) < cfg.sample_size and not crossed:
            total, chunk = self._reader.runs_page(
                flow["id"], page=page, per_page=per_page, since=start
            )
            if page == 1:
                total_in_window = total
            for item in chunk:
                if item["created_at"] < start:
                    crossed = True
                    break
                if len(sampled) < cfg.sample_size:
                    sampled.append(item)
            if len(chunk) < per_page:
                break
            page += 1
        capped = (
            len(sampled) >= cfg.sample_size
            and (crossed is False)
            and total_in_window > len(sampled)
        )
        in_window = total_in_window if capped else len(sampled)

        if sampled:
            last = sampled[0]
        else:
            _, latest = self._reader.runs_page(flow["id"], page=1, per_page=1, since=None)
            last = latest[0] if latest else None
        last_run = (
            {
                "created_at": last["created_at"],
                "conclusion": last.get("conclusion") or last.get("status"),
                "event": last["event"],
            }
            if last
            else None
        )

        conclusions: Counter[str] = Counter()
        events: Counter[str] = Counter()
        walls: list[float] = []
        for item in sampled:
            events[item["event"]] += 1
            if item.get("conclusion"):
                conclusions[item["conclusion"]] += 1
                wall = self._minutes(
                    item.get("run_started_at") or item["created_at"], item.get("updated_at")
                )
                if wall is not None:
                    walls.append(wall)
            else:
                conclusions[item.get("status") or "unknown"] += 1

        minutes = dict.fromkeys(OS_KEYS, 0.0)
        no_jobs = no_timing = 0
        for item in sampled:
            jobs = self._reader.jobs(item["id"])
            if not jobs:
                no_jobs += 1
            for entry in jobs:
                spent = self._minutes(entry.get("started_at"), entry.get("completed_at"))
                if spent is None:
                    no_timing += 1
                    continue
                labels = entry.get("labels") or []
                bucket = self._os.of(labels)
                minutes[bucket] += spent
                if bucket == "other":
                    self._other_labels[",".join(labels) or "(no labels)"] += 1
                elif item.get("conclusion") and item["id"] not in self._candidates[bucket]:
                    self._candidates[bucket].append(item["id"])
        count = len(sampled)
        per_run = {k: round(v / count, 4) if count else 0.0 for k, v in minutes.items()}
        row = self._identity(flow) | {
            "status": "measured",
            "events": dict(sorted(events.items())),
            "runs_in_window": in_window,
            "runs_sampled": count,
            "sample_capped": capped,
            "conclusions": dict(conclusions),
            "wall_minutes": {
                "n": len(walls),
                "p50": self._stats.percentile(walls, 50),
                "p90": self._stats.percentile(walls, 90),
            },
            "jobs_sampled_runs": count,
            "runs_without_jobs": no_jobs,
            "jobs_without_timing": no_timing,
            "job_minutes_sampled": {k: round(v, 4) for k, v in minutes.items()},
            "job_minutes_per_run_mean": per_run,
            "last_run": last_run,
        }
        return row

    def _cost(self, unknowns: list[str]) -> dict[str, Any]:
        try:
            repo = self._reader.repository()
            visibility = str(
                repo.get("visibility") or ("private" if repo.get("private") else "public")
            )
        except ForgeUnavailable as exc:
            unknowns.append(f"repository visibility: {exc}")
            visibility = "unknown"
        probes: list[dict[str, Any]] = []
        for key in OS_KEYS[:3]:
            for run_id in self._candidates[key][: self._settings.timing_probe_runs]:
                try:
                    billable = self._reader.timing(run_id).get("billable") or {}
                except ForgeUnavailable as exc:
                    unknowns.append(f"run timing ({key}): {exc}")
                    continue
                probes.append(
                    {
                        "os": key,
                        "run_id": run_id,
                        "billable_keys": sorted(billable),
                        "total_ms": sum(int(v.get("total_ms", 0)) for v in billable.values()),
                    }
                )
        with_data = [p for p in probes if p["billable_keys"]]
        observed = sum(p["total_ms"] for p in with_data) if with_data else None
        covered = sorted({p["os"] for p in with_data})
        billed: int | None = None
        if visibility != "public":
            basis = f"unknown: repository visibility is {visibility}"
        elif not with_data:
            basis = (
                f"unknown: the run timing API returned no billable entries for {len(probes)} probed "
                "run(s), which is absent data, not a measured 0"
            )
        elif observed:
            basis = (
                f"unknown: the run timing API reported {observed} billable ms; dollars not derived"
            )
        else:
            billed = 0
            basis = (
                f"public repository: the run timing API returned billable entries with 0 billable ms for "
                f"{len(with_data)} probed run(s) covering runner OS {', '.join(covered)}; runner OS not "
                "probed are listed in `probes` (standard-runner status is not verified; see other_runner_labels)"
            )
        return {
            "billed_usd": billed,
            "repository_visibility": visibility,
            "billable_ms_observed": observed,
            "timing_probe_runs": len(probes),
            "billable_keys_seen": sorted({k for p in probes for k in p["billable_keys"]}),
            "probes": probes,
            "basis": basis,
            "real_costs": "queueing and wall time, not dollars",
        }

    def _record(
        self,
        days: int,
        start: str,
        cutoff: str,
        rows: list[dict[str, Any]],
        cost: dict[str, Any],
        unknowns: list[str],
    ) -> dict[str, object]:
        measured = [r for r in rows if r["status"] == "measured"]
        disabled = [
            {k: r[k] for k in ("id", "name", "path", "state")} | {"last_run": r.get("last_run")}
            for r in rows
            if r["state"] != "active"
        ]
        sampled_minutes = dict.fromkeys(OS_KEYS, 0.0)
        estimated = dict.fromkeys(OS_KEYS, 0.0)
        conclusions: Counter[str] = Counter()
        by_state: dict[str, dict[str, Any]] = {
            name: {
                "runs_in_window": 0,
                "job_minutes_estimated_for_window": dict.fromkeys(OS_KEYS, 0.0),
            }
            for name in ("active", "disabled")
        }
        for r in measured:
            conclusions.update(r["conclusions"])
            bucket = by_state["active" if r["state"] == "active" else "disabled"]
            bucket["runs_in_window"] += r["runs_in_window"]
            for key in OS_KEYS:
                sampled_minutes[key] += r["job_minutes_sampled"][key]
                spent = r["job_minutes_per_run_mean"][key] * r["runs_in_window"]
                estimated[key] += spent
                bucket["job_minutes_estimated_for_window"][key] += spent
        for bucket in by_state.values():
            bucket["job_minutes_estimated_for_window"] = {
                k: round(v, 2) for k, v in bucket["job_minutes_estimated_for_window"].items()
            }
        return {
            "schema": SCHEMA,
            "repo": self._settings.repo,
            "source": "gh api GET (repos/<repo>/actions/workflows, .../workflows/<id>/runs, .../runs/<id>/jobs, .../runs/<id>/timing)",
            "collected_at": cutoff,
            "window": {"days": days, "start": start, "cutoff": cutoff},
            "sample_size_per_workflow": self._settings.sample_size,
            "wall_time_definition": "run_started_at to updated_at of a completed run, in minutes; includes any wait on a runner",
            "job_minutes_definition": "started_at to completed_at of each job in the sampled runs, by runner OS from the job labels",
            "cost": cost,
            "workflows": rows,
            "disabled_workflows": sorted(disabled, key=lambda w: w["name"]),
            "totals": {
                "workflows_total": len(rows),
                "workflows_active": sum(1 for r in rows if r["state"] == "active"),
                "workflows_disabled_manually": sum(
                    1 for r in rows if r["state"] == "disabled_manually"
                ),
                "workflows_disabled_other": sum(
                    1 for r in rows if r["state"] not in ("active", "disabled_manually")
                ),
                "workflows_unknown": len(rows) - len(measured),
                "runs_in_window": sum(r["runs_in_window"] for r in measured),
                "runs_sampled": sum(r["runs_sampled"] for r in measured),
                "conclusions_in_sample": dict(conclusions),
                "job_minutes_sampled": {k: round(v, 2) for k, v in sampled_minutes.items()},
                "job_minutes_estimated_for_window": {k: round(v, 2) for k, v in estimated.items()},
                "estimate_basis": "per-workflow mean job minutes per sampled run times runs in window; an estimate, not a measurement",
            },
            "other_runner_labels": dict(sorted(self._other_labels.items())),
            "totals_by_state": by_state,
            "totals_by_state_note": "state is the workflow's state at the cutoff; a now-disabled workflow's runs in the window ran before it was disabled",
            "unknowns": unknowns,
            "api_calls": self._reader.calls,
        }

    # ------------------------------------------------------------------ rendering

    BLOCKS = ("provenance", "cost", "headline", "workflows")

    @staticmethod
    def _marker(name: str) -> re.Pattern[str]:
        return re.compile(
            rf"(?P<head><!-- BEGIN GENERATED ci-baseline:{name} — regenerated by {re.escape(SCRIPT)} -->\n)"
            rf"(?P<body>.*?)(?P<tail><!-- END GENERATED ci-baseline:{name} -->)",
            re.DOTALL,
        )

    @staticmethod
    def _fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.1f}"

    def _blocks(self, record: Mapping[str, Any]) -> dict[str, str]:
        w, t, c, bs = record["window"], record["totals"], record["cost"], record["totals_by_state"]
        names = sorted(
            record["workflows"], key=lambda x: (x["state"] == "active", x["name"].lower())
        )
        out: dict[str, str] = {}
        out["provenance"] = (
            f"**Object:** the GitHub Actions workflows of `{record['repo']}`. **Source:** read-only "
            f"`gh api` GET calls, collected by `{SCRIPT}` into the JSON record this table is "
            f"rendered from. **Window:** {w['days']} days, {w['start']} to {w['cutoff']} (UTC). "
            f"**Cutoff:** {w['cutoff']}. {record['api_calls']} API calls, {len(record['unknowns'])} "
            "unreadable workflows or probes.\n"
        )
        probed = ", ".join(f"{p['os']} run {p['run_id']}" for p in c["probes"]) or "none"
        billed = "unknown" if c["billed_usd"] is None else str(c["billed_usd"])
        observed = (
            "unknown" if c["billable_ms_observed"] is None else str(c["billable_ms_observed"])
        )
        other = (
            ", ".join(f"`{k}` ({v} jobs)" for k, v in record["other_runner_labels"].items())
            or "none"
        )
        out["cost"] = (
            f"- Billed dollars: **{billed}**. Basis: {c['basis']}.\n"
            f"- Repository visibility: **{c['repository_visibility']}**, read with `GET repos/<repo>`.\n"
            f"- Run timing probes (`GET repos/<repo>/actions/runs/<id>/timing`, one completed run per "
            f"runner OS where the window has one): {probed}. Billable keys seen: "
            f"{', '.join(c['billable_keys_seen']) or 'none'}. Billable ms observed: {observed}.\n"
            f"- Runner labels in the `other` bucket (not ubuntu, macos or windows): {other}.\n"
            "- The costs that remain are queueing and wall time (the table below), not dollars.\n"
        )
        est_a = bs["active"]["job_minutes_estimated_for_window"]
        est_d = bs["disabled"]["job_minutes_estimated_for_window"]
        minutes = lambda d: ", ".join(f"{k} {v:,.0f}" for k, v in d.items())  # noqa: E731
        out["headline"] = (
            f"- Workflows: {t['workflows_total']} ({t['workflows_active']} active, "
            f"{t['workflows_disabled_manually']} `disabled_manually`, {t['workflows_disabled_other']} "
            f"disabled otherwise, {t['workflows_unknown']} unreadable). An earlier orientation expected "
            f"about {self._settings.orientation_disabled} disabled workflows; the measurement found "
            f"{t['workflows_disabled_manually']}.\n"
            f"- Runs created in the window: {t['runs_in_window']} (the API's `total_count` for the window); "
            f"{t['runs_sampled']} sampled (newest {record['sample_size_per_workflow']} per workflow) for "
            "conclusions, wall time and job minutes.\n"
            f"- Job minutes in the sample, by runner OS: {minutes(t['job_minutes_sampled'])}.\n"
            "- Job minutes **estimated** for the whole window (per-workflow sample mean per run times runs "
            f"in the window; an estimate, not a measurement): workflows active at the cutoff "
            f"({bs['active']['runs_in_window']} runs) {minutes(est_a)}; workflows now disabled "
            f"({bs['disabled']['runs_in_window']} runs) {minutes(est_d)}.\n"
            "- Conclusions in the sample: "
            + ", ".join(f"{k} {v}" for k, v in sorted(t["conclusions_in_sample"].items()))
            + ".\n"
        )
        lines = [
            "| Workflow | State | Triggers seen (sample) | Runs in window | Last run | Wall p50 / p90 min | Why disabled |",
            "|---|---|---|---|---|---|---|",
        ]
        for x in names:
            if x["status"] != "measured":
                lines.append(
                    f"| {x['name']} | `{x['state']}` | unknown | unknown | unknown | unknown ({x['reason']}) | "
                    f"{'n/a, active' if x['state'] == 'active' else 'unknown, operator to say'} |"
                )
                continue
            ev = ", ".join(f"{k} {v}" for k, v in x["events"].items()) or "none in window"
            lr = x.get("last_run")
            last = f"{lr['created_at'][:10]}, {lr['conclusion']}" if lr else "never run"
            wm = x["wall_minutes"]
            wall = (
                f"{self._fmt(wm['p50'])} / {self._fmt(wm['p90'])} (n={wm['n']})"
                if wm["n"]
                else "n/a (no completed run in window)"
            )
            if x["state"] == "active":
                why = "n/a, active"
            else:
                related = self._settings.related_records.get(x["name"])
                why = "unknown, operator to say" + (
                    f". Related record: {related}" if related else ""
                )
            n = f"{x['runs_in_window']}" + (" (sample capped)" if x["sample_capped"] else "")
            lines.append(f"| {x['name']} | `{x['state']}` | {ev} | {n} | {last} | {wall} | {why} |")
        out["workflows"] = "\n".join(lines) + "\n"
        return out

    def render(self, record: Mapping[str, Any], document: str) -> str:
        """The document with each GENERATED block rewritten from the record. A block the
        document lacks is an error, never a silent skip."""
        blocks = self._blocks(record)
        for name in self.BLOCKS:
            pattern = self._marker(name)
            if not pattern.search(document):
                raise ValueError(f"the document has no GENERATED ci-baseline:{name} block")
            document = pattern.sub(
                lambda m, name=name: m["head"] + blocks[name] + m["tail"], document, count=1
            )
        return document


class CiCostBaselineCli:
    """The command line: `collect`, `render` and `check`.

    Exit status of `collect`: 0 when every read answered; 2 when the record was written but holds
    unknowns (listed on stderr); 1 when nothing was written, because the workflow listing itself
    could not be read or the output file exists and `--force` was not given."""

    def __init__(self, root: Path, runner: Any = None, clock: ClockInterface | None = None) -> None:
        self._root = root
        self._runner = runner or SubprocessRunner()
        self._clock = clock or _Clock()

    def run(self, argv: Sequence[str]) -> int:
        parser = argparse.ArgumentParser(
            prog="ci_cost_baseline.py", description=__doc__.splitlines()[0]
        )
        sub = parser.add_subparsers(dest="command", required=True)
        collect = sub.add_parser("collect", help="read the forge and write a new record")
        collect.add_argument("--since-days", type=int, default=None)
        collect.add_argument("--out", default=None, help="default: the TOML's output, stamped")
        collect.add_argument("--force", action="store_true", help="overwrite an existing record")
        for name, text in (
            ("render", "rewrite the document's GENERATED blocks from the record"),
            ("check", "exit 1 if the document's GENERATED blocks differ from the record"),
        ):
            cmd = sub.add_parser(name, help=text)
            cmd.add_argument("--baseline", default=None)
            cmd.add_argument("--document", default=None)
        for cmd in sub.choices.values():
            cmd.add_argument("--config", default=DEFAULT_CONFIG)
        args = parser.parse_args(list(argv))
        settings = CiBaselineSettings.load(self._root / args.config)
        if args.command == "collect":
            return self._collect(settings, args)
        return self._render(settings, args, check=args.command == "check")

    def _collect(self, settings: CiBaselineSettings, args: argparse.Namespace) -> int:
        reader = GhActionsReader(self._runner, settings.repo, settings.timeout_seconds)
        record = CiCostBaseline(settings, reader, self._clock).collect(
            args.since_days or settings.window_days
        )
        unknowns: list[str] = record["unknowns"]  # type: ignore[assignment]
        if not record["workflows"] and unknowns:
            print("the workflow listing could not be read; nothing written:", file=sys.stderr)
            print("\n".join(unknowns), file=sys.stderr)
            return 1
        stamp = str(record["collected_at"]).replace("-", "").replace(":", "")
        out = self._root / (args.out or settings.output.format(stamp=stamp))
        if out.exists() and not args.force:
            print(f"{out.name} exists; pass --force to overwrite it", file=sys.stderr)
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        totals: Mapping[str, Any] = record["totals"]  # type: ignore[assignment]
        print(
            f"wrote {out.name}: {totals['workflows_total']} workflows, {totals['runs_in_window']} "
            f"runs, {record['api_calls']} API calls, {len(unknowns)} unknown"
        )
        if unknowns:
            print("unknown (the record was written):\n" + "\n".join(unknowns), file=sys.stderr)
            return 2
        return 0

    def _render(self, settings: CiBaselineSettings, args: argparse.Namespace, check: bool) -> int:
        baseline = self._root / (args.baseline or settings.baseline)
        document = self._root / (args.document or settings.document)
        record = json.loads(baseline.read_text(encoding="utf-8"))
        current = document.read_text(encoding="utf-8")
        wanted = CiCostBaseline(settings, None, self._clock).render(record, current)  # type: ignore[arg-type]
        if check:
            if wanted != current:
                print(
                    f"{document.name} is out of step with {baseline.name}; run render",
                    file=sys.stderr,
                )
                return 1
            return 0
        document.write_text(wanted, encoding="utf-8")
        print(f"rewrote the generated blocks of {document.name} from {baseline.name}")
        return 0


class _Clock(ClockInterface):
    """UTC to the second, the format the record and the API's own stamps share."""

    def now(self) -> str:
        return SystemClock().now()[:19] + "Z"


if __name__ == "__main__":
    sys.exit(CiCostBaselineCli(Path.cwd()).run(sys.argv[1:]))
