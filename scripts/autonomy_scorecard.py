# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How far vibey is from full autonomy, measured from primary data and never hand-written.

    python scripts/autonomy_scorecard.py measure                  # observe everything, record, render
    python scripts/autonomy_scorecard.py observe --sources forge --out <file>
    python scripts/autonomy_scorecard.py record <observation>...  # merge, judge, append, render
    python scripts/autonomy_scorecard.py reevaluate               # judge the latest figures again
    python scripts/autonomy_scorecard.py render                   # rewrite the GENERATED blocks
    python scripts/autonomy_scorecard.py check                    # exit 1 if anything is out of step

"Full autonomy" is a set of named stages of the delivery loop, each declared in
`scripts/autonomy_scorecard.toml` with the question it answers, the figures that answer it,
the threshold at which the answer counts as "runs without a person", and the reason for
that threshold. Each figure is observed from one source -- the forge (`gh`), the review
canary (`vibey-gh review-canary status`), the repository itself, or the local queue (read
only, and only where a DSN is declared) -- and carries its value, its sample, its window
and cutoff, how it was obtained, and its status:

    measured   a query against the named source produced it, inside the stated window
    declared   read from the repository (a constant in the code)
    stale      this run could not re-read it; the last good value is kept, marked, with the
               date it was last measured and the reason, for at most `max_stale_days`
    unknown    it could not be read and no recent value exists; no number is invented

A stage is as far along as its weakest judged criterion: autonomous when every criterion meets
its threshold, manual when any judged criterion is under its partial threshold, partial
otherwise, and unknown when nothing judged falls short but something could not be judged
(sub-doctrine 10.f: unknown stays unknown). The headline is a
count of declared stages, never a percentage that hides what it is made of.

Each measurement is appended, digest-chained, to the record
(`docs/architecture/evidence/autonomy-scorecard.jsonl`) through the family's own ledger
(`vibey_gh.review_canary.CanaryLedger`, 10.e), and the documents' GENERATED blocks are
rendered from the latest line. `check` re-verifies the chain, re-judges the latest line,
compares its stage definitions with the TOML, and fails when any block disagrees
(sub-doctrine 12.e: the check that says out loud when the step was missed).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from vibey_gh.review_canary import CanaryLedger

try:
    from scripts.interfaces.autonomy_scorecard_interface import (
        ClockInterface,
        CommandRunnerInterface,
        ForgeClientInterface,
        QueueReaderInterface,
        ScorecardLedgerInterface,
        ScorecardRendererInterface,
        SourceInterface,
        StageEvaluatorInterface,
        StalenessPolicyInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.autonomy_scorecard_interface import (  # type: ignore[import-not-found,no-redef]
        ClockInterface,
        CommandRunnerInterface,
        ForgeClientInterface,
        QueueReaderInterface,
        ScorecardLedgerInterface,
        ScorecardRendererInterface,
        SourceInterface,
        StageEvaluatorInterface,
        StalenessPolicyInterface,
    )

SCRIPT = "scripts/autonomy_scorecard.py"
DEFAULT_CONFIG = "scripts/autonomy_scorecard.toml"
RECORD_FORMAT = "vibey/autonomy-scorecard/1"
RECORD_KIND = "AutonomyMeasured"
FIGURE_STATUSES = ("measured", "declared", "stale", "unknown")
STAGE_STATUSES = ("autonomous", "partial", "manual", "unknown")
COMPARATORS = (">=", "<=", "is")
#: A UTC instant to the second, the only shape a cutoff or window bound takes.
ISO_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
#: A queue identifier (phase, kind) interpolated into SQL: lowercase words only.
SQL_WORD = re.compile(r"[a-z_]+")
REPO_URL = "https://github.com/the-vibey-project/vibey/blob/develop"


class SourceUnavailable(Exception):
    """A source could not answer; its figures are recorded unknown with this reason."""


# ------------------------------------------------------------------------ time


class Instants:
    """UTC instants as the record writes them: `YYYY-MM-DDTHH:MM:SSZ`."""

    @staticmethod
    def parse(text: str) -> datetime:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)

    @staticmethod
    def format(moment: datetime) -> str:
        return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def minus_days(cls, instant: str, days: int) -> str:
        return cls.format(cls.parse(instant) - timedelta(days=days))

    @classmethod
    def within(cls, instant: str | None, start: str, end: str) -> bool:
        if not instant:
            return False
        moment = cls.parse(instant)
        return cls.parse(start) <= moment < cls.parse(end)

    @classmethod
    def hours_between(cls, earlier: str, later: str) -> float:
        return (cls.parse(later) - cls.parse(earlier)).total_seconds() / 3600

    @staticmethod
    def day(instant: str | None) -> str:
        return instant[:10] if instant else "-"

    @staticmethod
    def minute(instant: str) -> str:
        return f"{instant[:10]} {instant[11:16]}Z"


class SystemClock(ClockInterface):
    def now(self) -> str:
        return Instants.format(datetime.now(UTC))


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class Settings:
    """`scripts/autonomy_scorecard.toml`, read once. Nothing here has a compiled-in value."""

    raw: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> Settings:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        settings = cls(raw)
        settings.validate()
        return settings

    @property
    def scorecard(self) -> Mapping[str, Any]:
        return dict(self.raw["scorecard"])

    def section(self, name: str) -> Mapping[str, Any]:
        return dict(self.scorecard[name])

    @property
    def stages(self) -> list[dict[str, Any]]:
        return [dict(stage) for stage in self.raw.get("stage", [])]

    def validate(self) -> None:
        seen: set[str] = set()
        for stage in self.stages:
            if stage["id"] in seen:
                raise ValueError(f"stage {stage['id']} is declared twice")
            seen.add(stage["id"])
            if not stage.get("criteria"):
                raise ValueError(f"stage {stage['id']} declares no criteria")
            for criterion in stage["criteria"]:
                if criterion["compare"] not in COMPARATORS:
                    raise ValueError(
                        f"stage {stage['id']}: compare {criterion['compare']!r} is not one of "
                        + ", ".join(COMPARATORS)
                    )
                if criterion["figure"] not in FigureCatalog.ids():
                    raise ValueError(
                        f"stage {stage['id']}: no source observes {criterion['figure']}"
                    )

    def digest(self) -> str:
        encoded = json.dumps(self.stages, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


# ------------------------------------------------------------------------ figures


@dataclass(frozen=True)
class Figure:
    """One observed number, with what it rests on. A share carries its numerator and
    denominator; the denominator is the sample a criterion's `min_sample` is held to."""

    id: str
    label: str
    unit: str
    value: float | bool | None
    status: str
    source: str
    method: str
    observed_at: str
    window: tuple[str, str] | None = None
    numerator: int | None = None
    denominator: int | None = None
    reason: str = ""
    last_measured: str | None = None

    def __post_init__(self) -> None:
        if self.status not in FIGURE_STATUSES:
            raise ValueError(f"{self.id}: status {self.status!r} is not one of {FIGURE_STATUSES}")
        if self.status == "unknown" and self.value is not None:
            raise ValueError(f"{self.id}: an unknown figure carries no value")
        if self.status != "unknown" and self.value is None:
            raise ValueError(f"{self.id}: a {self.status} figure needs a value")

    @property
    def known(self) -> bool:
        return self.status != "unknown"

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["window"] = list(self.window) if self.window else None
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> Figure:
        values = dict(raw)
        window = values.get("window")
        values["window"] = tuple(window) if window else None
        return cls(**values)


@dataclass(frozen=True)
class FigureSpec:
    id: str
    label: str
    unit: str
    source: str


class FigureCatalog:
    """Every figure a source declares: the one list the record, the stages and the renderers
    agree on. A stage may only name a figure that is here (`Settings.validate`)."""

    SPECS: tuple[FigureSpec, ...] = (
        FigureSpec("forge.review.verdict_share", "merged PRs with a review verdict at their head", "share", "forge"),
        FigureSpec("forge.approval.approver_share", "merged PRs approved by the delegated approver", "share", "forge"),
        FigureSpec("forge.approval.gate_required", "the review gate is a required check on the integration branch", "bool", "forge"),
        FigureSpec("forge.merge.not_operator_share", "merged PRs merged by an account other than the operator's", "share", "forge"),
        FigureSpec("forge.merge.reviewed_share", "merged PRs carrying an approving review (no bypass)", "share", "forge"),
        FigureSpec("forge.merge.reviews_per_merge", "reviews of any kind per merged PR", "ratio", "forge"),
        FigureSpec("forge.promotion.hand_dispatches", "promotion runs a person dispatched by hand", "count", "forge"),
        FigureSpec("forge.promotion.main_not_operator_share", "promotions merged into the release branch by an account other than the operator's", "share", "forge"),
        FigureSpec("forge.release.success_share", "release publishes that succeeded", "share", "forge"),
        FigureSpec("forge.ci.success_share", "CI runs on the integration branch that succeeded", "share", "forge"),
        FigureSpec("forge.ci.rerun_share", "CI runs on the integration branch that were re-run", "share", "forge"),
        FigureSpec("canary.meets_floor", "the latest review-canary measurement meets its floor", "bool", "canary"),
        FigureSpec("canary.recall_lower_bound", "review-canary recall, lower 95% bound", "ratio", "canary"),
        FigureSpec("canary.false_positive_upper_bound", "review-canary false-positive rate, upper 95% bound", "ratio", "canary"),
        FigureSpec("canary.age_days", "age of the latest review-canary measurement", "days", "canary"),
        FigureSpec("repo.review.timeout_kinds_share", "REVIEW gate kinds that may resolve without a person", "share", "repo"),
        FigureSpec("queue.design.unattended_share", "DESIGN gates answered without a person", "share", "queue"),
        FigureSpec("queue.build.unattended_share", "BUILD jobs finished per finished job or escalation", "share", "queue"),
        FigureSpec("queue.review.unattended_share", "REVIEW gates answered without a person", "share", "queue"),
        FigureSpec("queue.engines.paid_auth_fresh_share", "paid engines with a login check inside its time-to-live", "share", "queue"),
        FigureSpec("queue.done_projects", "projects that reached DONE", "count", "queue"),
        FigureSpec("queue.last_event_hours", "hours since the queue's latest event", "hours", "queue"),
    )  # fmt: skip

    @classmethod
    def ids(cls) -> list[str]:
        return [spec.id for spec in cls.SPECS]

    @classmethod
    def spec(cls, fid: str) -> FigureSpec:
        for spec in cls.SPECS:
            if spec.id == fid:
                return spec
        raise KeyError(fid)

    @classmethod
    def of(cls, source: str) -> list[FigureSpec]:
        return [spec for spec in cls.SPECS if spec.source == source]


class FigureFactory:
    """Stamps every figure a source returns with the source, the cutoff and the window."""

    def __init__(self, source: str, cutoff: str, window: tuple[str, str] | None) -> None:
        self._source = source
        self._cutoff = cutoff
        self._window = window

    def _base(self, fid: str) -> FigureSpec:
        spec = FigureCatalog.spec(fid)
        if spec.source != self._source:
            raise ValueError(f"{fid} belongs to the {spec.source} source, not {self._source}")
        return spec

    def share(self, fid: str, numerator: int, denominator: int, method: str) -> Figure:
        spec = self._base(fid)
        if denominator == 0:
            return self.unknown(fid, method, "the window holds no sample (0 of 0)")
        return Figure(
            fid,
            spec.label,
            spec.unit,
            numerator / denominator,
            "measured",
            self._source,
            method,
            self._cutoff,
            self._window,
            numerator,
            denominator,
        )

    def value(
        self,
        fid: str,
        value: float | bool,
        method: str,
        *,
        status: str = "measured",
        reason: str = "",
    ) -> Figure:
        spec = self._base(fid)
        return Figure(
            fid,
            spec.label,
            spec.unit,
            value,
            status,
            self._source,
            method,
            self._cutoff,
            self._window,
            reason=reason,
        )

    def unknown(self, fid: str, method: str, reason: str) -> Figure:
        spec = self._base(fid)
        return Figure(
            fid,
            spec.label,
            spec.unit,
            None,
            "unknown",
            self._source,
            method,
            self._cutoff,
            self._window,
            reason=reason,
        )

    def all_unknown(self, method: str, reason: str) -> list[Figure]:
        return [self.unknown(spec.id, method, reason) for spec in FigureCatalog.of(self._source)]


# ------------------------------------------------------------------------ commands


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def tail(self) -> str:
        text = (self.stderr or self.stdout).strip().splitlines()
        return text[-1] if text else f"exit {self.returncode}"


class SubprocessRunner(CommandRunnerInterface):
    def run(
        self, argv: Sequence[str], *, timeout: float, env: Mapping[str, str] | None = None
    ) -> CommandResult:
        merged = {**os.environ, **(env or {})}
        try:
            done = subprocess.run(  # noqa: S603 -- an argv list, never a shell
                list(argv),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged,
                check=False,
            )
        except FileNotFoundError:
            return CommandResult(127, "", f"{argv[0]}: not found")
        except subprocess.TimeoutExpired:
            return CommandResult(124, "", f"{argv[0]}: timed out after {timeout:.0f}s")
        return CommandResult(done.returncode, done.stdout, done.stderr)


# ------------------------------------------------------------------------ the forge


class GhForge(ForgeClientInterface):
    """The forge through the `gh` command line, the family's way of reading GitHub."""

    def __init__(
        self, runner: CommandRunnerInterface, repository: str, timeout: float = 120
    ) -> None:
        self._runner = runner
        self._repo = repository
        self._timeout = timeout

    def _out(self, argv: Sequence[str]) -> str:
        result = self._runner.run(["gh", *argv], timeout=self._timeout)
        if not result.ok:
            raise SourceUnavailable(f"`gh {' '.join(argv[:2])}` failed: {result.tail()}")
        return str(result.stdout)

    def _json(self, argv: Sequence[str]) -> Any:
        text = self._out(argv)
        try:
            return json.loads(text or "null")
        except json.JSONDecodeError as exc:
            raise SourceUnavailable(f"`gh {argv[0]}` did not return JSON: {exc.msg}") from exc

    def _lines(self, argv: Sequence[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for line in self._out(argv).splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SourceUnavailable(
                        f"`gh api` returned a line that is not JSON: {exc.msg}"
                    ) from exc
        return out

    def merged_pulls(self, base: str, since: str) -> list[dict[str, Any]]:
        value = self._json(
            [
                "pr",
                "list",
                "--repo",
                self._repo,
                "--base",
                base,
                "--state",
                "merged",
                "--search",
                f"merged:>={Instants.day(since)}",
                "--limit",
                "1000",
                "--json",
                "number,author,mergedAt,mergedBy,reviews,headRefOid",
            ]
        )
        return list(value or [])

    def check_runs(self, sha: str, name: str) -> list[dict[str, Any]]:
        path = f"repos/{self._repo}/commits/{sha}/check-runs?check_name={quote(name)}&per_page=100"
        return self._lines(["api", path, "--paginate", "--jq", ".check_runs[]"])

    def rulesets(self) -> list[dict[str, Any]]:
        listed = self._lines(["api", f"repos/{self._repo}/rulesets", "--paginate", "--jq", ".[]"])
        return [self._json(["api", f"repos/{self._repo}/rulesets/{item['id']}"]) for item in listed]

    def workflow_runs(
        self, workflow: str, *, branch: str | None, event: str | None, since: str
    ) -> list[dict[str, Any]]:
        query = f"per_page=100&created=>={Instants.day(since)}"
        if branch:
            query += f"&branch={quote(branch)}"
        if event:
            query += f"&event={quote(event)}"
        jq = (
            ".workflow_runs[] | {created_at, event, status, conclusion, run_attempt, "
            "actor: .triggering_actor.login, actor_type: .triggering_actor.type}"
        )
        path = f"repos/{self._repo}/actions/workflows/{workflow}/runs?{query}"
        return self._lines(["api", path, "--paginate", "--jq", jq])


class ForgeSource(SourceInterface):
    """Who merged, who approved, whether the review answered, and how promotion and CI ran."""

    name = "forge"

    def __init__(self, forge: ForgeClientInterface, settings: Settings) -> None:
        self._forge = forge
        self._settings = settings
        self._cfg = settings.section("forge")

    def observe(self, cutoff: str) -> list[Figure]:
        days = int(self._settings.section("windows")["forge_days"])
        start = Instants.minus_days(cutoff, days)
        make = FigureFactory(self.name, cutoff, (start, cutoff))
        s = self._settings.scorecard
        figures: list[Figure] = []
        method = (
            f"`gh pr list --base {s['integration_branch']} --state merged`, merged in the window"
        )
        try:
            pulls = [
                p
                for p in self._forge.merged_pulls(s["integration_branch"], start)
                if Instants.within(p.get("mergedAt"), start, cutoff)
            ]
        except SourceUnavailable as exc:
            for fid in (
                "forge.review.verdict_share",
                "forge.approval.approver_share",
                "forge.merge.not_operator_share",
                "forge.merge.reviewed_share",
                "forge.merge.reviews_per_merge",
            ):
                figures.append(make.unknown(fid, method, str(exc)))
        else:
            figures += self._pull_figures(make, pulls, method)
        figures.append(self._gate_required(make))
        figures += self._ci(make, start, cutoff)
        figures += self._promotion(make, start, cutoff)
        return figures

    # -------------------------------------------------------------- pull requests

    def _pull_figures(
        self, make: FigureFactory, pulls: Sequence[Mapping[str, Any]], method: str
    ) -> list[Figure]:
        s = self._settings.scorecard
        n = len(pulls)
        approved_by_approver = sum(
            1
            for p in pulls
            if any(
                (r.get("author") or {}).get("login") == s["approver"]
                and r.get("state") == "APPROVED"
                for r in p.get("reviews") or []
            )
        )
        not_operator = sum(
            1 for p in pulls if (p.get("mergedBy") or {}).get("login") != s["operator"]
        )
        reviewed = sum(1 for p in pulls if self._approved_by_other(p))
        reviews = sum(len(p.get("reviews") or []) for p in pulls)
        figures = [
            self._verdicts(make, pulls),
            make.share("forge.approval.approver_share", approved_by_approver, n, method + f"; an APPROVED review by `{s['approver']}`"),
            make.share("forge.merge.not_operator_share", not_operator, n, method + f"; `mergedBy` is not `{s['operator']}`"),
            make.share("forge.merge.reviewed_share", reviewed, n, method + "; an APPROVED review by an account other than the author"),
        ]  # fmt: skip
        if n:
            figures.append(
                make.value("forge.merge.reviews_per_merge", round(reviews / n, 2), method + "; every review state counted")
            )  # fmt: skip
        else:
            figures.append(
                make.unknown(
                    "forge.merge.reviews_per_merge", method, "no pull request merged in the window"
                )
            )
        return figures

    @staticmethod
    def _approved_by_other(pull: Mapping[str, Any]) -> bool:
        author = (pull.get("author") or {}).get("login")
        return any(
            r.get("state") == "APPROVED" and (r.get("author") or {}).get("login") != author
            for r in pull.get("reviews") or []
        )

    def _verdicts(self, make: FigureFactory, pulls: Sequence[Mapping[str, Any]]) -> Figure:
        name = self._cfg["review_check"]
        patterns = [re.compile(p) for p in self._cfg["verdict_titles"]]
        method = (
            f"the latest `{name}` check run at each merged head; a verdict is a title matching "
            + " or ".join(f"`{p.pattern}`" for p in patterns)
        )
        verdicts = 0
        for pull in pulls:
            try:
                runs = self._forge.check_runs(str(pull.get("headRefOid")), name)
            except SourceUnavailable as exc:
                return make.unknown("forge.review.verdict_share", method, str(exc))
            if not runs:
                continue
            latest = max(
                runs, key=lambda r: str(r.get("completed_at") or r.get("started_at") or "")
            )
            title = str((latest.get("output") or {}).get("title") or "")
            if any(p.search(title) for p in patterns):
                verdicts += 1
        return make.share("forge.review.verdict_share", verdicts, len(pulls), method)

    # -------------------------------------------------------------- rulesets

    def _gate_required(self, make: FigureFactory) -> Figure:
        branch = self._settings.scorecard["integration_branch"]
        name = self._cfg["review_check"]
        method = f"active branch rulesets that include `refs/heads/{branch}`, their required status checks"
        try:
            rulesets = self._forge.rulesets()
        except SourceUnavailable as exc:
            return make.unknown("forge.approval.gate_required", method, str(exc))
        applying = [r for r in rulesets if self._applies(r, branch)]
        if not applying:
            return make.unknown(
                "forge.approval.gate_required", method, f"no active ruleset applies to {branch}"
            )
        required = {
            check.get("context")
            for r in applying
            for rule in r.get("rules") or []
            if rule.get("type") == "required_status_checks"
            for check in (rule.get("parameters") or {}).get("required_status_checks") or []
        }
        return make.value(
            "forge.approval.gate_required",
            name in required,
            method
            + f" ({len(applying)} rulesets; required: {', '.join(sorted(c for c in required if c)) or 'none'})",
        )

    @staticmethod
    def _applies(ruleset: Mapping[str, Any], branch: str) -> bool:
        if ruleset.get("target") != "branch" or ruleset.get("enforcement") != "active":
            return False
        include = ((ruleset.get("conditions") or {}).get("ref_name") or {}).get("include") or []
        return f"refs/heads/{branch}" in include or "~ALL" in include

    # -------------------------------------------------------------- workflow runs

    def _outcomes(self, runs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        skip = set(self._cfg["not_an_outcome"])
        return [
            r for r in runs if r.get("status") == "completed" and r.get("conclusion") not in skip
        ]

    def _runs(
        self, workflow: str, branch: str | None, event: str | None, start: str, end: str
    ) -> list[dict[str, Any]]:
        runs = self._forge.workflow_runs(workflow, branch=branch, event=event, since=start)
        return [r for r in runs if Instants.within(r.get("created_at"), start, end)]

    def _ci(self, make: FigureFactory, start: str, end: str) -> list[Figure]:
        s, c = self._settings.scorecard, self._cfg
        method = f"`{c['ci_workflow']}` runs on `{s['integration_branch']}`, event `{c['ci_event']}`, created in the window"
        try:
            runs = self._runs(c["ci_workflow"], s["integration_branch"], c["ci_event"], start, end)
        except SourceUnavailable as exc:
            return [
                make.unknown("forge.ci.success_share", method, str(exc)),
                make.unknown("forge.ci.rerun_share", method, str(exc)),
            ]
        outcomes = self._outcomes(runs)
        completed = [r for r in runs if r.get("status") == "completed"]
        return [
            make.share("forge.ci.success_share", sum(1 for r in outcomes if r.get("conclusion") == "success"), len(outcomes), method + "; cancelled and skipped runs left out"),
            make.share("forge.ci.rerun_share", sum(1 for r in completed if int(r.get("run_attempt") or 1) > 1), len(completed), method + "; `run_attempt` above 1"),
        ]  # fmt: skip

    def _promotion(self, make: FigureFactory, start: str, end: str) -> list[Figure]:
        s, c = self._settings.scorecard, self._cfg
        figures: list[Figure] = []
        method = (
            f"`{c['promote_workflow']}` runs created in the window by `workflow_dispatch` "
            "whose triggering actor is not a bot"
        )
        try:
            runs = self._runs(c["promote_workflow"], None, None, start, end)
        except SourceUnavailable as exc:
            figures.append(make.unknown("forge.promotion.hand_dispatches", method, str(exc)))
        else:
            by_hand = [
                r
                for r in runs
                if r.get("event") == "workflow_dispatch" and r.get("actor_type") != "Bot"
            ]
            others = len(runs) - len(by_hand)
            figures.append(
                make.value(
                    "forge.promotion.hand_dispatches",
                    len(by_hand),
                    method + f" ({others} other runs in the window started on their own)",
                )
            )
        method = f"`gh pr list --base {s['release_branch']} --state merged`, merged in the window"
        try:
            pulls = [
                p
                for p in self._forge.merged_pulls(s["release_branch"], start)
                if Instants.within(p.get("mergedAt"), start, end)
            ]
        except SourceUnavailable as exc:
            figures.append(
                make.unknown("forge.promotion.main_not_operator_share", method, str(exc))
            )
        else:
            figures.append(
                make.share(
                    "forge.promotion.main_not_operator_share",
                    sum(
                        1 for p in pulls if (p.get("mergedBy") or {}).get("login") != s["operator"]
                    ),
                    len(pulls),
                    method + f"; `mergedBy` is not `{s['operator']}`",
                )
            )
        method = f"`{c['release_workflow']}` runs on `{s['release_branch']}`, event `{c['release_event']}`, created in the window"
        try:
            runs = self._outcomes(
                self._runs(
                    c["release_workflow"], s["release_branch"], c["release_event"], start, end
                )
            )
        except SourceUnavailable as exc:
            figures.append(make.unknown("forge.release.success_share", method, str(exc)))
        else:
            figures.append(
                make.share(
                    "forge.release.success_share",
                    sum(1 for r in runs if r.get("conclusion") == "success"),
                    len(runs),
                    method + "; cancelled and skipped runs left out",
                )
            )
        return figures


# ------------------------------------------------------------------------ the review canary


class CanarySource(SourceInterface):
    """The review canary's own verdict on itself (`vibey-gh review-canary status --json`),
    read through the family's command rather than recomputed here (10.e)."""

    name = "canary"

    def __init__(self, runner: CommandRunnerInterface, settings: Settings) -> None:
        self._runner = runner
        self._cfg = settings.section("canary")

    def command(self) -> list[str]:
        return [sys.executable if part == "{python}" else part for part in self._cfg["command"]]

    def observe(self, cutoff: str) -> list[Figure]:
        make = FigureFactory(self.name, cutoff, None)
        argv = self.command()
        method = "`vibey-gh review-canary status --json` against the committed ledger"
        result = self._runner.run(argv, timeout=float(self._cfg["timeout_seconds"]))
        try:
            answer = json.loads(result.stdout) if result.returncode in (0, 1, 3) else None
        except json.JSONDecodeError:
            answer = None
        if not isinstance(answer, dict):
            return make.all_unknown(method, f"the canary status did not answer: {result.tail()}")
        meets = answer.get("meets_floor")
        reasons = "; ".join(str(r) for r in answer.get("reasons") or [])
        figures = [
            make.value("canary.meets_floor", bool(meets), method, reason=reasons)
            if meets is not None
            else make.unknown(
                "canary.meets_floor", method, reasons or "no measurement is recorded"
            ),
        ]
        recall = (answer.get("recall") or {}).get("low")
        fp = (answer.get("false_positive") or {}).get("high")
        age = answer.get("age_days")
        for fid, value in (
            ("canary.recall_lower_bound", recall),
            ("canary.false_positive_upper_bound", fp),
            ("canary.age_days", age),
        ):
            if value is None:
                figures.append(make.unknown(fid, method, "the canary status does not report it"))
            else:
                figures.append(make.value(fid, round(float(value), 3), method))
        return figures


# ------------------------------------------------------------------------ the repository


class RepoSource(SourceInterface):
    """What the code itself declares: which REVIEW gate kinds may time out to a default."""

    name = "repo"

    def __init__(self, root: Path, settings: Settings) -> None:
        self._root = root
        self._cfg = settings.section("repo")

    def kinds(self) -> list[str]:
        path = self._root / self._cfg["gate_timeout_module"]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        name = self._cfg["gate_timeout_mapping"]
        for node in ast.walk(tree):
            value: ast.expr | None = None
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                value = node.value if node.target.id == name else None
            elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets
            ):
                value = node.value
            if isinstance(value, ast.Call) and value.args:
                value = value.args[0]
            if isinstance(value, ast.Dict):
                return [
                    k.value
                    for k in value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                ]
        raise ValueError(f"{name} is not a dict literal in {self._cfg['gate_timeout_module']}")

    def observe(self, cutoff: str) -> list[Figure]:
        make = FigureFactory(self.name, cutoff, None)
        module = self._cfg["gate_timeout_module"]
        method = f"`{self._cfg['gate_timeout_mapping']}` in `{module}`, against REVIEW's gate kinds"
        try:
            kinds = set(self.kinds())
        except (OSError, SyntaxError, ValueError) as exc:
            return [make.unknown("repo.review.timeout_kinds_share", method, str(exc))]
        review = list(self._cfg["review_gate_kinds"])
        allowed = [k for k in review if k in kinds]
        figure = make.share("repo.review.timeout_kinds_share", len(allowed), len(review), method)
        missing = [k for k in review if k not in kinds]
        return [
            replace(
                figure,
                status="declared",
                reason=("cannot time out: " + ", ".join(f"`{k}`" for k in missing))
                if missing
                else "",
            )
        ]


# ------------------------------------------------------------------------ the local queue


class PsqlQueue(QueueReaderInterface):
    """The local queue through `psql`, in a session that cannot write
    (`default_transaction_read_only=on`). Only constants and validated instants reach SQL."""

    def __init__(self, runner: CommandRunnerInterface, psql: str, dsn: str, timeout: float) -> None:
        self._runner = runner
        self._psql = psql
        self._dsn = dsn
        self._timeout = timeout

    @staticmethod
    def _instant(text: str) -> str:
        if not ISO_UTC.fullmatch(text):
            raise ValueError(f"not a UTC instant: {text!r}")
        return text

    @staticmethod
    def _word(text: str) -> str:
        if not SQL_WORD.fullmatch(text):
            raise ValueError(f"not a queue identifier: {text!r}")
        return text

    def _query(self, sql: str) -> Any:
        result = self._runner.run(
            [self._psql, "-X", "-At", "-v", "ON_ERROR_STOP=1", "-d", self._dsn, "-c", sql],
            timeout=self._timeout,
            env={"PGOPTIONS": "-c default_transaction_read_only=on"},
        )
        if not result.ok:
            raise SourceUnavailable(f"the queue did not answer: {result.tail()}")
        text = str(result.stdout).strip()
        try:
            return json.loads(text) if text else None
        except json.JSONDecodeError as exc:
            raise SourceUnavailable(
                f"the queue returned something that is not JSON: {exc.msg}"
            ) from exc

    _UTC = '\'YYYY-MM-DD"T"HH24:MI:SS"Z"\''

    def gates(self, start: str, end: str) -> list[dict[str, Any]]:
        a, b = self._instant(start), self._instant(end)
        sql = (
            "select coalesce(json_agg(json_build_object('kind', g.kind, 'phase', j.phase, "
            "'answered_by', g.answered_by)), '[]') from human_gate g "
            "left join job j on j.id = g.job_id "
            f"where g.raised_at >= '{a}' and g.raised_at < '{b}'"
        )
        return list(self._query(sql) or [])

    def jobs_succeeded(self, phase: str, start: str, end: str) -> int:
        a, b, p = self._instant(start), self._instant(end), self._word(phase)
        sql = (
            "select count(*) from job "
            f"where phase = '{p}' and state = 'succeeded' and updated_at >= '{a}' and updated_at < '{b}'"
        )
        return int(self._query(sql) or 0)

    def transitions(self, to: str, start: str, end: str) -> int:
        a, b, t = self._instant(start), self._instant(end), self._word(to)
        sql = (
            "select count(*) from event where kind = 'PhaseTransitioned' "
            f"and payload->>'to' = '{t}' and produced_at >= '{a}' and produced_at < '{b}'"
        )
        return int(self._query(sql) or 0)

    def last_event_at(self, end: str) -> str | None:
        b = self._instant(end)
        sql = (
            f"select json_build_object('at', to_char(max(produced_at) at time zone 'UTC', {self._UTC})) "
            f"from event where produced_at < '{b}'"
        )
        value = self._query(sql) or {}
        return value.get("at")

    def engine_auth(self) -> dict[str, str | None]:
        sql = (
            f"select coalesce(json_object_agg(engine_id, to_char(at at time zone 'UTC', {self._UTC})), '{{}}') "
            "from (select engine_id, max(auth_ok_at) as at from engine_health group by engine_id) as latest"
        )
        return dict(self._query(sql) or {})


class LikePatterns:
    """SQL LIKE patterns (`%`, `_`) matched in Python, so a declared answerer list means the
    same thing here as it would in the database."""

    def __init__(self, patterns: Sequence[str]) -> None:
        self._compiled = [
            re.compile(
                "".join(".*" if c == "%" else "." if c == "_" else re.escape(c) for c in p) + r"\Z"
            )
            for p in patterns
        ]

    def match(self, text: str | None) -> bool:
        return bool(text) and any(p.match(str(text)) for p in self._compiled)


class QueueSource(SourceInterface):
    """What the local queue shows: who answered the gates, how BUILD finished, whether the
    paid engines' logins are fresh, whether anything reached DONE."""

    name = "queue"

    def __init__(
        self,
        settings: Settings,
        reader: QueueReaderInterface | None,
        unavailable: str = "",
    ) -> None:
        self._settings = settings
        self._cfg = settings.section("queue")
        self._reader = reader
        self._unavailable = unavailable

    @classmethod
    def from_environment(
        cls, settings: Settings, runner: CommandRunnerInterface, environ: Mapping[str, str]
    ) -> QueueSource:
        cfg = settings.section("queue")
        dsn = environ.get(cfg["dsn_env"], "")
        if not dsn:
            return cls(settings, None, f"no read-only queue DSN in ${cfg['dsn_env']}")
        return cls(settings, PsqlQueue(runner, cfg["psql"], dsn, float(cfg["timeout_seconds"])))

    def observe(self, cutoff: str) -> list[Figure]:
        days = int(self._settings.section("windows")["queue_days"])
        start = Instants.minus_days(cutoff, days)
        make = FigureFactory(self.name, cutoff, (start, cutoff))
        method = "the local queue, read only"
        if self._reader is None:
            return make.all_unknown(method, self._unavailable)
        try:
            return self._observe(make, start, cutoff)
        except SourceUnavailable as exc:
            return make.all_unknown(method, str(exc))

    def _observe(self, make: FigureFactory, start: str, end: str) -> list[Figure]:
        assert self._reader is not None
        cfg = self._cfg
        unattended = LikePatterns(cfg["unattended_answerers"])
        gates = self._reader.gates(start, end)
        by = "answered by " + ", ".join(f"`{p}`" for p in cfg["unattended_answerers"])
        figures: list[Figure] = []
        for phase, fid in (
            ("design", "queue.design.unattended_share"),
            ("review", "queue.review.unattended_share"),
        ):
            answered = [g for g in gates if g.get("phase") == phase and g.get("answered_by")]
            figures.append(
                make.share(
                    fid,
                    sum(1 for g in answered if unattended.match(g.get("answered_by"))),
                    len(answered),
                    f"`human_gate` rows raised in the window by {phase.upper()} jobs and answered; unattended = {by}",
                )
            )
        succeeded = self._reader.jobs_succeeded("build", start, end)
        escalations = sum(1 for g in gates if g.get("phase") == "build")
        figures.append(
            make.share(
                "queue.build.unattended_share",
                succeeded,
                succeeded + escalations,
                "BUILD jobs that reached `succeeded` in the window, over those plus the gates BUILD jobs raised in it",
            )
        )
        auth = self._reader.engine_auth()
        ttl = float(cfg["auth_ttl_hours"])
        paid = list(cfg["paid_engines"])
        fresh = [
            e for e in paid if auth.get(e) and 0 <= Instants.hours_between(str(auth[e]), end) <= ttl
        ]
        figure = make.share(
            "queue.engines.paid_auth_fresh_share",
            len(fresh),
            len(paid),
            f"each paid engine's latest `engine_health.auth_ok_at`, within {ttl:g} h of the cutoff",
        )
        stale = [e for e in paid if e not in fresh]
        figures.append(
            replace(
                figure,
                reason=(
                    "lapsed: "
                    + ", ".join(
                        f"{e} (last {Instants.day(auth.get(e)) if auth.get(e) else 'never'})"
                        for e in stale
                    )
                )
                if stale
                else "",
            )
        )
        figures.append(
            make.value(
                "queue.done_projects",
                self._reader.transitions("done", start, end),
                "`PhaseTransitioned` events into `done` in the window",
            )
        )
        last = self._reader.last_event_at(end)
        method = "the latest `event.produced_at` before the cutoff"
        figures.append(
            make.value(
                "queue.last_event_hours", round(Instants.hours_between(last, end), 1), method
            )
            if last
            else make.unknown("queue.last_event_hours", method, "the queue holds no event")
        )
        return figures


# ------------------------------------------------------------------------ staleness


class StalenessPolicy(StalenessPolicyInterface):
    """A figure this run could not read keeps the previous record's value, marked stale with
    the date it was last measured and why it was not re-read, for at most `max_stale_days`.
    After that it is unknown. A value is never reused silently (10.f)."""

    def __init__(self, max_stale_days: int) -> None:
        self._max = max_stale_days

    def merge(
        self, previous: Sequence[Mapping[str, Any]], fresh: Sequence[Figure], cutoff: str
    ) -> list[Figure]:
        before = {str(f["id"]): Figure.from_dict(f) for f in previous}
        out: list[Figure] = []
        for figure in fresh:
            old = before.get(figure.id)
            if figure.known or old is None or not old.known:
                out.append(figure)
                continue
            last = old.last_measured or old.observed_at
            age = Instants.hours_between(last, cutoff) / 24
            if age > self._max:
                out.append(
                    replace(
                        figure,
                        reason=f"{figure.reason}; the last value, of {Instants.day(last)}, is over {self._max} days old",
                    )
                )
                continue
            out.append(
                replace(
                    old,
                    status="stale",
                    observed_at=cutoff,
                    last_measured=last,
                    reason=f"not re-read at {Instants.day(cutoff)}: {figure.reason}",
                )
            )
        return out


# ------------------------------------------------------------------------ judging


@dataclass(frozen=True)
class CriterionVerdict:
    figure: str
    compare: str
    autonomous: Any
    partial: Any
    status: str
    reason: str


@dataclass(frozen=True)
class StageVerdict:
    id: str
    status: str
    criteria: tuple[CriterionVerdict, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "criteria": [asdict(c) for c in self.criteria],
        }


class StageEvaluator(StageEvaluatorInterface):
    """Judges each declared stage from the figures, by the rules the module docstring states.

    A stage is as far along as its weakest judged criterion: one criterion under its partial
    threshold makes the stage manual whatever the others say, because a person is still
    needed there. Unknown is the answer only when nothing judged falls short."""

    ORDER = ("manual", "partial", "autonomous")

    def criterion(
        self, criterion: Mapping[str, Any], figures: Mapping[str, Figure]
    ) -> CriterionVerdict:
        fid, compare = str(criterion["figure"]), str(criterion["compare"])
        auto, part = criterion["autonomous"], criterion.get("partial")

        def verdict(status: str, reason: str = "") -> CriterionVerdict:
            return CriterionVerdict(fid, compare, auto, part, status, reason)

        figure = figures.get(fid)
        if figure is None or not figure.known or figure.value is None:
            return verdict("unknown", figure.reason if figure else "no source reported it")
        need = int(criterion.get("min_sample") or 0)
        if figure.denominator is not None and figure.denominator < need:
            return verdict(
                "unknown", f"a sample of {figure.denominator}, under the declared minimum of {need}"
            )
        value = figure.value
        if compare == "is":
            return verdict("autonomous" if value == auto else "manual")
        number = float(value)
        if compare == ">=":
            meets, close = number >= float(auto), part is not None and number >= float(part)
        else:
            meets, close = number <= float(auto), part is not None and number <= float(part)
        return verdict("autonomous" if meets else "partial" if close else "manual")

    def stage(self, stage: Mapping[str, Any], figures: Mapping[str, Figure]) -> StageVerdict:
        criteria = tuple(self.criterion(c, figures) for c in stage["criteria"])
        known = [c.status for c in criteria if c.status != "unknown"]
        if not known:
            status = "unknown"
        else:
            weakest = min(known, key=self.ORDER.index)
            if weakest != "autonomous":
                status = weakest
            else:
                status = "autonomous" if len(known) == len(criteria) else "unknown"
        return StageVerdict(str(stage["id"]), status, criteria)

    def evaluate(
        self, stages: Sequence[Mapping[str, Any]], figures: Sequence[Figure]
    ) -> list[StageVerdict]:
        by_id = {f.id: f for f in figures}
        return [self.stage(stage, by_id) for stage in stages]

    @staticmethod
    def headline(verdicts: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        counts = {status: 0 for status in STAGE_STATUSES}
        for v in verdicts:
            counts[str(v["status"])] += 1
        return {**counts, "total": len(verdicts)}


# ------------------------------------------------------------------------ the record


class ScorecardLedger(ScorecardLedgerInterface):
    """The record: the family's digest-chained ledger, with this measurement's own format."""

    def __init__(self) -> None:
        self._ledger = CanaryLedger(record_format=RECORD_FORMAT, kind=RECORD_KIND)

    def read(self, path: Path) -> tuple[Mapping[str, Any], ...]:
        return self._ledger.read(path)

    def append(self, path: Path, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._ledger.append(path, payload)


class EntryBuilder:
    """Turns figures into one ledger payload: the figures, the stages as declared, and the
    verdicts and headline they give."""

    def __init__(self, settings: Settings, evaluator: StageEvaluator | None = None) -> None:
        self._settings = settings
        self._evaluator = evaluator or StageEvaluator()

    def build(
        self, figures: Sequence[Figure], cutoff: str, recorded_at: str, sources: Mapping[str, str]
    ) -> dict[str, Any]:
        stages = self._settings.stages
        verdicts = [v.to_dict() for v in self._evaluator.evaluate(stages, figures)]
        windows = self._settings.section("windows")
        return {
            "cutoff": cutoff,
            "recorded_at": recorded_at,
            "windows": {k: int(v) for k, v in windows.items()},
            "sources": dict(sources),
            "figures": [f.to_dict() for f in sorted(figures, key=lambda f: f.id)],
            "stages": stages,
            "stages_digest": self._settings.digest(),
            "verdicts": verdicts,
            "headline": StageEvaluator.headline(verdicts),
        }


# ------------------------------------------------------------------------ rendering


class GeneratedBlocks:
    """The marker convention: `<!-- BEGIN GENERATED autonomy:NAME — regenerated by SCRIPT -->`."""

    PATTERN = re.compile(
        r"<!-- BEGIN GENERATED autonomy:(?P<name>[a-z0-9-]+) — regenerated by "
        + re.escape(SCRIPT)
        + r" -->\n(?P<body>.*?)<!-- END GENERATED autonomy:(?P=name) -->",
        re.DOTALL,
    )

    @classmethod
    def wrap(cls, name: str, body: str) -> str:
        return (
            f"<!-- BEGIN GENERATED autonomy:{name} — regenerated by {SCRIPT} -->\n"
            f"{body.rstrip()}\n<!-- END GENERATED autonomy:{name} -->"
        )

    @classmethod
    def replace_all(cls, document: str, blocks: Mapping[str, str]) -> str:
        return cls.PATTERN.sub(
            lambda m: cls.wrap(m["name"], blocks[m["name"]]) if m["name"] in blocks else m.group(0),
            document,
        )

    @classmethod
    def drift(cls, document: str, blocks: Mapping[str, str]) -> list[str]:
        present = {m["name"]: m["body"] for m in cls.PATTERN.finditer(document)}
        return sorted(
            name
            for name, body in blocks.items()
            if name not in present or present[name].rstrip() != body.rstrip()
        )


class Formatter:
    """How a value, a threshold and a status read in a table."""

    @staticmethod
    def percent(value: float) -> str:
        return f"{value * 100:.0f}%"

    @classmethod
    def value(cls, figure: Mapping[str, Any]) -> str:
        if figure["status"] == "unknown" or figure["value"] is None:
            return "unknown"
        unit, value = figure["unit"], figure["value"]
        if unit == "share":
            text = f"{figure['numerator']} of {figure['denominator']} ({cls.percent(float(value))})"
        elif unit == "bool":
            text = "yes" if value else "no"
        elif unit == "hours":
            text = f"{float(value):,.1f} h"
        elif unit == "days":
            text = f"{float(value):,.1f} days"
        elif unit == "count":
            text = f"{int(value):,}"
        else:
            text = f"{float(value):.2f}"
        if figure["status"] == "stale":
            text += f" (stale, measured {Instants.day(figure.get('last_measured'))})"
        return text

    @classmethod
    def threshold(cls, criterion: Mapping[str, Any], unit: str) -> str:
        compare, auto = criterion["compare"], criterion["autonomous"]
        if compare == "is":
            return "yes" if auto is True else "no" if auto is False else str(auto)
        sign = "≥" if compare == ">=" else "≤"
        if unit == "share":
            amount = cls.percent(float(auto))
        elif unit == "hours":
            amount = f"{float(auto):g} h"
        else:
            amount = f"{auto:g}" if isinstance(auto, float) else str(auto)
        sample = int(criterion.get("min_sample") or 0)
        return f"{sign} {amount}" + (f", n ≥ {sample}" if sample > 1 else "")

    @staticmethod
    def cell(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ")


class EntryView:
    """The latest ledger payload, indexed for rendering."""

    def __init__(self, entry: Mapping[str, Any], settings: Settings) -> None:
        self.entry = entry
        self.settings = settings
        self.figures = {str(f["id"]): f for f in entry["figures"]}
        self.verdicts = {str(v["id"]): v for v in entry["verdicts"]}
        self.stages = list(entry["stages"])
        self.headline = entry["headline"]

    @property
    def cutoff(self) -> str:
        return str(self.entry["cutoff"])

    def not_autonomous(self) -> list[tuple[Mapping[str, Any], str]]:
        return [
            (stage, str(self.verdicts[stage["id"]]["status"]))
            for stage in self.stages
            if self.verdicts[stage["id"]]["status"] != "autonomous"
        ]

    def count_sentence(self) -> str:
        h = self.headline
        parts = [f"{h[s]} {s}" for s in ("partial", "manual", "unknown") if h[s]]
        return f"{h['autonomous']} of {h['total']} stages autonomous" + (
            f" ({', '.join(parts)})" if parts else ""
        )

    def rows(
        self,
    ) -> list[tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]]:
        """(stage, criterion as declared, its verdict, its figure), stage by stage."""
        out = []
        for stage in self.stages:
            verdict = self.verdicts[stage["id"]]
            for declared, judged in zip(stage["criteria"], verdict["criteria"], strict=True):
                out.append((stage, declared, judged, self.figures[declared["figure"]]))
        return out


class DocsPageRenderer(ScorecardRendererInterface):
    """The reference page: the headline, the table, each stage's evidence, every figure."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _provenance(self, view: EntryView) -> str:
        record = self._settings.scorecard["record"]
        return (
            f"*Measured {Instants.minute(view.cutoff)} (the cutoff). Source: "
            f"[`{record}`]({REPO_URL}/{record}), regenerated by `{SCRIPT}`; "
            "do not edit inside these markers.*\n\n"
        )

    def blocks(self, entry: Mapping[str, Any]) -> dict[str, str]:
        view = EntryView(entry, self._settings)
        return {
            "headline": self._headline(view),
            "table": self._table(view),
            "evidence": self._evidence(view),
            "figures": self._figures(view),
        }

    def _headline(self, view: EntryView) -> str:
        missing = view.not_autonomous()
        listed = "".join(f"- **{s['title']}**: {status}\n" for s, status in missing) or "- none\n"
        return (
            self._provenance(view)
            + f"**{view.count_sentence()}** at the cutoff, {Instants.minute(view.cutoff)}.\n\n"
            + "Not yet autonomous:\n\n"
            + listed
        )

    def _table(self, view: EntryView) -> str:
        head = (
            self._provenance(view)
            + "| Stage | Metric | Value | Autonomous at | Criterion | Stage |\n|---|---|---|---|---|---|\n"
        )
        body = ""
        for stage, declared, judged, figure in view.rows():
            status = view.verdicts[stage["id"]]["status"]
            body += (
                "| "
                + " | ".join(
                    Formatter.cell(c)
                    for c in (
                        f"[{stage['title']}](#{stage['id']})",
                        figure["label"],
                        Formatter.value(figure),
                        Formatter.threshold(declared, figure["unit"]),
                        judged["status"],
                        f"**{status}**",
                    )
                )
                + " |\n"
            )
        return head + body

    def _evidence(self, view: EntryView) -> str:
        out = self._provenance(view)
        figure_rows = {d["figure"]: (j, f) for s, d, j, f in view.rows()}
        for stage in view.stages:
            status = view.verdicts[stage["id"]]["status"]
            out += f"### {stage['title']} {{ #{stage['id']} }}\n\n"
            out += f"**Status: {status}.** {stage['question']}\n\n"
            for declared in stage["criteria"]:
                judged, figure = figure_rows[declared["figure"]]
                window = figure.get("window")
                when = (
                    f"window {Instants.day(window[0])} to {Instants.minute(window[1])}"
                    if window
                    else f"read {Instants.minute(figure['observed_at'])}"
                )
                said = f" {judged['reason']}." if judged["reason"] else ""
                note = (
                    f" Note: {figure['reason']}."
                    if figure.get("reason") and figure["reason"] != judged["reason"]
                    else ""
                )
                out += (
                    f"- *{figure['label']}*: **{Formatter.value(figure)}**, {figure['status']}; "
                    f"autonomous at {Formatter.threshold(declared, figure['unit'])}; criterion "
                    f"**{judged['status']}**.{said}{note} Source: {figure['source']}, {when}; {figure['method']}. "
                    f"Why this threshold: {declared['reason']}\n"
                )
            out += f"\n**What would close it:** {stage['closes']}\n\n"
            out += "Answers to: " + ", ".join(stage["refs"]) + ".\n\n"
        return out

    def _figures(self, view: EntryView) -> str:
        out = (
            self._provenance(view)
            + "| Figure | Value | Status | Source | Reason |\n|---|---|---|---|---|\n"
        )
        for fid in sorted(view.figures):
            f = view.figures[fid]
            out += (
                "| "
                + " | ".join(
                    Formatter.cell(c)
                    for c in (
                        f"`{fid}`",
                        Formatter.value(f),
                        f["status"],
                        f["source"],
                        f.get("reason") or "-",
                    )
                )
                + " |\n"
            )
        return out


class SummaryRenderer(ScorecardRendererInterface):
    """The short block the README and the documentation's landing page carry."""

    def __init__(self, settings: Settings, page_link: str) -> None:
        self._settings = settings
        self._link = page_link

    def blocks(self, entry: Mapping[str, Any]) -> dict[str, str]:
        view = EntryView(entry, self._settings)
        missing = (
            ", ".join(f"{s['title']} ({status})" for s, status in view.not_autonomous()) or "none"
        )
        record = self._settings.scorecard["record"]
        return {
            "summary": (
                f"**Distance from full autonomy: {view.count_sentence()}**, measured at "
                f"{Instants.minute(view.cutoff)} from the forge, the review canary, the code and "
                f"the local queue. Not yet autonomous: {missing}. Each stage's metric, threshold, "
                f"evidence and what would close it are on [How far vibey is from full autonomy]"
                f"({self._link}); the record is [`{record}`]({REPO_URL}/{record}). "
                f"*Regenerated by `{SCRIPT}`; do not edit inside these markers.*\n"
            )
        }


class PaperRenderer(ScorecardRendererInterface):
    """The paper's scorecard: one sentence with the count and the cutoff, then a LaTeX
    `table*` in a ```latex fence, like the paper's other generated tables."""

    LABEL = "tab:autonomy-scorecard"
    _TEX: Mapping[str, str] = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "$": r"\$",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "[": "{[}",
        "]": "{]}",
        "`": "",
        "≥": r"$\geq$",
        "≤": r"$\leq$",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @classmethod
    def tex(cls, text: str) -> str:
        return "".join(cls._TEX.get(ch, ch) for ch in text)

    def blocks(self, entry: Mapping[str, Any]) -> dict[str, str]:
        view = EntryView(entry, self._settings)
        record = self._settings.scorecard["record"]
        h = view.headline
        missing = ", ".join(f"{s['title']} ({status})" for s, status in view.not_autonomous())
        sentence = (
            f"At the latest measurement's cutoff, {Instants.minute(view.cutoff)}, "
            f"{h['autonomous']} of the {h['total']} declared stages of the delivery loop met "
            f"every threshold for running without a person"
            + (f"; not yet autonomous: {missing}." if missing else ".")
            + f" The record is `{record}`."
        )
        lines = [
            sentence,
            "",
            "```latex",
            r"\begin{table*}[t]",
            r"\centering\footnotesize",
            r"\begin{tabular}{@{}p{1.55in}p{2.2in}p{1.25in}p{0.75in}p{0.65in}@{}}",
            r"\textbf{Stage} & \textbf{Metric} & \textbf{Value} & \textbf{Threshold} & \textbf{Status}\\",
            r"\hline",
        ]
        for stage, declared, _judged, figure in view.rows():
            status = view.verdicts[stage["id"]]["status"]
            cells = (
                stage["title"],
                figure["label"],
                Formatter.value(figure),
                Formatter.threshold(declared, figure["unit"]),
                status,
            )
            lines.append(" & ".join(self.tex(c) for c in cells) + r"\\")
        windows = view.entry["windows"]
        lines += [
            r"\end{tabular}",
            r"\caption{The autonomy scorecard: each declared stage of the delivery loop, the "
            r"figures that judge it, and the threshold at which it counts as running without a "
            r"person. A stage is as far along as its weakest criterion, and unknown when nothing "
            r"judged falls short but something could not be judged. "
            + self.tex(
                f"Cutoff {Instants.minute(view.cutoff)}; forge figures over the {windows['forge_days']} days "
                f"before it, queue figures over {windows['queue_days']}. A stale value is the last "
                f"good one, with the date it was measured. Record {record}, regenerated by {SCRIPT}."
            )
            + "}",
            rf"\label{{{self.LABEL}}}",
            r"\end{table*}",
            "```",
        ]
        return {"paper": "\n".join(lines)}


# ------------------------------------------------------------------------ the command


class Scorecard:
    """Observe, record, render and check, against one repository root."""

    def __init__(
        self,
        root: Path = Path("."),
        *,
        clock: ClockInterface | None = None,
        runner: CommandRunnerInterface | None = None,
        forge: ForgeClientInterface | None = None,
        queue: QueueReaderInterface | None = None,
        environ: Mapping[str, str] | None = None,
        config: str = DEFAULT_CONFIG,
    ) -> None:
        self.root = root
        self.settings = Settings.load(root / config)
        self._clock = clock or SystemClock()
        self._runner = runner or SubprocessRunner()
        self._forge = forge
        self._queue = queue
        self._environ = os.environ if environ is None else environ
        self._ledger = ScorecardLedger()

    # -------------------------------------------------------------- sources

    def sources(self, names: Sequence[str]) -> list[SourceInterface]:
        s = self.settings
        out: list[SourceInterface] = []
        for name in names:
            if name == "forge":
                out.append(
                    ForgeSource(self._forge or GhForge(self._runner, s.scorecard["repository"]), s)
                )
            elif name == "canary":
                out.append(CanarySource(self._runner, s))
            elif name == "repo":
                out.append(RepoSource(self.root, s))
            elif name == "queue":
                out.append(
                    QueueSource(s, self._queue)
                    if self._queue is not None
                    else QueueSource.from_environment(s, self._runner, self._environ)
                )
            else:
                raise ValueError(f"no such source: {name}")
        return out

    def observe(self, names: Sequence[str]) -> dict[str, Any]:
        cutoff = self._clock.now()
        figures: list[Figure] = []
        sources: dict[str, str] = {}
        for source in self.sources(names):
            observed = source.observe(cutoff)
            figures += observed
            reasons = [f.reason for f in observed if not f.known]
            sources[source.name] = (
                "observed" if any(f.known for f in observed) else f"unavailable: {reasons[0]}"
            )
        return {"cutoff": cutoff, "sources": sources, "figures": [f.to_dict() for f in figures]}

    # -------------------------------------------------------------- the record

    @property
    def record_path(self) -> Path:
        return self.root / str(self.settings.scorecard["record"])

    def entries(self) -> tuple[Mapping[str, Any], ...]:
        return self._ledger.read(self.record_path)

    def record(self, observations: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        if not observations:
            raise ValueError("record needs at least one observation")
        cutoff = max(str(o["cutoff"]) for o in observations)
        fresh: dict[str, Figure] = {}
        sources: dict[str, str] = {}
        for observation in observations:
            sources.update(observation.get("sources") or {})
            for raw in observation["figures"]:
                figure = Figure.from_dict(raw)
                if figure.id not in fresh or (figure.known and not fresh[figure.id].known):
                    fresh[figure.id] = figure
        for spec in FigureCatalog.SPECS:
            if spec.id not in fresh:
                fresh[spec.id] = FigureFactory(spec.source, cutoff, None).unknown(
                    spec.id, "not observed", f"this run did not observe the {spec.source} source"
                )
                sources.setdefault(spec.source, "not observed by this run")
        entries = self.entries()
        previous = entries[-1]["figures"] if entries else []
        merged = StalenessPolicy(int(self.settings.scorecard["max_stale_days"])).merge(
            previous, list(fresh.values()), cutoff
        )
        payload = EntryBuilder(self.settings).build(merged, cutoff, self._clock.now(), sources)
        self._ledger.append(self.record_path, payload)
        self.render()
        return payload

    def reevaluate(self) -> Mapping[str, Any]:
        entries = self.entries()
        if not entries:
            raise ValueError(
                f"{self.settings.scorecard['record']} holds no measurement to re-judge"
            )
        latest = entries[-1]
        figures = [Figure.from_dict(f) for f in latest["figures"]]
        payload = EntryBuilder(self.settings).build(
            figures, str(latest["cutoff"]), self._clock.now(), latest["sources"]
        )
        self._ledger.append(self.record_path, payload)
        self.render()
        return payload

    # -------------------------------------------------------------- the documents

    def documents(self) -> dict[str, ScorecardRendererInterface]:
        s = self.settings.scorecard
        page = s["docs_page"]
        index_dir = str(Path(s["docs_index"]).parent)
        return {
            page: DocsPageRenderer(self.settings),
            s["readme"]: SummaryRenderer(self.settings, page),
            s["docs_index"]: SummaryRenderer(self.settings, os.path.relpath(page, index_dir)),
            s["paper"]: PaperRenderer(self.settings),
        }

    def render(self) -> list[str]:
        entries = self.entries()
        if not entries:
            return []
        written = []
        for name, renderer in self.documents().items():
            path = self.root / name
            text = path.read_text(encoding="utf-8")
            updated = GeneratedBlocks.replace_all(text, renderer.blocks(entries[-1]))
            if updated != text:
                path.write_text(updated, encoding="utf-8")
                written.append(name)
        return written

    def check(self) -> list[str]:
        problems: list[str] = []
        try:
            entries = self.entries()
        except (ValueError, TypeError) as exc:
            return [f"the record is not an append-only chain: {exc}"]
        if not entries:
            return [f"{self.settings.scorecard['record']} holds no measurement"]
        latest = entries[-1]
        figures = [Figure.from_dict(f) for f in latest["figures"]]
        judged = [v.to_dict() for v in StageEvaluator().evaluate(latest["stages"], figures)]
        if judged != latest["verdicts"]:
            problems.append("the latest verdicts do not follow from its figures and stages")
        if StageEvaluator.headline(latest["verdicts"]) != latest["headline"]:
            problems.append("the latest headline does not follow from its verdicts")
        if latest["stages"] != self.settings.stages:
            problems.append(
                f"the stages in {DEFAULT_CONFIG} differ from the latest measurement's: run "
                f"`python {SCRIPT} reevaluate`"
            )
        missing = sorted(set(FigureCatalog.ids()) - {f.id for f in figures})
        if missing:
            problems.append("the latest measurement lacks figures: " + ", ".join(missing))
        for name, renderer in self.documents().items():
            text = (self.root / name).read_text(encoding="utf-8")
            for block in GeneratedBlocks.drift(text, renderer.blocks(latest)):
                problems.append(
                    f"{name}: block autonomy:{block} is missing or out of date (run `python {SCRIPT} render`)"
                )
        return problems


class ScorecardCli:
    """`python scripts/autonomy_scorecard.py <command>`."""

    SOURCES = ("forge", "canary", "repo", "queue")

    def __init__(self, scorecard: Scorecard | None = None) -> None:
        self._scorecard = scorecard

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog=SCRIPT, description=__doc__.split("\n\n")[0] if __doc__ else None
        )
        parser.add_argument("--root", type=Path, default=Path("."))
        commands = parser.add_subparsers(dest="command", required=True)
        observe = commands.add_parser("observe", help="observe figures and write them to a file")
        observe.add_argument("--sources", default=",".join(self.SOURCES))
        observe.add_argument("--out", type=Path, required=True)
        record = commands.add_parser("record", help="merge observations, judge, append, render")
        record.add_argument("observations", nargs="+", type=Path)
        measure = commands.add_parser("measure", help="observe every source, record and render")
        measure.add_argument("--sources", default=",".join(self.SOURCES))
        commands.add_parser("reevaluate", help="judge the latest figures by the current stages")
        commands.add_parser("render", help="rewrite the GENERATED blocks from the latest entry")
        commands.add_parser("check", help="exit 1 if the record or any block is out of step")
        return parser

    def run(self, argv: Sequence[str]) -> int:
        args = self.parser().parse_args(argv)
        card = self._scorecard or Scorecard(args.root)
        if args.command == "observe":
            observed = card.observe([s for s in args.sources.split(",") if s])
            args.out.write_text(
                json.dumps(observed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(
                f"observed {len(observed['figures'])} figures at {observed['cutoff']} -> {args.out}"
            )
            return 0
        if args.command in ("record", "measure", "reevaluate"):
            if args.command == "record":
                observations = [
                    json.loads(p.read_text(encoding="utf-8")) for p in args.observations
                ]
                payload = card.record(observations)
            elif args.command == "measure":
                payload = card.record([card.observe([s for s in args.sources.split(",") if s])])
            else:
                payload = card.reevaluate()
            view = EntryView(payload, card.settings)
            print(f"{view.count_sentence()} at {view.cutoff}")
            for stage, status in view.not_autonomous():
                print(f"  - {stage['id']}: {status}")
            return 0
        if args.command == "render":
            for name in card.render():
                print(f"rewrote {name}")
            return 0
        problems = card.check()
        for problem in problems:
            print(f"autonomy scorecard: {problem}", file=sys.stderr)
        return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(ScorecardCli().run(sys.argv[1:]))
