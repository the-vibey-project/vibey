# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one Ollama client every sovereign provider talks to the local model through."""

import json
import urllib.request
from collections.abc import Mapping

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.engines.interfaces import (
    OllamaChatClientInterface,
    OllamaTransportInterface,
)
from vibey.infrastructure.engines.ollama_chat import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TIMEOUT,
    DEFAULT_OLLAMA_URL,
    OLLAMA_MODEL_ENV,
    OLLAMA_TIMEOUT_ENV,
    OLLAMA_URL_ENV,
    OllamaChatClient,
    UrllibOllamaTransport,
)


class FakeTransport:
    def __init__(self, body: dict[str, object]) -> None:
        self.body = body
        self.calls: list[tuple[str, dict[str, object], int]] = []

    async def post_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> dict[str, object]:
        self.calls.append((url, dict(payload), timeout))
        return self.body


def _answering(content: str) -> FakeTransport:
    return FakeTransport({"message": {"content": content}})


class FakeResponse:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self.raw


def test_the_defaults_are_todays_endpoint_and_model() -> None:
    """Configurable, and nothing about an unconfigured install changes (ADR-0018)."""
    client = OllamaChatClient()
    assert client.base_url == DEFAULT_OLLAMA_URL == "http://127.0.0.1:11434"
    assert client.model == DEFAULT_OLLAMA_MODEL == "gpt-oss:20b"
    assert DEFAULT_OLLAMA_TIMEOUT == 900
    assert isinstance(client, OllamaChatClientInterface)
    assert isinstance(UrllibOllamaTransport(), OllamaTransportInterface)


def test_the_environment_chooses_the_endpoint_model_and_timeout() -> None:
    """VIBEY_OLLAMA_URL is the name vibey-gh's local-review fallback already reads, so one
    setting points both at the same server."""
    assert OLLAMA_URL_ENV == "VIBEY_OLLAMA_URL"
    assert OLLAMA_MODEL_ENV == "VIBEY_OLLAMA_MODEL"
    assert OLLAMA_TIMEOUT_ENV == "VIBEY_OLLAMA_TIMEOUT"
    client = OllamaChatClient.from_environment(
        {
            OLLAMA_URL_ENV: "https://gpu-box.internal:8443/",
            OLLAMA_MODEL_ENV: "qwen2.5-coder:32b",
            OLLAMA_TIMEOUT_ENV: "120",
        }
    )
    assert client.base_url == "https://gpu-box.internal:8443"
    assert client.model == "qwen2.5-coder:32b"
    assert client._timeout == 120


def test_an_explicit_model_beats_the_environment_and_empty_counts_as_unset() -> None:
    """--ollama-model wins over VIBEY_OLLAMA_MODEL; an empty variable is the shell's
    `${VAR:-default}` reading of it, which the workflows already use."""
    chosen = OllamaChatClient.from_environment({OLLAMA_MODEL_ENV: "from-env"}, model="from-flag")
    assert chosen.model == "from-flag"
    empty = OllamaChatClient.from_environment(
        {OLLAMA_URL_ENV: "", OLLAMA_MODEL_ENV: "", OLLAMA_TIMEOUT_ENV: ""}
    )
    assert empty.base_url == DEFAULT_OLLAMA_URL
    assert empty.model == DEFAULT_OLLAMA_MODEL
    assert empty._timeout == DEFAULT_OLLAMA_TIMEOUT


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://127.0.0.1:11434",
        "data:text/plain,hello",
        "127.0.0.1:11434",
        "http://",
        "",
    ],
)
def test_only_an_http_endpoint_with_a_host_is_accepted(url: str) -> None:
    """`urlopen` also speaks file:, ftp: and data:. A typo in the endpoint must fail at
    startup, naming the variable to fix, not read a local file and call it an answer."""
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_URL: .*http\\(s\\) URL with a host"):
        OllamaChatClient(base_url=url)


def test_the_environment_url_is_checked_too() -> None:
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_URL"):
        OllamaChatClient.from_environment({OLLAMA_URL_ENV: "file:///tmp/ollama"})


def test_a_blank_model_or_a_bad_timeout_is_refused() -> None:
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_MODEL: the local model name is empty"):
        OllamaChatClient(model="   ")
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_TIMEOUT: must be a positive number"):
        OllamaChatClient(timeout=0)
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_TIMEOUT: must be a whole number"):
        OllamaChatClient.from_environment({OLLAMA_TIMEOUT_ENV: "soon"})
    with pytest.raises(ConfigError, match="must be a positive number, got -5"):
        OllamaChatClient.from_environment({OLLAMA_TIMEOUT_ENV: "-5"})


@pytest.mark.asyncio
async def test_a_question_goes_out_constrained_and_deterministic() -> None:
    transport = _answering('{"answer": 42}')
    client = OllamaChatClient(
        base_url="http://model-host:11434/", model="m:1", timeout=30, transport=transport
    )
    schema = {"type": "object", "properties": {"answer": {"type": "integer"}}}

    answer = await client.ask("be terse", "what is it?", schema)

    assert answer == {"answer": 42}
    ((url, payload, timeout),) = transport.calls
    assert url == "http://model-host:11434/api/chat"
    assert timeout == 30
    assert payload["model"] == "m:1"
    assert payload["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "what is it?"},
    ]
    # Constrained decoding is the whole reason the sovereign path is reliable: the schema
    # is compiled to a grammar, so malformed JSON is unreachable rather than unlikely.
    assert payload["format"] == schema
    assert payload["stream"] is False
    assert payload["options"] == {"temperature": 0, "num_ctx": 4096}


@pytest.mark.asyncio
async def test_a_gateway_that_is_not_ollama_cannot_pass_for_an_answer() -> None:
    """Constrained decoding guarantees the schema only if the thing on the other end is
    actually Ollama. This is a process boundary, so the shape is asserted, not trusted."""
    with pytest.raises(ValueError, match="expected a JSON object, got list"):
        await OllamaChatClient(transport=_answering("[1, 2, 3]")).ask("s", "u", {})
    for body in ({"nothing": "useful"}, {"message": "flat"}, {"message": {"content": 7}}):
        with pytest.raises(ValueError, match="no message content"):
            await OllamaChatClient(transport=FakeTransport(body)).ask("s", "u", {})


def test_the_context_window_is_sized_to_the_prompt() -> None:
    """Ollama's default window is far smaller than a full ledger, and overflowing it
    degrades generation from seconds to never-finishes rather than erroring."""
    client = OllamaChatClient()
    assert client.context_window(0) == 4096
    assert client.context_window(300_000) == 32768
    assert 4096 < client.context_window(60_000) < 32768


@pytest.mark.asyncio
async def test_the_transport_posts_json_and_returns_the_decoded_body() -> None:
    seen: list[tuple[urllib.request.Request, int]] = []

    def opener(request: urllib.request.Request, *, timeout: int) -> FakeResponse:
        seen.append((request, timeout))
        return FakeResponse(b'{"message": {"content": "{}"}}')

    body = await UrllibOllamaTransport(opener=opener).post_json(
        "http://127.0.0.1:11434/api/chat", {"a": 1}, timeout=7
    )

    assert body == {"message": {"content": "{}"}}
    ((request, timeout),) = seen
    assert timeout == 7
    assert request.full_url == "http://127.0.0.1:11434/api/chat"
    assert request.data is not None and json.loads(request.data) == {"a": 1}
    assert request.get_header("Content-type") == "application/json"


@pytest.mark.asyncio
async def test_the_transport_refuses_a_non_object_response() -> None:
    def opener(request: urllib.request.Request, *, timeout: int) -> FakeResponse:
        return FakeResponse(b"[1, 2]")

    with pytest.raises(ValueError, match="non-object response"):
        await UrllibOllamaTransport(opener=opener).post_json(
            "https://127.0.0.1:11434/api/chat", {}, timeout=1
        )


@pytest.mark.asyncio
async def test_the_transport_refuses_a_non_http_url_before_opening_anything() -> None:
    """Safe on its own, not only behind the client's construction-time check."""
    opened: list[object] = []

    def opener(request: urllib.request.Request, *, timeout: int) -> FakeResponse:
        opened.append(request)
        return FakeResponse(b"{}")

    with pytest.raises(ValueError, match="refusing a non-HTTP model endpoint"):
        await UrllibOllamaTransport(opener=opener).post_json("file:///etc/passwd", {}, timeout=1)
    assert opened == []


# A real reply from gpt-oss:20b, recorded from a local Ollama on 2026-09-22 (POST
# /api/chat, stream false, the one user message below). GPT-OSS answers on two channels:
# `thinking` carries its reasoning and `content` the answer, and only `content` is read.
GPT_OSS_20B_REPLY: dict[str, object] = {
    "model": "gpt-oss:20b",
    "created_at": "2026-09-22T15:07:14.136724Z",
    "message": {
        "role": "assistant",
        "content": '{"ok": true}',
        "thinking": 'User says: "Reply with {"ok": true} and nothing else". So just '
        "output that JSON exactly. No additional explanation.",
    },
    "done": True,
    "done_reason": "stop",
    "total_duration": 1850002459,
    "load_duration": 39364084,
    "prompt_eval_count": 77,
    "prompt_eval_cached_count": 72,
    "prompt_eval_duration": 116239000,
    "eval_count": 41,
    "eval_duration": 1616024000,
}


@pytest.mark.asyncio
async def test_a_gpt_oss_reply_is_read_from_its_content_never_its_thinking() -> None:
    message = GPT_OSS_20B_REPLY["message"]
    assert isinstance(message, dict) and message["thinking"]  # a real reasoning channel
    client = OllamaChatClient(transport=FakeTransport(GPT_OSS_20B_REPLY))
    assert await client.ask("system", "user", {"type": "object"}) == {"ok": True}


@pytest.mark.asyncio
async def test_thinking_alone_is_no_answer() -> None:
    reply: dict[str, object] = {"message": {"role": "assistant", "thinking": '{"ok": true}'}}
    client = OllamaChatClient(transport=FakeTransport(reply))
    with pytest.raises(ValueError, match="no message content"):
        await client.ask("system", "user", {"type": "object"})
