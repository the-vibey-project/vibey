# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`VIBEY_OLLAMA_THINK` and `VIBEY_OLLAMA_RETRY_CONTEXT`: the first request's reasoning level,
and a retry that opens a larger window when the window was what ran out."""

import pytest

from tests.infrastructure.engines.test_ollama_chat import SequenceTransport, _cut_short
from vibey.domain.config import ConfigError
from vibey.infrastructure.engines.ollama_chat import (
    DEFAULT_OLLAMA_RETRY_CONTEXT,
    OLLAMA_RETRY_CONTEXT_ENV,
    OLLAMA_THINK_ENV,
    OllamaChatClient,
)

OK = {"message": {"content": '{"ok": true}'}}


async def test_the_first_request_asks_for_the_reasoning_level_the_operator_set() -> None:
    transport = SequenceTransport([OK])
    await OllamaChatClient(think="low", transport=transport).ask("s", "u", "json")
    assert transport.calls[0][1]["think"] == "low"


async def test_with_nothing_set_the_first_request_leaves_reasoning_to_the_model() -> None:
    transport = SequenceTransport([OK])
    await OllamaChatClient(transport=transport).ask("s", "u", "json")
    assert "think" not in transport.calls[0][1]


async def test_the_retry_still_asks_for_its_own_lighter_level() -> None:
    transport = SequenceTransport([_cut_short(), OK])
    client = OllamaChatClient(think="high", retry_think="low", transport=transport)
    await client.ask("s", "u", "json")
    assert transport.calls[0][1]["think"] == "high"
    assert transport.calls[1][1]["think"] == "low"


def test_the_first_reasoning_level_is_read_from_the_environment_and_checked() -> None:
    assert OLLAMA_THINK_ENV == "VIBEY_OLLAMA_THINK"
    assert OllamaChatClient.from_environment({})._think is None
    assert OllamaChatClient.from_environment({OLLAMA_THINK_ENV: ""})._think is None
    assert OllamaChatClient.from_environment({OLLAMA_THINK_ENV: " LOW "})._think == "low"
    assert OllamaChatClient.from_environment({OLLAMA_THINK_ENV: "false"})._think is False
    assert OllamaChatClient.from_environment({OLLAMA_THINK_ENV: "none"})._think is None
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_THINK: must be one of"):
        OllamaChatClient.from_environment({OLLAMA_THINK_ENV: "loud"})
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_THINK: must be one of"):
        OllamaChatClient(think="loud")


async def test_a_prompt_that_filled_the_window_gets_a_larger_one_on_the_retry() -> None:
    """The observed failure: a 6504-token prompt in an 8192 window left 1688 tokens for the
    reasoning and the answer, and the retry asked again with the same window."""
    transport = SequenceTransport([_cut_short(prompt_tokens=6504), OK])
    client = OllamaChatClient(context_ceiling=8192, transport=transport)

    await client.ask("s", "x" * 19_000, "json")

    first, second = (call[1] for call in transport.calls)
    assert first["options"]["num_ctx"] == 8192
    assert first["options"]["num_predict"] == 2048
    assert second["options"] == {"temperature": 0, "num_ctx": 10600, "num_predict": 4096}


async def test_the_retry_window_stops_at_the_retry_ceiling() -> None:
    transport = SequenceTransport([_cut_short(prompt_tokens=15_000), OK])
    client = OllamaChatClient(context_ceiling=8192, retry_context=16384, transport=transport)

    await client.ask("s", "x" * 19_000, "json")

    second = transport.calls[1][1]["options"]
    assert second["num_ctx"] == 16384
    assert second["num_predict"] == 2048  # only 1384 tokens of room: never less than the budget


async def test_the_retry_ceiling_equal_to_the_context_ceiling_keeps_the_retry_inside_it() -> None:
    transport = SequenceTransport([_cut_short(prompt_tokens=6504), OK])
    client = OllamaChatClient(context_ceiling=8192, retry_context=8192, transport=transport)

    await client.ask("s", "x" * 19_000, "json")

    assert transport.calls[1][1]["options"]["num_ctx"] == 8192


async def test_a_configured_ceiling_above_the_retry_ceiling_is_never_lowered() -> None:
    transport = SequenceTransport([_cut_short(prompt_tokens=30_000), OK])
    client = OllamaChatClient(context_ceiling=40_000, retry_context=8192, transport=transport)

    await client.ask("s", "x" * 90_000, "json")

    assert transport.calls[1][1]["options"]["num_ctx"] == 34_096


def test_the_retry_ceiling_is_read_from_the_environment_and_checked() -> None:
    assert OLLAMA_RETRY_CONTEXT_ENV == "VIBEY_OLLAMA_RETRY_CONTEXT"
    assert DEFAULT_OLLAMA_RETRY_CONTEXT == OllamaChatClient.CONTEXT_CEILING == 32768
    assert OllamaChatClient.from_environment({})._retry_context == 32768
    assert OllamaChatClient.from_environment({OLLAMA_RETRY_CONTEXT_ENV: ""})._retry_context == 32768
    env = {OLLAMA_RETRY_CONTEXT_ENV: " 16384 "}
    assert OllamaChatClient.from_environment(env)._retry_context == 16384
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_RETRY_CONTEXT: must be a whole number"):
        OllamaChatClient.from_environment({OLLAMA_RETRY_CONTEXT_ENV: "big"})
    with pytest.raises(ConfigError, match="VIBEY_OLLAMA_RETRY_CONTEXT: must be at least 4096"):
        OllamaChatClient.from_environment({OLLAMA_RETRY_CONTEXT_ENV: "1000"})
