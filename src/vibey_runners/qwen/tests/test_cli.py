# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import io
import json
import subprocess
import urllib.error
from pathlib import Path

import pytest
from typer.testing import CliRunner

from qwenloop import __version__
from qwenloop.cli.app import app
from qwenloop.domain.model import Backend, RepoItem, RunState, RunStatus, ServerInfo
from qwenloop.infrastructure.inference import OpenAICompatServer
from qwenloop.infrastructure.profiles import NVIDIA_BF16, PORTABLE

runner = CliRunner()


def test_version() -> None:
    """Asserts the CLI reports the package's own version, not a literal.

    Hardcoding it meant every release broke this test: the bump moves
    pyproject.toml and __init__.py, the literal stays behind, and CI fails on
    `assert "0.1.0" in "qwenloop 0.2.0"` — a failure that says nothing about the
    CLI and everything about the test.
    """
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_union_commands_are_present() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("run", "resume", "doctor", "cloud", "api", "voice", "model", "server"):
        assert command in result.stdout


def test_model_list_does_not_download() -> None:
    listed = runner.invoke(app, ["model", "list"])
    assert listed.exit_code == 0
    assert "Q5_K_M" in listed.stdout


def test_local_equivalent() -> None:
    result = runner.invoke(app, ["cloud"])
    assert result.exit_code == 0
    assert "local qwenloop equivalent" in result.stdout


def test_identity_usage_and_controls(tmp_path: Path) -> None:
    assert runner.invoke(app, ["whoami"]).exit_code == 0
    assert runner.invoke(app, ["usage", "--cwd", str(tmp_path)]).exit_code == 0
    run_id = "abc"
    assert runner.invoke(app, ["stop", run_id, "--cwd", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["wind-down", run_id, "--cwd", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["prompt", run_id, "hello", "--cwd", str(tmp_path)]).exit_code == 0
    inbox = tmp_path / ".qwenloop" / "runs" / run_id / "control" / "inbox"
    assert len(list(inbox.glob("*.json"))) == 3


def test_model_inspection_validation_and_remove(tmp_path: Path) -> None:
    assert runner.invoke(app, ["model", "inspect"]).exit_code == 0
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "qwenloop.cli.app.ModelCache.verify",
            lambda *_args: (_ for _ in ()).throw(FileNotFoundError("missing")),
        )
        assert runner.invoke(app, ["model", "verify"]).exit_code != 0
    assert runner.invoke(app, ["model", "remove", "portable"]).exit_code != 0
    assert runner.invoke(app, ["model", "remove", "portable", "--yes"]).exit_code == 0
    bf16 = runner.invoke(app, ["model", "install", "--profile", "nvidia-bf16"])
    assert bf16.exit_code == 0
    assert "BF16" in bf16.stdout


def test_server_and_tool_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, True, 1)

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return info

        async def start(self, _profile):  # type: ignore[no-untyped-def]
            return info

        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

        async def stop(self, _info):  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.VllmServer", Server)
    assert runner.invoke(app, ["server", "status"]).exit_code == 0
    assert runner.invoke(app, ["server", "start"]).exit_code == 0
    assert runner.invoke(app, ["server", "stop"]).exit_code == 0
    assert runner.invoke(app, ["tool", "approve", "read_file"]).exit_code == 0
    assert runner.invoke(app, ["tool", "deny", "shell"]).exit_code == 0


def test_doctor_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    assert runner.invoke(app, ["doctor"]).exit_code == 1
    monkeypatch.setattr("shutil.which", lambda _name: "/bin/tool")
    assert runner.invoke(app, ["doctor"]).exit_code == 0


@pytest.mark.parametrize(
    ("status", "expected"),
    [(RunStatus.COMPLETED, 0), (RunStatus.WINDING_DOWN, 75), (RunStatus.FAILED, 1)],
)
def test_run_statuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: RunStatus, expected: int
) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("do it")

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", False, True)

        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

    class FakeRunner:
        def __init__(self, *_args):  # type: ignore[no-untyped-def]
            pass

        async def run(self, **kwargs):  # type: ignore[no-untyped-def]
            return RunState(str(kwargs["run_id"]), status=status)

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.AutonomousRunner", FakeRunner)
    result = runner.invoke(app, ["run", str(plan), "--cwd", str(tmp_path)])
    assert result.exit_code == expected


def test_run_start_and_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("do it")

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return None

        async def start(self, _profile):  # type: ignore[no-untyped-def]
            raise OSError("missing")

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    result = runner.invoke(app, ["run", str(plan), "--cwd", str(tmp_path)])
    assert result.exit_code == 1
    assert "unavailable" in result.stderr


def test_run_waits_for_new_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, False, 1)

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return None

        async def start(self, _profile):  # type: ignore[no-untyped-def]
            return info

    class FakeRunner:
        def __init__(self, *_args):  # type: ignore[no-untyped-def]
            pass

        async def run(self, **_kwargs):  # type: ignore[no-untyped-def]
            return RunState("run", status=RunStatus.COMPLETED)

    async def ready(_server, value, **_kwargs):  # type: ignore[no-untyped-def]
        return value

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.AutonomousRunner", FakeRunner)
    monkeypatch.setattr("qwenloop.cli.app._wait_until_ready", ready)
    assert runner.invoke(app, ["run", str(plan), "--cwd", str(tmp_path)]).exit_code == 0


def test_server_start_reports_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class Server:
        async def start(self, _profile):  # type: ignore[no-untyped-def]
            raise OSError("missing runtime")

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    result = runner.invoke(app, ["server", "start", "--backend", "llama.cpp"])
    assert result.exit_code == 1
    assert "unavailable" in result.stderr


def test_server_stop_when_nothing_is_running(monkeypatch: pytest.MonkeyPatch) -> None:
    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return None

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.VllmServer", Server)
    result = runner.invoke(app, ["server", "stop"])
    assert result.exit_code == 0
    assert "not running" in result.stdout


def test_wait_until_ready_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, False, None)

    class Healthy:
        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

    assert asyncio.run(module._wait_until_ready(Healthy(), info, timeout_seconds=1)) is info

    class Unhealthy:
        async def health(self, _info):  # type: ignore[no-untyped-def]
            return False

    with pytest.raises(TimeoutError):
        asyncio.run(module._wait_until_ready(Unhealthy(), info, timeout_seconds=0))

    class EventuallyHealthy:
        def __init__(self) -> None:
            self.calls = 0

        async def health(self, _info):  # type: ignore[no-untyped-def]
            self.calls += 1
            return self.calls == 2

    assert (
        asyncio.run(module._wait_until_ready(EventuallyHealthy(), info, timeout_seconds=1)) is info
    )

    dead = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, False, 999)

    def missing(_pid, _signal):  # type: ignore[no-untyped-def]
        raise ProcessLookupError

    monkeypatch.setattr(module.os, "kill", missing)
    with pytest.raises(RuntimeError, match="exited"):
        asyncio.run(module._wait_until_ready(Unhealthy(), dead, timeout_seconds=1))


def test_portable_install_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "model.gguf"
    monkeypatch.setattr("qwenloop.cli.app.ModelCache.install", lambda *_args: target)
    result = runner.invoke(app, ["model", "install", "--profile", "portable"])
    assert result.exit_code == 0
    assert str(target) in result.stdout


def test_portable_install_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args):  # type: ignore[no-untyped-def]
        raise ValueError("bad artifact")

    monkeypatch.setattr("qwenloop.cli.app.ModelCache.install", fail)
    result = runner.invoke(app, ["model", "install", "--profile", "portable"])
    assert result.exit_code != 0


def test_remove_existing_profile_is_recoverable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "models" / "portable"
    target.mkdir(parents=True)
    monkeypatch.setattr("qwenloop.cli.app.user_cache_path", lambda _name: tmp_path)
    result = runner.invoke(app, ["model", "remove", "portable", "--yes"])
    assert result.exit_code != 0
    assert "Trash" in result.output


def test_entry_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    called: list[bool] = []
    monkeypatch.setattr(module, "app", lambda: called.append(True))
    assert module._nvidia_vram() == 0
    module.main()
    assert called == [True]


def test_nvidia_vram_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    class Result:
        stdout = "40960\n2048\n"

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Result())
    assert module._nvidia_vram() == 40960 * 1024 * 1024


def test_nvidia_vram_probe_without_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    assert module._nvidia_vram() == 0


@pytest.mark.parametrize("failure", [OSError("missing"), ValueError("bad")])
def test_nvidia_vram_probe_failure(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    import qwenloop.cli.app as module

    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")

    def fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise failure

    monkeypatch.setattr(module.subprocess, "run", fail)
    assert module._nvidia_vram() == 0


def test_run_rejects_storm_with_plan(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    result = runner.invoke(app, ["run", str(plan), "--storm"])
    assert result.exit_code != 0
    assert "not both" in result.output


def test_run_requires_plan_when_not_storm() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0
    assert "PLAN is required" in result.output


def test_discover_storm_repos_filters_uncloned_and_handles_gh_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import qwenloop.cli.app as module

    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b").mkdir()  # not cloned: no .git
    monkeypatch.setattr(module, "list_repo_names", lambda _owner: ["a", "b", "c"])
    assert module._discover_storm_repos("owner", tmp_path) == ["a"]
    monkeypatch.setattr(module, "list_repo_names", lambda _owner: None)
    assert module._discover_storm_repos("owner", tmp_path) == []


def test_storm_sweep_reports_per_repo_status_and_tally(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b" / ".git").mkdir(parents=True)

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", False, True)

        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

    class FakeRunner:
        def __init__(self, *_args):  # type: ignore[no-untyped-def]
            pass

        async def run(self, **kwargs):  # type: ignore[no-untyped-def]
            status = RunStatus.COMPLETED if kwargs["cwd"].name == "a" else RunStatus.FAILED
            return RunState(str(kwargs["run_id"]), status=status, turns=3)

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.AutonomousRunner", FakeRunner)
    monkeypatch.setattr("qwenloop.cli.app.list_repo_names", lambda _owner: ["a", "b"])
    monkeypatch.setattr("qwenloop.cli.app.list_open_issues", lambda _owner, _repo: None)
    monkeypatch.setattr("qwenloop.cli.app.list_open_pull_requests", lambda _owner, _repo: None)

    result = runner.invoke(
        app,
        [
            "run",
            "--storm",
            "--owner",
            "acme",
            "--repos-root",
            str(tmp_path),
            "--max-attempts",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert "a\tcompleted\t3" in result.stdout
    assert "b\tfailed\t3" in result.stdout
    assert "qwenstorm complete: 1/2 repos completed" in result.stdout


def test_tracked_repository_context_names_the_real_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    class Result:
        returncode = 0
        stdout = "pyproject.toml\0src/app.py\0tests/test_app.py\0"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Result())
    context = module._tracked_repository_context(Path("/repo"))
    assert "pyproject.toml" in context
    assert "no tracked Go manifest" in context
    assert "Python is part" in context


def test_tracked_repository_context_preserves_a_tracked_go_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import qwenloop.cli.app as module

    class Result:
        returncode = 0
        stdout = "go.mod\0internal/main.go\0"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Result())
    context = module._tracked_repository_context(Path("/repo"))
    assert "go.mod" in context
    assert "no tracked Go manifest" not in context
    assert "Python is part" not in context


@pytest.mark.parametrize(
    "result",
    [
        subprocess.CompletedProcess([], 1, "", "not a repository"),
        subprocess.CompletedProcess([], 0, "", ""),
    ],
)
def test_tracked_repository_context_handles_missing_facts(
    monkeypatch: pytest.MonkeyPatch, result: subprocess.CompletedProcess[str]
) -> None:
    import qwenloop.cli.app as module

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: result)
    context = module._tracked_repository_context(Path("/repo"))
    assert "inspect the repository" in context or "no tracked files" in context


def test_tracked_repository_context_handles_probe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    def fail(*_args, **_kwargs):
        raise OSError("git missing")

    monkeypatch.setattr(module.subprocess, "run", fail)
    assert "probe unavailable" in module._tracked_repository_context(Path("/repo"))


def test_tracked_repository_context_handles_missing_git(monkeypatch: pytest.MonkeyPatch) -> None:
    import qwenloop.cli.app as module

    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    assert "git is not installed" in module._tracked_repository_context(Path("/repo"))


def test_storm_retries_a_failed_item_until_it_converges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "a" / ".git").mkdir(parents=True)
    calls = 0

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", False, True)

        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

    class FakeRunner:
        def __init__(self, *_args):  # type: ignore[no-untyped-def]
            pass

        async def run(self, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal calls
            calls += 1
            status = RunStatus.FAILED if calls == 1 else RunStatus.COMPLETED
            return RunState(str(kwargs["run_id"]), status=status, turns=2)

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.AutonomousRunner", FakeRunner)
    monkeypatch.setattr(
        "qwenloop.cli.app.list_open_issues",
        lambda _owner, _repo: [RepoItem(1, "fix", "")],
    )
    monkeypatch.setattr("qwenloop.cli.app.list_open_pull_requests", lambda _owner, _repo: [])

    result = runner.invoke(
        app,
        [
            "run",
            "--storm",
            "--repos-root",
            str(tmp_path),
            "--repo",
            "a",
            "--max-attempts",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert calls == 2
    assert "a issue#1\tattempt 1/2\tfailed\t2" in result.stdout
    assert "a issue#1\tcompleted\t2 (attempt 2/2)" in result.stdout
    assert "qwenstorm complete: 1/1 repos completed (1/1 items completed)" in result.stdout


def test_storm_reports_a_successful_empty_backlog_without_starting_a_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "a" / ".git").mkdir(parents=True)

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", False, True)

        async def health(self, _info):  # type: ignore[no-untyped-def]
            return True

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.list_open_issues", lambda _owner, _repo: [])
    monkeypatch.setattr("qwenloop.cli.app.list_open_pull_requests", lambda _owner, _repo: [])

    result = runner.invoke(app, ["run", "--storm", "--repos-root", str(tmp_path), "--repo", "a"])
    assert result.exit_code == 0
    assert "a\tno-open-items\t0" in result.stdout
    assert "qwenstorm complete: 1/1 repos completed (0/0 items completed)" in result.stdout


def test_storm_skips_repo_not_cloned_locally(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("qwenloop.cli.app.list_repo_names", lambda _owner: [])
    result = runner.invoke(
        app, ["run", "--storm", "--repos-root", str(tmp_path), "--repo", "missing"]
    )
    assert result.exit_code == 0
    assert "skip missing: not cloned" in result.stdout
    assert "qwenstorm complete: 0/0 repos completed" in result.stdout


def test_storm_continues_past_unavailable_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b" / ".git").mkdir(parents=True)

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return None

        async def start(self, _profile):  # type: ignore[no-untyped-def]
            raise OSError("no runtime")

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    monkeypatch.setattr("qwenloop.cli.app.list_open_issues", lambda _owner, _repo: None)
    monkeypatch.setattr("qwenloop.cli.app.list_open_pull_requests", lambda _owner, _repo: None)

    result = runner.invoke(
        app,
        ["run", "--storm", "--repos-root", str(tmp_path), "--repo", "a", "--repo", "b"],
    )
    assert result.exit_code == 0
    assert "a\tunavailable\tno runtime" in result.stdout
    assert "b\tunavailable\tno runtime" in result.stdout
    assert "qwenstorm complete: 0/2 repos completed" in result.stdout


# --- openai-compat endpoint mode (Ollama first) -------------------------------------------

OLLAMA_MODELS = b'{"object": "list", "data": [{"id": "qwen2.5-coder:14b"}]}'


class FakeHttp:
    """`urlopen` for an Ollama-shaped endpoint. No socket is ever opened."""

    def __init__(self, models: bytes | BaseException = OLLAMA_MODELS) -> None:
        self.models = models
        self.urls: list[str] = []

    def __call__(self, request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        self.urls.append(request.full_url)
        if isinstance(self.models, BaseException):
            raise self.models
        return _Body(self.models)


class _Body(io.BytesIO):
    status = 200


class RecordingRunner:
    """Stands in for AutonomousRunner and remembers what each run was handed."""

    calls: list[dict[str, object]] = []

    def __init__(self, server, *_args):  # type: ignore[no-untyped-def]
        self.server = server

    async def run(self, **kwargs):  # type: ignore[no-untyped-def]
        RecordingRunner.calls.append({**kwargs, "server": self.server})
        return RunState(str(kwargs["run_id"]), status=RunStatus.COMPLETED, turns=2)


@pytest.fixture
def recording_runner(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    RecordingRunner.calls = []
    monkeypatch.setattr("qwenloop.cli.app.AutonomousRunner", RecordingRunner)
    return RecordingRunner.calls


def _no_managed_servers(monkeypatch: pytest.MonkeyPatch) -> None:
    class Forbidden:
        def __init__(self, *_args):  # type: ignore[no-untyped-def]
            raise AssertionError("an endpoint run must never build a managed server")

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Forbidden)
    monkeypatch.setattr("qwenloop.cli.app.VllmServer", Forbidden)


def test_run_attaches_to_the_endpoint_named_by_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, recording_runner: list[dict[str, object]]
) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    http = FakeHttp()
    monkeypatch.setattr("urllib.request.urlopen", http)
    _no_managed_servers(monkeypatch)
    result = runner.invoke(
        app,
        ["run", str(plan), "--cwd", str(tmp_path), "--base-url", "http://127.0.0.1:11434/v1"],
    )
    assert result.exit_code == 0, result.output
    call = recording_runner[0]
    info = call["server_info"]
    assert isinstance(call["server"], OpenAICompatServer)
    assert isinstance(info, ServerInfo)
    assert (info.backend, info.model, info.owned) == (
        Backend.OPENAI_COMPAT,
        "qwen2.5-coder:14b",
        False,
    )
    assert http.urls == ["http://127.0.0.1:11434/v1/models"]


def test_run_attaches_through_the_environment_with_config_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    isolated_settings: Path,
    recording_runner: list[dict[str, object]],
) -> None:
    isolated_settings.write_text(
        'model = "qwen2.5-coder:14b"\nmax_turns = 7\ncontext_window = 8192\n', encoding="utf-8"
    )
    monkeypatch.setenv("QWENLOOP_BASE_URL", "http://gpu-box:11434/v1")
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    _no_managed_servers(monkeypatch)
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    assert runner.invoke(app, ["run", str(plan), "--cwd", str(tmp_path)]).exit_code == 0
    call = recording_runner[0]
    assert call["max_turns"] == 7
    profile = call["profile"]
    assert profile.context_window == 8192  # type: ignore[attr-defined]
    assert profile.repository == "http://gpu-box:11434/v1"  # type: ignore[attr-defined]


def test_run_flag_beats_config_for_max_turns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    isolated_settings: Path,
    recording_runner: list[dict[str, object]],
) -> None:
    isolated_settings.write_text("max_turns = 7\n", encoding="utf-8")
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    result = runner.invoke(
        app,
        [
            "run",
            str(plan),
            "--cwd",
            str(tmp_path),
            "--backend",
            "openai-compat",
            "--max-turns",
            "96",
        ],
    )
    assert result.exit_code == 0, result.output
    assert recording_runner[0]["max_turns"] == 96


def test_run_fails_loudly_when_the_endpoint_lacks_the_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp(b'{"data": [{"id": "llama3:8b"}]}'))
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    result = runner.invoke(
        app, ["run", str(plan), "--cwd", str(tmp_path), "--base-url", "http://h:1/v1"]
    )
    assert result.exit_code == 1
    assert "qwenloop unavailable: model 'qwen2.5-coder:14b' is not served" in result.stderr
    assert "ollama pull qwen2.5-coder:14b" in result.stderr


def test_bad_configuration_exits_2_naming_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QWENLOOP_BASE_URL", "file:///etc/passwd")
    plan = tmp_path / "plan.md"
    plan.write_text("do it")
    result = runner.invoke(app, ["run", str(plan)])
    assert result.exit_code == 2
    assert "qwenloop configuration" in result.output
    assert "base_url must be an http" in result.output


def test_storm_sweeps_through_the_same_endpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, recording_runner: list[dict[str, object]]
) -> None:
    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b" / ".git").mkdir(parents=True)
    monkeypatch.setenv("QWENLOOP_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    _no_managed_servers(monkeypatch)
    monkeypatch.setattr("qwenloop.cli.app.list_open_issues", lambda _owner, _repo: None)
    monkeypatch.setattr("qwenloop.cli.app.list_open_pull_requests", lambda _owner, _repo: None)
    result = runner.invoke(
        app,
        ["run", "--storm", "--repos-root", str(tmp_path), "--repo", "a", "--repo", "b"],
    )
    assert result.exit_code == 0, result.output
    assert "qwenstorm complete: 2/2 repos completed" in result.stdout
    backends = {call["server_info"].backend for call in recording_runner}  # type: ignore[attr-defined]
    assert backends == {Backend.OPENAI_COMPAT}


def test_doctor_passes_when_the_endpoint_serves_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWENLOOP_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setattr("shutil.which", lambda _name: None)  # no llama-server, no vllm
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "backend: openai-compat (an OpenAI-compatible endpoint is configured)" in result.stdout
    assert "endpoint: http://127.0.0.1:11434/v1" in result.stdout
    assert "model: qwen2.5-coder:14b ok" in result.stdout


def test_doctor_fails_loudly_when_the_endpoint_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: "/bin/tool")  # binaries do not rescue it
    monkeypatch.setattr(
        "urllib.request.urlopen", FakeHttp(urllib.error.URLError("Connection refused"))
    )
    result = runner.invoke(app, ["doctor", "--backend", "openai-compat"])
    assert result.exit_code == 1
    assert "endpoint: http://127.0.0.1:11434/v1" in result.stdout
    assert "model: qwen2.5-coder:14b unavailable" in result.stdout
    assert "qwenloop doctor: openai-compat endpoint" in result.stderr
    assert "is unreachable (Connection refused)" in result.stderr


def test_doctor_fails_loudly_when_the_model_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    result = runner.invoke(
        app, ["doctor", "--base-url", "http://h:1/v1", "--model", "qwen2.5-coder:32b"]
    )
    assert result.exit_code == 1
    assert "'qwen2.5-coder:32b' is not served by http://h:1/v1" in result.stderr


def test_server_status_reports_the_endpoint_without_its_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QWENLOOP_API_KEY", "sk-very-secret")
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    result = runner.invoke(app, ["server", "status", "--base-url", "http://h:1/v1"])
    assert result.exit_code == 0
    status = json.loads(result.stdout)
    assert status["backend"] == "openai-compat"
    assert status["healthy"] is True
    assert status["owned"] is False
    assert status["token"] == "<redacted>"
    assert "sk-very-secret" not in result.stdout

    monkeypatch.setattr("urllib.request.urlopen", FakeHttp(urllib.error.URLError("down")))
    down = json.loads(
        runner.invoke(app, ["server", "status", "--base-url", "http://h:1/v1"]).stdout
    )
    assert down["healthy"] is False


def test_server_status_shows_a_managed_servers_own_token(monkeypatch: pytest.MonkeyPatch) -> None:
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, True, 1, "per-launch")

    class Server:
        def inspect(self, _profile):  # type: ignore[no-untyped-def]
            return info

    monkeypatch.setattr("qwenloop.cli.app.LlamaCppServer", Server)
    status = json.loads(runner.invoke(app, ["server", "status"]).stdout)
    assert status["token"] == "per-launch"


def test_server_start_checks_the_endpoint_instead_of_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", FakeHttp())
    _no_managed_servers(monkeypatch)
    result = runner.invoke(app, ["server", "start", "--base-url", "http://h:1/v1"])
    assert result.exit_code == 0, result.output
    started = json.loads(result.stdout)
    assert (started["backend"], started["healthy"], started["pid"]) == ("openai-compat", True, None)


def test_server_start_honours_vllm_and_the_configured_timeout_and_window(
    monkeypatch: pytest.MonkeyPatch, isolated_settings: Path
) -> None:
    isolated_settings.write_text(
        "startup_timeout_seconds = 11\ncontext_window = 16384\n", encoding="utf-8"
    )
    seen: dict[str, object] = {}
    info = ServerInfo(Backend.VLLM, NVIDIA_BF16.name, "x", True, False, 5, "t")

    class Vllm:
        async def start(self, profile):  # type: ignore[no-untyped-def]
            seen["profile"] = profile
            return info

    async def ready(_server, value, *, timeout_seconds):  # type: ignore[no-untyped-def]
        seen["timeout"] = timeout_seconds
        return value

    monkeypatch.setattr("qwenloop.cli.app.VllmServer", Vllm)
    monkeypatch.setattr("qwenloop.cli.app._wait_until_ready", ready)
    result = runner.invoke(app, ["server", "start", "--backend", "vllm"])
    assert result.exit_code == 0, result.output
    assert seen["timeout"] == 11
    assert seen["profile"].name == NVIDIA_BF16.name  # type: ignore[attr-defined]
    assert seen["profile"].context_window == 16384  # type: ignore[attr-defined]
