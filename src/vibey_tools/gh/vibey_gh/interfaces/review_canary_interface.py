# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for measuring the sovereign review against planted defects (vibey ADR-0016).

`vibey_gh.review_canary` supplies every class declared here. The records below are the
nouns the canary passes between them -- a case, the diff built from it, what one review of
it scored -- and are declared beside the ports, as `BranchHealthVerdict` is, so a reader of
a ledger entry or a test double needs nothing from the implementation.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

DEFECT = "defect"
CONTROL = "control"

# What one case's review came to. A defect is CAUGHT or MISSED, a control CLEAN or a
# FALSE_POSITIVE; a review that gave no verdict at all is NO_VERDICT, counted apart and
# never folded into either side.
CAUGHT = "caught"
MISSED = "missed"
CLEAN = "clean"
FALSE_POSITIVE = "false_positive"
NO_VERDICT = "no_verdict"
OUTCOMES = (CAUGHT, MISSED, CLEAN, FALSE_POSITIVE, NO_VERDICT)


@dataclass(frozen=True)
class CanaryEdit:
    """One exact replacement: `find` occurs once in the text so far and becomes `replace`.
    `planted`, on the one edit of a defect that carries it, is the text in `replace` that
    marks where the defect is."""

    find: str
    replace: str
    planted: str = ""


@dataclass(frozen=True)
class CanaryCase:
    """A pull-request diff, as edits to one file at the corpus pin: a defect of
    `defect_class` that a finding quoting one of `anchors` would be about, or a control."""

    id: str
    kind: str
    path: str
    how: str
    edits: tuple[CanaryEdit, ...]
    defect_class: str = ""
    anchors: tuple[str, ...] = ()

    @property
    def is_defect(self) -> bool:
        return self.kind == DEFECT


@dataclass(frozen=True)
class DefectClass:
    """A kind of defect, and the words a finding about one would plausibly use."""

    name: str
    summary: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class Corpus:
    """Every case, every class, the commit the cases are edits against, and the digest of
    the file they were read from -- so a measurement names exactly what it measured."""

    schema: str
    pin: str
    classes: Mapping[str, DefectClass]
    cases: tuple[CanaryCase, ...]
    digest: str

    @property
    def defects(self) -> tuple[CanaryCase, ...]:
        return tuple(case for case in self.cases if case.is_defect)

    @property
    def controls(self) -> tuple[CanaryCase, ...]:
        return tuple(case for case in self.cases if not case.is_defect)


@dataclass(frozen=True)
class BuiltCase:
    """A case made concrete: the file before and after, the diff between them, and -- for a
    defect -- the first and last line of the post-change text the planted text spans."""

    case: CanaryCase
    before: str
    after: str
    diff: str
    lines: tuple[int, int] | None = None


@dataclass(frozen=True)
class CaseResult:
    """What one review of one case came to, and the evidence for it.

    `blocked` is whether the gate would have stopped the change -- any verdict but an
    explicit pass. For a defect, `located` says some finding was about the planted lines and
    `classed` that such a finding also named the defect's class. `code` is the review's
    outcome code (`vibey_gh.review_outcome`), `reviewed` whenever there was a verdict.
    """

    case_id: str
    kind: str
    outcome: str
    code: str
    defect_class: str = ""
    seconds: float = 0.0
    attempts: int = 0
    parts: int = 0
    blocked: bool = False
    located: bool = False
    classed: bool = False
    findings: int = 0
    blocking_findings: int = 0
    matched: str = ""
    reason: str = ""
    evidence: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "case": self.case_id,
            "kind": self.kind,
            "class": self.defect_class,
            "outcome": self.outcome,
            "code": self.code,
            "seconds": round(self.seconds, 1),
            "attempts": self.attempts,
            "parts": self.parts,
            "blocked": self.blocked,
            "located": self.located,
            "classed": self.classed,
            "findings": self.findings,
            "blocking_findings": self.blocking_findings,
            "matched": self.matched,
            "reason": self.reason,
            "evidence": [dict(item) for item in self.evidence],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> CaseResult:
        return cls(
            case_id=str(value["case"]),
            kind=str(value["kind"]),
            outcome=str(value["outcome"]),
            code=str(value["code"]),
            defect_class=str(value.get("class", "")),
            seconds=float(value.get("seconds", 0.0)),
            attempts=int(value.get("attempts", 0)),
            parts=int(value.get("parts", 0)),
            blocked=bool(value.get("blocked", False)),
            located=bool(value.get("located", False)),
            classed=bool(value.get("classed", False)),
            findings=int(value.get("findings", 0)),
            blocking_findings=int(value.get("blocking_findings", 0)),
            matched=str(value.get("matched", "")),
            reason=str(value.get("reason", "")),
            evidence=tuple(dict(item) for item in value.get("evidence") or ()),
        )


@dataclass(frozen=True)
class CanaryFloor:
    """What a measurement must show before an approver may lean on the review."""

    min_recall_lower_bound: float
    max_false_positive_upper_bound: float
    max_age_days: int = 14


@runtime_checkable
class CorpusLoaderInterface(Protocol):
    """Reads, validates and builds the corpus."""

    def load(self, path: Path) -> Corpus:
        """The corpus at `path`, or `ValueError` naming every way it is malformed."""
        ...

    def build(self, corpus: Corpus, case: CanaryCase) -> BuiltCase:
        """The file at the pin, every edit applied, the diff, and a defect's lines.
        `ValueError` when the file cannot be read or an edit does not apply exactly once."""
        ...

    def problems(
        self, corpus: Corpus, *, min_defects: int, min_classes: int, min_controls: int
    ) -> list[str]:
        """Every reason the corpus is not a measurement: too few defects, classes or
        controls, or a case that does not build. Empty when it is one."""
        ...

    def diff(self, path: str, before: str, after: str) -> str:
        """A git-style unified diff of one file, three lines of context."""
        ...


@runtime_checkable
class FindingMatcherInterface(Protocol):
    """The matching rule: whether a finding is about a planted defect."""

    def same_path(self, said: str, path: str) -> bool:
        """`said` names `path`: equal once an `a/`, `b/` or `./` prefix is dropped, or
        either ends with the other at a `/`."""
        ...

    def located(self, finding: Mapping[str, Any], built: BuiltCase) -> bool:
        """On the case's file, and either its `line` within `line_tolerance` of the planted
        lines or its words quoting one of the case's anchors."""
        ...

    def classed(self, finding: Mapping[str, Any], keywords: Sequence[str]) -> bool:
        """Its words use one of the class's keywords, case-insensitively."""
        ...


@runtime_checkable
class WilsonIntervalInterface(Protocol):
    """The Wilson score interval of a binomial proportion."""

    def bounds(self, k: int, n: int, z: float) -> tuple[float, float] | None:
        """`(low, high)` for `k` of `n`, or None when `n` is 0: nothing was measured."""
        ...

    def confidence(self, z: float) -> float:
        """The two-sided confidence `z` stands for: 0.95 for 1.96."""
        ...


@runtime_checkable
class CanaryScorerInterface(Protocol):
    """Scores each review, and the measurement they make together."""

    def score(
        self,
        built: BuiltCase,
        keywords: Sequence[str],
        verdict: Mapping[str, Any] | None,
        *,
        code: str,
        seconds: float = 0.0,
        attempts: int = 0,
        parts: int = 0,
        reason: str = "",
    ) -> CaseResult:
        """One case's outcome: `verdict` None is NO_VERDICT, whatever `code` says."""
        ...

    def summarize(
        self, results: Sequence[CaseResult], classes: Sequence[str], z: float
    ) -> dict[str, Any]:
        """Recall, the lenient location-only recall, the false-positive rate -- each with
        its Wilson interval -- the no-verdict count by code, and recall per class."""
        ...

    def meets(self, summary: Mapping[str, Any], floor: CanaryFloor) -> tuple[bool, list[str]]:
        """Whether a summary clears the floor's two bounds, and every reason it does not."""
        ...


@runtime_checkable
class CanaryLedgerInterface(Protocol):
    """The append-only, digest-chained record of every measurement."""

    def read(self, path: Path) -> tuple[Mapping[str, Any], ...]:
        """Every measurement's payload, oldest first; `ValueError` for a broken chain."""
        ...

    def append(self, path: Path, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Append one measurement after the last, chained to it, and return its envelope."""
        ...


@runtime_checkable
class CanaryReportInterface(Protocol):
    """The generated block a page shows the latest measurement in."""

    def block(self, entry: Mapping[str, Any] | None) -> str:
        """The block, both markers included, for `entry` -- or saying there is none."""
        ...

    def apply(self, text: str, block: str) -> str:
        """`text` with its block replaced; `ValueError` when it has no block to replace."""
        ...


@runtime_checkable
class ReviewCanaryInterface(Protocol):
    """`vibey-gh review-canary`: measure, record, render, and say whether the floor holds."""

    def run(
        self,
        case_ids: Sequence[str] = (),
        *,
        work: Path | None = None,
        record: bool = True,
    ) -> dict[str, Any]:
        """Review every case (or `case_ids`), score them, and -- with `record` -- append the
        measurement to the ledger and render it. Returns the measurement."""
        ...

    def shard(self, index: int, of: int, *, out: Path, work: Path | None = None) -> dict[str, Any]:
        """Review only the cases whose place in the corpus is `index` modulo `of`, and write
        what each review said -- unscored, beside the settings, corpus and conditions they
        were heard under -- to `out`. Records nothing. Returns what it wrote."""
        ...

    def merge(self, paths: Sequence[Path], *, record: bool = True) -> dict[str, Any]:
        """The measurement the shard files at `paths` make together -- exactly the one an
        unsharded `run` of every case would have made -- recorded as `run` records it.
        `ValueError` unless they cover every case once, under one corpus, commit, model and
        set of settings."""
        ...

    def plan(self) -> dict[str, Any]:
        """What a sharded measurement needs: the model to serve, and one `I/N` per shard."""
        ...

    def status(self) -> dict[str, Any]:
        """Whether the latest recorded measurement meets the floor now: `meets_floor` True,
        False, or None when there is none, with every reason it does not."""
        ...

    def declare(self, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """The command's subcommands and flags."""
        ...
