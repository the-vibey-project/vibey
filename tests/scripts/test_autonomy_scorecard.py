# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/autonomy_scorecard.py`: the figures, the judging, staleness, the record, rendering.

Every source is driven through a fake (a forge that answers from fixture JSON shaped like
`gh`'s, a queue reader that answers from rows, a command runner for the canary), so each
decision about a failure -- say it is unknown, say why, never invent a value -- is exercised
without the network or the database.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from scripts import autonomy_scorecard as sc
from scripts.interfaces import autonomy_scorecard_interface as contracts

REPO = Path(__file__).resolve().parents[2]
SETTINGS = sc.Settings.load(REPO / sc.DEFAULT_CONFIG)
CUTOFF = "2026-10-02T00:00:00Z"
OPERATOR = SETTINGS.scorecard["operator"]
APPROVER = SETTINGS.scorecard["approver"]


class FixedClock:
    def __init__(self, stamp: str = CUTOFF) -> None:
        self.stamp = stamp

    def now(self) -> str:
        return self.stamp


def pull(number: int, merged_by: str = OPERATOR, reviews: Sequence[tuple[str, str]] = (), at: str = "2026-09-30T12:00:00Z") -> dict[str, Any]:  # fmt: skip
    return {
        "number": number,
        "author": {"login": OPERATOR},
        "mergedAt": at,
        "mergedBy": {"login": merged_by},
        "headRefOid": f"{number:040d}",
        "reviews": [{"author": {"login": who}, "state": state} for who, state in reviews],
    }


def run(event: str = "push", conclusion: str = "success", attempt: int = 1, at: str = "2026-09-30T12:00:00Z", actor_type: str = "User") -> dict[str, Any]:  # fmt: skip
    return {
        "created_at": at,
        "event": event,
        "status": "completed",
        "conclusion": conclusion,
        "run_attempt": attempt,
        "actor": "someone",
        "actor_type": actor_type,
    }


class FakeForge:
    """Answers like `gh`, from fixtures; a `failing` method raises SourceUnavailable."""

    def __init__(self, failing: Sequence[str] = ()) -> None:
        self.failing = set(failing)
        self.pulls: dict[str, list[dict[str, Any]]] = {
            "develop": [
                pull(1, reviews=[(APPROVER, "APPROVED")]),
                pull(2, merged_by="merge-bot", reviews=[("someone", "COMMENTED")]),
                pull(3),
                pull(4, at="2026-09-01T00:00:00Z"),  # before the window: left out
            ],
            "main": [pull(10), pull(11, merged_by="merge-bot")],
        }
        self.checks = {
            f"{1:040d}": [
                {"completed_at": "2026-09-30T10:00:00Z", "output": {"title": "PR review: review incomplete (needs a human review)"}},
                {"completed_at": "2026-09-30T11:00:00Z", "output": {"title": "PR review: gate (sovereign lane, whole review)"}},
            ],
            f"{2:040d}": [{"completed_at": "2026-09-30T11:00:00Z", "output": {"title": "PR review: sovereign lane found blocking findings"}}],
        }  # fmt: skip
        self.rules = [
            {
                "target": "branch",
                "enforcement": "active",
                "conditions": {"ref_name": {"include": ["refs/heads/develop"]}},
                "rules": [
                    {"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "gates"}]}}
                ],
            },
            {"target": "branch", "enforcement": "disabled", "conditions": {"ref_name": {"include": ["~ALL"]}}, "rules": []},
        ]  # fmt: skip
        self.runs = {
            "ci.yml": [run(), run(), run(conclusion="failure", attempt=2), run(conclusion="cancelled"), run(at="2026-08-01T00:00:00Z")],
            "promote-to-main.yml": [run("workflow_run"), run("schedule"), run("workflow_dispatch"), run("workflow_dispatch", actor_type="Bot"), run("workflow_run", conclusion="skipped")],
            "vibey-engine.yml": [run(), run(conclusion="failure")],
        }  # fmt: skip
        self.calls: list[tuple[Any, ...]] = []

    def _maybe_fail(self, name: str) -> None:
        if name in self.failing:
            raise sc.SourceUnavailable(f"{name}: HTTP 403")

    def merged_pulls(self, base: str, since: str) -> list[dict[str, Any]]:
        self._maybe_fail(f"merged_pulls:{base}")
        self.calls.append(("merged_pulls", base, since))
        return self.pulls[base]

    def check_runs(self, sha: str, name: str) -> list[dict[str, Any]]:
        self._maybe_fail("check_runs")
        return self.checks.get(sha, [])

    def rulesets(self) -> list[dict[str, Any]]:
        self._maybe_fail("rulesets")
        return self.rules

    def workflow_runs(self, workflow: str, *, branch: str | None, event: str | None, since: str) -> list[dict[str, Any]]:  # fmt: skip
        self._maybe_fail(f"runs:{workflow}")
        self.calls.append(("runs", workflow, branch, event, since))
        return self.runs[workflow]


class FakeQueue:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.rows = [
            {"kind": "question", "phase": "design", "answered_by": "automation:triaged-delivery"},
            {"kind": "question", "phase": "design", "answered_by": "gate-timeout"},
            {"kind": "question", "phase": "design", "answered_by": "cli"},
            {"kind": "question", "phase": "design", "answered_by": None},  # waiting: not answered
            {"kind": "budget_exhausted", "phase": "build", "answered_by": "cli"},
            {"kind": "choice", "phase": "review", "answered_by": "gate-timeout"},
        ]

    def gates(self, start: str, end: str) -> list[dict[str, Any]]:
        if self.fail:
            raise sc.SourceUnavailable("the queue did not answer: connection refused")
        return self.rows

    def jobs_succeeded(self, phase: str, start: str, end: str) -> int:
        return 9

    def transitions(self, to: str, start: str, end: str) -> int:
        return 2

    def last_event_at(self, end: str) -> str | None:
        return "2026-10-01T12:00:00Z"

    def engine_auth(self) -> dict[str, str | None]:
        return {
            "claudeloop": "2026-10-01T23:00:00Z",
            "codexloop": "2026-09-28T00:00:00Z",
            "gptossloop": "2026-10-01T23:00:00Z",
        }


class FakeRunner:
    def __init__(self, result: sc.CommandResult) -> None:
        self.result = result
        self.calls: list[list[str]] = []
        self.envs: list[Mapping[str, str] | None] = []

    def run(self, argv: Sequence[str], *, timeout: float, env: Mapping[str, str] | None = None) -> sc.CommandResult:  # fmt: skip
        self.calls.append(list(argv))
        self.envs.append(env)
        return self.result


def by_id(figures: Sequence[sc.Figure]) -> dict[str, sc.Figure]:
    return {f.id: f for f in figures}


CANARY = {
    "meets_floor": True,
    "reasons": [],
    "recall": {"low": 0.5242, "high": 0.857},
    "false_positive": {"low": 0.0, "high": 0.2153},
    "age_days": 0.5,
}


# --------------------------------------------------------------------------- contracts


def test_every_class_implements_the_contract_beside_it() -> None:
    forge = sc.ForgeSource(FakeForge(), SETTINGS)
    assert isinstance(sc.SystemClock().now(), str)
    pairs = [
        (sc.SystemClock(), contracts.ClockInterface),
        (sc.SubprocessRunner(), contracts.CommandRunnerInterface),
        (
            sc.GhForge(FakeRunner(sc.CommandResult(0, "", "")), "o/r"),
            contracts.ForgeClientInterface,
        ),
        (forge, contracts.SourceInterface),
        (sc.StalenessPolicy(14), contracts.StalenessPolicyInterface),
        (sc.StageEvaluator(), contracts.StageEvaluatorInterface),
        (sc.ScorecardLedger(), contracts.ScorecardLedgerInterface),
        (sc.DocsPageRenderer(SETTINGS), contracts.ScorecardRendererInterface),
    ]
    for instance, interface in pairs:
        for name in (n for n in vars(interface) if not n.startswith("_")):
            assert callable(getattr(instance, name)) or hasattr(instance, name), (instance, name)


def test_the_declared_stages_name_only_figures_a_source_observes() -> None:
    names = {c["figure"] for stage in SETTINGS.stages for c in stage["criteria"]}
    assert names <= set(sc.FigureCatalog.ids())
    bad = {"scorecard": dict(SETTINGS.scorecard), "stage": [{"id": "x", "criteria": [{"figure": "nope", "compare": ">="}]}]}  # fmt: skip
    with pytest.raises(ValueError, match="no source observes nope"):
        sc.Settings(bad).validate()
    bad["stage"] = [{"id": "x", "criteria": [{"figure": "forge.ci.success_share", "compare": ">"}]}]
    with pytest.raises(ValueError, match="is not one of"):
        sc.Settings(bad).validate()
    bad["stage"] = [{"id": "x", "criteria": []}]
    with pytest.raises(ValueError, match="declares no criteria"):
        sc.Settings(bad).validate()


# --------------------------------------------------------------------------- the forge


def test_the_forge_figures_are_computed_from_the_merged_pulls_and_runs_in_the_window() -> None:
    forge = FakeForge()
    figures = by_id(sc.ForgeSource(forge, SETTINGS).observe(CUTOFF))
    assert set(figures) == {s.id for s in sc.FigureCatalog.of("forge")}
    verdict = figures["forge.review.verdict_share"]
    # #1's latest check is a pass and #2's a block: both verdicts; #3 has none; #4 is outside.
    assert (verdict.numerator, verdict.denominator, verdict.status) == (2, 3, "measured")
    assert verdict.window == ("2026-09-18T00:00:00Z", CUTOFF)
    assert (figures["forge.approval.approver_share"].numerator, figures["forge.approval.approver_share"].denominator) == (1, 3)  # fmt: skip
    assert figures["forge.merge.not_operator_share"].numerator == 1
    assert figures["forge.merge.reviewed_share"].numerator == 1
    assert figures["forge.merge.reviews_per_merge"].value == 0.67
    assert figures["forge.approval.gate_required"].value is False
    assert "required: gates" in figures["forge.approval.gate_required"].method
    ci, rerun = figures["forge.ci.success_share"], figures["forge.ci.rerun_share"]
    assert (ci.numerator, ci.denominator) == (2, 3), "the cancelled run is not an outcome"
    assert (rerun.numerator, rerun.denominator) == (1, 4)
    assert figures["forge.promotion.hand_dispatches"].value == 1, "a bot's dispatch is not a hand"
    assert figures["forge.promotion.main_not_operator_share"].numerator == 1
    assert (figures["forge.release.success_share"].numerator, figures["forge.release.success_share"].denominator) == (1, 2)  # fmt: skip
    assert ("runs", "ci.yml", "develop", "push", "2026-09-18T00:00:00Z") in forge.calls


def test_a_required_review_gate_is_found_in_any_ruleset_that_applies() -> None:
    forge = FakeForge()
    forge.rules[0]["rules"][0]["parameters"]["required_status_checks"].append(
        {"context": "PR review / gate"}
    )
    figure = by_id(sc.ForgeSource(forge, SETTINGS).observe(CUTOFF))["forge.approval.gate_required"]
    assert figure.value is True
    forge.rules = [forge.rules[1]]
    figure = by_id(sc.ForgeSource(forge, SETTINGS).observe(CUTOFF))["forge.approval.gate_required"]
    assert figure.status == "unknown" and "no active ruleset applies" in figure.reason


@pytest.mark.parametrize(
    ("failing", "unknown"),
    [
        ("merged_pulls:develop", {"forge.review.verdict_share", "forge.approval.approver_share", "forge.merge.not_operator_share", "forge.merge.reviewed_share", "forge.merge.reviews_per_merge"}),
        ("check_runs", {"forge.review.verdict_share"}),
        ("rulesets", {"forge.approval.gate_required"}),
        ("runs:ci.yml", {"forge.ci.success_share", "forge.ci.rerun_share"}),
        ("runs:promote-to-main.yml", {"forge.promotion.hand_dispatches"}),
        ("merged_pulls:main", {"forge.promotion.main_not_operator_share"}),
        ("runs:vibey-engine.yml", {"forge.release.success_share"}),
    ],
)  # fmt: skip
def test_a_forge_query_that_fails_leaves_its_figures_unknown_with_the_reason(failing: str, unknown: set[str]) -> None:  # fmt: skip
    figures = sc.ForgeSource(FakeForge([failing]), SETTINGS).observe(CUTOFF)
    lost = {f.id for f in figures if not f.known}
    assert lost == unknown
    assert all("HTTP 403" in f.reason and f.value is None for f in figures if not f.known)


def test_an_empty_window_is_unknown_not_zero() -> None:
    forge = FakeForge()
    forge.pulls["develop"] = []
    figures = by_id(sc.ForgeSource(forge, SETTINGS).observe(CUTOFF))
    assert figures["forge.merge.reviewed_share"].status == "unknown"
    assert "0 of 0" in figures["forge.merge.reviewed_share"].reason
    assert figures["forge.merge.reviews_per_merge"].status == "unknown"


def test_gh_forge_builds_its_queries_and_reports_failures() -> None:
    lines = sc.CommandResult(0, '{"id": 7}\n\n{"id": 8}\n', "")
    runner = FakeRunner(lines)
    gh = sc.GhForge(runner, "o/r")
    assert gh.check_runs("abc", "PR review / gate") == [{"id": 7}, {"id": 8}]
    assert "check_name=PR%20review%20/%20gate" in runner.calls[-1][2]
    gh.workflow_runs("ci.yml", branch="develop", event="push", since="2026-09-18T01:02:03Z")
    assert runner.calls[-1][2] == "repos/o/r/actions/workflows/ci.yml/runs?per_page=100&created=>=2026-09-18&branch=develop&event=push"  # fmt: skip
    runner.result = sc.CommandResult(0, '[{"number": 1}]', "")
    assert gh.merged_pulls("develop", "2026-09-18T00:00:00Z") == [{"number": 1}]
    assert "merged:>=2026-09-18" in runner.calls[-1]
    runner.result = sc.CommandResult(0, '{"id": 3}\n', "")
    assert gh.rulesets() == [{"id": 3}]
    runner.result = sc.CommandResult(1, "", "HTTP 401: Bad credentials\n")
    with pytest.raises(sc.SourceUnavailable, match="Bad credentials"):
        gh.merged_pulls("develop", CUTOFF)
    runner.result = sc.CommandResult(0, "not json", "")
    with pytest.raises(sc.SourceUnavailable, match="did not return JSON"):
        gh.merged_pulls("develop", CUTOFF)
    with pytest.raises(sc.SourceUnavailable, match="not JSON"):
        gh.check_runs("abc", "x")


# --------------------------------------------------------------------------- the canary


def test_the_canary_is_read_through_its_own_status_command() -> None:
    runner = FakeRunner(sc.CommandResult(0, json.dumps(CANARY), ""))
    figures = by_id(sc.CanarySource(runner, SETTINGS).observe(CUTOFF))
    assert runner.calls[0][1:] == ["-m", "vibey_gh", "review-canary", "status", "--json"]
    assert figures["canary.meets_floor"].value is True
    assert figures["canary.recall_lower_bound"].value == 0.524
    assert figures["canary.false_positive_upper_bound"].value == 0.215
    assert figures["canary.age_days"].value == 0.5


def test_a_canary_under_its_floor_says_why_and_one_with_no_measurement_is_unknown() -> None:
    below = {**CANARY, "meets_floor": False, "reasons": ["recall lower bound 0.30 is under 0.5"]}
    figures = by_id(sc.CanarySource(FakeRunner(sc.CommandResult(1, json.dumps(below), "")), SETTINGS).observe(CUTOFF))  # fmt: skip
    assert figures["canary.meets_floor"].value is False
    assert "under 0.5" in figures["canary.meets_floor"].reason
    none = {"meets_floor": None, "reasons": ["no measurement is recorded"]}
    figures = by_id(sc.CanarySource(FakeRunner(sc.CommandResult(3, json.dumps(none), "")), SETTINGS).observe(CUTOFF))  # fmt: skip
    assert figures["canary.meets_floor"].status == "unknown"
    assert figures["canary.recall_lower_bound"].status == "unknown"


@pytest.mark.parametrize("result", [sc.CommandResult(2, "", "vibey-gh: review-canary: boom"), sc.CommandResult(0, "{oops", "")])  # fmt: skip
def test_a_canary_that_does_not_answer_is_unknown(result: sc.CommandResult) -> None:
    figures = sc.CanarySource(FakeRunner(result), SETTINGS).observe(CUTOFF)
    assert all(f.status == "unknown" for f in figures)
    assert "did not answer" in figures[0].reason


# --------------------------------------------------------------------------- the repository


def test_the_review_gate_kinds_that_may_time_out_are_read_from_the_code(tmp_path: Path) -> None:
    figure = sc.RepoSource(REPO, SETTINGS).observe(CUTOFF)[0]
    assert figure.status == "declared"
    assert (figure.numerator, figure.denominator) == (1, 2)
    assert "`approval`" in figure.reason
    module = tmp_path / SETTINGS.section("repo")["gate_timeout_module"]
    module.parent.mkdir(parents=True)
    module.write_text("DEFAULT_ANSWER_KEYS: dict[str, str] = {'approval': 'x', 'choice': 'y'}\n")
    figure = sc.RepoSource(tmp_path, SETTINGS).observe(CUTOFF)[0]
    assert (figure.value, figure.reason) == (1.0, "")
    module.write_text("DEFAULT_ANSWER_KEYS = 3\n")
    assert sc.RepoSource(tmp_path, SETTINGS).observe(CUTOFF)[0].status == "unknown"
    module.unlink()
    assert sc.RepoSource(tmp_path, SETTINGS).observe(CUTOFF)[0].status == "unknown"


# --------------------------------------------------------------------------- the queue


class NeverCheckedQueue(FakeQueue):
    def engine_auth(self) -> dict[str, str | None]:
        return {"claudeloop": "2026-10-01T23:00:00Z", "codexloop": None}


def test_a_paid_engine_never_checked_reads_as_lapsed_never() -> None:
    figures = by_id(sc.QueueSource(SETTINGS, NeverCheckedQueue()).observe(CUTOFF))
    engines = figures["queue.engines.paid_auth_fresh_share"]
    assert (engines.numerator, engines.denominator) == (1, 2)
    assert engines.reason == "lapsed: codexloop (last never)"


def test_the_queue_figures_count_who_answered_and_what_finished() -> None:
    figures = by_id(sc.QueueSource(SETTINGS, FakeQueue()).observe(CUTOFF))
    design = figures["queue.design.unattended_share"]
    assert (design.numerator, design.denominator) == (2, 3), "the waiting gate is not answered"
    assert design.window == ("2026-09-02T00:00:00Z", CUTOFF)
    assert figures["queue.review.unattended_share"].value == 1.0
    build = figures["queue.build.unattended_share"]
    assert (build.numerator, build.denominator) == (9, 10)
    engines = figures["queue.engines.paid_auth_fresh_share"]
    assert (engines.numerator, engines.denominator) == (1, 2)
    assert engines.reason == "lapsed: codexloop (last 2026-09-28)"
    assert figures["queue.done_projects"].value == 2
    assert figures["queue.last_event_hours"].value == 12.0


def test_a_queue_without_a_dsn_or_that_fails_is_unknown_and_never_written() -> None:
    source = sc.QueueSource.from_environment(SETTINGS, FakeRunner(sc.CommandResult(0, "", "")), {})
    figures = source.observe(CUTOFF)
    assert all(f.status == "unknown" for f in figures)
    assert "VIBEY_AUTONOMY_QUEUE_DSN" in figures[0].reason
    figures = sc.QueueSource(SETTINGS, FakeQueue(fail=True)).observe(CUTOFF)
    assert all("connection refused" in f.reason for f in figures)
    queue = FakeQueue()
    queue.last_event_at = lambda end: None  # type: ignore[method-assign]
    assert by_id(sc.QueueSource(SETTINGS, queue).observe(CUTOFF))["queue.last_event_hours"].status == "unknown"  # fmt: skip


def test_psql_queue_runs_read_only_and_refuses_anything_but_instants_and_words() -> None:
    runner = FakeRunner(sc.CommandResult(0, '[{"kind": "question"}]\n', ""))
    queue = sc.PsqlQueue(runner, "psql", "postgresql:///vibey", 10)
    assert queue.gates("2026-09-02T00:00:00Z", CUTOFF) == [{"kind": "question"}]
    assert runner.envs[-1] == {"PGOPTIONS": "-c default_transaction_read_only=on"}
    assert runner.calls[-1][:6] == ["psql", "-X", "-At", "-v", "ON_ERROR_STOP=1", "-d"]
    runner.result = sc.CommandResult(0, "4\n", "")
    assert queue.jobs_succeeded("build", "2026-09-02T00:00:00Z", CUTOFF) == 4
    assert queue.transitions("done", "2026-09-02T00:00:00Z", CUTOFF) == 4
    runner.result = sc.CommandResult(0, '{"at": "2026-10-01T00:00:00Z"}', "")
    assert queue.last_event_at(CUTOFF) == "2026-10-01T00:00:00Z"
    runner.result = sc.CommandResult(0, '{"claudeloop": null}', "")
    assert queue.engine_auth() == {"claudeloop": None}
    with pytest.raises(ValueError, match="not a UTC instant"):
        queue.gates("2026-09-02'; drop table job; --", CUTOFF)
    with pytest.raises(ValueError, match="not a queue identifier"):
        queue.jobs_succeeded("build'", "2026-09-02T00:00:00Z", CUTOFF)
    runner.result = sc.CommandResult(2, "", "psql: error: connection refused")
    with pytest.raises(sc.SourceUnavailable, match="connection refused"):
        queue.engine_auth()
    runner.result = sc.CommandResult(0, "{oops", "")
    with pytest.raises(sc.SourceUnavailable, match="not JSON"):
        queue.engine_auth()


def test_like_patterns_mean_what_they_mean_in_sql() -> None:
    like = sc.LikePatterns(["gate-timeout", "automation:%", "a_c"])
    assert like.match("automation:triaged-delivery") and like.match("gate-timeout") and like.match("abc")  # fmt: skip
    assert not like.match("gate-timeout-x") and not like.match("cli") and not like.match(None)


# --------------------------------------------------------------------------- figures


def test_a_figure_cannot_be_unknown_with_a_value_or_known_without_one() -> None:
    with pytest.raises(ValueError, match="carries no value"):
        sc.Figure("x", "x", "share", 1.0, "unknown", "forge", "m", CUTOFF)
    with pytest.raises(ValueError, match="needs a value"):
        sc.Figure("x", "x", "share", None, "measured", "forge", "m", CUTOFF)
    with pytest.raises(ValueError, match="is not one of"):
        sc.Figure("x", "x", "share", 1.0, "guessed", "forge", "m", CUTOFF)
    with pytest.raises(ValueError, match="belongs to the forge source"):
        sc.FigureFactory("queue", CUTOFF, None).unknown("forge.ci.success_share", "m", "r")
    figure = sc.FigureFactory("forge", CUTOFF, ("a", "b")).share(
        "forge.ci.success_share", 1, 2, "m"
    )
    assert sc.Figure.from_dict(json.loads(json.dumps(figure.to_dict()))) == figure


# --------------------------------------------------------------------------- staleness


def _measured(fid: str, value: float, at: str) -> dict[str, Any]:
    spec = sc.FigureCatalog.spec(fid)
    return sc.FigureFactory(spec.source, at, None).value(fid, value, "m").to_dict()


def test_a_figure_a_run_could_not_read_is_carried_forward_as_stale_then_unknown() -> None:
    policy = sc.StalenessPolicy(14)
    fresh = sc.FigureFactory("queue", CUTOFF, None).unknown("queue.done_projects", "m", "no DSN")
    previous = [_measured("queue.done_projects", 3, "2026-09-25T00:00:00Z")]
    (stale,) = policy.merge(previous, [fresh], CUTOFF)
    assert (stale.status, stale.value, stale.last_measured) == ("stale", 3, "2026-09-25T00:00:00Z")
    assert stale.reason == "not re-read at 2026-10-02: no DSN"
    (again,) = policy.merge([stale.to_dict()], [fresh], "2026-10-08T00:00:00Z")
    assert again.status == "stale" and again.last_measured == "2026-09-25T00:00:00Z"
    (old,) = policy.merge([stale.to_dict()], [fresh], "2026-10-10T00:00:00Z")
    assert old.status == "unknown" and "over 14 days old" in old.reason
    measured = sc.FigureFactory("queue", CUTOFF, None).value("queue.done_projects", 1, "m")
    assert policy.merge(previous, [measured], CUTOFF) == [measured]
    assert policy.merge([], [fresh], CUTOFF) == [fresh]


# --------------------------------------------------------------------------- judging


def _figure(fid: str, value: Any, numerator: int | None = None, denominator: int | None = None) -> sc.Figure:  # fmt: skip
    spec = sc.FigureCatalog.spec(fid)
    make = sc.FigureFactory(spec.source, CUTOFF, None)
    if value is None:
        return make.unknown(fid, "m", "could not read")
    if numerator is not None and denominator is not None:
        return make.share(fid, numerator, denominator, "m")
    return make.value(fid, value, "m")


CI_STAGE = next(s for s in SETTINGS.stages if s["id"] == "ci")


@pytest.mark.parametrize(
    ("success", "rerun", "stage", "criteria"),
    [
        ((95, 100), (1, 100), "autonomous", ("autonomous", "autonomous")),
        ((60, 100), (1, 100), "partial", ("partial", "autonomous")),
        ((40, 100), (1, 100), "manual", ("manual", "autonomous")),
        ((95, 100), (30, 100), "manual", ("autonomous", "manual")),
        ((95, 100), (10, 100), "partial", ("autonomous", "partial")),
        ((9, 9), (1, 100), "unknown", ("unknown", "autonomous")),
        ((40, 100), None, "manual", ("manual", "unknown")),
        (None, None, "unknown", ("unknown", "unknown")),
    ],
)
def test_a_stage_is_as_far_along_as_its_weakest_judged_criterion(success: Any, rerun: Any, stage: str, criteria: tuple[str, ...]) -> None:  # fmt: skip
    figures = [
        _figure("forge.ci.success_share", *(("v", *success) if success else (None,))),
        _figure("forge.ci.rerun_share", *(("v", *rerun) if rerun else (None,))),
    ]
    verdict = sc.StageEvaluator().evaluate([CI_STAGE], figures)[0]
    assert verdict.status == stage
    assert tuple(c.status for c in verdict.criteria) == criteria
    if success == (9, 9):
        assert "under the declared minimum of 10" in verdict.criteria[0].reason


def test_a_boolean_criterion_and_a_missing_figure() -> None:
    stage = next(s for s in SETTINGS.stages if s["id"] == "review-trust")
    yes = sc.StageEvaluator().evaluate([stage], [_figure("canary.meets_floor", True)])[0]
    no = sc.StageEvaluator().evaluate([stage], [_figure("canary.meets_floor", False)])[0]
    none = sc.StageEvaluator().evaluate([stage], [])[0]
    assert (yes.status, no.status, none.status) == ("autonomous", "manual", "unknown")
    assert none.criteria[0].reason == "no source reported it"
    headline = sc.StageEvaluator.headline([yes.to_dict(), no.to_dict(), none.to_dict()])
    assert headline == {"autonomous": 1, "partial": 0, "manual": 1, "unknown": 1, "total": 3}


# --------------------------------------------------------------------------- the record and documents


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    shutil.copy(REPO / sc.DEFAULT_CONFIG, tmp_path / sc.DEFAULT_CONFIG)
    module = tmp_path / SETTINGS.section("repo")["gate_timeout_module"]
    module.parent.mkdir(parents=True)
    shutil.copy(REPO / SETTINGS.section("repo")["gate_timeout_module"], module)
    s = SETTINGS.scorecard

    def marker(name: str) -> str:
        return sc.GeneratedBlocks.wrap(name, "")

    docs = {
        s["docs_page"]: "\n\n".join(
            marker(n) for n in ("headline", "table", "evidence", "figures")
        ),
        s["readme"]: marker("summary"),
        s["docs_index"]: marker("summary"),
        s["paper"]: "Prose.\n\n" + marker("paper") + "\n\nMore prose.\n",
    }
    for name, text in docs.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text + "\n", encoding="utf-8")
    return tmp_path


def card(root: Path, *, stamp: str = CUTOFF, queue: FakeQueue | None = None, forge: FakeForge | None = None) -> sc.Scorecard:  # fmt: skip
    return sc.Scorecard(
        root,
        clock=FixedClock(stamp),
        runner=FakeRunner(sc.CommandResult(0, json.dumps(CANARY), "")),
        forge=forge or FakeForge(),
        queue=queue,
        environ={},
    )


def test_measure_appends_one_chained_line_and_renders_every_document(root: Path) -> None:
    scorecard = card(root, queue=FakeQueue())
    payload = scorecard.record([scorecard.observe(sc.ScorecardCli.SOURCES)])
    assert payload["cutoff"] == CUTOFF and payload["stages_digest"] == SETTINGS.digest()
    assert {f["id"] for f in payload["figures"]} == set(sc.FigureCatalog.ids())
    assert payload["headline"]["total"] == len(SETTINGS.stages)
    assert scorecard.check() == []
    s = SETTINGS.scorecard
    page = (root / s["docs_page"]).read_text(encoding="utf-8")
    assert (
        "stages autonomous" in page
        and "### The pull-request review reaches a verdict { #pr-review }" in page
    )
    readme = (root / s["readme"]).read_text(encoding="utf-8")
    assert "(docs/reference/autonomy.md)" in readme and "Distance from full autonomy" in readme
    assert "(reference/autonomy.md)" in (root / s["docs_index"]).read_text(encoding="utf-8")
    paper = (root / s["paper"]).read_text(encoding="utf-8")
    assert paper.startswith("Prose.") and paper.rstrip().endswith("More prose.")
    assert r"\label{tab:autonomy-scorecard}" in paper and "At the latest measurement's cutoff, 2026-10-02 00:00Z" in paper  # fmt: skip
    assert "$\\geq$" in paper and "≥" not in paper.split("```latex", 1)[1]


def test_the_record_is_append_only(root: Path) -> None:
    first = card(root, queue=FakeQueue())
    first.record([first.observe(["forge", "queue"])])
    second = card(root, stamp="2026-10-09T00:00:00Z")
    second.record([second.observe(["forge"])])  # the queue is not reachable this week
    entries = second.entries()
    assert len(entries) == 2
    lines = (root / SETTINGS.scorecard["record"]).read_text(encoding="utf-8").splitlines()
    envelopes = [json.loads(line) for line in lines]
    assert [e["seq"] for e in envelopes] == [1, 2]
    assert envelopes[1]["previous_digest"] == envelopes[0]["digest"]
    assert envelopes[0]["format"] == sc.RECORD_FORMAT and envelopes[0]["kind"] == sc.RECORD_KIND
    done = next(f for f in entries[1]["figures"] if f["id"] == "queue.done_projects")
    assert done["status"] == "stale" and done["last_measured"] == CUTOFF
    canary = next(f for f in entries[1]["figures"] if f["id"] == "canary.meets_floor")
    assert canary["status"] == "unknown" and "did not observe the canary" in canary["reason"]
    assert entries[1]["sources"]["canary"] == "not observed by this run"
    assert second.check() == []
    edited = json.loads(lines[0])
    edited["payload"]["cutoff"] = "2026-10-01T00:00:00Z"
    lines[0] = json.dumps(edited, sort_keys=True, separators=(",", ":"))
    (root / SETTINGS.scorecard["record"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (problem,) = second.check()
    assert "not an append-only chain" in problem and "invalid digest" in problem


def test_check_names_every_kind_of_drift(root: Path) -> None:
    scorecard = card(root, queue=FakeQueue())
    assert scorecard.check() == [f"{SETTINGS.scorecard['record']} holds no measurement"]
    scorecard.record([scorecard.observe(sc.ScorecardCli.SOURCES)])
    readme = root / SETTINGS.scorecard["readme"]
    readme.write_text(readme.read_text(encoding="utf-8").replace("Distance", "Distanse"), encoding="utf-8")  # fmt: skip
    assert scorecard.check() == ["README.md: block autonomy:summary is missing or out of date (run `python scripts/autonomy_scorecard.py render`)"]  # fmt: skip
    assert scorecard.render() == ["README.md"]
    assert scorecard.render() == []
    toml = root / sc.DEFAULT_CONFIG
    toml.write_text(toml.read_text(encoding="utf-8").replace("autonomous = 0.95", "autonomous = 0.9", 1), encoding="utf-8")  # fmt: skip
    changed = card(root, queue=FakeQueue())
    assert any("reevaluate" in p for p in changed.check())
    changed.reevaluate()
    assert changed.check() == []
    assert len(changed.entries()) == 2


def test_check_refuses_verdicts_that_do_not_follow_from_the_figures(root: Path) -> None:
    scorecard = card(root, queue=FakeQueue())
    payload = dict(scorecard.record([scorecard.observe(sc.ScorecardCli.SOURCES)]))
    payload["verdicts"] = [{**v, "status": "autonomous"} for v in payload["verdicts"]]
    payload["figures"] = payload["figures"][1:]
    sc.ScorecardLedger().append(root / SETTINGS.scorecard["record"], payload)
    problems = scorecard.check()
    assert "the latest verdicts do not follow from its figures and stages" in problems
    assert "the latest headline does not follow from its verdicts" in problems
    assert any(p.startswith("the latest measurement lacks figures: ") for p in problems)


def test_the_cli_observes_records_reevaluates_renders_and_checks(root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:  # fmt: skip
    cli = sc.ScorecardCli(card(root, queue=FakeQueue()))
    out = tmp_path / "forge.json"
    assert cli.run(["observe", "--sources", "forge,repo", "--out", str(out)]) == 0
    observed = json.loads(out.read_text(encoding="utf-8"))
    assert observed["sources"] == {"forge": "observed", "repo": "observed"}
    assert cli.run(["record", str(out)]) == 0
    said = capsys.readouterr().out
    assert "stages autonomous" in said and "at 2026-10-02T00:00:00Z" in said
    assert cli.run(["measure"]) == 0
    assert cli.run(["reevaluate"]) == 0
    assert cli.run(["render"]) == 0
    assert cli.run(["check"]) == 0
    (root / SETTINGS.scorecard["readme"]).write_text("no markers\n", encoding="utf-8")
    assert cli.run(["check"]) == 1
    assert "block autonomy:summary is missing" in capsys.readouterr().err


def test_an_unavailable_source_is_named_in_the_record(root: Path) -> None:
    scorecard = card(root, queue=FakeQueue(fail=True))
    observed = scorecard.observe(["queue"])
    assert observed["sources"]["queue"].startswith("unavailable: the queue did not answer")
    with pytest.raises(ValueError, match="at least one observation"):
        scorecard.record([])
    with pytest.raises(ValueError, match="holds no measurement to re-judge"):
        scorecard.reevaluate()
    with pytest.raises(ValueError, match="no such source"):
        scorecard.sources(["tracker"])


def test_formatting_reads_like_a_table() -> None:
    share = _figure("forge.ci.success_share", "v", 3, 4).to_dict()
    assert sc.Formatter.value(share) == "3 of 4 (75%)"
    stale = {**share, "status": "stale", "last_measured": "2026-09-20T00:00:00Z"}
    assert sc.Formatter.value(stale) == "3 of 4 (75%) (stale, measured 2026-09-20)"
    assert sc.Formatter.value(_figure("queue.last_event_hours", 1234.5).to_dict()) == "1,234.5 h"
    assert sc.Formatter.value(_figure("canary.age_days", 2.0).to_dict()) == "2.0 days"
    assert sc.Formatter.value(_figure("canary.recall_lower_bound", 0.5).to_dict()) == "0.50"
    assert sc.Formatter.value(_figure("canary.meets_floor", None).to_dict()) == "unknown"
    assert (
        sc.Formatter.threshold({"compare": "<=", "autonomous": 24, "min_sample": 0}, "hours")
        == "≤ 24 h"
    )
    assert sc.Formatter.threshold({"compare": "is", "autonomous": False}, "bool") == "no"
    assert (
        sc.Formatter.threshold({"compare": ">=", "autonomous": 1.5, "min_sample": 1}, "ratio")
        == "≥ 1.5"
    )
    assert sc.PaperRenderer.tex("50% & [x] ≤ 2_y") == r"50\% \& {[}x{]} $\leq$ 2\_y"


def test_subprocess_runner_reports_a_missing_tool_and_a_timeout() -> None:
    runner = sc.SubprocessRunner()
    assert runner.run(["definitely-not-a-command-xyz"], timeout=5).returncode == 127
    slow = runner.run([sys_executable(), "-c", "import time; time.sleep(5)"], timeout=0.2)
    assert slow.returncode == 124 and "timed out" in slow.tail()
    done = runner.run([sys_executable(), "-c", "print('hi')"], timeout=10, env={"X": "1"})
    assert done.ok and done.stdout.strip() == "hi"
    assert sc.CommandResult(3, "", "").tail() == "exit 3"


def sys_executable() -> str:
    import sys

    return sys.executable
