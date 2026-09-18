# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from tests.application.fakes import make_job
from vibey.infrastructure.skills_context import (
    VibeySkillsContextCompiler,
    _load_json_object,
    _provenance,
    _request_for,
    compiler_from_config,
)


def _fake_cli(tmp_path: Path) -> tuple[str, ...]:
    script = tmp_path / "fake_vibey_skills.py"
    script.write_text(
        """# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
import json
import pathlib
import sys

args = sys.argv[1:]
if args[:2] == ["index", "build"]:
    output = pathlib.Path(args[args.index("--output") + 1])
    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text("{}")
    (output / "index.sqlite3").write_bytes(b"sqlite")
    raise SystemExit(0)
if args[:2] == ["index", "inspect"]:
    raise SystemExit(0)
if args[0] == "packet":
    packet = pathlib.Path(args[args.index("--output") + 1])
    manifest = pathlib.Path(args[args.index("--manifest") + 1])
    packet.write_text("# Vibey Skills Context Packet\\n\\nUse isolated databases.\\n")
    manifest.write_text(json.dumps({
        "status": "ok",
        "schema_version": 1,
        "index_version": 1,
        "skills_release": "2.17.0",
        "corpus_sha256": "corpus",
        "query_sha256": "query",
        "packet_sha256": "packet",
        "packet_token_estimate": 12,
        "selected_skills": ["python-quality-testing"],
    }))
    raise SystemExit(0)
raise SystemExit(1)
""",
        encoding="utf-8",
    )
    return sys.executable, str(script)


def _job():  # type: ignore[no-untyped-def]
    return replace(
        make_job(uuid4()),
        kind="build.implement",
        work_item_id="item-1",
        attempts=1,
        payload={
            "title": "PostgreSQL tests",
            "languages": ["python"],
            "verification": {"commands": ["pytest -q"]},
        },
    )


async def test_compiler_runs_process_contract_and_returns_bounded_provenance(
    tmp_path: Path,
) -> None:
    compiler = VibeySkillsContextCompiler(
        mode="inject",
        index_path=tmp_path / "index",
        command=_fake_cli(tmp_path),
    )

    result = await compiler.compile(job=_job(), worktree_path=tmp_path / "worktree")

    assert result.should_inject
    assert "isolated databases" in result.markdown
    assert result.provenance["skills_release"] == "2.17.0"
    assert result.provenance["selected_skills"] == ["python-quality-testing"]
    assert "PostgreSQL tests" not in json.dumps(result.provenance)
    request = next((tmp_path / "worktree/.vibey/context/skills").glob("*.request.json"))
    request_data = json.loads(request.read_text())
    assert request_data["commands"] == ["pytest -q"]
    assert request_data["languages"] == ["python"]
    assert request_data["maximum_context_tokens"] == 6000

    second = await compiler.compile(job=_job(), worktree_path=tmp_path / "second")
    assert second.status == "ok"


async def test_missing_cli_falls_back_without_raising(tmp_path: Path) -> None:
    compiler = VibeySkillsContextCompiler(
        mode="shadow",
        index_path=tmp_path / "index",
        command=(str(tmp_path / "missing-vibey-skills"),),
    )

    result = await compiler.compile(job=_job(), worktree_path=tmp_path / "worktree")

    assert result.status == "error"
    assert not result.should_inject
    assert result.provenance["fallback"] == "existing_prompt"


def test_project_config_is_off_by_default_and_validated(tmp_path: Path) -> None:
    assert compiler_from_config({}, repo_path=tmp_path) is None
    assert compiler_from_config({"skills_context": {"mode": "off"}}, repo_path=tmp_path) is None
    compiler = compiler_from_config(
        {"skills_context": {"mode": "shadow", "budget": 2_000}}, repo_path=tmp_path
    )
    assert isinstance(compiler, VibeySkillsContextCompiler)
    with pytest.raises(ValueError, match="off, shadow, or inject"):
        compiler_from_config({"skills_context": {"mode": "surprise"}}, repo_path=tmp_path)
    with pytest.raises(ValueError, match="budget"):
        compiler_from_config(
            {"skills_context": {"mode": "inject", "budget": True}}, repo_path=tmp_path
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    (
        ({"mode": "off", "index_path": Path("index")}, "shadow.*inject"),
        ({"mode": "inject", "index_path": Path("index"), "budget": 999}, "budget"),
        ({"mode": "inject", "index_path": Path("index"), "timeout_seconds": 0}, "positive"),
        ({"mode": "inject", "index_path": Path("index"), "command": ("",)}, "empty"),
    ),
)
def test_compiler_constructor_validation(kwargs: dict[str, object], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        VibeySkillsContextCompiler(**kwargs)  # type: ignore[arg-type]


async def test_compile_rejects_non_job(tmp_path: Path) -> None:
    compiler = VibeySkillsContextCompiler(mode="inject", index_path=tmp_path / "index")
    with pytest.raises(TypeError, match="JobRecord"):
        await compiler.compile(job=object(), worktree_path=tmp_path)


async def test_packet_failure_and_malformed_outputs_fall_back(tmp_path: Path) -> None:
    compiler = VibeySkillsContextCompiler(mode="inject", index_path=tmp_path / "index")
    compiler._ensure_index = AsyncMock()  # type: ignore[method-assign]
    compiler._run = AsyncMock(return_value=(3, "", "packet failed"))  # type: ignore[method-assign]
    context = tmp_path / "worktree/.vibey/context/skills"
    context.mkdir(parents=True)
    job = _job()
    (context / f"{job.id}.packet.json").write_text('{"status":"error"}')

    failed = await compiler.compile(job=job, worktree_path=tmp_path / "worktree")
    assert failed.status == "error"
    assert failed.provenance["detail"] == "packet failed"

    (context / f"{job.id}.packet.json").write_text("[]")
    malformed = await compiler.compile(job=job, worktree_path=tmp_path / "worktree")
    assert malformed.provenance["fallback"] == "existing_prompt"


async def test_invalid_index_is_rebuilt_and_build_failure_falls_back(tmp_path: Path) -> None:
    index = tmp_path / "index"
    index.mkdir()
    (index / "manifest.json").write_text("{}")
    (index / "index.sqlite3").write_bytes(b"db")
    compiler = VibeySkillsContextCompiler(mode="shadow", index_path=index)
    compiler._run = AsyncMock(  # type: ignore[method-assign]
        side_effect=((1, "", "bad index"), (1, "", "build failed"))
    )

    result = await compiler.compile(job=_job(), worktree_path=tmp_path / "worktree")

    assert result.status == "error"
    assert "build failed" in str(result.provenance["detail"])


async def test_run_kills_the_clis_whole_group_on_timeout_and_reraises(tmp_path: Path) -> None:
    """The CLI leads a group of its own, so the kill reaches what it started. A plain
    kill left the background `sleep` holding the pipes, and the wait after it waited
    on the sleep (#283)."""
    import asyncio

    from structlog.testing import capture_logs

    from tests.infrastructure.process.escapes import background_script, dead_within, read_pids

    pidfile = tmp_path / "background.pid"
    compiler = VibeySkillsContextCompiler(mode="shadow", index_path=tmp_path, timeout_seconds=1.0)
    loop = asyncio.get_running_loop()

    started = loop.time()
    with capture_logs() as logs, pytest.raises(TimeoutError):
        await compiler._run("/bin/sh", "-c", background_script(pidfile))

    # The old kill-then-wait returned only when the 30-second sleep did.
    assert loop.time() - started < 10
    (background,) = await read_pids(pidfile)
    assert await dead_within(background, seconds=5)
    assert not [e for e in logs if e["event"] == "skills_context_process_not_reaped"]


async def test_run_abandons_the_reap_after_the_grace_when_an_escaped_child_holds_the_pipes(
    tmp_path: Path,
) -> None:
    """No group kill reaches a child that left the group. The compiler gives up on the
    reap after `kill_grace_seconds`, logs it, and the timeout still propagates."""
    import asyncio

    from structlog.testing import capture_logs

    from tests.infrastructure.process.escapes import ESCAPE, dead_within, read_pids, release

    pidfile = tmp_path / "escape.pids"
    compiler = VibeySkillsContextCompiler(
        mode="shadow", index_path=tmp_path, timeout_seconds=1.0, kill_grace_seconds=0.2
    )
    loop = asyncio.get_running_loop()

    started = loop.time()
    with capture_logs() as logs, pytest.raises(TimeoutError):
        await compiler._run(sys.executable, "-c", ESCAPE, str(pidfile), "linger")
    escaped, cli = await read_pids(pidfile)
    try:
        assert loop.time() - started < 10
        (warning,) = [e for e in logs if e["event"] == "skills_context_process_not_reaped"]
        assert warning["pid"] == cli
        assert warning["kill_grace_seconds"] == 0.2
        assert await dead_within(cli, seconds=5)
    finally:
        await release(escaped)


def test_config_and_request_projection_variants(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be an object"):
        compiler_from_config({"skills_context": "yes"}, repo_path=tmp_path)
    with pytest.raises(ValueError, match="timeout"):
        compiler_from_config(
            {"skills_context": {"mode": "inject", "timeout_seconds": True}},
            repo_path=tmp_path,
        )
    for command in ("binary", ["binary", ""]):
        with pytest.raises(ValueError, match="command"):
            compiler_from_config(
                {"skills_context": {"mode": "inject", "command": command}},
                repo_path=tmp_path,
            )
    compiler = compiler_from_config(
        {
            "skills_context": {
                "mode": "inject",
                "command": ["vibey-skills"],
                "index_path": "relative-index",
                "timeout_seconds": 3,
            }
        },
        repo_path=tmp_path,
    )
    assert isinstance(compiler, VibeySkillsContextCompiler)
    assert compiler._index_path == tmp_path / "relative-index"

    payload = {
        "objective": "repair tests",
        "requirements": ["safe"],
        "verification": {"commands": "not-a-list"},
        "repair_detail": " failure " + "x" * 1_100,
    }
    request = _request_for(replace(_job(), payload=payload), budget=2_000)
    assert request["commands"] == []
    assert request["requirements"] == ["safe"]
    assert request["prior_failure_class"] == "verification"
    assert len(str(request["error_summary"])) == 1_000

    no_verification = _request_for(replace(_job(), payload={}), budget=1_000)
    assert no_verification["commands"] == []


def test_manifest_and_provenance_helpers(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    with pytest.raises(ValueError, match="JSON object"):
        _load_json_object(manifest)
    provenance = _provenance(
        mode="inject",
        status="error",
        manifest={"selected_plugins": ["core"], "secret": "excluded"},
        returncode=3,
        detail=" details ",
    )
    assert provenance["selected_plugins"] == ["core"]
    assert provenance["detail"] == "details"
    assert "secret" not in provenance
