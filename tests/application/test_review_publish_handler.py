# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`review.publish`: the last step of a delivered project, and what keeps it from surprising anyone."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.test_review_deployment_choice import (
    NOW,
    FakeProjectRepo,
    FakeReviewDeploymentLedger,
    _make_job,
)
from vibey.application.dto import HumanGateRecord, HumanGateRequest, ProjectRecord
from vibey.application.review_publish_handler import (
    PUBLISH_INTERVIEW_GATE_KIND,
    ReviewPublishHandler,
)
from vibey.application.worker import Failure, Park, Success
from vibey.domain.job import FailureClass
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase
from vibey.domain.publish import (
    PublishFailed,
    PublishKind,
    PublishPlan,
    PublishResult,
    PublishTarget,
)
from vibey.domain.spec import AcceptanceCriterion, DesignSpec

REMOTE = "git@github.com:me/x.git"


class _Gates:
    def __init__(self) -> None:
        self.records: list[HumanGateRecord] = []

    async def raise_gate(
        self, project_id: UUID, job_id: UUID | None, request: HumanGateRequest
    ) -> HumanGateRecord:
        record = HumanGateRecord(
            gate_id=uuid4(),
            project_id=project_id,
            job_id=job_id,
            kind=request.kind,
            prompt=request.prompt,
            options=request.options,
            default_answer=request.default_answer,
            answer=None,
            raised_at=NOW,
            timeout_at=None,
            answered_at=None,
            answered_by=None,
        )
        self.records.append(record)
        return record

    async def latest_for_job(self, job_id: UUID) -> HumanGateRecord | None:
        return self.records[-1] if self.records else None

    def answer(self, answer: Mapping[str, object]) -> None:
        last = self.records[-1]
        self.records[-1] = replace(last, answer=dict(answer), answered_at=NOW, answered_by="adam")


class _Specs:
    def __init__(self, spec: DesignSpec | None) -> None:
        self._spec = spec

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None:
        return self._spec


class _Publisher:
    def __init__(
        self,
        *,
        problem: str | None = None,
        remote: str | None = REMOTE,
        empty: bool = False,
        inspect_error: str | None = None,
        publish_error: str | None = None,
    ) -> None:
        self._problem = problem
        self._remote = remote
        self._empty = empty
        self._inspect_error = inspect_error
        self._publish_error = publish_error
        self.inspected: list[tuple[Path, str, str]] = []
        self.published: list[PublishPlan] = []

    async def problem(self) -> str | None:
        return self._problem

    async def inspect(self, repo_path: Path, *, branch: str, remote: str) -> PublishTarget:
        self.inspected.append((repo_path, branch, remote))
        if self._inspect_error:
            raise PublishFailed(self._inspect_error)
        return PublishTarget(
            branch=branch,
            remote=remote,
            remote_url=self._remote,
            default_branch="develop",
            repo_path=str(repo_path),
            remote_empty=self._empty,
        )

    async def publish(self, plan: PublishPlan, *, repo_path: Path) -> PublishResult:
        if self._publish_error:
            raise PublishFailed(self._publish_error)
        self.published.append(plan)
        return PublishResult(url="https://github.com/me/x/pull/7", kind=plan.kind)


def _spec() -> DesignSpec:
    return DesignSpec(
        "Ship the thing",
        (),
        (),
        (AcceptanceCriterion("C1", "g", "w", "t", "f"),),
        (),
        "one path",
    )


def _build(
    config: dict[str, object] | None = None,
    *,
    publisher: _Publisher | None = None,
    spec: DesignSpec | None = None,
):  # type: ignore[no-untyped-def]
    project_id = uuid4()
    project = ProjectRecord(
        project_id=project_id,
        name="Demo Project",
        repo_path=Path("/work/demo"),
        phase=Phase.REVIEW,
        cycle=1,
        max_cycles=3,
        config=config if config is not None else {},
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    projects = FakeProjectRepo(project)
    ledger = FakeReviewDeploymentLedger()
    gates = _Gates()
    pub = publisher or _Publisher()
    handler = ReviewPublishHandler(
        ledger=ledger,
        gates=gates,  # type: ignore[arg-type]
        projects=projects,  # type: ignore[arg-type]
        specs=_Specs(spec if spec is not None else _spec()),  # type: ignore[arg-type]
        publisher=pub,
    )
    job = _make_job(project_id=project_id, kind="review.publish")
    return handler, job, projects, ledger, gates, pub


def _kinds(ledger: FakeReviewDeploymentLedger) -> list[EventKind]:
    return [kind for kind, _ in ledger.appended]


async def test_a_job_of_another_kind_or_for_a_vanished_project_fails_plainly() -> None:
    handler, job, projects, *_ = _build({"publish": {"mode": "auto"}})

    wrong = await handler.handle(_make_job(project_id=job.project_id, kind="review.collect"))
    projects.project = None  # type: ignore[assignment]

    class _Gone(FakeProjectRepo):
        async def get(self, project_id: UUID) -> ProjectRecord | None:
            return None

    handler._projects = _Gone(
        ProjectRecord(  # type: ignore[assignment]
            project_id=job.project_id,
            name="x",
            repo_path=Path("."),
            phase=Phase.REVIEW,
            cycle=1,
            max_cycles=1,
            config={},
            created_at=NOW,
            updated_at=NOW,
        )
    )
    gone = await handler.handle(job)

    assert isinstance(wrong, Failure) and "expected review.publish job" in wrong.detail
    assert isinstance(gone, Failure) and "unknown project" in gone.detail


async def test_invalid_publish_settings_fail_naming_the_setting() -> None:
    handler, job, *_ = _build({"publish": {"mode": "sometimes"}})

    outcome = await handler.handle(job)

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.VIBEY and "publish.mode" in outcome.detail


async def test_with_publishing_off_a_stray_job_finishes_the_project_and_publishes_nothing() -> None:
    handler, job, projects, ledger, gates, publisher = _build()

    outcome = await handler.handle(job)

    assert outcome == Success({"published": False, "reason": "publishing is off"})
    assert _kinds(ledger) == [EventKind.PUBLISH_SKIPPED]
    assert projects.transitions == [(Phase.REVIEW, Phase.DONE)]
    assert publisher.inspected == [] and publisher.published == [] and gates.records == []


async def test_a_publisher_that_is_not_ready_parks_on_a_gate_that_retries_when_answered() -> None:
    handler, job, projects, ledger, _gates, publisher = _build(
        {"publish": {"mode": "auto"}}, publisher=_Publisher(problem="gh is not logged in")
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Park)
    assert outcome.request.kind == "engine_misconfigured"
    assert "gh is not logged in" in outcome.request.prompt
    assert "answer anything to retry" in outcome.request.prompt
    assert publisher.published == [] and projects.transitions == [] and _kinds(ledger) == []


async def test_a_branch_that_does_not_exist_fails_with_what_the_publisher_said() -> None:
    handler, job, *_ = _build(
        {"publish": {"mode": "auto"}}, publisher=_Publisher(inspect_error="no branch vibey/x")
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Failure) and outcome.detail == "no branch vibey/x"


async def test_auto_mode_publishes_the_proposal_without_asking_and_then_finishes() -> None:
    handler, job, projects, ledger, gates, publisher = _build({"publish": {"mode": "auto"}})

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result["published"] is True and outcome.result["kind"] == "pull_request"
    assert outcome.result["url"] == "https://github.com/me/x/pull/7"
    (plan,) = publisher.published
    assert plan.kind is PublishKind.PULL_REQUEST and plan.draft is True
    assert plan.base == "develop" and plan.title == "feat: Ship the thing"
    ((repo, branch, remote),) = publisher.inspected
    assert repo == Path("/work/demo") and branch.endswith("/integration") and remote == "origin"
    assert gates.records == []
    assert _kinds(ledger) == [EventKind.PUBLISH_COMPLETED]
    payload = ledger.appended[0][1]
    assert payload["kind"] == "pull_request" and payload["draft"] is True
    assert payload["visibility"] == "private" and payload["url"].endswith("/pull/7")
    assert projects.transitions == [(Phase.REVIEW, Phase.DONE)]


async def test_a_project_with_no_remote_gets_a_new_private_repository_by_default() -> None:
    handler, job, _projects, _ledger, _gates, publisher = _build(
        {"publish": {"mode": "auto", "owner": "org"}}, publisher=_Publisher(remote=None)
    )

    await handler.handle(job)

    (plan,) = publisher.published
    assert plan.kind is PublishKind.NEW_REPOSITORY and plan.visibility == "private"
    assert (plan.repo_name, plan.owner) == ("demo-project", "org")


async def test_an_empty_remote_from_an_earlier_attempt_is_pushed_to_not_recreated() -> None:
    handler, job, _projects, _ledger, _gates, publisher = _build(
        {"publish": {"mode": "auto"}}, publisher=_Publisher(empty=True)
    )

    await handler.handle(job)

    (plan,) = publisher.published
    assert plan.kind is PublishKind.NEW_REPOSITORY and plan.existing_remote == REMOTE


async def test_a_publish_that_fails_leaves_the_project_unfinished_and_says_why() -> None:
    handler, job, projects, ledger, *_ = _build(
        {"publish": {"mode": "auto"}}, publisher=_Publisher(publish_error="push rejected")
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Failure)
    assert outcome.detail == "publishing failed: push rejected"
    assert projects.transitions == [] and _kinds(ledger) == []


async def test_interview_mode_asks_first_showing_exactly_what_would_happen() -> None:
    handler, job, projects, ledger, gates, publisher = _build({"publish": {"mode": "interview"}})

    outcome = await handler.handle(job)

    assert isinstance(outcome, Park) and outcome.gate is not None
    request = outcome.request
    assert request.kind == PUBLISH_INTERVIEW_GATE_KIND
    assert request.options == ("accept_defaults", "custom", "skip")
    assert request.default_answer == "skip"  # silence publishes nothing
    assert "open a draft pull request into develop" in request.prompt
    assert "Title: feat: Ship the thing" in request.prompt
    assert len(gates.records) == 1
    assert publisher.published == [] and projects.transitions == [] and _kinds(ledger) == []


async def test_an_unanswered_interview_keeps_waiting_without_raising_another_gate() -> None:
    handler, job, _projects, _ledger, gates, publisher = _build({"publish": {"mode": "interview"}})
    await handler.handle(job)

    again = await handler.handle(job)

    assert isinstance(again, Park) and again.gate is None
    assert again.request.kind == PUBLISH_INTERVIEW_GATE_KIND and len(gates.records) == 1
    assert publisher.published == []


@pytest.mark.parametrize("answer", [{"choice": "accept_defaults"}, {}])
async def test_accepting_the_defaults_publishes_what_was_shown(answer: dict[str, object]) -> None:
    handler, job, projects, ledger, gates, publisher = _build({"publish": {"mode": "interview"}})
    await handler.handle(job)
    gates.answer(answer)

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success) and outcome.result["published"] is True
    (plan,) = publisher.published
    assert plan.title == "feat: Ship the thing" and plan.draft is True
    assert _kinds(ledger) == [EventKind.PUBLISH_COMPLETED]
    assert projects.transitions == [(Phase.REVIEW, Phase.DONE)]


async def test_a_custom_answer_changes_only_what_it_names() -> None:
    handler, job, _projects, _ledger, gates, publisher = _build({"publish": {"mode": "interview"}})
    await handler.handle(job)
    gates.answer({"choice": "custom", "draft": False, "title": "My title"})

    await handler.handle(job)

    (plan,) = publisher.published
    assert plan.draft is False and plan.title == "My title" and plan.base == "develop"


async def test_skipping_finishes_the_project_locally_and_publishes_nothing() -> None:
    handler, job, projects, ledger, gates, publisher = _build({"publish": {"mode": "interview"}})
    await handler.handle(job)
    gates.answer({"choice": "skip"})

    outcome = await handler.handle(job)

    assert outcome == Success({"published": False, "reason": "the operator chose not to publish"})
    assert _kinds(ledger) == [EventKind.PUBLISH_SKIPPED]
    assert projects.transitions == [(Phase.REVIEW, Phase.DONE)] and publisher.published == []


async def test_an_answer_that_cannot_be_used_asks_again_and_names_the_problem() -> None:
    handler, job, projects, _ledger, gates, publisher = _build({"publish": {"mode": "interview"}})
    await handler.handle(job)
    gates.answer({"choice": "custom", "base": "--force"})

    outcome = await handler.handle(job)

    assert isinstance(outcome, Park) and outcome.gate is None
    assert outcome.request.prompt.startswith(
        "Your answer could not be used: base must be a plain name"
    )
    assert "accept_defaults publishes exactly that" in outcome.request.prompt
    assert publisher.published == [] and projects.transitions == []


async def test_a_spec_that_is_gone_still_gives_a_usable_proposal() -> None:
    handler, job, _projects, _ledger, _gates, publisher = _build({"publish": {"mode": "auto"}})
    handler._specs = _Specs(None)  # type: ignore[assignment]

    await handler.handle(job)

    (plan,) = publisher.published
    assert plan.title == "feat: Demo Project" and "none recorded" in plan.body
