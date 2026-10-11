# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`--auto-accept-design` (application/design_auto_accept.py): an operator's flag lets a worker
accept one project's finished DESIGN spec, once, declining the visual stage and naming itself."""

from dataclasses import replace
from uuid import UUID

from tests.application.test_design_acceptance import Projects, Specs, project, spec
from tests.application.test_gate_notices import _Logger
from vibey.application.design_auto_accept import DESIGN_AUTO_ACCEPT_ACTOR, DesignAutoAccept
from vibey.application.dto import ProjectRecord
from vibey.application.interfaces import DesignAutoAcceptInterface
from vibey.domain.phase import Phase, VisualDecision
from vibey.domain.spec import DesignSpec


class _Jobs:
    def __init__(self, unsettled: int = 0) -> None:
        self.unsettled = unsettled
        self.asked: list[tuple[UUID, int, Phase]] = []

    async def count_unsettled(
        self, project_id: UUID, *, cycle: int, phase: Phase, exclude: UUID | None = None
    ) -> int:
        self.asked.append((project_id, cycle, phase))
        return self.unsettled


class _Acceptor:
    def __init__(self, projects: Projects, *, refuse: str | None = None) -> None:
        self._projects = projects
        self.refuse = refuse
        self.calls: list[tuple[UUID, VisualDecision, str | None]] = []

    async def accept(
        self,
        project_id: UUID,
        *,
        visual_choice: VisualDecision = VisualDecision.DECLINED,
        accepted_by: str | None = None,
    ) -> ProjectRecord:
        self.calls.append((project_id, visual_choice, accepted_by))
        if self.refuse is not None:
            raise ValueError(self.refuse)
        assert self._projects.project is not None
        self._projects.project = replace(self._projects.project, phase=Phase.BUILD)
        return self._projects.project


def _auto(
    *,
    phase: Phase = Phase.DESIGN,
    unsettled: int = 0,
    stored: DesignSpec | None = None,
    imported: DesignSpec | None = None,
    refuse: str | None = None,
    logger: _Logger | None = None,
):  # type: ignore[no-untyped-def]
    record = replace(project(), phase=phase)
    projects = Projects(record)
    specs = Specs(stored)
    jobs = _Jobs(unsettled)
    acceptor = _Acceptor(projects, refuse=refuse)
    sweep = DesignAutoAccept(
        projects=projects,  # type: ignore[arg-type]
        jobs=jobs,  # type: ignore[arg-type]
        specs=specs,  # type: ignore[arg-type]
        acceptor=acceptor,
        logger=logger or _Logger(),
        spec=imported,
    )
    return sweep, record.project_id, projects, specs, jobs, acceptor


def test_the_sweep_satisfies_its_declared_seam() -> None:
    assert isinstance(_auto()[0], DesignAutoAcceptInterface)


async def test_a_settled_design_is_accepted_once_declining_the_visual_stage_and_named() -> None:
    logger = _Logger()
    sweep, pid, _projects, _specs, jobs, acceptor = _auto(stored=spec(), logger=logger)

    first = await sweep.run(pid)
    again = await sweep.run(pid)

    assert first.accepted and first.message == "accepted the design; entered build"
    assert acceptor.calls == [(pid, VisualDecision.DECLINED, DESIGN_AUTO_ACCEPT_ACTOR)]
    assert jobs.asked == [(pid, 1, Phase.DESIGN)]
    assert not again.accepted and again.message is None
    assert ("info", "design.auto_accepted") in logger.events()


async def test_it_waits_for_design_jobs_and_says_so_once_per_change() -> None:
    sweep, pid, _projects, _specs, jobs, acceptor = _auto(unsettled=2, stored=spec())

    one = await sweep.run(pid)
    two = await sweep.run(pid)
    jobs.unsettled = 1
    three = await sweep.run(pid)

    assert one.message == "waiting for 2 DESIGN job(s) to finish"
    assert two.message is None
    assert three.message == "waiting for 1 DESIGN job(s) to finish"
    assert acceptor.calls == []


async def test_it_waits_for_a_spec_when_none_exists_and_none_was_given() -> None:
    sweep, pid, *_rest, acceptor = _auto(stored=None)

    report = await sweep.run(pid)

    assert report.message == "waiting for the synthesized spec"
    assert acceptor.calls == []


async def test_a_reviewed_spec_is_imported_once_before_accepting_even_with_no_stored_spec() -> None:
    reviewed = spec()
    sweep, pid, _projects, specs, _jobs, acceptor = _auto(
        stored=None, imported=reviewed, refuse="1 blocking question is open"
    )

    refused = await sweep.run(pid)
    specs.value = None  # a later refusal must not re-import over a spec someone changed
    still = await sweep.run(pid)

    assert refused.message == "not accepted yet: 1 blocking question is open"
    assert still.message is None
    assert specs.value is None
    assert len(acceptor.calls) == 2


async def test_the_import_replaces_the_synthesized_spec() -> None:
    sweep, pid, _projects, specs, _jobs, _acceptor = _auto(stored=spec(), imported=spec())

    assert (await sweep.run(pid)).accepted
    assert specs.value is not None and specs.value.objective == "Ship"


async def test_a_guard_refusal_is_retried_and_accepts_when_the_guard_allows() -> None:
    sweep, pid, _projects, _specs, _jobs, acceptor = _auto(stored=spec(), refuse="not yet")

    first = await sweep.run(pid)
    acceptor.refuse = None
    second = await sweep.run(pid)

    assert not first.accepted and first.message == "not accepted yet: not yet"
    assert second.accepted


async def test_a_project_that_left_design_or_vanished_is_finished_and_said_once() -> None:
    sweep, pid, *_rest = _auto(phase=Phase.BUILD, stored=spec())
    gone, gone_id, projects, *_ = _auto()
    projects.project = None

    left = await sweep.run(pid)
    left_again = await sweep.run(pid)
    missing = await gone.run(gone_id)

    assert left.message == "the project is in build, not DESIGN; nothing to accept"
    assert left_again.message is None
    assert missing.message == "the project no longer exists; nothing to accept"


async def test_without_a_project_there_is_nothing_to_do() -> None:
    sweep, *_rest = _auto(stored=spec())

    report = await sweep.run(None)

    assert report.project_id is None and not report.accepted and report.message is None


async def test_two_loops_sweeping_at_once_accept_the_design_only_once() -> None:
    import asyncio

    sweep, pid, _projects, _specs, jobs, acceptor = _auto(stored=spec())
    counting = jobs.count_unsettled

    async def yielding(*args: object, **kwargs: object) -> int:
        await asyncio.sleep(0)  # the first sweep holds the lock while the second waits for it
        return await counting(*args, **kwargs)  # type: ignore[arg-type]

    jobs.count_unsettled = yielding  # type: ignore[method-assign]

    reports = await asyncio.gather(sweep.run(pid), sweep.run(pid))

    assert [r.accepted for r in reports].count(True) == 1
    assert len(acceptor.calls) == 1
