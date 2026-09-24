# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contract tests for the Pydantic-backed SQLModel database projection."""

from uuid import UUID, uuid4

import asyncpg
import pytest
from sqlmodel import SQLModel, select

from vibey.infrastructure.db.interfaces import PostgresOrmInterface
from vibey.infrastructure.db.orm import PostgresOrm, _asyncpg_url
from vibey.infrastructure.db.orm_models import (
    ORM_TABLE_MODELS,
    ORM_TABLE_NAMES,
    ProjectOrm,
)

EXPECTED_TABLE_NAMES = frozenset(
    {
        "project",
        "event",
        "event_seq",
        "job",
        "job_dependency",
        "work_item",
        "open_item",
        "handoff",
        "engine_health",
        "rotation_cursor",
        "human_gate",
        "artifact",
        "budget_ledger",
        "schema_migration",
    }
)


@pytest.mark.parametrize(
    ("dsn", "expected"),
    [
        ("postgres://user@localhost/db", "postgresql+asyncpg://user@localhost/db"),
        ("postgresql://user@localhost/db", "postgresql+asyncpg://user@localhost/db"),
        ("postgresql+asyncpg://user@localhost/db", "postgresql+asyncpg://user@localhost/db"),
    ],
)
def test_postgres_dsn_is_normalized_for_asyncpg(dsn: str, expected: str) -> None:
    assert _asyncpg_url(dsn) == expected


def test_every_migrated_relation_has_a_pydantic_orm_model() -> None:
    assert ORM_TABLE_NAMES == EXPECTED_TABLE_NAMES
    assert {model.__tablename__ for model in ORM_TABLE_MODELS} == EXPECTED_TABLE_NAMES
    assert set(SQLModel.metadata.tables) >= EXPECTED_TABLE_NAMES

    project = ProjectOrm(name="demo", repo_path="/tmp/demo", config={})
    assert isinstance(project, SQLModel)
    assert project.model_dump()["name"] == "demo"
    assert isinstance(project.id, UUID)


async def test_orm_session_round_trips_a_project(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    # The ORM projection is a tool for the schema's owner, not an application path:
    # it maps every relation, including those the application role has no grant on.
    del owner_pool
    orm = PostgresOrm(database_url)
    assert isinstance(orm, PostgresOrmInterface)
    assert orm.engine.url.drivername == "postgresql+asyncpg"
    project = ProjectOrm(
        id=uuid4(),
        name="orm-demo",
        repo_path="/tmp/orm-demo",
        config={"source": "sqlmodel"},
    )
    try:
        async with orm.session() as session:
            session.add(project)
            await session.commit()
            result = await session.execute(select(ProjectOrm).where(ProjectOrm.id == project.id))
            loaded = result.scalar_one()
        assert loaded.id == project.id
        assert loaded.config == {"source": "sqlmodel"}
    finally:
        await orm.dispose()


async def test_orm_columns_match_every_migrated_relation(
    owner_pool: asyncpg.Pool,
) -> None:
    rows = await owner_pool.fetch(
        """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ANY($1::text[])
        ORDER BY table_name, ordinal_position
        """,
        list(EXPECTED_TABLE_NAMES),
    )
    actual = {
        table_name: {row["column_name"] for row in rows if row["table_name"] == table_name}
        for table_name in EXPECTED_TABLE_NAMES
    }
    mapped = {
        table_name: set(SQLModel.metadata.tables[table_name].columns.keys())
        for table_name in EXPECTED_TABLE_NAMES
    }
    assert actual == mapped
