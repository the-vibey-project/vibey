# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every abandonment takes: the reason and the label are checked, and who
ran the command is named, before the store is asked for anything."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from vibey.application.dto import AbandonmentReport, ProjectRecord
from vibey.application.interfaces import (
    CallerIdentity,
    ProjectAbandonmentInterface,
    ProjectAbandonmentStore,
)
from vibey.application.project_abandonment import ProjectAbandonment
from vibey.domain.errors import InvalidAbandonment
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import Caller

AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
PROJECT = ProjectRecord(
    project_id=uuid4(),
    name="greeter",
    repo_path=Path("/srv/greeter"),
    phase=Phase.BUILD,
    cycle=1,
    max_cycles=3,
    config={},
    created_at=AT,
    updated_at=AT,
)


class _Caller:
    def current(self) -> Caller:
        return Caller(uid=501, name="adam")


class _Store:
    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID, dict[str, str]]] = []

    async def preview(self, project_id: UUID) -> AbandonmentReport:
        self.calls.append(("preview", project_id, {}))
        return AbandonmentReport(
            project=PROJECT, left=Phase.BUILD, already_abandoned=False, written=False
        )

    async def abandon(
        self, project_id: UUID, *, reason: str, by: str, account: str
    ) -> AbandonmentReport:
        self.calls.append(("abandon", project_id, {"reason": reason, "by": by, "account": account}))
        return AbandonmentReport(
            project=PROJECT,
            left=Phase.BUILD,
            already_abandoned=False,
            written=True,
            reason=reason,
            by=by,
            account=account,
        )


def _service() -> tuple[ProjectAbandonment, _Store]:
    store = _Store()
    return ProjectAbandonment(store=store, caller=_Caller()), store


def test_the_service_and_its_collaborators_satisfy_their_seams() -> None:
    service, store = _service()
    assert isinstance(service, ProjectAbandonmentInterface)
    assert isinstance(store, ProjectAbandonmentStore)
    assert isinstance(_Caller(), CallerIdentity)


async def test_abandon_hands_the_store_the_checked_reason_the_label_and_the_account() -> None:
    service, store = _service()

    report = await service.abandon(
        PROJECT.project_id, reason="  built on a foreign spec ", by=" vibey-vscode "
    )

    assert store.calls == [
        (
            "abandon",
            PROJECT.project_id,
            {"reason": "built on a foreign spec", "by": "vibey-vscode", "account": "adam"},
        )
    ]
    assert report.written and report.by == "vibey-vscode" and report.account == "adam"


async def test_with_no_label_the_abandonment_is_recorded_under_the_account() -> None:
    service, store = _service()

    await service.abandon(PROJECT.project_id, reason="superseded")

    assert store.calls[0][2]["by"] == "adam"


async def test_a_dry_run_reports_the_attribution_it_would_record_and_writes_nothing() -> None:
    service, store = _service()

    report = await service.preview(PROJECT.project_id, reason=" superseded ")

    assert store.calls == [("preview", PROJECT.project_id, {})]
    assert (report.written, report.reason, report.by, report.account) == (
        False,
        "superseded",
        "adam",
        "adam",
    )


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize(
    ("reason", "by"), [("   ", None), ("superseded", "adam\nforged"), ("x\x00", None)]
)
async def test_a_reason_or_label_that_cannot_be_recorded_reaches_no_store(
    reason: str, by: str | None, dry_run: bool
) -> None:
    service, store = _service()
    act = service.preview if dry_run else service.abandon

    with pytest.raises(InvalidAbandonment):
        await act(PROJECT.project_id, reason=reason, by=by)

    assert store.calls == []
