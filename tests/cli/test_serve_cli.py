# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey serve`, end to end against real Postgres, and its contract with the CLI.

The server is replaced by one that, instead of listening, drives the built app in-process
(httpx over ASGI) and records every response -- so each test exercises exactly what
`vibey serve` composes: the settings, the binding, the token, the services, the
presenters and the hardened app. The contract tests hold the hub's documents equal to
what the matching `vibey ... --json` prints for the same database: one contract, two
readers (doctrine 7). `docs/reference/hub-api.json` is held equal to `--openapi`.
"""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
from fastapi import FastAPI
from typer.testing import CliRunner

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import EnqueueRequest, HumanGateRequest, ProjectRecord
from vibey.bootstrap import AppResources, build_app, migrations_dir
from vibey.cli.interfaces.serve_interface import ServeCommandInterface
from vibey.cli.main import app
from vibey.cli.serve import SERVE, CliHubProbes, ServeCommand
from vibey.domain.phase import Phase
from vibey.infrastructure.hub.lanes import LaneScanner
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HubSettings

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
REPO_ROOT = Path(__file__).resolve().parents[2]
COMMITTED = REPO_ROOT / "docs" / "reference" / "hub-api.json"

type Drive = Callable[[httpx.AsyncClient, str], Awaitable[None]]


class Driven:
    """A server that serves nothing: it hands the built app to `drive`, then returns."""

    def __init__(self, drive: Drive) -> None:
        self._drive = drive
        self.state: Path | None = None
        self.bound: tuple[str, int] | None = None
        self.app: FastAPI | None = None

    async def serve(self, app: FastAPI, *, host: str, port: int) -> None:
        self.bound, self.app = (host, port), app
        shown = f"[{host}]" if ":" in host else host
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url=f"http://{shown}:{port}"
        ) as client:
            assert self.state is not None
            token = (self.state / "token").read_text().strip()
            await self._drive(client, token)


class Names:
    def names(self, bound: str) -> frozenset[str]:
        return frozenset({"studio.local", bound})


def _command(tmp_path: Path, server: Driven, toml: str = "") -> ServeCommand:
    state = tmp_path / "state"
    (tmp_path / "vibey.toml").write_text(f"[hub]\nstate_dir = '{state}'\n{toml}")
    server.state = state
    return ServeCommand(server=server, names=Names(), config_path=lambda: tmp_path / "vibey.toml")


# -- no database --------------------------------------------------------------------------


def test_the_command_meets_its_declared_seam() -> None:
    assert isinstance(SERVE, ServeCommandInterface)


def test_the_cli_imports_without_the_hub_extra() -> None:
    """FastAPI and uvicorn ship only in the `hub` extra; the container image installs no
    extras, so every other command must run without them (its `--version` contract did not)."""
    import subprocess
    import sys

    probe = (
        "import sys\n"
        "sys.modules['fastapi'] = None\n"
        "sys.modules['uvicorn'] = None\n"
        "import vibey.cli.main\n"
        "assert 'vibey.infrastructure.hub.app' not in sys.modules\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed argv, this interpreter
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_the_committed_openapi_document_is_what_serve_prints() -> None:
    printed = runner.invoke(app, ["serve", "--openapi"])
    assert printed.exit_code == 0, printed.output
    assert printed.stdout == COMMITTED.read_text(), (
        "docs/reference/hub-api.json is stale: regenerate it with "
        "`vibey serve --openapi > docs/reference/hub-api.json`"
    )
    document = json.loads(printed.stdout)
    assert document["openapi"] == "3.1.0" and document["info"]["version"] == "1"


def test_an_undeclared_lan_address_is_refused_before_anything_opens(tmp_path: Path) -> None:
    def refuse() -> Any:
        raise AssertionError("nothing may open")

    command = ServeCommand(
        open_app=refuse,
        server=Driven(lambda *_: asyncio.sleep(0)),
        config_path=lambda: tmp_path / "vibey.toml",
    )
    with pytest.raises(Exception) as caught:
        asyncio.run(command.run(host="0.0.0.0", port=None))  # nosec B104 - refused
    assert getattr(caught.value, "exit_code", None) == 2


def test_serve_prints_the_openapi_document_through_typer(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[tuple[str | None, int | None]] = []

    async def run(*, host: str | None, port: int | None) -> None:
        ran.append((host, port))

    monkeypatch.setattr(SERVE, "run", run)
    result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9001"])
    assert result.exit_code == 0, result.output
    assert ran == [("127.0.0.1", 9001)]


def test_doctors_hub_exposure_line(tmp_path: Path) -> None:
    state = tmp_path / "state"
    toml = tmp_path / "vibey.toml"
    command = ServeCommand(config_path=lambda: toml)
    toml.write_text(f"[hub]\nstate_dir = '{state}'\n")
    LocalTokenStore(state).record_serving(
        ServingRecord(host="0.0.0.0", port=8765, pid=os.getpid())  # nosec B104 - a record
    )
    assert command.exposure_line() is False
    toml.write_text(f"[hub]\nstate_dir = '{state}'\nlan = true\n")
    assert command.exposure_line() is True
    toml.write_text("[hub]\nlan = 'yes'\n")
    assert command.exposure_line() is False


# -- against the database -----------------------------------------------------------------


@pytest.fixture
async def _an_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    conn = await asyncpg.connect(owner)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()
    await TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir())
    monkeypatch.setenv("VIBEY_PG_URL", os.environ["VIBEY_TEST_APP_DATABASE_URL"])


async def _seed(repo: Path) -> tuple[ProjectRecord, UUID, UUID, UUID]:
    """A project with an approval gate, a spending gate and one queued job."""
    async with build_app() as resources:
        project = await resources.projects.create("greeter", repo, max_cycles=3, config={})
        approval = await resources.gates.raise_gate(
            project.project_id, None, HumanGateRequest(kind="approval", prompt="ship it?")
        )
        spend = await resources.gates.raise_gate(
            project.project_id, None, HumanGateRequest(kind="budget_exhausted", prompt="more?")
        )
        job = await resources.jobs.enqueue(
            EnqueueRequest(
                project_id=project.project_id,
                cycle=1,
                phase=Phase.BUILD,
                kind="build.implement",
                idempotency_key=f"k-{uuid4()}",
                work_item_id="w1",
            )
        )
    return project, approval.gate_id, spend.gate_id, job.id


def _cli_json(*args: str) -> Any:
    result = runner.invoke(app, list(args))
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
def test_the_hub_speaks_the_clis_contract_end_to_end(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "vibey.toml").write_text('[queue.priority]\nsources = ["vibey-hub"]\n')
    project, approval, spend, job = asyncio.run(_seed(repo))
    pid = project.project_id
    got: dict[str, httpx.Response] = {}

    async def drive(client: httpx.AsyncClient, token: str) -> None:
        auth = {"authorization": f"Bearer {token}"}
        for name, path in {
            "projects": "/api/v1/projects",
            "gates": "/api/v1/gates",
            "project_gates": f"/api/v1/gates?project_id={pid}",
            "status": f"/api/v1/projects/{pid}/status",
            "budget": f"/api/v1/projects/{pid}/budget",
            "queue": f"/api/v1/projects/{pid}/queue",
            "loops": "/api/v1/loops",
            "lanes": "/api/v1/lanes",
            "doctor": "/api/v1/doctor",
            "ready": "/health/ready",
            "unknown": f"/api/v1/projects/{uuid4()}/status",
            "anonymous": "/api/v1/projects",
        }.items():
            got[name] = await client.get(path, headers={} if name == "anonymous" else auth)
        got["answer"] = await client.post(
            f"/api/v1/gates/{approval}/answer",
            headers=auth,
            json={"answer": {"verdict": "accept"}, "request_id": "phone-1"},
        )
        got["replay"] = await client.post(
            f"/api/v1/gates/{approval}/answer",
            headers=auth,
            json={"answer": {"verdict": "accept"}, "request_id": "phone-1"},
        )
        got["again"] = await client.post(
            f"/api/v1/gates/{approval}/answer",
            headers=auth,
            json={"answer": {"verdict": "changes"}, "request_id": "phone-2"},
        )
        got["spend"] = await client.post(
            f"/api/v1/gates/{spend}/answer", headers=auth, json={"answer": {"choice": "resume"}}
        )
        got["bump"] = await client.post(f"/api/v1/projects/{pid}/queue/{job}/bump", headers=auth)
        got["ledger"] = await client.get(
            f"/api/v1/projects/{pid}/ledger?kind=GateAnswered&limit=10", headers=auth
        )
        got["rebinding"] = await client.get(
            "/api/v1/projects", headers={**auth, "host": "attacker.example:8765"}
        )

    server = Driven(drive)
    asyncio.run(_command(tmp_path, server).run(host=None, port=None))

    assert server.bound == ("127.0.0.1", 8765)
    assert got["anonymous"].status_code == 401
    assert got["rebinding"].status_code == 421
    assert got["unknown"].status_code == 404
    assert got["ready"].json() == {"status": "ready"}
    # Every read is the CLI's own document for the same data. The gates were read
    # before any answer, so compare against the answer-free listing via its keys.
    assert got["projects"].json()[0]["open_gates"] == 2
    assert {g["gate_id"] for g in got["gates"].json()["gates"]} == {str(approval), str(spend)}
    assert got["project_gates"].json() == got["gates"].json()
    assert got["loops"].json() == _cli_json("loops", "--json")
    assert got["status"].json() == _cli_json("status", str(pid), "--json")
    assert got["budget"].json() == _cli_json("budget", "show", str(pid), "--json")
    assert got["lanes"].json() == {"lanes": []}
    assert [c["name"] for c in got["doctor"].json()["checks"]] == ["database", "hub-exposure"]
    assert got["doctor"].json()["checks"][0]["mark"] == "PASS"
    # The answer goes through the one answering service: recorded under the host, once.
    answered = got["answer"].json()
    assert answered["answered_by"] == "host" and answered["replayed"] is False
    assert got["replay"].json()["replayed"] is True
    assert got["again"].status_code == 409
    assert got["spend"].status_code == 200
    # A bump is requested as the declared source the repository admits.
    assert got["bump"].status_code == 200, got["bump"].text
    assert got["bump"].json()["changed"] is True
    assert got["ledger"].json() == _cli_json(
        "ledger", "search", str(pid), "--kind", "GateAnswered", "--limit", "10", "--json"
    )
    assert got["queue"].json()["project_id"] == str(pid)
    assert not (tmp_path / "state" / "serving.json").exists()


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
def test_a_repository_that_does_not_admit_the_hub_refuses_its_bump(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    project, _, _, job = asyncio.run(_seed(repo))
    got: dict[str, httpx.Response] = {}

    async def drive(client: httpx.AsyncClient, token: str) -> None:
        got["bump"] = await client.post(
            f"/api/v1/projects/{project.project_id}/queue/{job}/bump",
            headers={"authorization": f"Bearer {token}"},
        )

    asyncio.run(_command(tmp_path, Driven(drive)).run(host=None, port=None))
    assert got["bump"].status_code == 403


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
def test_a_declared_lan_answers_this_computers_names(tmp_path: Path) -> None:
    got: dict[str, httpx.Response] = {}

    async def drive(client: httpx.AsyncClient, token: str) -> None:
        auth = {"authorization": f"Bearer {token}"}
        got["name"] = await client.get(
            "/api/v1/projects", headers={**auth, "host": "studio.local:9100"}
        )
        got["declared"] = await client.get(
            "/api/v1/projects", headers={**auth, "host": "hub.example:9100"}
        )

    server = Driven(drive)
    command = _command(tmp_path, server, "lan = true\nport = 9100\nnames = ['hub.example']\n")
    asyncio.run(command.run(host="192.168.1.20", port=None))
    assert server.bound == ("192.168.1.20", 9100)
    assert got["name"].status_code == 200 and got["declared"].status_code == 200


async def test_a_database_that_does_not_answer_is_not_ready(tmp_path: Path) -> None:
    class Broken:
        async def get_latest(self) -> None:
            raise OSError("down")

    resources = AppResources.__new__(AppResources)
    object.__setattr__(resources, "projects", Broken())
    probes = CliHubProbes(
        resources=resources,
        settings=HubSettings(state_dir=tmp_path),
        store=LocalTokenStore(tmp_path),
        lanes=LaneScanner(engines=[], roots=[], now=lambda: 0.0),
    )
    assert await probes.ready() is False
    doctor = await probes.doctor()
    assert isinstance(doctor, dict)
    assert doctor["checks"][0]["mark"] == "FAIL"


async def test_the_openapi_only_app_is_never_ready() -> None:
    assert await ServeCommand._never_ready() is False


def test_a_config_or_token_that_cannot_be_used_exits_cleanly(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o755)
    (tmp_path / "vibey.toml").write_text(f"[hub]\nstate_dir = '{state}'\n")
    command = ServeCommand(
        server=Driven(lambda *_: asyncio.sleep(0)), config_path=lambda: tmp_path / "vibey.toml"
    )
    with pytest.raises(Exception) as caught:
        asyncio.run(command.run(host=None, port=None))
    assert getattr(caught.value, "exit_code", None) == 1
    (tmp_path / "vibey.toml").write_text("[hub]\nlan = 'yes'\n")
    with pytest.raises(Exception) as bad:
        asyncio.run(command.run(host=None, port=None))
    assert getattr(bad.value, "exit_code", None) == 2
