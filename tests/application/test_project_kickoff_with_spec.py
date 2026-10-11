# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Skipping DESIGN: a reviewed spec is accepted at once, with no interview job."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from vibey.application.dto import ProjectRecord
from vibey.application.project_kickoff import SUPPLIED_SPEC_ACTOR, accept_supplied_design
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.phase import Phase, VisualDecision
from vibey.domain.spec import AcceptanceCriterion, DesignSpec

NOW = datetime(2026, 10, 11, tzinfo=UTC)


def _project(phase: Phase) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name="widget",
        repo_path=Path("/tmp/widget"),
        phase=phase,
        cycle=2,
        max_cycles=10,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )


def _spec() -> DesignSpec:
    return DesignSpec(
        objective="a section",
        constraints=(),
        non_goals=(),
        criteria=(AcceptanceCriterion("C1", "a post", "it is built", "it renders", "a test"),),
        nfrs=(),
        walking_skeleton="one post end to end",
    )


class Projects:
    def __init__(self, project: ProjectRecord | None) -> None:
        self.project = project
        self.transitions: list[tuple[Phase, Phase]] = []

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self.project

    async def transition(self, project_id: UUID, expected: Phase, to: Phase) -> ProjectRecord:
        assert self.project is not None
        self.transitions.append((expected, to))
        self.project = replace(self.project, phase=to)
        return self.project


class Specs:
    def __init__(self) -> None:
        self.saved: list[tuple[UUID, int, DesignSpec]] = []

    async def save(self, project_id: UUID, cycle: int, spec: DesignSpec) -> None:
        self.saved.append((project_id, cycle, spec))


class Acceptor:
    def __init__(self, projects: Projects, *, refuses: str | None = None) -> None:
        self._projects = projects
        self._refuses = refuses
        self.calls: list[tuple[VisualDecision, str | None]] = []

    async def accept(
        self,
        project_id: UUID,
        *,
        visual_choice: VisualDecision = VisualDecision.DECLINED,
        accepted_by: str | None = None,
    ) -> ProjectRecord:
        self.calls.append((visual_choice, accepted_by))
        if self._refuses is not None:
            raise ValueError(self._refuses)
        assert self._projects.project is not None
        self._projects.project = replace(self._projects.project, phase=Phase.BUILD)
        return self._projects.project


async def test_a_fresh_project_enters_design_takes_the_spec_and_is_accepted_into_build() -> None:
    projects = Projects(_project(Phase.INTAKE))
    specs, acceptor = Specs(), Acceptor(projects)
    spec = _spec()

    accepted = await accept_supplied_design(
        projects=projects,  # type: ignore[arg-type]
        specs=specs,  # type: ignore[arg-type]
        acceptor=acceptor,  # type: ignore[arg-type]
        project_id=projects.project.project_id,  # type: ignore[union-attr]
        spec=spec,
    )

    assert projects.transitions == [(Phase.INTAKE, Phase.DESIGN)]  # no interview job anywhere
    assert [(cycle, saved) for _, cycle, saved in specs.saved] == [(2, spec)]
    # Visual design is declined, as every unattended acceptance declines it, and the ledger
    # says who accepted.
    assert acceptor.calls == [(VisualDecision.DECLINED, SUPPLIED_SPEC_ACTOR)]
    assert accepted.phase is Phase.BUILD


async def test_a_project_already_in_design_is_not_moved_again() -> None:
    projects = Projects(_project(Phase.DESIGN))
    acceptor = Acceptor(projects)

    await accept_supplied_design(
        projects=projects,  # type: ignore[arg-type]
        specs=Specs(),  # type: ignore[arg-type]
        acceptor=acceptor,  # type: ignore[arg-type]
        project_id=projects.project.project_id,  # type: ignore[union-attr]
        spec=_spec(),
        accepted_by="someone",
    )

    assert projects.transitions == []
    assert acceptor.calls == [(VisualDecision.DECLINED, "someone")]


async def test_an_unknown_project_is_refused_before_anything_is_saved() -> None:
    specs = Specs()
    with pytest.raises(UnknownProject):
        await accept_supplied_design(
            projects=Projects(None),  # type: ignore[arg-type]
            specs=specs,  # type: ignore[arg-type]
            acceptor=Acceptor(Projects(None)),  # type: ignore[arg-type]
            project_id=uuid4(),
            spec=_spec(),
        )
    assert specs.saved == []


@pytest.mark.parametrize("phase", [Phase.BUILD, Phase.REVIEW, Phase.ABANDONED])
async def test_a_project_past_design_cannot_have_its_design_skipped(phase: Phase) -> None:
    projects, specs = Projects(_project(phase)), Specs()
    with pytest.raises(WrongPhase, match="not design"):
        await accept_supplied_design(
            projects=projects,  # type: ignore[arg-type]
            specs=specs,  # type: ignore[arg-type]
            acceptor=Acceptor(projects),  # type: ignore[arg-type]
            project_id=projects.project.project_id,  # type: ignore[union-attr]
            spec=_spec(),
        )
    assert specs.saved == []  # a spec is never written over a project already building


async def test_a_spec_the_acceptance_refuses_stays_saved_so_it_can_be_fixed_and_accepted() -> None:
    projects = Projects(_project(Phase.INTAKE))
    specs = Specs()

    with pytest.raises(ValueError, match="no acceptance criteria"):
        await accept_supplied_design(
            projects=projects,  # type: ignore[arg-type]
            specs=specs,  # type: ignore[arg-type]
            acceptor=Acceptor(projects, refuses="no acceptance criteria"),  # type: ignore[arg-type]
            project_id=projects.project.project_id,  # type: ignore[union-attr]
            spec=_spec(),
        )

    assert len(specs.saved) == 1 and projects.project.phase is Phase.DESIGN  # type: ignore[union-attr]
