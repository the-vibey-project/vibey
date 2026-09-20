# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

from pathlib import Path

from claudeloop.infrastructure.agent.autonomy import AUTONOMY_SYSTEM_PROMPT_FRAGMENT
from claudeloop.infrastructure.agent.options import (
    DEFAULT_MAX_BUFFER_SIZE,
    build_turn_options,
)
from claudeloop.infrastructure.state_bus import FileStateBus


def test_default_max_buffer_size_exceeds_sdk_1mb_floor() -> None:
    options = build_turn_options(cwd="/tmp")
    assert options.max_buffer_size == DEFAULT_MAX_BUFFER_SIZE
    assert DEFAULT_MAX_BUFFER_SIZE > 1024 * 1024


def test_max_buffer_size_override() -> None:
    options = build_turn_options(cwd="/tmp", max_buffer_size=2 * 1024 * 1024)
    assert options.max_buffer_size == 2 * 1024 * 1024


def test_effort_and_partial_messages_wired() -> None:
    options = build_turn_options(
        cwd="/tmp",
        model="claude-sonnet-4-5",
        effort="medium",
        include_partial_messages=True,
    )
    assert options.model == "claude-sonnet-4-5"
    assert options.effort == "medium"
    assert options.include_partial_messages is True


def test_autonomy_prompt_warns_blocked_on_is_terminal() -> None:
    text = AUTONOMY_SYSTEM_PROMPT_FRAGMENT.lower()
    assert "blocked_on" in text
    assert "remaining_work" in text
    assert "null" in text


def test_resume_drops_session_id_without_fork() -> None:
    """Claude Code rejects --session-id with --resume unless --fork-session.

    claudeloop resume historically passed both (bookkeeping + SDK resume);
    only resume must reach ClaudeAgentOptions.
    """
    sid = "963044a8-322c-4655-b993-9c344e6ea82e"
    options = build_turn_options(cwd="/tmp", session_id=sid, resume=sid)
    assert options.resume == sid
    assert options.session_id is None
    assert options.continue_conversation is False
    assert options.fork_session is False


def test_continue_conversation_drops_session_id_without_fork() -> None:
    sid = "963044a8-322c-4655-b993-9c344e6ea82e"
    options = build_turn_options(cwd="/tmp", session_id=sid, continue_conversation=True)
    assert options.continue_conversation is True
    assert options.session_id is None
    assert options.resume is None


def test_fresh_session_may_pin_session_id() -> None:
    sid = "963044a8-322c-4655-b993-9c344e6ea82e"
    options = build_turn_options(cwd="/tmp", session_id=sid)
    assert options.session_id == sid
    assert options.resume is None
    assert options.continue_conversation is False


def test_file_state_bus_publish_and_status(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    bus = tmp_path / "bus.jsonl"
    publisher = FileStateBus(status_path=status, bus_path=bus, run_id="r1")
    publisher.publish("phase.running", {"phase": "RUNNING", "attempt": 1, "status": "active"})
    assert status.is_file()
    text = status.read_text(encoding="utf-8")
    assert "RUNNING" in text
    assert "r1" in bus.read_text(encoding="utf-8")


def test_file_state_bus_when_bus_already_exists(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    bus = tmp_path / "bus.jsonl"
    bus.write_text("existing content\n", encoding="utf-8")
    publisher = FileStateBus(status_path=status, bus_path=bus, run_id="r2")
    publisher.publish("test.event", {"data": "value"})
    content = bus.read_text(encoding="utf-8")
    assert "existing content" in content
    assert "value" in content


def test_file_state_bus_atomic_write_cleanup_on_error(tmp_path: Path) -> None:
    import contextlib
    from unittest.mock import patch

    status = tmp_path / "status.json"
    bus = tmp_path / "bus.jsonl"
    publisher = FileStateBus(status_path=status, bus_path=bus, run_id="r3")

    # Force os.replace to fail to trigger the exception handler
    with (
        patch("os.replace", side_effect=OSError("simulated replace failure")),
        contextlib.suppress(OSError),
    ):
        publisher.publish("test", {"data": "x"})

    # Verify no .status-* temp files are left behind
    temp_files = list(tmp_path.glob(".status-*"))
    assert len(temp_files) == 0


def test_build_turn_options_with_retry_watchdog() -> None:
    from claudeloop.infrastructure.agent.options import build_turn_options

    opts = build_turn_options(
        cwd="/tmp",
        retry_watchdog=True,
    )
    assert "CLAUDE_CODE_RETRY_WATCHDOG" in opts.env


def test_system_prompt_append_is_merged_after_autonomy_fragment() -> None:
    """A non-blank system_prompt_append is joined onto the autonomy fragment,
    not silently dropped."""
    options = build_turn_options(cwd="/tmp", system_prompt_append="extra house rules")
    append = options.system_prompt["append"]
    assert AUTONOMY_SYSTEM_PROMPT_FRAGMENT in append
    assert "extra house rules" in append


def test_blank_system_prompt_append_is_not_merged() -> None:
    """Whitespace-only append leaves the base fragment untouched (the
    ``.strip()`` guard on the truthiness check)."""
    options = build_turn_options(cwd="/tmp", system_prompt_append="   ")
    assert options.system_prompt["append"] == AUTONOMY_SYSTEM_PROMPT_FRAGMENT


def test_marketplace_style_plugin_name_becomes_local_config() -> None:
    """A plugin name with no path markers (no leading '/', '.', or an
    embedded '/') still resolves to a local SdkPluginConfig — same shape as
    a path-like plugin, just reached via the other branch."""
    options = build_turn_options(cwd="/tmp", plugins=["marketplace-plugin"])
    assert options.plugins == [{"type": "local", "path": "marketplace-plugin"}]


def test_allowed_tools_are_wired_into_options() -> None:
    options = build_turn_options(cwd="/tmp", allowed_tools=["Bash", "Read"])
    assert options.allowed_tools == ["Bash", "Read"]


def test_empty_allowed_tools_are_not_wired_into_options() -> None:
    options = build_turn_options(cwd="/tmp", allowed_tools=[])
    assert options.allowed_tools == []


def test_probe_options_without_model_omits_model_kwarg() -> None:
    from claudeloop.infrastructure.agent.options import build_probe_options

    options = build_probe_options(cwd="/tmp")
    assert options.model is None


# --- backend overlay: applied to the turn AND the probe ---

_LOCAL_ENV = {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:11434",
    "ANTHROPIC_AUTH_TOKEN": "ollama",
    "ANTHROPIC_API_KEY": "",
}


def test_turn_options_merge_the_backend_overlay_over_the_defaults() -> None:
    options = build_turn_options(
        cwd="/tmp",
        retry_watchdog=True,
        env={**_LOCAL_ENV, "CLAUDE_CODE_MAX_RETRIES": "2"},
    )
    assert options.env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:11434"
    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.env["CLAUDE_CODE_RETRY_WATCHDOG"] == "1"
    # The overlay is applied last, so a profile can retune a default.
    assert options.env["CLAUDE_CODE_MAX_RETRIES"] == "2"


def test_turn_options_without_an_overlay_keep_the_anthropic_defaults() -> None:
    options = build_turn_options(cwd="/tmp")
    assert options.env == {"CLAUDE_CODE_MAX_RETRIES": "10"}
    assert options.cli_path is None


def test_turn_options_carry_a_profile_cli_path() -> None:
    assert build_turn_options(cwd="/tmp", cli_path="/opt/claude").cli_path == "/opt/claude"


def test_probe_options_carry_the_same_backend() -> None:
    """Without the overlay a probe would re-check capacity on Anthropic while the
    run itself talks to a local server."""
    from claudeloop.infrastructure.agent.options import build_probe_options

    options = build_probe_options(cwd="/tmp", env=_LOCAL_ENV, cli_path="/opt/claude")
    assert options.env == _LOCAL_ENV
    assert options.cli_path == "/opt/claude"


def test_probe_options_without_an_overlay_set_no_env() -> None:
    from claudeloop.infrastructure.agent.options import build_probe_options

    options = build_probe_options(cwd="/tmp")
    assert options.env == {}
    assert options.cli_path is None
