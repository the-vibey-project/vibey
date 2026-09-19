# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import pytest

from claudeloop.application.dto import BackendStatus, RunResult, ToolCallStatus
from claudeloop.application.usecases.doctor import DoctorCheck, all_passed, run_doctor
from claudeloop.application.usecases.list_sessions import list_sessions
from claudeloop.application.usecases.resume_session import resolve_most_recent, resume_explicit
from claudeloop.application.usecases.run_control import request_wind_down
from claudeloop.application.usecases.run_plan import (
    run_from_plan_file,
    with_done_marker_instruction,
)
from claudeloop.domain.backend import BackendProfile
from claudeloop.domain.control import WindDownCommand
from claudeloop.domain.errors import InvalidSessionSelectorError
from claudeloop.domain.session import SessionRef

# --- run_plan ---


def test_with_done_marker_instruction_appends_the_marker_text() -> None:
    result = with_done_marker_instruction("do the thing", "MY_MARKER")
    assert "do the thing" in result
    assert "MY_MARKER" in result


class _StubRunner:
    def __init__(self, result: RunResult) -> None:
        self._result = result
        self.calls: list[tuple[str, str]] = []

    async def run(self, *, initial_prompt: str, continue_prompt: str) -> RunResult:
        self.calls.append((initial_prompt, continue_prompt))
        return self._result


async def test_run_from_plan_file_reads_the_file_and_delegates_to_runner(tmp_path: Path) -> None:
    plan_path = tmp_path / "handoff.md"
    plan_path.write_text("- [ ] do the thing\n")
    expected = RunResult(
        success=True, reason="done", session_id="sid", turns_spent=1, dollars_spent=0.0
    )
    stub = _StubRunner(expected)

    result = await run_from_plan_file(stub, plan_path)  # type: ignore[arg-type]

    assert result is expected
    assert len(stub.calls) == 1
    initial, continue_prompt = stub.calls[0]
    assert "do the thing" in initial
    assert "CLAUDELOOP_TASK_FULLY_COMPLETE" in initial
    assert "Continue exactly where you left off." in continue_prompt


# --- resume_session ---


async def test_resume_explicit_sends_a_single_continue_style_prompt() -> None:
    expected = RunResult(
        success=True, reason="done", session_id="sid", turns_spent=1, dollars_spent=0.0
    )
    stub = _StubRunner(expected)
    result = await resume_explicit(stub)  # type: ignore[arg-type]
    assert result is expected
    initial, continue_prompt = stub.calls[0]
    assert initial == continue_prompt  # resume uses the same marker-wrapped prompt both times


class _FakeCatalog:
    def __init__(self, ref: SessionRef | None) -> None:
        self._ref = ref

    def most_recent(self, cwd: str) -> SessionRef | None:
        return self._ref

    def list_all(self, cwd: str | None = None) -> list[SessionRef]:
        return [self._ref] if self._ref else []


def test_resolve_most_recent_returns_the_session_when_found() -> None:
    ref = SessionRef(session_id="abc", cwd="/repo")
    catalog = _FakeCatalog(ref)
    assert resolve_most_recent(catalog, "/repo") is ref  # type: ignore[arg-type]


def test_resolve_most_recent_raises_a_clear_error_when_none_found() -> None:
    catalog = _FakeCatalog(None)
    with pytest.raises(InvalidSessionSelectorError, match="No prior Claude Code sessions"):
        resolve_most_recent(catalog, "/repo")  # type: ignore[arg-type]


# --- list_sessions ---


def test_list_sessions_delegates_to_the_catalog() -> None:
    ref = SessionRef(session_id="abc", cwd="/repo")
    catalog = _FakeCatalog(ref)
    assert list_sessions(catalog, "/repo") == [ref]  # type: ignore[arg-type]


# --- doctor ---


class _FakeDoctorEnv:
    def __init__(
        self,
        *,
        cli_path: str | None,
        version: str | None,
        authed: bool,
        mcp_servers: list[str],
        anthropic_version: str | None = "0.0.0",
        api_count: int | None = 137,
        bundled_cli: str | None = None,
        backend_status: BackendStatus | None = None,
        tool_calls: dict[str, ToolCallStatus] | None = None,
    ) -> None:
        self._cli_path = cli_path
        self._version = version
        self._authed = authed
        self._mcp_servers = mcp_servers
        self._anthropic_version = anthropic_version
        self._api_count = api_count
        self._bundled_cli = bundled_cli
        self._backend_status = backend_status or BackendStatus(reachable=False, detail="down")
        self._tool_calls = tool_calls or {}
        self.version_asked: list[str] = []
        self.probed: list[tuple[str, str]] = []
        self.tool_probed: list[str] = []

    def find_claude_cli(self) -> str | None:
        return self._cli_path

    def find_bundled_claude_cli(self) -> str | None:
        return self._bundled_cli

    def claude_cli_version(self, path: str) -> str | None:
        self.version_asked.append(path)
        return self._version

    def probe_backend(self, base_url: str, auth_token: str) -> BackendStatus:
        self.probed.append((base_url, auth_token))
        return self._backend_status

    def probe_tool_calling(self, base_url: str, auth_token: str, model: str) -> ToolCallStatus:
        self.tool_probed.append(model)
        return self._tool_calls.get(model, ToolCallStatus(supported=True, detail="tool_use"))

    def is_authenticated(self) -> bool:
        return self._authed

    def configured_mcp_servers(self) -> list[str]:
        return self._mcp_servers

    def anthropic_sdk_version(self) -> str | None:
        return self._anthropic_version

    def api_surface_method_count(self) -> int | None:
        return self._api_count


def test_run_doctor_all_green(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    env = _FakeDoctorEnv(cli_path="/usr/bin/claude", version="1.0", authed=True, mcp_servers=[])
    checks = run_doctor(env, cwd=tmp_path)  # type: ignore[arg-type]
    assert all_passed(checks) is True
    assert {c.name for c in checks} == {
        "claude-cli",
        "authentication",
        "mcp-servers",
        "anthropic-sdk",
        "api-surface",
        "working-directory",
    }


def test_run_doctor_missing_cli() -> None:
    env = _FakeDoctorEnv(cli_path=None, version=None, authed=False, mcp_servers=[])
    checks = run_doctor(env, cwd=Path("/tmp"))  # type: ignore[arg-type]
    cli_check = next(c for c in checks if c.name == "claude-cli")
    assert cli_check.passed is False
    assert "not found" in cli_check.detail


def test_the_fake_doctor_env_satisfies_the_port() -> None:
    from claudeloop.application.interfaces import DoctorEnvironment

    env = _FakeDoctorEnv(cli_path=None, version=None, authed=False, mcp_servers=[])
    assert isinstance(env, DoctorEnvironment)


def test_run_doctor_falls_back_to_the_sdk_bundled_cli_when_claude_is_not_on_path() -> None:
    """Issue #121 S1b: a container with no global `claude` still runs, because the
    SDK launches its own bundled CLI — doctor must not fail it for that."""
    env = _FakeDoctorEnv(
        cli_path=None,
        version="2.1.0",
        authed=True,
        mcp_servers=[],
        bundled_cli="/sdk/_bundled/claude",
    )
    checks = run_doctor(env, cwd=Path("/tmp"))  # type: ignore[arg-type]
    cli_check = next(c for c in checks if c.name == "claude-cli")
    assert cli_check.passed is True
    assert "bundled" in cli_check.detail
    assert "/sdk/_bundled/claude" in cli_check.detail
    assert env.version_asked == ["/sdk/_bundled/claude"]


def test_run_doctor_checks_the_bundled_cli_before_path_like_the_sdk() -> None:
    """The SDK launches its bundled CLI even when another `claude` is on PATH,
    so that is the one whose version matters."""
    env = _FakeDoctorEnv(
        cli_path="/usr/local/bin/claude",
        version="2.1.259",
        authed=True,
        mcp_servers=[],
        bundled_cli="/sdk/_bundled/claude",
    )
    checks = run_doctor(env, cwd=Path("/tmp"))  # type: ignore[arg-type]
    cli_check = next(c for c in checks if c.name == "claude-cli")
    assert "what a run launches" in cli_check.detail
    assert env.version_asked == ["/sdk/_bundled/claude"]


def test_run_doctor_prefers_a_profile_cli_path() -> None:
    env = _FakeDoctorEnv(cli_path="/usr/bin/claude", version="2.1.0", authed=True, mcp_servers=[])
    profile = BackendProfile(cli_path="/opt/claude/bin/claude")
    checks = run_doctor(env, cwd=Path("/tmp"), backend=profile)  # type: ignore[arg-type]
    cli_check = next(c for c in checks if c.name == "claude-cli")
    assert cli_check.passed is True
    assert cli_check.detail == "profile cli_path /opt/claude/bin/claude (2.1.0)"
    assert env.version_asked == ["/opt/claude/bin/claude"]


def test_run_doctor_fails_a_profile_cli_path_that_does_not_answer() -> None:
    env = _FakeDoctorEnv(cli_path="/usr/bin/claude", version=None, authed=True, mcp_servers=[])
    profile = BackendProfile(cli_path="/opt/claude/bin/claude")
    checks = run_doctor(env, cwd=Path("/tmp"), backend=profile)  # type: ignore[arg-type]
    cli_check = next(c for c in checks if c.name == "claude-cli")
    assert cli_check.passed is False
    assert "did not answer" in cli_check.detail


def test_run_doctor_keeps_anthropic_authentication_for_the_default_profile() -> None:
    env = _FakeDoctorEnv(cli_path="/usr/bin/claude", version="1.0", authed=True, mcp_servers=[])
    checks = run_doctor(env, cwd=Path("/tmp"), backend=BackendProfile())  # type: ignore[arg-type]
    names = [c.name for c in checks]
    assert "authentication" in names
    assert "backend" not in names
    assert env.probed == []


_LOCAL = BackendProfile(
    name="local",
    base_url="http://127.0.0.1:11434",
    model_low="qwen2.5-coder:14b",
    model_medium="qwen2.5-coder:14b",
    model_high="qwen2.5-coder:32b",
)


def _local_checks(
    status: BackendStatus,
    *,
    token: str | None = "ollama",
    tool_calls: dict[str, ToolCallStatus] | None = None,
) -> dict[str, DoctorCheck]:
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=False,
        mcp_servers=[],
        backend_status=status,
        tool_calls=tool_calls,
    )
    checks = run_doctor(env, cwd=Path("/tmp"), backend=_LOCAL, auth_token=token)  # type: ignore[arg-type]
    return {c.name: c for c in checks}


def test_run_doctor_local_profile_replaces_anthropic_auth_with_backend_checks() -> None:
    """ANTHROPIC_AUTH_TOKEN being set used to be enough to pass; for a local
    backend what matters is that it answers and has the models."""
    by_name = _local_checks(
        BackendStatus(
            reachable=True,
            detail="answered",
            models=("qwen2.5-coder:14b", "qwen2.5-coder:32b"),
        )
    )
    assert "authentication" not in by_name
    assert by_name["backend-auth"].passed is True
    assert "auth_token" in by_name["backend-auth"].detail
    assert by_name["backend"].passed is True
    assert by_name["backend-models"].passed is True
    assert "all present" in by_name["backend-models"].detail
    assert by_name["backend-tools"].passed is True
    assert "qwen2.5-coder:14b, qwen2.5-coder:32b" in by_name["backend-tools"].detail


def test_run_doctor_local_profile_names_missing_models_and_how_to_pull_them() -> None:
    by_name = _local_checks(
        BackendStatus(reachable=True, detail="answered", models=("qwen2.5-coder:14b",))
    )
    models = by_name["backend-models"]
    assert models.passed is False
    assert "qwen2.5-coder:32b" in models.detail
    assert "ollama pull qwen2.5-coder:32b" in models.detail


def test_run_doctor_local_profile_accepts_an_implicit_latest_tag() -> None:
    profile = BackendProfile(
        name="local",
        base_url="http://127.0.0.1:11434",
        model_low="llama3",
        model_medium="llama3",
        model_high="llama3",
    )
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=False,
        mcp_servers=[],
        backend_status=BackendStatus(reachable=True, detail="ok", models=("llama3:latest",)),
    )
    checks = run_doctor(env, cwd=Path("/tmp"), backend=profile, auth_token="ollama")  # type: ignore[arg-type]
    assert next(c for c in checks if c.name == "backend-models").passed is True


def test_run_doctor_local_profile_unreachable_backend() -> None:
    by_name = _local_checks(BackendStatus(reachable=False, detail="cannot reach it"))
    assert by_name["backend"].passed is False
    assert "cannot reach it" in by_name["backend"].detail
    assert by_name["backend-models"].passed is False
    assert "not answering" in by_name["backend-models"].detail


def test_run_doctor_local_profile_unverifiable_model_listing_is_not_a_failure() -> None:
    by_name = _local_checks(BackendStatus(reachable=True, detail="answered", models=None))
    models = by_name["backend-models"]
    assert models.passed is True
    assert "verify by hand" in models.detail


def test_run_doctor_local_profile_unresolvable_token() -> None:
    profile = BackendProfile(
        name="remote",
        base_url="https://gpu.example",
        auth_token_env="GPU_TOKEN",
        model_low="m",
        model_medium="m",
        model_high="m",
    )
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=False,
        mcp_servers=[],
        backend_status=BackendStatus(reachable=True, detail="ok", models=("m",)),
    )
    checks = run_doctor(env, cwd=Path("/tmp"), backend=profile, auth_token=None)  # type: ignore[arg-type]
    auth = next(c for c in checks if c.name == "backend-auth")
    assert auth.passed is False
    assert "$GPU_TOKEN" in auth.detail
    assert env.probed == [("https://gpu.example", "")]


def test_run_doctor_local_profile_token_from_env_var() -> None:
    profile = BackendProfile(
        name="remote",
        base_url="https://gpu.example",
        auth_token_env="GPU_TOKEN",
        model_low="m",
        model_medium="m",
        model_high="m",
    )
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=False,
        mcp_servers=[],
        backend_status=BackendStatus(reachable=True, detail="ok", models=("m",)),
    )
    checks = run_doctor(env, cwd=Path("/tmp"), backend=profile, auth_token="s3cret")  # type: ignore[arg-type]
    auth = next(c for c in checks if c.name == "backend-auth")
    assert auth.passed is True
    assert "$GPU_TOKEN" in auth.detail
    assert env.probed == [("https://gpu.example", "s3cret")]


def test_run_doctor_flags_mcp_servers_as_needing_manual_verification(tmp_path: Path) -> None:
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=True,
        mcp_servers=["server-a", "server-b"],
    )
    checks = run_doctor(env, cwd=tmp_path)  # type: ignore[arg-type]
    mcp_check = next(c for c in checks if c.name == "mcp-servers")
    assert mcp_check.passed is False
    assert "server-a" in mcp_check.detail
    assert all_passed(checks) is False


def test_run_doctor_flags_non_git_working_directory(tmp_path: Path) -> None:
    env = _FakeDoctorEnv(cli_path="/usr/bin/claude", version="1.0", authed=True, mcp_servers=[])
    checks = run_doctor(env, cwd=tmp_path)  # type: ignore[arg-type]
    wd_check = next(c for c in checks if c.name == "working-directory")
    assert wd_check.passed is False


def test_run_doctor_reports_missing_api_surface_verification(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=True,
        mcp_servers=[],
        api_count=None,
    )
    checks = run_doctor(env, cwd=tmp_path)  # type: ignore[arg-type]
    api_check = next(c for c in checks if c.name == "api-surface")
    assert api_check.passed is False
    assert "baseline" in api_check.detail


def test_doctor_check_is_a_plain_value_object() -> None:
    check = DoctorCheck(name="x", passed=True, detail="ok")
    assert check.name == "x"
    assert check.passed is True


def test_all_passed_empty_list_is_true() -> None:
    assert all_passed([]) is True


class _FakeInbox:
    def __init__(self) -> None:
        self.commands: list[object] = []

    def enqueue(self, command: object) -> object:
        self.commands.append(command)
        return command


def test_request_wind_down_enqueues_the_command_with_its_reason() -> None:
    inbox = _FakeInbox()
    result = request_wind_down(inbox, reason="rotate", run_id="run-1")
    assert result.run_id == "run-1"
    assert result.command_type == "wind_down"
    assert inbox.commands == [WindDownCommand(reason="rotate")]


_BOTH = BackendStatus(
    reachable=True, detail="answered", models=("qwen2.5-coder:14b", "qwen2.5-coder:32b")
)


def test_run_doctor_fails_a_model_that_writes_tool_calls_as_text() -> None:
    """Captured live: qwen2.5-coder:14b on Ollama 0.34.2 answers a tools request
    with the call written out as JSON text — Claude Code can do nothing with it."""
    by_name = _local_checks(
        _BOTH,
        tool_calls={
            "qwen2.5-coder:14b": ToolCallStatus(
                supported=False, detail="wrote its tool call as text instead of calling it"
            ),
            "qwen2.5-coder:32b": ToolCallStatus(supported=None, detail="answered HTTP 400"),
        },
    )
    tools = by_name["backend-tools"]
    assert tools.passed is False
    assert "qwen2.5-coder:14b: wrote its tool call as text" in tools.detail
    assert "qwen2.5-coder:32b: answered HTTP 400" in tools.detail


def test_run_doctor_asks_each_distinct_tier_once() -> None:
    env = _FakeDoctorEnv(
        cli_path="/usr/bin/claude",
        version="1.0",
        authed=False,
        mcp_servers=[],
        backend_status=_BOTH,
    )
    run_doctor(env, cwd=Path("/tmp"), backend=_LOCAL, auth_token="ollama")  # type: ignore[arg-type]
    assert env.tool_probed == ["qwen2.5-coder:14b", "qwen2.5-coder:32b"]


def test_run_doctor_skips_the_tool_check_until_the_models_are_there() -> None:
    by_name = _local_checks(BackendStatus(reachable=True, detail="answered", models=()))
    tools = by_name["backend-tools"]
    assert tools.passed is False
    assert tools.detail.startswith("not checked")
