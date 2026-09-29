# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Why a pull request's review produced a verdict, or did not -- recorded, then counted.

An audit of 150 runs of the review workflow found the gate published 10 successes, 46
failures and 75 skips, and the sovereign diff review ran 16 times. Why, nobody could say
without opening each run: the reasons existed only as prose -- "the diff (~57195 tokens)
exceeds the sovereign model's window", "local model unreachable or timed out" -- worded
where they happened and recorded nowhere a program could read.

So every run now leaves a record in a small, CLOSED vocabulary:

- `lane`: what the evaluation decided about who reviews this head (`LANES`).
- `code`: why there is a verdict, or why there is none (`CODES`). A code outside the
  vocabulary is a malformed record, never a new category invented on the fly.
- `verdict`: `pass`, `fail`, or `none`.

Two records per run, each an artifact of the run: the evaluation's (`pr-review-lane`),
which is all there is when the gate never runs -- scans still pending, a merge conflict --
and the gate's (`pr-review-outcome`), which supersedes it. The gate also writes its record
into the check run's `output.text`, so it is readable beside the verdict it explains.

`ReviewOutcomeReader` is the read-only half: it lists the last runs of the workflow and
tabulates their records. It never writes. A run whose record expired, could not be
downloaded, or is not well formed is counted as exactly that -- a figure over an unknown
subset is not evidence (sub-doctrine 10.g) -- and the table states its object, its source,
the span of runs it covers and when it was read (sub-doctrine 10.f).
"""

from __future__ import annotations

import json
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.review_outcome_interface import (
    OutcomeVocabularyInterface,
    ReviewOutcomeReaderInterface,
)

__all__ = [
    "CODES",
    "LANES",
    "LANE_ARTIFACT",
    "LANE_SCHEMA",
    "LOCAL_SCHEMA",
    "OUTCOME_ARTIFACT",
    "OUTCOME_SCHEMA",
    "REVIEW_OUTCOMES",
    "VERDICTS",
    "OutcomeTable",
    "OutcomeVocabulary",
    "ReviewOutcomeReader",
    "RunRecord",
]

# Which record a file is, by its first field. Versioned, so a later shape is told apart
# rather than misread.
LANE_SCHEMA = "vibey-gh.review-lane/1"
OUTCOME_SCHEMA = "vibey-gh.review-outcome/1"
LOCAL_SCHEMA = "vibey-gh.local-review/1"

# The artifact each record travels in, and the one file inside it.
LANE_ARTIFACT = "pr-review-lane"
OUTCOME_ARTIFACT = "pr-review-outcome"
RECORD_FILE = "record.json"

# --- the lane decision -----------------------------------------------------------------------

SOVEREIGN_WHOLE = "sovereign_whole"
SOVEREIGN_CARRIES = "sovereign_carries"
SOVEREIGN_RESERVE = "sovereign_reserve"
PAID_ONLY = "paid_only"
NO_LANE = "none"

LANES: dict[str, str] = {
    SOVEREIGN_WHOLE: "no paid review is declared (8.b); the sovereign lane answers the whole review",
    SOVEREIGN_CARRIES: "the sovereign lane carries the diff half; the paid lane answers the rest",
    SOVEREIGN_RESERVE: "the paid lane reviews; the sovereign verdict is held in reserve",
    PAID_ONLY: "the paid lane reviews alone; the sovereign lane was not offered",
    NO_LANE: "no automated reviewer was offered this head",
}

# --- the verdict -------------------------------------------------------------------------------

PASS = "pass"
FAIL = "fail"
NO_VERDICT = "none"
VERDICTS = (PASS, FAIL, NO_VERDICT)

# --- the outcome codes -------------------------------------------------------------------------
# A verdict was produced.
REVIEWED = "reviewed"
# The evaluation's own answers, when no review was due or none could be offered.
NO_PULL_REQUEST = "no_pull_request"
SCANS_PENDING = "scans_pending"
SCANS_FAILING = "scans_failing"
BLOCKED = "blocked"
MERGE_CONFLICT = "merge_conflict"
PAID_LANE_DECLARED_OFF = "paid_lane_declared_off"
FORK_HEAD = "fork_head"
UNTRUSTED_AUTHOR = "untrusted_author"
LANE_DISABLED = "lane_disabled"
LANE_NOT_READY = "lane_not_ready"
GATE_NOT_REACHED = "gate_not_reached"
# The sovereign lane's job, before the model is asked.
TOOLING_UNAVAILABLE = "tooling_unavailable"
DIFF_UNAVAILABLE = "diff_unavailable"
HEAD_MOVED = "head_moved"
DOCUMENTS_UNAVAILABLE = "documents_unavailable"
EMPTY_DIFF = "empty_diff"
# Sizing the request.
DIFF_EXCEEDS_LIMIT = "diff_exceeds_limit"
DIFF_EXCEEDS_WINDOW = "diff_exceeds_window"
CHUNK_BUDGET_EXCEEDED = "chunk_budget_exceeded"
# Asking the model, and reading its answer.
MODEL_UNREACHABLE = "model_unreachable"
MODEL_TIMEOUT = "model_timeout"
MODEL_REFUSED = "model_refused"
PROMPT_TRUNCATED = "prompt_truncated"
ANSWER_INCOMPLETE = "answer_incomplete"
ANSWER_UNUSABLE = "answer_unusable"
# After the model answered.
RECORD_FAILED = "record_failed"
# The declared paid lane.
PAID_REVIEW_REFUSED = "paid_review_refused"
PAID_REVIEW_NO_VERDICT = "paid_review_no_verdict"
# The last resort: said, never guessed.
JOB_FAILED = "job_failed"
UNKNOWN = "unknown"

CODES: dict[str, str] = {
    REVIEWED: "a verdict was produced for the exact head",
    NO_PULL_REQUEST: "the run was not associated with an open pull request",
    SCANS_PENDING: "the exact head's scans had not settled, so no review was due yet",
    SCANS_FAILING: "completed checks were failing, and a bounded paid repair was due",
    BLOCKED: "automation was blocked pending operator action",
    MERGE_CONFLICT: "the head conflicts with its base, and a paid resolution was due",
    PAID_LANE_DECLARED_OFF: "the work needs a paid lane, and none is declared (8.b)",
    FORK_HEAD: "the head is in a fork, which never reaches the self-hosted sovereign runner",
    UNTRUSTED_AUTHOR: "the author is not trusted, and the sovereign lane reviews trusted authors only",
    LANE_DISABLED: "the sovereign lane is switched off ([pr_automation.fallback] enabled = false)",
    LANE_NOT_READY: "the sovereign runner's heartbeat was missing or stale",
    GATE_NOT_REACHED: "the evaluation ran, but the run ended before the gate recorded an outcome",
    TOOLING_UNAVAILABLE: "the tooling could not be installed on the self-hosted runner",
    DIFF_UNAVAILABLE: "the exact-head diff could not be fetched",
    HEAD_MOVED: "the pull request's head moved while its diff was fetched",
    DOCUMENTS_UNAVAILABLE: "the documents the whole review judges could not be fetched",
    EMPTY_DIFF: "the fetched diff was empty, which is a fetch failure, not an approvable change",
    DIFF_EXCEEDS_LIMIT: "the diff is past max_diff_chars and could not be split to fit it",
    DIFF_EXCEEDS_WINDOW: "one indivisible part of the diff is too large for the model's window",
    CHUNK_BUDGET_EXCEEDED: "the diff needs more chunks than max_chunks allows",
    MODEL_UNREACHABLE: "the local model could not be reached, retries included",
    MODEL_TIMEOUT: "the local model did not answer in time, retries included",
    MODEL_REFUSED: "the model server refused the request",
    PROMPT_TRUNCATED: "the model may not have read the whole prompt",
    ANSWER_INCOMPLETE: "the model's answer was not a complete verdict",
    ANSWER_UNUSABLE: "the model's answer was not a verdict at all",
    RECORD_FAILED: "a verdict was produced but could not be recorded as the review",
    PAID_REVIEW_REFUSED: "the paid review call was refused, and no fallback verdict stood in",
    PAID_REVIEW_NO_VERDICT: "the paid review returned no verdict, and no fallback verdict stood in",
    JOB_FAILED: "the review job failed before any reason could be named",
    UNKNOWN: "a reason was expected and none could be read",
}

# Where each record came from, and what a run is when neither answered.
SOURCE_GATE = "gate"
SOURCE_EVALUATE = "evaluate"
SOURCE_NONE = "none"
SOURCE_EXPIRED = "expired"
SOURCE_UNREADABLE = "unreadable"
SOURCE_IN_PROGRESS = "in_progress"
SOURCES = (
    SOURCE_GATE,
    SOURCE_EVALUATE,
    SOURCE_NONE,
    SOURCE_EXPIRED,
    SOURCE_UNREADABLE,
    SOURCE_IN_PROGRESS,
)

# The fields every record carries, and the schema each artifact must hold.
_REQUIRED = ("schema", "lane", "code", "verdict")
_SCHEMA_BY_ARTIFACT = {OUTCOME_ARTIFACT: OUTCOME_SCHEMA, LANE_ARTIFACT: LANE_SCHEMA}


@dataclass(frozen=True)
class OutcomeVocabulary:
    """The closed vocabulary (`OutcomeVocabularyInterface`, by shape: a frozen dataclass
    cannot inherit a protocol's read-only properties). Constructor arguments default to this module's tables, so an
    adopter with more lanes or codes constructs its own rather than editing these."""

    lanes: Mapping[str, str] = field(default_factory=lambda: dict(LANES))
    verdicts: tuple[str, ...] = VERDICTS
    codes: Mapping[str, str] = field(default_factory=lambda: dict(CODES))

    def describe(self, code: str) -> str:
        return self.codes.get(code, f"not in the vocabulary: {code!r}")

    def problems(self, record: Mapping[str, Any]) -> list[str]:
        said = [f"missing {name!r}" for name in _REQUIRED if name not in record]
        schema = record.get("schema")
        if "schema" in record and schema not in (LANE_SCHEMA, OUTCOME_SCHEMA):
            said.append(f"schema {schema!r} is not a review record")
        for name, allowed in (
            ("lane", self.lanes),
            ("code", self.codes),
            ("verdict", self.verdicts),
        ):
            if name in record and record[name] not in allowed:
                said.append(f"{name} {record[name]!r} is not in the vocabulary")
        return said


# The vocabulary the workflow records in, and the reader reads by.
REVIEW_OUTCOMES: OutcomeVocabularyInterface = OutcomeVocabulary()


@dataclass(frozen=True)
class RunRecord:
    """One run, and the record that answered for it (`RunRecordInterface`, by shape)."""

    run_id: int
    created_at: str
    conclusion: str
    source: str
    record: Mapping[str, Any] | None = None
    problem: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "conclusion": self.conclusion,
            "source": self.source,
            "record": dict(self.record) if self.record is not None else None,
            "problem": self.problem,
        }


@dataclass(frozen=True)
class OutcomeTable:
    """The records of a stated span of runs, counted (`OutcomeTableInterface`, by shape)."""

    repository: str
    workflow: str
    limit: int
    read_at: str
    runs: tuple[RunRecord, ...]
    vocabulary: OutcomeVocabularyInterface = field(default_factory=lambda: REVIEW_OUTCOMES)

    def _readable(self) -> list[Mapping[str, Any]]:
        return [
            run.record
            for run in self.runs
            if run.record is not None and run.source in (SOURCE_GATE, SOURCE_EVALUATE)
        ]

    def counts(self, key: str) -> dict[str, int]:
        tally = Counter(str(record.get(key, "")) for record in self._readable())
        return dict(sorted(tally.items(), key=lambda item: (-item[1], item[0])))

    def sources(self) -> dict[str, int]:
        tally = Counter(run.source for run in self.runs)
        return {source: tally.get(source, 0) for source in SOURCES}

    def span(self) -> dict[str, Any]:
        if not self.runs:
            return {"runs": 0}
        oldest, newest = self.runs[-1], self.runs[0]
        return {
            "runs": len(self.runs),
            "oldest": {"run_id": oldest.run_id, "created_at": oldest.created_at},
            "newest": {"run_id": newest.run_id, "created_at": newest.created_at},
        }

    def as_json(self) -> dict[str, Any]:
        return {
            "repository": self.repository,
            "workflow": self.workflow,
            "asked_for": self.limit,
            "read_at": self.read_at,
            "span": self.span(),
            "sources": self.sources(),
            "lanes": self.counts("lane"),
            "codes": self.counts("code"),
            "verdicts": self.counts("verdict"),
            "runs": [run.as_json() for run in self.runs],
        }

    def render(self) -> str:
        span = self.span()
        lines = [
            (
                f"Review outcomes: {self.repository}, workflow {self.workflow},"
                f" the last {span['runs']} run(s) (asked for {self.limit}); read {self.read_at}"
            ),
        ]
        if not self.runs:
            lines.append("No runs of the workflow were found, so nothing is counted.")
            return "\n".join(lines) + "\n"
        oldest, newest = span["oldest"], span["newest"]
        lines.append(
            f"Span: run {oldest['run_id']} ({oldest['created_at']}) to run"
            f" {newest['run_id']} ({newest['created_at']})."
        )
        lines.append(
            "Records: "
            + ", ".join(f"{count} {source}" for source, count in self.sources().items())
            + ". Only gate and evaluate records are counted below; every other run is"
            " named at the end, never folded in."
        )
        for title, key, table in (
            ("Lane decision", "lane", self.vocabulary.lanes),
            ("Outcome code", "code", self.vocabulary.codes),
            ("Verdict", "verdict", None),
        ):
            lines.append("")
            lines.append(f"{title}:")
            counted = self.counts(key)
            if not counted:
                lines.append("  (no readable records)")
            width = max((len(name) for name in counted), default=0)
            for name, count in counted.items():
                meaning = ""
                if table is not None:
                    meaning = "  " + table.get(name, f"not in the vocabulary: {name!r}")
                lines.append(f"  {name.ljust(width)}  {count:>4}{meaning}")
        missing = [run for run in self.runs if run.source not in (SOURCE_GATE, SOURCE_EVALUATE)]
        if missing:
            lines.append("")
            lines.append("Runs with no readable record:")
            for run in missing:
                why = f": {run.problem}" if run.problem else ""
                lines.append(
                    f"  run {run.run_id} ({run.created_at}, {run.conclusion}) {run.source}{why}"
                )
        return "\n".join(lines) + "\n"


Clock = Callable[[], float]


class ReviewOutcomeReader(ReviewOutcomeReaderInterface):
    """Lists the review workflow's last runs and reads the record each one left. Read-only:
    every call is a GET through the forge client, and downloads land in a temporary
    directory that is removed afterwards.

    `repository` is `owner/name`; empty lets the forge client resolve it from the working
    directory, as `gh` does. `transport` is the seam every call goes through.
    """

    def __init__(
        self,
        repository: str = "",
        *,
        workflow: str = "pr-review.yml",
        transport: GhTransportInterface | None = None,
        vocabulary: OutcomeVocabularyInterface | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self._gh = transport or GhTransport()
        self._vocabulary = vocabulary or REVIEW_OUTCOMES
        self._clock = clock or time.time

    @property
    def _repo_path(self) -> str:
        return self._repository or "{owner}/{repo}"

    def _repo_flag(self) -> list[str]:
        return ["--repo", self._repository] if self._repository else []

    def list_runs(self, limit: int) -> list[Mapping[str, Any]]:
        """The workflow's newest `limit` runs, newest first, paging 100 at a time."""
        runs: list[Mapping[str, Any]] = []
        page = 1
        while len(runs) < limit:
            listed = self._gh.json(
                [
                    "api",
                    (
                        f"repos/{self._repo_path}/actions/workflows/{self._workflow}/runs"
                        f"?per_page=100&page={page}"
                    ),
                ]
            )
            batch = (listed or {}).get("workflow_runs") or []
            runs.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return runs[:limit]

    def read(self, run: Mapping[str, Any]) -> RunRecord:
        """The record `run` left: the gate's when there is one, else the evaluation's."""
        run_id = int(run["id"])
        created = str(run.get("created_at", ""))
        conclusion = str(run.get("conclusion") or run.get("status") or "")
        if run.get("status") not in (None, "completed"):
            return RunRecord(run_id, created, conclusion, SOURCE_IN_PROGRESS)
        try:
            listed = self._gh.json(
                ["api", f"repos/{self._repo_path}/actions/runs/{run_id}/artifacts?per_page=100"]
            )
        except (RuntimeError, ValueError) as error:
            return RunRecord(run_id, created, conclusion, SOURCE_UNREADABLE, problem=str(error))
        artifacts = {item.get("name"): item for item in (listed or {}).get("artifacts") or []}
        for name, source in ((OUTCOME_ARTIFACT, SOURCE_GATE), (LANE_ARTIFACT, SOURCE_EVALUATE)):
            artifact = artifacts.get(name)
            if artifact is None:
                continue
            if artifact.get("expired"):
                return RunRecord(
                    run_id,
                    created,
                    conclusion,
                    SOURCE_EXPIRED,
                    problem=f"the {name} artifact has expired",
                )
            return self._download(run_id, created, conclusion, name, source)
        return RunRecord(
            run_id,
            created,
            conclusion,
            SOURCE_NONE,
            problem="the run left no review record (it predates them, or ended first)",
        )

    def _download(
        self, run_id: int, created: str, conclusion: str, name: str, source: str
    ) -> RunRecord:
        with tempfile.TemporaryDirectory(prefix="vibey-gh-outcome-") as scratch:
            done = self._gh.run(
                ["run", "download", str(run_id), "--name", name, "--dir", scratch]
                + self._repo_flag()
            )
            if done.returncode != 0:
                said = (done.stderr or "").strip().splitlines()
                return RunRecord(
                    run_id,
                    created,
                    conclusion,
                    SOURCE_UNREADABLE,
                    problem=f"could not download {name}: {said[-1] if said else done.returncode}",
                )
            path = Path(scratch) / RECORD_FILE
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                return RunRecord(
                    run_id,
                    created,
                    conclusion,
                    SOURCE_UNREADABLE,
                    problem=f"{name} holds no readable {RECORD_FILE}: {error}",
                )
        if not isinstance(record, dict):
            return RunRecord(
                run_id,
                created,
                conclusion,
                SOURCE_UNREADABLE,
                problem=f"{name} is not a JSON object",
            )
        problems = self._vocabulary.problems(record)
        if record.get("schema") not in (None, _SCHEMA_BY_ARTIFACT[name]):
            problems.append(f"{name} carries a {record.get('schema')!r} record")
        if problems:
            return RunRecord(
                run_id, created, conclusion, SOURCE_UNREADABLE, record, "; ".join(problems)
            )
        return RunRecord(run_id, created, conclusion, source, record)

    def tabulate(self, limit: int) -> OutcomeTable:
        if limit < 1:
            raise ValueError("the number of runs to tabulate must be at least 1")
        runs = tuple(self.read(run) for run in self.list_runs(limit))
        read_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._clock()))
        return OutcomeTable(
            repository=self._repository or "(the current repository)",
            workflow=self._workflow,
            limit=limit,
            read_at=read_at,
            runs=runs,
            vocabulary=self._vocabulary,
        )
