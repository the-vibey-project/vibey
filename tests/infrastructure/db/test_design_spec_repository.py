# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from dataclasses import replace
from pathlib import Path

import asyncpg

from vibey.domain.research_gap import ResearchGap
from vibey.domain.spec import AcceptanceCriterion, Constraint, ConstraintKind, DesignSpec
from vibey.infrastructure.db.design_spec_repository import FileDesignSpecRepository
from vibey.infrastructure.db.project_repository import PostgresProjectRepository


def buildable_spec() -> DesignSpec:
    return DesignSpec(
        "Ship",
        (Constraint("Offline", ConstraintKind.HARD),),
        ("Cloud",),
        (AcceptanceCriterion("AC-1", "input", "run", "output", "test passes"),),
        (),
        "one path",
    )


async def test_save_load_and_publish_spec_artifacts(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    projects = PostgresProjectRepository(migrated_pool)
    project = await projects.create("demo", tmp_path, max_cycles=10, config={})
    specs = FileDesignSpecRepository(projects)

    await specs.save(project.project_id, 1, buildable_spec())
    assert await specs.load(project.project_id, 1) == buildable_spec()
    await specs.publish(project.project_id, 1, buildable_spec())

    assert (tmp_path / ".vibey/context/spec.md").exists()
    assert (tmp_path / ".vibey/context/acceptance.md").exists()


async def test_research_gaps_survive_a_save_and_load_and_reach_the_published_spec(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    projects = PostgresProjectRepository(migrated_pool)
    project = await projects.create("demo", tmp_path, max_cycles=10, config={})
    specs = FileDesignSpecRepository(projects)
    gapped = replace(
        buildable_spec(), research_gaps=(ResearchGap("prior-art", "no evidence file."),)
    )

    await specs.save(project.project_id, 1, gapped)
    assert await specs.load(project.project_id, 1) == gapped
    await specs.publish(project.project_id, 1, gapped)

    spec_md = (tmp_path / ".vibey/context/spec.md").read_text()
    assert "## Research not performed" in spec_md
    assert "- prior-art: not researched. no evidence file." in spec_md


async def test_a_spec_saved_before_gaps_were_recorded_loads_with_none(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    projects = PostgresProjectRepository(migrated_pool)
    project = await projects.create("demo", tmp_path, max_cycles=10, config={})
    specs = FileDesignSpecRepository(projects)
    await specs.save(project.project_id, 1, buildable_spec())
    path = tmp_path / ".vibey/runs/1/design/spec.json"
    stored = json.loads(path.read_text())
    del stored["research_gaps"]
    path.write_text(json.dumps(stored))

    assert await specs.load(project.project_id, 1) == buildable_spec()


async def test_load_missing_spec_returns_none_and_unknown_project_fails(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    from uuid import UUID

    projects = PostgresProjectRepository(migrated_pool)
    project = await projects.create("demo", tmp_path, max_cycles=10, config={})
    specs = FileDesignSpecRepository(projects)
    assert await specs.load(project.project_id, 1) is None

    try:
        await specs.save(UUID(int=0), 1, buildable_spec())
    except LookupError as exc:
        assert "project" in str(exc)
    else:
        raise AssertionError("expected unknown project failure")
