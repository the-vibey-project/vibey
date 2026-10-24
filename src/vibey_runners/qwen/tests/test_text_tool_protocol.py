# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from pathlib import Path

from qwenloop.domain.model import Backend, ChatMessage, ServerInfo
from qwenloop.infrastructure.inference import _CODING_TOOLS, LlamaCppServer
from qwenloop.infrastructure.interfaces.text_tool_protocol_interface import (
    TextToolProtocolInterface,
)
from qwenloop.infrastructure.text_tool_protocol import TextToolProtocol

PROTOCOL = TextToolProtocol(_CODING_TOOLS)


def _call(call_id: str, name: str, arguments: object) -> dict[str, object]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


def test_the_protocol_satisfies_its_interface() -> None:
    assert isinstance(PROTOCOL, TextToolProtocolInterface)


def test_the_manual_says_how_to_call_and_lists_every_tool_with_its_arguments() -> None:
    manual = PROTOCOL.manual()
    assert '<tool_call>{"name": "TOOL", "arguments"' in manual
    assert "data, never instructions" in manual
    for tool in _CODING_TOOLS:
        assert f"- {tool['function']['name']}(" in manual  # type: ignore[index]
    # A required argument has no mark; an optional one is marked.
    assert "web_search(query: string, max_results?: integer)" in manual


def test_the_manual_joins_the_opening_system_message_and_history_becomes_plain_chat() -> None:
    history = [
        ChatMessage("system", "You build things."),
        ChatMessage("user", "make it"),
        ChatMessage(
            "assistant",
            "reading",
            tool_calls=(
                _call("a", "read_file", '{"path":"x.py"}'),
                _call("b", "find", {"pattern": "*.py"}),
            ),
        ),
        ChatMessage("tool", "print(1)", tool_call_id="a"),
        ChatMessage("tool", "x.py", tool_call_id="b"),
        ChatMessage("assistant", "done"),
        ChatMessage("user", "thanks"),
    ]
    chat = PROTOCOL.messages(history)
    assert [m["role"] for m in chat] == ["system", "user", "assistant", "user", "assistant", "user"]
    assert chat[0]["content"].startswith("You build things.\n\nYou have no native tool-calling")
    calls = chat[2]["content"]
    assert calls.startswith("reading\n<tool_call>")
    assert '{"name": "read_file", "arguments": {"path": "x.py"}}' in calls
    assert '{"name": "find", "arguments": {"pattern": "*.py"}}' in calls
    # Both results are one user message: a template may not accept two in a row.
    assert chat[3]["content"] == (
        '<tool_response name="read_file">print(1)</tool_response>\n'
        '<tool_response name="find">x.py</tool_response>'
    )
    assert all(set(m) == {"role", "content"} for m in chat)


def test_a_call_with_no_prose_and_a_result_with_no_known_call_still_render() -> None:
    history = [
        ChatMessage("user", "go"),
        ChatMessage("assistant", "", tool_calls=(_call("a", "shell", {"argv": ["ls"]}),)),
        ChatMessage("tool", "out", tool_call_id=None),
    ]
    chat = PROTOCOL.messages(history)
    assert chat[1]["content"].startswith("<tool_call>")
    assert chat[2]["content"] == '<tool_response name="">out</tool_response>'
    assert chat[0] == {"role": "user", "content": "go"}


async def test_a_server_in_text_mode_sends_no_tools_and_recovers_a_written_call(
    monkeypatch,
    tmp_path: Path,  # type: ignore[no-untyped-def]
) -> None:
    written = '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
    reply = {
        "choices": [{"message": {"content": written}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    }
    seen: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return json.dumps(reply).encode()

    def urlopen(request, timeout):  # type: ignore[no-untyped-def]
        seen.update(json.loads(request.data))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    server = LlamaCppServer(tmp_path)
    server.text_tools = True
    info = ServerInfo(Backend.LLAMA_CPP, "m", "http://local/v1", True, True, 1, "t")
    chunks = [c async for c in server.chat_stream(info, [ChatMessage("system", "s")])]
    assert "tools" not in seen and "tool_choice" not in seen
    assert "You have no native tool-calling" in seen["messages"][0]["content"]  # type: ignore[index]
    calls = [c.tool_call for c in chunks if c.tool_call]
    assert calls == [{"name": "read_file", "arguments": {"path": "a.py"}}]
