#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measure how often the sovereign DESIGN and DECOMPOSE producers fail on a live model.

A live experiment, not a test: it talks to a real Ollama server, takes minutes, and its
numbers belong to the host it ran on. It lives under `scripts/` so the normal suite
never collects it.

Every request goes through the production code path -- `GptossloopDesignProvider.batch`
and `GptossloopWorkPlanProducer.decompose` over an `OllamaChatClient` built by
`from_environment` -- so the prompt, the output budget and the retry policy measured are
the ones a worker sends. The only addition is a recording transport between the client
and the real HTTP transport, which notes each exchange's budget, `done_reason`, content
and reasoning sizes and latency.

Outcome classes, per run:

- ``ok``: the producer returned a value.
- ``empty_content``: the last reply carried no content (``done_reason`` recorded).
- ``invalid_json``: content that is not JSON.
- ``schema_violation``: JSON missing a required key or carrying a wrong type.
- ``plan_rule_violation``: a well-formed plan that breaks a decomposition rule.
- ``transport_error`` / ``other``: anything else, named.

Usage::

    uv run python scripts/sovereign_retry_experiment.py --runs 10 --record out.json

Temperature is 0, so an unchanged prompt tends to repeat its answer: the synthetic
workloads vary the brief, stage and spec across runs rather than repeat one input.
"""

from __future__ import annotations

import argparse
import asyncio
import collections
import functools
import json
import os
import statistics
import sys
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from interfaces.sovereign_retry_experiment_interface import (  # noqa: E402
    ExchangeRecorderInterface,
    SovereignRetryExperimentInterface,
)

from vibey.application.design import DesignEvent, DesignStage  # noqa: E402
from vibey.domain.ledger import EventKind, Provenance  # noqa: E402
from vibey.domain.spec import (  # noqa: E402
    AcceptanceCriterion,
    Constraint,
    ConstraintKind,
    DesignSpec,
    NonFunctionalRequirement,
)
from vibey.infrastructure.engines.gptossloop_decompose import (  # noqa: E402
    GptossloopWorkPlanProducer,
)
from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider  # noqa: E402
from vibey.infrastructure.engines.interfaces.ollama_chat_interface import (  # noqa: E402
    OllamaTransportInterface,
)
from vibey.infrastructure.engines.ollama_chat import (  # noqa: E402
    OllamaChatClient,
    UrllibOllamaTransport,
)


class RepresentativeInputs:
    """The synthetic briefs and specs the experiment replays, plus the replay loader."""

    BRIEFS: tuple[str, ...] = (
        "Build a command-line todo list manager in Python: add, list, complete and delete "
        "tasks, stored in a JSON file in the user's home directory. Standard library only.",
        "Build a small HTTP URL-shortener service: POST a URL, get a short code, GET the "
        "code to be redirected. SQLite storage, must answer in under 50 ms on a laptop.",
        "Build a Python library that converts CSV files to JSON Lines, streaming, with a "
        "--schema option that validates column types and reports the first bad row.",
    )

    #: (objective, walking skeleton, [(given, when, then, fit), ...]) per spec.
    SPEC_SHAPES: tuple[tuple[str, str, tuple[tuple[str, str, str, str], ...]], ...] = (
        (
            "A command-line todo manager storing tasks in a JSON file.",
            "`todo add x` then `todo list` prints x.",
            (
                ("an empty store", "`todo add milk` runs", "the store holds one task", "read JSON"),
                ("one open task", "`todo list` runs", "it prints the task and id", "stdout"),
                ("one open task", "`todo done 1` runs", "the task is complete", "read JSON"),
                ("one task", "`todo rm 1` runs", "the store is empty", "read JSON"),
            ),
        ),
        (
            "An HTTP URL shortener with SQLite storage.",
            "POST /shorten then GET /<code> redirects.",
            (
                ("a running server", "a client POSTs a URL", "it gets a code", "http.client"),
                ("a stored code", "a client GETs /<code>", "it gets a 302", "http.client"),
                ("no stored code", "a client GETs a bad code", "it gets 404", "http.client"),
            ),
        ),
        (
            "A streaming CSV to JSON Lines converter library with schema validation.",
            "convert('a.csv') yields one dict per row.",
            (
                ("a CSV with a header", "convert() runs", "one dict per row", "compare"),
                ("an int schema", "a row has a non-int", "it raises naming the row", "raises"),
                ("a 1 GB CSV", "convert() streams it", "memory under 100 MB", "tracemalloc"),
                ("an empty CSV", "convert() runs", "it yields nothing", "compare"),
                ("quoted commas", "convert() runs", "quoted fields stay whole", "compare"),
            ),
        ),
    )

    @classmethod
    def specs(cls) -> tuple[DesignSpec, ...]:
        return tuple(
            DesignSpec(
                objective=objective,
                constraints=(Constraint("Python 3.12 standard library only", ConstraintKind.HARD),),
                non_goals=("a graphical interface",),
                criteria=tuple(
                    AcceptanceCriterion(
                        criterion_id=f"ac-{index}", given=given, when=when, then=then, fit=fit
                    )
                    for index, (given, when, then, fit) in enumerate(criteria, start=1)
                ),
                nfrs=(
                    NonFunctionalRequirement(
                        nfr_id="nfr-1",
                        attribute="latency",
                        scale="milliseconds per command",
                        meter="pytest timing over 100 invocations",
                        must="under 200",
                        wish="under 50",
                        fit_criterion="p95 under 200 ms",
                    ),
                ),
                walking_skeleton=skeleton,
            )
            for objective, skeleton, criteria in cls.SPEC_SHAPES
        )

    @staticmethod
    def brief_events(brief: str) -> tuple[DesignEvent, ...]:
        now = datetime(2026, 9, 29, tzinfo=UTC)
        return (
            DesignEvent(EventKind.TRANSCRIPT_RECORDED, Provenance.UNTRUSTED, now, {"text": brief}),
            DesignEvent(
                EventKind.PHASE_TRANSITIONED,
                Provenance.TRUSTED,
                now,
                {"from": "intake", "to": "design", "cycle": 1, "guard": None},
            ),
        )

    @staticmethod
    def replay_events(path: Path) -> tuple[DesignEvent, ...]:
        """DESIGN-phase ledger rows exported as JSON: kind, provenance, produced_at, payload."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return tuple(
            DesignEvent(
                kind=EventKind(str(row["kind"])),
                provenance=Provenance(str(row["provenance"])),
                produced_at=datetime.fromisoformat(str(row["produced_at"])),
                payload=dict(row["payload"]),
            )
            for row in raw
        )


class RecordingTransport(ExchangeRecorderInterface):
    """The real HTTP transport, with a note of every exchange it carried."""

    def __init__(self, inner: OllamaTransportInterface) -> None:
        self._inner = inner
        self._exchanges: list[dict[str, Any]] = []

    def reset(self) -> None:
        self._exchanges = []

    def exchanges(self) -> list[dict[str, Any]]:
        return list(self._exchanges)

    async def post_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> dict[str, object]:
        options = payload.get("options")
        options = options if isinstance(options, dict) else {}
        row: dict[str, Any] = {
            "format": "schema"
            if isinstance(payload.get("format"), dict)
            else payload.get("format"),
            "think": payload.get("think"),
            "num_ctx": options.get("num_ctx"),
            "num_predict": options.get("num_predict"),
        }
        started = time.monotonic()
        try:
            body = await self._inner.post_json(url, payload, timeout=timeout)
        except Exception as exc:
            row.update(seconds=round(time.monotonic() - started, 2), error=repr(exc))
            self._exchanges.append(row)
            raise
        message = body.get("message")
        message = message if isinstance(message, dict) else {}
        content = message.get("content")
        thinking = message.get("thinking")
        row.update(
            seconds=round(time.monotonic() - started, 2),
            done_reason=body.get("done_reason"),
            eval_count=body.get("eval_count"),
            prompt_eval_count=body.get("prompt_eval_count"),
            content_chars=len(content) if isinstance(content, str) else None,
            thinking_chars=len(thinking) if isinstance(thinking, str) else 0,
        )
        self._exchanges.append(row)
        return body


class SovereignRetryExperiment(SovereignRetryExperimentInterface):
    """N runs per workload through the production producers, classified and summarised."""

    def __init__(
        self,
        *,
        runs: int,
        workloads: Sequence[str],
        environ: Mapping[str, str],
        replay_events: Sequence[DesignEvent] = (),
        replay_stage: DesignStage = DesignStage.WALKING_SKELETON,
    ) -> None:
        self._runs = runs
        self._workloads = tuple(workloads)
        self._environ = environ
        self._replay_events = tuple(replay_events)
        self._replay_stage = replay_stage
        self._recorder = RecordingTransport(UrllibOllamaTransport())
        chat = OllamaChatClient.from_environment(environ, transport=self._recorder)
        self._model = chat.model
        self._design = GptossloopDesignProvider(chat=chat)
        self._decompose = GptossloopWorkPlanProducer(chat=chat)

    def _jobs(self) -> list[tuple[str, str, Callable[[], Awaitable[object]]]]:
        stages = tuple(DesignStage)
        jobs: list[tuple[str, str, Callable[[], Awaitable[object]]]] = []
        for index in range(self._runs):
            if "design" in self._workloads:
                stage = stages[index % len(stages)]
                briefs = RepresentativeInputs.BRIEFS
                events = RepresentativeInputs.brief_events(briefs[index % len(briefs)])
                jobs.append(
                    (
                        "design.interview",
                        f"{stage.value}/brief-{index % len(briefs)}",
                        functools.partial(self._design.batch, stage, events),
                    )
                )
            if "replay" in self._workloads and self._replay_events:
                jobs.append(
                    (
                        "design.interview (production replay)",
                        self._replay_stage.value,
                        functools.partial(
                            self._design.batch, self._replay_stage, self._replay_events
                        ),
                    )
                )
            if "decompose" in self._workloads:
                specs = RepresentativeInputs.specs()
                spec = specs[index % len(specs)]
                jobs.append(
                    (
                        "build.decompose",
                        f"spec-{index % len(specs)}",
                        functools.partial(self._decompose.decompose, spec),
                    )
                )
        return jobs

    async def run(self) -> dict[str, Any]:
        started_at = datetime.now(UTC)
        rows: list[dict[str, Any]] = []
        for workload, label, call in self._jobs():
            self._recorder.reset()
            began = time.monotonic()
            error: BaseException | None = None
            try:
                await call()
            except Exception as exc:  # noqa: BLE001 - every failure is a measured outcome
                error = exc
            exchanges = self._recorder.exchanges()
            row = {
                "workload": workload,
                "label": label,
                "seconds": round(time.monotonic() - began, 2),
                "outcome": self._classify(error, exchanges),
                "error": None if error is None else f"{type(error).__name__}: {error}"[:300],
                "exchanges": exchanges,
            }
            rows.append(row)
            print(
                f"{workload:<40} {label:<28} {row['outcome']:<20} "
                f"{row['seconds']:>7.1f}s calls={len(exchanges)} "
                f"done={[e.get('done_reason') for e in exchanges]}",
                file=sys.stderr,
                flush=True,
            )
        return {
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "model": self._model,
            "runs_per_workload": self._runs,
            "environment": {
                key: self._environ.get(key)
                for key in (
                    "VIBEY_OLLAMA_URL",
                    "VIBEY_OLLAMA_MODEL",
                    "VIBEY_OLLAMA_CONTEXT",
                    "VIBEY_OLLAMA_OUTPUT",
                    "VIBEY_OLLAMA_FIT",
                    "VIBEY_OLLAMA_RETRY_THINK",
                )
            },
            "summary": self._summarise(rows),
            "runs": rows,
        }

    @staticmethod
    def _classify(error: BaseException | None, exchanges: Sequence[Mapping[str, Any]]) -> str:
        if error is None:
            return "ok"
        if not exchanges or "error" in exchanges[-1]:
            return "transport_error"
        if not exchanges[-1].get("content_chars"):
            return "empty_content"
        if isinstance(error, json.JSONDecodeError):
            return "invalid_json"
        if "invalid decomposition" in str(error):
            return "plan_rule_violation"
        if isinstance(error, (KeyError, TypeError, ValueError)):
            return "schema_violation"
        return "other"

    @staticmethod
    def _summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        by_workload: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
        for row in rows:
            by_workload[str(row["workload"])].append(row)
        summary: dict[str, Any] = {}
        for workload, items in by_workload.items():
            outcomes = collections.Counter(str(item["outcome"]) for item in items)
            first_calls = [item["exchanges"][0] for item in items if item["exchanges"]]
            summary[workload] = {
                "n": len(items),
                "outcomes": dict(outcomes),
                "ok_rate": round(outcomes["ok"] / len(items), 3),
                "empty_content_rate": round(outcomes["empty_content"] / len(items), 3),
                "schema_violation_rate": round(outcomes["schema_violation"] / len(items), 3),
                "empty_content_done_reasons": dict(
                    collections.Counter(
                        str(item["exchanges"][-1].get("done_reason"))
                        for item in items
                        if item["outcome"] == "empty_content"
                    )
                ),
                "first_call_empty_rate": round(
                    sum(1 for call in first_calls if not call.get("content_chars")) / len(items), 3
                ),
                "first_call_done_reasons": dict(
                    collections.Counter(str(call.get("done_reason")) for call in first_calls)
                ),
                "mean_seconds": round(
                    statistics.fmean(float(item["seconds"]) for item in items), 1
                ),
                "mean_calls": round(statistics.fmean(len(item["exchanges"]) for item in items), 2),
            }
        return summary


def main(argv: list[str] | None = None) -> int:
    """Entry point; a function only because argparse's CLI contract is one."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=10, help="runs per workload")
    parser.add_argument("--workloads", default="design,decompose")
    parser.add_argument("--replay-ledger", type=Path, help="exported DESIGN events (JSON)")
    parser.add_argument("--replay-stage", default=DesignStage.WALKING_SKELETON.value)
    parser.add_argument("--record", type=Path, help="write the full JSON record here")
    args = parser.parse_args(argv)
    workloads = [item.strip() for item in args.workloads.split(",") if item.strip()]
    replay = RepresentativeInputs.replay_events(args.replay_ledger) if args.replay_ledger else ()
    if replay and "replay" not in workloads:
        workloads.append("replay")
    experiment = SovereignRetryExperiment(
        runs=args.runs,
        workloads=workloads,
        environ=os.environ,
        replay_events=replay,
        replay_stage=DesignStage(args.replay_stage),
    )
    record = asyncio.run(experiment.run())
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": record["model"], "summary": record["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
