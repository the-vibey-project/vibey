# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey inputs`, end to end against real PostgreSQL, as the application role (SP-LOOPS Phase 3).

The composition root's own service (`bootstrap.run_inputs_app`) runs: the project is read from
the database, the input is a file in the person's state folder (here pytest's), keyed by project id, and the ledger holds one
`ArtifactProduced` event whose payload is exactly the digest, kind, size and name digest. Nothing of the
input enters Postgres but that digest. The person's own `vibey.toml` is a file in pytest's
temporary folder, never the real one.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
from typer.testing import CliRunner

import vibey.bootstrap
import vibey.cli.inputs as inputs_module
from tests.db_roles import TestDatabaseRoles
from vibey.bootstrap import build_app, migrations_dir
from vibey.cli.inputs import InputsCommands
from vibey.cli.main import app
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase
from vibey.domain.run_input import digest_of

pytestmark = pytest.mark.integration
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
ROLES = TestDatabaseRoles.from_environ(os.environ)


def _owner() -> str:
    return os.environ["VIBEY_TEST_DATABASE_URL"]


@pytest.fixture(autouse=True)
def _an_empty_schema_the_application_role_runs_on(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fresh() -> None:
        conn = await asyncpg.connect(_owner())
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.execute("CREATE SCHEMA public")
        finally:
            await conn.close()
        await ROLES.restore(_owner(), migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(_owner()))


@pytest.fixture
def commands(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    config = tmp_path / "config"
    config.mkdir()
    # The person's state folder stands in under pytest's folder: never the real one.
    monkeypatch.setattr(vibey.bootstrap, "run_inputs_root", lambda: tmp_path / "state" / "inputs")
    monkeypatch.setattr(
        inputs_module,
        "INPUTS",
        InputsCommands(
            user_config=lambda: config / "vibey.toml",
            project_config=lambda: tmp_path / "cwd" / "vibey.toml",
        ),
    )
    yield


def _project(repo: Path) -> UUID:
    async def create() -> UUID:
        async with build_app() as resources:
            project = await resources.projects.create("greeter", repo, max_cycles=3, config={})
            return project.project_id

    return asyncio.run(create())


def test_an_added_file_is_stored_on_disk_and_only_its_digest_reaches_the_ledger(
    tmp_path: Path, commands: None
) -> None:
    repo = tmp_path / "greeter"
    repo.mkdir()
    pid = _project(repo)
    spec = tmp_path / "spec.md"
    spec.write_bytes(b"# A secret spec\n")
    result = runner.invoke(app, ["inputs", "add", str(pid), "--file", str(spec)])
    assert result.exit_code == 0, result.output
    digest = digest_of(b"# A secret spec\n")
    store = tmp_path / "state" / "inputs" / str(pid)
    assert (store / "objects" / digest[:2] / digest).is_file()
    assert not (repo / ".vibey").exists()  # never inside the checkout

    listed = runner.invoke(app, ["inputs", "list", str(pid), "--json"])
    assert listed.exit_code == 0, listed.output
    assert [row["digest"] for row in json.loads(listed.output)["inputs"]] == [digest]

    async def events() -> list[tuple[EventKind, Phase, dict[str, object], UUID | None]]:
        async with build_app() as resources:
            found = await resources.ledger.all_for_project(pid)
        return [(e.kind, e.phase, dict(e.payload), e.job_id) for e in found]  # type: ignore[misc]

    recorded = [e for e in asyncio.run(events()) if e[0] == EventKind.ARTIFACT_PRODUCED]
    assert recorded == [
        (
            EventKind.ARTIFACT_PRODUCED,
            Phase.BUILD,
            {
                "artifact_type": "vibey_run_input",
                "digest": digest,
                "kind": "file",
                "size": 16,
                # The name's SHA-256 (fix round 1, review I2), never the name itself.
                "name_digest": hashlib.sha256(b"spec.md").hexdigest(),
            },
            None,
        )
    ]


def test_an_unknown_project_is_exit_1(tmp_path: Path, commands: None) -> None:
    result = runner.invoke(
        app, ["inputs", "add", "00000000-0000-0000-0000-000000000000", "--paste", "hi"]
    )
    assert result.exit_code == 1
    assert "unknown project" in result.output
