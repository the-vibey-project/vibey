# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qwenloop.application.runner import (
    _EMPTY_REPLY_PROMPT,
    AutonomousRunner,
    _has_cdd_evidence,
    _render_native_verdict,
    _system_prompt,
    _trim_transcript,
    _truncate_tool_result,
)
from qwenloop.domain.config import QwenConfig
from qwenloop.domain.model import (
    Backend,
    ChatChunk,
    ChatMessage,
    RunStatus,
    ServerInfo,
    ToolCallParseError,
)
from qwenloop.infrastructure.profiles import PORTABLE
from qwenloop.infrastructure.run_store import FileRunStore
from qwenloop.infrastructure.tools import SandboxTools


class FakeClock:
    """An in-memory clock: wall time from a fixed instant, monotonic time that advances a
    fixed step on every read, so a turn's timings are exact and assertable."""

    def __init__(self, step: float = 0.25) -> None:
        self.step = step
        self.elapsed = 0.0

    def now(self) -> datetime:
        return datetime(2026, 9, 22, 12, 0, tzinfo=UTC) + timedelta(seconds=self.elapsed)

    def monotonic(self) -> float:
        self.elapsed += self.step
        return self.elapsed


class FakeServer:
    chunks: list[ChatChunk] | None = None

    def inspect(self, profile):  # type: ignore[no-untyped-def]
        return None

    async def install(self, profile):  # type: ignore[no-untyped-def]
        raise AssertionError

    async def start(self, profile):  # type: ignore[no-untyped-def]
        raise AssertionError

    async def health(self, info):  # type: ignore[no-untyped-def]
        return True

    async def stop(self, info):  # type: ignore[no-untyped-def]
        return None

    async def chat_stream(
        self, info: ServerInfo, messages: Sequence[ChatMessage]
    ) -> AsyncIterator[ChatChunk]:
        del info, messages
        chunks = self.chunks or [
            ChatChunk(
                tool_call={
                    "name": "write_file",
                    "arguments": {"path": "done.txt", "content": "ok"},
                }
            ),
            ChatChunk(
                text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE",
                output_tokens=4,
            ),
        ]
        for chunk in chunks:
            yield chunk


def test_truncate_tool_result_leaves_short_text_untouched() -> None:
    assert _truncate_tool_result("short") == "short"


def test_truncate_tool_result_truncates_long_text() -> None:
    text = "x" * 8_010
    result = _truncate_tool_result(text, limit=8_000)
    assert result.startswith("x" * 8_000)
    assert result.endswith("...[truncated 10 characters]")


def test_trim_transcript_noop_within_budget() -> None:
    transcript = [ChatMessage("system", "sys"), ChatMessage("user", "plan")]
    assert _trim_transcript(transcript, context_window=32_768) is transcript


def test_trim_transcript_never_drops_head_even_over_budget() -> None:
    transcript = [ChatMessage("system", "sys"), ChatMessage("user", "plan")]
    assert _trim_transcript(transcript, context_window=1) is transcript


def test_trim_transcript_drops_oldest_tail_and_marks_it() -> None:
    transcript = [
        ChatMessage("system", "sys"),
        ChatMessage("user", "plan"),
        ChatMessage("tool", "a" * 400),  # 100 estimated tokens, dropped first
        ChatMessage("tool", "b" * 400),  # 100 estimated tokens, dropped second
        ChatMessage("tool", "c" * 4),  # 1 estimated token, kept
    ]
    trimmed = _trim_transcript(transcript, context_window=100)
    assert trimmed[0] == transcript[0]
    assert trimmed[1] == transcript[1]
    assert trimmed[2].role == "system"
    assert "2 earlier turn(s) omitted to fit the 100-token context window" in trimmed[2].content
    assert trimmed[3] == transcript[4]
    assert len(trimmed) == 4


class ScriptedServer:
    """A FakeServer variant that yields a different, pre-scripted turn each call."""

    def __init__(self, turns: list[list[ChatChunk]]) -> None:
        self._turns = turns
        self.seen: list[list[ChatMessage]] = []

    def inspect(self, profile):  # type: ignore[no-untyped-def]
        return None

    async def install(self, profile):  # type: ignore[no-untyped-def]
        raise AssertionError

    async def start(self, profile):  # type: ignore[no-untyped-def]
        raise AssertionError

    async def health(self, info):  # type: ignore[no-untyped-def]
        return True

    async def stop(self, info):  # type: ignore[no-untyped-def]
        return None

    async def chat_stream(
        self, info: ServerInfo, messages: Sequence[ChatMessage]
    ) -> AsyncIterator[ChatChunk]:
        del info
        self.seen.append(list(messages))
        for chunk in self._turns[len(self.seen) - 1]:
            yield chunk


class RecordingNotifier:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    async def notify(self, title: str, message: str) -> bool:
        self.calls.append((title, message))
        if self.fail:
            raise RuntimeError("desktop notification unavailable")
        return True


@pytest.mark.asyncio
async def test_runner_inserts_continue_prompt_after_assistant_only_turn(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(text="thinking out loud")],  # no tool call: ends on "assistant"
            [
                ChatChunk(
                    tool_call={"name": "write_file", "arguments": {"path": "x", "content": "y"}}
                )
            ],
            [
                ChatChunk(
                    text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE",
                    output_tokens=4,
                )
            ],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="nudge", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=3
    )
    assert result.status is RunStatus.COMPLETED
    # a bare-text turn must never leave two assistant messages back to back for the next request
    assert [message.role for message in server.seen[1][-2:]] == ["assistant", "user"]
    # a tool-only turn already ends on "tool", so no continuation prompt is needed or added
    assert server.seen[2][-1].role == "tool"


@pytest.mark.asyncio
async def test_runner_notifies_lifecycle_events(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")],
        ]
    )
    notifier = RecordingNotifier()
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server,
        FileRunStore(tmp_path),
        SandboxTools(tmp_path),
        notifier=notifier,
        clock=FakeClock(),
    ).run(
        run_id="notifications",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=2,
    )
    assert result.status is RunStatus.COMPLETED
    assert [title for title, _message in notifier.calls] == [
        "Qwen run started",
        "Qwen turn 1 complete",
        "Qwen turn 2 complete",
        "Qwen run completed",
    ]


@pytest.mark.asyncio
async def test_runner_ignores_notification_failures(tmp_path: Path) -> None:
    notifier = RecordingNotifier(fail=True)
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        FakeServer(),
        FileRunStore(tmp_path),
        SandboxTools(tmp_path),
        notifier=notifier,
        clock=FakeClock(),
    ).run(
        run_id="notification-failure",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=2,
    )
    assert result.status is RunStatus.COMPLETED
    assert len(notifier.calls) == 3


@pytest.mark.asyncio
async def test_runner_preserves_assistant_tool_call_context(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="tool-context",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=2,
    )
    assert result.status is RunStatus.COMPLETED
    assistant, tool = server.seen[1][-2:]
    assert assistant.role == "assistant"
    assert assistant.tool_calls[0]["function"]["name"] == "read_file"
    assert tool.role == "tool"
    assert tool.tool_call_id == assistant.tool_calls[0]["id"]


def test_system_prompt_marks_verdict_as_text_not_a_tool(tmp_path: Path) -> None:
    prompt = _system_prompt(tmp_path)
    assert "There is no qwenloop-verdict tool" in prompt
    assert "plain text in your final assistant response" in prompt


def test_cdd_evidence_requires_all_delivery_fields_inside_one_verdict() -> None:
    fields = (
        "criteria: done; tests: pass; repository: Python; "
        "levels: project/phase/epic/item; trajectory: converging; "
        "composition: atom-only; delivery: commit-ready"
    )
    assert not _has_cdd_evidence([ChatMessage("assistant", fields)])
    assert not _has_cdd_evidence(
        [ChatMessage("assistant", f"{fields}\n```qwenloop-verdict\npass\n```")]
    )
    assert _has_cdd_evidence(
        [
            ChatMessage(
                "assistant",
                f"```qwenloop-verdict\n{fields}\n```",
            )
        ]
    )


def test_native_verdict_serializes_non_string_arguments() -> None:
    rendered = _render_native_verdict({"complete": True})
    assert rendered == '```qwenloop-verdict\n{"complete": true}\n```'


@pytest.mark.asyncio
async def test_runner_normalizes_native_verdict_tool_call(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [
                ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}}),
                ChatChunk(tool_call={"name": "qwenloop-verdict", "arguments": {"verdict": "pass"}}),
                ChatChunk(text="QWENLOOP_TASK_FULLY_COMPLETE"),
            ]
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="native-verdict",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=1,
    )
    assert result.status is RunStatus.COMPLETED
    events = [
        json.loads(line)
        for line in (tmp_path / ".qwenloop" / "runs" / "native-verdict" / "events.jsonl")
        .read_text()
        .splitlines()
    ]
    assert not any(event.get("name") == "qwenloop-verdict" for event in events)
    assert any("```qwenloop-verdict" in event.get("text", "") for event in events)


@pytest.mark.asyncio
async def test_storm_cannot_complete_after_read_only_inspection(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [
                ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}}),
                ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE"),
            ]
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="storm-read-only",
        plan="# qwenstorm plan\nwork it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=1,
    )
    assert result.status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_storm_can_complete_after_repo_action(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "shell", "arguments": {"argv": ["true"]}})],
            [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="storm-progress",
        plan="# qwenstorm plan\nwork it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=2,
    )
    assert result.status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_storm_reopens_a_marker_without_cdd_evidence(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "shell", "arguments": {"argv": ["true"]}})],
            [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")],
            [
                ChatChunk(
                    text=(
                        "```qwenloop-verdict\n"
                        "criteria: done; tests: pass; repository: Python; "
                        "levels: project/phase/epic/item; trajectory: converging; "
                        "composition: atom-only; "
                        "delivery: commit-ready\n```\n"
                        "QWENLOOP_TASK_FULLY_COMPLETE"
                    )
                )
            ],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="cdd-evidence",
        plan="# qwenstorm plan\n## Convergence-Driven Development (CDD)",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=3,
    )
    assert result.status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_runner_accepts_completion_evidence_split_across_turns(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text="```qwenloop-verdict\npass\n```")],
            [ChatChunk(text="QWENLOOP_TASK_FULLY_COMPLETE")],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="split-completion",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=3,
    )
    assert result.status is RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_runner_emits_one_turn_completed_per_model_call(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(text="think"), ChatChunk(text="ing", input_tokens=7, output_tokens=2)],
            [
                ChatChunk(
                    tool_call={"name": "write_file", "arguments": {"path": "x", "content": "y"}}
                ),
                ChatChunk(text="```qwenloop-verdict\npass\n```\n"),
                ChatChunk(text="QWENLOOP_TASK_FULLY_COMPLETE", input_tokens=3, output_tokens=4),
            ],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="turns", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=3
    )
    assert result.status is RunStatus.COMPLETED
    events_path = tmp_path / ".qwenloop" / "runs" / "turns" / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    types = [event["type"] for event in events]
    # four streamed fragments across two model calls: many deltas, but two turns
    assert types.count("text_delta") == 4
    assert [event for event in events if event["type"] == "turn.completed"] == [
        {
            "type": "turn.completed",
            "turn": 1,
            "input_tokens": 7,
            "output_tokens": 2,
            "tool_called": False,
            # FakeClock: 250 ms per monotonic read -- start, answer, end
            "started_at": "2026-09-22T12:00:00.000Z",
            "ended_at": "2026-09-22T12:00:00.750Z",
            "duration_ms": 500,
            "model_ms": 250,
        },
        {
            "type": "turn.completed",
            "turn": 2,
            "input_tokens": 3,
            "output_tokens": 4,
            "tool_called": True,
            "started_at": "2026-09-22T12:00:00.750Z",
            "ended_at": "2026-09-22T12:00:01.500Z",
            "duration_ms": 500,
            "model_ms": 250,
        },
    ]
    # each boundary closes its own turn, so the run's verdict follows the last one
    assert types[-2:] == ["turn.completed", "completed"]


@pytest.mark.asyncio
async def test_runner_rejects_completion_verdict_with_no_tool_call(tmp_path: Path) -> None:
    server = FakeServer()
    server.chunks = [
        ChatChunk(
            text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE",
            output_tokens=4,
        )
    ]
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="premature",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=1,
    )
    # a verdict claimed without ever calling a tool is not trusted as real completion
    assert result.status is not RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_runner_bounds_repeated_marker_only_claims(tmp_path: Path) -> None:
    server = ScriptedServer([[ChatChunk(text="QWENLOOP_TASK_FULLY_COMPLETE")] for _ in range(3)])
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="marker-loop",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=40,
    )
    assert result.status is RunStatus.FAILED
    assert result.turns == 3


@pytest.mark.asyncio
async def test_runner_writes_contract_artifacts(tmp_path: Path) -> None:
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        FakeServer(), FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(run_id="abc", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=2)
    assert result.status is RunStatus.COMPLETED
    assert (tmp_path / "done.txt").read_text() == "ok"
    run_dir = tmp_path / ".qwenloop" / "runs" / "abc"
    assert (run_dir / "meta.json").is_file()
    assert (run_dir / "events.jsonl").is_file()
    assert (run_dir / "snapshots" / "latest.json").is_file()


@pytest.mark.asyncio
async def test_runner_honors_wind_down(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    store.create("abc", {})
    inbox = tmp_path / ".qwenloop" / "runs" / "abc" / "control" / "inbox"
    (inbox / "1.json").write_text('{"type":"wind_down"}')
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        FakeServer(), store, SandboxTools(tmp_path), clock=FakeClock()
    ).run(run_id="abc", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=2)
    assert result.status is RunStatus.WINDING_DOWN


@pytest.mark.asyncio
async def test_sandbox_rejects_escape_and_dangerous_command(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path)
    with pytest.raises(ValueError):
        await tools.execute("read_file", {"path": "../secret"})
    assert "error" in await tools.execute("shell", {"argv": ["rm", "x"]})
    assert "error" in await tools.execute("unknown", {})


@pytest.mark.asyncio
async def test_sandbox_read_and_write_report_errors_instead_of_raising(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path)
    # checking whether a file exists yet is routine for an autonomous agent; it must not crash the run
    missing = await tools.execute("read_file", {"path": "does-not-exist.md"})
    assert "error" in missing

    binary = tmp_path / "binary.dat"
    binary.write_bytes(b"\xff\xfe\x00\x01")
    not_utf8 = await tools.execute("read_file", {"path": "binary.dat"})
    assert "error" in not_utf8

    (tmp_path / "not-a-directory").write_text("x")
    blocked_write = await tools.execute(
        "write_file", {"path": "not-a-directory/child.txt", "content": "y"}
    )
    assert "error" in blocked_write

    # a command the model guesses at that isn't on PATH (e.g. "pip" instead of "python3 -m
    # pip", or a script that doesn't exist yet) must not crash the run either
    missing_binary = await tools.execute("shell", {"argv": ["definitely-not-a-real-command-xyz"]})
    assert "error" in missing_binary


@pytest.mark.asyncio
async def test_runner_fails_on_empty_response(tmp_path: Path) -> None:
    server = FakeServer()
    server.chunks = [ChatChunk()]
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="empty", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=1
    )
    assert result.status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_runner_turn_limit_after_text(tmp_path: Path) -> None:
    server = FakeServer()
    server.chunks = [ChatChunk(text="still working")]
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="limit", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=1
    )
    assert result.status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_runner_normalizes_invalid_tool_arguments(tmp_path: Path) -> None:
    server = FakeServer()
    server.chunks = [ChatChunk(tool_call={"name": "unknown", "arguments": "bad"})]
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="invalid",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=1,
    )
    assert result.status is RunStatus.FAILED


@pytest.mark.asyncio
async def test_sandbox_read_write_and_commands(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path)
    await tools.execute("write_file", {"path": "x.txt", "content": "hello"})
    assert await tools.execute("read_file", {"path": "x.txt"}) == {"content": "hello"}
    invalid = await tools.execute("shell", {"argv": "echo"})
    assert "error" in invalid
    success = await tools.execute("shell", {"argv": ["sh", "-c", "printf ok"]})
    assert success["exit_code"] == 0
    assert success["output"] == "ok"
    network_tools = SandboxTools(tmp_path, allow_network=True)
    assert (await network_tools.execute("shell", {"argv": ["true"]}))["exit_code"] == 0


@pytest.mark.asyncio
async def test_sandbox_command_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Process:
        returncode = None
        killed = False

        async def communicate(self):  # type: ignore[no-untyped-def]
            raise TimeoutError

        def kill(self) -> None:
            self.killed = True

        async def wait(self) -> None:
            return None

    process = Process()

    async def create(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create)
    result = await SandboxTools(tmp_path).execute("shell", {"argv": ["slow"]})
    assert result == {"error": "command timed out"}
    assert process.killed


def test_run_store_handles_empty_and_invalid_control(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path)
    assert store.read_control("missing") == []
    store.create("x", {})
    inbox = tmp_path / ".qwenloop" / "runs" / "x" / "control" / "inbox"
    (inbox / "bad.json").write_text("bad")
    (inbox / "list.json").write_text("[]")
    assert store.read_control("x") == []


@pytest.mark.asyncio
async def test_edit_file_replaces_exactly_one_occurrence(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
    tools = SandboxTools(tmp_path)
    result = await tools.execute(
        "edit_file", {"path": "a.py", "old_string": "y = 2", "new_string": "y = 3"}
    )
    assert result == {"replaced": 1, "path": "a.py"}
    assert (tmp_path / "a.py").read_text() == "x = 1\ny = 3\n"


@pytest.mark.asyncio
async def test_edit_file_refuses_what_it_cannot_do_exactly(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("same\nsame\n")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe")
    tools = SandboxTools(tmp_path)

    def call(path: str, old: str) -> dict[str, object]:
        return {"path": path, "old_string": old, "new_string": "z"}

    missing = await tools.execute("edit_file", call("a.py", "absent"))
    assert "not found" in str(missing["error"])
    many = await tools.execute("edit_file", call("a.py", "same"))
    assert "matches 2 times" in str(many["error"])
    empty = await tools.execute("edit_file", call("a.py", ""))
    assert "must not be empty" in str(empty["error"])
    no_file = await tools.execute("edit_file", call("new.py", "x"))
    assert "use write_file" in str(no_file["error"])
    binary = await tools.execute("edit_file", call("blob.bin", "x"))
    assert "cannot edit" in str(binary["error"])
    assert (tmp_path / "a.py").read_text() == "same\nsame\n"
    with pytest.raises(ValueError, match="escapes"):
        await tools.execute("edit_file", call("../outside.py", "x"))


@pytest.mark.asyncio
async def test_edit_file_reports_a_failed_write(tmp_path: Path) -> None:
    target = tmp_path / "ro.py"
    target.write_text("keep\n")
    target.chmod(0o444)
    try:
        result = await SandboxTools(tmp_path).execute(
            "edit_file", {"path": "ro.py", "old_string": "keep", "new_string": "gone"}
        )
    finally:
        target.chmod(0o644)
    assert "error" in result
    assert target.read_text() == "keep\n"


@pytest.mark.asyncio
async def test_write_file_refuses_to_gut_an_existing_file(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_text("".join(f"line {n}\n" for n in range(100)))
    tools = SandboxTools(tmp_path)

    refused = await tools.execute("write_file", {"path": "big.py", "content": "only\n"})
    assert "would remove 99 of 100 lines" in str(refused["error"])
    assert big.read_text().count("\n") == 100

    allowed = await tools.execute(
        "write_file", {"path": "big.py", "content": "only\n", "allow_shrink": True}
    )
    assert allowed == {"written": 5}
    assert big.read_text() == "only\n"


@pytest.mark.asyncio
async def test_write_file_guard_leaves_ordinary_writes_alone(tmp_path: Path) -> None:
    (tmp_path / "small.py").write_text("a\nb\n")
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe")
    long_text = "".join(f"line {n}\n" for n in range(60))
    (tmp_path / "long.py").write_text(long_text)
    tools = SandboxTools(tmp_path)

    new = await tools.execute("write_file", {"path": "new.py", "content": "x\n"})
    small = await tools.execute("write_file", {"path": "small.py", "content": "x\n"})
    binary = await tools.execute("write_file", {"path": "blob.bin", "content": "x\n"})
    grown = await tools.execute("write_file", {"path": "long.py", "content": long_text + "more\n"})
    assert all("written" in result for result in (new, small, binary, grown))


@pytest.mark.asyncio
async def test_turn_completed_carries_its_timing_and_the_servers_own(tmp_path: Path) -> None:
    timings = {
        "prompt_n": 812.0,
        "cache_n": 4096.0,
        "prompt_ms": 950.5,
        "predicted_n": 64.0,
        "predicted_ms": 1200.0,
        "predicted_per_second": 53.3,
    }
    server = ScriptedServer(
        [
            [
                ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}}),
                ChatChunk(text="", input_tokens=5, output_tokens=2, timings=timings),
            ],
            [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")],
        ]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    clock = FakeClock(step=0.25)
    await AutonomousRunner(server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=clock).run(
        run_id="timed", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=3
    )
    events = [
        json.loads(line)
        for line in (tmp_path / ".qwenloop" / "runs" / "timed" / "events.jsonl")
        .read_text()
        .splitlines()
    ]
    first, second = [event for event in events if event["type"] == "turn.completed"]
    # three monotonic reads per turn (start, answer, end), each 250 ms apart
    assert first["duration_ms"] == 500
    assert first["model_ms"] == 250
    assert first["started_at"] == "2026-09-22T12:00:00.000Z"
    assert first["ended_at"] == "2026-09-22T12:00:00.750Z"
    assert first["server_timings"] == timings
    # a response without timings records none rather than inventing them
    assert "server_timings" not in second


@pytest.mark.asyncio
async def test_a_turn_with_no_answer_at_all_is_still_timed(tmp_path: Path) -> None:
    server = ScriptedServer(
        [[], [ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")]]
    )
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock(step=0.5)
    ).run(
        run_id="silent", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=2
    )
    events = (tmp_path / ".qwenloop" / "runs" / "silent" / "events.jsonl").read_text().splitlines()
    first = next(json.loads(line) for line in events if '"turn.completed"' in line)
    assert first["duration_ms"] == 500
    assert first["model_ms"] == 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("info", "expected"),
    [
        (
            ServerInfo(
                Backend.LLAMA_CPP,
                PORTABLE.name,
                "http://127.0.0.1:9/v1",
                True,
                True,
                7,
                argv=("llama-server", "--api-key", "<redacted>"),
                log_path="/cache/server.log",
            ),
            {"argv": ["llama-server", "--api-key", "<redacted>"], "log_path": "/cache/server.log"},
        ),
        (
            ServerInfo(
                Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1:11434/v1", False, True
            ),
            {"endpoint": "http://127.0.0.1:11434/v1"},
        ),
    ],
)
async def test_meta_records_the_server_settings_the_run_used(
    tmp_path: Path, info: ServerInfo, expected: dict[str, object]
) -> None:
    server = ScriptedServer(
        [[ChatChunk(text="```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE")]]
    )
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="meta", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=1
    )
    meta = json.loads((tmp_path / ".qwenloop" / "runs" / "meta" / "meta.json").read_text())
    assert meta["server_settings"] == expected


class UnparseableThenScriptedServer(ScriptedServer):
    """Refuses the first `failures` calls as an unparseable tool call, then plays its turns."""

    def __init__(self, failures: int, turns: list[list[ChatChunk]]) -> None:
        super().__init__(turns)
        self.failures = failures
        # what each refused call was sent; `seen` keeps only the calls that answered,
        # because ScriptedServer picks its turn by counting them
        self.refused: list[list[ChatMessage]] = []

    async def chat_stream(
        self, info: ServerInfo, messages: Sequence[ChatMessage]
    ) -> AsyncIterator[ChatChunk]:
        if self.failures:
            self.failures -= 1
            self.refused.append(list(messages))
            raise ToolCallParseError("HTTP 500: error parsing tool call: raw='prose'")
        async for chunk in super().chat_stream(info, messages):
            yield chunk


_DONE = "```qwenloop-verdict\npass\n```\nQWENLOOP_TASK_FULLY_COMPLETE"


@pytest.mark.asyncio
async def test_an_unparseable_tool_call_is_retried_with_a_correction(tmp_path: Path) -> None:
    server = UnparseableThenScriptedServer(
        2,
        [
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text=_DONE)],
        ],
    )
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="retry", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=3
    )
    assert result.status is RunStatus.COMPLETED
    events = [
        json.loads(line)
        for line in (tmp_path / ".qwenloop" / "runs" / "retry" / "events.jsonl")
        .read_text()
        .splitlines()
    ]
    retried = [event for event in events if event["type"] == "turn.retried"]
    assert [(event["turn"], event["retry"]) for event in retried] == [(1, 1), (1, 2)]
    assert retried[0]["reason"] == "tool_call_parse_error"
    assert "error parsing tool call" in retried[0]["detail"]
    # each retry asks for a valid tool call before calling the model again
    assert server.refused[0][-1].content == "do it"
    assert server.refused[1][-1].content.startswith("Your last reply was not a valid tool call")
    assert [message.content[:9] for message in server.seen[0][-2:]] == ["Your last"] * 2
    # the retries belong to turn 1: it still closes once, with its tool call
    turns = [event for event in events if event["type"] == "turn.completed"]
    assert [(event["turn"], event["tool_called"]) for event in turns] == [(1, True), (2, False)]


@pytest.mark.asyncio
async def test_a_fourth_unparseable_tool_call_fails_the_run_as_before(tmp_path: Path) -> None:
    server = UnparseableThenScriptedServer(4, [[ChatChunk(text=_DONE)]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    runner = AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    )
    with pytest.raises(RuntimeError, match="error parsing tool call"):
        await runner.run(
            run_id="bound",
            plan="do it",
            cwd=tmp_path,
            profile=PORTABLE,
            server_info=info,
            max_turns=3,
        )
    events = (tmp_path / ".qwenloop" / "runs" / "bound" / "events.jsonl").read_text().splitlines()
    assert sum('"turn.retried"' in line for line in events) == 3


@pytest.mark.asyncio
async def test_with_no_empty_reply_retries_an_empty_reply_fails_the_run_as_before(
    tmp_path: Path,
) -> None:
    server = ScriptedServer([[], [ChatChunk(text=_DONE)]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="empty",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=3,
        max_empty_reply_retries=0,
    )
    # an empty reply is not a parse failure: with no retries declared it fails the run
    assert result.status is RunStatus.FAILED
    assert len(server.seen) == 1
    events = _events(tmp_path, "empty")
    assert not [event for event in events if event["type"] == "turn.retried"]
    assert events[-1] == {
        "type": "failed",
        "reason": "empty_response",
        "turn": 1,
        "max_turns": 3,
        "empty_replies": 1,
        "max_empty_reply_retries": 0,
    }


def _events(root: Path, run_id: str) -> list[dict[str, object]]:
    path = root / ".qwenloop" / "runs" / run_id / "events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def _empty(**kwargs: object) -> list[ChatChunk]:
    """One turn with no tool call and no text: what gpt-oss sent in 27 of 60 failed runs."""
    return [ChatChunk(**kwargs)]  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_an_empty_reply_is_recorded_and_retried_with_a_nudge(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            _empty(input_tokens=900, output_tokens=11, finish_reason="stop", reasoning_chars=37),
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text=_DONE)],
        ]
    )
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="nudge",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=5,
        max_empty_reply_retries=2,
    )
    assert result.status is RunStatus.COMPLETED
    events = _events(tmp_path, "nudge")
    empty = [event for event in events if event["type"] == "turn.empty"]
    # what the empty turn actually contained: how it ended, what it cost, whether the
    # model reasoned; the reasoning's length only, never its content
    assert empty == [
        {
            "type": "turn.empty",
            "turn": 1,
            "finish_reason": "stop",
            "input_tokens": 900,
            "output_tokens": 11,
            "reasoning_present": True,
            "reasoning_chars": 37,
            "empty_replies": 1,
            "max_empty_reply_retries": 2,
            "retrying": True,
        }
    ]
    # the retry is a new model call, so it spends a turn of the budget
    turns = [event["turn"] for event in events if event["type"] == "turn.completed"]
    assert turns == [1, 2, 3]
    # the retry sees a neutral nudge naming both ways out, and nothing else new
    nudge = server.seen[1][-1]
    assert (nudge.role, nudge.content) == ("user", _EMPTY_REPLY_PROMPT)
    assert server.seen[1][:-1] == server.seen[0]
    assert "call one of the tools" in _EMPTY_REPLY_PROMPT
    assert "answer in plain text" in _EMPTY_REPLY_PROMPT


@pytest.mark.asyncio
async def test_an_empty_reply_without_finish_reason_or_reasoning_says_so(tmp_path: Path) -> None:
    server = ScriptedServer([_empty(), [ChatChunk(text=_DONE)]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="bare", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=2
    )
    empty = next(event for event in _events(tmp_path, "bare") if event["type"] == "turn.empty")
    assert (empty["finish_reason"], empty["reasoning_present"], empty["reasoning_chars"]) == (
        None,
        False,
        0,
    )


@pytest.mark.asyncio
async def test_exhausted_empty_reply_retries_fail_the_run_for_that_reason(tmp_path: Path) -> None:
    server = ScriptedServer([_empty(finish_reason="stop") for _ in range(10)])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="silent",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=10,
        max_empty_reply_retries=2,
    )
    assert result.status is RunStatus.FAILED
    # the first empty reply plus two retries, then the run stops: bounded, not max_turns
    assert len(server.seen) == 3
    events = _events(tmp_path, "silent")
    retrying = [event["retrying"] for event in events if event["type"] == "turn.empty"]
    assert retrying == [True, True, False]
    assert events[-1] == {
        "type": "failed",
        "reason": "empty_response",
        "turn": 3,
        "max_turns": 10,
        "empty_replies": 3,
        "max_empty_reply_retries": 2,
    }


@pytest.mark.asyncio
async def test_empty_reply_retries_spend_the_turn_budget_and_cannot_outlast_it(
    tmp_path: Path,
) -> None:
    server = ScriptedServer([_empty() for _ in range(10)])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="cap",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=2,
        max_empty_reply_retries=50,
    )
    assert result.status is RunStatus.FAILED
    assert len(server.seen) == 2
    # the cap stopped it, and the event says so rather than blaming the empty reply
    assert _events(tmp_path, "cap")[-1] == {
        "type": "failed",
        "reason": "turn_limit",
        "turn": 2,
        "max_turns": 2,
    }


@pytest.mark.asyncio
async def test_empty_reply_retries_bound_consecutive_empty_turns_only(tmp_path: Path) -> None:
    tool = [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})]
    server = ScriptedServer([_empty(), tool, _empty(), tool, [ChatChunk(text=_DONE)]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    result = await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="reset",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=5,
        max_empty_reply_retries=1,
    )
    # a turn that did something clears the count: two separated empty replies both retry
    assert result.status is RunStatus.COMPLETED
    empty = [event for event in _events(tmp_path, "reset") if event["type"] == "turn.empty"]
    assert [(event["turn"], event["empty_replies"]) for event in empty] == [(1, 1), (3, 1)]


@pytest.mark.asyncio
async def test_a_turn_limit_failure_names_the_cap(tmp_path: Path) -> None:
    server = ScriptedServer([[ChatChunk(text="still working")]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="limit", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=1
    )
    assert _events(tmp_path, "limit")[-1] == {
        "type": "failed",
        "reason": "turn_limit",
        "turn": 1,
        "max_turns": 1,
    }


@pytest.mark.asyncio
async def test_repeated_invalid_completion_claims_fail_for_that_reason(tmp_path: Path) -> None:
    server = ScriptedServer([[ChatChunk(text="QWENLOOP_TASK_FULLY_COMPLETE")] for _ in range(3)])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="claims", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=9
    )
    assert _events(tmp_path, "claims")[-1] == {
        "type": "failed",
        "reason": "invalid_completion_claims",
        "turn": 3,
        "max_turns": 9,
    }


@pytest.mark.asyncio
async def test_meta_records_the_turn_cap_and_the_empty_reply_bound(tmp_path: Path) -> None:
    server = ScriptedServer(
        [
            [ChatChunk(tool_call={"name": "read_file", "arguments": {"path": "x"}})],
            [ChatChunk(text=_DONE)],
        ]
    )
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="caps",
        plan="do it",
        cwd=tmp_path,
        profile=PORTABLE,
        server_info=info,
        max_turns=60,
        max_empty_reply_retries=4,
    )
    meta = json.loads((tmp_path / ".qwenloop" / "runs" / "caps" / "meta.json").read_text())
    assert (meta["max_turns"], meta["max_empty_reply_retries"]) == (60, 4)


@pytest.mark.asyncio
async def test_the_runner_defaults_to_the_declared_empty_reply_bound(tmp_path: Path) -> None:
    server = ScriptedServer([[ChatChunk(text=_DONE)]])
    info = ServerInfo(Backend.OPENAI_COMPAT, PORTABLE.name, "http://127.0.0.1", False, True)
    await AutonomousRunner(
        server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()
    ).run(
        run_id="dflt", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=info, max_turns=1
    )
    meta = json.loads((tmp_path / ".qwenloop" / "runs" / "dflt" / "meta.json").read_text())
    assert meta["max_empty_reply_retries"] == QwenConfig().max_empty_reply_retries
