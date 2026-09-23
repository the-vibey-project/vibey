# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import io
import json
import urllib.error
from pathlib import Path

import pytest

from qwenloop.domain.interfaces.class_contracts import ToolCallParseErrorInterface
from qwenloop.domain.model import Backend, ChatMessage, ServerInfo, ToolCallParseError
from qwenloop.infrastructure.inference import (
    LlamaCppServer,
    OpenAICompatServer,
    OpenAIServer,
    VllmServer,
    _http_error_detail,
    _parse_text_tool_calls,
    _pid_alive,
)
from qwenloop.infrastructure.interfaces import AttachedServerInterface, ManagedServerInterface
from qwenloop.infrastructure.profiles import NVIDIA_BF16, PORTABLE


class UrlResponse(io.BytesIO):
    status = 200


@pytest.mark.asyncio
async def test_openai_health_and_chat(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": "done",
                    "tool_calls": [
                        {
                            "id": "call-2",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"x"}',
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1},
    }

    def urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        if request.full_url.endswith("/models"):
            return UrlResponse(b"{}")
        body = json.loads(request.data)
        assert body["tool_choice"] == "auto"
        assert body["messages"][-2:] == [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {"name": "read_file", "arguments": '{"path":"x"}'},
                    }
                ],
            },
            {"role": "tool", "content": "ok", "tool_call_id": "call-1"},
        ]
        assert {tool["function"]["name"] for tool in body["tools"]} == {
            "read_file",
            "write_file",
            "edit_file",
            "shell",
        }
        return UrlResponse(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    server = LlamaCppServer(tmp_path)
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://local/v1", True, True, 1, "t")
    assert await server.health(info)
    chunks = [
        chunk
        async for chunk in server.chat_stream(
            info,
            [
                ChatMessage("user", "x"),
                ChatMessage(
                    "assistant",
                    "",
                    tool_calls=(
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"x"}',
                            },
                        },
                    ),
                ),
                ChatMessage("tool", "ok", tool_call_id="call-1"),
            ],
        )
    ]
    assert chunks[0].tool_call == {
        "id": "call-2",
        "name": "read_file",
        "arguments": {"path": "x"},
    }
    assert chunks[1].text == "done"


@pytest.mark.asyncio
async def test_chat_stream_surfaces_context_overflow_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = json.dumps(
        {
            "error": {
                "message": "request (20030 tokens) exceeds the available context size (4096 tokens)",
            }
        }
    ).encode()

    def urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, io.BytesIO(body))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    server = LlamaCppServer(tmp_path)
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://local/v1", True, True, 1, "t")
    with pytest.raises(RuntimeError, match="exceeds the available context size"):
        async for _ in server.chat_stream(info, [ChatMessage("user", "x")]):
            pass


def test_http_error_detail_prefers_json_error_message() -> None:
    exc = urllib.error.HTTPError(
        "u", 400, "Bad Request", {}, io.BytesIO(json.dumps({"error": {"message": "boom"}}).encode())
    )
    assert _http_error_detail(exc) == "HTTP 400: boom"


def test_http_error_detail_falls_back_to_raw_body_text() -> None:
    exc = urllib.error.HTTPError("u", 502, "Bad Gateway", {}, io.BytesIO(b"gateway down"))
    assert _http_error_detail(exc) == "HTTP 502: gateway down"


def test_http_error_detail_falls_back_when_json_has_no_message() -> None:
    exc = urllib.error.HTTPError("u", 500, "Server Error", {}, io.BytesIO(b'{"error": {}}'))
    assert _http_error_detail(exc) == 'HTTP 500: {"error": {}}'


def test_http_error_detail_falls_back_when_body_is_not_a_mapping() -> None:
    exc = urllib.error.HTTPError("u", 400, "Bad Request", {}, io.BytesIO(b"[1, 2, 3]"))
    assert _http_error_detail(exc) == "HTTP 400: [1, 2, 3]"


def test_http_error_detail_falls_back_to_reason_on_empty_body() -> None:
    exc = urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b""))
    assert _http_error_detail(exc) == "HTTP 503: Unavailable"


def test_http_error_detail_falls_back_to_reason_when_body_unreadable() -> None:
    class UnreadableFp:
        def read(self) -> bytes:
            raise OSError("closed")

        def close(self) -> None:
            return None

    exc = urllib.error.HTTPError("u", 504, "Gateway Timeout", {}, UnreadableFp())  # type: ignore[arg-type]
    assert _http_error_detail(exc) == "HTTP 504: Gateway Timeout"


def test_server_argv_and_inspect(tmp_path: Path) -> None:
    llama = LlamaCppServer(tmp_path)
    model = tmp_path / "models" / PORTABLE.name / str(PORTABLE.filename)
    model.parent.mkdir(parents=True)
    model.write_bytes(b"x")
    assert "--jinja" in llama._argv(PORTABLE, 1234, "token")
    vllm = VllmServer(tmp_path)
    vllm_argv = vllm._argv(NVIDIA_BF16, 1234, "token")
    assert "hermes" in vllm_argv
    # vLLM answers only to the name it serves; the name requests send is the profile's.
    served = vllm_argv.index("--served-model-name")
    assert vllm_argv[served + 1] == NVIDIA_BF16.name
    assert isinstance(llama, ManagedServerInterface)
    assert isinstance(vllm, ManagedServerInterface)
    state = tmp_path / "servers" / f"{PORTABLE.name}.json"
    state.parent.mkdir()
    state.write_text("bad")
    assert llama.inspect(PORTABLE) is None
    state.write_text(
        json.dumps(
            {
                "backend": "llama.cpp",
                "profile": PORTABLE.name,
                "endpoint": "x",
                "owned": True,
                "pid": 1,
            }
        )
    )
    assert llama.inspect(PORTABLE) is not None


@pytest.mark.asyncio
async def test_stop_obeys_ownership(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[int, object]] = []
    monkeypatch.setattr("os.killpg", lambda pid, sig: calls.append((pid, sig)))
    monkeypatch.setattr("qwenloop.infrastructure.inference._pid_alive", lambda _pid: False)
    server = LlamaCppServer(tmp_path)
    await server.stop(ServerInfo(Backend.LLAMA_CPP, "p", "x", False, True, 5))
    await server.stop(ServerInfo(Backend.LLAMA_CPP, "p", "x", True, True, 5))
    assert calls


@pytest.mark.asyncio
async def test_base_install_and_argv_are_not_implicit(tmp_path: Path) -> None:
    server = OpenAIServer(tmp_path)
    with pytest.raises(RuntimeError):
        await server.install(PORTABLE)
    with pytest.raises(NotImplementedError):
        server._argv(PORTABLE, 1, "t")
    with pytest.raises(FileNotFoundError):
        LlamaCppServer(tmp_path)._argv(PORTABLE, 1, "t")


@pytest.mark.asyncio
async def test_start_persists_owned_server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model = tmp_path / "models" / PORTABLE.name / str(PORTABLE.filename)
    model.parent.mkdir(parents=True)
    model.write_bytes(b"x")

    class Process:
        pid = 42

    async def create(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return Process()

    monkeypatch.setattr("qwenloop.infrastructure.inference._free_port", lambda: 1234)
    monkeypatch.setattr("asyncio.create_subprocess_exec", create)
    server = LlamaCppServer(tmp_path)
    info = await server.start(PORTABLE)
    assert info.pid == 42
    assert info.model == PORTABLE.name
    inspected = server.inspect(PORTABLE)
    assert inspected is not None
    assert inspected.model == PORTABLE.name

    monkeypatch.setattr("qwenloop.infrastructure.inference._pid_alive", lambda _pid: True)
    reused = await server.start(PORTABLE)
    assert reused.pid == 42


@pytest.mark.asyncio
async def test_health_failure_and_malformed_tool_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def failed(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise OSError("offline")

    monkeypatch.setattr("urllib.request.urlopen", failed)
    server = LlamaCppServer(tmp_path)
    info = ServerInfo(Backend.LLAMA_CPP, "p", "http://bad/v1", True, False, 1)
    assert not await server.health(info)

    payload = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [{"function": {"name": "x", "arguments": "bad"}}],
                }
            }
        ]
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: UrlResponse(json.dumps(payload).encode()),
    )
    chunks = [chunk async for chunk in server.chat_stream(info, [])]
    assert chunks[0].tool_call == {"name": "x", "arguments": {}}

    payload["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = {"x": 1}
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: UrlResponse(json.dumps(payload).encode()),
    )
    chunks = [chunk async for chunk in server.chat_stream(info, [])]
    assert chunks[0].tool_call == {"name": "x", "arguments": {"x": 1}}

    payload["choices"][0]["message"] = {
        "content": '<tools>{"name":"read_file","arguments":{"path":"x"}}</tools>'
    }
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_args, **_kwargs: UrlResponse(json.dumps(payload).encode()),
    )
    chunks = [chunk async for chunk in server.chat_stream(info, [])]
    assert chunks[0].tool_call == {"name": "read_file", "arguments": {"path": "x"}}
    assert chunks[1].text == ""


@pytest.mark.asyncio
async def test_stop_ignores_missing_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def missing(_pid, _signal):  # type: ignore[no-untyped-def]
        raise ProcessLookupError

    monkeypatch.setattr("os.killpg", missing)
    server = LlamaCppServer(tmp_path)
    await server.stop(ServerInfo(Backend.LLAMA_CPP, "p", "x", True, True, 99))


@pytest.mark.asyncio
async def test_stop_cleans_matching_state_and_forces_after_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    server = LlamaCppServer(tmp_path)
    state = tmp_path / "servers" / f"{PORTABLE.name}.json"
    state.parent.mkdir()
    state.write_text(
        json.dumps(
            {
                "backend": "llama.cpp",
                "profile": PORTABLE.name,
                "endpoint": "x",
                "owned": True,
                "pid": 7,
            }
        )
    )
    signals: list[object] = []
    monkeypatch.setattr("os.killpg", lambda _pid, sig: signals.append(sig))
    monkeypatch.setattr("qwenloop.infrastructure.inference._pid_alive", lambda _pid: True)

    async def no_sleep(_delay):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)
    await server.stop(ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "x", True, True, 7))
    assert len(signals) == 2
    assert not state.exists()


def test_pid_alive_outcomes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.kill", lambda *_args: None)
    assert _pid_alive(1)

    def denied(*_args):  # type: ignore[no-untyped-def]
        raise PermissionError

    monkeypatch.setattr("os.kill", denied)
    assert _pid_alive(1)

    def missing(*_args):  # type: ignore[no-untyped-def]
        raise ProcessLookupError

    monkeypatch.setattr("os.kill", missing)
    assert not _pid_alive(1)


def test_free_port_uses_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    from qwenloop.infrastructure import inference

    class Socket:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *_args):  # type: ignore[no-untyped-def]
            return None

        def bind(self, address):  # type: ignore[no-untyped-def]
            assert address == ("127.0.0.1", 0)

        def getsockname(self):  # type: ignore[no-untyped-def]
            return ("127.0.0.1", 4321)

    monkeypatch.setattr("socket.socket", Socket)
    assert inference._free_port() == 4321


def test_qwen_fenced_json_tool_calls_are_normalized() -> None:
    calls, remaining = _parse_text_tool_calls(
        'before\n```json\n{\n  "name": "write_file",\n  "arguments": {\n'
        '    "path": "smoke.txt",\n    "content": "ok"\n  }\n}\n```\nafter'
    )
    assert calls == [{"name": "write_file", "arguments": {"path": "smoke.txt", "content": "ok"}}]
    assert remaining == "before\n\nafter"

    bare_fence, _ = _parse_text_tool_calls('```\n{"name": "shell", "arguments": {}}\n```')
    assert bare_fence == [{"name": "shell", "arguments": {}}]

    unrelated, unchanged = _parse_text_tool_calls("```qwenloop-verdict\nall good\n```")
    assert unrelated == []
    assert unchanged == "```qwenloop-verdict\nall good\n```"


def test_qwen_bare_unwrapped_json_tool_call_is_normalized() -> None:
    # observed in the wild: no fence, no tag, just the object followed by other text
    calls, remaining = _parse_text_tool_calls(
        '{\n  "name": "write_file",\n  "arguments": {\n    "path": "smoke.txt",\n'
        '    "content": "ok"\n  }\n}\n```qwenloop-verdict\ndone\n```'
    )
    assert calls == [{"name": "write_file", "arguments": {"path": "smoke.txt", "content": "ok"}}]
    assert remaining == "```qwenloop-verdict\ndone\n```"


def test_qwen_text_tool_calls_are_normalized() -> None:
    calls, remaining = _parse_text_tool_calls(
        'before <tools>{"name":"read_file","arguments":{"path":"README.md"}}</tools> after'
    )
    assert calls == [{"name": "read_file", "arguments": {"path": "README.md"}}]
    assert remaining == "before  after"

    malformed, unchanged = _parse_text_tool_calls("<tool_call>{bad}</tool_call>")
    assert malformed == []
    assert unchanged == "<tool_call>{bad}</tool_call>"

    invalid, _ = _parse_text_tool_calls('<tool_call>{"name": 1, "arguments": []}</tool_call>')
    assert invalid == []

    normalized, _ = _parse_text_tool_calls('<tool_call>{"name":"shell","arguments":[]}</tool_call>')
    assert normalized == [{"name": "shell", "arguments": {}}]


class Recorder:
    """A fake `urlopen` that answers from a table and remembers every request."""

    def __init__(self, answers: dict[str, object]) -> None:
        self.answers = answers
        self.requests: list[object] = []

    def __call__(self, request, timeout):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        self.timeout = timeout
        answer = self.answers[request.full_url.rsplit("/", 1)[-1]]
        if isinstance(answer, BaseException):
            raise answer
        return UrlResponse(answer if isinstance(answer, bytes) else json.dumps(answer).encode())


OLLAMA_MODELS = {
    "object": "list",
    "data": [
        {"id": "qwen2.5-coder:14b", "object": "model", "owned_by": "library"},
        {"id": "llama3:latest", "object": "model", "owned_by": "library"},
    ],
}
CHAT_REPLY = {
    "choices": [{"message": {"content": "hello"}}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 1},
}


def ollama(**kwargs: object) -> OpenAICompatServer:
    return OpenAICompatServer("http://127.0.0.1:11434/v1/", "qwen2.5-coder:14b", **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("url", ["file:///etc/passwd", "127.0.0.1:11434", "http://"])
def test_attached_server_refuses_a_non_http_url(url: str) -> None:
    with pytest.raises(ValueError, match="http:// or https://"):
        OpenAICompatServer(url, "m")


@pytest.mark.parametrize("url", ["http://u@host/v1"])
def test_attached_server_refuses_embedded_credentials(url: str) -> None:
    with pytest.raises(ValueError, match="must not include credentials"):
        OpenAICompatServer(url, "m")


def test_attached_server_profile_and_inspect_pin_nothing_and_own_nothing() -> None:
    server = ollama(api_key="sk-x", context_window=8192)
    assert isinstance(server, AttachedServerInterface)
    assert server.base_url == "http://127.0.0.1:11434/v1"
    profile = server.profile
    assert profile.name == "qwen2.5-coder:14b"
    assert profile.backend is Backend.OPENAI_COMPAT
    assert profile.repository == "http://127.0.0.1:11434/v1"
    assert profile.sha256 is None
    assert profile.context_window == 8192
    info = server.inspect(profile)
    assert info.backend is Backend.OPENAI_COMPAT
    assert info.endpoint == "http://127.0.0.1:11434/v1"
    assert (info.owned, info.healthy, info.pid) == (False, False, None)
    assert (info.token, info.model) == ("sk-x", "qwen2.5-coder:14b")


@pytest.mark.asyncio
async def test_attached_check_finds_the_model_and_sends_no_empty_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = Recorder({"models": OLLAMA_MODELS})
    monkeypatch.setattr("urllib.request.urlopen", fake)
    server = ollama(timeout_seconds=7)
    assert await server.check() == "qwen2.5-coder:14b"
    assert fake.requests[0].full_url == "http://127.0.0.1:11434/v1/models"  # type: ignore[attr-defined]
    assert not fake.requests[0].has_header("Authorization")  # type: ignore[attr-defined]
    assert fake.timeout == 7


@pytest.mark.asyncio
async def test_attached_check_sends_the_api_key_when_there_is_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = Recorder({"models": OLLAMA_MODELS})
    monkeypatch.setattr("urllib.request.urlopen", fake)
    await ollama(api_key="sk-local").check()
    assert fake.requests[0].get_header("Authorization") == "Bearer sk-local"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_attached_check_accepts_ollamas_implicit_latest_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": OLLAMA_MODELS}))
    assert await OpenAICompatServer("http://h/v1", "llama3").check() == "llama3:latest"
    with pytest.raises(RuntimeError, match="'llama3:8b' is not served"):
        await OpenAICompatServer("http://h/v1", "llama3:8b").check()


@pytest.mark.asyncio
async def test_attached_check_names_the_missing_model_and_what_is_served(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": OLLAMA_MODELS}))
    with pytest.raises(RuntimeError) as caught:
        await OpenAICompatServer("http://h/v1", "qwen2.5-coder:32b").check()
    message = str(caught.value)
    assert "'qwen2.5-coder:32b' is not served by http://h/v1" in message
    assert "qwen2.5-coder:14b, llama3:latest" in message
    assert "ollama pull qwen2.5-coder:32b" in message

    monkeypatch.setattr(
        "urllib.request.urlopen", Recorder({"models": {"object": "list", "data": []}})
    )
    with pytest.raises(RuntimeError, match="it serves: no models at all"):
        await ollama().check()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (
            urllib.error.URLError(ConnectionRefusedError(61, "Connection refused")),
            "Connection refused",
        ),
        (TimeoutError("timed out"), "timed out"),
    ],
)
async def test_attached_check_reports_an_unreachable_endpoint(
    monkeypatch: pytest.MonkeyPatch, failure: BaseException, expected: str
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": failure}))
    with pytest.raises(RuntimeError) as caught:
        await ollama().check()
    message = str(caught.value)
    assert "http://127.0.0.1:11434/v1/models is unreachable" in message
    assert expected in message
    assert "ollama serve" in message


@pytest.mark.asyncio
async def test_attached_check_reports_a_refusal_with_the_servers_own_words(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refusal = urllib.error.HTTPError(
        "u", 401, "Unauthorized", {}, io.BytesIO(b'{"error": {"message": "bad key"}}')
    )
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": refusal}))
    with pytest.raises(RuntimeError, match="refused the model list: HTTP 401: bad key"):
        await ollama().check()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"<html>not json</html>", b'["a"]', b'{"data": "nope"}'])
async def test_attached_check_refuses_a_body_that_is_not_a_model_list(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": body}))
    with pytest.raises(RuntimeError, match="did not answer with an OpenAI-compatible model list"):
        await ollama().check()


@pytest.mark.asyncio
async def test_attached_model_list_skips_entries_without_an_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    listing = {"data": ["junk", {"object": "model"}, {"id": "qwen2.5-coder:14b"}]}
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": listing}))
    assert await ollama().check() == "qwen2.5-coder:14b"


@pytest.mark.asyncio
async def test_attached_start_spawns_nothing_and_health_follows_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("an attached server must never spawn a process")

    monkeypatch.setattr("asyncio.create_subprocess_exec", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"models": OLLAMA_MODELS}))
    server = ollama()
    started = await server.start(server.profile)
    assert started.healthy
    assert not started.owned
    assert started.pid is None
    assert await server.health(started)

    monkeypatch.setattr(
        "urllib.request.urlopen", Recorder({"models": urllib.error.URLError("down")})
    )
    assert not await server.health(started)
    with pytest.raises(RuntimeError, match="unreachable"):
        await server.start(server.profile)


@pytest.mark.asyncio
async def test_attached_stop_never_touches_a_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args):  # type: ignore[no-untyped-def]
        raise AssertionError("an attached server must never be signalled")

    monkeypatch.setattr("os.killpg", forbidden)
    server = ollama()
    await server.stop(server.inspect(server.profile))
    await server.stop(ServerInfo(Backend.OPENAI_COMPAT, "m", "x", True, True, 1))


@pytest.mark.asyncio
async def test_attached_install_points_at_the_endpoint_instead() -> None:
    server = ollama()
    with pytest.raises(RuntimeError, match="ollama pull qwen2.5-coder:14b"):
        await server.install(server.profile)


@pytest.mark.asyncio
async def test_attached_chat_sends_the_configured_model_to_the_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = Recorder({"completions": CHAT_REPLY})
    monkeypatch.setattr("urllib.request.urlopen", fake)
    server = ollama()
    info = server.inspect(server.profile)
    chunks = [chunk async for chunk in server.chat_stream(info, [ChatMessage("user", "hi")])]
    assert chunks[-1].text == "hello"
    request = fake.requests[0]
    assert request.full_url == "http://127.0.0.1:11434/v1/chat/completions"  # type: ignore[attr-defined]
    assert json.loads(request.data)["model"] == "qwen2.5-coder:14b"  # type: ignore[attr-defined]
    assert not request.has_header("Authorization")  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_managed_chat_falls_back_to_the_profile_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = Recorder({"completions": CHAT_REPLY})
    monkeypatch.setattr("urllib.request.urlopen", fake)
    legacy = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://local/v1", True, True, 1, "t")
    _ = [chunk async for chunk in LlamaCppServer(tmp_path).chat_stream(legacy, [])]
    assert json.loads(fake.requests[0].data)["model"] == PORTABLE.name  # type: ignore[attr-defined]
    assert fake.requests[0].get_header("Authorization") == "Bearer t"  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.parametrize("configured", [900, 45.0, None])
async def test_chat_stream_waits_the_request_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configured: float | None
) -> None:
    """#345: the chat request waits `request_timeout_seconds`, not a fixed 300 s."""
    seen: list[object] = []
    reply = {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    def urlopen(request: object, timeout: object = None) -> io.BytesIO:
        seen.append(timeout)
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    server = LlamaCppServer(tmp_path)
    server.request_timeout_seconds = configured
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://local/v1", True, True, 1, "t")
    async for _ in server.chat_stream(info, [ChatMessage("user", "hi")]):
        pass
    assert seen == [configured]


def test_the_default_request_timeout_is_the_idle_timeout_default() -> None:
    assert OpenAICompatServer("http://127.0.0.1:11434/v1", "m").request_timeout_seconds == 900


@pytest.mark.asyncio
async def test_chat_stream_passes_the_servers_own_timings_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timings = {
        "prompt_n": 812,
        "cache_n": 4096,
        "prompt_ms": 950.5,
        "predicted_n": 64,
        "predicted_ms": 1200.0,
        "predicted_per_second": 53.3,
        "predicted_per_token_ms": 18.75,  # not one a run is tuned by: dropped
        "draft_n": True,  # a flag, not a number: dropped
    }
    monkeypatch.setattr(
        "urllib.request.urlopen", Recorder({"completions": {**CHAT_REPLY, "timings": timings}})
    )
    server = LlamaCppServer()
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1:9/v1", True, True)
    chunks = [chunk async for chunk in server.chat_stream(info, [ChatMessage("user", "hi")])]
    assert chunks[-1].timings == {
        "prompt_n": 812.0,
        "cache_n": 4096.0,
        "prompt_ms": 950.5,
        "predicted_n": 64.0,
        "predicted_ms": 1200.0,
        "predicted_per_second": 53.3,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("timings", [None, "fast", {}, {"unrelated": 1}])
async def test_chat_stream_invents_no_timings(
    monkeypatch: pytest.MonkeyPatch, timings: object
) -> None:
    reply = dict(CHAT_REPLY) if timings is None else {**CHAT_REPLY, "timings": timings}
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"completions": reply}))
    info = ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1:9/v1", True, True)
    chunks = [
        chunk async for chunk in LlamaCppServer().chat_stream(info, [ChatMessage("user", "hi")])
    ]
    assert chunks[-1].timings is None


@pytest.mark.asyncio
async def test_managed_server_logs_to_a_file_and_records_redacted_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model = tmp_path / "models" / PORTABLE.name / str(PORTABLE.filename)
    model.parent.mkdir(parents=True)
    model.write_bytes(b"x")
    # A stand-in llama-server: prints one line on each stream, then exits.
    binary = tmp_path / "fake-llama-server"
    binary.write_text("#!/bin/sh\necho 'model loaded'\necho 'slot 0 ready' >&2\n")
    binary.chmod(0o755)
    monkeypatch.setattr("qwenloop.infrastructure.inference._free_port", lambda: 1234)
    server = LlamaCppServer(tmp_path)
    server.binary = str(binary)
    info = await server.start(PORTABLE)
    token = info.token
    for _ in range(100):
        log = Path(info.log_path)
        if log.is_file() and "slot 0 ready" in log.read_text():
            break
        await asyncio.sleep(0.05)
    assert Path(info.log_path) == tmp_path / "servers" / PORTABLE.name / "server.log"
    assert "model loaded" in Path(info.log_path).read_text()
    assert info.argv[0] == str(binary)
    assert "<redacted>" in info.argv
    assert token and token not in info.argv
    inspected = server.inspect(PORTABLE)
    assert inspected is not None
    assert inspected.argv == info.argv
    assert inspected.log_path == info.log_path


def _server_error(body: dict[str, object], code: int = 500):  # type: ignore[no-untyped-def]
    payload = json.dumps(body).encode()

    def urlopen(request, timeout):  # type: ignore[no-untyped-def]
        del timeout
        raise urllib.error.HTTPError(request.full_url, code, "error", {}, io.BytesIO(payload))

    return urlopen


@pytest.mark.asyncio
async def test_an_unparseable_tool_call_is_its_own_error(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = "error parsing tool call: raw='The search tool does not exist', err=invalid character"
    monkeypatch.setattr("urllib.request.urlopen", _server_error({"error": {"message": raw}}))
    info = ServerInfo(Backend.OPENAI_COMPAT, "p", "http://127.0.0.1:11434/v1", False, True)
    with pytest.raises(ToolCallParseError) as caught:
        async for _ in LlamaCppServer().chat_stream(info, [ChatMessage("user", "x")]):
            pass
    assert caught.value.detail == f"HTTP 500: {raw}"
    # still a RuntimeError, so a caller that does not retry is unchanged
    assert isinstance(caught.value, RuntimeError)
    assert isinstance(caught.value, ToolCallParseErrorInterface)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "message"),
    [(500, "model runner has unexpectedly stopped"), (400, "error parsing tool call: raw='x'")],
)
async def test_other_server_errors_are_not_retryable(
    monkeypatch: pytest.MonkeyPatch, code: int, message: str
) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen", _server_error({"error": {"message": message}}, code)
    )
    info = ServerInfo(Backend.OPENAI_COMPAT, "p", "http://127.0.0.1:11434/v1", False, True)
    with pytest.raises(RuntimeError, match=message) as caught:
        async for _ in LlamaCppServer().chat_stream(info, [ChatMessage("user", "x")]):
            pass
    assert not isinstance(caught.value, ToolCallParseError)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["reasoning", "reasoning_content", "thinking"])
async def test_chat_stream_reports_how_the_reply_ended_and_its_reasoning_length(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    # gpt-oss on Ollama answers with a separate reasoning field; an "empty" turn may have
    # spent its tokens there. Its length is recorded, never its content.
    reply = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": "", field: "I should read the file."},
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 11},
    }
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"completions": reply}))
    info = ServerInfo(Backend.OPENAI_COMPAT, "p", "http://127.0.0.1:11434/v1", False, True)
    chunks = [chunk async for chunk in ollama().chat_stream(info, [ChatMessage("user", "hi")])]
    assert (chunks[-1].text, chunks[-1].finish_reason, chunks[-1].reasoning_chars) == (
        "",
        "stop",
        len("I should read the file."),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("message", [{"content": None}, {"content": "", "reasoning": None}])
async def test_chat_stream_invents_no_finish_reason_or_reasoning(
    monkeypatch: pytest.MonkeyPatch, message: dict[str, object]
) -> None:
    reply = {"choices": [{"message": message}], "usage": {}}
    monkeypatch.setattr("urllib.request.urlopen", Recorder({"completions": reply}))
    info = ServerInfo(Backend.OPENAI_COMPAT, "p", "http://127.0.0.1:11434/v1", False, True)
    chunks = [chunk async for chunk in ollama().chat_stream(info, [ChatMessage("user", "hi")])]
    assert (chunks[-1].finish_reason, chunks[-1].reasoning_chars) == (None, None)
