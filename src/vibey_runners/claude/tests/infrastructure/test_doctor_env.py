# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for infrastructure/doctor_env.py — RealDoctorEnvironment adapter."""

from __future__ import annotations

import json
import subprocess
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claudeloop.infrastructure.doctor_env import RealDoctorEnvironment


def test_find_claude_cli_when_not_in_path() -> None:
    """find_claude_cli returns None when claude is not in PATH."""
    env = RealDoctorEnvironment()
    with patch("shutil.which", return_value=None):
        assert env.find_claude_cli() is None


def test_find_claude_cli_when_in_path() -> None:
    """find_claude_cli returns path when claude is in PATH."""
    env = RealDoctorEnvironment()
    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        assert env.find_claude_cli() == "/usr/local/bin/claude"


def test_claude_cli_version_success() -> None:
    """claude_cli_version returns version string when command succeeds."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "claude 1.2.3\n"
    with patch("subprocess.run", return_value=mock_result):
        version = env.claude_cli_version("/path/to/claude")
        assert version == "claude 1.2.3"


def test_claude_cli_version_non_zero_exit() -> None:
    """claude_cli_version returns None when command exits non-zero."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        assert env.claude_cli_version("/path/to/claude") is None


def test_claude_cli_version_timeout() -> None:
    """claude_cli_version returns None on timeout."""
    env = RealDoctorEnvironment()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 10)):
        assert env.claude_cli_version("/path/to/claude") is None


def test_claude_cli_version_oserror() -> None:
    """claude_cli_version returns None on OSError."""
    env = RealDoctorEnvironment()
    with patch("subprocess.run", side_effect=OSError("Command not found")):
        assert env.claude_cli_version("/path/to/claude") is None


def test_claude_cli_version_empty_output() -> None:
    """claude_cli_version returns None when output is empty."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        assert env.claude_cli_version("/path/to/claude") is None


def test_is_authenticated_via_api_key(monkeypatch) -> None:
    """is_authenticated returns True when ANTHROPIC_API_KEY is set."""
    env = RealDoctorEnvironment()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    assert env.is_authenticated() is True


def test_is_authenticated_via_auth_token(monkeypatch) -> None:
    """is_authenticated returns True when ANTHROPIC_AUTH_TOKEN is set."""
    env = RealDoctorEnvironment()
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-token")
    assert env.is_authenticated() is True


def test_is_authenticated_via_claude_auth_status(monkeypatch) -> None:
    """is_authenticated checks claude auth status when no env vars set."""
    env = RealDoctorEnvironment()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"loggedIn": True})

    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert env.is_authenticated() is True


def test_is_authenticated_via_credentials_file(tmp_path: Path, monkeypatch) -> None:
    """is_authenticated checks .claude/.credentials.json as fallback."""
    env = RealDoctorEnvironment()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    # Create fake credentials file
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir()
    creds_file = claude_dir / ".credentials.json"
    creds_file.write_text("{}", encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch.object(env, "find_claude_cli", return_value=None),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
    ):
        assert env.is_authenticated() is True


def test_is_authenticated_false_when_nothing_found(tmp_path: Path, monkeypatch) -> None:
    """is_authenticated returns False when no auth method found."""
    env = RealDoctorEnvironment()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    fake_home = tmp_path / "home"
    fake_home.mkdir()

    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch.object(env, "find_claude_cli", return_value=None),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
    ):
        assert env.is_authenticated() is False


def test_is_authenticated_claude_auth_not_logged_in(monkeypatch) -> None:
    """is_authenticated handles claude auth status returning loggedIn: false."""
    env = RealDoctorEnvironment()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({"loggedIn": False})

    fake_home = Path("/nonexistent")
    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert env.is_authenticated() is False


def test_is_authenticated_claude_auth_invalid_json(monkeypatch) -> None:
    """is_authenticated handles invalid JSON from claude auth status."""
    env = RealDoctorEnvironment()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "not json"

    fake_home = Path("/nonexistent")
    with (
        patch("pathlib.Path.home", return_value=fake_home),
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert env.is_authenticated() is False


def test_configured_mcp_servers_no_claude_cli() -> None:
    """configured_mcp_servers returns empty list when claude CLI not found."""
    env = RealDoctorEnvironment()
    with (
        patch.object(env, "find_claude_cli", return_value=None),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
    ):
        assert env.configured_mcp_servers() == []


def test_configured_mcp_servers_command_fails() -> None:
    """configured_mcp_servers returns empty list when mcp list fails."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 1

    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        assert env.configured_mcp_servers() == []


def test_configured_mcp_servers_timeout() -> None:
    """configured_mcp_servers returns empty list on timeout."""
    env = RealDoctorEnvironment()
    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 60)),
    ):
        assert env.configured_mcp_servers() == []


def test_configured_mcp_servers_oserror() -> None:
    """configured_mcp_servers returns empty list on OSError."""
    env = RealDoctorEnvironment()
    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", side_effect=OSError("Command failed")),
    ):
        assert env.configured_mcp_servers() == []


def test_configured_mcp_servers_success() -> None:
    """configured_mcp_servers parses server names from colon-delimited output."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "server1: connected\nserver2: connected\nserver3: error\n"

    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        servers = env.configured_mcp_servers()
        assert "server1" in servers
        assert "server2" in servers
        assert "server3" in servers


def test_configured_mcp_servers_skips_blank_and_no_colon_lines() -> None:
    """configured_mcp_servers skips blank lines and lines without colons."""
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "server1: ok\n\nno-colon-line\nserver2: ok\n"

    with (
        patch.object(env, "find_claude_cli", return_value="/usr/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value=None),
        patch("subprocess.run", return_value=mock_result),
    ):
        servers = env.configured_mcp_servers()
        assert servers == ["server1", "server2"]


def test_anthropic_sdk_version_returns_version() -> None:
    """anthropic_sdk_version returns the anthropic module version."""
    env = RealDoctorEnvironment()
    result = env.anthropic_sdk_version()
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_api_surface_method_count_returns_int() -> None:
    """api_surface_method_count returns an integer count."""
    env = RealDoctorEnvironment()
    count = env.api_surface_method_count()
    assert count is None or isinstance(count, int)


def test_anthropic_sdk_version_import_error() -> None:
    """anthropic_sdk_version returns None when anthropic module cannot be imported."""
    import sys
    from unittest.mock import patch

    env = RealDoctorEnvironment()
    # Mock the import to raise ImportError
    with (
        patch.dict(sys.modules, {"anthropic": None}),
        patch("builtins.__import__", side_effect=ImportError("no module")),
    ):
        result = env.anthropic_sdk_version()
        assert result is None


def test_api_surface_method_count_import_error() -> None:
    """api_surface_method_count returns None when introspect module cannot be imported."""
    import sys
    from unittest.mock import patch

    env = RealDoctorEnvironment()
    # Mock sys.modules to make introspect unavailable
    with patch.dict(sys.modules, {"claudeloop.infrastructure.api.introspect": None}):
        result = env.api_surface_method_count()
        assert result is None


# --- bundled CLI fallback (issue #121, S1b) ---


def test_find_bundled_claude_cli_finds_the_sdk_copy(tmp_path: Path) -> None:
    bundled = tmp_path / "_bundled"
    bundled.mkdir()
    (bundled / "claude").write_text("#!/bin/sh\n")
    env = RealDoctorEnvironment(sdk_package_dir=tmp_path)
    with patch("claudeloop.infrastructure.doctor_env.platform.system", return_value="Linux"):
        assert env.find_bundled_claude_cli() == str(bundled / "claude")


def test_find_bundled_claude_cli_uses_the_windows_name(tmp_path: Path) -> None:
    bundled = tmp_path / "_bundled"
    bundled.mkdir()
    (bundled / "claude.exe").write_text("MZ")
    env = RealDoctorEnvironment(sdk_package_dir=tmp_path)
    with patch("claudeloop.infrastructure.doctor_env.platform.system", return_value="Windows"):
        assert env.find_bundled_claude_cli() == str(bundled / "claude.exe")


def test_find_bundled_claude_cli_none_when_the_sdk_bundles_nothing(tmp_path: Path) -> None:
    assert RealDoctorEnvironment(sdk_package_dir=tmp_path).find_bundled_claude_cli() is None


def test_default_sdk_dir_is_the_installed_claude_agent_sdk() -> None:
    import claude_agent_sdk

    env = RealDoctorEnvironment()
    assert env._sdk_package_dir == Path(claude_agent_sdk.__file__).parent


def test_mcp_listing_falls_back_to_the_bundled_cli_when_claude_is_not_on_path() -> None:
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "github: npx github-mcp - ✓ Connected\n"
    with (
        patch.object(env, "find_claude_cli", return_value=None),
        patch.object(env, "find_bundled_claude_cli", return_value="/sdk/_bundled/claude"),
        patch("subprocess.run", return_value=mock_result) as run,
    ):
        assert env.configured_mcp_servers() == ["github"]
    assert run.call_args.args[0][0] == "/sdk/_bundled/claude"


# --- probe_backend ---


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _opener(responses: dict[str, object]):  # type: ignore[no-untyped-def]
    seen: list[tuple[str, dict[str, str], float]] = []

    def _open(request, timeout):  # type: ignore[no-untyped-def]
        seen.append((request.full_url, dict(request.header_items()), timeout))
        outcome = responses[request.full_url]
        if isinstance(outcome, BaseException):
            raise outcome
        return _Response(outcome)  # type: ignore[arg-type]

    return _open, seen


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "nope", {}, None)  # type: ignore[arg-type]


def test_probe_backend_lists_models_from_the_openai_style_listing() -> None:
    body = json.dumps(
        {"object": "list", "data": [{"id": "qwen2.5-coder:14b"}, {"id": "qwen2.5-coder:1.5b"}]}
    ).encode()
    opener, seen = _opener({"http://127.0.0.1:11434/v1/models": body})
    env = RealDoctorEnvironment(opener=opener, backend_probe_timeout=2.5)
    status = env.probe_backend("http://127.0.0.1:11434/", "ollama")
    assert status.reachable is True
    assert status.models == ("qwen2.5-coder:14b", "qwen2.5-coder:1.5b")
    assert "2 model(s)" in status.detail
    url, headers, timeout = seen[0]
    assert timeout == 2.5
    assert headers["X-api-key"] == "ollama"
    assert headers["Authorization"] == "Bearer ollama"


def test_probe_backend_falls_back_to_ollamas_native_listing() -> None:
    body = json.dumps({"models": [{"name": "llama3:latest"}, {"size": 1}]}).encode()
    opener, _seen = _opener(
        {
            "http://h/v1/models": _http_error("http://h/v1/models", 404),
            "http://h/api/tags": body,
        }
    )
    status = RealDoctorEnvironment(opener=opener).probe_backend("http://h", "t")
    assert status.reachable is True
    assert status.models == ("llama3:latest",)


def test_probe_backend_answering_without_a_listing_is_reachable_but_unverified() -> None:
    opener, _seen = _opener(
        {
            "http://h/v1/models": b"<html>hello</html>",
            "http://h/api/tags": _http_error("http://h/api/tags", 401),
        }
    )
    status = RealDoctorEnvironment(opener=opener).probe_backend("http://h", "t")
    assert status.reachable is True
    assert status.models is None
    assert "HTTP 401" in status.detail


def test_probe_backend_non_list_json_is_not_a_listing() -> None:
    opener, _seen = _opener(
        {"http://h/v1/models": b'{"data": "x"}', "http://h/api/tags": b"[1, 2]"}
    )
    status = RealDoctorEnvironment(opener=opener).probe_backend("http://h", "t")
    assert status.reachable is True
    assert status.models is None
    assert "not with a model list" in status.detail


def test_probe_backend_unreachable() -> None:
    refused = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
    opener, _seen = _opener({"http://127.0.0.1:1/v1/models": refused})
    status = RealDoctorEnvironment(opener=opener).probe_backend("http://127.0.0.1:1", "t")
    assert status.reachable is False
    assert "cannot reach http://127.0.0.1:1" in status.detail
    assert "Connection refused" in status.detail


def test_probe_backend_timeout_is_unreachable() -> None:
    opener, _seen = _opener({"http://h/v1/models": TimeoutError()})
    status = RealDoctorEnvironment(opener=opener).probe_backend("http://h", "t")
    assert status.reachable is False
    assert status.detail == "cannot reach http://h: TimeoutError"


def test_mcp_listing_uses_the_bundled_cli_before_path_like_the_sdk() -> None:
    env = RealDoctorEnvironment()
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    with (
        patch.object(env, "find_claude_cli", return_value="/usr/local/bin/claude"),
        patch.object(env, "find_bundled_claude_cli", return_value="/sdk/_bundled/claude"),
        patch("subprocess.run", return_value=mock_result) as run,
    ):
        assert env.configured_mcp_servers() == []
    assert run.call_args.args[0][0] == "/sdk/_bundled/claude"


# --- probe_tool_calling ---


def _tool_env(outcome: object, **kwargs: object):  # type: ignore[no-untyped-def]
    opener, seen = _opener({"http://h/v1/messages": outcome})
    return RealDoctorEnvironment(opener=opener, **kwargs), seen  # type: ignore[arg-type]


def test_tool_probe_recognises_a_real_tool_call() -> None:
    body = json.dumps(
        {"content": [{"type": "tool_use", "name": "record_answer", "input": {"answer": 42}}]}
    ).encode()
    env, seen = _tool_env(body, tool_probe_timeout=33.0)
    status = env.probe_tool_calling("http://h/", "tok", "qwen3:32b")
    assert status.supported is True
    url, headers, timeout = seen[0]
    assert url == "http://h/v1/messages"
    assert timeout == 33.0
    assert headers["Content-type"] == "application/json"
    assert headers["X-api-key"] == "tok"


def test_tool_probe_sends_one_trivial_tool_and_names_the_model() -> None:
    captured: list[object] = []

    def _open(request, timeout):  # type: ignore[no-untyped-def]
        captured.append(request)
        return _Response(b'{"content": [{"type": "tool_use"}]}')

    RealDoctorEnvironment(opener=_open).probe_tool_calling("http://h", "t", "m1")
    request = captured[0]
    assert request.get_method() == "POST"  # type: ignore[attr-defined]
    payload = json.loads(request.data)  # type: ignore[attr-defined]
    assert payload["model"] == "m1"
    assert [tool["name"] for tool in payload["tools"]] == ["record_answer"]


def test_tool_probe_flags_a_tool_call_written_as_text() -> None:
    """The live shape from qwen2.5-coder:14b on Ollama 0.34.2."""
    body = json.dumps(
        {
            "content": [
                {"type": "text", "text": '{"name": "Write", "arguments": {"content": "hi"}}'}
            ],
            "stop_reason": "end_turn",
        }
    ).encode()
    env, _seen = _tool_env(body)
    status = env.probe_tool_calling("http://h", "t", "qwen2.5-coder:14b")
    assert status.supported is False
    assert "wrote its tool call as text" in status.detail
    assert '"name": "Write"' in status.detail


@pytest.mark.parametrize(
    ("outcome", "detail"),
    [
        (_http_error("http://h/v1/messages", 400), "answered HTTP 400"),
        (urllib.error.URLError(ConnectionRefusedError(61, "refused")), "no answer from"),
        (TimeoutError(), "TimeoutError"),
        (b"<html>", "not with JSON"),
        (b'{"content": "x"}', "without a content list"),
        (b"[]", "without a content list"),
    ],
)
def test_tool_probe_cannot_tell(outcome: object, detail: str) -> None:
    env, _seen = _tool_env(outcome)
    status = env.probe_tool_calling("http://h", "t", "m")
    assert status.supported is None
    assert detail in status.detail
