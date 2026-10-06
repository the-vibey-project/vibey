# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How long each request to the local model took, recorded -- and then read back as rates.

Measured 2026-10: on GitHub's `ubuntu-24.04-arm` CPU runner the sovereign review either
answered in 4 to 13 minutes or gave no verdict at about 158 to 160 minutes, eleven times.
Its deadline is scaled from `--prompt-tokens-per-second 40 --output-tokens-per-second 2`,
figures carried over from another machine, and nothing recorded what each request sent,
how long it was given, how long it ran, or what the model's own counters said. So before
anything about the deadline changes, it is measured:

- `RequestLog` is what `vibey-gh local-review` writes into its outcome record's `requests`:
  one entry per request attempt and one per one-token slot probe, each with what it sent,
  the deadline it was given and how that was derived, how long it took, its outcome in
  `vibey_gh.review_outcome`'s closed vocabulary, and -- when the model answered -- Ollama's
  own counters. Recording changes nothing a review decides.
- `ReviewTimings` (`vibey-gh review-timings`) reads those records back, read-only, and
  reports per model and runner the rates the model was observed to sustain, which requests
  timed out and at what size, and the rates a deadline could conservatively be scaled from
  -- a suggestion from a stated number of observations, never a measurement it did not make.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibey_gh import review_outcome as outcome
from vibey_gh.interfaces.review_timings_interface import (
    RequestLogInterface,
    ReviewTimingsInterface,
)

__all__ = [
    "MINIMUM_OBSERVATIONS",
    "REQUEST",
    "RUNNER_VARIABLES",
    "SLOT_PROBE",
    "RequestLog",
    "ReviewTimings",
    "RunnerLabel",
    "TimingsGroup",
    "TimingsReport",
]

# The two kinds of entry. A slot probe is the one-token request that waits for the model to
# come free before a review request is sent (`local_review.SlotWait`); it is marked as such
# so its tiny prompt is never read as the model's reading rate.
REQUEST = "request"
SLOT_PROBE = "slot_probe"

# The runner's own statement of where it is, from the variables every Actions runner sets.
RUNNER_VARIABLES: dict[str, str] = {
    "environment": "RUNNER_ENVIRONMENT",
    "os": "RUNNER_OS",
    "arch": "RUNNER_ARCH",
    "name": "RUNNER_NAME",
}

# Ollama reports durations in nanoseconds; recorded in seconds.
_NANOSECONDS = 1_000_000_000
_DURATIONS = (
    ("prompt_eval_duration", "prompt_eval_seconds"),
    ("eval_duration", "eval_seconds"),
    ("load_duration", "load_seconds"),
    ("total_duration", "total_seconds"),
)

# Below this many answered requests a group gets no suggested rates: "not enough data".
MINIMUM_OBSERVATIONS = 5


class RequestLog(RequestLogInterface):
    """Every request one review made of the model, in order (`RequestLogInterface`).

    `clock` is the seam every elapsed time is read from (`time.monotonic`, looked up when
    called, without one). `on_change` is told every entry each time one opens or closes, so
    a caller can keep a record on disk that a cancelled or killed process leaves behind
    with the request it was waiting on still named.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] | None = None,
        on_change: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> None:
        self._clock = clock
        self._on_change = on_change
        self._began = self._now()
        self._entries: list[dict[str, Any]] = []
        self._opened: dict[int, float] = {}
        self._part = (1, 1)
        self._attempt = 0

    def _now(self) -> float:
        return (self._clock or time.monotonic)()

    def _changed(self) -> None:
        if self._on_change is not None:
            self._on_change(self.entries())

    def part(self, index: int, count: int) -> None:
        self._part = (index, count)
        self._attempt = 0

    def attempt(self) -> int:
        self._attempt += 1
        return self._attempt

    def open(self, kind: str, **fields: Any) -> int:
        now = self._now()
        index = len(self._entries)
        self._entries.append(
            {
                "kind": kind,
                "part": self._part[0],
                "of": self._part[1],
                "attempt": self._attempt,
                "at_seconds": round(now - self._began, 3),
                # Every entry carries every field, so a record written mid-request reads
                # the same way as one written after: unfinished, nothing answered yet.
                "finished": False,
                "elapsed_seconds": None,
                "code": None,
                "answered": False,
                "ollama": None,
                **fields,
            }
        )
        self._opened[index] = now
        self._changed()
        return index

    def close(self, index: int, **fields: Any) -> None:
        entry = self._entries[index]
        entry.update(fields)
        entry["finished"] = True
        entry["elapsed_seconds"] = round(self._now() - self._opened.pop(index), 3)
        self._changed()

    def entries(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in self._entries]

    @staticmethod
    def _number(value: object) -> float | None:
        """`value` as a finite, non-negative number, or None: a malformed counter is not
        read as a figure."""
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        if not math.isfinite(value) or value < 0:
            return None
        return float(value)

    @staticmethod
    def _rate(count: float | None, seconds: float | None) -> float | None:
        if count is None or not seconds:
            return None
        return round(count / seconds, 3)

    def figures(self, body: object) -> dict[str, Any] | None:
        if not isinstance(body, Mapping):
            return None
        said: dict[str, Any] = {}
        for name in ("prompt_eval_count", "eval_count"):
            count = self._number(body.get(name))
            if count is not None:
                said[name] = int(count)
        for name, seconds in _DURATIONS:
            nanoseconds = self._number(body.get(name))
            if nanoseconds is not None:
                said[seconds] = round(nanoseconds / _NANOSECONDS, 3)
        said["prompt_tokens_per_second"] = self._rate(
            self._number(body.get("prompt_eval_count")), said.get("prompt_eval_seconds")
        )
        said["output_tokens_per_second"] = self._rate(
            self._number(body.get("eval_count")), said.get("eval_seconds")
        )
        reason = body.get("done_reason")
        if isinstance(reason, str):
            said["done_reason"] = reason
        return said


@dataclass(frozen=True)
class RunnerLabel:
    """Which runner a review ran on, as its environment states it (`RunnerLabelInterface`,
    by shape: a frozen dataclass cannot inherit a protocol's read-only properties)."""

    environment: str = ""
    os: str = ""
    arch: str = ""
    name: str = ""

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> RunnerLabel:
        return cls(
            **{key: str(environ.get(variable, "")) for key, variable in RUNNER_VARIABLES.items()}
        )

    @classmethod
    def from_record(cls, said: object) -> RunnerLabel:
        """The label a record carries; nothing stated for anything that is not a string."""
        if not isinstance(said, Mapping):
            return cls()
        return cls(
            **{key: value for key in RUNNER_VARIABLES if isinstance(value := said.get(key), str)}
        )

    def as_json(self) -> dict[str, str]:
        return {key: getattr(self, key) for key in RUNNER_VARIABLES if getattr(self, key)}

    def describe(self, *, with_name: bool = False) -> str:
        words = [word for word in (self.environment, self.os, self.arch) if word]
        if with_name and self.name:
            words.append(self.name)
        return " ".join(words) or "a runner that stated nothing about itself"


@dataclass(frozen=True)
class TimingsGroup:
    """The requests of every record made by one model on one kind of runner, and what they
    show (`TimingsGroupInterface`, by shape). Rates are Ollama's own counters, from answered
    requests only, never from a slot probe; percentiles are nearest-rank."""

    model: str
    runner: RunnerLabel
    records: int
    untimed: int
    entries: tuple[Mapping[str, Any], ...]
    names: tuple[str, ...] = ()
    minimum: int = MINIMUM_OBSERVATIONS
    with_name: bool = False

    # ------------------------------------------------------------------ the arithmetic

    @staticmethod
    def percentile(values: Sequence[float], fraction: float) -> float:
        """The nearest-rank percentile: the smallest value at least `fraction` of the values
        are no greater than. Never interpolated, so it is always a value that was observed."""
        ordered = sorted(values)
        return ordered[max(1, math.ceil(fraction * len(ordered))) - 1]

    @classmethod
    def spread(cls, values: Sequence[float]) -> dict[str, Any] | None:
        if not values:
            return None
        return {
            "n": len(values),
            "median": round(statistics.median(values), 3),
            "p10": round(cls.percentile(values, 0.10), 3),
            "p90": round(cls.percentile(values, 0.90), 3),
        }

    # ------------------------------------------------------------------ what was asked

    def _of(self, kind: str) -> list[Mapping[str, Any]]:
        return [entry for entry in self.entries if entry.get("kind") == kind]

    @staticmethod
    def _figures(entry: Mapping[str, Any]) -> Mapping[str, Any]:
        figures = entry.get("ollama")
        return figures if isinstance(figures, Mapping) else {}

    @staticmethod
    def _positive(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
            return None
        return float(value)

    def observed(self) -> list[Mapping[str, Any]]:
        """Every finished review request the model answered with both of its rates."""
        return [
            entry
            for entry in self._of(REQUEST)
            if entry.get("finished") is True
            and self._positive(self._figures(entry).get("prompt_tokens_per_second")) is not None
            and self._positive(self._figures(entry).get("output_tokens_per_second")) is not None
        ]

    def _rates(self, name: str) -> list[float]:
        return [float(self._figures(entry)[name]) for entry in self.observed()]

    @staticmethod
    def _codes(entries: Sequence[Mapping[str, Any]], answered: str) -> dict[str, int]:
        tally = Counter(
            str(entry.get("code") or answered) for entry in entries if entry.get("finished") is True
        )
        return dict(sorted(tally.items(), key=lambda item: (-item[1], item[0])))

    def timed_out(self) -> list[dict[str, Any]]:
        """Every review request that ran out of time, smallest prompt first."""
        found = [
            {
                "prompt_tokens_estimated": entry.get("prompt_tokens_estimated"),
                "deadline_seconds": entry.get("deadline_seconds"),
                "elapsed_seconds": entry.get("elapsed_seconds"),
            }
            for entry in self._of(REQUEST)
            if entry.get("code") == outcome.MODEL_TIMEOUT
        ]
        return sorted(found, key=lambda said: self._positive(said["prompt_tokens_estimated"]) or 0)

    def declared(self) -> list[dict[str, Any]]:
        """Each distinct basis the requests' deadlines were derived from."""
        seen: dict[tuple[Any, ...], dict[str, Any]] = {}
        for entry in self._of(REQUEST):
            basis = entry.get("deadline")
            if not isinstance(basis, Mapping):
                continue
            said = {
                key: basis.get(key)
                for key in ("prompt_tokens_per_second", "output_tokens_per_second", "floor_seconds")
            }
            seen.setdefault(tuple(said.values()), said)
        return [seen[key] for key in sorted(seen, key=repr)]

    def suggestion(self) -> dict[str, Any]:
        """The rates a deadline could be scaled from: the 10th percentile of each observed
        rate, rounded down and never under 1 -- conservative, since a deadline too short
        costs the verdict and one too long costs only time. Only from at least `minimum`
        answered requests; below that there is not enough data to suggest anything."""
        observations = len(self.observed())
        said: dict[str, Any] = {
            "enough": observations >= self.minimum,
            "observations": observations,
            "minimum": self.minimum,
            "prompt_tokens_per_second": None,
            "output_tokens_per_second": None,
        }
        if said["enough"]:
            for name in ("prompt_tokens_per_second", "output_tokens_per_second"):
                said[name] = max(1, math.floor(self.percentile(self._rates(name), 0.10)))
        return said

    # ------------------------------------------------------------------ the report

    def as_json(self) -> dict[str, Any]:
        requests = self._of(REQUEST)
        probes = self._of(SLOT_PROBE)
        observed = self.observed()
        counted = [
            float(self._figures(entry)["prompt_eval_count"])
            / float(entry["prompt_tokens_estimated"])
            for entry in observed
            if self._positive(self._figures(entry).get("prompt_eval_count")) is not None
            and self._positive(entry.get("prompt_tokens_estimated")) is not None
        ]
        loads = [
            float(load)
            for entry in self.entries
            if (load := self._positive(self._figures(entry).get("load_seconds"))) is not None
        ]
        return {
            "model": self.model,
            "runner": self.runner.as_json(),
            "runner_names": list(self.names),
            "records": self.records,
            "records_without_timings": self.untimed,
            "requests": len(requests),
            "unfinished": sum(1 for entry in requests if entry.get("finished") is not True),
            "request_codes": self._codes(requests, outcome.REVIEWED),
            "slot_probes": len(probes),
            "slot_probe_codes": self._codes(probes, "answered"),
            "answered": len(observed),
            "prompt_tokens_per_second": self.spread(self._rates("prompt_tokens_per_second")),
            "output_tokens_per_second": self.spread(self._rates("output_tokens_per_second")),
            "prompt_tokens_counted_per_estimated": self.spread(counted),
            "load_seconds": self.spread(loads),
            "timed_out": self.timed_out(),
            "declared": self.declared(),
            "suggestion": self.suggestion(),
        }

    @staticmethod
    def _said(spread: Mapping[str, Any] | None, unit: str) -> str:
        if spread is None:
            return f"{unit}: none observed"
        return (
            f"{unit}: median {spread['median']}, p10 {spread['p10']}, p90 {spread['p90']}"
            f" (from {spread['n']})"
        )

    @staticmethod
    def _tally(counts: Mapping[str, int]) -> str:
        return ", ".join(f"{name} {count}" for name, count in counts.items()) or "none"

    def render(self) -> list[str]:
        said = self.as_json()
        names = f" ({len(self.names)} runner name(s))" if self.names and not self.with_name else ""
        lines = [f"{self.model} on {self.runner.describe(with_name=self.with_name)}{names}"]
        lines.append(
            f"  {said['records']} record(s), {said['records_without_timings']} with no request"
            f" timings; {said['requests']} request(s), {said['unfinished']} unfinished;"
            f" {said['slot_probes']} slot probe(s)"
        )
        lines.append(f"  request outcomes: {self._tally(said['request_codes'])}")
        if said["slot_probes"]:
            lines.append(f"  slot probe outcomes: {self._tally(said['slot_probe_codes'])}")
        lines.append("  " + self._said(said["prompt_tokens_per_second"], "prompt tokens/s"))
        lines.append("  " + self._said(said["output_tokens_per_second"], "output tokens/s"))
        lines.append(
            "  "
            + self._said(
                said["prompt_tokens_counted_per_estimated"],
                "prompt tokens Ollama counted per token estimated",
            )
        )
        lines.append("  " + self._said(said["load_seconds"], "model load seconds"))
        timed_out = said["timed_out"]
        if timed_out:
            lines.append(f"  timed out: {len(timed_out)}, at")
            for each in timed_out:
                lines.append(
                    f"    ~{each['prompt_tokens_estimated']} estimated prompt tokens"
                    f" (deadline {each['deadline_seconds']}s, ran {each['elapsed_seconds']}s)"
                )
        else:
            lines.append("  timed out: none")
        for basis in said["declared"]:
            if basis["prompt_tokens_per_second"]:
                lines.append(
                    "  deadlines were scaled at --prompt-tokens-per-second"
                    f" {basis['prompt_tokens_per_second']} --output-tokens-per-second"
                    f" {basis['output_tokens_per_second']}, never under"
                    f" {basis['floor_seconds']}s"
                )
            else:
                lines.append(f"  deadlines were the fixed timeout of {basis['floor_seconds']}s")
        suggestion = said["suggestion"]
        if suggestion["enough"]:
            lines.append(
                f"  suggested: --prompt-tokens-per-second {suggestion['prompt_tokens_per_second']}"
                f" --output-tokens-per-second {suggestion['output_tokens_per_second']}"
                f" (a suggestion from {suggestion['observations']} answered request(s): the"
                " 10th percentile of each observed rate, rounded down)"
            )
        else:
            lines.append(
                f"  suggested: not enough data -- {suggestion['observations']} answered"
                f" request(s), at least {suggestion['minimum']} needed"
            )
        return lines


@dataclass(frozen=True)
class TimingsReport:
    """Every group's timings, what was read, what was skipped and when
    (`TimingsReportInterface`, by shape)."""

    read_at: str
    paths: tuple[str, ...]
    read: tuple[str, ...]
    skipped: tuple[tuple[str, str], ...]
    groups: tuple[TimingsGroup, ...] = field(default_factory=tuple)

    def as_json(self) -> dict[str, Any]:
        return {
            "read_at": self.read_at,
            "paths": list(self.paths),
            "read": list(self.read),
            "skipped": [{"path": path, "why": why} for path, why in self.skipped],
            "groups": [group.as_json() for group in self.groups],
        }

    def render(self) -> str:
        lines = [
            (
                f"Sovereign review request timings: {len(self.read)} local-review outcome"
                f" record(s) from {len(self.paths)} path(s), {len(self.skipped)} file(s)"
                f" skipped; read {self.read_at}"
            ),
        ]
        if not self.groups:
            lines.append("No local-review outcome records were found, so nothing is reported.")
        else:
            lines.append(
                "Rates are Ollama's own counters (prompt_eval_count / prompt_eval_duration,"
                " eval_count / eval_duration) from answered review requests, never a slot"
                " probe; percentiles are nearest-rank."
            )
        for group in self.groups:
            lines.append("")
            lines.extend(group.render())
        if self.skipped:
            lines.append("")
            lines.append("Skipped, never counted:")
            for path, why in self.skipped:
                lines.append(f"  {path}: {why}")
        return "\n".join(lines) + "\n"


class ReviewTimings(ReviewTimingsInterface):
    """Reads local-review outcome records and reports their request timings, read-only
    (`ReviewTimingsInterface`). `minimum` is the fewest answered requests a group needs for
    a suggestion; `by_name` keeps each runner name apart (a hosted runner's name is unique
    to its machine, so by default it is not part of the group); `clock` is the seam the
    report's read time comes from."""

    def __init__(
        self,
        *,
        minimum: int = MINIMUM_OBSERVATIONS,
        by_name: bool = False,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if type(minimum) is not int or minimum < 1:
            raise ValueError("the minimum number of answered requests must be at least 1")
        self._minimum = minimum
        self._by_name = by_name
        self._clock = clock

    @staticmethod
    def _files(path: Path) -> list[Path]:
        if path.is_dir():
            return sorted(found for found in path.rglob("*.json") if found.is_file())
        return [path]

    def records(
        self, paths: Sequence[Path]
    ) -> tuple[list[tuple[str, Mapping[str, Any]]], list[tuple[str, str]]]:
        read: list[tuple[str, Mapping[str, Any]]] = []
        skipped: list[tuple[str, str]] = []
        for path in paths:
            if not path.exists():
                skipped.append((str(path), "no such file or directory"))
                continue
            for file in self._files(path):
                try:
                    record = json.loads(file.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, ValueError) as error:
                    skipped.append((str(file), f"unreadable: {error}"))
                    continue
                schema = record.get("schema") if isinstance(record, dict) else None
                if schema != outcome.LOCAL_SCHEMA:
                    why = (
                        f"not a local-review outcome record (schema {schema!r}, expected"
                        f" {outcome.LOCAL_SCHEMA!r})"
                    )
                    skipped.append((str(file), why))
                    continue
                read.append((str(file), record))
        return read, skipped

    def report(self, paths: Sequence[Path]) -> TimingsReport:
        read, skipped = self.records(paths)
        grouped: dict[tuple[str, ...], dict[str, Any]] = {}
        for _, record in read:
            model = str(record.get("model") or "") or "(model not recorded)"
            stated = RunnerLabel.from_record(record.get("runner"))
            # By default a runner's name is not part of its group: a hosted runner's is
            # unique to its machine, so every run would be a group of one.
            runner = (
                stated if self._by_name else RunnerLabel(stated.environment, stated.os, stated.arch)
            )
            key = (model, runner.environment, runner.os, runner.arch, runner.name)
            group = grouped.setdefault(
                key,
                {
                    "model": model,
                    "runner": runner,
                    "records": 0,
                    "untimed": 0,
                    "entries": [],
                    "names": set(),
                },
            )
            group["records"] += 1
            if not self._by_name and stated.name:
                group["names"].add(stated.name)
            requests = record.get("requests")
            if not isinstance(requests, list):
                group["untimed"] += 1
                continue
            group["entries"].extend(entry for entry in requests if isinstance(entry, Mapping))
        groups = tuple(
            TimingsGroup(
                model=said["model"],
                runner=said["runner"],
                records=said["records"],
                untimed=said["untimed"],
                entries=tuple(said["entries"]),
                names=tuple(sorted(said["names"])),
                minimum=self._minimum,
                with_name=self._by_name,
            )
            for _, said in sorted(grouped.items())
        )
        read_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime((self._clock or time.time)()))
        return TimingsReport(
            read_at=read_at,
            paths=tuple(str(path) for path in paths),
            read=tuple(path for path, _ in read),
            skipped=tuple(skipped),
            groups=groups,
        )

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "paths",
            nargs="+",
            type=Path,
            metavar="PATH",
            help=(
                "a `local-review --outcome` record, or a directory searched recursively for"
                " them (a downloaded pr-review-sovereign artifact, say)"
            ),
        )
        parser.add_argument(
            "--minimum",
            type=int,
            default=MINIMUM_OBSERVATIONS,
            help=(
                "the fewest answered requests a group needs before rates are suggested"
                f" (default {MINIMUM_OBSERVATIONS})"
            ),
        )
        parser.add_argument(
            "--by-runner-name",
            action="store_true",
            help="keep each runner name apart; a hosted runner's name is unique to its machine",
        )
        parser.add_argument("--json", action="store_true", help="print the report as JSON")
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        try:
            timings = cls(minimum=args.minimum, by_name=args.by_runner_name)
        except ValueError as error:
            print(f"vibey-gh review-timings: {error}", file=sys.stderr)
            return 2
        return timings.run(args.paths, as_json=args.json)

    def run(self, paths: Sequence[Path], *, as_json: bool = False) -> int:
        """Print the report; 0 when at least one record was read, 1 when none was."""
        report = self.report(paths)
        if as_json:
            print(json.dumps(report.as_json(), indent=2))
        else:
            print(report.render(), end="")
        if not report.read:
            print(
                "vibey-gh review-timings: no local-review outcome record was read",
                file=sys.stderr,
            )
            return 1
        return 0
