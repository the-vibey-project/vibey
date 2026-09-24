# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Recompute the empirical numbers in docs/paper.md from tracked sources (#155, #192).

Three sources, all inside this repository, and nothing else: the rung table of the
sovereignty stress record, a compact extraction of the local Qwen storm run logs, and
this checkout's git history. Nothing is estimated, fetched or remembered, so anyone
holding the checkout can reproduce every figure the paper states:

    python scripts/paper_evidence.py          # the report
    python scripts/paper_evidence.py --json   # the same numbers, machine-readable

Every threshold the report applies is a flag whose default is the value the paper uses.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import date, datetime
from itertools import accumulate, pairwise
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from interfaces.paper_evidence_interface import (
    GitHistoryInterface,
    PaperEvidenceInterface,
    QwenStormRecordInterface,
    StressRecordInterface,
    StressRung,
)

DEFAULT_STRESS_RECORD = "src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md"
DEFAULT_QWEN_STORM_RECORD = "src/vibey_tools/gh/docs/qwenloop-storm-2026-09-20.json"
DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_REGION = (2, 32)
DEFAULT_FIT_MAX = 16
DEFAULT_WORK_UNITS = 100.0
DEFAULT_RELEASE_TAG_GLOB = "vibey-v*"
# The family's own development begins here. Earlier commits reachable from HEAD are the
# predecessor history of vibey-bootstrap (2026-04-09 to 2026-06-29), absorbed with it
# (ADR-0021); counted in the totals, they are left out of the per-day and per-hour figures.
DEFAULT_SINCE = "2026-08-09"
DEFAULT_REVISION = "HEAD"

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_TOTALS = re.compile(r"\*\*Totals\*\*:\s*(\d+) generations attempted,\s*(\d+) succeeded")
_PR_SUBJECT = re.compile(r"\(#\d+\)$")


class StressRecord(StressRecordInterface):
    """The stress record's rung table, parsed as printed and summarised without fitting."""

    def __init__(
        self,
        path: Path,
        region: tuple[int, int] = DEFAULT_REGION,
        fit_max: int = DEFAULT_FIT_MAX,
        work_units: float = DEFAULT_WORK_UNITS,
    ) -> None:
        self._path = path
        self._text = path.read_text(encoding="utf-8")
        self._region = region
        self._fit_max = fit_max
        self._work_units = work_units

    @staticmethod
    def _number(cell: str) -> float:
        match = _NUMBER.search(cell)
        if match is None:
            raise ValueError(f"no number in table cell {cell!r}")
        return float(match.group(0))

    def rungs(self) -> tuple[StressRung, ...]:
        rows: list[StressRung] = []
        in_table = False
        for line in self._text.splitlines():
            if line.startswith("| Concurrency"):
                in_table = True
                continue
            if not in_table:
                continue
            if not line.startswith("|"):
                break
            cells = [cell.strip().strip("*").strip() for cell in line.strip("|").split("|")]
            if set(cells[0]) <= set("-: "):
                continue
            succeeded, attempted = (int(part) for part in cells[1].split("/"))
            rows.append(
                StressRung(
                    concurrency=int(cells[0]),
                    attempted=attempted,
                    succeeded=succeeded,
                    p50_seconds=self._number(cells[3]),
                    max_seconds=self._number(cells[4]),
                    throughput_per_minute=self._number(cells[5]),
                )
            )
        if not rows:
            raise ValueError(f"{self._path}: no rung table found")
        return tuple(rows)

    @staticmethod
    def _log_log_slope(rungs: list[StressRung]) -> float:
        xs = [math.log(r.concurrency) for r in rungs]
        ys = [math.log(r.throughput_per_minute) for r in rungs]
        x_bar, y_bar = statistics.fmean(xs), statistics.fmean(ys)
        num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys, strict=True))
        den = sum((x - x_bar) ** 2 for x in xs)
        return num / den

    @staticmethod
    def _verdict(rate: float, band: tuple[float, float]) -> str:
        if rate < band[0]:
            return "below"
        return "above" if rate > band[1] else "inside"

    @staticmethod
    def _point(rung: StressRung) -> dict[str, float]:
        return {
            "concurrency": rung.concurrency,
            "throughput": rung.throughput_per_minute,
            "success": rung.succeeded / rung.attempted,
        }

    def summary(self) -> dict[str, Any]:
        rungs = list(self.rungs())
        attempted = sum(r.attempted for r in rungs)
        succeeded = sum(r.succeeded for r in rungs)
        declared = _TOTALS.search(self._text)

        perfect: list[StressRung] = []
        for rung in rungs:
            if rung.succeeded != rung.attempted:
                break
            perfect.append(rung)

        low, high = self._region
        region = [r for r in rungs if low <= r.concurrency <= high]
        rates = [r.throughput_per_minute for r in region]
        fitted = [r.throughput_per_minute for r in region if r.concurrency <= self._fit_max]
        band = (min(fitted), max(fitted))
        held_out = [r for r in region if r.concurrency > self._fit_max]
        serial = next((r for r in rungs if r.concurrency == 1), None)
        return {
            "record": str(self._path),
            "rungs": len(rungs),
            "attempted": attempted,
            "succeeded": succeeded,
            "success_rate": succeeded / attempted,
            "declared_totals": [int(g) for g in declared.groups()] if declared else None,
            "cumulative_attempted": list(accumulate(r.attempted for r in rungs)),
            "all_succeeded_through": {
                "concurrency": perfect[-1].concurrency if perfect else None,
                "generations": sum(r.attempted for r in perfect),
            },
            "serial_throughput_per_minute": serial.throughput_per_minute if serial else None,
            "region": {
                "concurrency": [low, high],
                "rungs": len(region),
                "attempted": sum(r.attempted for r in region),
                "succeeded": sum(r.succeeded for r in region),
                "rung_success_min": min(r.succeeded / r.attempted for r in region),
                "rung_success_max": max(r.succeeded / r.attempted for r in region),
                "throughput_min": min(rates),
                "throughput_max": max(rates),
                "throughput_mean": statistics.fmean(rates),
                "throughput_sd": statistics.stdev(rates),
                "throughput_cv": statistics.stdev(rates) / statistics.fmean(rates),
                "log_log_slope": self._log_log_slope(region),
            },
            "held_out_check": {
                "fitted_through": self._fit_max,
                "band": list(band),
                "held_out": [
                    {**self._point(r), "verdict": self._verdict(r.throughput_per_minute, band)}
                    for r in held_out
                ],
            },
            "t0_minutes": {
                "work_units": self._work_units,
                "lower": self._work_units / max(rates),
                "upper": self._work_units / min(rates),
                "serial": self._work_units / serial.throughput_per_minute if serial else None,
            },
            "peak": self._point(max(rungs, key=lambda r: r.throughput_per_minute)),
            "last": self._point(rungs[-1]),
        }


class GitHistory(GitHistoryInterface):
    """This checkout's history at HEAD: what was produced, when, and what was released."""

    def __init__(
        self,
        repo: Path,
        timezone: str = DEFAULT_TIMEZONE,
        release_tag_glob: str = DEFAULT_RELEASE_TAG_GLOB,
        since: date | None = None,
        revision: str = DEFAULT_REVISION,
    ) -> None:
        self._repo = repo
        self._timezone = timezone
        self._zone = ZoneInfo(timezone)
        self._release_tag_glob = release_tag_glob
        self._since = since
        self._revision = revision

    def _git(self, *args: str) -> str:
        # push-gate: not a push (reads tags and history for the paper's evidence)
        done = subprocess.run(
            ["git", *args], cwd=self._repo, check=True, capture_output=True, text=True
        )
        return done.stdout

    def _local(self, stamp: str) -> datetime:
        return datetime.fromtimestamp(int(stamp), self._zone)

    def _release_tags(self, until: int) -> list[tuple[datetime, str]]:
        # Every matching tag created by the revision's own commit time, reachable or not:
        # promotion rebases onto the release branch, so early tags sit on lines the
        # integration branch no longer contains, and they were releases all the same.
        listing = self._git(
            "for-each-ref", "--format=%(refname:short) %(creatordate:unix)", "refs/tags"
        )
        tags = []
        for line in listing.splitlines():
            name, stamp = line.rsplit(" ", 1)
            if fnmatch.fnmatch(name, self._release_tag_glob) and int(stamp) <= until:
                tags.append((self._local(stamp), name))
        return sorted(tags)

    def summary(self) -> dict[str, Any]:
        rev = self._revision
        every = [self._local(line) for line in self._git("log", "--format=%at", rev).split()]
        stamps = [s for s in every if self._since is None or s.date() >= self._since]
        per_day = Counter(stamp.date() for stamp in stamps)
        per_hour = Counter(stamp.hour for stamp in stamps)
        days = sorted(per_day)
        gaps = [((later - earlier).days - 1, earlier, later) for earlier, later in pairwise(days)]
        gap, after, before = max(gaps) if gaps else (0, None, None)
        hours: list[tuple[int, int]] = sorted(per_hour.items())
        quietest = min(hours, key=lambda hour: (hour[1], hour[0]))
        busiest = max(hours, key=lambda hour: (hour[1], -hour[0]))
        tags = self._release_tags(int(self._git("log", "-1", "--format=%ct", rev)))
        counts = list(per_day.values())
        count_sd = statistics.stdev(counts) if len(counts) > 1 else 0.0
        subjects = self._git("log", "--format=%s", rev).splitlines()
        return {
            "head": self._git("rev-parse", rev).strip(),
            "timezone": self._timezone,
            "commits": int(self._git("rev-list", "--count", rev)),
            "root_histories": len(self._git("rev-list", "--max-parents=0", rev).split()),
            "first_commit": min(every).isoformat(),
            "last_commit": max(every).isoformat(),
            "since": self._since.isoformat() if self._since else None,
            "window_commits": len(stamps),
            "active_days": len(days),
            "commits_per_active_day": {
                "min": min(counts),
                "median": statistics.median(counts),
                "max": max(counts),
                "mean": statistics.fmean(counts),
                "sd": count_sd,
                "cv": count_sd / statistics.fmean(counts),
            },
            "longest_inactive_gap": {
                "days": gap,
                "after": after.isoformat() if after else None,
                "before": before.isoformat() if before else None,
            },
            "hours_with_commits": len(per_hour),
            "quietest_hour": list(quietest),
            "busiest_hour": list(busiest),
            "pull_request_subjects": sum(1 for s in subjects if _PR_SUBJECT.search(s)),
            "release_tags": {
                "glob": self._release_tag_glob,
                "count": len(tags),
                "first": [tags[0][1], tags[0][0].isoformat()] if tags else None,
                "last": [tags[-1][1], tags[-1][0].isoformat()] if tags else None,
            },
        }


class QwenStormRecord(QwenStormRecordInterface):
    """Summarise a tracked, cutoff-bounded extraction of qwenloop event logs."""

    def __init__(self, path: Path) -> None:
        self._path = path
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"{path}: top-level record must be an object")
        self._record: dict[str, Any] = loaded

    @staticmethod
    def _non_negative_int(value: object, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} must be a non-negative integer")
        return value

    @classmethod
    def _int(cls, run: dict[str, Any], key: str) -> int:
        return cls._non_negative_int(run.get(key), f"qwen storm run field {key!r}")

    def summary(self) -> dict[str, Any]:
        raw_runs = self._record.get("runs")
        if not isinstance(raw_runs, list) or not all(isinstance(run, dict) for run in raw_runs):
            raise ValueError(f"{self._path}: runs must be a list of objects")
        runs = [run for run in raw_runs if isinstance(run, dict)]
        dispositions = [str(run.get("disposition", "")) for run in runs]
        observed_server = self._record.get("observed_server", {})
        model = observed_server.get("model", "") if isinstance(observed_server, dict) else ""
        active_processes = self._non_negative_int(
            self._record.get("active_storm_processes_at_cutoff", 0),
            f"{self._path}: field 'active_storm_processes_at_cutoff'",
        )
        return {
            "record": str(self._path),
            "observed_at": str(self._record.get("observed_at", "")),
            "timezone": str(self._record.get("timezone", "")),
            "active_storm_processes": active_processes,
            "model": str(model),
            "requested_settings": self._record.get("requested_settings", {}),
            "observed_server": observed_server,
            "runs": len(runs),
            "completed_runs": sum(run.get("disposition") == "completed" for run in runs),
            "verdict_runs": sum(bool(run.get("verdict_emitted")) for run in runs),
            "completion_marker_runs": sum(
                bool(run.get("completion_marker_emitted")) for run in runs
            ),
            "turns": sum(self._int(run, "turns") for run in runs),
            "tool_calls": sum(self._int(run, "tool_calls") for run in runs),
            "input_tokens": sum(self._int(run, "input_tokens") for run in runs),
            "output_tokens": sum(self._int(run, "output_tokens") for run in runs),
            "file_write_calls": sum(self._int(run, "file_write_calls") for run in runs),
            "bytes_written": sum(self._int(run, "bytes_written") for run in runs),
            "empty_runs": dispositions.count("no_events_at_cutoff"),
            "incomplete_runs": sum(run.get("disposition") != "completed" for run in runs),
        }


class PaperEvidence(PaperEvidenceInterface):
    """The tracked sources, composed and rendered as the report the paper cites."""

    def __init__(
        self,
        stress: StressRecordInterface,
        history: GitHistoryInterface,
        qwen_storm: QwenStormRecordInterface | None = None,
    ) -> None:
        self._stress = stress
        self._history = history
        self._qwen_storm = qwen_storm

    def collect(self) -> dict[str, Any]:
        history = self._history.summary()
        return {
            "revision": history["head"],
            "stress": self._stress.summary(),
            "history": history,
            "qwen_storm": self._qwen_storm.summary() if self._qwen_storm else None,
        }

    def render(self, evidence: dict[str, Any]) -> str:
        s, h = evidence["stress"], evidence["history"]
        q = evidence["qwen_storm"]
        region, check, t0 = s["region"], s["held_out_check"], s["t0_minutes"]
        low, high = region["concurrency"]
        perfect, gap, tags = (
            s["all_succeeded_through"],
            h["longest_inactive_gap"],
            h["release_tags"],
        )
        per_day = h["commits_per_active_day"]
        held = ", ".join(
            f"N={item['concurrency']} {item['throughput']:.2f} ({item['verdict']})"
            for item in check["held_out"]
        )
        lines = [
            f"paper evidence at {evidence['revision']}",
            "",
            f"stress record: {s['record']}",
            f"  {s['rungs']} rungs: {s['succeeded']}/{s['attempted']} succeeded "
            f"({s['success_rate']:.1%}); the record's own totals line: {s['declared_totals']}",
            f"  every generation succeeded through N={perfect['concurrency']} "
            f"({perfect['generations']} generations)",
            f"  serial baseline N=1: {s['serial_throughput_per_minute']:.2f}/min",
            f"  region N={low}..{high}, {region['rungs']} rungs: "
            f"{region['succeeded']}/{region['attempted']} succeeded "
            f"({region['succeeded'] / region['attempted']:.1%}); rung success "
            f"{region['rung_success_min']:.1%}..{region['rung_success_max']:.1%}",
            f"  region throughput/min: {region['throughput_min']:.2f}.."
            f"{region['throughput_max']:.2f}, mean {region['throughput_mean']:.2f}, "
            f"sample sd {region['throughput_sd']:.2f} (cv {region['throughput_cv']:.0%}), "
            f"log-log slope on N {region['log_log_slope']:.2f}",
            f"  band fitted through N={check['fitted_through']}: "
            f"{check['band'][0]:.2f}..{check['band'][1]:.2f}; held out: {held}",
            f"  T0 for {t0['work_units']:g} units in the region: "
            f"{t0['lower']:.0f}..{t0['upper']:.0f} min (serial rate alone: {t0['serial']:.0f} min)",
            f"  peak {s['peak']['throughput']:.2f}/min at N={s['peak']['concurrency']} "
            f"({s['peak']['success']:.1%} success); last rung N={s['last']['concurrency']} "
            f"{s['last']['throughput']:.2f}/min at {s['last']['success']:.1%}",
            f"  cumulative attempted by rung: {s['cumulative_attempted']}",
        ]
        if q is not None:
            requested = q["requested_settings"]
            observed = q["observed_server"]
            lines.extend(
                [
                    "",
                    f"qwenloop storm record: {q['record']}",
                    f"  observed at {q['observed_at']} ({q['timezone']}), model {q['model']}",
                    f"  runs {q['completed_runs']}/{q['runs']} completed; "
                    f"{q['completion_marker_runs']} emitted the completion marker; "
                    f"{q['verdict_runs']} emitted a verdict; {q['empty_runs']} had no events; "
                    f"{q['active_storm_processes']} processes were alive at cutoff",
                    f"  turns {q['turns']}, tool calls {q['tool_calls']}, "
                    f"tokens in/out {q['input_tokens']}/{q['output_tokens']}",
                    f"  writes {q['file_write_calls']} calls / {q['bytes_written']} bytes; "
                    f"requested context {requested.get('context_length')}, "
                    f"observed context {observed.get('context_length')}",
                ]
            )
        lines.extend(
            [
                "",
                f"git history ({h['timezone']}):",
                f"  commits reachable from the revision: {h['commits']} "
                f"across {h['root_histories']} "
                f"root histories, {h['first_commit']} .. {h['last_commit']}",
                f"  since {h['since']}: {h['window_commits']} commits",
                f"  active days {h['active_days']}; commits per active day min/median/max "
                f"{per_day['min']}/{per_day['median']}/{per_day['max']}, mean "
                f"{per_day['mean']:.1f}, sample sd {per_day['sd']:.1f} (cv {per_day['cv']:.0%})",
                f"  longest inactive gap: {gap['days']} days ({gap['after']} .. {gap['before']})",
                f"  hours of the day with commits: {h['hours_with_commits']}/24; "
                f"quietest {h['quietest_hour']}, busiest {h['busiest_hour']} [hour, commits]",
                f"  subjects ending in (#N): {h['pull_request_subjects']}",
                f"  release tags {tags['glob']}: {tags['count']}, first {tags['first']}, "
                f"last {tags['last']}",
            ]
        )
        return "\n".join(lines)


# A bare function because it is this script's `__main__` entry point (ADR-0016): it only
# parses flags, wires the three classes together and prints.
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--rev", default=DEFAULT_REVISION, help="the revision to read history at")
    parser.add_argument("--stress", default=DEFAULT_STRESS_RECORD, help="relative to --repo")
    parser.add_argument(
        "--qwen-storm",
        default=DEFAULT_QWEN_STORM_RECORD,
        help="relative path to the tracked local Qwen storm record",
    )
    parser.add_argument(
        "--no-qwen-storm",
        action="store_true",
        help="omit the local Qwen storm record",
    )
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--region-min", type=int, default=DEFAULT_REGION[0])
    parser.add_argument("--region-max", type=int, default=DEFAULT_REGION[1])
    parser.add_argument("--fit-max", type=int, default=DEFAULT_FIT_MAX)
    parser.add_argument("--work-units", type=float, default=DEFAULT_WORK_UNITS)
    parser.add_argument("--release-tag-glob", default=DEFAULT_RELEASE_TAG_GLOB)
    parser.add_argument(
        "--since", default=DEFAULT_SINCE, help="first day of the per-day figures; '' for all"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the report")
    args = parser.parse_args(argv)

    stress = StressRecord(
        args.repo / args.stress,
        region=(args.region_min, args.region_max),
        fit_max=args.fit_max,
        work_units=args.work_units,
    )
    since = date.fromisoformat(args.since) if args.since else None
    history = GitHistory(args.repo, args.timezone, args.release_tag_glob, since, args.rev)
    qwen_storm = None if args.no_qwen_storm else QwenStormRecord(args.repo / args.qwen_storm)
    evidence = PaperEvidence(stress, history, qwen_storm)
    collected = evidence.collect()
    print(json.dumps(collected, indent=2, default=str) if args.json else evidence.render(collected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
