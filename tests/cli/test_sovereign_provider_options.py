# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`--provider qwenloop` end to end through the CLI, with no paid credential in reach.

The local model is a real HTTP server on 127.0.0.1 that answers like Ollama's chat API,
so these exercise the shared client's actual transport, the environment it is configured
from, and the jobs the worker leaves behind -- not a patched function.
"""

import asyncio
import json
import os
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.build_kickoff import enqueue_build_decompose
from vibey.application.dto import EnqueueRequest, PreflightResult
from vibey.application.project_kickoff import enqueue_design_interview
from vibey.bootstrap import build_app, database_url
from vibey.cli.main import app
from vibey.domain.job import idempotency_key
from vibey.domain.phase import Phase
from vibey.domain.spec import AcceptanceCriterion, DesignSpec

pytestmark = pytest.mark.integration
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

#: Every credential a paid engine could reach for. The sovereign path must not need one.
PAID_CREDENTIALS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CURSOR_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
)

PLAN = {
    "items": [
        {
            "item_id": "ws",
            "title": "greet() end to end",
            "acceptance_ids": ["AC-1"],
            "depends_on": [],
            "est_effort": "standard",
            "files_touched_hint": ["greeter.py", "tests/test_greeter.py"],
            "verification": {
                "commands": ["python -m pytest -q tests"],
                "criteria_checked": ["AC-1"],
            },
        },
        {
            "item_id": "polite-greeting",
            "title": "greet politely",
            "acceptance_ids": ["AC-2"],
            "depends_on": ["ws"],
            "est_effort": "low",
            "files_touched_hint": ["greeter.py"],
            "verification": {
                "commands": ["python -m pytest -q tests -k polite"],
                "criteria_checked": ["AC-2"],
            },
        },
    ]
}


class FakeOllama:
    """An HTTP server that answers `/api/chat` the way Ollama does."""

    def __init__(self, answer: dict[str, object]) -> None:
        self.answer = answer
        self.requests: list[dict[str, object]] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - the stdlib's name
                length = int(self.headers["Content-Length"])
                fake.requests.append({"path": self.path, **json.loads(self.rfile.read(length))})
                body = json.dumps({"message": {"content": json.dumps(fake.answer)}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A002
                return None

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> "FakeOllama":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture(autouse=True)
async def _use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/vibey_test",
    )
    monkeypatch.setenv("VIBEY_PG_URL", url)
    conn = await asyncpg.connect(database_url())
    await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
    await conn.close()


@pytest.fixture
def _sovereign_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No paid credential, and no inherited Ollama or evidence settings."""
    for name in (
        *PAID_CREDENTIALS,
        "VIBEY_OLLAMA_URL",
        "VIBEY_OLLAMA_MODEL",
        "VIBEY_OLLAMA_TIMEOUT",
        "VIBEY_EVIDENCE_DIR",
        "VIBEY_FEATURE_QWENLOOP",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def _quiet_worker() -> Iterator[None]:
    """No real engine doctor runs at startup, and no LISTEN connection."""
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(
                return_value=PreflightResult(installed=True, version="1.0.0", auth_ok=True)
            ),
        ),
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as notifier,
    ):
        notifier.return_value = AsyncMock()
        yield


def _spec() -> DesignSpec:
    return DesignSpec(
        objective="a greeter",
        constraints=(),
        non_goals=(),
        criteria=tuple(
            AcceptanceCriterion(
                criterion_id=criterion_id,
                given="a name",
                when="greet runs",
                then="a greeting returns",
                fit="exact match",
            )
            for criterion_id in ("AC-1", "AC-2")
        ),
        nfrs=(),
        walking_skeleton="greet() end to end",
    )


async def _seed_decompose(tmp_path: Path) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create("sovereign", tmp_path, max_cycles=1, config={})
        await resources.design_specs.save(project.project_id, project.cycle, _spec())
        await enqueue_build_decompose(resources.jobs, project)
        return project.project_id


async def _seed_research(tmp_path: Path) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create(
            "sovereign-research", tmp_path, max_cycles=1, config={}
        )
        project = await resources.projects.transition(
            project.project_id, expected=Phase.INTAKE, to=Phase.DESIGN
        )
        await resources.jobs.enqueue(
            EnqueueRequest(
                project_id=project.project_id,
                cycle=project.cycle,
                phase=Phase.DESIGN,
                kind="design.research",
                idempotency_key=idempotency_key(
                    project.project_id, project.cycle, "design.research", "prior-art"
                ),
                payload={"topic": "prior-art"},
            )
        )
        return project.project_id


async def _rows(query: str, *args: object) -> list[asyncpg.Record]:
    conn = await asyncpg.connect(database_url())
    try:
        return list(await conn.fetch(query, *args))
    finally:
        await conn.close()


@pytest.mark.usefixtures("_sovereign_env", "_quiet_worker")
def test_the_worker_decomposes_on_the_local_model(tmp_path: Path) -> None:
    """DECOMPOSE on `--provider qwenloop` asks the local model, under the spec's own
    criterion ids as a grammar, and fans out items whose verify gates have something to
    run -- where the scripted fake it replaces left every command list empty."""
    project_id = asyncio.run(_seed_decompose(tmp_path))

    with FakeOllama(PLAN) as ollama, patch.dict(os.environ, {"VIBEY_OLLAMA_URL": ollama.url + "/"}):
        res = runner.invoke(
            app,
            ["worker", "--once", "--provider", "qwenloop", "--ollama-model", "sovereign:test"],
        )

    assert res.exit_code == 0, res.output
    assert "processed one job" in res.output
    ((request,),) = [ollama.requests]
    assert request["path"] == "/api/chat"
    assert request["model"] == "sovereign:test"
    item_schema = request["format"]["properties"]["items"]["items"]  # type: ignore[index]
    assert item_schema["properties"]["acceptance_ids"]["items"]["enum"] == ["AC-1", "AC-2"]

    rows = asyncio.run(
        _rows(
            "SELECT work_item_id, payload FROM job "
            "WHERE project_id = $1 AND kind = 'build.implement' ORDER BY created_at, id",
            project_id,
        )
    )
    implement = {row["work_item_id"]: json.loads(row["payload"]) for row in rows}
    assert set(implement) == {"ws", "polite-greeting"}
    assert implement["ws"]["verification"]["commands"] == ["python -m pytest -q tests"]
    assert implement["polite-greeting"]["verification"]["criteria_checked"] == ["AC-2"]


@pytest.mark.usefixtures("_sovereign_env", "_quiet_worker")
def test_an_invalid_plan_leaves_nothing_enqueued(tmp_path: Path) -> None:
    """Never a partial plan: a plan with an unmapped criterion is refused whole, and no
    build.implement job exists for any part of it."""
    project_id = asyncio.run(_seed_decompose(tmp_path))
    partial = {"items": [PLAN["items"][0]]}  # type: ignore[index]

    with FakeOllama(partial) as ollama, patch.dict(os.environ, {"VIBEY_OLLAMA_URL": ollama.url}):
        res = runner.invoke(app, ["worker", "--once", "--provider", "qwenloop"])

    assert res.exit_code == 0, res.output
    assert ollama.requests[0]["model"] == "qwen2.5-coder:14b"
    rows = asyncio.run(
        _rows(
            "SELECT kind, state, last_error FROM job WHERE project_id = $1 ORDER BY created_at",
            project_id,
        )
    )
    assert [row["kind"] for row in rows] == ["build.decompose"]
    assert "AC-2" in json.loads(rows[0]["last_error"])["detail"]


@pytest.mark.usefixtures("_sovereign_env")
def test_research_without_evidence_parks_a_research_evidence_gate(tmp_path: Path) -> None:
    """The research floor, reached loudly and once through the real worker: one attempt,
    a gate that asks for the reading by name, and no retry loop behind it."""
    project_id = asyncio.run(_seed_research(tmp_path))

    res = runner.invoke(app, ["work", str(project_id), "--provider", "qwenloop"])

    assert res.exit_code == 0, res.output
    assert "processed one job" in res.output
    jobs = asyncio.run(
        _rows("SELECT id, state, attempts, last_error FROM job WHERE project_id = $1", project_id)
    )
    ((job,),) = [jobs]
    assert job["state"] == "awaiting_human"
    # Parked, not failed: no failure is recorded, and the park refunds the claim, so the
    # retry after the human supplies the reading is not charged against the job's bound.
    assert job["last_error"] is None
    assert job["attempts"] == 0
    gates = asyncio.run(
        _rows("SELECT gate_id, kind, prompt FROM human_gate WHERE job_id = $1", job["id"])
    )
    ((gate,),) = [gates]
    assert gate["kind"] == "research_evidence"
    assert "'prior-art'" in gate["prompt"]
    assert "`prior-art.md`" in gate["prompt"]
    assert "VIBEY_EVIDENCE_DIR" in gate["prompt"]

    # The gate is a way forward, not a dead end: supply the reading, answer the way the
    # prompt says, and the same job runs again and records the operator's source.
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "prior-art.md").write_text(
        "source: https://example.test/greeters\n\nGreeters greet.", encoding="utf-8"
    )
    answered = runner.invoke(app, ["answer", str(gate["gate_id"]), "--raw", "{}"])
    assert answered.exit_code == 0, answered.output

    summary = {"title": "Prior art", "content": "Greeters greet."}
    with (
        FakeOllama(summary) as ollama,
        patch.dict(
            os.environ, {"VIBEY_OLLAMA_URL": ollama.url, "VIBEY_EVIDENCE_DIR": str(evidence)}
        ),
    ):
        rerun = runner.invoke(app, ["work", str(project_id), "--provider", "qwenloop"])

    assert rerun.exit_code == 0, rerun.output
    assert "processed one job" in rerun.output
    assert "Greeters greet." in str(ollama.requests[0]["messages"])
    (done,) = asyncio.run(_rows("SELECT state FROM job WHERE id = $1", job["id"]))
    assert done["state"] == "succeeded"
    (recorded,) = asyncio.run(
        _rows(
            "SELECT engine_id, provenance::text AS provenance, payload FROM event "
            "WHERE job_id = $1",
            job["id"],
        )
    )
    assert recorded["engine_id"] == "qwenloop"
    assert recorded["provenance"] == "untrusted"
    assert json.loads(recorded["payload"])["source"] == "https://example.test/greeters"


@pytest.mark.usefixtures("_sovereign_env")
def test_work_refuses_a_non_http_ollama_endpoint(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_research(tmp_path))
    with patch.dict(os.environ, {"VIBEY_OLLAMA_URL": "file:///etc/passwd"}):
        res = runner.invoke(app, ["work", str(project_id), "--provider", "qwenloop"])
    assert res.exit_code == 3, res.output
    assert "VIBEY_OLLAMA_URL" in res.output
    assert "http(s) URL with a host" in res.output


@pytest.mark.usefixtures("_sovereign_env", "_quiet_worker")
def test_worker_refuses_a_non_http_ollama_endpoint(tmp_path: Path) -> None:
    asyncio.run(_seed_decompose(tmp_path))
    with patch.dict(os.environ, {"VIBEY_OLLAMA_URL": "ftp://127.0.0.1:11434"}):
        res = runner.invoke(app, ["worker", "--once", "--provider", "qwenloop"])
    assert res.exit_code == 3, res.output
    assert "VIBEY_OLLAMA_URL" in res.output


@pytest.mark.usefixtures("_sovereign_env")
def test_work_passes_the_chosen_model_to_the_design_provider(tmp_path: Path) -> None:
    """`--ollama-model` reaches the client `vibey work` builds; the question batch goes to
    the named model on the configured server."""
    answer = {
        "questions": [{"question_id": "q1", "text": "why?", "default": "x", "blocking": False}]
    }

    async def seed() -> UUID:
        async with build_app() as resources:
            project = await resources.projects.create(
                "model-pick", tmp_path, max_cycles=1, config={}
            )
            await enqueue_design_interview(
                projects=resources.projects, jobs=resources.jobs, project_id=project.project_id
            )
            return project.project_id

    project_id = asyncio.run(seed())
    with FakeOllama(answer) as ollama, patch.dict(os.environ, {"VIBEY_OLLAMA_URL": ollama.url}):
        res = runner.invoke(
            app,
            ["work", str(project_id), "--provider", "qwenloop", "--ollama-model", "picked:1"],
        )

    assert res.exit_code == 0, res.output
    assert [request["model"] for request in ollama.requests] == ["picked:1"]


def test_both_commands_document_the_model_option() -> None:
    for command in ("work", "worker"):
        res = runner.invoke(app, [command, "--help"])
        assert res.exit_code == 0
        assert "--ollama-model" in res.output
        assert "VIBEY_OLLAMA_MODEL" in res.output
